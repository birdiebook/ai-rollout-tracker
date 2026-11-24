"""Shared base table + per-track write table (observations) and the merge tool (datamerge). Tmp dirs, no network."""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from ai_tracker import catalog, config, datamerge, observations

REPO = Path(__file__).resolve().parents[1]
TODAY = "2026-11-20"


def spec(key: str, lag: int = 10) -> catalog.Spec:
    return catalog.Spec(key=key, branch="G6", label=key, unit="x", freq="M", source="test",
                        fetch=lambda: pd.Series(dtype=float), lag_days=lag, license="unverified")


A, B, C = spec("a_m"), spec("b_m"), spec("c_m")
SPECS = [A, B, C]


def monthly(last: str, n: int = 12, value: float = 1.0) -> pd.Series:
    """n months to `last`; the value depends only on the month (so overlapping fetches agree) and `value`."""
    idx = pd.period_range(end=pd.Period(last, "M"), periods=n)
    return pd.Series([value + p.month for p in idx], index=idx)


def build(path: Path, *pairs, fetched=date(2026, 10, 15)) -> pd.DataFrame:
    """Write a table (+ fetch log) at `path` with plain upserts, no shared base involved."""
    for s, v in pairs:
        observations.upsert(s, v, fetched, path)
    return observations.read_table(path)


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    """Base dir with a_m and b_m (to 2026-09), an empty track dir, and the track layered over the base."""
    base, track = tmp_path / "base", tmp_path / "track"
    build(base / "observations.parquet", (A, monthly("2026-09")), (B, monthly("2026-09")))
    track.mkdir()
    path = track / "observations.parquet"
    monkeypatch.setattr(observations, "DEFAULT_PATH", path)
    monkeypatch.setattr(observations, "PATH", path)
    monkeypatch.setattr(observations, "SHARED_DIR", base)
    monkeypatch.setattr(catalog, "ALL", SPECS)
    return base, track


def snapshot(d: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted(d.glob("*.parquet"))}


# ------------------------------------------------------------------ the layered view


def test_view_is_base_union_track(dirs):
    base, track = dirs
    assert observations.load().equals(observations.read_table(base / "observations.parquet"))  # empty track
    build(track / "observations.parquet", (C, monthly("2026-10")))
    view = observations.load()
    assert sorted(view["series"].unique()) == ["a_m", "b_m", "c_m"] and len(view) == 36
    assert set(observations.load_log()["series"]) == {"a_m", "b_m", "c_m"}
    # an explicit path, or a changed PATH (--table), reads that file alone
    assert set(observations.load(track / "observations.parquet")["series"]) == {"c_m"}
    observations.PATH = track / "observations.parquet"
    assert len(observations.load()) == 36
    observations.PATH = Path(str(track / "observations.parquet"))  # equal path still layers
    assert len(observations.load()) == 36


def test_track_row_wins_on_identical_key(dirs):
    base, track = dirs
    row = observations.read_table(base / "observations.parquet").iloc[[0]].copy()
    row["value"] = 99.0
    observations.save(row)
    view = observations.load()
    hit = view[(view["series"] == row["series"].iloc[0]) & (view["period"] == row["period"].iloc[0])]
    assert hit["value"].tolist() == [99.0] and len(view) == 24


def test_track_row_wins_when_the_base_has_intraday_known_from():
    """astype(str) renders a datetime column without the time only if every value is midnight: a base that also holds
    intraday known_from (daily series) must still match a track row on an identical key (no duplicate)."""
    cols = ["series", "freq", "period", "value", "known_from", "source", "fetched_at"]
    base = pd.DataFrame([["rev_x", "Q", "2025Q1", 1.0, pd.Timestamp("2025-05-01"), "release", pd.Timestamp("2026-11-23")],
                         ["d_x", "D", "2025-05-01", 2.0, pd.Timestamp("2025-05-01 17:30"), "release",
                          pd.Timestamp("2026-11-23")]], columns=cols)
    track = pd.DataFrame([["rev_x", "Q", "2025Q1", 1.5, pd.Timestamp("2025-05-01"), "release",
                           pd.Timestamp("2026-11-24")]], columns=cols)
    out = observations.combine(base, track)
    assert len(out) == 2 and out.loc[out["series"] == "rev_x", "value"].tolist() == [1.5]
    log = observations.combine(base, track.assign(fetched_at=pd.Timestamp("2026-11-23")), key=observations.LOG_KEY)
    assert sorted(log["series"]) == ["d_x", "rev_x"]


def test_unset_means_one_table(dirs, monkeypatch):
    base, track = dirs
    monkeypatch.setattr(observations, "SHARED_DIR", None)
    assert observations.load().empty and observations.base_path() is None
    monkeypatch.setattr(observations, "SHARED_DIR", track)  # the base is the track table itself
    assert observations.base_path() is None


