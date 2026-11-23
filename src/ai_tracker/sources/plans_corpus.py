"""Document corpus and candidate sentences for multi-year plans (step 2, track D1).

Documents, 2022 onward:
- SEC EDGAR, Microsoft, Alphabet, Amazon, Meta, Oracle and CoreWeave: every 8-K with Item 2.02 (results), 7.01 or
  8.01, with its EX-99 exhibits and main document (types read from the filing index page); every 10-Q / 10-K
  primary document; for CoreWeave also its S-1, S-1/A and 424B prospectuses;
- microsoft.com: the earnings-call page of each fiscal quarter.
Other IR hosts are refused by the proxy (see docs/kallor/planer.md); nothing is worked around.

Candidate selection is deliberately broad (lesson R2-F1: a filter on forward-looking words missed a present-tense
sentence). A sentence is a candidate when it has a plan keyword (KEYWORD_RE) and any of: a dollar amount, a power
figure (MW/GW), a year after the document's year or a multi-year phrase, or a forward-looking word together with a
capex/capacity word. The agent reads every candidate and codes values into curated/plans.csv. Sentences are kept
only in data/raw (gitignored).

known_from of a document: the EDGAR filingDate (acceptanceDateTime kept); for a Microsoft call page, the filing date
of the 8-K Item 2.02 with the same quarter's results (the call is held the same afternoon).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass

import pandas as pd

from ai_tracker import config, http
from ai_tracker.sources import guidance_capex, tsmc_sec

SOURCE = "plans"
FIRST = "2022-01-01"
CIKS = {"msft": 789019, "googl": 1652044, "amzn": 1018724, "meta": 1326801, "orcl": 1341439, "crwv": 1769628}
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SUBMISSIONS_FILE = "https://data.sec.gov/submissions/{name}"
INDEX = "https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{acc}-index.htm"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{doc}"
MSFT_CALL = "https://www.microsoft.com/en-us/investor/events/fy-{fy}/earnings-fy-{fy}-q{q}"
ITEMS = ("2.02", "7.01", "8.01")
PROSPECTUS_FORMS = ("S-1", "S-1/A", "424B")  # CoreWeave's IPO documents
CANDIDATES_DIR = config.REPO / "data" / "raw" / "plans_candidates"  # gitignored

KEYWORD_RE = re.compile(
    r"(?i)(capex|capital expenditure|capital spending|capital investment|infrastructure|data ?cent(?:er|re)s?|"
    r"capacity|\bpower\b|gigawatts?|megawatts?|\d\s?GW\b|\d\s?MW\b|\bGW\b|\bMW\b|backlog|"
    r"remaining performance obligation|\bRPO\b|commitments?|committed|build[- ]?outs?|\bcompute\b|"
    r"invest\w*\s+(?:\S+\s+){0,6}?in\s+(?:\S+\s+){0,4}?(?:AI|artificial intelligence|infrastructure|data ?cent|"
    r"datacenter|capacity|compute|cloud))")
DOLLAR_RE = re.compile(r"\$\s?\d")
POWER_RE = re.compile(r"(?i)\d[\d.,]*\s*(?:GW|MW|gigawatts?|megawatts?)\b")
MULTIYEAR_RE = re.compile(
    r"(?i)(next (?:\w+ )?(?:two|three|four|five|six|seven|eight|nine|ten|several|few|\d+) years|multi-?year|"
    r"through (?:fiscal )?20\d\d|by (?:the end of )?(?:fiscal )?(?:year )?20\d\d|coming years|over time|"
    r"years? to come)")
FORWARD_RE = re.compile(r"(?i)\b(expect\w*|anticipat\w*|plan\w*|will|intend\w*|target\w*|on track|guid\w*|outlook)\b")
CAPEX_CAPACITY_RE = re.compile(r"(?i)(capex|capital expenditure|capital spending|capital investment|capacity|"
                               r"gigawatt|megawatt|\bGW\b|\bMW\b|data ?cent|infrastructure)")
YEAR_RE = re.compile(r"\b(20[2-4]\d)\b")


@dataclass
class Document:
    company: str
    doc_type: str  # "8-K EX-99.1", "8-K", "10-Q", "10-K", "S-1", "424B4", "call"
    url: str
    accession: str  # "" for a call page
    filed: str  # YYYY-MM-DD = known_from
    accepted: str  # EDGAR acceptanceDateTime ("" for a call page)
    form: str
    items: str
    label: str = ""  # e.g. "FY2026 Q1" for a Microsoft call


def _cached(url: str):
    name = http.raw_path(SOURCE, url).name
    hits = sorted((http.RAW_DIR / SOURCE).glob(f"*/{name}"))
    return hits[-1] if hits else None


def fetch_bytes(url: str, reuse: bool = True) -> bytes:
    """A document's bytes; an archived SEC document never changes, so an earlier raw copy is reused."""
    path = _cached(url) if reuse else None
    return path.read_bytes() if path else http.get(url, SOURCE).content


