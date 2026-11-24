"""BEA NIPA flat files (apps.bea.gov/national/Release/TXT/), no API key.

NipaDataQ.txt: "%SeriesCode,Period,Value" for every quarterly NIPA series (values with thousands
separators); SeriesRegister.txt: code, label, metric, scale (-6 = millions), table:line.
Only the latest vintage (all estimates as revised up to the last release) -> backfill. ~35 MB.

Release archive (track M1, below): real vintages of selected NIPA codes from BEA's own data archive, one per GDP
release since 2017-10-27, dated by the release's "Data published" line. See docs/kallor/makro_bea_bls.md.
"""

from __future__ import annotations

import csv
import io
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
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


# ------------------------------------------------------------------ release archive: real vintages
#
# BEA's data archive (apps.bea.gov/histdata, "National Accounts (NIPA)") keeps one directory per GDP release
# since 2002 with every NIPA table as published that day: GDP_and_PI/<year>/<quarter>/<Vintage>_<Month-D-YYYY>/
# Section<N>all_xls.xlsx. The directory list comes from the archive page's own JSON endpoint. Files are xlsx from
# the 2017Q3 advance estimate (2017-10-27); earlier releases are .xls only and are not read (no xls reader in the
# project). known_from = "Data published <date>" in the table header, not the directory name: the two differ for
# 2018Q4 (directory 2019-03-01, published 2019-02-28) and 2025Q3 (directory 2025-12-22, published 2025-12-23).
# The newest release is also read from apps.bea.gov/national/Release/XLSX/Survey/ in case the archive lags.
# Archived releases do not change, so a small extract per release is cached under <RAW_DIR>/bea/vintages/ and
# each 4-6 MB workbook pair is downloaded once.

ARCHIVE_API = "https://apps.bea.gov/histdata/core/data/Fea_DisplayChildrenC/"
ARCHIVE_FILES = "https://apps.bea.gov/HistData/Files/Releases/"
CURRENT_FILES = "https://apps.bea.gov/national/Release/XLSX/Survey/"
NIPA_ARCHIVE_ID = 7  # "National Accounts (NIPA)" in the archive's tree (HistMainId)
FIRST_XLSX = pd.Timestamp("2017-10-27")
MAX_DIR_GAP_DAYS = 10  # published date vs directory date; a larger gap means a wrong or moved file
# NIPA series code -> (section workbook, table prefix of the quarterly sheet(s) that hold it). Codes are BEA's own
# and stable across vintages; line numbers and table names (4.2.5 -> 4.2.5A/B) are not.
ARCHIVE_CODES = {
    "A191RL": (1, "T10502"),  # real GDP, percent change at annual rate (table 1.5.2, line 1)
    "Y034RY": (1, "T10502"),  # contribution to real GDP growth: information processing equipment (line 31)
    "B935RY": (1, "T10502"),  # ... computers and peripheral equipment (line 32)
    "B985RY": (1, "T10502"),  # ... software (line 38)
    "B852RC": (4, "T40205"),  # imports of computers, peripherals and parts, current dollars (4.2.5, 4.2.5A/B)
    "B852RX": (4, "T40206"),  # same, chained dollars (4.2.6, 4.2.6B)
    "B852RZ": (4, "T40202"),  # contribution to percent change in real imports (4.2.2)
}
CACHE_DIR = http.RAW_DIR / SOURCE / "vintages"
_DIR = re.compile(r"GDP_and_PI[\\/](\d{4})[\\/](Q\d)[\\/](?:\d\.\s*)?([A-Za-z]+)_([A-Za-z]+)-(\d{1,2})-(\d{4})$",
                  re.IGNORECASE)


@dataclass(frozen=True)
class Release:
    path: str  # relative to ARCHIVE_FILES, with forward slashes
    dir_date: pd.Timestamp  # date in the directory name (not used as known_from)
    vintage: str  # Advance, Second, Third, Initial, Updated, ...
    quarter: str  # e.g. 2026Q3


def _month_date(month: str, day: str, year: str) -> pd.Timestamp:
    for fmt, m in (("%B", month), ("%b", month[:3])):
        try:
            return pd.Timestamp(datetime.strptime(f"{m} {int(day)} {year}", f"{fmt} %d %Y"))
        except ValueError:
            continue
    raise ValueError(f"BEA: unreadable date {month} {day} {year}")


