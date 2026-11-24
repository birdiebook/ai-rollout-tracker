"""SEC EDGAR XBRL: non-dimensional facts of company-specific concepts, and lines that are sums of two concepts.

companyfacts carries only the standard taxonomies (us-gaap, dei, srt). A line a company tags with its own concept is
not there: Microsoft's cash-flow line "Depreciation, amortization, and other" is msft:DepreciationAmortizationAndOther
in every 10-Q/10-K, and Alphabet's balance sheet in the 10-Q for 2020Q1 used goog:Property...RightofUseAsset... .
Such facts are read from each filing's own XBRL instance (filing list and instance download as in sec_segment, with
the same raw cache), keeping only contexts without dimensions (the consolidated figure).

Duration facts become ai_tracker.sources.sec.Fact and instant facts ai_tracker.sources.sec_instant.Instant, with
filed = the filing date of the document, so the quarter, calendar and vintage logic of sec.py and sec_instant.py
applies unchanged. As in sec.facts, 3-month facts in 10-Ks (the unaudited quarterly note) are ignored.

Sums. Some lines are reported as two rows (Oracle adds back "Depreciation" and "Amortization of intangible assets"
separately), and a gross balance is net + accumulated depreciation. summed() and summed_instants() add facts of the
same period from the same filing, so both parts always come from one document (one basis); a period that only one
part carries in a filing gives no sum for that filing.
"""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from ai_tracker.sources import sec, sec_instant, sec_segment


@lru_cache(maxsize=None)
def _filings(cik: int, since: str, until: str) -> tuple[tuple[sec_segment.Filing, bytes], ...]:
    """(filing, instance bytes) for 10-Q/10-K filings filed in [since, until], oldest first."""
    out = []
    for f in sec_segment.filings(cik, since):
        if f.filed > until:
            continue
        raw = sec_segment.instance(f)
        if raw is not None:
            out.append((f, raw))
    return tuple(out)


def plain_facts(dim_facts: list[sec_segment.DimFact], f: sec_segment.Filing, concepts: list[str],
                unit: str = "USD") -> list[sec.Fact]:
    """sec.Facts without dimensions for a concept priority list, from one filing's parsed instance.

    Within the filing, the first concept in `concepts` that has a period wins.
    """
    by_period: dict[tuple, tuple[int, float]] = {}
    for d in dim_facts:
        if d.dims or d.unit != unit or d.concept not in concepts:
            continue
        if f.form.startswith("10-K") and sec._is_quarter(d.start, d.end):
            continue  # 10-K quarterly notes, as in sec.facts
        rank = concepts.index(d.concept)
        key = (d.start, d.end)
        if key not in by_period or rank < by_period[key][0]:
            by_period[key] = (rank, d.value)
    filed = pd.Timestamp(f.filed)
    return [sec.Fact(s, e, v, filed, f.form, f.accession) for (s, e), (_, v) in sorted(by_period.items())]


@lru_cache(maxsize=None)
def duration_facts(cik: int, concepts: tuple[str, ...], since: str = "2009-01-01",
                   until: str = "9999-12-31") -> tuple[sec.Fact, ...]:
    """Non-dimensional duration facts of `concepts` (local names, any namespace) over a company's filings."""
    out: list[sec.Fact] = []
    for f, raw in _filings(cik, since, until):
        out += plain_facts(sec_segment.parse_instance(raw, set(concepts)), f, list(concepts))
    return tuple(out)


@lru_cache(maxsize=None)
def instant_facts(cik: int, concept: str, since: str = "2009-01-01",
                  until: str = "9999-12-31") -> tuple[sec_instant.Instant, ...]:
    """Non-dimensional instant facts of one concept (local name, any namespace) over a company's filings."""
    return tuple(sec_instant.instance_instants(list(_filings(cik, since, until)), concept))


def summed(parts: list[list[sec.Fact]]) -> list[sec.Fact]:
    """Facts of the same (filing, start, end) added across parts; only periods every part has in that filing."""
    keyed = [{(f.accn, f.start, f.end): f for f in fs} for fs in parts]
    common = set.intersection(*(set(k) for k in keyed)) if keyed else set()
    out = []
    for k in sorted(common, key=lambda k: (keyed[0][k].filed, k)):
        first = keyed[0][k]
        out.append(sec.Fact(first.start, first.end, sum(p[k].val for p in keyed), first.filed, first.form, first.accn))
    return out


def summed_instants(parts: list[list[sec_instant.Instant]]) -> list[sec_instant.Instant]:
    """Instants of the same (filing, date) added across parts; only dates every part has in that filing."""
    keyed = [{(f.accn, f.end): f for f in fs} for fs in parts]
    common = set.intersection(*(set(k) for k in keyed)) if keyed else set()
    out = []
    for k in sorted(common, key=lambda k: (keyed[0][k].filed, k)):
        first = keyed[0][k]
        out.append(sec_instant.Instant(first.end, sum(p[k].val for p in keyed), first.filed, first.form, first.accn))
    return out


def starting_from(facts: list[sec.Fact], first_start: str) -> list[sec.Fact]:
    """Facts whose period starts on or after `first_start`: one definition regime of a line that changed content
    without restating earlier periods (Amazon's D&A line from 2019, ASC 842)."""
    t = pd.Timestamp(first_start)
    return [f for f in facts if f.start >= t]
