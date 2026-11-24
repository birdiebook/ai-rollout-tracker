"""Shared rolling-origin backtest and live forecast for the quarterly step-2 targets N3, N4 and N6.

Registered in docs/mattregister.md, "Steg 2", G-B, with the amendment "C0 preciseras efter granskning R6", which
adopts docs/granskning/r6_c0.md verbatim. The engine contract (engine.py) is unchanged: every input is read with
as_of(origin), the outcome is the target's first vintage, and a quarter whose first vintage is known on or before its
origin is never scored.

Implemented here, as registered:
- B0: last known quarter. B1: last quarter x exp(mean of the last 4 q/q log growth rates), all as_of(origin).
- Regression variant (N4 V1, N6 V1; F-B6, F-B7): B1 x exp(r_hat / 100), r_hat from an expanding OLS of B1's miss
  r_s = 100 * (log outcome_s - log B1_s) on a constant and x_s, x = the latest q/q log growth x 100 of the regressor
  sum known at the row's own origin. A training row s < q needs B1_s and x_s (each as of origin_s) and its first-vintage
  outcome known at origin_q. Minimum 12 complete rows (F-B4).
- Target-specific variants (N3 B2) through `Spec.extra`.
- Definition breaks (F-B8): a quarter q of a component is a break when the filing of q's first version restates an
  earlier quarter of that component by more than 2 %. A break quarter is not scored (and is no training row), and B1's
  window (q-4..q-1, the four growth rates) may not contain a break known at the origin (its filing on or before it).
- Evaluation (F-B4): from the first quarter where every implemented registered variant can be formed (a regression
  variant with >= 12 rows); B0 and B1 on the same quarters (common sample). Subperiod from 2023Q1.
- Test (F-B9, F-B10, F-B11): DM (absolute loss, Newey-West, HLN) of each variant against the comparator = the best of
  B0 and B1 by MAE in the period (B1 is the current main model, and the registered variants here build on B1 or on
  nothing). Holm within the target's step-2 family, a member not evaluated in this run (B3: track C2, DF: track C3)
  enters with p = 1. Promotion: Holm-p < 0.10 and lower MAE than the comparator in the full period and from 2023Q1.
  A passing variant in REVIEW_REQUIRED is only a conditional promotion. Default champion B1 (register section 3,
  "annars blir B1 huvudmodell", unchanged in G-B).

Fixed here where the register is silent (documented in docs/resultat/n3.md ... n6.md):
- A training row whose own outcome was known at its own origin (a forecast of a known number) is not used.
- A regressor growth that spans a break of one of the regressor's components is not used (x missing).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from ai_tracker import evaluation, observations
from ai_tracker.nowcast import engine, intervals
from ai_tracker.sources import sec

Q = "Q-DEC"
SUBPERIOD = pd.Period("2023Q1", freq=Q)
MIN_TRAIN = 12  # F-B4: complete training rows for a regression variant
BREAK_TOL = 0.02  # F-B8: a restated comparative more than 2 % off is a definition break
BASELINES = ("B0", "B1")
DEFAULT_CHAMPION = "B1"
HOLDOUT_START = pd.Timestamp("2025-07-01")  # G-E (informational counts only; simple variants use the full period)
DEV_END = pd.Timestamp("2025-06-30")


class NotAvailable(Exception):
    """The forecast (or a variant) cannot be formed from the information set."""


@dataclass(frozen=True)
class Aggregate:
    """A target or regressor: a table series (`components` empty) or the sum of components (derived here)."""

    key: str
    components: tuple[str, ...] = ()


@dataclass
class Spec:
    nowcast: str  # "n3"
    label: str  # "N3"
    target: Aggregate
    origin_for: Callable[[pd.Period], pd.Timestamp]
    target_quarter: Callable[[pd.Timestamp], pd.Period]
    variants: list[str]  # implemented here, in display order
    models: list[str]  # implemented non-baseline variants (tested)
    family: list[str]  # the registered step-2 Holm family (F-B9), implemented or not
    review_required: dict[str, str]
    regressor: Aggregate | None = None  # for the regression variant "V1"
    extra: Callable | None = None  # extra(info, quarter, rec) -> None; sets rec.levels / rec.reasons / rec.notes
    inputs: tuple[str, ...] = ()  # other table series the extra variant reads
    unit: str = "MUSD"
    champion: str = DEFAULT_CHAMPION
    quarter_notes: Callable[[pd.Period], str] | None = None  # e.g. N3's 14-week quarters

    def series(self) -> list[str]:
        keys = [self.target.key, *self.target.components, *self.inputs]
        if self.regressor:
            keys += [self.regressor.key, *self.regressor.components]
        return list(dict.fromkeys(keys))


# ------------------------------------------------------------------ data


def aggregate_rows(table: pd.DataFrame, agg: Aggregate) -> pd.DataFrame:
    """Vintages of the component sum (sec.aggregate: a quarter exists once every component has it, dated by the
    latest filing used, a new version whenever a component changes), without gaps (sec.contiguous_tail)."""
    frames = {}
    for c in agg.components:
        t = table[table["series"] == c]
        if t.empty:
            return observations._empty()
        frames[c] = t[["period", "value", "known_from"]]
    df = sec.contiguous_tail(sec.aggregate(frames))
    if df.empty:
        return observations._empty()
    return pd.DataFrame({"series": agg.key, "freq": "Q", "period": df["period"].astype(str),
                         "value": df["value"].astype(float), "known_from": pd.to_datetime(df["known_from"]),
                         "source": "derived", "fetched_at": pd.NaT})


def prepare(table: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    """The rows the target needs, with every component sum rebuilt from its components (rows of the same key that
    already exist, e.g. the catalog's rpo_hyp4, are replaced by the identical rebuild)."""
    keys = spec.series()
    t = table[table["series"].isin(keys)]
    for agg in (spec.target, spec.regressor):
        if agg is not None and agg.components:
            t = pd.concat([t[t["series"] != agg.key], aggregate_rows(t, agg)], ignore_index=True)
    return t


def breaks_of(table: pd.DataFrame, series: str, tol: float = BREAK_TOL) -> dict[pd.Period, tuple]:
    """F-B8: quarters q of `series` whose first-version filing restates an earlier quarter by more than `tol`, as
    q -> (filing date, description). The filing date is when the break becomes known."""
    t = table[table["series"] == series]
    if t.empty:
        return {}
    t = t.assign(p=observations.to_periods(t["period"], "Q")).sort_values("known_from")
    first = t.groupby("p")["known_from"].min()
    out = {}
    for q, d in first.items():
        earlier = t[t["p"] < q]
        before = earlier[earlier["known_from"] < d].groupby("p")["value"].last()
        at = earlier[earlier["known_from"] <= d].groupby("p")["value"].last()
        common = before.index.intersection(at.index)
        rel = (at[common] / before[common] - 1).abs()
        if len(rel) and rel.max() > tol:
            p = rel.idxmax()
            out[q] = (pd.Timestamp(d),
                      f"{series}: filing {d.date()} restates {p} by {100 * float(at[p] / before[p] - 1):+.1f} %")
    return out


def breaks(table: pd.DataFrame, agg: Aggregate) -> dict[pd.Period, tuple]:
    """Breaks of any component: q -> (earliest filing date that shows a break in q, description)."""
    out: dict[pd.Period, tuple] = {}
    for s in agg.components or (agg.key,):
        for q, (d, why) in breaks_of(table, s).items():
            out[q] = (min(d, out[q][0]), f"{out[q][1]}; {why}") if q in out else (d, why)
    return out


def known_breaks(brk: dict, origin) -> dict:
    """The breaks known at `origin` (their filing on or before it)."""
    return {q: v for q, v in brk.items() if v[0] <= pd.Timestamp(origin)}


def latest_growth(info: engine.InfoSet, agg: Aggregate, brk: dict) -> tuple[float, str | None]:
    """100 x q/q log growth of the latest quarter L of `agg` known at the origin (L vs L-1), and L."""
    r = info.get(agg.key)
    r = r[r > 0]
    if len(r) < 2:
        return float("nan"), None
    L = r.index.max()
    if L - 1 not in r.index or L in known_breaks(brk, info.origin):
        return float("nan"), str(L)
    info.mark(agg.key, [L - 1, L])
    return float(100 * (math.log(r[L]) - math.log(r[L - 1]))), str(L)


# ------------------------------------------------------------------ one quarter


@dataclass
class Record:
    quarter: pd.Period
    origin: pd.Timestamp
    info: engine.InfoSet
    levels: dict = field(default_factory=dict)  # variant -> level (NaN = not available)
    reasons: dict = field(default_factory=dict)
    notes: dict = field(default_factory=dict)  # diagnostics (sources, shares, known components)
    x: float = float("nan")  # regressor growth known at the origin
    x_period: str | None = None
    n_train: int = 0
    coef: list = field(default_factory=list)


def b0_b1(y: pd.Series, q: pd.Period, brk: dict) -> tuple[float, float, str | None]:
    """B0 and B1 for quarter q from the as-of history y (periods < q). B1 NaN (with the reason) when the 4 growth
    rates are not all known or the window crosses a definition break."""
    if q - 1 not in y.index:
        raise NotAvailable(f"{q - 1} not known at the origin")
    b0 = float(y[q - 1])
    window = pd.period_range(q - 5, q - 1, freq=Q)
    if any(p not in y.index for p in window) or (y.reindex(window) <= 0).any():
        return b0, float("nan"), "B1: 4 growth rates before the quarter not all known"
    crossing = [str(p) for p in window[1:] if p in brk]
    if crossing:
        return b0, float("nan"), f"B1: window crosses a definition break ({', '.join(crossing)})"
    g = np.diff(np.log(y.reindex(window).to_numpy(dtype=float)))
    return b0, float(b0 * math.exp(g.mean())), None


def record(table: pd.DataFrame, spec: Spec, q: pd.Period, brk: dict, rbrk: dict, origin=None) -> Record:
    origin = pd.Timestamp(origin if origin is not None else spec.origin_for(q))
    info = engine.InfoSet(table, origin)
    rec = Record(q, origin, info)
    y = info.get(spec.target.key)
    if q in y.index:
        raise NotAvailable(f"{spec.target.key} {q} is already known at {origin.date()}: no nowcast")
    y = y[y.index < q]
    b0, b1, why = b0_b1(y, q, known_breaks(brk, origin))
    rec.levels["B0"], rec.levels["B1"] = b0, b1
    info.mark(spec.target.key, [q - 1])
    if why:
        rec.reasons["B1"] = why
    else:
        info.mark(spec.target.key, list(pd.period_range(q - 5, q - 1, freq=Q)))
    if spec.target.components:  # F-B8: how many components of q were already filed at the origin
        rec.notes["components_known"] = [c for c in spec.target.components if q in info.get(c).index]
    if spec.regressor is not None:
        rec.x, rec.x_period = latest_growth(info, spec.regressor, rbrk)
    if spec.extra is not None:
        spec.extra(info, q, rec)
    return rec


def regression(rec: Record, train: list[Record], outcomes: pd.DataFrame) -> None:
    """V1 for `rec` from earlier records (F-B6, F-B7); sets rec.levels["V1"] or the reason."""
    rec.levels["V1"] = float("nan")
    if math.isnan(rec.levels["B1"]) or math.isnan(rec.x):
        rec.reasons["V1"] = "V1: B1 or the regressor growth not available at the origin"
        return
    rows = []
    for s in train:
        if s.quarter >= rec.quarter or s.quarter not in outcomes.index:
            continue
        kf = outcomes.at[s.quarter, "known_from"]
        if kf > rec.origin or kf <= s.origin:  # outcome not yet known / was known at the row's own origin
            continue
        if math.isnan(s.levels.get("B1", float("nan"))) or math.isnan(s.x):
            continue
        rows.append((s.x, 100 * (math.log(outcomes.at[s.quarter, "value"]) - math.log(s.levels["B1"]))))
    rec.n_train = len(rows)
    if len(rows) < MIN_TRAIN:
        rec.reasons["V1"] = f"V1: {len(rows)} training rows < {MIN_TRAIN}"
        return
    X = np.array([r[0] for r in rows])
    r = np.array([r[1] for r in rows])
    A = np.column_stack([np.ones(len(r)), X])
    coef, *_ = np.linalg.lstsq(A, r, rcond=None)
    rec.coef = [float(c) for c in coef]
    rec.levels["V1"] = float(rec.levels["B1"] * math.exp((coef[0] + coef[1] * rec.x) / 100))


# ------------------------------------------------------------------ backtest


def run(table: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    """One row per quarter with B0 (errors per variant, 100 * log forecast/outcome), from the first-vintage outcomes.
    attrs: known_at_origin (skipped, never scored), breaks (not scored), start (F-B4)."""
    t = prepare(table, spec)
    outcomes = engine.first_vintages(t, spec.target.key)
    brk = breaks(t, spec.target)
    rbrk = breaks(t, spec.regressor) if spec.regressor else {}
    recs, rows, known, skipped = {}, [], [], []
    for q in outcomes.index:
        note = engine.known_at_origin(outcomes, q, spec.origin_for(q), f"{spec.target.key} {q}")
        if note:  # filed on or before the origin: a forecast of a known number is never scored (nor a training row)
            known.append(note)
            continue
        try:
            recs[q] = record(t, spec, q, brk, rbrk)
        except NotAvailable:
            continue
    for q, rec in recs.items():
        if q in brk:
            skipped.append(f"{q}: {brk[q][1]}")
            continue
        if "V1" in spec.variants:  # a break quarter is not scored and is no training row either
            regression(rec, [s for s in recs.values() if s.quarter not in brk], outcomes)
        y = float(outcomes.at[q, "value"])
        row = {"quarter": q, "origin": rec.origin, "outcome": y, "outcome_known_from": outcomes.at[q, "known_from"],
               "n_train": rec.n_train, "x": rec.x, "x_period": rec.x_period,
               "reason": "; ".join(sorted(set(rec.reasons.values()))),
               "components_known": len(rec.notes.get("components_known", [])),
               "note": spec.quarter_notes(q) if spec.quarter_notes else "",
               **{k: v for k, v in rec.notes.items() if k != "components_known"}}
        for v in spec.variants:
            lv = rec.levels.get(v, float("nan"))
            row[v] = engine.log_error(lv, y) if lv is not None and np.isfinite(lv) and lv > 0 else float("nan")
        rows.append(row)
    df = pd.DataFrame(rows)
    df.attrs.update(known_at_origin=known, breaks=skipped)
    if df.empty:
        df.attrs["start"] = None
        df["in_period"] = []
        return df
    ok = df[list(spec.variants)].notna().all(axis=1)
    if "b2_source" in df:  # F-B4: B2 "can be formed" = formed from guidance, not its B1 fallback
        ok &= df["b2_source"].astype(str).str.startswith("guidance")
    start = df.loc[ok, "quarter"].min() if ok.any() else None
    df.attrs["start"] = start
    df["in_period"] = (df["quarter"] >= start) if start is not None else False
    return df


def _holm_family(p: dict, family: list[str]) -> dict:
    """Holm over the registered family; members without a p-value here (not evaluated in this run) get p = 1."""
    return evaluation.holm({v: (p[v] if v in p and not math.isnan(p[v]) else 1.0) for v in family})


def evaluate(frame: pd.DataFrame, spec: Spec) -> dict:
    """Metrics, DM against the comparator, Holm in the family and MDE, for the full period and from 2023Q1."""
    res = {}
    if frame.empty:
        return {"full": {"n": 0, "excluded": []}, "2023Q1-": {"n": 0, "excluded": []}}
    for name, mask in (("full", frame["in_period"]), ("2023Q1-", frame["in_period"] & (frame["quarter"] >= SUBPERIOD))):
        e = frame[mask]
        common = e.dropna(subset=spec.variants)
        excluded = sorted(str(q) for q in e.loc[~e.index.isin(common.index), "quarter"])
        if len(common) < 3:
            res[name] = {"n": len(common), "excluded": excluded}
            continue
        m = {v: engine.summary(common[v]) for v in spec.variants}
        comp = engine.best_baseline({b: m[b]["MAE"] for b in BASELINES}, BASELINES)
        dm = {v: evaluation.dm_test(common[v].to_numpy(), common[comp].to_numpy()) for v in spec.models}
        other = [b for b in BASELINES if b != comp][0]
        dm_base = evaluation.dm_test(common[other].to_numpy(), common[comp].to_numpy())
        holm = _holm_family({v: dm[v].p for v in spec.models}, spec.family)
        res[name] = {
            "n": len(common), "first": str(common["quarter"].min()), "last": str(common["quarter"].max()),
            "excluded": excluded, "metrics": m, "comparator": comp,
            "dm": {v: {"mean_diff": dm[v].mean_diff, "p": dm[v].p, "holm_p": holm[v], "mde": dm[v].mde,
                       "lag": dm[v].lag, "n": dm[v].n} for v in spec.models},
            "dm_baseline": {"variant": other, "mean_diff": dm_base.mean_diff, "p": dm_base.p, "mde": dm_base.mde},
            "holm_family": holm,
        }
    return res


def promotion(res: dict, spec: Spec) -> dict:
    """F-B10, F-B11: Holm-p < 0.10 and lower MAE than the comparator in both periods. REVIEW_REQUIRED: conditional."""
    checks = {}
    for v in spec.models:
        c = {}
        for per in ("full", "2023Q1-"):
            r = res.get(per, {})
            if "metrics" not in r:
                c[per] = {"mae_ok": False, "holm_ok": False, "note": "too few quarters"}
                continue
            c[per] = engine.period_check(r["metrics"][v]["MAE"], r["metrics"][r["comparator"]]["MAE"],
                                         r["dm"][v]["holm_p"], engine.PROMOTION_ALPHA)
        c["promoted"] = engine.passes({p: c[p] for p in ("full", "2023Q1-")})
        checks[v] = c
    mae = {v: res["full"]["metrics"][v]["MAE"] for v in spec.models if "metrics" in res.get("full", {})}
    d = engine.decide({v: checks[v]["promoted"] for v in mae}, mae, spec.review_required, DEFAULT_CHAMPION)
    return {"champion": d.champion, "checks": checks, "conditional": d.conditional}


def holdout_counts(frame: pd.DataFrame, first_live: pd.Timestamp) -> dict:
    """Informational (G-E, F-E1, F-E2): evaluated quarters in development (origin and outcome <= 2025-06-30), holdout
    (origin 2025-07-01 .. the day before the target's first live origin) and neither."""
    e = frame[frame["in_period"]]
    o, k = pd.to_datetime(e["origin"]), pd.to_datetime(e["outcome_known_from"])
    dev = (o <= DEV_END) & (k <= DEV_END)
    hold = (o >= HOLDOUT_START) & (o < first_live)
    return {"development": int(dev.sum()), "holdout": int(hold.sum()), "neither": int((~dev & ~hold).sum())}


# ------------------------------------------------------------------ intervals (G-C)


def interval_scores(frame: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    """Rolling-origin error distributions on every backtest row (also before the evaluation start); an error enters a
    pool only from its outcome's first-vintage known_from."""
    if frame.empty:
        return pd.DataFrame()
    e = frame.set_index("quarter")
    return intervals.score_frame(e[spec.variants], pd.to_datetime(e["origin"]), e["outcome_known_from"])


def evaluate_intervals(frame: pd.DataFrame, spec: Spec) -> dict:
    scored = interval_scores(frame, spec)
    sub = scored[scored["period"] >= SUBPERIOD] if len(scored) else scored
    return {"full": intervals.evaluate(scored, spec.variants, BASELINES),
            "2023Q1-": intervals.evaluate(sub, spec.variants, BASELINES)}


# ------------------------------------------------------------------ report


def backtest(table: pd.DataFrame, spec: Spec, log: bool = True, first_live: pd.Timestamp | None = None) -> dict:
    frame = run(table, spec)
    res = evaluate(frame, spec)
    out = {"frame": frame, "eval": res, "promotion": promotion(res, spec)}
    if intervals.ENABLED and not frame.empty:
        out["intervals"] = evaluate_intervals(frame, spec)
    if first_live is not None and not frame.empty:
        out["holdout"] = holdout_counts(frame, first_live)
    if log:
        rows = []
        for per, r in res.items():
            if "metrics" not in r:
                continue
            for v in spec.variants:
                rows.append({"target": spec.target.key, "variant": v, "period": f"{per} {r['first']}..{r['last']}",
                             "n": r["metrics"][v]["n"], "MAE": round(r["metrics"][v]["MAE"], 4),
                             "dm_p_vs_baseline": round(r["dm"][v]["p"], 4) if v in r["dm"] else ""})
        out["log"] = evaluation.log_run(f"{spec.nowcast}_backtest", rows)
    return out


def _f(x, nd=2) -> str:
    return "" if x is None or (isinstance(x, float) and not math.isfinite(x)) else f"{x:.{nd}f}"


def format_report(out: dict, spec: Spec) -> str:
    frame, lines = out["frame"], []
    lines.append(f"{spec.label} {spec.target.key}: {len(frame)} scored quarters "
                 f"({frame['quarter'].min() if len(frame) else '-'}..{frame['quarter'].max() if len(frame) else '-'}), "
                 f"evaluation start (F-B4) {frame.attrs.get('start')}")
    lines.append(f"known at origin (not scored): {frame.attrs.get('known_at_origin') or '-'}")
    lines.append(f"definition breaks (not scored): {frame.attrs.get('breaks') or '-'}")
    for per, r in out["eval"].items():
        if "metrics" not in r:
            lines.append(f"\n{per}: n={r['n']} (too few quarters)")
            continue
        lines.append(f"\n{per}: {r['first']}..{r['last']}, n={r['n']}, comparator {r['comparator']}, "
                     f"excluded {r['excluded'] or '-'}")
        lines.append(f"{'variant':8s}{'n':>4s}{'MAE':>8s}{'RMSE':>8s}{'bias':>8s}{'dMAE':>8s}{'DM p':>8s}{'Holm':>8s}"
                     f"{'MDE':>7s}")
        for v in spec.variants:
            m = r["metrics"][v]
            tail = ""
            if v in r["dm"]:
                d = r["dm"][v]
                tail = f"{d['mean_diff']:8.2f}{d['p']:8.3f}{d['holm_p']:8.3f}{d['mde']:7.2f}"
            elif v != r["comparator"]:
                d = r["dm_baseline"]
                tail = f"{d['mean_diff']:8.2f}{d['p']:8.3f}{'':>8s}{d['mde']:7.2f}"
            lines.append(f"{v:8s}{m['n']:4d}{m['MAE']:8.2f}{m['RMSE']:8.2f}{m['bias']:8.2f}{tail}")
        lines.append(f"Holm family {spec.family} (not evaluated here: p = 1): "
                     + ", ".join(f"{k} {_f(v, 3)}" for k, v in r["holm_family"].items()))
    p = out["promotion"]
    lines.append(f"\npromotion: champion {p['champion']}; "
                 + "; ".join(f"{v}: passes={c['promoted']} (full MAE ok {c['full']['mae_ok']}, Holm ok "
                             f"{c['full'].get('holm_ok')}; 2023Q1- MAE ok {c['2023Q1-']['mae_ok']}, Holm ok "
                             f"{c['2023Q1-'].get('holm_ok')})" for v, c in p["checks"].items())
                 + f"; conditional: {p['conditional'] or '-'}")
    if "holdout" in out:
        lines.append(f"G-E membership of the evaluated quarters (informational): {out['holdout']}")
    for per, r in (out.get("intervals") or {}).items():
        lines.append("\n" + intervals.markdown(r, f"{spec.label} intervals {per}"))
    return "\n".join(lines)


def markdown_table(res: dict, spec: Spec) -> str:
    """Swedish results table for docs/resultat (decimal comma)."""
    def c(x, nd=2, signed=False):
        if x is None or (isinstance(x, float) and not math.isfinite(x)):
            return "–"
        return (f"{x:+.{nd}f}" if signed else f"{x:.{nd}f}").replace(".", ",").replace("-", "−")
    lines = ["| Period | Variant | n | MAE | RMSE | Bias | MAE-skillnad mot jämförelsemodellen | DM p | Holm-p | MDE |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for per, r in res.items():
        if "metrics" not in r:
            continue
        for v in spec.variants:
            m = r["metrics"][v]
            name = f"**{v}**" if v == r["comparator"] else v
            if v in r["dm"]:
                d = r["dm"][v]
                tail = f"{c(d['mean_diff'], 2, True)} | {c(d['p'], 3)} | {c(d['holm_p'], 3)} | {c(d['mde'])}"
            elif v != r["comparator"]:
                d = r["dm_baseline"]
                tail = f"{c(d['mean_diff'], 2, True)} | {c(d['p'], 3)} | – | {c(d['mde'])}"
            else:
                tail = "– | – | – | –"
            lines.append(f"| {r['first']} – {r['last']} | {name} | {m['n']} | {c(m['MAE'])} | {c(m['RMSE'])} | "
                         f"{c(m['bias'], 2, True)} | {tail} |")
    return "\n".join(lines)


# ------------------------------------------------------------------ live


def live_forecast(table: pd.DataFrame, spec: Spec, origin) -> tuple[Record, pd.DataFrame]:
    """The forecast for the quarter of `origin` from rows known at the origin only (the table is truncated first)."""
    origin = pd.Timestamp(origin)
    q = spec.target_quarter(origin)
    if spec.origin_for(q) != origin:
        raise ValueError(f"{spec.label}: {origin.date()} is not the registered origin for {q} "
                         f"({spec.origin_for(q).date()})")
    t = prepare(table[table["known_from"] <= origin], spec)
    brk = breaks(t, spec.target)
    rbrk = breaks(t, spec.regressor) if spec.regressor else {}
    rec = record(t, spec, q, brk, rbrk, origin)
    if q in brk:  # cannot be known before the outcome is filed; kept for completeness
        raise NotAvailable(f"{q} is a definition break")
    if "V1" in spec.variants:
        outcomes = engine.first_vintages(t, spec.target.key)
        train = []
        for s in outcomes.index:
            if s >= q:
                continue
            try:
                train.append(record(t, spec, s, brk, rbrk))
            except NotAvailable:
                continue
        regression(rec, [s for s in train if s.quarter not in brk], outcomes)
    return rec, t


def live_distribution(table: pd.DataFrame, spec: Spec, origin, levels: dict, live_dir=None) -> dict:
    """G-C, F-C4: pools from the backtest reconstruction on the rows known at the origin plus the committed live
    forecasts whose outcome is known at the origin (a live error replaces the reconstruction of its quarter)."""
    origin = pd.Timestamp(origin)
    t = table[table["known_from"] <= origin]
    frame = run(t, spec)
    errors = (frame.set_index("quarter")[spec.variants] if len(frame)
              else pd.DataFrame(columns=spec.variants, index=pd.PeriodIndex([], freq=Q)))
    kf = frame.set_index("quarter")["outcome_known_from"] if len(frame) else pd.Series(dtype="datetime64[ns]")
    files = sorted(Path(live_dir).glob("*.json")) if live_dir else []
    outcomes = engine.first_vintages(prepare(t, spec), spec.target.key)
    live, live_kf = intervals.live_errors(files, outcomes, spec.variants, origin)
    e, known = intervals.merge_live(errors, kf, live, live_kf)
    logs = {v: (100 * math.log(x) if x is not None and np.isfinite(x) and x > 0 else float("nan"))
            for v, x in levels.items()}
    return intervals.live_block(logs, e, known, origin, live_index=live.index)


def live_payload(table: pd.DataFrame, spec: Spec, origin, live_dir=None) -> dict:
    origin = pd.Timestamp(origin)
    rec, t = live_forecast(table, spec, origin)
    levels = {v: rec.levels.get(v, float("nan")) for v in spec.variants}
    champion, note = spec.champion, ""
    if not np.isfinite(levels.get(champion, float("nan"))):
        note = f"champion {champion} not available ({rec.reasons.get(champion)}); fell back to B0"
        champion = "B0"
    extra = {"distribution": live_distribution(table, spec, origin, levels, live_dir)} if intervals.ENABLED else {}
    return {
        "nowcast": spec.label, "target": spec.target.key, "components": list(spec.target.components),
        "quarter": str(rec.quarter), "origin": origin.date().isoformat(), "registered_origin": True,
        "unit": spec.unit, "champion": champion, "value": levels[champion],
        "variants": {v: (None if not np.isfinite(x) else float(x)) for v, x in levels.items()},
        "unavailable": rec.reasons, "review_required": spec.review_required,
        "n_train_v1": rec.n_train if "V1" in spec.variants else None,
        "ols_coef_v1": rec.coef if "V1" in spec.variants else None,
        "regressor_growth": None if not np.isfinite(rec.x) else rec.x, "regressor_period": rec.x_period,
        "notes": {k: v for k, v in rec.notes.items()}, "note": note,
        "inputs": rec.info.inputs(),
        **extra,
    }


def write_live(table: pd.DataFrame, spec: Spec, origin, out_dir, today=None) -> Path:
    """forecasts/<nowcast>/<quarter>.json, written once (engine.write_live: refuses a future origin and an existing
    file before anything is computed)."""
    origin = pd.Timestamp(origin)
    path = Path(out_dir) / f"{spec.target_quarter(origin)}.json"
    return engine.write_live(path, origin, lambda: live_payload(table, spec, origin, live_dir=Path(out_dir)), today)
