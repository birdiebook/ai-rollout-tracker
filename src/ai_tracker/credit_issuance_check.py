"""Self-check of the KR1 extraction: re-fetch each source document and verify the row is there (no cache).

For each sampled row of curated/credit_issuance.csv (all rows by default: the documents are few):
- the block at the locator (credit_issuance_corpus.block_at) has the stored SHA-256; if not, every window of the same
  length in the document is searched for the hash ("moved");
- every number of the row is in the block: principal as the stated amount ("$1,250,000,000", "€750,000,000",
  "$1.25 billion"), coupon, yield, benchmark yield and price as percentages, spread as basis points ("T + 45",
  "+45 basis points") or as a percentage ("0.45%"), and maturity, pricing and settlement dates as written dates;
- a row coded by the parser (method "parser") gets the same values when the parser reads the document again;
- filed and accepted equal EDGAR's filingDate and acceptanceDateTime (submissions API, fetched again);
- yield = benchmark yield + spread within YIELD_TOL (1 bp) when all three are stated.
A manual row's stated exception (the note) is reported as "manual" with the numbers that are not in the block.

    python -m ai_tracker.credit_issuance_check [--frac 1.0] [--seed 20261125]

This confirms location, hash, numbers and dates, not the semantics (which document is the source, the benchmark,
currency and rate type): that is for the independent review. Nothing is written except raw copies (data/raw).
"""

from __future__ import annotations

import argparse
import re
import time

import pandas as pd

from ai_tracker import http
from ai_tracker.sources import credit_issuance as ci
from ai_tracker.sources import credit_issuance_corpus as cc
from ai_tracker.sources import credit_terms as ct

SOURCE = "credit_issuance_check"
OK = ("ok", "moved")
SYMBOL = {"USD": r"(?:US)?\$", "EUR": "€", "GBP": "£", "JPY": "¥", "CAD": r"C\$", "AUD": r"A\$", "CHF": "CHF"}
COMPARED = ("currency", "rate_type", "principal", "pricing_date", "settlement_date", "maturity", "coupon_pct",
            "benchmark_type", "benchmark_yield_pct", "spread_bp", "yield_pct", "price_pct")


def _num_re(x: float) -> str:
    """A number as written, with optional trailing zeros: 4.85 matches 4.850, 25 matches 25 and 25.0."""
    s = f"{x:.6f}".rstrip("0").rstrip(".")
    return rf"(?<![\d.]){re.escape(s)}" + (r"0*" if "." in s else r"(?:\.0+)?") + r"(?![\d])"


def amount_patterns(currency: str, millions: float) -> list[str]:
    sym = SYMBOL.get(currency, re.escape(currency))
    full = f"{int(round(millions * 1e6)):,}"
    bn = millions / 1000
    return [rf"{sym}\s?{re.escape(full)}(?![\d,])", rf"{sym}\s?{_num_re(bn)}\s*billion", rf"{sym}\s?{_num_re(millions)}\s*million"]


def date_patterns(day: str) -> list[str]:
    t = pd.Timestamp(day)
    return [rf"{t.strftime('%B')}\s+{t.day}\s*,\s*{t.year}"]


def spread_patterns(bp: float) -> list[str]:
    return [rf"T\s*\+\s*{_num_re(bp)}", rf"{_num_re(bp)}\s*(?:bps|bp|basis\s+points)", rf"{_num_re(bp / 100)}\s?%"]


def missing_numbers(row: pd.Series, text: str) -> list[str]:
    """Columns whose value is not written in the block text."""
    miss = []
    checks: list[tuple[str, list[str]]] = [("principal", amount_patterns(row["currency"], row["principal"])),
                                           ("maturity", date_patterns(row["maturity"]))]
    for c in ("coupon_pct", "yield_pct", "benchmark_yield_pct", "price_pct"):
        if pd.notna(row[c]):
            checks.append((c, [_num_re(row[c]) + r"\s?%"]))
    if pd.notna(row["spread_bp"]):
        checks.append(("spread_bp", spread_patterns(row["spread_bp"])))
    for c in ("pricing_date", "settlement_date"):
        if isinstance(row[c], str) and row[c] and "computed" not in row["note"] and "pricing date from" not in row["note"]:
            checks.append((c, date_patterns(row[c])))
    for col, pats in checks:
        if not any(re.search(p, text, re.I) for p in pats):
            miss.append(col)
    return miss