def parse_archive_dirs(payload) -> list[Release]:
    """Release directories from the archive's JSON (Fea_DisplayChildrenC, getDirs=true), oldest first."""
    row = payload[0] if isinstance(payload, list) else payload
    out = {}
    for full in row.get("FileArray") or []:
        rel = full.split("Releases/", 1)[-1]
        m = _DIR.search(rel)
        if not m or not rel.upper().startswith("GDP_AND_PI"):
            continue
        year, quarter, vintage, month, day, yyyy = m.groups()
        path = rel.replace("\\", "/")
        out[path] = Release(path, _month_date(month, day, yyyy), vintage, f"{year}{quarter.upper()}")
    return sorted(out.values(), key=lambda r: (r.dir_date, r.path))


def parse_published(cell: str) -> pd.Timestamp | None:
    """'Data published October 29, 2026' or 'Data published Oct 27 2017  8:30AM' -> date; None otherwise."""
    m = re.search(r"Data published\s+([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})", str(cell))
    return _month_date(*m.groups()) if m else None


def _number(v) -> float | None:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.replace(",", ""))
        except ValueError:
            return None  # '.....', '---', '(D)': not available
    return None


def parse_workbook(content: bytes, wanted: dict[str, str]) -> tuple[pd.Timestamp | None, dict[str, pd.Series]]:
    """(published date, {code: quarterly Series}) from a NIPA section workbook.

    `wanted`: code -> table prefix (e.g. "T10502"). Every quarterly sheet ("-Q") whose name starts with the prefix
    is read, so split tables (4.2.5A for 1967-1998, 4.2.5B from 1999) are joined; overlapping values must agree.
    The published date is the latest "Data published" among the sheets read (one release: they agree).
    """
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    parts: dict[str, list[pd.Series]] = {c: [] for c in wanted}
    published = []
    try:
        for name in wb.sheetnames:
            if not name.endswith("-Q") or not any(name.startswith(p) for p in set(wanted.values())):
                continue
            periods = None
            for r in wb[name].iter_rows(values_only=True):
                if not r or r[0] is None and (len(r) < 3 or r[2] is None):
                    continue
                if isinstance(r[0], str) and r[0].startswith("Data published"):
                    published.append(parse_published(r[0]))
                elif r[0] == "Line":
                    periods = [None if p is None else str(p).strip() for p in r[3:]]
                elif periods and len(r) > 2 and r[2] in wanted and name.startswith(wanted[r[2]]):
                    vals = {p: x for p, v in zip(periods, r[3:]) if p and (x := _number(v)) is not None}
                    parts[r[2]].append(pd.Series(vals, dtype=float))
    finally:
        wb.close()
    out = {}
    for code, found in parts.items():
        if not found:
            raise ValueError(f"BEA archive: series {code} not in tables {wanted[code]}*")
        s = found[0]
        for p in found[1:]:
            both = s.index.intersection(p.index)
            if len(both) and not np.allclose(s[both], p[both], rtol=0, atol=1e-9):
                raise ValueError(f"BEA archive: {code} differs between sheets of {wanted[code]}")
            s = s.combine_first(p)
        s.index = pd.PeriodIndex(s.index, freq="Q-DEC")
        out[code] = s.sort_index()
    dates = [d for d in published if d is not None]
    return (max(dates) if dates else None), out


def _section_codes() -> dict[int, dict[str, str]]:
    out: dict[int, dict[str, str]] = {}
    for code, (section, prefix) in ARCHIVE_CODES.items():
        out.setdefault(section, {})[code] = prefix
    return out


def read_release(urls: dict[int, str]) -> tuple[pd.Timestamp, dict[str, pd.Series]]:
    """Download the section workbooks of one release -> (published date, {code: Series})."""
    dates, data = [], {}
    for section, wanted in _section_codes().items():
        r = http.get(urls[section], SOURCE, save=False, timeout=300)
        published, series = parse_workbook(r.content, wanted)
        if published is None:
            raise ValueError(f"BEA: no 'Data published' date in {urls[section]}")
        dates.append(published)
        data.update(series)
    return max(dates), data


def _cache_path(rel: Release) -> Path:
    return CACHE_DIR / f"{rel.dir_date:%Y%m%d}_{rel.quarter}_{re.sub(r'[^A-Za-z]', '', rel.vintage)}.csv"


