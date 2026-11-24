"""D2: forecasts 1-8 quarters ahead for capex_hyp4 and the N4 cloud revenue sum (docs/mattregister.md, "2026-11-23 -
D2: prognoser 1-8 kvartal (förregistrering, F-E7)", with G-E, G-C/F-C7 and F-E6).

    python -m ai_tracker.nowcast.horizon        development evaluation (origins <= 2025-06-30 only)

Registered, implemented here:
- Targets: `capex_hyp4` and `rev_cloud3` (rev_aws + rev_google_cloud + rev_msft_cloud, first version where all three
  exist, built as in N4: quarterly.aggregate_rows). Outcome = the first vintage of the target quarter.
- Origin: calendar quarter end + 20 days (n1.origin_for). L = the latest quarter of the target known at the origin
  (as_of). Horizon h = 1-8: the target quarter is L + h.
- B0: y(L). B1: y(L) x exp(h x mean of the 4 latest q/q log growths up to L) (n1.b1_path).
- B2 (capex only): per company as N1's B2 and summed. A quarter in a year whose full-year guidance is known at the
  origin: N1's B2 rule (implied full year minus the year's known quarters, split over the year's unknown quarters by
  the company's B1 path; n1.guided_company with ahead=True). Later quarters: the last guided quarter's level x
  exp(k x the company's B1 drift), k = quarters after it. A company without comparable guidance (Amazon, Microsoft)
  or with no guided quarter before: its own B1 path.
- V_kedja: direct forecast per h. OLS (with a constant) of g_t(h) = 100 x (log y(t+h) - log y(t)) on R_t = 100 x
  y/y log growth of rpo_hyp4 at t and X_t = 100 x (log x_capex_cloud(t) - mean of log x_capex_cloud over the quarters
  up to and including t). Forecast: y(L) x exp((a + b R_L + c X_L) / 100). At least 12 rows per h (MIN_TRAIN).
- Errors: 100 x (log forecast - log outcome). MAE and bias per h.
- Intervals (G-C with F-C7): one error pool per (target, model, h). An error enters the pool of later origins only
  from its own outcome's first-vintage known_from (intervals.score_frame on the frame of that h alone).
- Holdout (G-E, D2 is a complex family): every origin passes factor.guard.check(family="D2"), which raises for an
  origin after 2025-06-30 while D2's holdout is closed, and the run reads only rows with known_from <= 2025-06-30
  (guard.dev_table), so an outcome first known later is not in the development evaluation (F-E1). Promotion (per
  horizon group h1-2, h3-4, h5-8, V_kedja against the best of B0, B1 and B2, F-E6, Holm over groups) is decided on the
  holdout only; nothing here decides anything.

Fixed here where the register is silent (docs/resultat/d2_utveckling.md):
- V_kedja's training rows are the quarters t of the history known at the origin (as_of for the target, rpo_hyp4 and
  x_capex_cloud) with t + h <= L and both regressors defined at t. Every value is known at the origin. The expanding
  mean of X_t runs over the as-of history of x_capex_cloud up to t. The regressors at the forecast are taken at L; if
  either is missing at L there is no V_kedja forecast.
- x_capex_cloud is rebuilt from its components with series.avstamning.derive (identical to the catalog rows), and
  rpo_hyp4 and rev_cloud3 with quarterly.aggregate_rows, so that every vintage is the one the components imply.
- Cloud definition breaks (N4, F-B8): a break quarter is not scored, and B1's growth window may not cross a break
  known at the origin. Capex has no break rule (as N1).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ai_tracker import evaluation, observations
from ai_tracker.factor import guard
from ai_tracker.nowcast import engine, intervals, n1, n4, quarterly
from ai_tracker.series import avstamning

FAMILY = "D2"
Q = "Q-DEC"
HORIZONS = tuple(range(1, 9))
MIN_TRAIN = 12
GROUPS = {"h1–2": (1, 2), "h3–4": (3, 4), "h5–8": (5, 6, 7, 8)}  # promotion groups (on the holdout only)
FIRST_QUARTER = pd.Period("2017Q1", freq=Q)  # first origin quarter tried (nothing is known before)
RPO = n4.RPO
X_KEY = "x_capex_cloud"


@dataclass(frozen=True)
class Target:
    name: str
    key: str
    label: str
    models: tuple[str, ...]
    components: tuple[str, ...] = ()  # derived sum (cloud); empty = a table series (capex)


CAPEX = Target("capex", n1.TARGET, "Capex MSFT+GOOGL+AMZN+META", ("B0", "B1", "B2", "V_kedja"))
CLOUD = Target("cloud", n4.TARGET, "Molnintäkter AWS + Google Cloud + Microsoft Cloud", ("B0", "B1", "V_kedja"),
               n4.COMPONENTS)
TARGETS = {t.name: t for t in (CAPEX, CLOUD)}
BASELINES = {"capex": ("B0", "B1", "B2"), "cloud": ("B0", "B1")}


def _guidance_series() -> list[str]:
    out = []
    for prefix, lease in n1.B2_GUIDANCE.values():
        out += [f"{prefix}_lo", f"{prefix}_hi"] + ([lease] if lease else [])
    return out


INPUTS = [n1.TARGET, *n1.COMPANIES, *_guidance_series(), *n4.COMPONENTS, *RPO.components]


# ------------------------------------------------------------------ data


def prepare(table: pd.DataFrame) -> pd.DataFrame:
    """The rows D2 reads: inputs as stored, rev_cloud3 and rpo_hyp4 rebuilt from their components, x_capex_cloud
    rebuilt from capex_hyp4 and the cloud components (release-dated vintages, no I/O)."""
    t = table[table["series"].isin(INPUTS)]
    cloud = quarterly.aggregate_rows(t, quarterly.Aggregate(n4.TARGET, n4.COMPONENTS))
    rpo = quarterly.aggregate_rows(t, RPO)
    recon = avstamning.BY_KEY[X_KEY]
    x = avstamning.derive(recon, t[t["series"].isin(recon.components)])
    x = x.assign(series=X_KEY, freq="Q", fetched_at=pd.NaT)[list(cloud.columns)] if len(x) else observations._empty()
    return pd.concat([t, cloud, rpo, x], ignore_index=True)


def dev_origins(end=guard.DEV_END) -> list[pd.Timestamp]:
    """Registered origins (quarter end + 20 days) from FIRST_QUARTER to `end`."""
    out, q = [], FIRST_QUARTER
    while n1.origin_for(q) <= pd.Timestamp(end):
        out.append(n1.origin_for(q))
        q += 1
    return out


# ------------------------------------------------------------------ one origin


@dataclass
class Path:
    """All models' forecasts at one origin for one target: levels[model][h]."""

    target: Target
    origin: pd.Timestamp
    base: pd.Period | None  # L
    levels: dict = field(default_factory=dict)  # model -> {h: level or NaN}
    reasons: dict = field(default_factory=dict)  # model -> why not available
    n_train: dict = field(default_factory=dict)  # h -> V_kedja training rows
    coef: dict = field(default_factory=dict)  # h -> [a, b_rpo, c_x]
    regressors: dict = field(default_factory=dict)  # R_L, X_L
    b2_sources: dict = field(default_factory=dict)  # company -> {h: source}


