"""Wikipedia pageviews (track B3): parsing, weekly sums, page moves, known_from. No network."""

from __future__ import annotations

import json

import pandas as pd
import pytest
import requests

from ai_tracker import catalog, observations
from ai_tracker.series import wikipedia as series
from ai_tracker.sources import wikipedia as wp


@pytest.fixture(autouse=True)
def _own_raw_dir(tmp_path, monkeypatch):
    """Never read the shared raw cache (a real fetch today would answer instead of the fakes)."""
    monkeypatch.setattr(wp.http, "RAW_DIR", tmp_path / "raw")


def _payload(days: dict[str, int]) -> dict:
    return {"items": [{"project": "en.wikipedia", "article": "X", "granularity": "daily",
                       "timestamp": d.replace("-", "") + "00", "access": "all-access", "agent": "user", "views": v}
                      for d, v in days.items()]}


def test_parse_daily():
    s = wp.parse(_payload({"2025-01-01": 5, "2025-01-02": 7}))
    assert list(s.index.strftime("%Y-%m-%d")) == ["2025-01-01", "2025-01-02"]
    assert s.tolist() == [5.0, 7.0]
    assert wp.parse({"items": []}).empty


def test_url_quotes_title():
    u = wp.url("en", "Claude (AI)", "20261122")
    assert u.endswith("/en.wikipedia/all-access/user/Claude_%28AI%29/daily/20150701/20261122")
    assert "%E5%A4%A7" in wp.url("ja", "大規模言語モデル", "20261122")


def test_weekly_sum_missing_days_are_zero_and_partial_last_week_dropped():
    # Mon 2025-01-06 .. Sun 2025-01-12 full week with one day missing; next week only Mon-Tue
    days = {f"2025-01-{d:02d}": 10 for d in range(6, 13) if d != 8} | {"2025-01-13": 3, "2025-01-14": 4}
    w = wp.weekly_sum([wp.parse(_payload(days))])
    assert list(w.index.astype(str)) == ["2025-01-06/2025-01-12"]
    assert w.iloc[0] == 60.0


def test_weekly_sum_adds_former_titles_and_languages():
    a = wp.parse(_payload({f"2025-01-{d:02d}": 1 for d in range(6, 13)}))  # current title
    b = wp.parse(_payload({"2025-01-06": 100}))  # former title (redirect after the move)
    w = wp.weekly_sum([a, b, pd.Series(dtype=float)])
    assert w.iloc[0] == 107.0


def test_weekly_sum_drops_the_partial_first_api_week():
    days = {f"2015-07-{d:02d}": 1 for d in range(1, 13)}  # API starts Wed 2015-07-01
    w = wp.weekly_sum([wp.parse(_payload(days))])
    assert list(w.index.astype(str)) == ["2015-07-06/2015-07-12"]


def test_weekly_sum_without_data_raises():
    with pytest.raises(ValueError):
        wp.weekly_sum([pd.Series(dtype=float)])


def test_daily_404_means_no_views(monkeypatch):
    def fake_get(url, source, **kw):
        r = requests.Response()
        r.status_code = 404
        raise requests.HTTPError(response=r)
    monkeypatch.setattr(wp.http, "get", fake_get)
    assert wp.daily("en", "Nope", pd.Timestamp("2026-11-23")).empty


def test_daily_other_errors_raise(monkeypatch):
    def fake_get(url, source, **kw):
        r = requests.Response()
        r.status_code = 503
        raise requests.HTTPError(response=r)
    monkeypatch.setattr(wp.http, "get", fake_get)
    with pytest.raises(requests.HTTPError):
        wp.daily("en", "X", pd.Timestamp("2026-11-23"))


def test_daily_asks_until_yesterday(monkeypatch):
    seen = {}

    class R:
        def json(self):
            return _payload({"2026-11-22": 1})

    def fake_get(url, source, **kw):
        seen["url"] = url
        return R()
    monkeypatch.setattr(wp.http, "get", fake_get)
    wp.daily("de", "OpenAI", pd.Timestamp("2026-11-23"))
    assert seen["url"].endswith("/de.wikipedia/all-access/user/OpenAI/daily/20150701/20261122")


