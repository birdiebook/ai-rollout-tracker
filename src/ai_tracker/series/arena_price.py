"""G2: price at fixed Arena capability (track G2A, docs/kallor/g2_arena_pris.md). Not a core series until reviewed.

Value for month m = lowest 3:1 blended first-party price (USD per 1M tokens, LiteLLM file at month end) among models
whose Arena text rating (overall, Bradley-Terry era from 2024-01-09) in the latest board known at month end is >= the
rating of a fixed reference model in that SAME board. The reference rule (section 1 of the doc) was locked before any
value was computed:
- variant A `g2_price_at_arena_capability`: reference gpt-4-0314, successors gpt-4-0613, gpt-4-1106-preview;
- variant B `g2_price_at_arena_capability_4o`: reference gpt-4o-2024-05-13, successors gpt-4o-2024-08-06,
  gpt-4-turbo-2024-04-09.
A successor is used only when the reference is missing from a board, offset by the median reference - successor
difference over the latest 3 earlier boards that hold both (earlier boards only: no future data).

Vintages follow sources/vintages.py: the first row of a month is known month end + 1 day from boards documented by
month end + 1 day (register 2026-11-25, Integration 14, R23-2, the X20 rule); a board published by month end but
documented later adds a row on its evidence date when the value changes. known_from = max(board vintage date, price known_from = month end + 1). Rows whose board exists only in the
dataset's bulk upload are source="backfill".
A key that LiteLLM's month-end file lists with `deprecation_date` <= month end does not count (retired model; rule added
2026-11-24 after the first build, docs/kallor/g2_arena_pris.md section 2).

Price corrections (X5, review R8 R-2): PRICE_CORRECTIONS replaces a LiteLLM price that is documented wrong, for one
(key, provider), only while LiteLLM still shows the old price, and only in snapshots dated on or after
max(the date the price changed, the date the evidence was published): nothing is back-dated. PRICE_CHECKS records,
per key that sets the minimum in some month, what the price was checked against (R-3); `table()` carries the status
per row (column `price_check`) and `build(exclude_keys=...)` gives the series without a key (R-4).
"""

from __future__ import annotations

from functools import lru_cache, partial

import numpy as np
import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.series import price_capability as pc
from ai_tracker.sources import arena_map

BT_START = pd.Timestamp("2024-01-09")  # first Bradley-Terry board (dataset card)
FIRST_MONTH = pd.Period("2024-01", "M")
OVERLAP_BOARDS = 3
TOL = 1e-9
PRICE_LAG_DAYS = pc.LAG_DAYS  # LiteLLM state at month end is known month end + 1 day

# Reference chains, locked 2026-11-24 (docs/kallor/g2_arena_pris.md section 1). Each model: (API name, display name);
# the API name wins when both are in a board.
CHAINS: dict[str, tuple[tuple[str, str], ...]] = {
    "gpt4": (("gpt-4-0314", "GPT-4 (0314)"), ("gpt-4-0613", "GPT-4 (0613)"),
             ("gpt-4-1106-preview", "GPT-4 Turbo Preview (1106)")),
    "gpt4o": (("gpt-4o-2024-05-13", "GPT-4o (2024-05-13)"), ("gpt-4o-2024-08-06", "GPT-4o (2024-08-06)"),
              ("gpt-4-turbo-2024-04-09", "GPT-4 Turbo (2024-04-09)")),
}
KEYS = {"gpt4": "g2_price_at_arena_capability", "gpt4o": "g2_price_at_arena_capability_4o"}

Board = tuple  # (published, ratings: pd.Series by model name, evidence, source, origin)

# ------------------------------------------------------------------ price corrections and checks (X5)
# Evidence that could be read is recorded as URL, read date and SHA-256 of the quoted passage (whitespace-normalized
# page text); the passage itself is kept only in data/raw/price_checks/<date>/quotes.json, never in git.
# developers.googleblog.com, ai.google.dev, discuss.ai.google.dev and docs.cloud.google.com are denied by the sandbox
# proxy (2026-11-24): Google's announcements are cited by URL, title and date only (from the search index).
_G_BLOG_PRO = ("https://developers.googleblog.com/en/updated-gemini-models-reduced-15-pro-pricing-increased-rate-limits-"
               "and-more/")
