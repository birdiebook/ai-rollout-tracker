"""G2: price at fixed capability per provider (GPQA Diamond variant), track G12 (docs/kallor/g1g2_nya.md).

Same measure as `g2_price_at_capability_gpqa` (price_capability.py: lowest 3:1 blended first-party price among the
provider's models whose best Epoch GPQA Diamond run known at month end is >= 0.767676; LiteLLM file as it stood at
month end), restricted to one provider's own API. Two differences, both towards later dates:
- a GPQA run counts from `Started at` + 30 days (register 2026-11-23, benchmark values), not + 7;
- rows are release-dated (known_from = month end + 1): every input is dated (LiteLLM commits on main, Epoch runs by
  start + 30 days). A value that changes later (Epoch re-runs or drops a run, LiteLLM history is rewritten) becomes
  a revision dated on the fetch day (epoch_hub.with_revisions).
Only providers with a value in every month from their first month are listed (OpenAI, Anthropic, Google, DeepSeek).
"""

from __future__ import annotations

from functools import lru_cache, partial

import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.series import price_capability as pc
from ai_tracker.sources import epoch_hub, model_map

RUN_LAG_DAYS = 30
PROVIDERS = {"openai": "OpenAI", "anthropic": "Anthropic", "gemini": "Google (Gemini API)", "deepseek": "DeepSeek"}


def provider_table(snaps: pd.DataFrame, epoch: dict, provider: str, end: pd.Timestamp,
                   mapping: pd.DataFrame | None = None) -> pd.DataFrame:
    """Monthly table for one provider (index = period), like price_capability.build."""
    mapping = model_map.key_models() if mapping is None else mapping
    runs = epoch["gpqa"].copy()
    runs["known_from"] = runs["known_from"] + pd.Timedelta(days=RUN_LAG_DAYS - 7)  # parse_gpqa adds 7
    return pc.build(snaps, pc.capability_gpqa(runs), pc._release(epoch), pc.GPQA_THRESHOLD, end,
                    mapping[mapping["provider"] == provider])


@lru_cache(maxsize=None)
def _table(provider: str) -> pd.DataFrame:
    snaps, epoch = pc._inputs()
    return provider_table(snaps, epoch, provider, pd.Timestamp.today().normalize())


def fetch(provider: str) -> pd.DataFrame:
    key = f"g2_price_at_capability_gpqa_{provider}"
    t = _table(provider)
    if t.empty:
        return pd.DataFrame(columns=["period", "value", "known_from"])
    frame = epoch_hub.release_frame(t["value"], lag_days=pc.LAG_DAYS)
    return epoch_hub.with_revisions(frame, key)


SPECS = [
    Spec(key=f"g2_price_at_capability_gpqa_{p}", branch="G2",
         label=f"Pris vid fast förmåga, {name} (GPQA Diamond ≥ frontens nivå 2025-01-01)",
         unit="USD per 1M tokens (3:1 input:output)", freq="M",
         source=f"LiteLLM git-historik ({name}) × Epoch AI GPQA Diamond", fetch=partial(fetch, p),
         lag_days=pc.LAG_DAYS, license=pc.LICENSE, revised=True, publish=True,
         question=f"Hur mycket billigare blir en fast förmågenivå hos {name}?",
         note="Förmåga från Epochs körning + 30 dagar, priser från LiteLLM-commits på main; release-daterad. "
              "Historik från 2025-03 (Epochs GPQA-körningar börjar 2025-01-27). Se docs/kallor/g1g2_nya.md")
    for p, name in PROVIDERS.items()
]
