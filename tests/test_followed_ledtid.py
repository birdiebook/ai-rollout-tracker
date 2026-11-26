"""LT1 "Ledtid i stacken" (register 2026-11-26 "LT1"). Synthetic data only.

- the catalog series: sums of the members, publish=False, classified, the stored rows equal the module's derivation
- the registered parameters and the reading in both directions, with each quantity's own limit
- the O1 transformation of a growth rate (yoy %) into pace and change in pace
- compute on a synthetic world: up-up, down-down and up-down patterns; the as-of boundary (a row known after the day
  changes nothing); a missing member and missing data
- render, antenna and the CLI
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from ai_tracker import catalog, licenses
from ai_tracker.followed import __main__ as CLI
from ai_tracker.followed import common as C
from ai_tracker.followed import ledtid as L
from ai_tracker.series import ledtid as LS

QS = [str(q) for q in pd.period_range("2019Q1", "2026Q3", freq="Q-DEC")]
INNER = ("msft", "googl", "amzn", "meta")


def _kf(q: str, lag: int = 30) -> pd.Timestamp:
    return pd.Period(q, freq="Q-DEC").end_time.normalize() + pd.Timedelta(days=lag)


def _rows(series: str, values: dict[str, float], lag: int = 30) -> pd.DataFrame:
    return pd.DataFrame([{"series": series, "freq": "Q", "period": p, "value": float(v), "known_from": _kf(p, lag),
                          "source": "release", "fetched_at": pd.Timestamp("2026-11-26")} for p, v in values.items()])


def _path(step: str, g1: float, g2: float, base: float = 1000.0, qs=QS) -> dict[str, float]:
    """Exponential path: quarterly log growth g1 before `step`, g2 from `step` on."""
    out, y = {}, math.log(base)
    for q in qs:
        y += g2 if pd.Period(q, freq="Q-DEC") >= pd.Period(step, freq="Q-DEC") else g1
        out[q] = math.exp(y)
    return out


def _world(supplier: tuple[str, float, float], buyer: tuple[str, float, float], qs=QS) -> pd.DataFrame:
    """L1 (rpo_etn, rpo_pwr) and the inner layer's quarterly capex, each with one step in growth."""
    parts = [_rows(f"rpo_{c}", _path(*supplier, qs=qs), lag=35) for c in LS.POWER]
    parts += [_rows(f"capex_{c}", _path(*buyer, base=100.0, qs=qs), lag=28) for c in INNER]
    return pd.concat(parts, ignore_index=True)


@pytest.fixture(autouse=True)
def _no_f1(monkeypatch):
    from ai_tracker.series import guidance_revisions as F1

    monkeypatch.setattr(F1, "load_csv", lambda: None)


# ------------------------------------------------------------------ catalog


def test_catalog_series_are_member_sums_unpublished_and_classified():
    specs = catalog.by_key()
    assert catalog.validate() == []
    for key in ("lt1_rpo_power", "lt1_rpo_net", "lt1_dlr_bookings4"):
        s = specs[key]
        assert s.publish is False and s.components and s.license.strip()
        assert licenses.verdict(s, specs).klass in licenses.CLASSES
        assert licenses.source_group(s.source)[1] == "kallor/ledtid.md"
    assert specs["lt1_rpo_power"].components == ("rpo_etn", "rpo_pwr")
    assert specs["lt1_rpo_net"].components == ("rpo_csco", "rpo_dell", "rpo_smci")
    assert specs["lt1_dlr_bookings4"].components == (LS.DLR_BOOKINGS,)


def test_stored_rows_equal_the_module_derivation_and_wait_for_every_member():
    w = _world(("2025Q1", 0.02, 0.10), ("2025Q2", 0.02, 0.10))
    late = w[(w["series"] == "rpo_pwr") & (w["period"] == "2026Q3")].index
    w.loc[late, "known_from"] = pd.Timestamp("2026-12-15")
    stored = catalog.by_key()["lt1_rpo_power"].fetch(w)
    derived = L.table_on("2027-01-01", w)
    d = derived[derived["series"] == "lt1_rpo_power"].sort_values("period", ignore_index=True)
    assert list(d["period"]) == list(stored.sort_values("period")["period"])
    assert np.allclose(d["value"], stored.sort_values("period")["value"])
    q3 = d[d["period"] == "2026Q3"].iloc[0]
    assert q3["known_from"] == pd.Timestamp("2026-12-15")  # dated by the latest member
    assert q3["value"] == pytest.approx(sum(_path("2025Q1", 0.02, 0.10)["2026Q3"] for _ in LS.POWER))
    on = L.table_on("2026-12-01", w)
    assert "2026Q3" not in set(on[on["series"] == "lt1_rpo_power"]["period"])  # Quanta has not filed on the day


