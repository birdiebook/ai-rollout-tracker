"""Per-series measures as of a computation date (register section 1).

Every value comes from `observations.as_of(series, date)`; every statistic over history (percentiles, the SD
behind the deadband) is computed over the measure's own values for periods known on that date, i.e. an
expanding window that ends at the computation date. Nothing is computed over the full table.

Pipeline for one series and date D:
1. values = as_of(series, D) (backfill-gated series: own snapshots only when they count, see `measure`).
2. D/W/2W series -> calendar months (mean for shares and prices, sum for flows). A month is used only when the
   series already has an observation in a later month (so a month still being filled is never aggregated).
   Observations are assigned to the month their period ends in.
3. Transform and pace: log x100 change over a year, or pp change for shares, or logit change for bounded
   scores, or doubling / halving time from a 24-month log-linear regression of front values (G1, G2).
4. Change in pace, percentiles (minimum history), expanding SD of change in pace, direction with deadband.
5. Surprise: outcome minus the committed live nowcast (N1/N2) in log x100, else minus naive baseline B1
   (drift: previous value x exp(mean of the last 4 log growths)) on the series' own scale.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from ai_tracker import catalog, config, observations
from ai_tracker.state import register as R

LN2 = math.log(2.0)


# ------------------------------------------------------------------ context


def _default_selection(when) -> list[str]:
    """`<valda>`: the selected G1 benchmarks on `when` (registered list plus registered replacements)."""
    from ai_tracker.series import epoch_hub  # lazy: series modules import the sources

    return epoch_hub.selected_on(when)


@dataclass
class Context:
    """The observation table split by series (plus derived series), the catalog and the forecasts root."""

    table: pd.DataFrame
    specs: dict[str, catalog.Spec] = field(default_factory=catalog.by_key)
    forecasts: Path = field(default_factory=lambda: config.REPO / "forecasts")
    core: dict[str, list[str]] = field(default_factory=lambda: R.CORE_SERIES)
    derived: dict = field(default_factory=lambda: R.DERIVED)
    selection: Callable[[pd.Timestamp], list[str]] = field(default_factory=lambda: _default_selection)
    by_series: dict[str, pd.DataFrame] = field(init=False)

    def __post_init__(self):
        t = self.table
        if any(c in t and not pd.api.types.is_datetime64_any_dtype(t[c]) for c in ("known_from", "fetched_at")):
            t = t.copy()
            for c in ("known_from", "fetched_at"):
                t[c] = pd.to_datetime(t[c])
        parts = {k: g for k, g in t.groupby("series", sort=False)}
        for key, (num, den, scale, *_rest) in self.derived.items():
            parts[key] = derived_rows(key, parts.get(num), parts.get(den), scale)
        self.by_series = parts

    def rows(self, key: str) -> pd.DataFrame:
        return self.by_series.get(key, observations._empty())

    def keys(self) -> list[str]:
        return list(self.by_series)


def derived_rows(key: str, num: pd.DataFrame | None, den: pd.DataFrame | None, scale: float) -> pd.DataFrame:
    """Ratio series in observation-table form: one row per (period, vintage of either component).

    The ratio for a period is formed at every known_from of either component, from the latest value of each
    known at that moment, so known_from = the later of the two. Nothing is formed before both exist.
    """
    if num is None or den is None or num.empty or den.empty:
        return observations._empty()
    rows = []
    for period in sorted(set(num["period"]) & set(den["period"])):
        a = num[num["period"] == period].sort_values("known_from")
        b = den[den["period"] == period].sort_values("known_from")
        for kf in sorted(set(a["known_from"]) | set(b["known_from"])):
            ak, bk = a[a["known_from"] <= kf], b[b["known_from"] <= kf]
            if ak.empty or bk.empty or not bk["value"].iloc[-1]:
                continue
            src = "backfill" if "backfill" in (ak["source"].iloc[-1], bk["source"].iloc[-1]) else "derived"
            rows.append((key, a["freq"].iloc[0], period, scale * ak["value"].iloc[-1] / bk["value"].iloc[-1], kf,
                         src, max(ak["fetched_at"].iloc[-1], bk["fetched_at"].iloc[-1])))
    return pd.DataFrame(rows, columns=observations.COLUMNS)


# ------------------------------------------------------------------ rules per series


@dataclass(frozen=True)
class Rule:
    method: str  # log | share | logit | doubling | halving
    agg: str  # mean | sum (only for D/W/2W)
    gated: bool  # backfill-gated (register change 2026-11-23)
    freq: str
    branch: str


def rule_for(key: str, ctx: Context) -> Rule:
    """Measure method from the register (overrides) or, by default, from the catalog unit and branch.

    Default: unit starting with '%' = share (pp); unit naming a 0-1 range = bounded score (logit); otherwise a
    positive quantity (log). G1 positive quantities use doubling time, G2 halving time (register section 1).
    """
    if key in ctx.derived:
        _n, _d, _s, method, freq, branch = ctx.derived[key]
        return Rule(method, "mean", key in R.BACKFILL_GATED, freq, branch)
    spec = ctx.specs.get(key)
    if spec is None:
        raise KeyError(f"{key}: not in the catalog and not a derived series")
    unit = spec.unit.strip().lower()
    if key in R.METHOD_OVERRIDES:
        method = R.METHOD_OVERRIDES[key]
    elif re.search(r"0\s*[-–]\s*1\b", unit):
        method = "logit"
    elif unit.startswith("%"):
        method = "share"
    elif spec.branch == "G1":
        method = "doubling"
    elif spec.branch == "G2":
        method = "halving"
    else:
        method = "log"
    if key in R.AGG_OVERRIDES:
        agg = R.AGG_OVERRIDES[key]
    elif method in ("share", "logit") or " per " in unit or "index" in unit or "pris" in unit:
        agg = "mean"
    else:
        agg = "sum"
    return Rule(method, agg, key in R.BACKFILL_GATED, spec.freq, spec.branch)


# ------------------------------------------------------------------ building blocks


def vintage(rows: pd.DataFrame, when) -> pd.DataFrame:
    """period -> (value, known_from, source) of the latest vintage known on `when`. Same rule as as_of."""
    t = rows[rows["known_from"] <= pd.Timestamp(when)]
    if t.empty:
        return pd.DataFrame(columns=["value", "known_from", "source"])
    return t.sort_values("known_from").groupby("period")[["value", "known_from", "source"]].last()


def to_monthly(s: pd.Series, how: str) -> pd.Series:
    """Sub-monthly series (PeriodIndex) -> calendar months; the last month present is dropped (still filling)."""
    if s.empty:
        return pd.Series(dtype=float)
    month = pd.PeriodIndex(pd.DatetimeIndex(s.index.end_time.normalize()), freq="M")
    g = s.groupby(month).agg(how)
    return g[g.index < month.max()]


def month_of(periods: pd.Index) -> pd.PeriodIndex:
    return pd.PeriodIndex(pd.DatetimeIndex(pd.PeriodIndex(periods).end_time.normalize()), freq="M")


def regular(s: pd.Series, freq: str) -> pd.Series:
    """Reindex on a gap-free period range so that shift(k) means k periods back."""
    if s.empty:
        return s.astype(float)
    rng = pd.period_range(s.index.min(), s.index.max(), freq=s.index.freq or catalog.FREQS[freq])
    return s.reindex(rng).astype(float)


def percentile(x: float, history: np.ndarray, min_n: int) -> float | None:
    """Percentile (0-100, ties count half) of x in the measure's own history; None below the minimum."""
    h = history[np.isfinite(history)]
    if not math.isfinite(x) or len(h) < min_n:
        return None
    return float(100.0 * ((h < x).sum() + 0.5 * (h == x).sum()) / len(h))