def text_of(url: str, reuse: bool = True) -> str:
    """Plain text (tsmc_sec.to_text) of a document: the text that locators count sentences in."""
    return tsmc_sec.to_text(fetch_bytes(url, reuse).decode("utf-8", errors="replace"))


def filings(company: str, first: str = FIRST) -> list[dict]:
    cik = CIKS[company]
    sub = http.get(SUBMISSIONS.format(cik=cik), SOURCE).json()
    blocks = [sub["filings"]["recent"]] + [http.get(SUBMISSIONS_FILE.format(name=f["name"]), SOURCE).json()
                                           for f in sub["filings"].get("files", [])]
    out = {}
    for b in blocks:
        for form, filed, acc, items, accepted, doc in zip(b["form"], b["filingDate"], b["accessionNumber"],
                                                         b["items"], b["acceptanceDateTime"], b["primaryDocument"]):
            if filed >= first:
                out[acc] = {"form": form, "filed": filed, "accession": acc, "items": items, "accepted": accepted,
                            "primary": doc}
    return sorted(out.values(), key=lambda f: (f["filed"], f["accepted"]))


_ROW_RE = re.compile(r'(?s)<tr[^>]*>\s*<td[^>]*>\d+</td>\s*<td[^>]*>[^<]*</td>\s*<td[^>]*><a href="([^"]+)"[^>]*>'
                     r'[^<]*</a>.*?</td>\s*<td[^>]*>([^<]*)</td>')


def exhibits(company: str, accession: str) -> list[tuple[str, str]]:
    """(document type, archive URL) of a filing's .htm documents, from its index page."""
    cik, folder = CIKS[company], accession.replace("-", "")
    page = fetch_bytes(INDEX.format(cik=cik, folder=folder, acc=accession)).decode("utf-8", errors="replace")
    out = []
    for href, typ in _ROW_RE.findall(page):
        href = href.replace("/ix?doc=", "")
        if href.lower().endswith((".htm", ".html")):
            out.append((typ.strip(), "https://www.sec.gov" + href))
    return out


def is_prospectus(form: str) -> bool:
    return form in ("S-1", "S-1/A") or form.startswith("424B")


def sec_documents(company: str, first: str = FIRST) -> list[Document]:
    docs = []
    for f in filings(company, first):
        form = f["form"]
        url = ARCHIVE.format(cik=CIKS[company], folder=f["accession"].replace("-", ""), doc=f["primary"])
        if form.startswith(("10-Q", "10-K")) or (company == "crwv" and is_prospectus(form)):
            docs.append(Document(company, form, url, f["accession"], f["filed"], f["accepted"], form, f["items"]))
        elif form.startswith("8-K") and any(i in f["items"] for i in ITEMS):
            for typ, u in exhibits(company, f["accession"]):
                if typ.startswith("EX-99") or typ.startswith("8-K"):
                    dt = form if typ.startswith("8-K") else f"8-K {typ}"
                    docs.append(Document(company, dt, u, f["accession"], f["filed"], f["accepted"], form, f["items"]))
    return docs


