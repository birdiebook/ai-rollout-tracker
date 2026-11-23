"""Shared HTTP client: honest User-Agent, per-host rate limit, retries, raw copies with fetch date.

Never impersonate a browser or work around bot protection. A refused request is a BLOCKED source.
Raw responses are saved under data/raw/<source>/<YYYY-MM-DD>/ (never committed).
"""

from __future__ import annotations

import hashlib
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import requests

from ai_tracker import config

DEFAULT_UA = "ai-rollout-tracker (github.com/birdiebook/ai-rollout-tracker)"
RAW_DIR = config.REPO / "data" / "raw"
MIN_INTERVAL = {"data.sec.gov": 0.2, "www.sec.gov": 0.2}  # SEC fair access: <= 10 req/s; we stay at 5
_last_call: dict[str, float] = {}


def user_agent(host: str) -> str:
    if host.endswith("sec.gov"):
        return config.require("SEC_USER_AGENT")  # SEC requires a declared contact; kept out of the repo
    return DEFAULT_UA


def _throttle(host: str) -> None:
    wait = MIN_INTERVAL.get(host, 0.5) - (time.monotonic() - _last_call.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    _last_call[host] = time.monotonic()


def raw_path(source: str, url: str, suffix: str = "", day: date | None = None) -> Path:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", urlparse(url).path.strip("/"))[-80:] or "index"
    digest = hashlib.sha1(url.encode()).hexdigest()[:8]
    return RAW_DIR / source / (day or date.today()).isoformat() / f"{name}_{digest}{suffix}"


def get(url: str, source: str, params: dict | None = None, save: bool = True, retries: int = 3,
        timeout: float = 60) -> requests.Response:
    """GET with throttling and retries on 429/5xx. Raises for other HTTP errors."""
    host = urlparse(url).netloc
    for attempt in range(retries + 1):
        _throttle(host)
        r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": user_agent(host)})
        if r.status_code in (429, 500, 502, 503, 504) and attempt < retries:
            time.sleep(2 ** attempt * 2)
            continue
        r.raise_for_status()
        if save:
            full = r.url if params else url
            p = raw_path(source, full)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(r.content)
        return r
    raise RuntimeError("unreachable")
