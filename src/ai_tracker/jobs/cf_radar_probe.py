"""One-off probe (track B3): which Radar AI endpoints answer, how far back, and in what shape.

Writes probe.json (status per endpoint and start date, groups, first/last timestamp, meta) and the raw weekly
responses (public aggregates). Removed once the series are fixed.
"""

from __future__ import annotations

import json
from pathlib import Path

from ai_tracker.sources import cloudflare_radar as cf

CANDIDATES = {
    "crawlers_client_type": ("/bots/crawlers/timeseries_groups/CLIENT_TYPE", {"normalization": "PERCENTAGE"}),
    "ai_bots_user_agent": ("/ai/bots/timeseries_groups/USER_AGENT", {"normalization": "PERCENTAGE",
                                                                      "limitPerGroup": 12}),
    "ai_bots_crawl_purpose": ("/ai/bots/timeseries_groups/CRAWL_PURPOSE", {"normalization": "PERCENTAGE"}),
    "ai_bots_volume": ("/ai/bots/timeseries", {}),
    "bots_category": ("/bots/timeseries_groups/BOT_CATEGORY", {}),
    "bots_ai_crawler_volume": ("/bots/timeseries", {"botCategory": "AI_CRAWLER"}),
    "http_bot_class": ("/http/timeseries_groups/bot_class", {}),
    "crawlers_user_agent": ("/bots/crawlers/timeseries_groups/USER_AGENT", {"normalization": "PERCENTAGE",
                                                                             "limitPerGroup": 12}),
    "inference_task": ("/ai/inference/timeseries_groups/TASK", {"normalization": "PERCENTAGE"}),
    "ranking_genai": ("/ranking/internet_services/timeseries_groups", {"serviceCategory": "Generative AI",
                                                                       "limit": 10}),
}
CHUNK_WEEKS = 50  # a 2025-07-01..now (73 weeks) window was refused, 2026-01-01..now (47 weeks) answered


def _summary(result: dict) -> dict:
    serie = result.get("serie_0") or {}
    ts = serie.get("timestamps") or []
    groups = {k: (v[:2] + v[-2:]) for k, v in serie.items() if k != "timestamps"}
    meta = result.get("meta") or {}
    return {"n": len(ts), "first": ts[0] if ts else None, "last": ts[-1] if ts else None, "groups": groups,
            "lastUpdated": meta.get("lastUpdated"), "normalization": meta.get("normalization"),
            "confidence": (meta.get("confidenceInfo") or {}).get("level"),
            "annotations": [(a.get("description"), a.get("startDate"), a.get("endDate"), a.get("eventType"))
                            for a in (meta.get("confidenceInfo") or {}).get("annotations", [])][:8]}


def run(out_dir: Path) -> None:
    import pandas as pd

    report = {}
    end = pd.Timestamp(cf.window("2026-01-01")["dateEnd"][:10])
    for name, (path, params) in CANDIDATES.items():
        tries = []
        e = end
        for _ in range(6):  # walk back in 50-week windows until the API refuses or returns nothing
            s = e - pd.Timedelta(weeks=CHUNK_WEEKS)
            win = {"dateStart": s.strftime("%Y-%m-%dT00:00:00Z"), "dateEnd": e.strftime("%Y-%m-%dT00:00:00Z")}
            agg = {} if name == "ranking_genai" else {"aggInterval": "1w"}
            try:
                res = cf.get(path, {**params, **agg, **win}, retries=1)
            except Exception as exc:  # noqa: BLE001
                tries.append({"window": win, "error": str(exc)[:400]})
                break
            tries.append({"window": win, **_summary(res)})
            (out_dir / f"{name}_{s.date()}.json").write_text(json.dumps(res), encoding="utf-8")
            if not tries[-1]["n"]:
                break
            e = s
        try:  # daily shape and lastUpdated for the last two weeks
            res = cf.get(path, {**params, "aggInterval": "1d", "dateRange": "14d"}, retries=1)
            tries.append({"daily14": True, **_summary(res)})
        except Exception as exc:  # noqa: BLE001
            tries.append({"daily14": True, "error": str(exc)[:400]})
        report[name] = tries
    text = json.dumps(report, indent=None, default=str)
    (out_dir / "probe.json").write_text(text, encoding="utf-8")
    for name, tries in report.items():  # the log is the readable copy (artifact blob host is not reachable)
        for t in tries:
            print("PROBE", name, json.dumps(t, default=str))
