"""Hand-checked mapping: Arena (LMArena text) model name -> first-party LiteLLM price keys (docs/kallor/g2_arena_pris.md).

Arena names come in two forms: API names until 2026-10-19 (`gpt-4o-2024-05-13`), display names from 2026-10-20
("GPT-4o (2024-05-13)"). Both forms of a model are listed in the same entry. Every entry was checked by hand against
the Arena boards (BT era, from 2024-01-09) and LiteLLM's first-party keys (model_map.FIRST_PARTY, the developer's own
API only). Evidence per entry: the key is the same model, the same version (dated snapshot) and the same date.

Rules:
- Effort / thinking variants of one model (`o3-mini` and `o3-mini-high`, `claude-3-7-sonnet-20250219` and its
  `-thinking-32k` run) map to the same key: they are sold under one key at one price per token. A key's capability
  in a board is the highest rating among its names present there (the best variant per priced model).
- Undated keys are used only when they are the model-specific name of a single model that never re-pointed (same
  keys as model_map.MODEL_MAP where that table has the model). Aliases that drift (`gpt-4o`, `chatgpt-4o-latest`,
  `*-chat-latest`, `-latest`, `qwen-max`, `qwen-plus`, `mistral-medium`, `gemini/gemini-1.5-pro`) are never mapped.
- Rolling aliases (DeepSeek's `deepseek-chat`, `deepseek-reasoner`, `deepseek-coder`) are mapped per served
  version with the date the alias started serving it (ROLLING). At a month end the alias counts only with the
  version it served then; after the last documented version (`end`) it has no capability.
- Experimental or consumer-only Arena entries (Gemini `-exp-`, Bard, Gemini Advanced, anonymous test names) and
  previews whose released API identity is not documented are not mapped.
UNMAPPED lists every qualifying name (rating >= gpt-4-0314 in at least one BT board, data 2026-11-24) that is not
mapped, with a reason code (REASONS). A new Arena name is neither mapped nor listed until reviewed, so it never
counts (arena_price.coverage reports it).
"""

from __future__ import annotations

import pandas as pd

from ai_tracker.sources import model_map

