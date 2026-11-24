"""Track M1: BEA release-archive vintages (GDP contributions, computer imports) and BLS CPI/PPI dating. No network."""

from __future__ import annotations

import io

import openpyxl
import pandas as pd
import pytest

from ai_tracker import catalog, http, observations
from ai_tracker.sources import bea_nipa, bls

T = pd.Timestamp
P = pd.Period


# ------------------------------------------------------------------ BEA archive


def _archive_payload():
    base = "/Inetpub/wwwroot/website/website/HistData/Files/Releases/"
    dirs = ["GDP_and_PI\\2002\\Q3\\1. Advance_October-31-2002", "GDP_and_PI\\2002old\\09_September\\_notes",
            "GDP_and_PI\\2018\\Q4", "GDP_and_PI\\2018\\Q4\\Initial_March-1-2019",
            "GDP_and_PI\\2018\\Q4\\Initial_March-1-2019\\UND", "GDP_and_PI\\2025\\Q3\\Initial_December-22-2025",
            "GDP_and_PI\\2026\\Q3\\Advance_October-29-2026"]
    return [{"FolderPattern": "GDP_and_PI\\dataYear\\Quarter\\vintage_NewReleaseDate",
             "FileArray": [base + d for d in dirs]}]


def test_parse_archive_dirs_keeps_release_directories_only():
    rels = bea_nipa.parse_archive_dirs(_archive_payload())
    assert [(r.quarter, r.vintage, r.dir_date) for r in rels] == [
        ("2002Q3", "Advance", T("2002-10-31")), ("2018Q4", "Initial", T("2019-03-01")),
        ("2025Q3", "Initial", T("2025-12-22")), ("2026Q3", "Advance", T("2026-10-29"))]
    assert rels[-1].path == "GDP_and_PI/2026/Q3/Advance_October-29-2026"


def test_parse_published_both_header_formats():
    assert bea_nipa.parse_published("Data published October 29, 2026") == T("2026-10-29")
    assert bea_nipa.parse_published("Data published Oct 27 2017  8:30AM") == T("2017-10-27")
    assert bea_nipa.parse_published("Data published Sept 27, 2018") == T("2018-09-27")
    assert bea_nipa.parse_published("File created Oct 28 2026  1:52PM") is None


def _sheet(ws, title, published, periods, rows):
    ws.append([title])
    ws.append(["Seasonally adjusted at annual rates"])
    ws.append([f"Quarterly data from {periods[0]} to {periods[-1]}"])
    ws.append(["Bureau of Economic Analysis"])
    ws.append([published])
    ws.append(["File created Oct 28 2026  1:52PM"])
    ws.append([])
    ws.append(["Line", None, None] + periods)
    for line, label, code, values in rows:
        ws.append([line, label, code] + values)
    ws.append(["Legend / Footnotes:"])


def _workbook(sheets) -> bytes:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, args in sheets.items():
        _sheet(wb.create_sheet(name), *args)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


SECTION1 = {
    "T10502-A": ("Table 1.5.2 annual", "Data published October 29, 2026", ["2024", "2025"],
                 [(31, "Information processing equipment", "Y034RY", [9.0, 9.0])]),
    "T10502-Q": ("Table 1.5.2. Contributions to Percent Change in Real Gross Domestic Product, Expanded Detail",
                 "Data published October 29, 2026", ["2026Q1", "2026Q2", "2026Q3"],
                 [(1, "    Gross domestic product", "A191RL", [1.0, 2.0, 3.4]),
                  (None, "Percentage points at annual rates:", None, [None, None, None]),
                  (31, "        Information processing equipment", "Y034RY", [0.5, 0.6, 0.86]),
                  (32, "          Computers and peripheral equipment", "B935RY", [".....", 0.4, 0.72]),
                  (38, "        Software\\4\\", "B985RY", [0.2, 0.21, 0.23])]),
    "T10102-Q": ("Table 1.1.2", "Data published October 29, 2026", ["2026Q3"],
                 [(1, "GDP", "A191RL", [99.0])]),  # another table with the same code: not read
}
SECTION4 = {
    "T40202-Q": ("Table 4.2.2", "Data published October 29, 2026", ["2026Q2", "2026Q3"],
                 [(35, "    Computers, peripherals, and parts", "B852RZ", [1.0, 8.38])]),
    "T40205A-Q": ("Table 4.2.5A", "Data published October 29, 2026", ["1998Q3", "1998Q4"],
                  [(118, "Computers, peripherals, and parts", "B852RC", [50000, 51000])]),
    "T40205B-Q": ("Table 4.2.5B", "Data published October 29, 2026", ["1998Q4", "2026Q3"],
                  [(118, "Computers, peripherals, and parts", "B852RC", [51000, 751292])]),
    "T40206B-Q": ("Table 4.2.6B", "Data published October 29, 2026", ["2026Q3"],
                  [(119, "Computers, peripherals, and parts\\1\\", "B852RX", [635007])]),
}


