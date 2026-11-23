"""Explicit mapping: Epoch AI model name -> LiteLLM price keys, restricted to first-party APIs.

First-party rule: a price counts only from the model developer's own API, as listed in LiteLLM under
that developer's provider (`litellm_provider`) and key prefix (FIRST_PARTY). Clouds and resellers
(Azure, Bedrock, Vertex partner models, OpenRouter, Together, Fireworks, DeepInfra, ...) never count,
also not when they host the developer's own model. Google counts through the Gemini API (AI Studio,
`gemini/`), not Vertex, so each developer has exactly one price channel. Open-weight models without a
first-party API from their developer have no price here (listed in docs/kallor/pris_formaga.md).

Key rules:
- Versioned keys (dated snapshots) plus a model-specific undated alias where LiteLLM has one
  (`o3` for `o3-2025-04-16`). Never `-latest` aliases, regional (`us/`), fast-mode (`fast/`),
  contributor, batch or other special tiers.
- Rolling aliases that the developer re-points to new models (`deepseek-chat`, `deepseek-reasoner`)
  are mapped to every model they served. At a date, an alias key takes the capability of the most
  recently released mapped model (release date <= date), so before the first mapped release it has no
  capability at all.
- When the identity of an in-place update is uncertain, only the model the key certainly served is
  mapped. Unmapped updates are listed in the doc.

The table covers every Epoch model with ECI >= 128 or an Epoch GPQA Diamond run >= 0.70 (fetched
2026-11-23) that has a first-party key in LiteLLM's history, so later ECI revisions near the threshold
are covered. Built from Epoch's version ids (API names) matched to LiteLLM keys, then checked by hand.
"""

from __future__ import annotations

import pandas as pd

# provider (litellm_provider) -> allowed key prefixes ("" = bare key without "/"). The prefix check
# guards against reseller keys that LiteLLM labels with the developer's provider ("azure/o3-mini...",
# "openrouter/openai/o1-mini" carry provider "openai"). DeepSeek's own API appears under both styles.
FIRST_PARTY: dict[str, tuple[str, ...]] = {
    "openai": ("",), "anthropic": ("",), "gemini": ("gemini/",), "xai": ("xai/",),
    "deepseek": ("", "deepseek/"), "mistral": ("mistral/",), "moonshot": ("moonshot/",),
    "dashscope": ("dashscope/",), "zai": ("zai/",), "minimax": ("minimax/",), "meta": ("meta/",),
    "volcengine": ("volcengine/",),
}
EXCLUDED_KEY_PARTS = ("-latest", "us/", "fast/", "contributor", "batch", "-flex", "priority")

_DS_CHAT = ("deepseek/deepseek-chat", "deepseek-chat")
_DS_REASONER = ("deepseek/deepseek-reasoner", "deepseek-reasoner")
# The only keys allowed to map to more than one Epoch model (rolling aliases, see module docstring).
ROLLING_ALIASES = frozenset(_DS_CHAT + _DS_REASONER)

