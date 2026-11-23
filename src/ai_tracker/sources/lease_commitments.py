"""Leases signed but not yet commenced: agent-extracted amounts from the lease notes of 10-Qs and 10-Ks.

Companies disclose, in the lease note, leases they have signed that have not yet commenced (no right-of-use asset
or liability yet), e.g. "we have additional operating and finance leases, primarily for datacenters, that have not
yet commenced of $X billion". The number is text, not XBRL: companyfacts has no standard concept for it. So:

1. candidates() fetches each 10-Q/10-K primary document (EDGAR archive, cached raw copy), converts it to plain
   text (tsmc_sec.to_text), splits it into sentences (guidance_capex.sentences, with
   tables split off, see sentences()) and returns the sentences that
   mention leases not yet commenced, with their locator ("sentence #k") and SHA-256 (guidance_capex.sentence_hash).
2. The agent reads every candidate sentence and records one row per amount in curated/lease_commitments.csv
   (a worksheet pre-fills the obvious pattern; every row is read and corrected by the agent before it is kept).
   The sentence itself is written only to data/raw/lease_commitments_sentences/ (gitignored): the repo is public,
   and only extracted figures with a source reference are published.
3. lease_check (python -m ai_tracker.lease_check) re-fetches a 20 % sample and verifies the hash and the number
   at the locator. An independent review (R5) reads the sources again before the series are used.

known_from = `filed`, the EDGAR filing date of the 10-Q/10-K (the amount is not in the earnings release).
period = the balance date the sentence refers to ("As of September 30, 2026, ..."), which is the fiscal period end
of the filing.

lease_type: operating | finance (Microsoft to FY2025 Q3, Meta to 2023), short_term | long_term (Alphabet's 10-K split by
lease term), total (one amount for all leases). The series per company (series/lease_commitments.py) is the total: `total` where given,
otherwise the sum of the parts from the same filing (operating + finance, short + long term), otherwise the single
type disclosed (Meta 2024Q1-Q3 and Oracle to FY2024: operating leases only, noted in the row).
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from ai_tracker import config, http
from ai_tracker.sources import guidance_capex as gc
from ai_tracker.sources import sec
from ai_tracker.sources import tsmc_sec

SOURCE = "lease_commitments"
PATH = config.REPO / "curated" / "lease_commitments.csv"
SENTENCES_DIR = config.REPO / "data" / "raw" / "lease_commitments_sentences"  # gitignored
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SUBMISSIONS_FILE = "https://data.sec.gov/submissions/{name}"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"
SINCE = "2019-01-01"  # ASC 842 (leases on the balance sheet) from 2019; MSFT adopted it in FY2019

COMPANIES = {"msft": 789019, "googl": 1652044, "amzn": 1018724, "meta": 1326801, "orcl": 1341439, "crwv": 1769628}
LEASE_TYPES = ("operating", "finance", "short_term", "long_term", "total")
COLUMNS = ["id", "company", "period", "lease_type", "value", "unit", "filed", "form", "accession", "source_url",
           "locator", "sentence_sha256", "note"]

CANDIDATE_RE = re.compile(r"(?i)(not\s+yet\s+commenced|ha(?:ve|d)\s+not\s+commenced|not\s+commenced|yet\s+to\s+commence|"
                          r"expected\s+to\s+commence|will\s+commence|additional\s+(?:operating\s+)?lease\s+commitments)")
LEASE_RE = re.compile(r"(?i)lease")


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


def documents(company: str, since: str = SINCE) -> list[Document]:
    """10-Q/10-K-family filings (amendments included) with their primary document, oldest first."""
    cik = COMPANIES[company]
    sub = http.get(SUBMISSIONS.format(cik=cik), SOURCE).json()
    blocks = [sub["filings"]["recent"]]
    for f in sub["filings"].get("files", []):
        if f.get("filingTo", "9999") >= since:
            blocks.append(http.get(SUBMISSIONS_FILE.format(name=f["name"]), SOURCE).json())
    out = {}
    for b in blocks:
        for i, form in enumerate(b["form"]):
            if form.startswith(sec.FORMS) and b["filingDate"][i] >= since and b["primaryDocument"][i]:
                out[b["accessionNumber"][i]] = Document(company, cik, b["accessionNumber"][i], b["filingDate"][i],
                                                        form, b["reportDate"][i], b["primaryDocument"][i])
    return sorted(out.values(), key=lambda d: (d.filed, d.accession))


def cached_get(url: str) -> bytes:
    """Content of an immutable archive URL: a raw copy from an earlier run, else a (saved) GET."""
    name = http.raw_path(SOURCE, url).name
    hits = sorted((http.RAW_DIR / SOURCE).glob(f"*/{name}"))
    return hits[-1].read_bytes() if hits else http.get(url, SOURCE).content


def document_text(url: str, fresh: bool = False) -> str:
    raw = http.get(url, SOURCE).content if fresh else cached_get(url)
    return tsmc_sec.to_text(raw.decode("utf-8", errors="replace"))


# A lease note's tables have no full stops, so guidance_capex.sentences leaves a table and the sentence after it
# in one piece. A number (or ")" / "%") followed by a capitalised word starts a new piece.
_TABLE_SPLIT = re.compile(r"(?<=[\d)%])\s+(?=[A-Z][a-z]+\s)")


def sentences(text: str) -> list[str]:
    """Sentences of a document's plain text; locators ("sentence #k") count in this list from 0."""
    return [p for s in gc.sentences(text) for p in _TABLE_SPLIT.split(s) if p.strip()]


