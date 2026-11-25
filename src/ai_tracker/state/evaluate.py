"""Pre-registered test of the state rule itself (docs/mattregister.md, "2026-11-25 – T1").

Reads the state engine (branch, measures, snapshot) and changes nothing in it.

(a) Revision stability: the real-time state at month end m (as_of(m) on today's table, what the backcast gives) against
    the state for the same month from "today's data for m" (`revised_table`: the periods known at m, each with its
    latest vintage known on the vintage day V).
(b) Information: does the real-time state at m say anything about the direction of the branch's change in pace over
    the next h months, measured with the vintage at m + h (`outcome`)? Baselines: persistence (the direction over the
    last h months, vintage m) and chance (block permutation of months within branch).
(c) Description only: months per state, too few series or families, other thresholds, the two subperiods.

Nothing here is a live rule: the result is a recommendation to the owner (register entry, "Beslutsregel").
"""

from __future__ import annotations

import dataclasses
import math
from fractions import Fraction

import numpy as np
import pandas as pd

from ai_tracker import catalog, observations
from ai_tracker.state import register as R
from ai_tracker.state.branch import branch, diffusion_v2_exact
from ai_tracker.state.measures import Context, measure_path

# ------------------------------------------------------------------ registered constants (register 2026-11-25, T1)
START, END = "2024-01", "2026-10"  # month ends m of (a) and (c); (b) ends at END - h
VINTAGE = "2026-11-25"  # V: the run day, latest vintage used for "today's data"
HORIZONS = (3, 6)  # months
BLOCK = 6  # block length of the permutation (months)
N_PERM = 9999
SEED = 20261125
MIN_PRED = 20  # fewer predictions with an outcome: no test, p = 1
ALPHA = 0.10  # Holm-adjusted
KAPPA_MIN = 0.70  # (a): pooled v2 kappa below -> review recommended
HARD_FLIP_MAX = 0.02  # (a): pooled v2 share of hard flips above -> review recommended
DEV_END = "2025-06"  # last origin of the G-E development window; origins from 2025-07 are the holdout window (described)
REGISTERED = "0,67/0,33"
THRESHOLDS: dict[str, tuple[Fraction, Fraction]] = {
    REGISTERED: (Fraction(str(R.ACCELERATING)), Fraction(str(R.BRAKING))),
    "0,60/0,40": (Fraction(60, 100), Fraction(40, 100)),
    "0,75/0,25": (Fraction(75, 100), Fraction(25, 100)),
}
RULES = ("v2", "v1")  # v2 is the primary rule, v1 secondary
FEW = "för få"  # the category for kappa: för få källor (v2) / för få serier (v1)
REAL_STATES = (R.STATE_ACCEL, R.STATE_STABLE, R.STATE_BRAKE)
LABEL = "rekonstruerad (as-of-backcast, inte ett skarpt register)"


def month_end(month) -> pd.Timestamp:
    return pd.Period(month, freq="M").end_time.normalize()


# ------------------------------------------------------------------ states


def classify(index: Fraction | None, n: int, minimum: int, few: str, accel: Fraction, brake: Fraction) -> str:
    """The registered state rule with given thresholds (register section 2), compared exactly. With the registered
    thresholds it equals branch.state_of / state_v2 (checked for every record in `records`)."""
    if n < minimum or index is None:
        return few
    if index >= accel:
        return R.STATE_ACCEL
    if index <= brake:
        return R.STATE_BRAKE
    return R.STATE_STABLE


def record(code: str, month, b: dict) -> dict:
    """One branch month from branch(): the states, the exact indices and the counted series (with what (b) needs)."""
    used = b["series_used"]
    fam: dict[str, list[int]] = {}
    for m in used:
        fam.setdefault(m["family"], []).append(int(m["direction"]))
    dirs = [d for ds in fam.values() for d in ds]
    rec = {
        "branch": code, "month": str(pd.Period(month, freq="M")), "state_v2": b["state"], "state_v1": b["v1"]["state"],
        "index_v2": diffusion_v2_exact(fam), "index_v1": Fraction(sum(d + 1 for d in dirs), 2 * len(dirs)) if dirs else None,
        "n_families": int(b["n_families"]), "n_series": int(b["n_series"]), "has_entries": bool(b["registered_entries"]),
        "series": [{"series": m["series"], "family": m["family"], "direction": int(m["direction"]),
                    "latest_period": m["latest_period"], "sign": int(m.get("direction_sign", 1))} for m in used],
    }
    for rule, field in (("v2", "state_v2"), ("v1", "state_v1")):
        if rec["has_entries"] and state(rec, rule, REGISTERED) != rec[field]:
            raise AssertionError(f"{code} {rec['month']}: {rule} reclassified {state(rec, rule, REGISTERED)!r}, "
                                 f"the engine says {rec[field]!r}")
    return rec


