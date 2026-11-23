"""PyPI daily downloads from pypistats.org (/api/packages/<p>/overall), track B1: the weekly refresh.

pypistats computes its numbers from the same BigQuery table (bigquery-public-data.pypi.file_downloads) once a
day and keeps 180 days. `with_mirrors` is every download row, the same definition as COUNT(*) in
sources/pypi_bq.py; the overlap check is in docs/kallor/utvecklaradoption.md. The API's etiquette page allows
regular fetches for a set of packages when results are cached and fetched at most once a day: we fetch once a
week and keep every response (http.RAW_DIR/pypistats/<fetch date>/), so the stored history grows past 180 days.
"""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache

import pandas as pd

from ai_tracker import http

BASE = "https://pypistats.org/api/packages"
SOURCE_DIR = "pypistats"
CATEGORY = "with_mirrors"  # = COUNT(*) in BigQuery


def url(project: str) -> str:
    return f"{BASE}/{project}/overall"


def parse(payload: dict, category: str = CATEGORY) -> pd.Series:
    rows = [r for r in payload.get("data", []) if r.get("category") == category]
    s = pd.Series({pd.Timestamp(r["date"]): float(r["downloads"]) for r in rows}, dtype=float)
    return s.sort_index()


def fetch(project: str) -> pd.Series:
    """Today's response (saved under RAW_DIR); daily with_mirrors downloads. At most one call per project and day
    in a process (the API updates once a day)."""
    return _fetch(project, date.today())


@lru_cache(maxsize=64)
def _fetch(project: str, day: date) -> pd.Series:
    return parse(http.get(url(project), source=SOURCE_DIR).json())


def stored(project: str) -> pd.Series:
    """Every stored response for `project`, newest fetch winning per day."""
    p = http.raw_path(SOURCE_DIR, url(project), day=date(2000, 1, 1))
    files = sorted(http.RAW_DIR.joinpath(SOURCE_DIR).glob(f"*/{p.name}"), key=lambda f: f.parent.name)
    parts = []
    for f in files:
        try:
            parts.append(parse(json.loads(f.read_text(encoding="utf-8"))))
        except (ValueError, KeyError):
            continue  # a truncated or error response is skipped, not trusted
    if not parts:
        return pd.Series(dtype=float)
    s = pd.concat(parts)
    return s[~s.index.duplicated(keep="last")].sort_index()
