"""Open or closed weights and the lab's country per model, for the G1 gap series (track Q2).

Doc: docs/kallor/g1_oppen_stangd.md.

Classification comes from the sources' own fields (register 2026-11-25, Q2). The curated tables here are the
documented fallbacks and the identities the fields cannot give:

- ORG_COUNTRY: Arena organization string (normalized) -> country, with a reference per row: Epoch's
  `Country (of organization)` for the same organization (all_ai_models.csv, read 2026-11-25), or a note why the
  string is that organization. Strings without a documented country are absent (the model is left out of the China
  series in that board).
- ARENA_MODELS: Arena names that no Arena field classifies (steps 1-3 of the register). Each row: weights, the date
  the weights were released (None for closed), organization string and a reference.
- ARENA_RENAMES: Arena's own renames, reviewed by hand from names that vanish and appear between consecutive boards
  (names, organization, licence and vote count only, never ratings). Evidence per row.
- DISPLAY_EXTRA: the switch to display names (boards 2026-10-15 -> 2026-10-20) that the mechanical rules in
  `arena_meta.display_switch_pairs` do not match.
- ECI_MODELS: Epoch models whose `Accessibility group` or `Country (of organization)` is missing both in
  eci_scores.csv and in all_ai_models.csv.
- ECI_WEIGHTS_RELEASE and `weights_release`: the date an open ECI model's weights were released, when it is after
  the model's `date` or Epoch's note leaves it open (register 2026-11-25, X20, after review R23).

Pure data and pure functions; no network.
"""

from __future__ import annotations

import re

OPEN, CLOSED = "open", "closed"
CHINA = "China"
US = "United States of America"
_EPOCH = "Epoch all_ai_models.csv (2026-11-25): Organization '{}' = Country '{}'"


def norm(text: str) -> str:
    """Lower case, letters and digits only ("Zhipu AI" -> "zhipuai", "GPT-4o (2024-05-13)" -> "gpt4o20240513")."""
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def _e(org: str, country: str) -> tuple[str, str]:
    return country, _EPOCH.format(org, country)


