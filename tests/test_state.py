"""Tests for branch states (register sections 1, 2, 5): measures, deadband, diffusion, regimes, ratio, leakage, writer."""

from __future__ import annotations

import json
import math
import subprocess

import numpy as np
import pandas as pd
import pytest

from ai_tracker import catalog, observations, pipeline
from ai_tracker.state import branch as B
from ai_tracker.state import measures as M
from ai_tracker.state import register as R
from ai_tracker.state import snapshot as S

FETCHED = pd.Timestamp("2026-11-23")


def spec(key, unit="MUSD", freq="M", branch="G6"):
    return catalog.Spec(key=key, branch=branch, label=key, unit=unit, freq=freq, source="test",
                        fetch=lambda: pd.Series(dtype=float), lag_days=0, license="unverified")


def rows(key, freq, periods, values, known_from=None, lag_days=10, source="release"):
    """Observation rows; known_from defaults to period end + lag_days."""
    pi = observations.to_periods(periods, freq)
    kf = (pd.DatetimeIndex(known_from) if known_from is not None
          else pd.DatetimeIndex(pi.end_time.normalize()) + pd.Timedelta(days=lag_days))
    return pd.DataFrame({"series": key, "freq": freq, "period": [str(p) for p in pi], "value": np.asarray(values, float),
                         "known_from": kf, "source": source, "fetched_at": FETCHED})


def monthly_rows(key, values, start="2015-01", **kw):
    return rows(key, "M", pd.period_range(start, periods=len(values), freq="M"), values, **kw)


def quarterly_rows(key, values, start="2010Q1", **kw):
    return rows(key, "Q", pd.period_range(start, periods=len(values), freq="Q"), values, **kw)


def ctx_for(table, specs, core=None, tmp_path=None, derived=None):
    return M.Context(pd.concat(table, ignore_index=True) if isinstance(table, list) else table,
                     specs={s.key: s for s in specs}, core=core or {}, derived=derived or {},
                     forecasts=tmp_path or M.config.REPO / "no-forecasts-here")


# ------------------------------------------------------------------ register mirror


def test_core_series_mirror_the_register_file():
    parsed = R.parse_register()
    assert parsed == {b: v for b, v in R.CORE_SERIES.items() if v}
    assert set(R.CORE_SERIES) == set(catalog.BRANCHES)


def test_register_parser_takes_later_tables_and_ignores_other_tables(tmp_path):
    f = tmp_path / "r.md"
    f.write_text("| Mått | Definition |\n|---|---|\n| G1 | `x` |\n\n"
                 "| Gren | Kärnserier | Anm |\n|---|---|---|\n| G2 | `a`, `b_{x,y}` | |\n\ntext\n\n"
                 "| Gren | Kärnserier | Anm |\n|---|---|---|\n| G1 | `bench_<aktiv regim>` | `not_this` |\n",
                 encoding="utf-8")
    assert R.parse_register(f) == {"G2": ["a", "b_{x,y}"], "G1": ["bench_<aktiv regim>"]}


def test_expand_braces():
    assert R.expand("us_elec_sales_com_{va,tx}_m") == ["us_elec_sales_com_va_m", "us_elec_sales_com_tx_m"]
    assert R.expand("rev_msft") == ["rev_msft"]
    assert len(R.core_entries("G8")) == 9 and len(R.core_entries("G7")) == 6


def test_every_registered_core_series_exists_and_has_the_registered_method():
    ctx = M.Context(observations._empty())
    expected = {"g2_price_at_capability_gpqa": "halving", "eu_ai_ent_se": "share", "rev_nvda": "log",
                "g1_epoch_bench_frontier_spireclimb": "logit", "g1_epoch_train_compute_frontier": "doubling",
                "g1_epoch_eci_frontier": "doubling", "g9_epoch_open_weights_share": "share",
                "g9_epoch_notable_models": "log", "g9_arxiv_cs_lg": "log",
                "capex_hyp4": "log", "capex_ocf_hyp4": "share", "us_imports_kr_m": "log",
                "us_elec_sales_com_oh_m": "log", "ai_postings_share_nl_d": "share", "btos_ai_use_v1": "share"}
    for key, method in expected.items():
        assert M.rule_for(key, ctx).method == method, key
    for code in catalog.BRANCHES:
        for entry in R.core_entries(code):
            if R.REGIME_PLACEHOLDER in entry:
                continue
            for key in ([entry.replace(R.SELECTED_PLACEHOLDER, b) for b in ctx.selection(pd.Timestamp("2026-11-30"))]
                        if R.SELECTED_PLACEHOLDER in entry else [entry]):
                M.rule_for(key, ctx)  # raises if neither catalogued nor derived
    assert M.rule_for("ai_postings_share_us_d", ctx).agg == "mean"


