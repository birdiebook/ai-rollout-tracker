"""ALFRED (St. Louis Fed archival FRED): real vintages without an API key.

Used only where the primary source is unreachable (Census M3: api.census.gov needs a key, pending) and,
as evidence, for historical release dates of primary sources (first vintage that contains a period).
Not used for Fed G.17 any more: that comes from federalreserve.gov (sources/fed_g17.py).

- vintage_dates(): the list on alfred.stlouisfed.org/series/downloaddata?seid=<id> ("Select Vintage
  Dates When Data Were Revised").
- vintages(): alfredgraph.csv with the id repeated once per vintage date; ALFRED returns at most
  MAX_PER_REQUEST vintage columns per call, so requests are chunked.
- release_rows(): one row per (period, vintage) where the value is new or changed -> release-dated rows.

Terms: FRED/ALFRED legal page (quoted in docs/datakallor/g3_g4_g5.md): "These series may be under copyright
or in the public domain and may be used without permission, provided you do not engage in any prohibited
use. When using, please cite the data source and acknowledge that you obtained the data from FRED".
"""

from __future__ import annotations

import io
import re

import pandas as pd

from ai_tracker import http, observations

BASE = "https://alfred.stlouisfed.org"
MAX_PER_REQUEST = 12  # observed: more vintage dates in one call are silently dropped
SOURCE = "alfred"


def parse_vintage_dates(html: str) -> list[str]:
    """Vintage dates (YYYY-MM-DD) from the download page's option list, sorted."""
    return sorted(set(re.findall(r'<option value="((?:19|20)\d{2}-\d{2}-\d{2})"', html)))


def vintage_dates(series_id: str) -> list[str]:
    r = http.get(f"{BASE}/series/downloaddata", SOURCE, params={"seid": series_id})
    return parse_vintage_dates(r.text)


def parse_vintage_csv(text: str, series_id: str) -> pd.DataFrame:
    """alfredgraph.csv -> wide frame: index observation date, one column per vintage date."""
    df = pd.read_csv(io.StringIO(text), na_values=[".", ""])
    df = df.set_index(df.columns[0])
    df.index = pd.to_datetime(df.index)
    cols = {}
    for c in df.columns:
        m = re.fullmatch(rf"{re.escape(series_id)}_(\d{{8}})", c)
        if not m:
            raise ValueError(f"unexpected ALFRED column {c!r}")
        cols[c] = pd.Timestamp(m.group(1))
    return df.rename(columns=cols).astype(float)


def vintages(series_id: str, dates: list[str]) -> pd.DataFrame:
    parts = []
    for i in range(0, len(dates), MAX_PER_REQUEST):
        chunk = dates[i:i + MAX_PER_REQUEST]
        r = http.get(f"{BASE}/graph/alfredgraph.csv", SOURCE,
                     params={"id": ",".join([series_id] * len(chunk)), "vintage_date": ",".join(chunk)})
        wide = parse_vintage_csv(r.text, series_id)
        missing = set(pd.to_datetime(chunk)) - set(wide.columns)
        if missing:
            raise ValueError(f"ALFRED returned fewer vintages than asked for {series_id}: {sorted(missing)[:3]}")
        parts.append(wide)
    return pd.concat(parts, axis=1).sort_index(axis=1)


def published(wide: pd.DataFrame) -> pd.DataFrame:
    """`wide` with ALFRED's 0.0 placeholders set to missing.

    ALFRED sometimes carries a not-yet-published month as exactly 0.0 (IMP5830, vintage 2025-12-11: October
    2025 = 0.0; the real value arrived 2026-01-08, R1 review section 3.2). Every series read here is a level
    (dollars, index points), where an exact zero is never a real observation, so a zero is not a release.
    """
    return wide.mask(wide == 0)


def release_rows(wide: pd.DataFrame) -> pd.DataFrame:
    """Columns period (observation date), value, known_from: a row whenever a vintage adds or changes a value.
    0.0 placeholders are not values (see `published`)."""
    return observations.vintage_rows(published(wide))


def first_release(wide: pd.DataFrame) -> pd.Series:
    """First vintage date in which each observation date has a value (= its first publication).
    0.0 placeholders do not count (see `published`)."""
    has = published(wide).notna()
    first = has.idxmax(axis=1)
    return first[has.any(axis=1)]


def fetch_release_rows(series_id: str) -> pd.DataFrame:
    return release_rows(vintages(series_id, vintage_dates(series_id)))
