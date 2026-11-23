"""Eurostat dissemination API (JSON-stat 2.0): share of enterprises using AI, `isoc_eb_ai`.

https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/isoc_eb_ai?format=JSON&lang=en&...
Enterprises with 10+ persons employed (size_emp=GE10), all activities without financial sector
(nace_r2=C10-S951_X_K), percent of enterprises (unit=PC_ENT). Annual ICT survey; the API gives only the
latest version (no first-release date per value). Observation flags: 'b' = break in time series.
"""

from __future__ import annotations

import itertools

import pandas as pd

from ai_tracker import http

URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/isoc_eb_ai"
SOURCE = "eurostat"
FILTER = {"size_emp": "GE10", "unit": "PC_ENT", "nace_r2": "C10-S951_X_K"}


def parse_jsonstat(doc: dict) -> pd.DataFrame:
    """JSON-stat 2.0 dataset -> long frame with one column per dimension plus value and flag."""
    ids, cats = doc["id"], []
    for d, size in zip(ids, doc["size"]):
        index = doc["dimension"][d]["category"]["index"]
        cats.append(sorted(index, key=index.get) if isinstance(index, dict) else list(index))
        if len(cats[-1]) != size:
            raise ValueError(f"JSON-stat: dimension {d} has {len(cats[-1])} categories, size says {size}")
    values, status = doc.get("value", {}), doc.get("status", {})
    if isinstance(values, list):
        values = {str(i): v for i, v in enumerate(values) if v is not None}
    rows = []
    for flat, combo in enumerate(itertools.product(*cats)):
        v = values.get(str(flat))
        if v is not None:
            rows.append((*combo, float(v), status.get(str(flat), "") if isinstance(status, dict) else ""))
    return pd.DataFrame(rows, columns=[*ids, "value", "flag"])


def series(long: pd.DataFrame, geo: str, indic: str, first_year: int) -> pd.Series:
    """Annual series for one geo/indicator from first_year. A break flag after the first year raises."""
    s = long[(long["geo"] == geo) & (long["indic_is"] == indic)].copy()
    s["year"] = s["time"].astype(int)
    s = s[s["year"] >= first_year].sort_values("year")
    later_breaks = s[(s["year"] > first_year) & s["flag"].str.contains("b")]
    if len(later_breaks):
        raise ValueError(f"Eurostat {geo} {indic}: break flag in {list(later_breaks['year'])}; split the series")
    return pd.Series(s["value"].to_numpy(), index=pd.PeriodIndex(s["year"].astype(str), freq="Y-DEC"), name=geo)


_CACHE: dict[tuple, dict] = {}


def fetch_long(geos: tuple[str, ...], indic: str) -> pd.DataFrame:
    key = (geos, indic)
    if key not in _CACHE:
        params = [("format", "JSON"), ("lang", "en"), ("indic_is", indic)] + [("geo", g) for g in geos] \
            + list(FILTER.items())
        _CACHE[key] = http.get(URL, SOURCE, params=params).json()
    return parse_jsonstat(_CACHE[key])