# ------------------------------------------------------------------ organization -> country (Arena strings)
# Keyed by norm(Arena organization string). Value: (country, reference).
ORG_COUNTRY: dict[str, tuple[str, str]] = {
    "01ai": _e("01.AI", CHINA),
    "ai2": _e("Allen Institute for AI", US),
    "allenai": _e("Allen Institute for AI", US),
    "allenaiuw": (US, _EPOCH.format("Allen Institute for AI", US) + "; University of Washington = " + US),
    "ai21labs": _e("AI21 Labs", "Israel"),
    "alibaba": _e("Alibaba", CHINA),
    "aliaba": (CHINA, "misspelling of 'Alibaba' in Arena's Space table (Qwen models); "
                      + _EPOCH.format("Alibaba", CHINA)),
    "amazon": _e("Amazon", US),
    "anthropic": _e("Anthropic", US),
    "antgroup": _e("Ant Group", CHINA),
    "arceeai": _e("Arcee AI", US),
    "baidu": _e("Baidu", CHINA),
    "blackforestlabs": _e("Black Forest Labs", "Germany"),
    "bytedance": _e("ByteDance", CHINA),
    "cohere": _e("Cohere", "Canada"),
    "databricks": _e("Databricks", US),
    "deepseek": _e("DeepSeek", CHINA),
    "deepseekai": _e("DeepSeek", CHINA),
    "google": _e("Google", US),
    "huggingface": _e("Hugging Face", US),
    "ibm": _e("IBM", US),
    "ideogram": _e("Ideogram", "Canada"),
    "inceptionai": (US, "Arena 'inception-ai' lists Mercury, the model of Inception Labs; "
                        + _EPOCH.format("Inception Labs", US)),
    "internlm": (CHINA, "InternLM is the model family of Shanghai AI Laboratory (huggingface.co/internlm); "
                        + _EPOCH.format("Shanghai AI Lab", CHINA)),
    "lmsys": _e("Large Model Systems Organization", US),
    "lumaai": _e("LumaLabs", US),
    "meituan": _e("Meituan Inc", CHINA),
    "meta": _e("Meta AI", US),
    "microsoft": _e("Microsoft", US),
    "microsoftai": (US, "Microsoft AI (MAI models), a Microsoft division; " + _EPOCH.format("Microsoft", US)),
    "minimax": _e("MiniMax", CHINA),
    "mistral": _e("Mistral AI", "France"),
    "moonshot": _e("Moonshot", CHINA),
    "mosaicml": _e("MosaicML", US),
    "nexusflow": _e("Nexusflow", US),
    "nousresearch": _e("Nous Research", US),  # X20 (R23-9): Epoch's spelling
    "nvidia": _e("Nvidia", US),  # X20 (R23-9): Epoch's spelling
    "openai": _e("OpenAI", US),
    "openbmb": _e("OpenBMB (Open Lab for Big Model Base)", CHINA),
    "openchat": (CHINA, "Arena 'OpenChat' lists OpenChat 3.5, which Epoch lists as 'OpenChat 3.5-7B' under Tsinghua "
                        "University; " + _EPOCH.format("Tsinghua University", CHINA)),
    "perplexityai": _e("Perplexity", US),
    "primeintellect": _e("Prime Intellect", US),
    "princeton": _e("Princeton University", US),
    "recraft": _e("Recraft", "United Kingdom"),
    "reflection": _e("Reflection", US),
    "rekaai": _e("Reka AI", US),
    "rwkv": _e("RWKV Foundation", "Multinational"),
    "salesforce": _e("Salesforce", US),
    "snowflake": _e("Snowflake", US),
    "stabilityai": _e("Stability AI", "United Kingdom"),
    "stanford": _e("Stanford University", US),
    "stepfun": _e("StepFun", CHINA),
    "tencent": _e("Tencent", CHINA),
    "thinky": (US, "Arena 'thinky' lists Inkling 2 Small, which Epoch lists under Thinking Machines; "
                   + _EPOCH.format("Thinking Machines", US)),
    "tii": _e("Technology Innovation Institute", "United Arab Emirates"),
    "togetherai": _e("Together", US),
    "tsinghua": _e("Tsinghua University", CHINA),
    "ucberkeley": _e("University of California (UC) Berkeley", US),
    "ucsd": _e("University of California San Diego", US),
    "upstage": _e("Upstage", "South Korea"),
    "upstageai": _e("Upstage", "South Korea"),
    "uw": _e("University of Washington", US),
    "xai": _e("xAI", US),
    "xiaomi": _e("Xiaomi Corp", CHINA),
    "zai": _e("Z.ai (Zhipu AI)", CHINA),
    "zhipu": _e("Z.ai (Zhipu AI)", CHINA),
    "zhipuai": _e("Z.ai (Zhipu AI)", CHINA),
}
# Seen in Arena but without a documented country, so left out of the China series: Cognitive Computations, LLaVA,
# Nomic AI, OpenAssistant, OpenGVLab, Snorkel AI, h2oai (small open models, never near a frontier).


def country(org: str | None) -> str | None:
    if not org:
        return None
    hit = ORG_COUNTRY.get(norm(org))
    return hit[0] if hit else None


def is_chinese(countries: str | None) -> bool | None:
    """True if every listed country is China, False if none is, None for a mix or nothing (left out)."""
    if countries is None or (isinstance(countries, float)) or not str(countries).strip():
        return None
    parts = [c.strip() for c in str(countries).split(",") if c.strip()]
    if not parts:
        return None
    flags = {p == CHINA for p in parts}
    return None if len(flags) > 1 else flags.pop()


