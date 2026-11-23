"""B3 (step 2, C2): guidance with a systematic deviation, for N1 and N2 (shared logic in nowcast/b3.py).

Synthetic fixtures only, no network. Checks: deviations enter only from outcomes known at the origin, positions,
the shrinkage arithmetic of F-B3, n_c < 4 -> m = 0, B3 = B2 with midpoint x exp(m), the step-2 Holm family {B3, DF}
with DF at p = 1 and the F-B10 comparator, and reruns from a truncated table.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from ai_tracker import observations
from ai_tracker.nowcast import b3, engine, n1, n2

M = lambda s: pd.Period(s, freq="M")  # noqa: E731
Q = lambda s: pd.Period(s, freq="Q-DEC")  # noqa: E731
DAY = pd.Timedelta(days=1)


def _rows(series, freq, periods, values, known_from, source="release"):
    n = len(periods)
    kf = known_from if isinstance(known_from, list) else [known_from] * n
    return pd.DataFrame({"series": series, "freq": freq, "period": [str(p) for p in periods],
                         "value": np.asarray(values, dtype=float), "known_from": pd.to_datetime(kf),
                         "source": source, "fetched_at": pd.Timestamp("2026-11-23")})


def _dev(company, period, k, d, kf, origin="2000-01-01"):
    return {"company": company, "group": b3.GROUPS[company], "period": period, "position": k,
            "guidance_origin": pd.Timestamp(origin), "guidance": 100.0, "outcome": 100.0 * math.exp(d),
            "outcome_known_from": pd.Timestamp(kf), "d": d}


# ================================================================== b3.py, pure


def test_shrinkage_arithmetic_unweighted_group_mean_company_included():
    meta = [0.10, 0.20, 0.05, 0.15, 0.25]  # n = 5
    googl = [-0.10, 0.30]  # n = 2: in the group mean, but its own m = 0
    rows = [_dev("meta", str(2010 + i), 1, d, f"{2011 + i}-02-01") for i, d in enumerate(meta)]
    rows += [_dev("googl", str(2015 + i), 1, d, f"{2016 + i}-02-01") for i, d in enumerate(googl)]
    rows += [_dev("tsmc", "2015Q1", 1, 5.0, "2015-04-10")]  # another group: never pooled with capex
    pool = pd.DataFrame(rows, columns=b3.COLUMNS)
    s = b3.shift(pool, "meta", 1, "2020-01-01")
    d_meta, d_googl = np.mean(meta), np.mean(googl)
    group = (d_meta + d_googl) / 2  # unweighted mean of company means, Meta included
    w = 5 / (5 + 4)
    assert s.n == 5 and s.group_n == 2 and s.w == pytest.approx(w)
    assert s.group_mean == pytest.approx(group) and s.d_mean == pytest.approx(d_meta)
    assert s.m == pytest.approx(w * d_meta + (1 - w) * group, abs=1e-15)
    g = b3.shift(pool, "googl", 1, "2020-01-01")
    assert g.n == 2 and g.m == 0.0 and g.w == 0.0
    # a company alone in its group: the group mean is its own mean, so m = its mean
    t = pd.DataFrame([_dev("tsmc", f"{2010 + i}Q1", 1, d, f"{2010 + i}-05-01") for i, d in enumerate(meta)],
                     columns=b3.COLUMNS)
    assert b3.shift(t, "tsmc", 1, "2020-01-01").m == pytest.approx(np.mean(meta))


@pytest.mark.parametrize("n,nonzero", [(0, False), (1, False), (3, False), (4, True)])
def test_fewer_than_four_own_deviations_gives_m_zero(n, nonzero):
    rows = [_dev("meta", str(2010 + i), 2, 0.1, f"{2011 + i}-02-01") for i in range(n)]
    rows += [_dev("googl", str(2010 + i), 2, 0.3, f"{2011 + i}-02-01") for i in range(6)]
    s = b3.shift(pd.DataFrame(rows, columns=b3.COLUMNS), "meta", 2, "2030-01-01")
    assert s.n == n and (s.m != 0.0) == nonzero
    if nonzero:  # 4/8 * 0.1 + 4/8 * (0.1 + 0.3)/2
        assert s.m == pytest.approx(0.5 * 0.1 + 0.5 * 0.2)


def test_only_outcomes_known_at_origin_enter():
    rows = [_dev("tsmc", f"{2010 + i}Q1", 1, 0.01 * (i + 1), f"{2010 + i}-05-01") for i in range(6)]
    pool = pd.DataFrame(rows, columns=b3.COLUMNS)
    # at 2014-05-01 the 2014 outcome is known (known_from == origin counts), 2015 not
    s = b3.shift(pool, "tsmc", 1, "2014-05-01")
    assert s.n == 5 and s.m == pytest.approx(np.mean([0.01, 0.02, 0.03, 0.04, 0.05]))
    assert b3.shift(pool, "tsmc", 1, "2014-04-30").n == 4
    assert b3.shift(pool, "tsmc", 1, "2013-04-30").m == 0.0  # n = 3
    # a deviation whose guidance origin lies after the origin never enters (implied, checked anyway)
    late = pd.DataFrame(rows + [_dev("tsmc", "2009Q1", 1, 9.0, "2009-05-01", origin="2020-01-01")],
                        columns=b3.COLUMNS)
    assert b3.shift(late, "tsmc", 1, "2014-05-01").m == s.m


def test_positions_are_estimated_separately():
    rows = [_dev("tsmc", f"{2010 + i}Q1", k, 0.1 * k, f"{2010 + i}-05-01") for i in range(5) for k in (1, 2, 3)]
    pool = pd.DataFrame(rows, columns=b3.COLUMNS)
    assert [b3.shift(pool, "tsmc", k, "2020-01-01").m for k in (1, 2, 3)] == pytest.approx([0.1, 0.2, 0.3])


def test_summed_outcomes_and_deviation_rows():
    f = pd.DataFrame({"value": [1.0, 2.0, 3.0], "known_from": pd.to_datetime(["2020-02-10", "2020-03-09",
                                                                             "2020-04-12"])},
                     index=pd.period_range("2020-01", periods=3, freq="M"))
    u = b3.summed_outcomes({"x": f}, {"2020Q1": [("x", M("2020-01")), ("x", M("2020-02")), ("x", M("2020-03"))],
                                      "2020Q2": [("x", M("2020-04"))]})
    assert u == {"2020Q1": (6.0, pd.Timestamp("2020-04-12"))}  # Q2 has a missing component: not known
    d = b3.deviations("tsmc", [(Q("2020Q1"), 2, pd.Timestamp("2020-03-05"), 5.0),
                               (Q("2020Q2"), 1, pd.Timestamp("2020-05-05"), 5.0)], u)
    assert len(d) == 1 and d.iloc[0]["d"] == pytest.approx(math.log(6 / 5)) and d.iloc[0]["position"] == 2


# ================================================================== N2 (TSMC)

BIAS = 0.03  # TSMC beats its guidance midpoint by about 3 % (what B3 targets)


@pytest.fixture(scope="module")
def tsmc():
    rng = np.random.default_rng(5)
    months = pd.period_range("2010-01", "2019-12", freq="M")
    rev = 1e5 * np.exp(np.cumsum(0.01 + 0.05 * rng.standard_normal(len(months))))
    y = pd.Series(rev, index=months)
    kf = [(p + 1).start_time + pd.Timedelta(days=9) for p in months]  # day 10 of the next month
    actual = y.groupby(y.index.asfreq("Q-DEC")).sum()
    quarters = [q for q in actual.index if q < n2.USD_FROM]
    noise = 0.01 * rng.standard_normal(len(quarters))
    mid = {q: actual[q] / math.exp(BIAS + e) for q, e in zip(quarters, noise)}
    qkf = [q.start_time + pd.Timedelta(days=14) for q in quarters]
    usd = [q for q in actual.index if q >= n2.USD_FROM]
    fx = 30.0
    umid = {q: actual[q] / fx / math.exp(BIAS) for q in usd}
    ukf = [q.start_time + pd.Timedelta(days=14) for q in usd]
    return pd.concat([
        _rows(n2.TARGET, "M", months, rev, kf),
        _rows("tsmc_guid_rev_twd_lo", "Q", quarters, [mid[q] * 0.99 for q in quarters], qkf),
        _rows("tsmc_guid_rev_twd_hi", "Q", quarters, [mid[q] * 1.01 for q in quarters], qkf),
        _rows("tsmc_guid_rev_usd_lo", "Q", usd, [umid[q] * 0.99 for q in usd], ukf),
        _rows("tsmc_guid_rev_usd_hi", "Q", usd, [umid[q] * 1.01 for q in usd], ukf),
        _rows("tsmc_guid_fx", "Q", usd, [fx] * len(usd), ukf),
    ], ignore_index=True)


def test_n2_deviations_positions_and_outcome_dates(tsmc):
    pool = n2.b3_deviations(tsmc)
    first = n2.first_vintages(tsmc)
    row = pool[(pool["period"] == "2012Q2")].set_index("position")
    assert list(row.index) == [1, 2, 3]
    # position k uses the guidance B2 used at the origin of the quarter's k-th month
    assert list(row["guidance_origin"]) == [n2.origin_for(M(m)) for m in ("2012-04", "2012-05", "2012-06")]
    g = n2.quarter_guidance(Q("2012Q2"), n2.origin_for(M("2012-05")), {k: v for k, v in tsmc.groupby("series")})[0]
    assert row.at[2, "guidance"] == pytest.approx(g)
    u = sum(first.at[M(m), "value"] for m in ("2012-04", "2012-05", "2012-06"))
    assert row.at[2, "outcome"] == pytest.approx(u) and row.at[2, "d"] == pytest.approx(math.log(u / g))
    assert row.at[3, "outcome_known_from"] == first.at[M("2012-06"), "known_from"]  # the last component's date
    assert (pool["outcome_known_from"] > pool["guidance_origin"]).all()


def test_n2_b3_exact_formula_and_known_outcomes_only(tsmc):
    m = M("2014-05")  # position 2
    fc = n2.forecast(n2.origin_for(m), tsmc)
    inp = fc.inputs
    pool = n2.b3_deviations(tsmc)
    origin = n2.origin_for(m)
    own = pool[(pool["position"] == 2) & (pool["outcome_known_from"] <= origin)]
    # quarters whose three months were all published by 2014-05-05: up to 2014Q1. From 2011Q1: B1 (and so B2,
    # and a guidance G) needs month m-13, which the fixture has only from 2011-02
    assert own["period"].min() == "2011Q1" and own["period"].max() == "2014Q1" and len(own) == 13
    mk = own["d"].mean()  # TSMC alone in its group: m = its own mean
    assert inp.b3_shift["m"] == pytest.approx(mk) and inp.b3_shift["n"] == 13
    assert abs(mk - BIAS) < 0.01
    y = observations.as_of(n2.TARGET, origin, tsmc)
    q_months = [M("2014-04"), M("2014-05"), M("2014-06")]
    b1 = {k: y[k - 12] * y[m - 1] / y[m - 13] for k in q_months[1:]}
    g = inp.b2_guidance
    exp_b3 = (g * math.exp(mk) - y[M("2014-04")]) * b1[m] / sum(b1.values())
    exp_b2 = (g - y[M("2014-04")]) * b1[m] / sum(b1.values())
    assert fc.logs["B3"] == pytest.approx(100 * math.log(exp_b3), abs=1e-9)
    assert fc.logs["B2"] == pytest.approx(100 * math.log(exp_b2), abs=1e-9)


def test_n2_poisoned_future_outcomes_never_move_b3(tsmc):
    m = M("2014-05")
    origin = n2.origin_for(m)
    ref = n2.forecast(origin, tsmc).logs["B3"]
    # absurd values for months published after the origin: they cannot enter any deviation known at the origin
    poison = tsmc.copy()
    late = (poison["series"] == n2.TARGET) & (poison["known_from"] > origin)
    poison.loc[late, "value"] *= 50
    assert n2.forecast(origin, poison).logs["B3"] == ref
    # publishing the 2014Q1 outcome a day after the origin removes it from the pool (n 13 -> 12)
    t = tsmc.copy()
    t.loc[(t["series"] == n2.TARGET) & (t["period"] == "2014-03"), "known_from"] = origin + DAY
    assert n2.forecast(origin, t).inputs.b3_shift["n"] == 12


def test_n2_m_zero_before_four_quarters_and_fallback_equals_b2(tsmc):
    frame = n2.run(tsmc)
    early = frame[frame["e_B2"].notna() & (frame.index < M("2012-02"))]  # deviations from 2011Q1 on
    assert len(early) == 12 and (early["b3_n"] < 4).all() and (early["b3_m"] == 0).all()
    assert (early["e_B3"] == early["e_B2"]).all()
    assert (frame.loc[frame.index >= M("2012-02"), "b3_n"] >= 4).all()
    # without guidance B3 = B2 = B1
    bare = tsmc[tsmc["series"] == n2.TARGET]
    fb = n2.run(bare)
    assert fb["e_B1"].notna().sum() > 100
    pd.testing.assert_series_equal(fb["e_B3"], fb["e_B1"], check_names=False)
    pd.testing.assert_series_equal(fb["e_B2"], fb["e_B1"], check_names=False)


def test_n2_rerun_from_truncated_table_is_identical(tsmc):
    frame = n2.run(tsmc)
    for m in (M("2013-06"), M("2016-04"), M("2018-08")):
        origin = n2.origin_for(m)
        f = n2.forecast(origin, tsmc[tsmc["known_from"] <= origin])
        y = 100 * np.log(n2.first_vintages(tsmc).at[m, "value"])
        assert frame.at[m, "e_B3"] == pytest.approx(f.logs["B3"] - y, abs=1e-12)
        assert frame.at[m, "b3_m"] == f.inputs.b3_shift["m"]
    # B3 removes most of the systematic miss in this fixture
    late = frame[frame.index >= M("2012-01")]
    assert late["e_B3"].abs().mean() < late["e_B2"].abs().mean()


def _n2_frame(e_b2, e_b3, seed=3):
    rng = np.random.default_rng(seed)
    n = len(e_b2)
    b = rng.normal(0, 3, n)
    idx = pd.period_range("2012-01", periods=n, freq="M")
    return pd.DataFrame({"e_B0": b * 1.5, "e_B1": b * 1.2, "e_V1": b * 1.2, "e_B2": e_b2, "e_B3": e_b3,
                         "n_train": 100}, index=idx)


def test_n2_step2_comparator_is_b2_and_holm_counts_df():
    rng = np.random.default_rng(1)
    e2 = rng.normal(2, 2, 180)
    good = n2.evaluate(_n2_frame(e2, e2 * 0.3 + rng.normal(0, 0.2, 180)))
    s = good.step2
    assert s["comparator"] == "B2" and s["candidates"] == ["B0", "B1", "B2"]
    assert s["p"]["DF"] == 1.0 and s["holm"]["B3"] == pytest.approx(min(1.0, 2 * s["p"]["B3"]))
    assert s["passed"] == {"B3": True} and s["champion"] == "B3"
    assert set(good.holm) == {"V1", "B2"}  # the locked family is not recomputed with B3
    # better than B1 but worse than B2: fails against the F-B10 comparator
    bad = n2.evaluate(_n2_frame(e2 * 0.3, e2 * 0.6)).step2
    assert bad["passed"] == {"B3": False} and bad["champion"] == n2.CHAMPION_AT_STEP2 == "B2"
    # no B3 column: unevaluated, p = 1
    frame = _n2_frame(e2, e2).drop(columns="e_B3")
    none = n2.evaluate(frame).step2
    assert none["p"] == {"B3": 1.0, "DF": 1.0} and none["passed"] == {} and none["champion"] == n2.CHAMPION_AT_STEP2


def test_n2_step2_needs_both_periods():
    rng = np.random.default_rng(2)
    e2 = rng.normal(2, 2, 180)
    e3 = e2 * 0.3
    e3[132:] = e2[132:] * 1.5  # worse from 2023-01
    s = n2.evaluate(_n2_frame(e2, e3)).step2
    assert s["passed"] == {"B3": False} and any(c.startswith("FAIL") and "2023" in c for c in s["checks"]["B3"])


# ================================================================== N1 (capex)

YEARS = pd.period_range("2012Q1", "2022Q4", freq="Q-DEC")


@pytest.fixture(scope="module")
def capex():
    """Four companies; Meta guides every year 2013-2022 (Oct of the year before, updated in July), Alphabet only
    2021-2022. Each year's outcome is the midpoint x exp(0.05) (Meta) by construction."""
    rng = np.random.default_rng(13)
    kf = [q.end_time.normalize() + pd.Timedelta(days=30) for q in YEARS]
    parts, total = [], 0
    vals = {}
    for i, c in enumerate(n1.COMPANIES):
        v = (1000 + 300 * i) * np.exp(np.cumsum(0.03 + 0.05 * rng.standard_normal(len(YEARS))))
        vals[c] = pd.Series(v, index=YEARS)
        parts.append(_rows(c, "Q", YEARS, v, kf))
        total = total + v
    parts.append(_rows("capex_hyp4", "Q", YEARS, total, kf))
    lease = pd.Series(50 * np.exp(np.cumsum(0.02 + 0.1 * rng.standard_normal(len(YEARS)))), index=YEARS)
    parts.append(_rows("fin_lease_meta", "Q", YEARS, lease.to_numpy(), kf))
    meta_u = (vals["capex_meta"] + lease).groupby(YEARS.year).sum()
    for y in range(2013, 2023):
        a = pd.Period(str(y), freq="Y-DEC")
        mid1, mid2 = meta_u[y] / math.exp(0.05), meta_u[y] / math.exp(0.04)
        parts += [_rows("guid_capex_meta_cy_lo", "A", [a, a], [mid1 * 0.95, mid2 * 0.97], [f"{y - 1}-10-29",
                                                                                          f"{y}-07-28"]),
                  _rows("guid_capex_meta_cy_hi", "A", [a, a], [mid1 * 1.05, mid2 * 1.03], [f"{y - 1}-10-29",
                                                                                          f"{y}-07-28"])]
    g_u = vals["capex_googl"].groupby(YEARS.year).sum()
    for y in (2021, 2022):
        a = pd.Period(str(y), freq="Y-DEC")
        parts += [_rows("guid_capex_googl_cy_lo", "A", [a], [g_u[y] * 0.9], [f"{y}-02-04"]),
                  _rows("guid_capex_googl_cy_hi", "A", [a], [g_u[y] * 0.92], [f"{y}-02-04"])]
    return pd.concat(parts, ignore_index=True)


