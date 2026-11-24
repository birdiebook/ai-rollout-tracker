"""The registered holdout evaluation of C3 (variant DF for N1-N4) and C4 (regime and breaks), run once.

    python -m ai_tracker.holdout        the one opening run (docs/holdout_logg.md); writes data/derived/holdout/

Register: docs/mattregister.md "Steg 2" G-E with R6 adopted verbatim (F-E1-F-E6, F-B9, F-B10, F-D6), locked specs
docs/steg2/c3_spec.md (5431f41) and docs/steg2/c4_spec.md (735dc64). Nothing here changes a model; it evaluates.

C3 (DF), per target:
- Membership by origin (F-E1, F-E2): the holdout is origins 2025-07-01 to the day before the target's first live
  origin, with the first-vintage outcome known now. Development = the registered development run (origin and outcome
  known <= 2025-06-30, table cut at 2025-06-30).
- n < 8 on the holdout: no test, DF goes in as a shadow in the live register (F-E6). Reported descriptively.
- n >= 8 (only N2 in practice): DM on absolute errors against the F-B10 comparator (best by MAE on the same holdout
  rows of the candidates in the locked spec: B0, B1 and B2 for N2), Holm in the step-2 family {B3, DF} with B3's p from
  its registered run. Pass = Holm-p < 0.10 and a lower MAE than the comparator on the holdout and in development.
  F-B10: the champion changes only if DF also beats the current champion (N2: B3) in both periods, and only after an
  independent review (CLAUDE.md: one review per positive result). A pass is therefore reported as "villkorad".

C4 (F-D6, c4_spec section 5), descriptive: (a) frequency of reported shifts and breaks, (b) the share of computation
dates where the real-time reported state differs from the smoothed state on 2026-10-31, (c) Spearman's rho between
P(slowdown) and N1 B1 / N2 B3 absolute errors, information only. The real-time sequence is computed from 2012-01-31 so
that the reported states and the break rule carry over from the development period exactly as stored values would.
"""

from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ai_tracker import config, evaluation, observations
from ai_tracker.factor import guard as factor_guard
from ai_tracker.nowcast import df, n2, n3, n4

HOLDOUT_START = factor_guard.HOLDOUT_START
DEV_END = factor_guard.DEV_END
FIRST_LIVE = {"N1": pd.Timestamp("2027-01-20"), "N2": pd.Timestamp("2026-12-05"), "N3": n3.FIRST_LIVE,
              "N4": n4.FIRST_LIVE}  # docs/drift.md; F-E2: the holdout ends the day before
MIN_N = 8  # F-E6
PROMOTION_P = 0.10
# Raw DM p of the other step-2 family members from their registered runs (F-B9): N2 B3 vs B2,
# experiments/runs/20261124T005428Z_n2_tsmc.csv ("B3 step2 vs B2 (Holm 0.0589)", dm_p 0.0294). Others p = 1.
FAMILY_P = {"N2": {"B3": 0.0294}}
CURRENT_CHAMPION = {"N1": "B1", "N2": "B3", "N3": "B1", "N4": "B1"}  # on 2026-11-24
C4_START, C4_END = pd.Timestamp("2025-07-31"), pd.Timestamp("2026-10-31")
OUT = config.REPO / "data" / "derived" / "holdout"


def _mae(e) -> float:
    e = np.asarray(e, float)
    return float(np.mean(np.abs(e))) if len(e) else float("nan")


def holdout_rows(frame: pd.DataFrame, key: str) -> pd.Series:
    o = pd.to_datetime(frame["origin"])
    return (o >= HOLDOUT_START) & (o < FIRST_LIVE[key])


