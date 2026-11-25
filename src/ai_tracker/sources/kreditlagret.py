"""KL1 "Kreditlagret": debt instruments and commitments of the outer layers, agent-coded from EDGAR text (step 2).

Coding rules: docs/mattregister.md, 2026-11-25 "KL1", "Kodningsregler för steg 2" (locked before any document was read).
Pattern of KR1 and CN1: document, location, verbatim quote and its SHA-256; the quote lives only under data/raw.

Corpus (rule "Korpus"):
- Anthropic, PBC (CIK 2130357): every S-1, S-1/A and 424B4 filed up to 2026-11-25 (no DRS drafts). The source is the
  latest of them; a row's known_from is the filing date of the earliest public document holding the same line (hash)
  and, for a row with a full balance date, stating that date for it (register X23, point 1; `stated_dates`).
- SpaceX (CIK 1181412, owner of xAI): 10-Q and 10-K filed 2026-06-12..2026-11-25 (register X23, point 3), coded like
  CoreWeave's periodic reports but by the agent, row by row.
- OpenAI: the EDGAR company search (browse-edgar, Atom) by name; a registration statement (S-1, S-1/A, F-1, F-1/A) is
  looked for in every match's submissions. None found -> recorded as a fact (docs/kallor/kreditlagret.md).
- CoreWeave (CIK 1769628): 10-Q and 10-K filed 2025-04-01..2026-11-25, and 8-Ks of the same period with item 1.01 or
  2.03. A balance date is coded from the first 10-Q/10-K that reports it as the current period.
- Meta (Hyperion) and Oracle (data-centre SPV, joint venture, lease arrangements): 10-Q and 10-K filed
  2025-01-01..2026-11-25; only lines that state an amount.

Text and location: KR1's line list (credit_issuance_corpus.lines), locator "line #k" (from 0) or, for a sentence the
list breaks over several lines, "lines #a-#b" (register addendum 2026-11-25); the quote is the line(s), quote_sha256 =
credit_issuance_corpus.block_hash(lines). CoreWeave's debt table ("The total debt obligations are as follows") is coded
by the deterministic `debt_table` (addendum, point 3); everything else is coded by the agent, row by row (method in the
note). `value_in_quote` is the number test that both the build and the self-check use.

    python -m ai_tracker.sources.kreditlagret corpus            # list and fetch the corpus (cached raw copies)
    python -m ai_tracker.sources.kreditlagret candidates ACC    # candidate lines of one document, for the coder
    python -m ai_tracker.sources.kreditlagret openai            # the OpenAI search, written to data/raw
    python -m ai_tracker.sources.kreditlagret quotes            # rebuild data/raw quotes from the CSV locators
    python -m ai_tracker.sources.kreditlagret build             # the CSV and the list of uncoded candidates

SEC: the generic client identity from .env (ai_tracker.http), one request at a time, BULK_SLEEP between documents,
and a stop on 403 or 429 (no retries on those).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from dataclasses import asdict, dataclass
from functools import lru_cache

import pandas as pd
import requests

from ai_tracker import config, http
from ai_tracker.sources import credit_issuance_corpus as cc

SOURCE = "kreditlagret"
CSV_PATH = config.REPO / "curated" / "kreditlagret.csv"
SKIPPED_PATH = config.REPO / "curated" / "kreditlagret_skipped.csv"  # uncoded candidate lines with the reason (X23)
QUOTES_DIR = config.REPO / "data" / "raw" / "kreditlagret_quotes"  # gitignored
CORPUS_DIR = config.REPO / "data" / "raw" / "kreditlagret_corpus"  # gitignored
LAST = "2026-11-25"
BULK_SLEEP = 0.3
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SUBMISSIONS_FILE = "https://data.sec.gov/submissions/{name}"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{doc}"
COMPANY_SEARCH = "https://www.sec.gov/cgi-bin/browse-edgar"

CIKS = {"anthropic": 2130357, "crwv": 1769628, "meta": 1326801, "orcl": 1341439, "spacex": 1181412}
NAMES = {"anthropic": "Anthropic", "openai": "OpenAI", "crwv": "CoreWeave", "meta": "Meta", "orcl": "Oracle",
         "spacex": "SpaceX"}
SPACEX_FIRST = "2026-06-12"  # the 424B4 (IPO); SpaceX's 10-Q/10-K from here (register X23, point 3)
REGISTRATION_FORMS = ("S-1", "S-1/A", "F-1", "F-1/A")
LAB_FORMS = ("S-1", "S-1/A", "424B4")

COLUMNS = ("id", "company", "instrument", "field", "value", "unit", "period", "filed", "accepted", "form", "accession",
           "source_url", "locator", "quote_sha256", "qualifier", "note")
FIELDS = {
    "principal": "MUSD", "commitment": "MUSD", "outstanding": "MUSD", "coupon_pct": "%", "margin_bp": "bp",
    "rate_pct": "%", "yield_pct": "%", "maturity": "date", "issue_date": "date", "secured": "code",
    "guarantor": "code", "collateral": "code", "offering": "code",
    # data-centre ventures (Meta) and SPV arrangements: amounts as stated
    "contribution": "MUSD", "distribution": "MUSD", "lease_commitment": "MUSD", "funding_commitment": "MUSD",
    "rvg_max": "MUSD", "exposure_max": "MUSD", "equity_carrying": "MUSD", "dev_cost": "MUSD",
}
DUE_FIELD = re.compile(r"due_(?:\d{4}|total|thereafter|\d{4}_\d{4})$")
QUALIFIERS = ("", "approx", "up_to", "at_least")
CODES = {"secured": ("secured", "unsecured"), "offering": ("144A", "registered", "private")}

DEBT_CANDIDATE = re.compile(r"(?i)\b(notes?|term loans?|credit (?:agreement|facility|facilities)|facilit(?:y|ies)|"
                            r"delayed draw|DDTL|revolving|indenture|borrowings?|loans?|debentures?|convertible)\b")
COMMIT_CANDIDATE = re.compile(r"(?i)\b(purchase (?:commitments?|obligations?)|contractual obligations|"
                              r"compute|cloud (?:services|computing|commitments?)|non-?cancel+able)\b")
SPV_CANDIDATE = re.compile(r"(?i)\b(Hyperion|joint venture|variable interest entit(?:y|ies)|residual value guarantee|"
                           r"special purpose)\b")
VENTURE_CANDIDATE = re.compile(r"\bVentures?\b")  # Meta's name for its data-centre ventures (register X23, point 2)
CANDIDATE_KINDS = {"anthropic": ("debt", "commit", "spv"), "crwv": ("debt",), "meta": ("spv", "venture"),
                   "orcl": ("spv",), "spacex": ("debt",)}
AMOUNT = re.compile(r"\$\s?\d|\d\s?%|\d[\d,]*\.?\d*\s*(?:million|billion)")


class Stop(RuntimeError):
    """SEC answered 403 or 429: stop the run (fair-access rule)."""


@dataclass(frozen=True)
class Doc:
    company: str
    form: str
    filed: str
    accepted: str
    accession: str
    url: str
    items: str = ""


@dataclass(frozen=True)
class Row:
    id: str
    company: str
    instrument: str
    field: str
    value: str
    unit: str
    period: str
    filed: str
    accepted: str
    form: str
    accession: str
    source_url: str
    locator: str
    quote_sha256: str
    qualifier: str = ""
    note: str = ""


# ------------------------------------------------------------------ fetching


def _cached(url: str):
    name = http.raw_path(SOURCE, url).name
    hits = sorted((http.RAW_DIR / SOURCE).glob(f"*/{name}"))
    return hits[-1] if hits else None


def fetch(url: str, reuse: bool = True, params: dict | None = None) -> bytes:
    """A document's bytes. An archived SEC document never changes, so a cached raw copy is reused. A network fetch
    sleeps BULK_SLEEP afterwards, and 403/429 raise Stop (no retry)."""
    path = _cached(url) if reuse and params is None else None
    if path is not None:
        return path.read_bytes()
    try:
        r = http.get(url, SOURCE, params=params, retries=0)
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else None
        if code in (403, 429):
            raise Stop(f"{url}: HTTP {code}, stopping (SEC fair access)") from exc
        raise
    time.sleep(BULK_SLEEP)
    return r.content


def submissions(cik: int) -> list[dict]:
    """Every filing of the CIK (recent block plus older files), oldest first, with items."""
    sub = json.loads(fetch(SUBMISSIONS.format(cik=cik), reuse=False))
    blocks = [sub["filings"]["recent"]] + [json.loads(fetch(SUBMISSIONS_FILE.format(name=f["name"]), reuse=False))
                                           for f in sub["filings"].get("files", [])]
    out = {}
    for b in blocks:
        for i, acc in enumerate(b["accessionNumber"]):
            out[acc] = {"form": b["form"][i], "filed": b["filingDate"][i], "accession": acc,
                        "accepted": b["acceptanceDateTime"][i], "primary": b["primaryDocument"][i],
                        "items": (b.get("items") or [""] * len(b["accessionNumber"]))[i] or ""}
    return sorted(out.values(), key=lambda f: (f["filed"], f["accepted"]))


def in_corpus(company: str, f: dict) -> bool:
    """Rule "Korpus" of the register entry."""
    form, filed, items = f["form"], f["filed"], f.get("items", "")
    if filed > LAST:
        return False
    if company == "anthropic":
        return form in LAB_FORMS
    if company == "crwv":
        if filed < "2025-04-01":
            return False
        return form in ("10-Q", "10-K") or (form == "8-K" and bool({"1.01", "2.03"} & set(items.split(","))))
    if company in ("meta", "orcl"):
        return filed >= "2025-01-01" and form in ("10-Q", "10-K")
    if company == "spacex":  # owner of xAI; periodic reports after the IPO (register X23, point 3)
        return filed >= SPACEX_FIRST and form in ("10-Q", "10-K")
    return False


def corpus(company: str, subs: list[dict] | None = None) -> list[Doc]:
    subs = submissions(CIKS[company]) if subs is None else subs
    return [Doc(company, f["form"], f["filed"], f["accepted"], f["accession"],
                ARCHIVE.format(cik=CIKS[company], folder=f["accession"].replace("-", ""), doc=f["primary"]), f["items"])
            for f in subs if in_corpus(company, f)]


def doc_lines(url: str, reuse: bool = True) -> list[str]:
    if reuse:
        return list(_cached_lines(url))
    return cc.lines(fetch(url, reuse=False).decode("utf-8", errors="replace"))


@lru_cache(maxsize=64)
def _cached_lines(url: str) -> tuple[str, ...]:
    return tuple(cc.lines(fetch(url).decode("utf-8", errors="replace")))


@lru_cache(maxsize=256)
def _hash_index(url: str, width: int) -> dict[str, int]:
    """SHA-256 of every window of `width` lines of a cached document -> its first line."""
    lines = _cached_lines(url)
    out: dict[str, int] = {}
    for k in range(len(lines) - width + 1):
        out.setdefault(quote_hash("\n".join(lines[k:k + width])), k)
    return out


LOCATOR = re.compile(r"line #(\d+)|lines #(\d+)-#(\d+)")


def span(locator: str) -> tuple[int, int]:
    m = LOCATOR.fullmatch(locator)
    if not m:
        raise ValueError(f"bad locator {locator!r}")
    if m.group(1) is not None:
        return int(m.group(1)), int(m.group(1))
    a, b = int(m.group(2)), int(m.group(3))
    if b <= a:
        raise ValueError(f"bad locator {locator!r}: a range needs b > a")
    return a, b


def locator_of(a: int, b: int) -> str:
    return f"line #{a}" if a == b else f"lines #{a}-#{b}"


def quote_at(lines: list[str], locator: str) -> str | None:
    """The quote at the locator: the line, or the lines joined by newlines. None when outside the document."""
    a, b = span(locator)
    return "\n".join(lines[a:b + 1]) if b < len(lines) else None


def quote_hash(quote: str) -> str:
    return cc.block_hash(quote.split("\n"))


def find_hash(lines: list[str], digest: str, width: int = 1) -> int | None:
    """First line k whose window lines[k:k+width] hashes to `digest` (a moved quote)."""
    for k in range(len(lines) - width + 1):
        if quote_hash("\n".join(lines[k:k + width])) == digest:
            return k
    return None


# ------------------------------------------------------------------ candidates


def candidates(lines: list[str], kinds: tuple[str, ...] = ("debt", "commit", "spv")) -> list[tuple[int, str, str]]:
    """(k, kind, line) of the candidate lines (rule "Kandidatrader"): a pattern of the kind and an amount or a rate."""
    pats = {"debt": DEBT_CANDIDATE, "commit": COMMIT_CANDIDATE, "spv": SPV_CANDIDATE, "venture": VENTURE_CANDIDATE}
    out = []
    for k, line in enumerate(lines):
        if not AMOUNT.search(line):
            continue
        for kind in kinds:
            if pats[kind].search(line):
                out.append((k, kind, line))
                break
    return out


# ------------------------------------------------------------------ OpenAI search


def openai_search(name: str = "openai") -> list[dict]:
    """Companies whose EDGAR name matches `name` (browse-edgar Atom), each with its registration statements."""
    xml = fetch(COMPANY_SEARCH, reuse=False, params={"company": name, "owner": "include", "action": "getcompany",
                                                     "output": "atom", "count": "100"}).decode("latin-1")
    out = []
    for entry in re.findall(r"(?s)<entry>(.*?)</entry>", xml):
        cik = re.search(r"<cik>(\d+)</cik>", entry)
        title = re.search(r"<name>(.*?)</name>", entry)
        if not cik:
            continue
        subs = submissions(int(cik.group(1)))
        forms = sorted({f["form"] for f in subs})
        out.append({"cik": int(cik.group(1)), "name": title.group(1) if title else "", "forms": forms,
                    "registration": [f["accession"] for f in subs if f["form"] in REGISTRATION_FORMS]})
    return out


# ------------------------------------------------------------------ rows and CSV


def check_value(field: str, value: str, unit: str) -> None:
    """Raise ValueError if a row's field, unit or value breaks the coding rules."""
    if field in FIELDS:
        want = FIELDS[field]
    elif DUE_FIELD.match(field):
        want = "MUSD"
    else:
        raise ValueError(f"unknown field {field!r}")
    if unit != want and not (want == "MUSD" and re.fullmatch(r"M[A-Z]{3}", unit)):
        raise ValueError(f"{field}: unit {unit!r}, expected {want}")
    if want == "date":
        if not re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?", value):
            raise ValueError(f"{field}: date {value!r} not ISO (YYYY-MM-DD, or YYYY-MM for a month)")
        pd.Timestamp(value)
    elif want == "code":
        if field in CODES and value not in CODES[field]:
            raise ValueError(f"{field}: code {value!r} not in {CODES[field]}")
        if not value.strip():
            raise ValueError(f"{field}: empty code")
    else:
        float(value)


