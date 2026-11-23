"""Probabilistic forecasts for the nowcasts: a forecast distribution from the model's own past out-of-sample errors.

OFF until grind G-C is registered. `ENABLED` stays False until docs/mattregister.md has the entry for grind G-C
(interval levels, CRPS, calibration rule; written by track C0, see docs/steg2/plan.md section 5 and the proposal in
docs/steg2/c1_forslag.md). While it is False nothing here is called by the backtests, the live writers, the scorecard
or the site; the code is exercised by the tests on synthetic data only. Turning it on is a one-line change after the
register entry exists, and the first real run is the registered one.

Method (proposal C1, docs/steg2/c1_forslag.md):
- Everything is in error space, e = 100 * (log forecast - log outcome), the unit the backtests already use.
- Error pool for model v at origin t: every earlier out-of-sample error of v whose outcome (first vintage) has
  known_from <= t. An error enters the pool on the day its outcome becomes known, never earlier (`pool`). The pool
  is expanding: nothing is dropped.
- n = pool size. n < MIN_ERRORS: no distribution. MIN_ERRORS <= n < MIN_EMPIRICAL: Student-t prediction
  distribution for a new draw from a normal with unknown mean and variance, e ~ mean + sd * sqrt(1 + 1/n) * t(n-1)
  (exact coverage for iid normal errors; it is the small-sample inflation). n >= MIN_EMPIRICAL: the empirical
  distribution of the pool.
- Empirical quantiles: Hyndman-Fan type 6 (position p(n+1), numpy "weibull"). For exchangeable errors the interval
  between the type-6 quantiles (1-L)/2 and (1+L)/2 covers a new error with probability L (exact when the positions
  are integers). It needs p(n+1) >= 1 for p = 0.025, i.e. n >= 39, which is why MIN_EMPIRICAL is 40 and not 20:
  with 20 errors the 2.5 % and 97.5 % quantiles are the sample min and max, and [min, max] covers only
  19/21 = 90.5 %.
- Outcome space: y = f - e, so Q_y(p) = f - Q_e(1 - p), and an interval covers y iff Q_e((1-L)/2) <= e <=
  Q_e((1+L)/2). PIT of the outcome = P(Y <= y) = P(E >= e) = 1 - F_e(e).
- CRPS (exact, in log x100 points): empirical distribution of the pool, mean|x_i - e| - sum|x_i - x_j| / (2 n^2);
  Student-t: closed form (Jordan, Krüger and Lerch 2019, scoringRules::crps_t). CRPS is translation invariant and
  y -> f - y is a reflection, so CRPS(F_y, y) = CRPS(F_e, e).
- PIT for the empirical case is the mid-rank (#{x > e} + 0.5 #{x = e} + 0.5) / (n + 1): discrete uniform for
  exchangeable errors, deterministic (no randomisation).
- Coverage test per level: hit h = 1{covered}; t = (mean h - L) / se, se^2 = max(Newey-West long-run variance of h,
  L(1-L)) / n (lag rule as in evaluation.py; the binomial floor avoids a zero variance when every forecast hits);
  p from Student's t with n-1 df; Holm over the levels.

Statistics use numpy only (as evaluation.py).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd

from ai_tracker import evaluation

# Grind G-C (docs/steg2/plan.md, section 5): stays False until docs/mattregister.md has the G-C entry. Do not turn
# it on to look at results first; the register entry comes before any real run (CLAUDE.md, förregistrering).
ENABLED = False
REGISTER_REF = "grind G-C, docs/mattregister.md"

QUANTILES = (0.025, 0.10, 0.25, 0.50, 0.75, 0.90, 0.975)
LEVELS = (0.50, 0.80, 0.95)
MIN_ERRORS = 8  # fewer past errors: no distribution
MIN_EMPIRICAL = 40  # from here the empirical pool (type 6 reaches the 2.5 % quantile from n = 39)
PIT_BINS = 10
CALIBRATION_ALPHA = 0.10  # proposed: a level fails calibration at Holm-p < 0.10 (as the promotion rule)
POOL_DECIMALS = 4  # errors stored in the live JSON (0.0001 log x100 points)


def level_key(level: float) -> str:
    return f"{round(level * 100):d}"


def quantile_key(p: float) -> str:
    return f"{p:g}"


# ------------------------------------------------------------------ Student t helpers (numpy only)


def t_cdf(z: float, df: float) -> float:
    """CDF of Student's t with `df` degrees of freedom."""
    if z == 0:
        return 0.5
    tail = evaluation.t_two_sided_p(z, df) / 2  # P(T > |z|)
    return 1 - tail if z > 0 else tail