def test_rule_defaults_from_unit_and_branch():
    c = ctx_for(observations._empty(), [spec("bench", unit="andel 0–1", branch="G1"),
                                        spec("compute", unit="FLOP", branch="G1"),
                                        spec("flow_d", unit="MUSD", freq="D"),
                                        spec("price_d", unit="USD per MWh", freq="D")])
    assert M.rule_for("bench", c).method == "logit"
    assert M.rule_for("compute", c).method == "doubling"
    assert M.rule_for("flow_d", c).agg == "sum"
    assert M.rule_for("price_d", c).agg == "mean"


# ------------------------------------------------------------------ measures: log, share, annual, percentiles


def test_log_pace_change_and_percentiles_monthly():
    g = np.r_[np.full(30, 0.01), np.full(12, 0.02)]  # monthly log growth 1 %, then 2 %
    x = 100 * np.exp(np.cumsum(g))
    c = ctx_for([monthly_rows("x", x)], [spec("x")])
    when = pd.Period("2018-06", "M").end_time.normalize() + pd.Timedelta(days=10)
    m = M.measure("x", when, c)
    assert m["latest_period"] == "2018-06"
    assert m["pace"] == pytest.approx(100 * 12 * 0.02)
    # pace now (24) minus pace six months earlier: 6 months at 2 % + 6 at 1 % -> 18
    assert m["change_in_pace"] == pytest.approx(24 - 18)
    # 42 months -> 30 pace values (the last one is the unique maximum) and 24 change values
    assert m["n_pace"] == 30 and m["pace_percentile"] == pytest.approx(100 * (29 + 0.5) / 30)
    assert m["n_change"] == 24 and m["change_percentile"] is not None
    assert m["valid"] and m["direction"] == 1


def test_percentile_needs_minimum_history_and_counts_ties_half():
    assert M.percentile(5.0, np.arange(23, dtype=float), 24) is None
    assert M.percentile(5.0, np.r_[np.arange(23, dtype=float), np.nan], 24) is None
    assert M.percentile(1.0, np.array([0.0, 1.0, 1.0, 2.0]), 4) == pytest.approx(50.0)


def test_share_pace_is_pp_change_and_quarterly_lags():
    v = np.arange(20, dtype=float) ** 2 / 10  # a share in percent
    c = ctx_for([quarterly_rows("s", v)], [spec("s", unit="% av företag", freq="Q")])
    m = M.measure("s", "2015-01-31", c)
    assert m["latest_period"] == "2014Q4" and m["method"] == "share"
    assert m["pace"] == pytest.approx(v[19] - v[15])
    assert m["change_in_pace"] == pytest.approx((v[19] - v[15]) - (v[17] - v[13]))
    assert m["pace_percentile"] is not None  # 16 pace values >= 8 quarters


def test_annual_series_needs_two_change_values_for_a_direction():
    v = [10.0, 25.0, 35.0]
    c = ctx_for([rows("a", "A", pd.period_range("2023", periods=3, freq="Y"), v)],
                [spec("a", unit="% av företag", freq="A")])
    m = M.measure("a", "2026-06-30", c)
    assert m["pace"] == 10.0 and m["change_in_pace"] == -5.0
    assert m["sd_change"] is None and not m["valid"] and "standardavvikelse" in m["reason"]
    assert m["pace_percentile"] is None  # < 5 years


def test_no_fallback_to_an_older_period_when_the_latest_has_no_change():
    x = list(100 * np.exp(0.01 * np.arange(40)))
    x[33] = np.nan  # gap 6 months before the end: change in pace undefined at the latest month
    t = monthly_rows("x", x).dropna(subset=["value"])
    m = M.measure("x", "2030-01-01", ctx_for([t], [spec("x")]))
    assert m["pace"] is not None and m["change_in_pace"] is None and not m["valid"]


# ------------------------------------------------------------------ monthly aggregation


def test_daily_share_is_averaged_and_the_last_month_is_dropped():
    days = pd.period_range("2024-01-01", "2024-03-10", freq="D")
    v = np.where(days.month == 1, 2.0, np.where(days.month == 2, 4.0, 9.0))
    c = ctx_for([rows("d", "D", days, v, lag_days=0)], [spec("d", unit="% av annonserna", freq="D")])
    s = M.to_monthly(observations.as_of("d", "2024-03-31", c.rows("d")), "mean")
    assert list(s.index.astype(str)) == ["2024-01", "2024-02"] and list(s) == [2.0, 4.0]
    m = M.measure("d", "2024-03-31", c)
    assert m["latest_period"] == "2024-02" and m["obs_in_latest_period"] == 29


def test_daily_flow_is_summed():
    days = pd.period_range("2024-01-01", "2024-02-02", freq="D")
    s = pd.Series(1.0, index=days)
    assert M.to_monthly(s, "sum").iloc[0] == 31.0


