"""EIA-930 Hourly Electric Grid Monitor: monthly average and peak hourly demand for data-centre-heavy areas.

Public domain (www.eia.gov/about/copyrights_reuse.php). api.eia.gov needs a key, so the six-month bulk CSVs on
www.eia.gov/electricity/gridmonitor/sixMonthFiles/ are used:

- EIA930_BALANCE_<year>_<Jan_Jun|Jul_Dec>.csv (from 2015 Jul_Dec, ~30-40 MB each): hourly data per balancing
  authority. Column "Demand (MW) (Adjusted)" is EIA's cleaned series (gaps and outliers imputed).
- EIA930_SUBREGION_<year>_<half>.csv (from 2018 Jul_Dec, ~25 MB): hourly demand per BA subregion, used for PJM's
  Dominion zone (BA PJM, sub-region DOM). Only "Demand (MW)" exists there (not cleaned).

Months are local calendar months ("Data Date" is the BA's local date). Average = mean of the hourly values,
peak = max hourly value, after removing glitches (drop_glitches: zeros and single-hour spikes). A month is kept only if at least MIN_COVERAGE of its hours have a value and it ended at
least COMPLETE_DAYS before the fetch day.

Size: the full CSVs are not kept. Each file is downloaded once, the rows of the wanted areas are kept as a small
gzip CSV in data/raw/eia930/hourly/ (with the file's Last-Modified), and the monthly aggregates are computed from
those. The files of the current and previous half-year are downloaded again on each fetch (REFRESH_DAYS), because
BAs revise recent hours; older files are taken from the raw copy.

Vintages: EIA rewrites every file daily (Last-Modified = today), so no dated history of revisions exists. The first
load is lag-dated backfill (month end + lag, today's values: revisions leak); later fetches add new months and
revisions with the fetch date (observations.new_rows).
"""

from __future__ import annotations

import gzip
import io
import json
from datetime import date
from functools import lru_cache

import pandas as pd

from ai_tracker import http
from ai_tracker.http import RAW_DIR

SOURCE = "eia930"
BASE = "https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/"
RAW = RAW_DIR / SOURCE / "hourly"
FIRST = {"BALANCE": (2015, 2), "SUBREGION": (2018, 2)}  # (year, half) of the first file
MIN_COVERAGE = 0.95
COMPLETE_DAYS = 2
SPIKE = 0.25  # an hour deviating more than this from the centred 5-hour median is a data glitch
REFRESH_DAYS = 200  # re-download files whose half-year ended less than this many days ago

# area code -> (file kind, BA, sub-region or None, demand column)
AREAS = {
    "pjm": ("BALANCE", "PJM", None, "Demand (MW) (Adjusted)"),
    "pjm_dom": ("SUBREGION", "PJM", "DOM", "Demand (MW)"),
    "erco": ("BALANCE", "ERCO", None, "Demand (MW) (Adjusted)"),
    "soco": ("BALANCE", "SOCO", None, "Demand (MW) (Adjusted)"),
    "azps": ("BALANCE", "AZPS", None, "Demand (MW) (Adjusted)"),
    "srp": ("BALANCE", "SRP", None, "Demand (MW) (Adjusted)"),
}


def file_name(kind: str, year: int, half: int) -> str:
    return f"EIA930_{kind}_{year}_{'Jan_Jun' if half == 1 else 'Jul_Dec'}.csv"


def half_end(year: int, half: int) -> pd.Timestamp:
    return pd.Timestamp(year, 6, 30) if half == 1 else pd.Timestamp(year, 12, 31)


def files(kind: str, today: date) -> list[tuple[int, int]]:
    """(year, half) of every six-month file from the first one to the one containing today."""
    y, h = FIRST[kind]
    out = []
    while pd.Timestamp(y, 1 if h == 1 else 7, 1) <= pd.Timestamp(today):
        out.append((y, h))
        y, h = (y, 2) if h == 1 else (y + 1, 1)
    return out


# ------------------------------------------------------------------ parsers (pure)


