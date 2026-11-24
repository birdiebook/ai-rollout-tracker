"""Sampling self-check of the P2a extraction: re-fetch each sampled document and verify the row is there.

For each sampled row of curated/useful_lives.csv the document is fetched again (no cache) and
- the sentence at the locator (sentence #k of guidance_capex.sentences) has the stored SHA-256; if not, the whole
  document is searched for the hash ("moved");
- every number of the row is in that sentence: lives (life_lo/hi, old_lo/hi) as digits or words ("six", "4.5",
  "four and a half") followed by "year" within a few words, an effect as "$X million/billion" or "$0.xx";
- for a stop row (the class is no longer stated): no sentence of the document gives a number of years for the
  asset class, i.e. the class name directly followed by a life ("network equipment Three to 20 years", "computer
  equipment, two to six years", "over periods of ...") or a life followed by "for (our) <class>" (Amazon's wording);
  a joint class that only ends in the same words ("servers and network equipment") is not the class;
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
    millions = list(dict.fromkeys([f"{v:g}", f"{v:,.0f}" if v == int(v) else f"{v:,}"]))
    b = v / 1000
    billions = list(dict.fromkeys([f"{b:g}", f"{b:.1f}", f"{b:.2f}"]))  # "$2 billion", "$2.0 billion", "$2.29 billion"
    return ([rf"\$\s?{re.escape(f)}\s*million" for f in millions]
            + [rf"\$\s?{re.escape(f)}\s*billion" for f in billions])


def numbers_in(row: pd.Series, sentence: str) -> bool:
    """Every number of the row appears in the sentence (see the module docstring)."""
    if row["row_type"] == "effect":
        return any(re.search(p, sentence, re.I) for p in effect_patterns(row["effect_value"], row["effect_unit"]))
    if row["row_type"] == "stop":
        return True  # nothing to find in the sentence; check_row tests that the class is no longer stated
    vals = [row[c] for c in ("life_lo", "life_hi", "old_lo", "old_hi") if pd.notna(row[c])]
    return all(any(re.search(p, sentence, re.I) for p in life_patterns(v)) for v in vals)


def class_stated(asset_class: str, text: str) -> bool:
    """Some sentence of the document gives a number of years for the asset class (see the module docstring)."""
    cls = re.escape(re.sub(r"\s+", " ", asset_class.strip())).replace(r"\ ", r"\s+")
    years = useful_lives_corpus.YEARS_RE.pattern.removeprefix("(?i)")
    direct = (rf"(?<!\band\s)(?<!\band\s\s)\b{cls}\b[\s,:;()]*(?:are\s+)?(?:generally\s+)?(?:depreciated\s+)?"
              rf"(?:over\s+(?:a\s+)?(?:periods?\s+(?:of\s+|up\s+to\s+)?)?)?{years}")
    reverse = rf"{years}\s+(?:[\w,]+\s+){{0,6}}?for\s+(?:our\s+)?{cls}\b"
    return any(re.search(direct, s, re.I) or re.search(reverse, s, re.I) for s in guidance_capex.sentences(text))


def check_row(row: pd.Series, text: str) -> str:
    """'ok' | 'moved' | 'sentence_not_found' | 'number_not_in_sentence' | 'class_still_stated'."""
    if row["locator"] == "absent":
        return "class_still_stated" if class_stated(row["asset_class"], text) else "ok"
    if row["row_type"] == "stop" and class_stated(row["asset_class"], text):
        return "class_still_stated"
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