def test_fortnights_go_to_the_month_they_end_in():
    weeks = pd.PeriodIndex(["2025-08-18/2025-08-24", "2025-09-01/2025-09-07", "2025-09-29/2025-10-05",
                            "2025-10-13/2025-10-19"], freq="W-SUN")
    s = pd.Series([1.0, 2.0, 4.0, 8.0], index=weeks)
    out = M.to_monthly(s, "mean")
    assert dict(zip(out.index.astype(str), out)) == {"2025-08": 1.0, "2025-09": 2.0}  # Oct still filling


# ------------------------------------------------------------------ doubling / halving time, logit


def test_halving_time_from_24_months_and_sign_of_direction():
    # price halves every 6 months for 30 months, then every 4 months for 18 months
    lg = np.r_[np.full(30, -math.log(2) / 6), np.full(18, -math.log(2) / 4)]
    price = 10 * np.exp(np.cumsum(lg))
    c = ctx_for([monthly_rows("p", price, start="2020-01")], [spec("p", unit="USD per 1M tokens", branch="G2")])
    m = M.measure("p", "2024-01-31", c)
    assert m["method"] == "halving" and m["latest_period"] == "2023-12"
    # the last 24 months mix 6 months at 6-month halving and 18 at 4-month: the OLS slope decides
    y = np.log(price[-24:])
    slope = np.polyfit(np.arange(24), y, 1)[0]
    assert m["pace"] == pytest.approx(math.log(2) / -slope)
    assert m["change_in_pace"] < 0 and m["direction"] == 1  # shorter halving time = accelerating
    assert m["direction_sign"] == -1


def test_halving_time_needs_24_months():
    price = 10 * np.exp(-0.1 * np.arange(23))
    c = ctx_for([monthly_rows("p", price)], [spec("p", unit="USD per 1M tokens", branch="G2")])
    m = M.measure("p", "2030-01-01", c)
    assert m["pace"] is None and not m["valid"]


def test_halving_uses_the_front_and_wrong_sign_gives_no_time():
    y = pd.Series(np.log([4.0, 2.0, 3.0, 1.0]))
    assert list(M.rolling_time(y, 4, "doubling").isna()) == [True] * 4  # falling series: no doubling time
    rising = pd.Series(np.log(np.arange(1, 25, dtype=float)))
    assert math.isnan(M.rolling_time(rising, 24, "halving").iloc[-1])
    price = np.r_[10 * np.exp(-0.1 * np.arange(24)), [50.0]]  # last month: price jumps up; front stays
    c = ctx_for([monthly_rows("p", price)], [spec("p", unit="USD per 1M tokens", branch="G2")])
    m = M.measure("p", "2030-01-01", c)
    assert m["level"] == 50.0 and m["pace"] is not None  # front = running min, so the jump is ignored


def test_logit_on_running_max_of_bounded_score():
    v = np.r_[np.linspace(0.2, 0.6, 30), [0.1]]
    c = ctx_for([monthly_rows("b", v)], [spec("b", unit="andel 0-1", branch="G1")])
    m = M.measure("b", "2030-01-01", c)
    front = np.maximum.accumulate(v)
    lg = np.log(front / (1 - front))
    assert m["method"] == "logit" and m["pace"] == pytest.approx(lg[-1] - lg[-13])


# ------------------------------------------------------------------ deadband, diffusion, state


def test_deadband_is_quarter_of_expanding_sd():
    rng = np.random.default_rng(1)
    x = 100 * np.exp(np.cumsum(0.01 + 0.02 * rng.standard_normal(60)))
    c = ctx_for([monthly_rows("x", x)], [spec("x")])
    m = M.measure("x", "2030-01-01", c)
    y = 100 * np.log(x)
    pace = y[12:] - y[:-12]
    change = pace[6:] - pace[:-6]
    assert m["change_in_pace"] == pytest.approx(change[-1])
    assert m["sd_change"] == pytest.approx(np.std(change, ddof=1))
    assert m["deadband"] == pytest.approx(0.25 * np.std(change, ddof=1))
    expected = 1 if change[-1] > m["deadband"] else -1 if change[-1] < -m["deadband"] else 0
    assert m["direction"] == expected


def test_direction_neutral_inside_band_and_signed_outside(monkeypatch):
    rng = np.random.default_rng(7)
    base = 100 * np.exp(np.cumsum(0.01 + 0.02 * rng.standard_normal(60)))
    c = ctx_for([monthly_rows("x", base)], [spec("x")])
    m = M.measure("x", "2030-01-01", c)
    chg = m["change_in_pace"]
    monkeypatch.setattr(R, "DEADBAND", abs(chg) / m["sd_change"] * 1.0001)  # band just wider than |change|
    assert M.measure("x", "2030-01-01", c)["direction"] == 0
    monkeypatch.setattr(R, "DEADBAND", abs(chg) / m["sd_change"] * 0.9999)
    assert M.measure("x", "2030-01-01", c)["direction"] == (1 if chg > 0 else -1)


