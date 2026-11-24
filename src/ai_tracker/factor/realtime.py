"""Real-time factors: the C3 panel and the two block factors as estimated on a given origin (computation date).

Specification: docs/steg2/c3_spec.md (fixed before the first real-data run; register G-B, F-B16-F-B22).

For an origin o (every step uses only rows with known_from <= o; the table is truncated before anything else):
1. Pace per series exactly as the state engine computes it (register section 1, `state.measures.measure_path` on
   as_of(o)): sub-monthly series to calendar months (the still-filling last month dropped), then 12-month (monthly)
   or 4-quarter (quarterly) change in 100 x log, or in percentage points for shares.
2. Window: pace months from SAMPLE_START to o's calendar month. A quarterly value sits in its quarter's last month.
3. F-B16: z = (pace - mean) / SD (ddof = 1) over the series' pace values in the window. A series enters when it has at
   least 24 monthly (8 quarterly) pace values in the window; otherwise it is left out on that origin.
4. A block is estimated when at least MIN_SERIES series are eligible; otherwise its factor is missing on that origin.
5. EM + Kalman smoother per block (dfm.py), re-estimated from the same deterministic start on every origin (F-B17).
   The factor path for the origin is the smoothed path over the window.

`vintage(table, o)` returns that path; `realtime_monthly(table, start, end)` the real-time monthly series in which
month m is the value for m in the vintage of m's last day (for C4). Both refuse origins after the development period
while the holdout is closed (guard.py). Results are cached under data/cache/factor/ (never committed), keyed by the
spec version, the origin and a hash of the rows known at the origin.
"""

from __future__ import annotations

import hashlib
import pickle
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from ai_tracker import config
from ai_tracker.factor import dfm, guard
from ai_tracker.state import measures

SPEC_VERSION = "c3-v1"  # docs/steg2/c3_spec.md
SAMPLE_START = pd.Period("2010-01", "M")
MIN_PACE = {"M": 24, "Q": 8}  # F-B16
MIN_SERIES = 2  # eligible series needed to estimate a block on an origin

# F-B21: fixed list per block for the whole backtest (G-A 2026-11-24 core series; G1, G2 and annual series excluded).
# BTOS enters as one series per regime (every key btos_ai_use_v<n>), missing outside its regime.
BLOCKS: dict[str, list[str]] = {
    "capex": [
        # G5
        "capex_hyp4", "us_constr_datacenter", "us_pfi_info_proc_eq_sw", "capex_ocf_hyp4", "capex_orcl",
        # G6
        "tsmc_revenue_m", "us_ip_semis_m", "us_ip_computers_m", "us_imports_tw_m", "us_imports_kr_m",
        "rev_amd_datacenter", "rev_avgo_semis", "rev_mrvl_datacenter", "asml_net_sales",
        # G7 (pjm_lf_peak_*_h5 are annual: excluded)
        *[f"us_elec_sales_com_{s}_m" for s in ("va", "tx", "ga", "az", "or", "oh")],
        *[f"eia930_avg_{s}_m" for s in ("pjm_dom", "erco", "azps", "soco", "srp")],
    ],
    "demand": [
        # G3 (eu_ai_ent_* are annual: excluded; BTOS: REGIME_PATTERNS)
        *[f"g3_npm_{s}_w" for s in ("openai", "anthropic_sdk", "langchain", "vercel_ai")],
        *[f"g3_pypi_{s}_wed" for s in ("openai", "anthropic", "langchain", "llama_index")],
        *[f"g3_wiki_{s}_en" for s in ("chatgpt", "llm", "genai")],
        "g3_cf_bots_ai_crawler_share", "g3_cf_ai_purpose_user_action",
        # G4 incl. RPO
        "rev_aws", "rev_google_cloud", "rev_msft_cloud", "rev_nvda_datacenter", "rev_orcl_cloud", "rpo_hyp4",
        # G8
        *[f"ai_postings_share_{c}_d" for c in ("us", "gb", "de", "fr", "ca", "au", "ie", "it", "nl")],
    ],
}
REGIME_PATTERNS: dict[str, list[str]] = {"demand": [r"btos_ai_use_v\d+"]}
# F-B20: quarterly stocks and shares are observed as the latent rate of the quarter's last month; other quarterly
# series are flows (mean of the three months).
QUARTERLY_STOCKS = {"rpo_hyp4", "capex_ocf_hyp4"}
# Components of derived series (state.register.DERIVED), kept when the table is cut to the panel's series.
DERIVED_INPUTS = {"capex_ocf_hyp4": ("capex_hyp4", "ocf_hyp4")}

