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
- 204 No Content = no rows;
- `time=from 2022-03 to 2022-07` asks for a range; the guide warns that the time predicate times out more often
  on large requests. If the full request times out or the API stays busy, fetch splits it into one request per
  year (same shape, so the same parser).

The key travels only in the query string of the request. Errors never contain the URL, raw copies are saved under
the URL without the key, and nothing here prints or logs the key.

One process asks the API at most once per response: a failed request is cached as well (review R13-3), so the 35
series of a weekly run share one failure instead of retrying it 35 times.

`python -m ai_tracker.sources.census_hs check` runs the first-keyed-fetch checklist of docs/kallor/census_hs.md
without writing to the table.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import date
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
TIMEOUT = (10, 120)  # connect, read (s); a read timeout counts as transient and leads to the per-year split
RETRIES = 2  # extra attempts for a timeout, a connection error, 429 or 5xx


class Transient(RuntimeError):
    """The API timed out or stayed busy after the retries: worth one try with smaller requests."""


def params(commodities: tuple[str, ...], countries: tuple[str, ...] = (), start: str = START,
           end: str | None = None) -> list[tuple[str, str]]:
    """Query parameters without the key: the HS codes for `countries` (none = the world total), every month from
    `start` (to `end`, inclusive, if given)."""
    get = f"CTY_CODE,CTY_NAME,I_COMMODITY,{VALUE}" if countries else f"I_COMMODITY,{VALUE}"
    when = f"from {start} to {end}" if end else f"from {start}"
    return ([("get", get)] + [("CTY_CODE", c) for c in countries] + [("I_COMMODITY", c) for c in commodities]
            + [("time", when)])


def public_url(p: list[tuple[str, str]]) -> str:
    """The request URL without the key (for raw copies and messages)."""
    return f"{BASE}?{urlencode(p)}"


def request(p: list[tuple[str, str]], key: str, timeout=TIMEOUT, retries: int = RETRIES) -> list[list[str]]:
    """GET the endpoint with the key; returns the JSON rows (header first), [] for 204. Never echoes the key.

    Raises Transient after the retries for a timeout, a connection error, 429 or 5xx, RuntimeError otherwise. The
    errors are raised outside any except block, so no exception that carries the URL with the key is chained to
    them (neither __cause__ nor __context__)."""
    url = public_url(p)
    for attempt in range(retries + 1):
        time.sleep(MIN_INTERVAL)
        failure = None
        try:
            r = requests.get(BASE, params=p + [("key", key)], timeout=timeout, allow_redirects=False,
                             headers={"User-Agent": http.DEFAULT_UA})
        except requests.RequestException as exc:  # the exception text can carry the URL with the key
            failure = type(exc).__name__
        if failure is not None:
            if attempt < retries:
                time.sleep(2 ** attempt * 2)
                continue
            raise Transient(f"Census API: {failure} for {url}")
        if r.status_code in (429, 500, 502, 503, 504):
            if attempt < retries:
                time.sleep(2 ** attempt * 2)
                continue
            raise Transient(f"Census API: HTTP {r.status_code} for {url}: {_scrub(r.text, key)}")
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
            rows = None
        if rows is None:
            raise RuntimeError(f"Census API: not JSON for {url}: {_scrub(r.text, key)}")
        save_raw(url, r.content)
        return rows
    raise RuntimeError("unreachable")


def rows_from(commodities: tuple[str, ...], countries: tuple[str, ...], key: str, start: str = START,
              today: date | None = None) -> list[list[str]]:
    """Every row from `start`: one request, or, if that one is Transient, one request per year (the guide: the time
    predicate times out more often, smaller requests do not). The yearly parts must share the header."""
    try:
        return request(params(commodities, countries, start), key)
    except Transient as exc:
        reason = str(exc).split(" for ")[0]
    first, last = int(start[:4]), (today or date.today()).year
    print(f"{SOURCE}: {reason}; asking one year at a time ({first}-{last})")
    out: list[list[str]] = []
    for year in range(first, last + 1):
        part = request(params(commodities, countries, start if year == first else f"{year}-01",
                              None if year == last else f"{year}-12"), key)
        if not part:
            continue
        if out and [str(h) for h in part[0]] != [str(h) for h in out[0]]:
            raise ValueError(f"Census API: header of {year} {part[0]} differs from {out[0]}")
        out = out + part[1:] if out else [list(part[0]), *part[1:]]
    return out


def _scrub(text: str, key: str, n: int = 200) -> str:
    """The first `n` characters of a response body or message, with the key blanked should it occur."""
    return text.replace(key, "***")[:n] if key else text[:n]


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
    """One monthly series (MUSD) from its own records. A month between the series' first and last record without a
    record is 0: the API returns records only for trade that happened (Census guide: 204 = no trade). Months before
    the first or after the last record are not filled, so a month that only the other response (countries or world)
    has, or that is not released yet, is never a false zero (register amendment 2026-11-24, review R13-1)."""
    if df.empty:
        raise ValueError("Census API: empty response")
    sub = df[(df["cty"] == cty) & (df["commodity"] == commodity)]
    if sub.empty:
        raise ValueError(f"Census API: no rows for country {cty}, HS {commodity}")
    s = pd.Series(sub["value"].to_numpy(), index=pd.PeriodIndex(sub["period"], freq="M"))
    return s.reindex(pd.period_range(s.index.min(), s.index.max(), freq="M"), fill_value=0.0)


