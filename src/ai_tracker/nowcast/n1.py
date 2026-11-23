"""N1: quarterly capex of MSFT+GOOGL+AMZN+META (`capex_hyp4`), pre-registered in docs/mattregister.md (section 3
and the later entries under "Ändringar"). Secondary evaluation N1b: the same models per company, pooled.

Registered choices implemented here, nothing else:
- Target: first vintage of the quarter. Origin: quarter end + 20 days. Information set: as_of(origin) for
  every input, including the target's own history (so training uses the vintages known at the origin).
- Error: log(forecast) - log(outcome) * 100. MAE main metric, bias reported.
- B0: last quarter's level. B1: last quarter * exp(mean of the last 4 q/q log growth rates).
- V1: B1 + bridge. Expanding OLS of the B1 residual in q/q log growth (g_s - drift_s) on a constant and the
  indicators' growth in the months of the quarter known at the origin.
- V2: the same regression with ridge; lambda by time-series CV inside each training window, standardisation
  fitted on training data only.
- Indicators: us_imports_tw_m, us_constr_datacenter (us_ip_semis excluded, register 2026-11-23).
- Minimum 12 training quarters; V1/V2 need every indicator for the quarter.

Fixed by this module where the register is silent (documented in docs/resultat/n1.md):
- Partial-quarter aggregation: for each indicator, J = the month positions (1st/2nd/3rd month) of the target
  quarter known at the origin. x_s = mean(log z over months J of quarter s) - mean(log z over months J of
  quarter s-1), for the target and every training quarter alike (same J, values as of the origin).
- "B1 + bridge" is read as: the bridge explains B1's miss, so B1 is the anchor and the regression adds a
  correction. A training row needs growth, drift (4 earlier growths) and all indicators.
- "12 quarters of training" = 12 complete regression rows, the strictest count. The evaluation starts at the
  first such quarter; B0/B1 are scored on the same quarters.
- A quarter where an indicator has no known month at the origin has no V1/V2 forecast. Metrics and tests
  use the common sample (all four variants present), and the excluded quarters are listed.
- Ridge: minimise ||r - a - Zb||^2 + lambda ||b||^2 on standardised Z (training mean/sd, ddof 0), intercept
  unpenalised. Grid LAMBDAS (26 values, 0.01-1000, log spaced). CV: expanding one-step-ahead inside the
  training window from CV_MIN rows, absolute-error loss (main metric), ties go to the larger lambda.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from ai_tracker import evaluation
from ai_tracker.nowcast import engine

TARGET = "capex_hyp4"
COMPANIES = ["capex_msft", "capex_googl", "capex_amzn", "capex_meta"]
INDICATORS = ["us_imports_tw_m", "us_constr_datacenter"]
ORIGIN_DAYS = 20
MIN_TRAIN = 12
SUBPERIOD = pd.Period("2023Q1", freq="Q-DEC")
LAMBDAS = np.logspace(-2, 3, 26)
CV_MIN = 8
VARIANTS = ["B0", "B1", "V1", "V2"]
BASELINES = ["B0", "B1"]
MODELS = ["V1", "V2"]
HOLM_ALPHA = 0.10
DEFAULT_CHAMPION = "B1"
# Champion for live forecasts, decided by the registered promotion rule on the phase 3 backtest
# (docs/resultat/n1.md). Changing it needs a new decision, not a rerun.
CHAMPION = "B1"


class NotAvailable(Exception):
    """The variant (or the whole forecast) cannot be formed from the information set."""


def origin_for(quarter: pd.Period) -> pd.Timestamp:
    return pd.Timestamp(quarter.end_time.normalize()) + pd.Timedelta(days=ORIGIN_DAYS)


def target_quarter(origin) -> pd.Period:
    """The last quarter that ended before `origin`."""
    return pd.Period(pd.Timestamp(origin), freq="Q-DEC") - 1


# ------------------------------------------------------------------ building blocks


def _quarter_months(q: pd.Period) -> pd.PeriodIndex:
    return pd.period_range(q.asfreq("M", "s"), q.asfreq("M", "e"), freq="M")


def known_positions(z: pd.Series, q: pd.Period) -> list[int]:
    """Month positions (0, 1, 2) of quarter q present in the as-of series z."""
    return [j for j, m in enumerate(_quarter_months(q)) if m in z.index]


def partial_growth(z: pd.Series, q: pd.Period, positions: list[int]) -> float:
    """Mean log level over `positions` of quarter q minus the same positions of q-1 (NaN if any is missing)."""
    cur = [_quarter_months(q)[j] for j in positions]
    prev = [_quarter_months(q - 1)[j] for j in positions]
    if not positions or any(m not in z.index for m in cur + prev):
        return float("nan")
    vals = np.log(z.loc[cur + prev].to_numpy(dtype=float))
    k = len(positions)
    return float(vals[:k].mean() - vals[k:].mean())


def ols_fit(X: np.ndarray, r: np.ndarray) -> np.ndarray:
    A = np.column_stack([np.ones(len(r)), X])
    coef, *_ = np.linalg.lstsq(A, r, rcond=None)
    return coef


def ols_predict(coef: np.ndarray, x: np.ndarray) -> float:
    return float(coef[0] + x @ coef[1:])


@dataclass
class Ridge:
    mu: np.ndarray
    sd: np.ndarray
    a: float
    b: np.ndarray
    lam: float

    def predict(self, x: np.ndarray) -> float:
        return float(self.a + ((x - self.mu) / self.sd) @ self.b)


def ridge_fit(X: np.ndarray, r: np.ndarray, lam: float) -> Ridge:
    """Ridge on standardised X; mean/sd from these rows only; unpenalised intercept = mean(r)."""
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd = np.where(sd > 0, sd, 1.0)
    Z = (X - mu) / sd
    a = float(r.mean())
    b = np.linalg.solve(Z.T @ Z + lam * np.eye(X.shape[1]), Z.T @ (r - a))
    return Ridge(mu, sd, a, b, float(lam))


def choose_lambda(X: np.ndarray, r: np.ndarray, lambdas=LAMBDAS, cv_min: int = CV_MIN) -> tuple[float, dict]:
    """Expanding one-step-ahead CV inside the training rows; each fold standardises on its own rows."""
    n = len(r)
    if n <= cv_min:
        raise NotAvailable(f"ridge CV needs more than {cv_min} rows, has {n}")
    losses = {}
    for lam in lambdas:
        err = [abs(ridge_fit(X[:j], r[:j], lam).predict(X[j]) - r[j]) for j in range(cv_min, n)]
        losses[float(lam)] = float(np.mean(err))
    best = min(losses.values())
    lam = max(l for l, v in losses.items() if v <= best + 1e-12)  # tie -> more shrinkage
    return lam, losses


# ------------------------------------------------------------------ one forecast


@dataclass
class Forecast:
    quarter: pd.Period
    origin: pd.Timestamp
    target: str
    levels: dict[str, float] = field(default_factory=dict)  # variant -> level (NaN if not available)
    reasons: dict[str, str] = field(default_factory=dict)  # variant -> why not available
    n_train: int = 0
    positions: dict[str, list[int]] = field(default_factory=dict)
    lam: float = float("nan")
    ols_coef: list[float] = field(default_factory=list)


def forecast(info: engine.InfoSet, target: str, quarter: pd.Period | None = None) -> Forecast:
    """All variants for `quarter` (default: the quarter before the origin) from the information set only."""
    quarter = quarter or target_quarter(info.origin)
    out = Forecast(quarter, info.origin, target)
    y = info.get(target)
    if quarter in y.index:
        raise NotAvailable(f"{target} {quarter} is already known at {info.origin.date()}: no nowcast")
    if quarter - 1 not in y.index:
        raise NotAvailable(f"{target} {quarter - 1} not known at {info.origin.date()}")
    y = y[y.index < quarter]
    full = pd.period_range(y.index.min(), quarter - 1, freq="Q-DEC")
    g = np.log(y.reindex(full)).diff()
    drift = g.rolling(4, min_periods=4).mean().shift(1)  # drift_s = mean(g_{s-4..s-1})
    d_q = float(g.iloc[-4:].mean()) if g.iloc[-4:].notna().all() and len(g) >= 4 else float("nan")
    last = float(y.loc[quarter - 1])
    out.levels["B0"] = last
    info.mark(target, [quarter - 1])
    if math.isnan(d_q):
        raise NotAvailable(f"{target}: fewer than 4 growth rates before {quarter}")
    out.levels["B1"] = last * math.exp(d_q)
    info.mark(target, full[-5:])

    out.levels["V1"] = out.levels["V2"] = float("nan")
    try:
        X, r, x_q, rows = _design(info, quarter, g, drift, out)
        out.n_train = len(r)
        if len(r) < MIN_TRAIN:
            raise NotAvailable(f"{len(r)} training rows < {MIN_TRAIN}")
        coef = ols_fit(X, r)
        out.ols_coef = [float(c) for c in coef]
        out.levels["V1"] = last * math.exp(d_q + ols_predict(coef, x_q))
        lam, _ = choose_lambda(X, r)
        out.lam = lam
        out.levels["V2"] = last * math.exp(d_q + ridge_fit(X, r, lam).predict(x_q))
        info.mark(target, sorted({str(p) for s in rows for p in pd.period_range(s - 5, s, freq="Q-DEC") if p in y.index}))
    except NotAvailable as exc:
        for v in MODELS:
            if math.isnan(out.levels[v]):
                out.reasons[v] = str(exc)
    return out


def _design(info, quarter, g, drift, out):
    """Training matrix X (rows = quarters before `quarter`), residual target r, and the target's x."""
    cols, x_q = {}, []
    for ind in INDICATORS:
        z = info.get(ind)
        z = z[z > 0]
        pos = known_positions(z, quarter)
        out.positions[ind] = pos
        if not pos:
            raise NotAvailable(f"{ind}: no month of {quarter} known at {info.origin.date()}")
        info.mark(ind, [_quarter_months(quarter)[j] for j in pos] + [_quarter_months(quarter - 1)[j] for j in pos])
        x_q.append(partial_growth(z, quarter, pos))
        cols[ind] = pd.Series({s: partial_growth(z, s, pos) for s in g.index}, dtype=float)
    if any(math.isnan(x) for x in x_q):
        raise NotAvailable(f"indicator growth for {quarter} not computable at {info.origin.date()}")
    frame = pd.DataFrame({"g": g, "drift": drift, **cols}).dropna()
    rows = list(frame.index)
    for ind in INDICATORS:
        info.mark(ind, sorted({str(m) for s in rows for q in (s - 1, s)
                               for m in (_quarter_months(q)[j] for j in out.positions[ind])}))
    X = frame[INDICATORS].to_numpy(dtype=float)
    r = (frame["g"] - frame["drift"]).to_numpy(dtype=float)
    return X, r, np.array(x_q, dtype=float), rows