def _nan_path() -> dict:
    return {h: float("nan") for h in HORIZONS}


def _drift(y: pd.Series) -> float:
    """Mean of the 4 latest q/q log growths up to y's last quarter (NaN without 5 positive contiguous values)."""
    last = y.index.max()
    w = y.reindex(pd.period_range(last - 4, last, freq=Q))
    if w.isna().any() or (w <= 0).any():
        return float("nan")
    return float(np.diff(np.log(w.to_numpy(dtype=float))).mean())


def b2_company(info: engine.InfoSet, series: str, L: pd.Period) -> tuple[dict, dict]:
    """B2 levels and sources for L+1..L+8 of one company (capex only)."""
    y = info.get(series)
    if y.empty:
        raise n1.NotAvailable(f"{series}: nothing known")
    d = _drift(y[y.index <= y.index.max()])
    if math.isnan(d):
        raise n1.NotAvailable(f"{series}: no 4 growth rates at {info.origin.date()}")
    levels, sources, guided = {}, {}, None
    for h in HORIZONS:
        q = L + h
        level, source, b1q, _ = n1.guided_company(info, series, q, ahead=True)
        if source.startswith("guidance") or source == "known at origin":
            guided = (q, level)
        elif guided is not None:  # a later quarter: B1 growth from the last guided (or known) quarter
            level, source = guided[1] * math.exp((q - guided[0]).n * d), f"B1 growth from {guided[0]}"
        levels[h], sources[h] = level, source
    return levels, sources


