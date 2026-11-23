"""Freshness check (warehouse.fresh) and its wiring into `pipeline weekly`. Synthetic fixtures, no network."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from ai_tracker import catalog, config, observations, pipeline, warehouse


def spec(key="s", freq="M", lag=10, **kw) -> catalog.Spec:
    return catalog.Spec(key=key, branch="G6", label=key, unit="x", freq=freq, source="test",
                        fetch=lambda: pd.Series(dtype=float), lag_days=lag, license="unverified", **kw)


def series(freq: str, last: str, n: int = 3) -> pd.Series:
    """n periods of `freq` ending with the period that contains `last`."""
    end = pd.Period(last, freq=catalog.FREQS[freq])
    return pd.Series(1.0, index=pd.period_range(end=end, periods=n))


def table(*pairs, fetched=date(2020, 1, 1)) -> pd.DataFrame:
    t = observations._empty()
    for s, v in pairs:
        t = pd.concat([t, observations.new_rows(s, v, t, fetched)], ignore_index=True)
    return t


def stale(pairs, today) -> pd.DataFrame:
    specs = [s for s, _ in pairs]
    return warehouse.fresh(warehouse.connect(table(*pairs), specs), today)


# ------------------------------------------------------------------ the bound


@pytest.mark.parametrize("freq, lag, bound", [("D", 17, 48), ("W", 5, 42), ("2W", 4, 48), ("M", 10, 71),
                                              ("Q", 25, 147), ("A", 31, 431), ("A", -50, 350)])
def test_derived_bound_per_frequency(freq, lag, bound):
    assert warehouse.max_age_days(spec(freq=freq, lag=lag)) == bound


def test_override_replaces_derived_bound():
    assert warehouse.max_age_days(spec(freq="M", lag=10, max_age_days=200, note="why")) == 200


# ------------------------------------------------------------------ fresh / stale per frequency


@pytest.mark.parametrize("freq, lag, last", [
    ("D", 17, "2026-10-31"), ("W", 5, "2026-10-04"), ("2W", 4, "2026-10-11"), ("M", 10, "2026-09"),
    ("Q", 25, "2026Q2"), ("A", 31, "2025")])
def test_fresh_on_the_bound_and_stale_one_day_after(freq, lag, last):
    s = spec(freq=freq, lag=lag)
    v = series(freq, last)
    end = v.index[-1].end_time.normalize()
    on_bound = end + pd.Timedelta(days=warehouse.max_age_days(s))
    assert stale([(s, v)], on_bound).empty
    out = stale([(s, v)], on_bound + pd.Timedelta(days=1))
    assert list(out["series"]) == ["s"]
    r = out.iloc[0]
    assert r["age_days"] == warehouse.max_age_days(s) + 1 and r["max_age_days"] == warehouse.max_age_days(s)
    assert r["last_period"] == str(v.index[-1]) and r["bound"] == "derived"


def test_annual_series_a_year_old_is_fresh():
    s = spec(key="eu", freq="A", lag=31)
    v = series("A", "2025")  # 2025 released early 2026; 2026 expected December 2026
    assert stale([(s, v)], "2026-12-15").empty
    assert stale([(s, v)], "2027-03-07").empty  # 2025-12-31 + 431 days
    assert list(stale([(s, v)], "2027-03-08")["series"]) == ["eu"]


def test_announced_annual_value_with_negative_lag():
    s = spec(key="scb", freq="A", lag=-50)  # 2026 known 2026-11-11, before the year ends
    v = series("A", "2026", n=1)
    assert stale([(s, v)], "2026-11-23").empty
    assert stale([(s, v)], "2027-12-16").empty
    assert len(stale([(s, v)], "2027-12-17")) == 1


def test_closed_series_is_never_stale():
    s = spec(key="old", closed=True, note="ended 2012")
    assert stale([(s, series("M", "2012-12"))], "2026-11-23").empty


def test_override_moves_the_bound():
    s = spec(key="nvda", freq="Q", lag=25, max_age_days=199, note="fiscal offset")
    v = series("Q", "2026Q2")
    assert stale([(s, v)], "2026-12-01").empty  # derived bound (147) would flag this
    out = stale([(s, v)], "2027-01-16")  # 2026-06-30 + 199 days + 1
    assert list(out["bound"]) == ["override"] and out["max_age_days"].iloc[0] == 199


def test_series_without_rows_is_stale():
    s, empty = spec(key="never"), spec(key="ok")
    out = warehouse.fresh(warehouse.connect(table((empty, series("M", "2026-10"))), [s, empty]), "2026-11-23")
    assert list(out["series"]) == ["never"] and pd.isna(out["age_days"].iloc[0])
    assert "no data" in warehouse.describe_stale(out)[0]


def test_only_rows_known_on_today_count():
    s = spec(key="rel", freq="Q", lag=25)
    filings = pd.DataFrame({"period": ["2026Q1", "2026Q2"], "value": [1.0, 2.0],
                            "known_from": ["2026-04-29", "2026-07-29"]})
    t = observations.new_rows(s, filings, observations._empty(), date(2026, 8, 1))
    con = warehouse.connect(t, [s])
    assert warehouse.fresh(con, "2026-08-24").empty  # 2026Q2 known: age 55 d
    early = warehouse.fresh(con, "2026-07-28")  # only 2026Q1 known on that day
    assert early.empty and warehouse.fresh(con, "2026-08-26").empty
    assert list(warehouse.fresh(con, "2026-12-01")["last_period"]) == ["2026Q2"]


def test_revision_of_old_periods_does_not_make_a_series_fresh():
    s = spec(key="rev", freq="M", lag=10)
    t = table((s, series("M", "2026-03")))
    revised = observations.new_rows(s, series("M", "2026-03") * 2, t, date(2026, 11, 20))
    t = pd.concat([t, revised], ignore_index=True)
    assert (t["source"] == "revision").any()
    assert list(warehouse.fresh(warehouse.connect(t, [s]), "2026-11-23")["series"]) == ["rev"]


def test_known_stale_is_accepted_until_its_date(monkeypatch):
    s = spec(key="out", freq="M", lag=35)
    pairs = [(s, series("M", "2025-08"))]
    monkeypatch.setattr(warehouse, "KNOWN_STALE", {"out": ("2025-12-31", "shutdown")})
    assert stale(pairs, "2025-12-31").empty
    assert len(stale(pairs, "2026-01-01")) == 1


def test_real_catalog_closed_and_overrides_have_reasons():
    specs = catalog.by_key()
    for key in ("tsmc_revenue_parent_m", "scb_ai_ent_se", "btos_ai_use_v1", "btos_ai_expect_v2_se"):
        assert specs[key].closed and "Avslutad" in specs[key].note, key
    assert not specs["btos_ai_use_v3"].closed and not specs["scb_ai_ent_se_nace21"].closed
    for s in catalog.ALL:
        if s.max_age_days is not None:
            assert "Aktualitet" in s.note, s.key


def test_validate_flags_bad_freshness_fields():
    errors = " ".join(catalog.validate([spec(key="a", max_age_days=0, note="x"), spec(key="b", closed=True)]))
    assert "a: max_age_days must be positive" in errors and "b: closed or max_age_days needs a reason" in errors


# ------------------------------------------------------------------ pipeline weekly


@pytest.fixture
def weekly_env(tmp_path, monkeypatch):
    ok, old, gone = spec(key="ok_m"), spec(key="old_m"), spec(key="gone_m", closed=True, note="ended")
    path = tmp_path / "observations.parquet"
    observations.save(table((ok, series("M", "2026-10", n=12)), (old, series("M", "2026-05")),
                            (gone, series("M", "2012-12"))), path)
    monkeypatch.setattr(observations, "PATH", path)
    monkeypatch.setattr(catalog, "ALL", [ok, old, gone])
    monkeypatch.setattr(config, "get", lambda name, default=None: "test-agent")
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    return summary


def test_weekly_fails_on_stale_series_and_says_whether_the_fetch_failed(weekly_env, monkeypatch, capsys):
    monkeypatch.setattr(observations, "refresh", lambda keys=None: {"ok_m": "ok +0", "old_m": "FAILED: HTTP 404"})
    assert pipeline.weekly(today="2026-11-23") == pipeline.STALE_EXIT
    out = capsys.readouterr().out
    assert "fetch failed: old_m" in out  # the warning
    assert "old_m (M): newest period 2026-05" in out and "fetch FAILED this run" in out
    assert "ok_m (M)" not in out and "gone_m (M)" not in out
    text = weekly_env.read_text(encoding="utf-8")
    assert "1 stale series" in text and "- stale: old_m" in text and "- fetch failed: `old_m`" in text


def test_weekly_stale_without_fetch_failure(weekly_env, monkeypatch, capsys):
    monkeypatch.setattr(observations, "refresh", lambda keys=None: {"ok_m": "ok +0", "old_m": "ok +0"})
    assert pipeline.weekly(today="2026-11-23") == pipeline.STALE_EXIT
    assert "fetch ok but no new period" in capsys.readouterr().out


def test_weekly_passes_when_fresh_and_scopes_to_keys(weekly_env, monkeypatch):
    monkeypatch.setattr(observations, "refresh", lambda keys=None: {"ok_m": "FAILED: timeout"})
    assert pipeline.weekly(["ok_m"], today="2026-11-23") == 0  # failed fetch, data still fresh: warning only
    assert pipeline.weekly(today="2026-07-15") == 0  # everything fresh on that day


def test_weekly_integrity_failure_wins_over_stale(weekly_env, monkeypatch):
    monkeypatch.setattr(observations, "refresh", lambda keys=None: {})
    monkeypatch.setattr(warehouse, "run_checks", lambda con=None: {"unique_key": pd.DataFrame({"series": ["a"]})})
    assert pipeline.weekly(today="2026-11-23") == 1


def test_cli_exit_code_for_stale(weekly_env, monkeypatch):
    monkeypatch.setattr(observations, "refresh", lambda keys=None: {})
    monkeypatch.setattr(pipeline, "utc_today", lambda: pd.Timestamp("2026-11-23"))
    assert pipeline.main(["weekly"]) == pipeline.STALE_EXIT
