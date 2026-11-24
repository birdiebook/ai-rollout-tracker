"""Sampling self-check of the P2a extraction: re-fetch each sampled document and verify the row is there.

For each sampled row of curated/useful_lives.csv the document is fetched again (no cache) and
- the sentence at the locator (sentence #k of guidance_capex.sentences) has the stored SHA-256; if not, the whole
  document is searched for the hash ("moved");
- every number of the row is in that sentence: lives (life_lo/hi, old_lo/hi) as digits or words ("six", "4.5",
  "four and a half") followed by "year" within a few words, an effect as "$X million/billion" or "$0.xx";
- a stop row's sentence states no number of years; a stop row with locator "absent" has no candidate sentence
  naming its asset class with a number of years;
- filed and accepted equal EDGAR's filingDate and acceptanceDateTime (submissions API, fetched again).

    python -m ai_tracker.useful_lives_check [--frac 0.3] [--seed 20261124]

This confirms location, hash, numbers and dates, not the semantics (asset class, scope, effective date): that is for
the independent review. Nothing is written except raw copies (data/raw).
"""

from __future__ import annotations

import argparse
import re

import pandas as pd

from ai_tracker import http
from ai_tracker.sources import guidance_capex, tsmc_sec, useful_lives, useful_lives_corpus

SOURCE = "useful_lives_check"
OK = ("ok", "moved")

_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine",
          10: "ten", 15: "fifteen", 20: "twenty", 25: "twenty-five", 30: "thirty", 40: "forty"}


def life_forms(x: float) -> list[str]:
    """Ways a life in years can be written: 6 -> 6, six; 4.5 -> 4.5, four and a half, four and one-half."""
    forms = [f"{x:g}"]
    whole = int(x)
    if x == whole:
        if whole in _WORDS:
            forms.append(_WORDS[whole])
    elif x - whole == 0.5:
        forms.append(f"{whole}½")
        if whole in _WORDS:
            forms += [f"{_WORDS[whole]} and a half", f"{_WORDS[whole]} and one-half", f"{_WORDS[whole]} and one half"]
    return forms


def life_patterns(x: float) -> list[str]:
    """Regexes: the number, then 'year' within 40 characters (a range "two to six years" puts 'years' after hi)."""
    gap = r"(?:[^.]|\.(?!\s)){0,40}?"  # no sentence end in between; a decimal point is fine
    return [rf"(?<![\d.]){re.escape(f)}(?![\d])" + gap + r"\byears?\b" if f[0].isdigit()
            else rf"\b{re.escape(f)}\b" + gap + r"\byears?\b" for f in life_forms(x)]


def effect_patterns(value: float, unit: str) -> list[str]:
    v = abs(value)
    if unit == "USD per share":
        return [rf"\$\s?{v:.2f}(?!\d)", rf"\$\s?{v:g}(?!\d)"]
    forms = lambda y: list(dict.fromkeys([f"{y:g}", f"{y:,.0f}" if y == int(y) else f"{y:,}"]))  # noqa: E731
    return ([rf"\$\s?{re.escape(f)}\s*million" for f in forms(v)]
            + [rf"\$\s?{re.escape(f)}\s*billion" for f in forms(v / 1000)])


def numbers_in(row: pd.Series, sentence: str) -> bool:
    """Every number of the row appears in the sentence (see the module docstring)."""
    if row["row_type"] == "effect":
        return any(re.search(p, sentence, re.I) for p in effect_patterns(row["effect_value"], row["effect_unit"]))
    if row["row_type"] == "stop":
        return useful_lives_corpus.YEARS_RE.search(sentence) is None
    vals = [row[c] for c in ("life_lo", "life_hi", "old_lo", "old_hi") if pd.notna(row[c])]
    return all(any(re.search(p, sentence, re.I) for p in life_patterns(v)) for v in vals)