def b2(info: engine.InfoSet, L: pd.Period, path: Path) -> None:
    total = {h: 0.0 for h in HORIZONS}
    for c in n1.COMPANIES:
        levels, sources = b2_company(info, c, L)
        path.b2_sources[c] = sources
        for h in HORIZONS:
            total[h] += levels[h]
    path.levels["B2"] = total


def regressors(info: engine.InfoSet) -> tuple[pd.Series, pd.Series]:
    """R_t (100 x y/y log growth of rpo_hyp4) and X_t (100 x log x_capex_cloud minus its expanding mean), from the
    as-of history at the origin."""
    rpo = info.get(RPO.key)
    rpo = rpo[rpo > 0]
    lr = np.log(rpo.astype(float))
    lag = lr.copy()
    lag.index = lag.index + 4
    R = (100 * (lr - lag.reindex(lr.index))).dropna()
    x = info.get(X_KEY)
    x = x[x > 0].sort_index()
    lx = np.log(x.astype(float))
    X = 100 * (lx - lx.expanding().mean())
    return R, X


def kedja(info: engine.InfoSet, y: pd.Series, L: pd.Period, path: Path) -> None:
    """V_kedja for h = 1-8 (direct OLS per h)."""
    path.levels["V_kedja"] = _nan_path()
    R, X = regressors(info)
    if L not in R.index or L not in X.index:
        path.reasons["V_kedja"] = f"V_kedja: regressors not known for {L} at {info.origin.date()}"
        return
    path.regressors = {"R_L": float(R[L]), "X_L": float(X[L])}
    ly = np.log(y[y > 0].astype(float))
    common = [t for t in R.index.intersection(X.index) if t in ly.index]
    short = []
    for h in HORIZONS:
        rows = [(R[t], X[t], 100 * (ly[t + h] - ly[t])) for t in common if t + h <= L and t + h in ly.index]
        path.n_train[h] = len(rows)
        if len(rows) < MIN_TRAIN:
            short.append(h)
            continue
        a = np.array(rows, dtype=float)
        A = np.column_stack([np.ones(len(a)), a[:, 0], a[:, 1]])
        coef, *_ = np.linalg.lstsq(A, a[:, 2], rcond=None)
        path.coef[h] = [float(c) for c in coef]
        g = float(coef[0] + coef[1] * R[L] + coef[2] * X[L])
        path.levels["V_kedja"][h] = float(y[L] * math.exp(g / 100))
    if short:
        path.reasons["V_kedja"] = f"V_kedja: < {MIN_TRAIN} training rows for h {short}"


def forecast(table: pd.DataFrame, target: Target, origin, brk: dict | None = None) -> Path:
    """Every model's path at `origin` from the prepared table, everything as_of(origin). Raises HoldoutClosed for an
    origin after the development period (G-E), before anything is read."""
    origin = guard.check(origin, f"D2 {target.name}", family=FAMILY)
    info = engine.InfoSet(table, origin)
    y = info.get(target.key)
    y = y[y > 0]
    path = Path(target, origin, None)
    if y.empty:
        for m in target.models:
            path.levels[m], path.reasons[m] = _nan_path(), f"{target.key}: nothing known"
        return path
    L = y.index.max()
    path.base = L
    path.levels["B0"] = {h: float(y[L]) for h in HORIZONS}
    path.levels["B1"] = _nan_path()
    crossing = [str(p) for p in pd.period_range(L - 3, L, freq=Q) if p in quarterly.known_breaks(brk or {}, origin)]
    if crossing:
        path.reasons["B1"] = f"B1: window crosses a definition break ({', '.join(crossing)})"
    else:
        try:
            b1 = n1.b1_path(y, [L + h for h in HORIZONS])
            path.levels["B1"] = {h: b1[L + h] for h in HORIZONS}
        except n1.NotAvailable as exc:
            path.reasons["B1"] = f"B1: {exc}"
    if "B2" in target.models:
        try:
            b2(info, L, path)
        except n1.NotAvailable as exc:
            path.levels["B2"], path.reasons["B2"] = _nan_path(), f"B2: {exc}"
    kedja(info, y, L, path)
    return path


