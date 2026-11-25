"""Self-check of the KR1 extraction: re-fetch each source document and verify the row is there (no cache).

For each sampled row of curated/credit_issuance.csv (all rows by default: the documents are few):
- the block at the locator (credit_issuance_corpus.block_at) has the stored SHA-256; if not, every window of the same
  length in the document is searched for the hash ("moved");
- every number of the row is in the tranche's part of the block ("i kolumnen när den anges", register 2026-11-25,
  X17): principal as the stated amount ("$1,250,000,000", "€750,000,000", "$1.25 billion"), coupon, yield,
  benchmark yield and price as percentages, spread as basis points ("T + 45", "+45 basis points") or as a percentage
  ("0.45%"), and the maturity as a written date; the pricing and settlement dates may also be on a line of the block
  without a tranche key (they apply to the whole offering). The tranche's part (tranche_text) is the whole block for a
  section, the text after the tranche's key for col #j in a keyed table, and cell j for a column table;
- a row coded by the parser (method "parser") gets the same values when the parser reads the document again;
- filed and accepted equal EDGAR's filingDate and acceptanceDateTime (submissions API, fetched again);
- yield = benchmark yield + spread within YIELD_TOL (1 bp) when all three are stated.
A manual row's stated exception (the note) is reported as "manual" with the numbers that are not in the block.

With --covers, every offering is also compared with the cover of its final prospectus supplement (the 424B2/424B5 of
the same company filed 0-7 days after the FWP): the set of (currency, principal, coupon or floating, maturity year)
must be the same. The final supplement is an independent document, so this checks the term sheet itself. The reverse
check: every final supplement in the corpus with debt tranches on its cover must have a source in the CSV
(credit_issuance.source_of), so an offering without a term sheet cannot drop out unnoticed.

    python -m ai_tracker.credit_issuance_check [--frac 1.0] [--seed 20261125] [--covers]

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


MENTION_RE = re.compile(r"(?i)\bthe\s+[\"“]?$")  # "the 2028 Notes" only mentions a tranche


def _keyed_line(line: str, keys: list[str]) -> bool:
    """The line's value (after the label, or the whole continuation line) begins with a tranche key, or with "In the
    case of the <key>": a keyed value. Other lines only mention tranches."""
    v = (line.split(" | ", 1)[1] if " | " in line else line).lstrip()
    alt = "|".join(re.escape(k) for k in keys)
    return bool(re.match(rf"(?:{alt})(?![\w-])", v) or re.match(rf"(?i)in\s+the\s+case\s+of\s+(?:the\s+)?(?:{alt})", v))


def _openings(line: str, keys: list[str]) -> list[tuple[int, int, str]]:
    """(start, end, key) where a tranche's text opens on a keyed line: "<key>" with an optional colon, or "in the case
    of (the) <key>". A key after "the" only mentions the tranche and opens nothing. Longest keys first, so "2028 Notes"
    is not found inside "2028 Floating Rate Notes". A line that is not keyed has no openings."""
    if not _keyed_line(line, keys):
        return []
    spans: list[tuple[int, int, str]] = []
    for k in sorted(keys, key=len, reverse=True):
        for pat, mention_ok in ((rf"(?i)\bin\s+the\s+case\s+of\s+(?:the\s+)?{re.escape(k)}(?![\w-])", True),
                                (rf"(?<![\w-]){re.escape(k)}(?![\w-])\s*:?", False)):
            for m in re.finditer(pat, line):
                if not mention_ok and MENTION_RE.search(line[:m.start()]):
                    continue
                if not any(m.start() < e and s < m.end() for s, e, _ in spans):
                    spans.append((m.start(), m.end(), k))
    return sorted(spans)


def tranche_text(block: list[str], col: int | None) -> tuple[str, str] | None:
    """(the tranche's own text, the block's lines without a tranche key) for a block and the locator's column.

    No column: a section is the tranche's own block. col #j with tranche keys (interpretation 2): key j of the parser's
    key list (credit_terms.keys_of, which defines j), and its text is everything after an opening of key j up to the
    next opening or the end of the line, on every keyed line of the block (_openings); the other lines are general.
    col #j without keys: a column table, and the text is cell j of every row with as many value cells as the
    principal row. None when the block has no column j."""
    if col is None:
        return "\n".join(block), ""
    own: list[str] = []
    general: list[str] = []
    keys = ct.keys_of(ct.fields(block))
    if keys:
        if col >= len(keys):
            return None
        for line in block:
            spans = _openings(line, keys)
            if not spans:
                general.append(line)
            for i, (_, e, k) in enumerate(spans):
                if k == keys[col]:
                    own.append(line[e:spans[i + 1][0] if i + 1 < len(spans) else len(line)].strip())
        return "\n".join(own), "\n".join(general)
    cells = [line.split(" | ") for line in block]
    n = max((len([c for c in cs[1:] if ct.money(c)]) for cs in cells if ct.field_name(cs[0]) == "principal"),
            default=0)
    if col >= n:
        return None
    for line, cs in zip(block, cells):
        if len(cs) - 1 == n:
            own.append(cs[1 + col])
        else:
            general.append(line)
    return "\n".join(own), "\n".join(general)


