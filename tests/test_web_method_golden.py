"""The method page's engine (web/src/lib/method/engine.ts) is tested in vitest against a golden file made by the
Python engine (state.branch with the dead band moved, nowcast.intervals, evaluation.holm). This keeps that golden file
current with the engine and the committed fixtures, and checks that it agrees with the fixtures at the registered
dead band (so the page's "registrerat" is the pipeline's number)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "web" / "fixtures" / "gen_method_golden.py"
FIXTURES = ROOT / "web-data-fixtures"


def _gen():
    spec = importlib.util.spec_from_file_location("gen_method_golden", GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_method_golden_is_current():
    gen = _gen()
    assert gen.OUT.read_text(encoding="utf-8") == gen.render(), (
        "web/fixtures/method_golden.json is stale: run PYTHONPATH=src python web/fixtures/gen_method_golden.py")


def test_golden_at_registered_deadband_is_the_fixture_record():
    g = json.loads(_gen().OUT.read_text(encoding="utf-8"))["deadband"]
    assert g["registered"] == 0.25
    for code, rows in g["branches"].items():
        reg = next(r for r in rows if r["k"] == g["registered"])
        doc = json.loads((FIXTURES / "branch" / f"{code}.json").read_text(encoding="utf-8"))
        assert doc["state"] == reg["state"], code
        assert (doc["index"] is None and reg["index"] is None) or abs(doc["index"] - reg["index"]) < 1e-12, code
        assert (doc["n_up"], doc["n_neutral"], doc["n_down"]) == (reg["n_up"], reg["n_neutral"], reg["n_down"]), code
        for s in doc["counted"]:
            assert reg["directions"][s["key"]] == s["direction"], (code, s["key"])


def test_golden_moves_states_and_registered_value_is_unchanged_after():
    from ai_tracker.state import register as R

    g = json.loads(_gen().OUT.read_text(encoding="utf-8"))
    assert R.DEADBAND == 0.25  # the generator restores the registered value
    states = {r["state"] for rows in g["deadband"]["branches"].values() for r in rows}
    assert {"bromsar in", "stabil"} <= states  # the probes cross at least one threshold
    widths = {w["w"]: w["hits"] for w in g["intervals"]["by_width"]}
    assert widths[0.5]["80"] < widths[1.0]["80"] < widths[2.0]["80"]