def rolling_time(y: pd.Series, window: int, kind: str) -> pd.Series:
    """Doubling (slope > 0) or halving (slope < 0) time in months from a log-linear OLS over `window` months.

    Needs all `window` months present. A slope of the wrong sign (or zero) gives no time (NaN).
    """
    v = y.to_numpy(dtype=float)
    t = np.arange(window, dtype=float)
    tc = t - t.mean()
    out = np.full(len(v), np.nan)
    for i in range(window - 1, len(v)):
        w = v[i - window + 1: i + 1]
        if np.isfinite(w).all():
            slope = float((tc * (w - w.mean())).sum() / (tc * tc).sum())
            if kind == "doubling" and slope > 0:
                out[i] = LN2 / slope
            elif kind == "halving" and slope < 0:
                out[i] = LN2 / -slope
    return pd.Series(out, index=y.index)


def _num(x) -> float | None:
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


# ------------------------------------------------------------------ surprise


def _live_nowcast(key: str, period, when, ctx: Context) -> tuple[float, str] | None:
    sub = R.NOWCAST_TARGETS.get(key)
    if not sub:
        return None
    path = Path(ctx.forecasts) / sub / f"{period}.json"
    if not path.is_file():
        return None
    d = json.loads(path.read_text(encoding="utf-8"))
    if pd.Timestamp(d["origin"]) > pd.Timestamp(when) or d.get("value") is None:
        return None
    return float(d["value"]), f"{sub.upper()} skarp nowcast ({d.get('champion', '?')}, origin {d['origin']})"


