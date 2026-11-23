"""PyPI BigQuery dry run (free): estimated bytes per backfill year and for one incremental window (track B1)."""

from __future__ import annotations

from pathlib import Path

from ai_tracker.sources import pypi_bq


def run(out_dir: Path) -> None:
    pypi_bq.dryrun(out_dir)
