"""SEC EDGAR XBRL instances: remaining performance obligations (RPO), a point-in-time balance, with vintages.

RPO (`us-gaap:RevenueRemainingPerformanceObligation`, ASC 606) is contracted revenue not yet recognised, as of
a balance date. It is a stock, not a flow: no year-to-date differencing, and the period of a value is the
calendar quarter of its balance date (an XBRL *instant* context). Filings are read as in
ai_tracker.sources.sec_segment (filing list from data.sec.gov/submissions, the instance document from the
filing's index.json, raw copies cached), because the timing split is dimensional (companyfacts has no
dimensions) and typed: ASC 606 timing facts carry the typed dimension
`RevenueRemainingPerformanceObligationExpectedTimingOfSatisfactionStartDateAxis` (a date), which
sec_segment.parse_instance does not read.

Per filing and balance date:
- total = the RPO amount with no dimension, or, when a company tags its total with only the start-date axis
  (Amazon from 2020Q3: one bucket, the weighted average remaining life in Period1), that single fact.
- near share = the percentage expected to be recognised in the first bucket: the timing bucket with the
  earliest start date (start-date axis only), whose `...ExpectedTimingOfSatisfactionPeriod1` gives its length.
  The length must equal the company's declared horizon (12 or 24 months), otherwise HorizonError: a changed
  horizon is a definition break and gets new keys. Undimensioned percentage facts (Oracle FY2019-FY2021,
  Microsoft's own 12-month tag FY2018) count when the company declares their horizon.
- near amount = total * near share (same filing), later = total - near amount.

Vintages (leakage-critical): known_from = the filing date. For every filing date d the latest value per
balance date among facts filed <= d is taken, and a row is written when a quarter's value is new or changed
by more than sec.TOL. A restated balance is a new vintage. Definition breaks (a restatement of an
earlier-filed balance by more than sec_segment.BREAK_REL) are found with sec_segment.definition_breaks and
split into separate series, as for segment revenue.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from xml.etree import ElementTree

import pandas as pd

from ai_tracker.sources import sec, sec_segment
from ai_tracker.sources.sec_segment import XBRLDI, XBRLI, Filing, _local

RPO = "RevenueRemainingPerformanceObligation"
PCT = "RevenueRemainingPerformanceObligationPercentage"
PERIOD1 = "RevenueRemainingPerformanceObligationExpectedTimingOfSatisfactionPeriod1"
START_AXIS = "RevenueRemainingPerformanceObligationExpectedTimingOfSatisfactionStartDateAxis"
# Microsoft's own tag in FY2018 10-Qs (before it used the us-gaap timing dimension): 12 months by name.
MSFT_PCT_12M = "RevenueRemainingPerformanceObligationPercentageOfRevenueExpectedToBeRecognizedOverNext12Months"
CONCEPTS = frozenset({RPO, PCT, PERIOD1, MSFT_PCT_12M})
NEAR_MAX_DAYS = 92  # the first bucket starts at most a quarter after the balance date (tagging slips allowed)


class HorizonError(ValueError):
    """A filing's first timing bucket has another length than the declared horizon: review, then new keys."""


@dataclass(frozen=True)
class InstantFact:
    """One fact in an instant context: concept local name, balance date, dimensions, raw text, unit."""

    concept: str
    instant: pd.Timestamp
    dims: frozenset  # {(axis, member)}; a typed member is its text, e.g. "2026-10-01"
    text: str
    unit: str

    @property
    def value(self) -> float:
        return float(self.text)


# ------------------------------------------------------------------ parsing


def parse_instants(raw: bytes, concepts: frozenset[str] = CONCEPTS) -> list[InstantFact]:
    """Facts of `concepts` (local names, any namespace) in instant contexts, explicit and typed dimensions."""
    root = ElementTree.fromstring(raw)
    contexts = {}
    for c in root.iter(XBRLI + "context"):
        inst = c.find(f"{XBRLI}period/{XBRLI}instant")
        if inst is None or not (inst.text or "").strip():
            continue
        dims = {(_local(m.get("dimension")), _local(m.text or "")) for m in c.iter(XBRLDI + "explicitMember")}
        dims |= {(_local(m.get("dimension")), "".join(m.itertext()).strip()) for m in c.iter(XBRLDI + "typedMember")}
        contexts[c.get("id")] = (pd.Timestamp(inst.text.strip()), frozenset(dims))
    units = {}
    for u in root.iter(XBRLI + "unit"):
        m = u.find(f"{XBRLI}measure")
        units[u.get("id")] = _local(m.text) if m is not None and m.text else ""
    out = []
    for el in root:
        if not isinstance(el.tag, str) or el.get("contextRef") not in contexts:
            continue
        name = el.tag.rsplit("}", 1)[-1]
        if name not in concepts or el.get(f"{{http://www.w3.org/2001/XMLSchema-instance}}nil") == "true":
            continue
        instant, dims = contexts[el.get("contextRef")]
        out.append(InstantFact(name, instant, dims, (el.text or "").strip(), units.get(el.get("unitRef"), "")))
    return out


def months(duration: str) -> int | None:
    """Whole months of an ISO 8601 duration (P12M, P1Y, P2Y -> 24); None with days, or not a duration."""
    m = re.fullmatch(r"P(?:(\d+)Y)?(?:(\d+)M)?", duration.strip())
    if not m or not any(m.groups()):
        return None
    return int(m.group(1) or 0) * 12 + int(m.group(2) or 0)


# ------------------------------------------------------------------ per filing


