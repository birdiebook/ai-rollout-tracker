"""The web pages /avstamningar and /regim (track W10) mirror registered constants that the site bundle does not carry:
the A5 reconciliation terms and the C4 rule thresholds. These tests fail if the mirrors drift from the Python code
that implements the register (docs/mattregister.md A5 and G-D)."""

import json
from pathlib import Path

import pytest

from ai_tracker.regime import bocpd, live, realtime
from ai_tracker.series import avstamning

WEB = Path(__file__).resolve().parents[1] / "web" / "src" / "lib" / "regime"


def _want() -> list[dict]:
    return [{"key": r.key, "num": [{"series": t.series, "window": t.window} for t in r.num],
             "den": [{"series": t.series, "window": t.window} for t in r.den], "scale": r.scale}
            for r in avstamning.RECONS]


def test_reconciliation_terms_match_avstamning():
    # Every reconciliation the page mirrors has avstamning's terms, in avstamning's order (integration of run 13:
    # split from the completeness check below, so that drift in the existing five is still caught).
    defs = json.loads((WEB / "reconciliations.json").read_text(encoding="utf-8"))["reconciliations"]
    want = {d["key"]: d for d in _want()}
    assert [d["key"] for d in defs] == [k for k in want if k in {d["key"] for d in defs}]
    for d in defs:
        assert d == want.get(d["key"]), d["key"]


@pytest.mark.xfail(strict=True, reason="P2b (run 13) added x_dep_rev, x_capcost_rev_r08/_r12, x_dep_capex and "
                                       "x_dep_rev_aws; web/src/lib/regime/reconciliations.json (web session) does "
                                       "not mirror them yet, and the capital-cost terms carry a weight (r on "
                                       "ppe_net_hyp4) that the mirror has no field for")
def test_web_mirrors_every_reconciliation():
    defs = json.loads((WEB / "reconciliations.json").read_text(encoding="utf-8"))["reconciliations"]
    assert [d["key"] for d in defs] == [r.key for r in avstamning.RECONS]


def test_regime_rules_match_c4_code():
    rules = json.loads((WEB / "rules.json").read_text(encoding="utf-8"))
    assert rules["shift_at_least"] == realtime.HIGH
    assert rules["back_at_most"] == realtime.LOW
    assert rules["break_at_least"] == bocpd.THRESHOLD
    assert rules["break_run_length_at_most"] == bocpd.RECENT
    for freq, frac in rules["hazard"].items():
        num, den = frac.split("/")
        assert abs(int(num) / int(den) - bocpd.HAZARD[freq]) < 1e-12
    assert rules["first_live"] == str(live.FIRST_LIVE.date())
