"""SWE-bench Verified leaderboard from the git history of github.com/SWE-bench/experiments.

Every leaderboard entry is a directory `evaluation/verified/<date>_<system>/` with `results/results.json`
(lists of instance ids: `resolved`, `no_generation`, ...). The board's state at a date is the tree of the last
commit on `main`'s first-parent chain dated <= that date (UTC), so an entry counts from the day it was merged,
never from the run date in its name.

- Frontier = max over entries of len(resolved) / 500 (SWE-bench Verified has 500 instances).
- History starts 2024-10-15: the repository was re-created that day ("Initial commit - reset history"), so the
  entries submitted earlier are dated by the reset, not by their original merge (conservative, later).
- Regime notes (README): from 2025-11-18 Verified accepts only submissions from academic or research teams with
  open methods; the mini-SWE-agent "bash-only" runs moved into `evaluation/verified/`.
- Licence: the repository has no licence file (checked 2026-11-24), so publish=False.
"""

from __future__ import annotations

import json
import subprocess
from functools import lru_cache
from pathlib import Path

import pandas as pd

from ai_tracker import config
from ai_tracker.sources import vintages

REPO_URL = "https://github.com/SWE-bench/experiments.git"
RAW = config.REPO / "data" / "raw" / "swebench"
CLONE = RAW / "repo"
BOARD = "evaluation/verified"
N_INSTANCES = 500
RESET = pd.Timestamp("2024-10-15")
LICENSE = ("unverified: github.com/SWE-bench/experiments has no LICENSE file (checked 2026-11-24); "
           "README asks to cite SWE-bench")


def _git(*args: str, repo: Path = CLONE) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def update_clone(clone: Path = CLONE) -> None:
    if (clone / ".git").exists():
        _git("fetch", "--quiet", "--no-tags", "origin", "main", repo=clone)
        _git("update-ref", "refs/heads/main", "FETCH_HEAD", repo=clone)
        return
    clone.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout", "--single-branch",
                    "--no-tags", REPO_URL, str(clone)], check=True)


def board_commits(clone: Path = CLONE) -> pd.DataFrame:
    """First-parent commits on main that touched the board: sha, day (UTC date)."""
    out = _git("log", "--first-parent", "main", "--format=%H %cI", "--", BOARD, repo=clone)
    rows = [line.split() for line in out.splitlines() if line.strip()]
    df = pd.DataFrame(rows, columns=["sha", "ts"])
    df["day"] = pd.to_datetime(df["ts"], utc=True).dt.tz_localize(None).dt.normalize()
    return df.drop(columns="ts").sort_values("day", kind="stable").reset_index(drop=True)


def daily_last(commits: pd.DataFrame) -> pd.DataFrame:
    """The last commit of each UTC day (git log lists newest first, so the first per day after a stable sort)."""
    return commits.groupby("day", as_index=False).first()


def results_blobs(sha: str, clone: Path = CLONE) -> dict[str, str]:
    """entry directory -> blob id of its results/results.json in the tree of `sha`."""
    out = _git("ls-tree", "-r", sha, "--", BOARD + "/", repo=clone)
    blobs = {}
    for line in out.splitlines():
        meta, path = line.split("\t", 1)
        if path.endswith("/results/results.json"):
            blobs[path[: -len("/results/results.json")]] = meta.split()[2]
    return blobs


def resolved_share(results: dict) -> float:
    return len(set(results.get("resolved") or [])) / N_INSTANCES


def _read_blobs(oids: list[str], clone: Path = CLONE) -> dict[str, float | None]:
    for i in range(0, len(oids), 200):  # one batched fetch instead of one lazy fetch per blob
        subprocess.run(["git", "-C", str(clone), "-c", "fetch.negotiationAlgorithm=noop", "fetch", "--quiet",
                        "--no-tags", "--no-write-fetch-head", "--filter=blob:none", "origin", *oids[i:i + 200]],
                       check=True, capture_output=True)
    out = {}
    for oid in oids:
        try:
            out[oid] = resolved_share(json.loads(_git("cat-file", "blob", oid, repo=clone)))
        except (json.JSONDecodeError, AttributeError):
            out[oid] = None
    return out


def events_from(trees: dict[pd.Timestamp, dict[str, str]], shares: dict[str, float | None]) -> pd.DataFrame:
    """Per day: published = evidence = the commit day, value = frontier share, top entry, number of entries."""
    rows = []
    for day, blobs in sorted(trees.items()):
        vals = {d: shares.get(o) for d, o in blobs.items() if shares.get(o) is not None}
        if vals:
            top = max(vals, key=vals.get)
            rows.append((day, vals[top], day, "release", top.rsplit("/", 1)[-1], len(vals)))
    return pd.DataFrame(rows, columns=["published", "value", "evidence", "source", "top_entry", "n_entries"])


@lru_cache(maxsize=1)
def events(clone: Path = CLONE) -> pd.DataFrame:
    update_clone(clone)
    commits = daily_last(board_commits(clone))
    trees = {day: results_blobs(sha, clone) for sha, day in zip(commits["sha"], commits["day"])}
    oids = sorted({o for t in trees.values() for o in t.values()})
    return events_from(trees, _read_blobs(oids, clone))


def frontier() -> pd.DataFrame:
    return vintages.monthly(events(), vintages.last_complete_month())