def test_n1_deviations_positions_outcomes_and_meta_leases(capex):
    pool = n1.b3_deviations(capex)
    meta = pool[pool["company"] == "meta"]
    assert set(meta["position"]) == {1, 2, 3, 4} and meta["period"].min() == "2013"
    r = meta[(meta["period"] == "2016")].set_index("position")
    assert list(r["guidance_origin"]) == [n1.origin_for(Q(f"2016Q{k}")) for k in (1, 2, 3, 4)]
    # k = 1, 2 (origins 04-20, 07-20) use the October range, k = 3, 4 the July update
    assert r.at[1, "d"] == pytest.approx(0.05) and r.at[2, "d"] == pytest.approx(0.05)
    assert r.at[3, "d"] == pytest.approx(0.04) and r.at[4, "d"] == pytest.approx(0.04)
    year = [Q(f"2016Q{k}") for k in (1, 2, 3, 4)]
    fv = {s: engine.first_vintage(capex, s) for s in ("capex_meta", "fin_lease_meta")}
    assert r.at[1, "outcome"] == pytest.approx(sum(fv["capex_meta"][q] + fv["fin_lease_meta"][q] for q in year))
    assert r.at[1, "outcome_known_from"] == pd.Timestamp("2017-01-30")
    googl = pool[pool["company"] == "googl"]
    assert set(googl["period"]) == {"2021", "2022"}