def t_pdf(z: float, df: float) -> float:
    c = math.lgamma((df + 1) / 2) - math.lgamma(df / 2) - 0.5 * math.log(df * math.pi)
    return math.exp(c - (df + 1) / 2 * math.log1p(z * z / df))


@lru_cache(maxsize=4096)
def t_ppf(p: float, df: float) -> float:
    """Quantile of Student's t by bisection on t_cdf (monotone; 1e-10 absolute)."""
    if not 0 < p < 1:
        raise ValueError(f"p must be in (0, 1), got {p}")
    if p == 0.5:
        return 0.0
    lo, hi = -1.0, 1.0
    while t_cdf(lo, df) > p:
        lo *= 2
    while t_cdf(hi, df) < p:
        hi *= 2
    for _ in range(200):
        mid = (lo + hi) / 2
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-10:
            break
    return (lo + hi) / 2


def _log_beta(a: float, b: float) -> float:
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def crps_t(y: float, df: float, loc: float = 0.0, scale: float = 1.0) -> float:
    """Closed-form CRPS of a location-scale Student t (df > 1)."""
    if df <= 1:
        raise ValueError("CRPS of Student's t needs df > 1")
    z = (y - loc) / scale
    ratio = math.exp(_log_beta(0.5, df - 0.5) - 2 * _log_beta(0.5, df / 2))
    return scale * (z * (2 * t_cdf(z, df) - 1) + 2 * t_pdf(z, df) * (df + z * z) / (df - 1)
                    - 2 * math.sqrt(df) / (df - 1) * ratio)


def norm_cdf(z: float) -> float:
    return 0.5 * math.erfc(-z / math.sqrt(2))


def crps_normal(y: float, loc: float = 0.0, scale: float = 1.0) -> float:
    """Closed-form CRPS of N(loc, scale^2) (Gneiting and Raftery 2007). Used as the reference in the tests."""
    z = (y - loc) / scale
    pdf = math.exp(-z * z / 2) / math.sqrt(2 * math.pi)
    return scale * (z * (2 * norm_cdf(z) - 1) + 2 * pdf - 1 / math.sqrt(math.pi))


def crps_sample(sample, y: float) -> float:
    """Exact CRPS of the empirical distribution of `sample` (point masses 1/n) at y:
    mean|x_i - y| - sum_ij |x_i - x_j| / (2 n^2), the double sum from the sorted sample in O(n log n)."""
    x = np.sort(np.asarray(sample, dtype=float))
    n = len(x)
    if n == 0:
        return float("nan")
    i = np.arange(1, n + 1)
    pair = 2 * float(np.sum((2 * i - n - 1) * x))  # sum_ij |x_i - x_j|
    return float(np.mean(np.abs(x - y)) - pair / (2 * n * n))


def pinball(q: float, p: float, y: float) -> float:
    """Quantile (pinball) loss of quantile forecast q at level p."""
    return (p - (y < q)) * (y - q)


# ------------------------------------------------------------------ the distribution of one forecast's error


