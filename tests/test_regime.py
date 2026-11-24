"""C4 regime and structural breaks: MS-EM recovers simulated regimes, BOCPD finds a planted break and matches brute
force, the reporting rules, real time (poison test: nothing after the computation date matters) and the holdout guard.
Synthetic fixtures only, no network."""

from __future__ import annotations

import itertools
import math

import numpy as np
import pandas as pd
import pytest

from ai_tracker.factor import guard as factor_guard
from ai_tracker.regime import bocpd, evaluate, guard, ms
from ai_tracker.regime import realtime as rt

TS = pd.Timestamp


# ------------------------------------------------------------------ Markov switching


def test_ms_recovers_simulated_regimes():
    P = [[0.97, 0.03], [0.02, 0.98]]
    y, s = ms.simulate(400, mu=[-1.0, 1.0], sigma=[0.6, 0.4], P=P, seed=1)
    r = ms.fit(y)
    assert r.converged
    assert abs(r.mu[0] + 1) < 0.2 and abs(r.mu[1] - 1) < 0.2
    assert abs(math.sqrt(r.sigma2[0]) - 0.6) < 0.15 and abs(math.sqrt(r.sigma2[1]) - 0.4) < 0.15
    # state 0 = slowdown = the lower mean, which is simulated state 0
    assert ((r.smoothed[:, 0] > 0.5) == (s == 0)).mean() > 0.95
    assert ((r.filtered[:, 0] > 0.5) == (s == 0)).mean() > 0.9
    assert r.P[0, 0] > 0.9 and r.P[1, 1] > 0.9


def test_ms_loglik_non_decreasing_and_labels_by_mean():
    y, s = ms.simulate(250, mu=[2.0, -0.5], sigma=[0.5, 0.5], P=[[0.95, 0.05], [0.05, 0.95]], seed=4)
    r = ms.fit(y)
    assert np.all(np.diff(r.history) > -1e-8)
    assert r.mu[0] < r.mu[1]  # relabelled: simulated state 1 (mean -0.5) is the slowdown
    assert ((r.smoothed[:, 0] > 0.5) == (s == 1)).mean() > 0.95


def test_filtered_probability_is_causal():
    y, _ = ms.simulate(120, mu=[-1, 1], sigma=[0.5, 0.5], P=[[0.95, 0.05], [0.05, 0.95]], seed=2)
    r = ms.fit(y)
    full, *_ = ms.filter_smooth(y, r.mu, r.sigma2, r.P)
    part, *_ = ms.filter_smooth(y[:70], r.mu, r.sigma2, r.P)
    np.testing.assert_allclose(full[:70], part)


def test_ms_start_and_floor_are_deterministic():
    y, _ = ms.simulate(100, mu=[0, 1], sigma=[1, 1], P=[[0.9, 0.1], [0.1, 0.9]], seed=7)
    a, b = ms.fit(y), ms.fit(y.copy())
    assert a.loglik == b.loglik and np.array_equal(a.filtered, b.filtered)
    assert (a.sigma2 >= ms.VAR_FLOOR * y.var(ddof=1) - 1e-12).all()


# ------------------------------------------------------------------ BOCPD


def _brute_force(x, H, prior=bocpd.PRIOR):
    """Exact P(r_T = r) by enumerating every segmentation (changepoint at each t >= 2 with probability H)."""
    T = len(x)

    def seg_loglik(seg):
        m, k, a, b = prior
        ll = 0.0
        for v in seg:
            if np.isfinite(v):
                ll += float(bocpd._log_t(v, m, k, a, b))
                m, k, a, b = (k * m + v) / (k + 1), k + 1, a + 0.5, b + k * (v - m) ** 2 / (2 * (k + 1))
        return ll

    post = np.zeros(T)
    for cps in itertools.product([0, 1], repeat=T - 1):
        starts = [0] + [t + 1 for t, c in enumerate(cps) if c]
        lp = sum(math.log(H) if c else math.log(1 - H) for c in cps)
        bounds = starts + [T]
        lp += sum(seg_loglik(x[bounds[i]:bounds[i + 1]]) for i in range(len(starts)))
        post[T - 1 - starts[-1]] += math.exp(lp)
    return post / post.sum()


def test_bocpd_matches_brute_force():
    x = np.array([0.1, -0.3, 2.5, 2.2, np.nan, 2.9, -0.2])
    for H in (1 / 36, 1 / 3):
        np.testing.assert_allclose(bocpd.run_length_posterior(x, H), _brute_force(x, H), rtol=1e-9, atol=1e-12)


