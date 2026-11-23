"""Rebuild of the GH Archive AI co-author aggregates (track B2) in Actions: an independent reproduction of
curated/github_ai_gharchive.csv on a machine with more bandwidth. Needs no secret; output = weekly counts only
(no repo ids, no commit content)."""

from __future__ import annotations

import os
from pathlib import Path

from ai_tracker.sources import gharchive


def run(out_dir: Path) -> None:
    df = gharchive.build(workers=int(os.environ.get("GHA_WORKERS", "8")), path=out_dir / "github_ai_gharchive.csv")
    # also in the log: the session cannot always reach the artifact blob host (weekly counts only)
    print("BEGIN github_ai_gharchive.csv\n" + df.to_csv(index=False) + "END github_ai_gharchive.csv", flush=True)
    print(f"{len(df)} weeks, {int((df['n_hours'] >= gharchive.MIN_HOURS).sum())} with a value")
