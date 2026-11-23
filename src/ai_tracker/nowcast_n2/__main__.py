"""Live N2 forecast: python -m ai_tracker.nowcast_n2 --origin YYYY-MM-DD [--refresh]

Writes forecasts/n2/<target month>.json once. Refuses to overwrite, refuses an origin that is not day 5, and
refuses when the target month's outcome is already in the table (then it would not be a forecast).
--refresh fetches tsmc_revenue_m and the indicators first (network).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ai_tracker import evaluation, observations
from ai_tracker.nowcast_n2 import engine

FORECAST_DIR = evaluation.REPO / "forecasts" / "n2"
# Set mechanically by the pre-registered promotion rule (backtest.py, docs/resultat/n2.md). B1 unless V1 passes.
CHAMPION = "B1"


def payload(fc: engine.Forecast, table: pd.DataFrame, champion: str = CHAMPION) -> dict:
    levels = fc.levels()
    if levels.get(champion) is None:
        raise RuntimeError(f"champion {champion} has no forecast for {fc.month}")
    t = engine.slim(table)
    return {
        "target": engine.TARGET,
        "unit": "mn TWD",
        "month": str(fc.month),
        "origin": str(fc.origin.date()),
        "champion": champion,
        "value": levels[champion],
        "variants": levels,
        "v1": {"n_train": fc.n_train, "lambda": fc.lam, "features": fc.inputs.x},
        "inputs": [{"series": s, "period": p, "value": v, "known_from": str(pd.Timestamp(k).date())}
                   for s, p, v, k in fc.inputs.used],
        "table_max_fetched_at": str(pd.Timestamp(t["fetched_at"].max()).date()) if len(t) else None,
        "git_sha": evaluation.git_sha(),
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def write(origin, table: pd.DataFrame, out_dir: Path = FORECAST_DIR, champion: str = CHAMPION) -> Path:
    origin = pd.Timestamp(origin)
    month = engine.target_for(origin)
    path = Path(out_dir) / f"{month}.json"
    if path.exists():
        raise FileExistsError(f"{path} exists; live forecasts are never rewritten")
    if str(month) in set(table.loc[table["series"] == engine.TARGET, "period"]):
        raise RuntimeError(f"outcome for {month} is already in the table; this would not be a live forecast")
    fc = engine.forecast(origin, table)
    data = payload(fc, table, champion)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:  # 'x' = fail if it appeared meanwhile
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--origin", required=True, help="forecast origin, day 5 of the month after the target month")
    ap.add_argument("--refresh", action="store_true", help="fetch the target and indicator series first")
    ap.add_argument("--out-dir", default=str(FORECAST_DIR))
    a = ap.parse_args(argv)
    if a.refresh:
        observations.refresh([engine.TARGET, *engine.INDICATORS])
    path = write(a.origin, observations.load(), Path(a.out_dir))
    print(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