def test_writes_never_touch_base(dirs):
    base, track = dirs
    before = snapshot(base)
    n = observations.upsert(A, monthly("2026-10"), date(2026, 11, 15))
    assert n == 1  # only the new period: the base's 12 are known through the view
    t = observations.read_table(track / "observations.parquet")
    assert t[["series", "period", "source"]].values.tolist() == [["a_m", "2026-10", "fetch"]]
    assert t["known_from"].iloc[0] == pd.Timestamp("2026-11-10")
    log = observations.read_log(track / "fetch_log.parquet")
    assert log[["series", "rows_added"]].values.tolist() == [["a_m", 1]]
    assert observations.upsert(A, monthly("2026-10"), date(2026, 11, 16)) == 0
    assert snapshot(base) == before
    assert len(observations.load()) == 25 and len(observations.load_log()) == 4


def test_rebuild_hides_base_rows_without_touching_base(dirs):
    base, track = dirs
    before = snapshot(base)
    assert observations.drop_series(["b_m"]) == 12
    assert observations.load_rebuilt() == ["b_m"]
    assert set(observations.load()["series"]) == {"a_m"}
    assert "b_m" in set(observations.load_log()["series"])  # the base's fetch dates are kept
    observations.upsert(B, monthly("2026-10", value=5.0), date(2026, 11, 15))
    b = observations.load().query("series == 'b_m'")
    assert len(b) == 12 and b["value"].min() == 6.0
    assert snapshot(base) == before


# ------------------------------------------------------------------ datamerge


def track_work(track: Path) -> None:
    """A track that adds c_m, fetches a new period of a_m and rebuilds b_m."""
    observations.upsert(A, monthly("2026-10"), date(2026, 11, 15))
    observations.drop_series(["b_m"])
    observations.upsert(B, monthly("2026-10", value=5.0), date(2026, 11, 15))
    observations.upsert(C, monthly("2026-10"), date(2026, 11, 15))


def test_merge_appends_updates_and_replaces(dirs):
    base, track = dirs
    track_work(track)
    view = observations.load().sort_values(observations.KEY).reset_index(drop=True)
    res = datamerge.merge(track, base, today=TODAY, specs=SPECS)
    assert res.ok and res.written, res.summary()
    assert set(res.added) == {"c_m"} and res.updated == {"a_m": 1} and res.replaced == {"b_m": (12, 12)}
    merged = observations.read_table(base / "observations.parquet")
    assert merged.sort_values(observations.KEY).reset_index(drop=True).equals(view)  # base = the track's view
    assert merged.query("series == 'b_m'")["value"].min() == 6.0
    assert len(list((base / "merge_backups").glob("*_observations.parquet"))) == 1
    assert "c_m" in set(observations.read_log(base / "fetch_log.parquet")["series"])


def test_merge_is_idempotent(dirs):
    base, track = dirs
    track_work(track)
    assert datamerge.merge(track, base, today=TODAY, specs=SPECS).written
    after = snapshot(base)
    again = datamerge.merge(track, base, today=TODAY, specs=SPECS)
    assert not again.written and not again.changed and sorted(again.unchanged) == ["a_m", "b_m", "c_m"]
    assert "nothing to merge" in again.summary()
    assert snapshot(base) == after


def test_merge_only_selected_series(dirs):
    base, track = dirs
    track_work(track)
    res = datamerge.merge(track, base, series=["c_m"], today=TODAY, specs=SPECS)
    assert res.written and set(res.added) == {"c_m"} and not res.updated and not res.replaced
    merged = observations.read_table(base / "observations.parquet")
    assert merged.query("series == 'b_m'")["value"].min() == 2.0  # untouched
    with pytest.raises(SystemExit, match="not in the track"):
        datamerge.merge(track, base, series=["zz_m"], today=TODAY, specs=SPECS)


def test_merge_refuses_on_failing_check(dirs, capsys):
    base, track = dirs
    track_work(track)
    bad = observations.read_table(track / "observations.parquet").iloc[[0]].copy()
    bad["series"] = "not_in_catalog_m"
    t = observations.read_table(track / "observations.parquet")
    observations.save(pd.concat([t, bad], ignore_index=True))
    before = snapshot(base)
    res = datamerge.merge(track, base, today=TODAY, specs=SPECS)
    assert not res.written and "series_in_catalog" in res.failed and "NOT written" in res.summary()
    assert snapshot(base) == before and not (base / "merge_backups").exists()
    assert datamerge.main([str(track), "--into", str(base), "--today", TODAY]) == 1
    assert "CHECK FAILED series_in_catalog" in capsys.readouterr().out


