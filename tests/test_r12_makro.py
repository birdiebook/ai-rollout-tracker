"""R12 review of track M1 (docs/granskning/r12_makro.md): BEA release-archive vintages and BLS CPI/PPI dating.

Fixtures only, no network. Dates and values in the fixtures were read from primary sources on 2026-11-24: BEA's
release archive (apps.bea.gov/histdata) and news-release archive, BLS's news-release archive, the CPI news releases,
the PPI news release 2002-02-15 and the PPI Detailed Reports (Table 11), and ALFRED vintages of CUSR0000SEHF01.

Passing tests pin properties the review verified. The six strict xfails for R-1, R-2, R-4, R-5, R-6 and R-8 flipped
when track X9 fixed the defects (branch auto14/x9-makro); their assertions are unchanged.
"""

from __future__ import annotations

import io
from datetime import date

import openpyxl
import pandas as pd
import pytest

from ai_tracker import catalog, http, observations, warehouse
from ai_tracker.sources import bea_nipa, bls

T = pd.Timestamp
P = pd.Period


class _Resp:
    def __init__(self, content=b"", payload=None, text="", headers=None):
        self.content, self._payload, self.text, self.headers = content, payload, text, headers or {}

    def json(self):
        return self._payload


# ------------------------------------------------------------------ BEA: dating and same-vintage sums


