"""PJM Interconnection: capacity auctions (RPM Base Residual Auction) and the annual long-term load forecast.

Everything comes from files on www.pjm.com (no account; Data Miner 2 is not used). Licence: no open licence.
The site's legal page could not be read (it redirects to /not-found) and the Data Miner 2 terms forbid
non-members to republish data, so the series are stored for analysis but not published (docs/kallor/el_datacenter.md).

Capacity auctions (www.pjm.com/markets-and-operations/rpm)
- Prices: rpm-auctions-resource-clearing-price-summary.xlsx, one table of Resource Clearing Prices ($/MW-day) for
  every RPM auction since DY 2007/08, by LDA. Only the BRA rows are used. Where a BRA cleared several products the
  value is the one PJM itself uses in its RTO history tables: Annual (DY 2014/15-2017/18), Capacity Performance
  (2018/19-2019/20); a single product before and after.
- Cleared MW: <DY>-bra-results.xlsx / <DY>-base-residual-auction-results.xlsx, sheet "BRA Resource Clearing Results",
  RTO "Total Annual Equivalent Resources Cleared" (from DY 2020/21, when 100 % CP made the quantity comparable;
  earlier years are .xls or a different definition).
- Period = the delivery year by its start year (2025 = DY 2025/26, June 2025 - May 2026), freq "A".
- known_from = the date the BRA results were posted (BRA_POSTED, each with its evidence). The summary file is
  rewritten after every auction (Last-Modified 2026-07-29), so its date says nothing about older auctions. For a
  delivery year missing from BRA_POSTED (a new auction) known_from = Last-Modified of that DY's results file (or of
  the summary when there is none) + 1 day.

Load forecast (www.pjm.com/library/reports-notices, "Load Forecast")
- <year>-load-report-data.xlsx (2017-2018: <year>-load-forecast-report-data.xlsx): monthly 50/50 peak (MW) and
  net energy (GWh) per zone for 15 (from 2026: 20) years. Summer peak = max of June-August (equals Table B-1),
  annual energy = sum of the months (equals Table E-1); checked for the 2026 report.
- <year>-load-report-tables.xlsx (2025 on): Table B-9 "Adjustments Above Embedded to Summer Peak Load", the large
  load adjustments (mostly data centres). Older reports have it only in the PDF.
- Design: one series per (quantity, area, horizon h); period = the report's vintage year V, value = the forecast
  for target year V + h. A new report is a new period, so the series shows how the h-year-ahead view moved.
- known_from of a report = its posting date (LF_POSTED); a report missing there = Last-Modified + 1 day. Tables
  files: Last-Modified + 1 day (the 2026 tables were corrected on 2026-02-06 and only that version is online).
"""

from __future__ import annotations

import io
import re
import zipfile
from datetime import timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache

import pandas as pd

from ai_tracker import http

SOURCE = "pjm"
BASE = "https://www.pjm.com"
RPM_PAGE = BASE + "/markets-and-operations/rpm"
LIBRARY_PAGE = BASE + "/library/reports-notices"  # links the report data files
LOAD_DEV_PAGE = BASE + "/planning/resource-adequacy-planning/load-forecast-dev-process"  # links the tables files
RPM_INFO = "/-/media/DotCom/markets-ops/rpm/rpm-auction-info/"
SUMMARY_URL = BASE + RPM_INFO + "rpm-auctions-resource-clearing-price-summary.xlsx"
MARGIN = pd.Timedelta(days=1)

# BRA results posting date per delivery year (start year), with evidence. Where the report gives no date, the
# earliest dated PJM document found that states the values is used (later than the real posting: conservative).
BRA_POSTED: dict[int, tuple[str, str]] = {
    **{y: ("2011-05-13", "not found separately; stated in the 2014/15 BRA report (posted May 13, 2011), Table 1")
       for y in range(2007, 2014)},
    2014: ("2011-05-13", "2014/15 BRA report: 'the results were posted on May 13, 2011'"),
    **{y: ("2016-05-24", "not found separately; stated in the 2019/20 BRA report (posted May 24, 2016), Table 1")
       for y in range(2015, 2019)},
    2019: ("2016-05-24", "2019/20 BRA report: 'the results were posted on May 24, 2016'"),
    2020: ("2017-05-23", "2020/21 BRA report: 'the results were posted on May 23, 2017'"),
    2021: ("2018-05-23", "2021/22 BRA report: 'the results were posted on May 23, 2018'"),
    2022: ("2021-06-02", "2022/23 BRA report: 'the results were posted on June 2, 2021'"),
    2023: ("2022-06-21", "2023/24 BRA report: 'the results were posted on June 21, 2022'"),
    2024: ("2023-02-27", "PJM news release 20230227 'PJM Capacity Auction Procures Adequate Resources' (S&P Global, "
                         "same day); the report online is a 2024 revision without date"),
    2025: ("2024-07-30", "2025/26 BRA report cover: 'July 30, 2024'"),
    2026: ("2025-07-22", "2026/27 BRA report cover: 'July 22, 2025'"),
    2027: ("2025-12-17", "2027/28 BRA report cover: 'December 17, 2025'"),
    2028: ("2026-07-14", "2028/29 BRA report cover: 'July 14, 2026'"),
}