def evaluate_df(key: str, dev: pd.DataFrame, full: pd.DataFrame) -> dict:
    """The F-E6 rule for one target. `dev` = the development run's frame (df.run, dev=True), `full` = the frame on the
    whole table (df.run, dev=False); both with e_DF and the candidates' errors, `full` optionally with e_<champion>."""
    tgt = df.TARGETS[key]
    cands = list(tgt.candidates)
    cols = ["e_DF", *[f"e_{c}" for c in cands]]
    h = full[holdout_rows(full, key)].dropna(subset=cols)
    champ = CURRENT_CHAMPION[key]
    models = ["DF", *cands, *([champ] if champ not in cands and f"e_{champ}" in full else [])]
    out = {"target": key, "main": tgt.main, "candidates": cands, "current_champion": champ,
           "window": [str(HOLDOUT_START.date()), str((FIRST_LIVE[key] - pd.Timedelta(days=1)).date())],
           "n": int(len(h)), "periods": [str(p) for p in h.index],
           "holdout_frame_rows": int(holdout_rows(full, key).sum()),
           "holdout_rows_with_df": int(full.loc[holdout_rows(full, key), "e_DF"].notna().sum())}
    out["metrics"] = {m: {"MAE": _mae(h[f"e_{m}"].dropna()), "bias": float(h[f"e_{m}"].mean()) if len(h) else
                          float("nan"), "n": int(h[f"e_{m}"].notna().sum())} for m in models}
    out["errors"] = {str(p): {m: (None if not np.isfinite(r[f"e_{m}"]) else float(r[f"e_{m}"])) for m in models}
                     for p, r in h.iterrows()}
    dev_eval = df.evaluate(tgt, dev)
    out["development"] = {k: dev_eval[k] for k in ("full", "sub")}
    dmask = pd.to_datetime(full["origin"]).le(DEV_END) & pd.to_datetime(full["outcome_known_from"]).le(DEV_END)
    both = dev["e_DF"].dropna().index.intersection(full.loc[dmask, "e_DF"].dropna().index)
    out["dev_consistency_max_abs_diff"] = (float((dev.loc[both, "e_DF"] - full.loc[both, "e_DF"]).abs().max())
                                           if len(both) else None)
    out["dev_consistency_rows"] = int(len(both))
    d_full = dev_eval["full"]
    if f"e_{champ}" in full and champ not in cands and "metrics" in d_full:  # current champion on the dev DF rows
        rows = dev.dropna(subset=cols).index
        out["development"]["champion_MAE"] = _mae(full.loc[full.index.intersection(rows), f"e_{champ}"].dropna())
    if out["n"] < MIN_N:
        out.update(test=False, outcome="skugga", reason=f"n = {out['n']} < {MIN_N} på holdouten: inget test (F-E6)")
        return out
    m = out["metrics"]
    comp = min(cands, key=lambda c: (m[c]["MAE"], cands.index(c)))
    dm = evaluation.dm_test(h["e_DF"].to_numpy(), h[f"e_{comp}"].to_numpy())
    p = dm.p if np.isfinite(dm.p) else 1.0
    family = {v: FAMILY_P.get(key, {}).get(v, 1.0) for v in tgt.family if v != "DF"}
    holm = evaluation.holm({**family, "DF": p})
    dev_ok = "metrics" in d_full and d_full["metrics"]["DF"]["MAE"] < d_full["metrics"][d_full["comparator"]]["MAE"]
    checks = {"holm": holm["DF"] < PROMOTION_P, "mae_holdout": m["DF"]["MAE"] < m[comp]["MAE"], "mae_dev": bool(dev_ok)}
    passed = all(checks.values())
    beats_champ = None
    if champ != tgt.main and champ in m:
        beats_champ = bool(m["DF"]["MAE"] < m[champ]["MAE"]
                           and out["development"].get("champion_MAE", float("inf")) > d_full["metrics"]["DF"]["MAE"])
    out.update(test=True, comparator=comp, dm_p=dm.p, dm_mean_diff=dm.mean_diff, mde=dm.mde, holm=holm,
               family_p=family, checks=checks, passed=passed, beats_current_champion=beats_champ)
    if passed and beats_champ is not False:
        out.update(outcome="villkorad", reason="regeln uppfylld; huvudmodellen byts först efter en oberoende granskning")
    elif passed:
        out.update(outcome="skugga", reason=f"regeln uppfylld mot {comp}, men DF slår inte nuvarande huvudmodell "
                                            f"{champ} i båda perioderna (F-B10): ingen ändring")
    else:
        out.update(outcome="skugga", reason="regeln inte uppfylld: " + ", ".join(k for k, v in checks.items() if not v))
    return out


def run_c3(table: pd.DataFrame, progress=print) -> tuple[dict, dict]:
    res, frames = {}, {}
    b3 = None
    for key in df.TARGETS:
        t0 = time.time()
        tgt = df.TARGETS[key]
        dev = df.run(tgt, table)
        full = df.run(tgt, table, dev=False)
        if key == "N2":
            b3 = n2.run(table)[["e_B3"]]
            full = full.join(b3, how="left")
        res[key] = evaluate_df(key, dev, full)
        frames[key] = full
        progress(f"C3 {key}: n holdout {res[key]['n']}, outcome {res[key]['outcome']} ({time.time() - t0:.0f}s)")
    return res, frames