def test_diffusion_index_and_state_thresholds():
    assert B.diffusion([1, 1, 0]) == pytest.approx(2.5 / 3)
    assert B.diffusion([1, -1]) == 0.5 and B.diffusion([]) is None
    assert B.state_of(0.67, 3) == R.STATE_ACCEL
    assert B.state_of(2 / 3, 3) == R.STATE_STABLE  # unrounded: 0.6667 < 0.67
    assert B.state_of(0.33, 3) == R.STATE_BRAKE
    assert B.state_of(1 / 3, 3) == R.STATE_STABLE  # 0.3333 > 0.33
    assert B.state_of(1.0, 2) == R.STATE_FEW and B.state_of(None, 0) == R.STATE_FEW


def _trend(key, acc):
    """Monthly series with steady growth and a final acceleration (+), deceleration (-) or none (0)."""
    rng = np.random.default_rng(abs(hash(key)) % 2**32)
    g = 0.01 + 0.002 * rng.standard_normal(60)
    g[-6:] += 0.01 * acc
    return monthly_rows(key, 100 * np.exp(np.cumsum(g)))


def test_branch_counts_directions_and_needs_three_series():
    keys = {"a": 1, "b": 1, "c": 1, "d": -1}
    t = [_trend(k, v) for k, v in keys.items()]
    specs = [spec(k) for k in keys]
    c = ctx_for(t, specs, core={"G6": ["a", "b", "c", "d"], "G4": ["a", "b"], "G1": []})
    out = B.branch("G6", "2030-01-01", c)
    assert (out["n_up"], out["n_down"], out["n_series"]) == (3, 1, 4)
    assert out["index"] == 0.75 and out["state"] == R.STATE_ACCEL
    two = B.branch("G4", "2030-01-01", c)
    assert two["index"] == 1.0 and two["state"] == R.STATE_FEW
    assert B.branch("G1", "2030-01-01", c)["state"] == "inga registrerade kärnserier"


def test_series_without_valid_measure_are_listed_not_counted():
    c = ctx_for([_trend("a", 1), monthly_rows("short", np.arange(1, 10, dtype=float))],
                [spec("a"), spec("short")], core={"G6": ["a", "short", "missing_regime_<aktiv regim>"]})
    out = B.branch("G6", "2030-01-01", c)
    assert out["n_series"] == 1 and out["state"] == R.STATE_FEW
    reasons = {m.get("series") or m["entry"]: m["reason"] for m in out["series_not_counted"]}
    assert "ingen takt" in reasons["short"] and "ingen regim" in reasons["missing_regime_<aktiv regim>"]


# ------------------------------------------------------------------ BTOS regime rule


def _fortnights(start, n):
    return pd.period_range(pd.Timestamp(start), periods=n, freq="2W-SUN").asfreq("W-SUN")


def test_active_regime_is_the_latest_known_and_pace_stays_within_it():
    w1, w2 = _fortnights("2023-09-24", 54), _fortnights("2025-11-30", 24)
    t = [rows("btos_ai_use_v1", "2W", w1, np.linspace(4, 10, 54)),
         rows("btos_ai_use_v1_se", "2W", w1, np.full(54, 0.2)),
         rows("btos_ai_use_v2", "2W", w2, np.linspace(17, 24, 24))]
    specs = [spec(k, unit="% av företag", freq="2W", branch="G3") for k in
             ("btos_ai_use_v1", "btos_ai_use_v1_se", "btos_ai_use_v2")]
    c = ctx_for(t, specs, core={"G3": ["btos_ai_use_<aktiv regim>"]})
    assert B.resolve("btos_ai_use_<aktiv regim>", "2025-09-30", c)[0] == "btos_ai_use_v1"
    m1 = B.branch("G3", "2025-09-30", c)["series_used"]
    assert m1 and m1[0]["series"] == "btos_ai_use_v1" and m1[0]["valid"]
    # once v2 is known it is the active regime; it is too short for a pace, and v1 is not used as fallback
    assert B.resolve("btos_ai_use_<aktiv regim>", "2026-10-31", c)[0] == "btos_ai_use_v2"
    out = B.branch("G3", "2026-10-31", c)
    assert out["n_series"] == 0
    assert out["series_not_counted"][0]["series"] == "btos_ai_use_v2"
    assert "ingen takt" in out["series_not_counted"][0]["reason"]


# ------------------------------------------------------------------ derived ratio series


