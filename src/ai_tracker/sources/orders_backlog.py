"""Orders and backlog in earnings releases (track S3): a curated CSV of agent-extracted figures with citations.

Vertiv, GE Vernova, Eaton, Dell, Digital Realty and Equinix state orders, backlog, book-to-bill, gas turbine slot
reservations, AI server orders and signed leases in the press release of their results 8-K (EX-99.1), not in XBRL.
The agent read the reading set (orders_backlog_corpus) and recorded one row per stated figure in
curated/orders_backlog.csv: the number as stated, its definition (measure, segment, component, window, form, organic,
unit), the period, dates, URL / accession, locator and the SHA-256 of the exact sentence. The sentence itself is kept
only in data/raw/orders_sentences (gitignored). Coding rules, committed before the coding:
docs/kallor/order_orderstock.md.

Row types:
- value : a stated figure for one definition and period
- stop  : the first regular release that no longer states a definition the previous regular release stated

A definition is (company, measure, segment, component, window, form, organic, unit). Different definitions are
different series; nothing is converted or spliced. known_from = `filed` (EDGAR filingDate).
"""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

import pandas as pd

from ai_tracker import config

PATH = config.REPO / "curated" / "orders_backlog.csv"
SENTENCES_DIR = config.REPO / "data" / "raw" / "orders_sentences"  # gitignored

COLUMNS = ["id", "company", "row_type", "measure", "segment", "component", "window", "form", "organic", "unit",
           "value", "qualifier", "metric_as_stated", "fiscal_period", "period_end", "filed", "accepted",
           "release_date", "form_type", "exhibit", "source_url", "accession", "locator", "sentence_sha256", "note"]
DEFINITION = ("company", "measure", "segment", "component", "window", "form", "organic", "unit")
COMPANIES = {"vrt": "Vertiv", "gev": "GE Vernova", "etn": "Eaton", "dell": "Dell", "dlr": "Digital Realty",
             "eqix": "Equinix"}
BRANCH = {"vrt": "G7", "gev": "G7", "etn": "G7", "dell": "G6", "dlr": "G4", "eqix": "G4"}
ROW_TYPES = ("value", "stop")
STOCKS = ("backlog", "signed_not_commenced", "slot_reservations", "backlog_and_slot_reservations")
FLOWS = ("orders", "book_to_bill", "shipments", "sales", "leases_signed", "bookings")
MEASURES = STOCKS + FLOWS
_ETN = ("electrical_americas", "electrical_global", "electrical")
SEGMENTS = {
    "vrt": ("total",),
    "gev": ("total", "power", "wind", "electrification", "gas_power"),
    "etn": _ETN + ("data_centers",) + tuple(f"{s}_data_centers" for s in _ETN),
    "dell": ("ai_servers",),
    "dlr": ("total", "gt_1mw", "0_1mw", "interconnection", "other"),
    "eqix": ("total",),
}
COMPONENTS = ("all", "equipment", "services", "dlr_share")
WINDOWS = ("q", "ttm", "ytd", "fy", "end")
FORMS = ("level", "yoy_pct", "qoq_pct", "vs_ye_pct", "ratio", "yoy_mult")
PCT_FORMS = ("yoy_pct", "qoq_pct", "vs_ye_pct")
ORGANIC = ("organic", "cc", "reported", "unspecified", "na")
UNITS = ("MUSD", "pct", "ratio", "GW", "MW")
QUALIFIERS = ("", "approx", "gt", "lt")
POINT_QUALIFIERS = ("", "approx")  # gt/lt are bounds: in the CSV, never series points
EXHIBITS = ("EX-99.1", "EX-99")
FORM_TYPES = ("8-K", "8-K/A")
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()  # a stop row (locator "absent")
MAX_RELEASE_LEAD_DAYS = 3  # the dateline may precede the filing day by at most this many days
MIDPOINT_DAYS = 45  # fiscal quarter -> calendar quarter containing its midpoint (sources/sec.py)
FY_MIDPOINT_DAYS = 182

# Extra Item 2.02 documents (preliminary results, investor-day updates): they can add values, never stops. Amendments
# (8-K/A) are extra by their form. Filled during the coding; each entry is an interpretation in the source doc.
EXTRA_DOCUMENTS: dict[str, str] = {
    "0001193125-22-256141": "vrt: preliminary third-quarter 2022 orders and backlog with an outlook update and a CEO "
                            "change (8-K 2022-10-03), not the regular results release",
}


