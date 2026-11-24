"""Document corpus and candidate sentences for the useful-life extraction (track P2a).

Documents (docs/kallor/nyttjandeperioder.md, "Korpus"), from SEC EDGAR only:
- every 10-K, 10-K/A, 10-KT, 10-Q and 10-Q/A primary document filed 2018-01-01 onward;
- every 8-K with Item 2.02 (results) filed in the same window, with its EX-99 exhibits (types from the index page);
for Microsoft, Alphabet, Amazon, Meta, Oracle and CoreWeave (CoreWeave from its first filing after the 2025 IPO).

Candidate sentences (locked before the coding): a sentence names an asset class that can hold servers or network
equipment (CLASS_RE) and either a useful life / depreciation (LIFE_RE) or a number of years (YEARS_RE), or it names a
change in estimate together with depreciation. Long "sentences" (tables flattened to one line) are kept. The agent
reads every candidate and codes the values into curated/useful_lives.csv; sentences stay in data/raw (gitignored).
The supplementary reading set (supplementary(), registered after review R15) adds the sentences the candidate rule
missed; candidates plus that set hold every coded row.

Text = tsmc_sec.to_text(document), sentences = guidance_capex.sentences(text); locator "sentence #k" counts from 0.
known_from of a document = its EDGAR filingDate (acceptanceDateTime kept).

    python -m ai_tracker.sources.useful_lives_corpus [--companies msft,googl] [--first 2018-01-01]
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass

import pandas as pd

from ai_tracker import config, http
from ai_tracker.sources import guidance_capex, tsmc_sec

SOURCE = "useful_lives"
FIRST = "2018-01-01"
LAST = "2026-11-24"
CIKS = {"msft": 789019, "googl": 1652044, "amzn": 1018724, "meta": 1326801, "orcl": 1341439, "crwv": 1769628}
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SUBMISSIONS_FILE = "https://data.sec.gov/submissions/{name}"
INDEX = "https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{acc}-index.htm"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{doc}"
PERIODIC = ("10-K", "10-Q")  # incl. 10-K/A, 10-KT, 10-Q/A
CANDIDATES_DIR = config.REPO / "data" / "raw" / "useful_lives_candidates"  # gitignored

CLASS_RE = re.compile(
    r"(?i)\bservers?\b|\bnetwork(?:ing)?\s+(?:equipment|assets|infrastructure|gear)|\bcomputer\s+(?:equipment|hardware)|"
    r"\btechnical\s+infrastructure|\binformation\s+technology\b|\btechnology\s+(?:equipment|infrastructure|assets)|"
    r"\bdata\s*cent(?:er|re)\s+equipment")
LIFE_RE = re.compile(r"(?i)useful\s+li(?:fe|ves)|depreciable\s+li(?:fe|ves)|estimated\s+li(?:fe|ves)|"
                     r"depreciat\w*\s+(?:over|using|on)")
NUMWORD = r"(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty)"
YEARS_RE = re.compile(rf"(?i)\b{NUMWORD}(?:\s+and\s+(?:a|one)[\s-]half)?(?:\s*(?:-|–|—|to)\s*{NUMWORD})?\s*years?\b")
ESTIMATE_RE = re.compile(r"(?i)change\w*\s+in\s+(?:accounting\s+)?estimates?")
DEPRECIATION_RE = re.compile(r"(?i)depreciat")

# Supplementary reading set (interpretation 1 of docs/kallor/nyttjandeperioder.md, registered 2026-11-24 after R15).
# The locked candidate rule missed effect sentences (no asset class with years) and two class names, so the agent
# also read (a) the WINDOW sentences after each candidate that describes a change and (b) every other sentence with
# a useful life and a number of years. Written as code after the coding, so that the reading set can be rebuilt: it
# holds every coded row that is not a candidate. The candidate rule itself is unchanged.
CHANGE_RE = re.compile(r"(?i)change\w*\s+in\s+(?:accounting\s+)?estimates?|"
                       r"(?:chang|increas|extend|lengthen|shorten|reduc|decreas|revis)\w*\s+(?:\w+\s+){0,6}?"
                       r"(?:estimated\s+)?(?:useful|depreciable)\s+li(?:fe|ves)")
LIFE_SCAN_RE = re.compile(r"(?i)useful\s+li|depreciable\s+li|estimated\s+useful\s+life")
WINDOW = 5


@dataclass
class Document:
    company: str
    doc_type: str  # "10-K", "10-Q", "10-K/A", ..., "8-K EX-99.1", ...
    url: str
    accession: str
    filed: str  # YYYY-MM-DD = known_from
    accepted: str  # EDGAR acceptanceDateTime
    form: str
    items: str
    report_date: str  # EDGAR reportDate (balance date for 10-K/10-Q; period reported for an 8-K Item 2.02)


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


def in_scope(f: dict, first: str = FIRST, last: str = LAST) -> bool:
    if not first <= f["filed"] <= last:
        return False
    return f["form"].startswith(PERIODIC) or (f["form"].startswith("8-K") and "2.02" in f["items"])


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


def exhibits(company: str, accession: str) -> list[tuple[str, str]]:
    cik, folder = CIKS[company], accession.replace("-", "")
    page = fetch_bytes(INDEX.format(cik=cik, folder=folder, acc=accession)).decode("utf-8", errors="replace")
    return parse_index(page)


def documents(company: str, first: str = FIRST, last: str = LAST) -> list[Document]:
    docs = []
    for f in submissions(company):
        if not in_scope(f, first, last):
            continue
        base = dict(company=company, accession=f["accession"], filed=f["filed"], accepted=f["accepted"],
                    form=f["form"], items=f["items"], report_date=f["report_date"])
        if f["form"].startswith(PERIODIC):
            url = ARCHIVE.format(cik=CIKS[company], folder=f["accession"].replace("-", ""), doc=f["primary"])
            docs.append(Document(doc_type=f["form"], url=url, **base))
        else:
            for typ, url in exhibits(company, f["accession"]):
                if typ.startswith("EX-99") and not url.lower().endswith(".txt"):
                    docs.append(Document(doc_type=f"8-K {typ}", url=url, **base))
    return docs


def is_candidate(sentence: str) -> bool:
    """See the module docstring (locked rule)."""
    if CLASS_RE.search(sentence) and (LIFE_RE.search(sentence) or YEARS_RE.search(sentence)):
        return True
    return bool(ESTIMATE_RE.search(sentence) and DEPRECIATION_RE.search(sentence))


def candidates(doc: Document, text: str) -> list[dict]:
    out = []
    for k, s in enumerate(guidance_capex.sentences(text)):
        if is_candidate(s):
            out.append({**asdict(doc), "k": k, "sha256": guidance_capex.sentence_hash(s), "length": len(s),
                        "sentence": s})
    return out


def supplementary(doc: Document, text: str) -> list[dict]:
    """Non-candidate sentences of the supplementary reading set; "why" is after_change and/or life_scan."""
    sents = guidance_capex.sentences(text)
    cand = {k for k, s in enumerate(sents) if is_candidate(s)}
    why: dict[int, list[str]] = {}
    for k in sorted(cand):
        if CHANGE_RE.search(sents[k]):
            for j in range(k + 1, min(k + 1 + WINDOW, len(sents))):
                if j not in cand and "after_change" not in why.setdefault(j, []):
                    why[j].append("after_change")
    for k, s in enumerate(sents):
        if k not in cand and LIFE_SCAN_RE.search(s) and YEARS_RE.search(s):
            why.setdefault(k, []).append("life_scan")
    return [{**asdict(doc), "k": k, "why": "+".join(why[k]), "sha256": guidance_capex.sentence_hash(sents[k]),
             "length": len(sents[k]), "sentence": sents[k]} for k in sorted(why)]


def build(companies: tuple[str, ...] = tuple(CIKS), first: str = FIRST, last: str = LAST) -> pd.DataFrame:
    """Fetch the corpus (sequentially, http.py rate limits) and write documents.json, candidates.jsonl and
    supplementary.jsonl (the supplementary reading set). Returns the candidates."""
    docs = []
    for c in companies:
        docs += documents(c, first, last)
    docs.sort(key=lambda d: (d.filed, d.company, d.doc_type))
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    (CANDIDATES_DIR / "documents.json").write_text(json.dumps([asdict(d) for d in docs], indent=1))
    rows, extra, failed = [], [], []
    for d in docs:
        try:
            text = text_of(d.url)
        except Exception as exc:  # noqa: BLE001 - reported, not hidden
            failed.append((d.url, type(exc).__name__))
            print(f"FAILED {d.url}: {type(exc).__name__}")
            continue
        rows += candidates(d, text)
        extra += supplementary(d, text)
    for name, out in (("candidates.jsonl", rows), ("supplementary.jsonl", extra)):
        with open(CANDIDATES_DIR / name, "w", encoding="utf-8") as fh:
            for r in out:
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
    print(res.groupby(["company"]).agg(documents=("url", "nunique"), candidates=("k", "size"),
                                       unique=("sha256", "nunique")).to_string())


if __name__ == "__main__":
    main()