# Epoch model name -> (provider, LiteLLM keys)
MODEL_MAP: dict[str, tuple[str, tuple[str, ...]]] = {
    # ---------------------------------------------------------------- OpenAI
    "GPT-4o (May 2024)": ("openai", ("gpt-4o-2024-05-13",)),
    "GPT-4o (Nov 2024)": ("openai", ("gpt-4o-2024-11-20",)),
    "o1-preview": ("openai", ("o1-preview-2024-09-12", "o1-preview")),
    "o1-mini": ("openai", ("o1-mini-2024-09-12", "o1-mini")),
    "o1": ("openai", ("o1-2024-12-17", "o1")),
    "o3-mini": ("openai", ("o3-mini-2025-01-31", "o3-mini")),
    "GPT-4.5": ("openai", ("gpt-4.5-preview-2025-02-27", "gpt-4.5-preview")),
    "GPT-4.1": ("openai", ("gpt-4.1-2025-04-14", "gpt-4.1")),
    "GPT-4.1 mini": ("openai", ("gpt-4.1-mini-2025-04-14", "gpt-4.1-mini")),
    "o3": ("openai", ("o3-2025-04-16", "o3")),
    "o4-mini": ("openai", ("o4-mini-2025-04-16", "o4-mini")),
    "o3-pro": ("openai", ("o3-pro-2025-06-10", "o3-pro")),
    "GPT-5": ("openai", ("gpt-5-2025-08-07", "gpt-5")),
    "GPT-5 mini": ("openai", ("gpt-5-mini-2025-08-07", "gpt-5-mini")),
    "GPT-5 nano": ("openai", ("gpt-5-nano-2025-08-07", "gpt-5-nano")),
    "GPT-5 Pro": ("openai", ("gpt-5-pro-2025-10-06", "gpt-5-pro")),
    "GPT-5.1": ("openai", ("gpt-5.1-2025-11-13", "gpt-5.1")),
    "GPT-5.2": ("openai", ("gpt-5.2-2025-12-11", "gpt-5.2")),
    "GPT-5.2 Pro": ("openai", ("gpt-5.2-pro-2025-12-11", "gpt-5.2-pro")),
    "GPT-5.4": ("openai", ("gpt-5.4-2026-03-05", "gpt-5.4")),
    "GPT-5.4 Pro": ("openai", ("gpt-5.4-pro-2026-03-05", "gpt-5.4-pro")),
    "GPT-5.4 Mini": ("openai", ("gpt-5.4-mini-2026-03-17", "gpt-5.4-mini")),
    "GPT-5.4 Nano": ("openai", ("gpt-5.4-nano-2026-03-17", "gpt-5.4-nano")),
    "GPT-5.5": ("openai", ("gpt-5.5-2026-04-23", "gpt-5.5")),
    "GPT-5.5 Pro": ("openai", ("gpt-5.5-pro-2026-04-23", "gpt-5.5-pro")),
    "GPT-5.6 Sol": ("openai", ("gpt-5.6-sol",)),
    "GPT-5.6 Terra": ("openai", ("gpt-5.6-terra",)),
    "GPT-5.6 Luna": ("openai", ("gpt-5.6-luna",)),
    "GPT-6 Astra": ("openai", ("gpt-6-astra",)),
    "GPT-6 Sol": ("openai", ("gpt-6-sol",)),
    "GPT-6 Luna": ("openai", ("gpt-6-luna",)),
    "GPT-6.1 Sol": ("openai", ("gpt-6.1-sol",)),
    "GPT-6.1 Terra": ("openai", ("gpt-6.1-terra",)),
    "GPT-6.2 Astra": ("openai", ("gpt-6.2-astra",)),
    # ---------------------------------------------------------------- Anthropic
    "Claude 3.5 Sonnet": ("anthropic", ("claude-3-5-sonnet-20240620",)),
    "Claude 3.5 Sonnet (October 2024)": ("anthropic", ("claude-3-5-sonnet-20241022",)),
    "Claude 3.7 Sonnet": ("anthropic", ("claude-3-7-sonnet-20250219",)),
    "Claude Opus 4": ("anthropic", ("claude-opus-4-20250514", "claude-4-opus-20250514")),
    "Claude Sonnet 4": ("anthropic", ("claude-sonnet-4-20250514", "claude-4-sonnet-20250514")),
    "Claude Opus 4.1": ("anthropic", ("claude-opus-4-1-20250805", "claude-opus-4-1")),
    "Claude Sonnet 4.5": ("anthropic", ("claude-sonnet-4-5-20250929", "claude-sonnet-4-5")),
    "Claude Haiku 4.5": ("anthropic", ("claude-haiku-4-5-20251001", "claude-haiku-4-5")),
    "Claude Opus 4.5": ("anthropic", ("claude-opus-4-5-20251101", "claude-opus-4-5")),
    "Claude Opus 4.6": ("anthropic", ("claude-opus-4-6-20260205", "claude-opus-4-6")),
    "Claude Sonnet 4.6": ("anthropic", ("claude-sonnet-4-6",)),
    "Claude Opus 4.7": ("anthropic", ("claude-opus-4-7-20260416", "claude-opus-4-7")),
    "Claude Opus 4.8": ("anthropic", ("claude-opus-4-8",)),
    "Claude Fable 5": ("anthropic", ("claude-fable-5",)),
    "Claude Sonnet 5": ("anthropic", ("claude-sonnet-5",)),
    "Claude Opus 5": ("anthropic", ("claude-opus-5",)),
    "Claude Fable 5.1": ("anthropic", ("claude-fable-5-1",)),
    "Claude Opus 5.5": ("anthropic", ("claude-opus-5-5",)),
    "Claude Sonnet 5.5": ("anthropic", ("claude-sonnet-5-5",)),
    "Claude Haiku 5.5": ("anthropic", ("claude-haiku-5-5",)),
    "Claude Fable 5.2": ("anthropic", ("claude-fable-5-2",)),
    # ---------------------------------------------------------------- Google (Gemini API)
    "Gemini 1.5 Pro (Sept 2024)": ("gemini", ("gemini/gemini-1.5-pro-002",)),
    "Gemini 2.0 Flash (Feb 2025)": ("gemini", ("gemini/gemini-2.0-flash-001", "gemini/gemini-2.0-flash")),
    "Gemini 2.5 Pro (Mar 2025)": ("gemini", ("gemini/gemini-2.5-pro-preview-03-25",)),
    "Gemini 2.5 Flash (Apr 2025)": ("gemini", ("gemini/gemini-2.5-flash-preview-04-17",)),
    "Gemini 2.5 Pro (May 2025)": ("gemini", ("gemini/gemini-2.5-pro-preview-05-06",)),
    "Gemini 2.5 Flash (May 2025)": ("gemini", ("gemini/gemini-2.5-flash-preview-05-20",)),
    "Gemini 2.5 Pro (Jun 2025)": ("gemini", ("gemini/gemini-2.5-pro-preview-06-05", "gemini/gemini-2.5-pro")),
    "Gemini 2.5 Flash (Jun 2025)": ("gemini", ("gemini/gemini-2.5-flash",)),
    "Gemini 2.5 Flash-Lite (Jun 2025)": ("gemini", ("gemini/gemini-2.5-flash-lite-preview-06-17",)),
    "Gemini 2.5 Flash (Sep 2025)": ("gemini", ("gemini/gemini-2.5-flash-preview-09-2025",)),
    "Gemini 3 Pro": ("gemini", ("gemini/gemini-3-pro-preview",)),
    "Gemini 3 Flash": ("gemini", ("gemini/gemini-3-flash-preview",)),
    "Gemini 3.1 Pro": ("gemini", ("gemini/gemini-3.1-pro-preview",)),
    "Gemini 3.1 Flash-Lite": ("gemini", ("gemini/gemini-3.1-flash-lite-preview", "gemini/gemini-3.1-flash-lite")),
    "Gemini 3.5 Flash": ("gemini", ("gemini/gemini-3.5-flash",)),
    "Gemini 3.6 Flash": ("gemini", ("gemini/gemini-3.6-flash",)),
    "Gemini 3.5 Flash-Lite": ("gemini", ("gemini/gemini-3.5-flash-lite",)),
    "Gemini 3.7 Flash": ("gemini", ("gemini/gemini-3.7-flash",)),
    "Gemini 3.8 Flash": ("gemini", ("gemini/gemini-3.8-flash",)),
    "Gemini 4 Argon": ("gemini", ("gemini/gemini-4-argon",)),
    "Gemini 4 Carbon": ("gemini", ("gemini/gemini-4-carbon",)),
    "Gemini 4 Hydrogen": ("gemini", ("gemini/gemini-4-hydrogen",)),
    "Gemini 4 Neon": ("gemini", ("gemini/gemini-4-neon",)),
    # ---------------------------------------------------------------- xAI
    "Grok-2 (Dec 2024)": ("xai", ("xai/grok-2-1212",)),
    "Grok 3": ("xai", ("xai/grok-3", "xai/grok-3-beta")),
    "Grok-3 mini": ("xai", ("xai/grok-3-mini", "xai/grok-3-mini-beta")),
    "Grok 4": ("xai", ("xai/grok-4-0709", "xai/grok-4")),
    "Grok 4 Fast": ("xai", ("xai/grok-4-fast-reasoning",)),
    "Grok 4.20": ("xai", ("xai/grok-4.20-beta-0309-reasoning", "xai/grok-4.20-0309-reasoning")),
    "Grok 4.3 Beta": ("xai", ("xai/grok-4.3",)),
    "Grok 4.5": ("xai", ("xai/grok-4.5",)),
    "Grok 4.6": ("xai", ("xai/grok-4.6",)),
    "Grok 4.7": ("xai", ("xai/grok-4.7",)),
    # ---------------------------------------------------------------- DeepSeek (rolling aliases, see above)
    "DeepSeek-V3": ("deepseek", (*_DS_CHAT, "deepseek/deepseek-v3")),
    "DeepSeek-R1": ("deepseek", (*_DS_REASONER, "deepseek/deepseek-r1")),
    "DeepSeek-V3 (Mar 2025)": ("deepseek", _DS_CHAT),
    "DeepSeek-R1 (May 2025)": ("deepseek", _DS_REASONER),
    "DeepSeek-V3.1": ("deepseek", (*_DS_CHAT, *_DS_REASONER)),
    "DeepSeek-V3.2-Exp": ("deepseek", (*_DS_CHAT, *_DS_REASONER)),
    "DeepSeek-V3.2": ("deepseek", (*_DS_CHAT, *_DS_REASONER, "deepseek/deepseek-v3.2")),
    "DeepSeek-V4-Pro": ("deepseek", ("deepseek/deepseek-v4-pro", "deepseek-v4-pro")),
    "DeepSeek-V4-Flash": ("deepseek", ("deepseek/deepseek-v4-flash", "deepseek-v4-flash")),
    # ---------------------------------------------------------------- Mistral
    "Mistral Medium 3": ("mistral", ("mistral/mistral-medium-2505",)),
    "Mistral Medium 3.5": ("mistral", ("mistral/mistral-medium-2604", "mistral/mistral-medium-3-5",
                                       "mistral/mistral-medium-3.5")),
    "Mistral Large 4 Preview": ("mistral", ("mistral/mistral-large-4-0",)),
    "Mistral Large 4": ("mistral", ("mistral/mistral-large-4",)),
    # ---------------------------------------------------------------- Moonshot
    "Kimi K2 (Jul 2025)": ("moonshot", ("moonshot/kimi-k2-0711-preview",)),
    "Kimi K2 Thinking": ("moonshot", ("moonshot/kimi-k2-thinking",)),
    "Kimi K2.5": ("moonshot", ("moonshot/kimi-k2.5",)),
    "Kimi K2.6": ("moonshot", ("moonshot/kimi-k2.6",)),
    "Kimi K2.7 Code": ("moonshot", ("moonshot/kimi-k2.7-code",)),
    "Kimi K3": ("moonshot", ("moonshot/kimi-k3",)),
    "Kimi K3.1 Pro": ("moonshot", ("moonshot/kimi-k3.1-pro",)),
    # ---------------------------------------------------------------- Alibaba (Model Studio / DashScope)
    "Qwen3.7-Max": ("dashscope", ("dashscope/qwen3.7-max",)),
    "Qwen 3.8 Max": ("dashscope", ("dashscope/qwen3.8-max",)),
    # ---------------------------------------------------------------- Z.ai
    "GLM-4.7": ("zai", ("zai/glm-4.7",)),
    "GLM-5": ("zai", ("zai/glm-5",)),
    "GLM-5.1": ("zai", ("zai/glm-5.1",)),
    "GLM-5.2": ("zai", ("zai/glm-5.2",)),
    "GLM-5.3": ("zai", ("zai/glm-5.3",)),
    "GLM-5.3-Flash": ("zai", ("zai/glm-5.3-flash",)),
    # ---------------------------------------------------------------- MiniMax, Meta, ByteDance
    "MiniMax-M3": ("minimax", ("minimax/MiniMax-M3",)),
    "Muse Spark 1.1": ("meta", ("meta/muse-spark-1.1",)),
    "Muse Spark 1.2": ("meta", ("meta/muse-spark-1.2",)),
    "Muse Spark 1.3": ("meta", ("meta/muse-spark-1.3",)),
    "Muse Wonder": ("meta", ("meta/muse-wonder-1.0",)),
    "Doubao Seed 2.1 Pro": ("volcengine", ("volcengine/doubao-seed-2-1-pro-260628",)),
    "Doubao Seed 2.1 Turbo": ("volcengine", ("volcengine/doubao-seed-2-1-turbo-260628",)),
}


