"""US Census international trade API: monthly US general imports by HS code and country (needs CENSUS_API_KEY).

Endpoint https://api.census.gov/data/timeseries/intltrade/imports/hs (dataset ITMONTHLYIMPORTSHS, monthly from
2013-01). Variable names are pinned from the keyless metadata (variables.json, read 2026-11-24): GEN_VAL_MO
"15-digit General Imports, Total Value" (US dollars), I_COMMODITY "2-, 4-, 6-, or 10-character Import Harmonized
Code", CTY_CODE / CTY_NAME, time (YYYY-MM, predicate only). Data requests without a key are redirected to
missing_key.html (302), so this module only runs when the key is set; without it the fetch raises
keyed.MissingKey before any request.

Request shape (Guide to International Trade Datasets, census.gov/foreign-trade/reference/guides):
- the response is a JSON array of rows, the first row is the header; predicate variables (time, and any
  predicate that is not in get) are appended as columns; rows are not sorted;
- repeated predicates are alternatives (`I_COMMODITY=8471&I_COMMODITY=8542`), `time=from 2013-01` asks for every
  month from then on;
- with CTY_CODE in get and CTY_CODE predicates (`CTY_CODE=5830&CTY_CODE=2010`) the rows are those countries;
  without CTY_CODE in get the value is the total for all countries (the guide's "TOTAL FOR ALL COUNTRIES",
  CTY_CODE "-"). So one fetch makes two requests: the countries, and the world total;
- 204 No Content = no rows.

The key travels only in the query string of the request. Errors never contain the URL, raw copies are saved under
the URL without the key, and nothing here prints or logs the key.
"""

from __future__ import annotations

import os
import time
from urllib.parse import urlencode

import pandas as pd
import requests

from ai_tracker import http, keyed

BASE = "https://api.census.gov/data/timeseries/intltrade/imports/hs"
SOURCE = "census_hs"
KEY_ENV = "CENSUS_API_KEY"
VALUE = "GEN_VAL_MO"
START = "2013-01"
WORLD = "-"
MIN_INTERVAL = 1.0  # seconds between requests (the API documents no rate; two requests per weekly run)


def params(commodities: tuple[str, ...], countries: tuple[str, ...] = (), start: str = START) -> list[tuple[str, str]]:
    """Query parameters without the key: the HS codes for `countries` (none = the world total), every month from
    `start`."""
    get = f"CTY_CODE,CTY_NAME,I_COMMODITY,{VALUE}" if countries else f"I_COMMODITY,{VALUE}"
    return ([("get", get)] + [("CTY_CODE", c) for c in countries] + [("I_COMMODITY", c) for c in commodities]
            + [("time", f"from {start}")])


def public_url(p: list[tuple[str, str]]) -> str:
    """The request URL without the key (for raw copies and messages)."""
    return f"{BASE}?{urlencode(p)}"


def request(p: list[tuple[str, str]], key: str, timeout: float = 180, retries: int = 3) -> list[list[str]]:
    """GET the endpoint with the key; returns the JSON rows (header first), [] for 204. Never echoes the key."""
    url = public_url(p)
    for attempt in range(retries + 1):
        time.sleep(MIN_INTERVAL)
        try:
            r = requests.get(BASE, params=p + [("key", key)], timeout=timeout, allow_redirects=False,
                             headers={"User-Agent": http.DEFAULT_UA})
        except requests.RequestException as exc:  # the exception text can carry the URL with the key
            if attempt < retries:
                time.sleep(2 ** attempt * 2)
                continue
            raise RuntimeError(f"Census API: {type(exc).__name__} for {url}") from None
        if r.status_code in (429, 500, 502, 503, 504) and attempt < retries:
            time.sleep(2 ** attempt * 2)
            continue
        if r.is_redirect or r.status_code in (301, 302, 303, 307, 308):
            where = r.headers.get("Location", "").rsplit("/", 1)[-1]
            raise RuntimeError(f"Census API refused the key (HTTP {r.status_code} to {where or '?'}); check "
                               f"{KEY_ENV} (activated? see docs/kallor/census_hs.md)")
        if r.status_code == 204:
            return []
        if not r.ok:
            raise RuntimeError(f"Census API: HTTP {r.status_code} for {url}: {_scrub(r.text, key)}")
        try:
            rows = r.json()
        except ValueError:
            raise RuntimeError(f"Census API: not JSON for {url}: {_scrub(r.text, key)}") from None
        save_raw(url, r.content)
        return rows
    raise RuntimeError("unreachable")