def class_stated(asset_class: str, text: str) -> bool:
    """Some sentence of the document names the asset class together with a number of years."""
    words = re.escape(re.sub(r"\s+", " ", asset_class.strip())).replace(r"\ ", r"\s+")
    return any(re.search(words, s, re.I) and useful_lives_corpus.YEARS_RE.search(s)
               for s in guidance_capex.sentences(text))


def check_row(row: pd.Series, text: str) -> str:
    """'ok' | 'moved' | 'sentence_not_found' | 'number_not_in_sentence' | 'class_still_stated'."""
    if row["locator"] == "absent":
        return "class_still_stated" if class_stated(row["asset_class"], text) else "ok"
    sents = guidance_capex.sentences(text)
    k = int(re.search(r"sentence #(\d+)", row["locator"]).group(1))
    at = sents[k] if k < len(sents) else None
    status = "ok"
    if at is None or guidance_capex.sentence_hash(at) != row["sentence_sha256"]:
        hits = [s for s in sents if guidance_capex.sentence_hash(s) == row["sentence_sha256"]]
        if not hits:
            return "sentence_not_found"
        at, status = hits[0], "moved"
    return status if numbers_in(row, at) else "number_not_in_sentence"


def check_dates(row: pd.Series, filings: dict[str, dict]) -> str:
    f = filings.get(row["accession"])
    if f is None:
        return "accession_not_in_submissions"
    if f["filed"] != row["filed"]:
        return f"filed_differs: {f['filed']}"
    if row["accepted"] and f["accepted"][:19] != row["accepted"][:19]:
        return f"accepted_differs: {f['accepted']}"
    return "ok"


def fetch_text(url: str) -> str:
    return tsmc_sec.to_text(http.get(url, SOURCE).content.decode("utf-8", errors="replace"))


def _submissions(company: str) -> dict[str, dict]:
    cik = useful_lives_corpus.CIKS[company]
    sub = http.get(useful_lives_corpus.SUBMISSIONS.format(cik=cik), SOURCE).json()
    blocks = [sub["filings"]["recent"]] + [http.get(useful_lives_corpus.SUBMISSIONS_FILE.format(name=f["name"]),
                                                    SOURCE).json() for f in sub["filings"].get("files", [])]
    return {acc: {"filed": b["filingDate"][i], "accepted": b["acceptanceDateTime"][i]}
            for b in blocks for i, acc in enumerate(b["accessionNumber"])}


def run(frac: float = 0.3, seed: int = 20261124) -> pd.DataFrame:
    df = useful_lives.load()
    sample = df.sample(frac=frac, random_state=seed).sort_values("id") if frac < 1 else df.sort_values("id")
    texts: dict[str, str] = {}
    subs: dict[str, dict] = {}
    res = []
    for _, row in sample.iterrows():  # sequential: several tracks share sec.gov's rate limit
        try:
            if row["company"] not in subs:
                subs[row["company"]] = _submissions(row["company"])
            dates = check_dates(row, subs[row["company"]])
            if row["source_url"] not in texts:
                texts[row["source_url"]] = fetch_text(row["source_url"])
            status = check_row(row, texts[row["source_url"]])
        except Exception as exc:  # noqa: BLE001 - a failed fetch is reported, not hidden
            status, dates = f"fetch_failed: {type(exc).__name__}", "not_checked"
        res.append((row["id"], row["row_type"], status, dates))
    return pd.DataFrame(res, columns=["id", "row_type", "status", "dates"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frac", type=float, default=0.3)
    ap.add_argument("--seed", type=int, default=20261124)
    a = ap.parse_args()
    res = run(a.frac, a.seed)
    for r in res.itertuples(index=False):
        print(f"{r.id:32s} {r.row_type:7s} {r.status:24s} {r.dates}")
    bad = ~res["status"].isin(OK) | (res["dates"] != "ok")
    print(f"{len(res)} checked, {int(bad.sum())} errors, error rate {bad.mean():.1%}, "
          f"{int((res['status'] == 'moved').sum())} moved")


if __name__ == "__main__":
    main()