_G_BLOG_FLASH = "https://developers.googleblog.com/en/gemini-15-flash-updates-google-ai-studio-gemini-api/"
_VERTEX = "https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing"
PRICE_EVIDENCE: dict[str, tuple[str, str, str]] = {  # id -> (url, read on, sha256 of the passage)
    "vertex_1_5_pro": (_VERTEX, "2026-11-24", "85a3257eada68094a00ba32b17c70af79b3410652aefe254490db3f11085b0ff"),
    "vertex_1_5_flash": (_VERTEX, "2026-11-24", "4ad5d37e6d5befcc8af892ac3dbc27b60926e59d64ac438534a7986ddc6a9a47"),
    "vertex_chars_per_token": (_VERTEX, "2026-11-24",
                               "c91f7a1579118e4cd6e53670efc2edbf1194fae70a5f3d16be1320bb6a2343a5"),
    "vertex_2_0_flash_lite": (_VERTEX, "2026-11-24", "00d8d2f7cfbe967b9a522e65b649cb37e0a44dde4e80ac67a3c4ca44d172d2b9"),
}

PRICE_CORRECTIONS: list[dict] = [
    {"key": key, "provider": "gemini", "effective": "2024-10-01", "published": "2024-09-24",
     "old": (3.50, 10.50), "new": (1.25, 5.00),
     "source": f"Google, 'Updated production-ready Gemini models, reduced 1.5 Pro pricing, increased rate limits, and "
               f"more' (2024-09-24, effective 2024-10-01, prompts <= 128k), {_G_BLOG_PRO} (host blocked; title and "
               f"date from the search index). Level from Google's Vertex price list (read 2026-11-24): input 0.0003125 "
               f"and output 0.00125 USD per 1,000 characters at <= 128k, about 4 characters per token = 1.25 / 5.00 "
               f"per 1M tokens. The blog's table is reported to give 2.50 for output; its stated 52 % output cut "
               f"(10.50 -> 5.04) and the price list give 5.00, which is used",
     "evidence": ("vertex_1_5_pro", "vertex_chars_per_token")}
    for key in ("gemini/gemini-1.5-pro-002", "gemini/gemini-1.5-pro-001")
] + [
    {"key": key, "provider": "gemini", "effective": "2024-08-12", "published": "2024-08-08",
     "old": (0.35, 1.05), "new": (0.075, 0.30),
     "source": f"Google, 'Gemini 1.5 Flash price drop with tuning rollout complete, and more' (2024-08-08, effective "
               f"2024-08-12, prompts <= 128k), {_G_BLOG_FLASH} (host blocked; title and date from the search index). "
               f"Level from Google's Vertex price list (read 2026-11-24): input 0.00001875 and output 0.000075 USD per "
               f"1,000 characters = 0.075 / 0.30 per 1M tokens, the price LiteLLM itself lists from 2024-09-15 "
               f"(R8 A-2b)",
     "evidence": ("vertex_1_5_flash", "vertex_chars_per_token")}
    for key in ("gemini/gemini-1.5-flash", "gemini/gemini-1.5-flash-001")
]

