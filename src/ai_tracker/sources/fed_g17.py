"""Federal Reserve G.17 (industrial production) from the primary source, with real vintages. No API key.

Vintages come from the Board's own release archive: every monthly release since 2016-04-15 and every
annual revision since 2017-03-31 has a directory on www.federalreserve.gov/releases/g17/ with the full
history of all IP series as of that release (`<dir>/ipdisk/ip_sa.txt`). known_from = the directory's date,
which is the release date (all 135 archive dates since 2016-04-15 equal the ALFRED vintage dates of
IPG3344S; see docs/kallor/fed_g17.md). The newest release is read from the Data Download Program (DDP,
Table 5 package, CSV) with the date from the DDP page ("last released <weekday>, <Month D, YYYY>").
The DDP's preformatted packages are retired on 2027-03-31, so when that fails the newest release is read
from /releases/g17/current/ipdisk/ip_sa.txt with the date of current/default.htm.

Archived releases do not change, so a small extract per release (only CODES) is cached under
data/raw/fed_g17/vintages/ and each 2.7 MB file is downloaded once.

Terms (www.federalreserve.gov/disclaimer.htm): "Unless otherwise indicated, information on Board's website
is in the public domain and may be copied and distributed without permission. Please cite to the Board as
the source of the information."
"""

from __future__ import annotations

import csv
import html as htmllib
import io
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from ai_tracker import config, http, observations

BASE = "https://www.federalreserve.gov"
SOURCE = "fed_g17"
CODES = ("G3344", "G3341")  # semiconductor and other electronic component (3344); computer and peripheral (3341)
DDP_PACKAGE = "Table 5: Industrial Production: Special Aggregates and Selected Detail"
CACHE = config.REPO / "data" / "raw" / SOURCE / "vintages"


# ------------------------------------------------------------------ parsers (pure)


def parse_archive(index_html: str) -> dict[pd.Timestamp, str]:
    """Release date -> directory path (relative to /releases/g17/) for every archived release with data.

    Monthly releases are `<YYYYMMDD>/ipdisk/`, annual revisions `Revisions/<YYYYMMDD>/ipdisk/` (any case).
    """
    out = {}
    for path, d in re.findall(r'href="(?:\./)?((?:[Rr]evisions/)?(\d{8}))/ipdisk/', index_html):
        out.setdefault(pd.Timestamp(d), path)
    return dict(sorted(out.items()))


def parse_ip_text(text: str, codes=CODES) -> dict[str, pd.Series]:
    """ip_sa.txt -> {code: monthly Series on month-start Timestamps}.

    Format: a quoted description line per series, then lines `"CODE"  YEAR  v1 ... v12` (fewer values in
    the latest year).
    """
    vals: dict[str, dict[pd.Timestamp, float]] = {c: {} for c in codes}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3 or not parts[0].startswith('"') or ":" in parts[0]:
            continue
        code = parts[0].strip('"')
        if code not in vals or not re.fullmatch(r"\d{4}", parts[1]):
            continue
        year = int(parts[1])
        if len(parts) - 2 > 12:
            raise ValueError(f"G.17 line with more than 12 months: {line[:60]!r}")
        for m, v in enumerate(parts[2:], start=1):
            vals[code][pd.Timestamp(year, m, 1)] = float(v)
    missing = [c for c, v in vals.items() if not v]
    if missing:
        raise ValueError(f"G.17 file lacks series {missing}")
    return {c: pd.Series(v, dtype=float).sort_index() for c, v in vals.items()}


def parse_ddp_page(page_html: str) -> tuple[pd.Timestamp, str]:
    """(last release date, query string of the Table 5 CSV package) from Choose.aspx?rel=G17."""
    m = re.search(r"last released\s+\w+,\s+([A-Z][a-z]+ \d{1,2}, \d{4})", page_html)
    if not m:
        raise ValueError("DDP page: no 'last released' date")
    released = pd.Timestamp(datetime.strptime(m.group(1), "%B %d, %Y"))
    for value, label in re.findall(r'<option value="(rel=G17[^"]*)"[^>]*>([^<]*)</option>', page_html):
        if htmllib.unescape(label).strip().startswith(DDP_PACKAGE):
            return released, htmllib.unescape(value)
    raise ValueError(f"DDP page: no package {DDP_PACKAGE!r}")


