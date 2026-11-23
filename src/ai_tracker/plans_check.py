"""Sampling check of the extracted plans: re-fetch the source and verify each sampled value is there.

For each sampled row of curated/plans.csv the document is fetched again (no cache), its sentence at the locator
(sentence #k of guidance_capex.sentences) must have the stored SHA-256, and the coded number(s) - or, for a
direction, a word of that direction - must appear in that sentence. If the sentence moved, the whole document is
searched for the hash ("moved", counted as located but reported). This checks location and number, not semantics
(period, basis, definition): that is the independent review R5.

    python -m ai_tracker.plans_check [--frac 0.2] [--seed 20261123]

Prints one line per sampled row and the error rate. Nothing is written except http raw copies (data/raw).
"""

from __future__ import annotations

import argparse
import re

import pandas as pd

from ai_tracker import http
from ai_tracker.guidance_check import DIRECTION_WORDS
from ai_tracker.sources import guidance_capex as gc
from ai_tracker.sources import plans, tsmc_sec

SOURCE = "plans_check"
WORD_MULTIPLES = {2.0: r"doubl|twice|2x|two times", 3.0: r"tripl|3x|three times", 4.0: r"quadrupl|4x|four times",
                  10.0: r"10x|tenfold|ten times"}


def _scaled(v: float) -> str:
    """Regex for the decimal number v (2.5 -> 2.5 / 2.50; 30 -> 30 / 30.0), not part of a longer number."""
    whole, _, frac = f"{round(v, 3):.3f}".rstrip("0").rstrip(".").partition(".")
    whole = f"{int(whole):,}".replace(",", ",?")
    tail = rf"\.{frac}0*" if frac else r"(?:\.0+)?"
    return rf"(?<![\d.]){whole}{tail}(?![\d])"


# the lower end of a range written once with its unit: "$34-39 billion", "$37 billion to $39 billion" is covered too
RANGE_TAIL = r"(?:\s*(?:-|–|to)\s*\$?\s*[\d.]+)?\s*"
WORD_GW = {1000.0: r"(?:a|another|one) gigawatt"}


def number_patterns(value: float, unit: str, in_millions: bool = False) -> list[str]:
    """Ways the value can be written: MUSD in trillions / billions / millions (a bare number in a table stated
    "in millions"), MW in GW or MW, multiples."""
    if unit == "MUSD":
        pats = [_scaled(value / 1e6) + RANGE_TAIL + r"trillion", _scaled(value / 1000) + RANGE_TAIL + r"(?:billion|B\b)",
                _scaled(value) + RANGE_TAIL + r"(?:million|M\b)"]
        return pats + ([_scaled(value)] if in_millions else [])
    if unit == "MW":
        pats = [_scaled(value / 1000) + r"\s*(?:GW|gigawatts?)", _scaled(value) + r"\s*(?:MWs?|megawatts?)"]
        return pats + ([WORD_GW[value]] if value in WORD_GW else [])
    if unit == "multiple":
        pats = [_scaled(value) + r"\s*x", _scaled(round((value - 1) * 100, 3)) + r"\s*%"]
        if value in WORD_MULTIPLES:
            pats.append(WORD_MULTIPLES[value])
        return pats
    raise ValueError(unit)


def sentence_ok(row: pd.Series, sentence: str) -> bool:
    if row["kind"] == "direction":
        return re.search(DIRECTION_WORDS[int(row["direction_code"])], sentence, re.I) is not None
    vals = [v for v in (row["value_lo"], row["value_hi"]) if pd.notna(v)]
    millions = re.search(r"(?i)\(in millions\)", sentence) is not None
    return all(any(re.search(p, sentence, re.I) for p in number_patterns(v, row["unit"], millions)) for v in vals)


def check_row(row: pd.Series, text: str) -> str:
    """'ok' | 'moved' | 'sentence_not_found' | 'number_not_in_sentence'."""
    sents = gc.sentences(text)
    k = int(re.search(r"sentence #(\d+)", row["locator"]).group(1))
    at = sents[k] if k < len(sents) else None
    status = "ok"
    if at is None or gc.sentence_hash(at) != row["sentence_sha256"]:
        hits = [s for s in sents if gc.sentence_hash(s) == row["sentence_sha256"]]
        if not hits:
            return "sentence_not_found"
        at, status = hits[0], "moved"
    return status if sentence_ok(row, at) else "number_not_in_sentence"


def fetch_text(url: str) -> str:
    return tsmc_sec.to_text(http.get(url, SOURCE).content.decode("utf-8", errors="replace"))


def run(frac: float = 0.2, seed: int = 20261123) -> pd.DataFrame:
    df = plans.load()
    sample = df.sample(frac=frac, random_state=seed).sort_values("id")
    texts: dict[str, str] = {}
    res = []
    for _, row in sample.iterrows():
        try:
            if row["source_url"] not in texts:
                texts[row["source_url"]] = fetch_text(row["source_url"])
            status = check_row(row, texts[row["source_url"]])
        except Exception as exc:  # noqa: BLE001 - a failed fetch is reported, not hidden
            status = f"fetch_failed: {type(exc).__name__}"
        res.append((row["id"], row["source_url"], status))
    return pd.DataFrame(res, columns=["id", "source_url", "status"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frac", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=20261123)
    a = ap.parse_args()
    res = run(a.frac, a.seed)
    for r in res.itertuples(index=False):
        print(f"{r.id:16s} {r.status:24s} {r.source_url}")
    bad = ~res["status"].isin(["ok", "moved"])
    print(f"plans: {len(res)} sampled, {int(bad.sum())} errors, error rate {bad.mean():.1%}, "
          f"{int((res['status'] == 'moved').sum())} moved")


if __name__ == "__main__":
    main()
