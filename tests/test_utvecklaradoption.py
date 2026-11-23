"""Developer adoption (track B1): npm, pypistats and PyPI BigQuery parsing, weekly aggregation, known_from
(fixtures, no network)."""

from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

from ai_tracker import catalog, http, observations
from ai_tracker.sources import download_counts, npm, pypi_bq, pypistats


def _days(start: str, values) -> pd.Series:
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="D"), dtype=float)


# ------------------------------------------------------------------ weekly aggregation


def test_weekly_complete_weeks_only_and_lag():
    # Monday 2026-11-02 .. Sunday 2026-11-22 (three weeks), fetched Monday 2026-11-23
    d = _days("2026-11-02", [10.0] * 21)
    w = download_counts.weekly(d, date(2026, 11, 23), lag_days=2)
    # the week ending 2026-11-22 is not known until 2026-11-24
    assert [str(p) for p in w.index] == ["2026-11-02/2026-11-08", "2026-11-09/2026-11-15"]
    assert (w == 70).all()
    w2 = download_counts.weekly(d, date(2026, 11, 24), lag_days=2)
    assert len(w2) == 3


def test_weekly_drops_week_beyond_coverage():
    d = _days("2026-11-02", [10.0] * 12)  # ends Friday 2026-11-13
    w = download_counts.weekly(d, date(2026, 12, 31), lag_days=2)
    assert len(w) == 1


def test_weekly_gap_day_filled_from_weekday_profile():
    week = [100, 100, 100, 100, 100, 50, 50]  # weekdays 100, weekend 50
    vals = week * 8 + [100, np.nan, 100, 100, 100, 50, 50]
    d = _days("2026-01-05", vals)  # Monday
    w = download_counts.weekly(d, date(2026, 12, 31), lag_days=2)
    assert len(w) == 9
    # profile from the 8 prior complete weeks: Tuesday is 100/600 of the week -> 500 / (500/600) = 600
    assert w.iloc[-1] == 600
    assert (w.iloc[:8] == 600).all()


def test_weekly_gap_without_history_uses_flat_share_and_min_days():
    d = _days("2026-01-05", [1] * 7 + [70, np.nan, 70, 70, 70, 70, 70]
              + [10, np.nan, np.nan, np.nan, np.nan, 10, 10] + [2] * 7)
    w = download_counts.weekly(d, date(2026, 12, 31), lag_days=2)
    assert list(w) == [7, 490, 14]  # 420 * 7 / 6; the third week has 3 days only: dropped (a gap)


def test_weekly_never_starts_with_an_estimated_week():
    d = _days("2026-01-06", [10.0] * 13)  # coverage starts on a Tuesday
    w = download_counts.weekly(d, date(2026, 12, 31), lag_days=2)
    assert [str(p) for p in w.index] == ["2026-01-12/2026-01-18"]


def test_weekly_start_trims_leading_zeros_and_explicit_start():
    d = _days("2026-01-05", [0] * 9 + [5] * 12)  # first download Wednesday 2026-01-14
    w = download_counts.weekly(d, date(2026, 12, 31), lag_days=2)
    assert str(w.index[0]) == "2026-01-12/2026-01-18" and w.iloc[0] == 25
    w2 = download_counts.weekly(_days("2026-01-05", [3] * 21), date(2026, 12, 31), 2, start=date(2026, 1, 12))
    assert str(w2.index[0]) == "2026-01-12/2026-01-18" and len(w2) == 2


# ------------------------------------------------------------------ npm


def _npm_payload(package, start, values):
    days = pd.date_range(start, periods=len(values), freq="D")
    return {"start": str(days[0].date()), "end": str(days[-1].date()), "package": package,
            "downloads": [{"downloads": v, "day": str(d.date())} for d, v in zip(days, values)]}


def test_npm_parse_and_ranges():
    s = npm.parse(_npm_payload("react", "2026-01-01", [1, 2, 3]))
    assert list(s) == [1, 2, 3] and s.index[0] == pd.Timestamp("2026-01-01")
    r = npm._ranges(date(2015, 1, 10), date(2026, 11, 22))
    assert r[0][0] == date(2015, 1, 10) and r[-1][1] == date(2026, 11, 22)
    assert all((b - a).days < 540 for a, b in r)  # API limit: 18 months
    assert all((r[i + 1][0] - r[i][1]).days == 1 for i in range(len(r) - 1))


