"""Variant DF (track C3) for N1-N4: the main model's forecast corrected by an OLS of its miss on the factors' nowcast
change. Register: docs/mattregister.md "Steg 2", G-B "Faktormodell (C3)", with R6 (F-B16-F-B22, F-E1-F-E6) adopted
verbatim; technical specification docs/steg2/c3_spec.md (fixed before the first real-data run).

    python -m ai_tracker.nowcast.df            development evaluation (origins <= 2025-06-30 only)

- Main model, fixed (F-B19): B1 for N1, N3 and N4, B2 for N2. It is not changed if a champion changes later.
- Miss r_s = 100 * (log outcome_s - log main_s) = -e_main_s (first-vintage outcome).
- Regressors (F-B19): a constant, df_capex and df_demand. df = mean of the block factor over the target period's months
  minus the mean over the previous period's months, both from the factor vintage of the forecast's own origin. Months:
  the calendar quarter (N1, N4), the fiscal quarter's three calendar months, i.e. the month it ends in and the two
  before (N3), the month m and m-1 (N2).
- Training rows (F-B18): earlier target periods s, each with the factor vintage of its own origin (pseudo real time),
  used only when s's first-vintage outcome is known at the current origin and both blocks exist at s's origin.
  Expanding window, at least 12 rows (G-B). Forecast = main x exp(r_hat / 100), so e_DF = e_main + r_hat.
- Comparator (F-B10): the best by MAE of B0, B1, the current champion and the model DF builds on, on the same rows.
- Holm (F-B9, register amendment): step-2 family per target; members not evaluated here enter with p = 1.
- Holdout (G-E): this module refuses any origin after 2025-06-30 (factor.guard) and runs on the rows known by then.
  Promotion is decided on the holdout only (F-E6); the development evaluation decides nothing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from ai_tracker import evaluation, observations
from ai_tracker.factor import guard, realtime
from ai_tracker.nowcast import n1, n2, n3, n4, quarterly

MIN_TRAIN = 12
BLOCKS = ("capex", "demand")


@dataclass
class Target:
    label: str
    main: str
    candidates: tuple[str, ...]  # F-B10 comparator candidates (B0, B1, champion, model DF builds on)
    family: tuple[str, ...]  # step-2 Holm family
    subperiod: pd.Period
    frame: Callable[[pd.DataFrame], pd.DataFrame]  # -> index period; origin, outcome_known_from, e_<variant>
    months: Callable[[pd.Period], tuple[pd.PeriodIndex, pd.PeriodIndex]]  # (target months, previous months)


def _quarter_months(q: pd.Period) -> tuple[pd.PeriodIndex, pd.PeriodIndex]:
    cur = pd.period_range(q.asfreq("M", "s"), q.asfreq("M", "e"), freq="M")
    return cur, cur - 3


def _fiscal_months(q: pd.Period) -> tuple[pd.PeriodIndex, pd.PeriodIndex]:
    end = n3.fiscal_quarter(q)[1].to_period("M")
    cur = pd.period_range(end - 2, end, freq="M")
    return cur, cur - 3


def _month(m: pd.Period) -> tuple[pd.PeriodIndex, pd.PeriodIndex]:
    return pd.PeriodIndex([m], freq="M"), pd.PeriodIndex([m - 1], freq="M")


def _std(df: pd.DataFrame, period_col: str | None, variants) -> pd.DataFrame:
    d = df.copy()
    if period_col:
        d = d.set_index(period_col)
    out = pd.DataFrame(index=d.index)
    out["origin"] = pd.to_datetime(d["origin"])
    out["outcome_known_from"] = pd.to_datetime(d["outcome_known_from"])
    for v in variants:
        out[f"e_{v}"] = d[f"e_{v}"] if f"e_{v}" in d else d[v]
    return out.sort_index()


def _n1_frame(t: pd.DataFrame) -> pd.DataFrame:
    return _std(n1.backtest_unit(t, n1.TARGET), "quarter", ("B0", "B1"))


def _n2_frame(t: pd.DataFrame) -> pd.DataFrame:
    return _std(n2.run(t), None, ("B0", "B1", "B2"))


def _quarterly_frame(spec: quarterly.Spec) -> Callable[[pd.DataFrame], pd.DataFrame]:
    def f(t: pd.DataFrame) -> pd.DataFrame:
        fr = quarterly.run(t, spec)
        if fr.empty:
            return pd.DataFrame(columns=["origin", "outcome_known_from", "e_B0", "e_B1"])
        return _std(fr, "quarter", ("B0", "B1"))
    return f


TARGETS: dict[str, Target] = {
    "N1": Target("N1", "B1", ("B0", "B1"), ("B3", "DF"), pd.Period("2023Q1", "Q-DEC"), _n1_frame, _quarter_months),
    "N2": Target("N2", "B2", ("B0", "B1", "B2"), ("B3", "DF"), pd.Period("2023-01", "M"), _n2_frame, _month),
    "N3": Target("N3", "B1", ("B0", "B1"), ("B2", "B3", "DF"), pd.Period("2023Q1", "Q-DEC"),
                 _quarterly_frame(n3.SPEC), _fiscal_months),
    "N4": Target("N4", "B1", ("B0", "B1"), ("V1", "DF"), pd.Period("2023Q1", "Q-DEC"),
                 _quarterly_frame(n4.SPEC), _quarter_months),
}


# ------------------------------------------------------------------ DF rows


def factor_changes(target: Target, period: pd.Period, v: realtime.Vintage) -> dict:
    cur, prev = target.months(period)
    return {f"df_{b}": v.mean_over(b, cur) - v.mean_over(b, prev) for b in BLOCKS}


def run(target: Target, table: pd.DataFrame, vintage_fn=None) -> pd.DataFrame:
    """DF for every period of the main model's backtest frame (development rows only). `vintage_fn(table, origin)`
    defaults to realtime.vintage (cached, guarded)."""
    vintage_fn = vintage_fn or realtime.vintage
    t = guard.dev_table(table)
    base = target.frame(t)
    base = base[base[f"e_{target.main}"].notna()]
    for o in base["origin"]:
        guard.check(o, f"DF {target.label}")
    vint = {o: vintage_fn(t, o) for o in sorted(set(base["origin"]))}
    rows = []
    for p, r in base.iterrows():
        v = vint[r["origin"]]
        rows.append({"period": p, **factor_changes(target, p, v),
                     "n_capex": len(v.fits["capex"].keys), "n_demand": len(v.fits["demand"].keys)})
    f = base.join(pd.DataFrame(rows).set_index("period"))
    f["r"] = -f[f"e_{target.main}"]
    return apply_df(f)


def apply_df(f: pd.DataFrame) -> pd.DataFrame:
    """OLS of r on (1, df_capex, df_demand), expanding window in pseudo real time (F-B18).
    Sets e_DF, n_train and the coefficients b0, b_capex, b_demand."""
    f = f.copy()
    f["e_DF"], f["n_train"] = np.nan, 0
    for c in ("b0", "b_capex", "b_demand"):
        f[c] = np.nan
    ok = f[["r", "df_capex", "df_demand"]].notna().all(axis=1)
    for p in f.index:
        o = f.at[p, "origin"]
        if not (np.isfinite(f.at[p, "df_capex"]) and np.isfinite(f.at[p, "df_demand"])):
            continue
        tr = f[ok & (f.index < p) & (f["outcome_known_from"] <= o)]
        f.at[p, "n_train"] = len(tr)
        if len(tr) < MIN_TRAIN:
            continue
        A = np.column_stack([np.ones(len(tr)), tr["df_capex"], tr["df_demand"]])
        coef, *_ = np.linalg.lstsq(A, tr["r"].to_numpy(dtype=float), rcond=None)
        rhat = float(coef[0] + coef[1] * f.at[p, "df_capex"] + coef[2] * f.at[p, "df_demand"])
        f.at[p, "e_DF"] = -f.at[p, "r"] + rhat  # e_main + r_hat
        f.at[p, "b0"], f.at[p, "b_capex"], f.at[p, "b_demand"] = (float(c) for c in coef)
    return f


# ------------------------------------------------------------------ evaluation


def evaluate(target: Target, f: pd.DataFrame) -> dict:
    """Development evaluation: DF against the F-B10 comparator on the common rows, full period and the subperiod.
    Informational only (F-E6: promotion is decided on the holdout)."""
    cols = ["e_DF", *[f"e_{c}" for c in target.candidates]]
    out = {}
    for name, mask in (("full", f.index == f.index), ("sub", f.index >= target.subperiod)):
        e = f[mask].dropna(subset=cols)
        if len(e) < 3:
            out[name] = {"n": int(len(e))}
            continue
        m = {c: evaluation.metrics(e[f"e_{c}"]) for c in ("DF", *target.candidates)}
        comp = min(target.candidates, key=lambda c: (m[c]["MAE"], target.candidates.index(c)))
        dm = evaluation.dm_test(e["e_DF"].to_numpy(), e[f"e_{comp}"].to_numpy())
        p = dm.p if np.isfinite(dm.p) else 1.0
        holm = evaluation.holm({v: (p if v == "DF" else 1.0) for v in target.family})
        out[name] = {"n": int(len(e)), "first": str(e.index.min()), "last": str(e.index.max()), "metrics": m,
                     "comparator": comp, "dm_p": dm.p, "dm_mean_diff": dm.mean_diff, "mde": dm.mde,
                     "holm_p": holm["DF"]}
    out["rows_with_factor"] = int(f[["df_capex", "df_demand"]].notna().all(axis=1).sum())
    out["rows_df"] = int(f["e_DF"].notna().sum())
    out["first_df"] = str(f.index[f["e_DF"].notna()].min()) if out["rows_df"] else None
    return out


def run_all(table: pd.DataFrame | None = None, targets=None) -> dict:
    table = observations.load() if table is None else table
    res = {}
    for k in targets or TARGETS:
        f = run(TARGETS[k], table)
        res[k] = {"frame": f, "eval": evaluate(TARGETS[k], f)}
    return res


def _c(x, nd=2, signed=False):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "–"
    return (f"{x:+.{nd}f}" if signed else f"{x:.{nd}f}").replace(".", ",").replace("-", "−")


def markdown(res: dict) -> str:
    lines = ["| Mål | Period | n | Jämförelse | MAE DF | MAE jämförelse | MAE-skillnad | Bias DF | DM p | Holm-p | MDE |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, r in res.items():
        for name in ("full", "sub"):
            e = r["eval"][name]
            if "metrics" not in e:
                lines.append(f"| {k} | {'hela' if name == 'full' else 'från 2023'} | {e['n']} | – | – | – | – | – | – | "
                             f"– | – |")
                continue
            m, comp = e["metrics"], e["comparator"]
            lines.append(f"| {k} | {e['first']} – {e['last']} | {e['n']} | {comp} | {_c(m['DF']['MAE'])} | "
                         f"{_c(m[comp]['MAE'])} | {_c(e['dm_mean_diff'], 2, True)} | {_c(m['DF']['bias'], 2, True)} | "
                         f"{_c(e['dm_p'], 3)} | {_c(e['holm_p'], 3)} | {_c(e['mde'])} |")
    return "\n".join(lines)


def main() -> int:
    res = run_all()
    print(markdown(res))
    for k, r in res.items():
        e = r["eval"]
        print(f"{k}: rows with both factors {e['rows_with_factor']}, DF formed {e['rows_df']} (first {e['first_df']})")
    rows = []
    for k, r in res.items():
        e = r["eval"]["full"]
        if "metrics" in e:
            rows.append({"target": k, "variant": "DF", "period": f"dev {e['first']}..{e['last']}", "n": e["n"],
                         "MAE": round(e["metrics"]["DF"]["MAE"], 4), "dm_p_vs_baseline": round(e["dm_p"], 4)})
    evaluation.log_run("c3_df_development", rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
