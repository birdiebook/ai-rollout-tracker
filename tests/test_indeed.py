"""Indeed Hiring Lab AI tracker: CSV layouts and vintages from git history (local fixture repo, no network)."""

from __future__ import annotations

import os
import subprocess
from datetime import date

import pandas as pd
import pytest

from ai_tracker import catalog, observations
from ai_tracker.sources import indeed

OLD = "modified_date,jobcountry,% of job postings\n1/1/19,US,2.1\n2/1/19,US,2.2\n13/1/19,US,2.3\n"
MID = "modified_date,jobcountry,AI_count,total,ma_share_perc\n2019-01-01,US,1,50,2.1\n2019-01-02,US,1,50,2.25\n"
NEW = ("date,jobcountry,AI_share_postings\n2019-01-01,US,2.1000000001\n2019-01-02,US,2.25\n"
       "2019-01-03,US,2.4\n2019-01-01,GB,1.5\n")


def test_parse_csv_layouts():
    old = indeed.parse_csv(OLD)
    assert list(old["date"]) == [pd.Timestamp("2019-01-01"), pd.Timestamp("2019-01-02"), pd.Timestamp("2019-01-13")]
    assert list(old["value"]) == [2.1, 2.2, 2.3]
    assert indeed.parse_csv(MID)["value"].tolist() == [2.1, 2.25]
    new = indeed.parse_csv(NEW)
    assert set(new["country"]) == {"US", "GB"}
    with pytest.raises(ValueError):
        indeed.parse_csv("date,jobcountry,other\n2019-01-01,US,1\n")


def test_file_pattern_excludes_genai():
    assert indeed.FILE_RE.match("AI_posting_2024-03-31_clean.csv")
    assert indeed.FILE_RE.match("ai-postings.csv") and indeed.FILE_RE.match("AI_posting.csv")
    assert not indeed.FILE_RE.match("GenAI_posting.csv") and not indeed.FILE_RE.match("genai-postings.csv")


def _commit(repo, when, msg, files=None, delete=(), merge=None):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "you@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "you@example.com",
           "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
    run = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, env=env)  # noqa: E731
    if merge:
        run("merge", "--no-ff", "-m", msg, merge)
        return
    for name, text in (files or {}).items():
        (repo / name).write_text(text)
        run("add", name)
    for name in delete:
        run("rm", "-q", name)
    run("commit", "-q", "-m", msg)


@pytest.fixture
def data_repo(tmp_path):
    repo = tmp_path / "origin"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    _commit(repo, "2024-04-29T14:00:00+00:00", "v1",
            {"AI_posting_2024-03-31_clean.csv": OLD, "GenAI_posting_2024-03-31_clean.csv": OLD.replace("2.", "9.")})
    # a branch commit made earlier than its merge: the merge time is when the data became public
    subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-b", "update"], check=True)
    _commit(repo, "2024-07-17T06:00:00+00:00", "v2 on branch", {"ai-postings.csv": MID},
            delete=["AI_posting_2024-03-31_clean.csv"])
    subprocess.run(["git", "-C", str(repo), "checkout", "-q", "main"], check=True)
    _commit(repo, "2024-07-20T09:00:00+00:00", "merge", merge="update")
    _commit(repo, "2024-10-15T05:00:00+00:00", "rename", {"AI_posting.csv": NEW}, delete=["ai-postings.csv"])
    _commit(repo, "2024-11-01T05:00:00+00:00", "readme only", {"README.md": "x"})
    return repo


def test_vintages_from_git_history(data_repo, tmp_path):
    clone = indeed.sync(tmp_path / "clone", url=str(data_repo))
    v = indeed.vintages(clone)
    assert [(kf, path) for kf, _, path in v] == [
        (pd.Timestamp("2024-04-29 14:00"), "AI_posting_2024-03-31_clean.csv"),
        (pd.Timestamp("2024-07-20 09:00"), "ai-postings.csv"),  # merge commit date, not the branch commit
        (pd.Timestamp("2024-10-15 05:00"), "AI_posting.csv"),
    ]
    rows = indeed.rows_from_repo(clone)
    us = rows[rows["country"] == "US"].set_index(["period", "known_from"])["value"]
    # 2019-01-01: same value in all versions (Excel rounding below ATOL) -> one row only
    assert us.loc[pd.Timestamp("2019-01-01")].to_dict() == {pd.Timestamp("2024-04-29 14:00"): 2.1}
    # 2019-01-02: revised in v2 (method change), unchanged in v3
    assert us.loc[pd.Timestamp("2019-01-02")].to_dict() == {pd.Timestamp("2024-04-29 14:00"): 2.2,
                                                            pd.Timestamp("2024-07-20 09:00"): 2.25}
    # 2019-01-13 only in v1: kept; 2019-01-03 and GB new in v3
    assert pd.Timestamp("2019-01-13") in us.index.get_level_values(0)
    assert us.loc[pd.Timestamp("2019-01-03")].index.tolist() == [pd.Timestamp("2024-10-15 05:00")]
    assert rows[rows["country"] == "GB"]["known_from"].tolist() == [pd.Timestamp("2024-10-15 05:00")]
    assert not (rows["value"] > 9).any()  # GenAI file never read

    # a second sync is a fetch, and gives the same rows
    assert indeed.rows_from_repo(indeed.sync(tmp_path / "clone", url=str(data_repo))).equals(rows)


def test_rows_load_as_release_vintages(data_repo, tmp_path):
    rows = indeed.rows_from_repo(indeed.sync(tmp_path / "clone", url=str(data_repo)))
    spec = catalog.by_key()["ai_postings_share_us_d"]
    us = rows[rows["country"] == "US"][["period", "value", "known_from"]]
    path = tmp_path / "obs.parquet"
    assert observations.upsert(spec, us, fetched_at=date(2026, 11, 23), path=path) == len(us)
    assert observations.upsert(spec, us, fetched_at=date(2026, 11, 24), path=path) == 0
    t = observations.load(path)
    assert set(t["source"]) == {"release"}
    assert observations.as_of(spec.key, "2024-05-01", t)["2019-01-02"] == 2.2
    assert observations.as_of(spec.key, "2024-08-01", t)["2019-01-02"] == 2.25
    assert len(observations.as_of(spec.key, "2024-04-01", t)) == 0


def test_catalog_entries():
    keys = {s.key for s in catalog.ALL if s.source.startswith("Indeed")}
    assert {f"ai_postings_share_{c}_d" for c in ("us", "gb", "de", "fr", "ca", "au")} <= keys
    for s in catalog.ALL:
        if s.key in keys:
            assert s.freq == "D" and s.branch == "G8" and "CC BY 4.0" in s.license and s.publish
