"""X25: fixes after R28 (register 2026-11-26 "X25"). Synthetic data only.

- seen data per reading (point 1): an unchanged reading after the register day keeps the note, a reading that rests on
  a value known after the register day is marked unseen, and a new vintage with the same value is not new
- acquisitions (point 2): every acquisition that touches a quarter, with its direction
- antenner (point 3): the main readings' inputs, and the note when two questions rest on the same series
- how often the rule could be tried (point 4): Y in the whole window, impulses read against Y, the untested direction
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

from ai_tracker.followed import antenner as AN
from ai_tracker.followed import betalningsgapet as B
from ai_tracker.followed import common as C
from ai_tracker.followed import elflaskhalsen as E
from ai_tracker.followed import ledtid as L

sys.path.insert(0, str(Path(__file__).parent))
import test_followed_betalningsgapet as TB  # noqa: E402
import test_followed_elflaskhalsen as TE  # noqa: E402
import test_followed_ledtid as TL  # noqa: E402

UNSEEN_NOTE = "ett utfall på osedda data"


@pytest.fixture
def _no_f1(monkeypatch):
    from ai_tracker.series import guidance_revisions as F1

    monkeypatch.setattr(F1, "load_csv", lambda: None)


def _row(series: str, period: str, value: float, kf: str) -> pd.DataFrame:
    return pd.DataFrame([{"series": series, "freq": "Q", "period": period, "value": float(value),
                          "known_from": pd.Timestamp(kf), "source": "release", "fetched_at": pd.Timestamp(kf)}])


# ------------------------------------------------------------------ point 1: seen data per reading


def test_resting_on_decided_and_undecided():
    r = C.read_rule({"2026Q1": 12.0, "2026Q2": 0.0}, {"2026Q2": 6.0, "2026Q3": 0.0}, g=10, h=5, k=2, t="2026Q3")
    assert r["outcome"] == C.FOR and C.resting_on(r) == (["2026Q1"], ["2026Q2"])
    n = C.read_rule({"2026Q1": 1.0, "2026Q2": 0.0}, {"2026Q2": 6.0, "2026Q3": 0.0}, g=10, h=5, k=2, t="2026Q3")
    assert n["outcome"] == C.NEITHER and C.resting_on(n) == (["2026Q1", "2026Q2"], ["2026Q2", "2026Q3"])
    x, y = {"2026Q1": 12.0, "2026Q2": 0.0}, {"2026Q2": 6.0, "2026Q3": 0.0}
    assert C.same_inputs(r, x, y, dict(x), {"2026Q2": 6.0})  # Y at 2026Q3 is not what the outcome rests on
    assert not C.same_inputs(r, x, y, x, {"2026Q2": 5.0})  # a revision of the deciding quarter
    assert not C.same_inputs(n, x, y, x, {"2026Q2": 6.0})  # the window's last quarter is new


def test_lt1_marks_the_reading_with_a_new_quarter_unseen_and_keeps_the_main_note(_no_f1):
    w = TL._world(("2025Q1", 0.02, 0.06), ("2025Q3", 0.03, 0.08))
    eq = TL._rows("rpo_eqix", {q: 100.0 for q in TL.QS})
    late = _row("rpo_eqix", "2026Q4", 100.0, "2026-12-10")
    r = L.compute("2026-12-15", pd.concat([w, eq, late], ignore_index=True))
    unseen = {(x["row"], x["buyer"], x["direction"], x["k"]) for x in r["readings"] if not x["seen"]}
    assert unseen and all(u[0] == "L3" and u[2] == "efter" for u in unseen)  # Y = Equinix got 2026Q4
    assert r["main_seen"] is True and r["seen_before_register"] is False
    text = L.render(r)
    assert C.SEEN_NOTE in text and "· **osedd**" in text and f"{len(unseen)} av 24 läsningar" in text
    assert L.antenna(r)["facts"]["Huvudläsningen på osedda data"] == "nej"


def test_lt1_main_reading_unseen_with_a_new_buyer_quarter(_no_f1):
    qs = [q for q in TL.QS if q <= "2026Q2"]
    w = TL._world(("2025Q4", 0.02, 0.12), ("2026Q1", 0.02, 0.12), qs=qs)
    new = []
    for c in TL.INNER:  # 2026Q3 for the inner layer and for L1 arrives after the register day
        new.append(_row(f"capex_{c}", "2026Q3", w[(w.series == f"capex_{c}") & (w.period == "2026Q2")].value.iloc[0]
                        * 1.13, "2026-12-01"))
    for c in ("etn", "pwr"):
        new.append(_row(f"rpo_{c}", "2026Q3", w[(w.series == f"rpo_{c}") & (w.period == "2026Q2")].value.iloc[0] * 1.13,
                        "2026-12-01"))
    r = L.compute("2026-12-15", pd.concat([w, *new], ignore_index=True))
    main = L.find(r, *L.MAIN)
    assert main["t"] == "2026Q3" and main["seen"] is False and r["main_seen"] is False
    assert UNSEEN_NOTE in L.render(r)
    assert L.antenna(r)["facts"]["Huvudläsningen på osedda data"] == "ja"


def test_el1_new_vintage_with_the_same_value_is_not_new_but_a_new_quarter_is():
    w = TE.world()
    same = w[(w["series"] == "rpo_pwr") & (w["period"] == "2026Q3")].assign(known_from=pd.Timestamp("2026-12-01"))
    r = E.compute("2026-12-15", pd.concat([w, same], ignore_index=True))
    assert r["seen_before_register"] is True and C.SEEN_NOTE in E.render(r)
    cap = w[(w["series"] == E.CAPEX_INNER) & (w["period"] == "2026Q3")].iloc[0]
    q4 = _row(E.CAPEX_INNER, "2026Q4", cap["value"] * 1.1, "2027-01-31")
    r = E.compute("2027-02-05", pd.concat([w, q4], ignore_index=True))
    assert r["main_seen"] is False and r["readings"]["nat|capex"]["t"] == "2026Q4"
    assert UNSEEN_NOTE in E.render(r) and E.antenna(r)["facts"]["Huvudläsningen på osedda data"] == "ja"


def test_bg1_unseen_after_a_new_quarter_for_every_company():
    w = TB.world()
    last = w.sort_values("period").groupby("series").tail(1)
    nxt = last.assign(period=[C.plus(p, 1) for p in last["period"]], value=last["value"] * 1.05,
                      known_from=pd.Timestamp("2027-02-10"))
    r = B.compute("2027-02-15", pd.concat([w, nxt], ignore_index=True))
    assert r["main_seen"] is False and "**Osedd:**" in B.render(r)
    assert B.compute("2026-12-31", w)["seen_before_register"] is True


# ------------------------------------------------------------------ point 2: acquisitions


def test_l1_lists_both_acquisitions_at_2026q2_with_their_directions():
    marks = L.acquisition_quarters("L1")
    assert marks["2026Q2"] == "Eaton–Fibrebond a + 4, ned; Eaton–Boyd Thermal a + 1, upp"
    assert marks["2025Q2"] == "Eaton–Fibrebond a, upp" and marks["2026Q3"] == "Eaton–Fibrebond a + 5, ned"
    assert "2026Q1" in marks and marks["2026Q1"] == "Eaton–Boyd Thermal a, upp"


# ------------------------------------------------------------------ point 3: antenner


def test_antenner_notes_main_readings_on_the_same_series():
    pair = {"x": ["rpo_etn", "rpo_pwr"], "y": ["capex_msft", "capex_googl"], "x_stat": "takt", "sign": 1}

    def mod(name, inputs):
        m = type(sys)(name)
        m.QUESTION = f"Fråga {name}?"
        m.compute = lambda as_of: {}
        m.render = lambda r: ""
        m.antenna = lambda r: C.antenna_row(m.QUESTION, C.FOR, "talar för", "2026Q3", {}, "–", None, inputs)
        return m

    mods = {"a": mod("a", pair), "b": mod("b", {**pair, "sign": -1}), "c": mod("c", {**pair, "x": ["rpo_eqix"]}),
            "d": mod("d", None)}
    r = AN.compute("2026-11-26", modules=mods)
    text = AN.render(r)
    assert "## Samma serier i flera frågor" in text
    assert "**a och b** har samma huvudpar" in text and "inte mer än en observation" in text
    assert "**a och c** läser samma Y" in text and "**b och c** läser samma Y" in text
    assert "**a och d**" not in text and "**c och d**" not in text


def test_lt1_and_el1_declare_the_same_main_pair(_no_f1):
    w = TE.world()
    lt = L.antenna(L.compute("2026-11-26", w))["main_inputs"]
    el = E.antenna(E.compute("2026-11-26", w))["main_inputs"]
    assert lt["x"] == el["x"] == ["rpo_etn", "rpo_pwr"]
    assert lt["y"] == el["y"] == sorted(f"capex_{c}" for c in ("msft", "googl", "amzn", "meta"))
    assert (lt["sign"], el["sign"]) == (1, -1)
    bg = B.antenna(B.compute("2026-11-26", TB.world()))["main_inputs"]
    assert set(bg["y"]) & set(lt["y"]) and set(bg["y"]) != set(lt["y"])


# ------------------------------------------------------------------ point 4: how often the rule could be tried


def test_history_counts_y_in_the_window_and_the_untested_direction():
    qs = [str(q) for q in pd.period_range("2020Q1", "2026Q3", freq="Q-DEC")]
    x = {q: 12.0 for q in qs}  # an impulse up at every origin, never down
    y = {q: 1.0 for q in qs if q >= "2025Q1"}  # Y only from 2025Q1
    r = C.read_rule(x, y, g=10, h=5, k=2, t="2026Q3")
    h = r["history"]
    assert h["n_x"] == len(qs) - 1 and h["impulses_down"] == 0
    assert h["n_y_window"] == sum(1 for q in qs[:-1] if q >= "2024Q4" and C.plus(q, 2) <= "2026Q3")
    assert h["n_impulse_read"] == h["n_tested"] and h["n_impulse_read"] < h["n_x"]
    lines = C.reading_lines(r, "X")
    assert "Riktningen nedåt har inte prövats" in lines[2] and f"i {h['n_y_window']} av {h['n_x']}" in lines[2]
    none = C.read_rule({q: 0.0 for q in qs}, y, g=10, h=5, k=2, t="2026Q3")
    assert "Ingen riktning har prövats" in C.tried_note(none["history"])
    assert h["n_tested"] == h["n_x"] - h["by_direction"]["up"][C.UNDECIDED]  # F0 (b)'s count is unchanged
