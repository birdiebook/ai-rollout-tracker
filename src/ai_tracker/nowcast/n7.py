"""N7: depreciation of the four largest hyperscalers 1-8 quarters ahead (docs/mattregister.md, "2026-11-24 - N7:
avskrivningar 1-8 kvartal (förregistrering, före körning)"). The register text governs where this code differs.

    python -m ai_tracker.nowcast backtest n7        registered backtest, logged to experiments/runs/

Registered, implemented here:
- Units. N7: `dep_hyp4` (MSFT + GOOGL + AMZN + META), rebuilt from the company series with quarterly.aggregate_rows
  (a version exists once all four have filed, known_from = the latest filing). N7b: the same models on dep_msft,
  dep_googl, dep_amzn and dep_meta, pooled over companies and origins. Capex: capex_<company>; a unit's moving average
  is the sum of its companies' moving averages.
- Origin: calendar quarter end + 20 days (n1.origin_for). Every input as_of(origin). L = the latest quarter of the
  unit's target known at the origin; horizon h = 1-8, target quarter L + h (as D2). Outcome = first vintage.
- Error 100 x (log forecast - log outcome). B0 = y(L). B1 = y(L) x exp(h x mean of the 4 latest q/q log growths)
  (n1.b1_path).
- V1: y_hat(t) = c * m(t), m(t) = sum over companies of (1/J) * sum_{j=1..J} capex(t - j), J = 4N quarters. A
  training row is a quarter t of the target's as-of history (y > 0) whose J capex lags of every company are known
  (> 0) at the origin; at least 12 rows. N from GRID: candidates with >= 12 rows are compared on their common rows (the
  largest candidate's rows) by in-sample MAE of 100 x |log(c m) - log y| with c fitted on those rows; ties go to the
  smaller N; c is then refitted on all rows of the chosen N. c = sum(y m) / sum(m^2) (OLS through the origin, levels).
  Future capex (quarters after the company's latest known capex quarter Lc): the company's B1 path as of the origin.
- V2: V1 with N per company = the latest stated server life (useful_life_servers_<company>_hi, the value of the latest
  stated quarter among rows known at the origin; the step function of useful_lives.in_effect), J = round(4 N); only c.
- Variants that cannot be formed are missing, never filled.
- Definition breaks (F-B8, as N4 and D2): a break quarter of any company series of the unit is not scored, and B1's
  window (growths ending in L-3..L) may not contain a break known at the origin. Training rows have no break rule.
- Evaluation per unit from the first origin where V1 can be formed, to LAST_ORIGIN. Each variant on its rows (variant,
  B0 and B1 present); comparator = the better of B0 and B1 by MAE on the same rows (ties: B0). Horizon groups h1-2,
  h3-4, h5-8; n = distinct origins. Periods: full and origins from 2023-04-20.
- DM per group and period (group_dm): mean of d = |e_a| - |e_b| over rows; Newey-West (Bartlett) on the per-origin sums
  of demeaned d (Driscoll-Kraay), lag max(newey_west_lag(T), h_max - 1), HLN with h_max, p from t(T - 1). No test
  (p = 1) at T < 8 or a non-positive HLN term. Holm over {V1, V2} x {h1-2, h3-4, h5-8} in each period.
- Decision per group (strict reading, F-B11): lower MAE than the comparator and Holm-p < 0.10 in both periods. The
  decisive evaluation for (variant, group) is N7 when N7 has >= 8 origins in both periods, else N7b. A passing
  variant is conditional (REVIEW_REQUIRED). Default champion B1.
- Intervals (G-C, F-C7): one error pool per unit, model and h; informational.

Fixed here where the register is silent:
- Origins are the registered origins of the quarters FIRST_QUARTER .. the quarter of LAST_ORIGIN; earlier ones have no
  V1 for any unit.
- DM: the per-origin sums are taken in origin order (consecutive in the sample, as engine.pooled_dm); the lag is capped
  at T - 1.
- Two passing variants in a group: the lower MAE on the rows where both exist (decisive evaluation, full period).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ai_tracker import evaluation, observations
from ai_tracker.nowcast import engine, intervals, n1, quarterly

Q = "Q-DEC"
COMPANIES = ("msft", "googl", "amzn", "meta")
TARGET = "dep_hyp4"
HORIZONS = tuple(range(1, 9))
GROUPS = {"h1–2": (1, 2), "h3–4": (3, 4), "h5–8": (5, 6, 7, 8)}
GRID = tuple(range(3, 11))  # N, years: J = 4N quarters
MIN_TRAIN = 12
MIN_ORIGINS = 8  # fewer distinct origins in a group: no DM test (p = 1)
SUBPERIOD_START = pd.Timestamp("2023-04-20")  # the first origin where h = 1 is 2023Q1
FIRST_QUARTER = pd.Period("2009Q1", freq=Q)
LAST_ORIGIN = pd.Timestamp("2026-10-20")
MODELS = ("B0", "B1", "V1", "V2")
VARIANTS = ("V1", "V2")
BASELINES = ("B0", "B1")
PERIODS = ("full", "2023-")
HOLM_ALPHA = engine.PROMOTION_ALPHA
DEFAULT_CHAMPION = "B1"
REVIEW_REQUIRED = {
    "V1": "villkorad: ett positivt resultat kräver ett oberoende granskningsspår (CLAUDE.md)",
    "V2": "villkorad: oberoende granskningsspår, och granskning av P2a:s extraktion av nyttjandeperioder",
}
HOLDOUT_START, HOLDOUT_END, DEV_END = pd.Timestamp("2025-07-01"), pd.Timestamp("2026-10-31"), pd.Timestamp("2025-06-30")


class NotAvailable(Exception):
    """A variant (or the forecast) cannot be formed from the information set."""


@dataclass(frozen=True)
class Unit:
    """A forecast target: the depreciation of `companies` (one company, or the four for dep_hyp4)."""

    key: str
    companies: tuple[str, ...]

    @property
    def dep(self) -> tuple[str, ...]:
        return tuple(f"dep_{c}" for c in self.companies)

    @property
    def capex(self) -> tuple[str, ...]:
        return tuple(f"capex_{c}" for c in self.companies)

    @property
    def lives(self) -> tuple[str, ...]:
        return tuple(f"useful_life_servers_{c}_hi" for c in self.companies)

    @property
    def aggregate(self) -> quarterly.Aggregate:
        return quarterly.Aggregate(self.key, self.dep if len(self.companies) > 1 else ())


N7 = Unit(TARGET, COMPANIES)
N7B = tuple(Unit(f"dep_{c}", (c,)) for c in COMPANIES)


def inputs() -> list[str]:
    return [*N7.dep, *N7.capex, *N7.lives]


def prepare(table: pd.DataFrame) -> pd.DataFrame:
    """The rows N7 reads; dep_hyp4 rebuilt from the company series (stored dep_hyp4 rows are replaced)."""
    t = table[table["series"].isin(inputs())]
    return pd.concat([t, quarterly.aggregate_rows(t, N7.aggregate)], ignore_index=True)


def origins(last=LAST_ORIGIN) -> list[pd.Timestamp]:
    out, q = [], FIRST_QUARTER
    while n1.origin_for(q) <= pd.Timestamp(last):
        out.append(n1.origin_for(q))
        q += 1
    return out


# ------------------------------------------------------------------ moving averages


@dataclass
class Capex:
    """One company's capex on a contiguous quarterly grid (NaN = unknown or not positive), with prefix sums so that
    the mean of quarters t-J .. t-1 is O(1)."""

    start: pd.Period
    values: np.ndarray
    _cs: np.ndarray = field(init=False, repr=False)
    _bad: np.ndarray = field(init=False, repr=False)

    def __post_init__(self):
        ok = np.isfinite(self.values) & (self.values > 0)
        self._cs = np.concatenate([[0.0], np.cumsum(np.where(ok, self.values, 0.0))])
        self._bad = np.concatenate([[0], np.cumsum(~ok)])

    @classmethod
    def from_series(cls, x: pd.Series, extra: dict | None = None) -> "Capex":
        """`x` (as-of capex on a PeriodIndex) plus `extra` (period -> level, the future path)."""
        s = x[x > 0] if len(x) else x
        if extra:
            s = pd.concat([s, pd.Series(extra, dtype=float)])
        if s.empty:
            return cls(pd.Period("2000Q1", freq=Q), np.array([], dtype=float))
        idx = pd.period_range(s.index.min(), s.index.max(), freq=Q)
        return cls(idx[0], s.reindex(idx).to_numpy(dtype=float))

    def mean_before(self, t: pd.Period, J: int) -> float:
        """Mean of capex(t-J) .. capex(t-1); NaN unless all J quarters are known and positive."""
        hi = (t - self.start).n  # index of t: the window is [hi - J, hi)
        lo = hi - J
        if lo < 0 or hi > len(self.values) or J <= 0:
            return float("nan")
        if self._bad[hi] - self._bad[lo]:
            return float("nan")
        return float((self._cs[hi] - self._cs[lo]) / J)


def moving_average(capex: dict[str, Capex], J: dict[str, int], t: pd.Period) -> float:
    """m(t) = sum over companies of the mean of their J capex lags (NaN if any company's window is incomplete)."""
    total = 0.0
    for c, x in capex.items():
        v = x.mean_before(t, J[c])
        if math.isnan(v):
            return float("nan")
        total += v
    return total


def training_rows(y: pd.Series, capex: dict[str, Capex], J: dict[str, int]) -> tuple[np.ndarray, np.ndarray, list]:
    """(y, m, quarters) of the complete training rows: y(t) > 0 known and every company's J lags known."""
    ys, ms, qs = [], [], []
    for t, v in y.items():
        if not (v > 0):
            continue
        m = moving_average(capex, J, t)
        if np.isfinite(m) and m > 0:
            ys.append(float(v))
            ms.append(m)
            qs.append(t)
    return np.array(ys), np.array(ms), qs


def fit_c(y: np.ndarray, m: np.ndarray) -> float:
    """OLS through the origin in levels."""
    return float(y @ m / (m @ m))


def in_sample_mae(y: np.ndarray, m: np.ndarray, c: float) -> float:
    return float(np.mean(np.abs(100 * (np.log(c * m) - np.log(y)))))


@dataclass
class Fit:
    c: float
    J: dict  # company -> J (quarters)
    n_train: int
    N: float | None = None  # V1: the chosen grid value (years)
    maes: dict = field(default_factory=dict)  # V1: candidate N -> in-sample MAE on the common rows


def select_v1(y: pd.Series, capex: dict[str, Capex], grid=GRID, min_train: int = MIN_TRAIN) -> Fit:
    """V1's N and c on the expanding window (register: common rows of the candidates, ties to the smaller N, c refitted
    on all rows of the chosen N)."""
    rows = {}
    for N in grid:
        J = {c: 4 * N for c in capex}
        ys, ms, qs = training_rows(y, capex, J)
        if len(ys) >= min_train:
            rows[N] = (ys, ms, qs)
    if not rows:
        raise NotAvailable(f"V1: no N in {grid[0]}..{grid[-1]} has {min_train} complete training rows")
    common_q = set(rows[max(rows)][2])
    maes, best = {}, None
    for N in sorted(rows):
        ys, ms, qs = rows[N]
        keep = np.array([q in common_q for q in qs])
        c = fit_c(ys[keep], ms[keep])
        maes[N] = in_sample_mae(ys[keep], ms[keep], c)
        if best is None or maes[N] < maes[best]:
            best = N
    ys, ms, _ = rows[best]
    return Fit(fit_c(ys, ms), {c: 4 * best for c in capex}, len(ys), float(best), maes)


def fit_v2(y: pd.Series, capex: dict[str, Capex], J: dict[str, int], min_train: int = MIN_TRAIN) -> Fit:
    ys, ms, _ = training_rows(y, capex, J)
    if len(ys) < min_train:
        raise NotAvailable(f"V2: {len(ys)} complete training rows < {min_train} (J {J})")
    return Fit(fit_c(ys, ms), dict(J), len(ys))


def stated_life(info: engine.InfoSet, series: str) -> float:
    """The latest stated server life known at the origin: the value of the latest stated quarter (useful_lives
    in_effect's step function, carried forward)."""
    s = info.get(series)
    s = s[s > 0] if len(s) else s
    if s.empty:
        raise NotAvailable(f"V2: {series} not known at {info.origin.date()}")
    return float(s[s.index.max()])


# ------------------------------------------------------------------ one origin


@dataclass
class Forecast:
    unit: Unit
    origin: pd.Timestamp
    base: pd.Period | None  # L
    levels: dict = field(default_factory=dict)  # model -> {h: level or NaN}
    reasons: dict = field(default_factory=dict)
    fits: dict = field(default_factory=dict)  # variant -> Fit
    capex_last: dict = field(default_factory=dict)  # company -> latest known capex quarter


def _nan_path() -> dict:
    return {h: float("nan") for h in HORIZONS}


def forecast(table: pd.DataFrame, unit: Unit, origin, brk: dict | None = None) -> Forecast:
    """Every model's path at `origin` from the prepared table, everything as_of(origin)."""
    origin = pd.Timestamp(origin)
    info = engine.InfoSet(table, origin)
    y = info.get(unit.key)
    y = y[y > 0] if len(y) else y
    out = Forecast(unit, origin, None)
    if y.empty:
        for m in MODELS:
            out.levels[m], out.reasons[m] = _nan_path(), f"{unit.key}: nothing known"
        return out
    L = y.index.max()
    out.base = L
    out.levels["B0"] = {h: float(y[L]) for h in HORIZONS}
    out.levels["B1"] = _nan_path()
    known = quarterly.known_breaks(brk or {}, origin)
    crossing = [str(p) for p in pd.period_range(L - 3, L, freq=Q) if p in known]
    if crossing:
        out.reasons["B1"] = f"B1: window crosses a definition break ({', '.join(crossing)})"
    else:
        try:
            b1 = n1.b1_path(y, [L + h for h in HORIZONS])
            out.levels["B1"] = {h: b1[L + h] for h in HORIZONS}
        except n1.NotAvailable as exc:
            out.reasons["B1"] = f"B1: {exc}"

    # capex as known at the origin, and each company's B1 path for the quarters after its latest known one
    known_capex, extended, path_error = {}, {}, None
    for c, key in zip(unit.companies, unit.capex):
        x = info.get(key)
        x = x[x > 0] if len(x) else x
        known_capex[c] = Capex.from_series(x)
        if x.empty:
            path_error = f"{key}: nothing known"
            extended[c] = known_capex[c]
            continue
        lc = x.index.max()
        out.capex_last[c] = str(lc)
        future = [lc + k for k in range(1, (L + max(HORIZONS) - 1 - lc).n + 1)]
        try:
            path = n1.b1_path(x, future) if future else {}
        except n1.NotAvailable as exc:
            path_error, path = f"capex path: {exc}", {}
        extended[c] = Capex.from_series(x, path)

    for v in ("V1", "V2"):
        out.levels[v] = _nan_path()
    try:
        out.fits["V1"] = select_v1(y, known_capex)
    except NotAvailable as exc:
        out.reasons["V1"] = str(exc)
    try:
        J = {c: int(round(4 * stated_life(info, s))) for c, s in zip(unit.companies, unit.lives)}
        out.fits["V2"] = fit_v2(y, known_capex, J)
    except NotAvailable as exc:
        out.reasons["V2"] = str(exc)
    for v, fit in out.fits.items():
        if path_error:
            out.reasons[v] = f"{v}: {path_error}"
            continue
        for h in HORIZONS:
            m = moving_average(extended, fit.J, L + h)
            out.levels[v][h] = fit.c * m if np.isfinite(m) else float("nan")
    return out


# ------------------------------------------------------------------ backtest frame


def frame(t: pd.DataFrame, unit: Unit, origin_list=None) -> pd.DataFrame:
    """One row per (origin, h) with a scorable first-vintage outcome: errors per model, fit details. Column
    in_period marks the unit's evaluation (from the first origin where V1 is formed)."""
    origin_list = origins() if origin_list is None else origin_list
    outcomes = engine.first_vintages(t, unit.key)
    brk = quarterly.breaks(t, unit.aggregate)
    rows, start, known, skipped = [], None, [], []
    for o in origin_list:
        f = forecast(t, unit, o, brk)
        if f.base is None:
            continue
        if start is None and np.isfinite(f.levels["V1"][1]):
            start = o
        for h in HORIZONS:
            q = f.base + h
            if q not in outcomes.index:
                continue
            if q in brk:
                skipped.append(f"{unit.key} {q} from {o.date()}")
                continue
            note = engine.known_at_origin(outcomes, q, o, f"{unit.key} {q}")
            if note:
                known.append(note)
                continue
            y = float(outcomes.at[q, "value"])
            v1, v2 = f.fits.get("V1"), f.fits.get("V2")
            row = {"unit": unit.key, "origin": o, "base": f.base, "h": h, "quarter": q, "outcome": y,
                   "outcome_known_from": outcomes.at[q, "known_from"],
                   "N_v1": v1.N if v1 else float("nan"), "c_v1": v1.c if v1 else float("nan"),
                   "n_train_v1": v1.n_train if v1 else 0,
                   "J_v2": ";".join(f"{c}:{j}" for c, j in v2.J.items()) if v2 else "",
                   "c_v2": v2.c if v2 else float("nan"), "n_train_v2": v2.n_train if v2 else 0,
                   "reason": "; ".join(sorted(set(f.reasons.values())))}
            for m in MODELS:
                lv = f.levels.get(m, {}).get(h, float("nan"))
                row[m] = engine.log_error(lv, y) if np.isfinite(lv) and lv > 0 else float("nan")
            rows.append(row)
    cols = ["unit", "origin", "base", "h", "quarter", "outcome", "outcome_known_from", "N_v1", "c_v1", "n_train_v1",
            "J_v2", "c_v2", "n_train_v2", "reason", *MODELS]
    df = pd.DataFrame(rows, columns=cols)
    df["in_period"] = (df["origin"] >= start) if start is not None else False
    df.attrs.update(start=start, known_at_origin=known, breaks=skipped,
                    break_quarters={str(q): str(v[0].date()) for q, v in brk.items()})
    return df


def run(table: pd.DataFrame, origin_list=None) -> dict:
    """{"N7": frame, "N7b": pooled frame of the four companies} on the prepared table."""
    t = prepare(table)
    n7 = frame(t, N7, origin_list)
    parts = [frame(t, u, origin_list) for u in N7B]
    n7b = pd.concat(parts, ignore_index=True)
    n7b.attrs.update(start={u.key: p.attrs["start"] for u, p in zip(N7B, parts)},
                     breaks=[b for p in parts for b in p.attrs["breaks"]],
                     known_at_origin=[k for p in parts for k in p.attrs["known_at_origin"]],
                     break_quarters={u.key: p.attrs["break_quarters"] for u, p in zip(N7B, parts)})
    return {"N7": n7, "N7b": n7b}


# ------------------------------------------------------------------ evaluation


@dataclass
class GroupDM:
    T: int  # distinct origins
    n: int  # rows
    lag: int
    mean_diff: float  # MAE(a) - MAE(b) over the rows
    se: float
    p: float  # NaN when not testable
    mde: float
    testable: bool
    note: str = ""


def group_dm(rows: pd.DataFrame, a: str, b: str, h_max: int, min_origins: int = MIN_ORIGINS) -> GroupDM:
    """DM on absolute loss over the rows of one horizon group (several units and horizons per origin): Driscoll-Kraay
    with origins as the time index, Newey-West lag max(newey_west_lag(T), h_max - 1), HLN with h = h_max."""
    r = rows.dropna(subset=[a, b])
    d = (r[a].abs() - r[b].abs()).to_numpy(dtype=float)
    n = len(d)
    T = int(r["origin"].nunique())
    mean = float(d.mean()) if n else float("nan")
    if T < min_origins:
        return GroupDM(T, n, 0, mean, float("nan"), float("nan"), float("nan"), False, f"T = {T} < {min_origins}")
    lag = min(max(evaluation.newey_west_lag(T), h_max - 1), T - 1)
    sums = pd.Series(d - mean, index=r.index).groupby(r["origin"].to_numpy()).sum().sort_index().to_numpy()
    lrv = float(sums @ sums / T)
    for k in range(1, lag + 1):
        lrv += 2 * (1 - k / (lag + 1)) * float(sums[k:] @ sums[:-k]) / T
    rad = (T + 1 - 2 * h_max + h_max * (h_max - 1) / T) / T
    if rad <= 0:
        return GroupDM(T, n, lag, mean, float("nan"), float("nan"), float("nan"), False, "HLN term <= 0")
    se = math.sqrt(max(lrv, 0.0) * T) / n / math.sqrt(rad)
    if se == 0:
        return GroupDM(T, n, lag, mean, 0.0, float("nan"), 0.0, False, "zero variance")
    stat = mean / se
    return GroupDM(T, n, lag, mean, se, evaluation.t_two_sided_p(stat, T - 1), evaluation.MDE_FACTOR * se, True)


def period_mask(f: pd.DataFrame, period: str) -> pd.Series:
    m = f["in_period"].astype(bool)
    return m & (f["origin"] >= SUBPERIOD_START) if period == "2023-" else m


def evaluate(f: pd.DataFrame) -> dict:
    """res[period][group][variant]: n rows, T origins, metrics of the variant and both baselines on the variant's rows,
    comparator, DM and Holm-p (Holm over the 6 variant x group tests of the period)."""
    res = {}
    for per in PERIODS:
        e = f[period_mask(f, per)] if len(f) else f
        res[per] = {}
        pvals = {}
        for g, hs in GROUPS.items():
            res[per][g] = {}
            eg = e[e["h"].isin(hs)] if len(e) else e
            for v in VARIANTS:
                rows = eg.dropna(subset=["B0", "B1", v]) if len(eg) else eg
                entry = {"n": len(rows), "T": int(rows["origin"].nunique()) if len(rows) else 0}
                if len(rows):
                    m = {x: evaluation.metrics(rows[x]) for x in (*BASELINES, v)}
                    comp = engine.best_baseline({b: m[b]["MAE"] for b in BASELINES}, BASELINES)
                    dm = group_dm(rows, v, comp, max(hs))
                    entry.update(first=str(rows["origin"].min().date()), last=str(rows["origin"].max().date()),
                                 metrics=m, comparator=comp, dm=dm,
                                 per_h={h: {x: evaluation.metrics(rows.loc[rows["h"] == h, x])
                                            for x in (*BASELINES, v)} for h in hs if (rows["h"] == h).any()})
                    pvals[(v, g)] = dm.p if dm.testable and np.isfinite(dm.p) else 1.0
                else:
                    pvals[(v, g)] = 1.0
                res[per][g][v] = entry
        holm = evaluation.holm({f"{v} {g}": p for (v, g), p in pvals.items()})
        for (v, g), p in pvals.items():
            res[per][g][v]["p_holm_input"] = p
            res[per][g][v]["holm_p"] = holm[f"{v} {g}"]
    return res


def _scope(res: dict, v: str, g: str) -> str:
    """The decisive evaluation for (variant, group): N7 with >= MIN_ORIGINS origins in both periods, else N7b."""
    ok = all(res["N7"][per][g][v]["T"] >= MIN_ORIGINS for per in PERIODS)
    return "N7" if ok else "N7b"


def decide(res: dict) -> dict:
    """Per group: checks per variant (in its decisive evaluation), the champion (B1 unless a variant passes and needs no
    review) and the conditional variants."""
    out = {}
    for g in GROUPS:
        checks, passed = {}, {}
        for v in VARIANTS:
            scope = _scope(res, v, g)
            c = {"scope": scope}
            for per in PERIODS:
                r = res[scope][per][g][v]
                if "metrics" not in r:
                    c[per] = {"mae_ok": False, "holm_ok": False, "note": "no rows"}
                    continue
                c[per] = engine.period_check(r["metrics"][v]["MAE"], r["metrics"][r["comparator"]]["MAE"],
                                             r["holm_p"], HOLM_ALPHA)
                c[per]["comparator"] = r["comparator"]
            c["passes"] = engine.passes({p: c[p] for p in PERIODS})
            checks[v], passed[v] = c, c["passes"]
        mae = {v: _common_mae(res, checks, g, v) for v in VARIANTS if passed[v]}
        d = engine.decide({v: passed[v] for v in mae}, mae, REVIEW_REQUIRED, DEFAULT_CHAMPION)
        best_conditional = min(d.conditional, key=lambda v: mae[v]) if d.conditional else None
        out[g] = {"checks": checks, "champion": d.champion, "conditional": d.conditional,
                  "best_conditional": best_conditional}
    return out


def _common_mae(res: dict, checks: dict, g: str, v: str) -> float:
    """MAE of v on the rows where every passing variant exists (decisive evaluation, full period)."""
    return res["_frames"][checks[v]["scope"]].pipe(_common_rows, g, [x for x in VARIANTS if checks[x]["passes"]])[v] \
        .abs().mean()


def _common_rows(f: pd.DataFrame, g: str, variants: list) -> pd.DataFrame:
    e = f[period_mask(f, "full") & f["h"].isin(GROUPS[g])]
    return e.dropna(subset=["B0", "B1", *variants])


def holdout_counts(f: pd.DataFrame) -> dict:
    """Informational (G-E): evaluated origins and rows in development (origin and outcome <= 2025-06-30), holdout
    (origin 2025-07-01 .. 2026-10-31) and neither."""
    e = f[f["in_period"]] if len(f) else f
    if e.empty:
        return {"development": [0, 0], "holdout": [0, 0], "neither": [0, 0]}
    o, k = pd.to_datetime(e["origin"]), pd.to_datetime(e["outcome_known_from"])
    dev = (o <= DEV_END) & (k <= DEV_END)
    hold = (o >= HOLDOUT_START) & (o <= HOLDOUT_END)
    nei = ~dev & ~hold
    return {name: [int(e.loc[m, "origin"].nunique()), int(m.sum())] for name, m in
            (("development", dev), ("holdout", hold), ("neither", nei))}


# ------------------------------------------------------------------ intervals (G-C, F-C7; informational)


def scored(f: pd.DataFrame) -> pd.DataFrame:
    """Rolling-origin error distributions with one pool per (unit, model, h): an error enters a pool only from its own
    outcome's first-vintage known_from (intervals.score_frame on one unit and h at a time)."""
    parts = []
    for (u, h), g in f.groupby(["unit", "h"]):
        g = g.set_index(g["origin"].dt.date.astype(str))
        s = intervals.score_frame(g[list(MODELS)], g["origin"], g["outcome_known_from"])
        if len(s):
            parts.append(s.assign(unit=u, h=h, in_period=g["in_period"].reindex(s["period"]).to_numpy()))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def interval_summary(f: pd.DataFrame) -> dict:
    """Per period and group: calibration per model on the evaluated rows with a distribution."""
    sc = scored(f) if len(f) else pd.DataFrame()
    out = {}
    for per in PERIODS:
        out[per] = {}
        for g, hs in GROUPS.items():
            if sc.empty:
                out[per][g] = pd.DataFrame()
                continue
            s = sc[sc["in_period"].astype(bool) & sc["h"].isin(hs)]
            if per == "2023-":
                s = s[pd.to_datetime(s["origin"]) >= SUBPERIOD_START]
            out[per][g] = intervals.calibration(s) if len(s) else pd.DataFrame()
    return out


# ------------------------------------------------------------------ report


def backtest(table: pd.DataFrame | None = None, log: bool = True, origin_list=None) -> dict:
    table = observations.load() if table is None else table
    frames = run(table, origin_list)
    res = {k: evaluate(f) for k, f in frames.items()}
    res["_frames"] = frames
    out = {"frames": frames, "eval": {k: res[k] for k in frames}, "decision": decide(res),
           "holdout": {k: holdout_counts(f) for k, f in frames.items()}}
    if intervals.ENABLED:
        out["intervals"] = {k: interval_summary(f) for k, f in frames.items()}
    if log:
        out["log"] = evaluation.log_run("n7_backtest", log_rows(out))
    return out


def log_rows(out: dict) -> list[dict]:
    rows = []
    for k, res in out["eval"].items():
        target = TARGET if k == "N7" else "dep_<company> pooled (N7b)"
        for per in PERIODS:
            for g in GROUPS:
                for v in VARIANTS:
                    r = res[per][g][v]
                    if "metrics" not in r:
                        rows.append({"target": target, "variant": f"{v} {g}", "period": per, "n": 0, "MAE": "",
                                     "dm_p_vs_baseline": ""})
                        continue
                    span = f"{per} {r['first']}..{r['last']} T={r['T']}"
                    for x in (*BASELINES, v):
                        rows.append({"target": target, "variant": f"{x} {g} ({v} rows)", "period": span,
                                     "n": r["metrics"][x]["n"], "MAE": round(r["metrics"][x]["MAE"], 4),
                                     "dm_p_vs_baseline": (round(r["dm"].p, 4) if x == v and r["dm"].testable
                                                          else "")})
    return rows


def _f(x, nd=2, signed=False) -> str:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "-"
    return f"{x:+.{nd}f}" if signed else f"{x:.{nd}f}"


def format_report(out: dict) -> str:
    lines = []
    for k, f in out["frames"].items():
        lines.append(f"{k}: {len(f)} scored rows, evaluated {int(f['in_period'].sum()) if len(f) else 0}, start "
                     f"{f.attrs.get('start')}, break quarters {f.attrs.get('break_quarters')}")
        lines.append(f"  holdout membership (origins, rows): {out['holdout'][k]}")
        for per in PERIODS:
            for g in GROUPS:
                for v in VARIANTS:
                    r = out["eval"][k][per][g][v]
                    if "metrics" not in r:
                        lines.append(f"  {per:6s} {g:5s} {v}: no rows")
                        continue
                    m, d = r["metrics"], r["dm"]
                    lines.append(
                        f"  {per:6s} {g:5s} {v}: T={r['T']:3d} n={r['n']:4d} MAE {v} {_f(m[v]['MAE'])} "
                        f"B0 {_f(m['B0']['MAE'])} B1 {_f(m['B1']['MAE'])} comp {r['comparator']} "
                        f"bias {v} {_f(m[v]['bias'], 2, True)} dMAE {_f(d.mean_diff, 2, True)} p {_f(d.p, 3)} "
                        f"Holm {_f(r['holm_p'], 3)} MDE {_f(d.mde)} lag {d.lag}{' ' + d.note if d.note else ''}")
    for g, d in out["decision"].items():
        lines.append(f"decision {g}: champion {d['champion']}; conditional {d['conditional'] or '-'}; "
                     + "; ".join(f"{v} ({c['scope']}) passes={c['passes']}" for v, c in d["checks"].items()))
    return "\n".join(lines)


def _c(x, nd=2, signed=False) -> str:
    """Swedish number (decimal comma, true minus)."""
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "–"
    return (f"{x:+.{nd}f}" if signed else f"{x:.{nd}f}").replace(".", ",").replace("-", "−")


def markdown_tables(out: dict, key: str) -> str:
    """Swedish results table per period for one evaluation (N7 or N7b)."""
    lines = []
    res = out["eval"][key]
    for per in PERIODS:
        title = "Hela perioden" if per == "full" else "Från 2023 (prognosdagar från 2023-04-20)"
        lines += [f"**{title}**", "",
                  "| Grupp | Variant | T (prognosdagar) | n (rader) | MAE variant | MAE B0 | MAE B1 | Jämförelse | "
                  "Bias variant | Bias jämförelse | MAE-skillnad | DM p | Holm-p | MDE |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for g in GROUPS:
            for v in VARIANTS:
                r = res[per][g][v]
                if "metrics" not in r:
                    lines.append(f"| {g} | {v} | 0 | 0 | – | – | – | – | – | – | – | – | – | – |")
                    continue
                m, d, comp = r["metrics"], r["dm"], r["comparator"]
                lines.append(f"| {g} | {v} | {r['T']} | {r['n']} | {_c(m[v]['MAE'])} | {_c(m['B0']['MAE'])} | "
                             f"{_c(m['B1']['MAE'])} | {comp} | {_c(m[v]['bias'], 2, True)} | "
                             f"{_c(m[comp]['bias'], 2, True)} | {_c(d.mean_diff, 2, True)} | "
                             f"{_c(d.p, 3) if d.testable else 'inget test'} | {_c(r['holm_p'], 3)} | "
                             f"{_c(d.mde) if d.testable else '–'} |")
        lines.append("")
    return "\n".join(lines)


def markdown_per_h(out: dict, key: str, per: str = "full") -> str:
    """Informational: MAE and bias per h on each variant's rows."""
    lines = ["| h | Variant | n | MAE variant | MAE B0 | MAE B1 | Bias variant | Bias B1 |", "|---|---|---|---|---|---|---|---|"]
    res = out["eval"][key][per]
    for g, hs in GROUPS.items():
        for v in VARIANTS:
            r = res[g][v]
            for h in hs:
                ph = r.get("per_h", {}).get(h)
                if not ph:
                    continue
                lines.append(f"| {h} | {v} | {ph[v]['n']} | {_c(ph[v]['MAE'])} | {_c(ph['B0']['MAE'])} | "
                             f"{_c(ph['B1']['MAE'])} | {_c(ph[v]['bias'], 2, True)} | {_c(ph['B1']['bias'], 2, True)} |")
    return "\n".join(lines)


def markdown_intervals(out: dict, key: str, per: str = "full") -> str:
    lines = ["| Grupp | Modell | n med fördelning | Täckning 50 % | Täckning 80 % | Täckning 95 % | CRPS |",
             "|---|---|---|---|---|---|---|"]
    any_row = False
    for g in GROUPS:
        cal = out.get("intervals", {}).get(key, {}).get(per, {}).get(g)
        if cal is None or cal.empty:
            continue
        for _, c in cal.iterrows():
            any_row = True
            lines.append(f"| {g} | {c['model']} | {c['n']} | {_c(100 * c['coverage_50'], 0)} % | "
                         f"{_c(100 * c['coverage_80'], 0)} % | {_c(100 * c['coverage_95'], 0)} % | {_c(c['crps'])} |")
    if not any_row:
        lines.append("| – | – | 0 | – | – | – | – |")
    return "\n".join(lines)