# (provider, LiteLLM keys, Arena names (API and display), evidence)
MODELS: list[tuple[str, tuple[str, ...], tuple[str, ...], str]] = [
    # ---------------------------------------------------------------- OpenAI
    ("openai", ("gpt-4-0314",), ("gpt-4-0314", "GPT-4 (0314)"), "dated snapshot, same date"),
    ("openai", ("gpt-4-0613",), ("gpt-4-0613", "GPT-4 (0613)"), "dated snapshot, same date"),
    ("openai", ("gpt-4-1106-preview",), ("gpt-4-1106-preview", "GPT-4 Turbo Preview (1106)", "gpt-4-turbo"),
     "dated preview; Arena's `gpt-4-turbo` (boards 2024-01-09 - 01-25) was renamed `gpt-4-1106-preview` from "
     "2024-02-02 (no overlap), before OpenAI's gpt-4-turbo-2024-04-09 existed"),
    ("openai", ("gpt-4-0125-preview",), ("gpt-4-0125-preview", "GPT-4 Turbo Preview (0125)"), "dated preview"),
    ("openai", ("gpt-4-turbo-2024-04-09",), ("gpt-4-turbo-2024-04-09", "GPT-4 Turbo (2024-04-09)"), "dated snapshot"),
    ("openai", ("gpt-4o-2024-05-13",), ("gpt-4o-2024-05-13", "GPT-4o (2024-05-13)"), "dated snapshot"),
    ("openai", ("gpt-4o-2024-08-06",), ("gpt-4o-2024-08-06", "GPT-4o (2024-08-06)"), "dated snapshot"),
    ("openai", ("gpt-4o-mini-2024-07-18",), ("gpt-4o-mini-2024-07-18", "GPT-4o mini (2024-07-18)"), "dated snapshot"),
    ("openai", ("o1-preview-2024-09-12",), ("o1-preview",), "only o1-preview snapshot (2024-09-12)"),
    ("openai", ("o1-mini-2024-09-12",), ("o1-mini",), "only o1-mini snapshot (2024-09-12)"),
    ("openai", ("o1-2024-12-17",), ("o1-2024-12-17", "o1 (2024-12-17)"), "dated snapshot"),
    ("openai", ("o3-mini-2025-01-31",), ("o3-mini", "o3-mini-high", "o3-mini (High)"),
     "only o3-mini snapshot (2025-01-31); high = reasoning effort, same key and price"),
    ("openai", ("gpt-4.5-preview-2025-02-27",), ("gpt-4.5-preview-2025-02-27", "GPT-4.5 Preview (2025-02-27)"),
     "dated snapshot"),
    ("openai", ("gpt-4.1-2025-04-14",), ("gpt-4.1-2025-04-14", "GPT-4.1 (2025-04-14)"), "dated snapshot"),
    ("openai", ("gpt-4.1-mini-2025-04-14",), ("gpt-4.1-mini-2025-04-14", "GPT-4.1 mini (2025-04-14)"), "dated snapshot"),
    ("openai", ("gpt-4.1-nano-2025-04-14",), ("gpt-4.1-nano-2025-04-14", "GPT-4.1 nano (2025-04-14)"), "dated snapshot"),
    ("openai", ("o3-2025-04-16",), ("o3-2025-04-16", "o3 (2025-04-16)"), "dated snapshot"),
    ("openai", ("o4-mini-2025-04-16",), ("o4-mini-2025-04-16", "o4-mini (2025-04-16)"), "dated snapshot"),
    ("openai", ("gpt-5-2025-08-07",), ("gpt-5-high", "GPT-5 (High)"), "only GPT-5 snapshot; high = effort"),
    ("openai", ("gpt-5-mini-2025-08-07",), ("gpt-5-mini-high", "GPT-5 mini (High)"), "only snapshot; effort"),
    ("openai", ("gpt-5-nano-2025-08-07",), ("gpt-5-nano-high", "GPT-5 nano (High)"), "only snapshot; effort"),
    ("openai", ("gpt-5.1-2025-11-13",), ("gpt-5.1", "gpt-5.1-high", "GPT-5.1", "GPT-5.1 (High)"),
     "only GPT-5.1 API snapshot; default and high effort (ChatGPT's 5.1 Instant is not this name)"),
    ("openai", ("gpt-5.2-2025-12-11",), ("gpt-5.2", "gpt-5.2-high", "GPT-5.2", "GPT-5.2 (High)"),
     "only GPT-5.2 API snapshot; effort variants"),
    ("openai", ("gpt-5.4-2026-03-05", "gpt-5.4"), ("gpt-5.4", "gpt-5.4-high", "GPT-5.4", "GPT-5.4 (High)"),
     "only GPT-5.4 snapshot (model_map keys); effort variants"),
    ("openai", ("gpt-5.4-mini-2026-03-17", "gpt-5.4-mini"), ("gpt-5.4-mini-high", "GPT-5.4 mini (High)"),
     "only snapshot (model_map keys); effort"),
    ("openai", ("gpt-5.4-nano-2026-03-17", "gpt-5.4-nano"), ("gpt-5.4-nano-high", "GPT-5.4 nano (High)"),
     "only snapshot (model_map keys); effort"),
    ("openai", ("gpt-5.5-2026-04-23", "gpt-5.5"), ("gpt-5.5", "gpt-5.5-high", "GPT-5.5", "GPT-5.5 (High)"),
     "only GPT-5.5 snapshot (model_map keys); effort variants"),
    ("openai", ("gpt-5.6-luna",), ("gpt-5.6-luna-xhigh", "GPT-5.6 Luna (xHigh)"), "single key per model; effort"),
    ("openai", ("gpt-5.6-sol",), ("gpt-5.6-sol-xhigh", "GPT-5.6 Sol (xHigh)"), "single key per model; effort"),
    ("openai", ("gpt-5.6-terra",), ("gpt-5.6-terra-xhigh", "GPT-5.6 Terra (xHigh)"), "single key per model; effort"),
    ("openai", ("gpt-6-astra",), ("gpt-6-astra-max", "GPT-6 Astra (Max)"), "single key per model; effort"),
    ("openai", ("gpt-6-luna",), ("gpt-6-luna-max", "GPT-6 Luna (Max)"), "single key per model; effort"),
    ("openai", ("gpt-6-sol",), ("gpt-6-sol-max", "GPT-6 Sol (Max)"), "single key per model; effort"),
    ("openai", ("gpt-6.1-sol",), ("gpt-6.1-sol-max", "GPT-6.1 Sol (Max)"), "single key per model; effort"),
    ("openai", ("gpt-6.1-terra",), ("GPT-6.1 Terra (Max)",), "single key per model; effort"),
    ("openai", ("gpt-6.2-astra",), ("GPT-6.2 Astra (Max)",), "single key per model; effort"),
    ("openai", ("gpt-6.2-sol",), ("GPT-6.2 Sol (Max)",), "single key per model; effort"),
    # ---------------------------------------------------------------- Anthropic
    ("anthropic", ("claude-3-opus-20240229",), ("claude-3-opus-20240229", "Claude 3 Opus (20240229)"), "dated"),
    ("anthropic", ("claude-3-sonnet-20240229",), ("claude-3-sonnet-20240229", "Claude 3 Sonnet (20240229)"), "dated"),
    ("anthropic", ("claude-3-haiku-20240307",), ("claude-3-haiku-20240307", "Claude 3 Haiku (20240307)"), "dated"),
    ("anthropic", ("claude-3-5-sonnet-20240620",), ("claude-3-5-sonnet-20240620", "Claude 3.5 Sonnet (20240620)"),
     "dated"),
    ("anthropic", ("claude-3-5-sonnet-20241022",), ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet (20241022)"),
     "dated"),
    ("anthropic", ("claude-3-5-haiku-20241022",), ("claude-3-5-haiku-20241022", "Claude 3.5 Haiku (20241022)"),
     "dated"),
    ("anthropic", ("claude-3-7-sonnet-20250219",),
     ("claude-3-7-sonnet-20250219", "claude-3-7-sonnet-20250219-thinking-32k", "Claude 3.7 Sonnet (20250219)",
      "Claude 3.7 Sonnet (Thinking 32K, 20250219)"), "dated; thinking budget = same key and price"),
    ("anthropic", ("claude-opus-4-20250514", "claude-4-opus-20250514"),
     ("claude-opus-4-20250514", "claude-opus-4-20250514-thinking-16k", "Claude Opus 4 (20250514)",
      "Claude Opus 4 (Thinking 16K, 20250514)"), "dated (both key spellings, model_map); thinking"),
    ("anthropic", ("claude-sonnet-4-20250514", "claude-4-sonnet-20250514"),
     ("claude-sonnet-4-20250514", "claude-sonnet-4-20250514-thinking-32k", "Claude Sonnet 4 (20250514)",
      "Claude Sonnet 4 (Thinking 32K, 20250514)"), "dated (both key spellings, model_map); thinking"),
    ("anthropic", ("claude-opus-4-1-20250805", "claude-opus-4-1"),
     ("claude-opus-4-1-20250805", "claude-opus-4-1-20250805-thinking-16k", "Claude Opus 4.1 (20250805)",
      "Claude Opus 4.1 (Thinking 16K, 20250805)"), "dated; thinking"),
    ("anthropic", ("claude-sonnet-4-5-20250929", "claude-sonnet-4-5"),
     ("claude-sonnet-4-5-20250929", "claude-sonnet-4-5-20250929-thinking-32k", "claude-sonnet-4-5-20250929-high-32k",
      "Claude Sonnet 4.5 (20250929)", "Claude Sonnet 4.5 (High, 32K, 20250929)"), "dated; thinking"),
    ("anthropic", ("claude-haiku-4-5-20251001", "claude-haiku-4-5"),
     ("claude-haiku-4-5-20251001", "Claude Haiku 4.5 (20251001)"), "dated"),
    ("anthropic", ("claude-opus-4-5-20251101", "claude-opus-4-5"),
     ("claude-opus-4-5-20251101", "claude-opus-4-5-20251101-thinking-32k", "claude-opus-4-5-20251101-high-32k",
      "Claude Opus 4.5 (20251101)", "Claude Opus 4.5 (High, 32K, 20251101)"), "dated; thinking"),
    ("anthropic", ("claude-opus-4-6-20260205", "claude-opus-4-6"),
     ("claude-opus-4-6", "claude-opus-4-6-thinking", "claude-opus-4-6-high", "Claude Opus 4.6",
      "Claude Opus 4.6 (High)"), "single snapshot (model_map keys); thinking/effort"),
    ("anthropic", ("claude-sonnet-4-6",), ("claude-sonnet-4-6", "Claude Sonnet 4.6"), "single key"),
    ("anthropic", ("claude-opus-4-7-20260416", "claude-opus-4-7"),
     ("claude-opus-4-7", "claude-opus-4-7-thinking", "claude-opus-4-7-high", "Claude Opus 4.7",
      "Claude Opus 4.7 (High)"), "single snapshot (model_map keys); thinking/effort"),
    ("anthropic", ("claude-opus-4-8",),
     ("claude-opus-4-8", "claude-opus-4-8-thinking", "claude-opus-4-8-high", "Claude Opus 4.8",
      "Claude Opus 4.8 (High)"), "single key; thinking/effort"),
    ("anthropic", ("claude-fable-5",), ("claude-fable-5", "claude-fable-5-high", "Claude Fable 5 (High)"),
     "single key; effort"),
    ("anthropic", ("claude-fable-5-1",), ("claude-fable-5.1-max", "Claude Fable 5.1 (Max)"), "single key; effort"),
    ("anthropic", ("claude-fable-5-2",), ("Claude Fable 5.2 (Max)",), "single key; effort"),
    ("anthropic", ("claude-sonnet-5",), ("claude-sonnet-5-high", "claude-sonnet-5-thinking", "Claude Sonnet 5 (High)"),
     "single key; effort"),
    ("anthropic", ("claude-opus-5",), ("claude-opus-5-high", "claude-opus-5-max", "Claude Opus 5 (High)",
                                       "Claude Opus 5 (Max)"), "single key; effort"),
    ("anthropic", ("claude-opus-5-5",), ("claude-opus-5.5-high", "Claude Opus 5.5 (High)"), "single key; effort"),
    ("anthropic", ("claude-sonnet-5-5",), ("claude-sonnet-5.5-xhigh", "Claude Sonnet 5.5 (xHigh)"),
     "single key; effort"),
    ("anthropic", ("claude-haiku-5-5",), ("Claude Haiku 5.5 (High)",), "single key; effort"),
    # ---------------------------------------------------------------- Google (Gemini API keys, from 2024-06)
    ("gemini", ("gemini/gemini-1.5-pro-001",), ("gemini-1.5-pro-api-0514", "gemini-1.5-pro-001", "Gemini 1.5 Pro (001)"),
     "Arena renamed gemini-1.5-pro-api-0514 (last 2024-10-15) to gemini-1.5-pro-001 (first 2024-10-23), no overlap; "
     "001 = the May 2024 GA version"),
    ("gemini", ("gemini/gemini-1.5-pro-002",), ("gemini-1.5-pro-002", "Gemini 1.5 Pro (002)"), "dated version"),
    ("gemini", ("gemini/gemini-1.5-flash-001",),
     ("gemini-1.5-flash-api-0514", "gemini-1.5-flash-001", "Gemini 1.5 Flash (001)"),
     "renamed like 1.5 Pro (last api-0514 2024-10-15, first -001 2024-10-23)"),
    ("gemini", ("gemini/gemini-1.5-flash-002",), ("gemini-1.5-flash-002", "Gemini 1.5 Flash (002)"), "dated version"),
    ("gemini", ("gemini/gemini-2.0-flash-001", "gemini/gemini-2.0-flash"),
     ("gemini-2.0-flash-001", "gemini-2.0-flash", "Gemini 2.0 Flash (001)"),
     "GA version (model_map keys); Arena's `gemini-2.0-flash` is one board (2025-02-06) beside -001"),
    ("gemini", ("gemini/gemini-2.0-flash-lite-preview-02-05",),
     ("gemini-2.0-flash-lite-preview-02-05", "gemini-2.0-flash-lite-preview", "Gemini 2.0 Flash-Lite Preview (02-05)"),
     "dated preview; `gemini-2.0-flash-lite-preview` = boards 2025-02-05/06, renamed with date from 2025-02-09"),
    ("gemini", ("gemini/gemini-2.5-pro-preview-03-25",), ("gemini-2.5-pro-exp-03-25",),
     "Google: the paid Preview 03-25 is the same model as Experimental 03-25 (model_map: Gemini 2.5 Pro (Mar 2025))"),
    ("gemini", ("gemini/gemini-2.5-pro-preview-05-06",), ("gemini-2.5-pro-preview-05-06",), "dated preview"),
    ("gemini", ("gemini/gemini-2.5-pro-preview-06-05",), ("gemini-2.5-pro-preview-06-05",), "dated preview"),
    ("gemini", ("gemini/gemini-2.5-pro",), ("gemini-2.5-pro", "Gemini 2.5 Pro"), "stable GA name (fixed model)"),
    ("gemini", ("gemini/gemini-2.5-flash-preview-04-17",), ("gemini-2.5-flash-preview-04-17",), "dated preview"),
    ("gemini", ("gemini/gemini-2.5-flash-preview-05-20",), ("gemini-2.5-flash-preview-05-20",), "dated preview"),
    ("gemini", ("gemini/gemini-2.5-flash",), ("gemini-2.5-flash", "Gemini 2.5 Flash"), "stable GA name (fixed model)"),
    ("gemini", ("gemini/gemini-2.5-flash-preview-09-2025",),
     ("gemini-2.5-flash-preview-09-2025", "Gemini 2.5 Flash Preview (09-2025)"), "dated preview"),
    ("gemini", ("gemini/gemini-2.5-flash-lite-preview-06-17",),
     ("gemini-2.5-flash-lite-preview-06-17-thinking", "Gemini 2.5 Flash-Lite Preview (Thinking, 06-17)"),
     "dated preview; thinking on = same key"),
    ("gemini", ("gemini/gemini-2.5-flash-lite-preview-09-2025",),
     ("gemini-2.5-flash-lite-preview-09-2025-no-thinking", "Gemini 2.5 Flash-Lite Preview (Non-Thinking, 09-2025)"),
     "dated preview; thinking off = same key"),
    ("gemini", ("gemini/gemini-3-pro-preview",), ("gemini-3-pro", "Gemini 3 Pro"),
     "Gemini 3 Pro was sold only as gemini-3-pro-preview in the API (model_map)"),
    ("gemini", ("gemini/gemini-3-flash-preview",),
     ("gemini-3-flash", "gemini-3-flash (thinking-minimal)", "Gemini 3 Flash", "Gemini 3 Flash (Minimal)"),
     "sold as gemini-3-flash-preview (model_map); thinking level = same key"),
    ("gemini", ("gemini/gemini-3.1-pro-preview",), ("gemini-3.1-pro-preview", "Gemini 3.1 Pro Preview"), "same id"),
    ("gemini", ("gemini/gemini-3.1-flash-lite-preview", "gemini/gemini-3.1-flash-lite"),
     ("gemini-3.1-flash-lite-preview", "Gemini 3.1 Flash-Lite Preview"), "same id (model_map keys)"),
    ("gemini", ("gemini/gemini-3.5-flash",),
     ("gemini-3.5-flash", "gemini-3.5-flash-high", "gemini-3.5-flash-medium", "Gemini 3.5 Flash (High)",
      "Gemini 3.5 Flash (Medium)"), "single key; thinking levels"),
    ("gemini", ("gemini/gemini-3.5-flash-lite",), ("gemini-3.5-flash-lite", "Gemini 3.5 Flash-Lite"), "same id"),
    ("gemini", ("gemini/gemini-3.6-flash",), ("gemini-3.6-flash", "gemini-3.6-flash-high", "Gemini 3.6 Flash (High)"),
     "single key; thinking levels"),
    ("gemini", ("gemini/gemini-3.7-flash",), ("gemini-3.7-flash-high", "Gemini 3.7 Flash (High)"), "single key"),
    ("gemini", ("gemini/gemini-3.8-flash",), ("gemini-3.8-flash-high", "Gemini 3.8 Flash (High)"), "single key"),
    ("gemini", ("gemini/gemini-4-argon",), ("gemini-4-argon-high", "Gemini 4 Argon (High)"), "single key"),
    ("gemini", ("gemini/gemini-4-carbon",), ("Gemini 4 Carbon (High)",), "single key"),
    ("gemini", ("gemini/gemini-4-hydrogen",), ("Gemini 4 Hydrogen (High)",), "single key"),
    ("gemini", ("gemini/gemini-4-neon",), ("Gemini 4 Neon (High)",), "single key"),
    # ---------------------------------------------------------------- xAI (keys from 2025-01)
    ("xai", ("xai/grok-3-mini-beta", "xai/grok-3-mini"),
     ("grok-3-mini-beta", "grok-3-mini-high", "Grok 3 Mini Beta", "Grok 3 Mini (High)"),
     "one model (beta renamed, model_map keys); high = effort"),
    ("xai", ("xai/grok-4-0709", "xai/grok-4"), ("grok-4-0709", "Grok 4 (0709)"), "dated (model_map keys)"),
    ("xai", ("xai/grok-4-fast-reasoning",), ("grok-4-fast-reasoning", "Grok 4 Fast (Reasoning)"), "same id"),
    ("xai", ("xai/grok-4-fast-non-reasoning",), ("grok-4-fast-chat", "Grok 4 Fast (Non-Reasoning)"),
     "non-reasoning mode of Grok 4 Fast, sold under its own key"),
    ("xai", ("xai/grok-4-1-fast-reasoning",), ("grok-4-1-fast-reasoning", "Grok 4.1 Fast (Reasoning)"), "same id"),
    ("xai", ("xai/grok-4.20-beta-0309-reasoning", "xai/grok-4.20-0309-reasoning"),
     ("grok-4.20-beta-0309-reasoning", "Grok 4.20 Beta (Reasoning, 0309)"), "same date tag 0309 (model_map keys)"),
    ("xai", ("xai/grok-4.20-multi-agent-beta-0309",),
     ("grok-4.20-multi-agent-beta-0309", "Grok 4.20 Multi-Agent Beta (0309)"), "same id"),
    ("xai", ("xai/grok-4.3",), ("grok-4.3", "Grok 4.3"), "same id"),
    ("xai", ("xai/grok-4.5",), ("grok-4.5", "Grok 4.5"), "same id"),
    ("xai", ("xai/grok-4.6",), ("grok-4.6-high", "Grok 4.6 (High)"), "single key; effort"),
    ("xai", ("xai/grok-4.7",), ("grok-4.7-xhigh", "Grok 4.7 (xHigh)"), "single key; effort"),
    # ---------------------------------------------------------------- DeepSeek, fixed ids (aliases: ROLLING)
    ("deepseek", ("deepseek-v4-pro", "deepseek/deepseek-v4-pro"),
     ("deepseek-v4-pro", "deepseek-v4-pro-thinking", "DeepSeek-V4-Pro"),
     "same id; thinking = same key. Later Arena entries (-high-preview, -high-20260813) are not mapped: possibly "
     "in-place updates, not documented"),
    ("deepseek", ("deepseek-v4-flash", "deepseek/deepseek-v4-flash"),
     ("deepseek-v4-flash", "deepseek-v4-flash-thinking", "DeepSeek-V4-Flash"), "same id; thinking = same key"),
    # ---------------------------------------------------------------- Mistral
    ("mistral", ("mistral/mistral-medium-2312",), ("mistral-medium", "Mistral Medium"),
     "Arena's mistral-medium = the Dec 2023 model (dated key 2312; the undated alias later re-pointed)"),
    ("mistral", ("mistral/mistral-large-2402",), ("mistral-large-2402", "Mistral Large (2402)"), "dated"),
    ("mistral", ("mistral/mistral-large-2407",), ("mistral-large-2407", "Mistral Large 2 (2407)"), "dated"),
    ("mistral", ("mistral/mistral-large-2411",), ("mistral-large-2411", "Mistral Large (2411)"), "dated"),
    ("mistral", ("mistral/mistral-large-2512", "mistral/mistral-large-3"), ("mistral-large-3", "Mistral Large 3"),
     "Mistral Large 3 = mistral-large-2512 (Dec 2025)"),
    ("mistral", ("mistral/mistral-large-4",), ("mistral-large-4", "Mistral Large 4"), "same id (model_map)"),
    ("mistral", ("mistral/mistral-medium-2505",), ("mistral-medium-2505", "Mistral Medium 3 (2505)"), "dated"),
    ("mistral", ("mistral/mistral-medium-2508", "mistral/mistral-medium-3-1-2508"),
     ("mistral-medium-2508", "Mistral Medium 3.1 (2508)"), "dated (both spellings)"),
    ("mistral", ("mistral/mistral-medium-2604", "mistral/mistral-medium-3-5", "mistral/mistral-medium-3.5"),
     ("mistral-medium-3.5", "Mistral Medium 3.5"), "model_map keys"),
    ("mistral", ("mistral/mistral-small-3-2-2506",), ("mistral-small-2506", "Mistral Small 3.2 (2506)"), "dated"),
    ("mistral", ("mistral/magistral-medium-2506",), ("magistral-medium-2506", "Magistral Medium (2506)"), "dated"),
    # ---------------------------------------------------------------- Moonshot (keys from 2025-07)
    ("moonshot", ("moonshot/kimi-k2-0711-preview",), ("kimi-k2-0711-preview", "Kimi K2 Preview (0711)"), "dated"),
    ("moonshot", ("moonshot/kimi-k2-0905-preview",), ("kimi-k2-0905-preview", "Kimi K2 Preview (0905)"), "dated"),
    ("moonshot", ("moonshot/kimi-k2-thinking-turbo",), ("kimi-k2-thinking-turbo", "Kimi K2 Thinking Turbo"), "same id"),
    ("moonshot", ("moonshot/kimi-k2.5",),
     ("kimi-k2.5-instant", "kimi-k2.5-thinking", "Kimi K2.5 (Instant)", "Kimi K2.5 (Thinking)"),
     "one key, thinking on/off"),
    ("moonshot", ("moonshot/kimi-k2.6",), ("kimi-k2.6", "Kimi K2.6"), "same id"),
    ("moonshot", ("moonshot/kimi-k3",), ("kimi-k3", "kimi-k3-max", "Kimi K3 (Max)"), "single key; effort"),
    ("moonshot", ("moonshot/kimi-k3.1-pro",), ("Kimi K3.1 Pro (Max)",), "single key; effort"),
    # ---------------------------------------------------------------- Z.ai (keys from 2025-12)
    ("zai", ("zai/glm-4.5",), ("glm-4.5", "GLM-4.5"), "same id"),
    ("zai", ("zai/glm-4.5-air",), ("glm-4.5-air", "GLM-4.5-Air"), "same id"),
    ("zai", ("zai/glm-4.5v",), ("glm-4.5v", "GLM-4.5V"), "same id"),
    ("zai", ("zai/glm-4.6",), ("glm-4.6", "GLM-4.6"), "same id"),
    ("zai", ("zai/glm-4.7",), ("glm-4.7", "GLM-4.7"), "same id"),
    ("zai", ("zai/glm-5",), ("glm-5", "GLM-5"), "same id"),
    ("zai", ("zai/glm-5.1",), ("glm-5.1", "GLM-5.1"), "same id"),
    ("zai", ("zai/glm-5.2",), ("glm-5.2 (max)", "glm-5.2-max", "GLM-5.2 (Max)"), "single key; effort"),
    ("zai", ("zai/glm-5.3",), ("glm-5.3-max", "GLM-5.3 (Max)"), "single key; effort"),
    ("zai", ("zai/glm-5.3-flash",), ("glm-5.3-flash", "GLM-5.3-Flash"), "same id"),
    ("zai", ("zai/glm-5v-turbo",), ("glm-5v-turbo", "GLM-5V-Turbo"), "same id"),
    # ---------------------------------------------------------------- MiniMax, Meta, Alibaba
    ("minimax", ("minimax/MiniMax-M2",), ("minimax-m2", "MiniMax-M2"), "same id"),
    ("minimax", ("minimax/MiniMax-M2.5",), ("minimax-m2.5", "MiniMax-M2.5"), "same id"),
    ("minimax", ("minimax/MiniMax-M3",), ("minimax-m3", "MiniMax-M3"), "same id"),
    ("meta", ("meta/muse-spark-1.1",), ("muse-spark-1.1", "Muse Spark 1.1"), "same id"),
    ("meta", ("meta/muse-spark-1.2",), ("muse-spark-1.2 (xHigh)", "Muse Spark 1.2 (xHigh)"), "single key; effort"),
    ("meta", ("meta/muse-spark-1.3",), ("muse-spark-1.3-max", "Muse Spark 1.3 (Max)"), "single key; effort"),
    ("meta", ("meta/muse-wonder-1.0",), ("muse-wonder-max", "Muse Wonder (Max)"), "single key (model_map)"),
    ("dashscope", ("dashscope/qwen-plus-2025-01-25",), ("qwen-plus-0125", "Qwen-Plus (0125)"), "dated snapshot"),
    ("dashscope", ("dashscope/qwen3.8-max",), ("qwen3.8-max", "Qwen3.8-Max"), "same id (model_map)"),
    ("dashscope", ("dashscope/qwen3-next-80b-a3b-instruct",),
     ("qwen3-next-80b-a3b-instruct", "Qwen3-Next-80B-A3B-Instruct"), "same id, Alibaba's own API"),
    ("dashscope", ("dashscope/qwen3-next-80b-a3b-thinking",),
     ("qwen3-next-80b-a3b-thinking", "Qwen3-Next-80B-A3B-Thinking"), "same id, Alibaba's own API"),
    ("dashscope", ("dashscope/qwen3-vl-235b-a22b-instruct",),
     ("qwen3-vl-235b-a22b-instruct", "Qwen3-VL-235B-A22B-Instruct"), "same id, Alibaba's own API"),
    ("dashscope", ("dashscope/qwen3-vl-235b-a22b-thinking",),
     ("qwen3-vl-235b-a22b-thinking", "Qwen3-VL-235B-A22B-Thinking"), "same id, Alibaba's own API"),
]

