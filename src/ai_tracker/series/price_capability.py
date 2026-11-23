"""G2: price at fixed capability (docs/mattregister.md, "Ändringar 2026-11-23 – G1, G2, G9").

Value for month m = lowest blended price (USD per 1M tokens, 3 input : 1 output) among first-party API
models whose capability is at least a fixed threshold, using the LiteLLM price file as it stood at the
end of m (latest sampled commit on main dated <= month end). A price first seen after month end does
not count. Only complete months are returned.

Two variants, documented in docs/kallor/pris_formaga.md:
- `g2_price_at_capability` (registered measure): capability = Epoch ECI as fetched now. A model
  counts from its Epoch release date. ECI values and the threshold are today's estimates -> the whole
  history is a backfill (source="backfill" on first load) and leaks later information.
- `g2_price_at_capability_gpqa`: capability = Epoch's own GPQA Diamond runs, each known from its
  `Started at` + 7 days. Honest timestamps per score, but one noisy, saturating benchmark.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.sources import model_map

# Locked 2026-11-23, see docs/mattregister.md ("2026-11-23 – G2: tröskel för pris vid fast förmåga låst").
# Frontier ECI at 2025-01-01 = max ECI among Epoch models released <= 2025-01-01 (o1, 141.16), as
# fetched 2026-11-23. Never recomputed: ECI refits do not move the threshold.
ECI_THRESHOLD = 141.16
# Benchmark variant: best Epoch GPQA Diamond run among models released <= 2025-01-01
# (o1-2024-12-17, high effort, 152/198 = 0.767677), floored to 6 decimals so o1 itself qualifies.
GPQA_THRESHOLD = 0.767676
INPUT_WEIGHT, OUTPUT_WEIGHT = 3, 1
TOL = 1e-9


def blended(input_per_m, output_per_m):
    """3:1 input:output blended price per 1M tokens."""
    return (INPUT_WEIGHT * np.asarray(input_per_m, dtype=float) + OUTPUT_WEIGHT * np.asarray(output_per_m, dtype=float)) \
        / (INPUT_WEIGHT + OUTPUT_WEIGHT)


def prices_at(snapshots: pd.DataFrame, when: pd.Timestamp) -> pd.DataFrame:
    """Price rows of the latest snapshot dated <= `when` (empty if none)."""
    s = snapshots[snapshots["snapshot_date"] <= pd.Timestamp(when)]
    if s.empty:
        return s
    return s[s["snapshot_date"] == s["snapshot_date"].max()]


def capability_eci(eci: pd.DataFrame):
    """when -> {model: capability} for models released by `when` (ECI as fetched, not as known then)."""
    def at(when: pd.Timestamp) -> dict[str, float]:
        e = eci[eci["release"] <= when]
        return dict(zip(e["model"], e["eci"]))
    return at


def capability_gpqa(runs: pd.DataFrame):
    """when -> {model: best GPQA score among runs known by `when`}."""
    def at(when: pd.Timestamp) -> dict[str, float]:
        r = runs[runs["known_from"] <= when]
        return r.groupby("model")["score"].max().to_dict()
    return at


def key_capability(capability: dict[str, float], release: dict[str, pd.Timestamp], when: pd.Timestamp,
                   mapping: pd.DataFrame) -> dict[str, float]:
    """Capability per LiteLLM key at `when`: that of the most recently released mapped model
    (release <= when). A rolling alias thus follows the model it serves; if that model has no known
    capability, the key has none."""
    m = mapping.assign(release=mapping["model"].map(release))
    m = m[m["release"].notna() & (m["release"] <= when)]
    out = {}
    for key, grp in m.sort_values(["release", "model"]).groupby("key"):
        latest = grp.iloc[-1]["model"]
        if latest in capability:
            out[key] = capability[latest]
    return out


def month_value(snapshots: pd.DataFrame, when: pd.Timestamp, capability: dict[str, float],
                release: dict[str, pd.Timestamp], threshold: float, mapping: pd.DataFrame) -> dict | None:
    """Lowest qualifying blended price at `when`, with the key and model that set it."""
    p = prices_at(snapshots, when)
    if p.empty:
        return None
    p = p.merge(mapping[["key", "provider"]].drop_duplicates(), on=["key", "provider"])  # first-party only
    cap = key_capability(capability, release, when, mapping)
    p = p.assign(capability=p["key"].map(cap)).dropna(subset=["capability"])
    p = p[p["capability"] >= threshold - TOL]
    if p.empty:
        return None
    p = p.assign(blended=blended(p["input_per_m"], p["output_per_m"])).sort_values(["blended", "key"])
    best = p.iloc[0]
    model = mapping[mapping["key"] == best["key"]].assign(r=lambda d: d["model"].map(release))
    model = model[model["r"] <= when].sort_values("r").iloc[-1]["model"]
    return {"value": float(best["blended"]), "key": best["key"], "model": model,
            "capability": float(best["capability"]), "n_qualifying": int(p["key"].nunique()),
            "snapshot_date": best["snapshot_date"]}


def build(snapshots: pd.DataFrame, capability_at, release: dict[str, pd.Timestamp], threshold: float,
          end: pd.Timestamp, mapping: pd.DataFrame | None = None) -> pd.DataFrame:
    """Monthly table (period index): value, key, model, capability, n_qualifying, snapshot_date.
    Only months that ended on or before `end`."""
    mapping = model_map.key_models() if mapping is None else mapping
    start = snapshots["snapshot_date"].min().to_period("M")
    last = (pd.Timestamp(end) + pd.Timedelta(days=1)).to_period("M") - 1  # last complete month
    rows = {}
    for period in pd.period_range(start, last, freq="M"):
        when = period.end_time.normalize()
        v = month_value(snapshots, when, capability_at(when), release, threshold, mapping)
        if v:
            rows[period] = v
    return pd.DataFrame.from_dict(rows, orient="index").sort_index()


@lru_cache(maxsize=1)
def _inputs():
    from ai_tracker.sources import epoch_capability, litellm_prices

    return litellm_prices.snapshots(), epoch_capability.load()


def _release(epoch: dict[str, pd.DataFrame]) -> dict[str, pd.Timestamp]:
    """Release date per Epoch model: ECI table first, GPQA runs for models without ECI."""
    rel = epoch["gpqa"].groupby("model")["release"].min().to_dict()
    rel.update(dict(zip(epoch["eci"]["model"], epoch["eci"]["release"])))
    return rel


def table(variant: str = "eci", end: pd.Timestamp | None = None) -> pd.DataFrame:
    snaps, epoch = _inputs()
    end = pd.Timestamp.today().normalize() if end is None else pd.Timestamp(end)
    if variant == "eci":
        return build(snaps, capability_eci(epoch["eci"]), _release(epoch), ECI_THRESHOLD, end)
    if variant == "gpqa":
        return build(snaps, capability_gpqa(epoch["gpqa"]), _release(epoch), GPQA_THRESHOLD, end)
    raise ValueError(variant)


def fetch_eci() -> pd.Series:
    t = table("eci")
    return t["value"].rename("g2_price_at_capability")


def fetch_gpqa() -> pd.Series:
    t = table("gpqa")
    return t["value"].rename("g2_price_at_capability_gpqa")


LICENSE = ("derived: LiteLLM model_prices_and_context_window.json (MIT, LICENSE in BerriAI/litellm) "
           "+ Epoch AI benchmarking hub (CC BY 4.0, README in benchmark_data.zip); credit Epoch AI")

SPECS = [
    Spec(key="g2_price_at_capability", branch="G2",
         label="Pris vid fast förmåga (ECI ≥ frontens nivå 2025-01-01)",
         unit="USD per 1M tokens (3:1 input:output)", freq="M", source="LiteLLM git-historik × Epoch AI ECI",
         fetch=fetch_eci, lag_days=0, license=LICENSE, revised=True, publish=True,
         question="Hur mycket billigare blir en fast förmågenivå?",
         note="Historiken är bakåtfylld: ECI och tröskeln är dagens skattningar (läckage). Se docs/kallor/pris_formaga.md"),
    Spec(key="g2_price_at_capability_gpqa", branch="G2",
         label="Pris vid fast förmåga (GPQA Diamond ≥ frontens nivå 2025-01-01)",
         unit="USD per 1M tokens (3:1 input:output)", freq="M", source="LiteLLM git-historik × Epoch AI GPQA Diamond",
         fetch=fetch_gpqa, lag_days=0, license=LICENSE, revised=True, publish=True,
         question="Samma mått med ärliga tidsstämplar för förmågan (Epochs egna körningar)",
         note="Förmåga känd från Epochs körning (Started at + 7 dagar). En brusig benchmark nära taket. Se docs/kallor/pris_formaga.md"),
]
