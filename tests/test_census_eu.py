"""Parsers and known_from rules for track I3 (Census BTOS/C30/trade, BEA, ALFRED, Eurostat, SCB). No network."""

from __future__ import annotations

import io
import json
import warnings
from datetime import date

import numpy as np
import pandas as pd
import pytest

from ai_tracker import catalog, observations, publication, warehouse
from ai_tracker.series import bea_nipa as bea_series
from ai_tracker.series import census_c30 as c30_series
from ai_tracker.series import census_trade as trade_series
from ai_tracker.sources import alfred, bea_nipa, census_btos, census_c30, census_trade, eurostat_ai, scb_ai


def xlsx(sheets: dict[str, pd.DataFrame], header: bool = True) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, df in sheets.items():
            df.to_excel(w, sheet_name=name, index=False, header=header)
    return buf.getvalue()


def spec(key="s", freq="M", lag=10) -> catalog.Spec:
    return catalog.Spec(key=key, branch="G3", label=key, unit="x", freq=freq, source="test",
                        fetch=lambda: pd.Series(dtype=float), lag_days=lag, license="unverified")


# ------------------------------------------------------------------ fortnights ("2W")


def test_fortnight_ordinal_is_consecutive_across_53_week_year():
    # BTOS collection-period ends: 202525, 202526, 202601 and 202625, 202626 (21 days), 202701, 202702
    ends = ["2025-12-14", "2025-12-28", "2026-01-11", "2026-12-13", "2027-01-03", "2027-01-17", "2027-01-31"]
    ords = observations.fortnight_ordinal(observations.to_periods(ends, "2W"))
    assert list(np.diff(ords[:3])) == [1, 1] and list(np.diff(ords[3:])) == [1, 1, 1]
    # smpdt = ISO year * 26 + fortnight - 1: 202319 ends 2023-09-24
    assert observations.fortnight_ordinal(observations.to_periods(["2023-09-24"], "2W"))[0] == 2023 * 26 + 18


def test_no_gaps_on_fortnights_catches_a_missing_cycle():
    s = spec("b", freq="2W", lag=4)
    ends = pd.to_datetime(["2023-09-24", "2023-10-08", "2023-10-22"])
    full = pd.DataFrame({"period": ends, "value": [1.0, 2.0, 3.0], "known_from": ends + pd.Timedelta(days=4)})
    t = observations.new_rows(s, full, observations._empty(), date(2026, 1, 1))
    assert warehouse.run_checks(warehouse.connect(t, [s]))["no_gaps"].empty
    t = observations.new_rows(s, full.drop(index=1), observations._empty(), date(2026, 1, 1))
    assert len(warehouse.run_checks(warehouse.connect(t, [s]))["no_gaps"]) == 1


# ------------------------------------------------------------------ release-dated revisions


def test_release_dated_value_change_becomes_revision_at_fetch_date():
    s = spec("r", freq="2W")
    rows = pd.DataFrame({"period": ["2026-11-15"], "value": [25.0], "known_from": ["2026-11-19"]})
    t = observations.new_rows(s, rows, observations._empty(), date(2026, 11, 20))
    rev = observations.new_rows(s, rows.assign(value=25.4), t, date(2026, 12, 1))
    assert list(rev["source"]) == ["revision"] and rev["known_from"].iloc[0] == pd.Timestamp("2026-12-01")
    t = pd.concat([t, rev], ignore_index=True)
    assert observations.as_of("r", "2026-11-30", t).iloc[0] == 25.0
    assert observations.as_of("r", "2026-12-01", t).iloc[0] == 25.4
    assert observations.new_rows(s, rows.assign(value=25.4), t, date(2026, 12, 2)).empty


def test_older_vintages_are_not_mistaken_for_revisions():
    s = spec("v", freq="M")
    rows = pd.DataFrame({"period": ["2026-01", "2026-01"], "value": [1.0, 1.5],
                         "known_from": ["2026-02-15", "2026-03-15"]})
    t = observations.new_rows(s, rows, observations._empty(), date(2026, 4, 1))
    assert observations.new_rows(s, rows, t, date(2026, 4, 2)).empty


# ------------------------------------------------------------------ BTOS


