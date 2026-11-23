"""Nowcast N2: TSMC monthly revenue (docs/mattregister.md, section 4 and the later changes).

Pre-registered and implemented exactly: B0, B1 and V1, nothing else.

Timing
- Target month m. Origin = day 5 of month m+1 (register change 2026-11-23; earliest 6-K ever filed is day 6).
- Every input is read with observations.as_of(series, origin), TSMC's own history included.
- Outcome = first vintage of month m (earliest known_from). Error = 100 * (log forecast - log outcome).

Models (all in 100 * log points)
- B0: log y(m-1).
- B1: log y(m-12) + log y(m-1) - log y(m-13)   (seasonal naive growth).
- V1: B1 + ridge prediction of the B1 residual r = 100 * (log outcome - log B1).
  Indicator list after the register change: us_imports_tw_m only.
  Feature x = 100 * (log I(L) - log I(L-12)), L = latest month of the indicator that as_of(origin) returns
  (normally m-2: FT-900 comes ~41 days after month end). One feature per indicator.
  Training rows: every earlier target month k < m with its own real-time inputs (as_of(origin_k)) and its first
  vintage outcome, kept only if that outcome's known_from <= origin_m.
  Ridge: features standardised with the training rows' mean and std (ddof=0), unpenalised intercept
  (= training mean of r), penalty lambda on the standardised slopes.
  lambda chosen by time-series CV inside the training window only: the last CV_FOLDS training rows are each
  predicted by a fit on the rows before it (standardisation refitted per fold), loss = mean absolute error,
  grid LAMBDAS, ties go to the larger lambda.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ai_tracker import observations

TARGET = "tsmc_revenue_m"
INDICATORS = ["us_imports_tw_m"]  # register change 2026-11-23: us_ip_semis excluded, Korea/Taiwan blocked
DROPPED_INDICATORS = {
    "kr_semi_exports_20d": "BLOCKED (Korea customs, other egress IP needed)",
    "kr_semi_exports_m": "BLOCKED (MOTIE/KOSIS/KITA; ECOS needs key)",
    "tw_exports_m": "BLOCKED (Taiwan MOF/customs)",
    "us_ip_semis": "excluded pending FRED/ALFRED terms decision",
}
VARIANTS = ["B0", "B1", "V1"]
ORIGIN_DAY = 5
MIN_TRAIN = 60  # months of V1 training rows required before a month is evaluated
EVAL_START = pd.Period("2012-01", "M")
SUBPERIOD_START = pd.Period("2023-01", "M")
CV_FOLDS = 24
LAMBDAS = np.logspace(-1, 4, 11)


def origin_for(month: pd.Period) -> pd.Timestamp:
    """Forecast origin for target month m: day 5 of m+1."""
    nxt = (month + 1).start_time
    return pd.Timestamp(nxt.year, nxt.month, ORIGIN_DAY)


def target_for(origin: pd.Timestamp) -> pd.Period:
    return pd.Timestamp(origin).to_period("M") - 1


def first_vintages(table: pd.DataFrame, series: str = TARGET) -> pd.DataFrame:
    """Earliest vintage per period: columns value, known_from, on a monthly PeriodIndex."""
    t = table[table["series"] == series].sort_values("known_from").groupby("period").first()
    t.index = pd.PeriodIndex(t.index, freq="M")
    return t[["value", "known_from"]].sort_index()


def _vintage_dates(table: pd.DataFrame, series: str, origin) -> pd.Series:
    """known_from of the vintage as_of(series, origin) uses for each period (same selection rule)."""
    t = table[(table["series"] == series) & (table["known_from"] <= origin)]
    kf = t.sort_values("known_from").groupby("period")["known_from"].last()
    kf.index = pd.PeriodIndex(kf.index, freq="M")
    return kf


@dataclass
class Inputs:
    """Everything one target month needs, read only through as_of(origin)."""
    month: pd.Period
    origin: pd.Timestamp
    b0: float = np.nan  # 100 * log forecast
    b1: float = np.nan
    x: dict = field(default_factory=dict)  # indicator -> feature (100 * y/y log growth of latest known month)
    used: list = field(default_factory=list)  # (series, period, value, known_from) actually used


def month_inputs(month: pd.Period, table) -> Inputs:
    """`table`: the observation table, or a dict series -> its rows (faster for many months)."""
    origin = origin_for(month)
    inp = Inputs(month, origin)
    by_series = table if isinstance(table, dict) else {k: g for k, g in table.groupby("series")}
    y = observations.as_of(TARGET, origin, by_series[TARGET])
    y_kf = _vintage_dates(by_series[TARGET], TARGET, origin)
    need = [month - 1, month - 12, month - 13]
    if month - 1 in y.index:
        inp.b0 = 100 * np.log(y[month - 1])
    if all(p in y.index for p in need):
        inp.b1 = 100 * (np.log(y[month - 12]) + np.log(y[month - 1]) - np.log(y[month - 13]))
    for p in need:
        if p in y.index:
            inp.used.append((TARGET, str(p), float(y[p]), y_kf[p]))
    for ind in INDICATORS:
        if ind not in by_series:
            continue
        s = observations.as_of(ind, origin, by_series[ind])
        if s.empty:
            continue
        last = s.index.max()
        if last - 12 in s.index and s[last] > 0 and s[last - 12] > 0:
            inp.x[ind] = 100 * (np.log(s[last]) - np.log(s[last - 12]))
            kf = _vintage_dates(by_series[ind], ind, origin)
            for p in (last, last - 12):
                inp.used.append((ind, str(p), float(s[p]), kf[p]))
    return inp


# ------------------------------------------------------------------ ridge


def ridge_fit(X: np.ndarray, y: np.ndarray, lam: float):
    """Standardise X on these rows, unpenalised intercept, L2 penalty lam on standardised slopes."""
    mu, sd = X.mean(axis=0), X.std(axis=0)
    sd = np.where(sd > 0, sd, 1.0)
    Z = (X - mu) / sd
    beta = np.linalg.solve(Z.T @ Z + lam * np.eye(Z.shape[1]), Z.T @ (y - y.mean()))
    return mu, sd, y.mean(), beta


def ridge_predict(model, X: np.ndarray) -> np.ndarray:
    mu, sd, b0, beta = model
    return b0 + ((X - mu) / sd) @ beta


def choose_lambda(X: np.ndarray, y: np.ndarray) -> float:
    """Expanding one-step CV over the last CV_FOLDS rows of the training window.

    Same as refitting ridge_fit per fold and lambda; the standardisation (which does not depend on lambda) is
    computed once per fold.
    """
    n, k = X.shape
    errs = np.zeros((len(LAMBDAS), 0)).tolist()
    for j in range(max(n - CV_FOLDS, 2), n):
        Xj, yj = X[:j], y[:j]
        mu, sd = Xj.mean(axis=0), Xj.std(axis=0)
        sd = np.where(sd > 0, sd, 1.0)
        Z = (Xj - mu) / sd
        ZtZ, Zty, z_new = Z.T @ Z, Z.T @ (yj - yj.mean()), (X[j] - mu) / sd
        for i, lam in enumerate(LAMBDAS):
            beta = np.linalg.solve(ZtZ + lam * np.eye(k), Zty)
            errs[i].append(abs(y[j] - (yj.mean() + z_new @ beta)))
    loss = np.array([np.mean(e) for e in errs])
    # ties (within 1e-12) go to the larger lambda
    return float(LAMBDAS[max(i for i in range(len(LAMBDAS)) if loss[i] <= loss.min() + 1e-12)])


# ------------------------------------------------------------------ one forecast


@dataclass
class Forecast:
    month: pd.Period
    origin: pd.Timestamp
    logs: dict  # variant -> 100 * log forecast (NaN if not available)
    n_train: int
    lam: float
    inputs: Inputs

    def levels(self) -> dict:
        return {v: (float(np.exp(f / 100)) if np.isfinite(f) else None) for v, f in self.logs.items()}


def forecast_from(month: pd.Period, records: dict, outcomes: pd.DataFrame) -> Forecast:
    """V1 trained on earlier months whose first-vintage outcome is known at this month's origin.

    `records` maps month -> Inputs (each built with as_of at its own origin), `outcomes` = first_vintages().
    """
    inp = records[month]
    origin = inp.origin
    value, known = outcomes["value"].to_dict(), outcomes["known_from"].to_dict()
    rows = []
    for k in sorted(records):
        if k >= month or k not in value:
            continue
        rk = records[k]
        if known[k] > origin or not np.isfinite(rk.b1) or len(rk.x) != len(INDICATORS):
            continue
        rows.append(([rk.x[i] for i in INDICATORS], 100 * np.log(value[k]) - rk.b1))
    logs = {"B0": inp.b0, "B1": inp.b1, "V1": np.nan}
    lam = np.nan
    if rows and np.isfinite(inp.b1) and len(inp.x) == len(INDICATORS):
        X = np.array([r[0] for r in rows], dtype=float)
        y = np.array([r[1] for r in rows], dtype=float)
        if len(y) >= MIN_TRAIN:
            lam = choose_lambda(X, y)
            model = ridge_fit(X, y, lam)
            logs["V1"] = inp.b1 + float(ridge_predict(model, np.array([[inp.x[i] for i in INDICATORS]]))[0])
    return Forecast(month, origin, logs, len(rows), lam, inp)


def build_records(table: pd.DataFrame, last_month: pd.Period) -> dict:
    tsmc = first_vintages(table)
    start = tsmc.index.min() + 1  # B0 needs one month of history
    by_series = {k: g for k, g in table.groupby("series")}
    return {m: month_inputs(m, by_series) for m in pd.period_range(start, last_month, freq="M")}


def slim(table: pd.DataFrame) -> pd.DataFrame:
    return table[table["series"].isin([TARGET, *INDICATORS])]


def forecast(origin, table: pd.DataFrame) -> Forecast:
    """Live / single-origin forecast. Uses only rows with known_from <= origin (the table is truncated first)."""
    origin = pd.Timestamp(origin)
    if origin.day != ORIGIN_DAY:
        raise ValueError(f"origin must be day {ORIGIN_DAY} of the month (register), got {origin.date()}")
    t = slim(table)
    t = t[t["known_from"] <= origin]
    month = target_for(origin)
    records = build_records(t, month)
    return forecast_from(month, records, first_vintages(t))