def state(rec: dict, rule: str, thresholds: str = REGISTERED) -> str:
    if not rec["has_entries"]:
        return rec["state_v2"]
    accel, brake = THRESHOLDS[thresholds]
    if rule == "v2":
        return classify(rec["index_v2"], rec["n_families"], R.MIN_FAMILIES, R.STATE_FEW_FAMILIES, accel, brake)
    return classify(rec["index_v1"], rec["n_series"], R.MIN_SERIES, R.STATE_FEW, accel, brake)


def records(ctx: Context, months, branches) -> dict[tuple[str, str], dict]:
    """(branch, month) -> record, every month end in `months` (as_of(month end) on ctx's table)."""
    out = {}
    for month in months:
        when = month_end(month)
        for code in branches:
            out[(code, str(month))] = record(code, month, branch(code, when, ctx))
    return out


# ------------------------------------------------------------------ (a) today's data for month m


def revised_table(table: pd.DataFrame, vintage) -> pd.DataFrame:
    """Today's data for every month at once: one row per (series, period) with the value and source of its latest row
    known on `vintage`, and known_from = the period's first known_from. as_of(m) on it gives exactly the periods known
    at m with their latest vintage; rows known after `vintage` are not used."""
    t = table[table["known_from"] <= pd.Timestamp(vintage)]
    if t.empty:
        return t.copy()
    t = t.sort_values(["series", "period", "known_from"], kind="mergesort")
    first = t.groupby(["series", "period"], sort=False)["known_from"].transform("min")
    last = ~t.duplicated(["series", "period"], keep="last")
    out = t[last].copy()
    out["known_from"] = first[last]
    return out.reset_index(drop=True)


def revised_context(ctx: Context, vintage) -> Context:
    """Same catalog, core lists, families, derived series and selection as `ctx`, on the revised table."""
    return dataclasses.replace(ctx, table=revised_table(ctx.table, vintage))


def _category(s: str) -> str:
    return s if s in REAL_STATES else FEW


def kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Cohen's kappa of two labelings; None when the expected agreement is 1 (or no pairs)."""
    if not pairs:
        return None
    cats = sorted({c for p in pairs for c in p})
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    pe = sum((sum(a == c for a, _ in pairs) / n) * (sum(b == c for _, b in pairs) / n) for c in cats)
    return None if pe >= 1.0 - 1e-15 else (po - pe) / (1.0 - pe)


def agreement(pairs: list[tuple[str, str]]) -> dict:
    """(a) on S: pairs (real-time, revised) where at least one is accelererar, stabil or bromsar in."""
    allp = [(_category(a), _category(b)) for a, b in pairs]
    s = [p for p in allp if p[0] in REAL_STATES or p[1] in REAL_STATES]
    hard = {R.STATE_ACCEL, R.STATE_BRAKE}
    return {
        "n_all": len(allp), "agree_all": (sum(a == b for a, b in allp) / len(allp)) if allp else None,
        "n": len(s), "agree": (sum(a == b for a, b in s) / len(s)) if s else None, "kappa": kappa(s),
        "hard_flips": (sum({a, b} == hard for a, b in s) / len(s)) if s else None,
        "n_hard": sum({a, b} == hard for a, b in s), "n_changed": sum(a != b for a, b in s),
    }


