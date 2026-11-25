"""Baidu figures stated only in sentences of its 6-K results releases: curated, regex-coded (track CN1).

Baidu states AI Cloud Infra revenue (from the 2025Q3 release) and Baidu Core's non-online marketing revenue
(2020Q3 - 2025Q3 releases) in sentences, in RMB billions with one decimal; no table holds them. The coding rules are
locked in the register entry 2026-11-25 CN1 (docs/mattregister.md, "Kodningsregler för texten"):

1. Corpus: the results release (exhibit 99.1) of every Baidu 6-K whose title is "Baidu Announces <First|...|Fourth>
   Quarter ... Results", filed from 2020-01-01. Text = tsmc_sec.to_text, sentences = guidance_capex.sentences,
   locator "sentence #k" counted from 0.
2. Candidate sentence: names "AI Cloud Infra" or "non-(online )?marketing revenue", and "billion".
3. A value is coded only when "was" or "reached" stands directly before the amount ("RMB" optional). Hedged amounts
   ("approximately", "about", "roughly", "around", "over", "more than", "exceeded") never match. The amount is in RMB
   billions; the series store it x 1000 as MRMB.
4. The quarter is the release's reported quarter. A sentence that names another quarter or a full/fiscal year is not
   coded. In a fourth-quarter release only sentences before the heading "Fiscal Year <year> Results" are coded.
5. At most one value per series and release; two different amounts raise CodingError.
6. Each row of curated/china_text.csv has the number, unit, period, filing date, acceptance time, URL, accession,
   locator and the SHA-256 of the sentence; the sentence itself is written only under data/raw (gitignored).
7. Candidates that are not coded are counted and listed with the reason (`python -m ai_tracker.sources.china_text`).

    python -m ai_tracker.sources.china_text [--write]

Nothing is guessed: a candidate the rules do not code stays uncoded, and the doc says why.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass

import pandas as pd

from ai_tracker import config
from ai_tracker.sources import china_parse, china_sec, guidance_capex
from ai_tracker.sources.tsmc_sec import to_text

CSV_PATH = config.REPO / "curated" / "china_text.csv"
SENTENCES_DIR = config.REPO / "data" / "raw" / "china_text_sentences"  # gitignored
SINCE = "2020-01-01"
COMPANY = "bidu"
UNIT = "RMB billion"
COLUMNS = ("id", "company", "series", "period", "value", "unit", "filed", "accepted", "form", "source_url",
           "accession", "locator", "sentence_sha256", "note")

CANDIDATE = re.compile(r"AI Cloud Infra|non-(?:online )?marketing revenue", re.I)
AMOUNT = r"(?:was|reached) (?:RMB ?)?(\d+(?:\.\d+)?) billion"
CODES = {
    "rev_bidu_ai_cloud_infra": re.compile(rf"revenue from AI Cloud Infra {AMOUNT}", re.I),
    "rev_bidu_core_nonads": re.compile(rf"non-(?:online )?marketing revenue(?: from Baidu Core)? {AMOUNT}", re.I),
}
QUARTER_NAMED = re.compile(r"\b(first|second|third|fourth) quarter(?: of)?,? (\d{4})\b", re.I)
YEAR_NAMED = re.compile(r"\b(?:full[- ]year|fiscal year|for the year)\b", re.I)
FY_HEADING = re.compile(r"\bFiscal Year (\d{4}) Results\b")


class CodingError(RuntimeError):
    pass


@dataclass(frozen=True)
class Doc:
    filed: str
    accepted: str
    form: str
    accession: str
    url: str
    quarter: pd.Period
    text: str


@dataclass(frozen=True)
class Row:
    id: str
    company: str
    series: str
    period: str
    value: float
    unit: str
    filed: str
    accepted: str
    form: str
    source_url: str
    accession: str
    locator: str
    sentence_sha256: str
    note: str = ""


def corpus(since: str = SINCE) -> list[Doc]:
    """Baidu results releases (rule 1), oldest first. Network (cached documents)."""
    out = []
    for f in china_sec.filings(china_sec.CIKS[COMPANY], since=since):
        index = json.loads(china_sec.cached_get(f.url("index.json")))
        for doc in china_sec.candidate_docs(f, index):
            text = to_text(china_sec.cached_get(f.url(doc)).decode("utf-8", errors="replace"))
            q = china_parse.bidu_quarter(text)
            if q is not None:
                out.append(Doc(f.filed, f.accepted, f.form, f.accession, f.url(doc), q, text))
                break
    return out


def codable_span(doc: Doc) -> int:
    """Characters of the text that may be coded (rule 4): a Q4 release up to its "Fiscal Year <year> Results"."""
    if doc.quarter.quarter == 4:
        m = FY_HEADING.search(doc.text)
        if m and int(m.group(1)) == doc.quarter.year:
            return m.start()
    return len(doc.text)


def reason_not_coded(sentence: str, quarter: pd.Period, in_span: bool) -> str | None:
    """Why a candidate sentence is not coded for the release quarter, or None if a rule codes it (rules 3 and 4)."""
    if not in_span:
        return "after the fiscal-year heading (annual figures)"
    if YEAR_NAMED.search(sentence):
        return "names a full or fiscal year"
    for name, year in QUARTER_NAMED.findall(sentence):
        if pd.Period(f"{year}Q{china_parse.ORDINAL[name.lower()]}", freq="Q-DEC") != quarter:
            return f"names another quarter ({name} quarter {year})"
    if not any(p.search(sentence) for p in CODES.values()):
        return "no 'was/reached <amount> billion' after the measure (hedged, growth only, or another wording)"
    return None


def code_doc(doc: Doc) -> tuple[list[Row], list[tuple[str, int, str]], dict[int, str]]:
    """(rows, uncoded candidates [(accession, k, reason)], {k: sentence}) of one release (rules 2-5)."""
    sents = guidance_capex.sentences(doc.text)
    span = codable_span(doc)
    rows: dict[str, Row] = {}
    uncoded, kept = [], {}
    pos = 0
    for k, s in enumerate(sents):
        start = doc.text.find(s, pos)
        pos = start + len(s) if start >= 0 else pos
        if not (CANDIDATE.search(s) and "billion" in s):
            continue
        why = reason_not_coded(s, doc.quarter, start < span)
        if why is not None:
            uncoded.append((doc.accession, k, why))
            continue
        for series, pat in CODES.items():
            m = pat.search(s)
            if not m:
                continue
            value = float(m.group(1))
            prev = rows.get(series)
            if prev is not None:
                if prev.value != value:
                    raise CodingError(f"{doc.accession}: two amounts for {series}: {prev.value} and {value}")
                continue
            rows[series] = Row(
                id=f"{COMPANY}-{doc.filed}-{series.removeprefix('rev_bidu_')}", company=COMPANY, series=series,
                period=str(doc.quarter), value=value, unit=UNIT, filed=doc.filed, accepted=doc.accepted,
                form=doc.form, source_url=doc.url, accession=doc.accession, locator=f"sentence #{k}",
                sentence_sha256=guidance_capex.sentence_hash(s))
            kept[k] = s
    return list(rows.values()), uncoded, kept


def extract(docs: list[Doc]) -> tuple[list[Row], list[tuple[str, int, str]]]:
    rows, uncoded = [], []
    for d in docs:
        r, u, kept = code_doc(d)
        rows += r
        uncoded += u
        for row in r:
            k = int(row.locator.removeprefix("sentence #"))
            SENTENCES_DIR.mkdir(parents=True, exist_ok=True)
            (SENTENCES_DIR / f"{row.id}.txt").write_text(kept[k], encoding="utf-8")
    return rows, uncoded


def write(rows: list[Row], path=CSV_PATH) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r.series, r.period, r.filed)):
            d = asdict(r)
            d["value"] = f"{r.value:g}"
            w.writerow(d)


def load(path=CSV_PATH) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False).assign(value=lambda d: d["value"].astype(float))


def series_rows(key: str, path=CSV_PATH) -> pd.DataFrame:
    """Release-dated rows (period, value MRMB, known_from) of one text series from the curated file."""
    df = load(path)
    df = df[df["series"] == key]
    out = pd.DataFrame({"period": df["period"], "value": df["value"] * 1000.0,
                        "known_from": pd.to_datetime(df["filed"])})
    return out.sort_values(["known_from", "period"], ignore_index=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="write curated/china_text.csv")
    a = ap.parse_args()
    rows, uncoded = extract(corpus())
    for r in rows:
        print(f"{r.series:26s} {r.period} {r.value:>6g} {r.filed} {r.accession} {r.locator}")
    print(f"{len(rows)} coded rows, {len(uncoded)} candidates not coded")
    for acc, k, why in uncoded:
        print(f"  not coded: {acc} sentence #{k}: {why}")
    if a.write:
        write(rows)
        print(f"wrote {CSV_PATH}")


if __name__ == "__main__":
    main()
