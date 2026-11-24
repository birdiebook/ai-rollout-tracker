"""Golden replay for the front end's asOf (web/src/lib/series/versions.ts), from Python's reference replay.

For every series in web-data-fixtures/ and a set of probe days (for the first, a middle and the last version day: the
day before, the day itself and the day after)
this writes what `ai_tracker.site_bundle.vintages.replay` returns: per probe day (ascending) the number of known periods
and the [index into versions.periods, value] pairs that differ from the previous probe (replay only adds or replaces). vitest (versions.test.ts) checks that asOf gives exactly the same; pytest
(tests/test_web_series_asof.py) checks that the committed file is current.

Usage: PYTHONPATH=src python web/fixtures/gen_series_asof_golden.py [out]   (deterministic)
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

from ai_tracker.site_bundle.vintages import replay

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "web-data-fixtures" / "series"
OUT = Path(__file__).resolve().parent / "series_asof_golden.json"


def _shift(day: str, n: int) -> str:
    return str(date.fromisoformat(day) + timedelta(days=n))


def probes(v: dict) -> list[str]:
    ds = v["dates"]
    picks = sorted({ds[0], ds[len(ds) // 2], ds[-1]})
    out = {_shift(ds[0], -1), ds[0], _shift(ds[-1], 1)}
    for d in picks:
        out |= {_shift(d, -1), d, _shift(d, 1)}
    return sorted(out)


def golden() -> dict:
    series = {}
    for f in sorted(FIXTURES.glob("*.json")):
        if f.name == "index.json":
            continue
        doc = json.loads(f.read_text(encoding="utf-8"))
        v = doc.get("versions")
        if not v:
            continue
        snaps, prev = [], {}
        for day in probes(v):
            got = replay(v, day)
            assert set(prev) <= set(got), "replay never forgets a period"
            changed = [[i, got[p]] for i, p in enumerate(v["periods"]) if p in got and prev.get(p) != got[p]]
            snaps.append({"day": day, "n": len(got), "changed": changed})
            prev = got
        series[doc["key"]] = snaps
    return {"about": "vintages.replay of web-data-fixtures at probe days; see gen_series_asof_golden.py", "series": series}


def render() -> str:
    return json.dumps(golden(), ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    out.write_text(render(), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1024:.1f} kB)")