# R-3: every key that sets the minimum of A or B in some month (after R-1, R-2, R-5; data 2026-11-24), checked against
# the developer's price page on 2026-11-24. Status:
#   developer_page: the level matches the developer's own price page as read that day (the page shows today's price,
#                   not the date it took effect);
#   not_listed:     the developer's page was read, the retired model is no longer on it;
#   blocked:        the developer's page is denied by the sandbox proxy (openai.com, platform.openai.com,
#                   developers.openai.com, api-docs.deepseek.com, mistral.ai, docs.mistral.ai, ai.google.dev,
#                   web.archive.org); not checked, not worked around;
#   disputed:       not checkable, and indirect evidence does not support the price.
# Everything except developer_page is unverified. (status, what was checked)
PRICE_CHECKS: dict[str, tuple[str, str]] = {
    "gpt-4-1106-preview": ("blocked", "10/30; OpenAI blocked; not on OpenRouter today"),
    "gpt-4-0125-preview": ("blocked", "10/30; OpenAI blocked; not on OpenRouter today"),
    "claude-3-sonnet-20240229": ("not_listed", "3/15; platform.claude.com pricing read, Claude 3 Sonnet no longer "
                                               "listed (retired)"),
    "gemini/gemini-1.5-flash": ("blocked", "0.35/1.05 (2024-06, launch price) not checkable (ai.google.dev blocked; "
                                           "Vertex lists only today's 0.075/0.30); 0.075/0.30 from 2024-08-12 = "
                                           "PRICE_CORRECTIONS, level on the Vertex list"),
    "gemini/gemini-1.5-flash-001": ("developer_page", "0.075/0.30 = Vertex list (characters x 4), evidence "
                                                      "vertex_1_5_flash"),
    "gemini/gemini-1.5-flash-002": ("developer_page", "0.075/0.30 = Vertex list, evidence vertex_1_5_flash"),
    "gemini/gemini-1.5-pro-002": ("developer_page", "1.25/5.00 after PRICE_CORRECTIONS = Vertex list, evidence "
                                                    "vertex_1_5_pro; date of the cut from the blocked announcement"),
    "gemini/gemini-2.0-flash-lite-preview-02-05": ("developer_page", "0.075/0.30 = Vertex list for Gemini 2.0 Flash "
                                                                     "Lite (the GA model; the preview is not listed), "
                                                                     "evidence vertex_2_0_flash_lite"),
    "deepseek-chat": ("blocked", "0.14/0.28 (V2 2024-07, V3 promotion to 2025-02-08); api-docs.deepseek.com blocked"),
    "deepseek/deepseek-chat": ("blocked", "0.14/0.28 (V3 promotion); api-docs.deepseek.com blocked"),
    "gpt-4o-2024-05-13": ("blocked", "5/15; OpenAI blocked; OpenRouter (provider OpenAI) 5/15 today"),
    "o1-mini-2024-09-12": ("blocked", "3/12 (2024-09); OpenAI blocked; not on OpenRouter today"),
    "gpt-5-nano-2025-08-07": ("blocked", "0.05/0.40; OpenAI blocked; OpenRouter (provider OpenAI) 0.05/0.40 today"),
    "mistral/mistral-small-3-2-2506": ("disputed", "0.06/0.18 in LiteLLM from 2026-03-07 (source mistral.ai/pricing, "
                                                   "bundled in an unrelated PR); mistral.ai, docs.mistral.ai and "
                                                   "archive.org blocked; OpenRouter lists only third-party hosts "
                                                   "(DeepInfra 0.075/0.20, 2026-11-24) (R8 R-4)"),
}
UNVERIFIED = frozenset(k for k, (status, _) in PRICE_CHECKS.items() if status != "developer_page")
DISPUTED = frozenset(k for k, (status, _) in PRICE_CHECKS.items() if status == "disputed")


def apply_corrections(prices: pd.DataFrame, when: pd.Timestamp,
                      corrections: list[dict] | None = None) -> pd.DataFrame:
    """Replace documented-wrong LiteLLM prices in the snapshot at `when` (see PRICE_CORRECTIONS)."""
    corrections = PRICE_CORRECTIONS if corrections is None else corrections
    if prices.empty or not corrections:
        return prices
    out = prices.copy()
    when = pd.Timestamp(when)
    for c in corrections:
        if when < max(pd.Timestamp(c["effective"]), pd.Timestamp(c["published"])):
            continue
        hit = ((out["key"] == c["key"]) & (out["provider"] == c["provider"])
               & np.isclose(out["input_per_m"], c["old"][0], rtol=0, atol=1e-9)
               & np.isclose(out["output_per_m"], c["old"][1], rtol=0, atol=1e-9))
        out.loc[hit, ["input_per_m", "output_per_m"]] = c["new"]
    return out


def rating(ratings: pd.Series, names: tuple[str, ...]) -> float | None:
    for n in names:
        if n in ratings.index and pd.notna(ratings[n]):
            return float(ratings[n])
    return None


def threshold(board: Board, earlier: list[Board], chain: tuple[tuple[str, str], ...]) -> tuple[float, str] | None:
    """Reference rating in `board` (and which model set it). `earlier`: boards published before `board` that are
    known at the vintage date; used only for a successor's offset."""
    ratings = board[1]
    r0 = rating(ratings, chain[0])
    if r0 is not None:
        return r0, chain[0][0]
    for succ in chain[1:]:
        rs = rating(ratings, succ)
        if rs is None:
            continue
        diffs = []
        for b in sorted(earlier, key=lambda b: (b[0], b[2])):
            if b[0] >= board[0]:
                continue
            a, s = rating(b[1], chain[0]), rating(b[1], succ)
            if a is not None and s is not None:
                diffs.append(a - s)
        if len(diffs) >= OVERLAP_BOARDS:
            return rs + float(np.median(diffs[-OVERLAP_BOARDS:])), succ[0]
    return None


