"""N7 (nowcast/n7.py): straight-line world where V1 and V2 are exact, as_of truncation and poison rows, undefined
variants, definition breaks, the grouped DM test and the decision rule. Synthetic fixtures only, no network."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from ai_tracker import evaluation
from ai_tracker.nowcast import __main__ as cli
from ai_tracker.nowcast import engine, n1, n7

TS = pd.Timestamp
Q = "Q-DEC"
QS = pd.period_range("2008Q1", "2024Q4", freq=Q)
ENDS = QS.end_time.normalize()
J_TRUE = 20  # N = 5 years
C_TRUE = 0.9
CONST = 16  # the last 16 quarters of capex grow at a constant rate


def _rows(series, periods, values, known_from, freq="Q", source="release"):
    return pd.DataFrame({"series": series, "freq": freq, "period": [str(p) for p in periods],
                         "value": np.asarray(values, dtype=float), "known_from": pd.to_datetime(list(known_from)),
                         "source": source, "fetched_at": TS("2026-11-24")})


def capex_path(n, seed, start):
    rng = np.random.default_rng(seed)
    g = 0.02 + 0.06 * rng.standard_normal(n)
    g[-CONST:] = 0.08
    return start * np.exp(np.cumsum(g))


def straight_line(x, J=J_TRUE, c=C_TRUE):
    """dep(t) = c * mean(capex(t-J) .. capex(t-1)); NaN where the window is incomplete."""
    out = np.full(len(x), np.nan)
    for i in range(J, len(x)):
        out[i] = c * x[i - J:i].mean()
    return out


def make_table(lives=True) -> pd.DataFrame:
    parts = []
    for i, c in enumerate(n7.COMPANIES):
        x = capex_path(len(QS), 1 + i, 1000 * (i + 1))
        kf = ENDS + pd.Timedelta(days=25 + 2 * i)
        parts.append(_rows(f"capex_{c}", QS, x, kf))
        d = straight_line(x)
        ok = ~np.isnan(d)
        parts.append(_rows(f"dep_{c}", QS[ok], d[ok], kf[ok]))
        if lives:  # a stated server life of 5 years, known from 2012
            parts.append(_rows(f"useful_life_servers_{c}_hi", [QS[16]], [5.0], [TS("2012-02-01")]))
    return pd.concat(parts, ignore_index=True)


@pytest.fixture(scope="module")
def table():
    return make_table()


@pytest.fixture(scope="module")
def prepared(table):
    return n7.prepare(table)


EXACT_ORIGIN = n1.origin_for(QS[-8])  # L = QS[-9]; L - 4 .. L + 7 lie in the constant-growth stretch


def _levels(f: n7.Forecast) -> dict:
    return {(m, h): v for m, d in f.levels.items() for h, v in d.items()}


# ------------------------------------------------------------------ straight-line world


@pytest.mark.parametrize("unit", [n7.N7, *n7.N7B], ids=lambda u: u.key)
def test_v1_and_v2_are_exact_in_a_straight_line_world(prepared, unit):
    f = n7.forecast(prepared, unit, EXACT_ORIGIN, {})
    assert f.base == QS[-9]
    assert f.fits["V1"].N == 5 and f.fits["V1"].c == pytest.approx(C_TRUE, rel=1e-10)
    assert f.fits["V1"].maes[5] == pytest.approx(0.0, abs=1e-9)
    assert all(f.fits["V1"].maes[N] > 1e-6 for N in f.fits["V1"].maes if N != 5)
    assert f.fits["V2"].J == {c: 20 for c in unit.companies}
    truth = engine.first_vintage(prepared, unit.key)
    for h in n7.HORIZONS:
        q = f.base + h
        for v in ("V1", "V2"):
            assert engine.log_error(f.levels[v][h], truth[q]) == pytest.approx(0.0, abs=1e-8), (v, h)
    # the drift baseline is not exact: depreciation growth still adjusts to the new capex growth
    assert max(abs(engine.log_error(f.levels["B1"][h], truth[f.base + h])) for h in n7.HORIZONS) > 1.0


def test_h1_is_the_quarter_just_ended(prepared):
    q = pd.Period("2019Q2", freq=Q)
    f = n7.forecast(prepared, n7.N7B[0], n1.origin_for(q), {})
    assert f.base == q - 1 and f.base + 1 == q


def test_hyp4_target_is_rebuilt_from_the_companies(table, prepared):
    y = engine.first_vintage(prepared, n7.TARGET)
    total = sum(engine.first_vintage(prepared, f"dep_{c}") for c in n7.COMPANIES).dropna()
    pd.testing.assert_series_equal(y.loc[total.index], total.rename(n7.TARGET), check_names=False)
    stale = _rows(n7.TARGET, [QS[30]], [1.0], [TS("2010-01-01")])  # a stored dep_hyp4 row is replaced
    assert n7.prepare(pd.concat([table, stale]))[lambda d: d.series == n7.TARGET]["value"].min() > 1.0


# ------------------------------------------------------------------ information set


@pytest.mark.parametrize("unit", [n7.N7, n7.N7B[2]], ids=lambda u: u.key)
@pytest.mark.parametrize("origin", [EXACT_ORIGIN, n1.origin_for(QS[40]), n1.origin_for(QS[25])])
def test_truncated_table_gives_identical_forecasts(table, unit, origin):
    full = n7.forecast(n7.prepare(table), unit, origin, {})
    cut = n7.forecast(n7.prepare(table[table["known_from"] <= origin]), unit, origin, {})
    a, b = _levels(full), _levels(cut)
    assert a.keys() == b.keys()
    for k in a:
        assert (math.isnan(a[k]) and math.isnan(b[k])) or a[k] == b[k], k


def test_rows_known_after_the_origin_change_nothing(table):
    origin = n1.origin_for(QS[40])
    late = origin + pd.Timedelta(days=1)
    poison = pd.concat([
        _rows("dep_msft", QS[30:40], np.full(10, 1e9), [late] * 10),  # revisions published after the origin
        _rows("capex_msft", QS[30:60], np.full(30, 1e9), [late] * 30),  # incl. future quarters
        _rows("useful_life_servers_msft_hi", [QS[39]], [10.0], [late]),
    ])
    a = n7.forecast(n7.prepare(table), n7.N7B[0], origin, {})
    b = n7.forecast(n7.prepare(pd.concat([table, poison], ignore_index=True)), n7.N7B[0], origin, {})
    assert _levels(a) == _levels(b)


def test_stated_life_is_the_latest_known_value(table):
    extra = pd.concat([_rows("useful_life_servers_meta_hi", [QS[24]], [4.0], [TS("2014-02-01")]),
                       _rows("useful_life_servers_meta_hi", [QS[32]], [6.0], [TS("2017-01-25")])])
    t = n7.prepare(pd.concat([table, extra], ignore_index=True))
    info = engine.InfoSet(t, TS("2016-12-31"))
    assert n7.stated_life(info, "useful_life_servers_meta_hi") == 4.0
    assert n7.stated_life(engine.InfoSet(t, TS("2017-01-25")), "useful_life_servers_meta_hi") == 6.0


# ------------------------------------------------------------------ undefined variants


def test_short_capex_history_leaves_v1_missing(prepared):
    early = n1.origin_for(QS[24])  # dep known from QS[20]: 4 rows, fewer than 12
    f = n7.forecast(prepared, n7.N7B[1], early, {})
    assert all(math.isnan(v) for v in f.levels["V1"].values())
    assert "12 complete training rows" in f.reasons["V1"]
    assert all(np.isfinite(v) for v in f.levels["B0"].values())


def test_no_stated_life_leaves_v2_missing(table):
    t = n7.prepare(make_table(lives=False))
    f = n7.forecast(t, n7.N7B[0], EXACT_ORIGIN, {})
    assert all(math.isnan(v) for v in f.levels["V2"].values())
    assert "not known" in f.reasons["V2"]
    assert np.isfinite(f.levels["V1"][1])


def test_v2_missing_when_its_window_lacks_rows(table):
    long_life = _rows("useful_life_servers_googl_hi", [QS[40]], [10.0], [TS("2017-01-01")])
    t = n7.prepare(pd.concat([table, long_life], ignore_index=True))
    f = n7.forecast(t, n7.N7B[1], n1.origin_for(QS[44]), {})  # J = 40: rows from QS[40] only
    assert math.isnan(f.levels["V2"][1]) and "training rows" in f.reasons["V2"]


def test_frame_marks_the_evaluation_start_and_scores_first_vintages(prepared):
    unit = n7.N7B[3]
    origin_list = [n1.origin_for(q) for q in QS[24:40]]
    f = n7.frame(prepared, unit, origin_list)
    start = f.attrs["start"]
    assert start is not None
    assert not f.loc[f["origin"] < start, "in_period"].any()
    assert f.loc[f["origin"] >= start, "in_period"].all()
    assert f.loc[f["origin"] < start, "V1"].isna().all()
    assert (f["quarter"] == f["base"] + f["h"]).all()
    assert (pd.to_datetime(f["outcome_known_from"]) > pd.to_datetime(f["origin"])).all()


# ------------------------------------------------------------------ definition breaks


def test_a_break_quarter_is_not_scored_and_blocks_b1(table):
    # the first filing of QS[44] restates QS[43] by +5 %: a definition break (F-B8)
    d = table[(table.series == "dep_meta") & (table.period == str(QS[43]))].iloc[0]
    kf44 = table[(table.series == "dep_meta") & (table.period == str(QS[44]))]["known_from"].iloc[0]
    restated = _rows("dep_meta", [QS[43]], [d["value"] * 1.05], [kf44])
    t = n7.prepare(pd.concat([table, restated], ignore_index=True))
    origin_list = [n1.origin_for(q) for q in QS[40:50]]
    f = n7.frame(t, n7.N7B[3], origin_list)
    assert str(QS[44]) in f.attrs["break_quarters"]
    assert not (f["quarter"] == QS[44]).any()
    after = n7.forecast(t, n7.N7B[3], n1.origin_for(QS[46]), n7.quarterly.breaks(t, n7.N7B[3].aggregate))
    assert all(math.isnan(v) for v in after.levels["B1"].values())
    assert "definition break" in after.reasons["B1"]


# ------------------------------------------------------------------ test and decision


def test_group_dm_equals_dm_test_with_one_row_per_origin():
    rng = np.random.default_rng(3)
    T = 30
    rows = pd.DataFrame({"origin": pd.date_range("2015-01-20", periods=T, freq="QS-JAN") + pd.Timedelta(days=19),
                         "a": rng.normal(0, 2, T), "b": rng.normal(0, 3, T)})
    g = n7.group_dm(rows, "a", "b", h_max=1)
    d = evaluation.dm_test(rows["a"].to_numpy(), rows["b"].to_numpy())
    assert g.testable and g.lag == d.lag
    assert g.p == pytest.approx(d.p) and g.mean_diff == pytest.approx(d.mean_diff) and g.mde == pytest.approx(d.mde)


def test_group_dm_lag_covers_the_overlap_and_needs_eight_origins():
    rng = np.random.default_rng(4)
    o = pd.date_range("2010-01-20", periods=40, freq="QS-JAN") + pd.Timedelta(days=19)
    rows = pd.DataFrame({"origin": np.repeat(o, 4), "a": rng.normal(0, 1, 160), "b": rng.normal(0, 2, 160)})
    assert n7.group_dm(rows, "a", "b", h_max=8).lag == 7
    short = rows[rows["origin"] < o[7]]
    r = n7.group_dm(short, "a", "b", h_max=2)
    assert not r.testable and math.isnan(r.p) and "T = 7" in r.note


def _synthetic_frame(unit, start="2014-01-20", T=50, v1_sd=1.0, base_sd=6.0, seed=0, v2_rows=True):
    rng = np.random.default_rng(seed)
    o = pd.date_range(start, periods=T, freq="QS-JAN") + pd.Timedelta(days=19)
    rows = []
    for origin in o:
        for h in n7.HORIZONS:
            rows.append({"unit": unit, "origin": origin, "h": h, "in_period": True,
                         "outcome_known_from": origin + pd.Timedelta(days=95 * h),
                         "B0": rng.normal(0, base_sd), "B1": rng.normal(0, base_sd), "V1": rng.normal(0, v1_sd),
                         "V2": rng.normal(0, v1_sd) if v2_rows or origin.year < 2016 else np.nan})
    return pd.DataFrame(rows)


def test_decision_rule_passing_variant_is_conditional_and_b1_stays():
    fb = _synthetic_frame("dep_meta", T=50, v2_rows=False)
    f7 = _synthetic_frame("dep_hyp4", start="2026-01-20", T=3)  # fewer than 8 origins: N7b decides
    res = {"N7": n7.evaluate(f7), "N7b": n7.evaluate(fb), "_frames": {"N7": f7, "N7b": fb}}
    for per in n7.PERIODS:  # the Holm family has 6 members in each period
        assert len([1 for g in n7.GROUPS for v in n7.VARIANTS if "holm_p" in res["N7b"][per][g][v]]) == 6
    d = n7.decide(res)
    for g in n7.GROUPS:
        c = d[g]["checks"]
        assert c["V1"]["scope"] == "N7b" and c["V1"]["passes"]
        assert not c["V2"]["passes"]  # V2 has 8 origins (2014-2015) and no rows from 2023
        assert d[g]["champion"] == "B1" and "V1" in d[g]["conditional"] and d[g]["best_conditional"] == "V1"
    assert res["N7"]["full"]["h1–2"]["V1"]["T"] == 3


def test_no_variant_passes_when_it_is_no_better():
    fb = _synthetic_frame("dep_meta", T=50, v1_sd=6.0, base_sd=6.0, seed=1)
    res = {"N7": n7.evaluate(fb.iloc[:0]), "N7b": n7.evaluate(fb), "_frames": {"N7": fb.iloc[:0], "N7b": fb}}
    d = n7.decide(res)
    assert all(d[g]["champion"] == "B1" and not d[g]["conditional"] for g in n7.GROUPS)


def test_backtest_on_synthetic_table(table, monkeypatch, tmp_path):
    monkeypatch.setattr(evaluation, "RUNS_DIR", tmp_path)
    origin_list = [n1.origin_for(q) for q in QS[28:60]]
    out = n7.backtest(table, origin_list=origin_list)
    assert out["log"].parent == tmp_path and out["log"].name.endswith("_n7_backtest.csv")
    assert set(out["frames"]) == {"N7", "N7b"}
    assert set(out["frames"]["N7b"]["unit"]) == {u.key for u in n7.N7B}
    report = n7.format_report(out)
    assert "decision h1–2" in report
    md = n7.markdown_tables(out, "N7b")
    assert "| h1–2 | V1 |" in md
    assert n7.markdown_per_h(out, "N7b").count("\n") > 2


def test_cli_runs_the_n7_backtest(monkeypatch, capsys):
    called = {}

    def fake_backtest():
        called["yes"] = True
        return {"log": "x.csv"}

    monkeypatch.setattr(n7, "backtest", fake_backtest)
    monkeypatch.setattr(n7, "format_report", lambda out: "report")
    assert cli.main(["backtest", "n7"]) == 0
    assert called and "report" in capsys.readouterr().out
