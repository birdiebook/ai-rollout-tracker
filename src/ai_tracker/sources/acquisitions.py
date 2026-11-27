"""Business acquisitions read from 10-Qs and 10-Ks: agent-extracted facts for LT1's acquisition mark (register QA1).

LT1 marks the origins whose change in pace an acquisition touches (register 2026-11-26 LT1 (c), X25 point 2). Eaton's
and Cisco's acquisitions were documented in the source documents before LT1; Quanta's are coded here from Quanta's own
filings (register 2026-11-27 QA1):

1. documents() lists the company's 10-Q/10-K filings on EDGAR; document_text() fetches the primary document (a cached
   raw copy when there is one), converts it to plain text (tsmc_sec.to_text) and splits it into sentences as
   lease_commitments does. Locators are "sentence #k" in that list, from 0.
2. The agent reads the acquisition note, MD&A and Part II Item 2 (unregistered sales of shares, which give closing
   dates) of each filing and records one row per fact in curated/acquisitions.csv: an acquisition stated directly
   (a closing date, a named deal, a subsequent event), a count (the number of businesses acquired in a stated
   period, e.g. "nine months ended": the quarter's new businesses are the count less the previous filing's), the
   consideration as stated, a statement about acquired RPO or backlog, or a quarter with no acquisition. The sentence itself is written only to
   data/raw/acquisitions_sentences/ (gitignored): the repo is public, and only figures with a source reference are
   published.
3. acquisitions_check (python -m ai_tracker.acquisitions_check) re-fetches a sample and verifies the hash at the
   locator, the numbers and dates of the row in the sentence, and the filing date.

An *event* is one acquisition, or the businesses a company acquired in one quarter when it only states them together.
Its quarter a is the calendar quarter of the closing date; when only a period is stated, the period's last quarter
(register QA1, point 3). marks() gives each event known on a day, with the latest consideration known on that day.
Nothing here changes a reading: the marks are text beside an outcome (LT1 (c)).
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ai_tracker import config, http
from ai_tracker.sources import lease_commitments as lc
from ai_tracker.sources import sec, tsmc_sec

SOURCE = "acquisitions"
PATH = config.REPO / "curated" / "acquisitions.csv"
SENTENCES_DIR = config.REPO / "data" / "raw" / "acquisitions_sentences"  # gitignored
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SUBMISSIONS_FILE = "https://data.sec.gov/submissions/{name}"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"
COMPANIES = {"pwr": 1050915}
NAMES = {"pwr": "Quanta"}
SINCE = "2023-01-01"  # register QA1, point 1: acquisitions that closed from 2023-01-01

ROW_TYPES = ("acquisition", "count", "consideration", "none", "rpo_statement")
MARK_TYPES = ("acquisition", "count")  # rows that carry an event's label
SCOPES = ("deal", "period")  # consideration of one named deal, or of every business acquired in a stated period
COLUMNS = ["id", "company", "event", "row_type", "label", "n_businesses", "closed", "quarter", "consideration_musd",
           "consideration_scope", "period_stated", "qualifier", "rpo_added_musd", "filed", "form", "accession",
           "source_url", "locator", "sentence_sha256", "note"]
QUALIFIERS = ("", "approx")


class CsvError(ValueError):
    pass


@dataclass(frozen=True)
class Document:
    company: str
    cik: int
    accession: str
    filed: str
    form: str
    report_date: str
    primary: str

    @property
    def url(self) -> str:
        return ARCHIVE.format(cik=self.cik, acc=self.accession.replace("-", ""), doc=self.primary)


def documents(company: str, since: str = "2022-12-31") -> list[Document]:
    """10-Q/10-K-family filings with a report date from `since` (the 10-K for 2022 included), oldest first."""
    cik = COMPANIES[company]
    sub = http.get(SUBMISSIONS.format(cik=cik), SOURCE).json()
    blocks = [sub["filings"]["recent"]]
    for f in sub["filings"].get("files", []):
        if f.get("filingTo", "9999") >= since:
            blocks.append(http.get(SUBMISSIONS_FILE.format(name=f["name"]), SOURCE).json())
    out = {}
    for b in blocks:
        for i, form in enumerate(b["form"]):
            if form.startswith(sec.FORMS) and b["reportDate"][i] >= since and b["primaryDocument"][i]:
                out[b["accessionNumber"][i]] = Document(company, cik, b["accessionNumber"][i], b["filingDate"][i],
                                                        form, b["reportDate"][i], b["primaryDocument"][i])
    return sorted(out.values(), key=lambda d: (d.filed, d.accession))


def cached_get(url: str) -> bytes:
    """Content of an immutable archive URL: a raw copy from an earlier run (this source or lease_commitments)."""
    for source in (SOURCE, lc.SOURCE):
        name = http.raw_path(source, url).name
        hits = sorted((http.RAW_DIR / source).glob(f"*/{name}"))
        if hits:
            return hits[-1].read_bytes()
    return http.get(url, SOURCE).content


def document_text(url: str, fresh: bool = False) -> str:
    raw = http.get(url, SOURCE).content if fresh else cached_get(url)
    return tsmc_sec.to_text(raw.decode("utf-8", errors="replace"))


def sentences(text: str) -> list[str]:
    """The same split as lease_commitments.sentences (tables split off); locators count from 0."""
    return lc.sentences(text)


def save_sentence(row_id: str, sentence: str) -> Path:
    """The exact source sentence, kept only in data/raw (gitignored)."""
    SENTENCES_DIR.mkdir(parents=True, exist_ok=True)
    p = SENTENCES_DIR / f"{row_id}.txt"
    p.write_text(sentence, encoding="utf-8")
    return p


# ------------------------------------------------------------------ the curated table


def quarter_of(day: str) -> str:
    return str(pd.Period(pd.Timestamp(day), freq="Q"))


def _num(x: str) -> float | None:
    return float(x) if str(x).strip() else None


def load(path: Path | None = None) -> pd.DataFrame:
    """curated/acquisitions.csv, validated (CsvError names the row)."""
    path = path or PATH
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if rows and list(rows[0]) != COLUMNS:
        raise CsvError(f"{path}: columns {list(rows[0])} != {COLUMNS}")
    seen = set()
    for r in rows:
        where = f"{path.name} row {r['id']}"
        if r["id"] in seen:
            raise CsvError(f"{where}: duplicate id")
        seen.add(r["id"])
        if r["company"] not in COMPANIES:
            raise CsvError(f"{where}: unknown company {r['company']!r}")
        if r["row_type"] not in ROW_TYPES:
            raise CsvError(f"{where}: row_type {r['row_type']!r} not in {ROW_TYPES}")
        if not re.fullmatch(r"\d{4}Q[1-4]", r["quarter"]):
            raise CsvError(f"{where}: quarter {r['quarter']!r}")
        if r["closed"]:
            if quarter_of(r["closed"]) != r["quarter"]:
                raise CsvError(f"{where}: closed {r['closed']} is not in quarter {r['quarter']}")
            if r["closed"] < SINCE:
                raise CsvError(f"{where}: closed before {SINCE} (register QA1, point 1)")
        if r["row_type"] == "consideration":
            if _num(r["consideration_musd"]) is None or r["consideration_scope"] not in SCOPES:
                raise CsvError(f"{where}: a consideration row needs consideration_musd and a scope in {SCOPES}")
            if r["consideration_scope"] == "period" and not r["period_stated"]:
                raise CsvError(f"{where}: a period consideration names its period")
        if r["row_type"] == "count" and (not r["n_businesses"] or not r["period_stated"]):
            raise CsvError(f"{where}: a count row needs n_businesses and the period it covers")
        if r["row_type"] in MARK_TYPES and not r["label"]:
            raise CsvError(f"{where}: an acquisition or count row needs the event's label")
        if r["qualifier"] not in QUALIFIERS:
            raise CsvError(f"{where}: qualifier {r['qualifier']!r}")
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", r["accession"]):
            raise CsvError(f"{where}: accession {r['accession']!r}")
        if not r["source_url"].startswith("https://www.sec.gov/Archives/edgar/data/"):
            raise CsvError(f"{where}: source_url is not an EDGAR archive URL")
        if r["accession"].replace("-", "") not in r["source_url"]:
            raise CsvError(f"{where}: source_url does not carry the accession")
        if not re.fullmatch(r"sentence #\d+", r["locator"]):
            raise CsvError(f"{where}: locator {r['locator']!r}")
        if not re.fullmatch(r"[0-9a-f]{64}", r["sentence_sha256"]):
            raise CsvError(f"{where}: sentence_sha256")
        if r["closed"] and r["filed"] < r["closed"]:
            raise CsvError(f"{where}: filed before the acquisition closed")
    df = pd.DataFrame(rows, columns=COLUMNS)
    for c in ("consideration_musd", "rpo_added_musd", "n_businesses"):
        df[c] = pd.to_numeric(df[c].replace("", None))
    df["known_from"] = pd.to_datetime(df["filed"])
    events = df.groupby("event")["quarter"].nunique()
    if (events > 1).any():
        raise CsvError(f"{path.name}: events with more than one quarter: {list(events[events > 1].index)}")
    return df


def _fmt_musd(v: float) -> str:
    return f"{v:,.0f}".replace(",", " ")


def marks(company: str, as_of=None, df: pd.DataFrame | None = None) -> list[tuple[str, str, str]]:
    """(label, quarter a, first known day) per acquisition event known on `as_of` (every event when None).

    The label carries the latest consideration known on the day (register QA1, points 3 to 5), with the period it
    covers when the company states it for a period: 'Quanta, 3 förvärv 2026Q2 (1 430 MUSD, 6 mån 2026)' or
    'Quanta–Cupertino Electric (2 035 MUSD)'. Quarters with no acquisition ('none') give no mark."""
    d = load() if df is None else df
    d = d[(d["company"] == company) & d["row_type"].isin((*MARK_TYPES, "consideration"))]
    if as_of is not None:
        d = d[d["known_from"] <= pd.Timestamp(as_of)]
    out = []
    for event, g in d.groupby("event"):
        acq = g[g["row_type"].isin(MARK_TYPES)].sort_values(["known_from", "id"])
        if acq.empty:
            continue  # a consideration known before the event is stated is not a mark on its own
        label = acq.iloc[-1]["label"]
        cons = g[g["row_type"] == "consideration"].sort_values(["known_from", "id"])
        if not cons.empty:
            c = cons.iloc[-1]
            approx = "cirka " if c["qualifier"] == "approx" else ""
            span = f", {c['period_stated']}" if c["consideration_scope"] == "period" else ""
            label += f" ({approx}{_fmt_musd(c['consideration_musd'])} MUSD{span})"
        first = str(g["known_from"].min().date())
        out.append((label, acq.iloc[0]["quarter"], first))
    return sorted(out, key=lambda m: (m[1], m[0]))
