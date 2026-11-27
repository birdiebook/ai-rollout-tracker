"""Self-check of the AN1 extraction (curated/anthropic_gaap.csv), register 2026-11-27 "AN1", (e) 1.

Every row (or a sample with --frac < 1): the document is fetched again without the cache, and
- the quote at the locator (header lines and row line of KR1's line list) has the stored SHA-256 (an archived EDGAR
  document does not change, so a quote that moved is an error, not a match);
- the cell at the locator, read again, is the row's value (sign as registered);
- filed and accepted equal EDGAR's filingDate and acceptanceDateTime (submissions API, fetched again).

    python -m ai_tracker.anthropic_gaap_check [--frac 1.0] [--seed 20261127]

This confirms location, hash, number and dates, not the semantics (which line, which period): that is the hand-read
sample's and the review's. Nothing is written except raw copies (data/raw).
"""

from __future__ import annotations

import argparse

import pandas as pd

from ai_tracker.sources import anthropic_gaap as A
from ai_tracker.sources import kreditlagret as kl


def check_row(row, lines: list[str]) -> str:
    """'ok' | 'quote_not_found' | 'value_differs: <v>'."""
    quote = A.quote_at(lines, row["locator"])
    if quote is None or A.quote_hash(quote) != row["quote_sha256"]:
        return "quote_not_found"
    v = A.cell_value(lines, row["locator"], A.ITEMS[row["item"]][2])
    return "ok" if v == float(row["value"]) else f"value_differs: {v}"


def check_dates(row, filings: dict[str, dict]) -> str:
    f = filings.get(row["accession"])
    if f is None:
        return "accession_not_in_submissions"
    if f["filed"] != row["filed"]:
        return f"filed_differs: {f['filed']}"
    if f["accepted"][:19] != row["accepted"][:19]:
        return f"accepted_differs: {f['accepted']}"
    return "ok"


def run(frac: float = 1.0, seed: int = 20261127, df: pd.DataFrame | None = None, fresh: bool = True) -> pd.DataFrame:
    df = A.load() if df is None else df
    if frac < 1.0:
        df = df.sample(frac=frac, random_state=seed)
    filings = {f["accession"]: f for f in kl.submissions(A.CIK)}
    out = []
    for url, g in df.groupby("source_url", sort=False):
        lines = kl.doc_lines(url, reuse=not fresh)
        for r in g.to_dict("records"):
            out.append({"id": r["id"], "quote": check_row(r, lines), "dates": check_dates(r, filings)})
    return pd.DataFrame(out)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m ai_tracker.anthropic_gaap_check")
    ap.add_argument("--frac", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=20261127)
    args = ap.parse_args(argv)
    res = run(args.frac, args.seed)
    bad = res[(res["quote"] != "ok") | (res["dates"] != "ok")]
    print(f"{len(res)} rows checked against freshly fetched documents: {len(res) - len(bad)} ok, {len(bad)} not")
    for r in bad.itertuples(index=False):
        print(f"  {r.id}: quote {r.quote}, dates {r.dates}")
    if len(bad):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
