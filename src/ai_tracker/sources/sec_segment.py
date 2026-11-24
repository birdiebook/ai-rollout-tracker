"""SEC EDGAR XBRL instances: dimensional (segment / product) revenue facts with vintages.

companyfacts carries no dimensions, so segment revenue (AWS, Google Cloud, Intelligent Cloud, Nvidia
Data Center) is read from each 10-Q/10-K's own XBRL instance document instead: the filing list from
data.sec.gov/submissions, the instance file from the filing's index.json in the EDGAR archive (the
`*_htm.xml` instance extracted from inline XBRL, or the plain `*.xml` instance before 2019).

A fact is kept when its context carries exactly one dimension, the requested (axis, member) pair, so
a member that is further broken down on another axis (e.g. segment x product) is not mixed in. Each
fact becomes an ai_tracker.sources.sec.Fact with filed = the filing date of the document it came
from, so the quarter and vintage logic of sec.py (3-month facts direct, YTD differencing, Q4 = FY -
9M, a version per filing date, consistent-basis restatements) applies unchanged. As in sec.facts,
3-month facts in 10-Ks (the unaudited quarterly note) are ignored.

Definition breaks. A re-segmentation keeps the member name but recasts history (Microsoft FY2025).
Spliced as revisions, it would rewrite the old definition's history with the new one at the recast
filing date and mix two definitions in one series. definition_breaks() finds filings that change
earlier-reported values of the same period by more than BREAK_REL; regimes() splits the facts at
those filings, and each regime is its own series. Small restatements below the threshold stay
ordinary vintages.

Filings never change, so instance documents are cached: the raw copies ai_tracker.http saves under
data/raw/sec_segment/<date>/ are reused on later runs.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from functools import lru_cache

from xml.etree import ElementTree

import pandas as pd
import requests

from ai_tracker import http
from ai_tracker.sources import sec

SOURCE = "sec_segment"
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SUBMISSIONS_FILE = "https://data.sec.gov/submissions/{name}"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{name}"
NEUTRAL_DIMS = {("ConsolidationItemsAxis", "OperatingSegmentsMember")}
BREAK_REL = 0.02  # a restatement of an earlier-reported period by more than 2% is a definition change

XBRLI = "{http://www.xbrl.org/2003/instance}"
XBRLDI = "{http://xbrl.org/2006/xbrldi}"


@dataclass(frozen=True)
class Filing:
    cik: int
    accession: str
    filed: str  # EDGAR filing date, YYYY-MM-DD
    form: str

    @property
    def folder(self) -> str:
        return ARCHIVE.format(cik=self.cik, acc=self.accession.replace("-", ""), name="")


@dataclass(frozen=True)
class DimFact:
    """One numeric duration fact from an instance: concept local name, period, dimensions, value."""

    concept: str
    start: pd.Timestamp
    end: pd.Timestamp
    dims: frozenset  # {(axis local name, member local name)}
    value: float
    unit: str


# ------------------------------------------------------------------ EDGAR access


def filings(cik: int, since: str = "2009-01-01") -> list[Filing]:
    """10-Q/10-K-family filings (amendments included) filed on or after `since`, oldest first."""
    sub = http.get(SUBMISSIONS.format(cik=cik), SOURCE).json()
    blocks = [sub["filings"]["recent"]]
    for f in sub["filings"].get("files", []):
        if f.get("filingTo", "9999") >= since:
            blocks.append(http.get(SUBMISSIONS_FILE.format(name=f["name"]), SOURCE).json())
    out = {}
    for b in blocks:
        for form, filed, acc in zip(b["form"], b["filingDate"], b["accessionNumber"]):
            if form.startswith(sec.FORMS) and filed >= since:
                out[acc] = Filing(cik, acc, filed, form)
    return sorted(out.values(), key=lambda f: (f.filed, f.accession))


def _cached_get(url: str) -> bytes:
    """Content of an immutable archive URL: a raw copy from an earlier run, else a (saved) GET."""
    name = http.raw_path(SOURCE, url).name
    hits = sorted((http.RAW_DIR / SOURCE).glob(f"*/{name}"))
    if hits:
        return hits[-1].read_bytes()
    for attempt in range(3):  # EDGAR's archive now and then answers 404 for a filing that loads on the next try
        try:
            return http.get(url, SOURCE).content
        except requests.HTTPError as e:
            if e.response is None or e.response.status_code != 404 or attempt == 2:
                raise
            time.sleep(2)
    raise RuntimeError("unreachable")


def instance_name(items: list[str]) -> str | None:
    """The XBRL instance among a filing folder's file names (None if the filing has no XBRL)."""
    xml = [n for n in items if n.lower().endswith(".xml") and n != "FilingSummary.xml"
           and not n.lower().endswith(("_cal.xml", "_def.xml", "_lab.xml", "_pre.xml"))
           and not (n[:1] == "R" and n[1:-4].isdigit())]
    extracted = [n for n in xml if n.lower().endswith("_htm.xml")]
    return (extracted or sorted(xml, key=len) or [None])[0]


def instance(f: Filing) -> bytes | None:
    index = json.loads(_cached_get(f.folder + "index.json"))
    name = instance_name([it["name"] for it in index["directory"]["item"]])
    return None if name is None else _cached_get(f.folder + name)


# ------------------------------------------------------------------ parsing


def _local(qname: str) -> str:
    return qname.split(":", 1)[-1].strip()


