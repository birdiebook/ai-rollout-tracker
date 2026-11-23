"""PyPI BigQuery calibration (track B1): estimated vs billed bytes for two small real queries (about 2 GB).

The dry-run estimate on a clustered table is an upper bound; this measures how far billing is below it.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ai_tracker.sources import pypi_bq


def run(out_dir: Path) -> None:
    cases = [(date(2026, 3, 15), date(2026, 3, 16), ["anthropic", "mcp"]),
             (date(2025, 9, 15), date(2025, 9, 16), pypi_bq.PROJECTS)]
    out = []
    for s, e, projects in cases:
        q = pypi_bq.sql(s, e, projects)
        est = pypi_bq.dry_run_bytes(q)
        body, stats = pypi_bq.run_query(q, int(est * 1.1) + 100_000_000)
        out.append({"start": s.isoformat(), "projects": projects, "estimated": est, **stats,
                    "rows": body.count("\n") - 1})
        print(out[-1])
        (out_dir / f"daily_{s.isoformat()}_{e.isoformat()}_{len(projects)}.csv").write_text(body, encoding="utf-8")
    (out_dir / "calibrate.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