# Load forecast report posting date per vintage, with evidence. "January YYYY" on the cover without a day -> the
# last day of January (later than the real posting: conservative).
LF_POSTED: dict[int, tuple[str, str]] = {
    **{y: (f"{y}-01-31", f"cover 'January {y}' without day; data file saved before end of January")
       for y in range(2017, 2024)},
    2024: ("2024-02-01", "cover 'Revised 2/1/2024'; the data file online was saved 2024-01-31, i.e. the revision"),
    2025: ("2025-01-24", "cover 'Posted Date: January 24, 2025'"),
    2026: ("2026-01-14", "cover 'Posted Date: January 14, 2026'"),
}

# Series keys -> (area code in the PJM file, label)
PRICE_AREAS = {"rto": "RTO", "dom": "DOM"}
LF_AREAS = {"rto": ("PJM_RTO", "PJM RTO"), "dom": ("DOM", "DOM")}
ADJ_AREAS = {"rto": "PJM RTO", "dom": "DOM"}
HORIZONS = (1, 5, 10)
CLEARED_FROM = 2020  # DY 2020/21: first 100 % Capacity Performance BRA


# ------------------------------------------------------------------ helpers (pure)


def lm_known_from(last_modified: str) -> pd.Timestamp:
    """HTTP Last-Modified -> known_from: UTC day + 1 day margin (naive midnight)."""
    t = parsedate_to_datetime(last_modified).astimezone(timezone.utc).replace(tzinfo=None)
    return pd.Timestamp(t).normalize() + MARGIN


def clean_xlsx(content: bytes) -> bytes:
    """Drop the created/modified stamps from docProps/core.xml: some PJM files have invalid ones
    ('2024- 1-31T19:36: 1Z') that openpyxl refuses. The sheets are untouched."""
    zin = zipfile.ZipFile(io.BytesIO(content))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename == "docProps/core.xml":
                data = re.sub(rb"<dcterms:(created|modified)[^>]*>[^<]*</dcterms:\1>", b"", data)
            zout.writestr(info, data)
    return out.getvalue()


def read_xlsx(content: bytes, **kw):
    return pd.read_excel(io.BytesIO(clean_xlsx(content)), **kw)


def _num(v) -> float | None:
    x = pd.to_numeric(v, errors="coerce")
    return None if pd.isna(x) else float(x)


def parse_price_summary(content: bytes) -> pd.DataFrame:
    """Clearing price summary -> rows (dy, area, value): BRA Resource Clearing Price, $/MW-day.

    dy is the delivery year's start year. Areas that were not modelled ('**') have no row.
    """
    raw = read_xlsx(content, header=None)
    hdr = next((i for i in range(len(raw)) if (raw.iloc[i].astype(str).str.strip() == "RTO").any()), None)
    if hdr is None:
        raise ValueError("price summary: no header row with RTO")
    cols = {str(v).strip(): j for j, v in enumerate(raw.iloc[hdr]) if pd.notna(v)}
    if "RTO" not in cols:
        raise ValueError("price summary: no RTO column")
    rows, dy, best = [], None, {}
    rank = {"CP": 0, "ANNUAL": 1}  # PJM's RTO history uses CP, else Annual, else the single product
    for i in range(hdr + 1, len(raw)):
        first = str(raw.iloc[i, 0]).strip()
        m = re.fullmatch(r"DY\s*(\d{2})/(\d{2})", first)
        if m:
            dy = 2000 + int(m.group(1))
            if int(m.group(2)) != (dy + 1) % 100:
                raise ValueError(f"price summary: bad delivery year {first!r}")
            continue
        if first != "BRA" or dy is None:
            continue
        product = str(raw.iloc[i, 1]).strip().upper()
        r = rank.get(product, 2 if product in ("*", "NAN", "") else 9)
        if r == 9 or (dy in best and best[dy][0] <= r):
            continue
        best[dy] = (r, i)
    for dy, (_, i) in sorted(best.items()):
        for area, j in cols.items():
            v = _num(raw.iloc[i, j])
            if v is not None:
                rows.append((dy, area, v))
    out = pd.DataFrame(rows, columns=["dy", "area", "value"])
    if out.empty or not (out["area"] == "RTO").any():
        raise ValueError("price summary: no BRA RTO prices found")
    return out


