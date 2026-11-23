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
STARTS = ["2019-01-01", "2021-01-01", "2022-01-01", "2023-01-01", "2023-07-01", "2024-01-01", "2024-07-01",
          "2025-01-01", "2025-07-01", "2026-01-01"]


def _summary(result: dict) -> dict:
    serie = result.get("serie_0") or {}
    ts = serie.get("timestamps") or []
    return {"meta": result.get("meta"), "groups": [k for k in serie if k != "timestamps"], "n": len(ts),
            "first": ts[0] if ts else None, "last": ts[-1] if ts else None,
            "keys": list(result.keys())}


def run(out_dir: Path) -> None:
    report = {}
    for name, (path, params) in CANDIDATES.items():
        tries = []
        for start in STARTS:
            agg = {} if name == "ranking_genai" else {"aggInterval": "1w"}
            try:
                res = cf.get(path, {**params, **agg, **cf.window(start)}, retries=1)
            except Exception as exc:  # noqa: BLE001
                tries.append({"start": start, "error": str(exc)[:300]})
                continue
            tries.append({"start": start, "ok": True, **_summary(res)})
            (out_dir / f"{name}.json").write_text(json.dumps(res), encoding="utf-8")
            break
        try:  # daily shape and lastUpdated for the last two weeks
            res = cf.get(path, {**params, "aggInterval": "1d", "dateRange": "14d"}, retries=1)
            tries.append({"daily14": True, **_summary(res)})
            (out_dir / f"{name}_daily.json").write_text(json.dumps(res), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            tries.append({"daily14": True, "error": str(exc)[:300]})
        report[name] = tries
        print(name, [t.get("start", "d14") + (" ok" if t.get("ok") or "n" in t else " err") for t in tries])
    (out_dir / "probe.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
