"""Sampling self-check of the S3 extraction: re-fetch each sampled exhibit and verify the row is there.

For each sampled row of curated/orders_backlog.csv the exhibit is fetched again (no cache) and
- the sentence at the locator (sentence #k of guidance_capex.sentences) has the stored SHA-256; if not, the whole
  document is searched for the hash ("moved");
- the number is in that sentence in one of the forms of its unit (value_patterns): USD as "$X billion", "$XB",
  "$X million", "$XM" or a table figure in millions or thousands ("7,400", "30,750"), percent as "X%" or "X percent"
  (absolute value), ratios as "X.Xx", "X.X times" or "X.X", GW as "X GW", "X gigawatts" or "from X to Y GW", MW as a
  number (in a table or before "MW");
- filed and accepted equal EDGAR's filingDate and acceptanceDateTime (submissions API, fetched again), and
  release_date equals the dateline of the exhibit (orders_backlog_corpus.dateline; empty when the dateline is missing
  or after the filing day);
- for a stop row: no sentence of the exhibit states the definition (stated_in): the measure word, the segment's word
  (not for total), a number in the unit's form, and for growth rates the basis words (organic, currency) and window
  words (trailing twelve months, sequential, year-end). It is a coarse check. A hit gives 'still_stated', and the
  reviewer reads the sentence.

    python -m ai_tracker.orders_check [--frac 0.3] [--seed 20261125]

This confirms location, hash, number and dates, not the semantics (definition, period, organic or not, first
document): that is for the independent review. Nothing is written except raw copies (data/raw).
"""

from __future__ import annotations

import argparse
import re

import pandas as pd

from ai_tracker import http
from ai_tracker.sources import guidance_capex, orders_backlog, orders_backlog_corpus, tsmc_sec

SOURCE = "orders_check"
OK = ("ok", "moved")


def _forms(v: float, decimals=(0, 1, 2)) -> list[str]:
    out = [f"{v:g}"] + [f"{v:.{d}f}" for d in decimals]
    return list(dict.fromkeys(out))


def _bare(f: str) -> str:
    """A number written as f, not part of a longer number."""
    return rf"(?<![\d.,]){re.escape(f)}(?![\d]|[.,]\d)"


def value_patterns(value: float, unit: str) -> list[str]:
    """Regexes for the ways a value in `unit` is written (module docstring). Signs are not matched."""
    v = abs(float(value))
    if unit == "MUSD":
        b = v / 1000
        billions = _forms(b)
        millions = list(dict.fromkeys(_forms(v) + [f"{v:,.0f}", f"{v:,.1f}", f"{v:,.2f}"]))
        thousands = list(dict.fromkeys([f"{v * 1000:,.0f}", f"{v * 1000:.0f}"]))
        return ([rf"\$\s?{re.escape(f)}\s*(?:billion|bn|B)\b" for f in billions]
                + [rf"\$\s?{re.escape(f)}\s*(?:million|mn|M)\b" for f in millions]
                + [_bare(f) for f in millions + thousands])
    if unit == "pct":
        return [_bare(f) + r"\)?\s?(?:%|percent|pct)" for f in _forms(v)]
    if unit == "ratio":
        return [_bare(f) for f in _forms(v)]
    if unit == "GW":
        # "29 GW", "7 gigawatts", and the first number of "from 50 to 55 GW"
        return [_bare(f) + r"(?:\s+to\s+[\d.]+)?\s?(?:GW|gigawatts?)\b" for f in _forms(v)]
    if unit == "MW":
        return [_bare(f) for f in _forms(v)]
    raise ValueError(f"unit {unit!r}")


def number_in(value: float, unit: str, sentence: str) -> bool:
    s = re.sub(r"\s+", " ", sentence)
    return any(re.search(p, s) for p in value_patterns(value, unit))


# ------------------------------------------------------------------ stops: is the definition still stated?

