"""EL1 "Elflaskhalsen" (register 2026-11-26 "EL1"). Synthetic data only.

- the locked parameters equal the register entry, which is unchanged since it was committed
- the reading rule both ways: tightening then braking, easing then accelerating (talar för), and the opposite (emot)
- the as-of boundary: a row known after the day changes nothing
- missing data: a missing month gives no quarter, a missing member gives no aggregate, a missing series is undecided
- discovery, antenna and render
"""

from __future__ import annotations

import hashlib
import math

import numpy as np
import pandas as pd
import pytest

from ai_tracker import config, followed
from ai_tracker.followed import antenner as AN
from ai_tracker.followed import common as C
from ai_tracker.followed import elflaskhalsen as E

QS = [str(q) for q in pd.period_range("2022Q1", "2026Q3", freq="Q-DEC")]
MONTHS = [str(m) for m in pd.period_range("2021-01", "2026-09", freq="M")]
DAY = "2026-11-26"
REGISTER = config.REPO / "docs" / "mattregister.md"
ENTRY = "### 2026-11-26 – EL1: följd fråga om elen som begränsning för utbyggnaden (förregistrering, före beräkning)"


def _q_kf(q: str, lag: int = 30) -> pd.Timestamp:
    return pd.Period(q, freq="Q-DEC").end_time.normalize() + pd.Timedelta(days=lag)


def _m_kf(m: str, lag: int = 10) -> pd.Timestamp:
    return pd.Period(m, freq="M").end_time.normalize() + pd.Timedelta(days=lag)


def _rows(series: str, freq: str, values: dict[str, float], kf) -> pd.DataFrame:
    return pd.DataFrame([{"series": series, "freq": freq, "period": p, "value": float(v), "known_from": kf(p),
                          "source": "release", "fetched_at": pd.Timestamp("2026-11-26")} for p, v in values.items()])


def _path(incs: dict[str, float], start: float = 1000.0) -> dict[str, float]:
    """Levels from quarterly log x100 increments (missing quarters: 0)."""
    y, out = 100.0 * math.log(start), {}
    for q in QS:
        y += incs.get(q, 0.0)
        out[q] = math.exp(y / 100.0)
    return out


def world(x_jump: float = 20.0, y_last_inc: float = 0.0, gw_jump: float = 20.0) -> pd.DataFrame:
    """A synthetic table. The grid backlog (rpo_pwr + rpo_etn) jumps by `x_jump` log points in 2026Q1 (pace +/-x_jump
    in 2026Q1-Q3, 0 before). The inner layer's capex grows 10 log points a quarter (pace 40, change 0) until 2026Q2,
    and by `y_last_inc` in 2026Q3 (change in pace at 2026Q3 = y_last_inc - 10). Monthly price and load are flat."""
    nat = _path({"2026Q1": x_jump})
    parts = [_rows("rpo_pwr", "Q", {q: 0.6 * v for q, v in nat.items()}, _q_kf),
             _rows("rpo_etn", "Q", {q: 0.4 * v for q, v in nat.items()}, lambda q: _q_kf(q, 35))]
    gw = _path({"2026Q1": gw_jump}, 50.0)
    parts.append(_rows(E.GW, "Q", gw, _q_kf))
    cap = _path({q: (y_last_inc if q == "2026Q3" else 10.0) for q in QS}, 50_000.0)
    parts.append(_rows(E.CAPEX_INNER, "Q", cap, lambda q: _q_kf(q, 31)))
    parts.append(_rows(E.DLR_MW, "Q", {q: 100.0 for q in QS}, lambda q: _q_kf(q, 24)))
    for c, key in E.INNER.items():
        parts.append(_rows(key, "Q", {q: 10_000.0 for q in QS}, lambda q: _q_kf(q, 30)))
    parts.append(_rows(E.PPI, "M", {m: 300.0 for m in MONTHS}, _m_kf))
    for key in (*E.LOAD, E.DOM):
        parts.append(_rows(key, "M", {m: 10_000.0 for m in MONTHS}, _m_kf))
    return pd.concat(parts, ignore_index=True)


