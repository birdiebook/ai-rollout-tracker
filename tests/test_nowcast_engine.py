"""Shared rolling-origin engine (ai_tracker.nowcast.engine): first vintage, vintage dates, outcome guard, promotion
rule. The nowcast-specific behaviour is tested in test_nowcast_n1.py, test_nowcast_n2.py, test_b2.py and
test_r1_leakage.py."""

from __future__ import annotations

import pandas as pd

from ai_tracker import observations
from ai_tracker.nowcast import engine


def _table():
    rows = [("2020-01", 1.0, "2020-02-10"), ("2020-01", 1.5, "2020-03-10"), ("2020-02", 2.0, "2020-03-10"),
            ("2020-02", 2.5, "2020-05-01")]
    return pd.DataFrame({"series": "s", "freq": "M", "period": [r[0] for r in rows], "value": [r[1] for r in rows],
                         "known_from": pd.to_datetime([r[2] for r in rows]), "source": "x",
                         "fetched_at": pd.Timestamp("2026-11-23")})


def test_first_vintage_is_the_earliest_row_never_a_revision():
    t = _table()
    fv = engine.first_vintages(t, "s")
    assert list(fv["value"]) == [1.0, 2.0]
    assert list(fv["known_from"]) == list(pd.to_datetime(["2020-02-10", "2020-03-10"]))
    assert engine.first_vintage(t, "s").to_dict() == fv["value"].to_dict()
    assert engine.first_known_from(t, "s").equals(fv["known_from"])
    assert engine.first_vintage(t, "missing").empty


def test_vintage_known_from_matches_as_of_selection():
    t = _table()
    for origin in ("2020-02-10", "2020-03-10", "2020-04-30", "2020-05-01"):
        kf = engine.vintage_known_from(t, pd.Timestamp(origin))
        s = observations.as_of("s", origin, t)
        assert list(kf.index) == list(s.index)
        for p in s.index:  # the value as_of returns is the one from the vintage dated kf[p]
            row = t[(t["period"] == str(p)) & (t["known_from"] == kf[p])]
            assert float(row["value"].iloc[0]) == s[p]


def test_outcome_known_at_origin_is_never_scored():
    fv = engine.first_vintages(_table(), "s")
    p = pd.Period("2020-01", "M")
    assert engine.known_at_origin(fv, p, pd.Timestamp("2020-02-10"), "s 2020-01") == "s 2020-01 (filed 2020-02-10)"
    assert engine.known_at_origin(fv, p, pd.Timestamp("2020-02-09"), "s 2020-01") is None


def test_promotion_rule_and_review_gate():
    ok = engine.period_check(5.0, 6.0, 0.01)
    assert ok == {"holm_p": 0.01, "holm_ok": True, "mae": 5.0, "best_mae": 6.0, "mae_ok": True}
    assert engine.passes({"full": ok, "sub": engine.period_check(5.0, 6.0)})  # no Holm test in this period
    assert not engine.passes({"full": ok, "sub": engine.period_check(5.0, 6.0, 0.2)})
    assert not engine.passes({"full": ok, "sub": engine.period_check(6.0, 6.0)})  # equal MAE is not lower
    mae = {"V1": 5.0, "B2": 4.0}
    d = engine.decide({"V1": True, "B2": True}, mae, {})
    assert d.champion == "B2" and d.winners == ["V1", "B2"] and d.conditional == {}
    d = engine.decide({"V1": True, "B2": True}, mae, {"B2": "waiting for review"})
    assert d.champion == "V1" and d.conditional == {"B2": "waiting for review"}
    d = engine.decide({"V1": False, "B2": True}, mae, {"B2": "waiting for review"}, default="B1")
    assert d.champion == "B1" and d.winners == []
    assert engine.best_baseline({"B0": 2.0, "B1": 2.0}) == "B0" and engine.best_baseline({"B0": 3.0, "B1": 2.0}) == "B1"