# ------------------------------------------------------------------ backtest


def backtest_unit(table: pd.DataFrame, target: str) -> pd.DataFrame:
    """Rolling-origin errors for one target series. One row per quarter with B0/B1 available."""
    fv = engine.first_vintage(table, target)
    fkf = engine.first_known_from(table, target)
    rows, known = [], []
    for q in fv.index[5:]:
        origin = origin_for(q)
        if fkf[q] <= origin:  # filed on or before the origin: a forecast of a known number is never scored
            known.append(f"{target} {q} (filed {fkf[q].date()})")
            continue
        try:
            f = forecast(engine.InfoSet(table, origin), target, q)
        except NotAvailable:
            continue
        row = {"unit": target, "quarter": q, "origin": origin.date(), "outcome": float(fv[q]),
               "n_train": f.n_train, "lambda": f.lam, "positions": str(f.positions),
               "reason": "; ".join(sorted(set(f.reasons.values())))}
        for v in VARIANTS:
            row[v] = engine.log_error(f.levels[v], fv[q]) if not math.isnan(f.levels[v]) else float("nan")
        rows.append(row)
    df = pd.DataFrame(rows)
    # Evaluation starts at the first quarter with >= MIN_TRAIN complete training rows and all indicators
    ok = df.index[df["V1"].notna()]
    start = df.loc[ok[0], "quarter"] if len(ok) else None
    df["in_period"] = df["quarter"] >= start if start is not None else False
    df.attrs["known_at_origin"] = known
    return df


