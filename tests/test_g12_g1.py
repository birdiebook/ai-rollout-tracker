"""Track G12, G1 sources: Arena (dataset + Space pickles), SWE-bench git board, and the monthly vintage rule.
Fixtures only, no network."""

from __future__ import annotations

import os
import pickle
import subprocess

import numpy as np
import pandas as pd
import pytest

from ai_tracker.sources import arena, swebench, vintages


# ------------------------------------------------------------------ vintages

def test_monthly_first_vintage_and_later_evidence():
    ev = pd.DataFrame({
        "published": ["2024-01-10", "2024-01-25", "2024-02-20"],
        "value": [10.0, 12.0, 15.0],
        "evidence": ["2024-01-12", "2024-02-03", "2024-02-29"],  # the 01-25 board is documented only in February
        "source": ["release", "release", "backfill"],
    })
    rows = vintages.monthly(ev, pd.Period("2024-03", "M"))
    jan = rows[rows["period"] == "2024-01"]
    assert list(jan["value"]) == [10.0, 12.0]
    assert list(jan["known_from"]) == [pd.Timestamp("2024-02-01"), pd.Timestamp("2024-02-03")]
    feb = rows[rows["period"] == "2024-02"]
    # documented on the last day of February: counts in the month-end vintage, known 03-01
    assert list(feb["value"]) == [15.0] and feb["known_from"].iloc[0] == pd.Timestamp("2024-03-01")
    assert feb["source"].iloc[0] == "backfill"
    mar = rows[rows["period"] == "2024-03"]
    assert list(mar["value"]) == [15.0]  # carried: latest documented board
    assert (rows["known_from"] >= pd.PeriodIndex(rows["period"], freq="M").end_time.normalize()).all()


def test_monthly_never_before_publish_date_and_empty_month():
    ev = pd.DataFrame({"published": ["2024-03-05"], "value": [1.0], "evidence": ["2024-03-01"],
                       "source": ["release"]})
    rows = vintages.monthly(ev, pd.Period("2024-03", "M"), first_month=pd.Period("2024-02", "M"))
    assert list(rows["period"]) == ["2024-03"]  # February had no board
    late = pd.DataFrame({"published": ["2024-03-05"], "value": [1.0], "evidence": ["2024-06-10"],
                         "source": ["backfill"]})
    r = vintages.monthly(late, pd.Period("2024-04", "M"))
    assert list(r["known_from"]) == [pd.Timestamp("2024-06-10")] * 2  # no month-end vintage before evidence


# ------------------------------------------------------------------ arena: evidence logs

def test_parse_dataset_log_takes_last_titled_commit_utc():
    # X5 (R8 R-1): the current rows are those of the LAST titled upload; earlier uploads are versions of their own
    log = "\n".join([
        "2026-11-24T04:02:13+00:00|Update webdev for 2026-11-23",
        "2026-04-03T23:50:00-04:00|Update text for 2026-04-02",  # = 04-04 03:50 UTC, the later upload
        "2026-04-03T22:50:26+00:00|Update text for 2026-04-02",
        "2026-04-02T19:50:32+00:00|add historical data",
    ])
    ev = arena.parse_dataset_log(log)
    assert ev[("text", "2026-04-02")] == pd.Timestamp("2026-04-04")
    assert ev[("webdev", "2026-11-23")] == pd.Timestamp("2026-11-24")
    assert len(ev) == 2


def test_parse_space_log_first_add_per_date():
    log = "\n".join(["C|2025-09-03T05:38:14+00:00", "elo_results_20250829.pkl", "leaderboard_table_20250829.csv",
                     "C|2023-05-20T10:07:35+00:00", "elo_results_20230508.pkl",
                     "C|2023-05-20T09:46:18+00:00", "elo_results_20230508.pkl", "elo_results_20240422-2.pkl"])
    sp = arena.parse_space_log(log)
    assert sp == {"2025-08-29": (pd.Timestamp("2025-09-03"), "elo_results_20250829.pkl"),
                  "2023-05-08": (pd.Timestamp("2023-05-20"), "elo_results_20230508.pkl")}