def test_n1_b3_meta_exact_and_alphabet_m_zero(capex):
    q = Q("2019Q2")  # origin 2019-07-20, position 2; Meta years 2013-2018 known (n = 6), Alphabet none
    info = engine.InfoSet(capex, n1.origin_for(q))
    f = n1.forecast(info, "capex_hyp4", q)
    sh = f.b3_shifts["capex_meta"]
    pool = n1.b3_deviations(capex)
    k2 = pool[(pool["company"] == "meta") & (pool["position"] == 2)
              & (pool["outcome_known_from"] <= info.origin)]
    assert sh["n"] == 6 == len(k2) and sh["m"] == pytest.approx(k2["d"].mean())  # Meta alone with deviations
    assert f.b3_shifts["capex_googl"]["n"] == 0 and f.b3_shifts["capex_googl"]["m"] == 0.0
    # independent B3 for Meta: B2's formula with midpoint x exp(m)
    lo = observations.as_of("guid_capex_meta_cy_lo", info.origin, capex)[pd.Period("2019", freq="Y-DEC")]
    hi = observations.as_of("guid_capex_meta_cy_hi", info.origin, capex)[pd.Period("2019", freq="Y-DEC")]
    y = observations.as_of("capex_meta", info.origin, capex)
    fl = observations.as_of("fin_lease_meta", info.origin, capex)
    year = [Q(f"2019Q{k}") for k in (1, 2, 3, 4)]

    def path(s, targets):
        g = np.diff(np.log(s.to_numpy()[-5:]))
        return {p: s.iloc[-1] * math.exp((p - s.index.max()).n * g.mean()) for p in targets}

    full = (lo + hi) / 2 * math.exp(sh["m"]) - (fl[Q("2019Q1")] + sum(path(fl, year[1:]).values()))
    b1 = path(y, year[1:])
    exp_meta = (full - y[Q("2019Q1")]) * b1[q] / sum(b1.values())
    exp = exp_meta + sum(f.b2_levels[c] for c in n1.COMPANIES if c != "capex_meta")
    assert f.levels["B3"] == pytest.approx(exp, rel=1e-12)
    assert f.levels["B3"] > f.levels["B2"]  # outcomes beat the midpoint: B3 raises Meta's forecast


