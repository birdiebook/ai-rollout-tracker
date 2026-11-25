"""G2: price at a rolling capability threshold (track Q1, docs/kallor/g2_rorlig_troskel.md). Catalog series, not core.

Register: docs/mattregister.md, "2026-11-25 – Q1: pris vid rörlig förmågetröskel". A fixed threshold saturates (review
R8): the cheapest tier clears it with room to spare and the price stops moving. A rolling threshold binds by
construction: what does the capability that was the frontier L months ago cost today?

Arena variants (`g2_price_rolling12_arena`, main, L = 12; `g2_price_rolling6_arena`, L = 6), within one board so that
scale breaks cancel (the idea of series/arena_price.py). A version of month m has a date d (sources/vintages.py: first
version month end + 1 from boards documented by month end, later versions on the evidence date of a board published
by month end but documented later, only when the value changes).
- b(m): latest board published <= end of m among the boards known at d (as G2A).
- reference board: latest board published <= end of m - L among the boards known at d (what is known at d about the
  frontier at m - L; the register explains why not "as known at the end of m - L": the measurement gap 2025-09 -
  2026-03 would make the lag up to L + 7). `literal_reference=True` gives the literal rule as a sensitivity.
- r(m): the top-rated model of the reference board (ties: name order); experimental names count.
- a name is found in a board as itself, else under its documented rename (RENAMES), else as the single board name with
  the same normalized form (lowercase letters and digits; the switch to display names in 2026-10).
- threshold: r(m)'s rating in b(m). If r(m) is not found: the first of the next SUCCESSORS models of the reference
  board (rank order) that is found in b(m) and shares >= OVERLAP_BOARDS earlier boards (published before b(m), known at
  d) with r(m): its rating in b(m) + the median r - s difference over the latest OVERLAP_BOARDS of them. Else no value.
- value: lowest 3:1 blended first-party price (LiteLLM at month end, arena_price's corrections and retirement rule,
  arena_map pairs, best variant per key) among keys rated >= threshold in b(m).
- known_from = max(d, month end + 1); source "backfill" when b(m) or the reference board is only in the bulk upload.

Frontier price (`g2_price_frontier_arena`, context, no pace measure): the price of the top-rated priced model in b(m).

ECI variant (`g2_price_rolling12_eci`): threshold = highest Epoch ECI among models released by the end of m - 12
(today's ECI), only when >= ECI_FLOOR (model_map covers ECI >= 128); price as above over model_map's keys. Every value
uses today's ECI: the history is a backfill (as g2_price_at_capability).
"""

from __future__ import annotations

import re
from functools import lru_cache, partial

import numpy as np
import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.series import arena_price as ap
from ai_tracker.series import price_capability as pc
from ai_tracker.sources import arena_map, model_map

LAGS = {"g2_price_rolling12_arena": 12, "g2_price_rolling6_arena": 6}
FRONTIER_KEY = "g2_price_frontier_arena"
ECI_KEY = "g2_price_rolling12_eci"
ECI_LAG = 12
ECI_FLOOR = 128.0  # model_map covers every Epoch model with ECI >= 128 (module doc of model_map)
SUCCESSORS = 10
OVERLAP_BOARDS = ap.OVERLAP_BOARDS
TOL = ap.TOL
PRICE_LAG_DAYS = ap.PRICE_LAG_DAYS

# Renames without overlap, documented with the boards in sources/arena_map.py (module doc and evidence column).
RENAMES: dict[str, str] = {
    "gpt-4-turbo": "gpt-4-1106-preview",
    "gemini-1.5-pro-api-0514": "gemini-1.5-pro-001",
    "gemini-1.5-flash-api-0514": "gemini-1.5-flash-001",
    "gemini-2.0-flash-lite-preview": "gemini-2.0-flash-lite-preview-02-05",
    "gemini-2.0-flash": "gemini-2.0-flash-001",
}

COLUMNS = ["period", "value", "known_from", "source", "key", "name", "rating", "threshold", "reference", "via",
           "board", "ref_board", "n_qualifying", "price_check"]


def norm(name: str) -> str:
    """Comparable name: 'gemini-2.5-pro' and 'Gemini 2.5 Pro' -> 'gemini25pro' (order kept)."""
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


