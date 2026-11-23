"""Sampling self-check of the B4 extraction: re-fetch the source and verify each sampled value is there.

AI KPIs (curated/ai_kpis.csv, agent-extracted): the document is fetched again (no cache), the sentence at the locator
(sentence #k of guidance_capex.sentences) must have the stored SHA-256, and the coded number - written the way the
company writes it ("$13 billion", "650 million", "53,000", "one billion", "40%") - or, for a capacity code, a word
of that code must appear in it. If the sentence moved, the document is searched for the hash ("moved").

Nvidia outlook (deterministic parse): the filing is fetched again and parsed; the sampled record's values must
come out the same.

    python -m ai_tracker.ai_kpis_check [--frac 0.2] [--seed 20261123] [--no-nvda]

Like guidance_check, this confirms location, hash and number, not the semantics (period, definition, basis): that
is for the independent review R5. Nothing is written except raw copies (data/raw).
"""

from __future__ import annotations

import argparse
import re

import pandas as pd

from ai_tracker import http
from ai_tracker.sources import ai_kpis, guidance_capex, nvda_guidance, tsmc_sec

SOURCE = "ai_kpis_check"

CAPACITY_WORDS = {
    2: r"significantly|extreme|sold out|fully subscribed|well ahead",
    1: r"constrain|exceed|ahead of|higher than|short|unserved|sold out|subscribed|committed",
    0: r"in line|balance",
    -1: r"secured|sufficient|enough|to meet demand|eased|no longer",
    -2: r"excess|exceeded our demand|underutili",
}
_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 10: "ten"}


def _num_forms(x: float) -> list[str]:
    """Ways a number can be written: 1.5 -> 1.5; 37 -> 37; 53000 -> 53,000; 1 -> one."""
    forms = [f"{x:g}", f"{x:,.0f}" if x == int(x) else f"{x:,}"]
    if x == int(x) and int(x) in _WORDS:
        forms.append(_WORDS[int(x)])
    return list(dict.fromkeys(forms))


def number_patterns(value: float, unit: str) -> list[str]:
    """Regexes for a stored value in the way the company writes it."""
    out = []
    if unit == "miljoner användare":
        out += [rf"{f}\s*million" for f in _num_forms(value)]
        if value >= 1000:
            out += [rf"{f}\s*billion" for f in _num_forms(value / 1000)]
    elif unit == "MUSD":
        out += [rf"\$\s?{f}\s*million" for f in _num_forms(value)]
        out += [rf"\$\s?{f}\s*billion" for f in _num_forms(value / 1000)]
    elif unit in ("biljoner tokens",):
        out += [rf"{f}\s*trillion" for f in _num_forms(value)]
    elif unit == "miljarder tokens per minut":
        out += [rf"{f}\s*billion" for f in _num_forms(value)]
    elif unit == "antal":
        out += [rf"(?<![\d,.]){re.escape(f)}(?![\d,])" for f in _num_forms(value)]
    elif unit == "%":
        out += [rf"(?<![\d.]){f}\s?%" for f in _num_forms(value)]
    elif unit == "procentenheter":
        out += [rf"(?<![\d.]){f}\s*(?:points?|pts)" for f in _num_forms(value)]
    else:
        raise ValueError(f"no pattern for unit {unit!r}")
    return out


def sentence_ok(row: pd.Series, sentence: str) -> bool:
    if row["kind"] == "code":
        return re.search(CAPACITY_WORDS[int(row["code"])], sentence, re.I) is not None
    vals = [row["value_lo"]] + ([row["value_hi"]] if row["kind"] == "range" else [])
    return all(any(re.search(p, sentence, re.I) for p in number_patterns(v, row["unit"])) for v in vals)


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
    return status if sentence_ok(row, at) else "number_not_in_sentence"


def fetch_text(url: str) -> str:
    return tsmc_sec.to_text(http.get(url, SOURCE).content.decode("utf-8", errors="replace"))


def check_nvda_record(rec: pd.Series, docs: list[tuple[str, str, str]]) -> str:
    text = next((t for typ, name, t in docs if name == rec["document"]), None)
    if text is None:
        return "document_not_found"
    o = nvda_guidance.parse_outlook(text)
    if o is None:
        return "no_outlook"
    for f in nvda_guidance.FIELDS:
        a, b = rec.get(f), o.values.get(f)
        if pd.isna(a) != (b is None) or (b is not None and abs(a - b) > 1e-6):
            return f"value_differs: {f}"
    return "ok"


def run(frac: float = 0.2, seed: int = 20261123, nvda: bool = True) -> dict[str, pd.DataFrame]:
    out = {}
    df = ai_kpis.load()
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
    out["kpi"] = pd.DataFrame(res, columns=["id", "source_url", "status"])
    if nvda:
        recs = nvda_guidance.records().drop_duplicates(["accession", "document", "period"])
        smp = recs.sample(frac=frac, random_state=seed)
        res = []
        for _, rec in smp.iterrows():
            url = nvda_guidance.FULL_TEXT.format(cik=nvda_guidance.CIK, acc=rec["accession"])
            try:
                raw = http.get(url, SOURCE).content.decode("utf-8", errors="replace")
                status = check_nvda_record(rec, nvda_guidance.split_documents(raw))
            except Exception as exc:  # noqa: BLE001
                status = f"fetch_failed: {type(exc).__name__}"
            res.append((f"{rec['period']} {rec['filed']} {rec['document']}", url, status))
        out["nvda"] = pd.DataFrame(res, columns=["id", "source_url", "status"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frac", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=20261123)
    ap.add_argument("--no-nvda", action="store_true")
    a = ap.parse_args()
    for name, res in run(a.frac, a.seed, not a.no_nvda).items():
        for r in res.itertuples(index=False):
            print(f"{name:5s} {r.id:40s} {r.status}")
        bad = ~res["status"].isin(["ok", "moved"])
        print(f"{name}: {len(res)} sampled, {int(bad.sum())} errors, error rate {bad.mean():.1%}, "
              f"{int((res['status'] == 'moved').sum())} moved\n")


if __name__ == "__main__":
    main()