def missing_numbers(row: pd.Series, text: str, general: str = "") -> list[str]:
    """Columns whose value is not written in the tranche's text; the pricing and settlement dates may also be in
    `general` (lines of the block without a tranche key)."""
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
        where = text + "\n" + general if col in ("pricing_date", "settlement_date") else text
        if not any(re.search(p, where, re.I) for p in pats):
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
    """(status, details): status 'ok' | 'moved' | 'block_not_found' | 'column_not_found' | 'number_not_in_block' |
    'parse_differs' | 'yield_gap' | 'manual'. Numbers are looked for in the tranche's part of the block
    (tranche_text)."""
    block, col = cc.block_at(doc_lines, row["locator"])
    status = "ok"
    if cc.block_hash(block) != row["block_sha256"]:
        n = len(block)
        hits = [doc_lines[i:i + n] for i in range(0, max(0, len(doc_lines) - n + 1))
                if cc.block_hash(doc_lines[i:i + n]) == row["block_sha256"]]
        if not hits:
            return "block_not_found", []
        block, status = hits[0], "moved"
    parts = tranche_text(block, col)
    if parts is None:
        return "column_not_found", []
    miss = missing_numbers(row, *parts)
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


COVER_RE = ci.COVER_RE
cover_tranches = ci.cover_tranches


def row_tranches(rows: pd.DataFrame) -> set[tuple]:
    return ci.offering_tranches(rows.to_dict("records"))


def covers(fetch=None, submissions=None) -> pd.DataFrame:
    """Both directions between the sources and the final prospectus supplements (424B2/424B5).

    check "source": each offering (source document) against the best-matching final supplement filed 0-7 days later
    (status ok, differs or no_final_supplement). check "supplement": each final supplement in the corpus with debt
    tranches on its cover against the sources (status ok when the CSV has a source for its offering, else no_source)."""
    fetch = fetch or fetch_lines
    submissions = submissions or (lambda co: cc.submissions(co, SOURCE))
    df = ci.load()
    out = []
    for co in ci.COMPANIES:
        g = df[df["company"] == co]
        subs = submissions(co)
        finals = [f for f in subs if f["form"] in ci.SUPPLEMENTS]
        fetched: dict[str, list[str]] = {}

        def lines_of(f: dict, co: str = co, fetched: dict = fetched) -> list[str]:
            u = cc.ARCHIVE.format(cik=cc.CIKS[co], folder=f["accession"].replace("-", ""), doc=f["primary"])
            if u not in fetched:
                fetched[u] = fetch(u)
                time.sleep(cc.BULK_SLEEP)
            return fetched[u]

        matched: dict[str, str] = {}
        sources = []
        for url, rows in g.groupby("source_url"):
            filed = pd.Timestamp(rows["filed"].iloc[0])
            mine, best = row_tranches(rows), None
            sources.append({"company": co, "filed": rows["filed"].iloc[0], "accession": rows["accession"].iloc[0],
                            "tranches": mine, "url": url})
            matched[rows["accession"].iloc[0]] = url  # a supplement that is itself the source
            for f in finals:
                if 0 <= (pd.Timestamp(f["filed"]) - filed).days <= ci.COVER_DAYS:
                    lines = lines_of(f)
                    if cc.kind(lines) != "final":
                        continue
                    c = cover_tranches(lines)
                    if c and (best is None or len(c & mine) > len(best[1] & mine)):
                        best = (f["accession"], c)
            if best is None:
                out.append((co, rows["filed"].iloc[0], url, "", "no_final_supplement", "", "source"))
                continue
            acc, c = best
            matched[acc] = url
            diff = sorted(mine ^ c)
            out.append((co, rows["filed"].iloc[0], url, acc, "ok" if not diff else "differs", str(diff), "source"))
        for f in finals:
            if not cc.in_scope(f):
                continue
            lines = lines_of(f)
            c = cover_tranches(lines) if cc.kind(lines) == "final" else set()
            if not c:
                continue
            url = matched.get(f["accession"])
            if url is None:
                src = ci.source_of(co, f["filed"], c, sources)
                url = next((s["url"] for s in sources if s["accession"] == src), None)
            out.append((co, f["filed"], url or "", f["accession"], "ok" if url else "no_source",
                        "" if url else str(sorted(c)), "supplement"))
    return pd.DataFrame(out, columns=["company", "filed", "source_url", "final_accession", "status", "diff", "check"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frac", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=20261125)
    ap.add_argument("--covers", action="store_true")
    a = ap.parse_args()
    if a.covers:
        cov = covers()
        for r in cov.itertuples(index=False):
            print(f"{r.check:10s} {r.company:6s} {r.filed} {r.final_accession:22s} {r.status:20s} {r.diff}")
        src, sup = cov[cov["check"] == "source"], cov[cov["check"] == "supplement"]
        print(f"{len(src)} offerings, {int((src['status'] == 'ok').sum())} equal to the final supplement; "
              f"{len(sup)} final debt supplements, {int((sup['status'] == 'no_source').sum())} without a source")
        return
    res = run(a.frac, a.seed)
    for r in res.itertuples(index=False):
        if r.status not in OK or r.dates != "ok":
            print(f"{r.id:24s} {r.method:7s} {r.status:22s} {r.details:30s} {r.dates}")
    bad = ~res["status"].isin(OK + ("manual",)) | (res["dates"] != "ok")
    print(f"{len(res)} checked, {int(bad.sum())} errors, {int((res['status'] == 'moved').sum())} moved, "
          f"{int((res['status'] == 'manual').sum())} manual (see notes)")


if __name__ == "__main__":
    main()
