"""D2 (nowcast/horizon.py): horizons 1-8, leakage (as_of for every input, poison rows), first-vintage outcome per
horizon, per-horizon error pools (F-C7) and the closed holdout (G-E). Synthetic fixtures only, no network."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from ai_tracker.factor import guard
from ai_tracker.nowcast import engine, horizon, n1, n4

TS = pd.Timestamp
Q = "Q-DEC"
QS = pd.period_range("2014Q1", "2021Q4", freq=Q)
ENDS = QS.end_time.normalize()


def _rows(series, periods, values, known_from, freq="Q", source="release"):
    return pd.DataFrame({"series": series, "freq": freq, "period": [str(p) for p in periods],
                         "value": np.asarray(values, dtype=float), "known_from": pd.to_datetime(list(known_from)),
                         "source": source, "fetched_at": TS("2026-11-24")})


def _path(n, seed, drift=0.05, sd=0.04, start=100.0):
    rng = np.random.default_rng(seed)
    return start * np.exp(np.cumsum(drift + sd * rng.standard_normal(n)))


def make_table() -> pd.DataFrame:
    parts, capex = [], {}
    for i, c in enumerate(n1.COMPANIES):
        v = _path(len(QS), 1 + i, start=1000 * (i + 1))
        kf = ENDS + pd.Timedelta(days=25 + 3 * i)
        capex[c] = (v, kf)
        parts.append(_rows(c, QS, v, kf))
    total = sum(v for v, _ in capex.values())
    kf_total = pd.DatetimeIndex(np.max(np.vstack([kf.values for _, kf in capex.values()]), axis=0))
    parts.append(_rows(n1.TARGET, QS, total, kf_total))
    lease = _path(len(QS), 9, start=50)
    parts.append(_rows("fin_lease_meta", QS, lease, ENDS + pd.Timedelta(days=34)))
    # full-year guidance for year Y given at the end of October of Y-1, midpoint = 1.03 x the realised year
    years = sorted({q.year for q in QS})
    for series, (prefix, lse) in n1.B2_GUIDANCE.items():
        v = pd.Series(capex[series][0], index=QS)
        if lse:
            v = v + pd.Series(lease, index=QS)
        full = v.groupby(v.index.year).sum()
        yp = [pd.Period(str(y), freq="Y-DEC") for y in years[1:]]
        kf = [TS(f"{y - 1}-10-30") for y in years[1:]]
        mid = np.array([1.03 * full[y] for y in years[1:]])
        parts.append(_rows(f"{prefix}_lo", yp, 0.98 * mid, kf, freq="A"))
        parts.append(_rows(f"{prefix}_hi", yp, 1.02 * mid, kf, freq="A"))
    for i, c in enumerate(n4.COMPONENTS):
        parts.append(_rows(c, QS, _path(len(QS), 10 + i, start=300 * (i + 1)), ENDS + pd.Timedelta(days=25 + 3 * i)))
    for i, c in enumerate(n4.RPO.components):
        parts.append(_rows(c, QS, _path(len(QS), 20 + i, start=900 * (i + 1)), ENDS + pd.Timedelta(days=26 + 2 * i)))
    return pd.concat(parts, ignore_index=True)


@pytest.fixture(scope="module")
def table():
    return make_table()


@pytest.fixture(scope="module")
def frames(table):
    return {name: horizon.run(table, t) for name, t in horizon.TARGETS.items()}


ORIGIN = TS("2019-01-20")


def _levels(p: horizon.Path) -> dict:
    return {(m, h): v for m, d in p.levels.items() for h, v in d.items()}


# ------------------------------------------------------------------ leakage


def test_poison_rows_after_the_origin_change_nothing(table):
    poison = []
    for s, g in table.groupby("series"):
        r = g.drop_duplicates("period").copy()
        r["value"] *= 7.0
        r["known_from"] = ORIGIN + pd.Timedelta(days=1)
        poison.append(r)
        if g["freq"].iloc[0] == "Q":  # and new quarters, published right after the origin
            fut = pd.period_range("2022Q1", "2022Q4", freq=Q)
            poison.append(_rows(s, fut, np.full(len(fut), 1e9), [ORIGIN + pd.Timedelta(days=2)] * len(fut)))
    poisoned = pd.concat([table, *poison], ignore_index=True)
    for t in horizon.TARGETS.values():
        clean = horizon.forecast(horizon.prepare(table), t, ORIGIN)
        dirty = horizon.forecast(horizon.prepare(poisoned), t, ORIGIN)
        a, b = _levels(clean), _levels(dirty)
        assert a.keys() == b.keys()
        assert all(np.isfinite(a[k]) for k in a if k[1] <= 3), t.name  # every model is formed for h 1-3
        for k in a:
            assert (np.isnan(a[k]) and np.isnan(b[k])) or a[k] == pytest.approx(b[k]), (t.name, k)
        assert clean.base == dirty.base and clean.n_train == dirty.n_train


def test_base_is_latest_known_quarter_and_baselines(table):
    t = horizon.prepare(table)
    p = horizon.forecast(t, horizon.CAPEX, ORIGIN)
    y = engine.InfoSet(t, ORIGIN).get(n1.TARGET)
    assert p.base == y.index.max() == pd.Period("2018Q3", Q)  # 2018Q4 is filed after the origin
    d = float(np.diff(np.log(y.iloc[-5:].to_numpy())).mean())
    for h in horizon.HORIZONS:
        assert p.levels["B0"][h] == pytest.approx(y.iloc[-1])
        assert p.levels["B1"][h] == pytest.approx(y.iloc[-1] * math.exp(h * d))


def test_b2_uses_guided_years_then_b1_growth_from_the_last_guided_quarter(table):
    t = horizon.prepare(table)
    p = horizon.forecast(t, horizon.CAPEX, ORIGIN)  # L = 2018Q3; 2018 and 2019 guided, 2020 not yet
    src = p.b2_sources["capex_googl"]
    assert all(src[h].startswith("guidance") for h in range(1, 6))  # 2018Q4, 2019Q1-Q4
    assert all(src[h] == "B1 growth from 2019Q4" for h in (6, 7, 8))
    assert all(v.startswith("B1") for v in p.b2_sources["capex_amzn"].values())
    info = engine.InfoSet(t, ORIGIN)
    g = {h: n1.guided_company(info, "capex_googl", p.base + h, ahead=True)[0] for h in range(1, 6)}
    y = info.get("capex_googl")
    d = float(np.diff(np.log(y.iloc[-5:].to_numpy())).mean())
    msft = n1.b1_path(info.get("capex_msft"), [p.base + 7])[p.base + 7]
    amzn = n1.b1_path(info.get("capex_amzn"), [p.base + 7])[p.base + 7]
    meta = horizon.b2_company(info, "capex_meta", p.base)[0][7]
    assert p.levels["B2"][7] == pytest.approx(msft + amzn + meta + g[5] * math.exp(2 * d))
    # the guided year sums to the implied full year (no quarter of 2019 known at the origin)
    lo, hi = info.get("guid_capex_googl_cy_lo"), info.get("guid_capex_googl_cy_hi")
    yp = pd.Period("2019", freq=lo.index.freq)
    assert sum(g[h] for h in range(2, 6)) == pytest.approx((lo[yp] + hi[yp]) / 2)


def test_v_kedja_is_direct_ols_per_h_with_at_least_12_rows(table):
    t = horizon.prepare(table)
    info = engine.InfoSet(t, ORIGIN)
    p = horizon.forecast(t, horizon.CAPEX, ORIGIN)
    R, X = horizon.regressors(info)
    y = info.get(n1.TARGET)
    L = p.base
    h = 2
    ts = [s for s in R.index.intersection(X.index) if s + h <= L and s in y.index]
    A = np.column_stack([np.ones(len(ts)), R[ts], X[ts]])
    g = 100 * (np.log(y[[s + h for s in ts]].to_numpy()) - np.log(y[ts].to_numpy()))
    coef, *_ = np.linalg.lstsq(A, g, rcond=None)
    assert p.n_train[h] == len(ts) >= horizon.MIN_TRAIN
    assert p.levels["V_kedja"][h] == pytest.approx(y[L] * math.exp((coef @ [1, R[L], X[L]]) / 100))
    # X is the log deviation from the expanding mean of x_capex_cloud known at the origin
    x = info.get(horizon.X_KEY)
    assert X[L] == pytest.approx(100 * (math.log(x[L]) - np.log(x[x.index <= L]).mean()))
    # rpo y/y at L
    r = info.get("rpo_hyp4")
    assert R[L] == pytest.approx(100 * math.log(r[L] / r[L - 4]))
    # an early origin has fewer than 12 rows: no V_kedja
    early = horizon.forecast(t, horizon.CAPEX, n1.origin_for(pd.Period("2017Q1", Q)))
    short = [k for k, n in early.n_train.items() if n < horizon.MIN_TRAIN]
    assert short and all(np.isnan(early.levels["V_kedja"][k]) for k in short)


# ------------------------------------------------------------------ outcomes and pools


def test_outcome_is_the_first_vintage_for_every_horizon(table):
    q = pd.Period("2019Q2", Q)
    first = {}
    rev = [table]
    for key, comp in ((n1.TARGET, None), (None, "rev_aws")):
        s = key or comp
        r = table[(table.series == s) & (table.period == str(q))]
        first[s] = float(r["value"].iloc[0])
        rev.append(_rows(s, [q], [first[s] * 1.5], [TS("2020-03-01")], source="revision"))
    t = pd.concat(rev, ignore_index=True)
    f = horizon.run(t, horizon.CAPEX)
    rows = f[f["quarter"] == q]
    assert sorted(rows["h"]) == list(horizon.HORIZONS)
    assert np.allclose(rows["outcome"], first[n1.TARGET])
    c = horizon.run(t, horizon.CLOUD)
    cloud_first = table[table.series.isin(n4.COMPONENTS) & (table.period == str(q))]["value"].sum()
    crow = c[c["quarter"] == q]
    assert len(crow) and np.allclose(crow["outcome"], cloud_first)
    assert (pd.to_datetime(f["outcome_known_from"]) > pd.to_datetime(f["origin"])).all()


def test_error_pool_per_horizon_holds_only_outcomes_known_at_the_origin(frames):
    f = frames["capex"]
    sc = horizon.scored(f, horizon.CAPEX)
    assert len(sc) and sc["method"].notna().any()
    for _, r in sc.iterrows():
        g = f[(f["h"] == r["h"]) & f[r["model"]].notna() & (f["origin"] != r["origin"])]
        expect = int((pd.to_datetime(g["outcome_known_from"]) <= r["origin"]).sum())
        assert r["n_pool"] == expect
    # a longer horizon has fewer known errors at the same origin, and h=8 errors of the previous origins are not in
    # the pool yet (their outcomes are seven quarters away)
    o = f.loc[f["h"] == 8, "origin"].max()
    n = sc[(sc["origin"] == o) & (sc["model"] == "B0")].set_index("h")["n_pool"]
    assert n[1] > n[8]
    prev8 = f[(f["h"] == 8) & (f["origin"] < o) & (pd.to_datetime(f["outcome_known_from"]) > o)]
    assert len(prev8) >= 6


def test_evaluate_reports_n_per_h(frames):
    e = horizon.evaluate(frames["capex"], horizon.CAPEX)
    assert set(e) == set(horizon.HORIZONS)
    assert e[1]["baselines"]["n"] >= e[8]["baselines"]["n"] > 0
    assert e[1]["kedja"]["n"] > 0
    assert "B2" in e[1]["baselines"]["metrics"]
    md = horizon.markdown({"capex": {"eval": e}})
    assert "| 8 |" in md


# ------------------------------------------------------------------ holdout


def test_holdout_guard_raises_for_d2_even_when_c3_is_open(table, monkeypatch):
    t = horizon.prepare(table)
    with pytest.raises(guard.HoldoutClosed):
        horizon.forecast(t, horizon.CAPEX, "2025-07-20")
    with pytest.raises(guard.HoldoutClosed):
        horizon.run(table, horizon.CLOUD, end="2025-12-31")
    monkeypatch.setattr(guard, "HOLDOUT_OPEN", True)  # opening C3 does not open D2
    with pytest.raises(guard.HoldoutClosed):
        horizon.forecast(t, horizon.CLOUD, "2025-07-20")
    horizon.forecast(t, horizon.CAPEX, "2025-04-20")  # the last development origin is allowed
    monkeypatch.setattr(guard, "OPEN_FAMILIES", frozenset({"D2"}))
    horizon.forecast(t, horizon.CAPEX, "2025-07-20")


def test_development_run_reads_nothing_known_after_dev_end(table, frames):
    late = _rows(n1.TARGET, pd.period_range("2022Q1", "2025Q4", freq=Q), np.full(16, 1e9),
                 [TS("2025-07-02")] * 16)
    f = horizon.run(pd.concat([table, late], ignore_index=True), horizon.CAPEX)
    assert (pd.to_datetime(f["outcome_known_from"]) <= guard.DEV_END).all()
    assert (f["origin"] <= guard.DEV_END).all()
    pd.testing.assert_frame_equal(f, frames["capex"])