def _scrub(text: str, key: str) -> str:
    """The first 200 characters of a response body, with the key blanked should the API echo it."""
    return text.replace(key, "***")[:200] if key else text[:200]


def save_raw(url: str, content: bytes) -> None:
    p = http.raw_path(SOURCE, url, ".json")
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    tmp.write_bytes(content)
    os.replace(tmp, p)


def parse(rows: list[list[str]], countries: set[str] | None = None) -> pd.DataFrame:
    """API rows -> long frame (cty, commodity, period, value in MUSD), sorted.

    Columns are found by name (first occurrence: a predicate in get may be repeated). Without a CTY_CODE column
    the rows are the world total (cty "-"). Rows of other countries are dropped when `countries` is given. A
    (country, code, month) that occurs twice with different values is an error, and so is a value that is not a
    number.
    """
    if not rows:
        return pd.DataFrame(columns=["cty", "commodity", "period", "value"])
    header, body = [str(h) for h in rows[0]], rows[1:]
    need = {"CTY_CODE": "cty", "I_COMMODITY": "commodity", "time": "period", VALUE: "value"}
    missing = [c for c in need if c not in header and c != "CTY_CODE"]
    if missing:
        raise ValueError(f"Census API: columns {missing} missing in header {header}")
    idx = {c: header.index(c) for c in need if c in header}
    df = pd.DataFrame([[r[idx[c]] if c in idx else WORLD for c in need] for r in body], columns=list(need.values()))
    df["cty"] = df["cty"].astype(str).str.strip()
    if countries is not None:
        df = df[df["cty"].isin(countries)]
    df["commodity"] = df["commodity"].astype(str).str.strip()
    df["period"] = pd.PeriodIndex(df["period"].astype(str), freq="M")
    vals = pd.to_numeric(df["value"], errors="coerce")
    if vals.isna().any():
        raise ValueError(f"Census API: {int(vals.isna().sum())} non-numeric {VALUE} values")
    df["value"] = vals.astype(float) / 1e6
    df = df.drop_duplicates()
    dup = df.duplicated(["cty", "commodity", "period"], keep=False)
    if dup.any():
        raise ValueError(f"Census API: {int(dup.sum())} rows with two values for one country, code and month")
    return df.sort_values(["cty", "commodity", "period"]).reset_index(drop=True)


def series(df: pd.DataFrame, cty: str, commodity: str) -> pd.Series:
    """One monthly series (MUSD). A month inside the response's range without a record is 0: the API returns
    records only for trade that happened (to be confirmed on the first keyed fetch, docs/kallor/census_hs.md)."""
    if df.empty:
        raise ValueError("Census API: empty response")
    full = pd.period_range(df["period"].min(), df["period"].max(), freq="M")
    sub = df[(df["cty"] == cty) & (df["commodity"] == commodity)]
    if sub.empty:
        raise ValueError(f"Census API: no rows for country {cty}, HS {commodity}")
    s = pd.Series(sub["value"].to_numpy(), index=pd.PeriodIndex(sub["period"], freq="M"))
    return s.reindex(full, fill_value=0.0)


_CACHE: dict[tuple, pd.DataFrame] = {}  # two requests per process for all series


def fetch(cty: str, commodity: str, commodities: tuple[str, ...], countries: tuple[str, ...]) -> pd.Series:
    """Spec.fetch: skipped (keyed.MissingKey) until CENSUS_API_KEY is set. `cty` "-" is the world total."""
    key = keyed.require(KEY_ENV)
    cache_key = (commodities, countries)
    if cache_key not in _CACHE:
        named = parse(request(params(commodities, countries), key), set(countries))
        world = parse(request(params(commodities), key))
        _CACHE[cache_key] = pd.concat([named, world], ignore_index=True)
    return series(_CACHE[cache_key], cty, commodity)
