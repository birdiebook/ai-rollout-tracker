"""Scheduled jobs: origin days, immutability of live forecasts, scorecard against first vintage, SEC requirement.

Synthetic fixtures only, no network.
"""

from __future__ import annotations

import json
import subprocess

import numpy as np
import pandas as pd
import pytest

from ai_tracker import config, observations, pipeline, warehouse
from ai_tracker.nowcast import n1
from ai_tracker.nowcast_n2 import __main__ as n2_live
from ai_tracker.nowcast_n2 import engine as n2

TS = pd.Timestamp


# ------------------------------------------------------------------ origin days


def test_n2_origin_is_day_5_for_previous_month():
    assert pipeline.n2_due("2026-12-05") == pipeline.Due("n2", TS("2026-12-05"), "2026-11")
    assert pipeline.n2_due("2027-01-05").period == "2026-12"  # year wrap
    assert pipeline.n2_due("2027-03-05").period == "2027-02"  # after a 28-day month
    for day in ("2026-12-04", "2026-12-06", "2026-11-23"):
        assert pipeline.n2_due(day) is None


@pytest.mark.parametrize("day,quarter", [
    ("2026-04-20", "2026Q1"),  # 31 Mar + 20
    ("2026-07-20", "2026Q2"),  # 30 Jun + 20 (30-day month)
    ("2026-10-20", "2026Q3"),  # 30 Sep + 20
    ("2027-01-20", "2026Q4"),  # 31 Dec + 20, year wrap
    ("2028-04-20", "2028Q1"),  # leap year
])
def test_n1_origin_is_quarter_end_plus_20(day, quarter):
    d = pipeline.n1_due(day)
    assert d == pipeline.Due("n1", TS(day), quarter)
    assert n1.origin_for(pd.Period(quarter, freq="Q-DEC")) == TS(day)


@pytest.mark.parametrize("day", ["2026-04-19", "2026-04-21", "2026-07-19", "2026-07-21", "2026-05-20",
                                 "2026-03-20", "2026-12-20", "2027-01-19", "2027-01-21"])
def test_n1_not_due_on_other_days(day):
    assert pipeline.n1_due(day) is None


def test_weekend_origins_are_kept_not_shifted():
    assert TS("2026-12-05").day_name() == "Saturday" and pipeline.n2_due("2026-12-05")
    assert TS("2025-04-20").day_name() == "Sunday" and pipeline.n1_due("2025-04-20").period == "2025Q1"
    assert TS("2024-10-20").day_name() == "Sunday" and pipeline.n1_due("2024-10-20").period == "2024Q3"
    # Monday after is not an origin
    assert pipeline.n1_due("2025-04-21") is None and pipeline.n2_due("2026-12-07") is None


def test_one_year_has_12_n2_and_4_n1_origins_never_on_the_same_day():
    days = pd.date_range("2026-01-01", "2026-12-31")
    found = [(day, d.nowcast) for day in days for d in pipeline.due(day)]
    assert sum(k == "n2" for _, k in found) == 12 and sum(k == "n1" for _, k in found) == 4
    assert len({day for day, _ in found}) == 16


def test_due_cli_writes_step_outputs(tmp_path, monkeypatch, capsys):
    out = tmp_path / "gh_out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setattr(pipeline, "FORECASTS", tmp_path / "forecasts")
    assert pipeline.main(["due", "--today", "2026-12-05"]) == 0
    assert out.read_text() == "due=true\nnowcasts=n2\n"
    (tmp_path / "forecasts" / "n2").mkdir(parents=True)
    (tmp_path / "forecasts" / "n2" / "2026-11.json").write_text("{}")
    out.unlink()
    pipeline.main(["due", "--today", "2026-12-05"])
    assert out.read_text() == "due=false\nnowcasts=\n"
    out.unlink()
    pipeline.main(["due", "--today", "2026-12-06"])
    assert out.read_text() == "due=false\nnowcasts=\n"


# ------------------------------------------------------------------ N2 fixture


def _rows(series, freq, periods, values, known_from, source="release"):
    return pd.DataFrame({"series": series, "freq": freq, "period": [str(p) for p in periods],
                         "value": np.asarray(values, dtype=float), "known_from": pd.to_datetime(known_from),
                         "source": source, "fetched_at": TS("2026-11-23")})


def n2_table(last="2019-11"):
    """TSMC filed day 10 of m+1, imports 41 days after month end, through `last` (target = the month after)."""
    rng = np.random.default_rng(3)
    months = pd.period_range("2007-01", last, freq="M")
    tsmc = 1e5 * np.exp(np.cumsum(0.01 + 0.05 * rng.standard_normal(len(months))))
    imp = 1e3 * np.exp(np.cumsum(0.005 + 0.03 * rng.standard_normal(len(months))))
    return pd.concat([
        _rows(n2.TARGET, "M", months, tsmc, [(p + 1).start_time + pd.Timedelta(days=9) for p in months]),
        _rows("us_imports_tw_m", "M", months, imp, months.end_time.normalize() + pd.Timedelta(days=41), "backfill"),
    ], ignore_index=True)


