"""Review R16 (docs/granskning/r16_n7.md): independent checks of N7's backtest (track P3, nowcast/n7.py).

Synthetic fixtures, no network. The real-data checks (marked real_data) skip unless the depreciation series are in
the default table.

Properties that hold (passing):
- An independent re-implementation of B0, B1, V1 and V2 from the register text gives the same levels as
  n7.forecast on a noisy synthetic table (all h, several origins).
- V1: ties in the in-sample MAE go to the smaller N; candidates are compared on the largest candidate's rows.
- Future capex starts after the company's own latest capex quarter Lc (a known capex(L + 1) is used, not B1's path).
- V2: J = round(4 N), so a stated life of 5.5 years gives J = 22.
- B1's break window is L-3 .. L (growths ending there), and only breaks filed on or before the origin count.
- group_dm: no test when the HLN term is <= 0 (T = 8 with h_max = 8).
- evaluate: an untestable test enters Holm with p = 1, and the family has six members in each period.
- decide: N7 (the sum) decides a group once it has >= 8 origins in both periods; otherwise N7b.
- Real data: forecasts from the table cut at the origin equal those from the full table.

Confirmed defect (strict xfail, flips when fixed):
- R16-S1: docs/resultat/n7.md explains V1's over-forecast with MSFT's "other" (which raises the 2024Q4-2025Q3
  outcomes and gives an under-forecast) and leaves out Meta's amortization of intangible assets (38 % of Meta's D&A
  in 2015, 2 % in 2022, SEC 10-K). See R-1 in the review.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ai_tracker import config, observations
from ai_tracker.nowcast import engine, n1, n7, quarterly
from conftest import real_table_exists

TS = pd.Timestamp
Q = "Q-DEC"
QS = pd.period_range("2008Q1", "2024Q4", freq=Q)
ENDS = QS.end_time.normalize()


def _rows(series, periods, values, known_from):
    return pd.DataFrame({"series": series, "freq": "Q", "period": [str(p) for p in periods],
                         "value": np.asarray(values, dtype=float), "known_from": pd.to_datetime(list(known_from)),
                         "source": "release", "fetched_at": TS("2026-11-24")})


def noisy_table(seed=7) -> pd.DataFrame:
    """Capex with noisy growth; depreciation = a drifting ratio x a 16-quarter mean of capex x noise, so no N fits
    exactly. Server lives step from 4 to 6 years. One revision of dep_meta (a later vintage)."""
    rng = np.random.default_rng(seed)
    parts = []
    for i, c in enumerate(n7.COMPANIES):
        x = 500 * (i + 1) * np.exp(np.cumsum(0.03 + 0.08 * rng.standard_normal(len(QS))))
        kf = ENDS + pd.Timedelta(days=24 + 3 * i)
        parts.append(_rows(f"capex_{c}", QS, x, kf))
        ratio = 1.1 * np.exp(-0.004 * np.arange(len(QS)))
        d = np.full(len(QS), np.nan)
        for k in range(16, len(QS)):
            d[k] = ratio[k] * x[k - 16:k].mean() * math.exp(0.05 * rng.standard_normal())
        ok = ~np.isnan(d)
        parts.append(_rows(f"dep_{c}", QS[ok], d[ok], kf[ok]))
        parts.append(_rows(f"useful_life_servers_{c}_hi", [QS[40], QS[56]], [4.0, 6.0 if i != 3 else 5.5],
                           [TS("2018-02-01"), TS("2022-02-01")]))
    late = _rows("dep_meta", [QS[50]], [1.0], [TS("2023-06-01")])  # a later vintage of 2020Q3
    late["value"] = parts[-2].loc[parts[-2]["period"] == str(QS[50]), "value"].to_numpy() * 1.01
    return pd.concat([*parts, late], ignore_index=True)


@pytest.fixture(scope="module")
def table():
    return noisy_table()


# ------------------------------------------------------------------ independent re-implementation (register text)


def _asof(t, series, origin):
    r = t[(t["series"] == series) & (t["known_from"] <= origin)].sort_values("known_from")
    s = r.groupby("period")["value"].last()
    s.index = pd.PeriodIndex(s.index, freq=Q)
    return s.sort_index()


def _b1_level(y, k):
    last = y.index.max()
    lv = [y.get(last - i, np.nan) for i in range(4, -1, -1)]
    if not all(v > 0 for v in lv):
        return float("nan")
    return float(y[last] * math.exp(k * np.mean(np.diff(np.log(lv)))))


def _mean_lags(cx, t, J):
    v = [cx.get(t - j, np.nan) for j in range(1, J + 1)]
    return float(np.mean(v)) if all(x > 0 for x in v) else float("nan")


def _fit(y, cx, J):
    rows = [(v, _mean_lags(cx, t, J), t) for t, v in y.items() if v > 0]
    rows = [r for r in rows if np.isfinite(r[1]) and r[1] > 0]
    ys, ms = np.array([r[0] for r in rows]), np.array([r[1] for r in rows])
    return rows, (float(ys @ ms / (ms @ ms)) if len(rows) else float("nan"))


def independent(t, company, origin) -> dict:
    """B0, B1, V1 and V2 levels for one company at `origin`, written from the register entry only."""
    y = _asof(t, f"dep_{company}", origin)
    y = y[y > 0]
    L = y.index.max()
    out = {"B0": {h: float(y[L]) for h in n7.HORIZONS}, "B1": {h: _b1_level(y, h) for h in n7.HORIZONS}}
    cx = _asof(t, f"capex_{company}", origin)
    cx = cx[cx > 0]
    lc = cx.index.max()
    ext = cx.to_dict()
    for k in range(1, (L + 7 - lc).n + 1):
        ext[lc + k] = _b1_level(cx, k)
    cand = {}
    for N in n7.GRID:
        rows, _ = _fit(y, cx.to_dict(), 4 * N)
        if len(rows) >= n7.MIN_TRAIN:
            cand[N] = rows
    if cand:
        common = {r[2] for r in cand[max(cand)]}
        mae = {}
        for N in sorted(cand):
            ys = np.array([r[0] for r in cand[N] if r[2] in common])
            ms = np.array([r[1] for r in cand[N] if r[2] in common])
            c = ys @ ms / (ms @ ms)
            mae[N] = float(np.mean(np.abs(100 * (np.log(c * ms) - np.log(ys)))))
        best = min(sorted(mae), key=lambda n: mae[n])
        _, c = _fit(y, cx.to_dict(), 4 * best)
        out["V1"] = {h: c * _mean_lags(ext, L + h, 4 * best) for h in n7.HORIZONS}
        out["N"] = best
    life = _asof(t, f"useful_life_servers_{company}_hi", origin)
    if len(life):
        J = int(round(4 * life[life.index.max()]))
        rows, c = _fit(y, cx.to_dict(), J)
        if len(rows) >= n7.MIN_TRAIN:
            out["V2"] = {h: c * _mean_lags(ext, L + h, J) for h in n7.HORIZONS}
    return out


@pytest.mark.parametrize("q", [QS[36], QS[44], QS[52], QS[60], QS[64]], ids=str)
@pytest.mark.parametrize("unit", n7.N7B, ids=lambda u: u.key)
def test_independent_reimplementation_matches_forecast(table, unit, q):
    origin = n1.origin_for(q)
    f = n7.forecast(n7.prepare(table), unit, origin, {})
    ref = independent(table, unit.companies[0], origin)
    for m in n7.MODELS:
        for h in n7.HORIZONS:
            a, b = f.levels[m][h], ref.get(m, {}).get(h, float("nan"))
            assert (math.isnan(a) and math.isnan(b)) or a == pytest.approx(b, rel=1e-12), (m, h)
    if "V1" in f.fits:
        assert f.fits["V1"].N == ref["N"]


# ------------------------------------------------------------------ V1 and V2 details


def test_v1_ties_go_to_the_smaller_n():
    qs = pd.period_range("2000Q1", "2012Q4", freq=Q)
    capex = {"msft": n7.Capex.from_series(pd.Series(100.0, index=qs))}
    y = pd.Series(90.0, index=qs[40:])  # constant capex: every N has the same m(t) and fits equally well
    fit = n7.select_v1(y, capex)
    assert sorted(fit.maes) == list(n7.GRID)
    assert len(set(fit.maes.values())) == 1
    assert fit.N == 3.0 and fit.J == {"msft": 12}


def test_v1_candidates_are_compared_on_the_largest_candidates_rows(table):
    origin = n1.origin_for(QS[60])
    info = engine.InfoSet(n7.prepare(table), origin)
    y = info.get("dep_meta")
    capex = {"meta": n7.Capex.from_series(info.get("capex_meta"))}
    fit = n7.select_v1(y, capex)
    largest = max(fit.maes)
    _, _, q_big = n7.training_rows(y, capex, {"meta": 4 * largest})
    for N, mae in fit.maes.items():
        ys, ms, qs = n7.training_rows(y, capex, {"meta": 4 * N})
        keep = np.array([q in set(q_big) for q in qs])
        assert keep.sum() == len(q_big)
        c = n7.fit_c(ys[keep], ms[keep])
        assert mae == pytest.approx(n7.in_sample_mae(ys[keep], ms[keep], c), rel=1e-12)
    ys, ms, _ = n7.training_rows(y, capex, fit.J)
    assert fit.c == pytest.approx(n7.fit_c(ys, ms), rel=1e-12) and fit.n_train == len(ys)  # refitted on all rows


def test_future_capex_starts_after_the_latest_known_capex_quarter(table):
    """Depreciation of the latest quarter not filed yet (L = Lc - 1): capex(L + 1) is the known value."""
    q = QS[56]
    origin = n1.origin_for(q)
    t = table[~((table["series"] == "dep_googl") & (table["period"] == str(q - 1)))]
    f = n7.forecast(n7.prepare(t), n7.N7B[1], origin, {})
    assert f.base == q - 2 and f.capex_last["googl"] == str(q - 1)
    cx = engine.InfoSet(n7.prepare(t), origin).get("capex_googl")
    fit = f.fits["V1"]
    J = fit.J["googl"]
    # h = 2 (target q): capex q-J .. q-1, all known, the last one is Lc = L + 1
    assert f.levels["V1"][2] == pytest.approx(fit.c * cx[pd.period_range(q - J, q - 1, freq=Q)].mean(), rel=1e-12)
    # h = 3 (target q + 1): capex q-J+1 .. q-1 known, capex(q) from B1's path one quarter after Lc
    path = n1.b1_path(cx[cx > 0], [q])
    known = cx[pd.period_range(q - J + 1, q - 1, freq=Q)].sum()
    assert f.levels["V1"][3] == pytest.approx(fit.c * (known + path[q]) / J, rel=1e-12)


def test_v2_rounds_four_times_a_half_year_life(table):
    f = n7.forecast(n7.prepare(table), n7.N7B[3], n1.origin_for(QS[60]), {})  # meta: 5.5 years from 2022
    assert f.fits["V2"].J == {"meta": 22}


@pytest.mark.parametrize("offset,known,blocked", [(4, True, False), (3, True, True), (0, True, True),
                                                   (0, False, False)])
def test_b1_break_window_is_l_minus_3_to_l(table, offset, known, blocked):
    origin = n1.origin_for(QS[60])
    p = n7.prepare(table)
    L = n7.forecast(p, n7.N7B[0], origin, {}).base
    filed = origin - pd.Timedelta(days=30) if known else origin + pd.Timedelta(days=1)
    f = n7.forecast(p, n7.N7B[0], origin, {L - offset: (filed, "synthetic break")})
    assert math.isnan(f.levels["B1"][1]) == blocked


# ------------------------------------------------------------------ test and decision


def test_group_dm_hln_term_zero_means_no_test():
    o = pd.date_range("2020-01-20", periods=8, freq="QS-JAN") + pd.Timedelta(days=19)
    rng = np.random.default_rng(5)
    rows = pd.DataFrame({"origin": np.repeat(o, 4), "a": rng.normal(0, 1, 32), "b": rng.normal(0, 2, 32)})
    r = n7.group_dm(rows, "a", "b", h_max=8)  # (T + 1 - 2h + h(h - 1)/T) / T = (9 - 16 + 7) / 8 = 0
    assert not r.testable and math.isnan(r.p) and "HLN" in r.note
    assert n7.group_dm(rows, "a", "b", h_max=4).testable


def _frame(unit, start, T, seed, v2_until=None, v1_sd=1.0):
    rng = np.random.default_rng(seed)
    o = pd.date_range(start, periods=T, freq="QS-JAN") + pd.Timedelta(days=19)
    rows = []
    for origin in o:
        for h in n7.HORIZONS:
            rows.append({"unit": unit, "origin": origin, "h": h, "in_period": True,
                         "outcome_known_from": origin + pd.Timedelta(days=95 * h),
                         "B0": rng.normal(0, 6), "B1": rng.normal(0, 6), "V1": rng.normal(0, v1_sd),
                         "V2": rng.normal(0, 1) if v2_until is None or origin < TS(v2_until) else np.nan})
    return pd.DataFrame(rows)


def test_untestable_tests_enter_holm_with_p_one():
    f = _frame("dep_meta", "2014-01-20", 50, 2, v2_until="2016-02-01")  # V2: 8 origins, none from 2023
    res = n7.evaluate(f)
    for per in n7.PERIODS:
        assert sum("holm_p" in res[per][g][v] for g in n7.GROUPS for v in n7.VARIANTS) == 6
    for g in n7.GROUPS:
        assert res["2023-"][g]["V2"]["n"] == 0 and res["2023-"][g]["V2"]["p_holm_input"] == 1.0
        assert res["full"][g]["V2"]["T"] == 8 and res["full"][g]["V2"]["dm"].testable is (g != "h5–8")


def test_the_sum_decides_once_it_has_eight_origins_in_both_periods():
    f7 = _frame("dep_hyp4", "2014-01-20", 50, 3)  # 50 origins, 14 of them from 2023-04-20
    fb = _frame("dep_meta", "2014-01-20", 50, 4, v1_sd=6.0)  # N7b: V1 no better
    res = {"N7": n7.evaluate(f7), "N7b": n7.evaluate(fb), "_frames": {"N7": f7, "N7b": fb}}
    d = n7.decide(res)
    for g in n7.GROUPS:
        assert d[g]["checks"]["V1"]["scope"] == "N7" and d[g]["checks"]["V1"]["passes"]
    short = f7[f7["origin"] < TS("2024-10-01")]  # 6 origins from 2023-04-20: N7b decides
    res = {"N7": n7.evaluate(short), "N7b": n7.evaluate(fb), "_frames": {"N7": short, "N7b": fb}}
    assert all(n7.decide(res)[g]["checks"]["V1"]["scope"] == "N7b" for g in n7.GROUPS)


# ------------------------------------------------------------------ real data (skipped without the series)


def needs_table(f):
    return pytest.mark.real_data(pytest.mark.skipif(not real_table_exists(), reason="no observation table")(f))


@pytest.fixture(scope="module")
def real():
    t = observations.load()
    t = t[t["series"].isin(n7.inputs())]
    missing = [s for s in (*n7.N7.dep, *n7.N7.capex) if not (t["series"] == s).any()]
    if missing:
        pytest.skip(f"not in the table: {', '.join(missing)}")
    return t


@needs_table
@pytest.mark.parametrize("origin", ["2016-10-20", "2019-07-20", "2021-04-20", "2023-01-20", "2024-10-20",
                                    "2025-04-20", "2026-07-20"])
def test_real_table_cut_at_the_origin_gives_the_same_forecasts(real, origin):
    origin = TS(origin)
    p = n7.prepare(real)
    for unit in (n7.N7, *n7.N7B):
        brk = quarterly.breaks(p, unit.aggregate)
        a = n7.forecast(p, unit, origin, brk)
        b = n7.forecast(n7.prepare(real[real["known_from"] <= origin]), unit, origin,
                        quarterly.known_breaks(brk, origin))
        for m in n7.MODELS:
            for h in n7.HORIZONS:
                x, y = a.levels[m][h], b.levels[m][h]
                assert (math.isnan(x) and math.isnan(y)) or x == y, (unit.key, m, h)


@needs_table
@pytest.mark.parametrize("company,origin", [("meta", "2021-04-20"), ("msft", "2023-01-20"), ("amzn", "2026-10-20"),
                                            ("googl", "2026-07-20")])
def test_real_independent_reimplementation(real, company, origin):
    origin = TS(origin)
    unit = next(u for u in n7.N7B if u.companies == (company,))
    f = n7.forecast(n7.prepare(real), unit, origin, {})
    ref = independent(real, company, origin)
    for m in n7.MODELS:
        for h in n7.HORIZONS:
            a, b = f.levels[m][h], ref.get(m, {}).get(h, float("nan"))
            assert (math.isnan(a) and math.isnan(b)) or a == pytest.approx(b, rel=1e-12), (m, h)


# ------------------------------------------------------------------ R16-S1 (results text)


def _bias_note() -> str:
    text = (config.REPO / "docs" / "resultat" / "n7.md").read_text(encoding="utf-8")
    start = text.index("- **V1 överskattar systematiskt")
    end = text.index("\n- **", start + 1)
    return text[start:end]


@pytest.mark.xfail(strict=True, reason="R16-S1: the bias note names MSFT 'other' as a cause of the over-forecast "
                                       "and leaves out Meta's amortization of intangible assets (R-1)")
def test_n7_bias_note_names_the_verified_causes():
    note = _bias_note()
    assert "immateriell" in note  # Meta: amortization of intangibles, 38 % of D&A 2015, 2 % 2022 (10-K)
    assert "nyttjandeperiod" in note
    if "other" in note:  # MSFT's 'other' raised the 2024Q4-2025Q3 outcomes: it works towards an under-forecast
        assert "underskatt" in note