class Lookup:
    """Name lookup in one board (rules 1-3 of the register)."""

    def __init__(self, ratings: pd.Series):
        self.ratings = ratings.dropna()
        groups: dict[str, list[str]] = {}
        for n in self.ratings.index:
            groups.setdefault(norm(n), []).append(n)
        self.by_norm = groups

    def find(self, name: str) -> str | None:
        if name in self.ratings.index:
            return name
        new = RENAMES.get(name)
        if new is not None and new in self.ratings.index:
            return new
        hits = self.by_norm.get(norm(name), [])
        return hits[0] if len(hits) == 1 else None

    def rating(self, name: str) -> float | None:
        n = self.find(name)
        return None if n is None else float(self.ratings[n])


def ranked(ratings: pd.Series) -> list[str]:
    """Names by rating, highest first (ties: name order)."""
    r = ratings.dropna()
    return sorted(r.index, key=lambda n: (-float(r[n]), n))


def _latest_per_date(boards: list) -> list:
    """One board per publish date (the latest version among those given), in publish order."""
    out: dict[pd.Timestamp, tuple] = {}
    for b in boards:  # sorted by (published, evidence): later versions overwrite
        out[b[0]] = b
    return [out[k] for k in sorted(out)]


def threshold(board, earlier: list, reference: list[str], lookup) -> tuple[float, str, str] | None:
    """(threshold, reference, via) in `board`. `reference`: the reference board's names in rank order (the first is
    r(m)); `earlier`: boards known at the version date (only those published before `board` are used, one version
    per date); `lookup(board) -> Lookup`. via = "" when r(m) is in the board, else the successor used."""
    if not reference:
        return None
    r = reference[0]
    lb = lookup(board)
    rr = lb.rating(r)
    if rr is not None:
        return rr, r, ""
    prior = _latest_per_date([b for b in earlier if b[0] < board[0]])
    for s in reference[1:1 + SUCCESSORS]:
        rs = lb.rating(s)
        if rs is None:
            continue
        diffs = []
        for b in prior:
            lk = lookup(b)
            a, c = lk.rating(r), lk.rating(s)
            if a is not None and c is not None:
                diffs.append(a - c)
        if len(diffs) >= OVERLAP_BOARDS:
            return rs + float(np.median(diffs[-OVERLAP_BOARDS:])), r, s
    return None


def frontier_threshold(prices: pd.DataFrame, ratings: pd.Series, pairs: pd.DataFrame) -> tuple[float, str] | None:
    """(rating, name) of the top-rated priced key in the board."""
    if prices.empty:
        return None
    q = prices.merge(ap.key_capability(ratings, pairs), on=["key", "provider"])
    if q.empty:
        return None
    best = q.sort_values(["rating", "name"], ascending=[False, True]).iloc[0]
    return float(best["rating"]), str(best["name"])


def _lookups():
    """board -> Lookup, built once per board (boards are kept alive by the caller's list)."""
    cache: dict[int, Lookup] = {}

    def lookup(b) -> Lookup:
        k = id(b[1])
        if k not in cache:
            cache[k] = Lookup(b[1])
        return cache[k]
    return lookup


def _versions(bs: list, m: pd.Period):
    """(known_from, known boards) per version of month m (sources/vintages.py)."""
    end = m.end_time.normalize()
    cand = [b for b in bs if b[0] <= end]
    base = max(end + pd.Timedelta(days=1), end + pd.Timedelta(days=PRICE_LAG_DAYS))
    for day in sorted({base} | {b[2] for b in cand if b[2] > end}):
        cutoff = end if day == base else day
        known = [b for b in cand if b[2] <= cutoff]
        if known:
            yield max(day, base), known