# ------------------------------------------------------------------ Arena: curated classification (step 4)
# name -> (weights or None, weights released on (YYYY-MM-DD, open only), organization string or '', reference).
# A row applies to every name of the model's class; None/'' = take that field from Arena.
ARENA_MODELS: dict[str, tuple[str, str | None, str, str]] = {
    "gpt-3.5-turbo": (CLOSED, None, "OpenAI", "OpenAI API model, weights never released "
                                              "(platform.openai.com/docs/models/gpt-3-5-turbo; host "
                                              "blocked, not read)"),
    "dbrx-instruct": (OPEN, "2024-03-27", "Databricks", "weights at huggingface.co/databricks/dbrx-instruct (gated "
                                                        "repository, answers 401 without login, 2026-11-25), "
                                                        "announced 2024-03-27 (databricks.com/blog/introducing-dbrx-"
                                                        "new-state-art-open-llm; host blocked, not read); Arena's "
                                                        "later label 'DBRX LICENSE'"),
    "qwen-max-2025-08-15": (CLOSED, None, "Alibaba", "Qwen-Max snapshot of Alibaba Cloud Model Studio, API only "
                                                     "(alibabacloud.com/help/en/model-studio/models; host blocked)"),
    "qwen-vl-max-2025-08-13": (CLOSED, None, "Alibaba", "Qwen-VL-Max snapshot of Alibaba Cloud Model Studio, API "
                                                        "only (alibabacloud.com/help/en/model-studio/models; "
                                                        "host blocked)"),
    "trinity-large-preview": (None, None, "Arcee AI", "organization blank in Arena; Epoch all_ai_models.csv lists "
                                                      "'Arcee Trinity Large' under Prime Intellect, Arcee AI (US)"),
    "trinity-large-thinking": (None, None, "Arcee AI", "organization blank in Arena; Epoch all_ai_models.csv lists "
                                                       "'Trinity Large Thinking' under Arcee AI (US)"),
}
# Left out on purpose (no source field and no documented identity): gpt-5-old (anonymous test name, Arena boards
# 2025-08-08 - 08-29) and llama-4-maverick-03-26-experimental (a customized chat variant whose weights were never
# released; Meta released Llama 4 Maverick under another name).

