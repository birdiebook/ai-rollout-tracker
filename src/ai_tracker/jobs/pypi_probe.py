"""PyPI BigQuery cost probe (dry runs only, free): estimated bytes for one day per project and year (track B1).

Used to size the backfill (docs/kallor/utvecklaradoption.md). Two days per year (15 March, 15 September).
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from ai_tracker.sources import pypi_bq

CANDIDATE_CONTROLS = ["flask", "django", "scipy", "pytz", "matplotlib", "pandas", "scikit-learn"]


def run(out_dir: Path) -> None:
    rows = []
    for year in range(2016, 2027):
        for md in ((3, 15), (9, 15)):
            d = date(year, *md)
            if d >= date.today():
                d = date(2026, 11, 15)
            for p in pypi_bq.PROJECTS + CANDIDATE_CONTROLS:
                est = pypi_bq.dry_run_bytes(pypi_bq.sql(d, d + timedelta(days=1), [p]))
                rows.append({"day": d.isoformat(), "project": p, "estimated": est})
                print(d, p, est)
    (out_dir / "probe.json").write_text(json.dumps(rows, indent=0), encoding="utf-8")