def test_capex_ocf_ratio_uses_same_period_versions_with_later_known_from():
    capex = rows("capex_hyp4", "Q", ["2025Q1", "2025Q1", "2025Q2"], [50.0, 60.0, 70.0],
                 known_from=["2025-04-30", "2025-07-30", "2025-07-30"])
    ocf = rows("ocf_hyp4", "Q", ["2025Q1", "2025Q2"], [100.0, 140.0], known_from=["2025-05-02", "2025-08-01"])
    d = M.derived_rows("capex_ocf_hyp4", capex, ocf, 100.0)
    got = {(r.period, str(r.known_from.date())): r.value for r in d.itertuples()}
    assert got == {("2025Q1", "2025-05-02"): 50.0, ("2025Q1", "2025-07-30"): 60.0, ("2025Q2", "2025-08-01"): 50.0}
    c = M.Context(pd.concat([capex, ocf]), specs={}, core={}, derived=R.DERIVED)
    assert observations.as_of("capex_ocf_hyp4", "2025-07-31", c.rows("capex_ocf_hyp4")).to_dict() == {
        pd.Period("2025Q1", "Q"): 60.0}
    assert M.rule_for("capex_ocf_hyp4", c).method == "share"


def test_ratio_series_pace_is_pp_over_four_quarters():
    q = pd.period_range("2015Q1", periods=24, freq="Q")
    capex = rows("capex_hyp4", "Q", q, np.linspace(40, 100, 24))
    ocf = rows("ocf_hyp4", "Q", q, np.full(24, 100.0))
    c = M.Context(pd.concat([capex, ocf]), specs=catalog.by_key(), core={}, derived=R.DERIVED)
    m = M.measure("capex_ocf_hyp4", "2030-01-01", c)
    step = 60 / 23
    assert m["pace"] == pytest.approx(4 * step) and m["change_in_pace"] == pytest.approx(0.0, abs=1e-9)


# ------------------------------------------------------------------ backfill gate


def test_backfill_gated_series_describes_but_does_not_count(monkeypatch):
    monkeypatch.setattr(R, "BACKFILL_GATED", {"eci"})
    price = 10 * np.exp(-0.05 * np.arange(48))
    back = monthly_rows("eci", price, start="2020-01", source="backfill", lag_days=0)
    c = ctx_for([back], [spec("eci", unit="USD per 1M tokens", branch="G2")])
    m = M.measure("eci", "2024-01-31", c)
    assert m["pace"] is not None and not m["valid"] and "bakåtfylld" in m["reason"]
    # 24 months of own snapshots: counts, computed on own rows only
    own = monthly_rows("eci", 10 * np.exp(-0.08 * np.arange(30)), start="2024-01", source="fetch", lag_days=1)
    c2 = ctx_for([back, own], [spec("eci", unit="USD per 1M tokens", branch="G2")])
    m2 = M.measure("eci", "2026-07-31", c2)
    assert m2["own_snapshot_months"] >= 24 and m2["sources"] == ["fetch"]
    assert m2["pace"] == pytest.approx(math.log(2) / 0.08)


def test_registered_backfill_gate_for_g1_and_g9():
    """Register 2026-11-23 (G1/G9 core table): ECI and the Epoch models database are gated, training compute
    counts but is flagged, arXiv counts."""
    assert {"g1_epoch_eci_frontier", "g9_epoch_open_weights_share", "g9_epoch_notable_models"} <= R.BACKFILL_GATED
    assert "g1_epoch_train_compute_frontier" not in R.BACKFILL_GATED
    assert "g1_epoch_train_compute_frontier" in R.BACKFILL_FLAGGED
    assert not {"g9_arxiv_cs_ai", "g9_arxiv_cs_lg", "g9_arxiv_cs_cl"} & R.BACKFILL_GATED
    ctx = M.Context(observations._empty())
    for key in ("g1_epoch_eci_frontier", "g9_epoch_open_weights_share", "g9_epoch_notable_models"):
        assert M.rule_for(key, ctx).gated, key
    assert not M.rule_for("g1_epoch_train_compute_frontier", ctx).gated


def test_flagged_backfill_series_counts_with_a_flag(monkeypatch):
    monkeypatch.setattr(R, "BACKFILL_FLAGGED", {"compute": "bakåtfylld, flaggas"})
    g = np.r_[np.full(40, 0.05), np.full(12, 0.08)]
    back = monthly_rows("compute", np.exp(np.cumsum(g)), start="2020-01", source="backfill", lag_days=7)
    c = ctx_for([back], [spec("compute", unit="FLOP", branch="G1")], core={"G1": ["compute"]})
    m = M.measure("compute", "2024-06-30", c)
    assert m["valid"] and m["flag"] == "bakåtfylld, flaggas" and m["sources"] == ["backfill"]
    assert B.branch("G1", "2024-06-30", c)["n_series"] == 1