CACHE_DIR = config.REPO / "data" / "cache" / "factor" / SPEC_VERSION


@dataclass
class SeriesInfo:
    key: str
    freq: str  # measure frequency (M or Q)
    kind: str  # dfm.MONTHLY / FLOW / STOCK
    n_pace: int
    mean: float = float("nan")
    sd: float = float("nan")
    eligible: bool = False
    reason: str = ""
    last_month: str | None = None


@dataclass
class Panel:
    block: str
    months: pd.PeriodIndex
    z: np.ndarray  # (T, N) eligible series only
    keys: list[str]
    kinds: list[str]
    info: list[SeriesInfo]  # every listed series, eligible or not


@dataclass
class BlockFit:
    block: str
    available: bool
    reason: str = ""
    keys: list[str] = field(default_factory=list)
    loadings: dict = field(default_factory=dict)
    idio: dict = field(default_factory=dict)
    a: float = float("nan")
    loglik: float = float("nan")
    n_iter: int = 0
    converged: bool = False
    series: list = field(default_factory=list)  # SeriesInfo as dicts


@dataclass
class Vintage:
    origin: pd.Timestamp
    path: pd.DataFrame  # index = months (PeriodIndex M); columns capex, demand (smoothed), capex_var, demand_var
    fits: dict  # block -> BlockFit
    spec_version: str = SPEC_VERSION

    def available(self, block: str) -> bool:
        return self.fits[block].available

    def mean_over(self, block: str, months) -> float:
        if not self.available(block):
            return float("nan")
        s = self.path[block].reindex(pd.PeriodIndex(months, freq="M"))
        return float(s.mean()) if s.notna().all() and len(s) else float("nan")


# ------------------------------------------------------------------ series and table


def block_series(block: str, keys) -> list[str]:
    """The block's series: the fixed list plus every regime series present in `keys`."""
    out = list(BLOCKS[block])
    for pat in REGIME_PATTERNS.get(block, []):
        rx = re.compile(pat + "$")
        out += sorted((k for k in set(keys) if rx.match(k)), key=lambda k: int(re.findall(r"\d+$", k)[0]))
    return out


def relevant(table: pd.DataFrame) -> pd.DataFrame:
    keys = set(table["series"].unique())
    need = set()
    for b in BLOCKS:
        for k in block_series(b, keys):
            need.add(k)
            need.update(DERIVED_INPUTS.get(k, ()))
    return table[table["series"].isin(need)]


def truncate(table: pd.DataFrame, origin) -> pd.DataFrame:
    """Rows known on or before the origin, of the panel's series only. Nothing after the origin survives this."""
    t = relevant(table)
    kf = pd.to_datetime(t["known_from"])
    return t[kf <= pd.Timestamp(origin)].assign(known_from=kf[kf <= pd.Timestamp(origin)])


def _month(period: str, freq: str) -> pd.Period:
    p = pd.Period(period, freq="Q-DEC" if freq == "Q" else "M")
    return p.asfreq("M", "e") if freq == "Q" else p


def panel(ctx: measures.Context, origin, block: str) -> Panel:
    origin = pd.Timestamp(origin)
    months = pd.period_range(SAMPLE_START, origin.to_period("M"), freq="M")
    cols, keys, kinds, info = [], [], [], []
    if len(months) == 0:  # origin before the sample start: nothing to estimate
        return Panel(block, months, np.empty((0, 0)), keys, kinds, info)
    for key in block_series(block, ctx.keys()):
        try:
            m, path = measures.measure_path(key, origin, ctx)
        except KeyError:  # not in the catalog
            info.append(SeriesInfo(key, "", "", 0, reason="saknas i katalogen"))
            continue
        freq = m.get("measure_freq", m.get("freq", ""))
        if path is None or freq not in MIN_PACE:
            info.append(SeriesInfo(key, freq, "", 0, reason=m.get("reason") or "ingen takt"))
            continue
        pace = path["pace"].astype(float)
        pace.index = pd.PeriodIndex([_month(p, freq) for p in pace.index], freq="M")
        pace = pace[(pace.index >= months[0]) & (pace.index <= months[-1])].dropna()
        kind = dfm.MONTHLY if freq == "M" else (dfm.STOCK if key in QUARTERLY_STOCKS else dfm.FLOW)
        si = SeriesInfo(key, freq, kind, int(len(pace)), last_month=str(pace.index.max()) if len(pace) else None)
        if len(pace) < MIN_PACE[freq]:
            si.reason = f"{len(pace)} taktvärden < {MIN_PACE[freq]}"
            info.append(si)
            continue
        mu, sd = float(pace.mean()), float(pace.std(ddof=1))
        si.mean, si.sd = mu, sd
        if not np.isfinite(sd) or sd <= 0:
            si.reason = "standardavvikelse 0"
            info.append(si)
            continue
        si.eligible = True
        info.append(si)
        cols.append(((pace - mu) / sd).reindex(months).to_numpy(dtype=float))
        keys.append(key)
        kinds.append(kind)
    z = np.column_stack(cols) if cols else np.empty((len(months), 0))
    return Panel(block, months, z, keys, kinds, info)