_DS_CHAT = ("deepseek-chat", "deepseek/deepseek-chat")
_DS_REASONER = ("deepseek-reasoner", "deepseek/deepseek-reasoner")
_DS_CODER = ("deepseek-coder", "deepseek/deepseek-coder")
# After V4 (first Arena board 2026-04-23) what the aliases serve is not documented in our sources (LiteLLM: deprecated
# 2026-07-24, successor deepseek-v4-flash), so they stop counting the day before.
_DS_END = "2026-04-22"
# Rolling aliases: (keys, Arena names, served from, served to (inclusive) or None, evidence). Dates from DeepSeek's
# API release notes (api-docs.deepseek.com/news; the version date is in the model name).
ROLLING: list[tuple[tuple[str, ...], tuple[str, ...], str, str | None, str]] = [
    (_DS_CHAT, ("deepseek-v2-api-0628",), "2024-06-28", None, "V2-0628 API update (date in the name)"),
    (_DS_CHAT, ("deepseek-v2.5", "DeepSeek-V2.5"), "2024-09-05", None, "V2.5 merged chat and coder, 2024-09-05"),
    (_DS_CHAT, ("deepseek-v2.5-1210", "DeepSeek-V2.5 (1210)"), "2024-12-10", None, "V2.5-1210, 2024-12-10"),
    (_DS_CHAT, ("deepseek-v3", "DeepSeek-V3"), "2024-12-26", None, "V3, 2024-12-26"),
    (_DS_CHAT, ("deepseek-v3-0324", "DeepSeek-V3 (0324)"), "2025-03-25", None, "V3-0324 on the API 2025-03-25"),
    (_DS_CHAT, ("deepseek-v3.1", "DeepSeek-V3.1"), "2025-08-21", None, "V3.1 non-thinking = deepseek-chat"),
    (_DS_CHAT, ("deepseek-v3.1-terminus", "DeepSeek-V3.1-Terminus"), "2025-09-22", None, "V3.1-Terminus"),
    (_DS_CHAT, ("deepseek-v3.2-exp", "DeepSeek-V3.2-Exp"), "2025-09-29", None, "V3.2-Exp"),
    (_DS_CHAT, ("deepseek-v3.2", "DeepSeek-V3.2"), "2025-12-01", _DS_END, "V3.2, 2025-12-01"),
    (_DS_REASONER, ("deepseek-r1", "DeepSeek-R1"), "2025-01-20", None, "R1, 2025-01-20"),
    (_DS_REASONER, ("deepseek-r1-0528", "DeepSeek-R1 (0528)"), "2025-05-28", None, "R1-0528"),
    (_DS_REASONER, ("deepseek-v3.1-thinking", "DeepSeek-V3.1 (Thinking)"), "2025-08-21", None,
     "V3.1 thinking = deepseek-reasoner"),
    (_DS_REASONER, ("deepseek-v3.1-terminus-thinking", "DeepSeek-V3.1-Terminus (Thinking)"), "2025-09-22", None,
     "V3.1-Terminus thinking"),
    (_DS_REASONER, ("deepseek-v3.2-exp-thinking", "DeepSeek-V3.2-Exp (Thinking)"), "2025-09-29", None,
     "V3.2-Exp thinking"),
    (_DS_REASONER, ("deepseek-v3.2-thinking", "DeepSeek-V3.2 (Thinking)"), "2025-12-01", _DS_END, "V3.2 thinking"),
    (_DS_CODER, ("deepseek-coder-v2-0724", "DeepSeek-Coder-V2"), "2024-07-24", None, "Coder-V2-0724 (date in name)"),
    (_DS_CODER, ("deepseek-v2.5", "DeepSeek-V2.5"), "2024-09-05", "2024-12-09",
     "V2.5 also served under deepseek-coder; later coder targets not documented"),
]

