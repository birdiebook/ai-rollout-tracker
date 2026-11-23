"""EIA Electric Power Monthly (EPM): retail electricity sales by state and sector, with real vintages.

Public domain (www.eia.gov/about/copyrights_reuse.php). api.eia.gov needs a key and is refused by the
proxy, so everything comes from files on www.eia.gov:

- Back issues (www.eia.gov/electricity/monthly/backissues.php): one zip per monthly issue, 2011-2026.
  Table 5.4.A in each issue holds the issue's data month and the same month a year earlier, for every
  state and sector. Each issue is a vintage. Issues from 2013 on have xlsx tables; the 2011-2012 issues
  only have .xls (needs xlrd) and are skipped.
- The current issue's table: electricity/monthly/xls/table_5_04_a.xlsx.
- Form EIA-861M sales_revenue.xlsx: every month from 2010-01, latest values (final after the annual
  EIA-861). Each downloaded version (by Last-Modified) is a vintage; it also gives the backfill.

known_from of a file = its HTTP Last-Modified date (UTC, floored to the day) + 2 days. Evidence: the
current table_5_04_a.xlsx has Last-Modified 2026-10-22 12:24 GMT while the EPM page gives release date
2026-10-23, so files can be staged a day before release; +2 days keeps a day of margin. A late re-upload
only makes known_from later (conservative).

Values are GWh (thousand MWh = million kWh), rounded to whole GWh as published in EPM, so the rounded
EPM tables and the unrounded EIA-861M file do not produce spurious revisions.

Raw files are kept under data/raw/eia_epm/ (archive tables are immutable and downloaded once).
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from datetime import timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache
from pathlib import Path

import pandas as pd

from ai_tracker import http
from ai_tracker.http import RAW_DIR

SOURCE = "eia_epm"
BASE = "https://www.eia.gov/electricity/monthly/"
BACKISSUES_URL = BASE + "backissues.php"
CURRENT_URL = BASE + "xls/table_5_04_a.xlsx"
EIA861M_URL = "https://www.eia.gov/electricity/data/eia861m/xls/sales_revenue.xlsx"
RAW = RAW_DIR / SOURCE
KNOWN_FROM_MARGIN = pd.Timedelta(days=2)
BACKFILL_LAG_DAYS = 90  # conservative: on-time EPM issues show 50-63 days from month end to known_from

STATES = {"VA": "Virginia", "TX": "Texas", "GA": "Georgia", "AZ": "Arizona", "OR": "Oregon", "OH": "Ohio"}
US = "US"
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], start=1)}


# ------------------------------------------------------------------ parsers (pure)


def known_from(last_modified: str) -> pd.Timestamp:
    """HTTP Last-Modified -> conservative known_from (naive UTC midnight)."""
    t = parsedate_to_datetime(last_modified).astimezone(timezone.utc).replace(tzinfo=None)
    return pd.Timestamp(t).normalize() + KNOWN_FROM_MARGIN


def archive_names(html: str) -> list[str]:
    """Issue zip names ('september2026') linked from backissues.php, ignoring commented-out entries."""
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    return sorted(set(re.findall(r'href="\./archive/([a-z]+\d{4})\.zip"', html)))


def parse_table_5_4_a(content: bytes) -> pd.DataFrame:
    """EPM Table 5.4.A (xlsx) -> rows (area, period, value): commercial sales, GWh, both months shown.

    area is a state code from STATES or "US".
    """
    raw = pd.read_excel(io.BytesIO(content), header=None)
    title = " ".join(str(x) for x in raw.iloc[:3, 0].dropna())
    m = re.search(r"by State,\s*([A-Za-z]+)\s+(\d{4})\s+and\s+(\d{4})", title)
    if not m or m.group(1).lower() not in MONTHS:
        raise ValueError(f"Table 5.4.A title not recognised: {title[:120]!r}")
    if not re.search(r"(?i)thousand megawatthours|million kilowatthours", title):
        raise ValueError(f"unexpected unit in {title[:120]!r}")
    month = MONTHS[m.group(1).lower()]
    current, previous = pd.Period(f"{m.group(2)}-{month:02d}", "M"), pd.Period(f"{m.group(3)}-{month:02d}", "M")
    if previous != current - 12:
        raise ValueError(f"expected current and year-ago month, got {current} and {previous}")
    header = next(i for i in range(len(raw)) if (raw.iloc[i].astype(str).str.strip() == "Commercial").any())
    col = int((raw.iloc[header].astype(str).str.strip() == "Commercial").to_numpy().nonzero()[0][0])
    names = raw.iloc[:, 0].astype(str).str.strip()
    wanted = {**{v: k for k, v in STATES.items()}, "U.S. Total": US}
    rows = []
    for name, area in wanted.items():
        hit = raw[names == name]
        if len(hit) != 1:
            raise ValueError(f"Table 5.4.A: {name!r} found {len(hit)} times")
        for period, c in ((current, col), (previous, col + 1)):
            v = pd.to_numeric(hit.iloc[0, c], errors="coerce")
            if pd.notna(v):
                rows.append((area, period, float(v)))
    return pd.DataFrame(rows, columns=["area", "period", "value"])


def parse_861m(content: bytes) -> pd.DataFrame:
    """EIA-861M sales_revenue.xlsx, sheet Monthly-States -> rows (area, period, value), commercial GWh.

    "US" = sum over the 50 states and DC (the sheet has no US row; matches EPM's U.S. Total).
    """
    raw = pd.read_excel(io.BytesIO(content), sheet_name="Monthly-States", header=None)
    top = raw.iloc[0].astype(str).str.strip().str.upper().tolist()
    if "COMMERCIAL" not in top:
        raise ValueError("EIA-861M layout not recognised (no COMMERCIAL block)")
    col = top.index("COMMERCIAL") + 1  # block: Revenue, Sales, Customers, Price
    if str(raw.iloc[1, col]).strip() != "Sales" or str(raw.iloc[2, col]).strip() != "Megawatthours":
        raise ValueError("EIA-861M layout not recognised (commercial sales column)")
    body = raw.iloc[3:, [0, 1, 2, col]].copy()
    body.columns = ["year", "month", "state", "mwh"]
    body = body[pd.to_numeric(body["year"], errors="coerce").notna()]
    body["period"] = [pd.Period(f"{int(y)}-{int(m):02d}", "M") for y, m in zip(body["year"], body["month"])]
    body["value"] = pd.to_numeric(body["mwh"], errors="coerce") / 1000.0
    states = body[body["state"].isin(STATES)].assign(area=lambda d: d["state"])
    us = body.groupby("period", as_index=False)["value"].sum().assign(area=US)
    n = body.groupby("period")["state"].nunique()
    us = us[us["period"].map(n) == 51]  # only complete months
    return pd.concat([states[["area", "period", "value"]], us[["area", "period", "value"]]], ignore_index=True)


def vintage_rows(tables: list[tuple[pd.Timestamp, pd.DataFrame]], full: pd.DataFrame | None,
                 backfill_lag_days: int = BACKFILL_LAG_DAYS) -> pd.DataFrame:
    """Rows (area, period, value, known_from, source) from dated documents.

    tables: dated documents (Table 5.4.A issues and EIA-861M versions), each a frame (area, period, value).
    Periods from the first data month of the earliest Table 5.4.A issue on get the full vintage chain: a
    row whenever the rounded value first appears or changes. Older periods have no dated vintage and get
    one backfill row from `full` (latest EIA-861M) at period end + lag: final values, so revisions leak.
    """
    tables = sorted(tables, key=lambda x: x[0])
    epm = [t for t in tables if t[1].attrs.get("kind") == "5.4.A"]
    cutoff = min(t[1]["period"].max() for t in epm) if epm else None
    rows = []
    latest: dict[tuple[str, pd.Period], float] = {}
    for kf, df in tables:
        for area, period, value in df[["area", "period", "value"]].itertuples(index=False):
            if cutoff is None or period < cutoff:
                continue
            v = float(round(value))
            if latest.get((area, period)) != v:
                latest[(area, period)] = v
                rows.append((area, period, v, kf, "release"))
    if full is not None:
        old = full if cutoff is None else full[full["period"] < cutoff]
        for area, period, value in old[["area", "period", "value"]].itertuples(index=False):
            kf = period.end_time.normalize() + pd.Timedelta(days=backfill_lag_days)
            rows.append((area, period, float(round(value)), kf, "backfill"))
    out = pd.DataFrame(rows, columns=["area", "period", "value", "known_from", "source"])
    return out.sort_values(["area", "period", "known_from"]).reset_index(drop=True)


# ------------------------------------------------------------------ downloads (cached raw files)


def _archive_table(name: str) -> tuple[pd.Timestamp, bytes] | None:
    """Table 5.4.A of one back issue, downloaded once. None if the issue has no xlsx version."""
    folder = RAW / "archive" / name
    meta_path = folder / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("skipped"):
            return None
        return known_from(meta["last_modified"]), (folder / "Table_5_04_A.xlsx").read_bytes()
    r = http.get(f"{BASE}archive/{name}.zip", SOURCE, save=False, timeout=120)
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    member = next((n for n in zf.namelist() if n.lower().endswith("table_5_04_a.xlsx")), None)
    folder.mkdir(parents=True, exist_ok=True)
    meta = {"url": r.url, "last_modified": r.headers["Last-Modified"]}
    if member is None:
        meta["skipped"] = "no Table_5_04_A.xlsx (older issues are .xls only)"
        meta_path.write_text(json.dumps(meta))
        return None
    content = zf.read(member)
    (folder / "Table_5_04_A.xlsx").write_bytes(content)
    meta_path.write_text(json.dumps(meta))
    return known_from(meta["last_modified"]), content


def _versioned(url: str, sub: str) -> list[tuple[pd.Timestamp, bytes]]:
    """Download the current file, keep one raw copy per Last-Modified, return all stored versions."""
    folder = RAW / sub
    folder.mkdir(parents=True, exist_ok=True)
    r = http.get(url, SOURCE, save=False, timeout=120)
    lm = r.headers["Last-Modified"]
    stamp = parsedate_to_datetime(lm).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = folder / f"{stamp}{Path(url).suffix}"
    if not target.exists():
        target.write_bytes(r.content)
        target.with_suffix(".json").write_text(json.dumps({"url": url, "last_modified": lm}))
    out = []
    for meta_path in sorted(folder.glob("*.json")):
        meta = json.loads(meta_path.read_text())
        out.append((known_from(meta["last_modified"]), meta_path.with_suffix(Path(url).suffix).read_bytes()))
    return out


def _tagged(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    df.attrs["kind"] = kind
    return df


@lru_cache(maxsize=1)
def all_rows() -> pd.DataFrame:
    """Every vintage row for every area (cached per process: one download for all specs)."""
    names = archive_names(http.get(BACKISSUES_URL, SOURCE).text)
    tables = []
    for name in names:
        if int(name[-4:]) < 2013:  # .xls only
            continue
        got = _archive_table(name)
        if got:
            tables.append((got[0], _tagged(parse_table_5_4_a(got[1]), "5.4.A")))
    tables += [(kf, _tagged(parse_table_5_4_a(c), "5.4.A")) for kf, c in _versioned(CURRENT_URL, "current")]
    full_versions = [(kf, _tagged(parse_861m(c), "861M")) for kf, c in _versioned(EIA861M_URL, "eia861m")]
    tables += full_versions
    return vintage_rows(tables, max(full_versions, key=lambda x: x[0])[1])


def fetch(area: str) -> pd.DataFrame:
    rows = all_rows()
    return rows[rows["area"] == area][["period", "value", "known_from", "source"]].reset_index(drop=True)