# ------------------------------------------------------------------ development backtest


def run(table: pd.DataFrame, target: Target, end=guard.DEV_END) -> pd.DataFrame:
    """One row per (origin, h) with a first-vintage outcome known by DEV_END: levels and errors per model.
    Development only: origins up to `end` (any origin after 2025-06-30 raises HoldoutClosed while D2's holdout is
    closed) and rows known by DEV_END."""
    origins = dev_origins(end)
    for o in origins:  # refuse before reading anything
        guard.check(o, f"D2 {target.name}", family=FAMILY)
    t = prepare(guard.dev_table(table))
    outcomes = engine.first_vintages(t, target.key)
    brk = quarterly.breaks(t, quarterly.Aggregate(target.key, target.components)) if target.components else {}
    rows = []
    for o in origins:
        p = forecast(t, target, o, brk)
        if p.base is None:
            continue
        for h in HORIZONS:
            q = p.base + h
            if q not in outcomes.index or q in brk:
                continue
            if engine.known_at_origin(outcomes, q, o, f"{target.key} {q}"):
                continue
            y = float(outcomes.at[q, "value"])
            row = {"origin": o, "base": p.base, "h": h, "quarter": q, "outcome": y,
                   "outcome_known_from": outcomes.at[q, "known_from"], "n_train": p.n_train.get(h, 0)}
            for m in target.models:
                lv = p.levels.get(m, {}).get(h, float("nan"))
                row[m] = engine.log_error(lv, y) if np.isfinite(lv) and lv > 0 else float("nan")
            rows.append(row)
    cols = ["origin", "base", "h", "quarter", "outcome", "outcome_known_from", "n_train", *target.models]
    return pd.DataFrame(rows, columns=cols)


def scored(frame: pd.DataFrame, target: Target) -> pd.DataFrame:
    """Rolling-origin error distributions per h (F-C7): the pool for (model, h) at an origin holds only that h's
    errors whose outcome was known at the origin."""
    parts = []
    for h, g in frame.groupby("h"):
        g = g.set_index(g["origin"].dt.date.astype(str))
        s = intervals.score_frame(g[list(target.models)], g["origin"], g["outcome_known_from"])
        if len(s):
            parts.append(s.assign(h=h))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def evaluate(frame: pd.DataFrame, target: Target) -> dict:
    """Per h: n, MAE and bias per model on (a) the baselines' common rows, (b) V_kedja's rows with the baselines on
    the same rows; interval coverage and CRPS per model on its own rows with a distribution. Informational only."""
    base = list(BASELINES[target.name])
    sc = scored(frame, target)
    out = {}
    for h in HORIZONS:
        f = frame[frame["h"] == h]
        res = {"n_rows": len(f)}
        cb = f.dropna(subset=base)
        res["baselines"] = {"n": len(cb), **({"first": str(cb["base"].min()), "last": str(cb["base"].max())}
                                               if len(cb) else {}),
                            "metrics": {m: evaluation.metrics(cb[m]) for m in base} if len(cb) else {}}
        cv = f.dropna(subset=[*base, "V_kedja"])
        res["kedja"] = {"n": len(cv), "metrics": {m: evaluation.metrics(cv[m]) for m in [*base, "V_kedja"]}
                        if len(cv) else {}}
        sh = sc[sc["h"] == h] if len(sc) else sc
        res["intervals"] = intervals.calibration(sh) if len(sh) else pd.DataFrame()
        out[h] = res
    return out


