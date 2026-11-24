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
month end; a board published by month end but documented later adds a row on its evidence date when the value
changes. known_from = max(board vintage date, price known_from = month end + 1). Rows whose board exists only in the
dataset's bulk upload are source="backfill".
A key that LiteLLM's month-end file lists with `deprecation_date` <= month end does not count (retired model; rule added
2026-11-24 after the first build, docs/kallor/g2_arena_pris.md section 2).
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


def live_prices(snaps: pd.DataFrame, when: pd.Timestamp, deprecations: pd.DataFrame | None) -> pd.DataFrame:
    """Price rows of the snapshot at `when`, without keys that the same snapshot lists as retired by `when`
    (LiteLLM `deprecation_date` <= when, as known then)."""
    prices = pc.prices_at(snaps, when)
    if deprecations is None or prices.empty:
        return prices
    d = deprecations[deprecations["sha"].isin(set(prices["sha"])) & (deprecations["key"] != "")]
    retired = set(d.loc[d["deprecation_date"] <= pd.Timestamp(when), "key"])
    return prices[~prices["key"].isin(retired)]


def build(boards: list[Board], snaps: pd.DataFrame, chain: tuple[tuple[str, str], ...], last_month: pd.Period,
          pairs_at=arena_map.pairs_at, deprecations: pd.DataFrame | None = None) -> pd.DataFrame:
    """Vintaged monthly rows: period, value, known_from, source + diagnostics (key, name, rating, threshold,
    reference, board, n_qualifying). Months FIRST_MONTH .. last_month (pass only complete months).
    `deprecations` (litellm_prices.deprecations()): keys retired by month end per the month-end snapshot are dropped."""
    bs = _norm(boards)
    rows = []
    for m in pd.period_range(FIRST_MONTH, last_month, freq="M") if FIRST_MONTH <= last_month else []:
        end = m.end_time.normalize()
        cand = [b for b in bs if b[0] <= end]
        if not cand:
            continue
        prices = live_prices(snaps, end, deprecations)
        pairs = pairs_at(end)
        base = max(end + pd.Timedelta(days=1), end + pd.Timedelta(days=PRICE_LAG_DAYS))
        days = sorted({base} | {b[2] for b in cand if b[2] > end})
        prev = None
        for day in days:
            cutoff = end if day == base else day
            known = [b for b in cand if b[2] <= cutoff]
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
                             "n_qualifying": v["n_qualifying"]})
                prev = v["value"]
    cols = ["period", "value", "known_from", "source", "key", "name", "rating", "threshold", "reference", "board",
            "n_qualifying"]
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
         "sources/arena_map.py. Ej registrerad (granskas först). Se docs/kallor/g2_arena_pris.md")

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