@dataclass(frozen=True)
class ErrorDistribution:
    """Predictive distribution of a forecast's error e = 100 * (log f - log y), from the past errors in `pool`."""

    method: str  # "empirical" | "student_t"
    pool: tuple  # sorted past errors
    loc: float = float("nan")  # student_t: mean of the pool
    scale: float = float("nan")  # student_t: sd (ddof 1) * sqrt(1 + 1/n)
    df: float = float("nan")  # student_t: n - 1

    @property
    def n(self) -> int:
        return len(self.pool)

    @classmethod
    def from_pool(cls, pool) -> "ErrorDistribution | None":
        """The registered rule: None below MIN_ERRORS, Student t below MIN_EMPIRICAL, else empirical."""
        x = np.asarray(pool, dtype=float)
        x = np.sort(x[np.isfinite(x)])
        n = len(x)
        if n < MIN_ERRORS:
            return None
        sd = float(np.std(x, ddof=1))
        if n < MIN_EMPIRICAL and sd > 0:  # a constant pool (only in synthetic data) stays a point mass
            return cls("student_t", tuple(float(v) for v in x), float(np.mean(x)), sd * math.sqrt(1 + 1 / n),
                       float(n - 1))
        return cls("empirical", tuple(float(v) for v in x))

    # -- error space
    def quantile(self, p: float) -> float:
        if self.method == "student_t":
            return self.loc + self.scale * t_ppf(p, self.df)
        return float(np.quantile(np.asarray(self.pool), p, method="weibull"))

    def interval(self, level: float) -> tuple[float, float]:
        """Central `level` interval of the error."""
        return self.quantile((1 - level) / 2), self.quantile((1 + level) / 2)

    def covers(self, e: float, level: float) -> bool:
        lo, hi = self.interval(level)
        return bool(lo <= e <= hi)

    def crps(self, e: float) -> float:
        if self.method == "student_t":
            return crps_t(e, self.df, self.loc, self.scale)
        return crps_sample(self.pool, e)

    def pit(self, e: float) -> float:
        """PIT of the *outcome*: P(Y <= y) = P(E >= e). Mid-rank for the empirical case."""
        if self.method == "student_t":
            return 1 - t_cdf((e - self.loc) / self.scale, self.df)
        x = np.asarray(self.pool)
        above, ties = int(np.sum(x > e)), int(np.sum(x == e))
        return (above + 0.5 * ties + 0.5) / (self.n + 1)

    def quantile_score(self, e: float, quantiles=QUANTILES) -> float:
        """Mean pinball loss of the quantile set (error space; equals the outcome-space score)."""
        return float(np.mean([pinball(self.quantile(p), p, e) for p in quantiles]))

    # -- outcome space (log x100 of the forecast f)
    def outcome_quantiles(self, f_log: float, quantiles=QUANTILES) -> dict[float, float]:
        """Quantiles of 100 * log(outcome): Q_y(p) = f - Q_e(1 - p)."""
        return {p: f_log - self.quantile(1 - p) for p in quantiles}

    # -- storage (live forecast JSON): enough to rebuild exactly the same distribution later
    def to_json(self) -> dict:
        out = {"method": self.method, "n_pool": self.n,
               "pool": [round(v, POOL_DECIMALS) for v in self.pool]}
        if self.method == "student_t":
            out.update(loc=self.loc, scale=self.scale, df=self.df)
        return out

    @classmethod
    def from_json(cls, d: dict) -> "ErrorDistribution | None":
        """Rebuild from a stored block, using the stored method and parameters (not today's constants)."""
        if not d or d.get("method") not in ("empirical", "student_t"):
            return None
        pool = tuple(sorted(float(v) for v in d["pool"]))
        if d["method"] == "student_t":
            return cls("student_t", pool, float(d["loc"]), float(d["scale"]), float(d["df"]))
        return cls("empirical", pool)


# ------------------------------------------------------------------ strict as-of error pools


def pool(errors: pd.Series, known_from: pd.Series, origin, exclude=None) -> np.ndarray:
    """Errors whose outcome was known on or before `origin` (first-vintage known_from), in period order.

    `errors` and `known_from` share an index (the target period). `exclude` (a period) is never in the pool even if
    its outcome were known (it is the period being forecast).
    """
    origin = pd.Timestamp(origin)
    kf = pd.to_datetime(known_from.reindex(errors.index))
    ok = errors.notna() & kf.notna() & (kf <= origin)
    if exclude is not None:
        ok &= errors.index != exclude
    return errors[ok].to_numpy(dtype=float)