# ------------------------------------------------------------------ estimation


def fit_block(p: Panel) -> tuple[BlockFit, np.ndarray | None, np.ndarray | None]:
    bf = BlockFit(p.block, False, keys=list(p.keys), series=[vars(s) for s in p.info])
    if len(p.keys) < MIN_SERIES:
        bf.reason = f"{len(p.keys)} valbara serier < {MIN_SERIES}"
        return bf, None, None
    r = dfm.fit(p.z, p.kinds)
    bf.available = True
    bf.loadings = dict(zip(p.keys, map(float, r.params.lam)))
    bf.idio = dict(zip(p.keys, map(float, r.params.R)))
    bf.a, bf.loglik, bf.n_iter, bf.converged = r.params.a, r.loglik, r.n_iter, r.converged
    return bf, r.f, r.f_var


def estimate(table: pd.DataFrame, origin) -> Vintage:
    """Both block factors as estimated on `origin` from the rows known then (no cache, no guard)."""
    origin = pd.Timestamp(origin)
    t = truncate(table, origin)
    ctx = measures.Context(t)
    months = pd.period_range(SAMPLE_START, origin.to_period("M"), freq="M")
    path = pd.DataFrame(index=months, dtype=float)
    fits = {}
    for block in BLOCKS:
        bf, f, v = fit_block(panel(ctx, origin, block))
        fits[block] = bf
        path[block] = f if f is not None else np.nan
        path[f"{block}_var"] = v if v is not None else np.nan
    return Vintage(origin, path, fits)


def _fingerprint(t: pd.DataFrame) -> str:
    cols = ["series", "period", "value", "known_from"]
    h = pd.util.hash_pandas_object(t[cols].sort_values(cols[:2] + ["known_from"]), index=False).to_numpy()
    return hashlib.sha256(h.tobytes()).hexdigest()[:16]


def vintage(table: pd.DataFrame, origin, cache: bool = True, cache_dir: Path | None = None) -> Vintage:
    """The factors on `origin` (guarded: raises guard.HoldoutClosed after the development period)."""
    origin = guard.check(origin, "factor vintage")
    if not cache:
        return estimate(table, origin)
    t = truncate(table, origin)
    d = Path(cache_dir or CACHE_DIR)
    path = d / f"{origin.date()}_{_fingerprint(t)}.pkl"
    if path.exists():
        with path.open("rb") as fh:
            return pickle.load(fh)
    v = estimate(t, origin)
    d.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("wb") as fh:
        pickle.dump(v, fh)
    tmp.replace(path)
    return v


def realtime_monthly(table: pd.DataFrame, start, end, cache: bool = True) -> pd.DataFrame:
    """Real-time monthly factor series for C4: month m -> the value for m in the vintage of m's last day, plus the
    number of series in each block on that day. NaN where a block is not available. Guarded like `vintage`."""
    months = pd.period_range(pd.Period(start, "M"), pd.Period(end, "M"), freq="M")
    guard.check(months[-1].end_time.normalize(), "real-time factor series")
    rows = []
    for m in months:
        v = vintage(table, m.end_time.normalize(), cache=cache)
        row = {"month": m}
        for b in BLOCKS:
            row[b] = float(v.path.at[m, b]) if v.available(b) else float("nan")
            row[f"n_{b}"] = len(v.fits[b].keys)
        rows.append(row)
    return pd.DataFrame(rows).set_index("month")
