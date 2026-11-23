"""AI labs' self-reported revenue (track B6): first-party statements only, kept as "rapporterad" series.

None of the frontier labs is a listed company, so there are no audited revenue figures. What exists is what the
labs say about themselves: funding announcements and other posts in their own newsroom, and on-record statements
by the CEO/CFO in the company's own channels. Secondary press reports ("people familiar with the matter") are
never registered; docs/kallor/labbintakter.md lists widely cited secondary figures as excluded.

Pipeline:
1. `discover()` reads a lab's sitemap, fetches every newsroom post through ai_tracker.http (raw copies under
   data/raw/lab_revenue/<date>/) and returns parsed `Post`s (title, datePublished, article:modified_time, body).
2. `candidates()` lists body sentences that mention revenue; the agent reads them and records one row per stated
   figure in curated/lab_revenue.csv (numbers and references only, the sentence's SHA-256, never the text).
Official filings: Anthropic, PBC (CIK 2130357) filed a public S-1 on 2026-10-26 and priced its IPO on 2026-11-19.
Its registration statement defines "Run-Rate Revenue" and states it; those statements are registered too, with
doc_type = the EDGAR form and known_from = the EDGAR filing date. DRS/DRS-A drafts are refused: EDGAR dates them by
the confidential submission, but they became public only later (the dates would leak). The S-1's GAAP revenue is
audited/reviewed accounting, not a self-reported figure, and belongs in the SEC pipeline, never in these series.

3. `verify()` re-fetches each row's document and checks that the sentence at the locator still hashes to the stored
   SHA-256 and still contains the stated number; `save_sentences()` keeps the sentences in data/raw (gitignored).

known_from = the post's datePublished (schema.org metadata, equal to the visible date on the page). period = the
date or period the figure refers to (period_end). Measures differ (run-rate revenue, calendar-year revenue,
ARR...) and are never mixed: one series per (lab, scope, measure). The figures are the companies' own,
unaudited, often stated as a bound ("over $5 billion"): `qualifier` keeps that.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ai_tracker import config, http

SOURCE = "lab_revenue"
PATH = config.REPO / "curated" / "lab_revenue.csv"
SENTENCES_DIR = config.REPO / "data" / "raw" / "lab_revenue_sentences"  # gitignored

# lab -> (sitemap URL, URL prefix of its newsroom). Only hosts the network allows are listed; see the doc for
# the labs whose sites were refused (BLOCKED) when the track ran.
SITEMAPS = {
    "anthropic": ("https://www.anthropic.com/sitemap.xml", "https://www.anthropic.com/news/"),
}
LABS = ("anthropic", "openai", "xai", "mistral", "cohere")
# Hosts whose terms leave automated access unsettled: fetching is paused until the owner decides (docs/beslutslogg.md,
# 2026-11-23, "Förstapartspriser: Anthropic pausad"; the same consumer-terms clause covers the websites). The curated
# CSV and the series need no network; only discovery and re-verification fetch, and they need allow_paused=True.
_PAUSE_REASON = "Anthropics villkor om automatisk åtkomst: väntar på beslut (beslutslogg 2026-11-23)"
PAUSED_HOSTS = {"www.anthropic.com": _PAUSE_REASON, "claude.com": _PAUSE_REASON}


class SourcePaused(RuntimeError):
    pass


def _get(url: str, allow_paused: bool = False):
    host = re.sub(r"^https?://([^/]+).*$", r"\1", url)
    if host in PAUSED_HOSTS and not allow_paused:
        raise SourcePaused(f"{host}: {PAUSED_HOSTS[host]}; pass allow_paused=True (CLI --allow-paused) once decided")
    return http.get(url, SOURCE)
# scope: what the figure covers
SCOPES = {
    "company": "hela bolaget",
    "claude_code": "Claude Code (produkt)",
}
# measure code -> definition (as the company uses the term)
MEASURES = {
    "RUN_RATE": "run-rate revenue i bolagets nyhetsrum: annualiserad intäktstakt vid en tidpunkt (bolagets egen "
                "term; beräkningssättet anges inte i inläggen)",
    "RUN_RATE_S1": "Run-Rate Revenue enligt Anthropics S-1: konsumtionsavgifter under de 28 dagar som slutar på "
                   "mätdagen × 13 plus månatliga abonnemangsavgifter på mätdagen × 12. Operativt mått, ej GAAP, "
                   "inte granskat av tredje part",
    "ARR": "annual recurring revenue: årlig återkommande intäkt (abonnemang), bolagets egen term",
    "REVENUE_CY": "intäkt för ett kalenderår (summa, inte takt)",
}
# as_stated: no hedge word; approx: "approximately/about/~"; over: "over/more than/surpassed/crossed"; nearly
QUALIFIERS = ("as_stated", "approx", "over", "nearly")
UNITS = ("MUSD",)

DOC_TYPES = ("newsroom", "S-1", "S-1/A", "424B4", "10-Q", "10-K", "8-K")  # newsroom post or EDGAR form
REFUSED_FORMS = ("DRS", "DRS/A")  # confidential drafts: EDGAR date != date made public
SEC_ARCHIVE = "https://www.sec.gov/Archives/edgar/data/"

COLUMNS = ["id", "lab", "scope", "measure", "qualifier", "value", "unit", "period", "period_end", "known_from",
           "doc_type", "accession", "modified", "source_url", "locator", "sentence_sha256", "note"]


class CsvError(ValueError):
    pass


# ------------------------------------------------------------------ text

def to_text(raw: str) -> str:
    """Markup to one line of plain text (tags dropped, entities decoded, whitespace collapsed)."""
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", raw)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t.replace("\xa0", " ")).strip()


def sentence_hash(sentence: str) -> str:
    """SHA-256 of a source sentence after whitespace normalisation (one space, stripped)."""
    return hashlib.sha256(re.sub(r"\s+", " ", sentence).strip().encode("utf-8")).hexdigest()


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9$•“\"(])")


def sentences(text: str) -> list[str]:
    """Sentences of a post body; locators count sentences in this list from 0 ("sentence #n")."""
    return [x for x in _SENTENCE_SPLIT.split(text) if x.strip()]


@dataclass
class Post:
    url: str
    title: str
    published: str  # YYYY-MM-DD (datePublished)
    modified: str  # YYYY-MM-DD (article:modified_time), "" if absent
    body: str  # plain text of the post body

    @property
    def sentences(self) -> list[str]:
        return sentences(self.body)


_PARA = re.compile(r'(?is)<p\b[^>]*class="[^"]*post-text[^"]*"[^>]*>(.*?)</p>')
_LI = re.compile(r'(?is)<li\b[^>]*class="[^"]*post-text[^"]*"[^>]*>(.*?)</li>')


def parse_post(url: str, raw: str) -> Post:
    """Title, dates and body of one newsroom post (Anthropic's markup: body paragraphs carry class post-text)."""
    pub = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', raw)
    if not pub:
        pub = re.search(r'article:published_time"\s+content="(\d{4}-\d{2}-\d{2})', raw)
    mod = re.search(r'article:modified_time"\s+content="(\d{4}-\d{2}-\d{2})', raw)
    title = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw)
    # body: post-text paragraphs and list items, in document order
    parts = sorted([(m.start(), m.group(1)) for m in _PARA.finditer(raw)] +
                   [(m.start(), m.group(1)) for m in _LI.finditer(raw)])
    body = " ".join(to_text(p) for _, p in parts)
    if not body:  # other templates: fall back to every paragraph
        body = " ".join(to_text(p) for p in re.findall(r"(?is)<p\b[^>]*>(.*?)</p>", raw))
    return Post(url=url, title=to_text(title.group(1)) if title else "", published=pub.group(1) if pub else "",
                modified=mod.group(1) if mod else "", body=body)


