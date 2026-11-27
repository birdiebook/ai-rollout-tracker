"""S1: symmetric rows beside locked rules (register 2026-11-27 "S1"). Synthetic data, plus real-data checks.

- the register entry is committed and unchanged, and the modules use its parameters
- F0's count (point 3): an origin is tried only when Y is in the window; the old count stays beside it, outcomes unchanged
- KL1-S (point 1): one row per entity and price/dependence measure, sign -1, both directions; the locked part of the
  report is byte for byte the same, and the antenna's main reading is unchanged
- EL1-S (point 2): the backlog's change in pace can give an impulse downward where the locked row (pace) cannot; it is
  LT1's main reading with the opposite sign
- seen data per row (point 4): a quarter known after 2026-11-27 makes a row unseen
"""

from __future__ import annotations

import hashlib
import math

import numpy as np
import pandas as pd
import pytest

from ai_tracker import config
from ai_tracker.followed import common as C
from ai_tracker.followed import elflaskhalsen as E
from ai_tracker.followed import kreditlagret as F
from ai_tracker.state import measures as M
from tests import test_followed_elflaskhalsen as TE

REGISTER = config.REPO / "docs" / "mattregister.md"
ENTRY = "### 2026-11-27 – S1: symmetriska rader bredvid låsta regler"


# ------------------------------------------------------------------ register


def _entry() -> str:
    text = REGISTER.read_text(encoding="utf-8")
    assert text.count(ENTRY) == 1
    return text.split(ENTRY, 1)[1].split("\n### ", 1)[0]


def test_register_entry_is_locked_and_matches_the_modules():
    entry = _entry()
    assert hashlib.sha256(entry.encode("utf-8")).hexdigest() == PINNED
    for want in ("*h* = 5 log × 100", "*k* = 2 kvartal", "Tecken *s* = −1", "Det är 18 rader",
                 "*g* = 10 log × 100", "**prövat** bara när Y finns i fönstret",
                 "**Övergångsnotis:**", "registerdagen 2026-11-27"):
        assert want in entry, want
    assert C.S1_REGISTERED == F.S1_REGISTERED == E.S1_REGISTERED == "2026-11-27"
    assert (F.S1_H, F.S1_K, F.S1_SIGN) == (5.0, 2, -1) and F.LIMIT == {"rate_eff": 0.25, "fcfgap": 5.0,
                                                                         "netdebt": 5.0, "leases": 5.0}
    assert F.S1_ENTITIES == ("outer", "inner", "orcl", "crwv", "nbis", "iren")
    assert sum(len(F.measures_of(e)) for e in F.S1_ENTITIES) == 18
    assert (E.S1_X, E.S1_Y, E.S1_G) == ("el1_ob_nat", "kl_capex4_inner", 10.0) and E.H["capex"] == 5.0
    # the locked rows are untouched
    assert E.MAIN == ("nat", "capex") and len(E.PAIRS) == 8 and E.G["nat"] == 10.0


PINNED = "74010d0ffd50fb97875580f4930feed3e7f36d1b3b0f879bc4377bfe2241cf37"  # the entry as committed in 654cbc0


# ------------------------------------------------------------------ point 3: the count of tried origins


def test_tried_needs_y_in_the_window_and_the_old_count_stays_beside_it():
    qs = [str(q) for q in pd.period_range("2020Q1", "2026Q3", freq="Q-DEC")]
    x = {q: (12.0 if q in ("2025Q1", "2026Q1") else 0.0) for q in qs}  # two impulses up, the rest without
    y = {q: 6.0 for q in qs if q >= "2024Q3"}  # Y only from 2024Q3
    r = C.read_rule(x, y, g=10, h=5, k=2, t="2026Q3")
    h = r["history"]
    no_imp = [q for q in qs[:-1] if x[q] == 0.0]
    with_y = [q for q in no_imp if all(C.plus(q, j) in y for j in (1, 2)) and C.plus(q, 2) <= "2026Q3"]
    assert h["n_tested"] == h["n_x"] == len(qs) - 1  # F0 before S1: every origin without impulse counted
    assert h["n_tried"] == 2 + len(with_y) < h["n_tested"]
    lines = C.reading_lines(r, "X")
    assert f"kunde prövas i {h['n_tried']} av {h['n_x']}" in lines[1]
    assert lines[3].startswith("  Övergång (registret 2026-11-27 S1, punkt 3)")
    assert f"före S1: {h['n_tested']} av {h['n_x']}; med den nya: {h['n_tried']} av {h['n_x']}" in lines[3]


