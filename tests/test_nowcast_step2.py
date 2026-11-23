"""N3-N6 (step 2, track C5): fiscal mapping, leakage (as_of for every input, first-vintage outcome, known-outcome
guard), definition breaks, Holm family, origin days and the immutable writers. Synthetic fixtures only, no network."""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from ai_tracker import pipeline
from ai_tracker.nowcast import engine, intervals, n3, n4, n5, n6, quarterly

TS = pd.Timestamp
Q = "Q-DEC"


def _rows(series, periods, values, known_from, freq="Q", source="release"):
    return pd.DataFrame({"series": series, "freq": freq, "period": [str(p) for p in periods],
                         "value": np.asarray(values, dtype=float), "known_from": pd.to_datetime(list(known_from)),
                         "source": source, "fetched_at": TS("2026-11-23")})


def _path(n, seed, drift=0.05, sd=0.04, start=100.0):
    rng = np.random.default_rng(seed)
    return start * np.exp(np.cumsum(drift + sd * rng.standard_normal(n)))


# ------------------------------------------------------------------ N3 fiscal calendar (F-B5)


def test_nvidia_fiscal_calendar_known_year_ends_and_14_week_quarters():
    assert n3.last_sunday_of_january(2025) == TS("2025-01-26")
    assert n3.last_sunday_of_january(2021) == TS("2021-01-31")  # 53-week FY2021
    assert n3.fiscal_quarter(pd.Period("2026Q3", Q)) == (TS("2026-07-27"), TS("2026-10-25"))
    assert n3.fiscal_quarter(pd.Period("2026Q4", Q)) == (TS("2026-10-26"), TS("2027-01-31"))
    assert n3.weeks(pd.Period("2026Q4", Q)) == 14 and n3.weeks(pd.Period("2020Q4", Q)) == 14
    assert n3.weeks(pd.Period("2025Q4", Q)) == 13 and n3.weeks(pd.Period("2026Q1", Q)) == 13
    # Q1-Q3 are 13 weeks; "the last Sunday of the month" is off by a week after a 53-week year (Nvidia's Q1 and Q2
    # FY2022 ended 2 May and 1 Aug 2021, R6 section 10)
    assert n3.fiscal_quarter(pd.Period("2021Q1", Q))[1] == TS("2021-05-02")
    assert n3.fiscal_quarter(pd.Period("2021Q2", Q))[1] == TS("2021-08-01")
    for q in pd.period_range("2010Q1", "2030Q4", freq=Q):
        s, e = n3.fiscal_quarter(q)
        assert e.day_name() == "Sunday" and n3.weeks(q) in (13, 14) and (n3.weeks(q) == 13 or q.quarter == 4)
        assert n3.fiscal_quarter(q - 1)[1] == s - pd.Timedelta(days=1)
        assert n3.target_quarter(n3.origin_for(q)) == q
        assert n3.target_quarter(n3.origin_for(q) - pd.Timedelta(days=1)) == q - 1


def test_n3_origin_days_in_pipeline():
    assert pipeline.n3_due("2027-02-14") == pipeline.Due("n3", TS("2027-02-14"), "2026Q4")
    assert pipeline.n3_due("2026-11-08").period == "2026Q3"
    assert pipeline.n3_due("2027-02-13") is None and pipeline.n3_due("2027-02-15") is None
    assert pipeline.n4_due("2027-01-20").period == "2026Q4" and pipeline.n6_due("2027-01-20").period == "2026Q4"
    assert pipeline.n4_due("2027-01-21") is None


# ------------------------------------------------------------------ N3 fixture


def n3_table(last="2021Q4"):
    qs = pd.period_range("2015Q1", last, freq=Q)
    tot = _path(len(qs), 1, start=1000)
    dc = tot * np.linspace(0.3, 0.8, len(qs))
    release = [n3.fiscal_quarter(q)[1] + pd.Timedelta(days=25) for q in qs]
    guid_kf = [release[i - 1] if i else release[0] - pd.Timedelta(days=90) for i in range(len(qs))]
    return pd.concat([
        _rows(n3.TARGET, qs, dc, release), _rows(n3.TOTAL, qs, tot, release),
        _rows(n3.GUIDANCE, qs, tot * 1.03, guid_kf),
    ], ignore_index=True)


