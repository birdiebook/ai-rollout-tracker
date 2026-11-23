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
- B2 (TSMC's own quarterly guidance; register changes "B2 (bolagens guidance) läggs till för N1 och N2" and
  "B2: TSMC före 2017Q3 och definitionen för N1"):
  G = the quarter's guided revenue in NT$, as known at the origin (as_of: a mid-quarter update is a later vintage
  and is used only from its own known_from). Quarters up to 2017Q2: midpoint of the NT$ range. From 2017Q3:
  midpoint of the US$ range x the assumed USD/NT$ rate. B2(m) = (G - sum of the quarter's months known at the
  origin) x B1 share, B1 share = B1(m) / sum of B1 over the quarter's unknown months (m included).
  B1 for a later unknown month j is the same seasonal naive growth from the latest known month L = m-1:
  y(j-12) * y(L) / y(L-12) (identical to iterating B1 month by month).
  Fallback to B1 (and the reason recorded) when the quarter has no guidance known at the origin, when lo or hi
  of the range or (from 2017Q3) the rate is missing, or when G - known months <= 0.
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
VARIANTS = ["B0", "B1", "V1", "B2"]
MODELS = ["V1", "B2"]  # the registered Holm family for N2 (register change "B2: TSMC före 2017Q3 ...")
# B2 may not be promoted before an independent review approves the extracted guidance values (register)
REVIEW_REQUIRED = {"B2": "villkorad: väntar på oberoende granskning av extraktionen (R2)"}
USD_FROM = pd.Period("2017Q3", "Q-DEC")  # TSMC guided in NT$ up to 2017Q2, in US$ from 2017Q3
GUIDANCE = {"twd_lo": "tsmc_guid_rev_twd_lo", "twd_hi": "tsmc_guid_rev_twd_hi",
            "usd_lo": "tsmc_guid_rev_usd_lo", "usd_hi": "tsmc_guid_rev_usd_hi", "fx": "tsmc_guid_fx"}
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
    b2: float = np.nan  # 100 * log forecast (= b1 when B2 falls back)
    b2_source: str = ""  # "guidance NT$" | "guidance US$xFX" | "B1: <reason>"
    b2_guidance: float = np.nan  # G, the quarter's guided revenue in mn NT$ (NaN on fallback)


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
    _b2(inp, y, by_series)
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


def _guidance_value(key: str, quarter: pd.Period, origin, by_series: dict):
    """(value, known_from) of guidance series GUIDANCE[key] for `quarter` as known at `origin`, or None."""
    series = GUIDANCE[key]
    if series not in by_series:
        return None
    s = observations.as_of(series, origin, by_series[series])
    if quarter not in s.index:
        return None
    kf = _vintage_dates_q(by_series[series], origin)
    return float(s[quarter]), kf[quarter]


def _vintage_dates_q(rows: pd.DataFrame, origin) -> pd.Series:
    t = rows[rows["known_from"] <= origin]
    kf = t.sort_values("known_from").groupby("period")["known_from"].last()
    kf.index = pd.PeriodIndex(kf.index, freq="Q-DEC")
    return kf


def quarter_guidance(quarter: pd.Period, origin, by_series: dict) -> tuple[float, str, list]:
    """G in mn NT$ for `quarter` as known at `origin`: (G, source, used rows), or (NaN, reason, [])."""
    if quarter < USD_FROM:
        lo, hi = (_guidance_value(k, quarter, origin, by_series) for k in ("twd_lo", "twd_hi"))
        if lo is None or hi is None:
            return np.nan, "no NT$ guidance known", []
        used = [(GUIDANCE["twd_lo"], str(quarter), *lo), (GUIDANCE["twd_hi"], str(quarter), *hi)]
        return (lo[0] + hi[0]) / 2, "guidance NT$", used
    lo, hi, fx = (_guidance_value(k, quarter, origin, by_series) for k in ("usd_lo", "usd_hi", "fx"))
    if lo is None or hi is None:
        return np.nan, "no US$ guidance known", []
    if fx is None:
        return np.nan, "US$ guidance without a known FX assumption", []
    used = [(GUIDANCE["usd_lo"], str(quarter), *lo), (GUIDANCE["usd_hi"], str(quarter), *hi),
            (GUIDANCE["fx"], str(quarter), *fx)]
    return (lo[0] + hi[0]) / 2 * fx[0], "guidance US$xFX", used


def _b2(inp: Inputs, y: pd.Series, by_series: dict) -> None:
    """B2 for inp.month from TSMC's quarterly guidance (module docstring). Needs B1; falls back to it."""
    m = inp.month
    if not np.isfinite(inp.b1):
        return
    inp.b2 = inp.b1
    quarter = m.asfreq("Q-DEC")
    months = pd.period_range(quarter.asfreq("M", "s"), quarter.asfreq("M", "e"), freq="M")
    g, source, used = quarter_guidance(quarter, inp.origin, by_series)
    if not np.isfinite(g):
        inp.b2_source = f"B1: {source}"
        return
    last = m - 1  # B1 needs m-1, so every earlier month of the quarter is known as well
    known = [k for k in months if k < m]
    unknown = [k for k in months if k >= m]
    if any(k not in y.index for k in known) or any(k in y.index for k in unknown) \
            or any(k - 12 not in y.index for k in unknown):
        inp.b2_source = "B1: quarter months not as expected at the origin"
        return
    b1 = {k: float(y[k - 12] * y[last] / y[last - 12]) for k in unknown}
    rest = g - float(sum(y[k] for k in known))
    if rest <= 0:
        inp.b2_source = "B1: guidance minus known months <= 0"
        return
    inp.b2 = 100 * np.log(rest * b1[m] / sum(b1.values()))
    inp.b2_source = source
    inp.b2_guidance = g
    y_kf = _vintage_dates(by_series[TARGET], TARGET, inp.origin)
    for k in sorted(set(known) | {k - 12 for k in unknown} | {last, last - 12}):
        rec = (TARGET, str(k), float(y[k]), y_kf[k])
        if rec not in inp.used:
            inp.used.append(rec)
    inp.used.extend(used)


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
    logs = {"B0": inp.b0, "B1": inp.b1, "V1": np.nan, "B2": inp.b2}
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
    return table[table["series"].isin([TARGET, *INDICATORS, *GUIDANCE.values()])]


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
