"""The front end's asOf (web/src/lib/series/versions.ts) is tested in vitest against a golden file made by Python's
reference replay (site_bundle.vintages.replay). This keeps that golden file current with the committed fixtures."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "web" / "fixtures" / "gen_series_asof_golden.py"


def _gen():
    spec = importlib.util.spec_from_file_location("gen_series_asof_golden", GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_asof_golden_is_current():
    gen = _gen()
    assert gen.OUT.read_text(encoding="utf-8") == gen.render(), (
        "web/fixtures/series_asof_golden.json is stale: run PYTHONPATH=src python web/fixtures/gen_series_asof_golden.py")


def test_golden_covers_every_versioned_fixture_and_boundaries():
    g = _gen().golden()["series"]
    assert len(g) >= 15
    for key, probes in g.items():
        assert probes[0]["n"] == 0, f"{key}: the day before the first version must show nothing"
        assert probes[1]["n"] > 0, f"{key}: the first version day itself must count (known_from == D)"
