"""Shared HTTP client: honest User-Agent, per-host rate limit, retries, raw copies with fetch date.

Never impersonate a browser or work around bot protection. A refused request is a BLOCKED source.
Raw responses are saved under data/raw/<source>/<YYYY-MM-DD>/ (never committed).

Shared raw cache: AI_TRACKER_SHARED_RAW (environment, .env.local or .env) moves RAW_DIR to a directory that
parallel worktrees share, read and write-through. Safe for these files: each is named by source, fetch date and
a hash of the URL, and written atomically, so two tracks fetching the same URL on the same day write the same
content to the same name. Unset (default): data/raw in this worktree. docs/drift.md, "Delad data", lists the
mutable files that also live under RAW_DIR.
"""

from __future__ import annotations

import hashlib
import os
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import requests

from ai_tracker import config

DEFAULT_UA = "ai-rollout-tracker (github.com/birdiebook/ai-rollout-tracker)"
RAW_DIR = Path(config.get("AI_TRACKER_SHARED_RAW") or config.REPO / "data" / "raw").expanduser()
MIN_INTERVAL = {"data.sec.gov": 0.2, "www.sec.gov": 0.2}  # SEC fair access: <= 10 req/s; we stay at 5
_last_call: dict[str, float] = {}


CONTACT_HOSTS = ("sec.gov", "bls.gov")  # refuse clients without a declared contact (SEC fair access, BLS policy)


def user_agent(host: str) -> str:
    host = host.lower().split(":")[0]  # netloc may carry a port
    if any(host == d or host.endswith("." + d) for d in CONTACT_HOSTS):  # the domain or a subdomain, not notbls.gov
        # The project's generic client identity with a contact address, from .env / Actions secret; never in the repo
        return config.require("SEC_USER_AGENT")
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
            tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
            tmp.write_bytes(r.content)
            os.replace(tmp, p)  # atomic: a reader in another worktree never sees half a file
        return r
    raise RuntimeError("unreachable")