def validate(df: pd.DataFrame) -> list[str]:
    """Problems with the curated rows; empty = valid."""
    errors = []
    if tuple(df.columns) != COLUMNS:
        return [f"columns {tuple(df.columns)} != {COLUMNS}"]
    if df["id"].duplicated().any():
        errors.append(f"duplicate ids: {sorted(df.loc[df['id'].duplicated(), 'id'])}")
    for r in df.itertuples(index=False):
        try:
            check_value(r.field, r.value, r.unit)
        except ValueError as exc:
            errors.append(f"{r.id}: {exc}")
        if r.qualifier not in QUALIFIERS:
            errors.append(f"{r.id}: qualifier {r.qualifier!r}")
        if not re.fullmatch(r"[0-9a-f]{64}", r.quote_sha256):
            errors.append(f"{r.id}: bad sha256")
        try:
            span(r.locator)
        except ValueError as exc:
            errors.append(f"{r.id}: {exc}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r.filed) or r.filed > LAST:
            errors.append(f"{r.id}: filed {r.filed!r}")
        if r.period and not re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?", r.period):
            errors.append(f"{r.id}: period {r.period!r}")
    return errors


def load(path=CSV_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    errors = validate(df)
    if errors:
        raise ValueError(f"{path}: " + "; ".join(errors[:10]))
    return df


def write(rows: list[Row], path=CSV_PATH) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in sorted(rows, key=lambda r: r.id):
            w.writerow(asdict(r))


def save_quote(row_id: str, line: str) -> None:
    QUOTES_DIR.mkdir(parents=True, exist_ok=True)
    (QUOTES_DIR / f"{row_id}.txt").write_text(line, encoding="utf-8")


def rebuild_quotes(df: pd.DataFrame | None = None) -> int:
    """Write every row's quote to data/raw from its document and locator (cached documents). Returns the count."""
    df = load() if df is None else df
    n = 0
    for r in df.itertuples(index=False):
        quote = quote_at(doc_lines(r.source_url), r.locator)
        if quote is not None and quote_hash(quote) == r.quote_sha256:
            save_quote(r.id, quote)
            n += 1
    return n


# ------------------------------------------------------------------ the number test (build and self-check)

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
          "December")
ZERO_FORMS = (r"\bno borrowings\b", r"\bno (?:amounts|notes|borrowings) (?:were |had been )?(?:outstanding|issued|drawn)")
CODE_FORMS = {
    ("secured", "secured"): r"(?i)(?<!un)secured",
    ("secured", "unsecured"): r"(?i)\bunsecured\b",
    ("offering", "144A"): r"144A",
    ("offering", "registered"): r"(?i)registered (?:offering|public offering)|registration statement on Form S-3",
    ("offering", "private"): r"(?i)private (?:offering|placement)",
}


def _num(x: float) -> str:
    """x as written, with optional trailing zeros (4.85 matches 4.850; 25 matches 25 and 25.0)."""
    t = f"{x:.6f}".rstrip("0").rstrip(".")
    return rf"(?<![\d.]){re.escape(t)}" + (r"0*" if "." in t else r"(?:\.0+)?") + r"(?![\d])"


def amount_forms(millions: float, currency: str = "USD") -> list[str]:
    sym = {"USD": r"(?:US)?\$", "EUR": "(?:€|EUR)"}.get(currency, re.escape(currency))
    out = [rf"{sym}\s?{_num(millions / 1000)}\s*billion", rf"{sym}?\s?{_num(millions)}\s*million"]
    thousands = round(millions * 1000, 6)
    if float(thousands).is_integer():  # a table "in thousands"
        out.append(rf"(?<![\d.,]){re.escape(f'{int(thousands):,}')}(?![\d,])")
    if float(millions).is_integer():  # a table "in millions"
        out.append(rf"(?<![\d.,]){re.escape(f'{int(millions):,}')}(?![\d,])")
    out.append(rf"{sym}\s?{re.escape(f'{int(round(millions * 1e6)):,}')}(?![\d,])")  # in full dollars
    return out


def date_forms(day: str) -> list[str]:
    parts = day.split("-")
    month = MONTHS[int(parts[1]) - 1]
    name = rf"(?:{month}|{month[:3]}\.?)"
    if len(parts) == 2:
        return [rf"{name}\s+(?:\d{{1,2}},\s*)?{parts[0]}"]
    return [rf"{name}\s+{int(parts[2])}\s*,\s*{parts[0]}"]


def value_in_quote(field: str, value: str, unit: str, quote: str) -> bool:
    """Does the quote write the row's value (rule "Självkontroll")? Amounts as $/billion/million or a table cell in
    millions, rates as percentages, margins as bp or a percentage, dates as written, codes by their wording."""
    text = re.sub(r"\s+", " ", quote)
    want = FIELDS.get(field, "MUSD")
    if want == "date":
        pats = date_forms(value)
    elif want == "code":
        pat = CODE_FORMS.get((field, value))
        return bool(re.search(pat, text)) if pat else value.lower() in text.lower()
    elif want == "%":
        pats = [_num(float(value)) + r"\s?%"] + ([r"non-interest[- ]bearing"] if float(value) == 0 else [])
    elif want == "bp":
        bp = float(value)
        pats = [rf"{_num(bp)}\s*(?:bps|bp|basis\s+points)", rf"{_num(bp / 100)}\s?%"]
    else:
        v = float(value)
        if v == 0:
            pats = list(ZERO_FORMS)
        else:
            cur = unit[1:] if re.fullmatch(r"M[A-Z]{3}", unit) and unit != "MUSD" else "USD"
            pats = amount_forms(v, cur)
    return any(re.search(p, text, flags=re.I) for p in pats)


# ------------------------------------------------------------------ CoreWeave's debt table (addendum, point 3)

TABLE_START = re.compile(r"(?i)^The total debt obligations are as follows")
SKIP_ROW = re.compile(r"(?i)^(Less|Total)\b")
SECTION = re.compile(r"(?i)^(Recourse|Non-recourse) debt:?$")
RATE_CELL = re.compile(r"^(\d+(?:\.\d+)?)\s?%$")
MONTH_CELL = re.compile(r"^([A-Z][a-z]+)\.? (\d{4})$")
DATE_HEADER = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December) "
                         r"(\d{1,2}), (\d{4})")