def candidate_sentences(text: str) -> list[tuple[int, str]]:
    """(index, sentence) for sentences about leases that have not commenced."""
    return [(k, s) for k, s in enumerate(sentences(text)) if CANDIDATE_RE.search(s) and LEASE_RE.search(s)]


@lru_cache(maxsize=None)
def candidates(company: str, since: str = SINCE) -> tuple[tuple[Document, int, str], ...]:
    out = []
    for doc in documents(company, since):
        for k, s in candidate_sentences(document_text(doc.url)):
            out.append((doc, k, s))
    return tuple(out)


# ------------------------------------------------------------------ amounts in a sentence

AMOUNT_RE = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)\s*(billion|million)", re.I)


def amounts(sentence: str) -> list[float]:
    """Dollar amounts in a sentence, in MUSD, in order of appearance."""
    out = []
    for num, unit in AMOUNT_RE.findall(sentence):
        v = float(num.replace(",", ""))
        out.append(v * 1000 if unit.lower() == "billion" else v)
    return out


def number_pattern(value_musd: float) -> str:
    """Regex for a MUSD amount as written: '$108.4 billion', '$650 million' / '$1,250 million', or a table cell
    in millions ('28,869', Amazon's commitments table)."""
    alts = []
    if value_musd >= 1000:
        b = round(value_musd / 1000, 3)
        whole, _, frac = f"{b:.3f}".rstrip("0").rstrip(".").partition(".")
        alts.append(rf"\$\s?{whole}" + (rf"\.{frac}0*" if frac else r"(?:\.0+)?") + r"\s*billion")
    m = round(value_musd, 1)
    whole, _, frac = f"{m:.1f}".rstrip("0").rstrip(".").partition(".")
    grouped = f"{int(whole):,}"
    alts.append(rf"\$\s?{grouped.replace(',', ',?')}" + (rf"\.{frac}0*" if frac else r"(?:\.0+)?") + r"\s*million")
    if not frac and "," in grouped:  # a bare table cell only with a thousands separator, never e.g. a year
        alts.append(rf"(?<![\d,.]){grouped}(?![\d,]|\.\d)")
    return r"(?i)(?:" + "|".join(alts) + ")"


# ------------------------------------------------------------------ curated CSV


class CsvError(ValueError):
    pass