def _btos_files(q7_text_new: str = "did this business use Super Intelligence or SI (formerly referred to as "
                "Artificial Intelligence or AI) in any of its business functions?") -> tuple[bytes, bytes]:
    cycles = ["202702", "202622", "202621", "202524", "202523", "202520", "202319"]
    yes = ["30.0%", "25.0%", "24.6%", "17.3%", ".", ".", "."]
    q28 = ["31.0%", "28.2%", "28.6%", "21.1%", ".", ".", "."]
    est = pd.DataFrame([[7, q7_text_new, 1, "Yes", *yes], [7, q7_text_new, 2, "No", *["50.0%"] * 7],
                        [28, "next six months ... " + q7_text_new, 1, "Yes", *q28]],
                       columns=["Question ID", "Question", "Answer ID", "Answer", *cycles])
    se = est.copy()
    se[cycles] = [["0.6%"] * 4 + ["."] * 3] * 3
    dates = pd.DataFrame({
        "Sample Year": [2, None, None, None, "SHUTDOWN", 4, None, None],
        "Smpdt": [202319, 202520, 202523, 202524, 202521, 202621, 202622, 202702],
        "Col End": pd.to_datetime(["2023-09-24", "2025-10-05", "2025-11-16", "2025-11-30", "2025-10-19",
                                   "2026-10-18", "2026-11-01", "2027-01-31"]),
        "Publication Date": pd.to_datetime(["2023-09-28", "2025-10-09", None, "2025-12-04", None, "2026-10-22",
                                            "2026-11-05", "2027-02-04"]),
    })
    national = xlsx({"Response Estimates": est, "Response Standard Errors": se,
                     "Collection and Reference Dates": dates})
    old_text = "did this business use Artificial Intelligence (AI) in producing goods or services?"
    core = pd.DataFrame([[7, old_text, 1, "Yes", "10.0%", "3.7%"], [24, old_text, 1, "Yes", "14.0%", "6.3%"]],
                        columns=["Question ID", "Question", "Answer ID", "Answer", "202520", "202319"])
    ai_core = xlsx({"National Estimates": core, "National SE": core.assign(**{"202520": "0.2%", "202319": "S"})})
    return national, ai_core


def test_btos_regimes_are_separate_and_dated_by_publication():
    national, ai_core = _btos_files()
    v1 = census_btos.build(national, ai_core, "use", "v1")
    assert list(v1["value"]) == [3.7, 10.0]
    # 202520 is scheduled 2025-10-09, inside the 2025 funding lapse: known from the day after the lapse (R1 3.6)
    assert list(v1["known_from"]) == [pd.Timestamp("2023-09-28"), pd.Timestamp("2025-11-13")]
    assert list(v1["period"]) == [pd.Timestamp("2023-09-24"), pd.Timestamp("2025-10-05")]
    v2 = census_btos.build(national, ai_core, "use", "v2")
    assert list(v2["value"]) == [17.3, 24.6]  # 202524 and 202621; shutdown '.' dropped
    with pytest.warns(UserWarning, match="202702"):
        v3 = census_btos.build(national, ai_core, "use", "v3")
    assert list(v3["value"]) == [25.0]  # 202702 is after the last reviewed regime: not stored
    expect = census_btos.build(national, ai_core, "expect", "v2")
    assert list(expect["value"]) == [21.1, 28.6]
    se_v1 = census_btos.build(national, ai_core, "use", "v1", stat="se")
    assert list(se_v1["value"]) == [0.2]  # 'S' (suppressed) dropped


def test_btos_publication_scheduled_in_a_funding_lapse_is_moved_past_it(monkeypatch):
    assert census_btos.release_date(202520, pd.Timestamp("2025-10-09")) == pd.Timestamp("2025-11-13")
    assert census_btos.release_date(202519, pd.Timestamp("2025-09-25")) == pd.Timestamp("2025-09-25")
    assert census_btos.release_date(202524, pd.Timestamp("2025-12-04")) == pd.Timestamp("2025-12-04")
    monkeypatch.setitem(census_btos.PUBLISHED, 202520, "2025-11-20")  # a documented date wins
    assert census_btos.release_date(202520, pd.Timestamp("2025-10-09")) == pd.Timestamp("2025-11-20")


def test_btos_schedule_is_logged_on_every_fetch(tmp_path):
    national, _ = _btos_files()
    path = tmp_path / "schedule_log.parquet"
    dates = census_btos.parse_dates(national)
    census_btos.log_schedule(dates, pd.Timestamp("2026-11-23 10:00"), path)
    census_btos.log_schedule(dates, pd.Timestamp("2026-11-23 18:00"), path)  # same day: replaced, not doubled
    later = dates.assign(published=dates["published"] + pd.Timedelta(days=1))
    log = census_btos.log_schedule(later, pd.Timestamp("2026-12-07"), path)
    assert len(log) == 2 * len(dates)
    assert set(log["fetched_at"]) == {pd.Timestamp("2026-11-23"), pd.Timestamp("2026-12-07")}
    one = log[log["smpdt"] == 202520].sort_values("fetched_at")["published"]
    assert list(one) == [pd.Timestamp("2025-10-09"), pd.Timestamp("2025-10-10")]