def test_new_count_is_symmetric_and_never_above_the_old_and_outcomes_do_not_move():
    rng = np.random.default_rng(27)
    qs = [str(q) for q in pd.period_range("2019Q1", "2026Q3", freq="Q-DEC")]
    for _ in range(100):
        x = {q: float(v) for q, v in zip(qs, rng.normal(0, 3, len(qs)))}
        y = {q: float(v) for q, v in zip(qs, rng.normal(0, 3, len(qs))) if rng.random() > 0.2}
        a = C.read_rule(x, y, g=2, h=1, k=2, t=qs[-1])
        b = C.read_rule({q: -v for q, v in x.items()}, {q: -v for q, v in y.items()}, g=2, h=1, k=2, t=qs[-1])
        ha, hb = a["history"], b["history"]
        assert ha["n_tried"] == hb["n_tried"] <= ha["n_tested"]
        assert ha["n_tested"] == ha["n_x"] - sum(ha["by_direction"][d][C.UNDECIDED] for d in ("up", "down"))
        imp_read = ha["n_impulse_read"]
        assert ha["n_tried"] - imp_read == sum(  # without impulse: Y known in all k quarters
            1 for q in qs[:-1] if abs(x[q]) < 2 and all(C.plus(q, j) in y for j in (1, 2)))


# ------------------------------------------------------------------ point 1: KL1-S


def _qrows(series: str, values: dict[str, float], lag: int = 30) -> pd.DataFrame:
    return pd.DataFrame([{"series": series, "freq": "Q", "period": q, "value": float(v),
                          "known_from": pd.Period(q, freq="Q-DEC").end_time.normalize() + pd.Timedelta(days=lag),
                          "source": "release", "fetched_at": pd.Timestamp("2026-11-27")} for q, v in values.items()])


KQ = [str(q) for q in pd.period_range("2022Q1", "2025Q3", freq="Q-DEC")]


def _kl_ms(dep_jump: float, last_inc: float) -> dict:
    """Oracle's (capex - OCF) / capex flat at 50 % and stepping by `dep_jump` pp at 2025Q2; Oracle's capex over four
    quarters growing 10 log points a quarter and by `last_inc` in 2025Q3. Every other KL1 series is unavailable."""
    dep = {q: 50.0 + (dep_jump if q >= "2025Q2" else 0.0) for q in KQ}
    y, cap = 100 * math.log(1000.0), {}
    for q in KQ:
        y += last_inc if q == "2025Q3" else 10.0
        cap[q] = math.exp(y / 100)
    t = pd.concat([_qrows("kl_fcfgap_orcl", dep), _qrows("kl_capex4_orcl", cap)], ignore_index=True)
    ctx = M.Context(table=t)
    ms = {k: {"series": k, "available": False} for g in F.keys().values() for k in g}
    for k in ("kl_fcfgap_orcl", "kl_capex4_orcl"):
        ms[k] = C.measure(k, "2025-12-31", ctx)
    return ms


@pytest.mark.parametrize("jump,inc,want,direction", [
    (10.0, 0.0, C.FOR, 1),       # dependence rose, capex pace fell (change -10): talar för, uppåt
    (-10.0, 20.0, C.FOR, -1),    # dependence fell, capex pace rose (+10): talar för, nedåt
    (10.0, 20.0, C.AGAINST, 1),  # rose, then pace rose: talar emot, uppåt
    (-10.0, 0.0, C.AGAINST, -1),  # fell, then pace fell: talar emot, nedåt
    (3.0, 0.0, C.NEITHER, 0),    # |pace| < 5: no impulse
])
def test_kl1s_reads_both_directions(jump, inc, want, direction):
    rows = F.s1_rows(_kl_ms(jump, inc))
    assert len(rows) == 18 and [(x["entity"], x["measure"]) for x in rows][:4] == [
        ("outer", m) for m in F.PRICE_DEP]
    x = next(x for x in rows if (x["entity"], x["measure"]) == ("orcl", "fcfgap"))
    assert x["t"] == "2025Q3" and x["outcome"] == want and x["params"] == {"g": 5.0, "h": 5.0, "k": 2, "sign": -1}
    assert x["x_series"] == "kl_fcfgap_orcl" and x["y_series"] == "kl_capex4_orcl" and x["x_stat"] == "pace"
    if direction:
        o = next(o for o in x["origins"] if o["origin"] == x["origin"])
        assert o["origin"] == "2025Q2" and o["direction"] == direction
        assert C.short(x).endswith(", uppåt" if direction > 0 else ", nedåt")
    others = [y for y in rows if y is not x]
    assert all(y["outcome"] == C.UNDECIDED for y in others)


@pytest.fixture(scope="module")
def kl_world():
    from tests.test_kreditlagret import _report_world

    return _report_world()


def _csv():
    from ai_tracker.sources import kreditlagret as kl

    return pd.DataFrame(columns=kl.COLUMNS)