def evaluate(errors: pd.DataFrame, pooled: bool) -> dict:
    """Metrics, DM vs best baseline, Holm over V1/V2, MDE for the full period and the subperiod."""
    res = {}
    for name, mask in (("full", errors["in_period"]), ("2023Q1-", errors["in_period"] & (errors["quarter"] >= SUBPERIOD))):
        e = errors[mask]
        common = e.dropna(subset=VARIANTS)
        excluded = sorted({f"{u} {q}" for u, q in e.loc[~e.index.isin(common.index), ["unit", "quarter"]].itertuples(index=False)})
        if len(common) < 3:  # nothing to test (e.g. a fixture that ends before the subperiod)
            res[name] = {"n": len(common), "excluded": excluded}
            continue
        m = {v: engine.summary(common[v]) for v in VARIANTS}
        best = min(BASELINES, key=lambda b: (m[b]["MAE"], BASELINES.index(b)))
        dm = {}
        for v in MODELS:
            r = engine.pooled_dm(common.assign(quarter=common["quarter"].astype(str)), v, best) if pooled \
                else evaluation.dm_test(common[v].to_numpy(), common[best].to_numpy())
            dm[v] = r
        holm = evaluation.holm({v: dm[v].p for v in MODELS})
        res[name] = {
            "n": len(common), "quarters": common["quarter"].nunique(),
            "first": str(common["quarter"].min()), "last": str(common["quarter"].max()),
            "excluded": excluded, "metrics": m, "best_baseline": best,
            "dm": {v: {"mean_diff": dm[v].mean_diff, "p": dm[v].p, "holm_p": holm[v], "mde": dm[v].mde,
                       "lag": dm[v].lag, "n": dm[v].n} for v in MODELS},
        }
    return res