def test_merge_refuses_a_stale_merged_series(dirs):
    base, track = dirs
    observations.drop_series(["b_m"])
    observations.upsert(B, monthly("2025-12"), date(2026, 11, 15))  # a rebuild that lost the recent periods
    before = snapshot(base)
    res = datamerge.merge(track, base, today=TODAY, specs=SPECS)
    assert not res.written and list(res.stale["series"]) == ["b_m"] and snapshot(base) == before
    # a stale series that is not merged does not block
    observations.upsert(C, monthly("2026-10"), date(2026, 11, 15))
    assert datamerge.merge(track, base, series=["c_m"], today=TODAY, specs=SPECS).written


def test_merge_replace_flag_for_legacy_track(dirs, tmp_path):
    """A run-1 style track: a full copy of data/ with a series rebuilt in place, no rebuilt_series.json."""
    base, _ = dirs
    legacy = tmp_path / "legacy"
    build(legacy / "observations.parquet", (A, monthly("2026-09")), (B, monthly("2026-10", value=5.0)),
          fetched=date(2026, 11, 15))
    union = datamerge.merge(legacy, base, today=TODAY, specs=SPECS, dry_run=True)
    assert "b_m" in union.updated and not union.written  # dry run, and union keeps both vintages of b_m
    res = datamerge.merge(legacy, base, replace=["b_m"], today=TODAY, specs=SPECS)
    assert res.written and res.replaced == {"b_m": (12, 12)}


def test_merge_into_empty_base(tmp_path, monkeypatch):
    monkeypatch.setattr(catalog, "ALL", SPECS)
    track = tmp_path / "t"
    build(track / "observations.parquet", (A, monthly("2026-10")), fetched=date(2026, 11, 15))
    res = datamerge.merge(track, tmp_path / "new_base", today=TODAY, specs=SPECS)
    assert res.written and res.added == {"a_m": 12}
    with pytest.raises(SystemExit, match="same directory"):
        datamerge.merge(track, track, today=TODAY, specs=SPECS)


# ------------------------------------------------------------------ config and new_track.sh


def test_config_reads_env_local_before_env(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "REPO", tmp_path)
    monkeypatch.delenv("AI_TRACKER_SHARED_DATA", raising=False)
    monkeypatch.delenv("X_ONLY_ENV", raising=False)
    (tmp_path / ".env").write_text("AI_TRACKER_SHARED_DATA=/from/env\nX_ONLY_ENV=1\n", encoding="utf-8")
    (tmp_path / ".env.local").write_text("AI_TRACKER_SHARED_DATA=/from/local\n", encoding="utf-8")
    assert config.get("AI_TRACKER_SHARED_DATA") == "/from/local" and config.get("X_ONLY_ENV") == "1"
    monkeypatch.setenv("AI_TRACKER_SHARED_DATA", "/from/environ")
    assert config.get("AI_TRACKER_SHARED_DATA") == "/from/environ"


@pytest.mark.skipif(shutil.which("git") is None or shutil.which("bash") is None, reason="needs git and bash")
def test_new_track_script(tmp_path):
    main = tmp_path / "main"
    main.mkdir()
    git = ["git", "-C", str(main), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run(["git", "init", "-q", "-b", "main", str(main)], check=True)
    (main / "README.md").write_text("x\n", encoding="utf-8")
    (main / ".env").write_text("SEC_USER_AGENT=dummy\n", encoding="utf-8")
    subprocess.run([*git, "add", "README.md"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "init"], check=True)
    env = {**os.environ, "AI_TRACKER_MAIN": str(main), "AI_TRACKER_WT_ROOT": str(tmp_path / "wt")}
    script = str(REPO / "scripts" / "new_track.sh")
    out = subprocess.run(["bash", script, "a1-rpo", "auto9"], env=env, capture_output=True, text=True, check=True)
    wt = tmp_path / "wt" / "a1-rpo"
    assert "auto9/a1-rpo" in out.stdout and (wt / "README.md").exists() and (wt / "data").is_dir()
    assert (wt / ".env").read_text(encoding="utf-8") == "SEC_USER_AGENT=dummy\n"
    local = (wt / ".env.local").read_text(encoding="utf-8")
    assert f"AI_TRACKER_SHARED_DATA={main}/data\n" in local and f"AI_TRACKER_SHARED_RAW={main}/data/raw\n" in local
    branch = subprocess.run(["git", "-C", str(wt), "branch", "--show-current"], capture_output=True, text=True)
    assert branch.stdout.strip() == "auto9/a1-rpo"
    again = subprocess.run(["bash", script, "a1-rpo", "auto9"], env=env, capture_output=True, text=True)
    assert again.returncode == 1 and "exists" in again.stderr