# two requests per process for all series; a failure is kept as its message, so it is not repeated per series
_CACHE: dict[tuple, pd.DataFrame | str] = {}


def responses(commodities: tuple[str, ...], countries: tuple[str, ...], key: str) -> pd.DataFrame:
    """Both responses (the named countries, then the world total) as one long frame, cached per process."""
    cache_key = (commodities, countries)
    if cache_key not in _CACHE:
        try:
            named = parse(rows_from(commodities, countries, key), set(countries))
            world = parse(rows_from(commodities, (), key))
            _CACHE[cache_key] = pd.concat([named, world], ignore_index=True)
        except Exception as exc:  # noqa: BLE001 - kept for the other series; request and parse never name the key
            _CACHE[cache_key] = _scrub(f"{type(exc).__name__}: {exc}", key, 400)
    hit = _CACHE[cache_key]
    if isinstance(hit, str):
        raise RuntimeError(f"{hit} (cached: this run asks the API once)")
    return hit


def fetch(cty: str, commodity: str, commodities: tuple[str, ...], countries: tuple[str, ...]) -> pd.Series:
    """Spec.fetch: skipped (keyed.MissingKey) until CENSUS_API_KEY is set. `cty` "-" is the world total."""
    key = keyed.require(KEY_ENV)
    return series(responses(commodities, countries, key), cty, commodity)


# ------------------------------------------------------------------ first keyed fetch: the checklist


def check(commodities: tuple[str, ...], countries: dict[str, str], table: pd.DataFrame | None = None) -> list[str]:
    """The checklist of docs/kallor/census_hs.md, "Kontrollera vid första hämtningen med nyckel", as report lines.
    Fetches like the weekly run (needs the key) but writes nothing to the observation table. `countries` maps the
    key suffix to CTY_CODE ("-" = world); `table` (default: observations.load()) gives the annual end-use series."""
    from ai_tracker import observations

    key = keyed.require(KEY_ENV)
    named = tuple(c for c in countries.values() if c != WORLD)
    df = responses(commodities, named, key)
    lines = [f"rows {len(df)}, months {df['period'].min()} .. {df['period'].max()}"]
    for geo, cty in countries.items():
        for code in commodities:
            sub = df[(df["cty"] == cty) & (df["commodity"] == code)]
            if sub.empty:
                lines.append(f"{code} {geo}: NO ROWS")
                continue
            s = series(df, cty, code)
            lines.append(f"{code} {geo}: {s.index.min()} .. {s.index.max()}, {len(sub)} records, "
                         f"{len(s) - len(sub)} months without a record (0)")
    table = observations.load() if table is None else table
    for geo, cty in countries.items():
        hs = df[(df["cty"] == cty) & df["commodity"].isin(["8471", "847330"]) & (df["period"].dt.year == 2025)]
        eu = table[table["series"].isin([f"us_imp_eu21300_{geo}_a", f"us_imp_eu21301_{geo}_a"])
                   & (table["period"].astype(str) == "2025")]
        eu_sum = eu.sort_values("known_from").groupby("series")["value"].last().sum() if len(eu) else None
        ratio = f"{hs['value'].sum() / eu_sum:.3f}" if eu_sum else "n/a"
        eu_txt = f"{eu_sum:,.1f} MUSD" if eu_sum is not None else "n/a (no annual rows)"
        lines.append(f"2025 {geo}: HS 8471 + 8473.30 = {hs['value'].sum():,.1f} MUSD, end-use 21300 + 21301 = "
                     f"{eu_txt}, ratio {ratio}")
    last = df["period"].max()
    try:
        upd = request([("get", "I_COMMODITY,GEN_VAL_MO,LAST_UPDATE"), ("I_COMMODITY", commodities[-1]),
                       ("time", f"from {last}")], key)
        seen = sorted({str(r[upd[0].index("LAST_UPDATE")]) for r in upd[1:]}) if upd else []
    except (RuntimeError, ValueError, IndexError) as exc:
        seen = [f"not read ({exc})"]
    lines.append(f"LAST_UPDATE for {last}: {seen or '?'} (compare with the FT-900 release day)")
    return lines


if __name__ == "__main__":
    if sys.argv[1:] != ["check"]:
        sys.exit("usage: python -m ai_tracker.sources.census_hs check")
    from ai_tracker.series import census_hs as hs_series

    geos = {geo: cty for geo, (cty, _) in hs_series.GEOS.items()}
    try:
        for line in check(hs_series.COMMODITIES, geos):
            print(line)
    except (keyed.MissingKey, RuntimeError, ValueError) as exc:
        sys.exit(f"check failed: {exc}")