def build(boards: list, snaps: pd.DataFrame, lag: int, last_month: pd.Period, pairs_at=arena_map.pairs_at,
          deprecations: pd.DataFrame | None = None, corrections: list[dict] | None = None,
          exclude_keys: tuple[str, ...] = (), literal_reference: bool = False) -> pd.DataFrame:
    """Vintaged monthly rows (COLUMNS) for lag L >= 1, or the frontier price for lag 0. Months from
    arena_price.FIRST_MONTH + lag to last_month (pass only complete months)."""
    bs = ap._norm(boards)
    lookup = _lookups()
    rows = []
    first = ap.FIRST_MONTH + lag
    for m in pd.period_range(first, last_month, freq="M") if first <= last_month else []:
        end = m.end_time.normalize()
        prices = ap.live_prices(snaps, end, deprecations, corrections)
        if exclude_keys and not prices.empty:
            prices = prices[~prices["key"].isin(exclude_keys)]
        pairs = pairs_at(end)
        ref_end = (m - lag).end_time.normalize()
        prev = None
        for known_from, known in _versions(bs, m):
            board = known[-1]  # latest published (ties: latest evidence)
            if lag == 0:
                ref_board, ft = board, frontier_threshold(prices, board[1], pairs)
                t = None if ft is None else (ft[0], ft[1], "")
            else:
                pool = [b for b in known if b[0] <= ref_end
                        and (not literal_reference or b[2] <= ref_end)]
                if not pool:
                    continue
                ref_board = pool[-1]
                t = threshold(board, known[:-1], ranked(ref_board[1]), lookup)
            if t is None:
                continue
            v = ap.month_value(prices, board[1], t[0], pairs)
            if v is None:
                continue
            if prev is None or not np.isclose(v["value"], prev, rtol=0, atol=1e-12):
                source = "backfill" if "backfill" in (board[3], ref_board[3]) else "release"
                rows.append({"period": str(m), "value": v["value"], "known_from": known_from, "source": source,
                             "key": v["key"], "name": v["name"], "rating": v["rating"], "threshold": t[0],
                             "reference": t[1], "via": t[2], "board": board[0], "ref_board": ref_board[0],
                             "n_qualifying": v["n_qualifying"],
                             "price_check": ap.PRICE_CHECKS.get(v["key"], ("unchecked", ""))[0]})
                prev = v["value"]
    return pd.DataFrame(rows, columns=COLUMNS)


def coverage(boards: list, lag: int, last_month: pd.Period) -> pd.DataFrame:
    """First version per month: names rated >= the threshold in b(m) that arena_map has not reviewed (they never
    count). Empty = every qualifying name is mapped or listed in UNMAPPED with a reason."""
    bs = ap._norm(boards)
    reviewed = arena_map.mapped_names() | set(arena_map.UNMAPPED)
    lookup = _lookups()
    rows = []
    first = ap.FIRST_MONTH + lag
    for m in pd.period_range(first, last_month, freq="M") if first <= last_month else []:
        ref_end = (m - lag).end_time.normalize()
        for _, known in _versions(bs, m):
            board = known[-1]
            pool = [b for b in known if b[0] <= ref_end]
            if not pool:
                break
            t = threshold(board, known[:-1], ranked(pool[-1][1]), lookup)
            if t is not None:
                r = board[1].dropna()
                rows += [(str(m), n) for n in r.index[r >= t[0] - TOL] if n not in reviewed]
            break
    return pd.DataFrame(rows, columns=["period", "name"])


# ------------------------------------------------------------------ ECI variant

def build_eci(snaps: pd.DataFrame, epoch: dict[str, pd.DataFrame], last_month: pd.Period, lag: int = ECI_LAG,
              floor: float = ECI_FLOOR, mapping: pd.DataFrame | None = None, deprecations: pd.DataFrame | None = None,
              corrections: list[dict] | None = None, exclude_keys: tuple[str, ...] = ()) -> pd.DataFrame:
    """Monthly table (period index): value, key, model, capability, threshold, reference, n_qualifying."""
    mapping = model_map.key_models() if mapping is None else mapping
    eci = epoch["eci"]
    release = pc._release(epoch)
    capability_at = pc.capability_eci(eci)
    first = snaps["snapshot_date"].min().to_period("M") if len(snaps) else last_month + 1
    rows = {}
    for m in pd.period_range(first, last_month, freq="M") if first <= last_month else []:
        when = m.end_time.normalize()
        ref = eci[eci["release"] <= (m - lag).end_time.normalize()]
        if ref.empty:
            continue
        ref = ref.sort_values(["eci", "model"], ascending=[False, True]).iloc[0]
        thr = float(ref["eci"])
        if thr < floor - TOL:
            continue
        p = ap.live_prices(snaps, when, deprecations, corrections)
        if p.empty:
            continue
        if exclude_keys:
            p = p[~p["key"].isin(exclude_keys)]
        p = p.merge(mapping[["key", "provider"]].drop_duplicates(), on=["key", "provider"])  # first-party only
        cap = pc.key_capability(capability_at(when), release, when, mapping)
        p = p.assign(capability=p["key"].map(cap)).dropna(subset=["capability"])
        p = p[p["capability"] >= thr - TOL]
        if p.empty:
            continue
        p = p.assign(blended=pc.blended(p["input_per_m"], p["output_per_m"])).sort_values(["blended", "key"])
        best = p.iloc[0]
        model = mapping[mapping["key"] == best["key"]].assign(r=lambda d: d["model"].map(release))
        model = model[model["r"] <= when].sort_values("r").iloc[-1]["model"]
        rows[m] = {"value": float(best["blended"]), "key": best["key"], "model": model,
                   "capability": float(best["capability"]), "threshold": thr, "reference": ref["model"],
                   "n_qualifying": int(p["key"].nunique())}
    return pd.DataFrame.from_dict(rows, orient="index").sort_index()


