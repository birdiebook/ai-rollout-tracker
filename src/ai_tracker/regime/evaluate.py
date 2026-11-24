"""F-D6 criteria for C4 (docs/steg2/c4_spec.md section 5). C4 is descriptive and is never promoted.

(a) frequency of reported shifts and breaks; (b) share of computation dates where the real-time reported state
differs from the state given by the same rule on the smoothed probabilities of the window's last day; (c) Spearman's
rho between P(slowdown) on the latest computation date <= the forecast origin and the main model's absolute error
(N1 B1, N2 B3, the main models at the lock), information only. Every function is guarded by the window's last date.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from ai_tracker.factor import realtime as factor_rt
from ai_tracker.regime import guard
from ai_tracker.regime import realtime as rt
from ai_tracker.state import measures

MAIN = {"N1": "B1", "N2": "B3"}  # main models on the lock date 2026-11-24


def frequency(states: pd.DataFrame, breaks: pd.DataFrame, start, end) -> dict:
    """(a) on computation dates in [start, end]."""
    guard.check(end, "C4 evaluation")
    s = states[(states["date"] >= pd.Timestamp(start)) & (states["date"] <= pd.Timestamp(end))]
    b = breaks[(breaks["date"] >= pd.Timestamp(start)) & (breaks["date"] <= pd.Timestamp(end))]
    out = {"ms": {}, "bocpd": {}}
    for block, g in s.groupby("block"):
        out["ms"][block] = {
            "dates_with_p": int(g["p_slow"].notna().sum()),
            "first_p": str(g.loc[g["p_slow"].notna(), "date"].min().date()) if g["p_slow"].notna().any() else None,
            "to_slowdown": int((g["shift"] == rt.SLOWDOWN).sum()),
            "to_expansion": int((g["shift"] == rt.EXPANSION).sum()),
            "months_expansion": int((g["state"] == rt.EXPANSION).sum()),
            "months_slowdown": int((g["state"] == rt.SLOWDOWN).sum()),
        }
    evaluated = b[b["p_recent"].notna()]
    out["bocpd"] = {
        "series_dates": int(len(evaluated)),
        "series": int(evaluated["series"].nunique()),
        "breaks": int(b["break"].sum()),
        "per_100": float(100 * b["break"].sum() / len(evaluated)) if len(evaluated) else float("nan"),
        "by_branch": {k: int(v) for k, v in b[b["break"]].groupby("branch").size().items()},
        "by_series": {k: int(v) for k, v in b[b["break"]].groupby("series").size().items()},
    }
    return out


def reclassification(table: pd.DataFrame, states: pd.DataFrame, start, end) -> dict:
    """(b): per block, the share of dates in [start, end] where the real-time reported state differs from the
    F-D2 rule applied to the smoothed probabilities from the MS fitted on `end`'s factor path."""
    end = guard.check(end, "C4 evaluation")
    t = rt.truncate(table, end)
    vint = factor_rt.vintage(t, end)
    fctx = measures.Context(factor_rt.truncate(t, end))
    out = {}
    for block in rt.BLOCKS:
        sm = rt.smoothed_probabilities(vint, fctx, end, block)
        g = states[(states["block"] == block) & (states["date"] >= pd.Timestamp(start))
                   & (states["date"] <= end)]
        if sm.empty or g.empty:
            out[block] = {"n": 0, "share_differs": float("nan")}
            continue
        smoothed_state = rt.state_sequence(sm)
        real = pd.Series(g["state"].to_numpy(), index=pd.DatetimeIndex(g["date"]).to_period("M"))
        both = real.notna() & real.index.isin(smoothed_state.index)
        real = real[both]
        sms = smoothed_state.reindex(real.index)
        ok = sms.notna()
        real, sms = real[ok], sms[ok]
        out[block] = {"n": int(len(real)), "share_differs": float((real != sms).mean()) if len(real) else float("nan"),
                      "months_slowdown_smoothed": int((sms == rt.SLOWDOWN).sum()),
                      "months_slowdown_realtime": int((real == rt.SLOWDOWN).sum())}
    return out


def _main_errors(table: pd.DataFrame) -> dict[str, pd.DataFrame]:
    from ai_tracker.nowcast import n1, n2

    f1 = n1.backtest_unit(table, n1.TARGET)
    f2 = n2.run(table)
    out = {}
    for key, f in (("N1", f1), ("N2", f2)):
        e = f[f"e_{MAIN[key]}"] if f"e_{MAIN[key]}" in f else f[MAIN[key]]
        out[key] = pd.DataFrame({"origin": pd.to_datetime(f["origin"]).to_numpy(),
                                 "outcome_known_from": pd.to_datetime(f["outcome_known_from"]).to_numpy(),
                                 "abs_error": np.abs(np.asarray(e, float))})
    return out


def association(ms_frame: pd.DataFrame, errors: dict[str, pd.DataFrame], start, end) -> dict:
    """(c): Spearman's rho and n between P(slowdown) per block on the latest computation date <= origin and |e|,
    for forecasts with origin in [start, end] and outcome known by `end` (F-E1). Information only."""
    end = guard.check(end, "C4 evaluation")
    out = {}
    for target, e in errors.items():
        e = e[(e["origin"] >= pd.Timestamp(start)) & (e["origin"] <= end) & (e["outcome_known_from"] <= end)
              & np.isfinite(e["abs_error"])]
        for block in rt.BLOCKS:
            g = ms_frame[(ms_frame["block"] == block) & ms_frame["p_slow"].notna()].sort_values("date")
            if g.empty or e.empty:
                out[(target, block)] = {"n": 0, "rho": float("nan")}
                continue
            e = e.assign(origin=pd.to_datetime(e["origin"]).astype("datetime64[ns]"))
            g = g.assign(date=pd.to_datetime(g["date"]).astype("datetime64[ns]"))
            m = pd.merge_asof(e.sort_values("origin"), g[["date", "p_slow"]], left_on="origin", right_on="date",
                              direction="backward").dropna(subset=["p_slow"])
            rho = float(stats.spearmanr(m["p_slow"], m["abs_error"]).statistic) if len(m) >= 3 else float("nan")
            out[(target, block)] = {"n": int(len(m)), "rho": rho,
                                    "first": str(m["origin"].min().date()) if len(m) else None,
                                    "last": str(m["origin"].max().date()) if len(m) else None}
    return out