def exposure(ctx: Context, rctx: Context, rt: dict) -> dict[tuple[str, str], tuple[int, int]]:
    """(branch, month) -> (counted series whose values known at m changed in later vintages, counted series)."""
    seen: dict[tuple[str, str], bool] = {}
    out = {}
    for (code, month), rec in rt.items():
        when = month_end(month)
        n_exp = 0
        for s in rec["series"]:
            k = (s["series"], month)
            if k not in seen:
                a = observations.as_of(s["series"], when, ctx.rows(s["series"]))
                b = observations.as_of(s["series"], when, rctx.rows(s["series"]))
                b = b.reindex(a.index)
                seen[k] = not (len(a) == len(b) and np.allclose(a.to_numpy(float), b.to_numpy(float),
                                                                rtol=1e-12, atol=1e-12, equal_nan=True))
            n_exp += seen[k]
        out[(code, month)] = (n_exp, len(rec["series"]))
    return out


def revision_table(rt: dict, rv: dict, rule: str, thresholds: str, branches, exp: dict | None = None) -> dict:
    """(a) per branch and pooled for one rule and threshold pair."""
    def summary(keys):
        pairs = [(state(rt[k], rule, thresholds), state(rv[k], rule, thresholds)) for k in keys]
        out = agreement(pairs)
        idx = f"index_{rule}"
        diffs = [abs(float(rv[k][idx]) - float(rt[k][idx])) for k in keys
                 if rt[k][idx] is not None and rv[k][idx] is not None]
        out["mean_abs_index_diff"] = float(np.mean(diffs)) if diffs else None
        if exp is not None:
            e = [exp[k] for k in keys]
            out["exposed_series_share"] = (sum(a for a, _ in e) / sum(n for _, n in e)) if sum(n for _, n in e) else None
            out["months_with_exposure"] = sum(a > 0 for a, _ in e)
        return out

    keys = sorted(rt)
    return {"pooled": summary(keys), "branches": {c: summary([k for k in keys if k[0] == c]) for c in branches}}


# ------------------------------------------------------------------ (b) outcomes and baselines


class PathCache:
    """measure_path(series, month end) on the real-time context, computed once."""

    def __init__(self, ctx: Context):
        self.ctx, self._d = ctx, {}

    def get(self, key: str, when) -> tuple[dict, pd.DataFrame | None]:
        k = (key, pd.Timestamp(when))
        if k not in self._d:
            self._d[k] = measure_path(key, pd.Timestamp(when), self.ctx)
        return self._d[k]

    def latest(self, key: str, when) -> str | None:
        return self.get(key, when)[0].get("latest_period")


def series_direction(cache: PathCache, key: str, sign: int, p_from: str | None, when) -> int | None:
    """sign(σ × (pace at the latest period − pace at p_from)), both from the vintage at `when`. None without a later
    period or without both paces."""
    if p_from is None:
        return None
    _m, path = cache.get(key, when)
    if path is None or p_from not in path.index:
        return None
    i, j = path.index.get_loc(p_from), len(path) - 1
    if not isinstance(i, (int, np.integer)) or j <= i:
        return None
    a, b = path["pace"].iloc[i], path["pace"].iloc[j]
    if not (math.isfinite(a) and math.isfinite(b)):
        return None
    d = sign * (float(b) - float(a))
    return 1 if d > 0 else -1 if d < 0 else 0


def aggregate(dirs: list[tuple[str, int | None]], rule: str) -> int | None:
    """Branch direction from (family, u) per series: +1 up (O > 1/2), -1 down (O < 1/2), None (tie or nothing)."""
    ok = [(f, u) for f, u in dirs if u is not None]
    if not ok:
        return None
    if rule == "v2":
        fam: dict[str, list[int]] = {}
        for f, u in ok:
            fam.setdefault(f, []).append(u)
        o = diffusion_v2_exact(fam)
    else:
        o = Fraction(sum(u + 1 for _, u in ok), 2 * len(ok))
    half = Fraction(1, 2)
    return 1 if o > half else -1 if o < half else None


def series_outcomes(cache: PathCache, rec: dict, h: int) -> tuple[list, list]:
    """Per counted series of `rec`: (family, u) of the outcome (vintage m + h) and (family, u') of persistence (vintage m)."""
    month = pd.Period(rec["month"], freq="M")
    m, t, prev = month_end(month), month_end(month + h), month_end(month - h)
    out, pers = [], []
    for s in rec["series"]:
        out.append((s["family"], series_direction(cache, s["series"], s["sign"], s["latest_period"], t)))
        pers.append((s["family"], series_direction(cache, s["series"], s["sign"], cache.latest(s["series"], prev), m)))
    return out, pers


