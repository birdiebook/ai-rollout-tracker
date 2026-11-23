"""Cloudflare Radar (track B3): response parsing, week windows, job CSV and log round trip. No network."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from ai_tracker import catalog, observations
from ai_tracker.jobs import cloudflare_radar as job
from ai_tracker.series import cloudflare_radar as series
from ai_tracker.sources import cloudflare_radar as cf

TODAY = pd.Timestamp("2026-11-23")  # a Monday


def _result(starts: list[str], groups: dict[str, list]) -> dict:
    return {"meta": {"lastUpdated": "2026-11-23T20:45:00Z", "normalization": "PERCENTAGE",
                     "confidenceInfo": {"level": 5, "annotations": []}},
            "serie_0": {"timestamps": [f"{s}T00:00:00Z" for s in starts],
                        **{g: [None if v is None else str(v) for v in vals] for g, vals in groups.items()}}}


def test_parse_groups_long_format():
    df = cf.parse_groups(_result(["2026-11-02", "2026-11-09"], {"AI_BOT": [4.5, 5.0], "HUMAN": [60, 61]}))
    assert set(df["group"]) == {"AI_BOT", "HUMAN"}
    assert df.loc[df["group"] == "AI_BOT", "value"].tolist() == [4.5, 5.0]


def test_weekly_keeps_complete_weeks_on_w_sun():
    res = _result(["2026-11-02", "2026-11-09", "2026-11-16", "2026-11-23"], {"AI_BOT": [1, 2, 3, 4]})
    s = cf.weekly(res, "AI_BOT", TODAY)
    assert list(s.index.astype(str)) == ["2026-11-02/2026-11-08", "2026-11-09/2026-11-15", "2026-11-16/2026-11-22"]
    assert s.tolist() == [1.0, 2.0, 3.0]


def test_weekly_refuses_unaligned_buckets_and_unknown_groups():
    with pytest.raises(ValueError, match="Mondays"):
        cf.weekly(_result(["2026-11-03"], {"AI_BOT": [1]}), "AI_BOT", TODAY)
    with pytest.raises(ValueError, match="not in Radar response"):
        cf.weekly(_result(["2026-11-02"], {"HUMAN": [1]}), "AI_BOT", TODAY)


def test_windows_are_whole_weeks_and_capped():
    w = cf.windows("2024-01-01", TODAY)
    assert w[0]["dateStart"] == "2024-01-01T00:00:00Z" and w[-1]["dateEnd"] == "2026-11-23T00:00:00Z"
    for a, b in zip(w, w[1:]):
        assert a["dateEnd"] == b["dateStart"]
    for x in w:
        span = pd.Timestamp(x["dateEnd"]) - pd.Timestamp(x["dateStart"])
        assert span <= pd.Timedelta(weeks=cf.CHUNK_WEEKS) and span.days % 7 == 0
        assert pd.Timestamp(x["dateStart"]).dayofweek == 0
    assert cf.windows("2024-01-03", TODAY)[0]["dateStart"] == "2024-01-08T00:00:00Z"  # next Monday


def test_fetch_query_joins_windows(monkeypatch):
    calls = []

    def fake_get(path, params, **kw):
        calls.append(params)
        start = pd.Timestamp(params["dateStart"][:10])
        end = pd.Timestamp(params["dateEnd"][:10])
        starts = [str(d.date()) for d in pd.date_range(start, end - pd.Timedelta(days=7), freq="7D")]
        return _result(starts, {"AI_BOT": [float(i + 1) for i in range(len(starts))]})
    monkeypatch.setattr(cf, "get", fake_get)
    q = cf.Query("/bots/crawlers/timeseries_groups/CLIENT_TYPE", "AI_BOT", {"normalization": "PERCENTAGE"},
                 start="2025-06-02")
    s, metas = cf.fetch_query(q, TODAY)
    assert len(calls) == len(metas) == 2 and all(c["aggInterval"] == "1w" for c in calls)
    assert s.index.is_unique and s.index.is_monotonic_increasing
    assert str(s.index[0]) == "2025-06-02/2025-06-08" and str(s.index[-1]) == "2026-11-16/2026-11-22"
    assert len(s) == len(pd.period_range("2025-06-02", "2026-11-22", freq="W-SUN"))


def test_get_reports_api_error_without_token(monkeypatch):
    class R:
        status_code, ok = 400, False

        def json(self):
            return {"success": False, "errors": [{"code": 1, "message": "dateRange too large"}]}
    seen = {}

    def fake_requests_get(url, params, headers, timeout):
        seen.update(headers)
        return R()
    monkeypatch.setenv(cf.TOKEN_ENV, "dummy-not-a-token")
    monkeypatch.setattr(cf.requests, "get", fake_requests_get)
    with pytest.raises(RuntimeError, match="dateRange too large") as e:
        cf.get("/ai/bots/timeseries", {})
    assert "dummy-not-a-token" not in str(e.value)
    assert seen["Authorization"] == "Bearer dummy-not-a-token" and "ai-rollout-tracker" in seen["User-Agent"]


def test_log_line_round_trip(tmp_path):
    s = pd.Series([1.5, 2.0, 3.25], index=pd.PeriodIndex(["2026-11-02/2026-11-08", "2026-11-09/2026-11-15",
                                                         "2026-11-23/2026-11-29"], freq="W-SUN"))
    line = cf.log_line("k1", s, [{"lastUpdated": "2026-11-23T20:45:00Z"}])
    rec = json.loads(line.removeprefix("RADAR "))
    assert rec["values"] == [1.5, 2.0, None, 3.25] and rec["start"] == "2026-11-02"
    log = f"2026-11-23T21:07:44.1Z noise\n2026-11-23T21:07:44.2Z {line}\n"
    assert cf.from_log(log, tmp_path) == ["k1"]
    back = cf.load_job_csv("k1", tmp_path)
    pd.testing.assert_series_equal(back, s, check_names=False, check_freq=False)


def test_series_reads_job_dir_without_token(tmp_path, monkeypatch):
    monkeypatch.delenv(cf.TOKEN_ENV, raising=False)
    monkeypatch.setattr(cf.config, "get", lambda name, default=None: str(tmp_path) if name == cf.JOB_DIR_ENV
                        else default)
    key = next(iter(series.QUERIES))
    cf.write_job_csv(tmp_path, key, pd.Series([7.0], index=pd.PeriodIndex(["2026-11-16/2026-11-22"],
                                                                          freq="W-SUN")))
    assert catalog.by_key()[key].fetch().tolist() == [7.0]
    monkeypatch.setattr(cf.config, "get", lambda name, default=None: default)
    with pytest.raises(RuntimeError, match="CLOUDFLARE_API_TOKEN"):
        catalog.by_key()[key].fetch()


def test_job_writes_csv_meta_and_log(tmp_path, monkeypatch, capsys):
    s = pd.Series([1.0], index=pd.PeriodIndex(["2026-11-16/2026-11-22"], freq="W-SUN"))
    monkeypatch.setattr(cf, "fetch_query", lambda q, today=None: (s, [{"lastUpdated": "x"}]))
    job.run(tmp_path)
    for key in series.QUERIES:
        assert cf.job_csv(tmp_path, key).exists()
    assert json.loads((tmp_path / "meta.json").read_text())["failed"] == {}
    assert capsys.readouterr().out.count("RADAR {") == len(series.QUERIES)


def test_job_fails_after_trying_every_series(tmp_path, monkeypatch):
    def boom(q, today=None):
        raise RuntimeError("HTTP 403")
    monkeypatch.setattr(cf, "fetch_query", boom)
    with pytest.raises(SystemExit):
        job.run(tmp_path)
    assert set(json.loads((tmp_path / "meta.json").read_text())["failed"]) == set(series.QUERIES)


def test_specs_valid():
    assert catalog.validate(series.SPECS) == []
    assert {s.key for s in series.SPECS} == set(series.QUERIES)
    assert {s.branch for s in series.SPECS} == {"G3"} and {s.freq for s in series.SPECS} == {"W"}
    assert all("CC BY-NC 4.0" in s.license for s in series.SPECS)
    for q in series.QUERIES.values():
        assert q.params.get("normalization", "PERCENTAGE") == "PERCENTAGE"  # never min-max scaled volumes


def test_known_from_is_week_end_plus_lag():
    key = next(iter(series.QUERIES))
    spec = catalog.by_key()[key]
    values = pd.Series([1.0], index=pd.PeriodIndex(["2026-11-16/2026-11-22"], freq="W-SUN"))
    rows = observations.new_rows(spec, values, observations._empty(), fetched_at=pd.Timestamp("2026-11-24").date())
    assert rows["known_from"].iloc[0] == pd.Timestamp("2026-11-22") + pd.Timedelta(days=spec.lag_days)


def test_weekly_drops_zero_padding_before_data_starts():
    res = _result(["2024-12-23", "2024-12-30", "2025-01-06"], {"AI_BOT": [0.0, 0.0, 4.0], "HUMAN": [0.0, 0.0, 96.0]})
    s = cf.weekly(res, "AI_BOT", TODAY)
    assert list(s.index.astype(str)) == ["2025-01-06/2025-01-12"]
    res = _result(["2025-01-06"], {"AI_BOT": [0.0], "HUMAN": [100.0]})  # a real 0 share is kept
    assert cf.weekly(res, "AI_BOT", TODAY).tolist() == [0.0]
