"""Aggregates over companies for followed questions (register 2026-11-26 "F0", (a); KL1 (b) "Lageraggregat").

Pure: numpy and pandas only, no catalog import, so series modules (which the catalog imports) can build their derived
catalog series with it.

A Formula is a ratio (or a sum, without a denominator) of weighted terms, each a component series at period p - offset.
A layer is the formula summed over its member companies: sums of the components, not a mean of the members' ratios.

Dating (as A5, series/avstamning.py): at every known_from d of any input, each input takes its latest vintage known on
d; a version exists only when every input has one, so a layer's version exists only once all its members have filed
for the period, and it is dated d (the latest component used). `missing(f, rows, period, when)` says which inputs a
period still lacks on a day, so a report can say which members are missing.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

QFREQ = "Q-DEC"  # calendar quarters (the companies' own mapping to them is done by the source series)


@dataclass(frozen=True)
class Term:
    series: str
    offset: int = 0  # p - offset
    weight: float = 1.0


@dataclass(frozen=True)
class Formula:
    key: str
    num: tuple[Term, ...]
    den: tuple[Term, ...] = ()  # empty: the value is the numerator
    scale: float = 1.0

    @property
    def components(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(t.series for t in (*self.num, *self.den)))


def sum4(series: str, weight: float = 1.0) -> tuple[Term, ...]:
    """The series summed over four quarters: p, p-1, p-2, p-3."""
    return tuple(Term(series, k, weight) for k in range(4))


def versions(rows: pd.DataFrame) -> dict[tuple[str, str], tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """(series, period) -> (known_from, value, is_backfill) arrays sorted by known_from."""
    out = {}
    r = rows.sort_values("known_from", kind="stable")
    for (s, p), g in r.groupby(["series", "period"], sort=False):
        out[(s, str(p))] = (g["known_from"].to_numpy(dtype="datetime64[ns]"), g["value"].to_numpy(dtype=float),
                            (g["source"] == "backfill").to_numpy())
    return out


def inputs(f: Formula, period: str, freq: str = QFREQ) -> list[tuple[str, str]]:
    """The (series, period) inputs a formula needs for `period`, in order, without repeats."""
    per = pd.Period(period, freq=freq)
    return list(dict.fromkeys((t.series, str(per - t.offset)) for t in (*f.num, *f.den)))


def derive(f: Formula, rows: pd.DataFrame, freq: str = QFREQ) -> pd.DataFrame:
    """Release-dated rows (period, value, known_from, source) of a formula from component rows in observation-table
    form. Pure: no I/O. A version per date on which an input gets a vintage, only when every input has one."""
    rows = rows[rows["series"].isin(f.components)].copy()
    if rows.empty:
        return pd.DataFrame(columns=["period", "value", "known_from", "source"])
    rows["known_from"] = pd.to_datetime(rows["known_from"])
    vers = versions(rows)
    anchor = f.num[0].series
    periods = sorted({p for (s, p) in vers if s == anchor})
    out = []
    for p in periods:
        per = pd.Period(p, freq=freq)
        num = [((t.series, str(per - t.offset)), t.weight) for t in f.num]
        den = [((t.series, str(per - t.offset)), t.weight) for t in f.den]
        need = list(dict.fromkeys(k for k, _ in num + den))
        if any(k not in vers for k in need):
            continue
        prev = None
        for d in np.unique(np.concatenate([vers[k][0] for k in need])):
            vals, backfill, ok = {}, False, True
            for k in need:
                kf, v, bf = vers[k]
                i = int(np.searchsorted(kf, d, side="right")) - 1
                if i < 0:
                    ok = False
                    break
                vals[k], backfill = v[i], backfill or bool(bf[i])
            if not ok:
                continue
            n = sum(w * vals[k] for k, w in num)
            if den:
                m = sum(w * vals[k] for k, w in den)
                if not np.isfinite(m) or m == 0:
                    continue
                value = f.scale * n / m
            else:
                value = f.scale * n
            if not np.isfinite(value):
                continue
            if prev is None or not np.isclose(value, prev, rtol=1e-12, atol=0):
                out.append((p, float(value), pd.Timestamp(d), "backfill" if backfill else "derived"))
                prev = value
    df = pd.DataFrame(out, columns=["period", "value", "known_from", "source"])
    return df.sort_values(["known_from", "period"], ignore_index=True)


def missing(f: Formula, rows: pd.DataFrame, period: str, when, freq: str = QFREQ) -> list[tuple[str, str]]:
    """The (series, period) inputs of `f` for `period` that have no vintage known on `when` (the missing-member rule:
    the aggregate has no value for the period until this list is empty)."""
    t = rows[(rows["series"].isin(f.components)) & (pd.to_datetime(rows["known_from"]) <= pd.Timestamp(when))]
    have = {(s, str(p)) for s, p in zip(t["series"], t["period"])}
    return [k for k in inputs(f, period, freq) if k not in have]