# ------------------------------------------------------------------ fetching

def sitemap_urls(lab: str, allow_paused: bool = False) -> list[str]:
    sitemap, prefix = SITEMAPS[lab]
    xml = _get(sitemap, allow_paused).text
    return sorted({u for u in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml) if u.startswith(prefix)})


def fetch_post(url: str, allow_paused: bool = False) -> Post:
    return parse_post(url, _get(url, allow_paused).text)


def parse_filing(url: str, raw: str, filed: str) -> Post:
    """An EDGAR document as a Post: the whole document's plain text is the body; published = filing date."""
    return Post(url=url, title="", published=filed, modified="", body=to_text(raw))


def fetch_document(row, allow_paused: bool = False) -> Post:
    """The document a CSV row cites: a newsroom post, or an EDGAR filing dated by its index page."""
    if row["doc_type"] == "newsroom":
        return fetch_post(row["source_url"], allow_paused)
    base = row["source_url"].rsplit("/", 1)[0]
    index = http.get(f"{base}/{row['accession']}-index.htm", SOURCE).text
    m = re.search(r"Filing Date</div>\s*<div class=\"info\">(\d{4}-\d{2}-\d{2})", index)
    if not m:
        raise RuntimeError(f"no filing date on the EDGAR index of {row['accession']}")
    return parse_filing(row["source_url"], http.get(row["source_url"], SOURCE).text, m.group(1))