def prediction(st: str) -> int:
    return 1 if st == R.STATE_ACCEL else -1 if st == R.STATE_BRAKE else 0


def block_order(n: int, block: int, rng: np.random.Generator) -> np.ndarray:
    """A random order of the blocks [0, block), [block, 2 block), ... of range(n), concatenated."""
    blocks = [np.arange(i, min(i + block, n)) for i in range(0, n, block)]
    return np.concatenate([blocks[k] for k in rng.permutation(len(blocks))]) if blocks else np.arange(0)


def hit_rate(pred: np.ndarray, out: np.ndarray) -> tuple[int, int]:
    """(hits, predictions with an outcome)."""
    ok = (pred != 0) & (out != 0)
    return int((pred[ok] == out[ok]).sum()), int(ok.sum())


def permutation_test(groups: list[tuple[np.ndarray, np.ndarray]], n_perm: int = N_PERM, block: int = BLOCK,
                     seed: int = SEED) -> dict:
    """Pooled hit rate H over groups (branches) of (prediction, outcome) arrays in month order, and its block
    permutation distribution (predictions permuted within group, outcomes fixed). p one-sided upper and lower."""
    hits = sum(hit_rate(p, o)[0] for p, o in groups)
    n = sum(hit_rate(p, o)[1] for p, o in groups)
    if n == 0:
        return {"H": None, "n": 0, "hits": 0, "chance": None, "p": 1.0, "p_low": 1.0}
    h_obs = hits / n
    rng = np.random.default_rng(seed)
    perm = np.empty(n_perm)
    for i in range(n_perm):
        hs = ns = 0
        for p, o in groups:
            a, b = hit_rate(p[block_order(len(p), block, rng)], o)
            hs, ns = hs + a, ns + b
        perm[i] = hs / ns if ns else -np.inf
    valid = perm[np.isfinite(perm)]
    eps = 1e-12
    return {"H": h_obs, "n": n, "hits": hits, "chance": float(valid.mean()) if len(valid) else None,
            "p": (1 + int((perm >= h_obs - eps).sum())) / (n_perm + 1),
            "p_low": (1 + int((perm <= h_obs + eps).sum())) / (n_perm + 1)}  # no prediction: H* < H, both tails


def holm(pvals: dict) -> dict:
    from ai_tracker.evaluation import holm as _holm

    return _holm(pvals)


