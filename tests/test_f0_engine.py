"""F0: the shared engine of the followed questions (register 2026-11-26 "F0"). Synthetic data only.

- aggregate: layer sums, a version only once every member has filed, the missing members of a period
- common: path_measures equals state.measures, the symmetric reading rule (truth table, symmetry, history counts)
- discovery: a module with compute and render is a question without touching __main__.py
- antenner: rows, changes against last month, a question without antenna or with an error
- KL1: its report on the synthetic world is byte-identical to the golden files rendered with the code before F0
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ai_tracker import followed
from ai_tracker.followed import __main__ as CLI
from ai_tracker.followed import aggregate as A
from ai_tracker.followed import antenner as AN
from ai_tracker.followed import common as C
from ai_tracker.followed import kreditlagret as F
from ai_tracker.series import kreditlagret as S
from ai_tracker.state import measures as M

GOLDEN = Path(__file__).parent / "golden"


def _rows(series: str, values: dict[str, float], kf: dict[str, str] | str) -> pd.DataFrame:
    return pd.DataFrame([{"series": series, "freq": "Q", "period": p, "value": float(v),
                          "known_from": pd.Timestamp(kf[p] if isinstance(kf, dict) else kf), "source": "release",
                          "fetched_at": pd.Timestamp("2026-11-25")} for p, v in values.items()])


def _kf(q: str, lag: int = 30) -> str:
    return str((pd.Period(q, freq="Q-DEC").end_time.normalize() + pd.Timedelta(days=lag)).date())


QS = [str(q) for q in pd.period_range("2022Q1", "2025Q4", freq="Q-DEC")]


# ------------------------------------------------------------------ aggregate


def test_series_module_uses_the_shared_aggregate():
    assert S.derive is A.derive and S.Formula is A.Formula and S.Term is A.Term


def test_layer_exists_only_once_every_member_has_filed_and_missing_says_who():
    f = A.Formula("x_layer", A.sum4("a") + A.sum4("b"))
    late = {q: _kf(q, 30) for q in QS}
    late["2025Q4"] = "2026-03-15"
    rows = pd.concat([_rows("a", {q: 1.0 for q in QS}, {q: _kf(q, 10) for q in QS}), _rows("b", {q: 2.0 for q in QS}, late)])
    d = A.derive(f, rows)
    last = d[d["period"] == "2025Q4"]
    assert list(last["known_from"]) == [pd.Timestamp("2026-03-15")] and float(last["value"].iloc[0]) == 12.0
    assert A.missing(f, rows, "2025Q4", "2026-02-01") == [("b", "2025Q4")]
    assert A.missing(f, rows, "2025Q4", "2026-03-15") == []
    assert A.inputs(f, "2025Q4")[:4] == [("a", "2025Q4"), ("a", "2025Q3"), ("a", "2025Q2"), ("a", "2025Q1")]


def test_quarters():
    assert C.quarter("2026-11-30") == "2026Q4" and C.quarter("2026Q1") == "2026Q1"
    assert C.quarter(pd.Period("2026-02", freq="M")) == "2026Q1"
    assert C.minus("2026Q1", 2) == "2025Q3" and C.plus("2025Q4", 1) == "2026Q1" and C.minus(None, 1) is None


# ------------------------------------------------------------------ measures


@pytest.mark.parametrize("key,method", [("kl_capex4_outer", "log"), ("kl_fcfgap_orcl", "share")])
def test_path_measures_equal_state_measures(key, method):
    rng = np.random.default_rng(3)
    vals = {q: float(v) for q, v in zip(QS, 1000 * np.exp(np.cumsum(rng.normal(0.05, 0.04, len(QS)))))}
    if method == "share":
        vals = {q: 30 + 10 * np.sin(i / 2) for i, q in enumerate(QS)}
    table = _rows(key, vals, {q: _kf(q) for q in QS})
    m = C.measure(key, "2026-06-01", M.Context(table=table))
    p = C.path_measures(vals, method)
    for q in QS:
        for col in ("pace", "change"):
            a, b = C.at(m, q, col), C.num(p.loc[q, col])
            assert (a is None and b is None) or abs(a - b) < 1e-9, (q, col)
    assert abs(m["surprise"] - p["surprise"].iloc[-1]) < 1e-9
    assert m["period"] == "2025Q4" and m["known_from"] == _kf("2025Q4")


def test_measure_of_an_unknown_series_is_unavailable():
    m = C.measure("kl_capex4_outer", "2026-01-01", M.Context(table=_rows("other", {"2025Q1": 1}, "2025-05-01")))
    assert m == {"series": "kl_capex4_outer", "available": False} and C.series_of(m, "pace") == {}


# ------------------------------------------------------------------ the symmetric reading rule


def _q(start: str, n: int) -> list[str]:
    return [str(q) for q in pd.period_range(start, periods=n, freq="Q-DEC")]


Q8 = _q("2024Q1", 8)  # 2024Q1 .. 2025Q4


def _x(**at):
    return {q: at.get(q.replace("Q", "q"), 0.0) for q in Q8}


@pytest.mark.parametrize("x_at,y_at,sign,want,origin", [
    ({"2025q2": 3.0}, {"2025Q3": 2.0}, 1, C.FOR, "2025Q2"),  # rise, then Y up
    ({"2025q2": -3.0}, {"2025Q3": -2.0}, 1, C.FOR, "2025Q2"),  # fall, then Y down: the same, mirrored
    ({"2025q2": 3.0}, {"2025Q3": -2.0}, 1, C.AGAINST, "2025Q2"),
    ({"2025q2": -3.0}, {"2025Q3": 2.0}, 1, C.AGAINST, "2025Q2"),
    ({"2025q2": 3.0}, {"2025Q3": -2.0}, -1, C.FOR, "2025Q2"),  # mechanism with opposite sign (as KL1: rate up, capex down)
    ({"2025q2": 3.0}, {"2025Q3": 0.5, "2025Q4": 0.5}, 1, C.UNDECIDED, "2025Q2"),  # window open to 2026Q1
    ({"2025q1": 3.0}, {"2025Q2": 0.5, "2025Q3": 0.5, "2025Q4": 0.5}, 1, C.NEITHER, "2025Q1"),  # Y below h for k quarters
    ({"2025q2": 1.9}, {"2025Q3": 5.0}, 1, C.NEITHER, None),  # no impulse (|X| < g)
    ({"2025q1": 3.0, "2025q3": -3.0}, {"2025Q2": 2.0, "2025Q4": 2.0}, 1, C.AGAINST, "2025Q3"),  # the latest impulse
])
def test_rule_truth_table(x_at, y_at, sign, want, origin):
    x = _x(**{k: v for k, v in x_at.items()})
    y = {q: y_at.get(q, 0.0) for q in Q8}
    r = C.read_rule(x, y, g=2.0, h=1.0, k=3, sign=sign)
    assert r["outcome"] == want and r["origin"] == origin and r["t"] == "2025Q4"
    assert r["text"] == C.OUTCOME_TEXT[want]


def test_rule_first_crossing_decides_and_missing_y_is_undecided():
    x = _x(**{"2025q1": 3.0})
    r = C.read_rule(x, {**{q: 0.0 for q in Q8}, "2025Q2": -1.5, "2025Q3": 4.0}, g=2, h=1, k=3)
    assert r["outcome"] == C.AGAINST and r["origins"][-3]["decided_at"] == "2025Q2"
    y = {q: 0.0 for q in Q8}
    y["2025Q2"] = None
    r = C.read_rule(x, y, g=2, h=1, k=3)
    assert r["outcome"] == C.UNDECIDED and r["reason"] == "Y saknas vid 2025Q2"
    r = C.read_rule({**x, "2025Q2": 3.0}, {q: 0.0 for q in Q8}, g=2, h=1, k=3)
    assert r["reason"] == "fönstret öppet till 2026Q1"


def test_rule_with_h_zero_needs_a_nonzero_y():
    x = _x(**{"2025q1": 3.0})
    assert C.read_rule(x, {q: 0.0 for q in Q8}, g=2, h=0, k=3)["outcome"] == C.NEITHER
    assert C.read_rule(x, {**{q: 0.0 for q in Q8}, "2025Q3": 0.1}, g=2, h=0, k=3)["outcome"] == C.FOR


def test_rule_without_x_or_y_cannot_be_decided():
    y = {q: 0.0 for q in Q8}
    x = {**_x(), "2025Q3": None}
    r = C.read_rule(x, y, g=2, k=2)
    assert r["outcome"] == C.UNDECIDED and "X saknas vid 2025Q3" in r["reason"]
    r = C.read_rule(_x(), {}, g=2, k=2)
    assert r["outcome"] == C.UNDECIDED and r["t"] is None
    with pytest.raises(ValueError):
        C.read_rule(_x(), y, g=0, k=2)
    with pytest.raises(ValueError):
        C.read_rule(_x(), y, g=1, k=2, sign=2)


def test_rule_is_symmetric_and_counts_how_often_it_could_be_tried():
    rng = np.random.default_rng(11)
    qs = _q("2020Q1", 24)
    for _ in range(50):
        x = {q: float(v) for q, v in zip(qs, rng.normal(0, 3, len(qs)))}
        y = {q: float(v) for q, v in zip(qs, rng.normal(0, 3, len(qs)))}
        y[qs[5]] = None
        a = C.read_rule(x, y, g=2, h=1, k=2)
        b = C.read_rule({q: -v for q, v in x.items()}, {q: None if v is None else -v for q, v in y.items()},
                        g=2, h=1, k=2)
        assert a["outcome"] == b["outcome"] and a["origin"] == b["origin"]
        ha, hb = a["history"], b["history"]
        assert ha["by_direction"]["up"] == hb["by_direction"]["down"] and ha["impulses_up"] == hb["impulses_down"]
        assert ha["n_x"] == 23 and ha["n_tested"] == ha["n_x"] - sum(ha["by_direction"][d][C.UNDECIDED]
                                                                    for d in ("up", "down"))
        assert ha["impulses_up"] + ha["impulses_down"] + ha["no_impulse"] == ha["n_x"]


def test_read_measures_and_reading_lines():
    vals = {q: 1000 * 1.05 ** i * (1.3 if i >= 10 else 1.0) for i, q in enumerate(QS)}
    t = pd.concat([_rows("kl_capex4_outer", vals, {q: _kf(q) for q in QS}),
                   _rows("kl_rate_eff_orcl", {q: 4 + (1.0 if i >= 8 else 0) for i, q in enumerate(QS)},
                         {q: _kf(q) for q in QS})])
    ctx = M.Context(table=t)
    mx, my = C.measure("kl_rate_eff_orcl", "2026-06-01", ctx), C.measure("kl_capex4_outer", "2026-06-01", ctx)
    r = C.read_measures(mx, my, x_stat="pace", g=0.25, k=3, h=5.0, sign=-1)
    assert r["x_series"] == "kl_rate_eff_orcl" and r["y_series"] == "kl_capex4_outer" and r["t"] == "2025Q4"
    assert r["outcome"] in C.OUTCOMES and r["history"]["impulses_up"] >= 1
    lines = C.reading_lines(r, "Oracle")
    assert lines[0].startswith("- **Oracle:** ") and "Regeln kunde prövas i" in lines[1]
    assert C.read_measures({"available": False, "series": "a"}, {"available": False, "series": "b"}, g=1, k=1)[
        "outcome"] == C.UNDECIDED


# ------------------------------------------------------------------ markdown


def test_fmt_and_table():
    assert C.fmt(1234.56, 1) == "1 234,6" and C.fmt(-0.25, 2, True) == "-0,25" and C.fmt(None) == "–"
    assert C.fmt_bn(313819) == "313,8 mdr" and C.fmt_pct(4.66) == "4,7 %"
    ms = {"a": {"available": False}, "b": {"available": True, "level": 2.0, "pace": 1.0, "change": -0.5,
                                           "surprise": 0.1, "period": "2025Q4", "known_from": "2026-01-30"}}
    lines = C.measure_table(ms, ["a", "b"], C.fmt_pct, str.upper)
    assert lines[:2] == C.TABLE_HEAD and lines[2] == "| A | – | – | – | – | – | – | `a` |"
    assert lines[3] == "| B | 2,0 % | +1,0 | -0,5 | +0,1 | 2025Q4 | 2026-01-30 | `b` |"


# ------------------------------------------------------------------ discovery and antenner


def _fake(name: str, outcome: str = "inget", fact: str = "1", with_antenna: bool = True, boom: bool = False):
    mod = types.ModuleType(name)
    mod.QUESTION = f"Fråga {name}?"

    def compute(as_of, table=None):
        if boom:
            raise RuntimeError("trasig")
        return {"as_of": str(as_of), "late": str(as_of) >= "2026-11-01"}

    mod.compute = compute
    mod.render = lambda r: f"# {name} {r['as_of']}\n"
    if with_antenna:
        mod.antenna = lambda r: C.antenna_row(mod.QUESTION, outcome if r["late"] else "kan_inte_avgoras",
                                              outcome if r["late"] else "kan inte avgöras", "2025Q4",
                                              {"f": fact if r["late"] else "0"}, "X omkring 2026-12-11", "2026-12-11")
    return mod


def test_questions_are_found_without_a_list(tmp_path, monkeypatch):
    found = followed.questions()
    assert {"kreditlagret", "antenner"} <= set(found) and not {"common", "aggregate"} & set(found)
    (tmp_path / "zz_ny_fraga.py").write_text("QUESTION = 'Ny?'\ndef compute(as_of, table=None):\n    return {}\n"
                                             "def render(r):\n    return 'ny'\n", encoding="utf-8")
    (tmp_path / "zz_hjalp.py").write_text("X = 1\n", encoding="utf-8")
    monkeypatch.setattr(followed, "__path__", [*followed.__path__, str(tmp_path)])
    monkeypatch.delitem(sys.modules, "ai_tracker.followed.zz_ny_fraga", raising=False)
    found = followed.questions()
    assert "zz_ny_fraga" in found and "zz_hjalp" not in found
    monkeypatch.setattr(CLI, "questions", lambda: {"zz_ny_fraga": found["zz_ny_fraga"]})
    out = tmp_path / "out.md"
    assert CLI.main(["zz_ny_fraga", "--as-of", "2026-11-25", "--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == "ny"


def test_antenner_rows_changes_and_failures():
    mods = {"a": _fake("a", "talar_for", "2"), "b": _fake("b", with_antenna=False), "c": _fake("c", boom=True)}
    r = AN.compute("2026-11-25", table=pd.DataFrame(), modules=mods)
    assert r["previous"] == "2026-10-25" and [x["key"] for x in r["rows"]] == ["a", "b", "c"]
    a = r["rows"][0]
    assert set(C.ANTENNA_KEYS) <= set(a) and a["outcome"] == "talar_for"
    assert a["changes"] == ["utslag: kan inte avgöras → talar_for", "f: 0 → 2"]
    assert r["rows"][1]["has_antenna"] is False and "RuntimeError: trasig" in r["rows"][2]["error"]
    text = AN.render(r)
    assert "| Fråga | Senaste utslag | Ändrat mot 2026-10-25 | Nästa osedda läsning |" in text
    assert "ingen antenn" in text and "fel vid beräkningen" in text and "X omkring 2026-12-11" in text
    assert AN.changes(a["current"], a["current"]) == [] and AN.previous("2026-03-31") == "2026-02-28"


# ------------------------------------------------------------------ KL1 on the synthetic world


@pytest.fixture(scope="module")
def world():
    from tests.test_kreditlagret import _report_world

    return _report_world()


def _csv():
    from ai_tracker.sources import kreditlagret as kl

    return pd.DataFrame([{**{c: "" for c in kl.COLUMNS}, "id": "x", "company": "anthropic",
                          "instrument": "anthropic_oblig_purchase_commitments", "field": "due_total", "value": "313819",
                          "unit": "MUSD", "period": "2026-09-30", "filed": "2026-10-26"}])


@pytest.mark.parametrize("day", ["2025-06-30", "2025-12-20", "2026-11-25"])
def test_kl1_report_is_byte_identical_to_the_golden_from_before_f0(world, day, monkeypatch):
    """tests/golden/kreditlagret_synth_<day>.md was rendered with the code before F0 (register F0: KL1 unchanged).
    Since S1 (register 2026-11-27, point 1) the report appends KL1-S as section 8: the locked part is still the golden,
    byte for byte, and the full report starts with it."""
    from ai_tracker.series import guidance_revisions as F1

    monkeypatch.setattr(F1, "load_csv", lambda: None)
    r = F.compute(day, table=world, csv=_csv())
    golden = (GOLDEN / f"kreditlagret_synth_{day}.md").read_text(encoding="utf-8")
    assert F.render_locked(r) == golden
    text = F.render(r)
    assert text.startswith(golden) and text[len(golden):].startswith("## 8. Tillägg S1")


def test_kl1_antenna(world, monkeypatch):
    from ai_tracker.series import guidance_revisions as F1

    monkeypatch.setattr(F1, "load_csv", lambda: None)
    r = F.compute("2026-01-10", table=world, csv=_csv())
    a = F.antenna(r)
    assert set(a) == set(C.ANTENNA_KEYS) and a["outcome"] in F.OUTCOME and a["question"] == F.QUESTION
    assert a["reading"] == F.SHORT[r["readings"]["outer"]["outcome"]] and a["t"] == r["readings"]["outer"]["t"]
    assert "Oracle mot inre lagret, utslag" in a["facts"] and "A har gällt (yttre)" in a["facts"]
    # every filing estimated in this world lies before the register day: no unseen reading is estimated yet
    assert a["next_unseen_date"] is None and "efter 2026-11-25" in a["next_unseen"]
    late = F.compute("2026-11-25", table=world, csv=_csv())
    text, day = F.next_unseen({**late, "next_filings": [
        {"company": "orcl", "estimated": "2026-12-11", "next_period": "2026Q4", "overdue": False,
         "then_estimated": None, "then_period": None}]})
    assert day == "2026-12-11" and text.startswith("Oracle 2026Q4 omkring 2026-12-11")
