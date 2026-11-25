"""Alibaba and Baidu quarterly results from their SEC Form 6-K press releases (EDGAR), release-dated (track CN1).

Both are foreign private issuers: no 10-Q, and the 20-F XBRL (companyfacts) is annual. Each quarterly results
announcement is furnished as an exhibit (usually 99.1) of a 6-K on the day of the announcement; the 6-K filing date is
each figure's `known_from` (docs/kallor/kina_sec.md, register entry 2026-11-25 CN1).

This module holds the EDGAR access, the release discovery and the vintage logic with its definition eras. Table
parsing is in ai_tracker.sources.china_parse, the curated text extraction (Baidu) in ai_tracker.sources.china_text.

Filings are immutable, so documents are cached: a raw copy that ai_tracker.http saved under data/raw/china_sec/<date>/
(in this or any track, AI_TRACKER_SHARED_RAW) is reused on later runs.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd
import requests

from ai_tracker import http
from ai_tracker.sources import china_parse
from ai_tracker.sources.tsmc_sec import to_text

SOURCE = "china_sec"
CIKS = {"baba": 1577552, "bidu": 1329099}
NAMES = {"baba": "Alibaba Group", "bidu": "Baidu"}
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SUBMISSIONS_FILE = "https://data.sec.gov/submissions/{name}"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"
XBRL_VIEWER = re.compile(r"(?i)R\d+\.htm")  # rendered XBRL pages of a filing, never a press release
DOC_PAUSE = 0.3  # seconds after each fetched document (several tracks share sec.gov; brief of run 14)
MIN_DOC_BYTES = 20_000  # results releases are 90 kB - 1 MB; buyback notices and cover letters are 2-15 kB
MAX_DOC_BYTES = 3_000_000
SINCE = {"baba": "2015-01-01", "bidu": "2020-01-01"}  # Baidu: the first release with a cash-flow table is 2020-03-04
TOL = 0.5  # MRMB: the tables round to millions; a smaller change is not a new vintage


class DefinitionBreakError(RuntimeError):
    """A release restates an earlier value of the same definition era, and that filing date is not declared."""


@dataclass(frozen=True)
class Filing:
    cik: int
    accession: str
    filed: str  # EDGAR filing date, YYYY-MM-DD
    accepted: str  # EDGAR acceptanceDateTime (UTC)
    form: str
    primary: str

    def url(self, doc: str) -> str:
        return ARCHIVE.format(cik=self.cik, acc=self.accession.replace("-", ""), doc=doc)


# ------------------------------------------------------------------ EDGAR access


def filings(cik: int, form_prefix: str = "6-K", since: str = "2000-01-01") -> list[Filing]:
    """Filings of one form family (amendments included) filed on or after `since`, oldest first."""
    sub = http.get(SUBMISSIONS.format(cik=cik), SOURCE).json()
    blocks = [sub["filings"]["recent"]]
    for f in sub["filings"].get("files", []):
        if f.get("filingTo", "9999") >= since:
            blocks.append(http.get(SUBMISSIONS_FILE.format(name=f["name"]), SOURCE).json())
    out = {}
    for b in blocks:
        for form, filed, acc, doc, acc_t in zip(b["form"], b["filingDate"], b["accessionNumber"],
                                                b["primaryDocument"], b["acceptanceDateTime"]):
            if form.startswith(form_prefix) and filed >= since:
                out[acc] = Filing(cik, acc, filed, acc_t, form, doc)
    return sorted(out.values(), key=lambda f: (f.filed, f.accession))


def cached_get(url: str, retries: int = 2) -> bytes:
    """An immutable archive URL: a raw copy from an earlier run (any track, shared raw), else a saved GET.

    EDGAR's archive now and then answers 404 for a filing that loads on the next try, so a 404 is retried.
    A 403 or 429 is raised: the caller stops (fair access), it is never worked around.
    """
    name = http.raw_path(SOURCE, url).name
    hits = sorted((http.RAW_DIR / SOURCE).glob(f"*/{name}"))
    if hits:
        return hits[-1].read_bytes()
    for attempt in range(retries + 1):
        try:
            content = http.get(url, SOURCE).content
            time.sleep(DOC_PAUSE)
            return content
        except requests.HTTPError as e:
            if e.response is None or e.response.status_code != 404 or attempt == retries:
                raise
            time.sleep(2)
    raise RuntimeError("unreachable")


def candidate_docs(f: Filing, index: dict) -> list[str]:
    """Documents of a filing that may hold a results release, in reading order: exhibits named ex99 (ex99-1 first),
    then any other .htm document of release size, then the primary document if it is that large (Alibaba's first
    release after the IPO, 2014-11-04, is the 6-K's primary document)."""
    items = [(it["name"], int(it.get("size") or 0)) for it in index["directory"]["item"]]
    docs = [(n, s) for n, s in items if n.lower().endswith((".htm", ".html")) and "index" not in n.lower()
            and not XBRL_VIEWER.fullmatch(n) and MIN_DOC_BYTES <= s <= MAX_DOC_BYTES]
    ex = sorted(n for n, _ in docs if n != f.primary and re.search(r"(?i)ex-?_?99", n))
    other = sorted(n for n, _ in docs if n != f.primary and n not in ex)
    primary = [n for n, _ in docs if n == f.primary]
    return ex + other + primary


def release_of(company: str, f: Filing) -> tuple[str, china_parse.Release] | None:
    """(document name, parsed release) of the results release furnished in a 6-K, or None."""
    parse = china_parse.PARSERS[company]
    index = json.loads(cached_get(f.url("index.json")))
    for doc in candidate_docs(f, index):
        text = to_text(cached_get(f.url(doc)).decode("utf-8", errors="replace"))
        rel = parse(text)
        if rel is not None:
            return doc, rel
    return None


@lru_cache(maxsize=None)
def releases(company: str) -> tuple[tuple[Filing, str, china_parse.Release], ...]:
    """Every results release of a company since SINCE, oldest first. Network (cached documents)."""
    out = []
    for f in filings(CIKS[company], since=SINCE[company]):
        hit = release_of(company, f)
        if hit is not None:
            out.append((f, *hit))
    return tuple(out)


# ------------------------------------------------------------------ definition eras and vintages


@dataclass(frozen=True)
class Era:
    key: str  # series key ("" for a definition with a single release: no series)
    first: str  # first release (filing date) on this definition
    last: str | None  # last release on it (None: open)
    definition: str  # Swedish, for the note
    revisions: tuple[str, ...] = ()  # declared filing dates of in-era restatements


# Boundaries from the companies' own text on reclassification (docs/kallor/kina_sec.md, "Definitioner").
ERAS: dict[tuple[str, str], tuple[Era, ...]] = {
    ("baba", "rev_cloud"): (
        Era("rev_baba_cloud_v1", "2016-08-11", "2021-05-13",
            "segmentet Cloud computing (FY2017–FY2021), före DingTalk"),
        # 2021-08-03: "Beginning on April 1, 2021, we reclassified the results of our DingTalk business ... to the cloud
        # computing segment. ... Comparative figures were reclassified". From 2022-02-24 the row is called "Cloud".
        Era("rev_baba_cloud_v2", "2021-08-03", "2023-05-18",
            "segmentet Cloud computing, från 2022-02 kallat Cloud, med DingTalk (omklassat från 2021-04-01)"),
        # 2023-08-10: the six business groups; segment revenue before consolidation (inter-segment) adjustments, with
        # DingTalk. One release only, so no series. 2023-11-16: DingTalk moves to All others from the quarter ended
        # September 30, 2023, with reclassified comparatives, stated in the 2023-11-16 release itself (and again in
        # 2024-08-15: "Starting from the quarter ended September 30, 2023, we reclassified the revenue of our DingTalk
        # business ... to All others"; review R21, N-5).
        Era("", "2023-08-10", "2023-08-10", "Cloud Intelligence Group med DingTalk (bara ett pressmeddelande)"),
        Era("rev_baba_cloud_v3", "2023-11-16", "2026-05-13",
            "Cloud Intelligence Group utan DingTalk, segmentintäkt före koncernelimineringar (med intäkter från andra "
            "segment)"),
        # 2026-08-20: "Cloud Intelligence Group and T-Head were combined to form AI Cloud and Compute Services."
        Era("rev_baba_cloud_v4", "2026-08-20", None,
            "AI Cloud and Compute Services (Cloud Intelligence Group och T-Head sammanslagna), före "
            "koncernelimineringar"),
    ),
    ("baba", "capex"): (
        # v1's line holds licensed copyrights of video content at least from FY2017: the 20-F FY2017 element is
        # PaymentsToAcquireOtherPropertyEquipmentIntangibleAssetsAndLicensedCopyrightsOfVideoContent, and the 2018-11-02
        # release splits 2017Q3 (8,002) into 5,322 PP&E and 2,680 copyrights and intangible assets (review R21, R21-4).
        Era("capex_baba_v1", "2015-01-29", "2018-05-04",
            "Purchase of property and equipment and intangible assets (excluding land use rights and construction in "
            "progress), avstämningen mot fritt kassaflöde. Raden innehåller licensierade upphovsrätter till "
            "videoinnehåll, åtminstone från FY2017 (begreppet i 20-F FY2017 slutar på "
            "\"AndLicensedCopyrightsOfVideoContent\"). Pressmeddelandet 2018-11-02 delar upp 2017Q3: av 8 002 MRMB var "
            "2 680 upphovsrätter och immateriella tillgångar och 5 322 anläggningstillgångar"),
        Era("", "2018-08-23", "2018-08-23",
            "property and equipment, intangible assets and licensed copyrights (bara ett pressmeddelande)"),
        Era("capex_baba_v2", "2018-11-02", None,
            "Purchase of property and equipment (excluding land use rights and construction in progress relating to "
            "office campuses), avstämningen mot fritt kassaflöde"),
    ),
    ("bidu", "capex_total"): (
        Era("capex_bidu", "2020-03-04", None, "Less: Capital expenditures, Baidu, Inc."),
    ),
    ("bidu", "capex_core"): (
        Era("capex_bidu_core", "2020-03-04", None,
            "Less: Capital expenditures, Baidu excl. iQIYI (Baidu, Inc. minus iQIYI:s konsoliderade kassaflöden)"),
    ),
}


def era_of(eras: tuple[Era, ...], filed: str) -> Era | None:
    for e in eras:
        if e.first <= filed and (e.last is None or filed <= e.last):
            return e
    return None


def figures(items, measure: str) -> list[tuple[str, str, float]]:
    """(filed, period, value) of one measure from [(Filing, doc, Release)], one per (release, period)."""
    out = []
    for f, _doc, rel in items:
        for q, (v, _label) in rel.figures.get(measure, {}).items():
            out.append((f.filed, str(q), v))
    return sorted(out)


def era_vintages(rows: list[tuple[str, str, float]], era: Era) -> pd.DataFrame:
    """Release-dated rows (period, value, known_from) of one era from (filed, period, value).

    A period gets a row when first released and again when a later release changes it by more than TOL; such a
    change at a filing date not in era.revisions raises DefinitionBreakError (register entry 2026-11-25 CN1).
    """
    last: dict[str, float] = {}
    out = []
    for filed, period, value in sorted(r for r in rows if era_of((era,), r[0]) is era):
        if period in last:
            if abs(value - last[period]) <= TOL:
                continue
            if filed not in era.revisions:
                raise DefinitionBreakError(
                    f"{era.key or era.definition}: {period} restated {last[period]} -> {value} on {filed}, "
                    f"not declared")
        last[period] = value
        out.append((period, float(value), pd.Timestamp(filed)))
    df = pd.DataFrame(out, columns=["period", "value", "known_from"])
    return df.sort_values(["known_from", "period"], ignore_index=True)


def undeclared(items, company: str, measure: str) -> list[str]:
    """Filing dates of releases with this measure that fall in no declared era (a new definition not yet declared)."""
    eras = ERAS[(company, measure)]
    return sorted({f.filed for f, _d, rel in items if measure in rel.figures and era_of(eras, f.filed) is None})


def series(company: str, measure: str, key: str) -> pd.DataFrame:
    """Release-dated quarterly rows (period, value MRMB, known_from) of one era series. Network (cached documents).

    Raises DefinitionBreakError when a release falls in no declared era, or restates an era's value undeclared.
    """
    items = releases(company)
    gaps = undeclared(items, company, measure)
    if gaps:
        raise DefinitionBreakError(f"{company} {measure}: releases in no declared era: {gaps}")
    era = next(e for e in ERAS[(company, measure)] if e.key == key)
    return era_vintages(figures(items, measure), era)