def parse_cleared_rto(content: bytes) -> float:
    """BRA results xlsx -> RTO total (annual-equivalent) cleared UCAP, MW."""
    raw = read_xlsx(content, sheet_name="BRA Resource Clearing Results", header=None)
    for i in range(len(raw)):
        cells = raw.iloc[i].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
        hit = cells.str.contains(r"^Total .*Resources Cleared", regex=True)
        if hit.any():
            j = int(hit.to_numpy().nonzero()[0][0])
            for k in range(i + 1, min(i + 5, len(raw))):
                if re.match(r"RTO\b", str(raw.iloc[k, 0]).strip()):
                    v = _num(raw.iloc[k, j])
                    if v is None:
                        break
                    return round(v, 1)  # MW with one decimal as in the reports
    raise ValueError("BRA results: RTO total cleared MW not found")


def results_links(html: str) -> dict[int, str]:
    """BRA results xlsx per delivery year (start year), from the RPM page."""
    out = {}
    pat = r'href="([^"]*rpm-auction-info/(?:\d{4}-\d{4}/)?(\d{4})-(\d{4})-(?:bra|base-residual-auction)-results\.xlsx)"'
    for url, y0, y1 in re.findall(pat, html):
        if int(y1) == int(y0) + 1:
            out[int(y0)] = url if url.startswith("http") else BASE + url
    return out


def load_data_links(html: str) -> dict[int, str]:
    out = {}
    for url, y in re.findall(r'href="([^"]*load-forecast/(\d{4})-load(?:-forecast)?-report-data\.xlsx)"', html):
        out[int(y)] = url if url.startswith("http") else BASE + url
    return out


def load_tables_links(html: str) -> dict[int, str]:
    out = {}
    for url, y in re.findall(r'href="([^"]*load-forecast/(\d{4})-load-report-tables\.xlsx)"', html):
        out[int(y)] = url if url.startswith("http") else BASE + url
    return out


def parse_load_data(content: bytes, sheet: str, vintage: int) -> pd.DataFrame:
    """Load report data xlsx, one zone sheet -> rows (target, peak_mw, energy_gwh): summer peak (max of Jun-Aug)
    and annual net energy (sum of 12 months), complete years only."""
    df = read_xlsx(content, sheet_name=sheet)
    need = {"YEAR", "MONTH", "PEAK_MW", "ENERGY_GWH"}
    if not need <= set(df.columns):
        raise ValueError(f"load data {vintage}/{sheet}: columns {list(df.columns)}")
    df = df.assign(YEAR=pd.to_numeric(df["YEAR"], errors="coerce"), MONTH=pd.to_numeric(df["MONTH"], errors="coerce"))
    df = df.dropna(subset=["YEAR", "MONTH"])
    if int(df["YEAR"].min()) != vintage:
        raise ValueError(f"load data {vintage}/{sheet}: first year {int(df['YEAR'].min())}")
    rows = []
    for year, g in df.groupby("YEAR"):
        if sorted(g["MONTH"].astype(int)) != list(range(1, 13)):
            continue
        summer = g[g["MONTH"].isin([6, 7, 8])]["PEAK_MW"].astype(float).max()
        rows.append((int(year), float(summer), float(g["ENERGY_GWH"].astype(float).sum())))
    return pd.DataFrame(rows, columns=["target", "peak_mw", "energy_gwh"])


