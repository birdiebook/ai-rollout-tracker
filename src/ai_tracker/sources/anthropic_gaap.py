"""AN1: Anthropic's reported (GAAP) revenue and results from its registration statement (register 2026-11-27 "AN1").

Corpus (entry, (a)): Anthropic, PBC (CIK 2130357), every S-1, S-1/A and 424B4 filed up to LAST, main document only. Never
DRS/DRS-A (EDGAR dates them by the confidential submission), never FWP. The prospectuses carry XBRL for the cover page
only, so the HTML tables are read, deterministically (entry, (d)):

    table        title line (exact)                                   columns                       kind
    quarterly    Quarterly Consolidated Statements of Operations      "Three Months Ended <date>"   q
    operations   Consolidated Statements of Operations                years, then six/nine months   a, ytd
    function     Supplemental Operating Expense Information           years, then six/nine months   a, ytd
    cashflows    Consolidated Statements of Cash Flows                years, then six/nine months   a, ytd
    summary      Consolidated Statements of Operations Data           as operations (cross-check)   a, ytd

A table is found on its title line (exactly one per document), its periods on the header lines below it and a row on
its label (exact text, a trailing footnote marker "(n)" ignored). A cell is read without judgement: "$" and thousands
commas dropped, parentheses negative, "—" zero. A missing table, column or row, or a row with the wrong number of cells,
raises ParseError: nothing is guessed.

Text and location: KR1's line list (credit_issuance_corpus.lines). The locator names the header lines and the row line,
"lines #a,#b,#k col #j" (j counts the value cells from 0), and the quote is those lines verbatim, joined by newlines;
quote_sha256 = credit_issuance_corpus.block_hash(lines). The quote lives only under data/raw (gitignored), the CSV
holds numbers and references. Every value of every document is a row; the series (series/anthropic_gaap.py) take the
first document that states a value and every later one that changes it (entry, (c)).

    python -m ai_tracker.sources.anthropic_gaap build     # parse the corpus -> curated/anthropic_gaap.csv + quotes
    python -m ai_tracker.sources.anthropic_gaap sums      # the sum checks of the entry, (e) 3

SEC: the generic client identity from the environment (ai_tracker.http), one request at a time, stop on 403/429
(sources.kreditlagret.fetch, whose cache of these immutable archive documents is shared).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass

import pandas as pd

from ai_tracker import config
from ai_tracker.sources import credit_issuance_corpus as cc
from ai_tracker.sources import kreditlagret as kl

CIK = 2130357
LAST = "2026-11-27"  # filings up to this day (entry, (a))
FORMS = ("S-1", "S-1/A", "424B4")
REFUSED_FORMS = ("DRS", "DRS/A")
CSV_PATH = config.REPO / "curated" / "anthropic_gaap.csv"
QUOTES_DIR = config.REPO / "data" / "raw" / "anthropic_gaap_quotes"  # gitignored

COLUMNS = ("id", "company", "series", "item", "table", "kind", "period", "period_end", "value", "unit", "form",
           "filed", "accepted", "accession", "source_url", "page", "locator", "quote_sha256", "note")

TITLES = {
    "quarterly": "Quarterly Consolidated Statements of Operations",
    "operations": "Consolidated Statements of Operations",
    "function": "Supplemental Operating Expense Information",
    "cashflows": "Consolidated Statements of Cash Flows",
    "summary": "Consolidated Statements of Operations Data",
}
# item -> (table, accepted labels, sign): sign -1 turns a stated outflow "(x)" into a positive amount (entry, (b) 5)
ITEMS = {
    "revenue": (("quarterly", "operations", "summary"), ("Revenue",), 1),
    "compute": (("quarterly", "operations"), ("Compute and infrastructure",), 1),
    "opinc": (("quarterly", "operations"), ("Operating income (loss)", "Operating loss", "Operating income"), 1),
    "cost_of_revenue": (("function",), ("Cost of revenue",), 1),
    "cfo": (("cashflows",), ("Net cash provided by (used in) operating activities",
                             "Net cash used in operating activities", "Net cash provided by operating activities"), 1),
    "capex": (("cashflows",), ("Purchases of property and equipment",), -1),
    "prepay_leased": (("cashflows",), ("Prepayments for leased assets and equipment",), -1),
}
# (accession, item): the document does not present the row. Listed by hand after a ParseError, checked to be absent
# (the build fails if the row appears), and logged in the register addendum 2026-11-27 AN1 (tillägg). Never inferred.
ABSENT = {
    ("0001628280-26-067168", "prepay_leased"): "the S-1's cash flow statement has no line 'Prepayments for leased "
                                               "assets and equipment' (first in the S-1/A of 2026-11-02)",
}
SERIES_TABLE = {"quarterly": {"q"}, "operations": {"a", "ytd"}, "function": {"a", "ytd"}, "cashflows": {"a", "ytd"}}
SEARCH = 70  # lines after the header within which a row must be found
END = re.compile(r"^(The accompanying notes|Table of Contents$)")
PAGE = re.compile(r"^(F-\d+|\d{1,3})$")
FOOTNOTE = re.compile(r"\s*\(\d\)$")
MONTHS = {m: i for i, m in enumerate(("January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"), 1)}
DATE = re.compile(r"^(January|February|March|April|May|June|July|August|September|October|November|December) "
                  r"(\d{1,2}), (\d{4})$")
YTD = re.compile(r"^(Six|Nine|Three) Months Ended (June|September|March) (\d{1,2}),?$")
YEAR_GROUP = re.compile(r"^Year Ended December 31,?$")
CELL = re.compile(r"^\$?\s*(\()?\s*(\d[\d,]*(?:\.\d+)?)\s*(\))?$")


class ParseError(ValueError):
    pass


@dataclass(frozen=True)
class Doc:
    form: str
    filed: str
    accepted: str
    accession: str
    url: str


@dataclass(frozen=True)
class Column:
    kind: str  # q, a, ytd
    period: str  # 2025Q1, 2025, 2026Q3 (ytd: the quarter the period ends in)
    period_end: str  # YYYY-MM-DD


# ------------------------------------------------------------------ corpus


def in_corpus(f: dict) -> bool:
    return f["form"] in FORMS and f["filed"] <= LAST


def corpus(subs: list[dict] | None = None) -> list[Doc]:
    subs = kl.submissions(CIK) if subs is None else subs
    out = []
    for f in subs:
        if f["form"] in REFUSED_FORMS or not in_corpus(f):
            continue
        out.append(Doc(f["form"], f["filed"], f["accepted"], f["accession"],
                       kl.ARCHIVE.format(cik=CIK, folder=f["accession"].replace("-", ""), doc=f["primary"])))
    return out


# ------------------------------------------------------------------ cells and headers


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.split("|")]


def label(line: str) -> str:
    return FOOTNOTE.sub("", cells(line)[0]).strip()


def parse_cell(text: str) -> float:
    """A table cell as a number: "$ 1,382" -> 1382, "(935)" -> -935, "—" -> 0. Anything else raises ParseError."""
    t = text.replace("$", " ").strip()
    if t in ("—", "–", "-"):
        return 0.0
    m = CELL.match(t)
    if not m or bool(m.group(1)) != bool(m.group(3)):
        raise ParseError(f"cell {text!r} is not a number")
    v = float(m.group(2).replace(",", ""))
    return -v if m.group(1) else v


def _quarter(month: int, year: int) -> str:
    return f"{year}Q{(month - 1) // 3 + 1}"


def _date(month: int, day: int, year: int) -> str:
    return f"{year:04d}-{month:02d}-{day:02d}"


def quarterly_header(lines: list[str], start: int) -> tuple[list[int], list[Column]]:
    """The "(in millions) | March 31, 2025 | ..." line within 3 lines after `start` ("Three Months Ended" above it)."""
    for k in range(start + 1, min(start + 4, len(lines))):
        cs = cells(lines[k])
        if len(cs) > 1 and all(DATE.match(c) for c in cs[1:]):
            if not any(lines[j] == "Three Months Ended" for j in range(start + 1, k)):
                raise ParseError(f"line {k}: no 'Three Months Ended' above the dates")
            cols = []
            for c in cs[1:]:
                m = DATE.match(c)
                mo, d, y = MONTHS[m.group(1)], int(m.group(2)), int(m.group(3))
                cols.append(Column("q", _quarter(mo, y), _date(mo, d, y)))
            return [k], cols
    raise ParseError(f"no quarter header after line {start}")


def statement_header(lines: list[str], start: int) -> tuple[list[int], list[Column]]:
    """Group line "Year Ended December 31, | Six/Nine Months Ended June 30/September 30," and the years below it (the
    years may share a line with a leading label cell, as in the summary table). The years rise within a group, and the
    second group starts where they stop rising."""
    for g in range(start + 1, min(start + 5, len(lines))):
        groups = cells(lines[g])
        if len(groups) == 2 and YEAR_GROUP.match(groups[0]) and YTD.match(groups[1]):
            y = g + 1
            ys = cells(lines[y])
            if ys and not re.fullmatch(r"\d{4}", ys[0]):
                ys = ys[1:]
            if not ys or not all(re.fullmatch(r"\d{4}", c) for c in ys):
                raise ParseError(f"line {y}: years expected, got {lines[y]!r}")
            years = [int(c) for c in ys]
            split = next((i for i in range(1, len(years)) if years[i] <= years[i - 1]), None)
            if split is None:
                raise ParseError(f"line {y}: no second column group in {years}")
            m = YTD.match(groups[1])
            mo, d = MONTHS[m.group(2)], int(m.group(3))
            n_months = {"Three": 3, "Six": 6, "Nine": 9}[m.group(1)]
            if n_months != mo:
                raise ParseError(f"line {g}: {groups[1]!r} does not start in January")
            cols = [Column("a", str(yr), _date(12, 31, yr)) for yr in years[:split]]
            cols += [Column("ytd", _quarter(mo, yr), _date(mo, d, yr)) for yr in years[split:]]
            return [g, y], cols
    raise ParseError(f"no statement header after line {start}")


def find_title(lines: list[str], table: str) -> int:
    hits = [k for k, x in enumerate(lines) if x == TITLES[table]]
    if len(hits) != 1:
        raise ParseError(f"{TITLES[table]!r}: {len(hits)} title lines, expected exactly 1")
    return hits[0]


def find_row(lines: list[str], header_end: int, labels: tuple[str, ...]) -> int:
    for k in range(header_end + 1, min(header_end + 1 + SEARCH, len(lines))):
        if END.match(lines[k]):
            break
        if "|" in lines[k] and label(lines[k]) in labels:
            return k
    raise ParseError(f"row {labels[0]!r} not found after line {header_end}")


def page_after(lines: list[str], k: int) -> str:
    for j in range(k + 1, min(k + 120, len(lines))):
        if PAGE.match(lines[j]):
            return lines[j]
    return ""


# ------------------------------------------------------------------ rows


def series_key(item: str, kind: str) -> str:
    return f"lab_gaap_anthropic_{item}_{kind}"


def locator_of(header: list[int], row: int, col: int) -> str:
    return "lines " + ",".join(f"#{k}" for k in (*header, row)) + f" col #{col}"


LOCATOR = re.compile(r"^lines ((?:#\d+,)*#\d+) col #(\d+)$")


def parse_locator(locator: str) -> tuple[list[int], int]:
    m = LOCATOR.match(locator)
    if not m:
        raise ValueError(f"bad locator {locator!r}")
    return [int(x) for x in m.group(1).replace("#", "").split(",")], int(m.group(2))


def quote_at(lines: list[str], locator: str) -> str | None:
    ks, _ = parse_locator(locator)
    if max(ks) >= len(lines):
        return None
    return "\n".join(lines[k] for k in ks)


def quote_hash(quote: str) -> str:
    return cc.block_hash(quote.split("\n"))


def cell_value(lines: list[str], locator: str, sign: int = 1) -> float:
    """The value at a locator: cell j of the row line (the last line), with the item's sign."""
    ks, j = parse_locator(locator)
    cs = cells(lines[ks[-1]])[1:]
    return sign * parse_cell(cs[j])


