"""R1 independent leakage review: known_from against documented first publication, and the nowcast engines.

Release dates below were read from the sources themselves on 2026-11-23 (docs/granskning/r1_lackage.md):
- Census FT-900 press releases (census.gov/foreign-trade/Press-Release/ft900/ft900_YYMM.pdf, "FOR RELEASE ..."),
- Census C30 press releases (construction/c30/pdf/prYYYYMM.pdf) and the C30 notices page (pdf/news.pdf),
- BEA news release archive (GDP advance/initial estimates),
- EDGAR submissions (filingDate of the first 10-Q/10-K per quarter; TSMC 6-K filingDate),
- EIA Electricity Monthly Update archive ("Release Date").

Tests marked xfail(strict=True) demonstrate a real dating bug; they turn into failures once the bug is fixed,
so the fix must also remove the mark. Synthetic fixtures for the engine tests, no network.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from ai_tracker import catalog, observations, publication
from ai_tracker.nowcast import engine, n1
from ai_tracker.nowcast_n2 import backtest as n2_backtest
from ai_tracker.nowcast_n2 import engine as n2
from ai_tracker.sources import alfred

SPECS = catalog.by_key()  # importing the catalog registers every series module's LATE dates


def rule_known_from(key: str, period: str) -> pd.Timestamp:
    """known_from that the backfill rule (period end + lag, LATE) gives a period of a lag-dated series."""
    s = SPECS[key]
    return publication.known_from(key, observations.to_periods([period], s.freq), s.lag_days)[0]


def bug(reason: str):
    return pytest.mark.xfail(strict=True, reason=reason)


# ------------------------------------------------------------------ 1. lag-dated sources vs documented releases

FT900_2025_10 = ("FT-900 for October 2025 was released 2026-01-08 (ft900_2510.pdf); LATE lacks 2025-10 because "
                 "ALFRED's 2025-12-11 vintage carries a 0.0 placeholder for it, so known_from = 2025-12-11")
FT900_2013 = "2013 shutdown: FT-900 Aug/Sep 2013 released 2013-10-24 / 2013-11-14; no LATE before 2017-11"
FT900_PRE2013 = "FT-900 2006-2012 often came 42-45 days after month end; the 41-day lag is 1-4 days early"

FT900 = [  # (month, first release from the FT-900 press release)
    ("2025-06", "2025-08-05"), ("2025-07", "2025-09-04"), ("2025-08", "2025-11-19"), ("2025-09", "2025-12-11"),
    ("2025-11", "2026-01-29"), ("2025-12", "2026-02-19"), ("2026-01", "2026-03-12"), ("2026-02", "2026-04-02"),
    ("2026-04", "2026-06-09"), ("2018-11", "2019-02-06"), ("2018-12", "2019-03-06"), ("2019-01", "2019-03-27"),
    ("2019-02", "2019-04-17"), ("2020-02", "2020-04-02"), ("2020-03", "2020-05-05"), ("2017-11", "2018-01-05"),
    ("2016-12", "2017-02-07"), ("2015-11", "2016-01-06"), ("2014-12", "2015-02-05"), ("2013-07", "2013-09-04"),
    ("2013-10", "2013-12-04"), ("2013-11", "2014-01-07"), ("2013-12", "2014-02-06"),
    pytest.param("2025-10", "2026-01-08", marks=bug(FT900_2025_10)),
    pytest.param("2013-08", "2013-10-24", marks=bug(FT900_2013)),
    pytest.param("2013-09", "2013-11-14", marks=bug(FT900_2013)),
    pytest.param("2007-12", "2008-02-14", marks=bug(FT900_PRE2013)),
    pytest.param("2007-06", "2007-08-14", marks=bug(FT900_PRE2013)),
]


@pytest.mark.parametrize("key", ["us_imports_tw_m", "us_imports_kr_m"])
@pytest.mark.parametrize("month,released", FT900)
def test_ft900_known_from_not_before_release(key, month, released):
    assert rule_known_from(key, month) >= pd.Timestamp(released)


C30_CATEGORY = ("C30 'Data center' was first published separately 2024-07-01 (May 2024 release, back to 2014-01; "
                "notice in pr202403/pr202404/pr202405.pdf and pdf/news.pdf); the backfill dates 2014-01..2024-04 "
                "at month end + 35 days, before the series existed")
C30 = [  # (month, first release of the Data center value)
    ("2025-08", "2025-11-17"), ("2025-09", "2026-01-21"), ("2025-10", "2026-01-21"), ("2025-11", "2026-02-27"),
    ("2025-12", "2026-02-27"), ("2026-01", "2026-03-23"), ("2026-02", "2026-05-07"), ("2026-03", "2026-05-07"),
    ("2025-07", "2025-09-02"), ("2024-05", "2024-07-01"), ("2024-06", "2024-08-01"),
    pytest.param("2014-01", "2024-07-01", marks=bug(C30_CATEGORY)),
    pytest.param("2019-06", "2024-07-01", marks=bug(C30_CATEGORY)),
    pytest.param("2021-12", "2024-07-01", marks=bug(C30_CATEGORY)),
    pytest.param("2023-12", "2024-07-01", marks=bug(C30_CATEGORY)),
    pytest.param("2024-04", "2024-07-01", marks=bug(C30_CATEGORY)),
]


@pytest.mark.parametrize("key", ["us_constr_datacenter", "us_constr_datacenter_nsa"])
@pytest.mark.parametrize("month,released", C30)
def test_c30_datacenter_known_from_not_before_release(key, month, released):
    assert rule_known_from(key, month) >= pd.Timestamp(released)


BEA = [("2024Q4", "2025-01-30"), ("2025Q1", "2025-04-30"), ("2025Q2", "2025-07-30"), ("2025Q3", "2025-12-23"),
       ("2025Q4", "2026-02-20"), ("2026Q1", "2026-04-30"), ("2026Q2", "2026-07-30")]


@pytest.mark.parametrize("quarter,released", BEA)
def test_bea_known_from_not_before_advance_estimate(quarter, released):
    for key in ("us_pfi_info_proc_eq_sw", "us_pfi_info_proc_eq", "us_pfi_computers", "us_pfi_software"):
        assert rule_known_from(key, quarter) >= pd.Timestamp(released)


# ------------------------------------------------------------------ 2. ALFRED as release evidence


@bug("alfred.first_release / release_rows treat a 0.0 placeholder as a published value "
     "(IMP5830, vintage 2025-12-11 has October 2025 = 0.0; the real value came 2026-01-08)")
def test_alfred_zero_placeholder_is_not_a_release():
    idx = pd.to_datetime(["2025-09-01", "2025-10-01"])
    wide = pd.DataFrame({pd.Timestamp("2025-12-11"): [14991.3, 0.0],
                         pd.Timestamp("2026-01-08"): [14991.3, 22252.7]}, index=idx)
    assert alfred.first_release(wide)[pd.Timestamp("2025-10-01")] == pd.Timestamp("2026-01-08")
    rows = alfred.release_rows(wide)
    assert not (rows["value"] == 0).any()


# ------------------------------------------------------------------ 3. later fetches of lag-dated sources


def _spec(key="s", lag=35):
    return catalog.Spec(key=key, branch="G5", label="x", unit="x", freq="M", source="x", fetch=lambda: None,
                        lag_days=lag, license="unverified")


def test_lag_rule_never_after_fetch_on_later_fetches():
    """Sanity of the existing rule: a later fetch never dates a new period after the fetch day."""
    spec = _spec()
    first = observations.new_rows(spec, pd.Series([1.0], index=pd.PeriodIndex(["2026-01"], freq="M")),
                                  observations._empty(), fetched_at=pd.Timestamp("2026-03-10").date())
    s = pd.Series([1.0, 2.0], index=pd.PeriodIndex(["2026-01", "2026-02"], freq="M"))
    new = observations.new_rows(spec, s, first, fetched_at=pd.Timestamp("2026-04-01").date())
    assert new["known_from"].max() <= pd.Timestamp("2026-04-01")


@bug("observations.new_rows dates a new period min(period end + lag, fetch date) on later fetches, even when an "
     "earlier fetch (stored fetched_at) after that date did not contain the period: a delayed release that is "
     "not in LATE is back-dated (live runs only; today's table is a single fetch)")
def test_new_period_is_not_dated_before_a_fetch_that_did_not_have_it():
    spec = _spec()
    # Fetch on 2025-11-10 holds months up to 2025-08 only (September is late: it would be due 2025-11-04)
    s1 = pd.Series([1.0, 2.0], index=pd.PeriodIndex(["2025-07", "2025-08"], freq="M"))
    t1 = observations.new_rows(spec, s1, observations._empty(), fetched_at=pd.Timestamp("2025-11-10").date())
    # September appears in the next fetch (2026-01-25); it was provably not public on 2025-11-10
    s2 = pd.Series([1.0, 2.0, 3.0], index=pd.PeriodIndex(["2025-07", "2025-08", "2025-09"], freq="M"))
    t2 = observations.new_rows(spec, s2, t1, fetched_at=pd.Timestamp("2026-01-25").date())
    sep = t2[t2["period"] == "2025-09"]["known_from"].iloc[0]
    assert sep > pd.Timestamp("2025-11-10")


# ------------------------------------------------------------------ 4. the stored table (skipped without data)

needs_table = pytest.mark.skipif(not observations.PATH.exists(), reason="data/observations.parquet not built")


@pytest.fixture(scope="module")
def stored():
    return observations.load()


def _first_kf(t: pd.DataFrame, series: str, period: str) -> pd.Timestamp:
    s = t[(t["series"] == series) & (t["period"] == period)]
    assert not s.empty, f"{series} {period} missing"
    return s["known_from"].min()


# capex_hyp4 needs all four 10-Q/10-K: latest first filingDate among MSFT, GOOGL, AMZN, META (EDGAR submissions)
HYP4_FILED = {"2017Q4": "2018-02-06", "2020Q1": "2020-05-01", "2021Q4": "2022-02-04", "2023Q4": "2024-02-02",
              "2024Q4": "2025-02-07", "2025Q3": "2025-10-31", "2025Q4": "2026-02-06", "2026Q3": "2026-10-30"}
TSMC_6K = {"2008-01": "2008-02-14", "2012-12": "2013-01-10", "2013-01": "2013-02-08", "2020-01": "2020-02-10",
           "2025-09": "2025-10-09", "2025-10": "2025-11-10", "2025-12": "2026-01-09", "2026-10": "2026-11-10"}
EPM = {"2024-06": "2024-08-23", "2024-09": "2024-11-22", "2024-11": "2025-01-24", "2025-08": "2025-10-24",
       "2025-09": "2025-11-25", "2025-10": "2025-12-23", "2025-11": "2026-01-26", "2026-01": "2026-03-24",
       "2026-03": "2026-05-22", "2026-07": "2026-09-24"}


@needs_table
def test_stored_sec_and_tsmc_first_vintage_not_before_filing(stored):
    for q, filed in HYP4_FILED.items():
        assert _first_kf(stored, "capex_hyp4", q) >= pd.Timestamp(filed), q
    for m, filed in TSMC_6K.items():
        assert _first_kf(stored, "tsmc_revenue_m", m) >= pd.Timestamp(filed), m


@needs_table
def test_stored_eia_first_vintage_not_before_epm_release(stored):
    for m, released in EPM.items():
        for area in ("va", "tx", "ga", "az", "or", "oh"):
            assert _first_kf(stored, f"us_elec_sales_com_{area}_m", m) >= pd.Timestamp(released), (area, m)
        assert _first_kf(stored, "us_elec_sales_com_m", m) >= pd.Timestamp(released), m


# ------------------------------------------------------------------ 5. N1 engine


T1 = "capex_r1"
IMP, CON = n1.INDICATORS


def _rows(series, freq, periods, values, known_from, source="release"):
    return pd.DataFrame({"series": series, "freq": freq, "period": [str(p) for p in periods],
                         "value": np.asarray(values, dtype=float), "known_from": pd.to_datetime(known_from),
                         "source": source, "fetched_at": pd.Timestamp("2026-11-23")})


def n1_table(seed=3) -> pd.DataFrame:
    """Target with revisions and indicators with their own later vintages (revisions after the origin)."""
    rng = np.random.default_rng(seed)
    months = pd.period_range("2011-01", "2021-06", freq="M")
    parts, qmean = [], {}
    for key, lag in ((IMP, 41), (CON, 35)):
        lvl = 1000 * np.exp(np.cumsum(0.01 + 0.03 * rng.standard_normal(len(months))))
        kf = months.end_time.normalize() + pd.Timedelta(days=lag)
        parts.append(_rows(key, "M", months, lvl, kf, "backfill"))
        # a second vintage of every month, 120 days later and 2 % off: must only matter after it is known
        parts.append(_rows(key, "M", months, lvl * np.exp(0.02 * rng.standard_normal(len(months))),
                           kf + pd.Timedelta(days=120), "revision"))
        qmean[key] = pd.Series(np.log(lvl), index=months).groupby(months.asfreq("Q-DEC")).mean()
    quarters = pd.period_range("2012Q1", "2021Q1", freq="Q-DEC")
    g = 0.02 + 0.5 * qmean[IMP].diff() + 0.3 * qmean[CON].diff() + 0.02 * rng.standard_normal(len(qmean[IMP]))
    capex = 500 * np.exp(g.loc[quarters].cumsum())
    parts.append(_rows(T1, "Q", quarters, capex, quarters.end_time.normalize() + pd.Timedelta(days=28)))
    parts.append(_rows(T1, "Q", quarters, capex * 1.02, quarters.end_time.normalize() + pd.Timedelta(days=300)))
    return pd.concat(parts, ignore_index=True)


def poison_after(table: pd.DataFrame, origin: pd.Timestamp, factor: float = 37.0) -> pd.DataFrame:
    """Every row not yet known at `origin` gets an absurd value."""
    t = table.copy()
    later = t["known_from"] > origin
    t.loc[later, "value"] = t.loc[later, "value"] * factor
    return t


@pytest.fixture(scope="module")
def t1():
    return n1_table()


@pytest.fixture(scope="module")
def bt1(t1):
    return n1.backtest_unit(t1, T1)


def test_n1_every_backtest_forecast_is_blind_to_rows_after_its_origin(t1, bt1):
    """The whole backtest path (target history, indicators, J positions, OLS, ridge standardisation, lambda CV):
    poisoning every row known after the origin leaves each scored forecast unchanged."""
    fv = engine.first_vintage(t1, T1)
    checked = 0
    for r in bt1.itertuples():
        origin = pd.Timestamp(r.origin)
        f = n1.forecast(engine.InfoSet(poison_after(t1, origin), origin), T1, r.quarter)
        for v in n1.VARIANTS:
            e = getattr(r, v)
            if math.isnan(e):
                assert math.isnan(f.levels[v])
                continue
            assert engine.log_error(f.levels[v], fv[r.quarter]) == pytest.approx(e, abs=1e-9), (r.quarter, v)
        checked += 1
    assert checked >= 20 and bt1["V2"].notna().sum() >= 10


def test_n1_sample_selection_does_not_depend_on_outcomes(t1, bt1):
    """Which quarters are scored (in_period, common sample, 'known at origin' exclusions) depends on what is
    available at each origin, never on the outcome values."""
    t = t1.copy()
    is_target = t["series"] == T1
    rng = np.random.default_rng(9)
    scale = {p: float(np.exp(rng.normal(0, 0.3))) for p in t.loc[is_target, "period"].unique()}
    t.loc[is_target, "value"] = t.loc[is_target, "value"] * t.loc[is_target, "period"].map(scale)
    other = n1.backtest_unit(t, T1)
    cols = ["quarter", "in_period"]
    pd.testing.assert_frame_equal(bt1[cols].reset_index(drop=True), other[cols].reset_index(drop=True))
    assert list(bt1.dropna(subset=n1.VARIANTS)["quarter"]) == list(other.dropna(subset=n1.VARIANTS)["quarter"])


def test_n1_indicator_revision_after_origin_changes_nothing_but_before_origin_does(t1):
    q = pd.Period("2019Q2", freq="Q-DEC")
    origin = n1.origin_for(q)
    base = n1.forecast(engine.InfoSet(t1, origin), T1, q)
    # a revision of a training-window month known one day after the origin: invisible
    late = _rows(CON, "M", [pd.Period("2018-05", "M")], [1e6], [origin + pd.Timedelta(days=1)], "revision")
    f_late = n1.forecast(engine.InfoSet(pd.concat([t1, late], ignore_index=True), origin), T1, q)
    assert f_late.levels["V1"] == base.levels["V1"] and f_late.lam == base.lam
    # the same revision known on the origin day is real-time information: it must move V1
    early = late.assign(known_from=origin)
    f_early = n1.forecast(engine.InfoSet(pd.concat([t1, early], ignore_index=True), origin), T1, q)
    assert f_early.levels["V1"] != base.levels["V1"]


# ------------------------------------------------------------------ 6. N2 engine


def n2_table(seed=4, outcome_day: int = 10) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    months = pd.period_range("2006-01", "2016-12", freq="M")
    imp = 7 + np.cumsum(rng.normal(0.005, 0.03, len(months)))
    ly = np.log(1e5) + np.cumsum(rng.normal(0.01, 0.04, len(months)))
    tsmc_kf = [(p + 1).start_time + pd.Timedelta(days=outcome_day - 1) for p in months]
    for i in range(60, len(months), 13):  # a few reports filed ~2.5 months late: not training rows until known
        tsmc_kf[i] += pd.Timedelta(days=75)
    imp_kf = months.end_time.normalize() + pd.Timedelta(days=41)
    parts = [_rows(n2.TARGET, "M", months, np.exp(ly), tsmc_kf),
             _rows(n2.TARGET, "M", months[::5], np.exp(ly[::5]) * 1.03,  # restated comparatives a year later
                   [(p + 13).start_time + pd.Timedelta(days=9) for p in months[::5]]),
             _rows("us_imports_tw_m", "M", months, np.exp(imp), imp_kf, "backfill"),
             _rows("us_imports_tw_m", "M", months, np.exp(imp + rng.normal(0, 0.01, len(months))),
                   imp_kf + pd.Timedelta(days=200), "revision")]
    return pd.concat(parts, ignore_index=True)


@pytest.fixture(scope="module")
def t2():
    return n2_table()


def test_n2_backtest_forecasts_are_blind_to_rows_after_their_origin(t2):
    """run() builds every month's inputs and V1 training rows from one full table; poisoning all rows known
    after a month's origin must leave that month's three forecasts (and lambda) unchanged."""
    t = n2.slim(t2)
    outcomes = n2.first_vintages(t)
    records = n2.build_records(t, outcomes.index.max())
    months = [m for m in sorted(records) if m in outcomes.index][-40::3]
    for m in months:
        f = n2.forecast_from(m, records, outcomes)
        p = poison_after(t, records[m].origin)
        fp = n2.forecast_from(m, n2.build_records(p, outcomes.index.max()), n2.first_vintages(p))
        for v in n2.VARIANTS:
            a, b = f.logs[v], fp.logs[v]
            assert (np.isnan(a) and np.isnan(b)) or a == pytest.approx(b, abs=1e-9), (m, v)
        assert f.n_train == fp.n_train and (f.lam == fp.lam or (np.isnan(f.lam) and np.isnan(fp.lam)))
    assert any(np.isfinite(n2.forecast_from(m, records, outcomes).logs["V1"]) for m in months)


def test_n2_sample_selection_does_not_depend_on_outcomes(t2):
    t = t2.copy()
    is_target = t["series"] == n2.TARGET
    rng = np.random.default_rng(2)
    scale = {p: float(np.exp(rng.normal(0, 0.2))) for p in t.loc[is_target, "period"].unique()}
    t.loc[is_target, "value"] = t.loc[is_target, "value"] * t.loc[is_target, "period"].map(scale)
    a, b = n2_backtest.run(t2), n2_backtest.run(t)
    ok = lambda f: f[[c for c in f if c.startswith("e_")]].notna().all(axis=1) & (f["n_train"] >= n2.MIN_TRAIN)  # noqa: E731
    assert list(a.index[ok(a)]) == list(b.index[ok(b)])
    assert (a["n_train"] == b["n_train"]).all()


@bug("latent: N2 backtest.run() scores months whose outcome is already known at the origin (N1 skips them); "
     "0 such months in the current data because the earliest 6-K is day 6")
def test_n2_month_with_outcome_known_at_origin_is_not_scored():
    t = n2_table(outcome_day=5)  # every 6-K filed on day 5 = the origin day: known at the origin
    frame = n2_backtest.run(t)
    assert (frame["outcome_known_from"] > frame["origin"]).all()