class CsvError(ValueError):
    pass


def _float(x) -> float | None:
    return float(x) if str(x).strip() not in ("", "nan", "None") else None


def _check_row(r: dict) -> None:
    if r["company"] not in COMPANIES or r["row_type"] not in ROW_TYPES:
        raise CsvError("company/row_type not in the scheme")
    for col, allowed in (("measure", MEASURES), ("component", COMPONENTS), ("window", WINDOWS), ("form", FORMS),
                         ("organic", ORGANIC), ("unit", UNITS), ("qualifier", QUALIFIERS),
                         ("exhibit", EXHIBITS), ("form_type", FORM_TYPES)):
        if r[col] not in allowed:
            raise CsvError(f"{col} {r[col]!r} not in the scheme")
    if r["segment"] not in SEGMENTS[r["company"]]:
        raise CsvError(f"segment {r['segment']!r} not in the scheme for {r['company']}")
    form, unit, measure = r["form"], r["unit"], r["measure"]
    if form in PCT_FORMS and unit != "pct":
        raise CsvError("a growth rate is in pct")
    if form in ("ratio", "yoy_mult") and unit != "ratio":
        raise CsvError("a ratio or multiple is in ratio")
    if form == "level" and unit not in ("MUSD", "GW", "MW"):
        raise CsvError("a level is in MUSD, GW or MW")
    if (measure == "book_to_bill") != (form == "ratio"):
        raise CsvError("form ratio is book-to-bill and only book-to-bill")
    if (r["organic"] == "na") != (form in ("level", "ratio")):
        raise CsvError("organic is na for levels and ratios and only for them")
    if (measure in STOCKS) != (r["window"] == "end"):
        raise CsvError("window end is for stocks (backlog, signed-not-commenced, reservations) and only for them")
    if r["component"] == "dlr_share" and r["company"] != "dlr":
        raise CsvError("component dlr_share is Digital Realty's")
    if not re.fullmatch(r"[0-9a-f]{64}", r["sentence_sha256"]):
        raise CsvError("sentence_sha256 must be 64 hex characters")
    if not r["source_url"].startswith("https://www.sec.gov/Archives/edgar/data/"):
        raise CsvError("source_url must be an EDGAR archive URL")
    if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", r["accession"]) or r["accession"].replace("-", "") not in r["source_url"]:
        raise CsvError("accession missing or not the URL's folder")
    filed = pd.Timestamp(r["filed"])
    if r["accepted"] and not -1 <= (pd.Timestamp(r["accepted"][:10]) - filed).days <= 1:
        raise CsvError(f"accepted {r['accepted']} does not match the filing date {r['filed']}")
    if r["release_date"]:
        lead = (filed - pd.Timestamp(r["release_date"])).days
        if not 0 <= lead <= MAX_RELEASE_LEAD_DAYS:
            raise CsvError(f"release_date {r['release_date']} is after the filing or more than "
                           f"{MAX_RELEASE_LEAD_DAYS} days before it")
    end = pd.Timestamp(r["period_end"])
    if not end < filed or (filed - end).days > 6 * 366:
        raise CsvError("period_end must be before the filing date (and within six years)")
    fp = r"FY\d{4}" if r["window"] == "fy" else r"(?:FY)?\d{4}Q[1-4]"
    if not re.fullmatch(fp, r["fiscal_period"]):
        raise CsvError(f"fiscal_period {r['fiscal_period']!r} is not {fp}")
    if r["row_type"] == "value":
        v = _float(r["value"])
        if v is None or not re.fullmatch(r"sentence #\d+", r["locator"]):
            raise CsvError("a value row has a value and a locator 'sentence #k'")
        if r["sentence_sha256"] == EMPTY_SHA256:
            raise CsvError("a value row has the hash of its sentence")
        if unit in ("MUSD", "GW", "MW") and v <= 0:
            raise CsvError("a level is positive")
        if unit == "pct" and not -100 <= v <= 1000:
            raise CsvError("a growth rate in pct is in [-100, 1000]")
        if unit == "ratio" and not 0 < v <= 20:
            raise CsvError("a ratio is in (0, 20]")
        if not r["metric_as_stated"].strip():
            raise CsvError("metric_as_stated missing")
    else:
        if r["value"].strip() or r["qualifier"] or r["locator"] != "absent" or r["sentence_sha256"] != EMPTY_SHA256:
            raise CsvError("a stop row has no value or qualifier, locator 'absent' and the SHA-256 of an empty string")
        if r["form_type"] != "8-K" or r["accession"] in EXTRA_DOCUMENTS:
            raise CsvError("a stop is coded in a regular release")