# ------------------------------------------------------------------ fetch

@lru_cache(maxsize=None)
def table(key: str) -> pd.DataFrame:
    from ai_tracker.sources import vintages

    boards, snaps, deps = ap._inputs()
    lag = 0 if key == FRONTIER_KEY else LAGS[key]
    return build(boards, snaps, lag, vintages.last_complete_month(), deprecations=deps)


def fetch(key: str) -> pd.DataFrame:
    return table(key)[["period", "value", "known_from", "source"]]


@lru_cache(maxsize=1)
def eci_table() -> pd.DataFrame:
    from ai_tracker.sources import litellm_prices, vintages

    snaps, epoch = pc._inputs()
    return build_eci(snaps, epoch, vintages.last_complete_month(), deprecations=litellm_prices.deprecations())


def fetch_eci() -> pd.Series:
    return eci_table()["value"].rename(ECI_KEY)


ARENA_LICENSE = ("derived: LiteLLM model_prices_and_context_window.json (MIT, LICENSE in BerriAI/litellm) + LMArena "
                 "leaderboard dataset (CC BY 4.0, dataset card) and the lmarena-ai/arena-leaderboard Space files (same "
                 "publisher, no licence file); credit LMArena")
_ARENA_SOURCE = "LiteLLM git-historik × LMArena text (HF-dataset och Space-filer)"
_UNIT = "USD per 1M tokens (3:1 input:output)"
_NOTE = ("Rörlig tröskel inom samma tavla: referensen är ettan i tavlan för m − L (känd vid versionens datum), med "
         "efterföljarregel när den saknas. Priser och koppling som g2_price_at_arena_capability (LiteLLM vid månadsslut, "
         "prisrättningar, pensionerade modeller räknas inte, förstapartsnycklar). Katalogserie, ingen takt. Se "
         "docs/kallor/g2_rorlig_troskel.md")

SPECS = [
    Spec(key="g2_price_rolling12_arena", branch="G2",
         label="Pris för förmågan som var fronten för 12 månader sedan (Arena, samma tavla)", unit=_UNIT, freq="M",
         source=_ARENA_SOURCE, fetch=partial(fetch, "g2_price_rolling12_arena"), lag_days=PRICE_LAG_DAYS,
         license=ARENA_LICENSE, revised=True, publish=True,
         question="Vad kostar förra årets frontförmåga i dag?", note=_NOTE),
    Spec(key="g2_price_rolling6_arena", branch="G2",
         label="Pris för förmågan som var fronten för 6 månader sedan (Arena, samma tavla)", unit=_UNIT, freq="M",
         source=_ARENA_SOURCE, fetch=partial(fetch, "g2_price_rolling6_arena"), lag_days=PRICE_LAG_DAYS,
         license=ARENA_LICENSE, revised=True, publish=True,
         question="Samma mått med ett halvår gammal front", note=_NOTE),
    Spec(key=FRONTIER_KEY, branch="G2", label="Pris för den högst rankade prissatta modellen (Arena)", unit=_UNIT,
         freq="M", source=_ARENA_SOURCE, fetch=partial(fetch, FRONTIER_KEY), lag_days=PRICE_LAG_DAYS,
         license=ARENA_LICENSE, revised=True, publish=True,
         question="Vad kostar fronten själv? Sammanhang till de rörliga trösklarna, inget takmått",
         note="Lägsta blandade förstapartspris bland nycklar med högsta rating bland prissatta nycklar i månadens "
              "tavla. Se docs/kallor/g2_rorlig_troskel.md"),
    Spec(key=ECI_KEY, branch="G2", label="Pris för förmågan som var fronten för 12 månader sedan (Epoch ECI)",
         unit=_UNIT, freq="M", source="LiteLLM git-historik × Epoch AI ECI", fetch=fetch_eci, lag_days=pc.LAG_DAYS,
         license=pc.LICENSE, revised=True, publish=True,
         question="Samma fråga med Epochs förmågeindex i stället för chattpreferens",
         note="Historiken är bakåtfylld: ECI och tröskeln är dagens skattningar (läckage). Värde bara när tröskeln är "
              "≥ 128 (model_map:s täckning). Se docs/kallor/g2_rorlig_troskel.md"),
]
