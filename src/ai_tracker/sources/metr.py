"""METR time horizon (benchmark_results_1_1.yaml): reference series only (mattregister 2026-11-23).

Licence (https://metr.org/time-horizons/): "The data and plots on this page are licensed under CC BY 4.0.
Please attribute to METR."

known_from. `release_date` in the YAML is the model's release, not when METR published the measurement. The
page's update log gives publication dates ("April 10th, 2026: Added GPT-5.4"). The numbers in the v1.1 file are
the ones after "March 3rd, 2026: Corrected a regularization mistake", so for every model

    known_from = max(date of the latest log entry naming the model, 2026-03-03)

A model the log does not name was in the set before the correction (the log lists every addition since
2025-03), so it gets 2026-03-03. The page is frozen ("no longer actively updated", last updated 2026-09-08).
"""

from __future__ import annotations

import html
import re
from functools import lru_cache

import pandas as pd
import yaml

from ai_tracker import http

YAML_URL = "https://metr.org/assets/benchmark_results_1_1.yaml"
PAGE_URL = "https://metr.org/time-horizons/"
SOURCE = "metr"
LICENSE = "CC BY 4.0 (metr.org/time-horizons: \"licensed under CC BY 4.0. Please attribute to METR.\")"
CORRECTION_DATE = pd.Timestamp("2026-03-03")

_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
_ENTRY = re.compile(rf"<li>\s*<strong>\s*(({_MONTHS})\s+\d{{1,2}})(?:st|nd|rd|th)?,\s*(\d{{4}})\s*:?\s*</strong>"
                    r"\s*:?\s*(.*?)</li>", re.S)


def norm(name: str) -> str:
    """Comparable model name: 'Claude Opus 4.6' and 'claude_opus_4_6_inspect' -> 'claudeopus46'."""
    name = re.sub(r"_inspect$", "", name.strip().lower())
    return re.sub(r"[^a-z0-9]", "", name)


def parse_update_log(page: str) -> list[tuple[pd.Timestamp, str]]:
    """[(date, text)] from the page's Updates list."""
    out = []
    for m in _ENTRY.finditer(page):
        day = pd.Timestamp(f"{m.group(1)} {m.group(3)}")
        text = html.unescape(re.sub(r"<[^>]+>", "", m.group(4))).strip()
        out.append((day, text))
    return out


def added_names(text: str) -> list[str]:
    """Model names in an 'Added X, Y and Z' entry."""
    m = re.match(r"Added\s+(.*)", text)
    if not m:
        return []
    body = re.split(r"\s+and notice\b|\.\s*$", m.group(1))[0]
    parts = re.split(r",\s*(?:and\s+)?|\s+and\s+", body)
    return [p.strip(" .\"“”") for p in parts if p.strip(" .")]


def parse_results(text: str) -> pd.DataFrame:
    """Per model: key, release_date, p50 (minutes), is_sota."""
    d = yaml.safe_load(text)
    rows = []
    for key, r in (d.get("results") or {}).items():
        m = r.get("metrics", {})
        p50 = (m.get("p50_horizon_length") or {}).get("estimate")
        if p50 is None or r.get("release_date") is None:
            continue
        rows.append((key, pd.Timestamp(str(r["release_date"])), float(p50), bool(m.get("is_sota", False))))
    return pd.DataFrame(rows, columns=["key", "release_date", "p50", "is_sota"])


def known_from_dates(results: pd.DataFrame, log: list[tuple[pd.Timestamp, str]]) -> pd.Series:
    latest: dict[str, pd.Timestamp] = {}
    for day, text in log:
        for name in added_names(text):
            n = norm(name)
            latest[n] = max(latest.get(n, day), day)
    return results["key"].map(lambda k: max(latest.get(norm(k), CORRECTION_DATE), CORRECTION_DATE))


def frontier_vintages(release: pd.Series, value: pd.Series, known: pd.Series) -> pd.DataFrame:
    """Monthly frontier by release month with every vintage: rows (period, value, known_from).

    Value of month m as known on day d = max over models released by the end of m whose known_from <= d.
    The row's known_from is max(d, first day after m). Months: first to last release month.
    """
    df = pd.DataFrame({"release": pd.to_datetime(release), "value": value, "known": pd.to_datetime(known)})
    months = pd.period_range(df["release"].min().to_period("M"), df["release"].max().to_period("M"), freq="M")
    rows = []
    for m in months:
        sub = df[df["release"] <= m.end_time]
        prev = None
        for d in sorted(sub["known"].unique()):
            v = sub.loc[sub["known"] <= d, "value"].max()
            kf = max(pd.Timestamp(d), m.end_time.normalize() + pd.Timedelta(days=1))
            if prev is None or v != prev:
                if rows and rows[-1][0] == str(m) and rows[-1][2] == kf:
                    rows[-1] = (str(m), float(v), kf)
                else:
                    rows.append((str(m), float(v), kf))
                prev = v
    return pd.DataFrame(rows, columns=["period", "value", "known_from"])


@lru_cache(maxsize=None)
def _texts() -> tuple[str, str]:
    return http.get(YAML_URL, SOURCE).text, http.get(PAGE_URL, SOURCE).text


def horizon_frontier() -> pd.DataFrame:
    from ai_tracker.sources.epoch_hub import with_revisions

    text, page = _texts()
    res = parse_results(text)
    log = parse_update_log(page)
    if not log:
        raise RuntimeError("METR update log not found on the page (layout changed?)")
    frame = frontier_vintages(res["release_date"], res["p50"], known_from_dates(res, log))
    return with_revisions(frame, "g1_metr_horizon_p50_frontier")