def slug(name: str) -> str:
    name = re.sub(r"\(\d\)", "", name)
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


@dataclass(frozen=True)
class TableRow:
    k: int
    instrument: str
    balance_date: str
    outstanding: float | None
    rate_pct: float | None
    maturity: str | None


def _money(cell: str) -> float | None:
    c = cell.replace("$", "").replace(",", "").strip()
    if c in ("—", "-", "–"):
        return 0.0
    try:
        return float(c)
    except ValueError:
        return None


def debt_table(lines: list[str]) -> list[TableRow]:
    """Instrument rows of the first debt-obligations table: (instrument, current balance date, outstanding MUSD,
    effective rate %, maturity month). The table ends at the first line without cells that is not a section heading.
    Subtotals and "Less"/"Total" lines are skipped; the non-recourse section prefixes the instrument id. A table "in
    thousands" (CoreWeave to its 2025 10-Qs) is converted to millions; the cell still reads as the stated figure."""
    start = next((k for k, line in enumerate(lines) if TABLE_START.match(line)), None)
    if start is None:
        return []
    header = next((k for k in range(start, min(start + 4, len(lines))) if DATE_HEADER.search(lines[k])), None)
    if header is None:
        return []
    dates = DATE_HEADER.findall(lines[header])
    m, d, y = dates[0]
    balance = f"{y}-{MONTHS.index(m) + 1:02d}-{int(d):02d}"
    scale = 0.001 if re.search(r"(?i)in thousands", lines[start]) else 1.0
    cols = [c.strip() for c in lines[header].split(" | ")]
    i_rate = next((i for i, c in enumerate(cols) if re.search(r"(?i)interest rate", c)), None)
    out, section = [], ""
    for k in range(header + 1, len(lines)):
        line = lines[k]
        sec = SECTION.match(line)
        if sec:
            section = "nonrecourse" if sec.group(1).lower().startswith("non") else "recourse"
            continue
        if " | " not in line:
            break
        cells = [c.strip() for c in line.split(" | ")]
        if SKIP_ROW.match(cells[0]) or len(cells) < 3:
            continue
        name, rest = cells[0], cells[1:]
        maturity = rate = None
        for c in rest[:-2]:
            mm = MONTH_CELL.match(c)
            if mm and mm.group(1)[:3] in [x[:3] for x in MONTHS]:
                maturity = f"{mm.group(2)}-{[x[:3] for x in MONTHS].index(mm.group(1)[:3]) + 1:02d}"
            rr = RATE_CELL.match(c)
            if rr and i_rate is not None:
                rate = float(rr.group(1))
        amounts = [_money(c) for c in rest[-2:]]
        if amounts[0] is None:
            continue
        amounts = [round(a * scale, 6) if a is not None else None for a in amounts]
        inst = f"crwv_{section + '_' if section == 'nonrecourse' else ''}{slug(name)}"
        out.append(TableRow(k, inst, balance, amounts[0], rate, maturity))
    return out


