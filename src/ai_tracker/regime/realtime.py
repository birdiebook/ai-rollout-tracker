"""C4 in real time: one record per computation date (month end), and the registered reporting rules.

Specification: docs/steg2/c4_spec.md (locked before the first real-data run; register G-D with F-D1-F-D8).

On a computation date d (every step uses only rows with known_from <= d; the table is truncated first):
- Markov switching per C3 block: y = the block's smoothed factor path as estimated on d (factor.realtime.vintage),
  from the first month with an observed z-value of a series that entered the estimate, to d's month. At least 60
  months, else no probability. MSIH(2)-AR(0) by EM from the same start on every date (ms.py). The stored value is
  the filtered P(slowdown) for d's month (F-D1).
- BOCPD per core series counted in the state on d (state.branch, same exceptions): pace path as_of(d), standardised
  with its own mean and SD over that path, hazard per frequency, normal-gamma prior (bocpd.py). Stored value
  P(r_T <= 2) at the series' latest period T.

`reported_states` (F-D2) and `reported_breaks` (F-D4) apply the reporting rules to the stored sequence. Neither a
break nor a regime probability changes the diffusion index or the branch state (F-D5, F-D8).
"""

from __future__ import annotations

import hashlib
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from ai_tracker import config
from ai_tracker.factor import realtime as factor_rt
from ai_tracker.regime import bocpd, guard, ms
from ai_tracker.state import branch as state_branch
from ai_tracker.state import measures
from ai_tracker.state import register as R

SPEC_VERSION = "c4-v1"  # docs/steg2/c4_spec.md
BLOCKS = tuple(factor_rt.BLOCKS)  # capex, demand
MIN_MONTHS = 60  # F-D3
HIGH, LOW = 0.8, 0.2  # F-D2
EXPANSION, SLOWDOWN = "expansion", "inbromsning"
BRANCHES = tuple(R.CORE_SERIES)  # G1-G9
DEV_START = pd.Timestamp("2012-01-31")
CACHE_DIR = config.REPO / "data" / "cache" / "regime" / SPEC_VERSION


def month_ends(start, end) -> list[pd.Timestamp]:
    months = pd.period_range(pd.Timestamp(start).to_period("M"), pd.Timestamp(end).to_period("M"), freq="M")
    return [m.end_time.normalize() for m in months]


def truncate(table: pd.DataFrame, date) -> pd.DataFrame:
    kf = pd.to_datetime(table["known_from"])
    keep = kf <= pd.Timestamp(date)
    return table[keep].assign(known_from=kf[keep])


# ------------------------------------------------------------------ Markov switching on one block


def history(vint: factor_rt.Vintage, ctx: measures.Context, date, block: str) -> tuple[pd.Series | None, str]:
    """The block's factor history on `date`: smoothed path from the first month with an observed z-value of a series
    in the estimate to the date's month. (None, reason) when the block is missing."""
    if not vint.available(block):
        return None, f"blocket saknas: {vint.fits[block].reason}"
    p = factor_rt.panel(ctx, date, block)
    used = [p.keys.index(k) for k in vint.fits[block].keys if k in p.keys]
    obs = np.isfinite(p.z[:, used]).any(axis=1) if used else np.zeros(len(p.months), bool)
    if not obs.any():
        return None, "inga observerade z-värden"
    first = p.months[int(np.argmax(obs))]
    y = vint.path[block]
    return y[y.index >= first], ""


def ms_record(y: pd.Series | None, reason: str = "") -> dict:
    out = {"p_slow": float("nan"), "n_months": 0 if y is None else int(len(y)), "first_month": None, "reason": reason}
    if y is None:
        return out
    out["first_month"] = str(y.index[0])
    if len(y) < MIN_MONTHS:
        out["reason"] = f"{len(y)} månader faktorhistorik < {MIN_MONTHS}"
        return out
    r = ms.fit(y.to_numpy(float))
    out.update(p_slow=r.p_slow, mu_slow=float(r.mu[0]), mu_exp=float(r.mu[1]), sd_slow=float(np.sqrt(r.sigma2[0])),
               sd_exp=float(np.sqrt(r.sigma2[1])), p_stay_slow=float(r.P[0, 0]), p_stay_exp=float(r.P[1, 1]),
               loglik=r.loglik, n_iter=r.n_iter, converged=r.converged)
    return out


def smoothed_probabilities(vint: factor_rt.Vintage, ctx: measures.Context, date, block: str) -> pd.Series:
    """Smoothed P(slowdown at t | whole history) from the MS fitted on `date`'s path (F-D6 b). Empty when none."""
    y, _ = history(vint, ctx, date, block)
    if y is None or len(y) < MIN_MONTHS:
        return pd.Series(dtype=float)
    r = ms.fit(y.to_numpy(float))
    return pd.Series(r.smoothed[:, 0], index=y.index)


# ------------------------------------------------------------------ BOCPD on the counted core series


def bocpd_rows(ctx: measures.Context, date) -> list[dict]:
    rows = []
    for code in BRANCHES:
        b = state_branch.branch(code, date, ctx)
        for m in b["series_used"]:
            key = m["series"]
            _m, path = measures.measure_path(key, date, ctx)
            freq = m.get("measure_freq", m.get("freq"))
            row = {"branch": code, "series": key, "freq": freq, "latest_period": m.get("latest_period"),
                   "hazard": bocpd.HAZARD.get(freq, float("nan")), "p_recent": float("nan"), "n_periods": 0,
                   "reason": ""}
            pace = path["pace"].astype(float) if path is not None else pd.Series(dtype=float)
            finite = np.flatnonzero(np.isfinite(pace.to_numpy()))
            if freq not in bocpd.HAZARD or not len(finite):
                row["reason"] = "ingen takt eller okänd frekvens"
                rows.append(row)
                continue
            pace = pace.iloc[finite[0]:]
            x = bocpd.standardize(pace.to_numpy())
            row["n_periods"] = int(len(pace))
            if x is None:
                row["reason"] = "färre än 2 taktvärden eller SD 0"
            else:
                row["p_recent"] = bocpd.p_recent(x, row["hazard"])
            rows.append(row)
    return rows