def discover(lab: str = "anthropic", allow_paused: bool = False) -> list[Post]:
    return [fetch_post(u, allow_paused) for u in sitemap_urls(lab, allow_paused)]


# a revenue term, near a money amount
_REVENUE = re.compile(r"(?i)\b(revenue|run[- ]rate|annuali[sz]ed|ARR|recurring)\b")
_MONEY = re.compile(r"\$\s?\d")


def candidates(posts: list[Post]) -> pd.DataFrame:
    """Sentences that mention revenue and a dollar amount, with url, published date and locator."""
    rows = []
    for p in posts:
        for i, s in enumerate(p.sentences):
            if _REVENUE.search(s) and _MONEY.search(s):
                rows.append({"url": p.url, "published": p.published, "modified": p.modified,
                             "locator": f"sentence #{i}", "sentence": s})
    return pd.DataFrame(rows, columns=["url", "published", "modified", "locator", "sentence"])


# ------------------------------------------------------------------ curated CSV

def _sentence_no(locator: str) -> int:
    m = re.search(r"sentence #(\d+)", locator)
    if not m:
        raise CsvError(f"locator {locator!r} must contain 'sentence #<n>'")
    return int(m.group(1))


def load(path: Path | None = None) -> pd.DataFrame:
    """Validated rows of curated/lab_revenue.csv, with known_from and period_end as Timestamps."""
    path = path or PATH
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if rows and list(rows[0]) != COLUMNS:
        raise CsvError(f"columns {list(rows[0])} != {COLUMNS}")
    seen = set()
    for r in rows:
        where = f"{path.name} id={r.get('id')}"
        if r["id"] in seen:
            raise CsvError(f"{where}: duplicate id")
        seen.add(r["id"])
        if r["lab"] not in LABS or r["scope"] not in SCOPES or r["measure"] not in MEASURES:
            raise CsvError(f"{where}: lab/scope/measure not in the scheme")
        if r["qualifier"] not in QUALIFIERS or r["unit"] not in UNITS:
            raise CsvError(f"{where}: qualifier/unit not in the scheme")
        try:
            value = float(r["value"])
        except ValueError:
            raise CsvError(f"{where}: value must be a number") from None
        if value <= 0:
            raise CsvError(f"{where}: value must be positive")
        if not re.fullmatch(r"[0-9a-f]{64}", r["sentence_sha256"]):
            raise CsvError(f"{where}: sentence_sha256 must be 64 hex characters")
        if not r["source_url"].startswith("https://"):
            raise CsvError(f"{where}: source_url must be https")
        if r["doc_type"] in REFUSED_FORMS:
            raise CsvError(f"{where}: {r['doc_type']} is a confidential draft; its EDGAR date is not when it became "
                           "public, cite the public S-1/S-1/A instead")
        if r["doc_type"] not in DOC_TYPES:
            raise CsvError(f"{where}: doc_type {r['doc_type']!r} not in the scheme")
        if r["doc_type"] == "newsroom":
            if r["accession"]:
                raise CsvError(f"{where}: a newsroom post has no accession")
        elif not (re.fullmatch(r"\d{10}-\d{2}-\d{6}", r["accession"]) and r["source_url"].startswith(SEC_ARCHIVE)):
            raise CsvError(f"{where}: an SEC filing needs an accession and an EDGAR Archives URL")
        if r["measure"] == "RUN_RATE_S1" and r["doc_type"] == "newsroom":
            raise CsvError(f"{where}: RUN_RATE_S1 is the S-1-defined metric; newsroom figures are RUN_RATE")
        _sentence_no(r["locator"])
        kf, end = pd.Timestamp(r["known_from"]), pd.Timestamp(r["period_end"])
        # a statement cannot describe a date after its own publication (that would be a forecast, not revenue)
        if end > kf:
            raise CsvError(f"{where}: period_end {end.date()} after the statement's publication {kf.date()}")
        if r["modified"] and pd.Timestamp(r["modified"]) < kf:
            raise CsvError(f"{where}: modified before published")
        if r["measure"] == "REVENUE_CY" and not re.fullmatch(r"\d{4}", r["period"]):
            raise CsvError(f"{where}: REVENUE_CY needs period = YYYY")
        if r["measure"] == "REVENUE_CY" and r["period_end"] != f"{r['period']}-12-31":
            raise CsvError(f"{where}: REVENUE_CY needs period_end = YYYY-12-31")
        if r["measure"] != "REVENUE_CY" and r["period"] != r["period_end"]:
            raise CsvError(f"{where}: a run-rate/ARR level refers to a date: period = period_end (YYYY-MM-DD)")
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["value"] = pd.to_numeric(df["value"])
    df["known_from"] = pd.to_datetime(df["known_from"])
    df["period_end"] = pd.to_datetime(df["period_end"])
    return df