def msft_call_documents(sec_docs: list[Document]) -> list[Document]:
    """Microsoft's earnings-call pages, dated by the 8-K Item 2.02 of the same quarter.

    An 8-K with results filed in January / April / July reports fiscal Q2 / Q3 / Q4 of the fiscal year ending in
    that calendar year; one filed in October reports Q1 of the next fiscal year.
    """
    seen, out = set(), []
    for d in sec_docs:
        if d.company != "msft" or "2.02" not in d.items or d.accession in seen:
            continue
        seen.add(d.accession)
        filed = pd.Timestamp(d.filed)
        q = {1: 2, 4: 3, 7: 4, 10: 1}.get(filed.month)
        if q is None:
            continue
        fy = filed.year + (1 if filed.month == 10 else 0)
        out.append(Document("msft", "call", MSFT_CALL.format(fy=fy, q=q), "", d.filed, "", "call", "",
                            label=f"FY{fy} Q{q}"))
    return out


def corpus(companies: tuple[str, ...] = tuple(CIKS), first: str = FIRST) -> list[Document]:
    docs = []
    for c in companies:
        docs += sec_documents(c, first)
    if "msft" in companies:
        docs += msft_call_documents(docs)
    return sorted(docs, key=lambda d: (d.filed, d.company, d.doc_type))


def is_candidate(sentence: str, doc_year: int) -> str | None:
    """Why the sentence is a candidate ('dollar' | 'power' | 'horizon' | 'forward') or None."""
    if not KEYWORD_RE.search(sentence):
        return None
    if DOLLAR_RE.search(sentence):
        return "dollar"
    if POWER_RE.search(sentence):
        return "power"
    if MULTIYEAR_RE.search(sentence) or any(int(y) > doc_year for y in YEAR_RE.findall(sentence)):
        return "horizon"
    if FORWARD_RE.search(sentence) and CAPEX_CAPACITY_RE.search(sentence):
        return "forward"
    return None


MAX_SENTENCE = 1500  # longer "sentences" are tables or bullet lists flattened to one line
WINDOW = 200  # in a long sentence, a keyword needs a dollar/power figure within this many characters


def is_long_candidate(sentence: str) -> str | None:
    """A long sentence (press-release highlight lists, tables) is a candidate when a keyword has a dollar amount
    or a power figure within WINDOW characters (rule change 2026-11-23, docs/kallor/planer.md)."""
    for m in KEYWORD_RE.finditer(sentence):
        near = sentence[max(0, m.start() - WINDOW):m.end() + WINDOW]
        if DOLLAR_RE.search(near) or POWER_RE.search(near):
            return "long"
    return None


def candidates(doc: Document, text: str) -> list[dict]:
    out = []
    year = int(doc.filed[:4])
    for k, s in enumerate(guidance_capex.sentences(text)):
        why = is_long_candidate(s) if len(s) > MAX_SENTENCE else is_candidate(s, year)
        if why:
            out.append({"company": doc.company, "doc_type": doc.doc_type, "url": doc.url, "filed": doc.filed,
                        "accession": doc.accession, "accepted": doc.accepted, "label": doc.label, "k": k,
                        "why": why, "sha256": guidance_capex.sentence_hash(s), "sentence": s})
    return out


def build(companies: tuple[str, ...] = tuple(CIKS), first: str = FIRST, reuse_list: bool = False) -> pd.DataFrame:
    """Fetch the corpus and write the candidates to data/raw/plans_candidates (one JSON line each).

    reuse_list: take the document list from the previous run (documents.json) instead of EDGAR's submissions.
    """
    listing = CANDIDATES_DIR / "documents.json"
    docs = [Document(**d) for d in json.loads(listing.read_text())] if reuse_list and listing.exists() \
        else corpus(companies, first)
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    (CANDIDATES_DIR / "documents.json").write_text(json.dumps([asdict(d) for d in docs], indent=1))
    rows, failed = [], []
    for d in docs:
        try:
            text = text_of(d.url)
        except Exception as exc:  # noqa: BLE001 - reported, not hidden
            failed.append((d.url, type(exc).__name__))
            continue
        rows += candidates(d, text)
    with open(CANDIDATES_DIR / "candidates.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    (CANDIDATES_DIR / "failed.json").write_text(json.dumps(failed, indent=1))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import sys

    res = build(reuse_list="--reuse-list" in sys.argv)
    print(f"documents: {len(json.loads((CANDIDATES_DIR / 'documents.json').read_text()))}")
    print(res.groupby(["company", "why"]).size().to_string())