def load(path: Path | None = None) -> pd.DataFrame:
    """Validated rows of the curated CSV, with known_from (= filed) as Timestamp."""
    path = path or PATH
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if rows and list(rows[0]) != COLUMNS:
        raise CsvError(f"columns {list(rows[0])} != {COLUMNS}")
    ids: set[str] = set()
    for r in rows:
        try:
            if r["id"] in ids:
                raise CsvError("duplicate id")
            _check_row(r)
        except (CsvError, ValueError) as exc:
            raise CsvError(f"{path.name} id={r.get('id')}: {exc}") from None
        ids.add(r["id"])
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["known_from"] = pd.to_datetime(df["filed"])
    dup = df[df["row_type"] == "value"].duplicated(list(DEFINITION) + ["period_end", "accession"], keep=False)
    if dup.any():
        raise CsvError(f"{path.name}: two values for one definition and period in one document: "
                       f"{sorted(df[df['row_type'] == 'value'][dup]['id'])[:6]}")
    return df


# ------------------------------------------------------------------ definitions and series

def definition_of(row) -> tuple[str, ...]:
    return tuple(str(row[c]) for c in DEFINITION)


def series_key(row) -> str:
    """ob_<company>_<measure>_<segment>[_<component>]_<window>_<form>[_<organic>]_<unit> (register 2026-11-25, S3)."""
    d = dict(zip(DEFINITION, definition_of(row)))
    parts = [d["company"], d["measure"], d["segment"]]
    if d["component"] != "all":
        parts.append(d["component"])
    parts += [d["window"], d["form"]]
    if d["organic"] != "na":
        parts.append(d["organic"])
    parts.append(d["unit"].lower())
    return "ob_" + "_".join(parts)


def period_of(period_end, window: str) -> str:
    """Calendar quarter containing the fiscal quarter's midpoint; for a fiscal year the calendar year of its midpoint."""
    end = pd.Timestamp(period_end)
    if window == "fy":
        return str((end - pd.Timedelta(days=FY_MIDPOINT_DAYS)).year)
    return str((end - pd.Timedelta(days=MIDPOINT_DAYS)).to_period("Q-DEC"))


def freq_of(window: str) -> str:
    return "A" if window == "fy" else "Q"


def points(df: pd.DataFrame) -> pd.DataFrame:
    """Value rows that are series points (qualifier empty or approx), with key and period."""
    v = df[(df["row_type"] == "value") & df["qualifier"].isin(POINT_QUALIFIERS)].copy()
    if v.empty:
        return v.assign(key=pd.Series(dtype=str), period=pd.Series(dtype=str))
    v["key"] = v.apply(series_key, axis=1)
    v["period"] = [period_of(e, w) for e, w in zip(v["period_end"], v["window"])]
    return v


