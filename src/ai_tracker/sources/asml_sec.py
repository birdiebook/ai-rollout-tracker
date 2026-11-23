"""ASML quarterly net sales and net bookings from its SEC Form 6-K results press releases (EDGAR).

ASML is a foreign private issuer: no 10-Q, and its 20-F XBRL (companyfacts) is annual only. Every
quarterly results press release is furnished as a 6-K exhibit on the day it is published (07:00 CET,
filed with EDGAR the same day), so the 6-K filing date is each figure's `known_from`.

Parsing is deterministic and strict, as in tsmc_sec:
- Key-figures table (2010s-): "(Figures in millions of euros unless otherwise indicated)" followed by
  column labels ("Q2 2026 Q3 2026", sometimes "FY 2024 FY 2025" too, newest column first or last),
  then rows "Total net sales" / "Net sales" and "Net bookings". Values are matched to the column labels;
  footnote markers (single digits, "*") are dropped, and a row whose value count does not match the
  column count is not used.
- Q2 2013 (Cymer acquisition): a split key-figures table, see parse_split_table.
- Older releases (to about 2012): bullet sentences "Q3 2009 net sales of EUR 555 million versus Q2 2009
  net sales of EUR 277 million" and "Q3 2009 net bookings valued at EUR 777 million", every figure with
  its own quarter label.
Each release also repeats the previous quarter (and older ones the year-ago quarter). These comparatives
become later vintages only when they differ from what was known (beyond rounding), so restatements are
real vintages and never leak back.

Net bookings definitions changed over time (EUV excluded 2013-2015, a 12-month shipment window from
2015Q2, all accepted orders later, and ASML stopped reporting quarterly bookings after 2025Q4). The label
and footnote that define each figure are kept (`Figure.definition`), and series are split where the
definition changes (see ai_tracker.series.halvledare and docs/kallor/halvledare.md).

Filings are immutable, so documents are cached: the raw copies ai_tracker.http saves under
data/raw/asml_sec/<date>/ are reused on later runs.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Callable

import pandas as pd
import requests

from ai_tracker import http
from ai_tracker.sources.tsmc_sec import to_text

SOURCE = "asml_sec"
CIK = 937966
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SUBMISSIONS_FILE = "https://data.sec.gov/submissions/{name}"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"
RESULT_MONTHS = (1, 2, 4, 7, 10)  # results are published mid/late Jan, Apr, Jul, Oct (Feb as a margin)
MAX_DOC_BYTES = 200_000  # press releases are 5-60 kB; financial statements and presentations are skipped by name
SKIP_DOC = re.compile(r"(?i)financial_?statement|financialsusgaap|statementsusgaap|presentat|ifrs|statutory|annual|agm|\.(jpg|gif|png|pdf|xml|xsd|txt)$")


@dataclass(frozen=True)
class Filing:
    accession: str
    filed: str  # EDGAR filing date, YYYY-MM-DD
    form: str
    primary: str

    def url(self, doc: str) -> str:
        return ARCHIVE.format(cik=CIK, acc=self.accession.replace("-", ""), doc=doc)


@dataclass
class Release:
    """One quarterly results press release: {measure: {quarter: (value MEUR, definition)}}."""

    quarter: pd.Period  # the reported (newest) quarter
    figures: dict[str, dict[pd.Period, tuple[float, str]]] = field(default_factory=dict)

    def add(self, measure: str, q: pd.Period, value: float, definition: str) -> None:
        self.figures.setdefault(measure, {}).setdefault(q, (value, definition))


# ------------------------------------------------------------------ EDGAR access


def filings(form_prefix: str = "6-K") -> list[Filing]:
    """All 6-K filings (amendments included), oldest first."""
    sub = http.get(SUBMISSIONS.format(cik=CIK), SOURCE).json()
    blocks = [sub["filings"]["recent"]]
    blocks += [http.get(SUBMISSIONS_FILE.format(name=f["name"]), SOURCE).json() for f in sub["filings"].get("files", [])]
    out = {}
    for b in blocks:
        for form, filed, acc, doc in zip(b["form"], b["filingDate"], b["accessionNumber"], b["primaryDocument"]):
            if form.startswith(form_prefix):
                out[acc] = Filing(acc, filed, form, doc)
    return sorted(out.values(), key=lambda f: (f.filed, f.accession))


def _cached_get(url: str, retries: int = 2) -> bytes:
    """An immutable archive URL: a raw copy from an earlier run, else a (saved) GET.

    EDGAR's archive occasionally answers 404 for a filing that exists (seen for index.json files that
    load on the next try), so a 404 is retried before it is raised.
    """
    name = http.raw_path(SOURCE, url).name
    hits = sorted((http.RAW_DIR / SOURCE).glob(f"*/{name}"))
    if hits:
        return hits[-1].read_bytes()
    for attempt in range(retries + 1):
        try:
            return http.get(url, SOURCE).content
        except requests.HTTPError as e:
            if e.response is None or e.response.status_code != 404 or attempt == retries:
                raise
            time.sleep(2)
    raise RuntimeError("unreachable")


def candidate_docs(f: Filing) -> list[str]:
    """Documents of a filing that may be a results press release (exhibits first, the cover last)."""
    try:
        index = json.loads(_cached_get(f.url("index.json")))
    except requests.HTTPError:  # a few old filings have no index.json (persistent 404): the main document only
        return [f.primary]
    items = [(it["name"], int(it.get("size") or 0)) for it in index["directory"]["item"]]
    docs = [n for n, size in items if n.lower().endswith((".htm", ".html")) and "index" not in n.lower()
            and not SKIP_DOC.search(n) and size <= MAX_DOC_BYTES]
    return sorted(docs, key=lambda n: (n == f.primary, n))


def release_of(f: Filing) -> Release | None:
    """The results release furnished in a 6-K, or None (most 6-Ks are something else)."""
    if pd.Timestamp(f.filed).month not in RESULT_MONTHS:
        return None
    for doc in candidate_docs(f):
        rel = parse_release(to_text(_cached_get(f.url(doc)).decode("utf-8", errors="replace")))
        if rel is not None:
            return rel
    return None


# ------------------------------------------------------------------ parsing

NUM_TOKEN = re.compile(r"\s*(\(?-?[\d][\d,]*(?:\.\d+)?\)?\*?|\*\)?)(?=\s|$)")
SALES_ROW = re.compile(r"(?i)(?<![a-z] )\b((?:total )?net sales)\b")
BOOKINGS_ROW = re.compile(r"(?i)\b(net bookings(?:,? excluding EUV)?)\b(?! \(units\))")
SENT_SALES = re.compile(r"(?i)\bQ([1-4]) (\d{4}) (?:total )?net sales (?:of|were|was|totaled) (?:EUR|€) ?([\d,]+(?:\.\d+)?) (million|billion)")
SENT_BOOKINGS = re.compile(r"(?i)\bQ([1-4]) (\d{4}) net bookings (?:valued at|totaled [\d,]+ (?:lithography )?systems valued at|of) "
                           r"(?:EUR|€) ?([\d,]+(?:\.\d+)?) (million|billion)")
RESULTS_RE = re.compile(r"(?i)\b(?:quarter|Q[1-4])\b.{0,40}\bresults\b|\bresults\b.{0,60}\bquarter\b")


def _value(tok: str) -> float:
    neg = tok.startswith("(") or tok.startswith("-")
    v = float(tok.strip("()*- ").replace(",", ""))
    return -v if neg else v


def _row_values(text: str, start: int) -> list[str]:
    """Numeric tokens right after a row label, up to the next word (footnote markers included)."""
    out, pos = [], start
    while True:
        m = NUM_TOKEN.match(text, pos)
        if not m:
            return out
        out.append(m.group(1))
        pos = m.end()


def _clean(tokens: list[str], n: int) -> list[float] | None:
    """Row values for n columns: footnote markers ("*", single digits) dropped. None if the count is off."""
    toks = [t for t in tokens if t.strip("*)") != ""]
    if len(toks) > n:  # footnote marks after the label or a value: "Net bookings 2 5,399 13,158 18,899 3 28,035 3"
        toks = [t for t in toks if not re.fullmatch(r"\(?[1-9]\)?\*?", t)]
    if len(toks) != n:
        return None
    return [_value(t) for t in toks]


MARKER = re.compile(r"\(?[1-9]\)?\*?|\*\)?")


def _definition(text: str, after: int, label: str, tokens: list[str]) -> str:
    """The bookings figure's definition: its label plus the footnote it points to (normalised text).

    The marker is the first token after the label when it is a footnote ("2", "(3)", "*"); the
    footnote is the note "(2) ..." / "*) ..." that mentions bookings. Without a marker: the label only.
    """
    label = re.sub(r"\s+", " ", label.lower())
    marks = [t for t in tokens[:1] if MARKER.fullmatch(t)] or [t for t in tokens if t.strip("*)") == ""][:1]
    if not marks:
        return label
    mark = marks[0].strip("()")
    num = mark.strip("*")
    rx = (rf"\(\s*{num}\s*\)\s*([^()]*?bookings[^()]*?\.)(?=\s|$)" if num
          else r"\*\)?\s*([^*]*?bookings[^*]*?\.)(?=\s|$)")
    m = re.search(rx, text[after:], re.I)  # the notes follow the table
    note = re.sub(r"\s+", " ", m.group(1)).strip().lower() if m else "?"
    return f"{label} | {note}"


HEADER_RE = re.compile(r"(?i)((?:(?:Q[1-4]|FY) ?\d{4}(?:\s+\(?[1-9]\)?)?\s+){2,})((?:total )?net sales)\b")
COL_TOKEN = re.compile(r"(?i)(Q[1-4]|FY) ?(\d{4})")


def parse_table(text: str, rel: Release) -> bool:
    """Key-figures table: column labels ("Q2 2026 Q3 2026", "FY 2024", footnote marks allowed) right
    before its first row "Net sales" / "Total net sales". True if net sales were read."""
    hm = HEADER_RE.search(text)
    if not hm:
        return False
    cols = [(k.upper(), int(y)) for k, y in COL_TOKEN.findall(hm.group(1))]
    body = text[hm.start(2):hm.start(2) + 3000]
    got = False
    for measure, row_re in (("net_sales", SALES_ROW), ("net_bookings", BOOKINGS_ROW)):
        m = row_re.search(body)
        if not m or (measure == "net_sales" and m.start() != 0):
            continue
        tokens = _row_values(body, m.end())
        vals = _clean(tokens, len(cols))
        if vals is None:
            continue
        definition = (re.sub(r"\s+", " ", m.group(1).lower()) if measure == "net_sales"
                      else _definition(text, hm.start(2) + m.end(), m.group(1), tokens))
        for (kind, year), v in zip(cols, vals):
            if kind != "FY":
                rel.add(measure, pd.Period(f"{year}{kind}", freq="Q-DEC"), v, definition)
        got = got or measure == "net_sales"
    return got


SPLIT_HEADER_RE = re.compile(r"(?i)\bQ([1-4]) (\d{4}) ASML \(excluding (\w+)\)(?:(?!\bnet sales\b).){0,200}?"
                             r"\bQ\1 \2 ASML \(including \3\) Q([1-4]) (\d{4}) ASML (?=net sales\b)")


def parse_split_table(text: str, rel: Release) -> bool:
    """Key figures split around an acquisition (Q2 2013, Cymer consolidated from 30 May 2013): columns
    "Qn ASML (excluding X)", the acquired company, a purchase price allocation, "Qn ASML (including X)" and
    the previous quarter. Cells of the middle columns are blank in some rows, so only the last two values of a
    row are read: the reported quarter (including the acquisition, as in later comparatives) and the previous
    quarter. True if net sales were read."""
    hm = SPLIT_HEADER_RE.search(text)
    if not hm:
        return False
    cols = [pd.Period(f"{hm.group(2)}Q{hm.group(1)}", freq="Q-DEC"),
            pd.Period(f"{hm.group(5)}Q{hm.group(4)}", freq="Q-DEC")]
    if cols[1] != cols[0] - 1:
        return False
    body = text[hm.end():hm.end() + 3000]
    got = False
    for measure, row_re in (("net_sales", SALES_ROW), ("net_bookings", BOOKINGS_ROW)):
        m = row_re.search(body)
        if not m or (measure == "net_sales" and m.start() != 0):
            continue
        toks = [t for t in _row_values(body, m.end()) if not MARKER.fullmatch(t)]
        if len(toks) < 2:
            continue
        definition = re.sub(r"\s+", " ", m.group(1).lower())
        for q, t in zip(cols, toks[-2:]):
            rel.add(measure, q, _value(t), definition)
        got = got or measure == "net_sales"
    return got


def parse_sentences(text: str, rel: Release) -> None:
    """Older releases: 'Q3 2009 net sales of EUR 555 million', 'Q3 2009 net bookings valued at EUR 777 million'."""
    for measure, rx, definition in (("net_sales", SENT_SALES, "net sales"),
                                    ("net_bookings", SENT_BOOKINGS, "net bookings (sentence)")):
        for m in rx.finditer(text):
            v = float(m.group(3).replace(",", "")) * (1000 if m.group(4).lower() == "billion" else 1)
            rel.add(measure, pd.Period(f"{m.group(2)}Q{m.group(1)}", freq="Q-DEC"), v, definition)


def parse_release(text: str) -> Release | None:
    """A quarterly results press release in plain text, or None if the document is something else."""
    head = text[:3000]
    if "ASML" not in head or not RESULTS_RE.search(head):
        return None
    rel = Release(pd.Period("1900Q1", freq="Q-DEC"))
    if not parse_table(text, rel) and not parse_split_table(text, rel):
        parse_sentences(text[:6000], rel)
    sales = rel.figures.get("net_sales", {})
    if not sales:
        return None
    rel.quarter = max(sales)
    return rel


# ------------------------------------------------------------------ series


def releases() -> list[tuple[Filing, Release]]:
    out = []
    for f in filings():
        rel = release_of(f)
        if rel is not None:
            out.append((f, rel))
    return out


def vintages(items: list[tuple[str, Release]], measure: str, tol: float = 1.0,
             keep: Callable[[pd.Period, str], bool] | None = None) -> pd.DataFrame:
    """Release-dated rows (period, value, known_from, definition) for one measure.

    `items` = (filing date, release), any order. A figure becomes a row when its quarter was not known
    yet or its value differs from the latest known one by more than `tol` (MEUR, table rounding).
    `keep(quarter, definition)` selects the figures of one definition regime (default: all).
    """
    known: dict[pd.Period, float] = {}
    rows = []
    for filed, rel in sorted(items, key=lambda x: x[0]):
        for q, (v, d) in sorted(rel.figures.get(measure, {}).items()):
            if keep is not None and not keep(q, d):
                continue
            if q not in known or abs(known[q] - v) > tol:
                known[q] = v
                rows.append((str(q), v, pd.Timestamp(filed), d))
    df = pd.DataFrame(rows, columns=["period", "value", "known_from", "definition"])
    return df.sort_values(["period", "known_from"]).reset_index(drop=True)