def test_btos_wording_change_is_not_silently_spliced():
    national, ai_core = _btos_files(q7_text_new="did this business use Artificial Intelligence (AI) in any of "
                                                "its business functions?")
    with pytest.raises(ValueError, match="wording"):
        census_btos.build(national, ai_core, "use", "v2")


def test_btos_specs_are_fortnightly_and_release_dated():
    btos = [s for s in catalog.ALL if s.key.startswith("btos_ai_")]
    assert len(btos) == 12 and {s.freq for s in btos} == {"2W"}
    assert not any(s.publish for s in btos if s.key.endswith("_se"))


# ------------------------------------------------------------------ C30


def _c30_file() -> bytes:
    rows = [["Value of Private Construction Put in Place - Seasonally Adjusted Annual Rate", None, None],
            ["(Millions of dollars.)", None, None], [None, None, None],
            ["Date", "Total\n_x000D_Private Construction1", "Data center"],
            ["Sep-26p", 1639330, 96462], ["Aug-26r", 1680267, 88815], ["Sep-25", 1500000, 50000],
            ["Dec-13", 1000000, None], [None, None, None],
            ["Source: U.S. Census Bureau, Construction Spending, November 2, 2026. Additional", None, None]]
    return xlsx({"Private SA": pd.DataFrame(rows)}, header=False)


def test_c30_parse_flags_and_release_line():
    df = census_c30.parse(_c30_file())
    assert list(df.index.astype(str)) == ["2025-09", "2026-08", "2026-09"]
    assert list(df["flag"]) == ["", "r", "p"] and df.loc[pd.Period("2026-09", "M"), "value"] == 96462
    assert census_c30.release_note(_c30_file()) == "November 2, 2026"
    with pytest.raises(ValueError):
        census_c30.parse(_c30_file(), column="Hospital")


def test_c30_known_from_uses_documented_late_releases():
    s = catalog.by_key()["us_constr_datacenter"]
    p = observations.to_periods(["2025-09", "2026-09"], "M")
    kf = publication.known_from(s.key, p, s.lag_days)
    assert kf[0] == pd.Timestamp("2026-01-21")  # shutdown: released with October data
    assert kf[1] == pd.Timestamp("2026-09-30") + pd.Timedelta(days=c30_series.LAG_DAYS)
    assert publication.LATE_RELEASES["us_constr_datacenter_nsa"] == c30_series.LATE


@pytest.mark.parametrize("module", [c30_series, trade_series, bea_series])
def test_late_releases_are_later_than_the_lag(module):
    for key in (s.key for s in module.SPECS):
        freq = catalog.by_key()[key].freq
        for period, d in module.LATE.items():
            end = publication.period_end(observations.to_periods([period], freq))[0]
            assert pd.Timestamp(d) > end + pd.Timedelta(days=module.LAG_DAYS), (key, period)


# ------------------------------------------------------------------ ALFRED


def test_alfred_vintages_to_release_rows():
    html = '<option value="lin">Levels</option><option value="2026-10-16">x</option><option value="2026-09-17">'
    assert alfred.parse_vintage_dates(html) == ["2026-09-17", "2026-10-16"]
    csv = ("observation_date,IPG3344S_20260917,IPG3344S_20261016,IPG3344S_20261117\n"
           "2026-07-01,100.0,100.5,100.5\n2026-08-01,101.0,101.0,101.2\n2026-09-01,,102.0,102.0\n"
           "2026-10-01,,,.\n")
    wide = alfred.parse_vintage_csv(csv, "IPG3344S")
    rows = alfred.release_rows(wide)
    got = {(str(r.period.date()), str(r.known_from.date())): r.value for r in rows.itertuples()}
    assert got == {("2026-07-01", "2026-09-17"): 100.0, ("2026-08-01", "2026-09-17"): 101.0,
                   ("2026-07-01", "2026-10-16"): 100.5, ("2026-09-01", "2026-10-16"): 102.0,
                   ("2026-08-01", "2026-11-17"): 101.2}
    first = alfred.first_release(wide)
    assert first[pd.Timestamp("2026-09-01")] == pd.Timestamp("2026-10-16") and len(first) == 3
    with pytest.raises(ValueError):
        alfred.parse_vintage_csv(csv.replace("IPG3344S_20260917", "OTHER_20260917"), "IPG3344S")


