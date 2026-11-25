"""Golden values for the explorable method page (web/src/lib/method/engine.ts), from the Python engine itself.

The method page lets the reader move the dead band, the interval level and the interval width. Everything the figures
show at a parameter value must be what the Python engine gives at that value, so nothing here is re-implemented:

- **Dead band.** `ai_tracker.state.branch.branch(code, when, ctx)` on the synthetic world of web-data-fixtures/
  (`site_bundle.synthetic.context`, the record date of the fixtures' live snapshot) with `register.DEADBAND`
  set to each probe value. At the registered 0.25 this is exactly what the fixtures' branch/<G>.json hold. Index v2
  (one vote per source family, the official rule) with each series' family and each family's vote, and v1 beside it.
- **Intervals.** `nowcast.intervals.ErrorDistribution` (G-C: Hyndman-Fan type 6 quantiles, mid-rank PIT,
  `pit_histogram`) and `binomial_band` on the illustration pool in web/src/lib/method/illustration.json, at every
  level the slider offers and for each width factor the calibration figure offers.
- **Holm.** `evaluation.holm` on a set of p-value families.

vitest (web/src/lib/method/engine.test.ts) checks that the TypeScript engine gives exactly the same; pytest
(tests/test_web_method_golden.py) checks that the committed file is current.

Usage: PYTHONPATH=src python web/fixtures/gen_method_golden.py            (deterministic)
       PYTHONPATH=src python web/fixtures/gen_method_golden.py --pool     (rewrite illustration.json, seed 90)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from ai_tracker import evaluation
from ai_tracker.nowcast import intervals as I
from ai_tracker.site_bundle import synthetic as SY
from ai_tracker.state import branch as BR
from ai_tracker.state import register as R

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "method_golden.json"
POOL = ROOT / "web" / "src" / "lib" / "method" / "illustration.json"
WHEN = "2026-10-31"  # the fixtures' live snapshot (synthetic.write_inputs)

# The dead-band slider's range and some values on each side of every branch's flip points.
DEADBANDS = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.75, 1.0, 1.25, 1.5, 2.0]
LEVELS = [round(0.5 + 0.05 * i, 2) for i in range(10)]  # 0.50 ... 0.95, the level slider
WIDTHS = [0.5, 0.6, 0.75, 0.9, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0]  # the width slider (forecast pool × factor)
BINOMIAL_N = list(range(1, 121)) + [150, 200, 238, 300]
HOLM = [
    {"B3": 0.04, "DF": 0.2},
    {"B2": 0.03, "B3": 0.04, "DF": 0.5},
    {"B2": 0.01, "B3": 0.08, "DF": 0.09},
    {"V1": 0.07},
    {"V1": 0.12, "DF": 0.02},
    {"B2": 0.6, "B3": 0.6, "DF": 0.6},
]


def write_pool() -> None:
    """The illustration pool: 40 past errors (n >= 40 gives the empirical distribution under G-C) and 80 later
    outcomes' errors, both from one Student t(5) with scale 4 (log x100). Invented numbers, labelled so on the page.
    The seed (90) was picked among 1-299 so that the unscaled pool is close to calibrated on the 80 outcomes: the
    figure is meant to show what too narrow and too wide look like against a calibrated reference."""
    rng = np.random.default_rng(90)
    pool = np.round(4.0 * rng.standard_t(5, 40), 2)
    outcomes = np.round(4.0 * rng.standard_t(5, 80), 2)
    doc = {"about": "Illustration only (invented errors, log x100): Student t(5) x 4, numpy default_rng(90). "
                    "Written by web/fixtures/gen_method_golden.py --pool.",
           "pool": [float(x) for x in pool], "outcomes": [float(x) for x in outcomes]}
    POOL.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")


def deadband_golden() -> dict:
    ctx = SY.context(Path("/nonexistent"))
    saved = R.DEADBAND
    out: dict[str, list] = {}
    try:
        for k in DEADBANDS:
            R.DEADBAND = k
            for code in SY.CORE:
                b = BR.branch(code, WHEN, ctx)
                out.setdefault(code, []).append({
                    "k": k, "index": b["index"], "state": b["state"], "n_series": b["n_series"],
                    "n_up": b["n_up"], "n_neutral": b["n_neutral"], "n_down": b["n_down"],
                    "rule_version": b["rule_version"], "n_families": b["n_families"],
                    "index_v1": b["v1"]["index"], "state_v1": b["v1"]["state"],
                    "votes": {f["family"]: f["vote"] for f in b["families"] if f["series"]},
                    "families": {m["series"]: m["family"] for m in b["series_used"]},
                    "directions": {m["series"]: m["direction"] for m in b["series_used"]}})
    finally:
        R.DEADBAND = saved
    return {"when": WHEN, "registered": saved, "branches": out}


def intervals_golden() -> dict:
    doc = json.loads(POOL.read_text(encoding="utf-8"))
    pool, outcomes = doc["pool"], doc["outcomes"]
    base = I.ErrorDistribution.from_pool(pool)
    assert base is not None and base.method == "empirical", "the illustration pool must use the empirical case"
    by_level = [{"level": L, "lo": base.interval(L)[0], "hi": base.interval(L)[1],
                 "inside": int(sum(base.covers(e, L) for e in pool))} for L in LEVELS]
    by_width = []
    for w in WIDTHS:
        dist = I.ErrorDistribution.from_pool([w * x for x in pool])
        pit = [dist.pit(e) for e in outcomes]
        by_width.append({"w": w, "hits": {I.level_key(L): int(sum(dist.covers(e, L) for e in outcomes)) for L in I.LEVELS},
                         "pit": pit, "pit_histogram": I.pit_histogram(pit)})
    bands = {I.level_key(L): [list(I.binomial_band(n, L)) for n in BINOMIAL_N] for L in [*I.LEVELS, *LEVELS]}
    return {"levels": LEVELS, "by_level": by_level, "by_width": by_width, "binomial_n": BINOMIAL_N,
            "binomial": bands, "n_pool": len(pool), "n_outcomes": len(outcomes)}


def golden() -> dict:
    return {"about": "Python engine values for web/src/lib/method/engine.ts; see web/fixtures/gen_method_golden.py",
            "deadband": deadband_golden(), "intervals": intervals_golden(),
            "holm": [{"p": p, "adjusted": evaluation.holm(p)} for p in HOLM]}


def render() -> str:
    return json.dumps(golden(), ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"


if __name__ == "__main__":
    if "--pool" in sys.argv[1:]:
        write_pool()
    OUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