def load(path: Path | None = None) -> pd.DataFrame:
    """Validated rows of curated/lease_commitments.csv, with known_from (= filed) as Timestamp."""
    path = path or PATH
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if rows and list(rows[0]) != COLUMNS:
        raise CsvError(f"columns {list(rows[0])} != {COLUMNS}")
    seen, keys = set(), set()
    for r in rows:
        where = f"{path.name} id={r.get('id')}"
        if r["id"] in seen:
            raise CsvError(f"{where}: duplicate id")
        seen.add(r["id"])
        if r["company"] not in COMPANIES or r["lease_type"] not in LEASE_TYPES or r["unit"] != "MUSD":
            raise CsvError(f"{where}: company/lease_type/unit not in the scheme")
        key = (r["company"], r["period"], r["lease_type"], r["accession"])
        if key in keys:
            raise CsvError(f"{where}: two values for one company, period, type and filing")
        keys.add(key)
        if not re.fullmatch(r"[0-9a-f]{64}", r["sentence_sha256"]):
            raise CsvError(f"{where}: sentence_sha256 must be 64 hex characters")
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", r["accession"]):
            raise CsvError(f"{where}: accession must look like 0000000000-00-000000")
        if not r["source_url"].startswith("https://www.sec.gov/Archives/") or not re.fullmatch(r"sentence #\d+",
                                                                                              r["locator"]):
            raise CsvError(f"{where}: source_url (EDGAR archive) and locator ('sentence #k') are required")
        if r["accession"].replace("-", "") not in r["source_url"]:
            raise CsvError(f"{where}: accession is not the source_url's folder")
        try:
            value = float(r["value"])
        except ValueError as exc:
            raise CsvError(f"{where}: value must be a number") from exc
        if value <= 0:
            raise CsvError(f"{where}: value must be positive")
        period, filed = pd.Timestamp(r["period"]), pd.Timestamp(r["filed"])
        if filed <= period:
            raise CsvError(f"{where}: filed {filed.date()} not after the balance date {period.date()}")
        if (filed - period).days > 120 and not r["form"].endswith("/A"):
            raise CsvError(f"{where}: filed more than 120 days after the balance date (wrong period?)")
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["value"] = pd.to_numeric(df["value"])
    df["known_from"] = pd.to_datetime(df["filed"])
    return df


def write(rows: list[dict], path: Path | None = None) -> None:
    path = path or PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def save_sentence(row_id: str, sentence: str) -> Path:
    """The exact source sentence, kept only in data/raw (gitignored)."""
    SENTENCES_DIR.mkdir(parents=True, exist_ok=True)
    p = SENTENCES_DIR / f"{row_id}.txt"
    p.write_text(sentence, encoding="utf-8")
    return p


# ------------------------------------------------------------------ series


def calendar_period(balance_date: str) -> str:
    """Calendar quarter of a balance date, by the fiscal-quarter midpoint rule (as sec_financing)."""
    return str((pd.Timestamp(balance_date) - pd.Timedelta(days=45)).to_period("Q-DEC"))


def totals(df: pd.DataFrame, company: str) -> pd.DataFrame:
    """Per filing: the total amount for its balance date (total, else operating + finance, else the one type)."""
    d = df[df["company"] == company]
    rows = []
    for (period, accn), g in d.groupby(["period", "accession"], sort=False):
        by = dict(zip(g["lease_type"], g["value"]))
        value = by["total"] if "total" in by else sum(by.values())
        rows.append((calendar_period(period), float(value), g["known_from"].iloc[0]))
    return pd.DataFrame(rows, columns=["period", "value", "known_from"])


def series_frame(df: pd.DataFrame, company: str) -> pd.DataFrame:
    """Release-dated rows (period, value, known_from): a later filing's different amount for the same balance
    date is a new version; a repeat adds no row."""
    t = totals(df, company).sort_values("known_from", kind="stable")
    out, last = [], {}
    for p, v, kf in t.itertuples(index=False):
        if p in last and abs(last[p] - v) < 0.5:
            continue
        last[p] = v
        out.append((p, v, kf))
    res = pd.DataFrame(out, columns=["period", "value", "known_from"])
    return res.drop_duplicates(["period", "known_from"], keep="last").reset_index(drop=True)
