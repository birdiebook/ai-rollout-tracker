"""Self-check of the agent-extracted acquisitions (curated/acquisitions.csv, register 2026-11-27 QA1).

For each sampled row (default every row: the table is small) the filing's primary document is fetched again (a fresh
request, not the cached raw copy), split into sentences as at extraction, and:
- the sentence at the locator ("sentence #k") has the stored SHA-256; if not, the whole document is searched for the
  hash ("moved": located, but reported);
- every figure of the row is in that sentence: the consideration (as "$ X million", "$ X billion" or a table amount
  in thousands, "1,799,666"), the number of businesses ("three businesses", "two acquisitions", "a business"), the
  closing date ("July 17, 2024") when the row has one; an RPO statement mentions remaining performance obligations or
  backlog and acquisitions;
- filed equals EDGAR's filingDate for the accession (submissions API, fetched again).

    python -m ai_tracker.acquisitions_check [--frac 1.0] [--seed 20261127]

This confirms location, hash, numbers and dates, not the semantics (which quarter a business closed in, whether a
count is new in the filing): that is for the independent review. Nothing is written except raw copies (data/raw).
"""

from __future__ import annotations

import argparse
import re

import pandas as pd

from ai_tracker.sources import acquisitions as A
from ai_tracker.sources import guidance_capex as gc

OK = ("ok", "moved")
_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine",
          10: "ten", 11: "eleven", 12: "twelve"}


def amount_patterns(musd: float) -> list[str]:
    """'$ 300 million', '$ 2.04 billion', or a table amount in thousands ('1,799,666', '$ 1,290,506')."""
    v = abs(float(musd))
    thousands = f"{round(v * 1000):,}"
    millions = list(dict.fromkeys([f"{v:g}", f"{v:,.1f}", f"{v:,.0f}" if v == int(v) else f"{v:,}"]))
    b = v / 1000
    billions = list(dict.fromkeys([f"{b:g}", f"{b:.1f}", f"{b:.2f}"]))
    return ([rf"(?<![\d,.]){re.escape(thousands)}(?![\d,])"]
            + [rf"\$\s?{re.escape(f)}\s*million" for f in millions]
            + [rf"\$\s?{re.escape(f)}\s*billion" for f in billions])


def count_patterns(n: int) -> list[str]:
    words = [str(n)] + ([_WORDS[n]] if n in _WORDS else []) + (["a", "an"] if n == 1 else [])
    return [rf"\b{w}\s+(?:additional\s+)?(?:business(?:es)?|acquisitions?)\b" for w in words]


def date_pattern(day: str) -> str:
    t = pd.Timestamp(day)
    return rf"\b{t.strftime('%B')}\s+{t.day},\s+{t.year}\b"


def numbers_in(row: pd.Series, sentence: str) -> bool:
    """Every figure of the row is in the sentence (see the module docstring)."""
    ok = True
    if pd.notna(row.get("consideration_musd")) and row["row_type"] == "consideration":
        ok &= any(re.search(p, sentence, re.I) for p in amount_patterns(row["consideration_musd"]))
    if pd.notna(row.get("n_businesses")) and row["row_type"] in ("acquisition", "count", "none"):
        ok &= any(re.search(p, sentence, re.I) for p in count_patterns(int(row["n_businesses"])))
    if row.get("closed"):
        ok &= bool(re.search(date_pattern(row["closed"]), sentence))
    if row["row_type"] == "rpo_statement":
        ok &= bool(re.search(r"(?i)remaining performance obligations|backlog", sentence)
                   and re.search(r"(?i)acqui", sentence))
    return bool(ok)


def check_row(row: pd.Series, text: str) -> str:
    """'ok' | 'moved' | 'sentence_not_found' | 'number_not_in_sentence'."""
    sents = A.sentences(text)
    k = int(re.fullmatch(r"sentence #(\d+)", row["locator"]).group(1))
    at = sents[k] if k < len(sents) else None
    status = "ok"
    if at is None or gc.sentence_hash(at) != row["sentence_sha256"]:
        hits = [j for j, s in enumerate(sents) if gc.sentence_hash(s) == row["sentence_sha256"]]
        if not hits:
            return "sentence_not_found"
        at, status = sents[hits[0]], "moved"
    return status if numbers_in(row, at) else "number_not_in_sentence"


def filing_dates(company: str) -> dict[str, str]:
    return {d.accession: d.filed for d in A.documents(company)}


def run(frac: float = 1.0, seed: int = 20261127, df: pd.DataFrame | None = None, fetch=None,
        dates: dict[str, dict[str, str]] | None = None) -> pd.DataFrame:
    """One row per sampled CSV row with its status and whether `filed` matches EDGAR."""
    df = A.load() if df is None else df
    s = df if frac >= 1 else df.sample(max(1, round(len(df) * frac)), random_state=seed)
    fetch = fetch or (lambda url: A.document_text(url, fresh=True))
    dates = dates if dates is not None else {c: filing_dates(c) for c in s["company"].unique()}
    texts: dict[str, str] = {}
    out = []
    for _, row in s.sort_values("id").iterrows():
        if row["source_url"] not in texts:
            texts[row["source_url"]] = fetch(row["source_url"])
        status = check_row(row, texts[row["source_url"]])
        filed_ok = dates.get(row["company"], {}).get(row["accession"]) == row["filed"]
        out.append({"id": row["id"], "status": status, "filed_ok": filed_ok})
    return pd.DataFrame(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frac", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=20261127)
    a = ap.parse_args()
    r = run(a.frac, a.seed)
    for _, x in r.iterrows():
        print(f"{x['id']:<28} {x['status']:<24} filed {'ok' if x['filed_ok'] else 'MISMATCH'}")
    bad = r[~r["status"].isin(OK) | ~r["filed_ok"]]
    print(f"{len(r)} rows checked, {len(bad)} with errors ({len(bad) / max(len(r), 1):.0%})")
    if len(bad):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