def test_n1_m_zero_before_four_years_and_b3_equals_b2(capex):
    q = Q("2016Q2")  # 2013-2015 known: n = 3
    f = n1.forecast(engine.InfoSet(capex, n1.origin_for(q)), "capex_hyp4", q)
    assert f.b3_shifts["capex_meta"]["n"] == 3 and f.levels["B3"] == f.levels["B2"]
    q4 = Q("2016Q4")  # origin 2017-01-20: 2016's outcome (known 2017-01-30) not yet known
    f4 = n1.forecast(engine.InfoSet(capex, n1.origin_for(q4)), "capex_hyp4", q4)
    assert f4.b3_shifts["capex_meta"]["n"] == 3 and f4.levels["B3"] == f4.levels["B2"]
    q1 = Q("2017Q2")  # origin 2017-07-20: 2013-2016 known, n = 4 (2013's k = 1 has no B1: 4 quarters known)
    f1 = n1.forecast(engine.InfoSet(capex, n1.origin_for(q1)), "capex_hyp4", q1)
    assert f1.b3_shifts["capex_meta"]["n"] == 4 and f1.levels["B3"] != f1.levels["B2"]
    # Amazon and Microsoft: B3 = B2 = B1
    for c in ("capex_msft", "capex_amzn"):
        fc = n1.forecast(engine.InfoSet(capex, n1.origin_for(q1)), c, q1)
        assert fc.levels["B3"] == fc.levels["B2"] == fc.levels["B1"]