def key_capability(ratings: pd.Series, pairs: pd.DataFrame) -> pd.DataFrame:
    """Per (key, provider): the best rating among its mapped names in the board, and that name."""
    p = pairs.assign(rating=pairs["name"].map(ratings)).dropna(subset=["rating"])
    if p.empty:
        return pd.DataFrame(columns=["key", "provider", "rating", "name"])
    best = p.sort_values(["rating", "name"], ascending=[False, True]).drop_duplicates(["key", "provider"])
    return best[["key", "provider", "rating", "name"]]


def month_value(prices: pd.DataFrame, ratings: pd.Series, thr: float, pairs: pd.DataFrame) -> dict | None:
    """Lowest qualifying blended price, with the key and Arena name that set it."""
    if prices.empty:
        return None
    cap = key_capability(ratings, pairs)
    q = prices.merge(cap, on=["key", "provider"])  # first-party: mapped (key, provider) pairs only
    q = q[q["rating"] >= thr - TOL]
    if q.empty:
        return None
    q = q.assign(blended=pc.blended(q["input_per_m"], q["output_per_m"])).sort_values(["blended", "key"])
    best = q.iloc[0]
    return {"value": float(best["blended"]), "key": best["key"], "name": best["name"],
            "rating": float(best["rating"]), "n_qualifying": int(q["key"].nunique())}


def _norm(boards: list[Board]) -> list[Board]:
    out = []
    for published, ratings, evidence, source, origin in boards:
        published = pd.Timestamp(published).normalize()
        if published < BT_START:
            continue
        evidence = max(pd.Timestamp(evidence).normalize(), published)  # never known before its own date
        out.append((published, ratings, evidence, source, origin))
    return sorted(out, key=lambda b: (b[0], b[2]))


def live_prices(snaps: pd.DataFrame, when: pd.Timestamp, deprecations: pd.DataFrame | None,
                corrections: list[dict] | None = None) -> pd.DataFrame:
    """Price rows of the snapshot at `when`, corrected (apply_corrections), without keys that the same snapshot lists
    as retired by `when` (LiteLLM `deprecation_date` <= when, as known then)."""
    prices = apply_corrections(pc.prices_at(snaps, when), when, corrections)
    if deprecations is None or prices.empty:
        return prices
    d = deprecations[deprecations["sha"].isin(set(prices["sha"])) & (deprecations["key"] != "")]
    retired = set(d.loc[d["deprecation_date"] <= pd.Timestamp(when), "key"])
    return prices[~prices["key"].isin(retired)]


def build(boards: list[Board], snaps: pd.DataFrame, chain: tuple[tuple[str, str], ...], last_month: pd.Period,
          pairs_at=arena_map.pairs_at, deprecations: pd.DataFrame | None = None,
          corrections: list[dict] | None = None, exclude_keys: tuple[str, ...] = ()) -> pd.DataFrame:
    """Vintaged monthly rows: period, value, known_from, source + diagnostics (key, name, rating, threshold,
    reference, board, n_qualifying, price_check = PRICE_CHECKS status of the key at the minimum or "unchecked").
    Months FIRST_MONTH .. last_month (pass only complete months).
    `deprecations` (litellm_prices.deprecations()): keys retired by month end per the month-end snapshot are dropped.
    `corrections`: default PRICE_CORRECTIONS ([] = none). `exclude_keys`: keys left out (sensitivity, R-4)."""
    bs = _norm(boards)
    rows = []
    for m in pd.period_range(FIRST_MONTH, last_month, freq="M") if FIRST_MONTH <= last_month else []:
        end = m.end_time.normalize()
        cand = [b for b in bs if b[0] <= end]
        if not cand:
            continue
        prices = live_prices(snaps, end, deprecations, corrections)
        if exclude_keys:
            prices = prices[~prices["key"].isin(exclude_keys)]
        pairs = pairs_at(end)
        base = max(end + pd.Timedelta(days=1), end + pd.Timedelta(days=PRICE_LAG_DAYS))
        days = sorted({base} | {b[2] for b in cand if b[2] > base})
        prev = None
        for day in days:
            # the first version (on `base`) uses every board documented through that day, so a board published on the
            # last day and documented the next enters its month (register 2026-11-25, Integration 14, R23-2; X20)
            known = [b for b in cand if b[2] <= day]
            if not known:
                continue
            board = known[-1]  # latest published (ties: latest evidence)
            t = threshold(board, known[:-1], chain)
            if t is None:
                continue
            v = month_value(prices, board[1], t[0], pairs)
            if v is None:
                continue
            if prev is None or not np.isclose(v["value"], prev, rtol=0, atol=1e-12):
                rows.append({"period": str(m), "value": v["value"], "known_from": max(day, base),
                             "source": board[3], "key": v["key"], "name": v["name"], "rating": v["rating"],
                             "threshold": t[0], "reference": t[1], "board": board[0],
                             "n_qualifying": v["n_qualifying"],
                             "price_check": PRICE_CHECKS.get(v["key"], ("unchecked", ""))[0]})
                prev = v["value"]
    cols = ["period", "value", "known_from", "source", "key", "name", "rating", "threshold", "reference", "board",
            "n_qualifying", "price_check"]
    return pd.DataFrame(rows, columns=cols)