def test_npm_gap_days_need_every_active_control_at_zero():
    react = _days("2026-01-01", [5, 0, 5, 5, 0])
    express = _days("2026-01-01", [0, 0, 0, 7, 0])  # inactive until day 4 (API returns 0 before)
    gaps = npm.gap_days([react, express])
    assert [str(d.date()) for d in gaps] == ["2026-01-02", "2026-01-05"]
    other = _days("2026-01-01", [9, 9, 9, 0, 9])  # a real zero of one package is not a gap
    assert npm.gap_days([react, other]).empty


def test_npm_weekly_from_fixture(monkeypatch):
    monday = "2026-10-05"
    react = [100] * 9 + [0] + [100] * 11  # 2026-10-14 is an npm gap day (react and express both 0)
    express = [50] * 9 + [0] + [50] * 11
    pkg = [10] * 9 + [0] + [10] * 11
    data = {"react": react, "express": express, "openai": pkg}
    monkeypatch.setattr(npm, "daily_raw", lambda p, since, until: _days(monday, data[p]))
    w = npm.weekly("openai", date(2026, 10, 1), today=date(2026, 10, 27))
    assert list(w.round()) == [70, 70, 70]  # the gap day is filled, not counted as 0


# ------------------------------------------------------------------ pypistats


PYPISTATS = {"data": [
    {"category": "with_mirrors", "date": "2026-11-21", "downloads": 120},
    {"category": "without_mirrors", "date": "2026-11-21", "downloads": 100},
    {"category": "with_mirrors", "date": "2026-11-22", "downloads": 130}],
    "package": "anthropic", "type": "overall_downloads"}


def test_pypistats_parse_with_mirrors():
    s = pypistats.parse(PYPISTATS)
    assert list(s) == [120, 130]


def test_pypistats_stored_newest_fetch_wins(tmp_path, monkeypatch):
    monkeypatch.setattr(http, "RAW_DIR", tmp_path)
    for day, value in (("2026-11-16", 1), ("2026-11-23", 2)):
        p = http.raw_path("pypistats", pypistats.url("anthropic"), day=date.fromisoformat(day))
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps({"data": [{"category": "with_mirrors", "date": "2026-11-15", "downloads": value},
                                          {"category": "with_mirrors", "date": day, "downloads": 9}]}))
    s = pypistats.stored("anthropic")
    assert s[pd.Timestamp("2026-11-15")] == 2 and len(s) == 3


# ------------------------------------------------------------------ PyPI BigQuery


def test_bq_sql_reads_only_needed_columns():
    q = pypi_bq.sql(date(2016, 1, 1), date(2017, 1, 1))
    assert "file.project" in q and "timestamp" in q
    assert "details" not in q and "SELECT *" not in q
    assert "timestamp >= TIMESTAMP('2016-01-01') AND timestamp < TIMESTAMP('2017-01-01')" in q
    for p in pypi_bq.PROJECTS:
        assert f"'{p}'" in q


def test_bq_year_chunks_and_monday():
    ch = pypi_bq.year_chunks(date(2016, 1, 1), date(2026, 11, 23))
    assert ch[0] == (date(2016, 1, 1), date(2017, 1, 1)) and ch[-1] == (date(2026, 1, 1), date(2026, 11, 23))
    assert pypi_bq.last_monday(date(2026, 11, 25)) == date(2026, 11, 23)
    assert pypi_bq.last_monday(date(2026, 11, 23)) == date(2026, 11, 23)


def test_bq_csv_body_strips_status_lines():
    assert pypi_bq._csv_body("Waiting on bqjob ... DONE\nday,project,downloads\n2026-01-01,mcp,3\n") \
        == "day,project,downloads\n2026-01-01,mcp,3\n"
    with pytest.raises(RuntimeError):
        pypi_bq._csv_body("Error in query string")


