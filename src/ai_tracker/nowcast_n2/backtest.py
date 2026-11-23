"""Pre-registered N2 backtest: rolling origin, expanding window, B0/B1/V1, DM + Holm + promotion rule.

Run: python -m ai_tracker.nowcast_n2.backtest   (reads data/observations.parquet, no network)

Promotion rule (register section 4, "as N1"), read conservatively:
- baseline = the better of B0 and B1 by MAE over the full evaluation period;
- DM test of V1 against that baseline on the full period; Holm over the single variant (adjusted p = p);
- V1 is promoted only if Holm-p < 0.10 AND V1's MAE is lower than both B0 and B1 in the full period AND in the
  subperiod from 2023-01. Otherwise B1 is the main model.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ai_tracker import evaluation, observations
from ai_tracker.nowcast_n2 import engine

PROMOTION_P = 0.10


@dataclass
class Result:
    frame: pd.DataFrame  # one row per evaluated month
    summary: pd.DataFrame  # one row per (period, variant)
    baseline: str
    holm_p: float
    promoted: bool
    champion: str
    reasons: list


COLUMNS = ["month", "origin", "outcome_known_from", "n_train", "lambda", "imports_lag",
           *[f"e_{v}" for v in engine.VARIANTS]]


def run(table: pd.DataFrame) -> pd.DataFrame:
    """Forecasts and errors for every month with a first-vintage outcome that was not yet known at its origin.

    A month whose first 6-K is dated on or before the origin is a forecast of a known number: it is never
    scored (same guard as N1). The skipped months are listed in frame.attrs["known_at_origin"].
    """
    t = engine.slim(table)
    outcomes = engine.first_vintages(t)
    last = outcomes.index.max()
    records = engine.build_records(t, last)
    rows, known = [], []
    for m in sorted(records):
        if m not in outcomes.index:
            continue
        if outcomes.at[m, "known_from"] <= records[m].origin:
            known.append(f"{m} (filed {pd.Timestamp(outcomes.at[m, 'known_from']).date()})")
            continue
        f = engine.forecast_from(m, records, outcomes)
        y = 100 * np.log(outcomes.at[m, "value"])
        imp_last = [p for s, p, *_ in f.inputs.used if s == "us_imports_tw_m"]
        rows.append({
            "month": m, "origin": f.origin, "outcome_known_from": outcomes.at[m, "known_from"],
            "n_train": f.n_train, "lambda": f.lam,
            "imports_lag": (m - pd.Period(max(imp_last), "M")).n if imp_last else np.nan,
            **{f"e_{v}": f.logs[v] - y for v in engine.VARIANTS},
        })
    frame = pd.DataFrame(rows, columns=COLUMNS).set_index("month")
    frame.attrs["known_at_origin"] = known
    return frame


def evaluate(frame: pd.DataFrame) -> Result:
    ok = frame[[f"e_{v}" for v in engine.VARIANTS]].notna().all(axis=1) & (frame["n_train"] >= engine.MIN_TRAIN)
    start = max(engine.EVAL_START, frame.index[ok].min())
    ev = frame[(frame.index >= start) & ok]
    periods = {"full": ev, "2023+": ev[ev.index >= engine.SUBPERIOD_START]}
    mae = {k: {v: evaluation.metrics(d[f"e_{v}"])["MAE"] for v in engine.VARIANTS} for k, d in periods.items()}
    baseline = min(("B0", "B1"), key=lambda v: mae["full"][v])

    out, dm_full = [], None
    for name, d in periods.items():
        base = min(("B0", "B1"), key=lambda v: mae[name][v])
        label = f"{d.index.min()}..{d.index.max()}"
        for v in engine.VARIANTS:
            m = evaluation.metrics(d[f"e_{v}"])
            row = {"period": name, "range": label, "variant": v, **m, "vs": "", "dm_diff": np.nan, "dm_p": np.nan,
                   "mde": np.nan}
            ref = baseline if name == "full" else base
            if v != ref:
                r = evaluation.dm_test(d[f"e_{v}"], d[f"e_{ref}"])
                row.update(vs=ref, dm_diff=r.mean_diff, dm_p=r.p, mde=r.mde)
                if name == "full" and v == "V1":
                    dm_full = r
            out.append(row)
    summary = pd.DataFrame(out)
    holm_p = evaluation.holm({"V1": dm_full.p})["V1"]
    checks = {
        f"Holm-p {holm_p:.3f} < {PROMOTION_P}": holm_p < PROMOTION_P,
        "lower MAE than B0 and B1, full period": mae["full"]["V1"] < min(mae["full"]["B0"], mae["full"]["B1"]),
        "lower MAE than B0 and B1, 2023+": mae["2023+"]["V1"] < min(mae["2023+"]["B0"], mae["2023+"]["B1"]),
    }
    promoted = all(checks.values())
    reasons = [f"{'PASS' if v else 'FAIL'}: {k}" for k, v in checks.items()]
    return Result(ev, summary, baseline, holm_p, promoted, "V1" if promoted else "B1", reasons)


def log(result: Result):
    rows = [{"target": engine.TARGET, "variant": r.variant, "period": f"{r.period} {r.range}", "n": r.n,
             "MAE": round(r.MAE, 4), "dm_p_vs_baseline": "" if np.isnan(r.dm_p) else round(r.dm_p, 4)}
            for r in result.summary.itertuples()]
    return evaluation.log_run("n2_tsmc", rows)


def markdown(result: Result) -> str:
    lines = ["| Period | Variant | n | MAE | RMSE | Bias | vs | MAE diff | DM p | MDE |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in result.summary.itertuples():
        f = lambda x: "" if np.isnan(x) else f"{x:.3f}"  # noqa: E731
        lines.append(f"| {r.period} {r.range} | {r.variant} | {r.n} | {r.MAE:.3f} | {r.RMSE:.3f} | {r.bias:+.3f} | "
                     f"{r.vs} | {f(r.dm_diff)} | {f(r.dm_p)} | {f(r.mde)} |")
    return "\n".join(lines)


def main():
    table = observations.load()
    frame = run(table)
    res = evaluate(frame)
    print(markdown(res))
    print(f"\nBaseline (best of B0/B1, full period): {res.baseline}. Holm-p (one variant): {res.holm_p:.4f}")
    print("\n".join(res.reasons))
    print(f"Promoted: {res.promoted}. Champion: {res.champion}")
    ev = res.frame
    print(f"\nOutcome known at origin: {len(frame.attrs['known_at_origin'])} months skipped "
          f"{frame.attrs['known_at_origin'] or ''}; scored with known outcome (must be 0): "
          f"{(ev['outcome_known_from'] <= ev['origin']).sum()}")
    print(f"Imports lag (months, target - latest known import month): {ev['imports_lag'].value_counts().to_dict()}")
    print(f"Lambda chosen: {ev['lambda'].value_counts().sort_index().to_dict()}")
    print(f"Run log: {log(res)}")
    return res


if __name__ == "__main__":
    main()