# ------------------------------------------------------------------ arena: restricted unpickler

def _obj_index(values):
    return pd.Index(list(values), dtype=object)


def _table(ratings: dict) -> pd.DataFrame:
    df = pd.DataFrame({"rating": list(ratings.values()), "variance": 1.0, "num_battles": 100},
                      index=_obj_index(ratings))
    df.columns = _obj_index(df.columns)
    return df


def _pickle(tree) -> bytes:
    return pickle.dumps(tree, protocol=4)


def test_pickle_tables_rebuilds_tables_and_series():
    s = pd.Series([1000.0, 900.0], index=_obj_index(["a", "b"]))
    blob = _pickle({"text": {"full": {"leaderboard_table_df": _table({"a": 1300.5, "b": 1200.25})},
                             "full_style_control": {"leaderboard_table_df": _table({"a": 1290.0, "b": 1210.0})}},
                    "elo_rating_final": s, "elo_rating_median": {"x": 1.0}})
    t = arena.pickle_tables(blob)
    assert t["text/full"].to_dict() == {"a": 1300.5, "b": 1200.25}
    assert t["text/full_style_control"]["b"] == 1210.0
    assert t["elo_rating_final"].to_dict() == {"a": 1000.0, "b": 900.0}
    assert t["elo_rating_median"].to_dict() == {"x": 1.0}


class _Evil:
    def __reduce__(self):
        return (os.system, ("touch SHOULD_NOT_EXIST",))


def test_safe_load_never_executes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    obj = arena.safe_load(pickle.dumps({"x": _Evil()}))
    assert not (tmp_path / "SHOULD_NOT_EXIST").exists()
    assert obj["x"].qual in ("posix.system", "nt.system", "os.system")


