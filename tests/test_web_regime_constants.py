"""The web pages /avstamningar and /regim (track W10) mirror registered constants that the site bundle does not carry:
the A5 reconciliation terms and the C4 rule thresholds. These tests fail if the mirrors drift from the Python code
that implements the register (docs/mattregister.md A5 and G-D)."""

import json
from pathlib import Path


from ai_tracker.regime import bocpd, live, realtime
from ai_tracker.series import avstamning

WEB = Path(__file__).resolve().parents[1] / "web" / "src" / "lib" / "regime"


def _term(t) -> dict:
    # A weight other than 1 is part of the term (P2b: r on ppe_net_hyp4). A mirror without it splits the
    # capital-cost pace into wrong numerator and denominator parts, so it must fail here (review L1-1).
    d = {"series": t.series, "window": t.window}
    if t.weight != 1.0:
        d["weight"] = t.weight
    return d


def _want() -> list[dict]:
    return [{"key": r.key, "num": [_term(t) for t in r.num], "den": [_term(t) for t in r.den], "scale": r.scale}
            for r in avstamning.RECONS]


def test_the_mirror_contract_carries_the_weights():
    """A mirror of x_capcost_rev_r08/_r12 without the weight differs from the contract (L1-1)."""
    want = {d["key"]: d for d in _want()}
    for key, r in (("x_capcost_rev_r08", 0.08), ("x_capcost_rev_r12", 0.12)):
        weighted = [t for t in want[key]["num"] if "weight" in t]
        assert weighted == [{"series": "ppe_net_hyp4", "window": 1, "weight": r}]
        unweighted = {**want[key], "num": [{"series": t["series"], "window": t["window"]} for t in want[key]["num"]]}
        assert unweighted != want[key]
    # the five A5 reconciliations of 2026-11-23 have no weight, so the existing mirror still matches
    assert all("weight" not in t for d in _want() if d["key"] in ("x_capex_cloud", "x_rpo_cover", "x_nvda_capex",
                                                                    "x_debt_capex", "x_capex_ocf")
               for t in d["num"] + d["den"])


def test_reconciliation_terms_match_avstamning():
    # Every reconciliation the page mirrors has avstamning's terms, in avstamning's order (integration of run 13:
    # split from the completeness check below, so that drift in the existing five is still caught).
    defs = json.loads((WEB / "reconciliations.json").read_text(encoding="utf-8"))["reconciliations"]
    want = {d["key"]: d for d in _want()}
    assert [d["key"] for d in defs] == [k for k in want if k in {d["key"] for d in defs}]
    for d in defs:
        assert d == want.get(d["key"]), d["key"]


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
