"""PJM capacity auctions and load forecast: parsers, posting dates, catalog wiring (no network)."""

from __future__ import annotations

import io
import re
import zipfile

import pandas as pd
import pytest
from openpyxl import Workbook

from ai_tracker import catalog, observations
from ai_tracker.series import pjm as pjm_series
from ai_tracker.sources import pjm


def _xlsx(sheets: dict[str, list[list]]) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for r in rows:
            ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _break_core(content: bytes) -> bytes:
    """Write the invalid docProps date some PJM files carry ('2024- 1-31T19:36: 1Z')."""
    zin = zipfile.ZipFile(io.BytesIO(content))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename == "docProps/core.xml":
                data = re.sub(rb"(<dcterms:modified[^>]*>)[^<]*", rb"\g<1>2024- 1-31T19:36: 1Z", data)
            zout.writestr(info, data)
    return out.getvalue()


HDR = [None, "Capacity Product Type *", "RTO", "MAAC", "DOM"]


def summary() -> bytes:
    rows = [["Resource Clearing Prices for all RPM Auctions held to date"], HDR,
            ["DY 07/08"], ["BRA", "*", 40.8, "**", "**"], [],
            ["DY 14/15"], ["BRA", "Annual", 125.99, 136.5, "**"], ["BRA", "Ext Summer", 125.99, 136.5, "**"],
            ["BRA", "Limited", 125.47, 136.0, "**"], ["1IA", "Annual", 25.0, 25.0, "**"], [],
            ["DY 18/19"], ["BRA", "CP", 164.77, 164.77, "**"], ["BRA", "BASE GEN", 149.98, 149.98, "**"], [],
            ["DY 22/23"], ["BRA", "CP", 50, 95.79, "**"], ["1IA", "***   AUCTION CANCELLED   ***"], [],
            ["DY25/26"], ["BRA", "CP", 269.92, 269.92, 444.26], ["3IA", "CP", 323.9, 323.9, 323.9],
            ["** LDA was not modeled"]]
    return _xlsx({"RCP": rows})


def test_price_summary_picks_the_bra_product_pjm_uses():
    df = pjm.parse_price_summary(summary())
    rto = df[df["area"] == "RTO"].set_index("dy")["value"]
    assert rto.to_dict() == {2007: 40.8, 2014: 125.99, 2018: 164.77, 2022: 50.0, 2025: 269.92}
    dom = df[df["area"] == "DOM"].set_index("dy")["value"]
    assert dom.to_dict() == {2025: 444.26}  # '**' = not modelled: no row; incremental auctions ignored


def test_price_summary_rejects_layout_without_rto():
    with pytest.raises(ValueError):
        pjm.parse_price_summary(_xlsx({"RCP": [["x"], [None, "Type", "MAAC"], ["DY 07/08"], ["BRA", "*", 1]]}))


def results(total_label="Total Annual Equivalent Resources Cleared               [MW]") -> bytes:
    rows = [["2024/2025 BRA Resource Clearing Results"], [], ["Resource Clearing Prices"], ["RTO", 28.92, 0, 28.92],
            [], ["Cleared & Make-Whole MWs"],
            ["LDA", "Annual Resources  [MW]", "Summer Period Resources [MW]", "Winter Period Resources [MW]",
             "Seasonal Resources Matched to be Annual [MW]", total_label, "Annual Resources Make-whole [MW]"],
            ["RTO*", 146871.8, 605.6, 605.6, 605.6, 147477.4, 4.1], ["MAAC", 1, 1, 1, 1, 64199.3, 0]]
    return _xlsx({"Summary": [["x"]], "BRA Resource Clearing Results": rows})


def test_cleared_rto_reads_total_column():
    assert pjm.parse_cleared_rto(results()) == pytest.approx(147477.4)
    with pytest.raises(ValueError):
        pjm.parse_cleared_rto(results(total_label="Something else"))