def test_parse_workbook_reads_codes_from_the_named_tables():
    wanted = bea_nipa._section_codes()
    pub, out = bea_nipa.parse_workbook(_workbook(SECTION1), wanted[1])
    assert pub == T("2026-10-29")
    assert out["A191RL"].to_dict() == {P("2026Q1", "Q"): 1.0, P("2026Q2", "Q"): 2.0, P("2026Q3", "Q"): 3.4}
    assert list(out["B935RY"].index.astype(str)) == ["2026Q2", "2026Q3"]  # '.....' = not available
    assert out["Y034RY"].index.freqstr == "Q-DEC"
    pub4, out4 = bea_nipa.parse_workbook(_workbook(SECTION4), wanted[4])
    assert out4["B852RC"].to_dict() == {P("1998Q3", "Q"): 50000.0, P("1998Q4", "Q"): 51000.0,
                                        P("2026Q3", "Q"): 751292.0}  # 4.2.5A and 4.2.5B joined
    assert out4["B852RX"].iloc[-1] == 635007


def test_parse_workbook_rejects_conflicting_split_tables_and_missing_codes():
    bad = dict(SECTION4)
    bad["T40205B-Q"] = ("Table 4.2.5B", "Data published October 29, 2026", ["1998Q4"],
                        [(118, "Computers", "B852RC", [52000])])
    with pytest.raises(ValueError, match="differs between sheets"):
        bea_nipa.parse_workbook(_workbook(bad), bea_nipa._section_codes()[4])
    with pytest.raises(ValueError, match="not in tables"):
        bea_nipa.parse_workbook(_workbook(SECTION1), {"B852RZ": "T40202"})


def test_check_release_date():
    rel = bea_nipa.Release("GDP_and_PI/2025/Q3/Initial_December-22-2025", T("2025-12-22"), "Initial", "2025Q3")
    bea_nipa.check_release_date(rel, T("2025-12-23"))
    with pytest.raises(ValueError, match="far from"):
        bea_nipa.check_release_date(rel, T("2026-02-01"))
    early = bea_nipa.Release("x", T("2025-09-28"), "Advance", "2025Q3")
    with pytest.raises(ValueError, match="before the quarter ended"):
        bea_nipa.check_release_date(early, T("2025-09-29"))


class _Resp:
    def __init__(self, content=b"", payload=None, text="", headers=None):
        self.content, self._payload, self.text, self.headers = content, payload, text, headers or {}

    def json(self):
        return self._payload