def series_frame(df: pd.DataFrame, lab: str, scope: str, measure: str) -> pd.DataFrame:
    """Release-dated rows (period, value, known_from) for one lab/scope/measure.

    A run-rate or ARR is a level at a point in time: period = the date it refers to (freq D); calendar-year
    revenue has period = the year (freq A). A later statement about the same period with a different value is a
    new vintage; the same value restated adds no row. The value is the number as stated (a bound stays the
    bound; the qualifier is in the CSV and the series note).
    """
    d = df[(df["lab"] == lab) & (df["scope"] == scope) & (df["measure"] == measure)]
    d = d.sort_values(["known_from", "period_end"], kind="stable")
    out, last = [], {}
    for p, v, kf in d[["period", "value", "known_from"]].itertuples(index=False):
        if p in last and last[p] == v:
            continue
        last[p] = v
        out.append((p, float(v), kf))
    res = pd.DataFrame(out, columns=["period", "value", "known_from"])
    return res.drop_duplicates(["period", "known_from"], keep="last").reset_index(drop=True)


# ------------------------------------------------------------------ verification

def _number_in(sentence: str, value_musd: float) -> bool:
    """Does the sentence state value_musd (as $X billion / $X million / $XB / $XM)?"""
    for num, mult in re.findall(r"\$\s?([\d,]+(?:\.\d+)?)\s*(billion|million|B\b|M\b|bn\b)", sentence):
        f = float(num.replace(",", "")) * (1000 if mult.lower() in ("billion", "b", "bn") else 1)
        if abs(f - value_musd) < 1e-6:
            return True
    return False


def check_row(row: dict | pd.Series, post: Post) -> list[str]:
    """Problems with one curated row against its fetched document; empty = verified."""
    errs = []
    sents = post.sentences
    n = _sentence_no(row["locator"])
    if n >= len(sents):
        return [f"{row['id']}: {row['locator']} beyond the post's {len(sents)} sentences"]
    s = sents[n]
    if sentence_hash(s) != row["sentence_sha256"]:
        errs.append(f"{row['id']}: sentence hash differs at {row['locator']}")
    if not _number_in(s, float(row["value"])):
        errs.append(f"{row['id']}: {row['value']} {row['unit']} not stated in the sentence")
    if post.published != str(pd.Timestamp(row["known_from"]).date()):
        errs.append(f"{row['id']}: known_from {row['known_from']} != document date {post.published}")
    return errs


def _documents(df: pd.DataFrame, allow_paused: bool = False) -> dict[str, Post]:
    return {r["source_url"]: fetch_document(r, allow_paused) for _, r in df.drop_duplicates("source_url").iterrows()}


def verify(path: Path | None = None, allow_paused: bool = False) -> list[str]:
    """Re-fetch every document in the CSV and check each row (network)."""
    df = load(path)
    posts = _documents(df, allow_paused)
    return [e for _, r in df.iterrows() for e in check_row(r, posts[r["source_url"]])]


def save_sentences(path: Path | None = None, allow_paused: bool = False) -> Path:
    """Write the source sentences of every row to data/raw (gitignored, never committed)."""
    df = load(path)
    posts = _documents(df, allow_paused)
    SENTENCES_DIR.mkdir(parents=True, exist_ok=True)
    out = SENTENCES_DIR / "sentences.jsonl"
    with open(out, "w", encoding="utf-8") as fh:
        for _, r in df.iterrows():
            s = posts[r["source_url"]].sentences[_sentence_no(r["locator"])]
            fh.write(json.dumps({"id": r["id"], "url": r["source_url"], "locator": r["locator"],
                                 "sha256": sentence_hash(s), "sentence": s}, ensure_ascii=False) + "\n")
    return out


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    allow = "--allow-paused" in args
    args = [a for a in args if a != "--allow-paused"]
    if args == ["verify"]:
        problems = verify(allow_paused=allow)
        print("\n".join(problems) or f"verified: all rows in {PATH.name} match their documents")
        print(f"sentences -> {save_sentences(allow_paused=allow)}")
        sys.exit(1 if problems else 0)
    posts = discover("anthropic", allow_paused=allow)
    pd.set_option("display.max_colwidth", None, "display.width", 250)
    print(f"{len(posts)} posts")
    print(candidates(posts).to_string())
