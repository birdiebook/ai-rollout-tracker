"""EIA Electric Power Monthly: Table 5.4.A and EIA-861M parsers, known_from, vintage chain (no network)."""

from __future__ import annotations

import io

import pandas as pd
import pytest
from openpyxl import Workbook

from ai_tracker import catalog, observations
from ai_tracker.sources import eia_epm

AREAS = {"Virginia": (4000, 3900), "West Virginia": (600, 590), "Texas": (18000, 17000), "Georgia": (5000, 4800),
         "Arizona": (4400, 3900), "Oregon": (2600, 2200), "Ohio": (3900, 3800), "U.S. Total": (150579, 144363)}


def table_5_4_a(month="July", year=2026, unit="Thousand Megawatthours", areas=AREAS) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["Table 5.4.A. Sales of Electricity to Ultimate Customers by End-Use Sector,"])
    ws.append([f"by State, {month} {year} and {year - 1} ({unit})"])
    ws.append([None, "Residential", None, "Commercial", None, "Industrial", None])
    ws.append(["Census Division\nand State"] + [f"{month} {y}" for y in (year, year - 1)] * 3)
    ws.append(["South Atlantic", 1, 1, 99999, 99999, 1, 1])
    for name, (cur, prev) in areas.items():
        ws.append([name, 1, 1, cur, prev, 1, 1])
    ws.append(["Notes: values are preliminary."])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


