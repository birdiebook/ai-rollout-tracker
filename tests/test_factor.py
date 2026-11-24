"""C3 factor model and variant DF: EM/Kalman on simulated DFM data, ragged edge, real-time (no data after the origin,
poison test), the holdout guard and DF's pseudo-real-time training rows. Synthetic fixtures only, no network."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai_tracker.factor import dfm, guard, realtime
from ai_tracker.nowcast import df

TS = pd.Timestamp


# ------------------------------------------------------------------ dfm on simulated data


def _sim(T=180, seed=3, kinds=None, a=0.9):
    kinds = kinds or ["M"] * 8 + ["QF"] * 4 + ["QS"] * 2
    rng = np.random.default_rng(seed)
    lam = rng.uniform(0.4, 1.0, len(kinds))
    R = rng.uniform(0.2, 0.6, len(kinds))
    z, f = dfm.simulate(T, kinds, lam, R, a, seed=seed)
    return z, f, kinds, lam


def test_em_recovers_factor_mixed_frequency():
    z, f, kinds, lam = _sim()
    r = dfm.fit(z, kinds)
    assert r.converged
    assert np.corrcoef(r.f, f)[0, 1] > 0.95
    assert abs(r.params.a - 0.9) < 0.1
    assert np.corrcoef(r.params.lam, lam)[0, 1] > 0.8
    assert (r.params.lam > 0).all()  # sign normalisation: loadings sum positive


def test_em_loglik_non_decreasing():
    z, _f, kinds, _lam = _sim(seed=5)
    r = dfm.fit(z, kinds, tol=1e-9, max_iter=40)
    assert np.all(np.diff(r.history) > -1e-6)


def test_em_recovers_factor_from_quarterly_only():
    z, f, kinds, _lam = _sim(T=240, seed=7, kinds=["QF"] * 5 + ["QS"])
    r = dfm.fit(z, kinds)
    q = np.arange(2, 240, 3)  # quarter-end months, where the data are
    assert np.corrcoef(r.f[q], f[q])[0, 1] > 0.85


def test_sign_is_flipped_when_loadings_negative():
    z, f, kinds, _lam = _sim(seed=11)
    r1, r2 = dfm.fit(z, kinds), dfm.fit(-z, kinds)
    assert np.allclose(r1.f, -r2.f, atol=1e-6)
    assert r2.params.lam.sum() > 0


def test_ragged_edge_projection_and_partial_information():
    z, f, kinds, _lam = _sim(seed=13)
    zr = z.copy()
    zr[-6:, :] = np.nan  # nothing observed in the last 6 months
    zr[-3:, 0] = z[-3:, 0]  # ... except one monthly series in the last 3
    r = dfm.fit(zr, kinds)
    assert np.isfinite(r.f).all() and len(r.f) == z.shape[0]
    # months -6..-4 have no data: the smoothed factor moves between the known ends (no jumps to zero)
    assert np.isfinite(r.f_var[-6:]).all() and (r.f_var[-6:-3] > r.f_var[:-12].mean()).all()
    # with no data at all at the end, the filtered path decays with a
    zn = z.copy()
    zn[-4:, :] = np.nan
    rn = dfm.fit(zn, kinds)
    a = rn.params.a
    assert np.allclose(rn.f[-3:], rn.f[-4] * a ** np.arange(1, 4), atol=1e-6)


def test_missing_series_column_is_harmless():
    z, f, kinds, _lam = _sim(seed=17)
    z[:, 1] = np.nan
    r = dfm.fit(z, kinds)
    assert np.corrcoef(r.f, f)[0, 1] > 0.9


# ------------------------------------------------------------------ synthetic observation table


def _rows(series, freq, periods, values, known_from):
    return pd.DataFrame({"series": series, "freq": freq, "period": [str(p) for p in periods],
                         "value": np.asarray(values, float), "known_from": pd.to_datetime(list(known_from)),
                         "source": "release", "fetched_at": TS("2026-11-23")})


def synthetic_table(end="2021-12", seed=0) -> pd.DataFrame:
    """Monthly capex-block series and quarterly demand-block series driven by two latent growth factors."""
    rng = np.random.default_rng(seed)
    months = pd.period_range("2008-01", end, freq="M")
    T = len(months)
    g1 = np.zeros(T)
    g2 = np.zeros(T)
    for t in range(1, T):
        g1[t] = 0.9 * g1[t - 1] + 0.01 * rng.standard_normal()
        g2[t] = 0.9 * g2[t - 1] + 0.01 * rng.standard_normal()
    parts = []
    for i, key in enumerate(["tsmc_revenue_m", "us_imports_tw_m", "us_ip_semis_m", "us_elec_sales_com_va_m"]):
        lvl = 100 * np.exp(np.cumsum(0.005 + (0.6 + 0.2 * i) * g1 + 0.004 * rng.standard_normal(T)))
        kf = [m.end_time.normalize() + pd.Timedelta(days=10 + 5 * i) for m in months]
        parts.append(_rows(key, "M", months, lvl, kf))
    quarters = pd.period_range("2008Q1", pd.Period(end, "M").asfreq("Q-DEC"), freq="Q-DEC")
    for i, key in enumerate(["rev_aws", "rev_nvda_datacenter", "rev_msft_cloud"]):
        lm = 1000 * np.exp(np.cumsum(0.01 + (0.7 + 0.2 * i) * g2 + 0.004 * rng.standard_normal(T)))
        s = pd.Series(lm, index=months)
        qv = [s[pd.period_range(q.asfreq("M", "s"), q.asfreq("M", "e"), freq="M")].sum() for q in quarters]
        kf = [q.end_time.normalize() + pd.Timedelta(days=25 + 3 * i) for q in quarters]
        parts.append(_rows(key, "Q", quarters, qv, kf))
    return pd.concat(parts, ignore_index=True)


@pytest.fixture(scope="module")
def table():
    return synthetic_table()


def test_vintage_estimates_both_blocks(table, tmp_path):
    v = realtime.vintage(table, "2019-06-05", cache_dir=tmp_path)
    assert v.available("capex") and v.available("demand")
    assert set(v.fits["capex"].keys) == {"tsmc_revenue_m", "us_imports_tw_m", "us_ip_semis_m", "us_elec_sales_com_va_m"}
    assert v.path.index[0] == pd.Period("2010-01", "M") and v.path.index[-1] == pd.Period("2019-06", "M")
    assert v.path[["capex", "demand"]].notna().all().all()
    # cached: the second call returns the same object content from disk
    v2 = realtime.vintage(table, "2019-06-05", cache_dir=tmp_path)
    pd.testing.assert_frame_equal(v.path, v2.path)
    assert len(list(tmp_path.glob("*.pkl"))) == 1


def test_block_needs_two_eligible_series(table):
    t = table[~table["series"].isin(["rev_nvda_datacenter", "rev_msft_cloud"])]
    v = realtime.estimate(t, "2019-06-05")
    assert v.available("capex") and not v.available("demand")
    assert v.path["demand"].isna().all()


def test_eligibility_needs_24_monthly_or_8_quarterly_pace_values(table):
    # rev_msft_cloud starting in 2017Q1: 4-quarter pace from 2018Q1, so 7 pace values known on 2019-11-05 (Q1-Q3 2019 +
    # 2018) -> not eligible; on 2020-02-05 it has 8 (2018Q1-2019Q4 known from 2020-01-31) -> eligible
    t = table[~((table["series"] == "rev_msft_cloud") & (table["period"] < "2017Q1"))]
    ctx = realtime.measures.Context(realtime.truncate(t, "2019-11-05"))
    p = realtime.panel(ctx, "2019-11-05", "demand")
    info = {s.key: s for s in p.info}
    assert not info["rev_msft_cloud"].eligible and info["rev_msft_cloud"].n_pace == 7
    ctx = realtime.measures.Context(realtime.truncate(t, "2020-02-05"))
    p = realtime.panel(ctx, "2020-02-05", "demand")
    assert "rev_msft_cloud" in p.keys


def test_zscore_uses_only_window_values_known_at_origin(table):
    ctx = realtime.measures.Context(realtime.truncate(table, "2019-06-05"))
    p = realtime.panel(ctx, "2019-06-05", "capex")
    z = p.z[:, p.keys.index("tsmc_revenue_m")]
    z = z[np.isfinite(z)]
    assert abs(z.mean()) < 1e-9 and abs(z.std(ddof=1) - 1) < 1e-9
    # tsmc known ~10 days after the month: May 2019 is not known on 2019-06-05, April is
    assert p.months[np.isfinite(p.z[:, p.keys.index("tsmc_revenue_m")])][-1] == pd.Period("2019-04", "M")


def test_poison_rows_after_origin_change_nothing(table):
    origin = TS("2019-06-05")
    clean = realtime.estimate(table, origin)
    poison = []
    for key in ["tsmc_revenue_m", "us_imports_tw_m", "rev_aws", "rev_nvda_datacenter"]:
        r = table[table["series"] == key].copy()
        r["value"] = r["value"] * 1000.0  # absurd revisions of every period ...
        r["known_from"] = origin + pd.Timedelta(days=1)  # ... known one day after the origin
        poison.append(r)
    future = _rows("us_ip_semis_m", "M", pd.period_range("2019-05", "2019-12", freq="M"), [1e9] * 8,
                   [origin + pd.Timedelta(days=2)] * 8)
    v = realtime.estimate(pd.concat([table, *poison, future], ignore_index=True), origin)
    pd.testing.assert_frame_equal(clean.path, v.path)


def test_holdout_guard_raises(table, tmp_path):
    assert not guard.HOLDOUT_OPEN
    with pytest.raises(guard.HoldoutClosed):
        realtime.vintage(table, "2025-07-01", cache_dir=tmp_path)
    with pytest.raises(guard.HoldoutClosed):
        realtime.vintage(table, "2026-11-05", cache=False)
    with pytest.raises(guard.HoldoutClosed):
        realtime.realtime_monthly(table, "2025-05", "2025-07")
    guard.check("2025-06-30")  # the last development day is allowed
    assert list(tmp_path.iterdir()) == []


def test_dev_table_drops_rows_known_after_dev_end():
    t = _rows("x", "M", ["2025-05", "2025-06"], [1, 2], ["2025-06-30", "2025-07-01"])
    assert list(guard.dev_table(t)["period"]) == ["2025-05"]


def test_df_run_refuses_holdout_origins():
    frame = pd.DataFrame({"origin": [TS("2025-06-05"), TS("2025-07-05")],
                          "outcome_known_from": [TS("2025-06-10"), TS("2025-06-20")],
                          "e_B0": [1.0, 2.0], "e_B1": [1.0, 2.0]},
                         index=pd.PeriodIndex(["2025-05", "2025-06"], freq="M"))
    tgt = df.Target("T", "B1", ("B0", "B1"), ("DF",), pd.Period("2023-01", "M"), lambda t: frame, df._month)
    with pytest.raises(guard.HoldoutClosed):
        df.run(tgt, pd.DataFrame(columns=["series", "known_from"]), vintage_fn=lambda t, o: None)


def test_realtime_monthly_uses_month_end_vintages(table, tmp_path, monkeypatch):
    monkeypatch.setattr(realtime, "CACHE_DIR", tmp_path)
    rt = realtime.realtime_monthly(table, "2019-03", "2019-05")
    assert list(rt.index.astype(str)) == ["2019-03", "2019-04", "2019-05"]
    v = realtime.vintage(table, "2019-04-30")
    assert rt.at[pd.Period("2019-04", "M"), "capex"] == v.path.at[pd.Period("2019-04", "M"), "capex"]


# ------------------------------------------------------------------ DF rows


def test_df_months():
    cur, prev = df._quarter_months(pd.Period("2024Q2", "Q-DEC"))
    assert list(cur.astype(str)) == ["2024-04", "2024-05", "2024-06"] and list(prev.astype(str))[0] == "2024-01"
    cur, prev = df._fiscal_months(pd.Period("2024Q3", "Q-DEC"))  # Nvidia Aug-Oct 2024, ends 2024-10-27
    assert list(cur.astype(str)) == ["2024-08", "2024-09", "2024-10"]
    assert list(prev.astype(str)) == ["2024-05", "2024-06", "2024-07"]
    cur, prev = df._month(pd.Period("2024-03", "M"))
    assert str(cur[0]) == "2024-03" and str(prev[0]) == "2024-02"


def _df_frame(n=40, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.period_range("2015Q1", periods=n, freq="Q-DEC")
    origin = [q.end_time.normalize() + pd.Timedelta(days=20) for q in idx]
    kf = [q.end_time.normalize() + pd.Timedelta(days=30) for q in idx]
    dc, dd = rng.standard_normal(n), rng.standard_normal(n)
    r = 1.0 + 3.0 * dc - 2.0 * dd + 0.3 * rng.standard_normal(n)
    return pd.DataFrame({"origin": origin, "outcome_known_from": kf, "df_capex": dc, "df_demand": dd, "r": r,
                         "e_B1": -r}, index=idx)


def test_df_expanding_ols_recovers_relation_and_needs_12_rows():
    f = df.apply_df(_df_frame())
    assert f["e_DF"].iloc[:12].isna().all() and f["e_DF"].iloc[12:].notna().all()
    assert f["n_train"].iloc[12] == 12  # rows 0..11, each known before the origin of row 12
    assert f["e_DF"].iloc[12:].abs().mean() < 0.3 * f["e_B1"].iloc[12:].abs().mean()
    assert abs(f["b_capex"].iloc[-1] - 3.0) < 0.3


def test_df_training_rows_only_with_outcome_known_at_origin():
    f = _df_frame()
    # the outcome of each period is known only 200 days after its quarter: training lags by two quarters
    f["outcome_known_from"] = [q.end_time.normalize() + pd.Timedelta(days=200) for q in f.index]
    g = df.apply_df(f)
    i = 20
    o = g["origin"].iloc[i]
    expected = int(((g.index < g.index[i]) & (g["outcome_known_from"] <= o)).sum())
    assert g["n_train"].iloc[i] == expected < i
    # a poisoned outcome that is not yet known at the origin cannot change the forecast
    f2 = f.copy()
    f2.loc[f2.index[i - 1], "r"] = 1e6
    assert df.apply_df(f2)["e_DF"].iloc[i] == g["e_DF"].iloc[i]


def test_df_missing_factor_rows_are_skipped():
    f = _df_frame()
    f.loc[f.index[:5], "df_demand"] = np.nan
    g = df.apply_df(f)
    assert g["e_DF"].iloc[:17].isna().all() and np.isfinite(g["e_DF"].iloc[17])


def test_df_evaluate_comparator_and_holm():
    f = df.apply_df(_df_frame())
    f["e_B0"] = f["e_B1"] * 1.5
    tgt = df.TARGETS["N3"]
    e = df.evaluate(tgt, f)
    assert e["full"]["comparator"] == "B1" and e["full"]["n"] == 28
    assert e["full"]["holm_p"] == pytest.approx(min(1.0, 3 * e["full"]["dm_p"]))  # family {B2, B3, DF}, others p = 1


def test_origin_before_sample_start_has_no_factor(table):
    v = realtime.estimate(table, "2009-06-05")
    assert not v.available("capex") and not v.available("demand") and v.path.empty