@pytest.mark.parametrize("day", ["2025-06-30", "2025-12-20", "2026-11-25"])
def test_kl1_locked_part_is_byte_identical_and_section_8_comes_after(kl_world, day, monkeypatch):
    from ai_tracker.series import guidance_revisions as F1

    monkeypatch.setattr(F1, "load_csv", lambda: None)
    r = F.compute(day, table=kl_world, csv=_csv())
    without = {**r, "s1": None}
    assert F.render(without) == F.render_locked(r)  # S1 adds nothing to sections 1-7
    text = F.render(r)
    head, tail = text.split("## 8. Tillägg S1: symmetrisk läsning bredvid den låsta", 1)
    assert head == F.render_locked(r) and "Avsnitt 1–7 ovan är den låsta läsningen" in tail
    for e in F.S1_ENTITIES:
        assert f"(Y = `kl_capex4_{e}`)" in tail
    assert tail.count("Övergång (registret 2026-11-27 S1, punkt 3)") == sum(
        1 for x in r["s1"]["rows"] if x["history"]["n_x"])
    assert all(x["seen"] for x in r["s1"]["rows"])  # up to the register day every row is seen


def test_kl1_antenna_main_reading_unchanged_and_s1_as_facts(kl_world, monkeypatch):
    from ai_tracker.series import guidance_revisions as F1

    monkeypatch.setattr(F1, "load_csv", lambda: None)
    r = F.compute("2025-12-20", table=kl_world, csv=_csv())
    a, b = F.antenna(r), F.antenna({**r, "s1": None})
    s1_keys = [k for k in a["facts"] if k.startswith("S1 symmetrisk, ")]
    assert len(s1_keys) == len(F.S1_ENTITIES) and list(a["facts"])[-len(s1_keys):] == s1_keys  # added after
    assert {k: v for k, v in a["facts"].items() if k not in s1_keys} == b["facts"]
    assert {k: v for k, v in a.items() if k != "facts"} == {k: v for k, v in b.items() if k != "facts"}


def test_kl1s_row_becomes_unseen_with_a_quarter_known_after_the_register_day():
    rows = F.s1_rows(_kl_ms(10.0, 0.0))
    ms = _kl_ms(10.0, 0.0)
    for x in rows:
        x["_mx"], x["_my"] = ms[x["x_series"]], ms[x["y_series"]]
    dep = {q: 50.0 + (10.0 if q >= "2025Q2" else 0.0) for q in KQ}
    t = pd.concat([_qrows("kl_fcfgap_orcl", dep), _qrows("kl_capex4_orcl", {q: 1.0 for q in KQ})])
    # on the register day Y was different (flat): the row's Y values are not the same, so it is unseen
    F.s1_seen(rows, "2026-12-31", M.Context(table=t))
    row = next(x for x in rows if (x["entity"], x["measure"]) == ("orcl", "fcfgap"))
    assert row["seen"] is False
    F.s1_seen(rows, "2026-11-27", M.Context(table=t))
    assert row["seen"] is True


# ------------------------------------------------------------------ point 2: EL1-S


def _el_world(y_last_inc: float = 20.0, extra: pd.DataFrame | None = None) -> pd.DataFrame:
    """TE.world with the grid backlog growing 10 log points a quarter to 2025Q4 and 4 a quarter after: its pace stays
    >= 22 (impulse up every quarter, never down), its change in pace falls to -12 at 2026Q2 (an impulse down)."""
    w = TE.world(20.0, y_last_inc)
    w = w[~w["series"].isin(["rpo_pwr", "rpo_etn"])]
    nat = TE._path({q: (10.0 if q <= "2025Q4" else 4.0) for q in TE.QS})
    parts = [w, TE._rows("rpo_pwr", "Q", {q: 0.6 * v for q, v in nat.items()}, TE._q_kf),
             TE._rows("rpo_etn", "Q", {q: 0.4 * v for q, v in nat.items()}, lambda q: TE._q_kf(q, 35))]
    if extra is not None:
        parts.append(extra)
    return pd.concat(parts, ignore_index=True)


def test_el1s_can_read_a_turn_downward_where_the_locked_row_cannot():
    r = E.compute("2026-11-27", table=_el_world(20.0))
    main, s1 = r["readings"]["nat|capex"], r["s1"]
    assert main["history"]["impulses_down"] == 0 and main["outcome"] == C.AGAINST  # pace +28 up, capex change +10
    assert s1["outcome"] == C.FOR and E.short(s1) == "talar för mekanismen, nedåt"  # change -12 down, capex +10
    assert s1["x_stat"] == "change" and s1["params"] == {"g": 10.0, "h": 5.0, "k": 2, "sign": -1}
    o = next(o for o in s1["origins"] if o["origin"] == s1["origin"])
    assert o["origin"] == "2026Q2" and o["direction"] == -1 and o["x"] == pytest.approx(-12.0)
    assert s1["history"]["impulses_down"] >= 1
    text = E.render(r)
    part = text.split("**Tillägg S1 (registret 2026-11-27 S1, punkt 2)", 1)[1].split("## 6. Att bevaka", 1)[0]
    assert "Riktningen nedåt har inträffat" in part and "LT1:s huvudläsning" in part
    assert text.index("**Tillägg S1") > text.index("(huvudläsning)")  # after the locked rows