def distribution_at(errors: pd.Series, known_from: pd.Series, origin, exclude=None) -> ErrorDistribution | None:
    return ErrorDistribution.from_pool(pool(errors, known_from, origin, exclude))


def score_frame(errors: pd.DataFrame, origin: pd.Series, known_from: pd.Series,
                levels=LEVELS, quantiles=QUANTILES) -> pd.DataFrame:
    """Rolling-origin distributions and their scores.

    errors: one column per model (100 * log f/y), index = target period; origin and known_from (first vintage of
    the outcome) on the same index. Row i of model v is scored with the distribution built from the pool at
    origin[i], i.e. only errors whose outcome was known at that origin.

    Returns one row per (period, model) with a defined error: n_pool, method, error, crps, pit, quantile_score,
    hit_<L> per level and eq_<p> (error quantiles). Rows without a distribution have method None and NaN scores.
    """
    origin = pd.to_datetime(origin.reindex(errors.index))
    known_from = pd.to_datetime(known_from.reindex(errors.index))
    rows = []
    for v in errors.columns:
        e_all = errors[v]
        for period in errors.index:
            e = e_all.at[period]
            if not np.isfinite(e):
                continue
            o = origin.at[period]
            if known_from.at[period] <= o:  # a forecast of a known number is never scored (engine guard)
                continue
            d = distribution_at(e_all, known_from, o, exclude=period)
            row = {"period": period, "model": v, "origin": o, "error": float(e),
                   "n_pool": len(pool(e_all, known_from, o, exclude=period)),
                   "method": d.method if d else None}
            if d is None:
                row.update(crps=np.nan, pit=np.nan, quantile_score=np.nan,
                           **{f"hit_{level_key(L)}": np.nan for L in levels},
                           **{f"eq_{quantile_key(p)}": np.nan for p in quantiles})
            else:
                row.update(crps=d.crps(e), pit=d.pit(e), quantile_score=d.quantile_score(e, quantiles),
                           **{f"hit_{level_key(L)}": float(d.covers(e, L)) for L in levels},
                           **{f"eq_{quantile_key(p)}": d.quantile(p) for p in quantiles})
            rows.append(row)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ calibration


@dataclass
class CoverageTest:
    level: float
    n: int
    coverage: float
    se: float
    stat: float
    p: float


def coverage_test(hits, level: float) -> CoverageTest:
    """H0: P(hit) = level. se^2 = max(Newey-West LRV of the hits, level(1-level)) / n; p from t(n-1)."""
    h = np.asarray(hits, dtype=float)
    h = h[np.isfinite(h)]
    n = len(h)
    if n < 2:
        return CoverageTest(level, n, float(h.mean()) if n else float("nan"), float("nan"), float("nan"),
                            float("nan"))
    lrv = max(evaluation.long_run_variance(h, evaluation.newey_west_lag(n)), level * (1 - level))
    se = math.sqrt(lrv / n)
    stat = (float(h.mean()) - level) / se
    return CoverageTest(level, n, float(h.mean()), se, stat, evaluation.t_two_sided_p(stat, n - 1))


def pit_histogram(pit, bins: int = PIT_BINS) -> list[int]:
    x = np.asarray(pit, dtype=float)
    x = x[np.isfinite(x)]
    counts, _ = np.histogram(np.clip(x, 0, 1), bins=bins, range=(0, 1))
    return [int(c) for c in counts]