MEASURE_WORDS = {
    "orders": r"\borders?\b",
    "backlog": r"\bbacklog\b",
    "book_to_bill": r"\bbook[\s-]+to[\s-]+bill\b",
    "slot_reservations": r"\bslot\s+reservations?\b",
    "backlog_and_slot_reservations": r"\bbacklog\b.{0,80}\bslot\s+reservations?\b",
    "shipments": r"\bship(?:ments?|ped)\b",
    "sales": r"\bsales\b",
    "leases_signed": r"\bbookings?\b|\bleases?\s+signed\b|\bsigned\b",
    "signed_not_commenced": r"\bnot[\s-]+yet[\s-]+commenced\b|\bbacklog\b",
    "bookings": r"\bbookings?\b",
}
SEGMENT_WORDS = {
    "power": r"\bPower\b", "wind": r"\bWind\b", "electrification": r"\bElectrification\b",
    "gas_power": r"\bGas\s+Power\b|\bgas\s+turbines?\b", "electrical_americas": r"\bElectrical\s+Americas\b",
    "electrical_global": r"\bElectrical\s+Global\b", "electrical": r"\bElectrical\b", "data_centers": r"\bdata\s+cent",
    "ai_servers": r"\bAI\b", "gt_1mw": r">\s*1\s*MW|\bgreater\s+than\s+(?:a\s+)?(?:1|one)\s*(?:MW|megawatt)",
    "0_1mw": r"\b0\s*[-–]\s*1\s*(?:MW|megawatt)", "interconnection": r"\binterconnection\b", "other": r"\bother\b",
}
UNIT_WORDS = {
    "pct": r"\d\s?(?:%|percent)", "MUSD": r"\$\s?\d", "ratio": r"\d\.\d\s?x\b|\d\.\d\s+times\b|\d\.\d",
    "GW": r"\d\s?(?:GW|gigawatts?)\b", "MW": r"\d\s?(?:MW|megawatts?)\b",
}
ORGANIC_WORDS = {"organic": r"\borganic(?:ally)?\b", "cc": r"\bforeign\s+exchange\b|\bcurrency\b",
                 "reported": r"\breported\b"}
TTM_WORDS = r"\btrailing\b|\bTTM\b|\btwelve[\s-]+months?\b|\b12[\s-]+months?\b|\brolling\b"
WINDOW_WORDS = {"ttm": TTM_WORDS, "ytd": r"\byear[\s-]+to[\s-]+date\b|\bYTD\b|\b(?:six|nine)\s+months\b",
                "fy": r"\bfull[\s-]+year\b|\bfiscal\s+(?:year\s+)?\d{4}\b|\bFY\s?\d{2}|\b(?:throughout|for)\s+the\s+year\b"}
FORM_WORDS = {"qoq_pct": r"\bsequential(?:ly)?\b", "vs_ye_pct": r"\bend\s+of\s+(?:fourth\s+quarter\s+)?\d{4}\b|"
              r"\byear[\s-]+end\b|\bend\s+of\s+(?:the\s+)?(?:prior|last)\s+year\b", "yoy_mult": r"\d\s?x\b"}


BULLETS = ("•", "◾", "▪")
BEFORE, AFTER, CONTEXT = 25, 120, 150  # characters around a measure word: the number, then the basis and window words


def stated_in(row: pd.Series, sentence: str) -> bool:
    """The sentence plausibly states the row's definition (coarse; see the module docstring).

    Some match of the measure word has a number in the unit's form up to AFTER characters after it or BEFORE
    characters before it ("orders up 15%", "$5.0 billion backlog"); the basis, window and form words are looked for
    within CONTEXT characters of that match, the segment's word anywhere in the sentence. A headline bullet is its own
    statement, so the regions end at the bullets around the match.
    """
    s = re.sub(r"\s+", " ", sentence)
    seg = row["segment"]
    if seg != "total" and not re.search(SEGMENT_WORDS[seg], s, 0 if seg in ("power", "wind") else re.I):
        return False
    for m in re.finditer(MEASURE_WORDS[row["measure"]], s, re.I):
        # a headline bullet ("•", "◾") is its own statement: the regions stop at the bullets around the match
        lo = max([s.rfind(b, 0, m.start()) for b in BULLETS] + [-1]) + 1
        his = [i for i in (s.find(b, m.end()) for b in BULLETS) if i >= 0]
        hi = min(his) if his else len(s)
        near = s[max(lo, m.start() - BEFORE):min(hi, m.end() + AFTER)]
        ctx = s[max(lo, m.start() - CONTEXT):min(hi, m.end() + CONTEXT)]

        def has(p, text=ctx):
            return re.search(p, text, re.I) is not None

        if not re.search(UNIT_WORDS[row["unit"]], near, re.I):
            continue
        if row["form"] in FORM_WORDS and not has(FORM_WORDS[row["form"]]):
            continue
        if row["window"] in WINDOW_WORDS and not has(WINDOW_WORDS[row["window"]]):
            continue
        if row["window"] == "q" and (has(TTM_WORDS, near) or has(WINDOW_WORDS["ytd"], near)
                                     or has(WINDOW_WORDS["fy"], near)):
            continue
        org = row["organic"]
        if org in ORGANIC_WORDS and not has(ORGANIC_WORDS[org]):
            continue
        if org == "unspecified" and any(has(p, near) for p in ORGANIC_WORDS.values()):
            continue
        return True
    return False