def promotion(res: dict) -> dict:
    """Registered rule, conservative reading: Holm-p < 0.10 and lower MAE than the best baseline, both in the
    full period and in the subperiod from 2023Q1. Otherwise B1. Several qualifying: lowest full-period MAE."""
    checks = {}
    for v in MODELS:
        c = {}
        for per in ("full", "2023Q1-"):
            r = res[per]
            c[per] = {"holm_p": r["dm"][v]["holm_p"], "holm_ok": bool(r["dm"][v]["holm_p"] < HOLM_ALPHA),
                      "mae": r["metrics"][v]["MAE"], "best_mae": r["metrics"][r["best_baseline"]]["MAE"],
                      "mae_ok": bool(r["metrics"][v]["MAE"] < r["metrics"][r["best_baseline"]]["MAE"])}
        c["promoted"] = all(c[p]["holm_ok"] and c[p]["mae_ok"] for p in ("full", "2023Q1-"))
        # The looser reading (Holm only in the full period) is reported, never used
        c["promoted_loose_reading"] = c["full"]["holm_ok"] and c["full"]["mae_ok"] and c["2023Q1-"]["mae_ok"]
        checks[v] = c
    winners = [v for v in MODELS if checks[v]["promoted"]]
    champion = min(winners, key=lambda v: res["full"]["metrics"][v]["MAE"]) if winners else DEFAULT_CHAMPION
    return {"champion": champion, "checks": checks}