def parse_adjustments(content: bytes, vintage: int) -> pd.DataFrame:
    """Load report tables xlsx, Table B-9 -> rows (area, target, value): large-load adjustments to the summer
    peak above what is embedded in the model, MW."""
    raw = read_xlsx(content, sheet_name="Table B9", header=None)
    title = " ".join(str(x) for x in raw.iloc[:6, 0].dropna())
    if "Adjustments Above Embedded to Summer Peak" not in title:
        raise ValueError(f"Table B9 title not recognised: {title[:120]!r}")
    hdr = None
    for i in range(len(raw)):
        years = [_num(v) for v in raw.iloc[i, 1:]]
        if years and years[0] == vintage:
            hdr = i
            break
    if hdr is None:
        raise ValueError(f"Table B9: no header row starting with {vintage}")
    targets = {j: int(_num(v)) for j, v in enumerate(raw.iloc[hdr]) if j > 0 and _num(v) is not None}
    names = raw.iloc[:, 0].astype(str).str.strip()
    rows = []
    for area in ADJ_AREAS.values():
        hit = raw[names == area]
        if len(hit) != 1:
            raise ValueError(f"Table B9: {area!r} found {len(hit)} times")
        for j, t in targets.items():
            v = _num(hit.iloc[0, j])
            if v is not None:
                rows.append((area, t, v))
    return pd.DataFrame(rows, columns=["area", "target", "value"])


def posted(table: dict[int, tuple[str, str]], key: int, last_modified: str | None) -> pd.Timestamp:
    if key in table:
        return pd.Timestamp(table[key][0])
    if not last_modified:
        raise ValueError(f"no posting date and no Last-Modified for {key}")
    return lm_known_from(last_modified)


# ------------------------------------------------------------------ downloads


def _get(url: str):
    return http.get(url, SOURCE, timeout=120)


@lru_cache(maxsize=1)
def bra_rows() -> pd.DataFrame:
    """Rows (series, period, value, known_from) for the BRA series (cached per process)."""
    page = _get(RPM_PAGE).text
    summary = _get(SUMMARY_URL)
    links = results_links(page)
    lm = {}
    rows = []
    for dy, url in sorted(links.items()):
        if dy < CLEARED_FROM:
            continue
        r = _get(url)
        lm[dy] = r.headers.get("Last-Modified")
        rows.append(("cleared_rto", dy, parse_cleared_rto(r.content)))
    prices = parse_price_summary(summary.content)
    for key, area in PRICE_AREAS.items():
        for dy, value in prices.loc[prices["area"] == area, ["dy", "value"]].itertuples(index=False):
            rows.append((f"rcp_{key}", int(dy), float(value)))
    out = pd.DataFrame(rows, columns=["series", "dy", "value"])
    out["known_from"] = [posted(BRA_POSTED, dy, lm.get(dy) or summary.headers.get("Last-Modified"))
                         for dy in out["dy"]]
    out["period"] = out["dy"].astype(str)
    return out


def bra(series: str) -> pd.DataFrame:
    df = bra_rows()
    return df[df["series"] == series][["period", "value", "known_from"]].reset_index(drop=True)


@lru_cache(maxsize=1)
def load_rows() -> pd.DataFrame:
    """Rows (series, period, value, known_from) for the load forecast series (cached per process)."""
    page = _get(LIBRARY_PAGE).text + _get(LOAD_DEV_PAGE).text
    data, tables = load_data_links(page), load_tables_links(page)
    if not data:
        raise ValueError("no load report data files linked from the library page")
    rows = []
    for v, url in sorted(data.items()):
        r = _get(url)
        kf = posted(LF_POSTED, v, r.headers.get("Last-Modified"))
        for key, (sheet, _) in LF_AREAS.items():
            df = parse_load_data(r.content, sheet, v).set_index("target")
            for h in HORIZONS:
                if v + h in df.index:
                    rows.append((f"peak_{key}_h{h}", v, float(df.loc[v + h, "peak_mw"]), kf))
                    rows.append((f"energy_{key}_h{h}", v, float(df.loc[v + h, "energy_gwh"]), kf))
    for v, url in sorted(tables.items()):
        r = _get(url)
        kf = max(lm_known_from(r.headers["Last-Modified"]), posted(LF_POSTED, v, r.headers["Last-Modified"]))
        adj = parse_adjustments(r.content, v)
        for key, area in ADJ_AREAS.items():
            a = adj[adj["area"] == area].set_index("target")["value"]
            for h in HORIZONS:
                if v + h in a.index:
                    rows.append((f"adj_{key}_h{h}", v, float(a[v + h]), kf))
    out = pd.DataFrame(rows, columns=["series", "vintage", "value", "known_from"])
    out["period"] = out["vintage"].astype(str)
    return out


def load_forecast(series: str) -> pd.DataFrame:
    df = load_rows()
    return df[df["series"] == series][["period", "value", "known_from"]].reset_index(drop=True)