# ------------------------------------------------------------------ one computation date


def _fingerprint(t: pd.DataFrame) -> str:
    cols = ["series", "period", "value", "known_from"]
    h = pd.util.hash_pandas_object(t[cols], index=False).to_numpy()
    h = np.sort(h)
    return hashlib.sha256(h.tobytes()).hexdigest()[:16]


def compute(table: pd.DataFrame, date, cache: bool = True, cache_dir: Path | None = None,
            factor_cache: bool = True) -> dict:
    """The C4 record for computation date `date` (guarded: raises HoldoutClosed after the development period)."""
    date = guard.check(date, "C4 record")
    t = truncate(table, date)
    path = None
    if cache:
        d = Path(cache_dir or CACHE_DIR)
        path = d / f"{date.date()}_{_fingerprint(t)}.pkl"
        if path.exists():
            with path.open("rb") as fh:
                return pickle.load(fh)
    ctx = measures.Context(t)
    vint = factor_rt.vintage(t, date, cache=factor_cache)
    fctx = measures.Context(factor_rt.truncate(t, date))
    rec = {"date": date, "spec_version": SPEC_VERSION, "ms": {}, "bocpd": bocpd_rows(ctx, date)}
    for block in BLOCKS:
        y, reason = history(vint, fctx, date, block)
        rec["ms"][block] = {**ms_record(y, reason), "n_series": len(vint.fits[block].keys)}
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("wb") as fh:
            pickle.dump(rec, fh)
        tmp.replace(path)
    return rec


def run(table: pd.DataFrame, start, end, cache: bool = True, progress=None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Records for every month end in [start, end] -> (ms frame, bocpd frame). Guarded before anything runs."""
    dates = month_ends(start, end)
    guard.check(dates[-1], "C4 run")
    ms_rows, b_rows = [], []
    for d in dates:
        rec = compute(table, d, cache=cache)
        for block, r in rec["ms"].items():
            ms_rows.append({"date": d, "block": block, **r})
        for r in rec["bocpd"]:
            b_rows.append({"date": d, **r})
        if progress:
            progress(d)
    return pd.DataFrame(ms_rows), pd.DataFrame(b_rows)


# ------------------------------------------------------------------ reporting rules on stored values


def state_sequence(p: pd.Series) -> pd.Series:
    """F-D2 on a monthly sequence of stored values (index = month Periods or month-end dates, NaN = no value).
    Expansion from the first value; shift when two consecutive months both >= 0.8 (<= 0.2 back); a missing month
    breaks the pair; the state is kept between 0.2 and 0.8 and over missing months. None before the first value."""
    idx = pd.PeriodIndex(pd.DatetimeIndex(p.index).to_period("M")) if not isinstance(p.index, pd.PeriodIndex) \
        else p.index
    s = pd.Series(p.to_numpy(float), index=idx).sort_index()
    out, state, prev_m, prev_v = [], None, None, None
    for m, v in s.items():
        if np.isfinite(v):
            if state is None:
                state = EXPANSION
            consecutive = prev_m is not None and (m - prev_m).n == 1 and prev_v is not None and np.isfinite(prev_v)
            if consecutive and v >= HIGH and prev_v >= HIGH:
                state = SLOWDOWN
            elif consecutive and v <= LOW and prev_v <= LOW:
                state = EXPANSION
        out.append(state)
        prev_m, prev_v = m, v
    return pd.Series(out, index=s.index, dtype=object)


def reported_states(ms_frame: pd.DataFrame) -> pd.DataFrame:
    """Adds `state` (F-D2) and `shift` (the new state on a date where it changed) per block."""
    parts = []
    for block, g in ms_frame.sort_values("date").groupby("block", sort=False):
        g = g.copy()
        st = state_sequence(pd.Series(g["p_slow"].to_numpy(float), index=pd.DatetimeIndex(g["date"])))
        g["state"] = st.to_numpy()
        prev = g["state"].shift(1)
        g["shift"] = np.where(prev.notna() & (g["state"] != prev), g["state"], None)
        parts.append(g)
    return pd.concat(parts).sort_values(["date", "block"]).reset_index(drop=True) if parts else ms_frame


def _ordinal(period: str, freq: str) -> int:
    return pd.Period(period, freq={"Q": "Q-DEC", "A": "Y-DEC"}.get(freq, freq)).ordinal


def reported_breaks(b_frame: pd.DataFrame) -> pd.DataFrame:
    """Adds `break` (F-D4): P(r_T <= 2) >= 0.8 at the latest period and no break reported for the same series on an
    earlier date with latest period p' such that T - p' <= 3 periods."""
    b = b_frame.sort_values("date").copy()
    flags = np.zeros(len(b), bool)
    last: dict[str, int] = {}
    for i, (_, r) in enumerate(b.iterrows()):
        if not (np.isfinite(r["p_recent"]) and r["p_recent"] >= bocpd.THRESHOLD) or r["latest_period"] is None:
            continue
        o = _ordinal(r["latest_period"], r["freq"])
        if r["series"] in last and o - last[r["series"]] <= bocpd.QUIET:
            continue
        flags[i] = True
        last[r["series"]] = o
    b["break"] = flags
    return b.reset_index(drop=True)
