"""Dated API prices from the git history of LiteLLM's `model_prices_and_context_window.json` (MIT).

The file has one entry per model key with `litellm_provider`, `mode`, `input_cost_per_token` and
`output_cost_per_token` (USD). Its git history gives dated versions: a price was known no later than the
date of the first commit on `main` that contained it.

Method:
- Blobless clone under data/raw/litellm/repo (never inside the tracked tree; data/ is gitignored).
- Commits that touched the file along `main`'s first-parent chain (the date it landed on main, not the
  PR branch's author date). Sample: the last such commit in each week (W-SUN) and in each month, so
  the state at every month end is exact and weekly states are available in between.
- Snapshot date = commit timestamp in UTC, as a date. With sampling, a price's first-seen date is the
  first *sampled* snapshot containing it: never earlier than the real commit (conservative).
- Only text-generation entries (`mode` chat or responses; responses = OpenAI's Responses-API-only
  models such as o3-pro) with both prices > 0 are kept. Batch, priority, flex, cached and
  >200k-context tiers are ignored: the standard list price is used.
- Output price = max(`output_cost_per_token`, `output_cost_per_reasoning_token`) when the entry lists a
  separate price for reasoning output (Gemini 2.5 Flash preview: $0.60 vs $3.50). Epoch measures
  capability with reasoning on, so the price must be the reasoning-mode price.

Cache: data/raw/litellm/snapshots_v2.parquet (snapshot_date, sha, key, provider, input_per_m, output_per_m).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pandas as pd

from ai_tracker import config

REPO_URL = "https://github.com/BerriAI/litellm.git"
FILE = "model_prices_and_context_window.json"
RAW = config.REPO / "data" / "raw" / "litellm"
CLONE = RAW / "repo"
CACHE = RAW / "snapshots_v2.parquet"  # bump the suffix when extract() changes
MODES = ("chat", "responses")
COLUMNS = ["snapshot_date", "sha", "key", "provider", "input_per_m", "output_per_m"]


def _git(*args: str, repo: Path = CLONE, input: str | None = None) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
                          input=input).stdout


def update_clone(clone: Path = CLONE) -> None:
    """Blobless clone (trees and commits only), or fetch new commits into an existing one."""
    if (clone / ".git").exists():
        _git("fetch", "--quiet", "--no-tags", "origin", "main", repo=clone)
        _git("update-ref", "refs/heads/main", "FETCH_HEAD", repo=clone)
        return
    clone.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout", "--single-branch",
                    "--no-tags", REPO_URL, str(clone)], check=True)


def file_commits(clone: Path = CLONE) -> pd.DataFrame:
    """Commits on main's first-parent chain that touched FILE: sha, ts (UTC)."""
    out = _git("log", "--first-parent", "main", "--format=%H %cI", "--", FILE, repo=clone)
    rows = [line.split() for line in out.splitlines() if line.strip()]
    df = pd.DataFrame(rows, columns=["sha", "ts"])
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    return df.sort_values("ts").reset_index(drop=True)


def sample_commits(commits: pd.DataFrame) -> pd.DataFrame:
    """Last commit per week (W-SUN) and per month, on UTC dates. Returns sha, ts, snapshot_date."""
    c = commits.copy()
    c["snapshot_date"] = c["ts"].dt.tz_convert("UTC").dt.tz_localize(None).dt.normalize()
    week = c.groupby(c["snapshot_date"].dt.to_period("W-SUN"))["ts"].idxmax()
    month = c.groupby(c["snapshot_date"].dt.to_period("M"))["ts"].idxmax()
    keep = sorted(set(week) | set(month))
    return c.loc[keep].reset_index(drop=True)


def extract(snapshot: dict) -> list[tuple[str, str, float, float]]:
    """(key, provider, input USD/1M, output USD/1M) for chat/responses entries with both prices > 0."""
    rows = []
    for key, v in snapshot.items():
        if not isinstance(v, dict) or v.get("mode", "chat") not in MODES:
            continue
        try:
            inp, outp = float(v["input_cost_per_token"]), float(v["output_cost_per_token"])
            reasoning = float(v.get("output_cost_per_reasoning_token") or 0)
        except (KeyError, TypeError, ValueError):
            continue
        outp = max(outp, reasoning)
        if inp > 0 and outp > 0:
            rows.append((key, str(v.get("litellm_provider", "")), inp * 1e6, outp * 1e6))
    return rows


def _read_blobs(shas: list[str], clone: Path) -> dict[str, dict]:
    oids = {sha: _git("rev-parse", f"{sha}:{FILE}", repo=clone).strip() for sha in shas}
    missing = sorted(set(oids.values()))
    for i in range(0, len(missing), 200):  # one batched fetch instead of one lazy fetch per blob
        subprocess.run(["git", "-C", str(clone), "-c", "fetch.negotiationAlgorithm=noop", "fetch", "--quiet",
                        "--no-tags", "--no-write-fetch-head", "--filter=blob:none", "origin",
                        *missing[i:i + 200]], check=True, capture_output=True)
    out = {}
    for sha, oid in oids.items():
        text = _git("cat-file", "blob", oid, repo=clone)
        try:
            out[sha] = json.loads(text)
        except json.JSONDecodeError:  # a broken commit on main: skip it, the next sample covers it
            out[sha] = None
    return out


def snapshots(refresh: bool = True, clone: Path = CLONE, cache: Path = CACHE) -> pd.DataFrame:
    """Price snapshots for all sampled commits, incremental over the cache."""
    old = pd.read_parquet(cache) if cache.exists() else pd.DataFrame(columns=COLUMNS)
    if not refresh and len(old):
        return old
    update_clone(clone)
    sample = sample_commits(file_commits(clone))
    todo = sample[~sample["sha"].isin(set(old["sha"]))]
    rows = []
    if len(todo):
        blobs = _read_blobs(list(todo["sha"]), clone)
        for sha, day in zip(todo["sha"], todo["snapshot_date"]):
            if blobs[sha] is not None:
                rows += [(day, sha, *r) for r in extract(blobs[sha])]
    new = pd.DataFrame(rows, columns=COLUMNS)
    # keep only sampled commits (a month's last commit can change when a later commit lands that month)
    out = pd.concat([old, new], ignore_index=True) if len(old) else new
    out = out[out["sha"].isin(set(sample["sha"]))].reset_index(drop=True)
    out["snapshot_date"] = pd.to_datetime(out["snapshot_date"])
    cache.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(cache, index=False)
    return out