def test_n1_future_outcome_never_enters(capex):
    q = Q("2019Q2")
    origin = n1.origin_for(q)
    ref = n1.forecast(engine.InfoSet(capex, origin), "capex_hyp4", q)
    # the 2018 Q4 first vintage published after the origin: 2018 drops out of the pool (n 6 -> 5)
    t = capex.copy()
    t.loc[(t["series"] == "fin_lease_meta") & (t["period"] == "2018Q4"), "known_from"] = origin + DAY
    f = n1.forecast(engine.InfoSet(t, origin), "capex_hyp4", q)
    assert f.b3_shifts["capex_meta"]["n"] == 5 and f.levels["B3"] != ref.levels["B3"]
    # absurd later revisions and later outcomes never move B3
    poison = pd.concat([capex, _rows("capex_meta", "Q", [Q("2017Q3")], [1e9], [origin + DAY]),
                        _rows("capex_meta", "Q", [Q("2017Q3")], [1e9], ["2019-01-01"], source="revision")],
                       ignore_index=True)
    # the 2019-01-01 revision is known at the origin, but U uses the first vintage only
    got = n1.forecast(engine.InfoSet(poison, origin), "capex_hyp4", q)
    assert got.b3_shifts["capex_meta"] == ref.b3_shifts["capex_meta"]


