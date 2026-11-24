"""Track B2: AI co-author trailers in GitHub commits (GH Archive part A, commit search part B). No network."""

from __future__ import annotations

import json
from datetime import date

import pandas as pd
import pytest

from ai_tracker import catalog, http, observations
from ai_tracker.series import github_ai
from ai_tracker.sources import gharchive, github_search


def _push(repo, commits, public=True, with_commits=True):
    payload = {"push_id": 1, "ref": "refs/heads/main"}
    if with_commits:
        payload["commits"] = [{"sha": s, "message": m, "distinct": d} for s, m, d in commits]
    return json.dumps({"id": "1", "type": "PushEvent", "public": public, "repo": {"id": repo, "name": "x/y"},
                       "payload": payload}).encode() + b"\n"


CLAUDE = "Fix\n\nCo-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
COPILOT = "Apply suggestion\n\nCo-authored-by: Copilot <175728472+Copilot@users.noreply.github.com>"


@pytest.mark.parametrize("identity,groups", [
    ("Claude <noreply@anthropic.com>", {"claude"}),
    ("claude[bot] <209825114+claude[bot]@users.noreply.github.com>", {"claude"}),
    ("Copilot <175728472+Copilot@users.noreply.github.com>", {"copilot"}),
    ("copilot-swe-agent[bot] <198982749+Copilot@users.noreply.github.com>", {"copilot"}),
    ("Copilot Autofix powered by AI <62310815+github-advanced-security[bot]@users.noreply.github.com>", {"copilot"}),
    ("Cursor Agent <cursoragent@cursor.com>", {"cursor"}),
    ("Devin AI <158243242+devin-ai-integration[bot]@users.noreply.github.com>", {"devin"}),
    ("Codex <codex@openai.com>", {"codex"}),
    ("gemini-code-assist[bot] <176961590+gemini-code-assist[bot]@users.noreply.github.com>", {"google"}),
    ("aider (gpt-4o) <noreply@aider.chat>", {"aider"}),
    ("Amp <amp@ampcode.com>", {"amp"}),
    ("coderabbitai[bot] <136622811+coderabbitai[bot]@users.noreply.github.com>", {"other"}),
    # not AI: rule-based bots and people with tool-like names
    ("dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>", set()),
    ("github-actions[bot] <github-actions[bot]@users.noreply.github.com>", set()),
    ("cursor <12345+someone@example.com>", set()),
    ("Devin Example <devin@example.com>", set()),
    ("A Person <person@example.org>", set()),
])
def test_identity_groups(identity, groups):
    assert gharchive.identity_groups(identity) == groups


def test_message_groups_needs_a_trailer_line():
    assert gharchive.message_groups(CLAUDE) == {"claude"}
    assert gharchive.message_groups(CLAUDE + "\n" + COPILOT.split("\n")[-1]) == {"claude", "copilot"}
    assert gharchive.message_groups("mention noreply@anthropic.com in prose") == set()
    assert gharchive.message_groups("Fix\n\nSigned-off-by: Claude <noreply@anthropic.com>") == set()
    assert gharchive.message_groups("x\n  CO-AUTHORED-BY:   CLAUDE <noreply@anthropic.com>  ") == {"claude"}


def test_count_lines():
    lines = [
        _push(1, [("a", CLAUDE, True), ("b", "plain", True), ("c", CLAUDE, False)]),  # c: not distinct
        _push(2, [("a", CLAUDE, True), ("d", COPILOT, True)]),  # a again: counted once in the hour
        _push(3, [("e", "plain", True)], public=False),  # private: ignored
        json.dumps({"type": "WatchEvent", "payload": {}}).encode() + b"\n",
    ]
    res = gharchive.count_lines(lines)
    assert res["status"] == "ok"
    assert (res["push_events"], res["commits"], res["ai_commits"]) == (2, 3, 2)
    assert res["groups"]["claude"] == 1 and res["groups"]["copilot"] == 1
    assert res["ai_repos"] == [1, 2]


def test_hour_without_commits_field_is_unmeasurable():
    # after 2025-10-08 PushEvent has no commits: the hour cannot be measured
    lines = [_push(1, [], with_commits=False)] * 9 + [_push(2, [("a", "x", True)])]
    assert gharchive.count_lines(lines)["status"] == "unmeasurable"
    assert gharchive.count_lines([])["status"] == "unmeasurable"


