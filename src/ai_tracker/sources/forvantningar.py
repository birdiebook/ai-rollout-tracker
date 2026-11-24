"""External expectations about AI: prediction markets (Manifold, Polymarket), lead L9 / branch G9.

Selection rule: docs/kallor/forvantningar.md, section 1 (committed before any price was read). `select()` applies
it to metadata only (title, type, status, dates, traders, volume) and never reads or prints a price; the result is
the committed file forvantningar_urval.json. Later rounds append with their own date; entries are never changed,
except `status` (`python -m ai_tracker.sources.forvantningar status`, which also reads metadata only).

Series (docs/kallor/forvantningar.md, section 3):
- Manifold: daily probability from the market's own trade history (/v0/bets, `probAfter` after every trade).
  Value of UTC day D = probability after the last trade before D+1 00:00 UTC (carried forward on days without
  trades); known_from = D+1 00:00 UTC, i.e. every trade used is timestamped before known_from. Days from the first
  trade to the earlier of (close/resolution day, yesterday). The resolution itself is not a price point. Rows
  known before the question's `selected_on` are source="backfill" (selection bias, see flag_preselection).
- Polymarket: the price history lives on clob.polymarket.com, which this environment cannot reach, so only our
  own snapshots from gamma-api: value = Yes price (`outcomePrices`, what Polymarket displays) at the first fetch
  after the W-SUN week ended, period = that week, known_from = the fetch date (UTC midnight, as for every fetched
  value in observations.new_rows). A later fetch in the same week keeps the stored snapshot.
- Metaculus: BLOCKED (API needs an account token; web pages behind a Cloudflare challenge). Kalshi: excluded by its
  Developer Agreement (storing data only for one's own trading). See the doc, sections 4-5.

Terms (quoted in the doc, section 4): neither Manifold's nor Polymarket's official terms page could be read from this
environment, so both are "unverified" and publish=False.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path

import pandas as pd

from ai_tracker import http

SOURCE = "forvantningar"
MANIFOLD = "https://api.manifold.markets/v0"
GAMMA = "https://gamma-api.polymarket.com"
URVAL_PATH = Path(__file__).with_name("forvantningar_urval.json")

LICENSE_MANIFOLD = ("unverified: official terms (docs.manifold.markets/terms, /data) not reachable from the "
                    "session; a third-party mirror of the API docs says non-commercial use is permitted")
LICENSE_POLYMARKET = ("unverified: polymarket.com terms not reachable from the session; public gamma API, "
                      "no key")

# ------------------------------------------------------------------ the rule (doc section 1), metadata only
TOPICS: list[tuple[str, str]] = [
    ("T1", r"\bAGI\b|artificial general intelligence|superintelligen|\bASI\b|\bIMO\b|math(ematical)? olympiad|"
           r"ARC-AGI|FrontierMath|Humanity's Last Exam|SWE-bench|Turing test|best AI model|top AI model|"
           r"GPT-?[6-9]|Gemini [4-9]|Claude [5-9]|Grok [5-9]"),
    ("T2", r"(?=.*(OpenAI|Anthropic|xAI|Mistral|Safe Superintelligence|CoreWeave|Nvidia|Cerebras))"
           r"(?=.*(IPO|go(es)? public|valuation|valued|revenue|market cap|largest company|funding|raise))"),
    ("T3", r"capex|capital expenditure|data ?cent(er|re)|Stargate|gigawatt"),
    ("T4", r"export control|export ban|export restriction|chip export|AI diffusion|\bH20\b|\bH200\b|Blackwell"),
    ("T5", r"AI Act|AI regulation|regulate AI|AI bill|AI law|SB ?1047|SB ?53|RAISE Act|moratorium|preempt|"
           r"executive order"),
]
AI_LINK = r"\bAI\b|artificial intelligence|Nvidia|OpenAI|Anthropic|chip|semiconductor|Stargate|data ?cent"
EXCLUDE = r"manifold|polymarket|metaculus|\bI\b|\bme\b|\bmy\b"
YEAR = r"\b20[2-9]\d\b"

MANIFOLD_TERMS = ["AGI", "artificial general intelligence", "superintelligence", "IMO", "ARC-AGI", "FrontierMath",
                  "SWE-bench", "Turing test", "AI model", "GPT-6", "Gemini 4", "Claude 5", "Grok 5", "OpenAI",
                  "Anthropic", "xAI", "Nvidia", "CoreWeave", "AI IPO", "capex", "data center", "Stargate",
                  "export controls", "H20", "H200", "AI Act", "AI regulation", "AI bill", "AI moratorium", "SB 53"]

MIN_BETTORS = 100
MIN_VOLUME_USD = 250_000
MIN_OPEN_DAYS = 90
MIN_LIFE_DAYS = 180
CLOSED_FROM = pd.Timestamp("2023-01-01")
CAP = 6
CAP_PER_EVENT = 2


def topic(title: str, ai_tag: bool = False) -> str | None:
    """First topic T1..T5 whose pattern matches the title (T3-T5 also need an AI link unless `ai_tag`)."""
    for code, pattern in TOPICS:
        if re.search(pattern, title, re.I):
            if code in ("T3", "T4", "T5") and not ai_tag and not re.search(AI_LINK, title, re.I):
                return None
            return code
    return None


def _ts(ms) -> pd.Timestamp | None:
    return None if ms is None else pd.Timestamp(int(ms), unit="ms")


def _iso(value) -> pd.Timestamp | None:
    if not value:
        return None
    t = pd.Timestamp(value)
    return t.tz_convert("UTC").tz_localize(None) if t.tzinfo is not None else t


def _datable(title: str, close: pd.Timestamp | None) -> bool:
    return bool(re.search(YEAR, title)) or close is not None


def eligible_time(created, close, is_open: bool, today: pd.Timestamp, allow_closed: bool = True) -> bool:
    """Criterion 3: open with close >= today + 90 d, or closed after 2023 with a life of >= 180 d."""
    if close is None or created is None:
        return False
    if is_open:
        return close >= today + pd.Timedelta(days=MIN_OPEN_DAYS)
    return allow_closed and close >= CLOSED_FROM and (close - created) >= pd.Timedelta(days=MIN_LIFE_DAYS)


def manifold_candidates(markets: list[dict], today: pd.Timestamp) -> list[dict]:
    """Rule applied to Manifold search results (dicts as returned by /v0/search-markets). No price is read."""
    out, seen = [], set()
    for m in markets:
        if m["id"] in seen:
            continue
        seen.add(m["id"])
        title = m.get("question", "")
        if (m.get("outcomeType"), m.get("mechanism"), m.get("token", "MANA")) != ("BINARY", "cpmm-1", "MANA"):
            continue
        if (m.get("uniqueBettorCount") or 0) < MIN_BETTORS or re.search(EXCLUDE, title, re.I):
            continue
        if m.get("resolution") == "CANCEL":
            continue
        t = topic(title)
        created = _ts(m.get("createdTime"))
        close = _ts(m.get("closeTime"))
        if m.get("isResolved") and m.get("resolutionTime"):
            close = min(close, _ts(m["resolutionTime"])) if close is not None else _ts(m["resolutionTime"])
        is_open = not m.get("isResolved") and close is not None and close > today
        if t is None or not _datable(title, close) or not eligible_time(created, close, is_open, today):
            continue
        out.append({"platform": "manifold", "id": m["id"], "title": title, "topic": t,
                    "resolution_url": m.get("url", ""), "resolution_source": "",
                    "created": str(created.date()), "close": str(close.date()),
                    "status": "open" if is_open else ("resolved" if m.get("isResolved") else "closed"),
                    "participation": int(m["uniqueBettorCount"]), "participation_unit": "unique traders",
                    "event": ""})
    return out


def polymarket_candidates(events: list[dict], today: pd.Timestamp) -> list[dict]:
    """Rule applied to Polymarket events (gamma /events with embedded markets). Open markets only."""
    out, seen = [], set()
    for e in events:
        for m in e.get("markets") or []:
            if m["id"] in seen:
                continue
            seen.add(m["id"])
            title = m.get("question", "")
            try:
                outcomes = json.loads(m.get("outcomes") or "[]")
            except ValueError:
                continue
            if outcomes != ["Yes", "No"] or re.search(EXCLUDE, title, re.I):
                continue
            if float(m.get("volumeNum") or 0) < MIN_VOLUME_USD:
                continue
            is_open = not m.get("closed") and m.get("active", True) and not m.get("archived")
            created, close = _iso(m.get("createdAt")), _iso(m.get("endDate"))
            t = topic(title, ai_tag=True)
            if t is None or not _datable(title, close) or \
                    not eligible_time(created, close, bool(is_open), today, allow_closed=False):
                continue
            out.append({"platform": "polymarket", "id": str(m["id"]), "title": title, "topic": t,
                        "resolution_url": f"https://polymarket.com/event/{e.get('slug', '')}",
                        "resolution_source": m.get("resolutionSource") or e.get("resolutionSource") or "",
                        "created": str(created.date()), "close": str(close.date()), "status": "open",
                        "participation": round(float(m["volumeNum"])), "participation_unit": "USD volume",
                        "event": str(e.get("id", ""))})
    return out


def apply_cap(cands: list[dict]) -> list[dict]:
    """Criterion 5: <= 6 per topic and platform by participation (ties: lowest id), <= 2 per Polymarket event."""
    def sort_id(c):
        return (0, int(c["id"]), "") if c["id"].isdigit() else (1, 0, c["id"])

    out = []
    for (platform, t) in sorted({(c["platform"], c["topic"]) for c in cands}):
        group = sorted([c for c in cands if (c["platform"], c["topic"]) == (platform, t)],
                       key=lambda c: (-c["participation"], sort_id(c)))
        per_event: dict[str, int] = {}
        taken = []
        for c in group:
            if c["event"] and per_event.get(c["event"], 0) >= CAP_PER_EVENT:
                continue
            per_event[c["event"]] = per_event.get(c["event"], 0) + 1
            taken.append(c)
            if len(taken) == CAP:
                break
        out += taken
    return out


# ------------------------------------------------------------------ fetching metadata
def search_manifold(term: str) -> list[dict]:
    r = http.get(f"{MANIFOLD}/search-markets", SOURCE, params={
        "term": term, "contractType": "BINARY", "filter": "all", "sort": "most-popular", "limit": 100})
    return r.json()


def polymarket_events(closed: bool) -> list[dict]:
    events, offset = [], 0
    while True:
        r = http.get(f"{GAMMA}/events", SOURCE, params={
            "tag_slug": "ai", "closed": str(closed).lower(), "limit": 100, "offset": offset})
        page = r.json()
        events += page
        if len(page) < 100:
            return events
        offset += 100


def select(today: date | None = None) -> list[dict]:
    """One selection round on `today` (metadata only). Returns the new entries (not yet in the file)."""
    day = pd.Timestamp(today or date.today())
    markets = [m for term in MANIFOLD_TERMS for m in search_manifold(term)]
    events = polymarket_events(False) + polymarket_events(True)
    cands = apply_cap(manifold_candidates(markets, day) + polymarket_candidates(events, day))
    known = {(q["platform"], q["id"]) for q in load_urval()}
    new = [dict(c, selected_on=str(day.date())) for c in cands if (c["platform"], c["id"]) not in known]
    return new


def load_urval(path: Path | None = None) -> list[dict]:
    p = path or URVAL_PATH
    return json.loads(p.read_text(encoding="utf-8"))["questions"] if p.exists() else []


def save_urval(questions: list[dict], path: Path | None = None) -> None:
    p = path or URVAL_PATH
    doc = {"rule": "docs/kallor/forvantningar.md, section 1", "questions": questions}
    p.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def market_status(q: dict) -> tuple[str, str]:
    """(status, close date) from the platform's current metadata (no price read)."""
    if q["platform"] == "manifold":
        m = http.get(f"{MANIFOLD}/market/{q['id']}", SOURCE).json()
        close = _ts(m.get("closeTime"))
        if m.get("isResolved") and m.get("resolutionTime"):
            close = min(close, _ts(m["resolutionTime"])) if close is not None else _ts(m["resolutionTime"])
        now = pd.Timestamp(datetime.now(timezone.utc).replace(tzinfo=None))
        status = "resolved" if m.get("isResolved") else ("closed" if close is not None and close <= now else "open")
        return status, str(close.date()) if close is not None else q["close"]
    m = http.get(f"{GAMMA}/markets/{q['id']}", SOURCE).json()
    return ("closed" if m.get("closed") else "open"), str(_iso(m.get("endDate")).date())


