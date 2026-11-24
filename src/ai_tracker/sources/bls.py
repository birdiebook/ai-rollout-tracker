"""BLS CPI and PPI from the flat files on download.bls.gov, with release dates from BLS's news-release archive.

download.bls.gov and www.bls.gov refuse clients without a declared contact (Akamai "Access Denied"; BLS usage
policy), so http.user_agent sends the project's generic client identity from .env for *.bls.gov. No API key and
no api.bls.gov quota are used.

Flat files (tab separated): series_id, year, period (M01-M12, M13 = annual average), value, footnote_codes.
Each file holds only the current vintage of every series. Release dates: www.bls.gov/bls/news-release/<cpi|ppi>.htm
lists every news release since reference month 1999-05 as "<Month> <YYYY> Consumer Price Index" with the release date in the file
name (cpi_MMDDYYYY.htm). A reference month without its own release ("Not published because of 2025 lapse ...")
is absent from that list.

Dating (docs/mattregister.md, 2026-11-24 M1). The file is the vintage of its latest release:
file date = max(newest release in the archive list, the file's Last-Modified). Values are dated back only as far as
BLS's own revision rules allow:
- cpi_nsa: CPI-U is final when released -> the reference month's release date ("release"). R-footnoted values
  (revised) get the file date.
- cpi_sa: seasonal factors are revised each February (January CPI release) for the previous 5 years -> a value
  for year y is known from the January-CPI release of year y+5, or the latest January release so far; months of
  the current year from their own release.
- ppi: every PPI can be revised monthly for 4 months after original publication -> P (preliminary) values get the
  file date; final values the release date of reference month m+4.
A month without its own release takes the next release; months before the archive take its first release.
Rule-dated rows are "backfill"; later changes become revisions dated by the fetch (observations.new_rows).

Licence (www.bls.gov/opub/copyright-information.htm): "You are free to use our public domain material without
specific permission, although we do ask that you cite the Bureau of Labor Statistics as the source."
"""

from __future__ import annotations

import html as htmllib
import io
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

import pandas as pd

from ai_tracker import http

FLAT = "https://download.bls.gov/pub/time.series/"
NEWS_ARCHIVE = "https://www.bls.gov/bls/news-release/{program}.htm"
SOURCE = "bls"
PROGRAMS = {"cpi": "Consumer Price Index", "ppi": "Producer Price Index"}
# series id -> (program, flat file under FLAT, dating rule)
SERIES = {
    "CUUR0000SEHF01": ("cpi", "cu/cu.data.12.USHousing", "cpi_nsa"),
    "CUSR0000SEHF01": ("cpi", "cu/cu.data.12.USHousing", "cpi_sa"),
    "PCU518210518210": ("ppi", "pc/pc.data.56.ISPsSearchPortandDataProcess", "ppi"),
    "PCU22112222112242": ("ppi", "pc/pc.data.46.Utilities", "ppi"),
}
# Stored from this month: CPI electricity NSA has only scattered months before 1952 (December values from 1913);
# 1952-01 is also where the SA series starts.
MONTHLY_FROM = {"CUUR0000SEHF01": pd.Period("1952-01", freq="M")}
SA_YEARS = 5  # CPI seasonally adjusted data are revised for the previous 5 years each February
PPI_REVISION_MONTHS = 4  # PPIs can be revised monthly for 4 months after original publication
MAX_RELEASE_LAG_DAYS = 120  # a release more than this after its reference month is a parsing error


# ------------------------------------------------------------------ parsers (pure)


def parse_flat(text: str, series_ids) -> dict[str, pd.DataFrame]:
    """Flat file -> {series id: DataFrame(period (monthly Period), value, footnotes)}. M13 and '-' are skipped."""
    wanted = set(series_ids)
    rows: dict[str, list] = {s: [] for s in wanted}
    lines = io.StringIO(text)
    header = [h.strip() for h in next(lines).split("\t")]
    if header[:4] != ["series_id", "year", "period", "value"]:
        raise ValueError(f"BLS flat file: unexpected header {header}")
    for line in lines:
        parts = [p.strip() for p in line.rstrip("\n").split("\t")]
        if len(parts) < 4 or parts[0] not in wanted:
            continue
        sid, year, period, value = parts[:4]
        if not re.fullmatch(r"M(0[1-9]|1[0-2])", period):
            continue  # M13 = annual average
        try:
            v = float(value)
        except ValueError:
            continue  # '-': not available (e.g. October 2025, lapse in appropriations)
        rows[sid].append((pd.Period(f"{year}-{period[1:]}", freq="M"), v, parts[4] if len(parts) > 4 else ""))
    missing = [s for s, r in rows.items() if not r]
    if missing:
        raise ValueError(f"BLS flat file lacks series {missing}")
    return {s: pd.DataFrame(r, columns=["period", "value", "footnotes"]).sort_values("period").reset_index(drop=True)
            for s, r in rows.items()}


