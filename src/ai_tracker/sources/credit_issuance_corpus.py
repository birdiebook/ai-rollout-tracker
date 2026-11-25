"""Document corpus for the spread at issuance (track KR1): EDGAR offering documents and their line lists.

Corpus (docs/kallor/kredit_emission.md, "Korpus", locked before the coding): the primary document of every FWP,
424B2 and 424B5 filed 2020-01-01 to 2026-11-25 by Microsoft, Alphabet, Amazon, Meta, Oracle and CoreWeave.
424B3/424B4, S-3/S-3ASR, S-4 and 8-K are not in the corpus.

Text and locator. A document is turned into a line list (`lines`): every table row becomes one line with its cells
joined by " | ", every block element (paragraph, heading, line break) its own line, whitespace collapsed, empty
cells and empty lines dropped. A tranche's locator is `lines #a-#b` (its block in that list, counted from 0), plus
` col #j` when the tranches share one table: in a keyed table (every value lists the tranches by key, "2030 Notes:
...") j is the tranche's key among the keys of the principal rows, from 0 (interpretation 2 in the doc), and in a table
with one column per tranche it is the value column. `block_hash` is the SHA-256 of the block.

`kind()` tells a final document from a preliminary supplement or another document (the rule in the doc: final terms =
principal, coupon or rate, maturity and a public offering price). The build uses it as the filter for what is coded
(sources/credit_issuance.rows_from_documents), and every document it drops is listed with the reason.

    python -m ai_tracker.sources.credit_issuance_corpus [--companies orcl,meta] [--first 2020-01-01]

writes data/raw/credit_issuance_corpus/documents.json (every document with its kind) and prints a summary.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
from dataclasses import asdict, dataclass

from ai_tracker import config, http

SOURCE = "credit_issuance"
FIRST = "2020-01-01"
LAST = "2026-11-25"
CIKS = {"msft": 789019, "googl": 1652044, "amzn": 1018724, "meta": 1326801, "orcl": 1341439, "crwv": 1769628}
FORMS = ("FWP", "424B2", "424B5")
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SUBMISSIONS_FILE = "https://data.sec.gov/submissions/{name}"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{doc}"
CORPUS_DIR = config.REPO / "data" / "raw" / "credit_issuance_corpus"  # gitignored
BULK_SLEEP = 0.3  # seconds between documents in a bulk loop (several tracks share sec.gov's rate limit)


@dataclass
class Document:
    company: str
    form: str
    url: str
    accession: str
    filed: str  # EDGAR filingDate = known_from
    accepted: str  # EDGAR acceptanceDateTime


# ------------------------------------------------------------------ text


def _cell(c: str) -> str:
    return re.sub(r"\s+", " ", c).strip()


def normalize(line: str) -> str:
    """One line of the line list: cells stripped, empty cells dropped, a lone currency sign joined to the next cell."""
    cells = [_cell(c) for c in line.split("|")]
    cells = [c for c in cells if c]
    out: list[str] = []
    for c in cells:
        if out and out[-1] in ("$", "€", "£", "US$"):
            out[-1] = out[-1] + c
        elif out and c == "%":
            out[-1] = out[-1] + c
        else:
            out.append(c)
    return " | ".join(out)


_BLOCK = re.compile(r"(?i)<(?:/?(?:p|div|tr|li|h[1-6]|table|tbody|thead|tfoot|center|title)\b[^>]*|br\b[^>]*)>")


def _row(m: re.Match) -> str:
    """A table row as one line: block tags inside a cell become spaces, cells are joined by ' | '."""
    r = _BLOCK.sub(" ", m.group(0))
    return "\n" + re.sub(r"(?i)</t[dh]\s*>", " | ", r) + "\n"


def lines(raw: str) -> list[str]:
    """The line list of an HTML (or plain text) document; locators count lines in this list from 0."""
    t = re.sub(r"\s+", " ", raw)  # line breaks in the source are only layout
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", t)
    t = re.sub(r"(?s)<!--.*?-->", " ", t)
    t = re.sub(r"(?is)<tr\b.*?</tr\s*>", _row, t)
    t = _BLOCK.sub("\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t).replace("\xa0", " ").replace("​", " ")
    out = []
    for line in t.split("\n"):
        n = normalize(line)
        if n:
            out.append(n)
    return out


def block_hash(block: list[str]) -> str:
    """SHA-256 of a block of lines (each normalized, joined by newlines)."""
    return hashlib.sha256("\n".join(normalize(x) for x in block).encode("utf-8")).hexdigest()


def block_at(doc_lines: list[str], locator: str) -> tuple[list[str], int | None]:
    """(lines a..b, column or None) for a locator 'lines #a-#b[ col #j]'."""
    m = re.fullmatch(r"lines #(\d+)-#(\d+)(?: col #(\d+))?", locator)
    if not m:
        raise ValueError(f"bad locator {locator!r}")
    a, b = int(m.group(1)), int(m.group(2))
    return doc_lines[a:b + 1], (int(m.group(3)) if m.group(3) else None)


# ------------------------------------------------------------------ document kind

PRELIM_RE = re.compile(r"(?i)subject\s+to\s+completion")
PRICE_RE = re.compile(r"(?i)price\s+to\s+(?:the\s+)?public|public\s+offering\s+price|re-?offer\s+price|issue\s+price|"
                      r"initial\s+price")
MATURITY_RE = re.compile(r"(?i)maturity|due\s+20\d\d")
COUPON_RE = re.compile(r"(?i)coupon|interest\s+rate|\d\.\d{2,3}%\s+notes|floating\s+rate\s+notes")
PRINCIPAL_RE = re.compile(r"(?i)principal\s+amount|aggregate\s+principal|size")
EQUITY_RE = re.compile(r"(?i)common\s+stock|class\s+a\s+common|shares\s+of|convertible|preferred\s+stock")


def kind(doc_lines: list[str]) -> str:
    """'final' (states final terms), 'preliminary' (subject to completion) or 'other' (no final debt terms).

    The build codes only 'final' documents and lists the others with the reason (curated/credit_issuance_skipped.csv);
    R20 checked that it keeps every debt term sheet in the corpus. The agent still reads every document it codes."""
    head = "\n".join(doc_lines[:80])
    text = "\n".join(doc_lines)
    if PRELIM_RE.search(head):
        return "preliminary"
    has_terms = all(r.search(text) for r in (PRICE_RE, MATURITY_RE, COUPON_RE, PRINCIPAL_RE))
    if not has_terms or (EQUITY_RE.search(head) and not re.search(r"(?i)\bnotes?\b", head)):
        return "other"
    return "final"


# ------------------------------------------------------------------ EDGAR


def _cached(url: str):
    name = http.raw_path(SOURCE, url).name
    hits = sorted((http.RAW_DIR / SOURCE).glob(f"*/{name}"))
    return hits[-1] if hits else None


def fetch_bytes(url: str, reuse: bool = True) -> bytes:
    """A document's bytes; an archived SEC document never changes, so an earlier raw copy is reused."""
    path = _cached(url) if reuse else None
    return path.read_bytes() if path else http.get(url, SOURCE).content