def _main(report: dict) -> dict:
    return report["readings"]["nat|capex"]


# ------------------------------------------------------------------ register


def test_register_entry_is_locked_and_matches_the_module():
    text = REGISTER.read_text(encoding="utf-8")
    assert ENTRY in text
    entry = text.split(ENTRY, 1)[1].split("\n### ", 1)[0]
    assert hashlib.sha256(entry.encode("utf-8")).hexdigest() == ENTRY_SHA256
    for want in ("| X1 elpris | 5,0 |", "| X2 last | 2,0 |", "| X3 orderstock elnät, MUSD | 10,0 |",
                 "| X4 orderstock gasturbiner, GW | 10,0 |", "| Y1 capex, inre lagret | 5,0 |",
                 "| Y2 tecknade MW, Digital Realty | 10,0 |", "*k* = 2 kvartal och tecken *s* = −1",
                 "**Huvudläsningen är X3\nmot Y1.**"):
        assert want in entry, want
    assert E.G == {"pris": 5.0, "last": 2.0, "nat": 10.0, "gw": 10.0} and E.H == {"capex": 5.0, "dlr": 10.0}
    assert E.K == 2 and E.SIGN == -1 and E.MAIN == ("nat", "capex") and len(E.PAIRS) == 8
    assert E.REGISTERED == "2026-11-26"


ENTRY_SHA256 = "b5610775b5e2513b664591c27f38c31ae9aa0492f9610c82c034b1625189be0d"


# ------------------------------------------------------------------ the reading both ways


@pytest.mark.parametrize("x_jump,y_inc,want,direction", [
    (20.0, 0.0, C.FOR, 1),       # tightening (pace +20), then braking (change -10): talar för, uppåt
    (-20.0, 20.0, C.FOR, -1),    # easing (pace -20), then accelerating (change +10): talar för, nedåt
    (20.0, 20.0, C.AGAINST, 1),  # tightening, then accelerating: talar emot, uppåt
    (-20.0, 0.0, C.AGAINST, -1),  # easing, then braking: talar emot, nedåt
    (5.0, 0.0, C.NEITHER, 0),    # |pace| < g: no impulse
    (20.0, 12.0, C.UNDECIDED, 1),  # change -> +2 within ±h at t, the window is open at q + 2
])
def test_main_reading_both_ways(x_jump, y_inc, want, direction):
    r = E.compute(DAY, table=world(x_jump, y_inc))
    m = _main(r)
    assert m["t"] == "2026Q3" and m["outcome"] == want, m
    o = next((x for x in m["origins"] if x["origin"] == m["origin"]), None)
    if direction:
        assert o["origin"] == "2026Q2" and o["direction"] == direction and o["expected"] == -direction
    if want == C.UNDECIDED:
        assert "fönstret öppet" in m["reason"]
    nat = r["measures"]["el1_ob_nat"]
    assert nat["period"] == "2026Q3" and nat["pace"] == pytest.approx(x_jump)
    cap = r["measures"][E.CAPEX_INNER]
    assert cap["change"] == pytest.approx(y_inc - 10.0)
    text = E.short(m)
    assert text.startswith(C.OUTCOME_TEXT[want])
    if want in (C.FOR, C.AGAINST):
        assert text.endswith("uppåt" if direction > 0 else "nedåt")


def test_both_directions_are_counted_alike():
    up = _main(E.compute(DAY, table=world(20.0, 0.0)))["history"]
    down = _main(E.compute(DAY, table=world(-20.0, 20.0)))["history"]
    assert (up["impulses_up"], up["impulses_down"]) == (2, 0)  # origins 2026Q1, 2026Q2 before t
    assert (down["impulses_up"], down["impulses_down"]) == (0, 2)
    assert up["by_direction"]["up"][C.FOR] == down["by_direction"]["down"][C.FOR]


