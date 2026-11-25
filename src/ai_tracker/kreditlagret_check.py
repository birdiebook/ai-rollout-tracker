"""Self-check of the KL1 extraction (curated/kreditlagret.csv): re-fetch each document without the cache, verify the rows.

For each sampled row (all rows with --frac 1.0, the registered setting):
- the quote at the locator (`line #k` or `lines #a-#b` of KR1's line list) has the stored SHA-256; if not, every window
  of the same width in the document is searched for the hash ("moved");
- the row's value is written in the quote (sources.kreditlagret.value_in_quote: amounts as $/billion/million or a table
  cell, rates as percentages, margins as bp or a percentage, dates as written, codes by their wording);
- filed and accepted equal EDGAR's filingDate and acceptanceDateTime (submissions API, fetched again).

    python -m ai_tracker.kreditlagret_check [--frac 1.0] [--seed 20261125]

This confirms location, hash, number and dates, not the semantics (which instrument, which balance date, whether the
stated figure is the right one): that is for an independent review. SEC: one request at a time, BULK_SLEEP between
documents, stop on 403/429 (sources.kreditlagret.fetch). Nothing is written except raw copies (data/raw).
"""

from __future__ import annotations

import argparse
import json

import pandas as pd

from ai_tracker.sources import credit_issuance_corpus as cc
from ai_tracker.sources import kreditlagret as kl

OK = ("ok", "moved")


def check_row(row: pd.Series, lines: list[str]) -> str:
    """'ok' | 'moved' | 'quote_not_found' | 'value_not_in_quote'."""
    a, b = kl.span(row["locator"])
    quote = kl.quote_at(lines, row["locator"])
    status = "ok"
    if quote is None or kl.quote_hash(quote) != row["quote_sha256"]:
        k = kl.find_hash(lines, row["quote_sha256"], b - a + 1)
        if k is None:
            return "quote_not_found"
        quote, status = "\n".join(lines[k:k + b - a + 1]), "moved"
    return status if kl.value_in_quote(row["field"], row["value"], row["unit"], quote) else "value_not_in_quote"


def check_dates(row: pd.Series, filings: dict[str, dict]) -> str:
    f = filings.get(row["accession"])
    if f is None:
        return "accession_not_in_submissions"
    if f["filed"] != row["filed"]:
        return f"filed_differs: {f['filed']}"
    if row["accepted"] and f["accepted"][:19] != row["accepted"][:19]:
        return f"accepted_differs: {f['accepted']}"
    return "ok"


def run(frac: float = 1.0, seed: int = 20261125, df: pd.DataFrame | None = None) -> pd.DataFrame:
    df = kl.load() if df is None else df
    if frac < 1.0:
        df = df.sample(frac=frac, random_state=seed)
    df = df.sort_values(["company", "accession", "id"])
    subs: dict[str, dict] = {}
    texts: dict[str, list[str]] = {}
    res = []
    for _, row in df.iterrows():  # sequential: several tracks share sec.gov's rate limit
        try:
            if row["company"] not in subs:
                subs[row["company"]] = {f["accession"]: f for f in kl.submissions(kl.CIKS[row["company"]])}
            dates = check_dates(row, subs[row["company"]])
            if row["source_url"] not in texts:
                raw = kl.fetch(row["source_url"], reuse=False)
                texts[row["source_url"]] = cc.lines(raw.decode("utf-8", errors="replace"))
            status = check_row(row, texts[row["source_url"]])
        except kl.Stop:
            raise
        except Exception as exc:  # noqa: BLE001 - a failed fetch is reported, not hidden
            status, dates = f"fetch_failed: {type(exc).__name__}", "not_checked"
        res.append((row["id"], status, dates))
    return pd.DataFrame(res, columns=["id", "status", "dates"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frac", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=20261125)
    ap.add_argument("--json", help="write the per-row result here")
    a = ap.parse_args()
    res = run(a.frac, a.seed)
    bad = ~res["status"].isin(OK) | (res["dates"] != "ok")
    for r in res[bad].itertuples(index=False):
        print(f"{r.id:70s} {r.status:24s} {r.dates}")
    print(f"{len(res)} checked, {int(bad.sum())} errors, {int((res['status'] == 'moved').sum())} moved, "
          f"{res['id'].str.split('-').str[0].nunique()} instruments")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res.to_dict(orient="records"), f, indent=1)
    raise SystemExit(1 if bad.any() else 0)


if __name__ == "__main__":
    main()