def test_n3_b2_is_guidance_times_last_known_share_as_of_origin():
    t = n3_table()
    q = pd.Period("2020Q2", Q)
    o = n3.origin_for(q)
    # a later vintage of the guidance (after the origin) must not be used
    t = pd.concat([t, _rows(n3.GUIDANCE, [q], [1e9], [o + pd.Timedelta(days=1)])], ignore_index=True)
    rec, _ = quarterly.live_forecast(t, n3.SPEC, o)
    g = t[(t.series == n3.GUIDANCE) & (t.period == str(q))].sort_values("known_from")["value"].iloc[0]
    L = q - 1
    dc = t[(t.series == n3.TARGET) & (t.period == str(L))]["value"].iloc[0]
    tot = t[(t.series == n3.TOTAL) & (t.period == str(L))]["value"].iloc[0]
    assert rec.levels["B2"] == pytest.approx(g * dc / tot)
    assert rec.notes["b2_share_quarter"] == str(L)
    assert all(TS(i["known_from"]) <= o for i in rec.info.inputs())


def test_n3_b2_falls_back_to_b1_without_known_guidance():
    t = n3_table()
    q = pd.Period("2020Q2", Q)
    t = t[~((t.series == n3.GUIDANCE) & (t.period == str(q)))]
    t = pd.concat([t, _rows(n3.GUIDANCE, [q], [5.0], [n3.origin_for(q) + pd.Timedelta(days=2)])], ignore_index=True)
    rec, _ = quarterly.live_forecast(t, n3.SPEC, n3.origin_for(q))
    assert rec.levels["B2"] == rec.levels["B1"] and rec.notes["b2_source"].startswith("B1")


def test_backtest_rows_equal_forecasts_from_data_known_at_origin():
    """Every scored quarter's forecast is what a forecaster at the origin would have made (no later rows used)."""
    for spec, table in ((n3.SPEC, n3_table()), (n4.SPEC, cloud_table()), (n6.SPEC, cloud_table())):
        f = quarterly.run(table, spec)
        assert len(f)
        for r in f.dropna(subset=spec.variants).tail(4).itertuples():
            rec, _ = quarterly.live_forecast(table, spec, r.origin)
            for v in spec.variants:
                assert rec.levels[v] == pytest.approx(r.outcome * math.exp(getattr(r, v) / 100)), (spec.label, v)


def test_n3_outcome_is_first_vintage_and_known_outcomes_are_not_scored():
    t = n3_table()
    q = pd.Period("2019Q3", Q)
    first = t[(t.series == n3.TARGET) & (t.period == str(q))]["value"].iloc[0]
    t = pd.concat([t, _rows(n3.TARGET, [q], [first * 2], ["2020-06-01"], source="revision")], ignore_index=True)
    early = pd.Period("2020Q1", Q)  # filed before its origin: never scored
    t.loc[(t.series == n3.TARGET) & (t.period == str(early)), "known_from"] = n3.origin_for(early) - pd.Timedelta(days=1)
    f = quarterly.run(t, n3.SPEC).set_index("quarter")
    assert f.at[q, "outcome"] == first
    assert early not in f.index and any(str(early) in k for k in f.attrs["known_at_origin"])
    assert (pd.to_datetime(f["outcome_known_from"]) > pd.to_datetime(f["origin"])).all()


def test_n3_holm_family_counts_unevaluated_members_with_p_1():
    f = quarterly.run(n3_table(), n3.SPEC)
    res = quarterly.evaluate(f, n3.SPEC)
    r = res["full"]
    assert set(r["holm_family"]) == {"B2", "B3", "DF"}
    assert r["holm_family"]["B3"] == 1.0 and r["holm_family"]["DF"] == 1.0
    assert r["dm"]["B2"]["holm_p"] == pytest.approx(min(1.0, 3 * r["dm"]["B2"]["p"]))


def test_n3_b2_passing_is_only_conditional():
    res = {per: {"metrics": {"B0": {"MAE": 5.0}, "B1": {"MAE": 4.0}, "B2": {"MAE": 1.0}}, "comparator": "B1",
                 "dm": {"B2": {"holm_p": 0.001}}} for per in ("full", "2023Q1-")}
    p = quarterly.promotion(res, n3.SPEC)
    assert p["checks"]["B2"]["promoted"] and p["champion"] == "B1" and "B2" in p["conditional"]


def test_n3_evaluation_starts_where_b2_is_formed_from_guidance():
    t = n3_table()
    t = t[~((t.series == n3.GUIDANCE) & t["period"].isin([str(p) for p in pd.period_range("2015Q1", "2017Q4", freq=Q)]))]
    f = quarterly.run(t, n3.SPEC)
    assert f.attrs["start"] == pd.Period("2018Q1", Q)
    assert (f.loc[f["in_period"], "b2_source"] == "guidance").all()


# ------------------------------------------------------------------ N4 / N6 fixture