def test_bocpd_detects_planted_break():
    # a 6 SD shift at period 61; each date standardises the path known then (real time)
    rng = np.random.default_rng(0)
    x = np.concatenate([rng.normal(0, 1, 60), rng.normal(6, 1, 8)])
    p = {T: bocpd.p_recent(bocpd.standardize(x[:T]), 1 / 36) for T in range(55, 69)}
    assert max(p[T] for T in range(55, 61)) < 0.2  # no break before it happens
    assert p[61] >= bocpd.THRESHOLD and p[62] >= bocpd.THRESHOLD  # seen at once
    assert p[64] < 0.2  # 4 periods later the run is longer than 2
    dates = [m.end_time.normalize() for m in pd.period_range("2015-01", periods=14, freq="M")]
    f = pd.DataFrame({"date": dates, "series": "s", "freq": "M", "latest_period": [str(d.to_period("M")) for d in dates],
                      "p_recent": [p[T] for T in range(55, 69)]})
    assert list(rt.reported_breaks(f).loc[lambda d: d["break"], "latest_period"]) == ["2015-07"]  # T = 61, once


def test_bocpd_missing_period_counts_as_a_period():
    post = bocpd.run_length_posterior(np.array([0.0, np.nan, np.nan, 0.1]), 1 / 12)
    assert len(post) == 4 and abs(post.sum() - 1) < 1e-12


def test_standardize():
    assert bocpd.standardize([1.0]) is None and bocpd.standardize([2.0, 2.0]) is None
    z = bocpd.standardize([1.0, 2.0, np.nan, 4.0])
    f = z[np.isfinite(z)]
    assert abs(f.mean()) < 1e-12 and abs(f.std(ddof=1) - 1) < 1e-12


# ------------------------------------------------------------------ reporting rules


def _months(n, start="2020-01"):
    return pd.period_range(start, periods=n, freq="M")


def test_state_sequence_two_consecutive_and_hysteresis():
    p = pd.Series([np.nan, 0.5, 0.85, 0.7, 0.9, 0.81, 0.5, 0.15, 0.3, 0.1, 0.19], index=_months(11))
    st = rt.state_sequence(p)
    assert st.iloc[0] is None
    assert list(st.iloc[1:]) == ["expansion", "expansion", "expansion", "expansion", "inbromsning", "inbromsning",
                                 "inbromsning", "inbromsning", "inbromsning", "expansion"]


def test_state_sequence_missing_month_breaks_the_pair():
    p = pd.Series([0.9, np.nan, 0.9, 0.95], index=_months(4))
    assert list(rt.state_sequence(p)) == ["expansion", "expansion", "expansion", "inbromsning"]


def test_reported_states_marks_shifts():
    dates = [m.end_time.normalize() for m in _months(5)]
    f = pd.DataFrame({"date": dates, "block": "capex", "p_slow": [0.1, 0.9, 0.9, 0.1, 0.1]})
    s = rt.reported_states(f)
    assert list(s["state"]) == ["expansion", "expansion", "inbromsning", "inbromsning", "expansion"]
    assert list(s["shift"].fillna("")) == ["", "", "inbromsning", "", "expansion"]


def test_reported_breaks_quiet_period():
    dates = [m.end_time.normalize() for m in _months(8)]
    q = ["2019Q4", "2019Q4", "2019Q4", "2020Q1", "2020Q1", "2020Q1", "2020Q2", "2020Q2"]
    f = pd.DataFrame({"date": dates, "series": "s", "freq": "Q", "latest_period": q,
                      "p_recent": [0.9, 0.95, 0.9, 0.85, 0.1, 0.9, 0.3, 0.3]})
    b = rt.reported_breaks(f)
    assert list(b["break"]) == [True] + [False] * 7  # same and next periods within 3 quarters are quiet
    m = pd.DataFrame({"date": dates[:3], "series": "m", "freq": "M", "latest_period": ["2020-01", "2020-04", "2020-05"],
                      "p_recent": [0.9, 0.9, 0.9]})
    assert list(rt.reported_breaks(m)["break"]) == [True, False, True]  # 3 months later is quiet, 4 is not


# ------------------------------------------------------------------ real time on a synthetic table


@pytest.fixture(scope="module")
def table():
    from test_factor import synthetic_table

    return synthetic_table(end="2017-12")