def information_rows(rt: dict, cache: PathCache, end: str, branches) -> dict[int, list[dict]]:
    """Per horizon: one row per branch month in the window with the outcome and persistence per rule."""
    out: dict[int, list[dict]] = {}
    for h in HORIZONS:
        last = pd.Period(end, freq="M") - h
        rows = []
        for (code, month), rec in sorted(rt.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            if pd.Period(month, freq="M") > last:
                continue
            o, p = series_outcomes(cache, rec, h)
            row = {"branch": code, "month": month, "h": h, "n_series_outcome": sum(u is not None for _, u in o),
                   "n_families_outcome": len({f for f, u in o if u is not None})}
            for rule in RULES:
                row[f"outcome_{rule}"] = aggregate(o, rule)
                row[f"persistence_{rule}"] = aggregate(p, rule)
                for thr in THRESHOLDS:
                    row[f"pred_{rule}_{thr}"] = prediction(state(rec, rule, thr))
            rows.append(row)
        out[h] = rows
    return out


def _arrays(rows: list[dict], code: str, rule: str, thr: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    r = [x for x in rows if x["branch"] == code]
    r.sort(key=lambda x: x["month"])
    pred = np.array([x[f"pred_{rule}_{thr}"] for x in r], dtype=int)
    out = np.array([x[f"outcome_{rule}"] or 0 for x in r], dtype=int)
    pers = np.array([np.nan if x[f"persistence_{rule}"] is None else x[f"persistence_{rule}"] for x in r], dtype=float)
    return pred, out, pers


def _persistence_credit(pred: np.ndarray, out: np.ndarray, pers: np.ndarray, only_predicted: bool) -> tuple[float, int]:
    ok = (out != 0) & ((pred != 0) if only_predicted else True)
    c = np.where(np.isnan(pers[ok]), 0.5, (pers[ok] == out[ok]).astype(float))
    return float(c.sum()), int(ok.sum())


def information(rows: list[dict], rule: str, thr: str, branches, n_perm: int, with_test: bool = True) -> dict:
    """(b) for one rule, threshold pair and horizon: pooled test and per-branch description."""
    groups, per = [], {}
    for code in branches:
        pred, out, pers = _arrays(rows, code, rule, thr)
        if len(pred) == 0:
            continue
        groups.append((pred, out))
        hits, n = hit_rate(pred, out)
        ha, na = hit_rate(np.where(pred == 1, 1, 0), out)
        hb, nb = hit_rate(np.where(pred == -1, -1, 0), out)
        pc, pn = _persistence_credit(pred, out, pers, True)
        defined = out != 0
        per[code] = {"n": n, "hits": hits, "H": hits / n if n else None, "n_accel": na, "hits_accel": ha,
                     "n_brake": nb, "hits_brake": hb, "persistence_same": pc / pn if pn else None,
                     "n_outcomes": int(defined.sum()), "up_share": float((out[defined] == 1).mean()) if defined.any() else None,
                     "months": len(pred)}
    if with_test:
        res = permutation_test(groups, n_perm=n_perm)
    else:  # (c): hit rate and chance level only, no p-value
        hits = sum(v["hits"] for v in per.values())
        n = sum(v["n"] for v in per.values())
        res = {"H": hits / n if n else None, "n": n, "hits": hits, "chance": None}
        if n:
            res["chance"] = permutation_test(groups, n_perm=min(n_perm, 999))["chance"]
    pc = pn = pc_all = pn_all = 0.0
    for code in per:
        pred, out, pers = _arrays(rows, code, rule, thr)
        a, b = _persistence_credit(pred, out, pers, True)
        c, d = _persistence_credit(pred, out, pers, False)
        pc, pn, pc_all, pn_all = pc + a, pn + b, pc_all + c, pn_all + d
    res["persistence_same"] = pc / pn if pn else None
    res["persistence_all"] = pc_all / pn_all if pn_all else None
    res["n_outcomes_all"] = int(pn_all)
    res["n_accel"] = sum(v["n_accel"] for v in per.values())
    res["hits_accel"] = sum(v["hits_accel"] for v in per.values())
    res["n_brake"] = sum(v["n_brake"] for v in per.values())
    res["hits_brake"] = sum(v["hits_brake"] for v in per.values())
    if with_test and res["n"] < MIN_PRED:
        res["p"], res["p_low"], res["tested"] = 1.0, 1.0, False
    elif with_test:
        res["tested"] = True
    res["branches"] = per
    return res


def subperiod(rows: list[dict], rule: str, lo: str | None, hi: str | None) -> dict:
    r = [x for x in rows if (lo is None or x["month"] >= lo) and (hi is None or x["month"] <= hi)]
    pred = np.array([x[f"pred_{rule}_{REGISTERED}"] for x in r], dtype=int)
    out = np.array([x[f"outcome_{rule}"] or 0 for x in r], dtype=int)
    hits, n = hit_rate(pred, out)
    return {"n": n, "hits": hits, "H": hits / n if n else None}


# ------------------------------------------------------------------ (c) description


def shares(rt: dict, rule: str, thr: str, branches) -> dict:
    out = {}
    for code in [*branches, "alla"]:
        keys = [k for k in rt if code == "alla" or k[0] == code]
        st = [_category(state(rt[k], rule, thr)) for k in keys]
        n = len(st)
        out[code] = {"months": n, **{c: (st.count(c) / n if n else None) for c in (*REAL_STATES, FEW)},
                     "mean_series": float(np.mean([rt[k]["n_series"] for k in keys])) if keys else None,
                     "mean_families": float(np.mean([rt[k]["n_families"] for k in keys])) if keys else None}
    return out


def threshold_agreement(rt: dict, rule: str, thr: str) -> float:
    keys = list(rt)
    return sum(state(rt[k], rule, thr) == state(rt[k], rule, REGISTERED) for k in keys) / len(keys)


# ------------------------------------------------------------------ run and decision


def decision(a: dict, b: dict) -> dict:
    """The registered decision rule, applied mechanically to the v2 results."""
    pooled = a["v2"][REGISTERED]["pooled"]
    k, hf = pooled["kappa"], pooled["hard_flips"]
    a_review = k is None or k < KAPPA_MIN or (hf is not None and hf > HARD_FLIP_MAX)
    tests = {h: b["v2"][REGISTERED][h] for h in HORIZONS}
    not_above = all(t["H"] is None or t["H"] <= max(t["persistence_same"] or 0.0, t["chance"] or 0.0)
                    for t in tests.values())
    wrong = any(t["p_low_holm"] < ALPHA for t in tests.values())
    passed = [h for h, t in tests.items()
              if t["p_holm"] < ALPHA and t["H"] is not None and t["H"] > (t["persistence_same"] or 0.0)]
    reasons = []
    if a_review:
        reasons.append("(a) kappa eller hårda byten utanför registrerad nivå")
    if not_above:
        reasons.append("(b) träffkvoten är inte över den bättre baslinjen vid någon horisont")
    if wrong:
        reasons.append("(b) tillstånden pekar fel oftare än slumpen")
    return {"a_review": a_review, "b_not_above": not_above, "b_wrong": wrong, "b_passed_horizons": passed,
            "b_verdict": "godkänt" if passed else "inte avgjort", "review_recommended": bool(reasons),
            "reasons": reasons, "positive_result": bool(passed)}


def run(ctx: Context | None = None, start: str = START, end: str = END, vintage: str = VINTAGE,
        n_perm: int = N_PERM, branches=None) -> dict:
    """The whole registered evaluation. `ctx` defaults to the observation table (shared base plus the track's)."""
    ctx = ctx or Context(observations.load())
    branches = list(branches or catalog.BRANCHES)
    if pd.Timestamp(vintage) < month_end(end):
        raise ValueError(f"vintage {vintage} is before the last month end {month_end(end).date()}")
    months = list(pd.period_range(start, end, freq="M"))
    rt = records(ctx, months, branches)
    rctx = revised_context(ctx, vintage)
    rv = records(rctx, months, branches)
    exp = exposure(ctx, rctx, rt)
    gated = {name: sum(any(s["series"] in R.BACKFILL_GATED for s in rec["series"]) for rec in recs.values())
             for name, recs in (("realtime", rt), ("revised", rv))}
    a = {rule: {thr: revision_table(rt, rv, rule, thr, branches, exp if thr == REGISTERED else None)
                for thr in THRESHOLDS} for rule in RULES}

    cache = PathCache(ctx)
    rows = information_rows(rt, cache, end, branches)
    b: dict = {}
    for rule in RULES:
        b[rule] = {}
        for thr in THRESHOLDS:
            reg = thr == REGISTERED
            b[rule][thr] = {h: information(rows[h], rule, thr, branches, n_perm, with_test=reg) for h in HORIZONS}
        tests = b[rule][REGISTERED]
        ph = holm({h: tests[h]["p"] for h in HORIZONS})
        pl = holm({h: tests[h]["p_low"] for h in HORIZONS})
        for h in HORIZONS:
            tests[h]["p_holm"], tests[h]["p_low_holm"] = ph[h], pl[h]
    dev_next = str(pd.Period(DEV_END, freq="M") + 1)
    sub = {rule: {h: {"till " + DEV_END: subperiod(rows[h], rule, None, DEV_END),
                      "från " + dev_next: subperiod(rows[h], rule, dev_next, None)} for h in HORIZONS}
           for rule in RULES}
    c = {"shares": {rule: {thr: shares(rt, rule, thr, branches) for thr in THRESHOLDS} for rule in RULES},
         "threshold_agreement": {rule: {thr: threshold_agreement(rt, rule, thr) for thr in THRESHOLDS}
                                 for rule in RULES},
         "subperiods": sub}
    return {"label": LABEL, "start": start, "end": end, "vintage": vintage, "n_perm": n_perm, "block": BLOCK,
            "seed": SEED, "branches": branches, "gated_counted_months": gated, "a": a, "b": b, "c": c,
            "decision": decision(a, b), "rows": rows,
            "states": {f"{k[0]} {k[1]}": {"realtime_v2": rt[k]["state_v2"], "revised_v2": rv[k]["state_v2"],
                                          "realtime_v1": rt[k]["state_v1"], "revised_v1": rv[k]["state_v1"]}
                       for k in sorted(rt)}}


# ------------------------------------------------------------------ output


def _clean(x):
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, Fraction):
        return float(x)
    if isinstance(x, (np.integer, np.floating, np.bool_)):
        x = x.item()
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def _f(x, d: int = 2) -> str:
    return "–" if x is None else f"{x:.{d}f}".replace(".", ",")


def _pct(x) -> str:
    return "–" if x is None else f"{100 * x:.0f} %"


def markdown(res: dict) -> str:
    """Tables for docs/resultat/t1_tillstandsregeln.md (Swedish)."""
    L: list[str] = []
    br = res["branches"]
    for rule in RULES:
        a = res["a"][rule][REGISTERED]
        L += [f"#### (a) {rule}: realtid mot dagens data", "",
              "| Gren | Månader i S | Samma tillstånd | Kappa | Hårda byten | Ändrade | Medel abs. indexskillnad | "
              "Räknade serier med reviderade värden |", "|---|---|---|---|---|---|---|---|"]
        for code in [*br, "Alla"]:
            s = a["pooled"] if code == "Alla" else a["branches"][code]
            if code != "Alla" and s["n"] == 0:
                L.append(f"| {code} | 0 | – | – | – | – | – | {_pct(s.get('exposed_series_share'))} |")
                continue
            L.append(f"| {code} | {s['n']} | {_pct(s['agree'])} | {_f(s['kappa'])} | {s['n_hard']} "
                     f"({_pct(s['hard_flips'])}) | {s['n_changed']} | {_f(s['mean_abs_index_diff'], 3)} | "
                     f"{_pct(s.get('exposed_series_share'))} |")
        L.append("")
    for rule in RULES:
        L += [f"#### (b) {rule}: tillståndet vid m mot riktningen i takt till m + h", "",
              "| h | Prediktioner (acc./broms.) | Träffar | Träffkvot | Slumpnivå | Persistens samma månader | "
              "p | Holm-p | p_ned (Holm) |", "|---|---|---|---|---|---|---|---|---|"]
        for h in HORIZONS:
            t = res["b"][rule][REGISTERED][h]
            L.append(f"| {h} | {t['n']} ({t['n_accel']}/{t['n_brake']}) | {t['hits']} (acc. {t['hits_accel']}, "
                     f"broms. {t['hits_brake']}) | {_f(t['H'])} | {_f(t['chance'])} | {_f(t['persistence_same'])} | "
                     f"{_f(t['p'], 3)} | {_f(t['p_holm'], 3)} | {_f(t['p_low_holm'], 3)} |")
        L += ["", f"Per gren ({rule}):", "",
              "| Gren | h | Prediktioner | Träffkvot | Acc.: träffar/antal | Broms.: träffar/antal | "
              "Persistens samma månader | Andel upp i utfallen | Månader med utfall |",
              "|---|---|---|---|---|---|---|---|---|"]
        for code in br:
            for h in HORIZONS:
                v = res["b"][rule][REGISTERED][h]["branches"].get(code)
                if not v or (v["n"] == 0 and v["n_outcomes"] == 0):
                    continue
                L.append(f"| {code} | {h} | {v['n']} | {_f(v['H'])} | {v['hits_accel']}/{v['n_accel']} | "
                         f"{v['hits_brake']}/{v['n_brake']} | {_f(v['persistence_same'])} | {_pct(v['up_share'])} | "
                         f"{v['n_outcomes']} av {v['months']} |")
        L.append("")
    L += ["#### (c) Andel månader per tillstånd (realtid, 2024-01–2026-10)", "",
          "| Gren | v2 acc. | v2 stabil | v2 broms. | v2 för få källor | Familjer (medel) | v1 acc. | v1 stabil | "
          "v1 broms. | v1 för få serier | Serier (medel) |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    s2, s1 = res["c"]["shares"]["v2"][REGISTERED], res["c"]["shares"]["v1"][REGISTERED]
    for code in [*br, "alla"]:
        x, y = s2[code], s1[code]
        L.append(f"| {code if code != 'alla' else 'Alla'} | {_pct(x[R.STATE_ACCEL])} | {_pct(x[R.STATE_STABLE])} | "
                 f"{_pct(x[R.STATE_BRAKE])} | {_pct(x[FEW])} | {_f(x['mean_families'], 1)} | {_pct(y[R.STATE_ACCEL])} | "
                 f"{_pct(y[R.STATE_STABLE])} | {_pct(y[R.STATE_BRAKE])} | {_pct(y[FEW])} | {_f(y['mean_series'], 1)} |")
    L += ["", "#### (c) Andra trösklar (beskrivning, inga p-värden)", "",
          "| Regel | Trösklar | Acc. | Stabil | Broms. | Samma som 0,67/0,33 | (a) kappa | (a) hårda byten | "
          "(b) h = 3: träffkvot (slump) | (b) h = 6: träffkvot (slump) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for rule in RULES:
        for thr in THRESHOLDS:
            x = res["c"]["shares"][rule][thr]["alla"]
            a = res["a"][rule][thr]["pooled"]
            b3, b6 = res["b"][rule][thr][3], res["b"][rule][thr][6]
            L.append(f"| {rule} | {thr} | {_pct(x[R.STATE_ACCEL])} | {_pct(x[R.STATE_STABLE])} | {_pct(x[R.STATE_BRAKE])} "
                     f"| {_pct(res['c']['threshold_agreement'][rule][thr])} | {_f(a['kappa'])} | {a['n_hard']} | "
                     f"{_f(b3['H'])} ({_f(b3.get('chance'))}, n = {b3['n']}) | {_f(b6['H'])} ({_f(b6.get('chance'))}, "
                     f"n = {b6['n']}) |")
    L += ["", "#### (c) Delperioder i (b) (beskrivning)", "",
          "| Regel | h | Ursprung | Prediktioner | Träffkvot |", "|---|---|---|---|---|"]
    for rule in RULES:
        for h in HORIZONS:
            for name, v in res["c"]["subperiods"][rule][h].items():
                L.append(f"| {rule} | {h} | {name} | {v['n']} | {_f(v['H'])} |")
    d = res["decision"]
    L += ["", "#### Beslutsregeln, mekaniskt", "",
          f"- (a) granskning: {'ja' if d['a_review'] else 'nej'}",
          f"- (b) inte över den bättre baslinjen vid någon horisont: {'ja' if d['b_not_above'] else 'nej'}",
          f"- (b) pekar fel oftare än slumpen: {'ja' if d['b_wrong'] else 'nej'}",
          f"- (b) {d['b_verdict']}" + (f" (h = {', '.join(map(str, d['b_passed_horizons']))})"
                                      if d["b_passed_horizons"] else ""),
          f"- Granskning av regeln rekommenderas: {'ja' if d['review_recommended'] else 'nej'}"
          + (f" ({'; '.join(d['reasons'])})" if d["reasons"] else ""), ""]
    return "\n".join(L)


def run_log_rows(res: dict) -> list[dict]:
    """Rows for evaluation.log_run: one per registered test (MAE empty; dm_p_vs_baseline holds the permutation p)."""
    out = []
    for rule in RULES:
        for h in HORIZONS:
            t = res["b"][rule][REGISTERED][h]
            last = str(pd.Period(res["end"], freq="M") - h)
            out.append({"target": f"T1 state {rule}", "variant": f"h{h} hit={_f(t['H'], 3)} chance={_f(t['chance'], 3)} "
                                                                 f"pers={_f(t['persistence_same'], 3)} holm={_f(t['p_holm'], 3)}",
                        "period": f"{res['start']}..{last}", "n": t["n"], "MAE": "", "dm_p_vs_baseline": t["p"]})
        a = res["a"][rule][REGISTERED]["pooled"]
        out.append({"target": f"T1 state {rule}", "variant": f"revision kappa={_f(a['kappa'], 3)} "
                                                             f"hard={_f(a['hard_flips'], 3)} agree={_f(a['agree'], 3)}",
                    "period": f"{res['start']}..{res['end']}", "n": a["n"], "MAE": "", "dm_p_vs_baseline": ""})
    return out
