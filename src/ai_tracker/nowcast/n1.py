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
- B2 (companies' own guidance; register change "B2: TSMC före 2017Q3 och definitionen för N1"), per company and
  then summed to capex_hyp4. For company c, quarter q in year Y, everything as_of(origin):
  - Meta: G = midpoint of the full-year range (guid_capex_meta_cy_lo/hi for Y), which includes finance-lease
    principal. Implied full year for capex_meta = G - (known quarters of fin_lease_meta in Y + B1 forecasts of
    fin_lease_meta for Y's unknown quarters).
  - Alphabet: G = midpoint of guid_capex_googl_cy_lo/hi for Y, used directly.
  - Quarter: (implied full year - Y's known quarters of capex_c) x B1 share, share = B1_c(q) / sum of B1_c over
    Y's unknown quarters.
  - Amazon, Microsoft, any other series, and a company with no full-year range known at the origin: B1_c.
  - Direction statements are never used.

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
VARIANTS = ["B0", "B1", "V1", "V2", "B2"]
BASELINES = ["B0", "B1"]
MODELS = ["V1", "V2", "B2"]  # the registered Holm family for N1 (register change "B2: TSMC före 2017Q3 ...")
# B2 may not be promoted before an independent review approves the extracted guidance values (register)
REVIEW_REQUIRED = {"B2": "villkorad: väntar på oberoende granskning av extraktionen (R2)"}
# company series -> (full-year guidance prefix, finance-lease series to subtract or None). Amazon and Microsoft
# guide on other definitions (net of incentives / incl. new finance leases at inception): B1.
B2_GUIDANCE = {"capex_meta": ("guid_capex_meta_cy", "fin_lease_meta"), "capex_googl": ("guid_capex_googl_cy", None)}
HOLM_ALPHA = engine.PROMOTION_ALPHA
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
    b2_sources: dict[str, str] = field(default_factory=dict)  # company series -> how B2 was formed
    b1_companies: float = float("nan")  # capex_hyp4 only: sum of the companies' B1 (diagnostic, not a variant)


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

    try:
        _b2(info, out)
    except NotAvailable as exc:
        out.levels["B2"] = float("nan")
        out.reasons["B2"] = str(exc)

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


def b1_path(y: pd.Series, targets: list) -> dict:
    """B1 (drift) for quarters after y's last known quarter L: y(L) * exp(h * mean of the last 4 log growths),
    h = quarters after L (constant drift; for h = 1 exactly B1). Raises NotAvailable without 4 growths."""
    if y.empty:
        raise NotAvailable(f"{y.name}: nothing known")
    last = y.index.max()
    full = pd.period_range(y.index.min(), last, freq="Q-DEC")
    yy = y.reindex(full)
    if len(yy) < 5 or yy.iloc[-5:].isna().any() or (yy.iloc[-5:] <= 0).any():
        raise NotAvailable(f"{y.name}: no 4 positive growth rates up to {last}")
    d = float(np.log(yy.iloc[-5:]).diff().iloc[1:].mean())
    return {p: float(yy.iloc[-1] * math.exp((p - last).n * d)) for p in targets}


def _year_quarters(q: pd.Period) -> pd.PeriodIndex:
    return pd.period_range(pd.Period(f"{q.year}Q1", freq="Q-DEC"), pd.Period(f"{q.year}Q4", freq="Q-DEC"),
                           freq="Q-DEC")


def b2_company(info: engine.InfoSet, series: str, quarter: pd.Period) -> tuple[float, str, float]:
    """(level, source, the company's own B1) of B2 for one company series and quarter, from the information set
    only."""
    y = info.get(series)
    y = y[y.index <= quarter]
    if quarter in y.index:  # this company has already filed the quarter: it is known, not forecast
        info.mark(series, [quarter])
        return float(y[quarter]), "known at origin", float(y[quarter])
    if quarter - 1 not in y.index:
        raise NotAvailable(f"{series} {quarter - 1} not known at {info.origin.date()}")
    year = _year_quarters(quarter)
    known = [p for p in year if p in y.index]
    unknown = [p for p in year if p not in y.index]
    b1 = b1_path(y, unknown)
    info.mark(series, list(y.index[-5:]))
    if series not in B2_GUIDANCE:
        return b1[quarter], "B1 (guidance definition not comparable)", b1[quarter]
    prefix, lease = B2_GUIDANCE[series]
    lo, hi = info.get(f"{prefix}_lo"), info.get(f"{prefix}_hi")
    yp = pd.Period(str(quarter.year), freq=lo.index.freq if len(lo) else "Y-DEC")
    if yp not in lo.index or yp not in hi.index:
        return b1[quarter], "B1 (no full-year range known)", b1[quarter]
    info.mark(f"{prefix}_lo", [yp])
    info.mark(f"{prefix}_hi", [yp])
    full_year = (float(lo[yp]) + float(hi[yp])) / 2
    source = "guidance"
    if lease:
        f = info.get(lease)
        f = f[f.index <= year[-1]]
        f_known = [p for p in year if p in f.index]
        f_unknown = [p for p in year if p not in f.index]
        try:
            f_b1 = b1_path(f, f_unknown) if f_unknown else {}
        except NotAvailable as exc:
            return b1[quarter], f"B1 ({lease}: {exc})", b1[quarter]
        info.mark(lease, f_known + list(f.index[-5:]))
        full_year -= float(sum(f[p] for p in f_known)) + sum(f_b1.values())
        source = "guidance - finance leases"
    info.mark(series, known)
    rest = full_year - float(sum(y[p] for p in known))
    if rest <= 0:
        return b1[quarter], "B1 (guidance minus known quarters <= 0)", b1[quarter]
    return rest * b1[quarter] / sum(b1.values()), source, b1[quarter]


def _b2(info: engine.InfoSet, out: Forecast) -> None:
    """B2 for out.target: per company (B2_GUIDANCE), summed for capex_hyp4; other series: B1 (no guidance)."""
    if out.target == "capex_hyp4":
        total = b1_total = 0.0
        for c in COMPANIES:
            level, source, b1q = b2_company(info, c, out.quarter)
            out.b2_sources[c] = source
            total += level
            b1_total += b1q
        out.levels["B2"] = total
        out.b1_companies = b1_total
    elif out.target in COMPANIES:
        out.levels["B2"], out.b2_sources[out.target], _ = b2_company(info, out.target, out.quarter)
    else:
        out.levels["B2"], out.b2_sources[out.target] = out.levels["B1"], "B1 (no guidance for this series)"


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
    outcomes = engine.first_vintages(table, target)
    fv = outcomes["value"]
    rows, known = [], []
    for q in fv.index[5:]:
        origin = origin_for(q)
        note = engine.known_at_origin(outcomes, q, origin, f"{target} {q}")
        if note:  # filed on or before the origin: a forecast of a known number is never scored
            known.append(note)
            continue
        try:
            f = forecast(engine.InfoSet(table, origin), target, q)
        except NotAvailable:
            continue
        row = {"unit": target, "quarter": q, "origin": origin.date(), "outcome": float(fv[q]),
               "n_train": f.n_train, "lambda": f.lam, "positions": str(f.positions),
               "reason": "; ".join(sorted(set(f.reasons.values()))),
               "b2_sources": "; ".join(f"{c}: {v}" for c, v in f.b2_sources.items()),
               "b2_guidance": sum(v.startswith("guidance") for v in f.b2_sources.values()),
               "B1_companies": (engine.log_error(f.b1_companies, fv[q]) if not math.isnan(f.b1_companies)
                                else float("nan"))}
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
        best = engine.best_baseline({b: m[b]["MAE"] for b in BASELINES}, BASELINES)
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
    full period and in the subperiod from 2023Q1. Otherwise B1. Several qualifying: lowest full-period MAE.
    A variant in REVIEW_REQUIRED (B2) that qualifies is only reported as conditional and never becomes champion."""
    checks = {}
    models = [v for v in MODELS if v in res["full"]["dm"]]
    for v in models:
        c = {}
        for per in ("full", "2023Q1-"):
            r = res[per]
            c[per] = engine.period_check(r["metrics"][v]["MAE"], r["metrics"][r["best_baseline"]]["MAE"],
                                         r["dm"][v]["holm_p"], HOLM_ALPHA)
        c["promoted"] = engine.passes({p: c[p] for p in ("full", "2023Q1-")})
        # The looser reading (Holm only in the full period) is reported, never used
        c["promoted_loose_reading"] = c["full"]["holm_ok"] and c["full"]["mae_ok"] and c["2023Q1-"]["mae_ok"]
        checks[v] = c
    d = engine.decide({v: checks[v]["promoted"] for v in models},
                      {v: res["full"]["metrics"][v]["MAE"] for v in models}, REVIEW_REQUIRED, DEFAULT_CHAMPION)
    return {"champion": d.champion, "checks": checks, "conditional": d.conditional}


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


def b2_usage(errors: pd.DataFrame) -> pd.DataFrame:
    """Per company: evaluated quarters where B2 used guidance, and the fallback reasons (common sample)."""
    e = errors[errors["in_period"]].dropna(subset=VARIANTS)
    rows = []
    for _, r in e.iterrows():
        for part in r["b2_sources"].split("; "):
            c, src = part.split(": ", 1)
            rows.append({"company": c, "quarter": str(r["quarter"]), "guidance": src.startswith("guidance"),
                         "source": src})
    return pd.DataFrame(rows)


def b2_info(errors: pd.DataFrame) -> dict:
    """Informational, not registered tests: B2 against B1 on every quarter where both exist (B2 needs no
    indicator, so the sample is longer than the registered one), and for capex_hyp4 the sum of the companies' B1
    (what B2 is without any guidance), to separate the guidance effect from the aggregation effect."""
    out = {}
    e = errors.dropna(subset=["B1", "B2"])
    e = e[e["b2_guidance"] > 0] if "b2_guidance" in e else e
    for name, d in (("all quarters with guidance", e), ("from 2023Q1", e[e["quarter"] >= SUBPERIOD])):
        if len(d) < 3:
            continue
        r = engine.pooled_dm(d.assign(quarter=d["quarter"].astype(str)), "B2", "B1") if d["unit"].nunique() > 1 \
            else evaluation.dm_test(d["B2"].to_numpy(), d["B1"].to_numpy())
        out[name] = {"first": str(d["quarter"].min()), "last": str(d["quarter"].max()), "n": len(d),
                     "MAE_B1": float(d["B1"].abs().mean()), "MAE_B2": float(d["B2"].abs().mean()),
                     "p": r.p, "mde": r.mde}
        if "B1_companies" in d and d["B1_companies"].notna().all():
            out[name]["MAE_B1_companies"] = float(d["B1_companies"].abs().mean())
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
        use = b2_usage(out[key]["errors"])
        if len(use):
            lines.append(f"{key} B2 usage (evaluated quarters with guidance / total, per company): "
                         + ", ".join(f"{c} {int(g['guidance'].sum())}/{len(g)}" for c, g in use.groupby("company")))
        for name, r in b2_info(out[key]["errors"]).items():
            lines.append(f"{key} info (not registered) B2 vs B1, {name} {r['first']}..{r['last']} n={r['n']}: "
                         f"MAE B1 {r['MAE_B1']:.2f}, B2 {r['MAE_B2']:.2f}"
                         + (f", sum of company B1 {r['MAE_B1_companies']:.2f}" if "MAE_B1_companies" in r else "")
                         + f", DM p {r['p']:.3f}, MDE {r['mde']:.2f}")
        p = out[key]["promotion"]
        lines.append(f"{key} promotion: champion {p['champion']} "
                     + ", ".join(f"{v}: passes rule={p['checks'][v]['promoted']}" for v in MODELS)
                     + f"; conditional: {p['conditional'] or '-'}")
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
    """forecasts/n1/<quarter>.json, written once (engine.write_live)."""
    path = Path(out_dir) / f"{target_quarter(pd.Timestamp(origin))}.json"
    return engine.write_live(path, origin, lambda: live_payload(table, origin), today)