def doc_lines(url: str, reuse: bool = True) -> list[str]:
    return lines(fetch_bytes(url, reuse).decode("utf-8", errors="replace"))


def submissions(company: str, source: str = SOURCE) -> list[dict]:
    """Every filing in EDGAR's submissions API for the company (recent block plus the older files)."""
    cik = CIKS[company]
    sub = http.get(SUBMISSIONS.format(cik=cik), source).json()
    blocks = [sub["filings"]["recent"]] + [http.get(SUBMISSIONS_FILE.format(name=f["name"]), source).json()
                                           for f in sub["filings"].get("files", [])]
    out = {}
    for b in blocks:
        for i, acc in enumerate(b["accessionNumber"]):
            out[acc] = {"form": b["form"][i], "filed": b["filingDate"][i], "accession": acc,
                        "accepted": b["acceptanceDateTime"][i], "primary": b["primaryDocument"][i]}
    return sorted(out.values(), key=lambda f: (f["filed"], f["accepted"]))


def in_scope(f: dict, first: str = FIRST, last: str = LAST) -> bool:
    return first <= f["filed"] <= last and f["form"] in FORMS


def documents(company: str, first: str = FIRST, last: str = LAST, subs: list[dict] | None = None) -> list[Document]:
    subs = submissions(company) if subs is None else subs
    return [Document(company=company, form=f["form"], accession=f["accession"], filed=f["filed"],
                     accepted=f["accepted"],
                     url=ARCHIVE.format(cik=CIKS[company], folder=f["accession"].replace("-", ""), doc=f["primary"]))
            for f in subs if in_scope(f, first, last)]


def build(companies: tuple[str, ...] = tuple(CIKS), first: str = FIRST, last: str = LAST) -> list[dict]:
    """Fetch the corpus (sequentially, BULK_SLEEP between documents) and write documents.json with each kind."""
    out = []
    for c in companies:
        for d in documents(c, first, last):
            cached = _cached(d.url) is not None
            try:
                ls = doc_lines(d.url)
                k = kind(ls)
            except Exception as exc:  # noqa: BLE001 - reported, not hidden
                ls, k = [], f"failed: {type(exc).__name__}"
            out.append({**asdict(d), "kind": k, "n_lines": len(ls)})
            if not cached:
                time.sleep(BULK_SLEEP)
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    (CORPUS_DIR / "documents.json").write_text(json.dumps(out, indent=1))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--companies", default=",".join(CIKS))
    ap.add_argument("--first", default=FIRST)
    ap.add_argument("--last", default=LAST)
    a = ap.parse_args()
    docs = build(tuple(a.companies.split(",")), a.first, a.last)
    from collections import Counter

    for (co, form, k), n in sorted(Counter((d["company"], d["form"], d["kind"]) for d in docs).items()):
        print(f"{co:6s} {form:6s} {k:12s} {n}")


if __name__ == "__main__":
    main()
