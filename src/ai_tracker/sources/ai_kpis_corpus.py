"""Document corpus and candidate sentences for the company AI-KPI extraction (step 2, track B4).

Documents, 2023 onward:
- SEC EDGAR, Microsoft, Alphabet, Amazon, Meta and Nvidia: every 8-K with Item 2.02 (results), 7.01 or 8.01, with
  its EX-99 exhibits (types read from the filing index page), and every 10-Q / 10-K primary document;
- microsoft.com: the earnings-call page of each fiscal quarter (the transcript, prepared remarks and Q&A).
Other companies' IR sites (abc.xyz, ir.aboutamazon.com, investor.atmeta.com, investor.nvidia.com), blog.google and
EDGAR full-text search (efts.sec.gov) are refused by the proxy: see docs/kallor/ai_nyckeltal.md.

Candidate selection is deliberately broad (lesson R2-F1 from the capex review: a filter on forward-looking words
missed a present-tense sentence). A sentence is a candidate when
- it contains a digit and any KPI keyword (KPI_RE: AI, tokens, users, developers, customers, Copilot, Gemini,
  Azure, Google Cloud, AWS, run-rate, backlog, ...), or
- it mentions capacity, supply or constraints together with demand/compute/AI/cloud words (CAPACITY_RE), digit or not.
The agent reads every candidate and codes the values into curated/ai_kpis.csv. Sentences are kept only in data/raw.

known_from of a document: the EDGAR filingDate for SEC documents (acceptanceDateTime kept); for a Microsoft call
page, the filing date of the 8-K Item 2.02 with the same quarter's results (the call is held the same afternoon).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass

import pandas as pd

from ai_tracker import config, http
from ai_tracker.sources import guidance_capex, tsmc_sec

SOURCE = "ai_kpis"
FIRST = "2023-01-01"
CIKS = {"msft": 789019, "googl": 1652044, "amzn": 1018724, "meta": 1326801, "nvda": 1045810}
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SUBMISSIONS_FILE = "https://data.sec.gov/submissions/{name}"
INDEX = "https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{acc}-index.htm"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{doc}"
MSFT_CALL = "https://www.microsoft.com/en-us/investor/events/fy-{fy}/earnings-fy-{fy}-q{q}"
ITEMS = ("2.02", "7.01", "8.01")
CANDIDATES_DIR = config.REPO / "data" / "raw" / "ai_kpis_candidates"  # gitignored

KPI_RE = re.compile(
    r"(?i)\b(AI|A\.I\.|artificial intelligence|gen(?:erative)?\s?AI|tokens?|inference|users?|MAUs?|DAUs?|WAUs?|"
    r"monthly actives?|daily actives?|weekly actives?|developers?|customers?|subscribers?|seats?|"
    r"Copilots?|Gemini|Meta AI|Llama|Foundry|Vertex|Bedrock|Trainium|TPUs?|GPUs?|Blackwell|Hopper|"
    r"Azure|Google Cloud|AWS|cloud|run[- ]rate|annual(?:ized)? revenue|backlog|remaining performance|"
    r"capacity|compute|data ?cent(?:er|re)s?|agents?|agentic|ChatGPT|OpenAI|Anthropic|models?)\b")
CAPACITY_RE = re.compile(
    r"(?i)(capacity|supply|constrain|shortage|short of|sold out|exceed(?:s|ed|ing)? (?:our )?(?:available )?"
    r"(?:supply|capacity)|demand (?:continues to |remains? )?(?:exceed|outpace|ahead)|in balance|"
    r"under-?utiliz|over-?capacity|excess capacity)")
CAPACITY_CONTEXT_RE = re.compile(r"(?i)(demand|AI|cloud|Azure|AWS|compute|GPU|data ?cent|infrastructure|"
                                 r"Blackwell|Hopper|accelerat|capacity)")


@dataclass
class Document:
    company: str
    doc_type: str  # "8-K EX-99.1", "8-K", "10-Q", "10-K", "call"
    url: str
    accession: str  # "" for a call page
    filed: str  # YYYY-MM-DD = known_from
    accepted: str  # EDGAR acceptanceDateTime ("" for a call page)
    form: str
    items: str
    label: str = ""  # e.g. "FY2026 Q1" for a Microsoft call

    @property
    def raw_name(self) -> str:
        return http.raw_path(SOURCE, self.url).name


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


def sec_documents(company: str, first: str = FIRST) -> list[Document]:
    docs = []
    for f in filings(company, first):
        form = f["form"]
        if form.startswith(("10-Q", "10-K")):
            url = ARCHIVE.format(cik=CIKS[company], folder=f["accession"].replace("-", ""), doc=f["primary"])
            docs.append(Document(company, form, url, f["accession"], f["filed"], f["accepted"], form, f["items"]))
        elif form.startswith("8-K") and any(i in f["items"] for i in ITEMS):
            for typ, url in exhibits(company, f["accession"]):
                if typ.startswith("EX-99") or typ.startswith("8-K"):
                    dt = form if typ.startswith("8-K") else f"8-K {typ}"
                    docs.append(Document(company, dt, url, f["accession"], f["filed"], f["accepted"], form,
                                         f["items"]))
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
            continue  # an 8-K Item 2.02 outside the results months (none seen)
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


def is_candidate(sentence: str) -> str | None:
    """'kpi' | 'capacity' | None (see the module docstring)."""
    if CAPACITY_RE.search(sentence) and CAPACITY_CONTEXT_RE.search(sentence):
        return "capacity"
    if re.search(r"\d", sentence) and KPI_RE.search(sentence):
        return "kpi"
    return None


MAX_SENTENCE = 1500  # longer "sentences" are tables flattened to one line; skipped


def candidates(doc: Document, text: str) -> list[dict]:
    out = []
    for k, s in enumerate(guidance_capex.sentences(text)):
        if len(s) > MAX_SENTENCE:
            continue
        why = is_candidate(s)
        if why:
            out.append({"company": doc.company, "doc_type": doc.doc_type, "url": doc.url, "filed": doc.filed,
                        "label": doc.label, "k": k, "why": why, "sha256": guidance_capex.sentence_hash(s),
                        "sentence": s})
    return out


def build(companies: tuple[str, ...] = tuple(CIKS), first: str = FIRST) -> pd.DataFrame:
    """Fetch the corpus and write the candidates to data/raw/ai_kpis_candidates (one JSON line each)."""
    docs = corpus(companies, first)
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    (CANDIDATES_DIR / "documents.json").write_text(json.dumps([asdict(d) for d in docs], indent=1))
    rows = []
    for d in docs:
        try:
            text = text_of(d.url)
        except Exception as exc:  # noqa: BLE001 - reported, not hidden
            print(f"FAILED {d.url}: {type(exc).__name__}")
            continue
        rows += candidates(d, text)
    df = pd.DataFrame(rows)
    with open(CANDIDATES_DIR / "candidates.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return df


if __name__ == "__main__":
    res = build()
    print(res.groupby(["company", "why"]).size().to_string())