def totals(facts: list[InstantFact]) -> dict[pd.Timestamp, float]:
    """Total RPO (USD) per balance date: the undimensioned fact, else a single start-date-only fact."""
    out: dict[pd.Timestamp, float] = {}
    single: dict[pd.Timestamp, list[float]] = {}
    for f in facts:
        if f.concept != RPO or f.unit != "USD":
            continue
        if not f.dims:
            out[f.instant] = f.value
        elif {a for a, _ in f.dims} == {START_AXIS} and len(f.dims) == 1:
            single.setdefault(f.instant, []).append(f.value)
    for instant, vals in single.items():
        if instant not in out and len(set(vals)) == 1:  # several buckets of amounts are not a total
            out[instant] = vals[0]
    return out


def near_shares(facts: list[InstantFact], horizon: int, undimensioned: bool) -> dict[pd.Timestamp, float]:
    """Share (0-1] of RPO in the first timing bucket per balance date; the bucket must last `horizon` months.

    `undimensioned`: the company's undimensioned us-gaap percentage (no timing axis) is its `horizon` share
    (declared per company after reading the filing text). Microsoft's own 12-month tag counts for horizon 12.
    """
    pct: dict[pd.Timestamp, dict[str, float]] = {}
    length: dict[pd.Timestamp, dict[str, str]] = {}
    flat: dict[pd.Timestamp, float] = {}
    for f in facts:
        axes = {a for a, _ in f.dims}
        if f.dims and (axes != {START_AXIS} or len(f.dims) != 1):
            continue  # another axis (a customer, a segment): a part, not the company total
        start = next(iter(f.dims))[1] if f.dims else None
        if f.concept == PCT and start:
            pct.setdefault(f.instant, {})[start] = f.value
        elif f.concept == PERIOD1 and start:
            length.setdefault(f.instant, {})[start] = f.text
        elif f.concept == PCT and not start and undimensioned:
            flat[f.instant] = f.value
        elif f.concept == MSFT_PCT_12M and not start and horizon == 12:
            flat[f.instant] = f.value
    out = dict(flat)
    for instant, buckets in pct.items():
        first = min(buckets, key=pd.Timestamp)
        if pd.Timestamp(first) > instant + pd.Timedelta(days=NEAR_MAX_DAYS):
            continue  # no first bucket tagged (only later ones)
        got = months(length.get(instant, {}).get(first, ""))
        if got != horizon:
            raise HorizonError(f"balance {instant.date()}: first bucket (start {first}) lasts "
                               f"{length.get(instant, {}).get(first)!r}, declared {horizon} months")
        out[instant] = buckets[first]
    for instant, v in out.items():
        if not 0 < v <= 1:
            raise ValueError(f"balance {instant.date()}: share {v} outside (0, 1]")
    return out


def filing_facts(f: Filing, facts: list[InstantFact], horizon: int | None,
                 undimensioned: bool = False) -> dict[str, list[sec.Fact]]:
    """sec.Facts (start = end = balance date) of one filing: total, and with a horizon near and later amounts."""
    filed = pd.Timestamp(f.filed)

    def fact(instant: pd.Timestamp, val: float) -> sec.Fact:
        return sec.Fact(instant, instant, val, filed, f.form, f.accession)

    tot = totals(facts)
    out = {"total": [fact(i, v) for i, v in sorted(tot.items())], "near": [], "later": []}
    if horizon is not None:
        try:
            shares = near_shares(facts, horizon, undimensioned)
        except (HorizonError, ValueError) as e:
            raise type(e)(f"{f.accession} ({f.form} filed {f.filed}): {e}") from None
        for instant, share in sorted(shares.items()):
            if instant in tot:
                near = tot[instant] * share
                out["near"].append(fact(instant, near))
                out["later"].append(fact(instant, tot[instant] - near))
    return out


@lru_cache(maxsize=None)
def company_instants(cik: int, since: str) -> tuple[tuple[Filing, tuple[InstantFact, ...]], ...]:
    """(filing, RPO instant facts) for every 10-Q/10-K since `since` (instances cached as in sec_segment)."""
    out = []
    for f in sec_segment.filings(cik, since):
        raw = sec_segment.instance(f)
        if raw is not None:
            out.append((f, tuple(parse_instants(raw))))
    return tuple(out)


# ------------------------------------------------------------------ vintages


def balance_quarter(instant: pd.Timestamp) -> pd.Period:
    """Calendar quarter of a balance date (Oracle's 30 Nov balance is Q4, filed before 31 Dec)."""
    return instant.to_period("Q-DEC")


def stock_vintages(facts: list[sec.Fact], scale: float = 1e-6) -> pd.DataFrame:
    """Release-dated quarterly rows of a balance: period, value (USD * scale), known_from, balance_date.

    For every filing date d, each balance date takes its latest fact filed <= d (sec.Fact.rank). If two
    balance dates fall in one calendar quarter, the later one wins. A row is written when a quarter's value is
    new or changed by more than sec.TOL (smaller changes are rounding).
    """
    by_key: dict[pd.Timestamp, list[sec.Fact]] = {}
    for f in facts:
        by_key.setdefault(f.end, []).append(f)
    for v in by_key.values():
        v.sort(key=lambda f: f.rank)
    last: dict[str, float] = {}
    rows = []
    for d in sorted({f.filed for f in facts}):
        by_period: dict[str, tuple[pd.Timestamp, float]] = {}
        for instant, versions in by_key.items():
            known = [f for f in versions if f.filed <= d]
            if not known:
                continue
            p = str(balance_quarter(instant))
            if p not in by_period or instant > by_period[p][0]:
                by_period[p] = (instant, known[-1].val)
        for p, (instant, val) in sorted(by_period.items()):
            if p not in last or abs(last[p] - val) > sec.TOL:
                last[p] = val
                rows.append((p, val * scale, d, instant))
    df = pd.DataFrame(rows, columns=["period", "value", "known_from", "balance_date"])
    return df.sort_values(["known_from", "period"], ignore_index=True)