def table_rows(doc: Doc, lines: list[str]) -> list[Row]:
    """CSV rows (fields outstanding, rate_pct, maturity) of a document's debt table; quotes saved under data/raw."""
    rows = []
    for t in debt_table(lines):
        quote = lines[t.k]
        values = [("outstanding", t.outstanding, "MUSD"), ("rate_pct", t.rate_pct, "%"), ("maturity", t.maturity, "date")]
        if not t.outstanding:  # nothing outstanding on the balance date: the row adds nothing to the weighted mean
            continue
        for field, value, unit in values:
            if value is None:
                continue
            v = value if isinstance(value, str) else repr(float(value)).removesuffix(".0")
            if not value_in_quote(field, v, unit, quote):
                raise ValueError(f"{doc.accession} line #{t.k}: {field}={v} not in the row")
            rid = f"{t.instrument}-{t.balance_date}-{field}"
            note = "debt table, effective interest rate as stated" if field == "rate_pct" else "debt table"
            rows.append(Row(rid, doc.company, t.instrument, field, v, unit, t.balance_date, doc.filed, doc.accepted,
                            doc.form, doc.accession, doc.url, f"line #{t.k}", quote_hash(quote), "", note))
            save_quote(rid, quote)
    return rows


def manual_row(doc: Doc, lines: list[str], locator: str, instrument: str, field: str, value: str, unit: str,
               period: str = "", qualifier: str = "", note: str = "", rid: str | None = None) -> Row:
    """One agent-coded row: the value must stand in the quote at the locator (or the build stops)."""
    quote = quote_at(lines, locator)
    if quote is None:
        raise ValueError(f"{doc.accession} {locator}: outside the document")
    check_value(field, value, unit)
    if not value_in_quote(field, value, unit, quote):
        raise ValueError(f"{doc.accession} {locator}: {field}={value} not in the quote: {quote[:300]}")
    rid = rid or f"{instrument}-{period or 'terms'}-{field}"
    save_quote(rid, quote)
    return Row(rid, doc.company, instrument, field, value, unit, period, doc.filed, doc.accepted, doc.form,
               doc.accession, doc.url, locator, quote_hash(quote), qualifier, note or "agent-coded")


