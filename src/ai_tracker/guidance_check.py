"""Sampling check of extracted guidance: re-fetch the source and verify each sampled value is there.

Capex guidance (curated/guidance_capex.csv, agent-extracted): the document is fetched again, its sentence at the
locator (sentence #k of guidance_capex.sentences) must have the stored SHA-256, and the guided number(s) - or,
for a direction, a word of that direction - must appear in that sentence. If the sentence moved, the whole
document is searched for the hash ("moved", counted as located but reported).

TSMC guidance (deterministic parse): the 6-K document is fetched again and the revenue range must appear in it as
"NT$/US$ x billion ... y billion" near the parsed values.

Neighbour check (R11-1, `--neighbours`): every document of the curated CSV is fetched again, and the sentence after
each sentence with a capex word (guidance_capex.candidates, "next") is listed when it holds a $ amount in billions
and is not coded. A hit is for the agent to read; nothing is coded automatically.

    python -m ai_tracker.guidance_check [--frac 0.2] [--seed 0] [--tsmc] [--neighbours]

Prints one line per sampled value and the error rate. Nothing is written except http raw copies (data/raw).
"""

from __future__ import annotations

import argparse
import re

import pandas as pd

from ai_tracker import http
from ai_tracker.sources import guidance_capex as gc
from ai_tracker.sources import tsmc_guidance, tsmc_sec

SOURCE = "guidance_check"

# words that must occur in a sentence coded with this direction (case-insensitive)
DIRECTION_WORDS = {
    2: r"significant|material|meaningful|notabl",
    1: r"increase|grow|higher|exceed|up\b",
    0: r"similar|flat|unchanged|remain",
    -1: r"decrease|declin|lower|moderate|down\b",
    -2: r"significant|material|meaningful|sharp",
}


def number_pattern(value_musd: float) -> str:
    """Regex for a MUSD value written in billions: 29000 -> 29 / 29.0, 8120 -> 8.12 / 8.120."""
    b = round(value_musd / 1000, 3)
    whole, _, frac = f"{b:.3f}".rstrip("0").rstrip(".").partition(".")
    tail = rf"\.{frac}0*" if frac else r"(?:\.0+)?"
    return rf"(?<![\d.]){whole}{tail}(?![\d])"


def sentence_ok(row: pd.Series, sentence: str) -> bool:
    if row["kind"] == "direction":
        return re.search(DIRECTION_WORDS[int(row["direction_code"])], sentence, re.I) is not None
    vals = [row["value_lo"]] + ([row["value_hi"]] if pd.notna(row["value_hi"]) else [])
    return all(re.search(number_pattern(v), sentence) for v in vals)


def check_capex_row(row: pd.Series, text: str) -> str:
    """'ok' | 'moved' (sentence found elsewhere, number there) | 'sentence_not_found' | 'number_not_in_sentence'."""
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


def check_tsmc_record(rec: pd.Series, text: str) -> str:
    cur = "US" if rec["currency"] == "USD" else "NT"
    lo, hi = number_pattern(rec["rev_lo"]), number_pattern(rec["rev_hi"])
    rx = rf"{cur}\s?\$\s?{lo}\s*billion\s*(?:and|to)\s*{cur}\s?\$\s?{hi}\s*billion"
    return "ok" if re.search(rx, text, re.I) else "number_not_in_document"


def fetch_text(url: str) -> str:
    return tsmc_sec.to_text(http.get(url, SOURCE).content.decode("utf-8", errors="replace"))


def uncoded_next_sentences(sents: list[str], coded: set[int], coded_sha: set[str]) -> list[int]:
    """Sentence numbers of 'next' candidates with a $ amount in billions that no CSV row codes (R11-1)."""
    return [i for i, why in gc.candidates(sents).items()
            if why == "next" and i not in coded and gc.sentence_hash(sents[i]) not in coded_sha
            and gc.AMOUNT_RE.search(sents[i])]


def neighbour_check(df: pd.DataFrame | None = None, fetch=None) -> pd.DataFrame:
    """For every document in the CSV: uncoded 'next' sentences with an amount (status 'read'), or the fetch error."""
    df = gc.load() if df is None else df
    fetch = fetch or fetch_text
    rows = []
    for url, g in df.groupby("source_url", sort=True):
        try:
            sents = gc.sentences(fetch(url))
        except Exception as exc:  # noqa: BLE001 - a failed fetch is reported, not hidden
            rows.append((url, None, f"fetch_failed: {type(exc).__name__}", ""))
            continue
        coded = {int(m.group(1)) for loc in g["locator"] if (m := re.search(r"sentence #(\d+)", loc))}
        for i in uncoded_next_sentences(sents, coded, set(g["sentence_sha256"])):
            rows.append((url, i, "read", gc.sentence_hash(sents[i])))
        if not any(r[0] == url for r in rows):
            rows.append((url, None, "ok", ""))
    return pd.DataFrame(rows, columns=["source_url", "sentence", "status", "sentence_sha256"])


def run(frac: float = 0.2, seed: int = 0, tsmc: bool = True) -> dict[str, pd.DataFrame]:
    out = {}
    df = gc.load()
    sample = df.sample(frac=frac, random_state=seed).sort_values("id")
    texts: dict[str, str] = {}
    res = []
    for _, row in sample.iterrows():
        try:
            text = texts.setdefault(row["source_url"], fetch_text(row["source_url"]))
            status = check_capex_row(row, text)
        except Exception as exc:  # noqa: BLE001 - a failed fetch is reported, not hidden
            status = f"fetch_failed: {type(exc).__name__}"
        res.append((row["id"], row["source_url"], status))
    out["capex"] = pd.DataFrame(res, columns=["id", "source_url", "status"])
    if tsmc:
        recs = tsmc_guidance.records()
        recs = recs.drop_duplicates(["accession", "document", "period"])
        smp = recs.sample(frac=frac, random_state=seed)
        res = []
        for _, rec in smp.iterrows():
            url = tsmc_sec.ARCHIVE.format(cik=tsmc_guidance.CIK, acc=rec["accession"].replace("-", ""), doc=rec["document"])
            try:
                status = check_tsmc_record(rec, fetch_text(url))
            except Exception as exc:  # noqa: BLE001
                status = f"fetch_failed: {type(exc).__name__}"
            res.append((f"{rec['period']} {rec['filed']} {rec['document']}", url, status))
        out["tsmc"] = pd.DataFrame(res, columns=["id", "source_url", "status"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frac", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-tsmc", action="store_true")
    ap.add_argument("--neighbours", action="store_true", help="R11-1: uncoded sentences after capex sentences")
    a = ap.parse_args()
    if a.neighbours:
        res = neighbour_check()
        for r in res.itertuples(index=False):
            print(f"{r.status:10s} {r.source_url} {'' if r.sentence is None else '#' + str(int(r.sentence))}")
        print(f"{res['source_url'].nunique()} documents, {int((res['status'] == 'read').sum())} sentences to read, "
              f"{int(res['status'].str.startswith('fetch_failed').sum())} fetch failures")
        return
    for name, res in run(a.frac, a.seed, not a.no_tsmc).items():
        for r in res.itertuples(index=False):
            print(f"{name:6s} {r.id:45s} {r.status}")
        bad = ~res["status"].isin(["ok", "moved"])
        print(f"{name}: {len(res)} sampled, {int(bad.sum())} errors, error rate {bad.mean():.1%}, "
              f"{int((res['status'] == 'moved').sum())} moved\n")


if __name__ == "__main__":
    main()
