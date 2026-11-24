"""US Census: annual US imports by country and 5-digit end-use code (no key).

www.census.gov/foreign-trade/statistics/product/enduse/imports/enduse_imports.xlsx ("Annual Country by 5-digit
End-Use Code, Annual totals", linked from foreign-trade/statistics/historical/enduse.html): one sheet, one row per
(CTY_CODE, END_USE) with CTY_DESC, COMM_DESC and value_YY columns (US dollars, one per year, ten years: 2016-2025
in the vintage of 2026-06-09). World total is CTY_CODE 0000. The file is replaced at the FT-900 Annual Revision
(server Last-Modified 2026-06-09 12:31 GMT, the release was 8:30 EDT that day) and has no version history.

Monthly data by country and end-use code exist only in api.census.gov (needs a key, sources/census_hs.py).
"""

from __future__ import annotations

import io
import re

import pandas as pd

from ai_tracker import http

URL = "https://www.census.gov/foreign-trade/statistics/product/enduse/imports/enduse_imports.xlsx"
SOURCE = "census_enduse"
COLUMNS = ("CTY_CODE", "CTY_DESC", "END_USE", "COMM_DESC")
YEAR_COL = re.compile(r"^value_(\d{2})$")


def _code(x) -> str:
    return str(x).strip()


def frame(content: bytes) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(content), dtype=object)


def parse(content: bytes | pd.DataFrame, cty_code: str, end_use: str, desc: str | None = None) -> pd.Series:
    """Annual values in MUSD for one country and end-use code, on a yearly PeriodIndex.

    `content` is the file or its `frame`. `desc` guards against a reused code: the file's COMM_DESC must equal it
    (case and spaces ignored)."""
    df = content if isinstance(content, pd.DataFrame) else frame(content)
    missing = [c for c in COLUMNS if c not in df.columns]
    years = {c: 2000 + int(m.group(1)) for c in df.columns if (m := YEAR_COL.match(str(c)))}
    if missing or not years:
        raise ValueError(f"enduse: unexpected columns {list(df.columns)[:8]} (missing {missing})")
    rows = df[(df["CTY_CODE"].map(_code) == cty_code) & (df["END_USE"].map(_code) == end_use)]
    if len(rows) != 1:
        raise ValueError(f"enduse: {len(rows)} rows for country {cty_code}, end use {end_use}")
    row = rows.iloc[0]
    if desc is not None and " ".join(str(row["COMM_DESC"]).split()).lower() != " ".join(desc.split()).lower():
        raise ValueError(f"enduse: {end_use} is {row['COMM_DESC']!r}, expected {desc!r}")
    vals = pd.to_numeric(pd.Series({years[c]: row[c] for c in years}), errors="coerce") / 1e6
    s = pd.Series(vals.to_numpy(dtype=float), index=pd.PeriodIndex([str(y) for y in vals.index], freq="Y-DEC"))
    return s.dropna().sort_index()


_CACHE: dict[str, pd.DataFrame] = {}  # one download and one parse per process for all series


def fetch(cty_code: str, end_use: str, desc: str | None = None) -> pd.Series:
    if URL not in _CACHE:
        _CACHE[URL] = frame(http.get(URL, SOURCE).content)
    return parse(_CACHE[URL], cty_code, end_use, desc)