def _same(a, b) -> bool:
    if (a is None or (isinstance(a, float) and pd.isna(a)) or a == "") and (b is None or b == ""):
        return True
    try:
        return abs(float(a) - float(b)) < 1e-6
    except (TypeError, ValueError):
        return str(a) == str(b)


def reparse_differs(row: pd.Series, doc_lines: list[str]) -> list[str]:
    """Columns where a fresh parse of the document differs from the row (parser rows only)."""
    _, parsed = ct.parse(doc_lines, row["filed"])
    match = [p for p in parsed if ci.locator(p) == row["locator"] and p["security"] == row["security"]]
    if not match:
        return ["tranche_not_parsed"]
    p = match[0]
    return [c for c in COMPARED if not _same(row[c], p[c])]


def check_row(row: pd.Series, doc_lines: list[str]) -> tuple[str, list[str]]:
    """(status, details): status 'ok' | 'moved' | 'block_not_found' | 'number_not_in_block' | 'parse_differs' |
    'yield_gap' | 'manual'."""
    block, _ = cc.block_at(doc_lines, row["locator"])
    status = "ok"
    if cc.block_hash(block) != row["block_sha256"]:
        n = len(block)
        hits = [doc_lines[i:i + n] for i in range(0, max(0, len(doc_lines) - n + 1))
                if cc.block_hash(doc_lines[i:i + n]) == row["block_sha256"]]
        if not hits:
            return "block_not_found", []
        block, status = hits[0], "moved"
    text = "\n".join(block)
    miss = missing_numbers(row, text)
    if row["method"] == "manual":
        return "manual", miss
    if miss:
        return "number_not_in_block", miss
    diff = reparse_differs(row, doc_lines) if status == "ok" else []
    if diff:
        return "parse_differs", diff
    if all(pd.notna(row[c]) for c in ("yield_pct", "benchmark_yield_pct", "spread_bp")):
        if abs(row["yield_pct"] - row["benchmark_yield_pct"] - row["spread_bp"] / 100) > ci.YIELD_TOL + 1e-9:
            return "yield_gap", [f"{row['yield_pct']} vs {row['benchmark_yield_pct']} + {row['spread_bp']} bp"]
    return status, []


def check_dates(row: pd.Series, filings: dict[str, dict]) -> str:
    f = filings.get(row["accession"])
    if f is None:
        return "accession_not_in_submissions"
    if f["filed"] != row["filed"]:
        return f"filed_differs: {f['filed']}"
    if row["accepted"] and f["accepted"][:19] != row["accepted"][:19]:
        return f"accepted_differs: {f['accepted']}"
    return "ok"


def fetch_lines(url: str) -> list[str]:
    return cc.lines(http.get(url, SOURCE).content.decode("utf-8", errors="replace"))


def run(frac: float = 1.0, seed: int = 20261125) -> pd.DataFrame:
    df = ci.load()
    sample = df.sample(frac=frac, random_state=seed).sort_values("id") if frac < 1 else df.sort_values("id")
    docs: dict[str, list[str]] = {}
    subs: dict[str, dict] = {}
    res = []
    for _, row in sample.iterrows():  # sequential: several tracks share sec.gov's rate limit
        try:
            if row["company"] not in subs:
                subs[row["company"]] = {f["accession"]: f for f in cc.submissions(row["company"], SOURCE)}
            dates = check_dates(row, subs[row["company"]])
            if row["source_url"] not in docs:
                docs[row["source_url"]] = fetch_lines(row["source_url"])
                time.sleep(cc.BULK_SLEEP)
            status, details = check_row(row, docs[row["source_url"]])
        except Exception as exc:  # noqa: BLE001 - a failed fetch is reported, not hidden
            status, details, dates = f"fetch_failed: {type(exc).__name__}", [], "not_checked"
        res.append((row["id"], row["method"], status, ",".join(details), dates))
    return pd.DataFrame(res, columns=["id", "method", "status", "details", "dates"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frac", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=20261125)
    a = ap.parse_args()
    res = run(a.frac, a.seed)
    for r in res.itertuples(index=False):
        if r.status not in OK or r.dates != "ok":
            print(f"{r.id:24s} {r.method:7s} {r.status:22s} {r.details:30s} {r.dates}")
    bad = ~res["status"].isin(OK + ("manual",)) | (res["dates"] != "ok")
    print(f"{len(res)} checked, {int(bad.sum())} errors, {int((res['status'] == 'moved').sum())} moved, "
          f"{int((res['status'] == 'manual').sum())} manual (see notes)")


if __name__ == "__main__":
    main()
