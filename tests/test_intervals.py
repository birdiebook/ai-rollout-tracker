"""Probabilistic forecasts (track C1): as-of error pools, coverage, CRPS, PIT and the leakage guard.

Synthetic data only. The method is not run on the real backtests before grind G-C is registered.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from ai_tracker.nowcast import intervals as I

P = lambda s: pd.Period(s, freq="M")


def _frame(errors: dict, start="2000-01", lag_days=9):
    """Monthly frame: origin = day 5 of m+1, outcome known day 10 of m+1 (after the origin, as in N2)."""
    n = len(next(iter(errors.values())))
    months = pd.period_range(start, periods=n, freq="M")
    origin = pd.Series([(m + 1).start_time + pd.Timedelta(days=4) for m in months], index=months)
    known = pd.Series([(m + 1).start_time + pd.Timedelta(days=lag_days) for m in months], index=months)
    return pd.DataFrame(errors, index=months), origin, known


def test_flag_is_off_until_gc_is_registered():
    assert I.ENABLED is False


# ------------------------------------------------------------------ pools


def test_pool_contains_exactly_the_errors_known_at_the_origin():
    e, origin, known = _frame({"A": np.arange(30, dtype=float)})
    m = P("2001-06")  # index 17; origin 2001-07-05; outcome of 2001-05 known 2001-06-10, of 2001-06 on 2001-07-10
    pool = I.pool(e["A"], known, origin[m], exclude=m)
    assert list(pool) == list(range(17))  # every month before m, m itself not
    # one day before the 2001-05 outcome is known it is not in the pool
    assert list(I.pool(e["A"], known, pd.Timestamp("2001-06-09"))) == list(range(16))
    assert list(I.pool(e["A"], known, pd.Timestamp("2001-06-10"))) == list(range(17))


def test_leakage_outcome_known_after_origin_never_enters_the_pool():
    """An earlier period whose outcome is published late (after the origin) is out of the pool at that origin,
    even though its period is earlier, and enters on its own known_from day."""
    e, origin, known = _frame({"A": np.ones(60)})
    late = P("2002-01")
    e.loc[late, "A"] = 1e6  # a poison value: if it leaks, the distribution explodes
    known[late] = pd.Timestamp("2003-06-01")
    s = I.score_frame(e, origin, known)
    before = s[(s["origin"] < pd.Timestamp("2003-06-01")) & (s["period"] > late)]
    assert len(before) > 10 and (before["eq_0.975"] < 10).all()
    for _, r in before.iterrows():
        assert 1e6 not in I.pool(e["A"], known, r["origin"], exclude=r["period"])
    after = s[s["origin"] >= pd.Timestamp("2003-06-01")]
    assert len(after) and all(1e6 in I.pool(e["A"], known, o) for o in after["origin"])
    # pool size never counts an error whose outcome is unknown at the origin
    for _, r in s.iterrows():
        assert r["n_pool"] == int(((known <= r["origin"]) & (e.index != r["period"])).sum())


def test_forecast_of_a_known_outcome_is_never_scored():
    e, origin, known = _frame({"A": np.ones(20)})
    known.iloc[15] = origin.iloc[15]  # outcome known at the origin
    s = I.score_frame(e, origin, known)
    assert e.index[15] not in set(s["period"])


def test_method_switches_at_the_registered_sizes():
    rng = np.random.default_rng(0)
    assert I.ErrorDistribution.from_pool(rng.normal(size=I.MIN_ERRORS - 1)) is None
    assert I.ErrorDistribution.from_pool(rng.normal(size=I.MIN_ERRORS)).method == "student_t"
    assert I.ErrorDistribution.from_pool(rng.normal(size=I.MIN_EMPIRICAL - 1)).method == "student_t"
    d = I.ErrorDistribution.from_pool(rng.normal(size=I.MIN_EMPIRICAL))
    assert d.method == "empirical"
    # with 40 errors the 2.5 % quantile is inside the sample, not clipped to its minimum
    assert d.quantile(0.025) > min(d.pool)
    assert I.ErrorDistribution.from_pool([np.nan] * 50) is None


def test_student_t_fallback_parameters():
    x = np.array([1.0, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    d = I.ErrorDistribution.from_pool(x)
    assert d.loc == pytest.approx(5.5) and d.df == 9
    assert d.scale == pytest.approx(np.std(x, ddof=1) * math.sqrt(1 + 1 / 10))
    lo, hi = d.interval(0.95)
    assert (lo + hi) / 2 == pytest.approx(5.5, abs=1e-8)
    assert hi - 5.5 == pytest.approx(d.scale * 2.2621571628, rel=1e-6)  # t(9) 97.5 % quantile


# ------------------------------------------------------------------ t helpers


@pytest.mark.parametrize("df", [3, 7, 30])
def test_t_quantile_inverts_cdf(df):
    for p in I.QUANTILES:
        assert I.t_cdf(I.t_ppf(p, df), df) == pytest.approx(p, abs=1e-9)
    assert I.t_ppf(0.975, 1e6) == pytest.approx(1.959964, abs=1e-4)


def test_t_pdf_integrates_to_cdf():
    z = np.linspace(-40, 1.3, 200001)
    f = np.array([I.t_pdf(v, 5) for v in z])
    assert np.trapezoid(f, z) == pytest.approx(I.t_cdf(1.3, 5), abs=1e-5)


# ------------------------------------------------------------------ CRPS


def _crps_numeric(cdf, y, lo, hi, n=100001):
    """Integral of F(x)^2 below y plus (1 - F(x))^2 above y (trapezoid, split at the step)."""
    f = cdf if getattr(cdf, "vectorized", False) else (lambda x: np.array([cdf(v) for v in x]))
    left, right = np.linspace(lo, y, n), np.linspace(y, hi, n)
    return float(np.trapezoid(f(left) ** 2, left) + np.trapezoid((1 - f(right)) ** 2, right))


@pytest.mark.parametrize("y", [-2.5, 0.0, 0.7, 3.1])
def test_crps_normal_closed_form_matches_integral(y):
    assert I.crps_normal(y, 0.3, 1.7) == pytest.approx(
        _crps_numeric(lambda v: I.norm_cdf((v - 0.3) / 1.7), y, -20, 20), abs=1e-6)


@pytest.mark.parametrize("y,df", [(0.0, 3), (1.5, 5), (-4.0, 12)])
def test_crps_t_closed_form_matches_integral(y, df):
    num = _crps_numeric(lambda v: I.t_cdf((v - 1.0) / 2.0, df), y, -2000, 2000, 60001)
    assert I.crps_t(y, df, 1.0, 2.0) == pytest.approx(num, abs=2e-3)


def test_crps_t_tends_to_normal():
    assert I.crps_t(0.8, 1e5, 0.2, 1.5) == pytest.approx(I.crps_normal(0.8, 0.2, 1.5), rel=1e-4)


def test_crps_sample_is_exact_for_the_empirical_distribution():
    rng = np.random.default_rng(2)
    x = rng.normal(size=25)
    y = 0.4
    brute = np.mean(np.abs(x - y)) - np.mean(np.abs(x[:, None] - x[None, :])) / 2
    assert I.crps_sample(x, y) == pytest.approx(brute, abs=1e-12)
    # and equals the integral of (ECDF - step)^2
    xs = np.sort(x)

    def ecdf(v):
        return np.searchsorted(xs, v, side="right") / len(xs)

    ecdf.vectorized = True
    assert I.crps_sample(x, y) == pytest.approx(_crps_numeric(ecdf, y, -8, 8, 400001), abs=1e-4)


def test_crps_sample_of_a_large_normal_sample_matches_closed_form():
    rng = np.random.default_rng(3)
    x = rng.normal(1.0, 2.0, size=200_000)
    for y in (-1.0, 1.0, 4.0):
        assert I.crps_sample(x, y) == pytest.approx(I.crps_normal(y, 1.0, 2.0), abs=0.01)


def test_crps_in_error_space_equals_outcome_space():
    """CRPS(F_y, y) with y = f - e equals CRPS(F_e, e): the reflection does not change the score."""
    rng = np.random.default_rng(4)
    pool = rng.normal(0.5, 3, size=60)
    d = I.ErrorDistribution.from_pool(pool)
    f, e = 1000.0, 2.2
    y = f - e
    assert d.crps(e) == pytest.approx(I.crps_sample(f - pool, y), abs=1e-12)


# ------------------------------------------------------------------ outcome space and signs


def test_outcome_quantiles_have_the_right_sign():
    """Errors are forecast - outcome. A model that always over-forecasts by 5 has outcomes below the forecast."""
    rng = np.random.default_rng(5)
    d = I.ErrorDistribution.from_pool(5 + rng.normal(0, 0.1, size=200))
    q = d.outcome_quantiles(100.0)
    assert q[0.5] == pytest.approx(95.0, abs=0.1)
    assert list(q.values()) == sorted(q.values())  # monotone in p
    assert d.pit(5.0) == pytest.approx(0.5, abs=0.06)
    assert d.pit(10.0) < 0.01  # error 10: outcome far below the forecast -> low PIT
    assert d.pit(0.0) > 0.99


def test_coverage_identity_error_and_outcome_space():
    rng = np.random.default_rng(6)
    d = I.ErrorDistribution.from_pool(rng.normal(size=80))
    f = 50.0
    q = d.outcome_quantiles(f, (0.1, 0.9))
    for e in rng.normal(size=200):
        assert d.covers(e, 0.8) == (q[0.1] <= f - e <= q[0.9])


# ------------------------------------------------------------------ calibration on iid normal errors


@pytest.fixture(scope="module")
def iid_scored():
    """Two models with iid N(0, 2^2) errors and one too-confident model scored with half-width pools, 600 months."""
    rng = np.random.default_rng(7)
    n = 600
    a = rng.normal(0, 2, size=n)
    b = rng.normal(1, 2, size=n)  # biased: the pool learns the bias
    e, origin, known = _frame({"A": a, "B": b})
    s = I.score_frame(e, origin, known)
    return e, origin, known, s


def test_coverage_is_nominal_on_iid_normal_errors(iid_scored):
    *_, s = iid_scored
    cal = I.calibration(s).set_index("model")
    for v in ("A", "B"):
        for L in I.LEVELS:
            k = I.level_key(L)
            assert cal.at[v, f"coverage_{k}"] == pytest.approx(L, abs=0.05)
        assert cal.at[v, "calibrated"]
        assert cal.at[v, "n_student_t"] == I.MIN_EMPIRICAL - I.MIN_ERRORS
        assert cal.at[v, "n_empirical"] == 600 - I.MIN_EMPIRICAL


def test_student_t_fallback_is_nominal_on_small_iid_normal_pools():
    """Many replications of a pool of 10 normal errors and one new draw: coverage of the t interval is exact."""
    rng = np.random.default_rng(8)
    hits = {L: [] for L in I.LEVELS}
    for _ in range(4000):
        x = rng.normal(3, 5, size=11)
        d = I.ErrorDistribution.from_pool(x[:10])
        for L in I.LEVELS:
            hits[L].append(d.covers(x[10], L))
    for L in I.LEVELS:
        assert np.mean(hits[L]) == pytest.approx(L, abs=0.02)


def test_empirical_type6_interval_is_nominal_on_small_exchangeable_pools():
    rng = np.random.default_rng(9)
    hits = []
    for _ in range(4000):
        x = rng.standard_t(4, size=I.MIN_EMPIRICAL + 1)
        d = I.ErrorDistribution.from_pool(x[:-1])
        hits.append(d.covers(x[-1], 0.95))
    assert np.mean(hits) == pytest.approx(0.95, abs=0.012)


def test_pit_is_uniform_for_a_calibrated_model(iid_scored):
    *_, s = iid_scored
    g = s[(s["model"] == "A") & s["method"].notna()]
    pit = g["pit"].to_numpy()
    assert pit.mean() == pytest.approx(0.5, abs=0.03)
    assert pit.var() == pytest.approx(1 / 12, abs=0.01)
    hist = np.array(I.pit_histogram(pit))
    expected = len(pit) / I.PIT_BINS
    chi2 = float(((hist - expected) ** 2 / expected).sum())
    assert chi2 < 21.67  # chi2(9) 99 % quantile


def test_an_overconfident_model_fails_calibration():
    """Errors N(0, 4^2) scored with a pool from N(0, 1): intervals far too narrow."""
    rng = np.random.default_rng(10)
    n = 300
    e, origin, known = _frame({"A": rng.normal(0, 4, size=n)})
    narrow = pd.DataFrame({"A": rng.normal(0, 1, size=n)}, index=e.index)
    rows = []
    for m in e.index[60:]:
        d = I.distribution_at(narrow["A"], known, origin[m], exclude=m)
        x = e.at[m, "A"]
        rows.append({"period": m, "model": "A", "method": d.method, "crps": d.crps(x), "pit": d.pit(x),
                     "quantile_score": d.quantile_score(x),
                     **{f"hit_{I.level_key(L)}": float(d.covers(x, L)) for L in I.LEVELS}})
    cal = I.calibration(pd.DataFrame(rows)).iloc[0]
    assert not cal["calibrated"]
    assert cal["coverage_95"] < 0.6 and cal["pit_var"] > 1 / 12 + 0.03


def test_coverage_test_floor_when_every_forecast_hits():
    t = I.coverage_test(np.ones(20), 0.95)
    assert t.coverage == 1.0 and math.isfinite(t.p) and t.p > 0.1  # 20 hits of 20 is no evidence at 95 %
    assert I.coverage_test(np.r_[np.ones(50), np.zeros(50)], 0.95).p < 0.001


def test_crps_ranks_the_unbiased_model_first(iid_scored):
    *_, s = iid_scored
    cal = I.calibration(s).set_index("model")
    # B's pool learns its bias, so it is calibrated too, and its CRPS is about the same as A's
    assert cal.at["B", "crps"] == pytest.approx(cal.at["A", "crps"], rel=0.15)
    # expected CRPS of the true N(0, s^2) at its own draws is s / sqrt(pi)
    assert cal.at["A", "crps"] == pytest.approx(2 / math.sqrt(math.pi), rel=0.1)
    r = I.crps_dm(s, "A", "B")
    assert r.n == 600 - I.MIN_ERRORS


def test_quantile_score_approximates_half_crps():
    """2 x mean pinball over many levels -> CRPS; with the seven registered levels it is a rough proxy."""
    rng = np.random.default_rng(11)
    d = I.ErrorDistribution.from_pool(rng.normal(size=5000))
    ps = np.linspace(0.005, 0.995, 199)
    for y in (-1.0, 0.3, 2.0):
        assert 2 * d.quantile_score(y, ps) == pytest.approx(d.crps(y), rel=0.03)


# ------------------------------------------------------------------ live block and stored distributions


def test_live_block_uses_only_known_errors_and_round_trips():
    rng = np.random.default_rng(12)
    e, origin, known = _frame({"A": rng.normal(0, 2, size=100), "B": rng.normal(0, 2, size=100)})
    o = origin.iloc[50]
    block = I.live_block({"A": 100 * math.log(1000.0), "B": float("nan"), "C": 1.0}, e, known, o)
    a = block["models"]["A"]
    assert a["n_pool"] == 50 and a["method"] == "empirical"
    assert block["models"]["B"] == {"method": None, "n_pool": 50, "n_live": 0} and "C" not in block["models"]
    q = [a["quantiles"][k] for k in block["quantile_levels"]]
    assert q == sorted(q) and q[3] == pytest.approx(1000 * math.exp(-np.median(e["A"].iloc[:50]) / 100), rel=1e-3)
    lo, hi = a["intervals"]["80"]
    assert lo == pytest.approx(a["quantiles"]["0.1"]) and hi == pytest.approx(a["quantiles"]["0.9"])
    d = I.ErrorDistribution.from_json(a)
    ref = I.ErrorDistribution.from_pool(e["A"].iloc[:50])
    for p in I.QUANTILES:
        assert d.quantile(p) == pytest.approx(ref.quantile(p), abs=1e-4)
    sc = I.score_live(block, "A", 1.0)
    assert set(sc) == {"crps", "pit", "hit_50", "hit_80", "hit_95"}
    assert I.score_live(block, "B", 1.0) == {} and I.score_live({}, "A", 1.0) == {}


def test_stored_student_t_parameters_are_used_not_recomputed():
    d = I.ErrorDistribution.from_pool(np.arange(10.0))
    stored = d.to_json() | {"scale": d.scale * 2}
    assert I.ErrorDistribution.from_json(stored).scale == pytest.approx(d.scale * 2, rel=1e-12)


# ------------------------------------------------------------------ registered additions (G-C, F-C4, F-C5)


def test_binomial_band_is_the_5th_and_95th_percentile():
    from math import comb
    n, L = 30, 0.8
    cdf = np.cumsum([comb(n, k) * L**k * (1 - L) ** (n - k) for k in range(n + 1)])
    lo, hi = I.binomial_band(n, L)
    assert lo * n == int(np.argmax(cdf >= 0.05)) and hi * n == int(np.argmax(cdf >= 0.95))
    assert lo < L < hi
    lo500, hi500 = I.binomial_band(500, 0.95)
    assert hi500 - lo500 == pytest.approx(2 * 1.645 * math.sqrt(0.95 * 0.05 / 500), abs=0.01)


def test_calibration_reports_the_binomial_band(iid_scored):
    *_, s = iid_scored
    cal = I.calibration(s).set_index("model")
    for L in I.LEVELS:
        k = I.level_key(L)
        lo, hi = cal.at["A", f"band_{k}"]
        assert lo < L < hi and [lo, hi] == list(I.binomial_band(int(cal.at["A", "n"]), L))


def _live_file(root, period, origin, variants):
    import json
    root.mkdir(parents=True, exist_ok=True)
    p = root / f"{period}.json"
    p.write_text(json.dumps({"month": period, "origin": origin, "champion": "A", "value": variants["A"],
                             "variants": variants}), encoding="utf-8")
    return p


def test_live_errors_enter_the_pool_only_from_their_outcomes_known_from(tmp_path):
    months = pd.period_range("2020-01", periods=4, freq="M")
    outcomes = pd.DataFrame({"value": [100.0, 100.0, 100.0, 100.0],
                             "known_from": pd.to_datetime(["2020-02-10", "2020-03-10", "2020-04-10", "2020-05-10"])},
                            index=months)
    files = [_live_file(tmp_path, "2020-01", "2020-02-05", {"A": 110.0, "B": None}),
             _live_file(tmp_path, "2020-02", "2020-03-05", {"A": 90.0, "B": 95.0}),
             _live_file(tmp_path, "2020-03", "2020-04-05", {"A": 105.0, "B": 95.0}),
             _live_file(tmp_path, "2020-04", "2020-05-11", {"A": 1.0, "B": 1.0})]  # outcome known at its origin
    e, kf = I.live_errors(files, outcomes, ["A", "B"], "2020-04-09")
    # 2020-03's outcome comes 2020-04-10, after the as-of day; 2020-04 is never a forecast
    assert list(e.index.astype(str)) == ["2020-01", "2020-02"]
    assert e.at[months[0], "A"] == pytest.approx(100 * math.log(1.1)) and np.isnan(e.at[months[0], "B"])
    assert e.at[months[1], "B"] == pytest.approx(100 * math.log(0.95))
    e2, _ = I.live_errors(files, outcomes, ["A", "B"], "2020-04-10")
    assert list(e2.index.astype(str)) == ["2020-01", "2020-02", "2020-03"]


def test_live_error_replaces_the_backtest_reconstruction_of_its_period():
    months = pd.period_range("2019-01", periods=24, freq="M")
    bt = pd.DataFrame({"A": np.arange(24.0)}, index=months)
    kf = pd.Series([(m + 1).start_time + pd.Timedelta(days=9) for m in months], index=months)
    live = pd.DataFrame({"A": [-50.0]}, index=pd.PeriodIndex([months[5]]))
    lkf = pd.Series([kf.iloc[5]], index=live.index)
    e, k = I.merge_live(bt, kf, live, lkf)
    assert len(e) == 24 and e.at[months[5], "A"] == -50.0 and k.equals(kf)
    block = I.live_block({"A": 100.0}, e, k, kf.iloc[-1], live_index=live.index)
    assert block["models"]["A"]["n_pool"] == 24 and block["models"]["A"]["n_live"] == 1
    assert -50.0 in block["models"]["A"]["pool"] and 5.0 not in block["models"]["A"]["pool"]