def coverage(boards: list[Board], chain: tuple[tuple[str, str], ...]) -> pd.DataFrame:
    """Every name that qualifies in at least one BT board: first/last qualifying board and mapping status
    (mapped, an UNMAPPED reason, or 'unreviewed')."""
    bs = _norm(boards)
    seen: dict[str, list] = {}
    for i, b in enumerate(bs):
        t = threshold(b, bs[:i], chain)
        if t is None:
            continue
        for name in b[1].index[b[1] >= t[0] - TOL]:
            s = seen.setdefault(name, [b[0], b[0]])
            s[1] = b[0]
    mapped = arena_map.mapped_names()
    rows = [(n, f, la, "mapped" if n in mapped else arena_map.UNMAPPED.get(n, "unreviewed"))
            for n, (f, la) in seen.items()]
    return pd.DataFrame(rows, columns=["name", "first", "last", "status"]).sort_values("name").reset_index(drop=True)


# ------------------------------------------------------------------ fetch

@lru_cache(maxsize=1)
def _inputs():
    from ai_tracker.sources import arena, litellm_prices

    return arena.subset_boards("text"), litellm_prices.snapshots(), litellm_prices.deprecations()


@lru_cache(maxsize=None)
def table(variant: str) -> pd.DataFrame:
    from ai_tracker.sources import vintages

    boards, snaps, deps = _inputs()
    return build(boards, snaps, CHAINS[variant], vintages.last_complete_month(), deprecations=deps)


def fetch(variant: str) -> pd.DataFrame:
    return table(variant)[["period", "value", "known_from", "source"]]


LICENSE = ("derived: LiteLLM model_prices_and_context_window.json (MIT, LICENSE in BerriAI/litellm) + LMArena "
           "leaderboard dataset (CC BY 4.0, dataset card); credit LMArena")
_NOTE = ("Lägsta blandade förstapartspris (3:1, LiteLLM vid månadsslut) bland modeller med Arena-rating (text, overall, "
         "BT-eran från 2024-01-09) ≥ referensens rating i samma tavla. known_from = senare av tavlans belägg och "
         "månadsslut + 1 dag; tavlor bara i bulkuppladdningen ger source=backfill. Handgranskad namnkoppling i "
         "sources/arena_map.py. Daterade prisrättningar och priskontroll per månad (PRICE_CORRECTIONS, PRICE_CHECKS; "
         "Mistral Small 3.2 2026-03 – 07 overifierad). Ej kärnserie (underkänd i granskning R8). Se "
         "docs/kallor/g2_arena_pris.md avsnitt 7")

SPECS = [
    Spec(key=KEYS["gpt4"], branch="G2", label="Pris vid fast Arena-förmåga (≥ GPT-4-0314 i samma tavla)",
         unit="USD per 1M tokens (3:1 input:output)", freq="M", source="LiteLLM git-historik × LMArena text",
         fetch=partial(fetch, "gpt4"), lag_days=PRICE_LAG_DAYS, license=LICENSE, revised=True, publish=True,
         question="Hur mycket billigare blir GPT-4-nivån (mars 2023) enligt mänskliga omdömen?", note=_NOTE),
    Spec(key=KEYS["gpt4o"], branch="G2", label="Pris vid fast Arena-förmåga (≥ GPT-4o-2024-05-13 i samma tavla)",
         unit="USD per 1M tokens (3:1 input:output)", freq="M", source="LiteLLM git-historik × LMArena text",
         fetch=partial(fetch, "gpt4o"), lag_days=PRICE_LAG_DAYS, license=LICENSE, revised=True, publish=True,
         question="Samma mått vid GPT-4o-nivån (maj 2024)", note=_NOTE),
]