def is_closed(q: dict, today: date | None = None) -> bool:
    """Closed for the catalog: not open in the file, or the scheduled close has passed."""
    return q["status"] != "open" or pd.Timestamp(q["close"]) < pd.Timestamp(today or date.today())


# ------------------------------------------------------------------ prices (after selection only)
def manifold_bets(contract_id: str) -> list[dict]:
    """Every bet of a market, newest first, paging with `before`."""
    bets, before = [], None
    while True:
        params = {"contractId": contract_id, "limit": 1000}
        if before:
            params["before"] = before
        page = http.get(f"{MANIFOLD}/bets", SOURCE, params=params, save=False).json()
        bets += page
        if len(page) < 1000:
            return bets
        before = page[-1]["id"]


def daily_from_trades(times: pd.Series, probs: pd.Series, end_day: pd.Timestamp) -> pd.DataFrame:
    """Daily close from timestamped probabilities (UTC, naive). Rows period (D), value, known_from (= D+1 00:00).

    Days from the first trade's day to `end_day` (inclusive); a day without trades carries the previous close.
    """
    s = pd.Series(pd.to_numeric(probs).to_numpy(), index=pd.to_datetime(times)).sort_index()
    s = s[s.index < end_day.normalize() + pd.Timedelta(days=1)]
    if s.empty:
        return pd.DataFrame(columns=["period", "value", "known_from"])
    days = pd.date_range(s.index[0].normalize(), end_day.normalize(), freq="D")
    close = s.groupby(s.index.normalize()).last().reindex(days).ffill()
    return pd.DataFrame({"period": [str(d.date()) for d in days], "value": close.to_numpy(dtype=float),
                         "known_from": days + pd.Timedelta(days=1)})