def parse_instance(raw: bytes, concepts: set[str] | None = None) -> list[DimFact]:
    """Numeric duration facts (any namespace) of an XBRL instance; `concepts` filters on local names."""
    root = ElementTree.fromstring(raw)
    contexts = {}
    for c in root.iter(XBRLI + "context"):
        start, end = c.find(f"{XBRLI}period/{XBRLI}startDate"), c.find(f"{XBRLI}period/{XBRLI}endDate")
        if start is None or end is None:
            continue  # instant
        dims = frozenset((_local(m.get("dimension")), _local(m.text or ""))
                         for m in c.iter(XBRLDI + "explicitMember"))
        contexts[c.get("id")] = (pd.Timestamp(start.text.strip()), pd.Timestamp(end.text.strip()), dims)
    units = {}
    for u in root.iter(XBRLI + "unit"):
        m = u.find(f"{XBRLI}measure")
        units[u.get("id")] = _local(m.text) if m is not None and m.text else ""
    out = []
    for el in root:
        if not isinstance(el.tag, str) or el.get("contextRef") not in contexts or el.get("unitRef") is None:
            continue
        name = el.tag.rsplit("}", 1)[-1]
        if concepts is not None and name not in concepts:
            continue
        try:
            val = float((el.text or "").strip())
        except ValueError:
            continue
        start, end, dims = contexts[el.get("contextRef")]
        out.append(DimFact(name, start, end, dims, val, units.get(el.get("unitRef"), "")))
    return out


def to_facts(dim_facts: list[DimFact], f: Filing, concepts: list[str], axis: str, member: str,
             unit: str = "USD") -> list[sec.Fact]:
    """sec.Facts for one (axis, member) and a concept priority list, from one filing's instance.

    A context counts when its dimensions are (axis, member), optionally with the consolidation-item
    marker for operating segments (ConsolidationItemsAxis = OperatingSegmentsMember, which older
    filings add to segment facts). Any other extra dimension (a product within the segment, a
    geography) excludes the fact. Within one filing, the first concept in `concepts` that has a
    period wins, and a context without the marker before one with it.
    """
    want = {(axis, member)}
    by_period: dict[tuple, tuple[tuple, float]] = {}
    for d in dim_facts:
        if d.unit != unit or d.concept not in concepts or set(d.dims) - NEUTRAL_DIMS != want:
            continue
        if f.form.startswith("10-K") and sec._is_quarter(d.start, d.end):
            continue  # 10-K quarterly notes, as in sec.facts
        rank = (concepts.index(d.concept), len(d.dims))
        key = (d.start, d.end)
        if key not in by_period or rank < by_period[key][0]:
            by_period[key] = (rank, d.value)
    filed = pd.Timestamp(f.filed)
    return [sec.Fact(s, e, v, filed, f.form, f.accession) for (s, e), (_, v) in sorted(by_period.items())]


# ------------------------------------------------------------------ definition breaks


def definition_breaks(facts: list[sec.Fact], rel: float = BREAK_REL) -> list[pd.Timestamp]:
    """Filing dates that restate a value of the current definition regime by more than `rel`.

    A filing that changes an earlier-filed value of the same (start, end) by more than `rel` starts
    a new regime. A recast is rolled out over several filings (each 10-Q recasts its own prior-year
    comparatives, the 10-K the prior years), so after a break only values filed at or after it are
    compared: the later filings of the same recast restate old-regime values and are not new breaks.
    Limitation (review R14, A-2b): a second reclassification soon after a break is flagged only where it
    changes a period already re-reported since the break; a period last filed before the break is not
    compared again.
    """
    seen: dict[tuple, float] = {}
    breaks = []
    for filed in sorted({f.filed for f in facts}):
        batch = [f for f in facts if f.filed == filed]
        if any((f.start, f.end) in seen and abs(f.val - seen[(f.start, f.end)]) > rel * max(abs(seen[(f.start, f.end)]), 1.0)
               for f in batch):
            breaks.append(filed)
            seen = {}
        for f in batch:
            seen[(f.start, f.end)] = f.val
    return breaks


def regimes(facts: list[sec.Fact], breaks: list[pd.Timestamp]) -> list[list[sec.Fact]]:
    """Facts split at the break dates: regime i holds the facts filed in [break_{i-1}, break_i)."""
    edges = [pd.Timestamp.min, *sorted(breaks), pd.Timestamp.max]
    return [[f for f in facts if lo <= f.filed < hi] for lo, hi in zip(edges[:-1], edges[1:])]


# ------------------------------------------------------------------ per company


@lru_cache(maxsize=None)
def company_facts(cik: int, since: str, concepts: tuple[str, ...]) -> tuple[tuple[Filing, tuple[DimFact, ...]], ...]:
    """(filing, dimensional facts of `concepts`) for every 10-Q/10-K since `since` (cached per process)."""
    out = []
    for f in filings(cik, since):
        raw = instance(f)
        if raw is None:
            continue
        out.append((f, tuple(d for d in parse_instance(raw, set(concepts)) if d.dims)))
    return tuple(out)


def member_facts(ciks: tuple[int, ...], since: str, concepts: tuple[str, ...],
                 members: tuple[tuple[str, str], ...]) -> list[sec.Fact]:
    """sec.Facts for one line item across filings.

    `members` are alternative (axis, member) names of the same line (a renamed member, or the same
    figure tagged on the segment axis in some years and on the product axis in others); for each
    filing the first alternative it carries wins. Whether the alternatives really are one definition
    is checked by definition_breaks: a renamed member with recast values shows up as a break.
    """
    out = []
    for cik in ciks:
        for f, dfs in company_facts(cik, since, concepts):
            for axis, m in members:
                got = to_facts(list(dfs), f, list(concepts), axis, m)
                if got:
                    out += got
                    break
    return out