def cloud_table(last="2021Q4"):
    qs = pd.period_range("2014Q1", last, freq=Q)
    ends = qs.end_time.normalize()
    parts = []
    for i, c in enumerate(n4.COMPONENTS):
        parts.append(_rows(c, qs, _path(len(qs), 10 + i, start=100 * (i + 1)), ends + pd.Timedelta(days=25 + 3 * i)))
    for i, c in enumerate(n4.RPO.components):
        lag = -20 if c == "rpo_orcl" else 26 + 2 * i  # Oracle's balance date is known before the origin (F-B8)
        parts.append(_rows(c, qs, _path(len(qs), 20 + i, start=300 * (i + 1)), ends + pd.Timedelta(days=lag)))
    return pd.concat(parts, ignore_index=True)


def test_n4_target_exists_only_when_all_components_known_dated_by_the_latest():
    t = cloud_table()
    agg = quarterly.aggregate_rows(t, quarterly.Aggregate(n4.TARGET, n4.COMPONENTS))
    q = "2018Q2"
    row = agg[agg["period"] == q].iloc[0]
    comp = t[t["series"].isin(n4.COMPONENTS) & (t["period"] == q)]
    assert row["value"] == pytest.approx(comp["value"].sum())
    assert row["known_from"] == comp["known_from"].max()
    o = n4.origin_for(pd.Period(q, Q))
    info = engine.InfoSet(quarterly.prepare(t, n4.SPEC), o)
    assert pd.Period(q, Q) not in info.get(n4.TARGET).index  # two components known, the sum is not


def test_n6_counts_components_known_at_origin_and_uses_naive_aggregate():
    f = quarterly.run(cloud_table(), n6.SPEC)
    assert (f["components_known"] == 1).all()  # Oracle filed before the origin, the others after
    assert (pd.to_datetime(f["outcome_known_from"]) > pd.to_datetime(f["origin"])).all()


def test_regressor_is_taken_as_known_at_each_rows_own_origin():
    t = cloud_table()
    q = pd.Period("2019Q3", Q)
    o = n4.origin_for(q)
    base = quarterly.run(t, n4.SPEC).set_index("quarter")
    # revise an RPO component of q-1 after the origin of q: q's row (and its regressor) must not change
    later = pd.concat([t, _rows("rpo_msft", [q - 1], [1e7], [o + pd.Timedelta(days=5)], source="revision")],
                      ignore_index=True)
    rev = quarterly.run(later, n4.SPEC).set_index("quarter")
    assert rev.at[q, "x"] == pytest.approx(base.at[q, "x"]) and rev.at[q, "x_period"] == str(q - 1)
    assert rev.at[q, "B1"] == pytest.approx(base.at[q, "B1"])
    assert rev.at[q + 1, "x"] != pytest.approx(base.at[q + 1, "x"])  # a later origin sees the revision


def test_v1_needs_12_training_rows_and_starts_the_evaluation():
    f = quarterly.run(cloud_table(), n4.SPEC)
    first = f.loc[f["V1"].notna()].iloc[0]
    assert first["n_train"] == quarterly.MIN_TRAIN and f.attrs["start"] == first["quarter"]
    assert f.loc[f["quarter"] < first["quarter"], "V1"].isna().all()


def test_definition_break_is_not_scored_and_b1_does_not_cross_it():
    t = cloud_table()
    q = pd.Period("2019Q2", Q)
    kf = t[(t.series == "rev_aws") & (t.period == str(q))]["known_from"].iloc[0]
    old = t[(t.series == "rev_aws") & (t.period == str(q - 4))]["value"].iloc[0]
    t = pd.concat([t, _rows("rev_aws", [q - 4], [old * 1.05], [kf], source="restated")], ignore_index=True)
    assert q in quarterly.breaks(t, quarterly.Aggregate(n4.TARGET, n4.COMPONENTS))
    f = quarterly.run(t, n4.SPEC).set_index("quarter")
    assert q not in f.index and any(str(q) in b for b in f.attrs["breaks"])
    for k in (1, 2, 3, 4):
        assert np.isnan(f.at[q + k, "B1"]) and "break" in f.at[q + k, "reason"]
    assert np.isfinite(f.at[q + 5, "B1"])


# ------------------------------------------------------------------ writers


