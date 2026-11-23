"""Daily package downloads -> W-SUN weekly totals (npm and PyPI, track B1). Shared by sources/npm.py and
sources/pypi_bq.py.

Rules (docs/kallor/utvecklaradoption.md):
- A week (Monday..Sunday) is kept only when it is complete in the source: its Sunday is on or before the last
  day the source covers, and Sunday + lag_days <= today (the value would not have been known earlier).
- Gap days (NaN: the source reported nothing for every package that day, e.g. npm 2026-10-14) are filled
  from the package's own weekday profile: weekly = sum of the reported days / their share of the week in the
  package's last 8 complete weeks *before* this week (past data only). With fewer than 4 such weeks the
  share is n_reported / 7. A week with fewer than MIN_DAYS reported days is dropped.
- The series starts at `start` (a Monday) or else at the first week with a download.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MIN_DAYS = 4  # a week needs at least 4 reported days
PROFILE_WEEKS = 8  # weekday profile from the last 8 complete weeks before the week
PROFILE_MIN = 4


def weekly(daily: pd.Series, today, lag_days: int, start=None) -> pd.Series:
    """`daily`: index = every covered day (DatetimeIndex), value = downloads, NaN = gap day.

    Returns weekly totals on a W-SUN PeriodIndex (float, rounded to whole downloads)."""
    daily = daily.sort_index().astype(float)
    if daily.empty:
        return pd.Series(dtype=float)
    first = pd.Timestamp(start) if start is not None else daily.index[(daily > 0).to_numpy()].min()
    if pd.isna(first):
        return pd.Series(dtype=float)
    last_known = pd.Timestamp(today).normalize() - pd.Timedelta(days=lag_days)
    days = pd.date_range(first - pd.Timedelta(days=first.weekday()), daily.index.max(), freq="D")
    d = daily.reindex(days)  # days outside the covered range are NaN, then handled like gap days
    d[d.index < first] = 0.0  # before the start: the package (or this owner of the name) did not exist
    weeks = d.index.to_period("W-SUN")
    frame = pd.DataFrame({"v": d.to_numpy(), "week": weeks, "dow": d.index.dayofweek})
    grid = frame.pivot(index="week", columns="dow", values="v").reindex(columns=range(7))
    grid = grid[(grid.index.end_time.normalize() <= min(daily.index.max(), last_known))]
    out, history = {}, []
    for week, row in grid.iterrows():
        vals = row.to_numpy(dtype=float)
        ok = ~np.isnan(vals)
        if ok.all():
            out[week] = vals.sum()
            if vals.sum() > 0:
                history.append(vals / vals.sum())
            continue
        if ok.sum() < MIN_DAYS:
            continue
        recent = history[-PROFILE_WEEKS:]
        share = np.mean(recent, axis=0)[ok].sum() if len(recent) >= PROFILE_MIN else ok.sum() / 7
        out[week] = vals[ok].sum() / share if share > 0 else vals[ok].sum()
    s = pd.Series(out, dtype=float).round()
    s.index = pd.PeriodIndex(s.index, freq="W-SUN")
    return s