# ------------------------------------------------------------------ BEA, trade


def test_bea_flat_file_parse():
    text = ('%SeriesCode,Period,Value\nA001RC,1947Q1,"244,142"\nB985RC,2026Q2,"612,345"\n'
            'B985RC,2026Q3,"620,001"\nA679RC,2026Q3,"1,001,000"\n')
    out = bea_nipa.parse_data(text, {"B985RC", "A679RC"})
    assert list(out["B985RC"].index.astype(str)) == ["2026Q2", "2026Q3"] and out["B985RC"].iloc[-1] == 620001
    assert out["A679RC"].iloc[0] == 1001000
    with pytest.raises(ValueError):
        bea_nipa.parse_data("code,when,x\n", {"A"})


def test_trade_drops_unpublished_months():
    cols = ["year", "CTY_CODE", "CTYNAME"] + [f"I{m}" for m in census_trade.MONTHS]
    df = pd.DataFrame([[2025, "5830", "Taiwan", *range(1, 13)], [2026, "5830", "Taiwan", *range(1, 10), 0, 0, 0],
                       [2026, "5800", "Korea, South", *[5] * 12]], columns=cols)
    s = census_trade.parse(xlsx({"country": df}), "5830")
    assert len(s) == 21 and str(s.index[-1]) == "2026-09" and s.iloc[-1] == 9
    with pytest.raises(ValueError):
        census_trade.parse(xlsx({"country": df}), "9999")


# ------------------------------------------------------------------ Eurostat, SCB


def _jsonstat() -> dict:
    return {"id": ["indic_is", "geo", "time"], "size": [1, 2, 3],
            "dimension": {"indic_is": {"category": {"index": {"E_AI_TANY": 0}}},
                          "geo": {"category": {"index": {"EU27_2020": 0, "SE": 1}}},
                          "time": {"category": {"index": {"2021": 0, "2023": 1, "2024": 2}}}},
            "value": {"0": 7.6, "1": 8.1, "2": 13.5, "3": 6.1, "4": 10.4, "5": 25.1}, "status": {"4": "b"}}


def test_eurostat_jsonstat_parse_and_break_rule():
    long = eurostat_ai.parse_jsonstat(json.loads(json.dumps(_jsonstat())))
    assert len(long) == 6 and long.loc[long["flag"] == "b", "time"].tolist() == ["2023"]
    se = eurostat_ai.series(long, "SE", "E_AI_TANY", 2023)
    assert list(se.index.astype(str)) == ["2023", "2024"] and se.iloc[0] == 10.4  # break at the start is fine
    with pytest.raises(ValueError, match="break"):
        eurostat_ai.series(long, "SE", "E_AI_TANY", 2021)  # break inside the series -> must be split
    bad = _jsonstat() | {"size": [1, 2, 4]}
    with pytest.raises(ValueError):
        eurostat_ai.parse_jsonstat(bad)


def test_scb_csv_parse():
    text = ('"TypAvTeknik","Redovisningsgrupp","000007JC 2021","000007JC 2023","000007JC 2025","000007JD 2025"\n'
            '"0080","Tot250",..,10,35,2\n"0080","0-9",..,..,17,2\n')
    long = scb_ai.parse_csv(text)
    s = scb_ai.share(long, {"TypAvTeknik": "0080", "Redovisningsgrupp": "Tot250"}, "000007JC")
    assert list(s.index.astype(str)) == ["2023", "2025"] and list(s) == [10.0, 35.0]


def test_annual_known_from_rules():
    by = catalog.by_key()
    p = observations.to_periods(["2026"], "A")
    assert publication.known_from("x", p, by["scb_ai_ent_se_nace21"].lag_days)[0] == pd.Timestamp("2026-11-11")
    assert publication.known_from("x", p, by["eu_ai_ent_se"].lag_days)[0] == pd.Timestamp("2027-01-31")
    assert publication.known_from("x", p, by["scb_ai_ent_se"].lag_days)[0] == pd.Timestamp("2026-12-31")


def test_new_series_are_valid_and_have_quoted_licences():
    ours = [s for s in catalog.ALL if s.source.split()[0] in ("US", "Eurostat", "SCB,", "BEA", "Federal", "Census")]
    assert len(ours) >= 28
    assert all(s.license != "unverified" and '"' in s.license for s in ours)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert catalog.validate() == []
