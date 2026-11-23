"""SEC EDGAR XBRL companyfacts: quarterly values with vintages (known_from = filing date).

companyfacts (data.sec.gov/api/xbrl/companyfacts/CIK##########.json) holds every non-dimensional XBRL
fact a company has filed: start, end, val, accn, fy, fp, form, filed. The same period is reported again
in later filings (comparatives, restatements), each with its own `filed` date.

Quarterly values. Cash-flow facts in 10-Qs are fiscal-year-to-date: 3, 6, 9 months, and the 10-K has
the full year. Income-statement facts (and Amazon's cash flows) also come as 3-month facts. One rule
covers both: group facts by `start`; within a group, consecutive end dates ~one quarter apart give a
quarter value C(e_k) - C(e_{k-1}) (the first end, if ~one quarter after start, is the quarter itself).
So Q4 = FY (10-K) - 9M YTD, and a 3-month fact is used as is. Facts are selected on start/end, never on
fy/fp (those describe the filing, not the fact). 3-month facts in 10-Ks (the unaudited quarterly note)
are ignored: that is where mis-dated tags were found, and Q4 follows from FY - 9M anyway.

Vintages (leakage-critical). For each distinct `filed` date d, quarter values are computed using only
facts with filed <= d, and a row (quarter, value, known_from=d) is emitted when a quarter's value is
new or changed. A quarter never gets a value dated before the last filing needed to compute it.
Amendments (10-Q/A, 10-K/A) and comparatives in later filings are ordinary later versions. Restated
inputs are only combined on a consistent basis (see _difference): a restatement that the filings do
not break down by quarter is not pushed into one quarter.

Calendar mapping. A fiscal quarter maps to the calendar quarter containing its midpoint. For companies
whose quarters end on calendar quarter ends (MSFT, GOOGL, AMZN, META) this is the calendar quarter of the
end date. NVDA's quarters end in late Jan/Apr/Jul/Oct: Aug-Oct maps to Q3, i.e. NVDA is offset by
about one month (see docs/kallor/sec.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from ai_tracker import http

BASE = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
FORMS = ("10-Q", "10-K")  # incl. 10-Q/A, 10-K/A, 10-KT; other forms (8-K, S-1, ...) are ignored
QUARTER_DAYS = (75, 105)  # a 13- or 14-week quarter, or a calendar quarter
TOL = 0.5e6  # USD; filings round to millions, smaller changes (thousands -> millions) are not revisions


@dataclass(frozen=True)
class Fact:
    start: pd.Timestamp
    end: pd.Timestamp
    val: float
    filed: pd.Timestamp
    form: str
    accn: str

    @property
    def rank(self) -> tuple:  # which of several facts for the same (start, end) is the latest
        return (self.filed, self.form.endswith("/A"), self.accn)


@dataclass(frozen=True)
class Quarter:
    value: float
    start: pd.Timestamp
    end: pd.Timestamp
    filed: pd.Timestamp  # latest filing among the inputs


@lru_cache(maxsize=None)
def companyfacts(cik: int) -> dict:
    """The companyfacts JSON for one CIK (one request per CIK and process; raw copy saved by http.get)."""
    return http.get(BASE.format(cik=cik), source="sec").json()


def facts(cf: dict, tag: str, taxonomy: str = "us-gaap", unit: str = "USD") -> list[Fact]:
    """Duration facts for one concept from 10-Q/10-K-family filings (not 10-K quarterly notes)."""
    concept = cf.get("facts", {}).get(taxonomy, {}).get(tag)
    if not concept:
        return []
    out = []
    for f in concept.get("units", {}).get(unit, []):
        if "start" not in f or not str(f.get("form", "")).startswith(FORMS):
            continue
        if f["form"].startswith("10-K") and _is_quarter(pd.Timestamp(f["start"]), pd.Timestamp(f["end"])):
            continue  # 10-K quarterly notes: unaudited, and where mis-dated tags occur (Amazon FY2012)
        out.append(Fact(pd.Timestamp(f["start"]), pd.Timestamp(f["end"]), float(f["val"]),
                        pd.Timestamp(f["filed"]), f["form"], f.get("accn", "")))
    return out


def _is_quarter(start: pd.Timestamp, end: pd.Timestamp) -> bool:
    days = (end - start).days + 1
    return QUARTER_DAYS[0] <= days <= QUARTER_DAYS[1]


def _difference(cur: list[Fact], base: list[Fact]) -> tuple[float, pd.Timestamp]:
    """C(e_k) - C(e_{k-1}) from version lists (sorted by rank): (value, latest input filed).

    The latest version of the closing fact is used, with the base version that was on file when it was
    filed (the earliest base if none was). If the closing fact was restated but the base was not
    restated since the closing fact's previous version, the restatement cannot be split by quarter
    (Meta restated full-year 2015 cash flows, never the 9M): the previous version is used, so a
    whole-year restatement is not dumped into one quarter. A restatement that truly hits only the last
    quarter is then missed; that is the conservative side.
    """
    restated = [b.filed for k, b in enumerate(base) if k and abs(b.val - base[k - 1].val) > TOL]
    c = cur[0]
    for this in cur[1:]:
        if abs(this.val - c.val) <= TOL or any(c.filed < d <= this.filed for d in restated):
            c = this
    on_file = [b for b in base if b.filed <= c.filed]
    b = on_file[-1] if on_file else base[0]
    return c.val - b.val, max(c.filed, b.filed)


def _quarters(sources: list[list[Fact]], cutoff: pd.Timestamp | None) -> dict[pd.Timestamp, Quarter]:
    versions: dict[tuple, list[Fact]] = {}
    for fs in sources:
        own: dict[tuple, list[Fact]] = {}
        for f in fs:
            if cutoff is None or f.filed <= cutoff:
                own.setdefault((f.start, f.end), []).append(f)
        for k, v in own.items():
            versions.setdefault(k, v)
    for v in versions.values():
        v.sort(key=lambda f: f.rank)
    groups: dict[pd.Timestamp, list[pd.Timestamp]] = {}
    for start, end in versions:
        groups.setdefault(start, []).append(end)

    best: dict[pd.Timestamp, tuple] = {}  # end -> (direct, inputs filed, Quarter)
    for start, ends in groups.items():
        ends.sort()
        prev = None
        for end in ends:
            q_start = start if prev is None else prev + pd.Timedelta(days=1)
            if _is_quarter(q_start, end):
                if prev is None:
                    c = versions[(start, end)][-1]
                    value, filed = c.val, c.filed
                else:
                    value, filed = _difference(versions[(start, end)], versions[(start, prev)])
                cand = (prev is None, filed, Quarter(value, q_start, end, filed))
                if end not in best or cand[:2] > best[end][:2]:
                    best[end] = cand
            prev = end
    return {e: c[2] for e, c in best.items()}


def quarters_at(sources: list[list[Fact]], cutoff: pd.Timestamp | None = None) -> dict[pd.Timestamp, Quarter]:
    """Fiscal-quarter values known at `cutoff` (facts filed later are ignored), keyed by quarter end.

    Within a `start` group of facts, consecutive end dates about one quarter apart give quarter k =
    C(e_k) - C(e_{k-1}) (see _difference); the first end, if one quarter after start, is the quarter
    itself. A direct 3-month fact wins over a difference; among differences the latest inputs win.

    `sources` is a priority list of fact lists, one per tag. Each quarter takes the first tag that can
    compute it on its own. Only quarters no single tag can compute are taken from all tags together
    (spliced per fact period), e.g. Nvidia FY2019 Q4 = full year under the new revenue tag minus 9M
    under the old one. Per-tag first keeps a restated full year under a new tag from being differenced
    against an old-basis 9M under the old tag (Microsoft FY2016 revenue, ASC 606).
    """
    out: dict[pd.Timestamp, Quarter] = {}
    for fs in sources:
        for end, q in _quarters([fs], cutoff).items():
            out.setdefault(end, q)
    if len(sources) > 1:
        for end, q in _quarters(sources, cutoff).items():
            out.setdefault(end, q)
    return out


def calendar_quarter(start: pd.Timestamp, end: pd.Timestamp) -> pd.Period:
    """Calendar quarter containing the fiscal quarter's midpoint."""
    return (start + (end - start) / 2).to_period("Q-DEC")