def calibration(scored: pd.DataFrame, levels=LEVELS, alpha: float = CALIBRATION_ALPHA) -> pd.DataFrame:
    """One row per model over the rows of `scored` that have a distribution: n (and per method), coverage and
    Holm-adjusted coverage-test p per level, mean CRPS, mean quantile score, PIT mean, PIT variance (uniform: 0.5
    and 1/12 = 0.0833; a larger variance means too narrow intervals), PIT histogram, and `calibrated` (no level
    with Holm-p < alpha)."""
    out = []
    for v, g in scored[scored["method"].notna()].groupby("model", sort=False):
        tests = {L: coverage_test(g[f"hit_{level_key(L)}"], L) for L in levels}
        holm = evaluation.holm({level_key(L): t.p for L, t in tests.items()})
        row = {"model": v, "n": len(g), "n_empirical": int((g["method"] == "empirical").sum()),
               "n_student_t": int((g["method"] == "student_t").sum()),
               "first": str(g["period"].min()), "last": str(g["period"].max())}
        for L, t in tests.items():
            k = level_key(L)
            row[f"coverage_{k}"] = t.coverage
            row[f"p_{k}"] = t.p
            row[f"holm_{k}"] = holm[k]
        row.update(crps=float(g["crps"].mean()), quantile_score=float(g["quantile_score"].mean()),
                   pit_mean=float(g["pit"].mean()), pit_var=float(g["pit"].var(ddof=0)),
                   pit_hist=pit_histogram(g["pit"]))
        row["calibrated"] = not any(holm[level_key(L)] < alpha for L in levels if not math.isnan(holm[level_key(L)]))
        out.append(row)
    return pd.DataFrame(out)


def crps_dm(scored: pd.DataFrame, a: str, b: str) -> evaluation.DMResult:
    """DM test on CRPS between models a and b, on the periods where both have a distribution. CRPS is a loss >= 0,
    so evaluation.dm_test's |loss| difference is the CRPS difference. With a `unit` column holding several units
    (N1b) the pooled DM of engine.pooled_dm is used (lag and df from the number of periods)."""
    from ai_tracker.nowcast import engine  # engine does not import this module; local import keeps it that way

    s = scored[scored["method"].notna()]
    pooled = "unit" in s and s["unit"].nunique() > 1
    w = s.pivot_table(index=["unit", "period"] if pooled else "period", columns="model", values="crps",
                      aggfunc="first").dropna(subset=[a, b])
    if pooled:
        f = w.reset_index().rename(columns={"period": "quarter"})
        return engine.pooled_dm(f.assign(quarter=f["quarter"].astype(str)), a, b)
    return evaluation.dm_test(w[a].to_numpy(), w[b].to_numpy())


def common_sample(scored: pd.DataFrame, models) -> pd.DataFrame:
    """Rows of `scored` for the periods (per unit) where every model in `models` has a distribution."""
    keys = ["unit", "period"] if "unit" in scored else ["period"]
    s = scored[scored["method"].notna() & scored["model"].isin(models)]
    have = s.groupby(keys)["model"].nunique()
    full = have[have == len(models)].index
    idx = pd.MultiIndex.from_frame(s[keys]) if len(keys) > 1 else pd.Index(s["period"])
    return s[idx.isin(full)]


def evaluate(scored: pd.DataFrame, models, baselines=("B0", "B1")) -> dict:
    """Interval evaluation of one period. Each model is evaluated on its own rows: every scored backtest row where
    it has a distribution (N1's V1/V2 have errors only from 2024Q2, so a sample common to all models would be
    empty). Calibration per model; the best baseline by mean CRPS on the baselines' common rows; a DM test on CRPS
    of each other model against it on their pairwise common rows (reported; Holm over the non-baseline models).
    Nothing here changes the champion: the registered promotion rule is on MAE."""
    s = scored[scored["method"].notna() & scored["model"].isin(models)] if len(scored) else scored
    if s.empty:
        return {"n_periods": 0, "calibration": pd.DataFrame(), "best_baseline": None, "dm": {}}
    cal = calibration(s)
    have = [b for b in baselines if b in set(cal["model"])]
    base = None
    if have:
        cb = common_sample(s, have)
        crps = cb.groupby("model")["crps"].mean().to_dict() if len(cb) else {}
        base = min(crps, key=lambda b: (crps[b], list(baselines).index(b))) if crps else None
    dm = {}
    for v in models:
        if v == base or base is None or v not in set(cal["model"]):
            continue
        if len(common_sample(s, [v, base])) >= 6:  # 3 common periods at least
            dm[v] = crps_dm(s, v, base)
    holm = evaluation.holm({v: r.p for v, r in dm.items() if v not in baselines})
    keys = ["unit", "period"] if "unit" in s else ["period"]
    return {"n_periods": int(s.groupby(keys).ngroups), "first": str(s["period"].min()), "last": str(s["period"].max()),
            "calibration": cal, "best_baseline": base,
            "dm": {v: {"mean_diff": r.mean_diff, "p": r.p, "holm_p": holm.get(v, float("nan")), "mde": r.mde, "n": r.n}
                   for v, r in dm.items()}}