def filter_hourly(content: bytes, kind: str) -> pd.DataFrame:
    """Full six-month CSV -> rows of the wanted areas: area, date (local), hour, mw."""
    want = {code: a for code, a in AREAS.items() if a[0] == kind}
    cols = {"Balancing Authority", "Data Date", "Hour Number"} | {a[3] for a in want.values()}
    if kind == "SUBREGION":
        cols.add("Sub-Region")
    df = pd.read_csv(io.BytesIO(content), usecols=lambda c: c in cols, dtype=str, low_memory=False)
    missing = cols - set(df.columns)
    if missing:
        raise ValueError(f"EIA-930 {kind}: missing columns {sorted(missing)}")
    parts = []
    for code, (_, ba, sub, col) in want.items():
        m = df["Balancing Authority"] == ba
        if sub is not None:
            m &= df["Sub-Region"] == sub
        part = df.loc[m, ["Data Date", "Hour Number", col]].rename(
            columns={"Data Date": "date", "Hour Number": "hour", col: "mw"})
        parts.append(part.assign(area=code))
    out = pd.concat(parts, ignore_index=True)
    out["mw"] = pd.to_numeric(out["mw"].str.replace(",", ""), errors="coerce")
    out["date"] = pd.to_datetime(out["date"], format="%m/%d/%Y")
    out["hour"] = pd.to_numeric(out["hour"], errors="coerce").astype("Int64")
    return out[["area", "date", "hour", "mw"]]


def drop_glitches(h: pd.DataFrame) -> pd.DataFrame:
    """Remove hours with demand <= 0 and isolated spikes or dips: more than SPIKE from the median of the 5 hours
    centred on it (per area, in time order). Real load moves smoothly; the files hold single-hour glitches
    (PJM 224 GW on 2020-07-13 h19, DOM 1.5e9 MW on 2021-10-18, zeros for SOCO and AZPS)."""
    h = h.sort_values(["area", "date", "hour"])
    med = h.groupby("area")["mw"].transform(lambda s: s.rolling(5, center=True, min_periods=3).median())
    bad = (h["mw"] <= 0) | ((h["mw"] / med - 1).abs() > SPIKE)
    return h[~bad]


def monthly(hourly: pd.DataFrame, today: date) -> pd.DataFrame:
    """Hourly rows -> monthly (area, period, avg_mw, peak_mw) for complete, well-covered months, after
    drop_glitches."""
    h = hourly.dropna(subset=["mw"]).drop_duplicates(["area", "date", "hour"], keep="last")
    h = drop_glitches(h)
    h = h.assign(period=h["date"].dt.to_period("M"))
    g = h.groupby(["area", "period"])["mw"].agg(avg_mw="mean", peak_mw="max", n="count").reset_index()
    hours = g["period"].map(lambda p: p.days_in_month * 24)
    ended = g["period"].map(lambda p: p.end_time.normalize() + pd.Timedelta(days=COMPLETE_DAYS)) \
        <= pd.Timestamp(today)
    g = g[(g["n"] >= MIN_COVERAGE * hours) & ended]
    return g[["area", "period", "avg_mw", "peak_mw"]].reset_index(drop=True)


# ------------------------------------------------------------------ downloads (filtered raw copies)


def _hourly_file(kind: str, year: int, half: int, today: date) -> pd.DataFrame:
    name = file_name(kind, year, half)
    path = RAW / f"{name}.gz"
    meta = RAW / f"{name}.json"
    fresh = (pd.Timestamp(today) - half_end(year, half)).days < REFRESH_DAYS
    if path.exists() and meta.exists() and not fresh:
        return pd.read_csv(path, parse_dates=["date"], dtype={"area": str})
    r = http.get(BASE + name, SOURCE, save=False, timeout=600)
    df = filter_hourly(r.content, kind)
    RAW.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        df.to_csv(f, index=False, date_format="%Y-%m-%d")
    tmp.replace(path)
    meta.write_text(json.dumps({"url": BASE + name, "last_modified": r.headers.get("Last-Modified"),
                                "fetched": today.isoformat(), "rows": len(df)}))
    return df


@lru_cache(maxsize=1)
def all_monthly(today: date | None = None) -> pd.DataFrame:
    today = today or date.today()
    parts = [_hourly_file(kind, y, h, today) for kind in FIRST for y, h in files(kind, today)]
    return monthly(pd.concat(parts, ignore_index=True), today)


def fetch(area: str, stat: str) -> pd.Series:
    df = all_monthly()
    s = df[df["area"] == area].set_index("period")[stat].sort_index()
    # keep the contiguous run that ends with the newest month (an early month with poor coverage would be a gap)
    idx = s.index
    start = 0
    for i in range(1, len(idx)):
        if (idx[i] - idx[i - 1]).n != 1:
            start = i
    return s.iloc[start:].round(1)
