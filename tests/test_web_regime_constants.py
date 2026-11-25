"""The web pages /avstamningar and /regim (track W10) mirror registered constants that the site bundle does not carry:
the A5 reconciliation terms and the C4 rule thresholds. These tests fail if the mirrors drift from the Python code
that implements the register (docs/mattregister.md A5 and G-D)."""

import json
from pathlib import Path

from ai_tracker.regime import bocpd, live, realtime
from ai_tracker.series import avstamning

WEB = Path(__file__).resolve().parents[1] / "web" / "src" / "lib" / "regime"


def test_reconciliation_terms_match_avstamning():
    defs = json.loads((WEB / "reconciliations.json").read_text(encoding="utf-8"))["reconciliations"]
    want = [{"key": r.key, "num": [{"series": t.series, "window": t.window} for t in r.num],
             "den": [{"series": t.series, "window": t.window} for t in r.den], "scale": r.scale}
            for r in avstamning.RECONS]
    assert defs == want


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
