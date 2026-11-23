"""Rolling-origin engine shared by the nowcasts (N1 in n1.py, N2 in n2.py, later N3-N4).

Contract, fixed so that a backtest and a live run see exactly the same information:

- A forecast is made at an *origin* date. Every input, including the target's own history, is read
  with `observations.as_of(series, origin)` (N1 through `InfoSet.get()`, N2 per series for speed).
  `vintage_known_from()` gives the known_from of the vintage as_of picked, for the input log.
- The outcome a forecast is scored against is the target's **first vintage** (the earliest known_from row
  for the period), never a later revision. `first_vintages()` reads it; it is the only function here that
  looks past the origin, and it is only used for scoring.
- An outcome whose first vintage is known on or before the origin is a forecast of a known number and is
  never scored (`known_at_origin()`).
- Errors are log(forecast) - log(outcome) * 100.
- Promotion (registered rule, read conservatively): a model variant passes only if every period's check
  passes (`period_check`, `passes`). Among the passing variants the lowest full-period MAE becomes champion,
  except variants in the nowcast's REVIEW_REQUIRED, which are only reported as conditional (`decide`).
- A live forecast is written once and never rewritten (`write_live`, `write_forecast`).

Pooled Diebold-Mariano (N1b): loss differences of several units (companies) per quarter. The mean is
over all unit-quarters (so it matches the pooled MAE) and the long-run variance is Newey-West on the
quarterly cross-sectional sums of the demeaned differences (Driscoll-Kraay), lag and the HLN correction
from the number of quarters, not the number of observations. Balanced panels: identical to a DM test on
the quarterly average loss difference.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ai_tracker import evaluation, observations


@dataclass
class InfoSet:
    """Everything known at `origin`. Records every series read, for the live forecast's input log."""

    table: pd.DataFrame
    origin: pd.Timestamp
    used: dict[str, list[str]] = field(default_factory=dict)  # series -> periods used

    def __post_init__(self):
        self.origin = pd.Timestamp(self.origin)

    def get(self, series: str) -> pd.Series:
        return observations.as_of(series, self.origin, self.table)

    def mark(self, series: str, periods) -> None:
        """Note that `periods` of `series` entered the forecast (for the input log only)."""
        self.used.setdefault(series, [])
        for p in periods:
            if str(p) not in self.used[series]:
                self.used[series].append(str(p))

    def inputs(self) -> list[dict]:
        """Inputs marked as used, with the value and known_from of the vintage that as_of picked."""
        out = []
        for series, periods in self.used.items():
            t = self.table[(self.table["series"] == series) & (self.table["known_from"] <= self.origin)]
            latest = t.sort_values("known_from").groupby("period").tail(1).set_index("period")
            for p in sorted(periods):
                r = latest.loc[p]
                out.append({"series": series, "period": p, "value": float(r["value"]),
                            "known_from": pd.Timestamp(r["known_from"]).date().isoformat(),
                            "source": str(r["source"])})
        return out


def first_vintages(table: pd.DataFrame, series: str) -> pd.DataFrame:
    """First published vintage per period: columns value, known_from (earliest known_from), on a PeriodIndex.
    For scoring only."""
    t = table[table["series"] == series]
    if t.empty:
        return pd.DataFrame({"value": pd.Series(dtype=float), "known_from": pd.Series(dtype="datetime64[ns]")})
    f = t.sort_values("known_from").groupby("period")[["value", "known_from"]].first()
    f.index = observations.to_periods(f.index, t["freq"].iloc[0])
    return f.sort_index()


def first_vintage(table: pd.DataFrame, series: str) -> pd.Series:
    """First published value per period, on a PeriodIndex. For scoring only."""
    if not (table["series"] == series).any():
        return pd.Series(dtype=float, name=series)
    return first_vintages(table, series)["value"].rename(series)


def first_known_from(table: pd.DataFrame, series: str) -> pd.Series:
    """known_from of the first vintage per period."""
    return first_vintages(table, series)["known_from"]


def vintage_known_from(rows: pd.DataFrame, origin) -> pd.Series:
    """known_from of the vintage that as_of(origin) uses for each period of `rows` (one series; the same
    selection rule as as_of: the latest known_from <= origin), on a PeriodIndex."""
    t = rows[rows["known_from"] <= origin]
    kf = t.sort_values("known_from").groupby("period")["known_from"].last()
    kf.index = observations.to_periods(kf.index, rows["freq"].iloc[0])
    return kf


def known_at_origin(outcomes: pd.DataFrame, period, origin, label: str) -> str | None:
    """The guard every backtest applies before scoring: if the first vintage of `period` (outcomes =
    first_vintages()) is known on or before `origin`, the forecast would be of a known number. Returns the note
    for attrs["known_at_origin"] in that case, None when the period may be scored."""
    kf = outcomes.at[period, "known_from"]
    return f"{label} (filed {pd.Timestamp(kf).date()})" if kf <= origin else None