def parse_table(lines: list[str], table: str, items: list[str], absent: tuple[str, ...] = ()) -> list[dict]:
    """Values of `items` in `table`: one dict per (item, column) with the locator, quote and page. An item in `absent`
    must not be found (ABSENT); it gives no values."""
    t = find_title(lines, table)
    header, cols = (quarterly_header if table == "quarterly" else statement_header)(lines, t)
    out = []
    for item in items:
        _, labels, sign = ITEMS[item]
        if item in absent:
            try:
                k = find_row(lines, header[-1], labels)
            except ParseError:
                continue
            raise ParseError(f"line {k}: {item} is listed as absent but the row is there")
        k = find_row(lines, header[-1], labels)
        cs = cells(lines[k])[1:]
        if len(cs) != len(cols):
            raise ParseError(f"line {k} ({item}): {len(cs)} cells, {len(cols)} columns")
        page = page_after(lines, k)
        for j, col in enumerate(cols):
            loc = locator_of(header, k, j)
            quote = quote_at(lines, loc)
            out.append({"item": item, "table": table, "kind": col.kind, "period": col.period,
                        "period_end": col.period_end, "value": sign * parse_cell(cs[j]), "page": page,
                        "locator": loc, "quote": quote, "quote_sha256": quote_hash(quote),
                        "label": label(lines[k])})
    return out