def still_stated(row: pd.Series, text: str) -> list[int]:
    """Sentence numbers of the exhibit that plausibly state the stop row's definition."""
    return [k for k, s in enumerate(guidance_capex.sentences(text)) if stated_in(row, s)]


# ------------------------------------------------------------------ rows

def check_row(row: pd.Series, text: str) -> str:
    """'ok' | 'moved' | 'sentence_not_found' | 'number_not_in_sentence' | 'still_stated: #k,...'."""
    if row["row_type"] == "stop":
        hits = still_stated(row, text)
        return "ok" if not hits else "still_stated: " + ",".join(f"#{k}" for k in hits[:5])
    sents = guidance_capex.sentences(text)
    k = int(re.search(r"sentence #(\d+)", row["locator"]).group(1))
    at = sents[k] if k < len(sents) else None
    status = "ok"
    if at is None or guidance_capex.sentence_hash(at) != row["sentence_sha256"]:
        hits = [s for s in sents if guidance_capex.sentence_hash(s) == row["sentence_sha256"]]
        if not hits:
            return "sentence_not_found"
        at, status = hits[0], "moved"
    return status if number_in(row["value"], row["unit"], at) else "number_not_in_sentence"


def check_dates(row: pd.Series, filings: dict[str, dict], text: str) -> str:
    f = filings.get(row["accession"])
    if f is None:
        return "accession_not_in_submissions"
    if f["filed"] != row["filed"]:
        return f"filed_differs: {f['filed']}"
    if row["accepted"] and f["accepted"][:19] != row["accepted"][:19]:
        return f"accepted_differs: {f['accepted']}"
    return check_release_date(row, text)


def check_release_date(row: pd.Series, text: str) -> str:
    """release_date is the dateline when that is on or up to MAX_RELEASE_LEAD_DAYS before the filing, else empty."""
    dl = orders_backlog_corpus.dateline(text)
    valid = dl is not None and 0 <= (pd.Timestamp(row["filed"]) - pd.Timestamp(dl)).days \
        <= orders_backlog.MAX_RELEASE_LEAD_DAYS
    want = dl if valid else ""
    return "ok" if (row["release_date"] or "") == want else f"release_date_differs: dateline {dl}"


def fetch_text(url: str) -> str:
    return tsmc_sec.to_text(http.get(url, SOURCE).content.decode("utf-8", errors="replace"))


def _submissions(company: str) -> dict[str, dict]:
    cik = orders_backlog_corpus.CIKS[company]
    sub = http.get(orders_backlog_corpus.SUBMISSIONS.format(cik=cik), SOURCE).json()
    blocks = [sub["filings"]["recent"]] + [http.get(orders_backlog_corpus.SUBMISSIONS_FILE.format(name=f["name"]),
                                                    SOURCE).json() for f in sub["filings"].get("files", [])]
    return {acc: {"filed": b["filingDate"][i], "accepted": b["acceptanceDateTime"][i]}
            for b in blocks for i, acc in enumerate(b["accessionNumber"])}


def run(frac: float = 0.3, seed: int = 20261125, df: pd.DataFrame | None = None) -> pd.DataFrame:
    df = orders_backlog.load() if df is None else df
    sample = df.sample(frac=frac, random_state=seed).sort_values("id") if frac < 1 else df.sort_values("id")
    texts: dict[str, str] = {}
    subs: dict[str, dict] = {}
    res = []
    for _, row in sample.iterrows():  # sequential: several tracks share sec.gov's rate limit
        try:
            if row["company"] not in subs:
                subs[row["company"]] = _submissions(row["company"])
            if row["source_url"] not in texts:
                texts[row["source_url"]] = fetch_text(row["source_url"])
            text = texts[row["source_url"]]
            dates = check_dates(row, subs[row["company"]], text)
            status = check_row(row, text)
        except Exception as exc:  # noqa: BLE001 - a failed fetch is reported, not hidden
            status, dates = f"fetch_failed: {type(exc).__name__}", "not_checked"
        res.append((row["id"], row["row_type"], status, dates))
    return pd.DataFrame(res, columns=["id", "row_type", "status", "dates"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frac", type=float, default=0.3)
    ap.add_argument("--seed", type=int, default=20261125)
    a = ap.parse_args()
    res = run(a.frac, a.seed)
    for r in res.itertuples(index=False):
        print(f"{r.id:26s} {r.row_type:6s} {r.status:28s} {r.dates}")
    bad = ~res["status"].isin(OK) | (res["dates"] != "ok")
    print(f"{len(res)} checked ({int((res['row_type'] == 'stop').sum())} stops), {int(bad.sum())} errors, "
          f"error rate {bad.mean():.1%}, {int((res['status'] == 'moved').sum())} moved")


if __name__ == "__main__":
    main()