FULL_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_MONTH_RE = "|".join(MONTHS)
ANY_DATE = re.compile(rf"(?i)\b({_MONTH_RE})\s+(\d{{1,2}})\s*,\s*(\d{{4}})")
AS_OF = re.compile(rf"(?i)\bA\s?s\s+of\s+(?:and\s+subsequent\s+to\s+)?({_MONTH_RE})\s+(\d{{1,2}})\s*,\s*(\d{{4}})")
PAGE_FILL = re.compile(r"^(?:\d{1,3}|Table of Contents|_+)$")  # page numbers and rules inside a table
NOTE_LINE = re.compile(r"^\(\d+\)")
CONTEXT_LINES = 30


def _dates(pattern: re.Pattern, text: str) -> set[str]:
    return {f"{y}-{[m.lower() for m in MONTHS].index(mo.lower()) + 1:02d}-{int(d):02d}"
            for mo, d, y in pattern.findall(text)}


def stated_dates(lines: list[str], a: int, b: int, width: int = CONTEXT_LINES) -> set[str]:
    """Balance dates a document states for the quote lines[a..b] (register X23, point 1): every date in the quote, and
    "as of <day>" in the `width` lines before the quote's table and in the table's notes ("(n)" lines within `width`
    after it). A quote that is not a table row: "as of <day>" in the `width` lines before and after it."""
    out = _dates(ANY_DATE, "\n".join(lines[a:b + 1]))
    if " | " in lines[a]:
        s, e = a, b
        while s > 0 and (" | " in lines[s - 1] or PAGE_FILL.match(lines[s - 1].strip())):
            s -= 1
        while e + 1 < len(lines) and (" | " in lines[e + 1] or PAGE_FILL.match(lines[e + 1].strip())):
            e += 1
        out |= _dates(AS_OF, "\n".join(lines[max(0, s - width):s]))
        out |= _dates(AS_OF, "\n".join(x for x in lines[e + 1:e + 1 + width] if NOTE_LINE.match(x)))
    else:
        out |= _dates(AS_OF, "\n".join(lines[max(0, a - width):a] + lines[b + 1:b + 1 + width]))
    return out