def run_backtest(table: pd.DataFrame, log: bool = True) -> dict:
    n1 = backtest_unit(table, TARGET)
    units = [backtest_unit(table, c) for c in COMPANIES]
    n1b = pd.concat(units, ignore_index=True)
    n1b.attrs["known_at_origin"] = [k for u in units for k in u.attrs["known_at_origin"]]
    out = {"N1": {"errors": n1, "eval": evaluate(n1, pooled=False)},
           "N1b": {"errors": n1b, "eval": evaluate(n1b, pooled=True)}}
    out["N1"]["promotion"] = promotion(out["N1"]["eval"])
    out["N1b"]["promotion"] = promotion(out["N1b"]["eval"])  # reported only; N1 decides
    if log:
        for key, name in (("N1", "n1"), ("N1b", "n1b")):
            rows = []
            for per, r in out[key]["eval"].items():
                for v in VARIANTS:
                    rows.append({"target": TARGET if key == "N1" else "capex_<company> pooled", "variant": v,
                                 "period": f"{r['first']}..{r['last']}", "n": r["metrics"][v]["n"],
                                 "MAE": r["metrics"][v]["MAE"],
                                 "dm_p_vs_baseline": r["dm"][v]["p"] if v in MODELS else ""})
            out[key]["log"] = evaluation.log_run(f"{name}_backtest", rows)
    return out


def format_report(out: dict) -> str:
    lines = []
    for key in ("N1", "N1b"):
        for per, r in out[key]["eval"].items():
            lines.append(f"\n{key} {per}: {r['first']}..{r['last']}, n={r['n']} ({r['quarters']} quarters), "
                         f"best baseline {r['best_baseline']}, excluded {r['excluded'] or '-'}")
            lines.append(f"{'variant':8s}{'n':>4s}{'MAE':>8s}{'RMSE':>8s}{'bias':>8s}{'dMAE':>8s}{'DM p':>7s}{'Holm':>7s}{'MDE':>7s}")
            for v in VARIANTS:
                m = r["metrics"][v]
                if v in MODELS:
                    d = r["dm"][v]
                    tail = f"{d['mean_diff']:8.2f}{d['p']:7.3f}{d['holm_p']:7.3f}{d['mde']:7.2f}"
                else:
                    tail = ""
                lines.append(f"{v:8s}{m['n']:4d}{m['MAE']:8.2f}{m['RMSE']:8.2f}{m['bias']:8.2f}{tail}")
        p = out[key]["promotion"]
        lines.append(f"{key} promotion: champion {p['champion']} "
                     + ", ".join(f"{v}: promoted={p['checks'][v]['promoted']}" for v in MODELS))
    return "\n".join(lines)


# ------------------------------------------------------------------ live forecast


def live_payload(table: pd.DataFrame, origin) -> dict:
    origin = pd.Timestamp(origin)
    q = target_quarter(origin)
    info = engine.InfoSet(table, origin)
    f = forecast(info, TARGET, q)
    champion = CHAMPION
    note = ""
    if math.isnan(f.levels.get(champion, float("nan"))):
        note = f"champion {champion} not available ({f.reasons.get(champion)}); fell back to {DEFAULT_CHAMPION}"
        champion = DEFAULT_CHAMPION
    registered = origin == origin_for(q)
    return {
        "nowcast": "N1", "target": TARGET, "quarter": str(q), "origin": origin.date().isoformat(),
        "registered_origin": registered, "unit": "MUSD",
        "champion": champion, "value": f.levels[champion],
        "variants": {v: (None if math.isnan(x) else x) for v, x in f.levels.items()},
        "unavailable": f.reasons, "n_train": f.n_train,
        "lambda_v2": None if math.isnan(f.lam) else f.lam, "ols_coef_v1": f.ols_coef,
        "month_positions": f.positions, "note": note,
        "inputs": info.inputs(),
    }


def write_live(table: pd.DataFrame, origin, out_dir, today=None):
    origin = pd.Timestamp(origin)
    today = pd.Timestamp(today or pd.Timestamp.now(tz="UTC").date())
    if origin > today:
        raise ValueError(f"origin {origin.date()} is in the future: as_of would not be the real information set")
    path = Path(out_dir) / f"{target_quarter(origin)}.json"
    if path.exists():
        raise FileExistsError(f"{path} already exists; live forecasts are never rewritten")
    return engine.write_forecast(path, live_payload(table, origin))
