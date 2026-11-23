"""arXiv API (export.arxiv.org): monthly new submissions in cs.AI, cs.LG and cs.CL.

Primary category. `cat:` in the API matches cross-listings too, and the API has no primary-category filter, so a
count from `totalResults` alone would include e.g. cs.CV papers cross-listed to cs.LG. We therefore page through
every record of `cat:cs.AI OR cat:cs.LG OR cat:cs.CL` per submission month and count `arxiv:primary_category`.
The same pass gives the union including cross-lists (each paper once).

Politeness. The API rate-limits hard (429 from shared IPs). One call at a time, at least 3 s apart
(arXiv's API terms), exponential backoff with Retry-After on 429/5xx and network errors, a call budget per run,
and a per-month cache in data/arxiv/monthly.json so an interrupted backfill resumes where it stopped. Pages are
not saved raw (about 4.7 MB per 2 000 records); the per-month counts with fetch date are the stored record.

known_from: month end + 7 days (late announcements and moderation holds keep the original submission date, so a
month's count still rises a little afterwards; revised=True). Months are re-fetched until they are 60 days old.

Licence: arXiv metadata is CC0 per arXiv's API terms, which could not be read from the sandbox (arxiv.org and
info.arxiv.org are refused): "unverified", publish=False until checked.
"""

from __future__ import annotations

import json
import os
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Callable

import pandas as pd
import requests

from ai_tracker import config, http

API = "https://export.arxiv.org/api/query"
SOURCE = "arxiv"
CATEGORIES = ("cs.AI", "cs.LG", "cs.CL")
START = "1998-01"
PAGE_SIZE = 2000
MIN_INTERVAL = 3.0  # seconds between calls, arXiv API terms
SETTLED_DAYS = 60  # re-fetch a month until it is this old
CACHE = config.REPO / "data" / "arxiv" / "monthly.json"
RETRY_STATUS = {429, 500, 502, 503, 504}
NS = {"a": "http://www.w3.org/2005/Atom", "os": "http://a9.com/-/spec/opensearch/1.1/",
      "x": "http://arxiv.org/schemas/atom"}


class ArxivError(RuntimeError):
    pass


class BudgetExhausted(RuntimeError):
    pass


# ------------------------------------------------------------------ politeness


@dataclass
class Pacer:
    """At least `min_interval` seconds between the starts of two calls."""
    min_interval: float = MIN_INTERVAL
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    _last: float | None = None

    def wait(self) -> None:
        if self._last is not None:
            gap = self.min_interval - (self.clock() - self._last)
            if gap > 0:
                self.sleep(gap)
        self._last = self.clock()


def backoff_delay(attempt: int, retry_after: str | None, base: float = 20.0, cap: float = 900.0) -> float:
    """Retry-After (seconds) if given, else base * 2**attempt, capped."""
    if retry_after:
        try:
            return min(cap, max(float(retry_after), base))
        except ValueError:
            pass
    return min(cap, base * 2 ** attempt)


def _http_get(params: dict) -> requests.Response:
    """One call through the shared client (honest User-Agent); no client-side retries, we back off here."""
    try:
        return http.get(API, SOURCE, params=params, save=False, retries=0, timeout=120)
    except requests.HTTPError as exc:
        return exc.response


@dataclass
class Client:
    get: Callable[[dict], requests.Response] = _http_get
    pacer: Pacer = field(default_factory=Pacer)
    sleep: Callable[[float], None] = time.sleep
    max_tries: int = 8
    budget: int = 1000  # calls allowed in this run
    calls: int = 0

    def fetch(self, params: dict) -> str:
        for attempt in range(self.max_tries):
            if self.calls >= self.budget:
                raise BudgetExhausted(f"arXiv call budget {self.budget} used")
            self.pacer.wait()
            self.calls += 1
            retry_after = None
            try:
                r = self.get(params)
            except (requests.ConnectionError, requests.Timeout):
                r = None
            if r is not None:
                if r.status_code == 200:
                    return r.text
                if r.status_code not in RETRY_STATUS:
                    raise ArxivError(f"HTTP {r.status_code} from arXiv")
                retry_after = r.headers.get("Retry-After")
            delay = backoff_delay(attempt, retry_after)
            print(f"arxiv: {'network error' if r is None else r.status_code}, waiting {delay:.0f} s", flush=True)
            self.sleep(delay)
        raise ArxivError(f"arXiv still refusing after {self.max_tries} tries")


# ------------------------------------------------------------------ parsing and paging