REASONS = {
    "alias_drifts": "ChatGPT / chat-latest alias that re-points without documented dates",
    "developer_not_first_party": "the developer's own API is not in the first-party rule (model_map.FIRST_PARTY)",
    "open_weights": "open weights without a first-party price in LiteLLM (only resellers / clouds)",
    "no_key": "developer in the rule, but LiteLLM has no first-party key for this version",
    "experimental": "experimental, consumer or anonymous test entry, not a priced API model",
    "identity_uncertain": "preview or update whose released API identity is not documented",
}

UNMAPPED: dict[str, str] = {  # hand-checked, qualifying names (>= gpt-4-0314 in a BT board), data 2026-11-24
    # alias_drifts (16)
    "ChatGPT-4o Latest (20250326)": "alias_drifts", "GPT-5 Chat": "alias_drifts",
    "GPT-5.2 Chat (20260210)": "alias_drifts", "GPT-5.3 Chat": "alias_drifts", "GPT-5.5 Instant": "alias_drifts",
    "chatgpt-4o-latest": "alias_drifts", "chatgpt-4o-latest-2024-08-08": "alias_drifts",
    "chatgpt-4o-latest-20240808": "alias_drifts", "chatgpt-4o-latest-20240903": "alias_drifts",
    "chatgpt-4o-latest-20241120": "alias_drifts", "chatgpt-4o-latest-20250129": "alias_drifts",
    "chatgpt-4o-latest-20250326": "alias_drifts", "gpt-5-chat": "alias_drifts",
    "gpt-5.2-chat-latest-20260210": "alias_drifts", "gpt-5.3-chat-latest": "alias_drifts",
    "gpt-5.5-instant": "alias_drifts",
    # experimental (33)
    "Gemini Advanced (0514)": "experimental", "amazon-nova-experimental-chat (10-09)": "experimental",
    "amazon-nova-experimental-chat (10-20)": "experimental", "amazon-nova-experimental-chat (11-10)": "experimental",
    "amazon-nova-experimental-chat (12-10)": "experimental",
    "amazon-nova-experimental-chat (26-01-10)": "experimental",
    "amazon-nova-experimental-chat (26-02-10)": "experimental", "amazon-nova-experimental-chat-05-14": "experimental",
    "amazon-nova-experimental-chat-10-09": "experimental", "amazon-nova-experimental-chat-10-20": "experimental",
    "amazon-nova-experimental-chat-11-10": "experimental", "amazon-nova-experimental-chat-12-10": "experimental",
    "amazon-nova-experimental-chat-26-01-10": "experimental",
    "amazon-nova-experimental-chat-26-02-10": "experimental", "bard-jan-24-gemini-pro": "experimental",
    "early-grok-3": "experimental", "gemini-1.5-flash-8b-exp-0827": "experimental",
    "gemini-1.5-flash-exp-0827": "experimental", "gemini-1.5-pro-exp-0801": "experimental",
    "gemini-1.5-pro-exp-0827": "experimental", "gemini-2.0-flash-exp": "experimental",
    "gemini-2.0-flash-thinking-exp-01-21": "experimental", "gemini-2.0-flash-thinking-exp-1219": "experimental",
    "gemini-2.0-pro-exp-02-05": "experimental", "gemini-advanced-0514": "experimental",
    "gemini-exp-1114": "experimental", "gemini-exp-1121": "experimental", "gemini-exp-1206": "experimental",
    "gpt-5-old": "experimental", "late-june-chatbot": "experimental",
    "llama-4-maverick-03-26-experimental": "experimental", "longcat-flash-chat-2602-exp": "experimental",
    "step-2-16k-exp-202412": "experimental",
    # identity_uncertain (17)
    "DeepSeek-V4-Flash Preview (High)": "identity_uncertain",
    "DeepSeek-V4-Pro (High, 20260813)": "identity_uncertain", "DeepSeek-V4-Pro Preview (High)": "identity_uncertain",
    "DeepSeek-V4.1-Flash-20260910 (Max)": "identity_uncertain", "Grok 3 Preview (02-24)": "identity_uncertain",
    "Grok 4.20 Beta 1": "identity_uncertain", "MiniMax-M2.1 Preview": "identity_uncertain",
    "Qwen3.7-Max-Preview": "identity_uncertain", "deepseek-v4-flash-high-preview": "identity_uncertain",
    "deepseek-v4-pro-high-20260813": "identity_uncertain", "deepseek-v4-pro-high-preview": "identity_uncertain",
    "deepseek-v4.1-flash-max": "identity_uncertain", "gemini-1.5-pro-api-0409-preview": "identity_uncertain",
    "grok-3-preview-02-24": "identity_uncertain", "grok-4.20-beta1": "identity_uncertain",
    "minimax-m2.1-preview": "identity_uncertain", "qwen3.7-max-preview": "identity_uncertain",
    # no_key (59)
    "Dola Seed 2.0 Pro": "no_key", "GLM-4 (0520)": "no_key", "GLM-4-Plus": "no_key", "GLM-4-Plus (0111)": "no_key",
    "GLM-4.6V": "no_key", "GLM-4.7-Flash": "no_key", "Gemini 1.5 Flash-8B (001)": "no_key",
    "Grok 2 (2024-08-13)": "no_key", "Grok 2 mini (2024-08-13)": "no_key", "Grok 4.1": "no_key",
    "Grok 4.1 (Thinking)": "no_key", "MiniMax-M1": "no_key", "MiniMax-M2.7": "no_key",
    "Mistral Small 24B Instruct (2501)": "no_key", "Mistral Small 3.1 24B Instruct (2503)": "no_key",
    "Muse Glimmer": "no_key", "Muse Spark": "no_key", "Qwen-Max (0919)": "no_key", "Qwen2.5-Max": "no_key",
    "Qwen2.5-Plus (1127)": "no_key", "Qwen3-Max (2025-09-23)": "no_key", "Qwen3-Max-Preview": "no_key",
    "Qwen3.5-Flash": "no_key", "Qwen3.5-Max-Preview": "no_key", "Qwen3.6-Max-Preview": "no_key",
    "Qwen3.6-Plus": "no_key", "Qwen3.7-Plus": "no_key", "dola-seed-2.0-preview": "no_key",
    "dola-seed-2.0-pro": "no_key", "gemini-1.5-flash-8b-001": "no_key", "glm-4-0520": "no_key",
    "glm-4-plus": "no_key", "glm-4-plus-0111": "no_key", "glm-4.6v": "no_key", "glm-4.7-flash": "no_key",
    "grok-2-2024-08-13": "no_key", "grok-2-mini-2024-08-13": "no_key", "grok-4.1": "no_key",
    "grok-4.1-thinking": "no_key", "minimax-m1": "no_key", "minimax-m2.7": "no_key",
    "mistral-small-24b-instruct-2501": "no_key", "mistral-small-3.1-24b-instruct-2503": "no_key",
    "muse-glimmer": "no_key", "muse-spark": "no_key", "qwen-max-0919": "no_key", "qwen-max-2025-01-25": "no_key",
    "qwen-max-2025-08-15": "no_key", "qwen-plus-0828": "no_key", "qwen-vl-max-2025-08-13": "no_key",
    "qwen2.5-max": "no_key", "qwen2.5-plus-1127": "no_key", "qwen3-max-2025-09-23": "no_key",
    "qwen3-max-preview": "no_key", "qwen3.5-flash": "no_key", "qwen3.5-max-preview": "no_key",
    "qwen3.6-max-preview": "no_key", "qwen3.6-plus": "no_key", "qwen3.7-plus": "no_key",
    # developer_not_first_party (110)
    "Amazon Nova 2 Lite": "developer_not_first_party", "Amazon Nova Lite 1.0": "developer_not_first_party",
    "Amazon Nova Micro 1.0": "developer_not_first_party", "Amazon Nova Pro 1.0": "developer_not_first_party",
    "Command A (03-2025)": "developer_not_first_party", "Command R+ (08-2024)": "developer_not_first_party",
    "ERNIE 5.0 (0110)": "developer_not_first_party", "ERNIE 5.1": "developer_not_first_party",
    "ERNIE-5.0-Preview (1022)": "developer_not_first_party", "ERNIE-5.0-Preview (1203)": "developer_not_first_party",
    "Granite 4.1 8B": "developer_not_first_party", "Granite 4.2 30B": "developer_not_first_party",
    "Granite 4.2 3B": "developer_not_first_party", "Granite 4.2 8B": "developer_not_first_party",
    "Granite-4.0-H-Small": "developer_not_first_party", "Hunyuan Large (2025-02-10)": "developer_not_first_party",
    "Hunyuan Large Vision": "developer_not_first_party", "Hunyuan Standard (2025-02-10)": "developer_not_first_party",
    "Hunyuan T1 (20250711)": "developer_not_first_party", "Hunyuan Turbo (0110)": "developer_not_first_party",
    "Hunyuan TurboS (20250226)": "developer_not_first_party",
    "Hunyuan TurboS (20250416)": "developer_not_first_party",
    "Hunyuan Vision 1.5 Thinking": "developer_not_first_party", "Hy3": "developer_not_first_party",
    "Hy3 preview": "developer_not_first_party", "Jamba 1.5 Large": "developer_not_first_party",
    "Ling-flash-2.0": "developer_not_first_party", "LongCat-Flash-Chat": "developer_not_first_party",
    "LongCat-Flash-Chat Exp (2602)": "developer_not_first_party", "Mercury": "developer_not_first_party",
    "Mercury 2": "developer_not_first_party", "MiMo-V2-Flash (Non-Thinking)": "developer_not_first_party",
    "MiMo-V2-Flash (Thinking)": "developer_not_first_party", "MiMo-V2-Omni": "developer_not_first_party",
    "MiMo-V2-Pro": "developer_not_first_party", "MiMo-V2.5": "developer_not_first_party",
    "MiMo-V2.5-Pro": "developer_not_first_party", "MiMo-V2.6-Flash": "developer_not_first_party",
    "MiMo-V2.6-Pro": "developer_not_first_party", "Reka Core (20240904)": "developer_not_first_party",
    "Reka Flash (20240904)": "developer_not_first_party", "Ring-flash-2.0": "developer_not_first_party",
    "Solar Pro 4": "developer_not_first_party", "Step 5 Preview": "developer_not_first_party",
    "Step-1o Turbo (202506)": "developer_not_first_party", "Step-2 16K Exp (202412)": "developer_not_first_party",
    "Step-3": "developer_not_first_party", "Step-3.5-Flash": "developer_not_first_party",
    "Trinity Large Preview": "developer_not_first_party", "Trinity Large Thinking": "developer_not_first_party",
    "Yi Lightning": "developer_not_first_party", "amazon-nova-lite-v1.0": "developer_not_first_party",
    "amazon-nova-micro-v1.0": "developer_not_first_party", "amazon-nova-pro-v1.0": "developer_not_first_party",
    "command-a-03-2025": "developer_not_first_party", "command-r-plus": "developer_not_first_party",
    "command-r-plus-08-2024": "developer_not_first_party", "ernie-5.0-0110": "developer_not_first_party",
    "ernie-5.0-preview-1022": "developer_not_first_party", "ernie-5.0-preview-1203": "developer_not_first_party",
    "ernie-5.1": "developer_not_first_party", "ernie-5.1-preview": "developer_not_first_party",
    "granite-4.1-8b": "developer_not_first_party", "granite-4.2-30b": "developer_not_first_party",
    "granite-4.2-3b": "developer_not_first_party", "granite-4.2-8b": "developer_not_first_party",
    "hunyuan-hy3-preview": "developer_not_first_party", "hunyuan-large-2025-02-10": "developer_not_first_party",
    "hunyuan-large-vision": "developer_not_first_party", "hunyuan-standard-2025-02-10": "developer_not_first_party",
    "hunyuan-standard-256k": "developer_not_first_party", "hunyuan-t1-20250711": "developer_not_first_party",
    "hunyuan-turbo-0110": "developer_not_first_party", "hunyuan-turbos-20250226": "developer_not_first_party",
    "hunyuan-turbos-20250416": "developer_not_first_party",
    "hunyuan-vision-1.5-thinking": "developer_not_first_party", "hy3": "developer_not_first_party",
    "ibm-granite-h-small": "developer_not_first_party", "jamba-1.5-large": "developer_not_first_party",
    "ling-flash-2.0": "developer_not_first_party", "longcat-flash-chat": "developer_not_first_party",
    "mai-1-preview": "developer_not_first_party", "mercury": "developer_not_first_party",
    "mercury-2": "developer_not_first_party", "mimo-v2-flash (non-thinking)": "developer_not_first_party",
    "mimo-v2-flash (thinking)": "developer_not_first_party", "mimo-v2-omni": "developer_not_first_party",
    "mimo-v2-pro": "developer_not_first_party", "mimo-v2.5": "developer_not_first_party",
    "mimo-v2.5-pro": "developer_not_first_party", "mimo-v2.6-flash": "developer_not_first_party",
    "mimo-v2.6-pro": "developer_not_first_party", "nova-2-lite": "developer_not_first_party",
    "reka-core-20240501": "developer_not_first_party", "reka-core-20240722": "developer_not_first_party",
    "reka-core-20240904": "developer_not_first_party", "reka-flash-20240722": "developer_not_first_party",
    "reka-flash-20240904": "developer_not_first_party", "ring-flash-2.0": "developer_not_first_party",
    "solar-pro4": "developer_not_first_party", "step-1o-turbo-202506": "developer_not_first_party",
    "step-3": "developer_not_first_party", "step-3.5-flash": "developer_not_first_party",
    "trinity-large": "developer_not_first_party", "trinity-large-preview": "developer_not_first_party",
    "trinity-large-thinking": "developer_not_first_party", "yi-large": "developer_not_first_party",
    "yi-large-preview": "developer_not_first_party", "yi-lightning": "developer_not_first_party",
    "yi-lightning-lite": "developer_not_first_party",
    # open_weights (121)
    "Athene 70B (0725)": "open_weights", "Athene V2 Chat": "open_weights", "Aya Expanse 32B": "open_weights",
    "Beam 1.0 501B A23B": "open_weights", "Gemma 2 27B IT": "open_weights", "Gemma 2 9B IT": "open_weights",
    "Gemma 2 9B IT SimPO": "open_weights", "Gemma 3 12B IT": "open_weights", "Gemma 3 27B IT": "open_weights",
    "Gemma 3 4B IT": "open_weights", "Gemma 3n E4B IT": "open_weights", "Gemma 4 26B A4B": "open_weights",
    "Gemma 4 31B": "open_weights", "INTELLECT-3": "open_weights", "Inkling": "open_weights",
    "Inkling 2 Mini": "open_weights", "Inkling 2 Small": "open_weights", "Inkling Small": "open_weights",
    "Inkling-Small": "open_weights", "Llama 3 70B Instruct": "open_weights",
    "Llama 3.1 405B Instruct (BF16)": "open_weights", "Llama 3.1 405B Instruct (FP8)": "open_weights",
    "Llama 3.1 70B Instruct": "open_weights", "Llama 3.1 Nemotron 51B Instruct": "open_weights",
    "Llama 3.1 Nemotron 70B Instruct": "open_weights", "Llama 3.1 Nemotron Ultra 253B v1": "open_weights",
    "Llama 3.1 Tulu 3 70B": "open_weights", "Llama 3.3 70B Instruct": "open_weights",
    "Llama 3.3 Nemotron Super 49B v1": "open_weights", "Llama 3.3 Nemotron Super 49B v1.5": "open_weights",
    "Llama 4 Maverick 17B 128E Instruct": "open_weights", "Llama 4 Scout 17B 16E Instruct": "open_weights",
    "Molmo 2 8B": "open_weights", "NVIDIA-Nemotron-3-Nano-30B-A3B (BF16)": "open_weights",
    "NVIDIA-Nemotron-3-Super-120B-A12B": "open_weights", "NVIDIA-Nemotron-3-Ultra-550B-A55B (NVFP4)": "open_weights",
    "NVIDIA-Nemotron-3.5-Lightning-30B-A3B (NVFP4)": "open_weights",
    "NVIDIA-Nemotron-3.5-Super-VL-120B-A12B (NVFP4)": "open_weights", "Nemotron-4 340B Instruct": "open_weights",
    "OLMo 2 32B Instruct (0325)": "open_weights", "Olmo 3 32B Think": "open_weights",
    "Olmo 3.1 32B Instruct": "open_weights", "Olmo 3.1 32B Think": "open_weights", "Phi-4": "open_weights",
    "QwQ-32B": "open_weights", "Qwen2.5-72B-Instruct": "open_weights", "Qwen2.5-Coder-32B-Instruct": "open_weights",
    "Qwen3-235B-A22B": "open_weights", "Qwen3-235B-A22B (Non-Thinking)": "open_weights",
    "Qwen3-235B-A22B-Instruct (2507)": "open_weights", "Qwen3-235B-A22B-Thinking (2507)": "open_weights",
    "Qwen3-30B-A3B": "open_weights", "Qwen3-30B-A3B-Instruct (2507)": "open_weights", "Qwen3-32B": "open_weights",
    "Qwen3-Coder-480B-A35B-Instruct": "open_weights", "Qwen3.5-122B-A10B": "open_weights",
    "Qwen3.5-27B": "open_weights", "Qwen3.5-35B-A3B": "open_weights", "Qwen3.5-397B-A17B": "open_weights",
    "Qwen3.8-27B": "open_weights", "athene-70b": "open_weights", "athene-70b-0725": "open_weights",
    "athene-v2-chat": "open_weights", "c4ai-aya-expanse-32b": "open_weights", "gemma-2-27b-it": "open_weights",
    "gemma-2-9b-it": "open_weights", "gemma-2-9b-it-simpo": "open_weights", "gemma-3-12b-it": "open_weights",
    "gemma-3-27b-it": "open_weights", "gemma-3-4b-it": "open_weights", "gemma-3n-e4b-it": "open_weights",
    "gemma-4-26b-a4b": "open_weights", "gemma-4-31b": "open_weights", "gpt-oss-120b": "open_weights",
    "gpt-oss-20b": "open_weights", "inkling": "open_weights", "intellect-3": "open_weights",
    "llama-3-70b-instruct": "open_weights", "llama-3.1-405b-instruct": "open_weights",
    "llama-3.1-405b-instruct-bf16": "open_weights", "llama-3.1-405b-instruct-fp8": "open_weights",
    "llama-3.1-70b-instruct": "open_weights", "llama-3.1-nemotron-51b-instruct": "open_weights",
    "llama-3.1-nemotron-70b-instruct": "open_weights", "llama-3.1-nemotron-ultra-253b-v1": "open_weights",
    "llama-3.1-tulu-3-70b": "open_weights", "llama-3.1-tulu-3-8b": "open_weights",
    "llama-3.3-70b-instruct": "open_weights", "llama-3.3-nemotron-49b-super-v1": "open_weights",
    "llama-4-maverick-17b-128e-instruct": "open_weights", "llama-4-scout-17b-16e-instruct": "open_weights",
    "molmo-2-8b": "open_weights", "nemotron-4-340b-instruct": "open_weights",
    "nvidia-llama-3.3-nemotron-super-49b-v1.5": "open_weights", "nvidia-nemotron-3-nano-30b-a3b-bf16": "open_weights",
    "nvidia-nemotron-3-super-120b-a12b": "open_weights", "nvidia-nemotron-3-ultra-550b-a55b-nvfp4": "open_weights",
    "nvidia-nemotron-3.5-lightning-30b-a3b-nvfp4": "open_weights",
    "nvidia-nemotron-3.5-super-vl-120b-a12b-nvfp4": "open_weights", "olmo-2-0325-32b-instruct": "open_weights",
    "olmo-3-32b-think": "open_weights", "olmo-3.1-32b-instruct": "open_weights", "olmo-3.1-32b-think": "open_weights",
    "phi-4": "open_weights", "qwen2-72b-instruct": "open_weights", "qwen2.5-72b-instruct": "open_weights",
    "qwen2.5-coder-32b-instruct": "open_weights", "qwen3-235b-a22b": "open_weights",
    "qwen3-235b-a22b-instruct-2507": "open_weights", "qwen3-235b-a22b-no-thinking": "open_weights",
    "qwen3-235b-a22b-thinking-2507": "open_weights", "qwen3-30b-a3b": "open_weights",
    "qwen3-30b-a3b-instruct-2507": "open_weights", "qwen3-32b": "open_weights",
    "qwen3-coder-480b-a35b-instruct": "open_weights", "qwen3.5-122b-a10b": "open_weights",
    "qwen3.5-27b": "open_weights", "qwen3.5-35b-a3b": "open_weights", "qwen3.5-397b-a17b": "open_weights",
    "qwen3.8-27b": "open_weights", "qwq-32b": "open_weights",
}