ORIGIN_N2 = TS("2020-01-05")  # target 2019-12; the 2019-12 6-K comes 2020-01-10


# ------------------------------------------------------------------ live runs and immutability


def test_live_writes_once_and_second_run_is_a_noop(tmp_path):
    table = n2_table()
    d = pipeline.n2_due(ORIGIN_N2)
    path = pipeline.run_live(d, tmp_path, table, refresh=False, today=ORIGIN_N2)
    assert path == tmp_path / "n2" / "2019-12.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["origin"] == "2020-01-05" and data["month"] == "2019-12"
    assert all(TS(i["known_from"]) <= ORIGIN_N2 for i in data["inputs"])
    before = path.read_bytes()
    assert pipeline.run_live(d, tmp_path, table, refresh=False, today=ORIGIN_N2) is None
    assert path.read_bytes() == before
    # the outcome arrives later: still no rewrite
    later = pd.concat([table, _rows(n2.TARGET, "M", [pd.Period("2019-12", "M")], [1.0], ["2020-01-10"])])
    assert pipeline.run_live(d, tmp_path, later, refresh=False, today=ORIGIN_N2) is None
    assert path.read_bytes() == before


def test_live_wrapper_writes_scorecard_and_skips_non_origin_days(tmp_path, monkeypatch):
    out = tmp_path / "gh_out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    table = n2_table()
    assert pipeline.live(root=tmp_path, table=table, refresh=False, today="2020-01-06") == []
    assert not (tmp_path / "n2").exists() and not (tmp_path / "SCORECARD.md").exists()
    written = pipeline.live(root=tmp_path, table=table, refresh=False, today=ORIGIN_N2)
    assert written == [tmp_path / "n2" / "2019-12.json"]
    assert "2019-12" in (tmp_path / "SCORECARD.md").read_text(encoding="utf-8")
    assert pipeline.live(root=tmp_path, table=table, refresh=False, today=ORIGIN_N2) == []
    assert out.read_text().splitlines()[-1] == "written="


def test_live_refuses_an_origin_that_is_not_today(tmp_path):
    with pytest.raises(ValueError):
        pipeline.run_live(pipeline.n2_due(ORIGIN_N2), tmp_path, n2_table(), refresh=False, today="2020-01-06")


def test_n2_writer_refuses_future_origin(tmp_path):
    with pytest.raises(ValueError, match="future"):
        n2_live.write("2020-01-05", n2_table(), tmp_path, today="2020-01-04")
    assert not list(tmp_path.iterdir())


def test_live_n2_uses_only_data_known_at_origin(tmp_path):
    table = n2_table()
    poison = _rows("us_imports_tw_m", "M", [pd.Period("2019-11", "M")], [1e12], ["2020-01-06"], "fetch")
    a = pipeline.run_live(pipeline.n2_due(ORIGIN_N2), tmp_path / "a", table, refresh=False, today=ORIGIN_N2)
    b = pipeline.run_live(pipeline.n2_due(ORIGIN_N2), tmp_path / "b", pd.concat([table, poison]),
                          refresh=False, today=ORIGIN_N2)
    va, vb = (json.loads(p.read_text(encoding="utf-8"))["variants"] for p in (a, b))
    assert va == vb


def test_refresh_failure_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "get", lambda name, default=None: "test-agent")
    monkeypatch.setattr(observations, "refresh", lambda keys=None: {k: "FAILED: boom" for k in keys})
    with pytest.raises(SystemExit, match="refresh failed"):
        pipeline.run_live(pipeline.n2_due(ORIGIN_N2), tmp_path, n2_table(), refresh=True, today=ORIGIN_N2)
    assert not (tmp_path / "n2").exists()


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "README").write_text("x")
    _git(tmp_path, "add", "README")
    _git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "init")
    return tmp_path


def test_publish_commits_new_file_once(repo):
    f = repo / "forecasts" / "n2" / "2019-12.json"
    f.parent.mkdir(parents=True)
    f.write_text('{"value": 1}\n')
    (repo / "forecasts" / "SCORECARD.md").write_text("# s\n")
    assert pipeline.publish(["forecasts/n2/2019-12.json"], repo)
    head = _git(repo, "rev-parse", "HEAD")
    assert _git(repo, "log", "-1", "--format=%an") == pipeline.BOT_NAME
    assert set(_git(repo, "show", "--name-only", "--format=", "HEAD").split()) == {
        "forecasts/n2/2019-12.json", "forecasts/SCORECARD.md"}
    # second run: already in HEAD, even if the working copy was changed -> no commit, nothing staged
    f.write_text('{"value": 2}\n')
    assert not pipeline.publish(["forecasts/n2/2019-12.json"], repo)
    assert _git(repo, "rev-parse", "HEAD") == head
    assert _git(repo, "diff", "--cached", "--name-only") == ""


