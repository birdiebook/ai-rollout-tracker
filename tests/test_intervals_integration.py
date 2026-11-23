"""Track C1 integration behind the grind G-C flag: backtests, live files, scorecard and site.

Synthetic data only. With intervals.ENABLED False nothing changes (the flag-off tests set it explicitly); the tests turn it on with
monkeypatch to check the wiring before the register entry exists.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from ai_tracker import catalog, pipeline
from ai_tracker.nowcast import intervals, n1, n2
from ai_tracker.site import data as D
from ai_tracker.site import render as R
from ai_tracker.state import measures as M

TS = pd.Timestamp


def _rows(series, freq, periods, values, known_from, source="release"):
    return pd.DataFrame({"series": series, "freq": freq, "period": [str(p) for p in periods],
                         "value": np.asarray(values, dtype=float), "known_from": pd.to_datetime(known_from),
                         "source": source, "fetched_at": TS("2026-11-23")})


def n2_table(last="2014-10", seed=3):
    """Random-walk TSMC (6-K day 10 of m+1) and imports; always drawn through 2024-12, then cut at `last`, so a
    longer table extends a shorter one with the same values."""
    rng = np.random.default_rng(seed)
    months = pd.period_range("2005-01", "2024-12", freq="M")
    tsmc = 1e5 * np.exp(np.cumsum(0.01 + 0.05 * rng.standard_normal(len(months))))
    imp = 1e3 * np.exp(np.cumsum(0.005 + 0.03 * rng.standard_normal(len(months))))
    return pd.concat([
        _rows(n2.TARGET, "M", months, tsmc, [(p + 1).start_time + pd.Timedelta(days=9) for p in months]),
        _rows("us_imports_tw_m", "M", months, imp, months.end_time.normalize() + pd.Timedelta(days=41), "backfill"),
    ], ignore_index=True).query("period <= @last").reset_index(drop=True)


def n1_table(seed=0):
    rng = np.random.default_rng(seed)
    months = pd.period_range("2009-01", "2020-12", freq="M")
    parts, qmean = [], {}
    for key, lag in ((n1.INDICATORS[0], 41), (n1.INDICATORS[1], 35)):
        lvl = pd.Series(1000 * np.exp(np.cumsum(0.01 + 0.03 * rng.standard_normal(len(months)))), index=months)
        qmean[key] = np.log(lvl).groupby(lvl.index.asfreq("Q-DEC")).mean()
        parts.append(_rows(key, "M", months, lvl.to_numpy(), months.end_time.normalize() + pd.Timedelta(days=lag),
                           "backfill"))
    quarters = pd.period_range("2010Q1", "2020Q3", freq="Q-DEC")
    a, b = n1.INDICATORS
    g = 0.02 + 0.5 * qmean[a].diff() + 0.3 * qmean[b].diff() + 0.02 * rng.standard_normal(len(qmean[a]))
    capex = 500 * np.exp(g.loc[quarters].cumsum())
    parts.append(_rows(n1.TARGET, "Q", quarters, capex.to_numpy(), quarters.end_time.normalize() + pd.Timedelta(days=30)))
    return pd.concat(parts, ignore_index=True)


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setattr(intervals, "ENABLED", True)


# ------------------------------------------------------------------ flag off: nothing changes


def test_flag_off_live_files_have_no_distribution(tmp_path, monkeypatch):
    monkeypatch.setattr(intervals, "ENABLED", False)
    d = json.loads(n2.write("2014-12-05", n2_table(), tmp_path).read_text(encoding="utf-8"))
    assert "distribution" not in d
    assert "distribution" not in n1.live_payload(n1_table(), n1.origin_for(pd.Period("2019Q2", "Q-DEC")))


# ------------------------------------------------------------------ N2


def test_n2_live_distribution_uses_only_errors_known_at_origin(on, tmp_path):
    table = n2_table()
    origin = TS("2014-12-05")  # target 2014-11; the 2014-11 6-K comes 2014-12-10
    d = json.loads(n2.write(origin, table, tmp_path).read_text(encoding="utf-8"))
    block = d["distribution"]
    assert block["registered"] == intervals.REGISTER_REF
    frame = n2.run(table[table["known_from"] <= origin])
    for v in n2.VARIANTS:
        m = block["models"][v]
        assert m["n_pool"] == int(frame[f"e_{v}"].notna().sum())
        assert (frame["outcome_known_from"] <= origin).all()
    champ = block["models"][d["champion"]]
    q = [champ["quantiles"][k] for k in block["quantile_levels"]]
    assert q == sorted(q) and q[0] < d["value"] < q[-1]
    # rows known after the origin (later months, a late revision) change nothing in the stored distribution
    later = pd.concat([n2_table(last="2016-06"),
                       _rows(n2.TARGET, "M", [pd.Period("2013-05", "M")], [1.0], ["2015-01-01"], "revision")])
    again = n2.live_distribution(n2.forecast(origin, later), later)
    assert json.loads(json.dumps(again)) == block


def test_n2_backtest_interval_evaluation_on_synthetic_frame(on):
    frame = n2.run(n2_table(last="2019-11"))
    out = n2.evaluate_intervals(frame)
    cal = out["full"]["calibration"].set_index("model")
    assert set(cal.index) == set(n2.VARIANTS) and out["full"]["best_baseline"] in ("B0", "B1")
    # each model on its own rows: V1 starts later (60 training months, then MIN_ERRORS own errors)
    assert cal.at["V1", "first"] > cal.at["B1", "first"]
    assert cal.at["B0", "n"] == int(frame["e_B0"].notna().sum()) - intervals.MIN_ERRORS
    # the synthetic target is a random walk with iid shocks: B0's errors are iid, so its intervals are calibrated
    for L in intervals.LEVELS:
        assert cal.at["B0", f"coverage_{intervals.level_key(L)}"] == pytest.approx(L, abs=0.08)
    assert out["2023+"]["n_periods"] == 0  # the fixture ends 2019
    md = intervals.markdown(out["full"], "N2 intervals full")
    assert "| B0 |" in md and "Calibrated" in md
    assert "no model" in intervals.markdown(out["2023+"], "N2 intervals 2023+")


# ------------------------------------------------------------------ N1


def test_n1_live_distribution_and_backtest(on):
    table = n1_table()
    origin = n1.origin_for(pd.Period("2019Q2", "Q-DEC"))
    d = n1.live_payload(table, origin)
    block = d["distribution"]
    err = n1.backtest_unit(table[table["known_from"] <= origin], n1.TARGET)
    assert (err["outcome_known_from"] <= origin).all()
    assert block["models"]["B1"]["n_pool"] == int(err["B1"].notna().sum())
    assert block["models"]["B1"]["method"] == "student_t"  # fewer than 40 quarters
    assert d2_equal(n1.live_payload(pd.concat([table, _rows(n1.TARGET, "Q", [pd.Period("2018Q1", "Q-DEC")], [1.0],
                                                             ["2019-12-01"], "revision")]), origin)["distribution"],
                    block)
    res = n1.evaluate_intervals(n1.backtest_unit(table, n1.TARGET))
    assert set(res) == {"full", "2023Q1-"} and res["2023Q1-"]["n_periods"] == 0
    cal = res["full"]["calibration"].set_index("model")
    assert {"B0", "B1", "V1", "V2"} <= set(cal.index) and "B2" not in cal.index  # B2 needs company series
    assert cal.at["V1", "first"] > cal.at["B1", "first"]


def d2_equal(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_n1_interval_scores_pool_per_unit(on):
    """N1b: pools never mix companies."""
    t = n1_table()
    e1 = n1.backtest_unit(t, n1.TARGET)
    e2 = e1.assign(unit="other", B1=e1["B1"] + 100)  # a second unit with very different errors
    s = n1.interval_scores(pd.concat([e1, e2], ignore_index=True))
    one = s[(s["unit"] == n1.TARGET) & (s["model"] == "B1") & s["method"].notna()]
    assert (one["eq_0.975"] < 50).all()


# ------------------------------------------------------------------ scorecard and site


def _forecast_with_distribution(root, table):
    path = n2.write("2014-12-05", table, root / "n2")
    return json.loads(path.read_text(encoding="utf-8")), path


def test_scorecard_scores_the_stored_distribution(on, tmp_path):
    table = n2_table()
    d, path = _forecast_with_distribution(tmp_path, table)
    before = path.read_bytes()
    lo, hi = d["distribution"]["models"][d["champion"]]["intervals"]["80"]
    outcome = (lo + hi) / 2
    scored = pd.concat([table, _rows(n2.TARGET, "M", [pd.Period("2014-11", "M")], [outcome], ["2014-12-10"])])
    row = pipeline.score(tmp_path, scored)["n2"].iloc[0]
    assert row["status"] == "utfall" and row["hit_80_champion"] == 1.0 and row["crps_champion"] >= 0
    dist = intervals.ErrorDistribution.from_json(d["distribution"]["models"][d["champion"]])
    assert row["crps_champion"] == pytest.approx(dist.crps(row["err_champion"]))
    assert row["interval_80"] == [lo, hi]
    md = pipeline.render(pipeline.score(tmp_path, scored), today="2015-01-01")
    assert "### Intervall" in md and "Täckning 80 %" in md
    assert path.read_bytes() == before


def test_scorecard_without_flag_has_no_interval_section(tmp_path, monkeypatch):
    monkeypatch.setattr(intervals, "ENABLED", False)
    table = n2_table()
    n2.write("2014-12-05", table, tmp_path / "n2")
    md = pipeline.render(pipeline.score(tmp_path, table), today="2015-01-01")
    assert "### Intervall" not in md


def test_site_shows_the_champions_interval(on, tmp_path):
    table = n2_table()
    d, _ = _forecast_with_distribution(tmp_path, table)
    lo, hi = d["distribution"]["models"][d["champion"]]["intervals"]["80"]
    full = pd.concat([table, _rows(n2.TARGET, "M", [pd.Period("2014-11", "M")], [hi * 1.5], ["2014-12-10"])])
    spec = catalog.Spec(key=n2.TARGET, branch="G6", label="TSMC", unit="mn TWD", freq="M", source="test",
                        fetch=lambda: pd.Series(dtype=float), lag_days=10, license="CC BY 4.0 (test)", publish=True)
    ctx = M.Context(full, specs={n2.TARGET: spec}, derived={}, core={}, forecasts=tmp_path, selection=lambda w: [])
    doc = D.nowcasts(ctx, tmp_path, "2015-01-01")
    nc = next(n for n in doc["nowcasts"] if n["id"] == "n2")
    f = nc["forecasts"][0]
    assert f["intervals"]["80"] == [D._num(lo, 6), D._num(hi, 6)] and "distribution" not in f
    champ = next(c for c in nc["coverage"] if c["variant"] == "champion")
    assert champ["n"] == 1 and champ["coverage_80"] == 0.0  # the outcome is far above the 80 % interval
    html = R.nowcast_section(nc, {"repo": "https://example.invalid/r"})
    assert "80 % intervall" in html and "Täckning 95 %" in html
    assert json.dumps(doc)  # JSON-safe
    assert "pool" not in json.dumps(doc)  # the error pool stays in the forecast file


def test_site_without_flag_has_no_interval_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(intervals, "ENABLED", False)
    table = n2_table()
    n2.write("2014-12-05", table, tmp_path / "n2")
    spec = catalog.Spec(key=n2.TARGET, branch="G6", label="TSMC", unit="mn TWD", freq="M", source="test",
                        fetch=lambda: pd.Series(dtype=float), lag_days=10, license="CC BY 4.0 (test)", publish=True)
    ctx = M.Context(table, specs={n2.TARGET: spec}, derived={}, core={}, forecasts=tmp_path, selection=lambda w: [])
    nc = next(n for n in D.nowcasts(ctx, tmp_path, "2015-01-01")["nowcasts"] if n["id"] == "n2")
    assert "intervals" not in nc["forecasts"][0] and nc["coverage"] == []
    assert "80 % intervall" not in R.nowcast_section(nc, {"repo": "https://example.invalid/r"})
    assert not math.isnan(nc["forecasts"][0]["value"])


def test_n2_live_pool_includes_committed_live_errors(on, tmp_path):
    """F-C4: a committed live forecast whose outcome is known at the next origin enters the pool (replacing the
    reconstruction of its month); one whose outcome is not yet known does not."""
    table = n2_table(last="2014-12")
    n2_dir = tmp_path / "n2"
    first = json.loads(n2.write("2014-12-05", n2_table(last="2014-10"), n2_dir).read_text(encoding="utf-8"))
    later = pd.concat([table, _rows(n2.TARGET, "M", [pd.Period("2014-12", "M")], [1.0], ["2015-01-10"])])
    # origin 2015-01-05: 2014-11 is known (2014-12-10), so the live 2014-11 error is in the pool
    d = n2.live_distribution(n2.forecast("2015-01-05", table), table, n2_dir)
    y = float(table[(table["series"] == n2.TARGET) & (table["period"] == "2014-11")]["value"].iloc[0])
    e_live = round(100 * (math.log(first["variants"]["B1"]) - math.log(y)), intervals.POOL_DECIMALS)
    assert d["models"]["B1"]["n_live"] == 1 and e_live in d["models"]["B1"]["pool"]
    without = n2.live_distribution(n2.forecast("2015-01-05", table), table, None)
    assert without["models"]["B1"]["n_pool"] == d["models"]["B1"]["n_pool"]  # replaced, not added
    # at the 2014-11 origin itself its outcome (2014-12-10) is not known: the live file never enters its own pool
    fc = n2.forecast("2014-12-05", n2_table(last="2014-10"))
    early = n2.live_distribution(fc, later, n2_dir)
    assert early["models"]["B1"]["n_live"] == 0