def _write_bq(root, fetched, start, end, rows):
    d = root / fetched
    d.mkdir(parents=True, exist_ok=True)
    body = "day,project,downloads\n" + "".join(f"{a},{b},{c}\n" for a, b, c in rows)
    (d / f"daily_{start}_{end}.csv").write_text(body)


def test_bq_load_daily_newest_fetch_gaps_and_zeros(tmp_path):
    _write_bq(tmp_path, "2026-11-01", "2026-10-01", "2026-10-04",
              [("2026-10-01", "requests", 100), ("2026-10-01", "mcp", 5), ("2026-10-02", "mcp", 6),
               ("2026-10-03", "requests", 100), ("2026-10-03", "mcp", 7)])
    _write_bq(tmp_path, "2026-11-08", "2026-10-03", "2026-10-05",
              [("2026-10-03", "requests", 110), ("2026-10-04", "requests", 100)])
    wide, covered = pypi_bq.load_daily(tmp_path)
    assert list(covered.strftime("%d")) == ["01", "02", "03", "04"]
    assert wide.loc["2026-10-01", "mcp"] == 5 and wide.loc["2026-10-01", "openai"] == 0  # absent row = 0
    assert wide.loc["2026-10-02"].isna().all()  # no `requests` row: a gap in the table
    assert wide.loc["2026-10-03", "requests"] == 110 and wide.loc["2026-10-03", "mcp"] == 0  # newer fetch wins
    assert pypi_bq.incremental_window(tmp_path, date(2026, 10, 30)) == (date(2026, 10, 5), date(2026, 10, 26))
    assert pypi_bq.incremental_window(tmp_path / "none", date(2026, 10, 30)) is None


def test_bq_execute_refuses_over_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(pypi_bq, "dry_run_bytes", lambda q: int(200e9))
    ran = []
    monkeypatch.setattr(pypi_bq, "run_query", lambda q, cap: ran.append(cap))
    with pytest.raises(RuntimeError, match="above cap"):
        pypi_bq.execute([(date(2016, 1, 1), date(2017, 1, 1)), (date(2017, 1, 1), date(2018, 1, 1))],
                        tmp_path, cap_gb=300)
    assert ran == [] and json.loads((tmp_path / "bytes.json").read_text())["refused"]


def test_bq_execute_records_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(pypi_bq, "dry_run_bytes", lambda q: int(1e9))
    monkeypatch.setattr(pypi_bq, "run_query", lambda q, cap: ("day,project,downloads\n2016-01-01,numpy,1\n",
                                                             {"job_id": "x", "processed": 9e8, "billed": 9e8}))
    rec = pypi_bq.execute([(date(2016, 1, 1), date(2017, 1, 1))], tmp_path, cap_gb=2)
    log = json.loads((tmp_path / "bytes.json").read_text())
    assert rec[0]["rows"] == 1 and log["billed_gb"] == 0.9 and not log["refused"]
    assert (tmp_path / "daily_2016-01-01_2017-01-01.csv").exists()


# ------------------------------------------------------------------ catalog and known_from


def _b1_specs():
    return [s for s in catalog.ALL if s.key.startswith(("g3_npm_", "g3_pypi_"))]


def test_b1_specs_valid():
    specs = _b1_specs()
    assert len(specs) >= 20 and not catalog.validate(specs)
    assert all(s.branch == "G3" and s.freq == "W" for s in specs)
    assert all(not s.publish for s in specs if s.key.startswith("g3_npm_"))  # npm licence unverified


def test_b1_known_from_is_sunday_plus_lag():
    spec = next(s for s in _b1_specs() if s.key == "g3_npm_openai_w")
    values = pd.Series([70.0, 80.0], index=pd.PeriodIndex(["2026-11-08", "2026-11-15"], freq="W-SUN"))
    rows = observations.new_rows(spec, values, observations._empty(), fetched_at=date(2026, 11, 23))
    assert list(rows["known_from"]) == [pd.Timestamp("2026-11-10"), pd.Timestamp("2026-11-17")]
    assert set(rows["source"]) == {"backfill"}
