"""Self-check of the CN1 text extraction (curated/china_text.csv): re-fetch every document and verify every row.

For each row (all rows, not a sample: there are few) the document is fetched again without the cache and
- the sentence at the locator (sentence #k of guidance_capex.sentences) has the stored SHA-256; if not, the whole
  document is searched for the hash ("moved");
- the number of the row stands in that sentence as "<value> billion" (one decimal, or a whole number);
- filed and accepted equal EDGAR's filingDate and acceptanceDateTime (submissions API, fetched again).

    python -m ai_tracker.china_text_check

This confirms location, hash, number and dates, not the semantics (measure, quarter): that is for the independent
extraction review. Nothing is written except raw copies (data/raw/china_text_check).
"""

from __future__ import annotations

import argparse
import re

import pandas as pd

from ai_tracker import http
from ai_tracker.sources import china_sec, china_text, guidance_capex, tsmc_sec

SOURCE = "china_text_check"
OK = ("ok", "moved")


def number_in(value: float, sentence: str) -> bool:
    forms = dict.fromkeys([f"{value:g}", f"{value:.1f}"])
    return any(re.search(rf"(?<![\d.]){re.escape(f)}\s*billion", sentence) for f in forms)


def check_row(row: pd.Series, text: str) -> str:
    """'ok' | 'moved' | 'sentence_not_found' | 'number_not_in_sentence'."""
    sents = guidance_capex.sentences(text)
    k = int(re.search(r"sentence #(\d+)", row["locator"]).group(1))
    at = sents[k] if k < len(sents) else None
    status = "ok"
    if at is None or guidance_capex.sentence_hash(at) != row["sentence_sha256"]:
        hits = [s for s in sents if guidance_capex.sentence_hash(s) == row["sentence_sha256"]]
        if not hits:
            return "sentence_not_found"
        at, status = hits[0], "moved"
    return status if number_in(float(row["value"]), at) else "number_not_in_sentence"


def check_dates(row: pd.Series, filings: dict[str, dict]) -> str:
    f = filings.get(row["accession"])
    if f is None:
        return "accession_not_in_submissions"
    if f["filed"] != row["filed"]:
        return f"filed_differs: {f['filed']}"
    if row["accepted"] and f["accepted"][:19] != row["accepted"][:19]:
        return f"accepted_differs: {f['accepted']}"
    return "ok"


def _submissions(cik: int) -> dict[str, dict]:
    sub = http.get(china_sec.SUBMISSIONS.format(cik=cik), SOURCE).json()
    blocks = [sub["filings"]["recent"]] + [http.get(china_sec.SUBMISSIONS_FILE.format(name=f["name"]), SOURCE).json()
                                           for f in sub["filings"].get("files", [])]
    return {acc: {"filed": b["filingDate"][i], "accepted": b["acceptanceDateTime"][i]}
            for b in blocks for i, acc in enumerate(b["accessionNumber"])}


def run() -> pd.DataFrame:
    df = china_text.load().sort_values("id")
    texts: dict[str, str] = {}
    subs: dict[str, dict] = {}
    res = []
    for _, row in df.iterrows():  # sequential: several tracks share sec.gov's rate limit
        try:
            if row["company"] not in subs:
                subs[row["company"]] = _submissions(china_sec.CIKS[row["company"]])
            dates = check_dates(row, subs[row["company"]])
            if row["source_url"] not in texts:
                raw = http.get(row["source_url"], SOURCE).content
                texts[row["source_url"]] = tsmc_sec.to_text(raw.decode("utf-8", errors="replace"))
            status = check_row(row, texts[row["source_url"]])
        except Exception as exc:  # noqa: BLE001 - a failed fetch is reported, not hidden
            status, dates = f"fetch_failed: {type(exc).__name__}", "not_checked"
        res.append((row["id"], status, dates))
    return pd.DataFrame(res, columns=["id", "status", "dates"])


def main() -> None:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    res = run()
    for r in res.itertuples(index=False):
        print(f"{r.id:36s} {r.status:24s} {r.dates}")
    bad = ~res["status"].isin(OK) | (res["dates"] != "ok")
    print(f"{len(res)} checked, {int(bad.sum())} errors, {int((res['status'] == 'moved').sum())} moved")
    raise SystemExit(1 if bad.any() else 0)


if __name__ == "__main__":
    main()
