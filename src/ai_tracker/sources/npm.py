"""npm downloads per day (api.npmjs.org/downloads/range), track B1.

API (github.com/npm/registry, docs/download-counts.md): daily counts per package, computed once per day soon
after UTC midnight; at most 18 months per range query; earliest date 2015-01-10. Scoped names go in the path
as they are (`/downloads/range/<a>:<b>/@anthropic-ai/sdk`).

Days the API returns as 0 for every control package (react and express) are gaps in npm's own data
(e.g. 2020-06-22, 2023-11-03, 2026-10-14): they become NaN for every package and are filled in the weekly
total from the package's weekday profile (sources/download_counts.py). A day not yet computed is also 0, so the
weekly series only keeps weeks whose Sunday + lag is on or before the fetch date.
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

import pandas as pd

from ai_tracker import http
from ai_tracker.sources import download_counts

BASE = "https://api.npmjs.org/downloads/range"
EARLIEST = date(2015, 1, 10)
CHUNK_DAYS = 500  # < 18 months per query
CONTROLS = ["react", "express"]
LAG_DAYS = 2  # Sunday's counts land soon after UTC midnight; Tuesday 00:00 is a conservative known_from


def _ranges(since: date, until: date) -> list[tuple[date, date]]:
    out, cur = [], since
    while cur <= until:
        end = min(cur + timedelta(days=CHUNK_DAYS - 1), until)
        out.append((cur, end))
        cur = end + timedelta(days=1)
    return out


def parse(payload: dict) -> pd.Series:
    rows = payload.get("downloads") or []
    s = pd.Series({pd.Timestamp(r["day"]): float(r["downloads"]) for r in rows}, dtype=float)
    return s.sort_index()


@lru_cache(maxsize=64)
def daily_raw(package: str, since: date, until: date) -> pd.Series:
    """Counts as the API returns them (0 for gaps and for days not computed yet)."""
    parts = []
    for a, b in _ranges(max(since, EARLIEST), until):
        r = http.get(f"{BASE}/{a.isoformat()}:{b.isoformat()}/{package}", source="npm")
        parts.append(parse(r.json()))
    s = pd.concat(parts) if parts else pd.Series(dtype=float)
    return s[~s.index.duplicated(keep="last")].sort_index()


def gap_days(controls: list[pd.Series]) -> pd.DatetimeIndex:
    """Days on which every active control package reports 0: npm reported nothing that day.

    A control is active from its first day with a download (the API returns 0 for express before 2021-09)."""
    frame = pd.concat(controls, axis=1)
    active = frame.gt(0).cummax()
    zero_or_inactive = frame.eq(0) | ~active
    gap = zero_or_inactive.all(axis=1) & active.any(axis=1)
    return pd.DatetimeIndex(frame.index[gap.to_numpy()])


def clean_daily(raw: pd.Series, gaps: pd.DatetimeIndex) -> pd.Series:
    s = raw.copy()
    s[s.index.isin(gaps)] = float("nan")
    return s


def weekly(package: str, since: date, start: date | None = None, today: date | None = None) -> pd.Series:
    """Weekly downloads of `package` (W-SUN), gaps filled, complete and known weeks only."""
    today = today or date.today()
    until = today - timedelta(days=1)
    controls = [daily_raw(c, EARLIEST, until) for c in CONTROLS]
    raw = daily_raw(package, since, until)
    return download_counts.weekly(clean_daily(raw, gap_days(controls)), today, LAG_DAYS, start)