def _read_cache(rel: Release) -> tuple[pd.Timestamp, dict[str, pd.Series]] | None:
    p = _cache_path(rel)
    if not p.exists():
        return None
    df = pd.read_csv(p, dtype={"code": str, "period": str})
    if set(ARCHIVE_CODES) - set(df["code"]):
        return None  # extract from an older code list: download again
    data = {c: pd.Series(g["value"].to_numpy(float), index=pd.PeriodIndex(g["period"], freq="Q-DEC")).sort_index()
            for c, g in df.groupby("code")}
    return pd.Timestamp(df["published"].iloc[0]), data


def _write_cache(rel: Release, published: pd.Timestamp, data: dict[str, pd.Series]) -> None:
    p = _cache_path(rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    df = pd.concat([pd.DataFrame({"code": c, "period": s.index.astype(str), "value": s.to_numpy()})
                    for c, s in data.items()])
    df["published"] = published.date().isoformat()
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    df.to_csv(tmp, index=False)
    os.replace(tmp, p)


def check_release_date(rel: Release, published: pd.Timestamp) -> None:
    if abs((published - rel.dir_date).days) > MAX_DIR_GAP_DAYS:
        raise ValueError(f"BEA archive {rel.path}: published {published.date()} far from directory date")
    if published <= pd.Period(rel.quarter, freq="Q-DEC").end_time:
        raise ValueError(f"BEA archive {rel.path}: published {published.date()} before the quarter ended")


def archive_vintages(since: pd.Timestamp = FIRST_XLSX) -> dict[pd.Timestamp, dict[str, pd.Series]]:
    """Published date -> {code: Series} for every archived release on or after `since`."""
    listing = http.get(ARCHIVE_API, SOURCE, params={"HistMainId": NIPA_ARCHIVE_ID, "getFiles": "false",
                                                    "getDirs": "true"}).json()
    out: dict[pd.Timestamp, dict[str, pd.Series]] = {}
    for rel in parse_archive_dirs(listing):
        if rel.dir_date < since:
            continue
        cached = _read_cache(rel)
        if cached is None:
            urls = {s: f"{ARCHIVE_FILES}{rel.path}/Section{s}all_xls.xlsx" for s in _section_codes()}
            cached = read_release(urls)
            check_release_date(rel, cached[0])
            _write_cache(rel, *cached)
        published, data = cached
        if published in out:
            raise ValueError(f"BEA archive: two releases published {published.date()} ({rel.path})")
        out[published] = data
    if not out:
        raise ValueError("BEA archive: no releases found")
    return out


def current_vintage() -> tuple[pd.Timestamp, dict[str, pd.Series]]:
    return read_release({s: f"{CURRENT_FILES}Section{s}All_xls.xlsx" for s in _section_codes()})


_VINTAGES: dict[pd.Timestamp, dict[str, pd.Series]] | None = None


def all_vintages() -> dict[pd.Timestamp, dict[str, pd.Series]]:
    """Archive plus the current release (memoised per process: several catalog series share one download)."""
    global _VINTAGES
    if _VINTAGES is None:
        vintages = archive_vintages()
        published, data = current_vintage()
        if published < max(vintages):
            raise ValueError(f"BEA current release {published.date()} older than the archive's newest")
        vintages.setdefault(published, data)  # the archive holds it once it is moved there
        _VINTAGES = dict(sorted(vintages.items()))
    return _VINTAGES


def wide_frame(vintages: dict[pd.Timestamp, dict[str, pd.Series]], code: str) -> pd.DataFrame:
    """Quarter x published date, for one code."""
    return pd.DataFrame({d: v[code] for d, v in sorted(vintages.items())}).sort_index()


def archive_rows(codes: str | tuple[str, ...],
                 vintages: dict[pd.Timestamp, dict[str, pd.Series]] | None = None) -> pd.DataFrame:
    """Release-dated rows (period, value, known_from) for one code, or for the sum of several codes taken from
    the same vintage (missing if any part is missing in that vintage)."""
    from ai_tracker import observations  # lazy: observations -> catalog -> series modules import this module

    vintages = vintages if vintages is not None else all_vintages()
    parts = [wide_frame(vintages, c) for c in ((codes,) if isinstance(codes, str) else codes)]
    wide = parts[0]
    for p in parts[1:]:
        wide = wide.add(p, fill_value=None)
    return observations.vintage_rows(wide.round(6))