def test_clean_xlsx_reads_files_with_invalid_docprops():
    broken = _break_core(results())
    assert pjm.parse_cleared_rto(broken) == pytest.approx(147477.4)


def test_links_from_pages():
    rpm = ('<a href="/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2020-2021-base-residual-auction-results.xlsx">'
           '<a href="/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2026-2027/2026-2027-bra-results.xlsx">'
           '<a href="/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2019-2020-base-residual-auction-results-xls.xls">')
    links = pjm.results_links(rpm)
    assert sorted(links) == [2020, 2026] and links[2026].startswith("https://www.pjm.com/-/media/")
    lib = ('<a href="/-/media/DotCom/library/reports-notices/load-forecast/2017-load-forecast-report-data.xlsx">'
           '<a href="/-/media/DotCom/library/reports-notices/load-forecast/2026-load-report-data.xlsx">'
           '<a href="/-/media/DotCom/planning/res-adeq/load-forecast/2026-load-report-tables.xlsx">')
    assert sorted(pjm.load_data_links(lib)) == [2017, 2026]
    assert sorted(pjm.load_tables_links(lib)) == [2026]


def load_data(vintage=2026, years=3, partial_last=True) -> bytes:
    def sheet(zone, scale):
        rows = [["ZONE_NAME", "YEAR", "MONTH", "PEAK_MW", "ENERGY_GWH"]]
        for y in range(vintage, vintage + years):
            for m in range(1, 13 if not (partial_last and y == vintage + years - 1) else 7):
                peak = scale * (100 + (y - vintage) + (50 if m == 7 else 20 if m == 1 else 0))
                rows.append([zone, str(y), m, peak, scale * 10])
        return rows
    return _xlsx({"DOM": sheet("DOM", 1), "PJM_RTO": sheet("PJM_RTO", 10)})


def test_load_data_summer_peak_and_annual_energy():
    df = pjm.parse_load_data(load_data(), "PJM_RTO", 2026).set_index("target")
    assert list(df.index) == [2026, 2027]  # 2028 incomplete (6 months) is dropped
    assert df.loc[2027, "peak_mw"] == 10 * 151  # July, not the January peak
    assert df.loc[2027, "energy_gwh"] == 12 * 100
    with pytest.raises(ValueError):
        pjm.parse_load_data(load_data(), "PJM_RTO", 2025)  # first year must be the vintage


def tables(vintage=2026) -> bytes:
    rows = [[None], [" Back to TOC"], [None], ["Table B-9"],
            [f"Adjustments Above Embedded to Summer Peak Load (MW) for Each PJM Zone and RTO ({vintage} - 2046)"],
            ["* Note: updated"], [None] + [float(vintage + i) for i in range(11)],
            ["AE"] + [0.0] * 11, ["DOM"] + [100.0 * i for i in range(11)], [None],
            ["PJM RTO"] + [1000.0 * i for i in range(11)]]
    return _xlsx({"Table of Contents": [["x"]], "Table B9": rows})


def test_adjustments_table_b9():
    df = pjm.parse_adjustments(tables(), 2026)
    dom = df[df["area"] == "DOM"].set_index("target")["value"]
    assert dom[2031] == 500.0 and len(dom) == 11
    with pytest.raises(ValueError):
        pjm.parse_adjustments(tables(2025), 2026)


def test_posting_dates_and_fallback():
    assert pjm.posted(pjm.BRA_POSTED, 2025, None) == pd.Timestamp("2024-07-30")
    # unknown delivery year: Last-Modified (UTC day) + 1 day
    assert pjm.posted(pjm.BRA_POSTED, 2029, "Tue, 22 Dec 2026 21:30:00 GMT") == pd.Timestamp("2026-12-23")
    with pytest.raises(ValueError):
        pjm.posted(pjm.LF_POSTED, 2027, None)
    # every curated BRA date is before the delivery year ends, never after the auction it dates (sanity)
    for dy, (d, why) in pjm.BRA_POSTED.items():
        assert pd.Timestamp(d) < pd.Timestamp(dy + 1, 5, 31) or dy < 2011, (dy, d)
        assert why


