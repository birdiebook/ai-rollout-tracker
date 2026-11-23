"""US Census international trade (FT-900): US goods imports by partner country, monthly.

www.census.gov/foreign-trade/balance/country.xlsx: one row per (year, CTY_CODE) with IJAN..IDEC (imports)
and EJAN..EDEC (exports), millions of USD, not seasonally adjusted, Census basis, from 1985. Months not
yet published are 0 in the current year's row. Latest vintage only (annual revisions in June, unverified).
HS-level detail (8471, 8473, 8542) is only in api.census.gov, which requires an API key.
"""

from __future__ import annotations

import io

import pandas as pd

from ai_tracker import http

URL = "https://www.census.gov/foreign-trade/balance/country.xlsx"
SOURCE = "census_trade"
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def parse(content: bytes, cty_code: str, flow: str = "I") -> pd.Series:
    df = pd.read_excel(io.BytesIO(content), dtype=object)
    rows = df[df["CTY_CODE"].astype(str).str.strip() == cty_code].copy()
    if rows.empty:
        raise ValueError(f"trade: country {cty_code} not found")
    rows["year"] = rows["year"].astype(int)
    last_year = rows["year"].max()
    out = {}
    for _, r in rows.sort_values("year").iterrows():
        for i, m in enumerate(MONTHS, start=1):
            v = float(r[flow + m])
            if r["year"] == last_year and v == 0:  # not yet published
                continue
            out[pd.Period(f"{r['year']}-{i:02d}", freq="M")] = v
    s = pd.Series(out, dtype=float).sort_index()
    return s


_CACHE: dict[str, bytes] = {}


def fetch(cty_code: str, flow: str = "I") -> pd.Series:
    if URL not in _CACHE:
        _CACHE[URL] = http.get(URL, SOURCE).content
    return parse(_CACHE[URL], cty_code, flow)