def vintages(sources: list[list[Fact]], scale: float = 1e-6) -> pd.DataFrame:
    """Release-dated quarterly rows from one or more tags (priority list, see quarters_at).

    For every filing date d, quarters are computed from facts filed <= d and a row is emitted when a
    calendar quarter's value is new or changed by more than TOL (smaller changes are rounding). If two
    fiscal quarter ends fall in one calendar quarter (an end date tagged one day off), the one with the
    latest inputs wins. Returns columns period (calendar quarter, str), value (USD * scale),
    known_from and fiscal_end, sorted by known_from.
    """
    cutoffs = sorted({f.filed for fs in sources for f in fs})
    last: dict[str, float] = {}
    rows = []
    for d in cutoffs:
        by_period: dict[str, Quarter] = {}
        for q in quarters_at(sources, d).values():
            p = str(calendar_quarter(q.start, q.end))
            if p not in by_period or (q.filed, q.end) > (by_period[p].filed, by_period[p].end):
                by_period[p] = q
        for p, q in sorted(by_period.items()):
            if p not in last or abs(last[p] - q.value) > TOL:
                last[p] = q.value
                rows.append((p, q.value * scale, d, q.end))
    df = pd.DataFrame(rows, columns=["period", "value", "known_from", "fiscal_end"])
    return df.sort_values(["known_from", "period"], ignore_index=True)


def contiguous_tail(df: pd.DataFrame) -> pd.DataFrame:
    """Drop periods before the last gap (in the latest vintage), so a series has no holes.

    Early XBRL years and tag changes can leave quarters that cannot be computed (e.g. a year with only
    the full-year fact). The series then starts after the last missing quarter.
    """
    if df.empty:
        return df
    periods = pd.PeriodIndex(sorted(set(df["period"])), freq="Q-DEC")
    ords = periods.asi8
    breaks = [i for i in range(1, len(ords)) if ords[i] != ords[i - 1] + 1]
    if not breaks:
        return df
    first = periods[breaks[-1]]
    return df[pd.PeriodIndex(df["period"], freq="Q-DEC") >= first].reset_index(drop=True)


def aggregate(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Sum of several companies per calendar quarter, as vintages.

    A quarter's aggregate exists only once every company has a value for it; each version is dated by
    the latest of the filings it uses (a new row whenever any component's value changes).
    """
    rows = []
    names = list(frames)
    periods = set.intersection(*(set(f["period"]) for f in frames.values())) if frames else set()
    for p in sorted(periods):
        parts = {n: frames[n][frames[n]["period"] == p].sort_values("known_from") for n in names}
        dates = sorted({d for part in parts.values() for d in part["known_from"]})
        prev = None
        for d in dates:
            vals = []
            for part in parts.values():
                known = part[part["known_from"] <= d]
                if known.empty:
                    break
                vals.append(known["value"].iloc[-1])
            else:
                total = float(sum(vals))
                if prev is None or abs(total - prev) > TOL * 1e-6:
                    rows.append((p, total, d))
                    prev = total
    return pd.DataFrame(rows, columns=["period", "value", "known_from"]).sort_values(
        ["known_from", "period"], ignore_index=True)
