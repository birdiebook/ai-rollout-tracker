"""Epoch hub parsers and derivations, on small in-memory fixtures (no network)."""

from __future__ import annotations

import io
import zipfile
from datetime import date

import numpy as np
import pandas as pd
import pytest

from ai_tracker import catalog, observations
from ai_tracker.sources import epoch_hub as e

RUN_COLS = "Model version,mean_score,Best score (across scorers),Release date,Started at,id\n"


def _bench_zip() -> dict[str, bytes]:
    meta = ("benchmark,in_eci,source_file,score_column,scale,random_baseline,score_ceiling,release_date,superseded_by\n"
            "A,True,a.csv,Best score (across scorers),1.0,0,1,2025-01-01,\n")
    a = RUN_COLS + ("m1,0.1,0.10,2025-01-01,2025-01-10T10:00:00Z,1\n"
                    "m2,0.3,0.30,2025-01-01,2025-01-31T23:59:59Z,2\n"
                    "m3,0.9,0.90,2024-12-01,2025-02-01T00:00:01Z,3\n"   # model released earlier, run started in Feb
                    "m4,0.5,0.50,2025-01-01,,4\n")                        # no Started at: dropped
    b = RUN_COLS + "m1,0.2,0.20,2025-01-01,2025-03-01T00:00:00Z,1\nm2,0.2,0.25,2025-01-01,2025-03-02,2\n"
    ext = "Model version,Score,Release date\nm1,0.99,2025-01-01\n"
    eci = "Model,eci,date\nx,100,2025-01-02\ny,120,2025-01-20\nz,110,2025-02-03\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("benchmark_metadata.csv", meta)
        z.writestr("a.csv", a)
        z.writestr("b.csv", b)
        z.writestr("c_external.csv", ext)
        z.writestr("epoch_capabilities_index/eci_scores.csv", eci)
    return e.read_zip(buf.getvalue())


def test_epoch_runs_only_own_runs_with_started_at():
    runs = e.epoch_runs(_bench_zip())
    assert set(runs["benchmark"]) == {"a", "b"}  # external file ignored
    assert "m4" not in set(runs["model"])
    assert str(runs["started_at"].dt.tz) == "UTC"


def test_frontier_as_of_excludes_runs_started_after_month_end():
    runs = e.epoch_runs(_bench_zip())
    mf = e.monthly_frontier(runs[runs["benchmark"] == "a"], pd.Period("2025-03", "M"))
    # m3 (0.90) belongs to an older model but its run started 1 second into February: not in January
    assert mf.loc[pd.Period("2025-01", "M"), "frontier"] == pytest.approx(0.30)
    assert mf.loc[pd.Period("2025-02", "M"), "frontier"] == pytest.approx(0.90)
    assert mf.loc[pd.Period("2025-03", "M"), "frontier"] == pytest.approx(0.90)  # carried forward
    assert list(mf["runs"]) == [2, 1, 0]


def test_release_frame_known_from_is_day_after_month_end():
    s = pd.Series([0.3], index=pd.PeriodIndex(["2025-01"], freq="M"))
    f = e.release_frame(s, lag_days=1)
    assert f["known_from"].iloc[0] == pd.Timestamp("2025-02-01")


def _runs(rows):
    return pd.DataFrame(rows, columns=["benchmark", "model", "score", "started_at"]).assign(
        started_at=lambda d: pd.to_datetime(d["started_at"], utc=True, format="mixed"))


def test_selection_rule_coverage_among_unsaturated():
    rows = []
    for b, n, top in [("sat", 50, 0.95), ("big", 40, 0.6), ("mid", 30, 0.79), ("small", 10, 0.5),
                      ("tiny", 5, 0.1), ("edge", 45, 0.80)]:
        rows += [(b, f"{b}{i}", top * (i + 1) / n, "2026-01-01") for i in range(n)]
    rows.append(("small", "late", 0.99, "2026-11-24T00:00:00Z"))  # after the selection date: ignored
    sel = e.select_benchmarks(_runs(rows), "2026-11-23")
    assert list(sel.index) == ["big", "mid", "small"]  # 'sat' and 'edge' (frontier >= 0.80) excluded
    assert sel.loc["small", "frontier"] == pytest.approx(0.5)


def test_selection_ties_broken_by_name():
    rows = [(b, f"m{i}", 0.1, "2026-01-01") for b in ("zeta", "alpha", "beta") for i in range(3)]
    assert list(e.select_benchmarks(_runs(rows), "2026-11-23", n=2).index) == ["alpha", "beta"]


def test_successor_rule():
    rows = []
    for b, n, top in [("big", 40, 0.95), ("mid", 30, 0.5), ("small", 10, 0.5), ("next1", 20, 0.75),
                      ("next2", 15, 0.6), ("next3", 12, 0.2)]:
        rows += [(b, f"{b}{i}", top * (i + 1) / n, "2026-12-01") for i in range(n)]
    sel, swaps = e.apply_successor_rule(["big", "mid", "small"], _runs(rows), "2026-12-31")
    # big passed 0.90 -> next in coverage ranking with frontier < 0.70 (next1 at 0.75 is not eligible)
    assert sel == ["next2", "mid", "small"] and swaps == [("big", "next2")]
    # nothing passes 0.90 -> unchanged
    assert e.apply_successor_rule(["mid", "small"], _runs(rows), "2026-12-31") == (["mid", "small"], [])