# ------------------------------------------------------------------ the registered reading


def test_registered_parameters():
    assert (L.G_BUYER, L.G_SUPPLIER, L.WINDOWS, L.SIGN) == (5.0, 10.0, (2, 4), 1)
    assert L.limits("fore") == (10.0, 5.0) and L.limits("efter") == (5.0, 10.0)
    assert L.MAIN == ("L1", "inner", "fore", 2) and L.REGISTERED == "2026-11-26"
    assert len(L.ROWS) * len(L.DIRECTIONS) * len(L.WINDOWS) == 24
    assert L.acquisition_quarters("L2") == {q: "Cisco–Splunk" for q in ("2024Q1", "2024Q2", "2025Q1", "2025Q2")}


def _m(key: str, change: dict[str, float]) -> dict:
    qs = sorted(change, key=lambda q: pd.Period(q, freq="Q-DEC"))
    return {"series": key, "available": True, "period": qs[-1],
            "path": {q: {"level": 1.0, "pace": 0.0, "change": v} for q, v in change.items()}}


def _ms(sup: dict[str, float], buy: dict[str, float]) -> dict[str, dict]:
    return {"lt1_rpo_power": _m("lt1_rpo_power", sup), "kl_capex4_inner": _m("kl_capex4_inner", buy)}


Q = ["2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2"]


@pytest.mark.parametrize("sup, buy, want, d", [
    ([0, 12, 0, 0, 0, 0], [0, 0, 6, 0, 0, 0], C.FOR, 1),        # orders up, then capex pace up
    ([0, -12, 0, 0, 0, 0], [0, 0, -6, 0, 0, 0], C.FOR, -1),     # orders down, then capex pace down: as much for
    ([0, 12, 0, 0, 0, 0], [0, 0, -6, 0, 0, 0], C.AGAINST, 1),   # orders up, capex pace down
    ([0, 9, 0, 0, 0, 0], [0, 0, 6, 0, 0, 0], C.NEITHER, 0),     # 9 < g = 10 for a supplier: no impulse
    ([0, 12, 0, 0, 0, 0], [0, 0, 4, 0, 0, 0], C.NEITHER, 1),    # 4 < h = 5 for a buyer
])
def test_reading_before(sup, buy, want, d):
    ms = _ms(dict(zip(Q, sup)), dict(zip(Q, buy)))
    r = L.reading("L1", "inner", "fore", 4, ms)
    assert r["outcome"] == want and r["t"] == "2026Q2" and (r["origin"] is None) == (d == 0)
    if d:
        o = next(x for x in r["origins"] if x["origin"] == r["origin"])
        assert o["direction"] == d and r["params"] == {"g": 10.0, "h": 5.0, "k": 4, "sign": 1}


@pytest.mark.parametrize("buy, sup, want", [
    ([0, 6, 0, 0, 0, 0], [0, 0, 11, 0, 0, 0], C.FOR),        # capex pace up first, then orders: "efter" talar för
    ([0, -6, 0, 0, 0, 0], [0, 0, -11, 0, 0, 0], C.FOR),
    ([0, 6, 0, 0, 0, 0], [0, 0, -11, 0, 0, 0], C.AGAINST),
    ([0, 6, 0, 0, 0, 0], [0, 0, 9, 0, 0, 0], C.NEITHER),     # 9 < h = 10 for a supplier as Y
    ([0, 4, 0, 0, 0, 0], [0, 0, 11, 0, 0, 0], C.NEITHER),    # 4 < g = 5 for a buyer as X
])
def test_reading_after_swaps_the_roles_and_the_limits(buy, sup, want):
    ms = _ms(dict(zip(Q, sup)), dict(zip(Q, buy)))
    r = L.reading("L1", "inner", "efter", 4, ms)
    assert r["outcome"] == want and r["x_series"] == "kl_capex4_inner" and r["y_series"] == "lt1_rpo_power"
    assert r["params"]["g"] == 5.0 and r["params"]["h"] == 10.0


def test_window_open_and_missing_y_cannot_be_decided():
    ms = _ms({"2025Q4": 0, "2026Q1": 12}, {"2025Q4": 0, "2026Q1": 0, "2026Q2": 1})
    r = L.reading("L1", "inner", "fore", 2, ms)  # t = 2026Q2, Y(2026Q2) below h, 2026Q3 not yet known
    assert r["outcome"] == C.UNDECIDED and "fönstret öppet" in r["origins"][-1]["reason"]
    ms["kl_capex4_inner"] = {"series": "kl_capex4_inner", "available": False}
    assert L.reading("L1", "inner", "fore", 2, ms)["outcome"] == C.UNDECIDED