def earliest(rows: list[Row], earlier: list[Doc], lines_of=None) -> list[Row]:
    """known_from rule for the lab's registration statement: a row moves to the earliest public document (oldest first
    in `earlier`) whose line list holds the same quote (same SHA-256) and, for a row with a full balance date (period
    YYYY-MM-DD), states that date for it (`stated_dates`, register X23, point 1); filed, accepted, form, accession, URL
    and locator then point to that document. `lines_of(url)` gives a document's lines (default: the cached copy)."""
    lines_of = lines_of or _cached_lines
    out = []
    for r in rows:
        a, b = span(r.locator)
        width = b - a + 1
        best = r
        for d in earlier:
            if d.filed >= r.filed:
                continue
            k = _hash_index(d.url, width).get(r.quote_sha256)
            if k is None:
                continue
            if FULL_DATE.fullmatch(r.period) and r.period not in stated_dates(list(lines_of(d.url)), k, k + width - 1):
                continue  # the earlier document states another balance date for the same line
            best = Row(**{**asdict(r), "filed": d.filed, "accepted": d.accepted, "form": d.form,
                          "accession": d.accession, "source_url": d.url, "locator": locator_of(k, k + width - 1)})
            break
        out.append(best)
    return out


# ------------------------------------------------------------------ build