def parse_doc(lines: list[str], accession: str = "") -> list[dict]:
    """Every registered value of one document (entry, (b)) plus the summary table's revenue (cross-check only)."""
    absent = tuple(i for (acc, i) in ABSENT if acc == accession)
    out = []
    for table in ("quarterly", "operations", "function", "cashflows", "summary"):
        items = [i for i, (tables, _, _) in ITEMS.items() if table in tables]
        out += parse_table(lines, table, items, absent)
    return out


def _fmt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else repr(float(v))


def rows_for(doc: Doc, lines: list[str]) -> list[dict]:
    out = []
    for r in parse_doc(lines, doc.accession):
        sid = series_key(r["item"], r["kind"]) if r["kind"] in SERIES_TABLE.get(r["table"], ()) else ""
        note = "cross-check only (summary table)" if r["table"] == "summary" else ""
        if r["label"] != ITEMS[r["item"]][1][0]:
            note = (note + "; " if note else "") + f"label: {r['label']}"
        if ITEMS[r["item"]][2] < 0:
            note = (note + "; " if note else "") + "stated as an outflow, sign reversed"
        out.append({"id": f"{doc.accession}-{r['table']}-{r['item']}-{r['kind']}-{r['period']}", "company": "anthropic",
                    "series": sid, "item": r["item"], "table": r["table"], "kind": r["kind"], "period": r["period"],
                    "period_end": r["period_end"], "value": _fmt(r["value"]), "unit": "MUSD", "form": doc.form,
                    "filed": doc.filed, "accepted": doc.accepted, "accession": doc.accession, "source_url": doc.url,
                    "page": r["page"], "locator": r["locator"], "quote_sha256": r["quote_sha256"], "note": note,
                    "_quote": r["quote"]})
    return out


