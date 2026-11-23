"""SEC EDGAR XBRL companyfacts: what the financing series need beyond ai_tracker.sources.sec.

sec.py handles duration facts (flows: YTD differencing, Q4 = FY - 9M, vintages per filing date). This module
adds balances (instant facts), sums of tags, two gap fillers for flows, and the instance-document check that
guards the zero fill. Series: ai_tracker/series/sec_finansiering.py, docs: docs/kallor/finansiering.md.

Balances. A balance is an instant fact (no `start`) dated at its `end`. Only balances at a fiscal period end
are kept: the report dates of the company's own 10-Q/10-K filings (report_dates). That drops instants at other
dates (subsequent events, acquisition dates). A balance at fiscal quarter end e maps to the calendar quarter
containing the midpoint of the fiscal quarter ending at e, taken as e - 45 days, as sec.calendar_quarter does
for flows: for calendar-quarter companies the quarter of e, for Oracle (quarters ending Aug/Nov/Feb/May) the
quarter that holds two of its three months.

Balance vintages (leakage-critical, as in sec.vintages). For every filing date d, each quarter-end balance is
the latest version filed <= d, and a row is emitted when it is new or changed by more than sec.TOL. Restated
comparatives are later versions with the later filing date. A tag priority list works per quarter end.

Formulas. Some measures are sums of tags (cash + marketable securities, current + noncurrent debt) or fall back
between such sums. sum_frames adds component vintages (a quarter exists once every component has a value, each
version dated by the latest component); first_available takes each quarter from the first formula that has it,
with that formula's own vintages only.

Gap fillers for flows (both dated no earlier than the filings they use):
- derived_first_quarters: when a company discloses a flow only in some quarters (Meta's interest expense), the
  first quarter of a fiscal year is missing from YTD differencing although a later 10-Q carries both the 6-month
  YTD and the second quarter's 3-month fact. Q1 = YTD(6M) - Q2(3M) from the same filing (same accession).
- zero_facts: a cash-flow line with nothing to report is often left out of the statement (Microsoft has issued
  no long-term debt since FY2017 and dropped the line in FY2026 10-Qs; Meta has never repaid long-term debt).
  For a 10-Q/10-K that has the financing total (NetCashProvidedByUsedInFinancingActivities) but none of the
  measure's tags, the current period's value is 0 - but only after the filing's own XBRL instance (all
  namespaces, so company-specific tags too) is checked and holds no concept matching the measure's pattern.
  Comparative columns are not filled (they belong to their own filings). Filings before ZERO_SINCE are not
  filled.
"""

from __future__ import annotations

import re
from collections import Counter

import pandas as pd

from ai_tracker.sources import sec, sec_segment

FORMS = sec.FORMS
REPORT_SHARE = 0.25
MIDPOINT_DAYS = 45  # e - 45 days is the midpoint of a fiscal quarter ending at e (13-14 weeks)


def instant_facts(cf: dict, tag: str, taxonomy: str = "us-gaap", unit: str = "USD") -> list[sec.Fact]:
    """Instant facts for one concept from 10-Q/10-K-family filings, as Facts with start == end."""
    concept = cf.get("facts", {}).get(taxonomy, {}).get(tag)
    if not concept:
        return []
    out = []
    for f in concept.get("units", {}).get(unit, []):
        if "start" in f or not str(f.get("form", "")).startswith(FORMS):
            continue
        end = pd.Timestamp(f["end"])
        out.append(sec.Fact(end, end, float(f["val"]), pd.Timestamp(f["filed"]), f["form"], f.get("accn", "")))
    return out


def report_dates(cf: dict) -> set[pd.Timestamp]:
    """Fiscal period ends: per 10-Q/10-K accession, the latest `end` that is common in that filing.

    Common = at least REPORT_SHARE of the count of the filing's most frequent end (instant and duration facts
    together). The balance-sheet date is the most frequent end of a 10-Q or 10-K; a few instants dated after
    it (subsequent events) do not reach the share.
    """
    ends: dict[str, Counter] = {}
    for concepts in cf.get("facts", {}).values():
        for concept in concepts.values():
            for facts in concept.get("units", {}).values():
                for f in facts:
                    if str(f.get("form", "")).startswith(FORMS) and f.get("accn"):
                        ends.setdefault(f["accn"], Counter())[f["end"]] += 1
    out = set()
    for c in ends.values():
        top = max(c.values())
        out.add(pd.Timestamp(max(e for e, n in c.items() if n >= REPORT_SHARE * top)))
    return out


def calendar_quarter(end: pd.Timestamp) -> pd.Period:
    return (end - pd.Timedelta(days=MIDPOINT_DAYS)).to_period("Q-DEC")


def balances_at(sources: list[list[sec.Fact]], ends: set[pd.Timestamp],
                cutoff: pd.Timestamp | None = None) -> dict[pd.Timestamp, sec.Fact]:
    """Latest version (filed <= cutoff) of each quarter-end balance; the first tag with a value per end wins."""
    out: dict[pd.Timestamp, sec.Fact] = {}
    for fs in sources:
        own: dict[pd.Timestamp, sec.Fact] = {}
        for f in fs:
            if f.end in ends and (cutoff is None or f.filed <= cutoff):
                if f.end not in own or f.rank > own[f.end].rank:
                    own[f.end] = f
        for e, f in own.items():
            out.setdefault(e, f)
    return out


