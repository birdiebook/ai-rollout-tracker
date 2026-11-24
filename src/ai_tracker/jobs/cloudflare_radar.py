"""Cloudflare Radar job (track B3): every Radar series in the catalog, fetched with the Actions secret.

Writes <key>.csv (period,value) and meta.json (lastUpdated, normalization, confidence and annotations per request
window) into out_dir, and prints one compact line per series to the log:

    RADAR {"key": ..., "start": "<first W-SUN period>", "values": [...], "last_updated": ...}

The log line is how a session without access to the artifact blob host reads the result
(`cloudflare_radar.from_log`). Everything here is a public Radar aggregate (shares in per cent).
"""

from __future__ import annotations

import json
from pathlib import Path

from ai_tracker.series.cloudflare_radar import QUERIES
from ai_tracker.sources import cloudflare_radar as cf


def run(out_dir: Path) -> None:
    meta, failed = {}, {}
    for key, q in QUERIES.items():
        try:
            s, metas = cf.fetch_query(q)
        except Exception as exc:  # noqa: BLE001 - report every series, fail at the end
            failed[key] = f"{type(exc).__name__}: {str(exc)[:300]}"
            print(f"RADAR_FAILED {key} {failed[key]}")
            continue
        cf.write_job_csv(out_dir, key, s)
        meta[key] = metas
        print(cf.log_line(key, s, metas))
    (out_dir / "meta.json").write_text(json.dumps({"series": meta, "failed": failed}, indent=1, default=str),
                                       encoding="utf-8")
    if failed:
        raise SystemExit(f"{len(failed)} Radar series failed: {sorted(failed)}")