def build(docs: list[Doc] | None = None, reuse: bool = True) -> pd.DataFrame:
    docs = corpus() if docs is None else docs
    rows = []
    for d in docs:
        rows += rows_for(d, kl.doc_lines(d.url, reuse=reuse))
    return pd.DataFrame(rows)


def write(df: pd.DataFrame) -> None:
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    df[list(COLUMNS)].to_csv(CSV_PATH, index=False, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    QUOTES_DIR.mkdir(parents=True, exist_ok=True)
    quotes = {r["id"]: r["_quote"] for r in df.to_dict("records")}
    (QUOTES_DIR / "quotes.json").write_text(json.dumps(quotes, ensure_ascii=False, indent=1), encoding="utf-8")


def load(path=None) -> pd.DataFrame:
    df = pd.read_csv(path or CSV_PATH, dtype=str, keep_default_na=False)
    if tuple(df.columns) != COLUMNS:
        raise ValueError(f"columns {tuple(df.columns)} != {COLUMNS}")
    df["value"] = df["value"].astype(float)
    return df


def validate(df: pd.DataFrame) -> list[str]:
    errors = []
    if df["id"].duplicated().any():
        errors.append(f"duplicate ids: {sorted(df.loc[df['id'].duplicated(), 'id'])[:3]}")
    if (df["form"].isin(REFUSED_FORMS)).any() or not df["form"].isin(FORMS).all():
        errors.append("a row comes from a form outside the corpus")
    if not df["source_url"].str.startswith("https://www.sec.gov/Archives/edgar/data/2130357/").all():
        errors.append("a row's source_url is not Anthropic's EDGAR archive")
    if (df["filed"] > LAST).any():
        errors.append(f"a row is filed after {LAST}")
    for r in df.itertuples(index=False):
        try:
            parse_locator(r.locator)
        except ValueError as exc:
            errors.append(f"{r.id}: {exc}")
        if not re.fullmatch(r"[0-9a-f]{64}", r.quote_sha256):
            errors.append(f"{r.id}: bad quote_sha256")
        if r.series and r.series != series_key(r.item, r.kind):
            errors.append(f"{r.id}: series {r.series} != {series_key(r.item, r.kind)}")
    return errors


# ------------------------------------------------------------------ versions (entry, (c))


def versions(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """Release-dated rows (period, value, known_from) of one series: the first document stating a value, then every
    later document that changes it. A value a later document no longer has keeps its last version."""
    if key.startswith("lab_gaap_anthropic_gross_profit_"):
        kind = key.rsplit("_", 1)[1]
        d = gross_profit(df, kind)
    else:
        d = df[df["series"] == key]
    rows = []
    for period, g in d.sort_values(["filed", "accepted"]).groupby("period", sort=True):
        last = None
        for r in g.itertuples(index=False):
            if last is None or r.value != last:
                rows.append((period, float(r.value), pd.Timestamp(r.filed)))
                last = r.value
    return pd.DataFrame(rows, columns=["period", "value", "known_from"])


def gross_profit(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    """Revenue minus cost of revenue, same document and column (entry, (b) 4): derived, never stated."""
    rev = df[df["series"] == series_key("revenue", kind)].set_index(["accession", "period"])
    cor = df[df["series"] == series_key("cost_of_revenue", kind)].set_index(["accession", "period"])
    both = rev.join(cor[["value"]], rsuffix="_cor", how="inner")
    out = both.reset_index()[["accession", "period", "filed", "accepted"]].copy()
    out["value"] = (both["value"] - both["value_cor"]).to_numpy()
    return out


# ------------------------------------------------------------------ sum checks (entry, (e) 3)


def latest_values(df: pd.DataFrame) -> dict[tuple[str, str], float]:
    """{(series, period): value} from the latest document stating it."""
    d = df[df["series"] != ""].sort_values(["filed", "accepted"])
    return {(r.series, r.period): float(r.value) for r in d.itertuples(index=False)}


def sum_checks(df: pd.DataFrame) -> list[dict]:
    """Quarters against the year and the year to date, per document and item, tolerance 1 MUSD per quarter summed;
    and the summary table's revenue against the statement's, per document and column."""
    out = []
    for acc, g in df.groupby("accession", sort=False):
        form, filed = g["form"].iloc[0], g["filed"].iloc[0]
        val = {(r.item, r.table, r.kind, r.period): float(r.value) for r in g.itertuples(index=False)}
        for item in ("revenue", "compute", "opinc"):
            qs = {p: v for (i, t, k, p), v in val.items() if i == item and t == "quarterly"}
            for (i, t, k, p), v in val.items():
                if i != item or t != "operations" or k not in ("a", "ytd"):
                    continue
                year = int(p[:4])
                n = 4 if k == "a" else int(p[-1])
                parts = [f"{year}Q{j}" for j in range(1, n + 1)]
                if not all(x in qs for x in parts):
                    continue
                s = sum(qs[x] for x in parts)
                out.append({"accession": acc, "form": form, "filed": filed, "item": item, "check": f"{'+'.join(parts)} = {k} {p}",
                            "sum": s, "stated": v, "diff": s - v, "ok": abs(s - v) <= n})
        for (i, t, k, p), v in val.items():
            if i == "revenue" and t == "summary":
                ref = val.get(("revenue", "operations", k, p))
                if ref is not None:
                    out.append({"accession": acc, "form": form, "filed": filed, "item": "revenue",
                                "check": f"summary = statement, {k} {p}", "sum": v, "stated": ref, "diff": v - ref,
                                "ok": v == ref})
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m ai_tracker.sources.anthropic_gaap")
    ap.add_argument("command", choices=("build", "sums"))
    args = ap.parse_args(argv)
    if args.command == "build":
        df = build()
        errs = validate(df)
        if errs:
            raise SystemExit("\n".join(errs))
        write(df)
        print(f"{len(df)} rows from {df['accession'].nunique()} documents -> {CSV_PATH}")
    else:
        checks = sum_checks(load())
        for c in checks:
            print(f"{'ok ' if c['ok'] else 'DIFF'} {c['form']:6} {c['filed']} {c['item']:8} {c['check']:34} "
                  f"sum {c['sum']:>10,.0f} stated {c['stated']:>10,.0f} diff {c['diff']:+.0f}")
        bad = [c for c in checks if not c["ok"]]
        print(f"{len(checks)} checks, {len(bad)} outside the tolerance")


if __name__ == "__main__":
    main()