def test_sample_hours_and_replacement():
    monday = date(2025, 9, 1)
    assert gharchive.week_hours(monday)[0] == (monday, 2)
    assert gharchive.week_hours(monday)[-1] == (date(2025, 9, 7), 12)
    assert sorted(gharchive.SAMPLE_HOURS.values()) == [2, 6, 10, 12, 14, 18, 22]
    seen = []

    def get(d, h):
        seen.append(h)
        return {"status": "ok" if h == 8 else "missing"}

    assert gharchive.sample_hour(monday, 6, get)["status"] == "ok" and seen == [6, 7, 8]
    seen.clear()
    assert gharchive.sample_hour(monday, 22, lambda d, h: seen.append(h) or {"status": "missing"}) is None
    assert seen == [22, 23]  # never past midnight


def test_aggregate_week_and_min_hours(tmp_path):
    hour = {"status": "ok", "push_events": 10, "commits": 20, "ai_commits": 2,
            "groups": {"claude": 2, "copilot": 1}, "ai_repos": [1, 2]}
    full = gharchive.aggregate_week(date(2025, 9, 1), [hour] * 5 + [None, None])
    assert (full["n_hours"], full["commits"], full["ai_commits"], full["ai_repos"]) == (5, 100, 10, 2)
    assert full["ai_claude"] == 10 and full["ai_cursor"] == 0
    short = gharchive.aggregate_week(date(2025, 9, 8), [hour] * 4 + [None] * 3)
    p = tmp_path / "agg.csv"
    pd.DataFrame([full, short], columns=gharchive.COLUMNS).to_csv(p, index=False)
    s = gharchive.share("ai_commits", p)
    assert list(s.index.astype(str)) == ["2025-09-01/2025-09-07"]  # the 4-hour week has no value
    assert s.iloc[0] == pytest.approx(10.0)
    assert gharchive.level("ai_repos", p).iloc[0] == 2


def test_mondays_cover_registered_period():
    weeks = gharchive.mondays()
    assert weeks[0] == date(2021, 1, 4) and weeks[-1] == date(2025, 9, 29) and len(weeks) == 248


def test_search_weeks_and_queries():
    today = date(2026, 11, 23)  # a Monday: the last complete week is 2026-11-16..22
    assert github_search.last_complete_monday(today) == date(2026, 11, 16)
    assert github_search.last_complete_monday(date(2026, 11, 22)) == date(2026, 11, 9)
    full = github_search.weeks_to_query(today, max_weeks=None)
    assert full[0] == date(2024, 1, 1) and full[-1] == date(2026, 11, 16) and len(full) == 151
    first = github_search.weeks_to_query(today)  # cold start: the newest 12 weeks, contiguous
    assert len(first) == 12 and first == full[-12:]
    stored = {str(pd.Period(w, "W-SUN")) for w in full}
    recent = github_search.weeks_to_query(today, stored)
    assert len(recent) == 8 and recent[0] == date(2026, 9, 28)
    stored.discard(str(pd.Period(date(2025, 3, 3), "W-SUN")))  # a hole is filled on the next run
    assert date(2025, 3, 3) in github_search.weeks_to_query(today, stored)


def test_joined_never_leaves_a_hole():
    w = pd.period_range("2026-10-04", periods=6, freq="W-SUN")
    stored = {str(p) for p in w[:3]}
    values = pd.Series([1.0, 1.0, 1.0, 1.0, 1.0], index=w[[0, 1, 2, 4, 5]])  # week 3 failed this run
    assert list(github_search.joined(values, stored).index) == list(w[[0, 1, 2]])
    values = pd.Series([1.0, 1.0], index=w[[4, 5]])  # cold start, week 3 failed: keep the newest block
    assert list(github_search.joined(values, set()).index) == list(w[[4, 5]])
    older = pd.Series([1.0, 1.0], index=w[[0, 1]])  # backfill chunk below a stored block, week 2 failed
    assert list(github_search.joined(older, {str(p) for p in w[3:]}).index) == []
    assert github_search.query("all", date(2024, 1, 1)) == "committer-date:2024-01-01..2024-01-07"
    assert github_search.query("claude", date(2024, 1, 1)).startswith('"noreply@anthropic.com" committer-date:')
    assert github_search.QUERIES["any"].count(" OR ") <= 5  # search allows five operators