def test_fraction_share_is_measured_in_percentage_points(monkeypatch):
    monkeypatch.setitem(R.METHOD_OVERRIDES, "ow", "share")
    q = pd.period_range("2015Q1", periods=24, freq="Q")
    x = np.linspace(0.2, 0.43, 24)
    c = ctx_for([rows("ow", "Q", q, x)], [spec("ow", unit="andel (0–1)", freq="Q", branch="G9")])
    m = M.measure("ow", "2030-01-01", c)
    assert m["method"] == "share" and m["pace"] == pytest.approx(100 * 4 * 0.01)


# ------------------------------------------------------------------ <valda>: selected benchmarks (G1)


def _bench(slug, frontier, runs, start="2023-01"):
    f = monthly_rows(f"g1_epoch_bench_frontier_{slug}", frontier, start=start, lag_days=31)
    r = monthly_rows(f"g1_epoch_bench_runs_{slug}", runs, start=start, lag_days=31)
    sp = [spec(f"g1_epoch_bench_frontier_{slug}", unit="andel rätt (0–1)", branch="G1"),
          spec(f"g1_epoch_bench_runs_{slug}", unit="antal körningar", branch="G1")]
    return [f, r], sp


def test_selected_placeholder_resolves_to_the_selection_on_the_date():
    n = 40
    t1, s1 = _bench("x", np.linspace(0.05, 0.6, n), np.full(n, 3.0))
    t2, s2 = _bench("y", np.linspace(0.02, 0.4, n) ** 1.2, np.full(n, 2.0))
    t3, s3 = _bench("z", np.linspace(0.1, 0.5, n), np.full(n, 1.0))
    core = {"G1": ["g1_epoch_bench_frontier_<valda>"]}
    c = ctx_for(t1 + t2 + t3, s1 + s2 + s3, core=core)
    c.selection = lambda when: ["x", "y"] if when < pd.Timestamp("2025-06-01") else ["z", "y"]
    b = B.branch("G1", "2025-05-31", c)
    assert [m["series"] for m in b["series_used"] + b["series_not_counted"]] == [
        "g1_epoch_bench_frontier_x", "g1_epoch_bench_frontier_y"]
    assert b["registered_entries"] == ["g1_epoch_bench_frontier_<valda>"]
    b2 = B.branch("G1", "2025-06-30", c)
    assert {m["series"] for m in b2["series_used"] + b2["series_not_counted"]} == {
        "g1_epoch_bench_frontier_z", "g1_epoch_bench_frontier_y"}
    c.selection = lambda when: []
    assert B.branch("G1", "2025-06-30", c)["series_not_counted"][0]["series"] is None
    c.selection = lambda when: ["missing"]
    assert "saknas i katalogen" in B.branch("G1", "2025-06-30", c)["series_not_counted"][0]["reason"]


def test_selected_benchmark_guard_saturated_or_retired():
    n = 40
    t, sp = _bench("x", np.linspace(0.05, 0.6, n), np.full(n, 3.0))
    c = ctx_for(t, sp, core={"G1": ["g1_epoch_bench_frontier_<valda>"]})
    c.selection = lambda when: ["x"]
    when = pd.Period("2026-04", "M").end_time.normalize() + pd.Timedelta(days=31)  # 2026-04 known on 2026-05-31
    assert B.benchmark_guard("g1_epoch_bench_frontier_x", when, c) == ""
    m = B.branch("G1", when, c)["series_used"]
    assert len(m) == 1  # counts
    # saturated: the frontier known on the date passes 0.90
    t_sat, sp_sat = _bench("x", np.r_[np.linspace(0.05, 0.6, n - 1), 0.95], np.full(n, 3.0))
    c_sat = ctx_for(t_sat, sp_sat, core={"G1": ["g1_epoch_bench_frontier_<valda>"]})
    c_sat.selection = lambda when: ["x"]
    assert B.benchmark_guard("g1_epoch_bench_frontier_x", when, c_sat).startswith("mättad")
    assert B.branch("G1", when, c_sat)["series_used"] == []
    # retired: no run in the last months known on the date (newest month with a run ended > 90 days before)
    t_ret, sp_ret = _bench("x", np.linspace(0.05, 0.6, n), np.r_[np.full(n - 4, 3.0), np.zeros(4)])
    c_ret = ctx_for(t_ret, sp_ret, core={"G1": ["g1_epoch_bench_frontier_<valda>"]})
    c_ret.selection = lambda when: ["x"]
    g = B.benchmark_guard("g1_epoch_bench_frontier_x", when, c_ret)
    assert g.startswith("avslutad") and "2025-12" in g
    # the guard only uses what is known: a later saturation does not reach back
    early = pd.Timestamp("2025-06-30")
    assert B.benchmark_guard("g1_epoch_bench_frontier_x", early, c_sat) == ""


