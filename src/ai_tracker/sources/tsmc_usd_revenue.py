"""TSMC's quarterly revenue in US$, parsed deterministically from the quarterly release in the same 6-K documents
tsmc_guidance reads (fix track X8 after review R11, finding R11-7; register 2026-11-24 "F1: rättning efter R11").

Every quarterly release from 2017-01 states the quarter's revenue in US dollars in one fixed form:

    In US dollars, <first|second|third|fourth> quarter revenue was $<x> billion

Only this form is coded. The quarter is the latest calendar quarter with that ordinal that ended before the filing
date (the release reports the quarter just ended). Values in million US$ (as stated, two decimals of a billion).
One record per (filing, document); known_from = the filing date (tsmc_guidance's convention); a repeat adds no
vintage. Used for F1's US$ sensitivity of TSMC's surprise against its own US$ guidance (from 2017Q3).
"""

from __future__ import annotations

import hashlib
import re

import pandas as pd

from ai_tracker.sources import tsmc_guidance

_ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4}
USD_REV_RE = re.compile(r"(?i)In\s+US\s+dollars?\s*,\s*(?P<ord>first|second|third|fourth)\s+quarter\s+revenue\s+"
                        r"was\s+(?:US)?\s?\$\s?(?P<x>\d+(?:\.\d+)?)\s*billion")
COLUMNS = ["period", "value", "filed", "accepted", "accession", "document", "form", "offset", "sentence_sha256"]
SCAN_FROM = "2017-01-01"  # the form was checked in every 6-K from here (2016Q4 to 2026Q3); earlier ones are not read


def _sha(text: str) -> str:
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().encode("utf-8")).hexdigest()


def reported_quarter(filed: str, ordinal: int) -> pd.Period:
    """The latest calendar quarter with this ordinal that ended before the filing date."""
    q = pd.Period(pd.Timestamp(filed), "Q-DEC") - 1
    while q.quarter != ordinal:
        q -= 1
    return q


def parse(text: str, filed: str) -> list[dict]:
    """US$ revenue statements in one document's text: period, value (million US$). The last one per quarter wins."""
    out = {}
    for m in USD_REV_RE.finditer(text):
        q = reported_quarter(filed, _ORD[m.group("ord").lower()])
        out[str(q)] = {"period": str(q), "value": float(m.group("x")) * 1000, "offset": m.start(),
                       "sentence_sha256": _sha(m.group(0))}
    return list(out.values())


def records(items=None) -> pd.DataFrame:
    """One row per (filing, document, quarter); `items` as tsmc_guidance.records()."""
    if items is None:
        items = [(f, tsmc_guidance.documents(f)) for f in tsmc_guidance.filings() if f.filed >= SCAN_FROM]
    rows = []
    for f, docs in items:
        for name, text in docs:
            for r in parse(text, f.filed):
                rows.append({**r, "filed": f.filed, "accepted": f.accepted, "accession": f.accession,
                             "document": name, "form": f.form})
    return pd.DataFrame(rows, columns=COLUMNS)


def vintages(recs: pd.DataFrame) -> pd.DataFrame:
    """Release-dated (period, value, known_from); a repeated value adds no row."""
    return tsmc_guidance.vintages(recs, "value")
