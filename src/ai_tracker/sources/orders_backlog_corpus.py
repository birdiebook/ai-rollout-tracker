"""Document corpus and candidate sentences for the orders and backlog extraction (track S3).

Documents (docs/kallor/order_orderstock.md, "Korpus"), from SEC EDGAR only: the press release exhibit of every 8-K and
8-K/A with Item 2.02 filed 2022-01-01..2026-11-25 (EX-99.1, or EX-99 when the filing has no EX-99.1), for Vertiv,
GE Vernova, Eaton, Dell, Digital Realty and Equinix. Gap rule: a 10-Q/10-K whose quarter has no Item 2.02 8-K between
the balance date and the periodic filing takes the 8-K with an EX-99 exhibit filed on that day or up to seven days
before it (GE Vernova 2025-07-23 is tagged Item 2.01 in EDGAR).

Candidate sentences (locked before the coding): a measure word (MEASURE_RE) and a digit. The reading set is the
candidates plus the sentence after each candidate. Text = tsmc_sec.to_text(exhibit), sentences =
guidance_capex.sentences(text); locator "sentence #k" counts from 0. known_from = EDGAR filingDate.

    python -m ai_tracker.sources.orders_backlog_corpus [--companies vrt,gev] [--first 2022-01-01]
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass

import pandas as pd

from ai_tracker import config, http
from ai_tracker.sources import guidance_capex, tsmc_sec

SOURCE = "orders_backlog"
FIRST = "2022-01-01"
LAST = "2026-11-25"
CIKS = {"vrt": 1674101, "gev": 1996810, "etn": 1551182, "dell": 1571996, "dlr": 1297996, "eqix": 1101239}
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SUBMISSIONS_FILE = "https://data.sec.gov/submissions/{name}"
INDEX = "https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{acc}-index.htm"
PERIODIC = ("10-K", "10-Q")
GAP_DAYS = 7
CANDIDATES_DIR = config.REPO / "data" / "raw" / "orders_candidates"  # gitignored
PAUSE = 0.3  # seconds between documents in bulk loops (several tracks share sec.gov's rate limit)

MEASURE_RE = re.compile(
    r"(?i)\border(?:s|ed|ing)?\b|\bbookings?\b|\bbacklog\b|\bbook[\s-]+to[\s-]+bill\b|\bslot\s+reservations?\b|"
    r"\breservation\s+agreements?\b|\bsigned\b|\bleases?\b|\bnot[\s-]+yet[\s-]+commenced\b|\bpipeline\b")
DIGIT_RE = re.compile(r"\d")


@dataclass
class Document:
    company: str
    url: str
    accession: str
    filed: str  # YYYY-MM-DD = known_from
    accepted: str  # EDGAR acceptanceDateTime
    form: str  # 8-K or 8-K/A
    items: str
    exhibit: str  # EX-99.1 or EX-99
    report_date: str
    via: str  # "item_2.02" or "gap_rule"


def _cached(url: str):
    name = http.raw_path(SOURCE, url).name
    hits = sorted((http.RAW_DIR / SOURCE).glob(f"*/{name}"))
    return hits[-1] if hits else None


def fetch_bytes(url: str, reuse: bool = True) -> bytes:
    """A document's bytes; an archived SEC document never changes, so an earlier raw copy is reused."""
    path = _cached(url) if reuse else None
    return path.read_bytes() if path else http.get(url, SOURCE).content


def text_of(url: str, reuse: bool = True) -> str:
    """Plain text (tsmc_sec.to_text) of an exhibit: the text that locators count sentences in."""
    return tsmc_sec.to_text(fetch_bytes(url, reuse).decode("utf-8", errors="replace"))


