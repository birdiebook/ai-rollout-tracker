"""Commit-search counts (track B2) in Actions: the backfill from 2024-01 with the workflow's GITHUB_TOKEN, which
the session cannot use (its anonymous search runs into GitHub's secondary rate limit). Output: total_count per
query and week (counts only) as CSV and as the day's counts.json cache file."""

from __future__ import annotations

import json
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path

from ai_tracker.sources import github_search


def run(out_dir: Path) -> None:
    github_search.MIN_INTERVAL = float(os.environ.get("GHS_MIN_INTERVAL", "2.5"))
    deadline = time.monotonic() + 60 * float(os.environ.get("GHS_DEADLINE_MIN", "45"))
    today = datetime.now(timezone.utc).date()

    def get(q: str):  # stop asking near the job timeout so the artifact is still uploaded
        return github_search.total_count(q) if time.monotonic() < deadline else None

    # the live path of a cold start (the newest MAX_WEEKS_PER_FETCH weeks); a full backfill from 2024 does not fit
    # (2026-11-23: 140 answers in 75 minutes under the secondary rate limit)
    df = github_search.counts(set(), today=today, get=get, max_weeks=github_search.MAX_WEEKS_PER_FETCH)
    out = df.copy()
    out.index = [p.start_time.date().isoformat() for p in df.index]
    out.index.name = "week"
    out.to_csv(out_dir / "github_search_counts.csv")
    # also in the log: the session cannot always reach the artifact blob host (counts only, public anyway)
    print("BEGIN github_search_counts.csv\n" + out.to_csv() + "END github_search_counts.csv", flush=True)
    cache = github_search._cache_path(today)
    if cache.exists():
        (out_dir / f"counts_{today.isoformat()}.json").write_text(cache.read_text(encoding="utf-8"), encoding="utf-8")
    print(json.dumps({"day": today.isoformat(), "weeks": len(df), "missing": int(df.isna().any(axis=1).sum())}))
    if date.today() != today:
        print("note: local date differs from UTC date")
