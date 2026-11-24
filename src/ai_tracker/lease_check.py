"""Sampling self-check of the agent-extracted lease commitments: re-fetch the filing, verify the number at the locator.

For a sample of rows of curated/lease_commitments.csv (default 20 %), the 10-Q/10-K primary document is fetched
again (a fresh request, not the cached raw copy), split into sentences as at extraction, and:
- the sentence at the locator (sentence #k) must have the stored SHA-256; if not, the whole document is searched
  for the hash ("moved": located, but reported);
- the stored amount must appear in that sentence, written in billions or millions;
- the sentence, or the one before or after it (CoreWeave and a page break at Meta put the amount in the next
  sentence, Oracle's MD&A from November 2023 in the sentence before), must mention leases that have not commenced.

    python -m ai_tracker.lease_check [--frac 0.2] [--seed 0]

Prints one line per sampled row and the error rate. Nothing is written except http raw copies (data/raw). This is
the track's own check; the independent review (R5) reads the sources again.
"""

from __future__ import annotations

import argparse
import re

import pandas as pd

from ai_tracker.sources import guidance_capex as gc
from ai_tracker.sources import lease_commitments as lc

OK = ("ok", "moved")


def check_row(row: pd.Series, text: str) -> str:
    """'ok' | 'moved' | 'sentence_not_found' | 'number_not_in_sentence' | 'not_a_commitment_sentence'."""
    sents = lc.sentences(text)
    k = int(re.fullmatch(r"sentence #(\d+)", row["locator"]).group(1))
    at = sents[k] if k < len(sents) else None
    status = "ok"
    if at is None or gc.sentence_hash(at) != row["sentence_sha256"]:
        hits = [j for j, s in enumerate(sents) if gc.sentence_hash(s) == row["sentence_sha256"]]
        if not hits:
            return "sentence_not_found"
        k, at, status = hits[0], sents[hits[0]], "moved"
    # the amount can follow the sentence that names the leases (CoreWeave, Meta's page break), or precede it (Oracle's
    # 10-Q MD&A from November 2023: "... operating lease commitments to $X" and then "... expected to commence ...")
    context = (sents[k - 1] + " " if k else "") + at + (" " + sents[k + 1] if k + 1 < len(sents) else "")
    if not (lc.CANDIDATE_RE.search(context) and lc.LEASE_RE.search(context)):
        return "not_a_commitment_sentence"
    if not re.search(lc.number_pattern(float(row["value"])), at):
        return "number_not_in_sentence"
    return status


def sample(df: pd.DataFrame, frac: float = 0.2, seed: int = 0) -> pd.DataFrame:
    """At least one row; stratified by company so that every company is checked."""
    n = max(1, round(len(df) * frac))
    first = df.groupby("company", group_keys=False).apply(lambda g: g.sample(1, random_state=seed))
    rest = df.drop(first.index)
    extra = rest.sample(max(0, n - len(first)), random_state=seed) if len(rest) else rest
    return pd.concat([first, extra]).sort_values("id")


def run(frac: float = 0.2, seed: int = 0, df: pd.DataFrame | None = None, fetch=None) -> pd.DataFrame:
    df = lc.load() if df is None else df
    fetch = fetch or (lambda url: lc.document_text(url, fresh=True))
    texts: dict[str, str] = {}
    res = []
    for _, row in sample(df, frac, seed).iterrows():
        try:
            if row["source_url"] not in texts:
                texts[row["source_url"]] = fetch(row["source_url"])
            status = check_row(row, texts[row["source_url"]])
        except Exception as exc:  # noqa: BLE001 - a failed fetch is reported, not hidden
            status = f"fetch_failed: {type(exc).__name__}"
        res.append((row["id"], row["value"], row["source_url"], status))
    return pd.DataFrame(res, columns=["id", "value", "source_url", "status"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frac", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    res = run(a.frac, a.seed)
    for r in res.itertuples(index=False):
        print(f"{r.id:16s} {r.value:>10,.0f}  {r.status}")
    bad = ~res["status"].isin(OK)
    print(f"{len(res)} sampled, {int(bad.sum())} errors, error rate {bad.mean():.1%}, "
          f"{int((res['status'] == 'moved').sum())} moved")


if __name__ == "__main__":
    main()