def test_search_counts_cache_and_shares(tmp_path, monkeypatch):
    monkeypatch.setattr(http, "RAW_DIR", tmp_path)
    calls = []

    def get(q):
        calls.append(q)
        if q == github_search.query("claude", date(2026, 11, 9)):
            return None  # GitHub kept answering incomplete: the value is missing this run
        return 1000 if q.startswith("committer-date") else 10

    today = date(2026, 11, 23)
    stored = {str(p) for p in pd.period_range("2024-01-07", "2026-11-22", freq="W-SUN")}
    df = github_search.counts(stored, today=today, get=get)
    assert len(calls) == 8 * len(github_search.QUERIES)
    assert df.loc[pd.Period("2026-11-16", "W-SUN"), "all"] == 1000
    share = github_search.share("claude", df)
    assert len(share) == 7 and share.iloc[-1] == pytest.approx(1.0)
    # same day again: answered from the cache, only the missing query is asked again
    calls.clear()
    github_search.counts(stored, today=today, get=get)
    assert len(calls) == 1


class _Resp:
    def __init__(self, status, body=None, headers=None):
        self.status_code, self._body, self.headers = status, body or {}, headers or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


def test_total_count_retries(monkeypatch):
    monkeypatch.setattr(github_search, "MIN_INTERVAL", 0)
    monkeypatch.setattr(github_search.time, "sleep", lambda s: None)
    monkeypatch.setattr(github_search, "_auth_ok", [True])
    monkeypatch.setenv("GITHUB_TOKEN", "dummy")
    answers = iter([_Resp(401), _Resp(403, headers={"retry-after": "1"}), _Resp(502),
                    _Resp(200, {"incomplete_results": True, "total_count": 5}),
                    _Resp(200, {"incomplete_results": False, "total_count": 7})])
    auth = []

    def fake_get(url, params, headers, timeout):
        auth.append("Authorization" in headers)
        return next(answers)

    monkeypatch.setattr(github_search.requests, "get", fake_get)
    assert github_search.total_count("q") == 7
    assert auth == [True, False, False, False, False]  # a stale token falls back to anonymous
    monkeypatch.setattr(github_search.requests, "get",
                        lambda *a, **k: _Resp(200, {"incomplete_results": True, "total_count": 1}))
    assert github_search.total_count("q", retries=2) is None


def test_catalog_entries():
    specs = github_ai.SPECS + github_ai.SEARCH_SPECS
    keys = {s.key: s for s in specs}
    assert not catalog.validate(specs)
    assert all(s.branch == "G3" and s.freq == "W" and not s.publish for s in specs)
    a = [s for k, s in keys.items() if k.startswith("g3_gh_")]
    b = [s for k, s in keys.items() if k.startswith("g3_ghs_")]
    assert len(a) == 12 and all(s.closed and not s.revised for s in a)
    assert len(b) == 6 and all(s.revised and not s.closed for s in b)
    assert {s.key for s in github_ai.SPECS} <= set(catalog.by_key())
    assert not {s.key for s in github_ai.SEARCH_SPECS} & set(catalog.by_key())  # BLOCKED: not catalogued


def test_search_series_backfill_then_recent_weeks(tmp_path, monkeypatch):
    """A cold start backfills from 2024-01 in capped chunks; afterwards a fetch asks the last 8 weeks only."""
    monkeypatch.setattr(observations, "PATH", tmp_path / "observations.parquet")
    asked = []

    def fake_counts(stored, today=None, get=None, max_weeks=None):
        weeks = github_search.weeks_to_query(date(2026, 11, 23), stored, max_weeks)
        asked.append(len(weeks))
        df = pd.DataFrame({n: 100.0 for n in github_search.QUERIES}, index=pd.PeriodIndex(weeks, freq="W-SUN"))
        df["all"] = 1000.0
        return df

    monkeypatch.setattr(github_search, "counts", fake_counts)
    spec = catalog.by_key(github_ai.SEARCH_SPECS)["g3_ghs_ai_coauthor_share_w"]
    for k in range(37):
        observations.upsert(spec, spec.fetch(), fetched_at=date(2026, 11, 23))
    assert asked[:2] == [12, 12] and asked[-2:] == [11, 8]  # 4 older weeks a run until 2024-01, then 8 a run
    t = observations.load()
    assert t["period"].nunique() == 151
    assert (t["source"] == "backfill").sum() == 12