# ------------------------------------------------------------------ Arena: renames (name classes)
# (old name, new name, first board with the new name, evidence). Reviewed by hand: consecutive boards where the old
# name vanishes and the new one appears; same organization and licence where Arena gives them; for dataset boards the
# vote count carries over. Not mapped: splits (one name into two), preview -> GA changes (different checkpoints) and
# names that vanish with no successor (removed models).
_SPACE = "Space boards {}: '{}' last on {}, '{}' first on {}"
ARENA_RENAMES: list[tuple[str, str, str, str]] = [
    ("claude-v1", "claude-1", "2023-08-02", "Space boards 2023-07-17 / 2023-08-02; Space table key 'claude-1' "
                                            "Anthropic, Proprietary"),
    ("claude-instant-v1", "claude-instant-1", "2023-08-02", "Space boards 2023-07-17 / 2023-08-02"),
    ("claude-2", "claude-2.0", "2023-12-06", "Space boards 2023-11-16 / 2023-12-06; 'claude-2.1' appears as a new "
                                             "model the same day"),
    ("gpt-4", "gpt-4-0314", "2023-12-06", "Space boards 2023-11-16 / 2023-12-06; in May 2023 the only GPT-4 was "
                                          "0314 (0613 released 2023-06-13), and Arena moved the history to "
                                          "'gpt-4-0314'"),
    ("gpt-4-turbo", "gpt-4-1106-preview", "2024-02-02", "Space boards 2024-01-25 / 2024-02-02; arena_map "
                                                        "(documented rename, no overlap)"),
    ("dbrx-instruct", "dbrx-instruct-preview", "2024-04-11", "Space boards 2024-04-10 / 2024-04-11"),
    ("athene-70b", "athene-70b-0725", "2024-07-30", "Space boards before / 2024-07-30 (Nexusflow Athene-70B, "
                                                    "released 2024-07-25)"),
    ("chatgpt-4o-latest-2024-08-08", "chatgpt-4o-latest", "2024-08-22", "Space boards before / 2024-08-22"),
    ("chatgpt-4o-latest", "chatgpt-4o-latest-20240808", "2024-09-15", "Space boards before / 2024-09-15 (the "
                                                                      "later snapshot -20240903 appears as new)"),
    ("gemini-1.5-pro-api-0514", "gemini-1.5-pro-001", "2024-10-23", "Space boards 2024-10-15 / 2024-10-23; "
                                                                    "arena_map"),
    ("gemini-1.5-flash-api-0514", "gemini-1.5-flash-001", "2024-10-23", "Space boards 2024-10-15 / 2024-10-23; "
                                                                        "arena_map"),
    ("qwen-max-2025-01-25", "qwen2.5-max", "2025-02-05", "Space boards before / 2025-02-05; Alibaba's API id of "
                                                         "Qwen2.5-Max is qwen-max-2025-01-25"),
    ("gemini-2.0-flash-001", "gemini-2.0-flash", "2025-02-06", "Space boards 2025-02-05 / 2025-02-06; arena_map"),
    ("gemini-2.0-flash-lite-preview", "gemini-2.0-flash-lite-preview-02-05", "2025-02-09",
     "Space boards 2025-02-06 / 2025-02-09; arena_map"),
    ("trinity-large", "trinity-large-preview", "2026-04-09", "dataset boards before / 2026-04-09, Apache 2.0, votes "
                                                             "12,625 -> 13,146"),
    ("claude-sonnet-5-thinking", "claude-sonnet-5-high", "2026-07-10", "dataset boards before / 2026-07-10, "
                                                                       "anthropic, Proprietary; same 'thinking' -> "
                                                                       "'high' relabel as 2026-08-12"),
    ("glm-5.2 (max)", "glm-5.2-max", "2026-07-26", "dataset boards before / 2026-07-26, zai, MIT, votes 18,017 -> "
                                                   "19,623"),
    ("kimi-k3", "kimi-k3-max", "2026-07-26", "dataset boards before / 2026-07-26, moonshot, votes 3,619 -> 3,569; "
                                             "licence changes from Proprietary to 'Kimi K3 license' (weights)"),
    ("deepseek-v4-flash-thinking", "deepseek-v4-flash-high-preview", "2026-08-02",
     "dataset boards before / 2026-08-02, deepseek, MIT, votes 46,445 -> 48,387"),
    ("deepseek-v4-pro-thinking", "deepseek-v4-pro-high-preview", "2026-08-02",
     "dataset boards before / 2026-08-02, deepseek, MIT, votes 44,669 -> 46,859"),
    ("claude-opus-4-5-20251101-thinking-32k", "claude-opus-4-5-20251101-high-32k", "2026-08-12",
     "dataset boards before / 2026-08-12, anthropic, Proprietary, votes 37,213 -> 37,217"),
    ("claude-opus-4-6-thinking", "claude-opus-4-6-high", "2026-08-12", "dataset boards before / 2026-08-12, votes "
                                                                       "72,425 -> 72,466"),
    ("claude-opus-4-7-thinking", "claude-opus-4-7-high", "2026-08-12", "dataset boards before / 2026-08-12, votes "
                                                                       "60,222 -> 60,268"),
    ("claude-opus-4-8-thinking", "claude-opus-4-8-high", "2026-08-12", "dataset boards before / 2026-08-12, votes "
                                                                       "40,409 -> 40,588"),
    ("claude-sonnet-4-5-20250929-thinking-32k", "claude-sonnet-4-5-20250929-high-32k", "2026-08-12",
     "dataset boards before / 2026-08-12, votes 82,549 -> 82,533"),
    ("gemini-3.6-flash", "gemini-3.6-flash-high", "2026-08-12", "dataset boards before / 2026-08-12, google, votes "
                                                                "13,559 -> 13,693"),
    ("claude-fable-5", "claude-fable-5-high", "2026-09-25", "dataset boards before / 2026-09-25, anthropic, "
                                                            "Proprietary, votes 30,057 -> 36,462; same effort relabel"),
]
# The first display names arrived one board early, on 2026-10-15 (Claude, Gemini, Kimi and Muse models). The pairs
# 2026-10-13 -> 2026-10-15 are listed by `arena_meta.early_display_pairs` (same normalized name, same organization and
# licence) and were reviewed by hand; they are part of the renames (register 2026-11-25, item 1).

