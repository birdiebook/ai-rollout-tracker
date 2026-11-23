"""BEA NIPA flat files (apps.bea.gov/national/Release/TXT/), no API key.

NipaDataQ.txt: "%SeriesCode,Period,Value" for every quarterly NIPA series (values with thousands
separators); SeriesRegister.txt: code, label, metric, scale (-6 = millions), table:line.
Only the latest vintage (all estimates as revised up to the last release) -> backfill. ~35 MB.
"""

from __future__ import annotations

import csv
import io

import pandas as pd

from ai_tracker import http

BASE = "https://apps.bea.gov/national/Release/TXT/"
SOURCE = "bea"


def parse_data(text: str, codes: set[str]) -> dict[str, pd.Series]:
    out: dict[str, dict[str, float]] = {c: {} for c in codes}
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    if [h.lstrip("%") for h in header[:3]] != ["SeriesCode", "Period", "Value"]:
        raise ValueError(f"BEA: unexpected header {header}")
    for code, period, value in reader:
        if code in out:
            out[code][period] = float(value.replace(",", ""))
    return {c: pd.Series(v, dtype=float).set_axis(pd.PeriodIndex(list(v), freq="Q-DEC")).sort_index()
            for c, v in out.items()}


_CACHE: dict[str, str] = {}


def fetch(code: str, file: str = "NipaDataQ.txt") -> pd.Series:
    if file not in _CACHE:
        _CACHE[file] = http.get(BASE + file, SOURCE, timeout=300).text
    s = parse_data(_CACHE[file], {code})[code]
    if s.empty:
        raise ValueError(f"BEA: series {code} not in {file}")
    return s