def is_first_party(key: str, provider: str) -> bool:
    if provider not in FIRST_PARTY or any(p in key for p in EXCLUDED_KEY_PARTS):
        return False
    return any(("/" not in key) if prefix == "" else (key.startswith(prefix) and key.count("/") == 1)
               for prefix in FIRST_PARTY[provider])


def problems(model_map: dict | None = None) -> list[str]:
    """Mapping errors; empty = valid. Every key must pass the first-party rule for its provider."""
    errors = []
    for model, (provider, keys) in (MODEL_MAP if model_map is None else model_map).items():
        if not keys:
            errors.append(f"{model}: no keys")
        errors += [f"{model}: {k} is not first-party for {provider}" for k in keys
                   if not is_first_party(k, provider)]
    long = key_models(model_map)
    multi = long.groupby("key")["model"].nunique()
    errors += [f"{k}: mapped to several models but not a rolling alias" for k in multi[multi > 1].index
               if k not in ROLLING_ALIASES]
    errors += [f"{k}: mapped under several providers" for k, n in long.groupby("key")["provider"].nunique().items()
               if n > 1]
    return errors


def key_models(model_map: dict | None = None) -> pd.DataFrame:
    """Long table: key, provider, model (one row per mapped pair)."""
    rows = [(k, p, m) for m, (p, keys) in (MODEL_MAP if model_map is None else model_map).items() for k in keys]
    return pd.DataFrame(rows, columns=["key", "provider", "model"])
