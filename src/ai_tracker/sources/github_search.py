"""GitHub commit search (G3, step 2 track B2): weekly counts of commits with AI co-author trailers, from 2024.

Registered in docs/kallor/github_ai.md (part B) before any value was fetched. GH Archive lost commit messages
on 2025-10-08 (Events API change), so this is the live continuation, as a different measure: GitHub's
commit-search index (default branches of public repos), `total_count` only. Nothing but counts is stored.

Each fetch asks the last REQUERY_WEEKS complete weeks (values change afterwards: late merges, deleted repos,
index rebuilds) and, oldest first, the weeks since START that the series does not have yet, at most
MAX_WEEKS_PER_FETCH weeks in all (GitHub's secondary rate limit: a cold start fills the history over a few runs).
Counts are cached per fetch day under RAW_DIR/github_search/<day>/counts.json, so the series of one run share
the queries.
"""

from __future__ import annotations

import json
import os
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

from ai_tracker import http

SOURCE = "github_search"
API = "https://api.github.com/search/commits"
START = date(2024, 1, 1)  # Monday
REQUERY_WEEKS = 8
MAX_WEEKS_PER_FETCH = 40  # 200 queries, about 20 minutes at MIN_INTERVAL
MIN_INTERVAL = 6.0  # seconds; the primary limit is 30 searches per minute, the secondary limit is stricter
SECONDARY_WAIT = 90.0  # seconds to back off after a secondary-rate-limit 403
QUERIES = {
    "all": "",
    "any": ('"noreply@anthropic.com" OR "Copilot@users.noreply.github.com" OR "cursoragent@cursor.com" OR '
            '"devin-ai-integration" OR "codex@openai.com"'),
    "claude": '"noreply@anthropic.com"',
    "copilot": '"Copilot@users.noreply.github.com"',
    "cursor": '"cursoragent@cursor.com"',
}
_last = [0.0]
_auth_ok = [True]


def query(name: str, monday: date) -> str:
    rng = f"committer-date:{monday:%Y-%m-%d}..{monday + timedelta(days=6):%Y-%m-%d}"
    return f"{QUERIES[name]} {rng}".strip()


def _headers() -> dict:
    h = {"User-Agent": http.DEFAULT_UA, "Accept": "application/vnd.github+json",
         "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and _auth_ok[0]:
        h["Authorization"] = f"Bearer {token}"
    return h


def total_count(q: str, retries: int = 5) -> int | None:
    """total_count of one search; None when GitHub keeps reporting incomplete results or errors."""
    for attempt in range(retries + 1):
        wait = MIN_INTERVAL - (time.monotonic() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.monotonic()
        try:
            r = requests.get(API, params={"q": q, "per_page": 1}, headers=_headers(), timeout=60)
        except requests.RequestException:
            time.sleep(5 * 2 ** min(attempt, 4))
            continue
        if r.status_code == 401 and _auth_ok[0]:  # a stale token: the anonymous limit still works
            _auth_ok[0] = False
            continue
        if r.status_code in (403, 429):  # primary limit: wait for the reset; secondary limit: back off longer
            reset = float(r.headers.get("x-ratelimit-reset") or 0)
            retry_after = float(r.headers.get("retry-after") or 0)
            primary = r.headers.get("x-ratelimit-remaining") == "0"
            floor = 10 if primary else SECONDARY_WAIT * (attempt + 1)
            time.sleep(min(max(retry_after, reset - time.time() if primary else 0, floor), 600))
            continue
        if r.status_code >= 500:
            time.sleep(5 * 2 ** min(attempt, 4))
            continue
        r.raise_for_status()  # 422 = a malformed query: a bug, not an outage
        body = r.json()
        if body.get("incomplete_results"):
            time.sleep(10)
            continue
        return int(body["total_count"])
    return None


def last_complete_monday(today: date) -> date:
    """Monday of the last ISO week that ended before today."""
    return today - timedelta(days=today.weekday() + 7)


def weeks_to_query(today: date, stored: set | None = None, max_weeks: int | None = MAX_WEEKS_PER_FETCH) -> list[date]:
    """The last REQUERY_WEEKS complete weeks, then the oldest weeks since START missing from `stored` (week
    strings 'YYYY-MM-DD/YYYY-MM-DD'), at most `max_weeks` in all (None = no cap), in date order."""
    stored = stored or set()
    last = last_complete_monday(today)
    all_weeks, m = [], START
    while m <= last:
        all_weeks.append(m)
        m += timedelta(days=7)
    recent = all_weeks[-REQUERY_WEEKS:]
    missing = [w for w in all_weeks[:-REQUERY_WEEKS] if str(pd.Period(w, "W-SUN")) not in stored]
    pick = recent + missing
    if max_weeks is not None:
        pick = pick[:max_weeks]
    return sorted(pick)


def _cache_path(today: date) -> Path:
    return http.RAW_DIR / SOURCE / today.isoformat() / "counts.json"


def stored_periods(key: str) -> set[str]:
    """Weeks the table already has for series `key` (decided per series, so that every series of a cold start
    is backfilled although they share one cache)."""
    from ai_tracker import observations  # lazy: observations imports the catalog, which imports this module

    t = observations.load()
    return set(t.loc[t["series"] == key, "period"].astype(str))


def counts(stored: set | None = None, today: date | None = None, get=total_count,
           max_weeks: int | None = MAX_WEEKS_PER_FETCH) -> pd.DataFrame:
    """Counts per week (index W-SUN period) and query name (columns); missing answers are NaN."""
    today = today or date.today()
    path = _cache_path(today)
    cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    rows = {}
    for monday in weeks_to_query(today, stored, max_weeks):
        row = {}
        for name in QUERIES:
            q = query(name, monday)
            if q not in cache:
                cache[q] = get(q)
                if cache[q] is not None:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
                    tmp.write_text(json.dumps({k: v for k, v in cache.items() if v is not None}, indent=0),
                                   encoding="utf-8")
                    os.replace(tmp, path)
            row[name] = cache[q]
        rows[monday] = row
    df = pd.DataFrame.from_dict(rows, orient="index", columns=list(QUERIES)).astype(float)
    df.index = pd.PeriodIndex(pd.to_datetime(df.index), freq="W-SUN")
    return df


def share(name: str, df: pd.DataFrame) -> pd.Series:
    return (100.0 * df[name] / df["all"]).dropna().rename(name)


def level(name: str, df: pd.DataFrame) -> pd.Series:
    return df[name].dropna().rename(name)


def fetch(key: str, name: str, kind: str) -> pd.Series:
    """Spec.fetch for series `key`: share (%) or level of query `name`."""
    df = counts(stored_periods(key))
    return share(name, df) if kind == "share" else level(name, df)
