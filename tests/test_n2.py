"""N2 nowcast (TSMC monthly revenue): leakage, first-vintage outcome, models, promotion rule, live writer.

Synthetic fixtures only, no network.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from ai_tracker import observations
from ai_tracker.nowcast_n2 import __main__ as live
from ai_tracker.nowcast_n2 import backtest, engine

P = lambda s: pd.Period(s, freq="M")  # noqa: E731
START, END = P("2007-01"), P("2024-06")


def _rows(series, periods, values, known_from, source):
    return pd.DataFrame({"series": series, "freq": "M", "period": [str(p) for p in periods], "value": values,
                         "known_from": pd.to_datetime(known_from), "source": source,
                         "fetched_at": pd.Timestamp("2026-11-23")})


@pytest.fixture(scope="module")
def table():
    """TSMC (6-K filed day 10 of m+1) whose B1 residual depends on import y/y growth two months back."""
    rng = np.random.default_rng(1)
    months = pd.period_range(START, END, freq="M")
    g = np.zeros(len(months))  # import y/y growth, 100 * log
    for i in range(1, len(months)):
        g[i] = 0.7 * g[i - 1] + rng.normal(0, 8)
    imp = np.zeros(len(months))
    imp[:12] = 7 + rng.normal(0, 0.05, 12)
    for i in range(12, len(months)):
        imp[i] = imp[i - 12] + g[i] / 100
    ly = np.zeros(len(months))
    ly[:13] = np.log(1e5) + rng.normal(0, 0.05, 13)
    for i in range(13, len(months)):
        r = 0.3 * g[i - 2] + rng.normal(0, 1.0)
        ly[i] = ly[i - 12] + ly[i - 1] - ly[i - 13] + r / 100
    tsmc_kf = [(p + 1).start_time + pd.Timedelta(days=9) for p in months]
    imp_kf = [p.end_time.normalize() + pd.Timedelta(days=41) for p in months]
    return pd.concat([_rows(engine.TARGET, months, np.exp(ly), tsmc_kf, "release"),
                      _rows("us_imports_tw_m", months, np.exp(imp), imp_kf, "backfill")], ignore_index=True)


@pytest.fixture(scope="module")
def frame(table):
    return backtest.run(table)


def test_cv_matches_brute_force():
    rng = np.random.default_rng(5)
    X = rng.normal(size=(70, 1))
    y = 0.4 * X[:, 0] + rng.normal(size=70)
    losses = []
    for lam in engine.LAMBDAS:
        losses.append(np.mean([abs(y[j] - engine.ridge_predict(engine.ridge_fit(X[:j], y[:j], lam), X[j:j + 1])[0])
                               for j in range(70 - engine.CV_FOLDS, 70)]))
    best = max(i for i, v in enumerate(losses) if v <= min(losses) + 1e-12)
    assert engine.choose_lambda(X, y) == engine.LAMBDAS[best]


def test_origin_and_target():
    assert engine.origin_for(P("2026-11")) == pd.Timestamp("2026-12-05")
    assert engine.target_for(pd.Timestamp("2026-12-05")) == P("2026-11")
    assert engine.origin_for(P("2026-12")) == pd.Timestamp("2027-01-05")


def test_baselines_exact(table):
    m = P("2014-06")
    f = engine.forecast(engine.origin_for(m), table)
    y = observations.as_of(engine.TARGET, "2030-01-01", table)
    assert np.exp(f.logs["B0"] / 100) == pytest.approx(y[m - 1])
    assert np.exp(f.logs["B1"] / 100) == pytest.approx(y[m - 12] * y[m - 1] / y[m - 13])
    # imports: FT-900 lag 41 days, so the latest month known on day 5 of m+1 is m-2
    imp = [p for s, p, *_ in f.inputs.used if s == "us_imports_tw_m"]
    assert max(imp) == str(m - 2)
    assert np.isfinite(f.logs["V1"]) and f.n_train >= engine.MIN_TRAIN


def test_value_known_after_origin_is_never_used(table):
    m = P("2014-06")
    origin = engine.origin_for(m)
    base = engine.forecast(origin, table)
    poison = pd.concat([
        _rows(engine.TARGET, [m - 1, m - 13], [1e12, 1e-3], [origin + pd.Timedelta(days=1)] * 2, "revision"),
        _rows("us_imports_tw_m", [m - 1, m - 2], [1e9, 1e9], [origin + pd.Timedelta(days=1)] * 2, "revision"),
    ])
    poisoned = engine.forecast(origin, pd.concat([table, poison], ignore_index=True))
    assert poisoned.logs == base.logs and poisoned.inputs.used == base.inputs.used
    assert all(pd.Timestamp(k) <= origin for *_, k in base.inputs.used)


def test_6k_filed_on_day_6_is_not_visible_at_day_5(table):
    m = P("2014-06")
    t = table.copy()
    t.loc[(t["series"] == engine.TARGET) & (t["period"] == str(m)), "known_from"] = pd.Timestamp("2014-07-06")
    f = engine.forecast(pd.Timestamp("2014-07-05"), t)
    assert str(m) not in [p for s, p, *_ in f.inputs.used if s == engine.TARGET]
    assert f.logs["B0"] == pytest.approx(100 * np.log(observations.as_of(engine.TARGET, "2014-07-05", t)[m - 1]))
    # and the run records that the outcome came after the origin
    frame = backtest.run(t)
    assert frame.at[m, "outcome_known_from"] > frame.at[m, "origin"]


def test_outcome_is_first_vintage(table, frame):
    k = P("2013-03")
    first = observations.as_of(engine.TARGET, "2030-01-01", table)[k]
    rev = _rows(engine.TARGET, [k], [first * 1.5], [pd.Timestamp("2013-08-01")], "revision")
    t = pd.concat([table, rev], ignore_index=True)
    assert engine.first_vintages(t).at[k, "value"] == pytest.approx(first)
    frame_rev = backtest.run(t)
    # error for k itself is measured against the first vintage
    assert frame_rev.at[k, "e_B0"] == pytest.approx(frame.at[k, "e_B0"])
    # a month whose inputs do not include k, but whose V1 trains on k: training uses k's first vintage too
    m = P("2013-09")  # inputs m-1, m-12, m-13 = 2013-08, 2012-09, 2012-08
    assert frame_rev.at[m, "e_V1"] == pytest.approx(frame.at[m, "e_V1"])


def test_rerun_from_truncated_table_is_identical(table, frame):
    for m in (P("2014-03"), P("2016-11")):
        origin = engine.origin_for(m)
        truncated = table[table["known_from"] <= origin]
        f_trunc, f_full = engine.forecast(origin, truncated), engine.forecast(origin, table)
        assert f_trunc.logs == f_full.logs and f_trunc.lam == f_full.lam
        y = 100 * np.log(engine.first_vintages(table).at[m, "value"])
        for v in engine.VARIANTS:
            assert frame.at[m, f"e_{v}"] == pytest.approx(f_trunc.logs[v] - y, abs=1e-12)


def test_v1_learns_a_real_signal(frame):
    res = backtest.evaluate(frame)
    full = res.summary[res.summary["period"] == "full"].set_index("variant")
    assert full.at["V1", "MAE"] < full.at["B1", "MAE"]


def test_ridge_shrinks_and_cv_prefers_large_lambda_on_noise():
    rng = np.random.default_rng(0)
    X, y = rng.normal(size=(80, 1)), rng.normal(size=80)
    small, large = engine.ridge_fit(X, y, 0.1), engine.ridge_fit(X, y, 1e4)
    assert abs(large[3][0]) < abs(small[3][0])
    assert engine.ridge_predict(large, X[:1])[0] == pytest.approx(y.mean(), abs=0.01)
    Xc = np.ones((80, 1))  # constant feature: every lambda gives the same CV loss, tie goes to the largest
    assert engine.choose_lambda(Xc, y) == engine.LAMBDAS[-1]


def test_origin_must_be_day_5(table):
    with pytest.raises(ValueError):
        engine.forecast(pd.Timestamp("2014-07-08"), table)


def _frame(e_b0, e_b1, e_v1, start="2012-01"):
    idx = pd.period_range(start, periods=len(e_b0), freq="M")
    return pd.DataFrame({"e_B0": e_b0, "e_B1": e_b1, "e_V1": e_v1, "n_train": 100}, index=idx)


def test_promotion_rule_mechanics():
    rng = np.random.default_rng(3)
    n = 180  # 2012-01 .. 2026-12
    b = rng.normal(0, 3, n)
    good = backtest.evaluate(_frame(b * 1.2, b, b * 0.3))
    assert good.promoted and good.champion == "V1" and good.holm_p < 0.10
    # better on the full period but worse from 2023: not promoted
    v = b * 0.3
    v[132:] = b[132:] * 1.5
    split = backtest.evaluate(_frame(b * 1.2, b, v))
    assert not split.promoted and split.champion == "B1"
    assert any(r.startswith("FAIL") and "2023" in r for r in split.reasons)
    # baseline is the better of B0/B1, and B1 stays champion even if B0 is better
    b0best = backtest.evaluate(_frame(b * 0.9, b, b))
    assert b0best.baseline == "B0" and b0best.champion == "B1"


def test_live_writer(tmp_path, table):
    t = table[table["period"] <= "2016-11"]
    path = live.write("2017-01-05", t, tmp_path)
    assert path.name == "2016-12.json"
    d = json.loads(path.read_text())
    assert d["month"] == "2016-12" and d["origin"] == "2017-01-05" and d["champion"] == live.CHAMPION
    assert d["value"] == d["variants"][live.CHAMPION] and set(d["variants"]) == set(engine.VARIANTS)
    assert d["git_sha"] and d["created_utc"].endswith("Z")
    assert all(pd.Timestamp(i["known_from"]) <= pd.Timestamp("2017-01-05") for i in d["inputs"])
    assert {i["series"] for i in d["inputs"]} == {engine.TARGET, "us_imports_tw_m"}
    with pytest.raises(FileExistsError):
        live.write("2017-01-05", t, tmp_path)
    with pytest.raises(RuntimeError):  # outcome already in the table: not a live forecast
        live.write("2016-12-05", t, tmp_path)
    with pytest.raises(ValueError):
        live.write("2017-02-06", t, tmp_path)