def stock_vintages(sources: list[list[sec.Fact]], ends: set[pd.Timestamp], scale: float = 1e-6) -> pd.DataFrame:
    """Release-dated quarterly balances: columns period, value (USD * scale), known_from, fiscal_end.

    If two fiscal period ends map to one calendar quarter (a 52/53-week year end), the later end wins.
    """
    cutoffs = sorted({f.filed for fs in sources for f in fs if f.end in ends})
    last: dict[str, float] = {}
    rows = []
    for d in cutoffs:
        by_period: dict[str, sec.Fact] = {}
        for e, f in balances_at(sources, ends, d).items():
            p = str(calendar_quarter(e))
            if p not in by_period or e > by_period[p].end:
                by_period[p] = f
        for p, f in sorted(by_period.items()):
            if p not in last or abs(last[p] - f.val) > sec.TOL:
                last[p] = f.val
                rows.append((p, f.val * scale, d, f.end))
    df = pd.DataFrame(rows, columns=["period", "value", "known_from", "fiscal_end"])
    return df.sort_values(["known_from", "period"], ignore_index=True)


def sum_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Sum of component vintages (period, value, known_from); a quarter needs every component."""
    if len(frames) == 1:
        return frames[0][["period", "value", "known_from"]].copy()
    return sec.aggregate({str(i): f for i, f in enumerate(frames)})


def first_available(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Each period from the first frame that has it (that frame's vintages only)."""
    taken: set[str] = set()
    parts = []
    for f in frames:
        f = f[["period", "value", "known_from"]]
        new = f[~f["period"].isin(taken)]
        taken |= set(new["period"])
        parts.append(new)
    if not parts:
        return pd.DataFrame(columns=["period", "value", "known_from"])
    return pd.concat(parts, ignore_index=True).sort_values(["known_from", "period"], ignore_index=True)


# ------------------------------------------------------------------ gap fillers for flows

FINANCING_TOTAL = ("NetCashProvidedByUsedInFinancingActivities",
                   "NetCashProvidedByUsedInFinancingActivitiesContinuingOperations")
ZERO_SINCE = pd.Timestamp("2016-01-01")


def derived_first_quarters(fs: list[sec.Fact]) -> list[sec.Fact]:
    """Q1 = 6-month YTD - Q2 3-month fact, both from the same filing, as Facts (start, Q1 end)."""
    by_accn: dict[str, list[sec.Fact]] = {}
    for f in fs:
        by_accn.setdefault(f.accn, []).append(f)
    out = []
    for group in by_accn.values():
        for ytd in group:
            if not 165 <= (ytd.end - ytd.start).days + 1 <= 195:
                continue
            for q2 in group:
                if q2.end == ytd.end and sec._is_quarter(q2.start, q2.end) and sec._is_quarter(ytd.start, q2.start
                                                                                               - pd.Timedelta(days=1)):
                    out.append(sec.Fact(ytd.start, q2.start - pd.Timedelta(days=1), ytd.val - q2.val, ytd.filed,
                                        ytd.form, ytd.accn))
    return out


def zero_candidates(cf: dict, tags: list[str], since: pd.Timestamp = ZERO_SINCE) -> dict[str, list[sec.Fact]]:
    """Accessions with the financing total but none of `tags`: accn -> zero Facts for the current period(s).

    The current periods are the financing-total facts ending at the filing's report date (3 months and YTD).
    """
    have = {f.accn for t in tags for f in sec.facts(cf, t)}
    total: dict[str, list[sec.Fact]] = {}
    for t in FINANCING_TOTAL:
        for f in sec.facts(cf, t):
            total.setdefault(f.accn, []).append(f)
    out = {}
    for accn, fs in total.items():
        if accn in have or min(f.filed for f in fs) < since:
            continue
        report = max(f.end for f in fs)
        cur = {(f.start, f.end): f for f in fs if f.end == report}
        out[accn] = [sec.Fact(s, e, 0.0, f.filed, f.form, accn) for (s, e), f in sorted(cur.items())]
    return out


def instance_concepts(raw: bytes) -> set[str]:
    """Local names of the elements that carry a contextRef in an XBRL instance (any namespace)."""
    text = raw.decode("utf-8", errors="replace")
    return set(re.findall(r"<[\w.\-]+:(\w+)\b[^>]*\bcontextRef=", text))


def filing_for(cik: int, accn: str, fact: sec.Fact) -> sec_segment.Filing:
    return sec_segment.Filing(cik, accn, str(fact.filed.date()), fact.form)


def zero_facts(cik: int, cf: dict, tags: list[str], pattern: str, exclude: str,
               since: pd.Timestamp = ZERO_SINCE) -> tuple[list[sec.Fact], list[str]]:
    """Zero Facts for filings without the line, each verified against the filing's instance document.

    Returns (zero facts, accessions refused because the instance has a matching concept, e.g. a
    company-specific tag, or has no instance). A refused filing leaves a gap; it is never filled.
    """
    zeros, refused = [], []
    rx, ex = re.compile(pattern), re.compile(exclude)
    for accn, fs in zero_candidates(cf, tags, since).items():
        raw = sec_segment.instance(filing_for(cik, accn, fs[0]))
        hits = [] if raw is None else [c for c in instance_concepts(raw) if rx.search(c) and not ex.search(c)]
        if raw is None or hits:
            refused.append(f"{accn}: {', '.join(sorted(hits)) or 'no XBRL instance'}")
        else:
            zeros += fs
    return zeros, refused