def test_bra_and_load_rows_end_to_end(monkeypatch):
    pages = {
        pjm.RPM_PAGE: '<a href="/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2025-2026/'
                      '2025-2026-base-residual-auction-results.xlsx">',
        pjm.SUMMARY_URL: summary(),
        pjm.BASE + "/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2025-2026/"
                   "2025-2026-base-residual-auction-results.xlsx": results(),
        pjm.LIBRARY_PAGE: '<a href="/-/media/DotCom/library/reports-notices/load-forecast/2026-load-report-data.xlsx">'
                          '<a href="/-/media/DotCom/library/reports-notices/load-forecast/2027-load-report-data.xlsx">',
        pjm.LOAD_DEV_PAGE: '<a href="/-/media/DotCom/planning/res-adeq/load-forecast/2026-load-report-tables.xlsx">',
        pjm.BASE + "/-/media/DotCom/library/reports-notices/load-forecast/2026-load-report-data.xlsx":
            load_data(2026, 12),
        pjm.BASE + "/-/media/DotCom/library/reports-notices/load-forecast/2027-load-report-data.xlsx":
            load_data(2027, 12),
        pjm.BASE + "/-/media/DotCom/planning/res-adeq/load-forecast/2026-load-report-tables.xlsx": tables(),
    }

    class R:
        def __init__(self, body):
            self.content = body if isinstance(body, bytes) else body.encode()
            self.text = body if isinstance(body, str) else ""
            self.headers = {"Last-Modified": "Fri, 06 Feb 2026 17:31:47 GMT"}

    monkeypatch.setattr(pjm, "_get", lambda url: R(pages[url]))
    pjm.bra_rows.cache_clear()
    pjm.load_rows.cache_clear()
    try:
        rto = pjm.bra("rcp_rto").set_index("period")
        assert rto.loc["2007", "known_from"] == pd.Timestamp("2011-05-13")
        assert rto.loc["2025", "value"] == 269.92 and rto.loc["2025", "known_from"] == pd.Timestamp("2024-07-30")
        assert pjm.bra("cleared_rto")["value"].tolist() == [147477.4]
        peak = pjm.load_forecast("peak_dom_h5").set_index("period")
        assert peak.loc["2026", "value"] == 155 and peak.loc["2026", "known_from"] == pd.Timestamp("2026-01-14")
        # 2027 is not in LF_POSTED: Last-Modified + 1 day
        assert peak.loc["2027", "known_from"] == pd.Timestamp("2026-02-07")
        adj = pjm.load_forecast("adj_rto_h10")
        assert adj["value"].tolist() == [10000.0] and adj["known_from"].tolist() == [pd.Timestamp("2026-02-07")]
        # the observation table accepts the rows (negative lag: known before the period ends)
        spec = catalog.by_key(pjm_series.SPECS)["pjm_lf_peak_dom_h5"]
        new = observations.new_rows(spec, pjm.load_forecast("peak_dom_h5"), observations._empty())
        assert set(new["source"]) == {"release"} and len(new) == 2
    finally:
        pjm.bra_rows.cache_clear()
        pjm.load_rows.cache_clear()


def test_catalog_entries():
    keys = {s.key for s in pjm_series.SPECS}
    assert {"pjm_bra_rcp_rto_a", "pjm_bra_rcp_dom_a", "pjm_bra_cleared_rto_a", "pjm_lf_peak_dom_h10",
            "pjm_lf_energy_rto_h1", "pjm_lf_adj_dom_h5"} <= keys
    assert catalog.validate(pjm_series.SPECS) == []
    assert not any(s.publish for s in pjm_series.SPECS)  # no open licence
