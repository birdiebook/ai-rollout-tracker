"""W9 time travel: the front end's cut of today's bundle (web/src/lib/timetravel/gate.ts) is tested in vitest
against a golden file made by Python's replay ON each probe day (web/fixtures/gen_timetravel_golden.py:
vintages.encode(rows, D), observations.as_of(key, D), site.data.Record(today=D) with only the snapshots dated
<= D). This keeps that golden file current with the committed fixtures, and checks that it covers the boundaries."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "web" / "fixtures" / "gen_timetravel_golden.py"


def _gen():
    spec = importlib.util.spec_from_file_location("gen_timetravel_golden", GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_timetravel_golden_is_current():
    gen = _gen()
    assert gen.OUT.read_text(encoding="utf-8") == gen.render(), (
        "web/fixtures/timetravel_golden.json is stale: run PYTHONPATH=src python web/fixtures/gen_timetravel_golden.py")


def test_golden_covers_month_ends_live_snapshot_and_build_day():
    import json

    g = json.loads(_gen().OUT.read_text(encoding="utf-8"))
    by_day = {p["day"]: p for p in g["probes"]}
    assert by_day["2025-06-29"]["record"] is None  # the day before the first month end: no record
    assert by_day["2025-06-30"]["record"]["month"] == "2025-06"  # the month end itself counts
    assert by_day["2026-10-30"]["record"]["kind"] == "rekonstruerad"  # the day before the live snapshot
    assert by_day["2026-10-31"]["record"]["kind"] == "skarp"  # the live snapshot from its date
    n = {d: sum((s["versions"] or {}).get("n", 0) for s in p["series"].values()) for d, p in by_day.items()}
    days = sorted(n)
    assert all(n[a] <= n[b] for a, b in zip(days, days[1:])), "versions only grow with the day"
    assert n["2026-11-13"] < n["2026-11-14"], "a version day itself counts (known_from == D)"
