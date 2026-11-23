"""US Census Construction Spending (C30): value of private construction put in place, by type.

Files: www.census.gov/construction/c30/xlsx/privsatime.xlsx (SAAR) and privtime.xlsx (NSA), monthly,
millions of USD. Column "Data center" (under Office) from 2014-01. Month labels like "Sep-26p" / "Aug-26r":
p = preliminary, r = revised (the latest month is preliminary, the two before it revised; annual
revisions in July, unverified). The files hold only the latest vintage.
"""

from __future__ import annotations

import io
import re

import pandas as pd

from ai_tracker import http

BASE = "https://www.census.gov/construction/c30/xlsx/"
FILES = {"sa": "privsatime.xlsx", "nsa": "privtime.xlsx"}
SOURCE = "census_c30"
_MONTH = re.compile(r"^([A-Z][a-z]{2})-(\d{2})([pr]?)$")


def parse(content: bytes, column: str = "Data center") -> pd.DataFrame:
    """Frame indexed by monthly period with columns value (MUSD) and flag ('', 'p' or 'r')."""
    raw = pd.read_excel(io.BytesIO(content), header=None, dtype=object)
    header = next(i for i in range(len(raw)) if str(raw.iat[i, 0]).strip() == "Date")
    names = [str(x).strip() for x in raw.iloc[header]]
    if column not in names:
        raise ValueError(f"C30: column {column!r} not found")
    col = names.index(column)
    rows = []
    for label, value in zip(raw.iloc[header + 1:, 0], raw.iloc[header + 1:, col]):
        m = _MONTH.match(str(label).strip())
        if not m or pd.isna(value):
            continue
        period = pd.Period(pd.to_datetime(f"{m.group(1)} 20{m.group(2)}", format="%b %Y"), freq="M")
        rows.append((period, float(value), m.group(3)))
    df = pd.DataFrame(rows, columns=["period", "value", "flag"]).set_index("period").sort_index()
    if df.index.duplicated().any():
        raise ValueError("C30: duplicate months")
    return df


def release_note(content: bytes) -> str | None:
    """The release line in the file, e.g. 'Construction Spending, November 2, 2026'."""
    raw = pd.read_excel(io.BytesIO(content), header=None, dtype=object)
    for x in raw.iloc[:, 0].dropna().astype(str):
        m = re.search(r"Construction Spending, ([A-Z][a-z]+ \d{1,2}, \d{4})", x)
        if m:
            return m.group(1)
    return None


def fetch(kind: str = "sa", column: str = "Data center") -> pd.Series:
    content = http.get(BASE + FILES[kind], SOURCE).content
    return parse(content, column)["value"]