def run_all(table: pd.DataFrame | None = None) -> dict:
    table = observations.load() if table is None else table
    res = {}
    for name, target in TARGETS.items():
        f = run(table, target)
        res[name] = {"frame": f, "eval": evaluate(f, target)}
    return res


# ------------------------------------------------------------------ report


def _c(x, nd=1, signed=False):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "–"
    return (f"{x:+.{nd}f}" if signed else f"{x:.{nd}f}").replace(".", ",").replace("-", "−")


def markdown(res: dict) -> str:
    lines = []
    for name, r in res.items():
        target = TARGETS[name]
        base = list(BASELINES[name])
        lines += [f"### {target.label} (`{target.key}`)", "",
                  "| h | n | Baskvartal L | " + " | ".join(f"MAE {m}" for m in base) + " | "
                  + " | ".join(f"Bias {m}" for m in base) + " | n V_kedja | MAE V_kedja | MAE bästa baslinje, samma rader |"
                  " Bias V_kedja |",
                  "|" + "---|" * (7 + 2 * len(base))]
        for h, e in r["eval"].items():
            b = e["baselines"]
            m = b["metrics"]
            span = f"{b['first']} – {b['last']}" if b["n"] else "–"
            maes = " | ".join(_c(m[x]["MAE"]) if m else "–" for x in base)
            bias = " | ".join(_c(m[x]["bias"], 1, True) if m else "–" for x in base)
            k = e["kedja"]
            if k["n"]:
                km = k["metrics"]
                best = min(base, key=lambda x: km[x]["MAE"])
                kv = f"{k['n']} | {_c(km['V_kedja']['MAE'])} | {_c(km[best]['MAE'])} ({best}) | {_c(km['V_kedja']['bias'], 1, True)}"
            else:
                kv = "0 | – | – | –"
            lines.append(f"| {h} | {b['n']} | {span} | {maes} | {bias} | {kv} |")
        lines += ["", f"Intervall ({target.key}), per modell och h, rader med fördelning (felpool per h, F-C7):", "",
                  "| h | Modell | n med fördelning | t / empirisk | Täckning 50 % | Täckning 80 % | Täckning 95 % | CRPS |",
                  "|---|---|---|---|---|---|---|---|"]
        any_cal = False
        for h, e in r["eval"].items():
            cal = e["intervals"]
            for _, c in cal.iterrows():
                any_cal = True
                lines.append(f"| {h} | {c['model']} | {c['n']} | {c['n_student_t']} / {c['n_empirical']} | "
                             f"{_c(100 * c['coverage_50'], 0)} % | {_c(100 * c['coverage_80'], 0)} % | "
                             f"{_c(100 * c['coverage_95'], 0)} % | {_c(c['crps'], 2)} |")
        if not any_cal:
            lines.append("| – | – | 0 | – | – | – | – | – |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    res = run_all()
    print(markdown(res))
    rows = []
    for name, r in res.items():
        for h, e in r["eval"].items():
            for m, v in e["baselines"]["metrics"].items():
                rows.append({"target": f"D2 {name}", "variant": f"{m} h{h}", "period": "dev <= 2025-06-30",
                             "n": v["n"], "MAE": round(v["MAE"], 4), "dm_p_vs_baseline": ""})
            k = e["kedja"]
            if k["n"]:
                rows.append({"target": f"D2 {name}", "variant": f"V_kedja h{h}", "period": "dev <= 2025-06-30",
                             "n": k["n"], "MAE": round(k["metrics"]["V_kedja"]["MAE"], 4), "dm_p_vs_baseline": ""})
    evaluation.log_run("d2_horizon_development", rows)
    for name, r in res.items():
        f = r["frame"]
        print(f"{name}: origins with rows {f['origin'].nunique()}, last origin {f['origin'].max().date()}, "
              f"last outcome known {pd.Timestamp(f['outcome_known_from'].max()).date()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