STATE_CODES = ["AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DC", "DE", "FL", "GA", "HI", "IA", "ID", "IL", "IN", "KS",
               "KY", "LA", "MA", "MD", "ME", "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM", "NV",
               "NY", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV", "WY"]


def sales_revenue(months=((2026, 8), (2026, 7)), va=8502970.0, incomplete=None) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Monthly-States"
    sectors = ["RESIDENTIAL", "COMMERCIAL", "INDUSTRIAL", "TRANSPORTATION", "TOTAL"]
    ws.append([None] * 4 + sum(([s, None, None, None] for s in sectors), []))
    ws.append([None] * 4 + ["Revenue", "Sales", "Customers", "Price"] * 5)
    ws.append(["Year", "Month", "State", "Data Status"] + ["Thousand Dollars", "Megawatthours", "Count", "Cents/kWh"] * 5)
    for y, m in months:
        for st in STATE_CODES:
            if incomplete == (y, m) and st == "WY":
                continue
            com = va if st == "VA" else 1000.0
            ws.append([y, m, st, "Preliminary"] + [1, 2, 3, 4] + [1, com, 3, 4] + [1, 2, 3, 4] * 3)
    ws.append(["Footnote text"])
    wb.create_sheet("US-YTD")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_table_5_4_a():
    df = eia_epm.parse_table_5_4_a(table_5_4_a())
    got = {(a, str(p)): v for a, p, v in df.itertuples(index=False)}
    assert got[("VA", "2026-07")] == 4000 and got[("VA", "2025-07")] == 3900  # not West Virginia
    assert got[("US", "2026-07")] == 150579 and got[("US", "2025-07")] == 144363
    assert {a for a, _ in got} == set(eia_epm.STATES) | {"US"}
    # older issues: "Retail Sales ...", million kWh (same quantity)
    old = eia_epm.parse_table_5_4_a(table_5_4_a("November", 2012, "Million Kilowatthours"))
    assert set(old["period"].astype(str)) == {"2012-11", "2011-11"}


@pytest.mark.parametrize("kw", [{"unit": "Megawatts"}, {"month": "Julember"},
                                {"areas": {k: v for k, v in AREAS.items() if k != "Ohio"}}])
def test_parse_table_5_4_a_rejects_unexpected_layouts(kw):
    with pytest.raises((ValueError, StopIteration)):
        eia_epm.parse_table_5_4_a(table_5_4_a(**kw))


def test_parse_861m_commercial_gwh_and_us_sum():
    df = eia_epm.parse_861m(sales_revenue(incomplete=(2026, 7)))
    got = {(a, str(p)): v for a, p, v in df.itertuples(index=False)}
    assert got[("VA", "2026-08")] == pytest.approx(8502.97)
    assert got[("US", "2026-08")] == pytest.approx(8502.97 + 50 * 1.0)
    assert ("US", "2026-07") not in got  # a month with a missing state gives no US total


def test_known_from_is_last_modified_plus_margin():
    # current EPM table: Last-Modified 2026-10-22 12:24 GMT, release date 2026-10-23
    kf = eia_epm.known_from("Thu, 22 Oct 2026 12:24:47 GMT")
    assert kf == pd.Timestamp("2026-10-24") and kf > pd.Timestamp("2026-10-23")
    assert eia_epm.known_from("Thu, 22 Oct 2026 23:30:00 -0500") == pd.Timestamp("2026-10-25")  # UTC day


def test_archive_names_skip_commented_links():
    html = ('<!--<li><a href="./archive/december2026.zip">ZIP</a></li>-->'
            '<li><a href="./archive/september2026.zip">ZIP</a> <a href="./archive/september2026.pdf">PDF</a></li>'
            '<li><a href="./archive/august2026.zip">ZIP</a></li>')
    assert eia_epm.archive_names(html) == ["august2026", "september2026"]


def _frame(kind, rows):
    df = pd.DataFrame([(a, pd.Period(p, "M"), v) for a, p, v in rows], columns=["area", "period", "value"])
    df.attrs["kind"] = kind
    return df


def test_vintage_chain_backfill_and_rounding():
    first = _frame("5.4.A", [("VA", "2013-01", 100.2), ("VA", "2012-01", 90.0)])   # year-ago < cutoff: ignored
    later = _frame("5.4.A", [("VA", "2014-01", 120.0), ("VA", "2013-01", 101.0)])  # revision of 2013-01
    full = _frame("861M", [("VA", "2012-01", 91.4), ("VA", "2012-12", 95.0), ("VA", "2013-01", 100.6),
                           ("VA", "2014-01", 119.9)])
    kf1, kf2, kf3 = pd.Timestamp("2013-03-26"), pd.Timestamp("2014-03-26"), pd.Timestamp("2026-10-25")
    rows = eia_epm.vintage_rows([(kf2, later), (kf3, full), (kf1, first)], full, backfill_lag_days=90)
    got = {(str(p), kf): (v, s) for _, p, v, kf, s in rows.itertuples(index=False)}
    assert got == {
        ("2012-01", pd.Timestamp("2012-01-31") + pd.Timedelta(days=90)): (91.0, "backfill"),
        ("2012-12", pd.Timestamp("2012-12-31") + pd.Timedelta(days=90)): (95.0, "backfill"),
        ("2013-01", kf1): (100.0, "release"),
        ("2013-01", kf2): (101.0, "release"),
        # 861M: 100.6 -> 101 equals the latest value: no row. 119.9 -> 120 likewise.
        ("2014-01", kf2): (120.0, "release"),
    }


def test_catalog_entries():
    specs = {s.key: s for s in catalog.ALL if s.key.startswith("us_elec_sales_com")}
    assert {"us_elec_sales_com_m", "us_elec_sales_com_va_m", "us_elec_sales_com_tx_m", "us_elec_sales_com_ga_m",
            "us_elec_sales_com_az_m", "us_elec_sales_com_or_m"} <= set(specs)
    for s in specs.values():
        assert s.branch == "G7" and s.freq == "M" and "public domain" in s.license.lower() and s.revised


def test_source_column_kept_on_upsert(tmp_path):
    spec = catalog.by_key()["us_elec_sales_com_va_m"]
    rows = pd.DataFrame({"period": [pd.Period("2012-01", "M"), pd.Period("2013-01", "M")], "value": [91.0, 100.0],
                         "known_from": [pd.Timestamp("2012-04-30"), pd.Timestamp("2013-03-26")],
                         "source": ["backfill", "release"]})
    path = tmp_path / "obs.parquet"
    assert observations.upsert(spec, rows, path=path) == 2
    assert observations.load(path)["source"].tolist() == ["backfill", "release"]