# Display names (2026-10-15 -> 2026-10-20) that the mechanical rules do not match: (API name, display name, evidence)
DISPLAY_EXTRA: list[tuple[str, str, str]] = [  # boards 2026-10-15 / 2026-10-20, same organization and licence
    ('deepseek-v4.1-flash-max', 'DeepSeek-V4.1-Flash-20260910 (Max)', 'deepseek, MIT, votes 12,793 -> 13,444'),
    ('gemini-2.5-flash-lite-preview-09-2025-no-thinking', 'Gemini 2.5 Flash-Lite Preview (Non-Thinking, 09-2025)',
     'google, Proprietary, votes 47,437 -> 47,428'),
    ('gemini-3-flash (thinking-minimal)', 'Gemini 3 Flash (Minimal)', 'google, Proprietary, votes 91,039 -> 91,005'),
    ('gpt-5.2-chat-latest-20260210', 'GPT-5.2 Chat (20260210)', 'openai, Proprietary, votes 35,999 -> 35,991'),
    ('gpt-5.3-chat-latest', 'GPT-5.3 Chat', 'openai, Proprietary, votes 34,345 -> 34,343'),
    ('grok-4-fast-chat', 'Grok 4 Fast (Non-Reasoning)', 'xai, Proprietary, votes 6,340 -> 6,341'),
    ('hunyuan-hy3-preview', 'Hy3 preview', 'tencent, tencent-hunyuan-community, votes 6,879 -> 6,880'),
    ('mistral-medium-2505', 'Mistral Medium 3 (2505)', 'mistral, Proprietary, votes 32,782 -> 32,783'),
    ('mistral-medium-2508', 'Mistral Medium 3.1 (2508)', 'mistral, Proprietary, votes 95,321 -> 95,291'),
    ('mistral-small-2506', 'Mistral Small 3.2 (2506)', 'mistral, Apache 2.0, votes 17,462 -> 17,459'),
    ('nova-2-lite', 'Amazon Nova 2 Lite', 'amazon, Proprietary, votes 12,413 -> 12,409'),
    ('nvidia-llama-3.3-nemotron-super-49b-v1.5', 'Llama 3.3 Nemotron Super 49B v1.5',
     'nvidia, Nvidia Open, votes 3,328 -> 3,327'),
    ('qwen3-235b-a22b-no-thinking', 'Qwen3-235B-A22B (Non-Thinking)', 'alibaba, Apache 2.0, votes 37,484 -> 37,483'),
]
# Unmatched on 2026-10-20: 'Beam 1.0 501B A23B' (reflection, new that day).


# ------------------------------------------------------------------ Epoch: curated classification
# Epoch model -> (weights or None, country or None, reference). Only for models whose field is missing both in
# eci_scores.csv and all_ai_models.csv. Country by the lab's ORG_COUNTRY row.
_HF = "weights at huggingface.co/{} (repository created {}, checked 2026-11-25); {}"
_PALM = ("Google PaLM 2, announced 2023-05-10 (blog.google/technology/ai/google-palm-2-ai-large-language-model/; host "
         "blocked, not read), "
         "served through Google's API, weights never released; Google = " + US)
ECI_MODELS: dict[str, tuple[str | None, str | None, str]] = {
    **{m: (CLOSED, US, _PALM) for m in ("PaLM 2-L", "PaLM 2-M", "PaLM 2-S")},
    'Qwen2.5-Coder-14B': (OPEN, CHINA, _HF.format('Qwen/Qwen2.5-Coder-14B', '2024-11-08', 'Qwen = Alibaba')),
    'Qwen2.5-Coder-3B': (OPEN, CHINA, _HF.format('Qwen/Qwen2.5-Coder-3B', '2024-11-08', 'Qwen = Alibaba')),
    'Qwen2.5-Coder-0.5B': (OPEN, CHINA, _HF.format('Qwen/Qwen2.5-Coder-0.5B', '2024-11-08', 'Qwen = Alibaba')),
    'CodeQwen1.5-7B': (OPEN, CHINA, _HF.format('Qwen/CodeQwen1.5-7B', '2024-04-15', 'Qwen = Alibaba')),
    'Qwen-1_8B': (OPEN, CHINA, _HF.format('Qwen/Qwen-1_8B', '2023-11-30', 'Qwen = Alibaba')),
    'Yi-9B': (OPEN, CHINA, _HF.format('01-ai/Yi-9B', '2024-03-01', '01.AI')),
    'DeepSeek-Coder-V2-Lite-Base': (OPEN, CHINA,
                                    _HF.format('deepseek-ai/DeepSeek-Coder-V2-Lite-Base', '2024-06-14', 'DeepSeek')),
    'internlm-20b': (OPEN, CHINA, _HF.format('internlm/internlm-20b', '2023-09-18', 'InternLM = Shanghai AI Lab')),
    'internlm-7b': (OPEN, CHINA, _HF.format('internlm/internlm-7b', '2023-07-06', 'InternLM = Shanghai AI Lab')),
    'chatglm2-6b': (OPEN, CHINA,
                    _HF.format('zai-org/chatglm2-6b (formerly THUDM)', '2023-06-24', 'Zhipu AI / Tsinghua')),
    'vicuna-13b-v1.1': (OPEN, US, _HF.format('lmsys/vicuna-13b-v1.1', '2023-04-12', 'LMSYS')),
    'open_llama_7b': (OPEN, None, _HF.format('openlm-research/open_llama_7b', '2023-06-07', 'country not documented')),
    'INTELLECT-1': (OPEN, None, _HF.format('PrimeIntellect/INTELLECT-1', '2024-11-28', 'country from eci_scores.csv')),
}
# Left out (no field in either Epoch file and no documented answer): Qwen 3.6 Max (Preview), Qwen 3.6 Flash,
# Qwen 3.5 Plus (hosted 397B-A17B) and Qwen 3.5 Flash (hosted 35B-A3B), Alibaba's hosted API models (whether
# their weights are the published ones is not documented). Their country is in eci_scores.csv (China).