def submissions(company: str) -> list[dict]:
    """Every filing in EDGAR's submissions API for the company (recent block plus the older files)."""
    cik = CIKS[company]
    sub = http.get(SUBMISSIONS.format(cik=cik), SOURCE).json()
    blocks = [sub["filings"]["recent"]] + [http.get(SUBMISSIONS_FILE.format(name=f["name"]), SOURCE).json()
                                           for f in sub["filings"].get("files", [])]
    out = {}
    for b in blocks:
        for i, acc in enumerate(b["accessionNumber"]):
            out[acc] = {"form": b["form"][i], "filed": b["filingDate"][i], "accession": acc, "items": b["items"][i],
                        "accepted": b["acceptanceDateTime"][i], "primary": b["primaryDocument"][i],
                        "report_date": b["reportDate"][i]}
    return sorted(out.values(), key=lambda f: (f["filed"], f["accepted"]))


def is_results_8k(f: dict) -> bool:
    return f["form"] in ("8-K", "8-K/A") and "2.02" in (f["items"] or "").split(",")


def select_filings(filings: list[dict], first: str = FIRST, last: str = LAST) -> list[tuple[dict, str]]:
    """(filing, via) of the corpus: every results 8-K in the window, plus the gap rule (module doc)."""
    in_window = [f for f in filings if first <= f["filed"] <= last]
    chosen = {f["accession"]: (f, "item_2.02") for f in in_window if is_results_8k(f)}
    results_days = sorted(f["filed"] for f in in_window if is_results_8k(f))
    for p in in_window:
        if not p["form"].startswith(PERIODIC) or not p["report_date"]:
            continue
        if any(p["report_date"] < d <= p["filed"] for d in results_days):
            continue
        lo = (pd.Timestamp(p["filed"]) - pd.Timedelta(days=GAP_DAYS)).strftime("%Y-%m-%d")
        for f in in_window:
            if f["form"] in ("8-K", "8-K/A") and lo <= f["filed"] <= p["filed"] and f["accession"] not in chosen:
                chosen[f["accession"]] = (f, "gap_rule")
    return sorted(chosen.values(), key=lambda t: (t[0]["filed"], t[0]["accepted"]))


_ROW_RE = re.compile(r'(?s)<tr[^>]*>\s*<td[^>]*>\d+</td>\s*<td[^>]*>[^<]*</td>\s*<td[^>]*><a href="([^"]+)"[^>]*>'
                     r'[^<]*</a>.*?</td>\s*<td[^>]*>([^<]*)</td>')


def parse_index(page: str) -> list[tuple[str, str]]:
    """(document type, archive URL) of a filing's .htm/.txt documents, from its index page."""
    out = []
    for href, typ in _ROW_RE.findall(page):
        href = href.replace("/ix?doc=", "")
        if href.lower().endswith((".htm", ".html", ".txt")):
            out.append((typ.strip(), "https://www.sec.gov" + href))
    return out


def release_exhibit(exhibits: list[tuple[str, str]]) -> tuple[str, str] | None:
    """The press release: EX-99.1, else the EX-99 exhibit when there is no EX-99.1 (never EX-99.2 or later)."""
    htm = [(t, u) for t, u in exhibits if not u.lower().endswith(".txt")]
    for t, u in htm:
        if t == "EX-99.1":
            return t, u
    plain = [(t, u) for t, u in htm if t == "EX-99"]
    return plain[0] if plain else None


def documents(company: str, first: str = FIRST, last: str = LAST, pause: float = PAUSE) -> list[Document]:
    docs = []
    cik = CIKS[company]
    for f, via in select_filings(submissions(company), first, last):
        folder = f["accession"].replace("-", "")
        page = fetch_bytes(INDEX.format(cik=cik, folder=folder, acc=f["accession"])).decode("utf-8", errors="replace")
        ex = release_exhibit(parse_index(page))
        time.sleep(pause)
        if ex is None:
            print(f"no press release exhibit: {company} {f['accession']}")
            continue
        docs.append(Document(company=company, url=ex[1], accession=f["accession"], filed=f["filed"],
                             accepted=f["accepted"], form=f["form"], items=f["items"], exhibit=ex[0],
                             report_date=f["report_date"], via=via))
    return docs


_MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?"
# A dateline: a date after a dash, bracket, parenthesis, comma or capitalised word (the state) and before a dash,
# "/PRNewswire" or "Full story" ("COLUMBUS, Ohio [April 27, 2022] –", "COLUMBUS, Ohio October 26, 2022 –", "CAMBRIDGE, Mass., (Apr. 25, 2024) –", "DUBLIN--(BUSINESS
# WIRE)--February 4, 2022--", "REDWOOD CITY, Calif., Feb. 16, 2022 /PRNewswire/", "Dallas, TX — July 24, 2025 —").
DATELINE_RE = re.compile(rf"(?:[—–\-(\[,]|\b[A-Z][a-z]+)\s*({_MONTH}\s+\d{{1,2}},\s+\d{{4}})\s*[)\]]?\s*(?:[—–\-]|/\s*PRNewswire|Full story)")


def dateline(text: str) -> str | None:
    """The press release's dateline as YYYY-MM-DD: the first dateline-shaped date in the exhibit text, or None."""
    m = DATELINE_RE.search(re.sub(r"\s+", " ", text))
    if not m:
        return None
    raw = m.group(1).replace(".", "").replace("Sept ", "Sep ")
    try:
        return pd.Timestamp(raw).strftime("%Y-%m-%d")
    except ValueError:
        return None


def is_candidate(sentence: str) -> bool:
    """See the module docstring (locked rule)."""
    return bool(MEASURE_RE.search(sentence) and DIGIT_RE.search(sentence))


def reading_set(text: str) -> dict[int, str]:
    """Sentence number -> "candidate" or "after" (the sentence after a candidate that is not one itself)."""
    sents = guidance_capex.sentences(text)
    out: dict[int, str] = {}
    for k, s in enumerate(sents):
        if is_candidate(s):
            out[k] = "candidate"
    for k in sorted(out):
        if out[k] == "candidate" and k + 1 < len(sents):
            out.setdefault(k + 1, "after")
    return dict(sorted(out.items()))


def build(companies: tuple[str, ...] = tuple(CIKS), first: str = FIRST, last: str = LAST) -> pd.DataFrame:
    """Fetch the corpus (sequentially) and write documents.json and reading.jsonl. Returns the reading set."""
    docs = []
    for c in companies:
        docs += documents(c, first, last)
    docs.sort(key=lambda d: (d.filed, d.company))
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    (CANDIDATES_DIR / "documents.json").write_text(json.dumps([asdict(d) for d in docs], indent=1))
    rows, failed = [], []
    for d in docs:
        try:
            text = text_of(d.url)
        except Exception as exc:  # noqa: BLE001 - reported, not hidden
            failed.append((d.url, type(exc).__name__))
            print(f"FAILED {d.url}: {type(exc).__name__}")
            continue
        sents = guidance_capex.sentences(text)
        for k, why in reading_set(text).items():
            rows.append({**asdict(d), "k": k, "why": why, "sha256": guidance_capex.sentence_hash(sents[k]),
                         "length": len(sents[k]), "sentence": sents[k]})
        time.sleep(PAUSE)
    with open(CANDIDATES_DIR / "reading.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    (CANDIDATES_DIR / "failed.json").write_text(json.dumps(failed, indent=1))
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--companies", default=",".join(CIKS))
    ap.add_argument("--first", default=FIRST)
    ap.add_argument("--last", default=LAST)
    a = ap.parse_args()
    res = build(tuple(a.companies.split(",")), a.first, a.last)
    if res.empty:
        print("no candidates")
        return
    print(res.groupby(["company", "why"]).agg(documents=("url", "nunique"), sentences=("k", "size"),
                                              unique=("sha256", "nunique")).to_string())


if __name__ == "__main__":
    main()