def problems() -> list[str]:
    """Mapping errors; empty = valid."""
    errors = []
    names: dict[str, str] = {}
    key_provider: dict[str, str] = {}
    for provider, keys, arena_names, evidence in MODELS:
        if not keys or not arena_names or not evidence:
            errors.append(f"{arena_names}: empty keys, names or evidence")
        for k in keys:
            if not model_map.is_first_party(k, provider):
                errors.append(f"{k}: not first-party for {provider}")
            if key_provider.setdefault(k, provider) != provider:
                errors.append(f"{k}: under several providers")
            if k in ROLLING_KEYS:
                errors.append(f"{k}: rolling alias in MODELS")
        for n in arena_names:
            if n in names:
                errors.append(f"{n}: mapped twice")
            names[n] = provider
    for keys, arena_names, start, end, evidence in ROLLING:
        if end is not None and pd.Timestamp(end) < pd.Timestamp(start):
            errors.append(f"{arena_names}: served interval ends before it starts")
        errors += [f"{k}: not first-party for deepseek" for k in keys if not model_map.is_first_party(k, "deepseek")]
        errors += [f"{n}: both in MODELS and ROLLING" for n in arena_names if n in names]
    rolling_names = {n for _, ns, *_ in ROLLING for n in ns}
    errors += [f"{n}: mapped and listed as unmapped" for n in UNMAPPED if n in names or n in rolling_names]
    errors += [f"{n}: unknown reason {r}" for n, r in UNMAPPED.items() if r not in REASONS]
    return errors