def test_flat_price_and_load_give_no_impulse():
    r = E.compute(DAY, table=world())
    for x in ("pris", "last"):
        rr = r["readings"][f"{x}|capex"]
        assert rr["outcome"] == C.NEITHER and r["measures"][E.X[x]]["pace"] == pytest.approx(0.0)


# ------------------------------------------------------------------ monthly to quarterly, and dating


def test_twelve_month_mean_ends_with_the_quarters_last_month_and_is_dated_by_the_latest_month():
    t = world()
    vals = {m: float(i) for i, m in enumerate(MONTHS, start=1)}
    t = pd.concat([t[t["series"] != E.PPI], _rows(E.PPI, "M", vals, _m_kf)], ignore_index=True)
    rows = E.derived_rows(E.FORMULAS["el1_pris4"], E._cut(t, pd.Timestamp(DAY)))
    last = rows[rows["period"] == "2026Q3"]
    months = [str(m) for m in pd.period_range("2025-10", "2026-09", freq="M")]
    assert float(last["value"].iloc[0]) == pytest.approx(np.mean([vals[m] for m in months]))
    assert last["known_from"].iloc[0] == _m_kf("2026-09")
    assert min(rows["period"]) == "2021Q4" and all(p[4] == "Q" for p in rows["period"])  # first twelve months: 2021


def test_a_missing_month_or_area_gives_no_quarter():
    t = world()
    t = t[~((t["series"] == "eia930_avg_soco_m") & (t["period"] == "2026-08"))]
    m = E.compute(DAY, table=t)["measures"]["el1_last4"]
    assert m["period"] == "2026Q2"  # 2026Q3's twelve months need 2026-08 in every area
    assert m["path"]["2026Q2"]["level"] == pytest.approx(5 * 10_000.0)


def test_missing_member_gives_no_aggregate_and_says_who():
    t = world()
    t = t[~((t["series"] == "rpo_etn") & (t["period"] == "2026Q3"))]
    m = E.compute(DAY, table=t)["measures"]["el1_ob_nat"]
    assert m["period"] == "2026Q2"
    assert m["missing_next"] == {"period": "2026Q3", "inputs": {"rpo_etn": ["2026Q3"]}}


# ------------------------------------------------------------------ the as-of boundary


def test_a_row_known_after_the_day_changes_nothing():
    base = world(20.0, 0.0)
    day = pd.Timestamp(DAY)
    late = pd.concat([
        _rows("rpo_pwr", "Q", {"2026Q3": 1e9}, lambda q: day + pd.Timedelta(days=1)),  # a later vintage
        _rows(E.CAPEX_INNER, "Q", {"2026Q4": 1e9}, lambda q: day + pd.Timedelta(days=2)),  # a later quarter
        _rows(E.PPI, "M", {"2026-10": 1e6, "2026-11": 1e6, "2026-12": 1e6}, lambda m: day + pd.Timedelta(days=3)),
    ], ignore_index=True)
    a = E.compute(DAY, table=base)
    b = E.compute(DAY, table=pd.concat([base, late], ignore_index=True))
    a.pop("generated"), b.pop("generated")
    assert a == b
    assert E.render(a) == E.render(b)
    assert _main(a)["outcome"] == C.FOR


def test_the_day_before_a_filing_reads_the_quarter_before():
    t = world(20.0, 0.0)
    kf = t[(t["series"] == E.CAPEX_INNER) & (t["period"] == "2026Q3")]["known_from"].iloc[0]
    r = E.compute(str((kf - pd.Timedelta(days=1)).date()), table=t)
    assert r["measures"][E.CAPEX_INNER]["period"] == "2026Q2" and _main(r)["t"] == "2026Q2"


# ------------------------------------------------------------------ missing data