def log_error(forecast: float, outcome: float) -> float:
    return float((math.log(forecast) - math.log(outcome)) * 100)


# ------------------------------------------------------------------ pooled DM


def pooled_dm(frame: pd.DataFrame, a: str, b: str, h: int = 1) -> evaluation.DMResult:
    """DM on absolute-error loss, pooled over units. `frame` has columns quarter, unit, <a>, <b> (errors).

    mean = average over unit-quarters; variance = Newey-West on quarterly sums of demeaned differences
    (Driscoll-Kraay), lag and HLN correction from T = number of quarters; p from t with T-1 df.
    """
    f = frame.dropna(subset=[a, b])
    d = f[a].abs() - f[b].abs()
    n_obs = len(d)
    if f["quarter"].nunique() < 3:  # too few common periods for a DM test (HLN factor is 0 at T = 1)
        return evaluation.DMResult(int(f["quarter"].nunique()), 0, float(d.mean()) if n_obs else float("nan"),
                                   0.0, float("nan"), float("nan"), 0.0)
    mean = float(d.mean())
    sums = (d - mean).groupby(f["quarter"]).sum().sort_index().to_numpy()
    T = len(sums)
    lag = evaluation.newey_west_lag(T)
    lrv = float(sums @ sums / T)
    for k in range(1, lag + 1):
        lrv += 2 * (1 - k / (lag + 1)) * (sums[k:] @ sums[:-k]) / T
    hln = math.sqrt((T + 1 - 2 * h + h * (h - 1) / T) / T)
    se = math.sqrt(max(lrv, 0.0) * T) / n_obs / hln
    if se == 0:
        return evaluation.DMResult(T, lag, mean, 0.0, float("nan"), float("nan"), 0.0)
    stat = mean / se
    return evaluation.DMResult(T, lag, mean, se, stat, evaluation.t_two_sided_p(stat, T - 1),
                               evaluation.MDE_FACTOR * se)


# ------------------------------------------------------------------ promotion rule

PROMOTION_ALPHA = 0.10  # Holm-adjusted p must be below this (register, N1 and N2)


def best_baseline(mae: dict, baselines=("B0", "B1")) -> str:
    """The baseline with the lowest MAE; ties go to the earlier one in `baselines`."""
    return min(baselines, key=lambda b: (mae[b], list(baselines).index(b)))


def period_check(mae: float, best_mae: float, holm_p: float | None = None, alpha: float = PROMOTION_ALPHA) -> dict:
    """One period of the rule: MAE below the best baseline's, and Holm-p < alpha where the period tests it."""
    c = {"holm_p": holm_p, "holm_ok": bool(holm_p < alpha)} if holm_p is not None else {}
    return {**c, "mae": mae, "best_mae": best_mae, "mae_ok": bool(mae < best_mae)}


def passes(checks: dict) -> bool:
    """A variant passes when every period's check passes (period -> period_check())."""
    return all(c["mae_ok"] and c.get("holm_ok", True) for c in checks.values())


@dataclass
class Decision:
    champion: str
    winners: list  # passing variants that may become champion
    conditional: dict  # variant -> status, for variants that pass but need a review first


def decide(passed: dict, mae_full: dict, review_required: dict, default: str = "B1") -> Decision:
    """Champion = the passing variant with the lowest full-period MAE, else `default`. A passing variant in
    `review_required` is only reported as conditional and never becomes champion."""
    conditional = {v: review_required[v] for v in passed if passed[v] and v in review_required}
    winners = [v for v in passed if passed[v] and v not in review_required]
    champion = min(winners, key=lambda v: mae_full[v]) if winners else default
    return Decision(champion, winners, conditional)


# ------------------------------------------------------------------ live forecast file


def write_live(path: Path, origin, build, today=None, stamp_key: str = "written_utc") -> Path:
    """Write the live forecast `build()` returns, once. Refuses an origin after today (UTC; as_of would not be
    the real information set) and an existing file, before anything is computed."""
    origin = pd.Timestamp(origin)
    today = pd.Timestamp(today or datetime.now(timezone.utc).date())
    if origin > today:
        raise ValueError(f"origin {origin.date()} is in the future: as_of would not be the real information set")
    if Path(path).exists():
        raise FileExistsError(f"{path} already exists; live forecasts are never rewritten")
    return write_forecast(path, build(), stamp_key)


def write_forecast(path: Path, payload: dict, stamp_key: str = "written_utc") -> Path:
    """Write a live forecast. Refuses to overwrite: the timestamp is the proof (CLAUDE.md, protected)."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"{path} already exists; live forecasts are never rewritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**payload, stamp_key: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "git_sha": evaluation.git_sha()}
    with path.open("x", encoding="utf-8") as f:  # "x": fails if the file appeared meanwhile
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path


def summary(errors: pd.Series) -> dict:
    return evaluation.metrics(errors.to_numpy())