def load_corpus(company: str) -> list[Doc]:
    return [Doc(**d) for d in json.loads((CORPUS_DIR / f"{company}.json").read_text())]


def build() -> list[Row]:
    """Every row from the cached corpus: CoreWeave's debt tables (parser) plus the agent's coding (kreditlagret_coding),
    the lab's rows moved to their earliest public document. Network only for documents not cached."""
    from ai_tracker.sources import kreditlagret_coding as coding

    rows: list[Row] = []
    for company, codes in coding.ALL.items():
        docs = {d.accession: d for d in load_corpus(company)}
        for c in codes:
            d = docs[c.accession]
            r = manual_row(d, doc_lines(d.url), c.locator, c.instrument, c.field, c.value, c.unit, c.period,
                           c.qualifier, c.note, c.rid)
            rows.append(r)
        if company == "anthropic":
            ordered = sorted(docs.values(), key=lambda d: (d.filed, d.accepted))
            moved = earliest([r for r in rows if r.company == "anthropic"], ordered)
            rows = [r for r in rows if r.company != "anthropic"] + moved
    for d in load_corpus("crwv"):
        if d.form in ("10-Q", "10-K"):
            rows += table_rows(d, doc_lines(d.url))
    ids = [r.id for r in rows]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise ValueError(f"duplicate row ids: {dup}")
    return rows


# ------------------------------------------------------------------ uncoded candidates (register X23, point 2)

SKIPPED_COLUMNS = ("company", "accession", "filed", "form", "locator", "kind", "reason", "reason_by")
EXHIBIT = re.compile(r"^\d+\.\d+\s*\|")
SKIP_RULES = (  # (pattern, reason), first match wins; applied after the agent's own reasons
    (re.compile(r"(?i)fair value|expenses?\b|\bincome\b|net loss|\blosses\b|loss on|accumulated deficit|revenue|"
                r"amortiz|issuance costs|\bdiscount\b|capitalized|cash (?:used|provided)"),
     "verkligt värde, kostnader, kassaflöde eller resultatposter: inte ett instrument"),
    (re.compile(r"(?i)\bpreferred\b|common stock|\bshares?\b|\bSAFEs?\b|stock-based|share-based|\bRS[AU]s?\b|"
                r"\bSeries [A-H]\b|equity awards?|capped call|conversion (?:rate|price)|"
                r"\bconvert(?:ed|s)? (?:their|at|into|in full)|put right|stockholders|shareholders|net tangible book"),
     "aktier, preferensaktier, SAFE, optioner eller konvertering till aktier: inte skuld"),
    (re.compile(r"(?i)\bredeem|redemption|repurchase|change of control|fundamental change|events? of default|"
                r"covenant|make-whole|prepa(?:y|id|yment)|\bswap\b|hedg|sinking fund|undrawn fees?|commitment fee"),
     "villkor utanför kodningsreglerna (inlösen, återköp, kovenanter, säkringar, avgifter, utfallshändelser)"),
    (re.compile(r"(?i)guarantee|guarantor|pledge|collateral"),
     "garanti eller säkerhet: fälten guarantor och collateral kodades inte för raden (ingen serie och ingen "
     "rapportrad använder dem)"),
)
PERIODIC_REASON = ("text eller tabell i 10-Q/10-K utanför skuldtabellen: balanserna kodas ur skuldtabellen och villkoren "
                   "ur 8-K (posten, Korpus); raden kan ange villkor för ett instrument utan eget 8-K")
TABLE_REASON = "rad i skuldtabellen som tolkningen inte kodar (delsumma, Less/Total eller inget utestående; tillägget punkt 3)"
NOT_ASSESSED = "inte bedömd rad för rad"


def _debt_table_span(lines: list[str]) -> tuple[int, int] | None:
    rows = debt_table(lines)
    start = next((k for k, line in enumerate(lines) if TABLE_START.match(line)), None)
    if start is None:
        return None
    end = start
    for k in range(start + 1, len(lines)):
        if " | " not in lines[k] and not SECTION.match(lines[k]):
            break
        end = k
    return (start, max([end] + [t.k for t in rows]))