def run_c4(table: pd.DataFrame, run_day, progress=print) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    from ai_tracker.regime import evaluate as rev
    from ai_tracker.regime import realtime as rt

    t0 = time.time()
    ms_f, b_f = rt.run(table, rt.DEV_START, C4_END,
                       progress=lambda d: progress(f"C4 {d.date()} {time.time() - t0:.0f}s") if d.month == 12
                       or d >= C4_START else None)
    states, breaks = rt.reported_states(ms_f), rt.reported_breaks(b_f)
    errors = rev._main_errors(table)
    hold_err = {k: e[(e["origin"] >= HOLDOUT_START) & (e["origin"] < FIRST_LIVE[k])] for k, e in errors.items()}
    assoc = rev.association(states, hold_err, HOLDOUT_START, run_day)
    h_states = states[(states["date"] >= C4_START) & (states["date"] <= C4_END)]
    h_breaks = breaks[(breaks["date"] >= C4_START) & (breaks["date"] <= C4_END) & breaks["break"]]
    out = {
        "window": [str(C4_START.date()), str(C4_END.date())],
        "frequency": rev.frequency(states, breaks, C4_START, C4_END),
        "frequency_development": rev.frequency(states, breaks, rt.DEV_START, DEV_END),
        "reclassification": rev.reclassification(table, states, C4_START, C4_END),
        "association": {f"{k[0]}/{k[1]}": v for k, v in assoc.items()},
        "ms_path": {b: [{"date": str(r["date"].date()), "p": None if not np.isfinite(r["p_slow"]) else
                         round(float(r["p_slow"]), 4), "state": r["state"], "shift": r["shift"],
                         "mu_slow": r.get("mu_slow"), "mu_exp": r.get("mu_exp"), "converged": r.get("converged")}
                        for _, r in g.iterrows()] for b, g in h_states.groupby("block")},
        "breaks": [{"date": str(r["date"].date()), "branch": r["branch"], "series": r["series"],
                    "latest_period": r["latest_period"], "p": round(float(r["p_recent"]), 3)}
                   for _, r in h_breaks.iterrows()],
        "seconds": round(time.time() - t0),
    }
    return out, states, breaks


def _json(x):
    if isinstance(x, dict):
        return {str(k): _json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_json(v) for v in x]
    if hasattr(x, "item") and not isinstance(x, (str, bytes)):
        x = x.item()
    if isinstance(x, float) and not math.isfinite(x):
        return None
    if isinstance(x, (pd.Timestamp, pd.Period)):
        return str(x)
    return x


def main() -> int:
    t0 = time.time()
    run_day = pd.Timestamp(datetime.now(timezone.utc).date())
    table = observations.load()
    c3, frames = run_c3(table)
    c4, states, breaks = run_c4(table, run_day)
    OUT.mkdir(parents=True, exist_ok=True)
    for k, f in frames.items():
        f.to_parquet(OUT / f"df_{k.lower()}.parquet")
    states.to_parquet(OUT / "c4_ms.parquet")
    breaks.to_parquet(OUT / "c4_bocpd.parquet")
    res = {"run_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "git_sha": evaluation.git_sha(),
           "c3": c3, "c4": c4, "seconds": round(time.time() - t0)}
    (OUT / "results.json").write_text(json.dumps(_json(res), indent=1, ensure_ascii=False), encoding="utf-8")
    rows = []
    for k, r in c3.items():
        m = r["metrics"]["DF"]
        rows.append({"target": k, "variant": f"DF holdout ({r['outcome']})",
                     "period": f"holdout {r['window'][0]}..{r['window'][1]}", "n": r["n"],
                     "MAE": None if not np.isfinite(m["MAE"]) else round(m["MAE"], 4),
                     "dm_p_vs_baseline": round(r["dm_p"], 4) if r.get("test") else None})
    for b, v in c4["frequency"]["ms"].items():
        rows.append({"target": f"C4 {b}", "variant": "MS holdout", "period": f"holdout {c4['window'][0]}.."
                     f"{c4['window'][1]}", "n": v["dates_with_p"], "MAE": None, "dm_p_vs_baseline": None})
    log = evaluation.log_run("holdout_c3_c4", rows)
    print(json.dumps(_json({k: {kk: vv for kk, vv in v.items() if kk not in ("errors", "periods")}
                            for k, v in c3.items()}), indent=1, ensure_ascii=False))
    print(json.dumps(_json({k: v for k, v in c4.items() if k != "ms_path"}), indent=1, ensure_ascii=False))
    print(f"results {OUT / 'results.json'}, log {log}, {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