def test_with_revisions_adds_row_dated_today_when_value_changes():
    key = "g1_test"
    first = pd.DataFrame({"period": ["2025-01", "2025-02"], "value": [0.3, 0.5],
                          "known_from": pd.to_datetime(["2025-02-01", "2025-03-01"])})
    spec = catalog.Spec(key, "G1", key, "x", "M", "t", lambda: None, 1, "unverified")
    table = observations.new_rows(spec, first, observations._empty(), fetched_at=date(2025, 3, 5))
    changed = first.assign(value=[0.3, 0.6])
    out = e.with_revisions(changed, key, table, today=date(2025, 4, 2))
    added = observations.new_rows(spec, out, table, fetched_at=date(2025, 4, 2))
    assert list(zip(added["period"], added["value"], added["known_from"])) == [
        ("2025-02", 0.6, pd.Timestamp("2025-04-02"))]
    table = pd.concat([table, added], ignore_index=True)
    # identical refetch adds nothing, and as_of keeps the old vintage before the revision date
    assert observations.new_rows(spec, e.with_revisions(changed, key, table, date(2025, 4, 9)), table).empty
    assert observations.as_of(key, "2025-03-31", table).iloc[-1] == pytest.approx(0.5)
    assert observations.as_of(key, "2025-04-02", table).iloc[-1] == pytest.approx(0.6)


def test_runs_ledger_keeps_first_seen(tmp_path):
    path = tmp_path / "runs.parquet"
    runs = _runs([("a", "m1", 0.1, "2026-01-01")])
    e.update_runs_ledger(runs, date(2026, 1, 5), path)
    more = _runs([("a", "m1", 0.1, "2026-01-01"), ("a", "m2", 0.2, "2026-01-07")])
    led = e.update_runs_ledger(more, date(2026, 1, 12), path).set_index("model")
    assert led.loc["m1", "first_seen"] == pd.Timestamp("2026-01-05")
    assert led.loc["m2", "first_seen"] == pd.Timestamp("2026-01-12")
    # a replaced run (re-run with a new start) keeps the old row in the ledger
    rerun = _runs([("a", "m1", 0.15, "2026-01-20"), ("a", "m2", 0.2, "2026-01-07")])
    assert len(e.update_runs_ledger(rerun, date(2026, 1, 26), path)) == 3


def test_eci_frontier_weekly_complete_weeks_only():
    s = e.eci_frontier(_bench_zip(), today=date(2025, 2, 5))  # Wednesday: week of 2025-02-03 not complete
    assert s.index.freqstr.startswith("W")
    assert s.index[-1] == pd.Period("2025-02-02", freq="W-SUN")
    assert s.iloc[0] == 100 and s.iloc[-1] == 120  # z (110, released 2025-02-03) not yet included


def test_models_derivations():
    notable = pd.DataFrame({
        "Publication date": pd.to_datetime(["2025-01-05", "2025-01-20", "2025-03-01", "2025-04-02"]),
        "Open model weights?": ["Yes", "No", None, "Yes"],
        "Training compute (FLOP)": [1e24, np.nan, 5e23, 3e25]})
    n = e.notable_per_month(notable, today=date(2025, 4, 10), start="2024-12")
    assert list(n) == [0, 2, 0, 1]  # Dec..Mar; April incomplete
    sh = e.open_weights_share(notable, today=date(2025, 7, 1), start="2025Q1")
    assert list(sh) == [0.5, 1.0]  # blank excluded from the denominator
    tc = e.train_compute_frontier(notable, today=date(2025, 5, 1), start="2025-01")
    assert list(tc) == [1e24, 1e24, 1e24, 3e25]


def test_hw_price_performance_prefers_tensor_16bit():
    hw = pd.DataFrame({"Release date": ["2016-05-01", "2017-06-01", "2018-01-01"],
                       "Tensor-FP16/BF16 performance (FLOP/s)": [np.nan, 1e14, np.nan],
                       "FP16 (half precision) performance (FLOP/s)": [1e13, 5e13, 1e12],
                       "Release price (USD)": [1000, 10000, 100]})
    s = e.hw_price_performance(hw, today=date(2019, 3, 1), start="2016")
    assert list(s) == [1e10, 1e10, 1e10]  # 2017: 1e14/1e4 = 1e10 (tensor), 2018 chip 1e10 ties


def test_epoch_specs_are_valid():
    from ai_tracker.series import epoch_hub as se

    assert catalog.validate(se.SPECS) == []
    keys = {s.key for s in se.SPECS}
    assert {"g1_epoch_eci_frontier", "g9_epoch_open_weights_share", "g2_epoch_hw_price_performance"} <= keys
    assert len(se.SELECTED_BENCHMARKS) == e.SELECT_N


def test_source_modules_import_first_without_cycle():
    import subprocess
    import sys

    for mod in ("ai_tracker.sources.epoch_hub", "ai_tracker.sources.metr", "ai_tracker.sources.arxiv"):
        r = subprocess.run([sys.executable, "-c", f"import {mod}"], capture_output=True, text=True,
                           env={"PYTHONPATH": str(catalog.__file__).rsplit("/ai_tracker/", 1)[0]})
        assert r.returncode == 0, r.stderr[-500:]
