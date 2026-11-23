"""Rolling-origin engine shared by the nowcasts (N1, later N2-N4).

Contract, fixed so that a backtest and a live run see exactly the same information:

- A forecast is made at an *origin* date. Every input, including the target's own history, is read
  through `InfoSet.get()`, which is `observations.as_of(series, origin)`. Nothing else touches the table.
- The outcome a forecast is scored against is the target's **first vintage** (the earliest known_from row
  for the period), never a later revision. `first_vintage()` reads it; it is the only function here that
  looks past the origin, and it is only used for scoring.
- Errors are log(forecast) - log(outcome) * 100.

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


def first_vintage(table: pd.DataFrame, series: str) -> pd.Series:
    """First published value per period (earliest known_from), on a PeriodIndex. For scoring only."""
    t = table[table["series"] == series]
    if t.empty:
        return pd.Series(dtype=float, name=series)
    s = t.sort_values("known_from").groupby("period")["value"].first()
    s.index = observations.to_periods(s.index, t["freq"].iloc[0])
    return s.sort_index().rename(series)


def first_known_from(table: pd.DataFrame, series: str) -> pd.Series:
    t = table[table["series"] == series]
    s = t.groupby("period")["known_from"].min()
    s.index = observations.to_periods(s.index, t["freq"].iloc[0])
    return s.sort_index()


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


# ------------------------------------------------------------------ live forecast file


def write_forecast(path: Path, payload: dict) -> Path:
    """Write a live forecast. Refuses to overwrite: the timestamp is the proof (CLAUDE.md, protected)."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"{path} already exists; live forecasts are never rewritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**payload, "written_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "git_sha": evaluation.git_sha()}
    with path.open("x", encoding="utf-8") as f:  # "x": fails if the file appeared meanwhile
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path


def summary(errors: pd.Series) -> dict:
    return evaluation.metrics(errors.to_numpy())