def test_publish_refuses_other_files(repo):
    (repo / "README").write_text("changed")
    _git(repo, "add", "README")
    f = repo / "forecasts" / "n1" / "2026Q4.json"
    f.parent.mkdir(parents=True)
    f.write_text("{}\n")
    with pytest.raises(SystemExit, match="unexpected staged"):
        pipeline.publish(["forecasts/n1/2026Q4.json"], repo)
    with pytest.raises(SystemExit, match="only forecasts"):
        pipeline.publish(["README"], repo)


# ------------------------------------------------------------------ scorecard


def _forecast(root, sub, period, origin, champion, variants, target):
    key = "quarter" if sub == "n1" else "month"
    p = root / sub / f"{period}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"target": target, key: period, "origin": origin, "champion": champion,
                             "value": variants[champion], "variants": variants}), encoding="utf-8")
    return p


def test_scorecard_scores_against_first_vintage(tmp_path):
    q = pd.Period("2026Q4", freq="Q-DEC")
    f1 = _forecast(tmp_path, "n1", "2026Q4", "2027-01-20", "B1",
                   {"B0": 90.0, "B1": 100.0, "V1": None, "V2": 105.0}, n1.TARGET)
    _forecast(tmp_path, "n2", "2026-11", "2026-12-05", "B1", {"B0": 10.0, "B1": 11.0, "V1": 12.0}, n2.TARGET)
    before = f1.read_bytes()
    table = pd.concat([
        _rows(n1.TARGET, "Q", [q], [110.0], ["2027-02-05"]),  # first vintage
        _rows(n1.TARGET, "Q", [q], [200.0], ["2027-05-01"], "revision"),  # later revision: never scored
    ], ignore_index=True)
    s = pipeline.score(tmp_path, table)
    r = s["n1"].iloc[0]
    assert r["outcome"] == 110.0 and r["known_from"] == "2027-02-05" and r["status"] == "utfall"
    assert r["err_champion"] == pytest.approx(100 * np.log(100 / 110))
    assert r["err_B0"] == pytest.approx(100 * np.log(90 / 110)) and np.isnan(r["err_V1"])
    n2row = s["n2"].iloc[0]
    assert n2row["status"] == "väntar" and np.isnan(n2row["err_champion"])
    md = pipeline.scorecard(tmp_path, table, today="2027-05-02").read_text(encoding="utf-8")
    assert "| 2026Q4 | 2027-01-20 | B1 | 100.0 | 110.0 | 2027-02-05 | -9.53 |" in md
    assert "Utvärderade: 1 av 1." in md and "Utvärderade: 0 av 1." in md
    assert f1.read_bytes() == before  # forecast files are read, never edited


def test_scorecard_never_scores_an_outcome_known_at_origin(tmp_path):
    q = pd.Period("2026Q4", freq="Q-DEC")
    _forecast(tmp_path, "n1", "2026Q4", "2027-01-20", "B1", {"B0": 1.0, "B1": 1.0, "V1": None, "V2": None},
              n1.TARGET)
    r = pipeline.score(tmp_path, _rows(n1.TARGET, "Q", [q], [2.0], ["2027-01-20"]))["n1"].iloc[0]
    assert r["status"].startswith("utfall känt") and np.isnan(r["err_champion"])


def test_scorecard_on_empty_forecasts_dir(tmp_path):
    md = pipeline.scorecard(tmp_path, observations._empty(), today="2026-11-23").read_text(encoding="utf-8")
    assert md.count("Inga skarpa prognoser än.") == 2


# ------------------------------------------------------------------ weekly and SEC requirement


def test_sec_user_agent_is_required(monkeypatch):
    monkeypatch.setattr(config, "get", lambda name, default=None: default)
    with pytest.raises(SystemExit, match="SEC_USER_AGENT is not set"):
        pipeline.require_sec(["tsmc_revenue_m"])
    with pytest.raises(SystemExit, match="SEC_USER_AGENT is not set"):
        pipeline.require_sec(None)
    pipeline.require_sec(["us_imports_tw_m"])  # no SEC series: no requirement


def test_weekly_exit_code_follows_checks(monkeypatch):
    monkeypatch.setattr(observations, "refresh", lambda keys=None: {"us_imports_tw_m": "FAILED: x"})
    monkeypatch.setattr(warehouse, "connect", lambda *a, **k: None)
    monkeypatch.setattr(warehouse, "fresh", lambda con=None, today=None: pd.DataFrame(columns=["series"]))
    monkeypatch.setattr(warehouse, "run_checks", lambda con=None: {"unique_key": pd.DataFrame()})
    assert pipeline.weekly(["us_imports_tw_m"]) == 0  # a failed source is a warning
    monkeypatch.setattr(warehouse, "run_checks", lambda con=None: {"unique_key": pd.DataFrame({"series": ["a"]})})
    assert pipeline.weekly(["us_imports_tw_m"]) == 1
    with pytest.raises(SystemExit, match="unknown series"):
        pipeline.weekly(["no_such_series"])