def test_quarterly_writer_writes_once_and_refuses_bad_origins(tmp_path):
    t = cloud_table("2021Q3")
    o = n4.origin_for(pd.Period("2021Q4", Q))
    p = n4.write_live(t, o, tmp_path, today=o)
    d = json.loads(p.read_text(encoding="utf-8"))
    assert p.name == "2021Q4.json" and d["quarter"] == "2021Q4" and d["champion"] == "B1"
    assert all(TS(i["known_from"]) <= o for i in d["inputs"])
    if intervals.ENABLED:
        assert "distribution" in d
    before = p.read_bytes()
    with pytest.raises(FileExistsError):
        n4.write_live(t, o, tmp_path, today=o)
    assert p.read_bytes() == before
    with pytest.raises(ValueError, match="future"):
        n6.write_live(t, o, tmp_path / "x", today=o - pd.Timedelta(days=1))
    with pytest.raises(ValueError, match="registered origin"):
        n6.write_live(t, o + pd.Timedelta(days=1), tmp_path / "y", today=o + pd.Timedelta(days=1))
    known = pd.concat([t, *(_rows("rpo_" + c, [pd.Period("2021Q4", Q)], [1.0], [o - pd.Timedelta(days=1)])
                            for c in ("msft", "googl", "amzn", "orcl"))], ignore_index=True)
    with pytest.raises(quarterly.NotAvailable, match="already known"):
        n6.write_live(known, o, tmp_path / "z", today=o)


def test_pipeline_runs_n3_live_and_scores_n4_against_derived_first_vintage(tmp_path):
    t = n3_table("2021Q3")
    o = n3.origin_for(pd.Period("2021Q4", Q))
    path = pipeline.run_live(pipeline.Due("n3", o, "2021Q4"), tmp_path, t, refresh=False, today=o)
    assert path == tmp_path / "n3" / "2021Q4.json"
    assert pipeline.run_live(pipeline.Due("n3", o, "2021Q4"), tmp_path, t, refresh=False, today=o) is None
    c = cloud_table("2021Q3")
    o4 = n4.origin_for(pd.Period("2021Q4", Q))
    pipeline.run_live(pipeline.Due("n4", o4, "2021Q4"), tmp_path, c, refresh=False, today=o4)
    full = cloud_table("2021Q4")
    s = pipeline.score(tmp_path, full)
    r = s["n4"].iloc[0]
    y = full[full["series"].isin(n4.COMPONENTS) & (full["period"] == "2021Q4")]["value"].sum()
    assert r["status"] == "utfall" and r["outcome"] == pytest.approx(y)
    d = json.loads((tmp_path / "n4" / "2021Q4.json").read_text(encoding="utf-8"))
    assert r["err_champion"] == pytest.approx(100 * math.log(d["value"] / y))
    assert s["n3"].iloc[0]["status"] == "väntar"


def test_live_keys_per_target():
    assert set(pipeline.live_keys("n3")) >= {"rev_nvda_datacenter", "rev_nvda", "nvda_guid_rev_mid"}
    assert set(pipeline.live_keys("n4")) >= {*n4.COMPONENTS, *n4.RPO.components}
    assert set(pipeline.live_keys("n6")) >= {*n4.COMPONENTS, *n4.RPO.components}
    k5 = pipeline.live_keys("n5")
    assert k5 and all(k.startswith("btos_ai_use_") and not k.endswith("_se") for k in k5)
    assert "btos_ai_use_v1" not in k5  # closed regime


# ------------------------------------------------------------------ N5


def btos_table(n=12, version="v2", start="2025-11-23"):
    weeks = pd.period_range(TS(start), periods=n, freq="W-SUN")[::1]
    weeks = pd.PeriodIndex([weeks[0] + 2 * i for i in range(n)], freq="W-SUN")
    vals = 20 + 0.3 * np.arange(n) + np.sin(np.arange(n))
    return _rows(n5.key(version), weeks, vals, weeks.end_time.normalize() + pd.Timedelta(days=4), freq="2W")


def test_n5_backtest_origin_day_before_publication_and_b1_formula():
    t = pd.concat([btos_table(12, "v2"), btos_table(3, "v3", "2026-11-01")], ignore_index=True)
    f = n5.run(t)
    assert (pd.to_datetime(f["origin"]) == pd.to_datetime(f["outcome_known_from"]) - pd.Timedelta(days=1)).all()
    v2 = f[f.regime == "v2"].reset_index(drop=True)
    y = btos_table(12, "v2")["value"].to_numpy()
    r = v2[v2["n_regime"] == 7].iloc[0]  # the 8th publication: first with 7 earlier observations (F-B4)
    assert r["in_period"] and r["B1"] == pytest.approx(y[6] + (y[6] - y[0]) / 6 - y[7])
    assert r["B0"] == pytest.approx(y[6] - y[7])
    assert not f.loc[f.regime == "v3", "in_period"].any()  # never mixes regimes
    assert f.loc[f.regime == "v3", "B1"].isna().all()