# ------------------------------------------------------------------ surprise


def test_surprise_b1_drift_and_live_nowcast(tmp_path):
    x = np.array([100, 110, 120, 125, 140, 150.0])
    c = ctx_for([monthly_rows("x", x)], [spec("x")], tmp_path=tmp_path)
    m = M.measure("x", "2030-01-01", c)
    y = 100 * np.log(x)
    assert m["surprise"] == pytest.approx(y[5] - (y[4] + (y[4] - y[0]) / 4)) and m["surprise_basis"].startswith("B1")
    q = pd.period_range("2024Q1", periods=6, freq="Q")
    c2 = ctx_for([rows("capex_hyp4", "Q", q, x)], [spec("capex_hyp4", freq="Q", branch="G5")], tmp_path=tmp_path)
    (tmp_path / "n1").mkdir()
    (tmp_path / "n1" / "2025Q2.json").write_text(json.dumps({"origin": "2025-07-20", "value": 145.0,
                                                             "champion": "B1"}))
    m2 = M.measure("capex_hyp4", "2025-08-31", c2)
    assert m2["surprise"] == pytest.approx(100 * math.log(150 / 145)) and "N1" in m2["surprise_basis"]


# ------------------------------------------------------------------ leakage


def _world():
    t = [_trend(k, v) for k, v in {"a": 1, "b": -1, "c": 0}.items()]
    days = pd.period_range("2024-01-01", "2026-06-30", freq="D")
    t.append(rows("d", "D", days, np.linspace(1, 5, len(days)), lag_days=5))
    t.append(rows("d", "D", days[:200], np.linspace(2, 3, 200), known_from=[pd.Timestamp("2025-03-15")] * 200))
    q = pd.period_range("2012Q1", periods=58, freq="Q")
    t.append(rows("capex_hyp4", "Q", q, np.exp(np.linspace(1, 3, 58)), lag_days=30))
    t.append(rows("ocf_hyp4", "Q", q, np.exp(np.linspace(1.5, 2.5, 58)), lag_days=35))
    specs = [spec(k) for k in "abc"] + [spec("d", unit="% andel", freq="D"),
                                        spec("capex_hyp4", freq="Q", branch="G5"),
                                        spec("ocf_hyp4", freq="Q", branch="G5")]
    core = {"G6": ["a", "b", "c", "d"], "G5": ["capex_hyp4", "capex_ocf_hyp4"]}
    return pd.concat(t, ignore_index=True), specs, core


def _state(table, specs, core, when):
    c = M.Context(table, specs={s.key: s for s in specs}, core=core, derived=R.DERIVED,
                  forecasts=M.config.REPO / "no-forecasts-here")
    return {code: B.branch(code, when, c) for code in core}


@pytest.mark.parametrize("when", ["2025-01-31", "2025-06-30", "2026-03-31"])
def test_future_rows_never_affect_any_measure(when):
    table, specs, core = _world()
    base = _state(table, specs, core, when)
    future = table[table["known_from"] <= pd.Timestamp(when)].copy()
    future["value"] = future["value"] * 1000 + 7  # a wild revision of every past value ...
    future["known_from"] = pd.Timestamp(when) + pd.Timedelta(days=1)  # ... known the day after
    assert _state(pd.concat([table, future], ignore_index=True), specs, core, when) == base


@pytest.mark.parametrize("when", ["2025-01-31", "2025-06-30", "2026-03-31"])
def test_recomputing_a_past_date_from_a_truncated_table_is_identical(when):
    table, specs, core = _world()
    truncated = table[table["known_from"] <= pd.Timestamp(when)].reset_index(drop=True)
    assert _state(truncated, specs, core, when) == _state(table, specs, core, when)


def test_vintage_helper_matches_as_of():
    table, _, _ = _world()
    sub = table[table["series"] == "d"]
    v = M.vintage(sub, "2025-06-30")["value"]
    a = observations.as_of("d", "2025-06-30", sub)
    assert list(v.to_numpy()) == list(a.to_numpy())


# ------------------------------------------------------------------ writer


def _tiny_table():
    return pd.concat([_trend(k, 1) for k in "ab"], ignore_index=True)


def test_snapshot_writer_refuses_overwrite_future_and_non_month_end(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "compute", lambda when, ctx: {"G6": {"index": 1.0, "state": "x"}})
    p = S.write("2026-10-31", _tiny_table(), tmp_path, today="2026-11-23")
    d = json.loads(p.read_text(encoding="utf-8"))
    assert p.name == "2026-10.json" and d["date"] == "2026-10-31" and d["snapshot"] == "2026-10"
    assert {"git_sha", "created_utc", "register_sha256", "branches"} <= set(d)
    before = p.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        S.write("2026-10-31", _tiny_table(), tmp_path, today="2026-11-23")
    assert p.read_text(encoding="utf-8") == before
    with pytest.raises(ValueError, match="future"):
        S.write("2026-11-30", _tiny_table(), tmp_path, today="2026-11-23")
    with pytest.raises(ValueError, match="last day"):
        S.write("2026-09-15", _tiny_table(), tmp_path, today="2026-11-23")
    assert not (tmp_path / "2026-11.json").exists()


