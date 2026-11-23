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
        rows += [(b, f"{b}{i}", top * (i + 1) / n, "2026-11-01") for i in range(n)]
    rows.append(("small", "late", 0.99, "2026-11-24T00:00:00Z"))  # after the selection date: ignored
    sel = e.select_benchmarks(_runs(rows), "2026-11-23")
    assert list(sel.index) == ["big", "mid", "small"]  # 'sat' and 'edge' (frontier >= 0.80) excluded
    assert sel.loc["small", "frontier"] == pytest.approx(0.5)
    t = e.selection_table(_runs(rows), "2026-11-23")
    assert t.loc["tiny", "status"] == "efterträdare" and t.loc["tiny", "rank"] == 4
    assert t.loc["edge", "reason"].startswith("frontvärde 0,800")


def test_selection_ties_broken_by_name():
    rows = [(b, f"m{i}", 0.1, "2026-11-01") for b in ("zeta", "alpha", "beta") for i in range(3)]
    assert list(e.select_benchmarks(_runs(rows), "2026-11-23", n=2).index) == ["alpha", "beta"]


def test_retired_benchmarks_are_excluded():
    rows = [(b, f"{b}{i}", 0.3, day) for b, n, day in [("old", 50, "2026-08-24T23:00:00Z"),
                                                         ("recent", 40, "2026-08-25T00:00:00Z"),
                                                         ("superseded", 60, "2026-11-01"), ("other", 5, "2026-11-01")]
            for i in range(n)]
    sup = pd.Series({"superseded": "Superseded-v2", "recent": np.nan})
    t = e.selection_table(_runs(rows), "2026-11-23", sup)
    # 90 days before 2026-11-23 is 2026-08-25: a run on that day keeps the benchmark active
    assert list(t[t["status"] == "vald"].index) == ["recent", "other"]
    assert t.loc["old", "reason"] == "avslutad: ingen Epoch-körning sedan 2026-08-24"
    assert t.loc["superseded", "reason"] == "avslutad: ersatt av Superseded-v2"


REAL_STEMS = ["chess_puzzles", "ebr_bench", "frontiermath", "frontiermath_erdos", "frontiermath_tier_4",
              "frontiermath_tier_4_v2", "frontiermath_tiers_1_3_v2", "furniture_assembly", "gpqa_diamond",
              "math_level_5", "mirrorcode", "mystery_game_puzzles", "otis_mock_aime_2024_2025", "simpleqa_verified",
              "spireclimb", "spireclimb_sts1_a20_heart", "spireclimb_sts2_a10", "swe_bench_verified"]


def test_family_key_on_epochs_benchmark_names():
    fam = {b: e.family(b) for b in REAL_STEMS}
    groups = {}
    for b, f in fam.items():
        groups.setdefault(f, []).append(b)
    assert groups["frontiermath"] == ["frontiermath", "frontiermath_erdos", "frontiermath_tier_4",
                                      "frontiermath_tier_4_v2", "frontiermath_tiers_1_3_v2"]
    assert groups["spireclimb"] == ["spireclimb", "spireclimb_sts1_a20_heart", "spireclimb_sts2_a10"]
    assert {f for f, v in groups.items() if len(v) > 1} == {"frontiermath", "spireclimb"}
    assert fam["gpqa_diamond"] == "gpqa" and fam["math_level_5"] == "math" and fam["swe_bench_verified"] == "swe"


def test_one_per_family_most_models_then_base_variant():
    rows = []
    for b, n in [("spire", 13), ("spire_a20", 13), ("spire_b", 14), ("fm", 30), ("fm_erdos", 17), ("solo", 5)]:
        rows += [(b, f"{b}{i}", 0.3, "2026-11-01") for i in range(n)]
    sup = pd.Series({"fm": "fm-v2"})
    t = e.selection_table(_runs(rows), "2026-11-23", sup)
    assert list(t[t["status"] == "vald"].index) == ["fm_erdos", "spire_b", "solo"]
    assert "samma familj som spire_b (färre modeller)" in t.loc["spire", "reason"]
    tie = _runs([r for r in rows if r[0] != "spire_b"])
    t2 = e.selection_table(tie, "2026-11-23", sup)
    assert t2.loc["spire", "status"] == "vald"  # tie at 13: the base variant
    assert "lika många modeller, basvarianten" in t2.loc["spire_a20", "reason"]


def test_successor_rule():
    rows = []
    for b, n, top in [("big", 40, 0.95), ("mid", 30, 0.5), ("small", 10, 0.5), ("next1", 20, 0.75),
                      ("next2", 15, 0.6), ("next3", 12, 0.2)]:
        rows += [(b, f"{b}{i}", top * (i + 1) / n, "2026-12-01") for i in range(n)]
    sel, swaps = e.apply_successor_rule(["big", "mid", "small"], _runs(rows), "2026-12-31")
    # big passed 0.90 -> next in coverage ranking with frontier < 0.70 (next1 at 0.75 is not eligible)
    assert sel == ["next2", "mid", "small"] and [s[:2] for s in swaps] == [("big", "next2")]
    assert swaps[0][2].startswith("mättad")
    # nothing passes 0.90 -> unchanged
    assert e.apply_successor_rule(["mid", "small"], _runs(rows), "2026-12-31") == (["mid", "small"], [])
    # 90 days later without runs: all retired, and no successor is eligible
    sel, swaps = e.apply_successor_rule(["mid"], _runs(rows), "2027-03-15")
    assert sel == ["mid"] and swaps[0][1] is None and swaps[0][2].startswith("avslutad")


