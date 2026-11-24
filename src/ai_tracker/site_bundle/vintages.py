"""Compact version history for time travel ("what did we know on date X"), encoding `versions-v1`.

A series' versions are the rows (period, value, known_from) of the observation table. The encoding stores each
distinct period and each distinct known_from day once, and one row per version as three parallel integer/float
arrays sorted by (date, period):

    {"encoding": "versions-v1", "freq": "M", "native_freq": "M", "aggregation": null,
     "periods": ["2016-01", ...], "dates": ["2016-02-15", ...],
     "p": [0, 1, ...], "d": [0, 0, ...], "v": [101.2, 99.8, ...],
     "n_versions": 812, "n_revised_periods": 40, "first_known": "2016-02-15", "last_known": "2026-11-20",
     "collapsed_before": null}

Replay (as_of(D)): walk the rows in order while dates[d[i]] <= D and keep the last v per p. That is exactly
observations.as_of: the latest version with known_from <= D, rows with known_from == D included.

Rules that keep it honest (tested in tests/test_site_bundle.py):
- A row is never dated earlier than its known_from. A known_from with a time of day is moved to the next day.
- Only rows known on the build date are included (known_from <= as_of).
- A version that rounds to the same stored value as the previous version of the same period is dropped (it does not
  change any replay).
- Daily series ("D") are stored as calendar-month versions: for every known_from day d, the registered aggregation
  (state.measures.rule_for(...).agg, to_monthly: the month still being filled is dropped) of as_of(d). Every
  input of such a month value was known on d. The native daily levels are in the series document's `levels`.
- Size guard: a series with more than `max_rows` rows has its oldest versions collapsed: every version known before
  a cutoff day is replaced by the version current at the cutoff, dated at the cutoff (later, never earlier).
  `collapsed_before` then names the cutoff, and time travel before it shows nothing for that series.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from ai_tracker import observations
from ai_tracker.state import measures as M

ENCODING = "versions-v1"
DIGITS = 6
MAX_ROWS = 6000


def _r(x) -> float | None:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(x):
        return None
    if x == 0:
        return 0.0
    return float(f"{x:.{DIGITS}g}")


def day_ceil(ts: pd.Series) -> pd.Series:
    """known_from as a day, never earlier: a time of day moves the row to the next day."""
    ts = pd.to_datetime(ts)
    return ts.dt.ceil("D")


def _monthly_versions(rows: pd.DataFrame, agg: str) -> pd.DataFrame:
    """Calendar-month versions of a daily series: per known_from day d, the registered aggregation (state.measures
    .to_monthly: `agg` over the days of each month, the newest month present dropped) of as_of(d). Incremental: a
    month is re-aggregated only on a day that changes one of its days or completes it."""
    periods = rows["period"].astype(str)
    uniq = pd.Index(periods.unique())
    month_of = dict(zip(uniq, (str(m) for m in M.month_of(observations.to_periods(uniq, "D")))))
    t = rows.assign(period=periods, month=periods.map(month_of)).sort_values(["kday", "known_from"], kind="mergesort")
    fn = np.mean if agg == "mean" else np.sum
    members: dict[str, dict[str, float]] = {}
    last_max = None
    out_p, out_v, out_d = [], [], []
    for d, g in t.groupby("kday", sort=True):
        touched = set()
        for p, m, v in zip(g["period"], g["month"], g["value"]):
            members.setdefault(m, {})[p] = float(v)
            touched.add(m)
        newest = max(members)
        due = {m for m in touched if m < newest}
        if last_max is not None and newest > last_max:
            due |= {m for m in members if last_max <= m < newest}
        last_max = newest
        for m in sorted(due):
            out_p.append(m)
            out_v.append(float(fn(list(members[m].values()))))
            out_d.append(d)
    return pd.DataFrame({"period": out_p, "value": out_v, "kday": out_d})


def _dedupe(df: pd.DataFrame) -> pd.DataFrame:
    """Keep a version only when its stored (rounded) value differs from the previous version of the period."""
    df = df.sort_values(["period", "kday"], kind="mergesort")
    df = df.groupby(["period", "kday"], as_index=False).last()  # several rows on one day: the last one wins
    df["r"] = [_r(v) for v in df["value"]]
    df = df[df["r"].notna()]
    prev = df.groupby("period")["r"].shift(1)
    return df[prev.isna() | (prev != df["r"])]


def _collapse(df: pd.DataFrame, max_rows: int) -> tuple[pd.DataFrame, str | None]:
    if len(df) <= max_rows:
        return df, None
    days = np.sort(df["kday"].unique())
    for cut in days:
        early = df[df["kday"] < cut]
        if early.empty:
            continue
        keep = early.sort_values("kday").groupby("period").tail(1).assign(kday=cut)
        late = df[df["kday"] >= cut]
        merged = pd.concat([keep, late], ignore_index=True)
        merged = _dedupe(merged[["period", "value", "kday"]])
        if len(merged) <= max_rows:
            return merged, str(pd.Timestamp(cut).date())
    last = days[-1]
    keep = df.sort_values("kday").groupby("period").tail(1).assign(kday=last)
    return _dedupe(keep[["period", "value", "kday"]]), str(pd.Timestamp(last).date())


def encode(rows: pd.DataFrame, as_of, agg: str | None = None, max_rows: int = MAX_ROWS) -> dict | None:
    """The versions of one series (observation-table rows) known on `as_of`. `agg`: aggregation for a daily series
    (the registered measure aggregation); None keeps the native frequency."""
    if rows is None or rows.empty:
        return None
    as_of = pd.Timestamp(as_of)
    t = rows[["period", "value", "known_from", "freq"]].copy()
    t["kday"] = day_ceil(t["known_from"])
    t = t[(t["known_from"] <= as_of) & t["value"].notna()]
    if t.empty:
        return None
    native = str(t["freq"].iloc[0])
    freq, aggregation = native, None
    if native == "D" and agg:
        t = _monthly_versions(t, agg)
        freq, aggregation = "M", agg
        if t.empty:
            return None
    df = _dedupe(t[["period", "value", "kday"]])
    df, collapsed = _collapse(df, max_rows)
    periods = sorted(df["period"].astype(str).unique())  # every period format of the table sorts as text
    pidx = {p: i for i, p in enumerate(periods)}
    days = sorted(df["kday"].unique())
    didx = {d: i for i, d in enumerate(days)}
    df = df.assign(pi=df["period"].astype(str).map(pidx), di=df["kday"].map(didx)).sort_values(["di", "pi"])
    n_per_period = df.groupby("pi").size()
    return {"encoding": ENCODING, "freq": freq, "native_freq": native, "aggregation": aggregation,
            "periods": periods, "dates": [str(pd.Timestamp(d).date()) for d in days],
            "p": [int(x) for x in df["pi"]], "d": [int(x) for x in df["di"]], "v": [float(x) for x in df["r"]],
            "n_versions": int(len(df)), "n_revised_periods": int((n_per_period > 1).sum()),
            "first_known": str(pd.Timestamp(days[0]).date()), "last_known": str(pd.Timestamp(days[-1]).date()),
            "collapsed_before": collapsed}


def replay(enc: dict, when) -> dict[str, float]:
    """period -> value as known on `when` (the front end's algorithm, used by the tests)."""
    when = str(pd.Timestamp(when).date())
    out: dict[str, float] = {}
    for p, d, v in zip(enc["p"], enc["d"], enc["v"]):
        if enc["dates"][d] > when:
            break
        out[enc["periods"][p]] = v
    return out
