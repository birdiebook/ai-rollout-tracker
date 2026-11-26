"""BG1 "Betalningsgapet" (register 2026-11-26 "BG1"). Synthetic data only, no network, no observation table.

- the registered quantities: requirement = four quarters of depreciation + r x net PP&E, gap = 100 x requirement /
  cloud revenue (or RPO), sums over the members, a version only once every component has one
- the reading both ways (sign -1): gap opens then capex pace falls, gap closes then capex pace rises, the opposite moves,
  no impulse
- the as-of boundary: a row known after the day changes nothing
- missing data: a missing member, a missing series, an empty table
- regime markers, the antenna and discovery by the CLI
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai_tracker import followed
from ai_tracker.followed import __main__ as CLI
from ai_tracker.followed import antenner as AN
from ai_tracker.followed import betalningsgapet as B
from ai_tracker.followed import common as C

QS = [str(q) for q in pd.period_range("2021Q1", "2025Q4", freq="Q-DEC")]
N = len(QS)
DAY = "2026-03-15"  # every quarter of QS is known (known_from = quarter end + 30 days)


def _kf(q: str, lag: int = 30) -> pd.Timestamp:
    return pd.Period(q, freq="Q-DEC").end_time.normalize() + pd.Timedelta(days=lag)


def _rows(series: str, values: dict[str, float], lag: int = 30) -> list[dict]:
    return [{"series": series, "freq": "Q", "period": q, "value": float(v), "known_from": _kf(q, lag),
             "source": "release", "fetched_at": pd.Timestamp("2026-03-15")} for q, v in values.items()]


def _path(level: float, growth) -> dict[str, float]:
    g = np.broadcast_to(np.asarray(growth, dtype=float), (N,))
    return dict(zip(QS, level * np.exp(np.cumsum(g))))


def _steps(before: float, after: float, at: int) -> np.ndarray:
    """Quarterly log growth: `before` for the first `at` quarters, then `after`."""
    return np.array([before] * at + [after] * (N - at))


def world(rev_g=0.05, req_g=0.05, capex_g=0.05, skip: tuple[str, ...] = ()) -> pd.DataFrame:
    """Every company the same: cloud revenue and RPO grow at rev_g, depreciation and net PP&E at req_g (so the
    requirement grows at req_g for any r), capex at capex_g (log growth per quarter)."""
    rows = []
    for c in B.COMPANIES:
        for key, level, g in ((B.CLOUD_REV[c], 100.0, rev_g), (f"rpo_{c}", 1000.0, rev_g), (f"dep_{c}", 20.0, req_g),
                              (f"ppe_net_{c}", 400.0, req_g), (f"capex_{c}", 50.0, capex_g)):
            if key not in skip:
                rows += _rows(key, _path(level, g))
    return pd.DataFrame(rows)


def main(r: dict) -> dict:
    return next(x for x in r["readings"] if x["id"] == "main")


# ------------------------------------------------------------------ the registered quantities


def test_formulas_follow_the_register():
    f = B.formula("gap_moln", "moln4", 0.10)
    assert f.scale == 100.0 and set(f.components) == {
        *(f"dep_{c}" for c in B.CLOUD4), *(f"ppe_net_{c}" for c in B.CLOUD4), *(B.CLOUD_REV[c] for c in B.CLOUD4)}
    # four quarters of depreciation, net PP&E at quarter end weighted with r, cloud revenue over four quarters
    assert sorted(t.offset for t in f.num if t.series == "dep_msft") == [0, 1, 2, 3]
    assert [(t.offset, t.weight) for t in f.num if t.series == "ppe_net_orcl"] == [(0, 0.10)]
    assert sorted(t.offset for t in f.den if t.series == "rev_aws") == [0, 1, 2, 3]
    # r = 0: only depreciation; the RPO gap divides by the balance at quarter end
    assert not [t for t in B.formula("krav", "moln4", 0.0).num if t.series.startswith("ppe_net")]
    assert [(t.series, t.offset) for t in B.formula("gap_rpo", "moln3", 0.10).den] == [
        ("rpo_msft", 0), ("rpo_googl", 0), ("rpo_amzn", 0)]
    assert B.GROUPS["moln4"] == ("msft", "googl", "amzn", "orcl") and "crwv" not in B.GROUPS["moln4"]
    assert (B.G, B.H, B.K, B.SIGN, B.R_MAIN, B.R_SENS) == (5.0, 5.0, 2, -1, 0.10, (0.0, 0.08, 0.12))


def test_registered_rows_one_per_x():
    ids = [x["id"] for x in B.reading_specs()]
    assert ids[:6] == ["main", "rpo", "r00", "r08", "r12", "rpo_ex_orcl"]
    assert ids[6:] == [f"{c}_{k}" for c in B.COMPANIES for k in ("moln", "rpo")]


def test_gap_level_and_dating():
    t = world(rev_g=0.0, req_g=0.0, capex_g=0.0)
    t.loc[(t["series"] == "rev_orcl_cloud") & (t["period"] == "2025Q4"), "known_from"] = pd.Timestamp("2026-02-20")
    r = B.compute(DAY, table=t)
    gap = r["quantities"]["gap_moln(molnfyran, r=0,10)"]
    # (4 x 20 x 4 + 0.10 x 400 x 4) / (4 x 100 x 4) = 480 / 1600 = 30 %
    assert gap["level"] == pytest.approx(30.0) and gap["period"] == "2025Q4"
    assert gap["known_from"] == "2026-02-20"  # the latest component used
    assert gap["pace"] == pytest.approx(0.0, abs=1e-9) and gap["path"]["2021Q4"]["level"] == pytest.approx(30.0)
    assert "2021Q3" not in gap["kf"]  # four quarters are needed for the first version
    assert r["quantities"]["gap_rpo(molnfyran, r=0,10)"]["level"] == pytest.approx(100 * 480 / 4000)
    assert r["quantities"]["krav(molnfyran, r=0,00)"]["level"] == pytest.approx(320.0)


# ------------------------------------------------------------------ the reading, both ways


def test_gap_opens_then_capex_pace_falls_speaks_for():
    r = B.compute(DAY, table=world(req_g=_steps(0.05, 0.10, 12), capex_g=_steps(0.05, -0.10, 17)))
    x = main(r)
    o = next(o for o in x["origins"] if o["origin"] == x["origin"])
    assert x["outcome"] == C.FOR and x["t"] == "2025Q4" and o["direction"] == 1 and o["expected"] == -1
    assert o["x"] >= B.G and o["y"] <= -B.H


def test_gap_closes_then_capex_pace_rises_speaks_for():
    r = B.compute(DAY, table=world(rev_g=_steps(0.05, 0.10, 12), capex_g=_steps(0.02, 0.15, 17)))
    x = main(r)
    o = next(o for o in x["origins"] if o["origin"] == x["origin"])
    assert x["outcome"] == C.FOR and o["direction"] == -1 and o["expected"] == 1
    assert o["x"] <= -B.G and o["y"] >= B.H
    assert x["history"]["impulses_down"] >= 1 and x["history"]["impulses_up"] == 0


@pytest.mark.parametrize("rev_g,req_g,capex_g", [
    (0.05, _steps(0.05, 0.10, 12), _steps(0.02, 0.15, 17)),  # gap opens, capex pace rises
    (_steps(0.05, 0.10, 12), 0.05, _steps(0.05, -0.10, 17)),  # gap closes, capex pace falls
])
def test_the_opposite_move_speaks_against(rev_g, req_g, capex_g):
    assert main(B.compute(DAY, table=world(rev_g=rev_g, req_g=req_g, capex_g=capex_g)))["outcome"] == C.AGAINST


def test_no_impulse_is_neither_and_steady_capex_is_neither():
    r = B.compute(DAY, table=world())
    assert {x["outcome"] for x in r["readings"]} == {C.NEITHER}
    # the gap opens but capex pace stays within +-h: neither at t-2 ("holds" is not "for"); at t-1 the window is open
    m = main(B.compute(DAY, table=world(req_g=_steps(0.05, 0.10, 12))))
    o = {x["origin"]: x for x in m["origins"]}
    assert o["2025Q2"]["direction"] == 1 and o["2025Q2"]["outcome"] == C.NEITHER
    assert m["outcome"] == C.UNDECIDED and m["origin"] == "2025Q3" and "fönstret öppet" in m["reason"]


def test_sensitivity_rows_read_their_own_r():
    # only net PP&E accelerates: r = 0 sees no impulse, r > 0 does
    t = world(capex_g=_steps(0.05, -0.10, 17))
    ppe = t["series"].str.startswith("ppe_net_")
    for s in t.loc[ppe, "series"].unique():
        vals = _path(400.0, _steps(0.05, 0.20, 12))
        t.loc[t["series"] == s, "value"] = t.loc[t["series"] == s, "period"].map(vals).to_numpy()
    by = {x["id"]: x for x in B.compute(DAY, table=t)["readings"]}
    assert by["r00"]["outcome"] == C.NEITHER and by["r00"]["origin"] is None
    assert by["r08"]["outcome"] == by["r12"]["outcome"] == by["main"]["outcome"] == C.FOR


# ------------------------------------------------------------------ the as-of boundary


def test_a_row_known_after_the_day_changes_nothing():
    base = world(req_g=_steps(0.05, 0.10, 12), capex_g=_steps(0.05, -0.10, 17))
    late = pd.DataFrame(
        _rows("rev_aws", {"2025Q4": 1e6}, lag=200)  # a revision known 2026-07-19
        + _rows("capex_msft", {"2026Q1": 1e6}, lag=30)  # a quarter known 2026-04-30
        + _rows("useful_life_servers_msft_hi", {"2025Q3": 4.0, "2025Q4": 9.0}, lag=200))
    a = B.compute(DAY, table=base)
    b = B.compute(DAY, table=pd.concat([base, late], ignore_index=True))
    assert B.render(a).replace(a["generated"], "") == B.render(b).replace(b["generated"], "")
    assert a["readings"] == b["readings"] and b["life_changes"] == []
    # and on the day the revision is known it is used
    c = B.compute("2026-07-20", table=pd.concat([base, late], ignore_index=True))
    assert c["quantities"]["moln(Amazon)"]["level"] > a["quantities"]["moln(Amazon)"]["level"]


def test_compute_equals_compute_on_the_truncated_table():
    t = world(req_g=_steps(0.05, 0.10, 12), capex_g=_steps(0.05, -0.10, 17))
    for day in ("2024-02-15", "2025-08-01", DAY):
        cut = t[t["known_from"] <= pd.Timestamp(day)]
        a, b = B.compute(day, table=t), B.compute(day, table=cut)
        assert B.render(a) == B.render(b) and a["readings"] == b["readings"]


# ------------------------------------------------------------------ missing data


def test_a_member_missing_for_the_last_quarter_is_named_and_the_aggregate_stops():
    t = world(req_g=_steps(0.05, 0.10, 12), capex_g=_steps(0.05, -0.10, 17))
    t = t[~((t["series"] == "rev_orcl_cloud") & (t["period"] == "2025Q4"))]
    r = B.compute(DAY, table=t)
    gap = r["quantities"]["gap_moln(molnfyran, r=0,10)"]
    assert gap["period"] == "2025Q3" and gap["missing_next"] == ["rev_orcl_cloud 2025Q4"]
    assert "saknar på dagen: `rev_orcl_cloud 2025Q4`" in B.render(r)
    # the company rows of the others still have 2025Q4
    assert r["quantities"]["gap_moln(Microsoft, r=0,10)"]["period"] == "2025Q4"


def test_a_missing_series_cannot_be_decided_and_says_why():
    r = B.compute(DAY, table=world(skip=("rev_orcl_cloud",)))
    x = main(r)
    assert x["outcome"] == C.UNDECIDED and "X saknas" in x["reason"]
    assert r["quantities"]["gap_moln(molnfyran, r=0,10)"]["available"] is False
    oracle = next(y for y in r["readings"] if y["id"] == "orcl_moln")
    assert oracle["outcome"] == C.UNDECIDED
    assert next(y for y in r["readings"] if y["id"] == "orcl_rpo")["outcome"] == C.NEITHER  # RPO still there
    assert "kan inte avgöras" in B.render(r)


def test_an_empty_table_renders_and_has_an_antenna():
    empty = pd.DataFrame(columns=["series", "freq", "period", "value", "known_from", "source", "fetched_at"])
    r = B.compute(DAY, table=empty)
    assert all(x["outcome"] == C.UNDECIDED for x in r["readings"]) and r["next_filings"] == []
    text = B.render(r)
    assert "# Betalningsgapet per 2026-03-15" in text and "BLOCKED" in text
    a = B.antenna(r)
    assert a["outcome"] == C.UNDECIDED and a["t"] is None and a["next_unseen_date"] is None


# ------------------------------------------------------------------ regime markers, antenna, discovery


def test_useful_life_changes_are_listed_and_only_the_highest_value_marks_a_reading():
    t = pd.concat([world(req_g=_steps(0.05, 0.10, 12), capex_g=_steps(0.05, -0.10, 17)), pd.DataFrame(
        _rows("useful_life_servers_msft_hi", {"2022Q3": 4.0, "2025Q1": 6.0})
        + _rows("useful_life_servers_msft_lo", {"2022Q3": 4.0, "2025Q1": 6.0})
        + _rows("useful_life_servers_amzn_lo", {"2022Q3": 6.0, "2025Q2": 5.0}))], ignore_index=True)
    r = B.compute(DAY, table=t)
    assert [(x["company"], x["end"], x["period"]) for x in r["life_changes"]] == [
        ("msft", "hi", "2025Q1"), ("msft", "lo", "2025Q1"), ("amzn", "lo", "2025Q2")]
    m = main(r)
    assert m["origin"] == "2025Q3"
    assert any("Microsoft ändrades 2025Q1 (4 → 6 år" in f for f in m["flags"])
    assert not any("Amazon" in f for f in m["flags"])  # a change of the lowest value only does not mark
    assert not any("nyttjandeperioden" in f for f in next(x for x in r["readings"] if x["id"] == "amzn_moln")["flags"])


def test_microsoft_old_basis_marks_origins_through_2026q1():
    spec = {"who": "moln4"}
    assert any("gamla basen" in f for f in B.flags(spec, "2026Q1", []))
    assert not any("gamla basen" in f for f in B.flags(spec, "2026Q2", []))
    assert B.flags({"who": "googl"}, "2025Q1", []) == [] and B.flags(spec, None, []) == []


def test_antenna_and_next_unseen():
    r = B.compute(DAY, table=world(req_g=_steps(0.05, 0.10, 12), capex_g=_steps(0.05, -0.10, 17)))
    a = B.antenna(r)
    assert set(a) == set(C.ANTENNA_KEYS) and a["question"] == B.QUESTION
    assert a["outcome"] == C.FOR and a["reading"] == "talar för mekanismen" and a["t"] == "2025Q4"
    assert "Gapet mot RPO, molnfyran, r = 0,10" in a["facts"] and "Impulser i huvudläsningens historik" in a["facts"]
    # every filing estimated in this world lies before the register day
    assert a["next_unseen_date"] is None and f"efter {B.REGISTERED}" in a["next_unseen"]
    fake = [{"company": c, "estimated": d, "next_period": "2026Q4", "overdue": False, "then_estimated": None,
             "then_period": None} for c, d in (("orcl", "2026-12-11"), ("msft", "2027-01-29"), ("googl", "2027-01-29"),
                                               ("amzn", "2027-01-31"), ("crwv", "2027-02-13"))]
    text, day = B.next_unseen({**r, "next_filings": fake})
    assert day == "2026-12-11" and text.startswith("Oracle 2026Q4 omkring 2026-12-11")
    assert "molnfyrans huvudläsning när alla fyra har lämnat in (uppskattat 2027-01-31)" in text
    row = AN.compute("2026-02-20", table=world(), modules={"betalningsgapet": B})["rows"][0]  # 2025Q4 from 2026-01-30
    assert row["has_antenna"] and "error" not in row and row["previous"]["t"] == "2025Q3" and row["t"] == "2025Q4"
    assert row["changes"][0] == "kvartal: 2025Q3 → 2025Q4"


def test_found_by_the_cli(tmp_path, monkeypatch):
    assert followed.questions()["betalningsgapet"] is B
    t = world()
    monkeypatch.setattr(B.C, "prepare", lambda table=None, _p=C.prepare: _p(t if table is None else table))
    out = tmp_path / "bg1.md"
    assert CLI.main(["betalningsgapet", "--as-of", DAY, "--out", str(out), "--json", str(tmp_path / "bg1.json")]) == 0
    assert out.read_text(encoding="utf-8").startswith("# Betalningsgapet per 2026-03-15")
