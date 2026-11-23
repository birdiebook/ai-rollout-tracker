"""arXiv paging, pacing, backoff and resumable collection, with a mocked API (no network)."""

from __future__ import annotations

import re
from datetime import date

import pandas as pd
import pytest

from ai_tracker.sources import arxiv


def feed(total: int, entries: list[tuple[str, str]]) -> str:
    items = "".join(f"<entry><id>http://arxiv.org/abs/{i}</id><arxiv:primary_category term=\"{c}\"/></entry>"
                    for i, c in entries)
    return ('<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/" '
            f'xmlns:arxiv="http://arxiv.org/schemas/atom"><opensearch:totalResults>{total}</opensearch:totalResults>'
            f"{items}</feed>")


class Resp:
    def __init__(self, status: int, text: str = "", headers: dict | None = None):
        self.status_code, self.text, self.headers = status, text, headers or {}


class FakeClock:
    def __init__(self):
        self.t, self.sleeps = 0.0, []

    def clock(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


def client(responses, budget=1000):
    clk = FakeClock()
    calls = []

    def get(params):
        calls.append(dict(params))
        clk.t += 0.5  # each call takes half a second
        r = responses(params) if callable(responses) else responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    c = arxiv.Client(get=get, pacer=arxiv.Pacer(clock=clk.clock, sleep=clk.sleep), sleep=clk.sleep, budget=budget)
    return c, calls, clk


RECORDS = [("1", "cs.LG"), ("2", "cs.CV"), ("3", "cs.AI"), ("4", "cs.CL"), ("5", "cs.LG")]


def paged(total=5, records=RECORDS):
    def respond(params):
        s, n = params["start"], params["max_results"]
        return Resp(200, feed(total, records[s:s + n]))
    return respond


def test_parse_feed_and_error_entry():
    total, entries = arxiv.parse_feed(feed(3, [("a", "cs.LG")]))
    assert total == 3 and entries == [("http://arxiv.org/abs/a", "cs.LG")]
    err = feed(1, []).replace("</feed>", "<entry><id>https://arxiv.org/api/errors</id><summary>bad</summary></entry></feed>")
    with pytest.raises(arxiv.ArxivError):
        arxiv.parse_feed(err)


def test_pagination_counts_primary_and_union():
    c, calls, _ = client(paged())
    out = arxiv.fetch_month(pd.Period("2025-10", "M"), c, page_size=2)
    assert [p["start"] for p in calls] == [0, 2, 4]
    assert all(p["sortBy"] == "submittedDate" for p in calls)
    assert "submittedDate:[202510010000 TO 202510312359]" in calls[0]["search_query"]
    assert out == {"total": 5, "n": 5, "primary": {"cs.AI": 1, "cs.LG": 2, "cs.CL": 1}}  # cs.CV not primary


def test_empty_page_is_retried_then_incomplete_month_raises():
    seq = iter([feed(5, RECORDS[:2]), feed(5, []), feed(5, RECORDS[2:4]), feed(5, RECORDS[4:])])
    c, calls, _ = client(lambda p: Resp(200, next(seq)))
    assert arxiv.fetch_month(pd.Period("2025-10", "M"), c, page_size=2)["n"] == 5
    assert [p["start"] for p in calls] == [0, 2, 2, 4]

    c, _, _ = client(lambda p: Resp(200, feed(5, RECORDS[:2]) if p["start"] == 0 else feed(5, [])))
    with pytest.raises(arxiv.ArxivError, match="saw 2 records of 5"):
        arxiv.fetch_month(pd.Period("2025-10", "M"), c, page_size=2, empty_retries=1)


def test_pacing_at_least_three_seconds_between_calls():
    c, calls, clk = client(paged())
    arxiv.fetch_month(pd.Period("2025-10", "M"), c, page_size=2)
    assert len(calls) == 3 and clk.sleeps == [pytest.approx(2.5), pytest.approx(2.5)]


def test_backoff_on_429_and_5xx_honours_retry_after():
    ok = Resp(200, feed(1, [("1", "cs.AI")]))
    c, calls, clk = client([Resp(429), Resp(429, headers={"Retry-After": "120"}), Resp(503), ok])
    assert arxiv.fetch_month(pd.Period("2025-10", "M"), c)["n"] == 1
    backoffs = [s for s in clk.sleeps if s > arxiv.MIN_INTERVAL]
    assert backoffs == [20.0, 120.0, 80.0]  # base*2**0, Retry-After, base*2**2
    assert len(calls) == 4


def test_network_error_is_retried_and_4xx_is_not():
    import requests

    c, _, _ = client([requests.ConnectionError("reset"), Resp(200, feed(0, []))])
    assert arxiv.fetch_month(pd.Period("2025-10", "M"), c)["n"] == 0
    c, _, _ = client([Resp(400)])
    with pytest.raises(arxiv.ArxivError, match="HTTP 400"):
        arxiv.fetch_month(pd.Period("2025-10", "M"), c)


def test_gives_up_after_max_tries():
    c, calls, _ = client(lambda p: Resp(429))
    c.max_tries = 3
    with pytest.raises(arxiv.ArxivError, match="still refusing"):
        arxiv.fetch_month(pd.Period("2025-10", "M"), c)
    assert len(calls) == 3


def _month(params) -> str:
    return re.search(r"submittedDate:\[(\d{6})", params["search_query"]).group(1)


def test_resumable_collect_and_refetch_window(tmp_path):
    path = tmp_path / "monthly.json"
    one = lambda p: Resp(200, feed(1, [(_month(p), "cs.LG")]))  # noqa: E731
    today = date(2025, 4, 10)  # complete months: 2025-01..2025-03
    c, calls, _ = client(one, budget=2)
    cache = arxiv.collect(today, c, path, start="2025-01")
    assert sorted(cache) == ["2025-01", "2025-02"] and len(calls) == 2  # stopped by the budget, saved
    with pytest.raises(RuntimeError, match="incomplete: 1 months"):
        arxiv.series_from_cache(arxiv.load_cache(path), "cs.LG", today, start="2025-01")

    c, calls, _ = client(one)
    cache = arxiv.collect(today, c, path, start="2025-01")
    # resumes with the missing month, then re-fetches February (fetched only 41 days after its end);
    # January was fetched 69 days after its end and is settled
    assert [_month(p) for p in calls] == ["202503", "202502"]
    s = arxiv.series_from_cache(cache, "primary_all", today, start="2025-01")
    assert list(s) == [1.0] * 3 and str(s.index[-1]) == "2025-03"
    assert list(arxiv.series_from_cache(cache, "cs.AI", today, start="2025-01")) == [0.0] * 3

    due = arxiv.months_due(arxiv.load_cache(path), date(2025, 5, 2), start="2025-01")
    assert [str(m) for m in due] == ["2025-04", "2025-02", "2025-03"]


def test_month_error_does_not_stop_collection(tmp_path):
    def respond(p):
        return Resp(400) if "20250201" in p["search_query"] else Resp(200, feed(0, []))
    c, _, _ = client(respond)
    cache = arxiv.collect(date(2025, 4, 2), c, tmp_path / "m.json", start="2025-01")
    assert sorted(cache) == ["2025-01", "2025-03"]


def test_arxiv_specs_not_published_until_licence_checked():
    from ai_tracker import catalog
    from ai_tracker.series import arxiv as sa

    assert catalog.validate(sa.SPECS) == []
    assert not any(s.publish for s in sa.SPECS)