def test_successor_rule_skips_families_already_selected():
    rows = []
    for b, n, top in [("a", 40, 0.95), ("b", 30, 0.5), ("b_v2", 20, 0.3), ("c", 10, 0.4)]:
        rows += [(b, f"{b}{i}", top * (i + 1) / n, "2026-12-01") for i in range(n)]
    sel, _ = e.apply_successor_rule(["a", "b"], _runs(rows), "2026-12-31")
    assert sel == ["c", "b"]  # b_v2 has more models but its family is already selected


def test_run_known_is_started_plus_30_days_and_first_seen_after_the_first_fetch():
    runs = _runs([("a", "m1", 0.1, "2026-10-01T10:00:00Z"), ("a", "m2", 0.2, "2026-10-01T00:00:00Z"),
                  ("a", "m3", 0.3, "2026-10-01T10:00:00Z"), ("a", "m4", 0.4, "2026-12-20T10:00:00Z")])
    runs["first_seen"] = pd.to_datetime(["2026-11-23", "2026-11-23", "2026-12-14", "2026-12-21"])
    k = e.run_known(runs, first_fetch=pd.Timestamp("2026-11-23"))
    assert list(k) == [pd.Timestamp("2026-11-01"), pd.Timestamp("2026-10-31"),  # rounded up to midnight
                       pd.Timestamp("2026-12-14"),  # first seen in a later fetch, after start + 30
                       pd.Timestamp("2027-01-20")]  # later fetch, but start + 30 is later still


def test_monthly_vintages_known_30_days_after_month_and_late_runs_add_vintages():
    runs = _runs([("a", "m1", 0.1, "2026-08-10"), ("a", "m2", 0.3, "2026-08-31T23:00:00Z"),
                  ("a", "m3", 0.2, "2026-09-05"), ("a", "m4", 0.5, "2026-08-20")])
    runs["first_seen"] = pd.to_datetime(["2026-11-23", "2026-11-23", "2026-11-23", "2026-12-07"])
    fr = e.monthly_vintages(runs, pd.Period("2026-09", "M"), "frontier")
    got = list(zip(fr["period"], fr["value"], fr["known_from"]))
    assert got == [("2026-08", 0.3, pd.Timestamp("2026-09-01") + pd.Timedelta(days=30)),
                   ("2026-08", 0.5, pd.Timestamp("2026-12-07")),  # m4 published late: a new vintage
                   ("2026-09", 0.3, pd.Timestamp("2026-10-31")),
                   ("2026-09", 0.5, pd.Timestamp("2026-12-07"))]
    n = e.monthly_vintages(runs, pd.Period("2026-09", "M"), "runs")
    assert list(zip(n["period"], n["value"], n["known_from"])) == [
        ("2026-08", 2.0, pd.Timestamp("2026-10-01")), ("2026-08", 3.0, pd.Timestamp("2026-12-07")),
        ("2026-09", 1.0, pd.Timestamp("2026-10-31"))]
    assert e.monthly_vintages(runs, pd.Period("2026-07", "M"), "frontier").empty  # no complete month yet


REAL_ZIP = e.config.REPO / "data" / "raw" / "epoch" / "2026-11-23"


@pytest.mark.skipif(not list(REAL_ZIP.glob("data_benchmark_data.zip_*")), reason="no 2026-11-23 raw copy")
def test_rule_reproduces_the_registered_selection_on_the_2026_11_23_vintage():
    from ai_tracker.series import epoch_hub as se

    files = e.read_zip(next(REAL_ZIP.glob("data_benchmark_data.zip_*")).read_bytes())
    runs, sup = e.epoch_runs(files), e.superseded_by(files)
    t = e.selection_table(runs, e.SELECTION_DATE, sup)
    assert list(t[t["status"] == "vald"].index) == list(se.SELECTED_BENCHMARKS)
    assert t.loc["frontiermath", "reason"].startswith("avslutad: ersatt av")
    assert e.apply_successor_rule(list(se.SELECTED_BENCHMARKS), runs, e.SELECTION_DATE, superseded=sup)[1] == []


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
    assert 0 < len(se.SELECTED_BENCHMARKS) <= e.SELECT_N
    for slug in se.CLOSED_BENCHMARKS:
        spec = catalog.by_key(se.SPECS)[f"g1_epoch_bench_frontier_{slug}"]
        assert spec.closed and "Avslutad:" in spec.note
    assert se.selected_on("2024-01-31") == se.selected_on(e.SELECTION_DATE) == list(se.SELECTED_BENCHMARKS)


def test_selected_on_applies_replacements_from_their_date(monkeypatch):
    from ai_tracker.series import epoch_hub as se

    monkeypatch.setattr(se, "SELECTED_BENCHMARKS", {"a": "A", "b": "B"})
    monkeypatch.setattr(se, "REPLACEMENTS", [("2027-02-01", "a", "c")])
    assert se.selected_on("2027-01-31") == ["a", "b"] and se.selected_on("2027-02-01") == ["c", "b"]


def test_source_modules_import_first_without_cycle():
    import subprocess
    import sys

    for mod in ("ai_tracker.sources.epoch_hub", "ai_tracker.sources.metr", "ai_tracker.sources.arxiv"):
        r = subprocess.run([sys.executable, "-c", f"import {mod}"], capture_output=True, text=True,
                           env={"PYTHONPATH": str(catalog.__file__).rsplit("/ai_tracker/", 1)[0]})
        assert r.returncode == 0, r.stderr[-500:]