def parse_news_archive(page_html: str, program: str) -> pd.Series:
    """Reference month (Period M) -> release date, from the news-release archive page of `program` (cpi, ppi)."""
    name = PROGRAMS[program]
    out: dict[pd.Period, pd.Timestamp] = {}
    for item in re.findall(r"<li>(.*?)</li>", page_html, flags=re.S):
        text = re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", item))).strip()
        m = re.match(rf"([A-Z][a-z]+) (\d{{4}}) {name}\b", text)
        link = re.search(rf"{program}_(\d{{8}})\.(?:htm|pdf|txt)", item)
        if not m or not link:
            continue  # navigation, or "Not published because of ..."
        month = pd.Period(datetime.strptime(f"{m.group(1)} {m.group(2)}", "%B %Y"), freq="M")
        released = pd.Timestamp(datetime.strptime(link.group(1), "%m%d%Y"))
        lag = (released - month.end_time.normalize()).days
        if not 0 < lag <= MAX_RELEASE_LAG_DAYS:
            raise ValueError(f"BLS {program}: release {released.date()} for {month} is {lag} days after month end")
        if month in out and out[month] != released:
            raise ValueError(f"BLS {program}: two release dates for {month}")
        out[month] = released
    if not out:
        raise ValueError(f"BLS {program}: no releases on the archive page")
    return pd.Series(out).sort_index()


def release_date(month: pd.Period, calendar: pd.Series) -> tuple[pd.Timestamp | None, bool]:
    """(release date that first contained `month`, whether it was the month's own release).

    No own release: the earliest release for a later month. Before the archive: its first release. After the
    newest listed month: (None, False).
    """
    if month in calendar.index:
        return calendar[month], True
    if month < calendar.index.min():
        return calendar.min(), False
    later = calendar[calendar.index > month]
    return (later.min(), False) if len(later) else (None, False)


def date_rows(df: pd.DataFrame, rule: str, calendar: pd.Series, file_date: pd.Timestamp) -> pd.DataFrame:
    """Columns period, value, known_from, source for one series' current vintage (see module docstring)."""
    out = []
    for period, value, notes in df[["period", "value", "footnotes"]].itertuples(index=False):
        first, own = release_date(period, calendar)
        first = file_date if first is None else min(first, file_date)
        kf, src = first, "release" if own else "backfill"
        if rule == "cpi_nsa":
            if "R" in notes:
                kf, src = file_date, "backfill"
        elif rule == "cpi_sa":
            revisions = [d for y in range(period.year + 1, period.year + SA_YEARS + 1)
                         if (d := release_date(pd.Period(f"{y}-01", freq="M"), calendar)[0]) is not None
                         and d <= file_date]
            if "R" in notes:
                kf, src = file_date, "backfill"
            elif revisions and max(revisions) > first:
                kf, src = max(revisions), "backfill"
        elif rule == "ppi":
            if "P" in notes or "C" in notes:
                kf = file_date
            else:
                final = release_date(period + PPI_REVISION_MONTHS, calendar)[0]
                kf = file_date if final is None else max(first, min(final, file_date))
            src = "backfill"
        else:
            raise ValueError(f"unknown dating rule {rule!r}")
        out.append((period, value, kf, src))
    return pd.DataFrame(out, columns=["period", "value", "known_from", "source"])


def last_modified(headers) -> pd.Timestamp | None:
    value = headers.get("Last-Modified") if headers else None
    if not value:
        return None
    return pd.Timestamp(parsedate_to_datetime(value).date())


# ------------------------------------------------------------------ fetching

_CACHE: dict[str, tuple[str, pd.Timestamp | None]] = {}
_CALENDARS: dict[str, pd.Series] = {}


def calendar(program: str) -> pd.Series:
    if program not in _CALENDARS:
        page = http.get(NEWS_ARCHIVE.format(program=program), SOURCE).text
        _CALENDARS[program] = parse_news_archive(page, program)
    return _CALENDARS[program]


def _flat(file: str) -> tuple[str, pd.Timestamp | None]:
    if file not in _CACHE:
        r = http.get(FLAT + file, SOURCE, timeout=120)
        _CACHE[file] = (r.text, last_modified(r.headers))
    return _CACHE[file]


def release_rows(series_id: str) -> pd.DataFrame:
    program, file, rule = SERIES[series_id]
    text, modified = _flat(file)
    cal = calendar(program)
    file_date = max(d for d in (cal.max(), modified) if d is not None)
    df = parse_flat(text, [series_id])[series_id]
    if series_id in MONTHLY_FROM:
        df = df[df["period"] >= MONTHLY_FROM[series_id]].reset_index(drop=True)
    return date_rows(df, rule, cal, file_date)