def markdown(res: dict, title: str = "") -> str:
    """Calibration table of evaluate() as Markdown."""
    cal = res["calibration"]
    if cal.empty:
        return f"{title}: no model has a distribution."
    lines = [f"{title}: {res['first']}..{res['last']}, {res['n_periods']} periods (each model on its own rows), "
             f"best baseline by CRPS {res['best_baseline']} (DM on pairwise common rows)",
             "| Model | n | first | t / emp | " + " | ".join(f"Cov {level_key(L)} (Holm p)" for L in LEVELS)
             + " | CRPS | dCRPS | DM p | PIT mean | PIT var | Calibrated |",
             "|" + "---|" * (9 + len(LEVELS))]
    for r in cal.itertuples():
        r = r._asdict()
        dm = res["dm"].get(r["model"], {})
        cov = " | ".join(f"{r[f'coverage_{level_key(L)}']:.2f} ({r[f'holm_{level_key(L)}']:.2f})" for L in LEVELS)
        lines.append(f"| {r['model']} | {r['n']} | {r['first']} | {r['n_student_t']} / {r['n_empirical']} | {cov} | {r['crps']:.3f} | "
                     f"{dm.get('mean_diff', float('nan')):+.3f} | {dm.get('p', float('nan')):.3f} | "
                     f"{r['pit_mean']:.3f} | {r['pit_var']:.4f} | {'yes' if r['calibrated'] else 'no'} |")
    return "\n".join(lines)


# ------------------------------------------------------------------ live forecast block


def live_block(logs: dict, errors: pd.DataFrame, known_from: pd.Series, origin,
               quantiles=QUANTILES, levels=LEVELS) -> dict:
    """The `distribution` block of a live forecast file.

    logs: model -> 100 * log forecast (NaN if unavailable). errors: the backtest errors per model (columns), index
    = target period, with the outcomes' first-vintage known_from. Only errors with known_from <= origin enter.
    Per model: the stored distribution (method, pool and t parameters, so the scorecard rebuilds exactly this
    distribution), quantiles and central intervals of the outcome in levels (exp of 100 * log / 100).
    """
    origin = pd.Timestamp(origin)
    models = {}
    for v, f in logs.items():
        if v not in errors.columns:
            continue
        d = distribution_at(errors[v], known_from, origin)
        n = len(pool(errors[v], known_from, origin))
        if d is None or f is None or not np.isfinite(f):
            models[v] = {"method": None, "n_pool": n}
            continue
        q = d.outcome_quantiles(float(f), quantiles)
        qi = {L: (f - d.quantile((1 + L) / 2), f - d.quantile((1 - L) / 2)) for L in levels}
        models[v] = {**d.to_json(),
                     "quantiles": {quantile_key(p): float(math.exp(x / 100)) for p, x in q.items()},
                     "intervals": {level_key(L): [float(math.exp(lo / 100)), float(math.exp(hi / 100))]
                                   for L, (lo, hi) in qi.items()}}
    return {"registered": REGISTER_REF, "space": "100 * log, error = forecast - outcome",
            "min_errors": MIN_ERRORS, "min_empirical": MIN_EMPIRICAL,
            "quantile_levels": [quantile_key(p) for p in quantiles], "interval_levels": [level_key(L) for L in levels],
            "models": models}


def score_live(block: dict, model: str, error: float, levels=LEVELS) -> dict:
    """Scores of one stored live distribution against a realised error (scorecard): crps, pit, hit_<L>."""
    d = ErrorDistribution.from_json((block or {}).get("models", {}).get(model) or {})
    if d is None or not np.isfinite(error):
        return {}
    return {"crps": d.crps(error), "pit": d.pit(error), **{f"hit_{level_key(L)}": float(d.covers(error, L))
                                                            for L in levels}}
