"""G2 from our own first-party price snapshots (track B5): price at fixed capability, independent of LiteLLM.

`g2_fp_price_at_capability_gpqa_anthropic` (month): lowest blended price (3 input : 1 output, USD per 1M
tokens) among Anthropic models that are generally available on Anthropic's own API and whose Epoch GPQA
Diamond capability, as known at month end, is at least the locked threshold (price_capability.GPQA_THRESHOLD,
docs/mattregister.md 2026-11-23). Prices come from our latest snapshot of Anthropic's pricing page dated
within SNAPSHOT_MAX_AGE_DAYS before month end (sources/firstparty_prices.py); no snapshot in that window
= no value (a gap, never a stale carry-forward). Base tier only; retired and limited-availability models
never count.

One developer per series: only Anthropic's page is reachable and allowed (docs/kallor/priser.md). A
cross-developer minimum over whichever hosts happen to be open would change definition whenever a host
opens, so a combined series is registered only when more developers are collected.

known_from = month end + 1 day (the month's state includes a snapshot taken on the last day; same rule as
price_capability.LAG_DAYS). History starts with our first snapshot (2026-11-23): nothing is backfilled.
"""

from __future__ import annotations

import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.series import price_capability as pc
from ai_tracker.sources import firstparty_prices as fp
from ai_tracker.sources import model_map

SNAPSHOT_MAX_AGE_DAYS = 7  # weekly collector (Mondays): the last Monday of a month is <= 6 days before its end
LAG_DAYS = pc.LAG_DAYS
# Published model name -> Epoch model name, where they differ. Anthropic's page uses Epoch's names, and a
# name counts only if it is an Epoch model in model_map.MODEL_MAP for the developer (tested).
EPOCH_NAME: dict[str, dict[str, str]] = {"anthropic": {}}


def epoch_model(developer: str, name: str) -> str | None:
    name = EPOCH_NAME.get(developer, {}).get(name, name)
    entry = model_map.MODEL_MAP.get(name)
    provider = fp.PROVIDERS[developer].litellm_provider
    return name if entry and entry[0] == provider else None


def month_value(store: pd.DataFrame, developer: str, when: pd.Timestamp, capability: dict[str, float],
                threshold: float) -> dict | None:
    s = store[(store["developer"] == developer) & (store["snapshot_date"] <= when)
              & (store["snapshot_date"] > when - pd.Timedelta(days=SNAPSHOT_MAX_AGE_DAYS + 1))]
    if s.empty:
        return None
    s = s[s["snapshot_date"] == s["snapshot_date"].max()]
    s = s[s["base_tier"] & (s["availability"] == "available")]
    s = s.assign(epoch=[epoch_model(developer, m) for m in s["model"]])
    s = s.assign(capability=s["epoch"].map(capability)).dropna(subset=["capability"])
    s = s[s["capability"] >= threshold - pc.TOL]
    if s.empty:
        return None
    s = s.assign(blended=pc.blended(s["input_per_m"], s["output_per_m"])).sort_values(["blended", "model"])
    best = s.iloc[0]
    return {"value": float(best["blended"]), "model": best["model"], "capability": float(best["capability"]),
            "n_qualifying": int(s["model"].nunique()), "snapshot_date": best["snapshot_date"]}


def build(store: pd.DataFrame, developer: str, capability_at, threshold: float, end: pd.Timestamp) -> pd.DataFrame:
    """Monthly table: period, value, known_from, model, capability, n_qualifying, snapshot_date.
    Complete months only (month end <= `end`)."""
    cols = ["period", "value", "known_from", "model", "capability", "n_qualifying", "snapshot_date"]
    store = store[store["developer"] == developer]
    if store.empty:
        return pd.DataFrame(columns=cols)
    start = store["snapshot_date"].min().to_period("M")
    last = (pd.Timestamp(end) + pd.Timedelta(days=1)).to_period("M") - 1
    rows = []
    for period in pd.period_range(start, last, freq="M"):
        when = period.end_time.normalize()
        v = month_value(store, developer, when, capability_at(when), threshold)
        if v:
            rows.append({"period": period, "known_from": when + pd.Timedelta(days=LAG_DAYS), **v})
    return pd.DataFrame(rows, columns=cols)


def table(developer: str = "anthropic", end: pd.Timestamp | None = None, store: pd.DataFrame | None = None,
          gpqa: pd.DataFrame | None = None) -> pd.DataFrame:
    from ai_tracker.sources import epoch_capability

    store = fp.load() if store is None else store
    if gpqa is None:
        gpqa = epoch_capability.load()["gpqa"]
    end = pd.Timestamp.today().normalize() if end is None else pd.Timestamp(end)
    return build(store, developer, pc.capability_gpqa(gpqa), pc.GPQA_THRESHOLD, end)


def fetch_anthropic() -> pd.DataFrame:
    """Take this week's snapshot (idempotent per day), then compute the series from all own snapshots."""
    status = fp.take_snapshot(providers=[fp.PROVIDERS["anthropic"]])
    if status["anthropic"].startswith("FAILED"):
        raise RuntimeError(f"anthropic snapshot {status['anthropic']}")
    return table("anthropic")[["period", "value", "known_from"]]


LICENSE = ("derived: Anthropic pricing page (platform.claude.com, prices are list prices; no data licence stated, "
           "redistribution not checked) + Epoch AI benchmarking hub (CC BY 4.0)")

SPECS = [
    Spec(key="g2_fp_price_at_capability_gpqa_anthropic", branch="G2",
         label="Pris vid fast förmåga, Anthropics egen prislista (GPQA Diamond ≥ frontens nivå 2025-01-01)",
         unit="USD per 1M tokens (3:1 input:output)", freq="M", source="Egna ögonblicksbilder av Anthropics prissida × Epoch AI GPQA Diamond",
         fetch=fetch_anthropic, lag_days=LAG_DAYS, license=LICENSE, revised=True, publish=False,
         question="Samma mått som g2_price_at_capability_gpqa, men med priset direkt från utvecklaren (oberoende av LiteLLM)",
         note="Egna veckovisa ögonblicksbilder från 2026-11-23, ingen bakåtfyllning. En utvecklare. Se docs/kallor/priser.md"),
]
