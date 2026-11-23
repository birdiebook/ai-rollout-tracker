"""PyPI BigQuery backfill 2016 -> last Sunday, one capped query per year (track B1).

Refused before any query runs if the total dry-run estimate is above pypi_bq.BACKFILL_MAX_GB.
Output: daily_<start>_<end>.csv per year and bytes.json (estimated, processed and billed bytes per query).
"""

from __future__ import annotations

from pathlib import Path

from ai_tracker.sources import pypi_bq


def run(out_dir: Path) -> None:
    pypi_bq.backfill(out_dir)
