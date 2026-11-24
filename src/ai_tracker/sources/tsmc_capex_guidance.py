"""TSMC's annual capital expenditure outlook, parsed deterministically from the same 6-K documents tsmc_guidance reads
(track F1, register 2026-11-24 "F1: revideringar av guidance ...").

Until about 2015 TSMC's quarterly release and presentation state the year's capex outlook ("2010 capital expenditure
to be around US$ 4.8 billion", "TSMC further expects the capital expenditures for 2012 to be about US$6 billion",
"2015 Capital Expenditures to be between US$ 10.5 billion and US$ 11 billion"). In 2016-2021 the release states the
budget in January and when it changes; from 2022 only the January budget (later changes were given on the call only,
which is not in EDGAR; review R11-8). Only one strict sentence form is coded:

    <year> [total] capital expenditure(s)|capex|capital budget ... | capital expenditure(s) [estimate] for <year> ...
    then a verb (to be, will be, expected to be, to remain), then about | around | approximately | between |
    in the range of | in the range between, then US$x [billion] (and|to) US$y billion, or US$x billion.

No amount and no sentence end may stand between the subject and the verb (_GAP). Other wordings (near the mid point
of a range, approach, above, likely to be in the previously forecast range) are not coded. Known uncoded statements
(R11-8): all for 2003, 2009-07-30 (an amount between subject and verb: the raise is dated from 2009-07-31) and
2012-04-26 (a raise to US$8-8.5 billion in another wording). The guided year must be named and must be the filing year or the next; an earlier year would be an outcome.
Values in million US$. One record per (filing, document, year): within a document the last statement for the year
counts. known_from = the filing date (tsmc_guidance's convention); repeats add no vintage (tsmc_guidance.vintages).
The matched sentence is kept only as a SHA-256 (the text stays in data/raw, the repo is public).
"""

from __future__ import annotations

import hashlib
import re

import pandas as pd

from ai_tracker.sources import tsmc_guidance

DEFINITION = "TSMC_CAPEX_USD"
_SUBJECT = (r"(?:(?P<y1>20\d\d)\s*,?\s*(?:total\s+)?(?:capital\s+expenditures?|capex|capital\s+budget)"
            r"|(?:capital\s+expenditures?|capex|capital\s+budget)(?:\s+estimate)?\s+for\s+(?P<y2>20\d\d))")
_GAP = r"(?:(?!\.\s)[^$]){0,120}?"  # no amount and no sentence end between the subject and the verb
_VERB = r"\b(?:to\s+be|will\s+be|expected\s+to\s+be|to\s+remain)\s+"
_QUAL = r"(?P<qual>in\s+the\s+range\s+(?:of|between)|between|about|around|approximately)\s*"
_AMOUNT = (r"US\s?\$\s?(?P<lo>\d+(?:\.\d+)?)\s*(?:billion\s*)?(?:(?:and|to|-|–)\s*(?:US\s?\$\s?)?"
           r"(?P<hi>\d+(?:\.\d+)?)\s*)?billion")
CAPEX_RE = re.compile(r"(?i)" + _SUBJECT + _GAP + _VERB + _QUAL + _AMOUNT)
COLUMNS = ["period", "year", "kind", "lo", "hi", "filed", "accepted", "accession", "document", "form", "offset",
           "sentence_sha256"]


def _sha(text: str) -> str:
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().encode("utf-8")).hexdigest()


def parse(text: str, filed: str) -> list[dict]:
    """Capex outlook statements in one document's text: year, kind (approx/range), lo, hi (million US$)."""
    out = {}
    fy = pd.Timestamp(filed).year
    for m in CAPEX_RE.finditer(text):
        year = int(m.group("y1") or m.group("y2"))
        if year not in (fy, fy + 1):
            continue  # an earlier year is an outcome; a later one is not a statement we code
        lo, hi = float(m.group("lo")), float(m.group("hi")) if m.group("hi") else None
        qual = re.sub(r"\s+", " ", m.group("qual").lower())
        is_range = hi is not None
        if is_range and not qual.startswith(("between", "in the range")):
            continue  # "about US$x to y" is not a form we code
        if not is_range:
            hi = lo
        if lo > hi or lo <= 0:
            continue
        out[year] = {"year": year, "kind": "range" if is_range else "approx", "lo": lo * 1000, "hi": hi * 1000,
                     "offset": m.start(), "sentence_sha256": _sha(m.group(0))}
    return list(out.values())


def records(items=None) -> pd.DataFrame:
    """One row per (filing, document, year) with a capex outlook; `items` as tsmc_guidance.records()."""
    if items is None:
        items = [(f, tsmc_guidance.documents(f)) for f in tsmc_guidance.filings()]
    rows = []
    for f, docs in items:
        for name, text in docs:
            for r in parse(text, f.filed):
                rows.append({"period": str(r["year"]), **r, "filed": f.filed, "accepted": f.accepted,
                             "accession": f.accession, "document": name, "form": f.form})
    return pd.DataFrame(rows, columns=COLUMNS)


def vintages(recs: pd.DataFrame, field: str) -> pd.DataFrame:
    """Release-dated (period, value, known_from) of `lo` or `hi`; a repeated value adds no row."""
    return tsmc_guidance.vintages(recs, field)