def test_compute_record_on_synthetic_table(table, tmp_path):
    rec = rt.compute(table, "2016-06-30", cache=True, cache_dir=tmp_path, factor_cache=False)
    for block in rt.BLOCKS:
        r = rec["ms"][block]
        assert r["first_month"] == "2010-01" if block == "capex" else r["first_month"] == "2010-03"
        assert r["n_months"] >= rt.MIN_MONTHS and 0.0 <= r["p_slow"] <= 1.0
        assert r["mu_slow"] <= r["mu_exp"]
    keys = {b["series"] for b in rec["bocpd"]}
    assert {"tsmc_revenue_m", "rev_aws"} <= keys
    assert all(0 <= b["p_recent"] <= 1 for b in rec["bocpd"] if np.isfinite(b["p_recent"]))
    assert len(list(tmp_path.glob("*.pkl"))) == 1
    again = rt.compute(table, "2016-06-30", cache=True, cache_dir=tmp_path, factor_cache=False)
    assert again["ms"] == rec["ms"]


def test_short_history_gives_no_probability(table):
    rec = rt.compute(table, "2013-06-30", cache=False, factor_cache=False)
    r = rec["ms"]["capex"]
    assert np.isnan(r["p_slow"]) and r["n_months"] < rt.MIN_MONTHS and "faktorhistorik" in r["reason"]


def test_poison_rows_after_date_change_nothing(table):
    date = TS("2016-06-30")
    clean = rt.compute(table, date, cache=False, factor_cache=False)
    poison = []
    for key in ["tsmc_revenue_m", "us_imports_tw_m", "rev_aws", "rev_nvda_datacenter"]:
        r = table[table["series"] == key].copy()
        r["value"] = r["value"] * 1000.0
        r["known_from"] = date + pd.Timedelta(days=1)
        poison.append(r)
    later = table[pd.to_datetime(table["known_from"]) > date]  # the genuine future is also in the table
    assert len(later)
    v = rt.compute(pd.concat([table, *poison], ignore_index=True), date, cache=False, factor_cache=False)
    assert v["ms"] == clean["ms"]
    pd.testing.assert_frame_equal(pd.DataFrame(v["bocpd"]), pd.DataFrame(clean["bocpd"]))
    cut = rt.compute(table[pd.to_datetime(table["known_from"]) <= date], date, cache=False, factor_cache=False)
    assert cut["ms"] == clean["ms"]


# ------------------------------------------------------------------ holdout guard


def test_holdout_guard_raises(table, tmp_path):
    assert not guard.HOLDOUT_OPEN
    assert guard.DEV_END == factor_guard.DEV_END == TS("2025-06-30")
    with pytest.raises(guard.HoldoutClosed):
        rt.compute(table, "2025-07-31", cache_dir=tmp_path)
    with pytest.raises(guard.HoldoutClosed):
        rt.run(table, "2025-05-31", "2025-07-31", cache=False)
    states = pd.DataFrame(columns=["date", "block", "p_slow", "state", "shift"])
    breaks = pd.DataFrame(columns=["date", "series", "branch", "p_recent", "break"])
    with pytest.raises(guard.HoldoutClosed):
        evaluate.frequency(states, breaks, "2025-07-31", "2026-10-31")
    with pytest.raises(guard.HoldoutClosed):
        evaluate.reclassification(table, states, "2025-07-31", "2026-10-31")
    with pytest.raises(guard.HoldoutClosed):
        evaluate.association(states, {}, "2025-07-01", "2026-10-31")
    guard.check("2025-06-30")
    assert list(tmp_path.iterdir()) == []


def test_c4_flag_is_separate_from_c3(monkeypatch, table):
    # opening C3 alone does not open C4 (one opening per family, F-E3)
    monkeypatch.setattr(factor_guard, "HOLDOUT_OPEN", True)
    with pytest.raises(guard.HoldoutClosed):
        rt.compute(table, "2025-07-31", cache=False)


@pytest.mark.real_data
def test_real_table_holdout_guard_raises_before_any_computation():
    from conftest import real_table_exists

    from ai_tracker import observations

    if not real_table_exists():
        pytest.skip("no real observation table")
    t = observations.load()
    for d in ("2025-07-31", "2026-10-31", "2026-11-30"):
        with pytest.raises(guard.HoldoutClosed):
            rt.compute(t, d, cache=False)
    with pytest.raises(guard.HoldoutClosed):
        rt.run(t, "2025-01-31", "2026-10-31", cache=False)