def surprise(key: str, rule: Rule, levels: pd.Series, y: pd.Series, when, ctx: Context) -> tuple[float | None, str]:
    """Latest outcome minus the live nowcast (log x100) or minus B1 drift on the transformed scale."""
    if y.empty or not math.isfinite(y.iloc[-1]):
        return None, ""
    period = y.index[-1]
    live = _live_nowcast(key, period, when, ctx)
    if live is not None and levels.iloc[-1] > 0 and live[0] > 0:
        return 100.0 * (math.log(levels.iloc[-1]) - math.log(live[0])), live[1]
    if len(y) < 6 or not np.isfinite(y.iloc[-6:-1].to_numpy()).all():  # y[t-5..t-1]
        return None, "B1 saknas (kräver 5 föregående perioder)"
    last, first = y.iloc[-2], y.iloc[-6]  # mean of the last 4 changes = (y[t-1] - y[t-5]) / 4
    b1 = last + (last - first) / 4.0
    unit = {"log": "log x100", "doubling": "log x100", "halving": "log x100", "share": "pe", "logit": "logit"}
    return float(y.iloc[-1] - b1), f"B1 drift ({unit[rule.method]})"


# ------------------------------------------------------------------ one series


def own_months(rows: pd.DataFrame, when) -> int:
    """Distinct calendar months (by known_from) with own, non-backfill rows known on `when`."""
    t = rows[(rows["known_from"] <= pd.Timestamp(when)) & (rows["source"] != "backfill")]
    return int(t["known_from"].dt.to_period("M").nunique())


def measure(key: str, when, ctx: Context) -> dict:
    """All registered measures of one series as of `when`. `valid` = may count in the diffusion index."""
    return measure_path(key, when, ctx)[0]