def series_frame(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """Release-dated rows (period, value, known_from) of one series.

    The first document that states a figure for a period counts; a repeated value adds no row, a changed value is a
    new vintage (register 2026-11-25, S3).
    """
    p = points(df)
    p = p[p["key"] == key].sort_values(["known_from", "accepted", "id"], kind="stable")
    out, last = [], {}
    for per, v, kf in p[["period", "value", "known_from"]].itertuples(index=False):
        if per in last and last[per] == v:
            continue
        last[per] = v
        out.append((per, float(v), kf))
    res = pd.DataFrame(out, columns=["period", "value", "known_from"])
    res = res.drop_duplicates(["period", "known_from"], keep="last")
    return res.sort_values(["period", "known_from"]).reset_index(drop=True)


def catalog_keys(df: pd.DataFrame, min_periods: int = 2) -> list[str]:
    """Series keys with points for at least `min_periods` periods (register: at least two)."""
    p = points(df)
    if p.empty:
        return []
    n = p.groupby("key")["period"].nunique()
    return sorted(n[n >= min_periods].index)


def definition_rows(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """All rows (values of every qualifier and stops) of one series key."""
    if df.empty:
        return df
    return df[df.apply(series_key, axis=1) == key]


def stopped(df: pd.DataFrame, key: str) -> pd.Series | None:
    """The stop row if the newest series row of the definition (by filing) is a stop, else None.

    Series rows are points and stops. A bound ("more than 100%") restates the definition but is not a point, so a
    bound after a stop does not reopen the series (interpretation in docs/kallor/order_orderstock.md).
    """
    d = definition_rows(df, key)
    if d.empty:
        return None
    d = d[(d["row_type"] == "stop") | d["qualifier"].isin(POINT_QUALIFIERS)]
    if d.empty:
        return None
    d = d.sort_values(["known_from", "row_type"], kind="stable")  # 'stop' sorts after 'value' on one day
    last = d.iloc[-1]
    return last if last["row_type"] == "stop" else None


def regular_releases(df: pd.DataFrame, company: str) -> list[str]:
    """Accessions of the company's regular releases in the CSV, by filing (8-K, not in EXTRA_DOCUMENTS)."""
    d = df[(df["company"] == company) & (df["form_type"] == "8-K") & ~df["accession"].isin(list(EXTRA_DOCUMENTS))]
    d = d.sort_values(["known_from", "accepted"], kind="stable")
    return list(dict.fromkeys(d["accession"]))


def release_periods(df: pd.DataFrame) -> dict[str, str]:
    """Accession -> the release's own fiscal period: the latest period_end of its quarterly (non-fy) rows."""
    out = {}
    for acc, g in df.groupby("accession"):
        q = g[g["window"] != "fy"]
        out[acc] = str((q if not q.empty else g)["period_end"].max())
    return out


def expected_stops(df: pd.DataFrame, regular: dict[str, list[str]] | None = None) -> pd.DataFrame:
    """(company, key, accession) where the stop rule (register 2026-11-25, S3) puts a stop.

    `regular` maps a company to its regular releases in filing order (default: regular_releases of the CSV, so a
    release with no coded row at all must be passed explicitly). A definition is stated by a release when the release
    has a value row (any qualifier) for its own period: the latest period_end of the release for q/ttm/ytd/end, the
    fiscal year that ends with it for fy (compared between fourth-quarter releases only).
    """
    vals = df[df["row_type"] == "value"].copy()
    out = []
    if vals.empty:
        return pd.DataFrame(out, columns=["company", "key", "accession"])
    vals["key"] = vals.apply(series_key, axis=1)
    own = release_periods(df)
    for company in sorted(set(df["company"])):
        rel = (regular or {}).get(company) or regular_releases(df, company)
        v = vals[vals["company"] == company]
        stated = {acc: set(v[(v["accession"] == acc) & (v["period_end"] == own.get(acc))]["key"]) for acc in rel}
        fy_releases = [acc for acc in rel if (v[(v["accession"] == acc) & (v["window"] == "fy")].shape[0] > 0)]
        for prev, cur in zip(rel, rel[1:]):
            for key in sorted(stated[prev] - stated[cur]):
                if "_fy_" in key:
                    continue
                out.append((company, key, cur))
        for prev, cur in zip(fy_releases, fy_releases[1:]):
            for key in sorted(k for k in stated[prev] - stated[cur] if "_fy_" in k):
                out.append((company, key, cur))
    return pd.DataFrame(out, columns=["company", "key", "accession"])


def gap_periods(df: pd.DataFrame, key: str) -> dict[str, str]:
    """Missing periods within a series' span -> why (a stop covers it, or no release in the corpus states it)."""
    f = series_frame(df, key)
    if f.empty:
        return {}
    window = definition_rows(df, key)["window"].iloc[0]
    freq = "Y-DEC" if window == "fy" else "Q-DEC"
    have = set(f["period"])
    idx = pd.period_range(min(have), max(have), freq=freq)
    stops = definition_rows(df, key)
    stops = stops[stops["row_type"] == "stop"]
    stop_periods = sorted(period_of(e, window) for e in stops["period_end"])
    out = {}
    for p in idx:
        s = str(p)
        if s in have:
            continue
        after_stop = [sp for sp in stop_periods if sp <= s]
        out[s] = ("stop: the company stopped stating the figure (curated/orders_backlog.csv)" if after_stop
                  else "not stated in any results release in the corpus")
    return out
