"""B2 (companies' own guidance) for N1 and N2: exact formulas, as_of leakage, vintages, currency switch, Meta's
finance-lease adjustment and the fallback to B1. Synthetic fixtures only, no network.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from ai_tracker import observations
from ai_tracker.nowcast import engine as n1_engine
from ai_tracker.nowcast import n1
from ai_tracker.nowcast import n2

M = lambda s: pd.Period(s, freq="M")  # noqa: E731
Q = lambda s: pd.Period(s, freq="Q-DEC")  # noqa: E731
DAY = pd.Timedelta(days=1)


def _rows(series, freq, periods, values, known_from, source="release"):
    n = len(periods)
    kf = known_from if isinstance(known_from, list) else [known_from] * n
    return pd.DataFrame({"series": series, "freq": freq, "period": [str(p) for p in periods],
                         "value": np.asarray(values, dtype=float), "known_from": pd.to_datetime(kf),
                         "source": source, "fetched_at": pd.Timestamp("2026-11-23")})


# ================================================================== N2 (TSMC)


def _q_kf(q):  # guidance known on day 15 of the quarter's first month
    return q.start_time + pd.Timedelta(days=14)


@pytest.fixture(scope="module")
def tsmc():
    rng = np.random.default_rng(7)
    months = pd.period_range("2014-01", "2018-12", freq="M")
    rev = 1e5 * np.exp(np.cumsum(0.01 + 0.05 * rng.standard_normal(len(months))))
    y = pd.Series(rev, index=months)
    kf = [(p + 1).start_time + pd.Timedelta(days=9) for p in months]
    parts = [_rows(n2.TARGET, "M", months, rev, kf)]
    quarters = pd.period_range("2014Q1", "2018Q4", freq="Q-DEC")
    actual = y.groupby(y.index.asfreq("Q-DEC")).sum()
    twd = [q for q in quarters if q < n2.USD_FROM]
    usd = [q for q in quarters if q >= n2.USD_FROM]
    fx = 30.0
    parts += [
        _rows("tsmc_guid_rev_twd_lo", "Q", twd, [actual[q] * 0.97 for q in twd], [_q_kf(q) for q in twd]),
        _rows("tsmc_guid_rev_twd_hi", "Q", twd, [actual[q] * 0.99 for q in twd], [_q_kf(q) for q in twd]),
        _rows("tsmc_guid_rev_usd_lo", "Q", usd, [actual[q] / fx * 0.97 for q in usd], [_q_kf(q) for q in usd]),
        _rows("tsmc_guid_rev_usd_hi", "Q", usd, [actual[q] / fx * 0.99 for q in usd], [_q_kf(q) for q in usd]),
        _rows("tsmc_guid_fx", "Q", quarters, [fx] * len(quarters), [_q_kf(q) for q in quarters]),
        # decoys: a US$ range for an NT$ quarter and an NT$ range for a US$ quarter must never be read
        _rows("tsmc_guid_rev_usd_lo", "Q", [Q("2017Q2")], [1.0], [_q_kf(Q("2017Q2"))]),
        _rows("tsmc_guid_rev_usd_hi", "Q", [Q("2017Q2")], [2.0], [_q_kf(Q("2017Q2"))]),
        _rows("tsmc_guid_rev_twd_lo", "Q", [Q("2017Q3")], [1.0], [_q_kf(Q("2017Q3"))]),
        _rows("tsmc_guid_rev_twd_hi", "Q", [Q("2017Q3")], [2.0], [_q_kf(Q("2017Q3"))]),
    ]
    return pd.concat(parts, ignore_index=True)


def _expected_b2(table, month, g):
    """Register formula, written independently of the engine."""
    origin = n2.origin_for(month)
    y = observations.as_of(n2.TARGET, origin, table)
    q = month.asfreq("Q-DEC")
    months = pd.period_range(q.asfreq("M", "s"), q.asfreq("M", "e"), freq="M")
    known = [k for k in months if k < month]
    unknown = [k for k in months if k >= month]
    b1 = {k: y[k - 12] * y[month - 1] / y[month - 13] for k in unknown}
    return (g - sum(y[k] for k in known)) * b1[month] / sum(b1.values())


def _g(table, series_lo, series_hi, q, when, fx=None):
    lo = observations.as_of(series_lo, when, table)[q]
    hi = observations.as_of(series_hi, when, table)[q]
    return (lo + hi) / 2 * (fx if fx else 1.0)


@pytest.mark.parametrize("month", ["2016-04", "2016-05", "2016-06"])
def test_n2_b2_exact_formula_each_month_position(tsmc, month):
    m = M(month)
    f = n2.forecast(n2.origin_for(m), tsmc)
    g = _g(tsmc, "tsmc_guid_rev_twd_lo", "tsmc_guid_rev_twd_hi", Q("2016Q2"), n2.origin_for(m))
    assert f.inputs.b2_source == "guidance NT$" and f.inputs.b2_guidance == pytest.approx(g)
    assert np.exp(f.logs["B2"] / 100) == pytest.approx(_expected_b2(tsmc, m, g), rel=1e-12)


def test_n2_ntd_before_2017q3_usd_times_fx_from_2017q3(tsmc):
    f_q2 = n2.forecast(n2.origin_for(M("2017-06")), tsmc)
    g_q2 = _g(tsmc, "tsmc_guid_rev_twd_lo", "tsmc_guid_rev_twd_hi", Q("2017Q2"), "2030-01-01")
    assert f_q2.inputs.b2_source == "guidance NT$" and f_q2.inputs.b2_guidance == pytest.approx(g_q2)
    f_q3 = n2.forecast(n2.origin_for(M("2017-07")), tsmc)
    g_q3 = _g(tsmc, "tsmc_guid_rev_usd_lo", "tsmc_guid_rev_usd_hi", Q("2017Q3"), "2030-01-01", fx=30.0)
    assert f_q3.inputs.b2_source == "guidance US$xFX" and f_q3.inputs.b2_guidance == pytest.approx(g_q3)
    assert np.exp(f_q3.logs["B2"] / 100) == pytest.approx(_expected_b2(tsmc, M("2017-07"), g_q3), rel=1e-12)
    used = {s for s, *_ in f_q3.inputs.used}
    assert {"tsmc_guid_rev_usd_lo", "tsmc_guid_rev_usd_hi", "tsmc_guid_fx"} <= used
    assert "tsmc_guid_rev_twd_lo" not in used
    # a US$ quarter without a known FX assumption falls back to B1
    no_fx = tsmc[~((tsmc["series"] == "tsmc_guid_fx") & (tsmc["period"] == "2017Q3"))]
    f = n2.forecast(n2.origin_for(M("2017-07")), no_fx)
    assert f.logs["B2"] == f.logs["B1"] and "FX" in f.inputs.b2_source


def test_n2_guidance_filed_day_after_origin_is_invisible(tsmc):
    m = M("2016-07")
    origin = n2.origin_for(m)  # 2016-08-05
    t = tsmc.copy()
    sel = t["series"].str.startswith("tsmc_guid") & (t["period"] == "2016Q3")
    t.loc[sel, "known_from"] = origin + DAY
    f = n2.forecast(origin, t)
    assert f.logs["B2"] == f.logs["B1"] and f.inputs.b2_source.startswith("B1: no NT$ guidance")
    assert not [r for r in f.inputs.used if r[0].startswith("tsmc_guid")]
    # one day later (next month's origin) it is used
    f2 = n2.forecast(n2.origin_for(m + 1), t)
    assert f2.inputs.b2_source == "guidance NT$"
    # and an absurd value dated after the origin never moves the forecast
    poison = pd.concat([tsmc, _rows("tsmc_guid_rev_twd_lo", "Q", [Q("2016Q3")], [1e12], [origin + DAY]),
                        _rows("tsmc_guid_rev_twd_hi", "Q", [Q("2016Q3")], [1e12], [origin + DAY])], ignore_index=True)
    assert n2.forecast(origin, poison).logs == n2.forecast(origin, tsmc).logs


def test_n2_mid_quarter_update_used_only_after_its_date(tsmc):
    q = Q("2016Q3")
    upd = pd.Timestamp("2016-08-20")  # after the origin for July (08-05), before the origin for August (09-05)
    g0 = _g(tsmc, "tsmc_guid_rev_twd_lo", "tsmc_guid_rev_twd_hi", q, "2030-01-01")
    t = pd.concat([tsmc, _rows("tsmc_guid_rev_twd_lo", "Q", [q], [g0 * 1.10], [upd], "update"),
                   _rows("tsmc_guid_rev_twd_hi", "Q", [q], [g0 * 1.12], [upd], "update")], ignore_index=True)
    jul, aug = n2.forecast(n2.origin_for(M("2016-07")), t), n2.forecast(n2.origin_for(M("2016-08")), t)
    assert jul.inputs.b2_guidance == pytest.approx(g0)
    assert jul.logs == n2.forecast(n2.origin_for(M("2016-07")), tsmc).logs
    assert aug.inputs.b2_guidance == pytest.approx(g0 * 1.11)
    assert np.exp(aug.logs["B2"] / 100) == pytest.approx(_expected_b2(t, M("2016-08"), g0 * 1.11), rel=1e-12)
    assert ("tsmc_guid_rev_twd_lo", "2016Q3", g0 * 1.10, upd) in aug.inputs.used


def test_n2_fallback_to_b1_without_guidance(tsmc):
    bare = tsmc[~tsmc["series"].str.startswith("tsmc_guid")]
    f = n2.forecast(n2.origin_for(M("2016-09")), bare)
    assert f.logs["B2"] == f.logs["B1"] and f.inputs.b2_source.startswith("B1:")
    frame = n2.run(bare)
    ok = frame["e_B1"].notna()
    assert ok.sum() > 24 and (frame.loc[ok, "e_B2"] == frame.loc[ok, "e_B1"]).all()
    assert frame.loc[ok, "b2_source"].str.startswith("B1:").all()


def test_n2_backtest_rerun_from_truncated_table_is_identical(tsmc):
    frame = n2.run(tsmc)
    for m in (M("2016-06"), M("2017-08")):
        origin = n2.origin_for(m)
        f = n2.forecast(origin, tsmc[tsmc["known_from"] <= origin])
        y = 100 * np.log(n2.first_vintages(tsmc).at[m, "value"])
        assert frame.at[m, "e_B2"] == pytest.approx(f.logs["B2"] - y, abs=1e-12)


def test_n2_b2_promotion_is_only_conditional(monkeypatch):
    # The review gate as it stood before R2 approved the TSMC extraction (2026-11-23).
    monkeypatch.setattr(n2, "REVIEW_REQUIRED", {"B2": "villkorad: väntar på oberoende granskning av extraktionen (R2)"})
    rng = np.random.default_rng(3)
    n = 180
    b = rng.normal(0, 3, n)
    idx = pd.period_range("2012-01", periods=n, freq="M")
    frame = pd.DataFrame({"e_B0": b * 1.2, "e_B1": b, "e_V1": b * 1.05, "e_B2": b * 0.3, "n_train": 100}, index=idx)
    res = n2.evaluate(frame)
    assert set(res.holm) == {"V1", "B2"} and res.holm["B2"] < 0.10
    assert all(line.startswith("PASS") for line in res.checks["B2"])
    assert res.conditional == {"B2": n2.REVIEW_REQUIRED["B2"]} and "R2" in res.conditional["B2"]
    assert res.champion == "B1" and not res.promoted


def test_n2_b2_promoted_once_review_approved():
    rng = np.random.default_rng(3)
    n = 180
    b = rng.normal(0, 3, n)
    idx = pd.period_range("2012-01", periods=n, freq="M")
    frame = pd.DataFrame({"e_B0": b * 1.2, "e_B1": b, "e_V1": b * 1.05, "e_B2": b * 0.3, "n_train": 100}, index=idx)
    assert n2.REVIEW_REQUIRED == {}
    res = n2.evaluate(frame)
    assert res.champion == "B2" and not res.conditional


# ================================================================== N1 (capex)

YEARS = pd.period_range("2017Q1", "2022Q4", freq="Q-DEC")
ORIGIN = n1.origin_for(Q("2021Q2"))  # 2021-07-20


@pytest.fixture(scope="module")
def capex():
    rng = np.random.default_rng(11)
    kf = [q.end_time.normalize() + pd.Timedelta(days=30) for q in YEARS]
    parts, total = [], 0
    for i, c in enumerate(n1.COMPANIES):
        v = (1000 + 300 * i) * np.exp(np.cumsum(0.03 + 0.05 * rng.standard_normal(len(YEARS))))
        parts.append(_rows(c, "Q", YEARS, v, kf))
        total = total + v
    parts.append(_rows("capex_hyp4", "Q", YEARS, total, kf))
    lease = 50 * np.exp(np.cumsum(0.02 + 0.1 * rng.standard_normal(len(YEARS))))
    parts.append(_rows("fin_lease_meta", "Q", YEARS, lease, kf))
    a = pd.Period("2021", freq="Y-DEC")
    parts += [
        # Meta's 2021 range (incl. finance leases), set in October 2020 and updated in April 2021
        _rows("guid_capex_meta_cy_lo", "A", [a, a], [7000, 7400], ["2020-10-29", "2021-04-28"]),
        _rows("guid_capex_meta_cy_hi", "A", [a, a], [7600, 8000], ["2020-10-29", "2021-04-28"]),
        _rows("guid_capex_googl_cy_lo", "A", [a], [5500], ["2021-02-04"]),
        _rows("guid_capex_googl_cy_hi", "A", [a], [5900], ["2021-02-04"]),
        # Amazon and Microsoft guide on other definitions: present, never used
        _rows("guid_capex_amzn_cy_lo", "A", [a], [1.0], ["2021-02-04"]),
        _rows("guid_capex_amzn_cy_hi", "A", [a], [2.0], ["2021-02-04"]),
        _rows("guid_capex_msft_q_lo", "Q", [Q("2021Q2")], [1.0], ["2021-04-27"]),
    ]
    return pd.concat(parts, ignore_index=True)


def _b1_path(y: pd.Series, targets):
    """Independent drift path: last level * exp(h * mean of the last four log growth rates)."""
    g = np.diff(np.log(y.to_numpy()[-5:]))
    last = y.index.max()
    return {p: y.iloc[-1] * math.exp((p - last).n * g.mean()) for p in targets}


def _expected_company(table, series, q, origin, lo, hi, lease=None):
    y = observations.as_of(series, origin, table)
    year = pd.period_range(f"{q.year}Q1", f"{q.year}Q4", freq="Q-DEC")
    known = [p for p in year if p in y.index]
    unknown = [p for p in year if p not in y.index]
    full = (lo + hi) / 2
    if lease:
        f = observations.as_of(lease, origin, table)
        f_unknown = [p for p in year if p not in f.index]
        full -= sum(f[p] for p in year if p in f.index) + sum(_b1_path(f, f_unknown).values())
    b1 = _b1_path(y, unknown)
    return (full - sum(y[p] for p in known)) * b1[q] / sum(b1.values())


def test_n1_meta_finance_lease_adjustment_exact(capex):
    q = Q("2021Q2")
    f = n1.forecast(n1_engine.InfoSet(capex, ORIGIN), "capex_meta", q)
    # the April update (7400-8000) is known at 2021-07-20; finance leases: Q1 known, Q2-Q4 by B1
    exp = _expected_company(capex, "capex_meta", q, ORIGIN, 7400, 8000, lease="fin_lease_meta")
    assert f.levels["B2"] == pytest.approx(exp, rel=1e-12)
    assert f.b2_sources["capex_meta"] == "guidance - finance leases"
    # without the lease adjustment the number would be larger: the adjustment is really applied
    assert exp < _expected_company(capex, "capex_meta", q, ORIGIN, 7400, 8000)


def test_n1_alphabet_direct_and_amazon_microsoft_b1(capex):
    q = Q("2021Q2")
    info = n1_engine.InfoSet(capex, ORIGIN)
    f = n1.forecast(info, "capex_hyp4", q)
    assert f.b2_sources == {"capex_msft": "B1 (guidance definition not comparable)",
                            "capex_googl": "guidance",
                            "capex_amzn": "B1 (guidance definition not comparable)",
                            "capex_meta": "guidance - finance leases"}
    parts = {
        "capex_googl": _expected_company(capex, "capex_googl", q, ORIGIN, 5500, 5900),
        "capex_meta": _expected_company(capex, "capex_meta", q, ORIGIN, 7400, 8000, lease="fin_lease_meta"),
    }
    for c in ("capex_msft", "capex_amzn"):
        parts[c] = n1.forecast(n1_engine.InfoSet(capex, ORIGIN), c, q).levels["B1"]
    assert f.levels["B2"] == pytest.approx(sum(parts.values()), rel=1e-12)
    for c in ("capex_msft", "capex_amzn"):
        fc = n1.forecast(n1_engine.InfoSet(capex, ORIGIN), c, q)
        assert fc.levels["B2"] == fc.levels["B1"]
    assert not any(s.startswith(("guid_capex_amzn", "guid_capex_msft")) for s in info.used)


def test_n1_guidance_filed_day_after_origin_is_invisible(capex):
    q = Q("2021Q2")
    base = n1.forecast(n1_engine.InfoSet(capex, ORIGIN), "capex_meta", q)
    # the April update moved to the day after the origin: the October 2020 range is used instead
    t = capex.copy()
    t.loc[t["series"].str.startswith("guid_capex_meta") & (t["known_from"] == "2021-04-28"), "known_from"] = ORIGIN + DAY
    f = n1.forecast(n1_engine.InfoSet(t, ORIGIN), "capex_meta", q)
    assert f.levels["B2"] == pytest.approx(
        _expected_company(t, "capex_meta", q, ORIGIN, 7000, 7600, lease="fin_lease_meta"), rel=1e-12)
    assert f.levels["B2"] != base.levels["B2"]
    # all of Meta's guidance after the origin: B1
    t2 = capex.copy()
    t2.loc[t2["series"].str.startswith("guid_capex_meta"), "known_from"] = ORIGIN + DAY
    f2 = n1.forecast(n1_engine.InfoSet(t2, ORIGIN), "capex_meta", q)
    assert f2.levels["B2"] == f2.levels["B1"] and f2.b2_sources["capex_meta"] == "B1 (no full-year range known)"
    # absurd guidance and finance-lease values dated after the origin never move B2
    a = pd.Period("2021", freq="Y-DEC")
    poison = pd.concat([capex,
                        _rows("guid_capex_meta_cy_lo", "A", [a], [1e9], [ORIGIN + DAY]),
                        _rows("guid_capex_googl_cy_hi", "A", [a], [1e9], [ORIGIN + DAY]),
                        _rows("fin_lease_meta", "Q", [Q("2021Q2")], [1e9], [ORIGIN + DAY]),
                        _rows("capex_meta", "Q", [Q("2021Q2")], [1e9], [ORIGIN + DAY])], ignore_index=True)
    info = n1_engine.InfoSet(poison, ORIGIN)
    got = n1.forecast(info, "capex_hyp4", q).levels
    ref = n1.forecast(n1_engine.InfoSet(capex, ORIGIN), "capex_hyp4", q).levels
    assert {k for k, v in got.items() if np.isfinite(v)} == {k for k, v in ref.items() if np.isfinite(v)}
    assert all(got[k] == ref[k] for k in ref if np.isfinite(ref[k]))
    assert all(pd.Timestamp(i["known_from"]) <= ORIGIN for i in info.inputs())


def test_n1_mid_year_update_used_only_after_its_date(capex):
    q1 = n1.forecast(n1_engine.InfoSet(capex, n1.origin_for(Q("2021Q1"))), "capex_meta", Q("2021Q1"))
    exp = _expected_company(capex, "capex_meta", Q("2021Q1"), n1.origin_for(Q("2021Q1")), 7000, 7600,
                            lease="fin_lease_meta")  # 2021-04-20: before the 04-28 update
    assert q1.levels["B2"] == pytest.approx(exp, rel=1e-12)


def test_n1_fallback_to_b1_without_guidance(capex):
    bare = capex[~capex["series"].str.startswith("guid_capex")]
    q = Q("2021Q2")
    f = n1.forecast(n1_engine.InfoSet(bare, ORIGIN), "capex_hyp4", q)
    b1s = {c: n1.forecast(n1_engine.InfoSet(bare, ORIGIN), c, q).levels["B1"] for c in n1.COMPANIES}
    # per company and then summed (register): with no guidance B2 = sum of the companies' B1
    assert f.levels["B2"] == pytest.approx(sum(b1s.values()), rel=1e-12)
    assert all(v.startswith("B1") for v in f.b2_sources.values())
    for c in n1.COMPANIES:
        fc = n1.forecast(n1_engine.InfoSet(bare, ORIGIN), c, q)
        assert fc.levels["B2"] == fc.levels["B1"]
    # a series with no guidance mapping: B2 = its own B1
    g = n1.forecast(n1_engine.InfoSet(bare, ORIGIN), "fin_lease_meta", q)
    assert g.levels["B2"] == g.levels["B1"]


def test_n1_b2_promotion_is_only_conditional():
    res = {}
    for per in ("full", "2023Q1-"):
        res[per] = {"best_baseline": "B1",
                    "metrics": {"B0": {"MAE": 10.0}, "B1": {"MAE": 5.0}, "V1": {"MAE": 6.0}, "V2": {"MAE": 6.0},
                                "B2": {"MAE": 3.0}},
                    "dm": {"V1": {"holm_p": 0.5}, "V2": {"holm_p": 0.5}, "B2": {"holm_p": 0.01}}}
    p = n1.promotion(res)
    assert p["checks"]["B2"]["promoted"] and p["champion"] == "B1"
    assert p["conditional"] == {"B2": n1.REVIEW_REQUIRED["B2"]}
