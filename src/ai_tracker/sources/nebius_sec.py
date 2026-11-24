"""Nebius Group quarterly revenue, capex and operating cash flow from its SEC Form 6-K results releases.

Nebius Group N.V. (CIK 1513845, formerly Yandex N.V.) is a foreign private issuer: it files a 20-F, whose
XBRL (companyfacts) is annual only, and no 10-Q. Each quarterly results press release is furnished as
exhibit 99.1 of a 6-K, filed on the day of the release or the day after; the 6-K filing date is each
figure's `known_from`.

Parsing is deterministic and strict. Two highlight tables of the release are read:
- "Consolidated results": row "Revenues";
- "Selected consolidated cash flow data": rows "... operating activities – continuing operations" and
  "Purchases of property(, plant) and equipment (and intangible assets)" (sign flipped: capex > 0).
Each table has the header "Three months ended <Month> <day> [Six|Nine|Twelve months ended ...]
<prior year> <year> Change ...", in USD millions with one decimal. Every row must have exactly one value
pair plus a change column per header block, or the row is not used.

The figures become ordinary sec.Facts (3-month and year-to-date durations, USD), so the quarter and
vintage logic of ai_tracker.sources.sec applies unchanged: YTD differencing, Q4 = FY - 9M, one version per
filing date, comparatives give a new version only if the value changed beyond rounding. Q1 of the prior
year is derived as 6M - Q2 from the H1 release (sources.sec_financing.derived_first_quarters).

Definition. From the Q2 2025 release (2025-08-07) Toloka is deconsolidated and its results for prior
periods are in discontinued operations; earlier releases report a different basis (Q3 2024 revenue 43.3
there, 32.1 restated). Only releases filed on or after SINCE are read, and a restatement of more than 2 %
of an already filed value in later releases raises DefinitionBreakError (sec_segment.definition_breaks), so
a new basis cannot be spliced in silently. See docs/kallor/neoclouds.md.

Filings are immutable: documents are cached through sec_segment._cached_get (raw copies reused).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import pandas as pd

from ai_tracker import http
from ai_tracker.sources import sec, sec_financing, sec_segment
from ai_tracker.sources.tsmc_sec import to_text

SOURCE = "nebius_sec"
CIK = 1513845
SINCE = "2025-08-01"  # first release on the current basis (Toloka deconsolidated): 2025-08-07
RESULT_MONTHS = (2, 3, 5, 6, 8, 9, 11, 12)  # releases come in mid Feb/May/Aug/Nov; the next month as a margin
MAX_DOC_BYTES = 600_000  # press releases are 220-380 kB; interim financial statements (1.2-1.8 MB) are skipped
MEASURES = ("rev", "capex", "ocf")


class DefinitionBreakError(RuntimeError):
    pass


@dataclass(frozen=True)
class Filing:
    accession: str
    filed: str  # EDGAR filing date, YYYY-MM-DD
    form: str
    primary: str

    def url(self, doc: str) -> str:
        return sec_segment.ARCHIVE.format(cik=CIK, acc=self.accession.replace("-", ""), name=doc)


# ------------------------------------------------------------------ EDGAR access


def filings(since: str = SINCE) -> list[Filing]:
    """6-K filings (amendments included) filed on or after `since`, oldest first."""
    sub = http.get(sec_segment.SUBMISSIONS.format(cik=CIK), SOURCE).json()
    blocks = [sub["filings"]["recent"]]
    for f in sub["filings"].get("files", []):
        if f.get("filingTo", "9999") >= since:
            blocks.append(http.get(sec_segment.SUBMISSIONS_FILE.format(name=f["name"]), SOURCE).json())
    out = {}
    for b in blocks:
        for form, filed, acc, doc in zip(b["form"], b["filingDate"], b["accessionNumber"], b["primaryDocument"]):
            if form.startswith("6-K") and filed >= since:
                out[acc] = Filing(acc, filed, form, doc)
    return sorted(out.values(), key=lambda f: (f.filed, f.accession))


def candidate_docs(f: Filing) -> list[str]:
    """Exhibits of a filing that may be a results release (the 6-K cover and large documents skipped)."""
    index = json.loads(sec_segment._cached_get(f.url("index.json")))
    return sorted(it["name"] for it in index["directory"]["item"]
                  if it["name"].lower().endswith((".htm", ".html")) and "index" not in it["name"].lower()
                  and it["name"] != f.primary and int(it.get("size") or 0) <= MAX_DOC_BYTES)


def release_of(f: Filing) -> dict[str, list[tuple[pd.Timestamp, pd.Timestamp, float]]] | None:
    """The figures of the results release furnished in a 6-K, or None (most 6-Ks are something else)."""
    if pd.Timestamp(f.filed).month not in RESULT_MONTHS:
        return None
    for doc in candidate_docs(f):
        rel = parse_release(to_text(sec_segment._cached_get(f.url(doc)).decode("utf-8", errors="replace")))
        if rel is not None:
            return rel
    return None


# ------------------------------------------------------------------ parsing

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
TITLE_RE = re.compile(r"(?i)^.{0,120}?Nebius(?: Group N\.V\.)? (?:reports|announces) .{0,40}?quarter .{0,40}?financial results")
HEADER_RE = re.compile(
    rf"(?:In USD \$ millions )?Three months ended ({MONTHS}) (\d{{1,2}}),? "
    rf"(?:(Six|Nine|Twelve) months ended (?:{MONTHS}) \d{{1,2}},? )?(?:In USD \$ millions )?(\d{{4}}) (\d{{4}}) Change")
NUM = r"\(?\s*-?[\d,]+(?:\.\d+)?\s*\)|-?[\d,]+(?:\.\d+)?|—"
CHANGE = r"-?[\d,]+(?:\.\d+)?\s*%|n/m"
BLOCK = rf"\s+({NUM})\s+({NUM})\s+(?:{CHANGE})"
TABLES = {
    "rev": ("Consolidated results", {"rev": r"Revenues"}),
    "cash": ("Selected consolidated cash flow data",
             {"ocf": r"(?:Net )?[Cc]ash (?:provided by / \(used in\)|used in|provided by) operating activities\s*[–-]\s*"
                     r"continuing operations",
              "capex": r"Pu?r?chases of property(?:, plant)? and equipment(?: and intangible assets)?"}),
}
SIGN = {"rev": 1.0, "ocf": 1.0, "capex": -1.0}  # capex is an outflow in the table: stored as a positive amount
YTD_MONTHS = {"Six": 6, "Nine": 9, "Twelve": 12}
TABLE_SPAN = 2500  # characters after a table title that hold its header and rows


def _value(tok: str) -> float:
    tok = tok.replace(" ", "")
    if tok == "—":
        return 0.0
    neg = tok.startswith("(") or tok.startswith("-")
    v = float(tok.strip("()-").replace(",", ""))
    return -v if neg else v


def _periods(m: re.Match) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """(start, end) per column: [3M prior year, 3M year] (+ [YTD prior year, YTD year])."""
    month, day, ytd, y0, y1 = m.groups()
    out = []
    ends = [pd.Timestamp(f"{y} {month} {day}") for y in (y0, y1)]
    if int(y1) != int(y0) + 1:
        return []
    for e in ends:
        out.append(((e + pd.Timedelta(days=1)) - pd.DateOffset(months=3), e))
    if ytd:
        if YTD_MONTHS[ytd] != ends[0].month:  # calendar fiscal year: the YTD must start on 1 January
            return []
        out += [(pd.Timestamp(e.year, 1, 1), e) for e in ends]
    return out


def parse_table(text: str, title: str, rows: dict[str, str]) -> dict[str, list[tuple[pd.Timestamp, pd.Timestamp, float]]]:
    i = text.find(title)
    if i < 0:
        return {}
    body = text[i:i + TABLE_SPAN]
    hm = HEADER_RE.search(body)
    if not hm:
        return {}
    periods = _periods(hm)
    blocks = len(periods) // 2
    out = {}
    for measure, label in rows.items():
        rm = re.search(rf"(?:{label}){BLOCK * blocks}(?=\s|$)", body[hm.end():])
        if not rm or not periods:
            continue
        vals = [_value(v) * SIGN[measure] for v in rm.groups()]
        out[measure] = [(s, e, v) for (s, e), v in zip(periods, vals)]
    return out


def parse_release(text: str) -> dict[str, list[tuple[pd.Timestamp, pd.Timestamp, float]]] | None:
    """{measure: [(start, end, USD millions)]} of a Nebius results release in plain text, or None.

    None if the document is not a results release or its revenue row cannot be read.
    """
    if not TITLE_RE.search(text[:2000]):
        return None
    out = {}
    for title, rows in TABLES.values():
        out.update(parse_table(text, title, rows))
    return out if out.get("rev") else None


# ------------------------------------------------------------------ facts and vintages


def to_facts(items: list[tuple[Filing, dict]], measure: str) -> list[sec.Fact]:
    """sec.Facts (USD) of one measure, one per (release, column), dated by the 6-K's filing date."""
    out = []
    for f, rel in items:
        for start, end, v in rel.get(measure, []):
            out.append(sec.Fact(start, end, v * 1e6, pd.Timestamp(f.filed), f.form, f.accession))
    return out


def releases(since: str = SINCE) -> list[tuple[Filing, dict]]:
    out = []
    for f in filings(since):
        rel = release_of(f)
        if rel is not None:
            out.append((f, rel))
    return out


def vintages(items: list[tuple[Filing, dict]], measure: str, declared_breaks: tuple[str, ...] = ()) -> pd.DataFrame:
    """Release-dated quarterly rows (period, value MUSD, known_from, fiscal_end) for one measure.

    Raises DefinitionBreakError if a release restates an earlier released value by more than 2 % and that
    filing date is not declared.
    """
    facts = to_facts(items, measure)
    found = [str(d.date()) for d in sec_segment.definition_breaks(facts)]
    if sorted(found) != sorted(declared_breaks):
        raise DefinitionBreakError(f"nebius {measure}: definition breaks {found}, declared {list(declared_breaks)}")
    df = sec.vintages([facts, sec_financing.derived_first_quarters(facts)])
    df["value"] = df["value"].round(3)  # the releases have one decimal; drop float noise from the USD scaling
    return df