def manifold_end_day(q: dict, now: pd.Timestamp) -> pd.Timestamp:
    """Last complete UTC day: yesterday, or the close/resolution day if earlier."""
    return min(pd.Timestamp(q["close"]), now.normalize() - pd.Timedelta(days=1))


def manifold_series(q: dict, now: pd.Timestamp | None = None) -> pd.DataFrame:
    now = now or pd.Timestamp(datetime.now(timezone.utc).replace(tzinfo=None))
    bets = pd.DataFrame(manifold_bets(q["id"]))
    if bets.empty:
        return pd.DataFrame(columns=["period", "value", "known_from"])
    bets = bets.dropna(subset=["probAfter", "createdTime"])
    df = daily_from_trades(pd.to_datetime(bets["createdTime"], unit="ms"), bets["probAfter"],
                           manifold_end_day(q, now))
    return flag_preselection(df, q)


def flag_preselection(df: pd.DataFrame, q: dict) -> pd.DataFrame:
    """source="backfill" for rows known before the question's selection day, "release" from it on (R3, D3).

    Each value is point-in-time correct (recomputed from the trades), but the question set was chosen on
    `selected_on` with metadata known only then (traders, life, resolution != CANCEL): a set-level view of G9
    before that day is survivorship-conditioned. Backfill marks it, as for every history loaded after the fact.
    """
    df = df.copy()
    df["source"] = ["backfill" if kf < pd.Timestamp(q["selected_on"]) else "release" for kf in df["known_from"]]
    return df


