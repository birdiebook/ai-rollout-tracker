"""Nowcast N2: TSMC monthly revenue (docs/mattregister.md, section 4 and the later changes). Shared rolling-origin
contract (first vintage, outcome-known guard, promotion rule, immutable writer): engine.py.

    python -m ai_tracker.nowcast n2 --origin YYYY-MM-DD [--refresh]   live forecast -> forecasts/n2/<month>.json
    python -m ai_tracker.nowcast backtest n2                          pre-registered backtest, logged to experiments/runs/
    (python -m ai_tracker.nowcast_n2 [...] and python -m ai_tracker.nowcast_n2.backtest remain as compatibility shims)

Pre-registered and implemented exactly: B0, B1, V1 and B2, and in step 2 B3 (C2), nothing else.

B3 (step 2, register G-B and "C0 preciseras efter granskning R6", F-B1-F-B3, F-B9-F-B11; shared logic in b3.py):
B2 with the quarter's NT$ midpoint G x exp(m_k), k = the target month's position in its quarter (1-3). m_k is
estimated at the origin from TSMC's earlier quarters: d = log(U / G at the origin of that quarter's k-th month),
U = the quarter's three first vintages, only quarters whose U was known at the origin, shrunk per F-B3 (n >= 4).
Holm family {B3, DF} with DF at p = 1; comparator = the best of B0, B1, the champion (B2) and B2 (evaluate_step2).

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

Promotion rule (register section 4, "as N1", and the B2 changes), read conservatively:
- baseline = the better of B0 and B1 by MAE over the full evaluation period;
- DM test of each variant (V1, B2) against that baseline on the full period; Holm over the registered family
  {V1, B2} (before B2 the family was V1 alone);
- a variant passes only if Holm-p < 0.10 AND its MAE is lower than both B0 and B1 in the full period AND in the
  subperiod from 2023-01. Otherwise B1 is the main model.
- A passing variant in REVIEW_REQUIRED is only a conditional promotion (an independent review of the extracted
  guidance values comes first). It never sets the champion. R2 approved B2's extraction, so the set is empty.

Live forecast: writes forecasts/n2/<target month>.json once. Refuses to overwrite, refuses an origin that is not
day 5, refuses an origin after today (UTC; as_of would not be the real information set), and refuses when the
target month's outcome is already in the table (then it would not be a forecast).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from ai_tracker import evaluation, observations
from ai_tracker.nowcast import b3, engine, intervals

TARGET = "tsmc_revenue_m"
INDICATORS = ["us_imports_tw_m"]  # register change 2026-11-23: us_ip_semis excluded, Korea/Taiwan blocked
DROPPED_INDICATORS = {
    "kr_semi_exports_20d": "BLOCKED (Korea customs, other egress IP needed)",
    "kr_semi_exports_m": "BLOCKED (MOTIE/KOSIS/KITA; ECOS needs key)",
    "tw_exports_m": "BLOCKED (Taiwan MOF/customs)",
    "us_ip_semis": "not in the registered variants (Fed G.17 primary source since I7; needs a new registered variant)",
}
VARIANTS = ["B0", "B1", "V1", "B2", "B3"]
MODELS = ["V1", "B2"]  # the registered Holm family for N2 (register change "B2: TSMC före 2017Q3 ..."), locked
# Step 2 (register "C0 preciseras efter granskning R6", F-B9): the Holm family for N2 in step 2 is {B3, DF}. A member
# that is not evaluated yet enters with p = 1. F-B10: B3 is compared with the best of B0, B1, the current champion
# and B2 (the model B3 builds on); B3 itself is never a candidate.
STEP2_MODELS = ["B3", "DF"]
STEP2_UNEVALUATED = {"DF": "not built yet (C3)"}
STEP2_BUILDS_ON = {"B3": "B2"}
# F-B10 "nuvarande huvudmodell" = the champion when step 2 was registered; fixed, so that a rerun after a promotion
# never compares B3 with itself (review R7, R7-F2)
CHAMPION_AT_STEP2 = "B2"
# B2 may not be promoted before an independent review approves the extracted guidance values (register)
# Review R2 (docs/granskning/r2_guidance.md) approved the TSMC guidance extraction on 2026-11-23.
REVIEW_REQUIRED: dict[str, str] = {}
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
    """Earliest vintage per period: columns value, known_from, on a monthly PeriodIndex (engine.first_vintages)."""
    return engine.first_vintages(table, series)


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
    b2_known: float = np.nan  # sum of the quarter's months known at the origin (B3 reuses B2's pieces)
    b2_share: float = np.nan  # B1 share of month m among the quarter's unknown months
    b3: float = np.nan  # 100 * log forecast (= b2 when B2 falls back to B1)
    b3_source: str = ""
    b3_shift: dict = field(default_factory=dict)  # b3.Shift.as_dict() at this origin and position


def month_inputs(month: pd.Period, table) -> Inputs:
    """`table`: the observation table, or a dict series -> its rows (faster for many months)."""
    origin = origin_for(month)
    inp = Inputs(month, origin)
    by_series = table if isinstance(table, dict) else {k: g for k, g in table.groupby("series")}
    y = observations.as_of(TARGET, origin, by_series[TARGET])
    y_kf = engine.vintage_known_from(by_series[TARGET], origin)
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
            kf = engine.vintage_known_from(by_series[ind], origin)
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
    kf = engine.vintage_known_from(by_series[series], origin)
    return float(s[quarter]), kf[quarter]


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
    inp.b2_known = float(sum(y[k] for k in known))
    inp.b2_share = b1[m] / sum(b1.values())
    y_kf = engine.vintage_known_from(by_series[TARGET], inp.origin)
    for k in sorted(set(known) | {k - 12 for k in unknown} | {last, last - 12}):
        rec = (TARGET, str(k), float(y[k]), y_kf[k])
        if rec not in inp.used:
            inp.used.append(rec)
    inp.used.extend(used)


# ------------------------------------------------------------------ B3 (step 2, C2; shared logic in b3.py)


def position(month: pd.Period) -> int:
    """F-B1: the origin position k = 1-3 of target month m within its quarter."""
    return (month.month - 1) % 3 + 1


def b3_deviations(table: pd.DataFrame | None, records: dict | None = None,
                  outcomes: pd.DataFrame | None = None) -> pd.DataFrame:
    """TSMC's deviations d_{P,k} = log(U_P / G_P(o_{P,k})) (b3.py; F-B1, F-B2). G = the guidance B2 used at the
    origin of the quarter's k-th month (none where B2 fell back to B1). U_P = sum of the quarter's three months'
    first vintages in NT$, known from the latest of their known_from. Pass `records` and `outcomes` when built."""
    if records is None:
        t = slim(table)
        outcomes = first_vintages(t)
        if outcomes.empty:
            return b3.empty()
        records = build_records(t, outcomes.index.max())
    guidance = [(m.asfreq("Q-DEC"), position(m), r.origin, r.b2_guidance) for m, r in sorted(records.items())
                if r.b2_source.startswith("guidance")]
    quarters = {str(q): [(TARGET, k) for k in pd.period_range(q.asfreq("M", "s"), q.asfreq("M", "e"), freq="M")]
                for q in sorted({g[0] for g in guidance})}
    return b3.deviations("tsmc", guidance, b3.summed_outcomes({TARGET: outcomes}, quarters))


def b3_pool(table: pd.DataFrame, records: dict, outcomes: pd.DataFrame) -> pd.DataFrame:
    """B3's pool for N2: TSMC's deviations plus those of the other companies in its group ("quarterly_revenue",
    b3.BUILDERS; Nvidia once N3 adds its builder)."""
    own = b3_deviations(None, records, outcomes)
    other = b3.group_pool(table, b3.GROUPS["tsmc"], skip=("ai_tracker.nowcast.n2:b3_deviations",))
    parts = [p for p in (own, other) if len(p)]
    return pd.concat(parts, ignore_index=True) if parts else b3.empty()


def _b3(inp: Inputs, pool: pd.DataFrame) -> None:
    """B3 = B2 with the guidance midpoint x exp(m_k) (G-B, F-B1, F-B3). Same formulas and fallbacks as B2."""
    inp.b3, inp.b3_source, inp.b3_shift = inp.b2, inp.b2_source, {}
    if not np.isfinite(inp.b2) or not inp.b2_source.startswith("guidance"):
        return
    s = b3.shift(pool, "tsmc", position(inp.month), inp.origin)
    inp.b3_shift = s.as_dict()
    if s.m == 0.0:
        return
    rest = b3.scaled(inp.b2_guidance, s.m) - inp.b2_known
    if rest <= 0:
        inp.b3, inp.b3_source = inp.b1, "B1: guidance x exp(m) minus known months <= 0"
        return
    inp.b3 = 100 * np.log(rest * inp.b2_share)
    inp.b3_source = f"{inp.b2_source} x exp(m)"


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


def forecast_from(month: pd.Period, records: dict, outcomes: pd.DataFrame, pool: pd.DataFrame | None = None
                  ) -> Forecast:
    """V1 trained on earlier months whose first-vintage outcome is known at this month's origin.

    `records` maps month -> Inputs (each built with as_of at its own origin), `outcomes` = first_vintages().
    `pool`: B3's deviations (b3_pool()); None = TSMC's own deviations from `records` and `outcomes` (the group has no
    other company with deviations yet; run() and forecast() always pass b3_pool()). Filtered on the origin in b3.
    """
    inp = records[month]
    _b3(inp, b3_deviations(None, records, outcomes) if pool is None else pool)
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
    logs = {"B0": inp.b0, "B1": inp.b1, "V1": np.nan, "B2": inp.b2, "B3": inp.b3}
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
    outcomes = first_vintages(t)
    return forecast_from(month, records, outcomes, b3_pool(table[table["known_from"] <= origin], records, outcomes))


# ------------------------------------------------------------------ backtest

PROMOTION_P = engine.PROMOTION_ALPHA


@dataclass
class Result:
    frame: pd.DataFrame  # one row per evaluated month
    summary: pd.DataFrame  # one row per (period, variant)
    baseline: str
    holm_p: float  # V1's Holm-adjusted p (kept for the phase 3 report)
    promoted: bool  # a variant was promoted outright (not conditionally)
    champion: str
    reasons: list  # V1's checks
    holm: dict = None  # variant -> Holm-adjusted p over the registered family
    checks: dict = None  # variant -> list of PASS/FAIL lines
    conditional: dict = None  # variant -> status, for variants that pass but need a review first
    step2: dict = None  # step-2 family {B3, DF}: comparator, Holm, checks, champion (evaluate_step2)


COLUMNS = ["month", "origin", "outcome_known_from", "n_train", "lambda", "imports_lag", "b2_source", "b3_m", "b3_n",
           *[f"e_{v}" for v in VARIANTS]]


def run(table: pd.DataFrame) -> pd.DataFrame:
    """Forecasts and errors for every month with a first-vintage outcome that was not yet known at its origin.

    A month whose first 6-K is dated on or before the origin is a forecast of a known number: it is never
    scored (same guard as N1). The skipped months are listed in frame.attrs["known_at_origin"].
    """
    t = slim(table)
    outcomes = first_vintages(t)
    last = outcomes.index.max()
    records = build_records(t, last)
    pool = b3_pool(table, records, outcomes)  # the full table: other group members' series are not in slim()
    rows, known = [], []
    for m in sorted(records):
        if m not in outcomes.index:
            continue
        note = engine.known_at_origin(outcomes, m, records[m].origin, str(m))
        if note:
            known.append(note)
            continue
        f = forecast_from(m, records, outcomes, pool)
        y = 100 * np.log(outcomes.at[m, "value"])
        imp_last = [p for s, p, *_ in f.inputs.used if s == "us_imports_tw_m"]
        rows.append({
            "month": m, "origin": f.origin, "outcome_known_from": outcomes.at[m, "known_from"],
            "n_train": f.n_train, "lambda": f.lam,
            "imports_lag": (m - pd.Period(max(imp_last), "M")).n if imp_last else np.nan,
            "b2_source": f.inputs.b2_source,
            "b3_m": f.inputs.b3_shift.get("m", 0.0), "b3_n": f.inputs.b3_shift.get("n", 0),
            **{f"e_{v}": f.logs[v] - y for v in VARIANTS},
        })
    frame = pd.DataFrame(rows, columns=COLUMNS).set_index("month")
    frame.attrs["known_at_origin"] = known
    return frame


def evaluate(frame: pd.DataFrame) -> Result:
    variants = [v for v in VARIANTS if f"e_{v}" in frame]
    models = [v for v in MODELS if v in variants]
    ok = frame[[f"e_{v}" for v in variants]].notna().all(axis=1) & (frame["n_train"] >= MIN_TRAIN)
    start = max(EVAL_START, frame.index[ok].min())
    ev = frame[(frame.index >= start) & ok]
    periods = {"full": ev, "2023+": ev[ev.index >= SUBPERIOD_START]}
    mae = {k: {v: evaluation.metrics(d[f"e_{v}"])["MAE"] for v in variants} for k, d in periods.items()}
    baseline = engine.best_baseline(mae["full"])

    out, dm_full = [], {}
    for name, d in periods.items():
        base = engine.best_baseline(mae[name])
        label = f"{d.index.min()}..{d.index.max()}"
        for v in variants:
            m = evaluation.metrics(d[f"e_{v}"])
            row = {"period": name, "range": label, "variant": v, **m, "vs": "", "dm_diff": np.nan, "dm_p": np.nan,
                   "mde": np.nan}
            ref = baseline if name == "full" else base
            if v != ref:
                r = evaluation.dm_test(d[f"e_{v}"], d[f"e_{ref}"])
                row.update(vs=ref, dm_diff=r.mean_diff, dm_p=r.p, mde=r.mde)
                if name == "full" and v in models:
                    dm_full[v] = r
            out.append(row)
    summary = pd.DataFrame(out)
    holm = evaluation.holm({v: dm_full[v].p for v in models})
    checks, passed = {}, {}
    for v in models:
        # Holm on the full period only; MAE below both baselines in both periods
        per = {"full": engine.period_check(mae["full"][v], min(mae["full"]["B0"], mae["full"]["B1"]), holm[v],
                                           PROMOTION_P),
               "2023+": engine.period_check(mae["2023+"][v], min(mae["2023+"]["B0"], mae["2023+"]["B1"]))}
        c = {
            f"Holm-p {holm[v]:.3f} < {PROMOTION_P} (family {'+'.join(models)})": per["full"]["holm_ok"],
            "lower MAE than B0 and B1, full period": per["full"]["mae_ok"],
            "lower MAE than B0 and B1, 2023+": per["2023+"]["mae_ok"],
        }
        checks[v] = [f"{'PASS' if ok_ else 'FAIL'}: {k}" for k, ok_ in c.items()]
        passed[v] = engine.passes(per)
    d = engine.decide(passed, mae["full"], REVIEW_REQUIRED, "B1")
    return Result(ev, summary, baseline, holm.get("V1", np.nan), bool(d.winners), d.champion, checks.get("V1", []),
                  holm, checks, d.conditional, evaluate_step2(ev, periods, mae, variants))


def evaluate_step2(ev: pd.DataFrame, periods: dict, mae: dict, variants: list) -> dict:
    """Step-2 family {B3, DF} (F-B9, F-B10, F-B11), on the same months as evaluate().

    Comparator for B3 = the best by full-period MAE of B0, B1, the champion at step 2 (CHAMPION_AT_STEP2) and B2 (the
    model B3 builds on); DM of B3 against it on the full period, Holm over {B3, DF} with DF at p = 1 (not built). Passing needs Holm-p <
    0.10 (full period, "as before for N2") and a lower MAE than every comparator candidate in the full period and from
    2023-01. A passing variant replaces the champion only if not in REVIEW_REQUIRED (it beats the champion by
    construction). The locked phase 3-4 family {V1, B2} is not recomputed."""
    cands = [c for c in dict.fromkeys(["B0", "B1", CHAMPION_AT_STEP2, STEP2_BUILDS_ON["B3"]]) if c != "B3"]
    cands = [c for c in cands if c in variants]
    p, dm, comp = {}, {}, None
    if "B3" in variants and len(ev) >= 3:
        comp = engine.best_baseline(mae["full"], cands)
        r = evaluation.dm_test(ev["e_B3"], ev[f"e_{comp}"])
        dm = {"vs": comp, "mean_diff": r.mean_diff, "p": r.p, "mde": r.mde, "n": r.n}
        p["B3"] = r.p if np.isfinite(r.p) else 1.0
    else:
        p["B3"] = 1.0
    p.update({v: 1.0 for v in STEP2_UNEVALUATED})
    holm = evaluation.holm(p)
    checks, passed = {}, {}
    if comp is not None:
        per = {"full": engine.period_check(mae["full"]["B3"], min(mae["full"][c] for c in cands), holm["B3"],
                                           PROMOTION_P),
               "2023+": engine.period_check(mae["2023+"]["B3"], min(mae["2023+"][c] for c in cands))}
        c = {f"Holm-p {holm['B3']:.3f} < {PROMOTION_P} (step-2 family {'+'.join(STEP2_MODELS)}, DF p = 1)":
             per["full"]["holm_ok"],
             f"lower MAE than {'/'.join(cands)}, full period": per["full"]["mae_ok"],
             f"lower MAE than {'/'.join(cands)}, 2023+": per["2023+"]["mae_ok"]}
        checks["B3"] = [f"{'PASS' if ok_ else 'FAIL'}: {k}" for k, ok_ in c.items()]
        passed["B3"] = engine.passes(per)
    d = engine.decide(passed, {v: mae["full"][v] for v in passed}, REVIEW_REQUIRED, CHAMPION_AT_STEP2)
    return {"candidates": cands, "comparator": comp, "dm": dm, "p": p, "holm": holm, "checks": checks,
            "passed": passed, "unevaluated": dict(STEP2_UNEVALUATED), "champion": d.champion,
            "conditional": d.conditional}


# ------------------------------------------------------------------ forecast distributions (C1, grind G-C)


def interval_scores(frame: pd.DataFrame) -> pd.DataFrame:
    """Rolling-origin error distributions (intervals.score_frame) on run()'s frame. Every scored month feeds the
    pools, also months before the evaluation period; an error enters only from its outcome's first-vintage
    known_from (6-K filing date)."""
    errors = frame[[f"e_{v}" for v in VARIANTS]].rename(columns=lambda c: c[2:])
    return intervals.score_frame(errors, frame["origin"], frame["outcome_known_from"])


def evaluate_intervals(frame: pd.DataFrame) -> dict:
    """Interval evaluation (intervals.evaluate): each variant on every month of run()'s frame where it has a
    distribution, full period and from 2023-01. Reported only; the champion is decided by evaluate() on MAE."""
    scored = interval_scores(frame)
    return {"full": intervals.evaluate(scored, VARIANTS),
            "2023+": intervals.evaluate(scored[scored["period"] >= SUBPERIOD_START], VARIANTS)}


def live_distribution(fc: Forecast, table: pd.DataFrame, live_dir: Path | None = None) -> dict:
    """The live file's `distribution` block (grind G-C, F-C4): each variant's pool = the backtest reconstruction on
    the rows known at the origin (run() on the truncated table: earlier origins see the same as_of, and only
    outcomes known at the origin exist) plus the committed live forecasts in `live_dir` whose outcome is known at
    the origin (a live error replaces the reconstruction of its month). intervals.live_block filters on known_from
    again."""
    t = slim(table)
    t = t[t["known_from"] <= fc.origin]
    frame = run(t)
    errors = frame[[f"e_{v}" for v in VARIANTS]].rename(columns=lambda c: c[2:])
    files = sorted(Path(live_dir).glob("*.json")) if live_dir else []
    live, live_kf = intervals.live_errors(files, first_vintages(t), VARIANTS, fc.origin)
    errors, known = intervals.merge_live(errors, frame["outcome_known_from"], live, live_kf)
    return intervals.live_block(fc.logs, errors, known, fc.origin, live_index=live.index)


def b2_usage(frame: pd.DataFrame) -> pd.DataFrame:
    """Per quarter: months where B2 used guidance and months where it fell back to B1 (with the reason)."""
    f = frame.assign(quarter=[str(m.asfreq("Q-DEC")) for m in frame.index],
                     used=frame["b2_source"].str.startswith("guidance"))
    return f.groupby("quarter").agg(months=("used", "size"), guidance=("used", "sum"),
                                    sources=("b2_source", lambda s: "; ".join(sorted(set(s)))))


def log(result: Result):
    rows = [{"target": TARGET, "variant": r.variant, "period": f"{r.period} {r.range}", "n": r.n,
             "MAE": round(r.MAE, 4), "dm_p_vs_baseline": "" if np.isnan(r.dm_p) else round(r.dm_p, 4)}
            for r in result.summary.itertuples()]
    s2 = result.step2 or {}
    if s2.get("comparator"):  # step-2 test of B3 against its F-B10 comparator (row label says so)
        full = result.summary[(result.summary["period"] == "full") & (result.summary["variant"] == "B3")].iloc[0]
        rows.append({"target": TARGET, "variant": f"B3 step2 vs {s2['comparator']} (Holm {s2['holm']['B3']:.4f})",
                     "period": f"full {full['range']}", "n": int(full["n"]), "MAE": round(float(full["MAE"]), 4),
                     "dm_p_vs_baseline": round(float(s2["dm"]["p"]), 4)})
    return evaluation.log_run("n2_tsmc", rows)


def markdown(result: Result) -> str:
    lines = ["| Period | Variant | n | MAE | RMSE | Bias | vs | MAE diff | DM p | MDE |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in result.summary.itertuples():
        f = lambda x: "" if np.isnan(x) else f"{x:.3f}"  # noqa: E731
        lines.append(f"| {r.period} {r.range} | {r.variant} | {r.n} | {r.MAE:.3f} | {r.RMSE:.3f} | {r.bias:+.3f} | "
                     f"{r.vs} | {f(r.dm_diff)} | {f(r.dm_p)} | {f(r.mde)} |")
    return "\n".join(lines)


def main_backtest():
    table = observations.load()
    frame = run(table)
    res = evaluate(frame)
    print(markdown(res))
    print(f"\nBaseline (best of B0/B1, full period): {res.baseline}. Holm-p over {MODELS}: {res.holm}")
    for v, lines in res.checks.items():
        print(f"{v}: " + " | ".join(lines))
    print(f"Promoted outright: {res.promoted}. Champion: {res.champion}. Conditional: {res.conditional or '-'}")
    s2 = res.step2
    print(f"\nStep 2 family {STEP2_MODELS} (DF unevaluated, p = 1): comparator for B3 = {s2['comparator']} "
          f"(best of {s2['candidates']}), DM {s2['dm']}, raw p {s2['p']}, Holm {s2['holm']}")
    for v, lines in s2["checks"].items():
        print(f"{v}: " + " | ".join(lines))
    print(f"Step 2 champion: {s2['champion']}. Conditional: {s2['conditional'] or '-'}")
    ev3 = res.frame
    print(f"B3 shifted (m != 0) in {(ev3['b3_m'] != 0).sum()} of {len(ev3)} evaluated months; "
          f"m range {ev3['b3_m'].min():+.4f}..{ev3['b3_m'].max():+.4f}")
    ev = res.frame
    use = b2_usage(ev)
    print(f"B2 used guidance in {int(use['guidance'].sum())} of {int(use['months'].sum())} months; "
          f"fallbacks: {ev.loc[~ev['b2_source'].str.startswith('guidance'), 'b2_source'].value_counts().to_dict()}")
    print(f"\nOutcome known at origin: {len(frame.attrs['known_at_origin'])} months skipped "
          f"{frame.attrs['known_at_origin'] or ''}; scored with known outcome (must be 0): "
          f"{(ev['outcome_known_from'] <= ev['origin']).sum()}")
    print(f"Imports lag (months, target - latest known import month): {ev['imports_lag'].value_counts().to_dict()}")
    print(f"Lambda chosen: {ev['lambda'].value_counts().sort_index().to_dict()}")
    sub = res.summary[(res.summary["period"] == "2023+") & res.summary["variant"].isin(MODELS)]
    print(f"Holm over {MODELS} in 2023+ (reported; the rule's Holm test is on the full period): "
          f"{evaluation.holm(dict(zip(sub['variant'], sub['dm_p'])))}")
    pos = ev.assign(pos=[(m.month - 1) % 3 + 1 for m in ev.index])
    for k, d in pos.groupby("pos"):
        r = evaluation.dm_test(d["e_B2"], d["e_B1"])
        r3 = evaluation.dm_test(d["e_B3"], d["e_B2"])
        print(f"info (not registered) month {k} of the quarter, n={len(d)}: MAE B1 {d['e_B1'].abs().mean():.2f}, "
              f"B2 {d['e_B2'].abs().mean():.2f}, bias B2 {d['e_B2'].mean():+.2f}, DM p {r.p:.4f}; "
              f"B3 {d['e_B3'].abs().mean():.2f}, bias B3 {d['e_B3'].mean():+.2f}, DM p B3 vs B2 {r3.p:.4f}")
    if intervals.ENABLED:  # grind G-C: off until the register entry exists
        for name, r in evaluate_intervals(frame).items():
            print("\n" + intervals.markdown(r, f"N2 intervals {name}"))
    print(f"Run log: {log(res)}")
    return res


# ------------------------------------------------------------------ live forecast

FORECAST_DIR = evaluation.REPO / "forecasts" / "n2"
# Set mechanically by the pre-registered promotion rule (evaluate(), docs/resultat/n2.md). B1 unless a model passes.
# B2 promoted 2026-11-23 by the registered rule after review R2 approved the TSMC guidance. B3 promoted 2026-11-24 by
# the step-2 rule (evaluate_step2 against the fixed F-B10 comparator CHAMPION_AT_STEP2 = B2) after review R7
# (docs/granskning/r7_b3_n2.md) and with Nvidia in the F-B3 group mean per the register entry 2026-11-24 "B3: Nvidia i
# gruppmedlet för kvartalsintäkt": Holm-p 0.059 in {B3, DF}, MAE below B0/B1/B2 in both periods (docs/resultat/n2.md).
# A decision taken is not changed by reruns.
CHAMPION = "B3"


def payload(fc: Forecast, table: pd.DataFrame, champion: str = CHAMPION, live_dir: Path | None = None) -> dict:
    levels = fc.levels()
    if levels.get(champion) is None:
        raise RuntimeError(f"champion {champion} has no forecast for {fc.month}")
    t = slim(table)
    out = {
        "target": TARGET,
        "unit": "mn TWD",
        "month": str(fc.month),
        "origin": str(fc.origin.date()),
        "champion": champion,
        "value": levels[champion],
        "variants": levels,
        "v1": {"n_train": fc.n_train, "lambda": fc.lam, "features": fc.inputs.x},
        "b3": {"source": fc.inputs.b3_source, "shift": fc.inputs.b3_shift},
        "inputs": [{"series": s, "period": p, "value": v, "known_from": str(pd.Timestamp(k).date())}
                   for s, p, v, k in fc.inputs.used],
        "table_max_fetched_at": str(pd.Timestamp(t["fetched_at"].max()).date()) if len(t) else None,
        **({"distribution": live_distribution(fc, table, live_dir)} if intervals.ENABLED else {}),
    }
    from ai_tracker.nowcast import df  # C3 shadow on B2 (F-B19); late import: df imports this module

    return df.attach_live(out, "N2", table, fc.origin, fc.month, levels)


def write(origin, table: pd.DataFrame, out_dir: Path = FORECAST_DIR, champion: str = CHAMPION, today=None) -> Path:
    """forecasts/n2/<month>.json, written once (engine.write_live; the timestamp field is created_utc)."""
    month = target_for(pd.Timestamp(origin))

    def build() -> dict:
        if str(month) in set(table.loc[table["series"] == TARGET, "period"]):
            raise RuntimeError(f"outcome for {month} is already in the table; this would not be a live forecast")
        return payload(forecast(origin, table), table, champion, live_dir=Path(out_dir))

    return engine.write_live(Path(out_dir) / f"{month}.json", origin, build, today, stamp_key="created_utc")


def main_live(argv=None):
    """Live N2 forecast: --origin YYYY-MM-DD [--refresh] [--out-dir D]. Prints the written file."""
    ap = argparse.ArgumentParser(prog="python -m ai_tracker.nowcast n2", description=main_live.__doc__)
    add_live_args(ap)
    run_live(ap.parse_args(argv))
    return 0


def add_live_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--origin", required=True, help="forecast origin, day 5 of the month after the target month")
    ap.add_argument("--refresh", action="store_true", help="fetch the target, indicators and guidance series first")
    ap.add_argument("--out-dir", default=str(FORECAST_DIR))
    ap.add_argument("--table", default=None, help="observation table (default data/observations.parquet)")


def run_live(a: argparse.Namespace) -> Path:
    if a.refresh:
        from ai_tracker.pipeline import live_keys  # same inputs as the scheduled run, incl. B2's guidance

        observations.refresh(live_keys("n2"))
    path = write(a.origin, observations.load(Path(a.table) if a.table else None), Path(a.out_dir))
    print(path.read_text(encoding="utf-8"))
    return path