def test_match_table_needs_exact_equality():
    rows = pd.Series({"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0, "e": 5.0})
    tables = {"full": rows + 0.5, "full_old": pd.concat([rows, pd.Series({"gpt-4-turbo": 9.0})])}
    assert arena.match_table(tables, rows, ("full", "full_old")) == "full_old"
    assert arena.match_table({"full": rows.iloc[:3]}, rows, ("full",)) is None  # too few common models


# ------------------------------------------------------------------ arena: boards

def _dataset(boards: dict[str, dict[str, float]]) -> pd.DataFrame:
    return pd.DataFrame([(m, r, d) for d, b in boards.items() for m, r in b.items()],
                        columns=["model_name", "rating", "leaderboard_publish_date"])


BASE = {"m1": 1000.0, "m2": 1010.0, "m3": 1020.0, "m4": 1030.0, "mixtral-8x7b-instruct-v0.1": 1100.0}


def test_board_events_prefers_complete_space_table_and_dates_by_evidence():
    ds = _dataset({"2024-01-09": BASE,  # censored: the published #1 is missing in the dataset
                   "2025-10-01": {**BASE, "m5": 1300.0},  # only in the bulk upload
                   "2026-05-01": {**BASE, "Mixtral 8x7B Instruct v0.1": 1105.0, "m6": 1400.0}})
    ds = ds[~((ds.leaderboard_publish_date == "2026-05-01") & (ds.model_name == "mixtral-8x7b-instruct-v0.1"))]
    space = {"2024-01-09": (pd.Timestamp("2024-01-10"), "elo_results_20240109.pkl"),
             "2024-02-01": (pd.Timestamp("2024-02-05"), "elo_results_20240201.pkl")}
    full = pd.Series({**BASE, "gpt-4-turbo": 1250.0})
    pickles = {"elo_results_20240109.pkl": {"elo_rating_final": full, "elo_rating_online": full + 3},
               "elo_results_20240201.pkl": {"elo_rating_final": full + 1}}  # no dataset board that day
    ev = arena.board_events(ds, "text", {("text", "2026-05-01"): pd.Timestamp("2026-05-02")}, space, pickles)
    by = ev.set_index(ev["published"].dt.strftime("%Y-%m-%d"))
    assert by.loc["2024-01-09", "top"] == 1250.0 and by.loc["2024-01-09", "top_model"] == "gpt-4-turbo"
    assert by.loc["2024-01-09", "evidence"] == pd.Timestamp("2024-01-10")
    assert by.loc["2024-01-09", "origin"] == "space:elo_rating_final"
    assert by.loc["2024-02-01", "origin"] == "space-unmatched:elo_rating_final"  # same table as the last match
    assert by.loc["2024-02-01", "top"] == 1251.0
    assert by.loc["2025-10-01", "source"] == "backfill"
    assert by.loc["2025-10-01", "evidence"] == arena.DATASET_CREATED
    assert by.loc["2026-05-01", "evidence"] == pd.Timestamp("2026-05-02")
    assert by.loc["2026-05-01", "ref"] == 1105.0  # renamed reference
    assert by.loc["2024-01-09", "top"] - by.loc["2024-01-09", "ref"] == 150.0


def test_monthly_rows_gap_and_top():
    ev = pd.DataFrame({"published": pd.to_datetime(["2024-01-09"]), "top": [1250.0], "ref": [1100.0],
                       "evidence": pd.to_datetime(["2024-01-10"]), "source": ["release"]})
    gap = arena.monthly_rows(ev, "gap", pd.Period("2024-01", "M"))
    top = arena.monthly_rows(ev, "top", pd.Period("2024-01", "M"))
    assert gap["value"].tolist() == [150.0] and top["value"].tolist() == [1250.0]
    assert top["known_from"].tolist() == [pd.Timestamp("2024-02-01")]


# ------------------------------------------------------------------ SWE-bench

def test_resolved_share_and_events():
    assert swebench.resolved_share({"resolved": ["a", "b", "b"], "no_generation": ["c"]}) == 2 / 500
    trees = {pd.Timestamp("2024-10-15"): {"evaluation/verified/x": "o1", "evaluation/verified/y": "o2"},
             pd.Timestamp("2024-11-02"): {"evaluation/verified/x": "o1"}}  # y removed from the board
    ev = swebench.events_from(trees, {"o1": 0.4, "o2": 0.5})
    assert ev["value"].tolist() == [0.5, 0.4]
    assert ev["top_entry"].tolist() == ["y", "x"]
    assert (ev["published"] == ev["evidence"]).all()


def _git(repo, *args, date=None):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}
    if date:
        env["GIT_COMMITTER_DATE"] = env["GIT_AUTHOR_DATE"] = date
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env=env).stdout


def test_board_commits_and_trees_from_local_repo(tmp_path):
    repo = tmp_path / "exp"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    d = repo / "evaluation" / "verified" / "20241001_a" / "results"
    d.mkdir(parents=True)
    (d / "results.json").write_text('{"resolved": ["i1", "i2"]}')
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "a", date="2024-10-15T23:30:00-07:00")  # = 10-16 06:30 UTC
    (repo / "README.md").write_text("x")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "readme", date="2024-10-20T10:00:00+00:00")  # does not touch the board
    commits = swebench.daily_last(swebench.board_commits(repo))
    assert commits["day"].tolist() == [pd.Timestamp("2024-10-16")]
    blobs = swebench.results_blobs(commits["sha"].iloc[0], repo)
    assert list(blobs) == ["evaluation/verified/20241001_a"]
    assert swebench.resolved_share({"resolved": ["i1", "i2"]}) == pytest.approx(0.004)


def test_specs_register_cleanly():
    from ai_tracker import catalog
    from ai_tracker.series import arena as sa, swebench as ss

    assert catalog.validate(sa.SPECS + ss.SPECS) == []
    assert not ss.SPECS[0].publish  # no licence file
    assert all(np.isfinite([s.lag_days for s in sa.SPECS]))