ROLLING_KEYS = frozenset(k for keys, *_ in ROLLING for k in keys)


def fixed_pairs() -> pd.DataFrame:
    """Long table of the fixed mapping: name, key, provider."""
    rows = [(n, k, p) for p, keys, names, _ in MODELS for n in names for k in keys]
    return pd.DataFrame(rows, columns=["name", "key", "provider"])


def pairs_at(when) -> pd.DataFrame:
    """(name, key, provider) pairs valid at `when`: the fixed mapping plus, per rolling alias key, the names of the
    version it served at `when` (latest start <= when, and when <= end)."""
    when = pd.Timestamp(when)
    rows = []
    by_key: dict[str, list] = {}
    for keys, names, start, end, _ in ROLLING:
        for k in keys:
            by_key.setdefault(k, []).append((pd.Timestamp(start), None if end is None else pd.Timestamp(end), names))
    for k, versions in by_key.items():
        live = [v for v in versions if v[0] <= when]
        if not live:
            continue
        start, end, names = max(live, key=lambda v: v[0])
        if end is not None and when > end:
            continue
        rows += [(n, k, "deepseek") for n in names]
    out = pd.concat([fixed_pairs(), pd.DataFrame(rows, columns=["name", "key", "provider"])], ignore_index=True)
    return out


def mapped_names() -> set[str]:
    return set(fixed_pairs()["name"]) | {n for _, ns, *_ in ROLLING for n in ns}