def test_lead_time_and_acquisition_marks():
    sup = {"2023Q1": 12, "2023Q2": 0, "2023Q3": 0, "2023Q4": 0, "2024Q1": -12, "2024Q2": 0, "2024Q3": 0,
           "2024Q4": 0, "2025Q1": 0, "2025Q2": 0}
    buy = {"2023Q1": 0, "2023Q2": 0, "2023Q3": 7, "2023Q4": 0, "2024Q1": 0, "2024Q2": -6, "2024Q3": 0, "2024Q4": 0,
           "2025Q1": 0, "2025Q2": 0}
    ms = {"lt1_rpo_net": _m("lt1_rpo_net", sup), "kl_capex4_inner": _m("kl_capex4_inner", buy)}
    r = L.reading("L2", "inner", "fore", 4, ms)
    assert [(x["origin"], x["lag"], x["direction"]) for x in r["lags"]] == [("2023Q1", 2, 1), ("2024Q1", 1, -1)]
    assert r["lags"][1]["acquisition"] == "Cisco–Splunk" and r["lags"][0]["acquisition"] is None
    lt = L.lead_time(r)
    assert (lt["latest"], lt["median_before"], lt["n_before"]) == (1, 2.0, 1)
    # in "efter" the supplier is Y: the mark goes on the deciding quarter
    ms2 = {"lt1_rpo_net": _m("lt1_rpo_net", {"2023Q3": 0, "2023Q4": 0, "2024Q1": 0, "2024Q2": 15, "2024Q3": 0}),
           "kl_capex4_inner": _m("kl_capex4_inner", {"2023Q3": 0, "2023Q4": 0, "2024Q1": 6, "2024Q2": 0,
                                                     "2024Q3": 0})}
    e = L.reading("L2", "inner", "efter", 2, ms2)
    assert e["outcome"] == C.FOR and e["origin_acquisition"] == "Cisco–Splunk"
    assert L.lead_time({"lags": []})["latest"] is None


# ------------------------------------------------------------------ O1: a growth rate, not a level


def test_yoy_measure_transforms_a_growth_rate():
    v = {"2025Q1": 10.0, "2025Q2": 20.0, "2025Q3": 30.0, "2025Q4": -50.0}
    t = _rows(L.EATON_ORDERS, v)
    m = L.yoy_measure(t, L.EATON_ORDERS, "2026-03-01")
    assert m["available"] and m["period"] == "2025Q4" and m["level"] == -50.0 and m["surprise"] is None
    assert m["path"]["2025Q1"]["pace"] == pytest.approx(100 * math.log(1.10))
    assert m["path"]["2025Q3"]["change"] == pytest.approx(100 * (math.log(1.30) - math.log(1.10)))
    assert m["change"] == pytest.approx(100 * (math.log(0.5) - math.log(1.2)))
    assert m["path"]["2025Q2"]["change"] is None  # needs two quarters back
    assert not L.yoy_measure(t, L.EATON_ORDERS, "2025-04-01")["available"]  # nothing known on the day


# ------------------------------------------------------------------ compute on a synthetic world


@pytest.mark.parametrize("supplier, buyer, want, d", [
    (("2025Q4", 0.02, 0.12), ("2026Q1", 0.02, 0.12), C.FOR, 1),
    (("2025Q4", 0.10, -0.02), ("2026Q1", 0.10, -0.02), C.FOR, -1),
    (("2025Q4", 0.02, 0.12), ("2026Q1", 0.10, -0.02), C.AGAINST, 1),
])
def test_compute_main_reading_both_ways(supplier, buyer, want, d):
    qs = [q for q in QS if q <= "2026Q2"]
    w = _world(supplier, buyer, qs=qs)
    r = L.compute("2026-09-30", table=w)
    main = L.find(r, *L.MAIN)
    assert main["t"] == "2026Q2" and main["outcome"] == want
    o = next(x for x in main["origins"] if x["origin"] == main["origin"])
    assert o["direction"] == d
    a = L.antenna(r)
    assert set(a) == set(C.ANTENNA_KEYS) and a["outcome"] == want and a["t"] == "2026Q2"