def measure_path(key: str, when, ctx: Context) -> tuple[dict, pd.DataFrame | None]:
    """`measure` plus the measure's history as of `when`: a frame indexed by period (str) with the columns level
    (aggregated/transformed input before pace), pace and change (change in pace). None when there is no data.
    The history is the same computation the latest values come from (one vintage, as_of(when)); the site draws it."""
    when = pd.Timestamp(when)
    rule = rule_for(key, ctx)
    rows = ctx.rows(key)
    out: dict = {"series": key, "method": rule.method, "freq": rule.freq, "valid": False, "reason": ""}
    if key in R.BACKFILL_FLAGGED:
        out["flag"] = R.BACKFILL_FLAGGED[key]
    gated_note = ""
    if rule.gated:
        n_own = own_months(rows, when)
        out["own_snapshot_months"] = n_own
        if n_own >= R.OWN_SNAPSHOT_MONTHS:
            rows = rows[rows["source"] != "backfill"]  # counts, on own snapshots only
        else:
            gated_note = f"bakåtfylld: {n_own} < {R.OWN_SNAPSHOT_MONTHS} mån egna ögonblicksbilder, bara beskrivning"

    values = observations.as_of(key, when, rows)
    meta = vintage(rows, when)
    if values.empty:
        out["reason"] = "inga data kända på beräkningsdagen"
        return out, None

    freq = rule.freq
    if freq in R.SUBMONTHLY:
        x = to_monthly(values, rule.agg)
        months = month_of(observations.to_periods(meta.index, freq))
        meta = meta.assign(month=months.astype(str))
        freq = "M"
        if x.empty:
            out["reason"] = "ingen hel månad känd"
            return out, None
        latest = str(x.index[-1])
        m = meta[meta["month"] == latest]
        known_from, sources = m["known_from"].max(), sorted(set(meta["source"]))
        n_obs = int(len(m))
    else:
        x = values
        latest = str(x.index[-1])
        known_from, sources = meta.loc[latest, "known_from"], sorted(set(meta["source"]))
        n_obs = 1
    x = regular(x, freq)
    out.update(latest_period=latest, known_from=str(pd.Timestamp(known_from).date()), sources=sources,
               level=_num(x.iloc[-1]), obs_in_latest_period=n_obs, measure_freq=freq)

    method = rule.method
    sign = 1.0
    if method in ("doubling", "halving"):
        if freq != "M":
            raise ValueError(f"{key}: doubling/halving time is registered for monthly front values only")
        front = x.cummax() if method == "doubling" else x.cummin()
        front = front.where(x.notna())
        y = 100.0 * np.log(front.where(front > 0))
        pace = rolling_time(y / 100.0, R.DOUBLING_WINDOW, method)
        change = pace - pace.shift(R.DOUBLING_CHANGE_LAG)
        sign = -1.0  # a shorter doubling/halving time is acceleration
        out["pace_unit"] = "månader (fördubblingstid)" if method == "doubling" else "månader (halveringstid)"
    else:
        if method == "log":
            y = 100.0 * np.log(x.where(x > 0))
            out["pace_unit"] = "log x100 per år"
        elif method == "share":
            fraction = bool(re.search(r"0\s*[-–]\s*1\b", ctx.specs[key].unit)) if key in ctx.specs else False
            y = 100.0 * x if fraction else x  # a 0-1 share in percentage points
            out["pace_unit"] = "procentenheter per år"
        elif method == "logit":
            p = x.cummax().where(x.notna())
            y = np.log(p.where((p > 0) & (p < 1)) / (1 - p.where((p > 0) & (p < 1))))
            out["pace_unit"] = "logit per år"
        else:
            raise ValueError(f"{key}: unknown method {method}")
        pace = y - y.shift(R.PACE_LAG[freq])
        change = pace - pace.shift(R.CHANGE_LAG[freq])

    p_now, c_now = pace.iloc[-1], change.iloc[-1]
    min_n = R.MIN_HISTORY[freq]
    out.update(pace=_num(p_now), change_in_pace=_num(c_now),
               pace_percentile=percentile(p_now, pace.to_numpy(), min_n),
               change_percentile=percentile(c_now, change.to_numpy(), min_n),
               n_pace=int(np.isfinite(pace.to_numpy()).sum()), n_change=int(np.isfinite(change.to_numpy()).sum()),
               direction_sign=int(sign))
    s, s_basis = surprise(key, rule, x, y, when, ctx)
    out.update(surprise=_num(s), surprise_basis=s_basis)

    hist = change.to_numpy()
    hist = hist[np.isfinite(hist)]
    sd = float(np.std(hist, ddof=1)) if len(hist) >= R.MIN_SD_VALUES else None
    out["sd_change"] = sd
    if not math.isfinite(p_now):
        out["reason"] = "ingen takt på senaste perioden (för kort historik eller lucka)"
    elif not math.isfinite(c_now):
        out["reason"] = "ingen förändring i takt på senaste perioden (för kort historik eller lucka)"
    elif sd is None:
        out["reason"] = f"standardavvikelse saknas (färre än {R.MIN_SD_VALUES} värden för förändring i takt)"
    else:
        band = R.DEADBAND * sd
        signed = sign * c_now
        out["deadband"] = band
        out["direction"] = 1 if signed > band else -1 if signed < -band else 0
        if gated_note:
            out["reason"] = gated_note
        else:
            out["valid"] = True
    if gated_note and not out["reason"]:
        out["reason"] = gated_note
    path = pd.DataFrame({"level": x, "pace": pace, "change": change})
    path.index = path.index.astype(str)
    return out, path
