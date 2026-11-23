"""N5: share of US firms using AI (Census BTOS), the active wording regime (docs/mattregister.md "Steg 2", G-B, with
R6's F-B4 and F-B8b adopted verbatim). Errors in percentage points: e = forecast - outcome.

    python -m ai_tracker.nowcast backtest n5
    python -m ai_tracker.nowcast n5 --origin YYYY-MM-DD      live forecast -> forecasts/n5/<collection end>.json

Registered (F-B8b)
- Target: every publication in the active regime (biweekly, not aggregated to months), first version. One series per
  wording regime (btos_ai_use_v1, _v2, _v3); observations are never combined across regimes.
- B0 = y(t-1). B1 = y(t-1) + (y(t-1) - y(t-7)) / 6, t-k = the k-th earlier publication in the same regime. Both need
  every observation in the same regime.
- Backtest origin = known_from of the target's first version - 1 day (the actual publication). The forecast needs the
  previous publication to be known at the origin. B0 and B1 only read the series itself, so this origin is free of
  leakage (F-B8b).
- Evaluation (F-B4): from the first publication in a regime with 7 earlier observations in that regime. Subperiod
  from 2023-01 (all of BTOS's AI series is later, so it equals the full period).
- Main model without variants: B1. No Holm family, no promotion question.

Live origin: the day before the *scheduled* publication, from the schedule census_btos logs at every fetch
(data/raw/census_btos/schedule_log.parquet), as known on the origin (the latest log entry fetched on or before it).
No logged schedule, a scheduled date inside a federal funding lapse, or a cycle outside every reviewed wording regime:
no forecast (refused, never guessed).

Fixed here where the register is silent (docs/resultat/n5.md): the interval pool (G-C) of a model is its past errors
over all regimes (the model is the same rule); periods are the W-SUN week of the collection end, as in the table.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ai_tracker import evaluation, observations
from ai_tracker.nowcast import engine, intervals
from ai_tracker.sources import census_btos

VERSIONS = [r.version for r in census_btos.REGIMES]
PREFIX = "btos_ai_use_"
VARIANTS = ["B0", "B1"]
BASELINES = ("B0", "B1")
CHAMPION = "B1"  # F-B8b: "Huvudmodell utan varianter: B1"
LAGS = 7  # B1 needs y(t-1) and y(t-7)
SUBPERIOD = pd.Timestamp("2023-01-01")
DEV_END = pd.Timestamp("2025-06-30")
HOLDOUT_START = pd.Timestamp("2025-07-01")
UNIT = "procentenheter"


class NotAvailable(Exception):
    pass


def key(version: str) -> str:
    return f"{PREFIX}{version}"


def forecast_levels(y: pd.Series, target: pd.Period) -> tuple[dict, dict]:
    """B0 and B1 (percent) for `target` from the as-of series y of one regime. Raises NotAvailable without the
    previous publication."""
    prev = y[y.index < target]
    if prev.empty:
        raise NotAvailable(f"no earlier publication of the regime known before {target}")
    levels, reasons = {"B0": float(prev.iloc[-1])}, {}
    if len(prev) >= LAGS:
        levels["B1"] = float(prev.iloc[-1] + (prev.iloc[-1] - prev.iloc[-LAGS]) / 6)
    else:
        levels["B1"] = float("nan")
        reasons["B1"] = f"B1: {len(prev)} earlier observations in the regime < {LAGS}"
    return levels, reasons


def run(table: pd.DataFrame) -> pd.DataFrame:
    """One row per publication with a forecast: errors (pp) per variant, origin = first known_from - 1 day."""
    rows = []
    for v in VERSIONS:
        k = key(v)
        rows_v = table[table["series"] == k]
        if rows_v.empty:
            continue
        out = engine.first_vintages(table, k)
        for i, p in enumerate(out.index):
            origin = pd.Timestamp(out.at[p, "known_from"]).normalize() - pd.Timedelta(days=1)
            if engine.known_at_origin(out, p, origin, f"{k} {p}"):
                continue  # cannot happen with this origin; the guard is kept
            y = observations.as_of(k, origin, rows_v)
            if i == 0 or out.index[i - 1] not in y.index:  # F-B8b: previous publication known at the origin
                continue
            levels, reasons = forecast_levels(y, p)
            outcome = float(out.at[p, "value"])
            rows.append({"period": p, "regime": v, "series": k, "origin": origin,
                         "outcome": outcome, "outcome_known_from": out.at[p, "known_from"],
                         "n_regime": int((y.index < p).sum()), "reason": "; ".join(reasons.values()),
                         **{m: (levels[m] - outcome if np.isfinite(levels[m]) else float("nan")) for m in VARIANTS}})
    df = pd.DataFrame(rows)
    if df.empty:
        df["in_period"] = []
        return df
    df = df.sort_values("origin", ignore_index=True)
    df["in_period"] = df["n_regime"] >= LAGS  # F-B4
    return df


def evaluate(frame: pd.DataFrame) -> dict:
    res = {}
    for name, mask in (("full", frame["in_period"]),
                       ("2023-01-", frame["in_period"] & (frame["period"].map(lambda p: p.start_time) >= SUBPERIOD))):
        e = frame[mask].dropna(subset=VARIANTS)
        if len(e) < 3:
            res[name] = {"n": len(e)}
            continue
        m = {v: evaluation.metrics(e[v]) for v in VARIANTS}
        best = engine.best_baseline({b: m[b]["MAE"] for b in BASELINES}, BASELINES)
        other = [b for b in BASELINES if b != best][0]
        dm = evaluation.dm_test(e[other].to_numpy(), e[best].to_numpy())
        res[name] = {"n": len(e), "first": str(e["period"].min()), "last": str(e["period"].max()),
                     "by_regime": e.groupby("regime").size().to_dict(), "metrics": m, "best": best,
                     "dm": {"variant": other, "mean_diff": dm.mean_diff, "p": dm.p, "mde": dm.mde}}
    return res


def holdout_counts(frame: pd.DataFrame, first_live: pd.Timestamp | None = None) -> dict:
    e = frame[frame["in_period"]]
    o, k = pd.to_datetime(e["origin"]), pd.to_datetime(e["outcome_known_from"])
    dev = (o <= DEV_END) & (k <= DEV_END)
    hold = (o >= HOLDOUT_START) & ((o < first_live) if first_live is not None else True)
    return {"development": int(dev.sum()), "holdout": int(hold.sum()), "neither": int((~dev & ~hold).sum())}


def interval_scores(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    e = frame.set_index("period")
    return intervals.score_frame(e[VARIANTS], pd.to_datetime(e["origin"]), e["outcome_known_from"])


def evaluate_intervals(frame: pd.DataFrame) -> dict:
    scored = interval_scores(frame)
    sub = scored[scored["period"].map(lambda p: p.start_time) >= SUBPERIOD] if len(scored) else scored
    return {"full": intervals.evaluate(scored, VARIANTS, BASELINES),
            "2023-01-": intervals.evaluate(sub, VARIANTS, BASELINES)}


def backtest(table: pd.DataFrame | None = None, log: bool = True) -> dict:
    table = observations.load() if table is None else table
    t = table[table["series"].str.startswith(PREFIX) & ~table["series"].str.endswith("_se")]
    frame = run(t)
    res = evaluate(frame) if len(frame) else {}
    out = {"frame": frame, "eval": res, "champion": CHAMPION, "holdout": holdout_counts(frame) if len(frame) else {}}
    if intervals.ENABLED and len(frame):
        out["intervals"] = evaluate_intervals(frame)
    if log:
        rows = [{"target": "btos_ai_use_<regim>", "variant": v, "period": f"{per} {r['first']}..{r['last']}",
                 "n": r["metrics"][v]["n"], "MAE": round(r["metrics"][v]["MAE"], 4),
                 "dm_p_vs_baseline": round(r["dm"]["p"], 4) if v == r["dm"]["variant"] else ""}
                for per, r in res.items() if "metrics" in r for v in VARIANTS]
        out["log"] = evaluation.log_run("n5_backtest", rows)
    return out


def format_report(out: dict) -> str:
    f = out["frame"]
    lines = [f"N5 BTOS: {len(f)} publications with a forecast, {int(f['in_period'].sum()) if len(f) else 0} evaluated "
             f"(F-B4: 7 earlier observations in the regime)"]
    for per, r in out["eval"].items():
        if "metrics" not in r:
            lines.append(f"{per}: n={r['n']}")
            continue
        lines.append(f"\n{per}: {r['first']}..{r['last']}, n={r['n']} {r['by_regime']}, best baseline {r['best']}")
        for v in VARIANTS:
            m = r["metrics"][v]
            tail = (f"  dMAE {r['dm']['mean_diff']:+.3f} DM p {r['dm']['p']:.3f} MDE {r['dm']['mde']:.3f}"
                    if v == r["dm"]["variant"] else "")
            lines.append(f"{v}: n {m['n']} MAE {m['MAE']:.3f} RMSE {m['RMSE']:.3f} bias {m['bias']:+.3f}{tail}")
    lines.append(f"\nchampion {CHAMPION} (F-B8b, no variants); G-E membership (informational): {out['holdout']}")
    for per, r in (out.get("intervals") or {}).items():
        lines.append("\n" + intervals.markdown(r, f"N5 intervals {per} (pp)"))
    return "\n".join(lines)


# ------------------------------------------------------------------ live: the logged schedule


def schedule_path() -> Path:
    return census_btos.SCHEDULE_LOG


def schedule(as_of, path: Path | None = None) -> pd.DataFrame | None:
    """The BTOS schedule (smpdt, col_end, published) as logged by the latest fetch on or before `as_of`, or None."""
    path = Path(path or schedule_path())
    if not path.exists():
        return None
    log = pd.read_parquet(path)
    log = log[pd.to_datetime(log["fetched_at"]) <= pd.Timestamp(as_of)]
    if log.empty:
        return None
    last = log["fetched_at"].max()
    return log[log["fetched_at"] == last].sort_values("smpdt").reset_index(drop=True)


def scheduled_cycle(today, path: Path | None = None) -> dict | None:
    """The cycle whose scheduled publication is the day after `today`, with its regime and target period, or None
    (no logged schedule or no publication tomorrow). Raises NotAvailable for a date that cannot be trusted."""
    today = pd.Timestamp(today).normalize()
    s = schedule(today, path)
    if s is None:
        return None
    hit = s[pd.to_datetime(s["published"]).dt.normalize() == today + pd.Timedelta(days=1)]
    if hit.empty:
        return None
    r = hit.iloc[0]
    pub = pd.Timestamp(r["published"])
    for first, last in census_btos.FUNDING_LAPSES:
        if first <= pub <= last:
            raise NotAvailable(f"cycle {int(r['smpdt'])}: scheduled {pub.date()} inside a funding lapse")
    regime = census_btos.regime_of(int(r["smpdt"]))
    if regime is None:
        raise NotAvailable(f"cycle {int(r['smpdt'])} is outside every reviewed wording regime")
    period = pd.Timestamp(r["col_end"]).to_period("W-SUN")
    same = [c for c in s.itertuples() if c.smpdt < r["smpdt"] and census_btos.regime_of(int(c.smpdt)) is regime]
    prev = pd.Timestamp(same[-1].col_end).to_period("W-SUN") if same else None
    return {"smpdt": int(r["smpdt"]), "published": pub, "regime": regime.version, "series": key(regime.version),
            "period": period, "previous_period": prev, "fetched_at": pd.Timestamp(r["fetched_at"])}


def file_stem(period: pd.Period) -> str:
    """forecasts/n5/<collection end date>.json (the W-SUN week's Sunday)."""
    return str(period.end_time.date())


def live_errors(files, table: pd.DataFrame, as_of) -> tuple[pd.DataFrame, pd.Series]:
    """Errors (pp) of committed live forecasts whose outcome (first vintage) is known at `as_of` (F-C4)."""
    rows, kf = {}, {}
    for f in sorted(files):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        out = engine.first_vintages(table, d["target"])
        p = pd.Period(d["period"], freq="W-SUN")
        if p not in out.index:
            continue
        known = pd.Timestamp(out.at[p, "known_from"])
        if known > pd.Timestamp(as_of) or known <= pd.Timestamp(d["origin"]):
            continue
        y = float(out.at[p, "value"])
        rows[p] = {v: (float(d["variants"][v]) - y if d["variants"].get(v) is not None else float("nan"))
                   for v in VARIANTS}
        kf[p] = known
    idx = pd.PeriodIndex(sorted(rows), freq="W-SUN")
    return (pd.DataFrame([rows[p] for p in idx], index=idx, columns=VARIANTS),
            pd.Series([kf[p] for p in idx], index=idx, dtype="datetime64[ns]"))


def live_distribution(table: pd.DataFrame, origin, levels: dict, live_dir=None) -> dict:
    origin = pd.Timestamp(origin)
    t = table[(table["known_from"] <= origin) & table["series"].str.startswith(PREFIX)]
    frame = run(t)
    errors = frame.set_index("period")[VARIANTS] if len(frame) else pd.DataFrame(columns=VARIANTS)
    kf = frame.set_index("period")["outcome_known_from"] if len(frame) else pd.Series(dtype="datetime64[ns]")
    files = sorted(Path(live_dir).glob("*.json")) if live_dir else []
    live, live_kf = live_errors(files, t, origin)
    e, known = intervals.merge_live(errors, kf, live, live_kf)
    return intervals.live_block(levels, e, known, origin, live_index=live.index, additive=True)


def live_payload(table: pd.DataFrame, origin, cycle: dict, live_dir=None) -> dict:
    origin = pd.Timestamp(origin)
    k, p = cycle["series"], cycle["period"]
    t = table[table["known_from"] <= origin]
    y = observations.as_of(k, origin, t[t["series"] == k])
    if p in y.index:
        raise NotAvailable(f"{k} {p} is already known at {origin.date()}: no nowcast")
    pp = cycle.get("previous_period")  # F-B8b: the previous publication of the regime must be known at the origin
    if pp is None or pp not in y.index:
        raise NotAvailable(f"previous publication ({pp}) of {k} not known at {origin.date()}")
    levels, reasons = forecast_levels(y, p)
    if not np.isfinite(levels[CHAMPION]):
        raise NotAvailable(f"{CHAMPION} cannot be formed: {reasons[CHAMPION]} (F-B4/F-B8b); no forecast written")
    prev_periods = list(y[y.index < p].index[-LAGS:])
    kf = engine.vintage_known_from(t[t["series"] == k], origin)
    extra = {"distribution": live_distribution(table, origin, levels, live_dir)} if intervals.ENABLED else {}
    return {
        "nowcast": "N5", "target": k, "regime": cycle["regime"], "cycle": cycle["smpdt"], "period": str(p),
        "scheduled_publication": str(cycle["published"].date()), "schedule_fetched": str(cycle["fetched_at"].date()),
        "origin": origin.date().isoformat(), "registered_origin": True, "unit": UNIT, "error_space": "pp",
        "champion": CHAMPION, "value": levels[CHAMPION], "variants": levels, "unavailable": reasons,
        "inputs": [{"series": k, "period": str(q), "value": float(y[q]), "known_from": str(kf[q].date())}
                   for q in prev_periods],
        **extra,
    }


def write_live(table: pd.DataFrame, origin, out_dir, today=None, schedule_file: Path | None = None) -> Path:
    """forecasts/n5/<collection end>.json, written once. Refuses when the origin is not the day before a logged
    scheduled publication of a reviewed regime, or B1 cannot be formed."""
    origin = pd.Timestamp(origin)
    cycle = scheduled_cycle(origin, schedule_file)
    if cycle is None:
        raise NotAvailable(f"{origin.date()} is not the day before a BTOS publication in the logged schedule "
                           f"({schedule_file or schedule_path()})")
    path = Path(out_dir) / f"{file_stem(cycle['period'])}.json"
    return engine.write_live(path, origin, lambda: live_payload(table, origin, cycle, live_dir=Path(out_dir)), today)