def test_el1s_antenna_keeps_the_main_reading():
    r = E.compute("2026-11-27", table=_el_world(20.0))
    a, b = E.antenna(r), E.antenna({**r, "s1": None})
    assert {k: v for k, v in a.items() if k != "facts"} == {k: v for k, v in b.items() if k != "facts"}
    new = [k for k in a["facts"] if k.startswith("S1: ")]
    assert len(new) == 3 and {k: v for k, v in a["facts"].items() if k not in new} == b["facts"]
    assert a["facts"]["S1: orderstock elnät som förändring i takt mot capex inre lagret"] == \
        "talar för mekanismen, nedåt"


def test_el1s_unseen_after_the_register_day():
    nat_q4 = TE._path({q: (10.0 if q <= "2025Q4" else 4.0) for q in TE.QS})["2026Q3"] * math.exp(0.04)
    kf = pd.Timestamp("2027-01-30")
    extra = pd.concat([
        pd.DataFrame([{"series": s, "freq": "Q", "period": "2026Q4", "value": v, "known_from": kf, "source": "release",
                       "fetched_at": kf} for s, v in (("rpo_pwr", 0.6 * nat_q4), ("rpo_etn", 0.4 * nat_q4))]),
    ])
    w = _el_world(20.0, extra)
    cap = w[w["series"] == E.CAPEX_INNER].sort_values("period").iloc[-1]
    w = pd.concat([w, pd.DataFrame([{**cap.to_dict(), "period": "2026Q4", "value": cap["value"] * math.exp(0.1),
                                     "known_from": kf}])], ignore_index=True)
    assert E.compute("2026-11-27", table=w)["s1"]["seen"] is True
    late = E.compute("2027-02-15", table=w)
    assert late["s1"]["t"] == "2026Q4" and late["s1"]["seen"] is False


# ------------------------------------------------------------------ real data


@pytest.fixture(scope="module")
def real():
    from ai_tracker import observations

    t = observations.load()
    need = {"kl_capex4_inner", "kl_capex4_orcl", "rpo_pwr", "rpo_etn", "lt1_rpo_power"}
    if t.empty or not need <= set(t["series"]):
        pytest.skip("no real observation table with the KL1, EL1 and LT1 series")
    return t


@pytest.mark.real_data
@pytest.mark.parametrize("day", ["2026-11-27", "2025-11-27"])
def test_el1s_is_lt1s_main_reading_mirrored(real, day):
    from ai_tracker.followed import ledtid as L

    lt = L.compute(day, real)
    main = next(x for x in lt["readings"]
                if (x["row"], x["buyer"], x["direction"], x["k"]) == tuple(lt["main"]))
    s1 = E.compute(day, table=real)["s1"]
    flip = {C.FOR: C.AGAINST, C.AGAINST: C.FOR, C.NEITHER: C.NEITHER, C.UNDECIDED: C.UNDECIDED}
    assert s1["t"] == main["t"] and s1["outcome"] == flip[main["outcome"]]
    assert {o["origin"]: flip[o["outcome"]] for o in main["origins"]} == {o["origin"]: o["outcome"]
                                                                         for o in s1["origins"]}
    hm, hs = main["history"], s1["history"]
    assert (hm["impulses_up"], hm["impulses_down"]) == (hs["impulses_up"], hs["impulses_down"])
    for d in ("up", "down"):
        assert hm["by_direction"][d][C.FOR] == hs["by_direction"][d][C.AGAINST]
        assert hm["by_direction"][d][C.AGAINST] == hs["by_direction"][d][C.FOR]


@pytest.mark.real_data
def test_el1s_downward_impulses_occur_in_the_real_history(real):
    s1 = E.compute("2026-11-27", table=real)["s1"]
    main = E.compute("2026-11-27", table=real)["readings"]["nat|capex"]
    assert main["history"]["impulses_down"] == 0 and s1["history"]["impulses_down"] > 0


@pytest.mark.real_data
@pytest.mark.parametrize("day", ["2026-11-27", "2025-11-27"])
def test_kl1_locked_part_on_real_data_is_in_the_results_document(real, day):
    r = F.compute(day, real)
    doc = (config.REPO / "docs" / "resultat" / "kreditlagret.md").read_text(encoding="utf-8")
    locked = "\n".join(("#" + x) if x.startswith("#") else x for x in F.render_locked(r).split("\n"))
    assert locked.strip("\n") in doc