def _schedule(tmp_path, rows, fetched="2020-01-01"):
    p = tmp_path / "schedule_log.parquet"
    pd.DataFrame([{"smpdt": s, "col_end": TS(c), "published": TS(pub), "fetched_at": TS(fetched)} for s, c, pub in rows]
                 ).to_parquet(p, index=False)
    return p


def test_n5_due_and_writer_follow_the_logged_schedule(tmp_path, monkeypatch):
    log = _schedule(tmp_path, [(202620, "2026-10-04", "2026-10-08"), (202621, "2026-10-18", "2026-10-22"),
                               (202622, "2026-11-01", "2026-11-05")])
    monkeypatch.setattr(n5, "schedule_path", lambda: log)
    assert pipeline.n5_due("2026-10-21") == pipeline.Due("n5", TS("2026-10-21"), "2026-10-18")
    assert pipeline.n5_due("2026-10-22") is None
    c = n5.scheduled_cycle("2026-11-04")
    assert c["regime"] == "v3" and c["previous_period"] is None  # first cycle of v3
    # B1 needs 7 earlier observations in the regime: no forecast, nothing written
    t = btos_table(6, "v2", "2026-07-12")
    with pytest.raises(n5.NotAvailable):
        n5.write_live(t, "2026-11-04", tmp_path / "out", today="2026-11-04")
    assert not (tmp_path / "out").exists() or not list((tmp_path / "out").glob("*.json"))
    assert pipeline.run_live(pipeline.Due("n5", TS("2026-11-04"), "2026-11-01"), tmp_path, t, refresh=False,
                             today="2026-11-04") is None


def test_n5_writer_writes_b1_with_additive_distribution(tmp_path, monkeypatch):
    t = btos_table(40, "v2", "2025-01-05")
    weeks = sorted(pd.PeriodIndex(t["period"], freq="W-SUN"))
    nxt = weeks[-1] + 2
    pub = nxt.end_time.normalize() + pd.Timedelta(days=4)
    log = _schedule(tmp_path, [(202601, str(weeks[-1].end_time.date()), "2026-01-01"),
                               (202602, str(nxt.end_time.date()), str(pub.date()))])
    monkeypatch.setattr(n5, "schedule_path", lambda: log)
    monkeypatch.setattr(n5.census_btos, "regime_of", lambda s: n5.census_btos.REGIMES[1])
    o = pub - pd.Timedelta(days=1)
    p = n5.write_live(t, o, tmp_path / "n5", today=o)
    d = json.loads(p.read_text(encoding="utf-8"))
    y = t.sort_values("period")["value"].to_numpy()
    assert d["value"] == pytest.approx(y[-1] + (y[-1] - y[-7]) / 6) and d["period"] == str(nxt)
    assert p.name == f"{nxt.end_time.date()}.json"
    if intervals.ENABLED:
        m = d["distribution"]["models"]["B1"]
        assert d["distribution"]["space"].startswith("percentage points")
        lo, hi = m["intervals"]["80"]
        assert lo < d["value"] < hi and hi - lo < 10  # levels in percent, not exp(log)
    with pytest.raises(FileExistsError):
        n5.write_live(t, o, tmp_path / "n5", today=o)
    # scorecard: error in percentage points
    out = pd.concat([t, _rows(n5.key("v2"), [nxt], [d["value"] - 1.0], [pub], freq="2W")], ignore_index=True)
    r = pipeline.score(tmp_path, out)["n5"].iloc[0]
    assert r["status"] == "utfall" and r["err_champion"] == pytest.approx(1.0)


def test_n5_refuses_untrusted_schedule_dates(tmp_path, monkeypatch):
    log = _schedule(tmp_path, [(202520, "2025-10-05", "2025-10-09"), (202702, "2027-01-31", "2027-02-04")])
    monkeypatch.setattr(n5, "schedule_path", lambda: log)
    assert pipeline.n5_due("2025-10-08") is None  # inside the funding lapse
    with pytest.raises(n5.NotAvailable, match="lapse"):
        n5.scheduled_cycle("2025-10-08")
    with pytest.raises(n5.NotAvailable, match="wording regime"):
        n5.scheduled_cycle("2027-02-03")
    monkeypatch.setattr(n5, "schedule_path", lambda: tmp_path / "missing.parquet")
    assert pipeline.n5_due("2027-02-03") is None  # no logged schedule: never guessed


def test_n5_schedule_is_read_as_known_on_the_origin(tmp_path, monkeypatch):
    log = _schedule(tmp_path, [(202621, "2026-10-18", "2026-10-22")], fetched="2026-10-25")
    monkeypatch.setattr(n5, "schedule_path", lambda: log)
    assert pipeline.n5_due("2026-10-21") is None  # the schedule was logged after the origin