def test_archive_vintages_dates_by_published_line_and_caches(monkeypatch, tmp_path):
    monkeypatch.setattr(bea_nipa, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(bea_nipa, "FIRST_XLSX", T("2025-01-01"))
    payload = [{"FileArray": [bea_nipa.ARCHIVE_FILES + "GDP_and_PI\\2025\\Q3\\Initial_December-22-2025"]}]
    s1 = _workbook({k: (v[0], "Data published December 23, 2025", *v[2:]) for k, v in SECTION1.items()})
    s4 = _workbook({k: (v[0], "Data published December 23, 2025", *v[2:]) for k, v in SECTION4.items()})
    calls = []

    def fake_get(url, source, params=None, save=True, timeout=60, **kw):
        calls.append(url)
        if url == bea_nipa.ARCHIVE_API:
            return _Resp(payload=payload)
        return _Resp(content=s1 if "Section1" in url else s4)

    monkeypatch.setattr(http, "get", fake_get)
    got = bea_nipa.archive_vintages(since=T("2025-01-01"))
    assert list(got) == [T("2025-12-23")]  # the header date, not the directory's 2025-12-22
    assert sum("Section" in c for c in calls) == 2
    calls.clear()
    again = bea_nipa.archive_vintages(since=T("2025-01-01"))  # second run: from the extract cache
    assert [c for c in calls if "Section" in c] == []
    assert again[T("2025-12-23")]["B852RC"].equals(got[T("2025-12-23")]["B852RC"])


def _vintages():
    q = lambda *ps: pd.PeriodIndex(ps, freq="Q-DEC")  # noqa: E731
    v1 = {"Y034RY": pd.Series([0.5, 0.6], q("2026Q1", "2026Q2")), "B985RY": pd.Series([0.2, 0.21], q("2026Q1", "2026Q2"))}
    v2 = {"Y034RY": pd.Series([0.5, 0.62, 0.86], q("2026Q1", "2026Q2", "2026Q3")),
          "B985RY": pd.Series([0.2, 0.21], q("2026Q1", "2026Q2"))}  # software for 2026Q3 not yet there
    v3 = {"Y034RY": pd.Series([0.5, 0.62, 0.86], q("2026Q1", "2026Q2", "2026Q3")),
          "B985RY": pd.Series([0.2, 0.21, 0.23], q("2026Q1", "2026Q2", "2026Q3"))}
    return {T("2026-07-30"): v1, T("2026-08-26"): v2, T("2026-10-29"): v3}


def test_archive_rows_one_code_and_same_vintage_sum():
    one = bea_nipa.archive_rows("Y034RY", _vintages())
    assert [(str(p), v, k.date().isoformat()) for p, v, k in one.itertuples(index=False)] == [
        ("2026Q1", 0.5, "2026-07-30"), ("2026Q2", 0.6, "2026-07-30"), ("2026Q2", 0.62, "2026-08-26"),
        ("2026Q3", 0.86, "2026-08-26")]
    gross = bea_nipa.archive_rows(("Y034RY", "B985RY"), _vintages())
    got = {(str(p), k.date().isoformat()): v for p, v, k in gross.itertuples(index=False)}
    assert got == {("2026Q1", "2026-07-30"): 0.7, ("2026Q2", "2026-07-30"): 0.81, ("2026Q2", "2026-08-26"): 0.83,
                   ("2026Q3", "2026-10-29"): 1.09}  # 2026Q3 only once both parts exist in the same vintage


def test_all_vintages_adds_current_release_and_rejects_an_older_one(monkeypatch):
    v = _vintages()
    archive = {k: v[k] for k in list(v)[:2]}
    monkeypatch.setattr(bea_nipa, "_VINTAGES", None)
    monkeypatch.setattr(bea_nipa, "archive_vintages", lambda: dict(archive))
    monkeypatch.setattr(bea_nipa, "current_vintage", lambda: (T("2026-10-29"), v[T("2026-10-29")]))
    assert list(bea_nipa.all_vintages()) == list(v)
    monkeypatch.setattr(bea_nipa, "_VINTAGES", None)
    monkeypatch.setattr(bea_nipa, "current_vintage", lambda: (T("2026-07-01"), v[T("2026-10-29")]))
    with pytest.raises(ValueError, match="older than the archive"):
        bea_nipa.all_vintages()


def test_archive_specs_in_catalog():
    specs = catalog.by_key()
    gross = specs["ai_invest_contrib_gross"]
    assert gross.branch == "G5" and gross.freq == "Q" and gross.publish and "Y034RY + B985RY" in gross.source
    assert specs["us_imp_computers_real"].branch == "G6"
    assert {k for k in specs if k.startswith(("us_gdp_contrib", "us_imp_computers"))} == {
        "us_gdp_contrib_info_proc_eq", "us_gdp_contrib_computers", "us_gdp_contrib_software",
        "us_imp_computers_nom", "us_imp_computers_real", "us_imp_computers_contrib_imp"}


# ------------------------------------------------------------------ BLS

FLAT = (
    "series_id        \tyear\tperiod\t       value\tfootnote_codes\n"
    "CUUR0000SEHF01   \t2025\tM09\t     296.887\t\n"
    "CUUR0000SEHF01   \t2025\tM10\t           -\tX\n"
    "CUUR0000SEHF01   \t2025\tM11\t     294.939\t\n"
    "CUUR0000SEHF01   \t2025\tM12\t     295.121\tR\n"
    "CUUR0000SEHF01   \t2025\tM13\t     292.027\t\n"
    "CUSR0000SAH      \t2025\tM11\t     999.000\t\n"
)

ARCHIVE_HTML = """
<ul><li><a href="/bls/history/home.htm">History</a></li></ul>
<ul>
<li><a href="/news.release/archives/cpi_02112026.htm">January 2026 Consumer Price Index</a> (<a href="/news.release/archives/cpi_02112026.pdf">PDF</a>)</li>
<li><a href="/news.release/archives/cpi_01132026.htm">December 2025 Consumer Price Index</a> (<a href="/news.release/archives/cpi_01132026.pdf">PDF</a>)</li>
<li><a href="/news.release/archives/cpi_12182025.htm">November 2025 Consumer Price Index</a> (<a href="/news.release/archives/cpi_12182025.pdf">PDF</a>)</li>
<li>October 2025 Consumer Price Index &ndash; Not published because of 2025 lapse in federal government appropriations</li>
<li><a href="/news.release/archives/cpi_10242025.htm">September 2025 Consumer Price Index</a> (<a href="/news.release/archives/cpi_10242025.pdf">PDF</a>)</li>
<li><a href="/news.release/archives/cpi_02132024.htm">January 2024 Consumer Price Index</a> (<a href="/news.release/archives/cpi_02132024.pdf">PDF</a>)</li>
<li>May 2002 Consumer Price Index (<a aria-label="May 2002 TXT" href="/news.release/history/cpi_06182002.txt">TXT</a>)</li>
</ul>
"""


def _cal():
    return bls.parse_news_archive(ARCHIVE_HTML, "cpi")


def test_parse_flat_skips_annual_and_unavailable():
    out = bls.parse_flat(FLAT, ["CUUR0000SEHF01"])["CUUR0000SEHF01"]
    assert [str(p) for p in out["period"]] == ["2025-09", "2025-11", "2025-12"]
    assert list(out["footnotes"]) == ["", "", "R"]
    with pytest.raises(ValueError, match="lacks series"):
        bls.parse_flat(FLAT, ["PCU518210518210"])


def test_parse_news_archive():
    cal = _cal()
    assert cal[P("2025-11", "M")] == T("2025-12-18")
    assert cal[P("2002-05", "M")] == T("2002-06-18")  # TXT link in the history folder
    assert P("2025-10", "M") not in cal.index  # not published
    assert cal.index.is_monotonic_increasing
    bad = '<li><a href="/news.release/archives/cpi_01132025.htm">December 2025 Consumer Price Index</a></li>'
    with pytest.raises(ValueError, match="days after month end"):
        bls.parse_news_archive(bad, "cpi")


def test_release_date_rules():
    cal = _cal()
    assert bls.release_date(P("2025-11", "M"), cal) == (T("2025-12-18"), True)
    assert bls.release_date(P("2025-10", "M"), cal) == (T("2025-12-18"), False)  # next release
    assert bls.release_date(P("1999-01", "M"), cal) == (T("2002-06-18"), False)  # before the archive
    assert bls.release_date(P("2026-02", "M"), cal) == (None, False)  # not listed yet


def test_date_rows_cpi_nsa():
    df = pd.DataFrame({"period": [P("2025-11", "M"), P("2025-12", "M"), P("2026-02", "M"), P("2001-01", "M")],
                       "value": [1.0, 2.0, 3.0, 4.0], "footnotes": ["", "R", "", ""]})
    out = bls.date_rows(df, "cpi_nsa", _cal(), T("2026-03-11"))
    assert list(zip(out["known_from"], out["source"])) == [
        (T("2025-12-18"), "release"), (T("2026-03-11"), "backfill"),  # R: revised, file date
        (T("2026-03-11"), "backfill"), (T("2002-06-18"), "backfill")]


def test_date_rows_cpi_sa_follows_the_february_revisions():
    df = pd.DataFrame({"period": [P("2019-05", "M"), P("2023-05", "M"), P("2026-01", "M"), P("2025-12", "M")],
                       "value": [1.0, 2.0, 3.0, 4.0], "footnotes": ["", "", "", ""]})
    out = bls.date_rows(df, "cpi_sa", _cal(), T("2026-03-11"))
    assert list(zip(out["known_from"], out["source"])) == [
        (T("2024-02-13"), "backfill"),  # 2019 last revised with the January 2024 CPI (2019 + 5)
        (T("2026-02-11"), "backfill"),  # 2023 revised with the January 2026 CPI, the latest so far
        (T("2026-02-11"), "release"),  # current year: own release
        (T("2026-02-11"), "backfill")]  # first released 2026-01-13, revised 2026-02-11


def test_date_rows_ppi_preliminary_and_final():
    cal = bls.parse_news_archive(ARCHIVE_HTML.replace("Consumer", "Producer").replace("cpi_", "ppi_"), "ppi")
    df = pd.DataFrame({"period": [P("2025-09", "M"), P("2025-10", "M"), P("2025-12", "M")],
                       "value": [1.0, 2.0, 3.0], "footnotes": ["", "", "P"]})
    out = bls.date_rows(df, "ppi", cal, T("2026-02-11"))
    assert list(out["known_from"]) == [
        T("2026-02-11"),  # final: release of 2026-01 (m + 4)
        T("2026-02-11"),  # October 2025 had no release; m + 4 = 2026-02 is not listed yet -> file date
        T("2026-02-11")]  # P: file date
    assert set(out["source"]) == {"backfill"}
    df2 = pd.DataFrame({"period": [P("2025-09", "M")], "value": [1.0], "footnotes": [""]})
    assert bls.date_rows(df2, "ppi", cal, T("2026-12-01"))["known_from"].iloc[0] == T("2026-02-11")


def test_last_modified():
    assert bls.last_modified({"Last-Modified": "Fri, 13 Nov 2026 13:30:00 GMT"}) == T("2026-11-13")
    assert bls.last_modified({}) is None


def test_release_rows_file_date_and_later_fetch_revisions(monkeypatch):
    monkeypatch.setattr(bls, "_CACHE", {})
    monkeypatch.setattr(bls, "_CALENDARS", {})
    flat = ("series_id\tyear\tperiod\tvalue\tfootnote_codes\n"
            "PCU518210518210\t2025\tM09\t124.0\t\n"
            "PCU518210518210\t2026\tM01\t123.8\tP\n")
    page = ARCHIVE_HTML.replace("Consumer", "Producer").replace("cpi_", "ppi_")

    def fake_get(url, source, params=None, save=True, timeout=60, **kw):
        if "news-release" in url:
            return _Resp(text=page)
        return _Resp(text=flat, headers={"Last-Modified": "Thu, 12 Feb 2026 13:30:00 GMT"})

    monkeypatch.setattr(http, "get", fake_get)
    rows = bls.release_rows("PCU518210518210")
    assert list(rows["known_from"]) == [T("2026-02-11"), T("2026-02-12")]  # P: Last-Modified is later
    spec = catalog.by_key()["us_ppi_data_processing_m"]
    table = observations.new_rows(spec, rows, pd.DataFrame(columns=observations.COLUMNS), fetched_at=T("2026-02-20").date())
    assert len(table) == 2 and set(table["source"]) == {"backfill"}
    # next fetch: same file -> nothing new; a revised preliminary value -> a revision dated by the fetch
    assert observations.new_rows(spec, rows, table, fetched_at=T("2026-02-27").date()).empty
    later = rows.copy()
    later.loc[1, "value"] = 124.5
    later.loc[1, "known_from"] = T("2026-03-12")
    rev = observations.new_rows(spec, later, table, fetched_at=T("2026-03-13").date())
    assert list(zip(rev["period"], rev["value"], rev["source"], rev["known_from"])) == [
        ("2026-01", 124.5, "revision", T("2026-03-13"))]


def test_bls_specs_in_catalog():
    specs = catalog.by_key()
    assert specs["us_ppi_data_processing_m"].branch == "G4"
    assert {specs[k].branch for k in ("us_cpi_electricity_nsa_m", "us_cpi_electricity_sa_m",
                                      "us_ppi_elec_commercial_m")} == {"G7"}
    assert all(specs[k].publish and specs[k].freq == "M" for k in ("us_cpi_electricity_nsa_m",
                                                                     "us_ppi_data_processing_m"))


def test_bls_hosts_get_the_declared_contact_user_agent(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "ai-rollout-tracker contact@example.org")
    assert http.user_agent("download.bls.gov") == "ai-rollout-tracker contact@example.org"
    assert http.user_agent("www.bls.gov") == "ai-rollout-tracker contact@example.org"
    assert http.user_agent("apps.bea.gov") == http.DEFAULT_UA