def test_n1_rerun_from_truncated_table_is_identical(capex):
    errors = n1.backtest_unit(capex, "capex_hyp4")
    pool = n1.b3_deviations(capex)
    for q in (Q("2018Q3"), Q("2020Q4"), Q("2022Q2")):
        origin = n1.origin_for(q)
        t = capex[capex["known_from"] <= origin]
        f = n1.forecast(engine.InfoSet(t, origin), "capex_hyp4", q)  # pool rebuilt from the truncated table
        g = n1.forecast(engine.InfoSet(capex, origin), "capex_hyp4", q, pool)
        assert f.levels["B3"] == g.levels["B3"]
        row = errors.set_index("quarter").loc[q]
        assert row["B3"] == pytest.approx(engine.log_error(f.levels["B3"], row["outcome"]), abs=1e-12)


def _res(mae, holm_p):
    return {per: {"best_baseline": "B1", "metrics": {k: {"MAE": v} for k, v in mae.items()},
                  "step2": {"comparator": min(("B0", "B1", "B2"), key=lambda c: mae[c]),
                            "comparator_mae": min(mae[c] for c in ("B0", "B1", "B2")),
                            "holm": {"B3": holm_p, "DF": 1.0}}}
            for per in ("full", "2023Q1-")}


def test_n1_step2_promotion_mechanics():
    base = {"B0": 10.0, "B1": 5.0, "V1": 6.0, "V2": 6.0, "B2": 4.0}
    p = n1.promotion_step2(_res({**base, "B3": 3.0}, 0.02))
    assert p["checks"]["B3"]["promoted"] and p["champion"] == "B3"
    assert p["checks"]["B3"]["full"]["comparator"] == "B2"
    # beats B1 (the champion) but not B2: fails (F-B10)
    q = n1.promotion_step2(_res({**base, "B3": 4.5}, 0.02))
    assert not q["checks"]["B3"]["promoted"] and q["champion"] == n1.CHAMPION_AT_STEP2
    r = n1.promotion_step2(_res({**base, "B3": 3.0}, 0.2))  # Holm fails
    assert not r["checks"]["B3"]["promoted"] and r["champion"] == n1.CHAMPION_AT_STEP2


def test_n1_step2_holm_family_has_df_at_one(capex):
    errors = n1.backtest_unit(capex, "capex_hyp4")
    errors["in_period"] = errors["quarter"] >= Q("2017Q1")
    errors[["V1", "V2"]] = errors[["V1", "V2"]].fillna(0.0)  # no indicators in this fixture
    res = n1.evaluate(errors, pooled=False)
    s2 = res["full"]["step2"]
    assert s2["p"]["DF"] == 1.0 and s2["holm"]["B3"] == pytest.approx(min(1.0, 2 * s2["p"]["B3"]))
    assert s2["candidates"] == ["B0", "B1", "B2"]
    assert set(res["full"]["dm"]) == set(n1.MODELS) == {"V1", "V2", "B2"}  # locked family unchanged
