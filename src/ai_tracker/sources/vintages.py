"""Monthly release-dated rows from dated leaderboard (or price list) events.

An event is one published state of a source: `published` (the date the state refers to, e.g. a leaderboard's
publish date), `value` (the number computed from that state, e.g. the top rating), `evidence` (the earliest
date we can document that the state was public, e.g. the commit that added it) and `source` ("release" when the
evidence is a dated record, "backfill" when it is only a later bulk upload).

Monthly rule (frontier as known by month end, register 2026-11-23): month m takes the value of the latest
published state with published <= end of m among the states documented by then.
- First vintage: known_from = end of m + 1 day, using states with evidence <= end of m (a state documented on
  the last day counts, since as_of reads a date as the end of that day; +1 as in the registered G2 series).
- Each state published <= end of m but documented later adds a vintage on its evidence date when it changes the
  value (revisions become new versions; nothing is back-dated).
A month in which no state is documented yet gets its first row on the first evidence date.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

COLUMNS = ["period", "value", "known_from", "source"]


def monthly(events: pd.DataFrame, last_month: pd.Period, first_month: pd.Period | None = None) -> pd.DataFrame:
    """Release-dated monthly rows (period, value, known_from, source) from `events`
    (published, value, evidence, source), for months first_month (default: month of the first event) to
    last_month (pass only complete months)."""
    if events.empty:
        return pd.DataFrame(columns=COLUMNS)
    ev = events.dropna(subset=["value"]).copy()
    ev["published"] = pd.to_datetime(ev["published"]).dt.normalize()
    ev["evidence"] = pd.to_datetime(ev["evidence"]).dt.normalize()
    ev["evidence"] = ev[["evidence", "published"]].max(axis=1)  # never known before its own date
    ev = ev.sort_values(["published", "evidence"]).reset_index(drop=True)
    start = first_month or ev["published"].min().to_period("M")
    rows = []
    for m in pd.period_range(start, last_month, freq="M") if start <= last_month else []:
        end = m.end_time.normalize()
        cand = ev[ev["published"] <= end]
        if cand.empty:
            continue
        base = end + pd.Timedelta(days=1)
        days = sorted({base} | set(cand.loc[cand["evidence"] > end, "evidence"]))
        prev = None
        for day in days:
            cutoff = end if day == base else day
            known = cand[cand["evidence"] <= cutoff]
            if known.empty:
                continue
            last = known.iloc[-1]  # latest published (ties: latest evidence)
            v = float(last["value"])
            if prev is None or not np.isclose(v, prev, rtol=0, atol=1e-9):
                rows.append((str(m), v, day, last["source"]))
                prev = v
    return pd.DataFrame(rows, columns=COLUMNS)


def last_complete_month(today=None) -> pd.Period:
    return pd.Period(pd.Timestamp(today) if today is not None else pd.Timestamp.today(), freq="M") - 1