def parse_feed(text: str) -> tuple[int, list[tuple[str, str]]]:
    """(totalResults, [(id, primary category)]) from an Atom response. Raises on an API error entry."""
    root = ET.fromstring(text)
    entries = []
    for e in root.findall("a:entry", NS):
        eid = (e.findtext("a:id", default="", namespaces=NS) or "").strip()
        if "api/errors" in eid:
            raise ArxivError((e.findtext("a:summary", default="", namespaces=NS) or "API error").strip()[:200])
        prim = e.find("x:primary_category", NS)
        entries.append((eid, prim.get("term") if prim is not None else ""))
    total = int(root.findtext("os:totalResults", default="0", namespaces=NS))
    return total, entries


def month_query(month: pd.Period) -> str:
    cats = " OR ".join(f"cat:{c}" for c in CATEGORIES)
    first, last = month.start_time, month.end_time
    return f"({cats}) AND submittedDate:[{first:%Y%m%d}0000 TO {last:%Y%m%d}2359]"


def fetch_month(month: pd.Period, client: Client, page_size: int = PAGE_SIZE, empty_retries: int = 3) -> dict:
    """Page through one month; returns {'total', 'n', 'primary': {cat: n}}.

    Stable order (sortBy=submittedDate ascending), dedupe by id. An empty page before `total` is reached is
    retried (the API sometimes returns one); the month is accepted when the ids seen match totalResults within
    max(2, 0.2 %), else ArxivError (the month stays uncached and is retried next run).
    """
    q = month_query(month)
    ids: dict[str, str] = {}
    start, total, empties = 0, None, 0
    while total is None or start < total:
        params = {"search_query": q, "start": start, "max_results": page_size,
                  "sortBy": "submittedDate", "sortOrder": "ascending"}
        t, entries = parse_feed(client.fetch(params))
        total = t if total is None else max(total, t)
        if not entries:
            if total == 0:
                break
            empties += 1
            if empties > empty_retries:
                break
            continue
        empties = 0
        ids.update(entries)
        start += len(entries)
    n = len(ids)
    if abs(n - (total or 0)) > max(2, 0.002 * (total or 0)):
        raise ArxivError(f"{month}: saw {n} records of {total}")
    primary = {c: sum(1 for p in ids.values() if p == c) for c in CATEGORIES}
    return {"total": int(total or 0), "n": n, "primary": primary}


# ------------------------------------------------------------------ resumable collection


def load_cache(path: Path | None = None) -> dict:
    path = path or CACHE
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_cache(cache: dict, path: Path | None = None) -> None:
    path = path or CACHE
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, indent=0, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def months_due(cache: dict, today: date, start: str = START) -> list[pd.Period]:
    """Missing months first (oldest first), then cached months fetched less than SETTLED_DAYS after month end."""
    last = pd.Period(pd.Timestamp(today), freq="M") - 1
    months = pd.period_range(start, last, freq="M")
    missing = [m for m in months if str(m) not in cache]
    unsettled = [m for m in months if str(m) in cache and
                 (pd.Timestamp(cache[str(m)]["fetched"]) - m.end_time.normalize()).days < SETTLED_DAYS]
    return missing + unsettled


def collect(today: date | None = None, client: Client | None = None, path: Path | None = None,
            start: str = START) -> dict:
    """Fetch due months, saving the cache after each one. Stops quietly when the call budget is used."""
    today = today or date.today()
    client = client or Client(budget=int(os.environ.get("ARXIV_MAX_CALLS", "1000")))
    cache = load_cache(path)
    for m in months_due(cache, today, start):
        try:
            cache[str(m)] = {**fetch_month(m, client), "fetched": today.isoformat()}
        except BudgetExhausted:
            break
        except ArxivError as exc:
            print(f"arxiv {m}: {exc}")
            continue
        save_cache(cache, path)
        print(f"arxiv {m}: {cache[str(m)]['n']} records ({client.calls} calls)", flush=True)
    return cache


def series_from_cache(cache: dict, kind: str, today: date, start: str = START) -> pd.Series:
    """kind: 'primary_all' (sum over CATEGORIES), 'listed' (union incl. cross-lists) or a category.

    Refuses a partial history: the first load becomes the backfill, so it must be complete."""
    last = pd.Period(pd.Timestamp(today), freq="M") - 1
    months = pd.period_range(start, last, freq="M")
    missing = [str(m) for m in months if str(m) not in cache]
    if missing:
        raise RuntimeError(f"arXiv history incomplete: {len(missing)} months missing (first {missing[0]}); "
                           "run again to resume")

    def value(c: dict) -> float:
        if kind == "listed":
            return float(c["n"])
        if kind == "primary_all":
            return float(sum(c["primary"].values()))
        return float(c["primary"][kind])

    return pd.Series([value(cache[str(m)]) for m in months], index=months, dtype=float)


@lru_cache(maxsize=None)
def _collected() -> str:
    return json.dumps(collect())


def monthly(kind: str) -> pd.Series:
    return series_from_cache(json.loads(_collected()), kind, date.today())