def skip_reason(company: str, doc: Doc, k: int, line: str, agent: dict, table: tuple[int, int] | None) -> tuple[str, str]:
    """(reason, by) for an uncoded candidate line: the agent's own reason for the line, else the first rule."""
    if (doc.accession, f"line #{k}") in agent:
        return agent[(doc.accession, f"line #{k}")], "agent"
    if EXHIBIT.match(line):
        return "bilageförteckning", "regel"
    if company == "crwv" and doc.form in ("10-Q", "10-K") and table and table[0] <= k <= table[1]:
        return TABLE_REASON, "regel"
    for pat, reason in SKIP_RULES:
        if pat.search(line):
            return reason, "regel"
    if company == "crwv" and doc.form in ("10-Q", "10-K"):
        return PERIODIC_REASON, "regel"
    return NOT_ASSESSED, "ingen"


def skipped(csv_rows: pd.DataFrame | None = None) -> pd.DataFrame:
    """Every candidate line of the corpus that no coded row covers, with the reason (register X23, point 2). The lab's
    candidates are read in its source (the latest document); other companies in every corpus document."""
    from ai_tracker.sources import kreditlagret_coding as coding

    df = load() if csv_rows is None else csv_rows
    covered: dict[str, set[int]] = {}
    for r in df.itertuples(index=False):
        a, b = span(r.locator)
        covered.setdefault(r.accession, set()).update(range(a, b + 1))
    for codes in coding.ALL.values():
        for c in codes:
            a, b = span(c.locator)
            covered.setdefault(c.accession, set()).update(range(a, b + 1))
    out = []
    for company, kinds in CANDIDATE_KINDS.items():
        docs = sorted(load_corpus(company), key=lambda d: (d.filed, d.accepted))
        if company == "anthropic":
            docs = docs[-1:]
        for d in docs:
            lines = doc_lines(d.url)
            table = _debt_table_span(lines) if company == "crwv" and d.form in ("10-Q", "10-K") else None
            for k, kind, line in candidates(lines, kinds):
                if k in covered.get(d.accession, set()):
                    continue
                reason, by = skip_reason(company, d, k, line, coding.SKIP, table)
                out.append((company, d.accession, d.filed, d.form, f"line #{k}", kind, reason, by))
    return pd.DataFrame(out, columns=SKIPPED_COLUMNS)


def write_skipped(df: pd.DataFrame, path=SKIPPED_PATH) -> None:
    df.sort_values(["company", "filed", "accession"], kind="stable").to_csv(path, index=False, lineterminator="\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("corpus")
    c = sub.add_parser("candidates")
    c.add_argument("accession")
    c.add_argument("--company", default="crwv")
    sub.add_parser("openai")
    sub.add_parser("quotes")
    sub.add_parser("build")
    a = ap.parse_args()
    if a.cmd == "corpus":
        CORPUS_DIR.mkdir(parents=True, exist_ok=True)
        for co in CIKS:
            docs = corpus(co)
            (CORPUS_DIR / f"{co}.json").write_text(json.dumps([asdict(d) for d in docs], indent=1))
            for d in docs:
                n = len(doc_lines(d.url))
                print(f"{co:9s} {d.form:6s} {d.filed} {d.accession} {d.items:18s} {n:6d} lines")
    elif a.cmd == "candidates":
        docs = [Doc(**d) for d in json.loads((CORPUS_DIR / f"{a.company}.json").read_text())]
        d = next(d for d in docs if d.accession == a.accession)
        for k, kind, line in candidates(doc_lines(d.url)):
            print(f"#{k} [{kind}] {line[:600]}")
    elif a.cmd == "openai":
        res = openai_search()
        CORPUS_DIR.mkdir(parents=True, exist_ok=True)
        (CORPUS_DIR / "openai_search.json").write_text(json.dumps(
            {"searched": pd.Timestamp.now(tz="UTC").isoformat(), "url": COMPANY_SEARCH + "?company=openai&owner="
             "include&action=getcompany&output=atom&count=100", "matches": res}, indent=1))
        for m in res:
            print(m["cik"], m["name"], m["registration"], ",".join(m["forms"]))
    elif a.cmd == "quotes":
        print(rebuild_quotes(), "quotes written")
    elif a.cmd == "build":
        rows = build()
        write(rows)
        errors = validate(load())
        print(f"wrote {len(rows)} rows to {CSV_PATH}" + (f"; {len(errors)} problems" if errors else ""))
        sk = skipped()
        write_skipped(sk)
        print(f"wrote {len(sk)} uncoded candidates to {SKIPPED_PATH} "
              f"({(sk['reason_by'] == 'ingen').sum()} not assessed)")


if __name__ == "__main__":
    main()