def parse_ddp_csv(text: str, codes=CODES) -> dict[str, pd.Series]:
    """DDP CSV (layout=seriesrow) -> {code: monthly Series}. Series id is `IP.<code>.S` (S = seasonally adjusted)."""
    rows = list(csv.reader(io.StringIO(text)))
    header = rows[0]
    if header[:6] != ["Description:", "Unit:", "Multiplier:", "Currency:", "Unique Identifier:", "Series Name:"]:
        raise ValueError(f"unexpected DDP header {header[:6]}")
    months = pd.to_datetime(header[6:], format="%Y-%m")
    out = {}
    for r in rows[1:]:
        code = re.fullmatch(r"IP\.(\w+)\.S", r[5].strip())
        if not code or code.group(1) not in codes:
            continue
        if "Index" not in r[1]:
            raise ValueError(f"unexpected DDP unit {r[1]!r}")
        s = pd.Series(pd.to_numeric(r[6:], errors="coerce"), index=months, dtype=float).dropna()
        out[code.group(1)] = s
    missing = [c for c in codes if c not in out]
    if missing:
        raise ValueError(f"DDP CSV lacks series {missing}")
    return out


def parse_current_date(page_html: str) -> pd.Timestamp:
    """Release date from /releases/g17/current/default.htm (`<div class="dates">Release Date: ...</div>`)."""
    m = re.search(r"Release Date:\s*([A-Z][a-z]+ \d{1,2}, \d{4})", page_html)
    if not m:
        raise ValueError("G.17 current page: no release date")
    return pd.Timestamp(datetime.strptime(m.group(1), "%B %d, %Y"))


def wide_frame(vintages: dict[pd.Timestamp, dict[str, pd.Series]], code: str) -> pd.DataFrame:
    """Observation month x release date, for one code."""
    return pd.DataFrame({d: v[code] for d, v in sorted(vintages.items())}).sort_index()


# ------------------------------------------------------------------ fetching


def _cache_path(released: pd.Timestamp) -> Path:
    return CACHE / f"{released:%Y%m%d}.csv"


def _read_cache(released: pd.Timestamp) -> dict[str, pd.Series] | None:
    p = _cache_path(released)
    if not p.exists():
        return None
    df = pd.read_csv(p, parse_dates=["period"])
    if set(CODES) - set(df["code"]):
        return None
    return {c: g.set_index("period")["value"].sort_index() for c, g in df.groupby("code")}


def _write_cache(released: pd.Timestamp, series: dict[str, pd.Series]) -> None:
    p = _cache_path(released)
    p.parent.mkdir(parents=True, exist_ok=True)
    df = pd.concat([s.rename("value").rename_axis("period").reset_index().assign(code=c) for c, s in series.items()])
    df[["code", "period", "value"]].to_csv(p, index=False)


def archived_vintages() -> dict[pd.Timestamp, dict[str, pd.Series]]:
    index = http.get(f"{BASE}/releases/g17/", SOURCE).text
    out = {}
    for released, path in parse_archive(index).items():
        cached = _read_cache(released)
        if cached is None:
            r = http.get(f"{BASE}/releases/g17/{path}/ipdisk/ip_sa.txt", SOURCE, save=False)
            cached = parse_ip_text(r.text)
            _write_cache(released, cached)
        out[released] = cached
    return out


def current_vintage() -> tuple[pd.Timestamp, dict[str, pd.Series]]:
    """Newest release: DDP CSV, or the current release's text file once the DDP packages are retired."""
    try:
        released, query = parse_ddp_page(http.get(f"{BASE}/datadownload/Choose.aspx?rel=G17", SOURCE).text)
        return released, parse_ddp_csv(http.get(f"{BASE}/datadownload/Output.aspx?{query}", SOURCE).text)
    except Exception as exc:  # noqa: BLE001 - fall back to the release's own data file
        print(f"G.17 DDP unavailable ({type(exc).__name__}: {str(exc)[:80]}); using current/ipdisk")
        released = parse_current_date(http.get(f"{BASE}/releases/g17/current/default.htm", SOURCE).text)
        return released, parse_ip_text(http.get(f"{BASE}/releases/g17/current/ipdisk/ip_sa.txt", SOURCE).text)


def all_vintages() -> dict[pd.Timestamp, dict[str, pd.Series]]:
    vintages = archived_vintages()
    released, data = current_vintage()
    if released < max(vintages):
        raise ValueError(f"G.17 current release {released.date()} older than the archive's newest")
    vintages.setdefault(released, data)  # the archive already holds it once it is moved there
    return vintages


def release_rows(code: str, vintages: dict[pd.Timestamp, dict[str, pd.Series]] | None = None) -> pd.DataFrame:
    """Columns period, value, known_from: one row per (month, release) where the value is new or changed."""
    return observations.vintage_rows(wide_frame(vintages or all_vintages(), code))
