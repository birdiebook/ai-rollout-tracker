"""Cloudflare Radar API (api.cloudflare.com/client/v4/radar): AI bot and crawler traffic (G3, track B3).

Needs CLOUDFLARE_API_TOKEN (custom token, Account > Radar: Read). The token exists only in GitHub Actions, so the
API is called by the job `ai_tracker.jobs.cloudflare_radar` (workflow job.yml) and by the weekly fetch
(fetch-weekly.yml passes the secret). Locally, `CLOUDFLARE_RADAR_JOB_DIR` points at a downloaded job artifact and
the same series are read from its CSV files instead (`load_job_csv`).

Values are shares in per cent (normalization PERCENTAGE), never min-max scaled volumes: a MIN0_MAX series is
rescaled to the maximum of each response, so every fetch would rewrite the whole history.

Licence (developers.cloudflare.com/radar, source src/content/docs/radar/index.mdx in cloudflare/cloudflare-docs):
"Data available via Radar API endpoints is made available under the CC BY-NC 4.0 license."
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import requests

from ai_tracker import config
from ai_tracker.http import DEFAULT_UA

BASE = "https://api.cloudflare.com/client/v4/radar"
TOKEN_ENV = "CLOUDFLARE_API_TOKEN"
JOB_DIR_ENV = "CLOUDFLARE_RADAR_JOB_DIR"
LICENSE = ("CC BY-NC 4.0 (developers.cloudflare.com/radar: \"Data available via Radar API endpoints is made "
           "available under the CC BY-NC 4.0 license.\"). Attribution: Cloudflare Radar")


@dataclass(frozen=True)
class Query:
    """One Radar timeseries_groups request; `group` picks the share series out of the response."""

    path: str
    group: str
    params: dict = field(default_factory=dict)
    start: str = "2024-01-01"  # first dateStart to ask for (earliest the endpoint accepts, from the probe)


def token() -> str:
    return config.require(TOKEN_ENV)


def get(path: str, params: dict, retries: int = 4, timeout: float = 120) -> dict:
    """GET a Radar endpoint as JSON. Raises with the API's own error message (never the token)."""
    headers = {"Authorization": f"Bearer {token()}", "User-Agent": DEFAULT_UA}
    for attempt in range(retries + 1):
        r = requests.get(f"{BASE}{path}", params={**params, "format": "json"}, headers=headers, timeout=timeout)
        if r.status_code in (429, 500, 502, 503, 504) and attempt < retries:
            time.sleep(2 ** attempt * 3)
            continue
        try:
            body = r.json()
        except ValueError:
            r.raise_for_status()
            raise
        if not r.ok or not body.get("success", False):
            errs = "; ".join(str(e.get("message", e)) for e in body.get("errors", []))[:300]
            raise RuntimeError(f"Radar {path}: HTTP {r.status_code}: {errs}")
        time.sleep(0.3)  # well under the API's 1200 requests / 5 min
        return body["result"]
    raise RuntimeError("unreachable")


def parse_groups(result: dict) -> pd.DataFrame:
    """A timeseries_groups result -> long frame (timestamp, group, value).

    Radar answers {"meta": ..., "serie_0": {"timestamps": [...], "<group>": [...], ...}}; values are strings.
    """
    serie = result.get("serie_0") or next(v for k, v in result.items() if k != "meta")
    ts = pd.to_datetime(serie["timestamps"], utc=True).tz_localize(None)
    rows = []
    for g, vals in serie.items():
        if g == "timestamps":
            continue
        rows.append(pd.DataFrame({"timestamp": ts, "group": g, "value": pd.to_numeric(pd.Series(vals),
                                                                                         errors="coerce")}))
    if not rows:
        return pd.DataFrame(columns=["timestamp", "group", "value"])
    return pd.concat(rows, ignore_index=True)


def weekly(result: dict, group: str, today: pd.Timestamp | None = None) -> pd.Series:
    """Weekly share (per cent) of `group` on W-SUN periods, complete weeks only.

    Radar's 1w buckets are labelled by their start; the bucket must start on a Monday (else the window was not
    week-aligned and the data is refused) and must have ended before `today` (no partial last week).
    """
    df = parse_groups(result)
    df = df[df["group"] == group]
    if df.empty:
        raise ValueError(f"group {group!r} not in Radar response")
    starts = pd.DatetimeIndex(df["timestamp"]).normalize()
    if (starts.dayofweek != 0).any():
        raise ValueError("Radar weekly buckets do not start on Mondays")
    today = pd.Timestamp(today or pd.Timestamp.now(tz="UTC").date()).normalize()
    ends = starts + pd.Timedelta(days=7)
    keep = (ends <= today).to_numpy() & df["value"].notna().to_numpy()
    s = pd.Series(df["value"].to_numpy()[keep], index=pd.PeriodIndex(starts[keep], freq="W-SUN"))
    return s[~s.index.duplicated(keep="last")].sort_index()


def window(start: str, today: pd.Timestamp | None = None) -> dict:
    """dateStart/dateEnd for whole weeks: from the Monday on or after `start` to the latest Monday 00:00 UTC."""
    today = pd.Timestamp(today or pd.Timestamp.now(tz="UTC").date()).normalize()
    end = today - pd.Timedelta(days=today.dayofweek)
    s = pd.Timestamp(start).normalize()
    s += pd.Timedelta(days=(7 - s.dayofweek) % 7)
    return {"dateStart": s.strftime("%Y-%m-%dT00:00:00Z"), "dateEnd": end.strftime("%Y-%m-%dT00:00:00Z")}


def fetch_query(q: Query, today: pd.Timestamp | None = None) -> tuple[pd.Series, dict]:
    """Weekly series for `q` from the API, plus the response meta (lastUpdated, confidenceInfo)."""
    result = get(q.path, {**q.params, "aggInterval": "1w", **window(q.start, today)})
    return weekly(result, q.group, today), result.get("meta", {})


def job_csv(out_dir: Path, key: str) -> Path:
    return Path(out_dir) / f"{key}.csv"


def load_job_csv(key: str, job_dir: str | Path | None = None) -> pd.Series:
    """The weekly series `key` from a downloaded job artifact (CSV period,value)."""
    job_dir = job_dir or config.get(JOB_DIR_ENV)
    if not job_dir:
        raise RuntimeError(f"{TOKEN_ENV} is not set and no {JOB_DIR_ENV} (downloaded job artifact) is given")
    df = pd.read_csv(job_csv(Path(job_dir), key), dtype={"period": str})
    return pd.Series(df["value"].to_numpy(dtype=float), index=pd.PeriodIndex(df["period"], freq="W-SUN"))


def series(key: str, q: Query) -> pd.Series:
    """Spec.fetch: the API when the token is present (Actions), else the job artifact (local track runs)."""
    if os.environ.get(TOKEN_ENV) or config.get(TOKEN_ENV):
        return fetch_query(q)[0]
    return load_job_csv(key)