# ------------------------------------------------------------------ Epoch: weights release date (X20, R23-3)
# Register 2026-11-25, X20: an open ECI model is open from max(date, w); before that it counts as closed (Epoch counts
# API access as closed weights). w comes from this table, else from a past-tense weights sentence with a date in
# Epoch's `Accessibility notes`; a note that says the weights come later and gives no date leaves the model out of the
# open-vs-closed measure. Epoch model -> (w, reference).
ECI_WEIGHTS_RELEASE: dict[str, tuple[str, str]] = {
    "GLM-5.3": ("2026-08-25", ("Epoch note (all_ai_models.csv, 2026-11-25): 'The model weights of GLM-5.3 will be "
                               "publicly available soon in two weeks.' (as of 2026/08/14); huggingface.co/zai-org/"
                               "GLM-5.3 created 2026-08-25 (API createdAt, read 2026-11-25; creation, not proven public "
                               "that day); Arena lists glm-5.3-max as MIT from the board 2026-08-19")),
}

_MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
_DATE = re.compile(rf"\b(\d{{4}}[-/]\d{{2}}[-/]\d{{2}}|(?:{_MONTHS})[a-z]*\.? \d{{1,2}},? \d{{4}}|"
                   rf"\d{{1,2}} (?:{_MONTHS})[a-z]* \d{{4}})\b", re.IGNORECASE)
_SENTENCE = re.compile(r"(?<=[.;])\s+")
_WEIGHTS = re.compile(r"\bweights?\b", re.IGNORECASE)
_RELEASED = re.compile(r"\breleased\b", re.IGNORECASE)
_LATER = re.compile(r"\b(?:will|soon)\b", re.IGNORECASE)  # the register's words for "the weights come later"
PENDING = "pending"


def weights_release(note) -> str | None:
    """Release date of the weights in an Epoch `Accessibility notes` text: 'YYYY-MM-DD' from the first sentence that
    mentions weights, says they were released and has a date; PENDING when a weights sentence says they come later
    and no sentence dates the release; None when the note says nothing about it."""
    if not isinstance(note, str) or not note.strip():
        return None
    pending = False
    for sentence in _SENTENCE.split(note):
        if not _WEIGHTS.search(sentence):
            continue
        if _LATER.search(sentence):
            pending = True
            continue
        if _RELEASED.search(sentence) and (m := _DATE.search(sentence)):
            return _iso(m.group(1))
    return PENDING if pending else None


def _iso(text: str) -> str:
    from datetime import datetime

    t = text.replace("/", "-").replace(",", "").replace(".", "")
    for fmt in ("%Y-%m-%d", "%B %d %Y", "%b %d %Y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(t, fmt).date().isoformat()
        except ValueError:
            continue
    import pandas as pd

    return pd.Timestamp(t).date().isoformat()  # e.g. "Sept 4 2026"; raises on a text that is no date


class Classes:
    """Name classes (union-find): every name of one Arena model."""

    def __init__(self, pairs=()):
        self.parent: dict[str, str] = {}
        for a, b in pairs:
            self.union(a, b)

    def find(self, x: str) -> str:
        p = self.parent.get(x, x)
        if p == x:
            return x
        root = self.find(p)
        self.parent[x] = root
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)

    def members(self) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for x in set(self.parent) | set(self.parent.values()):
            out.setdefault(self.find(x), set()).add(x)
        return out