def _workbook(sheets: dict[str, tuple[str, list[str], list[tuple[str, list]]]]) -> bytes:
    """{sheet name: (published line, periods, [(code, values)])} -> xlsx bytes in BEA's layout."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, (published, periods, rows) in sheets.items():
        ws = wb.create_sheet(name)
        header = [f"Table {name}", "Seasonally adjusted at annual rates", "Quarterly data",
                  "Bureau of Economic Analysis", published, "File created Jun 28 2023  1:07PM"]
        for line in header:
            ws.append([line])
        ws.append([])
        ws.append(["Line", None, None] + periods)
        for i, (code, values) in enumerate(rows, start=1):
            ws.append([i, code.lower(), code] + values)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


JUNE29 = "Data published June 29, 2023"
S1_2023Q1_THIRD = {"T10502-Q": (JUNE29, ["2022Q4", "2023Q1"],
                                [("A191RL", [2.6, 2.0]), ("Y034RY", [0.01, -0.03]), ("B935RY", [0.02, -0.01]),
                                 ("B985RY", [0.04, 0.02])])}
# The split table 4.2.5A (1967-1998) is not updated in every release and keeps an older "Data published" line.
S4_2023Q1_THIRD = {"T40202-Q": (JUNE29, ["2023Q1"], [("B852RZ", [-0.5])]),
                   "T40205A-Q": ("Data published September 30, 2022", ["1998Q4"], [("B852RC", [100.0])]),
                   "T40205B-Q": (JUNE29, ["1999Q1", "2023Q1"], [("B852RC", [110.0, 300.0])]),
                   "T40206B-Q": (JUNE29, ["2023Q1"], [("B852RX", [290.0])])}


def test_release_dated_by_header_not_by_a_directory_nine_days_earlier(monkeypatch, tmp_path):
    """2023Q1 Third: the archive directory says June 20, the release (and every table header) June 29, 2023. An
    un-updated split sheet with an older header must not pull the date back either."""
    monkeypatch.setattr(bea_nipa, "CACHE_DIR", tmp_path)
    payload = [{"FileArray": [bea_nipa.ARCHIVE_FILES + "GDP_and_PI\\2023\\Q1\\Third_June-20-2023"]}]
    s1, s4 = _workbook(S1_2023Q1_THIRD), _workbook(S4_2023Q1_THIRD)

    def fake_get(url, source, params=None, save=True, timeout=60, **kw):
        if url == bea_nipa.ARCHIVE_API:
            return _Resp(payload=payload)
        return _Resp(content=s1 if "Section1" in url else s4)

    monkeypatch.setattr(http, "get", fake_get)
    got = bea_nipa.archive_vintages(since=T("2017-10-27"))
    assert list(got) == [T("2023-06-29")]
    assert got[T("2023-06-29")]["B852RC"].to_dict() == {P("1998Q4", "Q"): 100.0, P("1999Q1", "Q"): 110.0,
                                                        P("2023Q1", "Q"): 300.0}


def _q(*periods):
    return pd.PeriodIndex(periods, freq="Q-DEC")


def _gross_vintages():
    q = _q
    return {
        # first archived release: 2017Q2 was first published earlier (2017-07-28) and gets this date
        T("2017-10-27"): {"Y034RY": pd.Series([0.10, 0.20], q("2017Q2", "2017Q3")),
                          "B985RY": pd.Series([0.05, 0.06], q("2017Q2", "2017Q3"))},
        T("2017-11-29"): {"Y034RY": pd.Series([0.10, 0.25], q("2017Q2", "2017Q3")),  # only Y034RY revised
                          "B985RY": pd.Series([0.05, 0.06], q("2017Q2", "2017Q3"))},
        T("2017-12-21"): {"Y034RY": pd.Series([0.10, 0.25], q("2017Q2", "2017Q3")),
                          "B985RY": pd.Series([0.05, 0.09], q("2017Q2", "2017Q3"))},  # only B985RY revised
    }


def test_gross_contribution_is_always_a_same_vintage_sum_and_older_periods_get_the_first_vintage():
    v = _gross_vintages()
    rows = bea_nipa.archive_rows(("Y034RY", "B985RY"), v)
    for p, value, kf in rows.itertuples(index=False):
        assert value == pytest.approx(v[kf]["Y034RY"][p] + v[kf]["B985RY"][p], abs=1e-9)
    assert [(str(p), v_, k.date().isoformat()) for p, v_, k in rows.itertuples(index=False)] == [
        ("2017Q2", 0.15, "2017-10-27"), ("2017Q3", 0.26, "2017-10-27"), ("2017Q3", 0.31, "2017-11-29"),
        ("2017Q3", 0.34, "2017-12-21")]
    assert rows["known_from"].min() == T("2017-10-27")  # nothing is dated before the first archived release


# Real B852RX (imports of computers, peripherals and parts, chained dollars): the comprehensive update of
# 2023-09-28 moved to 2017 dollars and the table now starts in 2007Q1; the release before it (2023-08-30, 2012
# dollars) started in 2002Q1. Values from BEA's archive (track M1 extracts, re-read by R12 from the workbooks).
REBASED = {
    T("2023-08-30"): {"B852RX": pd.Series([80963.0, 87694.0], pd.PeriodIndex(["2006Q4", "2007Q1"], freq="Q-DEC"))},
    T("2023-09-28"): {"B852RX": pd.Series([82231.0], pd.PeriodIndex(["2007Q1"], freq="Q-DEC"))},
}


def test_real_computer_imports_show_only_periods_of_the_newest_vintage(monkeypatch):
    monkeypatch.setattr(bea_nipa, "_VINTAGES", REBASED)
    rows = catalog.by_key()["us_imp_computers_real"].fetch()
    latest = rows.sort_values("known_from").groupby("period").tail(1)
    assert {str(p) for p in latest["period"]} <= {"2007Q1"}


# ------------------------------------------------------------------ BLS: release calendar and dating rules


def _li(month: str, program: str, mmddyyyy: str | None) -> str:
    name = bls.PROGRAMS[program]
    if mmddyyyy is None:
        return f"<li>{month} {name}&ndash; Not published because of 2025 lapse in federal government appropriations</li>"
    return (f'<li><a href="/news.release/archives/{program}_{mmddyyyy}.htm">{month} {name}</a> '
            f'(<a href="/news.release/archives/{program}_{mmddyyyy}.pdf">PDF</a>)</li>')


def _archive(program: str, items) -> str:
    return "<ul>" + "\n".join(_li(m, program, d) for m, d in items) + "</ul>"


# BLS news-release archive, www.bls.gov/bls/news-release/cpi.htm (read 2026-11-24)
CPI_ITEMS = [("October 2026", "11102026"), ("September 2026", "10142026"), ("January 2026", "02132026"),
             ("December 2025", "01132026"), ("November 2025", "12182025"), ("October 2025", None),
             ("September 2025", "10242025"), ("August 2025", "09112025")]


def test_cpi_nsa_release_dates_around_the_2025_shutdown():
    cal = bls.parse_news_archive(_archive("cpi", CPI_ITEMS), "cpi")
    flat = ("series_id\tyear\tperiod\tvalue\tfootnote_codes\n"  # values as in the CPI news releases
            "CUUR0000SEHF01\t2025\tM08\t298.738\t\n"
            "CUUR0000SEHF01\t2025\tM09\t296.887\t\n"
            "CUUR0000SEHF01\t2025\tM10\t-\tX\n"
            "CUUR0000SEHF01\t2025\tM11\t294.939\t\n"
            "CUUR0000SEHF01\t2025\tM12\t295.121\t\n"
            "CUUR0000SEHF01\t2026\tM01\t299.731\t\n"
            "CUUR0000SEHF01\t2026\tM09\t309.852\t\n"
            "CUUR0000SEHF01\t2026\tM10\t307.673\t\n")
    df = bls.parse_flat(flat, ["CUUR0000SEHF01"])["CUUR0000SEHF01"]
    out = bls.date_rows(df, "cpi_nsa", cal, T("2026-11-13"))
    assert {str(p): (k.date().isoformat(), s) for p, _, k, s in out.itertuples(index=False)} == {
        "2025-08": ("2025-09-11", "release"), "2025-09": ("2025-10-24", "release"),
        "2025-11": ("2025-12-18", "release"), "2025-12": ("2026-01-13", "release"),
        "2026-01": ("2026-02-13", "release"), "2026-09": ("2026-10-14", "release"),
        "2026-10": ("2026-11-10", "release")}  # October 2025 never collected: no row


def test_cpi_sa_window_matches_the_revisions_seen_in_alfred():
    """ALFRED CUSR0000SEHF01: the January-2018 CPI release (2018-02-14) revised 2013-01..2017-12 and left 2012-12
    unchanged; nothing in 2021-01..2026-06 changed after the release that last revised it."""
    cal = bls.parse_news_archive(_archive("cpi", [("January 2018", "02142018"), ("January 2017", "02152017"),
                                                  ("December 2016", "01182017")]), "cpi")
    df = pd.DataFrame({"period": [P("2012-12", "M"), P("2013-01", "M"), P("2017-12", "M")],
                       "value": [1.0, 2.0, 3.0], "footnotes": ["", "", ""]})
    out = bls.date_rows(df, "cpi_sa", cal, T("2018-03-01"))
    assert list(out["known_from"]) == [T("2017-02-15"), T("2018-02-14"), T("2018-02-14")]


# BLS news-release archive, www.bls.gov/bls/news-release/ppi.htm (read 2026-11-24)
PPI_ITEMS = [("February 2026", "03182026"), ("January 2026", "02272026"), ("December 2025", "01302026"),
             ("November 2025", "01142026"), ("October 2025", None), ("September 2025", "11252025"),
             ("August 2025", "09102025"), ("July 2025", "08142025"), ("June 2025", "07162025"),
             ("May 2025", "06122025")]


def test_ppi_final_values_dated_at_release_m_plus_4_through_the_shutdown():
    """PPI Detailed Reports (Table 11, 518210 and 221122-42): May 2025 is final in the September-2025 report
    (2025-11-25), June and July 2025 in the November-2025 report (2026-01-14, October was not published),
    September 2025 in the January-2026 report (2026-02-27); October 2025 first appears 2026-01-14."""
    cal = bls.parse_news_archive(_archive("ppi", PPI_ITEMS), "ppi")
    months = ["2025-05", "2025-06", "2025-07", "2025-09", "2025-10", "2025-11"]
    df = pd.DataFrame({"period": [P(m, "M") for m in months], "value": [124.185, 123.663, 126.753, 123.943,
                                                                         124.462, 123.2],
                       "footnotes": ["", "", "", "", "", "P"]})
    out = bls.date_rows(df, "ppi", cal, T("2026-03-18"))
    assert dict(zip(months, out["known_from"])) == {
        "2025-05": T("2025-11-25"), "2025-06": T("2026-01-14"), "2025-07": T("2026-01-14"),
        "2025-09": T("2026-02-27"), "2025-10": T("2026-03-18"), "2025-11": T("2026-03-18")}


def _bls_fetch(monkeypatch, page: str, flat: str, headers=None):
    monkeypatch.setattr(bls, "_CACHE", {})
    monkeypatch.setattr(bls, "_CALENDARS", {})

    def fake_get(url, source, params=None, save=True, timeout=60, **kw):
        return _Resp(text=page) if "news-release" in url else _Resp(text=flat, headers=headers or {})

    monkeypatch.setattr(http, "get", fake_get)


def test_ppi_data_processing_not_dated_before_the_index_was_introduced(monkeypatch):
    page = _archive("ppi", [("January 2002", "02152002"), ("April 2001", "05112001")])
    flat = ("series_id\tyear\tperiod\tvalue\tfootnote_codes\n"
            "PCU518210518210\t2000\tM12\t100.0\t\n"
            "PCU518210518210\t2001\tM01\t100.6\t\n")
    _bls_fetch(monkeypatch, page, flat, {"Last-Modified": "Fri, 15 Feb 2002 13:30:00 GMT"})
    rows = bls.release_rows("PCU518210518210")
    assert rows["known_from"].min() >= T("2002-02-15")


def test_news_archive_reads_six_digit_release_names():
    page = ('<ul><li><a href="/news.release/archives/cpi_06161999.htm">May 1999 Consumer Price Index</a></li>\n'
            '<li>April 1999 Consumer Price Index (<a aria-label="April 1999 Consumer Price Index TXT" '
            'href="/news.release/history/cpi_051499.txt">TXT</a>)</li></ul>')
    cal = bls.parse_news_archive(page, "cpi")
    assert cal.get(P("1999-04", "M")) == T("1999-05-14")


def test_month_beyond_the_archive_list_is_never_dated_to_an_earlier_release(monkeypatch):
    page = _archive("cpi", [("September 2026", "10142026")])
    flat = ("series_id\tyear\tperiod\tvalue\tfootnote_codes\n"
            "CUUR0000SEHF01\t2026\tM09\t309.852\t\n"
            "CUUR0000SEHF01\t2026\tM10\t307.673\t\n")
    _bls_fetch(monkeypatch, page, flat, headers={})
    rows = bls.release_rows("CUUR0000SEHF01").set_index("period")
    assert rows.loc[P("2026-10", "M"), "known_from"] > T("2026-10-14")


# ------------------------------------------------------------------ warehouse: known gaps, contact identity


def _cpi_table(months: list[str]):
    spec = catalog.by_key()["us_cpi_electricity_nsa_m"]
    rows = pd.DataFrame({"period": months, "value": [300.0] * len(months),
                         "known_from": [pd.Period(m, "M").end_time.normalize() + pd.Timedelta(days=12)
                                        for m in months]})
    return spec, observations.new_rows(spec, rows, observations._empty(), date(2026, 11, 24))


def test_october_2025_alone_is_an_accepted_gap():
    spec, t = _cpi_table(["2025-09", "2025-11", "2025-12"])
    assert warehouse.run_checks(warehouse.connect(t, [spec]))["no_gaps"].empty


def test_a_second_cpi_gap_is_still_reported():
    spec, t = _cpi_table(["2025-09", "2025-11", "2025-12", "2026-02"])
    assert len(warehouse.run_checks(warehouse.connect(t, [spec]))["no_gaps"]) == 1


def test_contact_identity_only_for_the_named_domains(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "ai-rollout-tracker contact@example.org")
    assert http.user_agent("download.bls.gov") == "ai-rollout-tracker contact@example.org"
    assert http.user_agent("bls.gov") == "ai-rollout-tracker contact@example.org"
    assert http.user_agent("notbls.gov") == http.DEFAULT_UA