def yes_price(market: dict) -> float:
    outcomes = json.loads(market["outcomes"])
    prices = json.loads(market["outcomePrices"])
    return float(prices[outcomes.index("Yes")])


def snapshot_row(market: dict, now: pd.Timestamp) -> pd.DataFrame:
    """Our snapshot: the last complete W-SUN week before `now`, known from the fetch date."""
    period = now.to_period("W-SUN") - 1
    return pd.DataFrame({"period": [str(period)], "value": [yes_price(market)],
                         "known_from": [now.normalize()], "source": ["snapshot"]})


def polymarket_series(q: dict, now: pd.Timestamp | None = None, table: pd.DataFrame | None = None) -> pd.DataFrame:
    """Stored snapshots plus a new one for the week that just ended, unless that week already has one."""
    from ai_tracker import observations  # lazy: observations -> catalog -> series -> this module

    from ai_tracker.series.forvantningar import key

    cols = ["period", "value", "known_from", "source"]
    table = observations.load() if table is None else table
    stored = table.loc[table["series"] == key(q), cols].reset_index(drop=True)
    now = now or pd.Timestamp(datetime.now(timezone.utc).replace(tzinfo=None))
    period = str(now.to_period("W-SUN") - 1)
    if is_closed(q, now.date()) or period in set(stored["period"]):
        return stored
    market = _gamma_market(q["id"])
    if market.get("closed"):
        return stored
    return pd.concat([stored, snapshot_row(market, now)], ignore_index=True) if len(stored) else \
        snapshot_row(market, now)


@lru_cache(maxsize=None)
def _gamma_market(market_id: str) -> dict:
    return http.get(f"{GAMMA}/markets/{market_id}", SOURCE).json()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "select":
        new = select()
        save_urval(load_urval() + new)
        for q in new:  # metadata only, never a price
            print(f"{q['platform']:10s} {q['topic']} {q['id']:22s} {q['participation']:>10d} {q['status']:8s} "
                  f"{q['close']} {q['title'][:80]}")
        print(f"{len(new)} new questions -> {URVAL_PATH.name}")
    elif cmd == "status":
        qs = load_urval()
        for q in qs:
            q["status"], q["close"] = market_status(q)
        save_urval(qs)
        print(f"status updated for {len(qs)} questions")
    else:
        sys.exit("usage: python -m ai_tracker.sources.forvantningar select|status")