def test_topic_weekly_uses_every_title_of_the_languages(monkeypatch):
    calls = []

    def fake_daily(lang, title, today=None):
        calls.append((lang, title))
        return wp.parse(_payload({f"2025-01-{d:02d}": 1 for d in range(6, 13)}))
    monkeypatch.setattr(wp, "daily", fake_daily)
    w = wp.topic_weekly("gemini", ("en", "de"))
    assert calls == [("en", t) for t in wp.TOPICS["gemini"]["en"]] + [("de", "Google Gemini")]
    assert w.iloc[0] == 7.0 * len(calls)


def test_topics_cover_every_language():
    for topic, langs in wp.TOPICS.items():
        assert set(langs) == set(wp.LANGS), topic
        assert all(titles and all(t.strip() for t in titles) for titles in langs.values()), topic
        assert all(len(set(titles)) == len(titles) for titles in langs.values()), topic


def test_specs_valid():
    assert len(series.SPECS) == 2 * len(wp.TOPICS)
    assert catalog.validate(series.SPECS) == []
    assert {s.branch for s in series.SPECS} == {"G3"} and {s.freq for s in series.SPECS} == {"W"}
    assert all(s.publish and s.license.startswith("CC0") for s in series.SPECS)
    assert {s.key for s in series.SPECS} <= set(catalog.by_key())


def test_known_from_is_week_end_plus_lag():
    spec = catalog.by_key()["g3_wiki_chatgpt_en"]
    values = pd.Series([1.0, 2.0], index=pd.PeriodIndex(["2026-11-09/2026-11-15", "2026-11-16/2026-11-22"],
                                                        freq="W-SUN"))
    rows = observations.new_rows(spec, values, observations._empty(), fetched_at=pd.Timestamp("2026-11-24").date())
    assert rows["known_from"].dt.strftime("%Y-%m-%d").tolist() == ["2026-11-17", "2026-11-24"]
    assert set(rows["source"]) == {"backfill"}


def test_product_topics_count_from_launch(monkeypatch):
    # a generic title with views long before the product existed (de "Claude" since 2015)
    old = {f"2023-03-{d:02d}": 50 for d in range(6, 20)}
    monkeypatch.setattr(wp, "daily", lambda lang, title, today=None: wp.parse(_payload(old)))
    w = wp.topic_weekly("claude", ("de",))  # launch 2023-03-14 (Tuesday)
    assert list(w.index.astype(str)) == ["2023-03-13/2023-03-19"]
    assert w.iloc[0] == 50 * 6  # 14th..19th only
    assert set(wp.LAUNCH) <= set(wp.TOPICS)


def test_get_waits_out_429(monkeypatch):
    calls, slept = [], []

    def fake_get(url, source, retries=3, **kw):
        calls.append(retries)
        if len(calls) < 3:
            r = requests.Response()
            r.status_code = 429
            r.headers["retry-after"] = "2"
            raise requests.HTTPError(response=r)
        return "ok"
    monkeypatch.setattr(wp.http, "get", fake_get)
    monkeypatch.setattr(wp.time, "sleep", slept.append)
    assert wp._get("u") == "ok"
    assert calls == [0, 0, 0] and slept == [2.5, 2.5]


def test_daily_reads_todays_raw_copy(monkeypatch):
    today = pd.Timestamp.now(tz="UTC").normalize().tz_localize(None)
    u = wp.url("en", "OpenAI", (today - pd.Timedelta(days=1)).strftime("%Y%m%d"))
    p = wp.http.raw_path(wp.SOURCE, u)
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(_payload({"2026-11-01": 9})), encoding="utf-8")
    monkeypatch.setattr(wp.http, "get", lambda *a, **k: pytest.fail("network"))
    assert wp.daily("en", "OpenAI", today).tolist() == [9.0]