def test_snapshot_contains_measures_and_is_json_clean(tmp_path, monkeypatch):
    table, specs, core = _world()
    monkeypatch.setattr(R, "CORE_SERIES", core)
    real = M.Context

    def ctx(t):
        return real(t, specs={s.key: s for s in specs}, core=core, derived=R.DERIVED,
                    forecasts=tmp_path / "none")

    monkeypatch.setattr(S, "Context", ctx)
    p = S.write("2026-03-31", table, tmp_path, today="2026-11-23")
    d = json.loads(p.read_text(encoding="utf-8"))
    assert "NaN" not in p.read_text(encoding="utf-8")
    g6 = d["branches"]["G6"]
    assert g6["n_series"] == 4 and g6["state"] in (R.STATE_ACCEL, R.STATE_STABLE, R.STATE_BRAKE)
    used = {m["series"]: m for m in g6["series_used"]}
    assert {"latest_period", "known_from", "pace", "change_in_pace", "direction", "deadband"} <= set(used["a"])
    assert d["branches"]["G1"]["state"] == "inga registrerade kärnserier"


def test_due_only_on_month_end_without_file(tmp_path):
    assert S.due("2026-11-30", tmp_path) and not S.due("2026-11-29", tmp_path)
    assert S.due("2028-02-29", tmp_path) and S.due("2027-02-28", tmp_path) and not S.due("2028-02-28", tmp_path)
    (tmp_path / "2026-11.json").write_text("{}")
    assert not S.due("2026-11-30", tmp_path)


def test_backcast_is_labelled_reconstructed(tmp_path, monkeypatch):
    table, specs, core = _world()
    real = M.Context
    monkeypatch.setattr(S, "Context", lambda t: real(t, specs={s.key: s for s in specs}, core=core,
                                                     derived=R.DERIVED, forecasts=tmp_path / "none"))
    monkeypatch.setattr(S, "compute", lambda when, ctx: {c: B.branch(c, when, ctx) for c in core})
    out = tmp_path / "bc.csv"
    df = S.backcast("2025-01", "2025-03", table, out)
    assert out.is_file() and len(df) == 3 * len(core)
    assert (df["label"] == S.BACKCAST_LABEL).all() and "rekonstruerad" in S.BACKCAST_LABEL


# ------------------------------------------------------------------ publish snapshots


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


def test_publish_commits_a_new_snapshot_once(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "README").write_text("x")
    _git(tmp_path, "add", "README")
    _git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "init")
    f = tmp_path / "snapshots" / "2026-11.json"
    f.parent.mkdir()
    f.write_text("{}\n")
    (tmp_path / "forecasts").mkdir()
    (tmp_path / "forecasts" / "SCORECARD.md").write_text("# s\n")
    assert pipeline.publish(["snapshots/2026-11.json"], tmp_path)
    assert _git(tmp_path, "show", "--name-only", "--format=", "HEAD").split() == ["snapshots/2026-11.json"]
    assert "Monthly snapshot 2026-11" in _git(tmp_path, "log", "-1", "--format=%s")
    assert not pipeline.publish(["snapshots/2026-11.json"], tmp_path)
    with pytest.raises(SystemExit, match="only forecasts"):
        pipeline.publish(["snapshots/latest.json"], tmp_path)


def test_stale_series_not_counted():
    """Register amendment 2026-11-23: a series older than its freshness bound is not counted."""
    import pandas as pd

    from ai_tracker import catalog, warehouse
    from ai_tracker.state import branch as B

    spec = catalog.by_key()["us_imports_tw_m"]
    rows = pd.DataFrame({"series": "us_imports_tw_m", "freq": "M", "period": ["2026-01"], "value": [1.0],
                         "known_from": [pd.Timestamp("2026-03-01")], "source": "fetch",
                         "fetched_at": [pd.Timestamp("2026-03-01")]})

    class Ctx:
        def rows(self, key):
            return rows if key == "us_imports_tw_m" else rows.iloc[0:0]

    bound = warehouse.max_age_days(spec)
    fresh_day = pd.Timestamp("2026-01-31") + pd.Timedelta(days=bound)
    assert B.stale_reason("us_imports_tw_m", fresh_day, Ctx()) == ""
    assert B.stale_reason("us_imports_tw_m", fresh_day + pd.Timedelta(days=1), Ctx()).startswith("inaktuell")