def test_missing_series_are_undecided_and_render():
    t = world()
    t = t[~t["series"].isin([E.GW, E.DLR_MW])]
    r = E.compute(DAY, table=t)
    assert r["readings"]["gw|capex"]["outcome"] == C.UNDECIDED
    assert r["measures"]["el1_dlr_mw4"]["available"] is False
    for x in E.X:
        rr = r["readings"][f"{x}|dlr"]
        assert rr["outcome"] == C.UNDECIDED and rr["t"] is None
    text = E.render(r)
    assert "Regeln kunde inte prövas" in text or "kan inte avgöras" in text
    row = E.antenna(r)
    assert set(row) == set(C.ANTENNA_KEYS)


def test_empty_table():
    t = world().iloc[0:0]
    r = E.compute(DAY, table=t)
    assert all(rr["outcome"] == C.UNDECIDED for rr in r["readings"].values())
    E.render(r)
    assert E.antenna(r)["next_unseen_date"] is None


# ------------------------------------------------------------------ discovery, antenna, render


def test_found_as_a_question_and_in_antenner():
    assert followed.questions()["elflaskhalsen"] is E
    t = world(20.0, 0.0)
    a = AN.compute(DAY, table=t, modules={"elflaskhalsen": E})
    row = a["rows"][0]
    assert not row.get("error") and row["outcome"] == C.FOR and row["t"] == "2026Q3"
    assert row["previous"]["t"] == "2026Q2"  # 2026-10-26: the inner layer's 2026Q3 is filed 2026-10-31
    assert any(c.startswith("kvartal: 2026Q2 → 2026Q3") for c in row["changes"])


def test_antenna_and_next_unseen():
    r = E.compute(DAY, table=world(20.0, 0.0))
    row = E.antenna(r)
    assert row["reading"] == "talar för mekanismen, uppåt" and len(row["facts"]) == 7 + 3
    assert row["next_unseen_date"] == "2027-01-30"  # 2026Q4 end + the longest median lag of the four (30 days)
    assert row["next_unseen"].startswith("inre lagrets capex för 2026Q4")
    old = E.compute("2025-11-26", table=world(20.0, 0.0))
    assert old["seen_before_register"] and old["next_unseen"].startswith("inre lagrets capex för 2026Q4")


def test_render_has_every_row_and_the_seen_data_note():
    r = E.compute(DAY, table=world(20.0, 0.0))
    text = E.render(r)
    assert text.startswith("# Elflaskhalsen per 2026-11-26")
    for x in E.X:
        assert text.count(E.XNAME[x]) >= 2
    assert "(huvudläsning):** talar för mekanismen, uppåt" in text
    assert "inget utfall på" in text and "osedda data" in text
    assert "Regeln kunde prövas i" in text


# ------------------------------------------------------------------ the real table (shared base + track view)

RESULTS = config.REPO / "docs" / "resultat" / "elflaskhalsen.md"


def _demote(text: str) -> str:
    return "\n".join(("#" + x) if x.startswith("#") else x for x in text.split("\n"))


@pytest.fixture(scope="module")
def real():
    from ai_tracker import observations

    t = observations.load()
    if t.empty or E.CAPEX_INNER not in set(t["series"]) or "rpo_pwr" not in set(t["series"]):
        pytest.skip("no real observation table with the EL1 series")
    return t


@pytest.mark.real_data
@pytest.mark.parametrize("day,main", [("2026-11-26", C.AGAINST), ("2025-11-26", C.UNDECIDED)])
def test_results_document_is_the_command_output(real, day, main):
    r = E.compute(day, table=real)
    assert _main(r)["outcome"] == main
    assert _demote(E.render(r)).strip("\n") in RESULTS.read_text(encoding="utf-8")


def test_results_say_the_readings_are_on_seen_data():
    res = RESULTS.read_text(encoding="utf-8")
    assert "Läsningarna är gjorda på sedda data" in res and "Vad som skiljer de två dagarna" in res
