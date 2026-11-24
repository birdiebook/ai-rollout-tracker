"""GH Archive (G3, step 2 track B2): share of public push commits with an AI co-author trailer, weekly, 2021-2025.

Registered in docs/kallor/github_ai.md (part A) before any weekly value was computed. Summary:
- Hourly files https://data.gharchive.org/YYYY-MM-DD-H.json.gz, downloaded and counted here (no BigQuery).
- Commit = element of payload.commits of a public PushEvent with distinct = true; one count per SHA per hour.
- Seven fixed sample hours per ISO week (SAMPLE_HOURS). An hour is measurable when the file reads to the end
  and >= 90 % of its PushEvents carry `commits`; else h+1..h+3 the same day replace it. A week needs >= 5.
- GitHub removed `commits` from PushEvent in the Events API (from GH Archive hour 2025-10-08-17), so the
  series ends with ISO week 2025-W40 (Sunday 2025-10-05) and is closed.

Weekly aggregates are numbers only and are kept in curated/github_ai_gharchive.csv (rebuilt with
`python -m ai_tracker.sources.gharchive build`); per-hour results are cached under RAW_DIR/gharchive/hours/.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import time
import zlib
from concurrent.futures import ProcessPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests

from ai_tracker import config, http

SOURCE = "gharchive"
URL = "https://data.gharchive.org/{d:%Y-%m-%d}-{h}.json.gz"
CURATED = config.REPO / "curated" / "github_ai_gharchive.csv"
START = date(2021, 1, 4)  # Monday of ISO week 2021-W01
END = date(2025, 10, 5)  # Sunday of ISO week 2025-W40, last full week before the payload change
SAMPLE_HOURS = {0: 2, 1: 6, 2: 10, 3: 14, 4: 18, 5: 22, 6: 12}  # ISO weekday (Mon=0) -> UTC hour
MAX_SHIFT = 3  # replacement hours h+1..h+3, same day
MIN_HOURS = 5
MIN_COMMITS_FIELD = 0.9
COUNT_VERSION = 2  # part of the hour-cache path: bump when the counting changes (v1 missed "Co-Authored-By")

TRAILER = re.compile(r"^\s*co-authored-by:\s*(.+?)\s*$", re.I | re.M)
GROUPS: dict[str, list[str]] = {
    "claude": [r"noreply@anthropic\.com", r"claude\[bot\]@users\.noreply\.github\.com"],
    "copilot": [r"\bcopilot@users\.noreply\.github\.com", r"^copilot autofix"],
    "cursor": [r"cursoragent@cursor\.com"],
    "devin": [r"devin-ai-integration\[bot\]@"],
    "codex": [r"codex@openai\.com", r"chatgpt-codex-connector\[bot\]@"],
    "google": [r"gemini-code-assist\[bot\]@", r"google-labs-jules\[bot\]@"],
    "aider": [r"@aider\.chat"],
    "amp": [r"amp@ampcode\.com"],
    "other": [r"factory-droid\[bot\]@", r"openhands@all-hands\.dev", r"codegen-sh\[bot\]@",
              r"terragon-labs\[bot\]@", r"coderabbitai\[bot\]@", r"cubic-dev-ai\[bot\]@", r"ellipsis-dev\[bot\]@",
              r"greptile-apps\[bot\]@", r"qodo-merge-pro\[bot\]@"],
}
_GROUP_RX = {g: [re.compile(p) for p in ps] for g, ps in GROUPS.items()}
_ID_PREFIX = re.compile(r"<\d+\+")
COLUMNS = ["week", "n_hours", "push_events", "commits", "ai_commits", "ai_repos"] + [f"ai_{g}" for g in GROUPS]


def identity_groups(identity: str) -> set[str]:
    """AI groups an identity (the text after 'Co-authored-by:') belongs to."""
    s = _ID_PREFIX.sub("<", identity.strip().lower())
    return {g for g, rxs in _GROUP_RX.items() if any(rx.search(s) for rx in rxs)}


def message_groups(message: str) -> set[str]:
    """AI groups named in the co-author trailers of a commit message (empty = not AI co-authored)."""
    out: set[str] = set()
    if "authored-by" not in message.lower():  # cheap pre-filter; the trailer regex decides
        return out
    for ident in TRAILER.findall(message):
        out |= identity_groups(ident)
    return out


def count_lines(lines: Iterable[bytes]) -> dict:
    """Counts for one hour file (iterable of JSON lines). Raises on a corrupt or truncated stream."""
    push = with_commits = 0
    shas: set[str] = set()
    ai: set[str] = set()
    groups: dict[str, set[str]] = {g: set() for g in GROUPS}
    repos: set[int] = set()
    for line in lines:
        if b'"PushEvent"' not in line:
            continue
        e = json.loads(line)
        if e.get("type") != "PushEvent" or e.get("public") is False:
            continue
        push += 1
        p = e.get("payload") or {}
        if "commits" not in p:
            continue
        with_commits += 1
        for c in p.get("commits") or []:
            sha = c.get("sha")
            if not sha or not c.get("distinct", True) or sha in shas:
                continue
            shas.add(sha)
            gs = message_groups(c.get("message") or "")
            if gs:
                ai.add(sha)
                repos.add((e.get("repo") or {}).get("id"))
                for g in gs:
                    groups[g].add(sha)
    measurable = push > 0 and with_commits >= MIN_COMMITS_FIELD * push
    return {"status": "ok" if measurable else "unmeasurable", "push_events": push, "commits": len(shas),
            "ai_commits": len(ai), "groups": {g: len(v) for g, v in groups.items()},
            "ai_repos": sorted(r for r in repos if r is not None)}


def hour_cache(d: date, h: int) -> Path:
    return http.RAW_DIR / SOURCE / f"hours_v{COUNT_VERSION}" / f"{d:%Y-%m-%d}-{h}.json"


def _download_count(url: str, retries: int = 8) -> dict:
    """Download one hour file to a temp file (length checked), then count it. Streams that break are retried."""
    headers = {"User-Agent": http.user_agent("data.gharchive.org")}
    tmp_dir = http.RAW_DIR / SOURCE / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp = tmp_dir / f"{os.getpid()}.json.gz"
    try:
        tmp.unlink(missing_ok=True)
        expected = -1
        for attempt in range(retries + 1):
            try:  # resume a broken transfer with a Range request instead of starting over
                have = tmp.stat().st_size if tmp.exists() else 0
                h = dict(headers, Range=f"bytes={have}-") if have else headers
                with requests.get(url, stream=True, timeout=(20, 30), headers=h) as r:
                    if r.status_code == 404:
                        return {"status": "missing"}
                    if r.status_code == 416 and have == expected:
                        break
                    r.raise_for_status()
                    if r.status_code == 200:
                        have = 0
                        expected = int(r.headers.get("content-length") or -1)
                    elif expected < 0:  # 206: total size after the slash in Content-Range
                        expected = int((r.headers.get("content-range") or "/-1").rsplit("/", 1)[1])
                    with open(tmp, "ab" if have else "wb") as f:
                        for chunk in r.iter_content(1 << 20):
                            f.write(chunk)
                if expected >= 0 and tmp.stat().st_size != expected:
                    raise OSError(f"short download {tmp.stat().st_size} of {expected}")
                break
            except (requests.RequestException, OSError) as exc:
                if attempt == retries:
                    return {"status": "unreadable", "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
                time.sleep(2 * 2 ** min(attempt, 3))
        try:
            with gzip.open(tmp, "rb") as f:
                return count_lines(f)
        except (OSError, EOFError, zlib.error, json.JSONDecodeError, UnicodeDecodeError) as exc:
            return {"status": "corrupt", "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
    finally:
        tmp.unlink(missing_ok=True)


def hour_result(d: date, h: int, refresh: bool = False) -> dict:
    """Counts for one hour, cached as JSON (an 'unreadable' result is not cached, so it is retried)."""
    p = hour_cache(d, h)
    if p.exists() and not refresh:
        return json.loads(p.read_text(encoding="utf-8"))
    res = _download_count(URL.format(d=d, h=h))
    res["hour"] = f"{d:%Y-%m-%d}-{h}"
    res["fetched_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if res["status"] != "unreadable":
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(res), encoding="utf-8")
        os.replace(tmp, p)
    return res


def week_hours(monday: date) -> list[tuple[date, int]]:
    return [(monday + timedelta(days=k), h) for k, h in SAMPLE_HOURS.items()]


def sample_hour(d: date, h: int, get=hour_result) -> dict | None:
    """The registered hour, or the first measurable replacement h+1..h+3 the same day; None if none."""
    for s in range(MAX_SHIFT + 1):
        if h + s > 23:
            break
        res = get(d, h + s)
        if res.get("status") == "ok":
            return res
    return None


def aggregate_week(monday: date, results: list[dict | None]) -> dict:
    """Weekly row from the sample-hour results (None = no measurable hour that day)."""
    ok = [r for r in results if r is not None]
    row = {"week": monday.isoformat(), "n_hours": len(ok),
           "push_events": sum(r["push_events"] for r in ok), "commits": sum(r["commits"] for r in ok),
           "ai_commits": sum(r["ai_commits"] for r in ok),
           "ai_repos": len(set().union(*[set(r["ai_repos"]) for r in ok])) if ok else 0}
    for g in GROUPS:
        row[f"ai_{g}"] = sum(r["groups"].get(g, 0) for r in ok)
    return row


def _week(monday: date) -> dict:
    return aggregate_week(monday, [sample_hour(d, h) for d, h in week_hours(monday)])


def mondays(start: date = START, end: date = END) -> list[date]:
    out, m = [], start - timedelta(days=start.weekday())
    while m + timedelta(days=6) <= end:
        out.append(m)
        m += timedelta(days=7)
    return out


def build(start: date = START, end: date = END, workers: int = 6, path: Path | None = CURATED) -> pd.DataFrame:
    """Count every sample hour (cached) and write the weekly aggregates to the curated CSV."""
    weeks = mondays(start, end)
    hours = [dh for m in weeks for dh in week_hours(m)]
    todo = [dh for dh in hours if not hour_cache(*dh).exists()]
    print(f"{len(weeks)} weeks, {len(hours)} sample hours, {len(todo)} not cached", flush=True)
    t0 = time.monotonic()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for i, res in enumerate(ex.map(hour_result, *zip(*todo)) if todo else [], 1):
            if i % 50 == 0 or res["status"] != "ok":
                print(f"{i}/{len(todo)} {res.get('hour')} {res['status']} {time.monotonic() - t0:.0f}s", flush=True)
    rows = [_week(m) for m in weeks]  # replacement hours are fetched here when needed (rare)
    df = pd.DataFrame(rows, columns=COLUMNS)
    if path is not None and (path != CURATED or (start, end) == (START, END)):  # never a partial curated file
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False, lineterminator="\n")
    return df


def load(path: Path = CURATED) -> pd.DataFrame:
    """Weekly aggregates with a value (>= MIN_HOURS measurable hours), indexed by W-SUN period."""
    df = pd.read_csv(path)
    df = df[df["n_hours"] >= MIN_HOURS].copy()
    df.index = pd.PeriodIndex(pd.to_datetime(df["week"]), freq="W-SUN")
    return df


def share(col: str, path: Path = CURATED) -> pd.Series:
    df = load(path)
    return (100.0 * df[col] / df["commits"]).rename(col)


def level(col: str, path: Path = CURATED) -> pd.Series:
    return load(path)[col].astype(float)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ai_tracker.sources.gharchive")
    ap.add_argument("cmd", choices=["build"])
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--start", default=START.isoformat())
    ap.add_argument("--end", default=END.isoformat())
    a = ap.parse_args(argv)
    df = build(date.fromisoformat(a.start), date.fromisoformat(a.end), a.workers)
    print(f"{len(df)} weeks, {int((df['n_hours'] >= MIN_HOURS).sum())} with a value")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
