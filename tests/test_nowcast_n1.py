"""N1 nowcast: leakage tests, rolling-origin contract, pooled DM, promotion rule and the live writer.

Synthetic fixtures only, no network and no data/observations.parquet.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from ai_tracker import evaluation, observations
from ai_tracker.nowcast import engine, n1

T = "capex_test"
IMP, CON = n1.INDICATORS


def _rows(series, freq, periods, values, known_from, source="release"):
    return pd.DataFrame({"series": series, "freq": freq, "period": [str(p) for p in periods],
                         "value": np.asarray(values, dtype=float), "known_from": pd.to_datetime(known_from),
                         "source": source, "fetched_at": pd.Timestamp("2026-11-23")})


def make_table(seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    months = pd.period_range("2011-01", "2020-12", freq="M")
    ind = {}
    for key, lag in ((IMP, 41), (CON, 35)):
        lvl = 1000 * np.exp(np.cumsum(0.01 + 0.03 * rng.standard_normal(len(months))))
        ind[key] = pd.Series(lvl, index=months)
    quarters = pd.period_range("2012Q1", "2020Q3", freq="Q-DEC")
    # capex growth loads on the indicators' quarterly growth plus noise
    qmean = {k: np.log(v).groupby(v.index.asfreq("Q-DEC")).mean() for k, v in ind.items()}
    g = 0.02 + 0.5 * qmean[IMP].diff() + 0.3 * qmean[CON].diff() + 0.02 * rng.standard_normal(len(qmean[IMP]))
    capex = 500 * np.exp(g.loc[quarters].cumsum())
    parts = [_rows(k, "M", months, v.to_numpy(), months.end_time.normalize() + pd.Timedelta(days=lag), "backfill")
             for k, (v, lag) in zip(ind, ((ind[IMP], 41), (ind[CON], 35)))]
    first_kf = quarters.end_time.normalize() + pd.Timedelta(days=30)
    parts.append(_rows(T, "Q", quarters, capex.to_numpy(), first_kf))
    # every 4th quarter revised a year later by +3 %: later vintages must not be scored
    rev = quarters[::4]
    parts.append(_rows(T, "Q", rev, capex.loc[rev].to_numpy() * 1.03, rev.end_time.normalize() + pd.Timedelta(days=395)))
    return pd.concat(parts, ignore_index=True)


@pytest.fixture(scope="module")
def table():
    return make_table()


ORIGIN = n1.origin_for(pd.Period("2018Q2", freq="Q-DEC"))  # 2018-07-20


def fc(table, origin=ORIGIN):
    return n1.forecast(engine.InfoSet(table, origin), T)


def same(a: n1.Forecast, b: n1.Forecast):
    assert a.levels.keys() == b.levels.keys()
    for v in a.levels:
        assert a.levels[v] == pytest.approx(b.levels[v], rel=0, abs=0) or (math.isnan(a.levels[v]) and math.isnan(b.levels[v]))
    assert a.lam == b.lam and a.n_train == b.n_train and a.positions == b.positions


# ------------------------------------------------------------------ basics


def test_origin_and_target_quarter():
    assert n1.origin_for(pd.Period("2026Q4", freq="Q-DEC")) == pd.Timestamp("2027-01-20")
    assert n1.target_quarter("2027-01-20") == pd.Period("2026Q4", freq="Q-DEC")


def test_partial_growth_is_mean_log_of_known_months_vs_same_months_previous_quarter():
    z = pd.Series([1.0, 2.0, 4.0, 8.0, 16.0], index=pd.period_range("2020-01", periods=5, freq="M"))
    q = pd.Period("2020Q2", freq="Q-DEC")
    assert n1.known_positions(z, q) == [0, 1]
    expected = (math.log(8) + math.log(16)) / 2 - (math.log(1) + math.log(2)) / 2
    assert n1.partial_growth(z, q, [0, 1]) == pytest.approx(expected)
    assert math.isnan(n1.partial_growth(z, q, [0, 1, 2]))


def test_forecast_has_all_variants(table):
    f = fc(table)
    assert set(f.levels) == set(n1.VARIANTS) and all(np.isfinite(list(f.levels.values())))
    assert f.n_train >= n1.MIN_TRAIN
    # imports known 41 days after month end: April and May 2018 by 2018-07-20, not June
    assert f.positions == {IMP: [0, 1], CON: [0, 1]}


# ------------------------------------------------------------------ leakage


def test_value_known_after_origin_is_never_used(table):
    base = fc(table)
    q = n1.target_quarter(ORIGIN)
    poison = pd.concat([
        table,
        # June 2018 (3rd month of the quarter) published one day after the origin, absurd value
        _rows(IMP, "M", [pd.Period("2018-06", "M")], [1e12], [ORIGIN + pd.Timedelta(days=1)], "fetch"),
        # a revision of a known month and of the target's own history, both dated after the origin
        _rows(CON, "M", [pd.Period("2018-04", "M")], [1e-6], [ORIGIN + pd.Timedelta(days=1)], "revision"),
        _rows(T, "Q", [q - 1], [1e9], [ORIGIN + pd.Timedelta(days=1)], "revision"),
        # the target itself, filed after the origin
        _rows(T, "Q", [q], [1e9], [ORIGIN + pd.Timedelta(days=2)]),
    ], ignore_index=True)
    info = engine.InfoSet(poison, ORIGIN)
    same(base, n1.forecast(info, T))
    assert all(pd.Timestamp(i["known_from"]) <= ORIGIN for i in info.inputs())
    assert "2018-06" not in info.used[IMP]


def test_outcome_is_first_vintage_not_revision(table):
    err = n1.backtest_unit(table, T)
    fv = engine.first_vintage(table, T)
    latest = observations.as_of(T, "2100-01-01", table)
    revised = [q for q in err["quarter"] if not np.isclose(fv[q], latest[q])]
    assert revised  # the fixture has revised quarters inside the backtest
    for q, out in zip(err["quarter"], err["outcome"]):
        assert out == fv[q]
    # changing a revision that is only known after q's origin leaves q's score unchanged
    q = revised[0]
    t2 = table.copy()
    mask = (t2["series"] == T) & (t2["period"] == str(q)) & (t2["known_from"] > n1.origin_for(q) + pd.Timedelta(days=60))
    assert mask.sum() == 1
    t2.loc[mask, "value"] *= 2
    err2 = n1.backtest_unit(t2, T)
    row = lambda e: e[e["quarter"] == q].iloc[0]
    for v in n1.VARIANTS:
        assert row(err2)[v] == row(err)[v] or (math.isnan(row(err2)[v]) and math.isnan(row(err)[v]))


def test_no_quarter_scored_when_outcome_known_at_origin(table):
    # a filing on the origin day makes the quarter a known number: skipped, never scored
    q = pd.Period("2019Q1", freq="Q-DEC")
    t2 = table.copy()
    mask = (t2["series"] == T) & (t2["period"] == str(q)) & (t2["known_from"] == q.end_time.normalize() + pd.Timedelta(days=30))
    t2.loc[mask, "known_from"] = n1.origin_for(q)
    err = n1.backtest_unit(t2, T)
    assert q not in set(err["quarter"])
    assert any(str(q) in k for k in err.attrs["known_at_origin"])
    with pytest.raises(n1.NotAvailable):
        n1.forecast(engine.InfoSet(t2, n1.origin_for(q)), T)


def test_standardisation_and_lambda_from_training_rows_only(monkeypatch):
    rng = np.random.default_rng(1)
    X, r = rng.standard_normal((20, 2)) * [1, 50] + [3, -7], rng.standard_normal(20)
    m = n1.ridge_fit(X[:15], r[:15], 1.0)
    assert np.allclose(m.mu, X[:15].mean(axis=0)) and np.allclose(m.sd, X[:15].std(axis=0))
    assert m.a == pytest.approx(r[:15].mean())
    calls = []
    real = n1.ridge_fit

    def spy(Xs, rs, lam):
        calls.append(len(rs))
        return real(Xs, rs, lam)

    monkeypatch.setattr(n1, "ridge_fit", spy)
    lam, losses = n1.choose_lambda(X[:15], r[:15])
    # every CV fit uses only the rows before the predicted row, starting at CV_MIN
    assert sorted(set(calls)) == list(range(n1.CV_MIN, 15))
    monkeypatch.undo()
    # rows after the training window cannot change the choice
    assert n1.choose_lambda(X[:15], r[:15])[0] == lam
    X2 = X.copy()
    X2[15:] *= 1000
    assert n1.choose_lambda(X2[:15], r[:15])[0] == lam


def test_target_quarter_indicator_moves_v2_but_not_lambda(table):
    base = fc(table)
    t2 = table.copy()
    mask = (t2["series"] == CON) & (t2["period"].isin(["2018-04", "2018-05"]))
    t2.loc[mask, "value"] *= 1.5  # known at the origin, but only the target quarter's own x
    f2 = fc(t2)
    assert f2.lam == base.lam and f2.n_train == base.n_train
    assert f2.levels["V2"] != base.levels["V2"] and f2.levels["B1"] == base.levels["B1"]


def test_truncated_table_gives_identical_forecast(table):
    base_info = engine.InfoSet(table, ORIGIN)
    base = n1.forecast(base_info, T)
    cut = table[table["known_from"] <= ORIGIN].reset_index(drop=True)
    cut_info = engine.InfoSet(cut, ORIGIN)
    same(base, n1.forecast(cut_info, T))
    assert base_info.inputs() == cut_info.inputs()


def test_missing_indicator_month_means_no_v_forecast(table):
    t2 = table[~((table["series"] == CON) & table["period"].isin(["2018-04", "2018-05", "2018-06"]))]
    f = fc(t2)
    assert math.isnan(f.levels["V1"]) and math.isnan(f.levels["V2"]) and "no month" in f.reasons["V1"]
    assert np.isfinite(f.levels["B1"])


def test_backtest_starts_at_min_training_and_uses_common_sample(table):
    err = n1.backtest_unit(table, T)
    inp = err[err["in_period"]]
    assert inp["n_train"].min() >= n1.MIN_TRAIN
    assert err.loc[~err["in_period"], "V1"].isna().all()
    res = n1.evaluate(err, pooled=False)
    assert res["full"]["metrics"]["B1"]["n"] == res["full"]["metrics"]["V1"]["n"] == res["full"]["n"]


# ------------------------------------------------------------------ statistics and rule


def test_pooled_dm_balanced_equals_dm_on_quarterly_average():
    rng = np.random.default_rng(2)
    q = np.repeat(np.arange(30), 4)
    frame = pd.DataFrame({"quarter": q, "a": rng.standard_normal(120) * 2, "b": rng.standard_normal(120)})
    r = engine.pooled_dm(frame, "a", "b")
    dbar = (frame["a"].abs() - frame["b"].abs()).groupby(q).mean().to_numpy()
    lag = evaluation.newey_west_lag(30)
    hln = math.sqrt((30 - 1) / 30)
    se = math.sqrt(evaluation.long_run_variance(dbar, lag) / 30) / hln
    assert r.n == 30 and r.lag == lag
    assert r.se == pytest.approx(se) and r.mean_diff == pytest.approx(dbar.mean())
    assert r.p == pytest.approx(evaluation.t_two_sided_p(dbar.mean() / se, 29))


def _res(mae, holm_p):
    out = {}
    for per in ("full", "2023Q1-"):
        out[per] = {"best_baseline": "B1",
                    "metrics": {"B0": {"MAE": 10.0}, "B1": {"MAE": 5.0}, "V1": {"MAE": mae[per][0]}, "V2": {"MAE": mae[per][1]}},
                    "dm": {"V1": {"holm_p": holm_p[per][0]}, "V2": {"holm_p": holm_p[per][1]}}}
    return out


def test_promotion_rule():
    # V1 better and significant in both periods -> promoted; V2 significant only in full period -> not
    res = _res({"full": (4.0, 3.0), "2023Q1-": (4.0, 3.0)}, {"full": (0.05, 0.05), "2023Q1-": (0.05, 0.2)})
    p = n1.promotion(res)
    assert p["champion"] == "V1" and not p["checks"]["V2"]["promoted"] and p["checks"]["V2"]["promoted_loose_reading"]
    # lower MAE but not significant -> B1 stays
    assert n1.promotion(_res({"full": (4.0, 4.0), "2023Q1-": (4.0, 4.0)},
                             {"full": (0.2, 0.2), "2023Q1-": (0.2, 0.2)}))["champion"] == "B1"
    # significant but worse in the subperiod -> B1
    assert n1.promotion(_res({"full": (4.0, 4.0), "2023Q1-": (6.0, 6.0)},
                             {"full": (0.01, 0.01), "2023Q1-": (0.01, 0.01)}))["champion"] == "B1"


# ------------------------------------------------------------------ live writer


def test_live_writer_writes_once(table, tmp_path, monkeypatch):
    monkeypatch.setattr(n1, "TARGET", T)
    path = n1.write_live(table, ORIGIN, tmp_path, today="2026-11-23")
    assert path.name == "2018Q2.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    assert d["quarter"] == "2018Q2" and d["origin"] == "2018-07-20" and d["registered_origin"]
    assert d["champion"] == n1.CHAMPION and d["value"] == d["variants"][n1.CHAMPION]
    assert set(d["variants"]) == set(n1.VARIANTS) | {"DF"} and d["git_sha"] and d["written_utc"].endswith("Z")
    assert d["inputs"] and all(pd.Timestamp(i["known_from"]) <= ORIGIN for i in d["inputs"])
    assert {i["series"] for i in d["inputs"]} == {T, IMP, CON}
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        n1.write_live(table, ORIGIN, tmp_path, today="2026-11-23")
    assert path.read_bytes() == before


def test_live_writer_refuses_future_origin_and_known_outcome(table, tmp_path, monkeypatch):
    monkeypatch.setattr(n1, "TARGET", T)
    with pytest.raises(ValueError):
        n1.write_live(table, "2027-01-20", tmp_path, today="2026-11-23")
    with pytest.raises(n1.NotAvailable):  # 2018Q2 is filed 30 days after quarter end
        n1.write_live(table, "2018-08-15", tmp_path, today="2026-11-23")
    assert not list(tmp_path.iterdir())


def test_live_champion_falls_back_to_b1_when_unavailable(table, monkeypatch):
    monkeypatch.setattr(n1, "TARGET", T)
    monkeypatch.setattr(n1, "CHAMPION", "V2")
    t2 = table[~((table["series"] == CON) & table["period"].isin(["2018-04", "2018-05", "2018-06"]))]
    d = n1.live_payload(t2, ORIGIN)
    assert d["champion"] == "B1" and "fell back" in d["note"]