def test_a_row_known_after_the_day_changes_nothing():
    w = _world(("2025Q4", 0.02, 0.12), ("2026Q1", 0.02, 0.12), qs=[q for q in QS if q <= "2026Q2"])
    day = "2026-09-30"
    base = L.compute(day, table=w)
    extra = pd.concat([w,
                       _rows("rpo_etn", {"2026Q2": 1.0}, lag=200),       # a revision known after the day
                       _rows("rpo_etn", {"2026Q3": 9e9}, lag=10),        # a quarter known after the day
                       _rows("capex_msft", {"2026Q3": 9e9}, lag=10),
                       _rows(L.EATON_ORDERS, {"2026Q3": 500.0}, lag=10)], ignore_index=True)
    later = L.compute(day, table=extra)
    assert pd.Timestamp(day) < _kf("2026Q3", 10)
    strip = lambda r: {k: v for k, v in r.items() if k != "generated"}  # noqa: E731
    assert strip(later) == strip(base)
    assert L.render(later) == L.render(base)
    cut = L.compute(day, table=extra[extra["known_from"] <= pd.Timestamp(day)])
    assert strip(cut) == strip(base)
    on = L.compute("2026-11-01", table=extra)  # Eaton has filed 2026Q3, Quanta not: no aggregate for the quarter
    assert on["measures"]["lt1_rpo_power"]["period"] == "2026Q2" and on["missing"]["lt1_rpo_power"] == ["rpo_pwr (2026Q3)"]


def test_missing_member_and_missing_data():
    w = _world(("2025Q4", 0.02, 0.12), ("2026Q1", 0.02, 0.12), qs=[q for q in QS if q <= "2026Q2"])
    w = w[~((w["series"] == "rpo_pwr") & (w["period"] == "2026Q2"))]
    r = L.compute("2026-09-30", table=w)
    assert r["measures"]["lt1_rpo_power"]["period"] == "2026Q1"
    assert r["missing"]["lt1_rpo_power"] == ["rpo_pwr (2026Q2)"]
    assert "`lt1_rpo_power` saknar rpo_pwr (2026Q2)" in L.render(r)
    # nothing for L2, L3, O1, O2 and the outer layer: every such reading cannot be decided, and the report renders
    for x in r["readings"]:
        if x["row"] != "L1" or x["buyer"] == "outer":
            assert x["outcome"] == C.UNDECIDED
    empty = L.compute("2026-09-30", table=w.iloc[:0])
    assert all(x["outcome"] == C.UNDECIDED for x in empty["readings"])
    assert L.antenna(empty)["outcome"] == C.UNDECIDED and "# Ledtid i stacken" in L.render(empty)


def test_render_flags_the_extraction_and_says_no_test():
    w = _world(("2025Q4", 0.02, 0.12), ("2026Q1", 0.02, 0.12), qs=[q for q in QS if q <= "2026Q2"])
    r = L.compute("2026-09-30", table=w)
    text = L.render(r)
    assert "publish=False` i väntan på granskningen" in text and "inget test" in text
    assert "Före och efter är inte varandras motsats" in text and text.count("| K-inre | före |") == text.count("| K-inre | efter |") == 10
    assert r["seen_before_register"] is True and "inget utfall på osedda data" in text


def test_next_unseen_after_the_register():
    nx = {q: {"quantity": q, "period": "2026Q4", "estimated": None, "missing": []} for q in ("inner", "outer",
                                                                                         *L.SUPPLIERS)}
    nx["inner"]["estimated"] = "2027-01-31"
    nx["L2"].update(period="2026Q3", estimated="2026-12-09")
    text, day = L.next_unseen({"next": nx})
    assert day == "2026-12-09" and text.startswith("L2 efter K-inre med 2026Q3 omkring 2026-12-09")
    assert "huvudläsningen (L1 före K-inre)" in text and "2027-01-31" in text
    old = {q: {**x, "estimated": "2026-02-01" if x["estimated"] else None} for q, x in nx.items()}
    assert L.next_unseen({"next": old}) == ("med inlämningar efter 2026-11-26 (inga uppskattade ännu)", None)


def test_question_is_found_by_the_cli(tmp_path, monkeypatch):
    from ai_tracker import followed

    assert "ledtid" in followed.questions()
    w = _world(("2025Q4", 0.02, 0.12), ("2026Q1", 0.02, 0.12), qs=[q for q in QS if q <= "2026Q2"])
    monkeypatch.setattr(L, "compute", lambda as_of, table=None, _c=L.compute: _c(as_of, table=w))
    out = tmp_path / "r.md"
    assert CLI.main(["ledtid", "--as-of", "2026-09-30", "--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8").startswith("# Ledtid i stacken per 2026-09-30")
