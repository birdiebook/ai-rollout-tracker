"""B3: guidance with a systematic deviation (step 2, track C2). Shared by N1, N2 and (later) N3.

Registered in docs/mattregister.md, "Steg 2", G-B ("B3, guidance med systematisk avvikelse"), as made precise by the
entry "C0 preciseras efter granskning R6", which adopts docs/granskning/r6_c0.md verbatim:

- F-B1 (the recommended option): for company c, guided period P and origin position k,
  d_{c,P,k} = log(U_P / G_{c,P}(o_{P,k})), where o_{P,k} is the k-th registered origin whose target period lies in
  P and G_{c,P}(o) is the midpoint B2 uses at o. Positions: k = 1-3 for TSMC (the N2 origins of the quarter's three
  months), k = 1 for Nvidia (the N3 origin), k = 1-4 for Meta and Alphabet (the N1 origins of the year's four
  quarters). m_{c,k} is estimated per position; n = the number of periods P with d_{c,P,k}. B3 at origin o_{P',k}
  uses m_{c,k}.
- F-B2: U is the sum of the components' first vintages on the guidance's definition and currency, known at an origin
  when the last component's first vintage has known_from <= the origin. Revisions are never used.
- F-B3: m_c = w * dbar_c + (1 - w) * dbar_group, w = n_c / (n_c + 4). dbar_group is the unweighted mean of the
  company means among companies with the same guided quantity (GROUPS) and at least one known deviation, the company
  itself included. n_c >= 4 is required of the company's own n_c; with n_c < 4, m_c = 0.
- B3 = B2 computed with the midpoint x exp(m). Otherwise the same formulas as B2 (each nowcast applies this).

Fixed here where the text is silent (most conservative reading, docs/resultat/n1.md and n2.md):
- A deviation exists only where B2 actually used guidance at o_{P,k} (B2 fell back to B1: no G, no d).
- "Per position" also applies to the group mean: dbar_group at position k is formed from the group's deviations at
  the same position k (TSMC's k = 1 is pooled with Nvidia's k = 1, its only position).
- Leakage guard, applied at every origin: a deviation enters only if its outcome's known_from <= origin, and its
  guidance origin <= origin (implied, but checked).

Pools: each nowcast builds the deviations of its own companies (n1.b3_deviations, n2.b3_deviations). A group mean
needs every company of the group, so BUILDERS lists, per group, the functions that build its deviations from the
observation table. N3's successor adds its Nvidia builder to "quarterly_revenue"; N2's pool then picks it up.
"""

from __future__ import annotations

import importlib
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

SHRINK = 4  # w = n / (n + SHRINK)
MIN_N = 4  # the company's own n_c must be >= MIN_N, else m = 0
GROUPS = {"tsmc": "quarterly_revenue", "nvda": "quarterly_revenue", "meta": "fy_capex", "googl": "fy_capex"}
# group -> "module:function" building that group's deviations from an observation table (see module docstring)
BUILDERS = {
    "quarterly_revenue": ["ai_tracker.nowcast.n2:b3_deviations"],  # N3 (Nvidia) adds its builder here
    "fy_capex": ["ai_tracker.nowcast.n1:b3_deviations"],
}
COLUMNS = ["company", "group", "period", "position", "guidance_origin", "guidance", "outcome", "outcome_known_from",
           "d"]


def empty() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype=t) for c, t in
                         zip(COLUMNS, [str, str, str, int, "datetime64[ns]", float, float, "datetime64[ns]", float])})


def deviations(company: str, guidance: list, outcomes: dict) -> pd.DataFrame:
    """One row per (period P, position k) where B2 used guidance and U_P exists in the table.

    guidance: (period, position, guidance origin, G) for every registered origin where B2 used guidance.
    outcomes: period -> (U, known_from of U's last component), from first vintages only.
    """
    rows = []
    for period, k, origin, g in guidance:
        if str(period) not in outcomes or not (g > 0):
            continue
        u, kf = outcomes[str(period)]
        if not (u > 0):
            continue
        rows.append({"company": company, "group": GROUPS[company], "period": str(period), "position": int(k),
                     "guidance_origin": pd.Timestamp(origin), "guidance": float(g), "outcome": float(u),
                     "outcome_known_from": pd.Timestamp(kf), "d": math.log(u / g)})
    return pd.DataFrame(rows, columns=COLUMNS) if rows else empty()


def summed_outcomes(first: dict, periods: dict) -> dict:
    """U per guided period from first vintages: first = component series -> engine.first_vintages() frame;
    periods = guided period label -> list of (series, sub-period) components. A period with a missing component is
    left out (it is not known)."""
    out = {}
    for label, parts in periods.items():
        vals, kfs = [], []
        for series, p in parts:
            f = first.get(series)
            if f is None or p not in f.index:
                break
            vals.append(float(f.at[p, "value"]))
            kfs.append(pd.Timestamp(f.at[p, "known_from"]))
        else:
            if vals:
                out[str(label)] = (float(sum(vals)), max(kfs))
    return out


@dataclass(frozen=True)
class Shift:
    """m for one company, position and origin, with what it was formed from."""
    company: str
    position: int
    m: float  # natural-log shift applied to the guidance midpoint (0 when n < MIN_N)
    n: int  # the company's own number of known deviations at this position
    d_mean: float  # dbar_c (NaN when n = 0)
    group_mean: float  # dbar_group (NaN when no company in the group has a known deviation)
    w: float  # n / (n + SHRINK), 0 when n < MIN_N
    group_n: int  # companies in the group mean

    def as_dict(self) -> dict:
        f = lambda x: None if (isinstance(x, float) and math.isnan(x)) else x  # noqa: E731
        return {"company": self.company, "position": self.position, "m": self.m, "n": self.n,
                "d_mean": f(self.d_mean), "group_mean": f(self.group_mean), "w": self.w, "group_n": self.group_n}


def known(pool: pd.DataFrame, origin) -> pd.DataFrame:
    """Deviations whose outcome (and guidance) were known at `origin`. The only filter between pool and estimate."""
    origin = pd.Timestamp(origin)
    return pool[(pool["outcome_known_from"] <= origin) & (pool["guidance_origin"] <= origin)]


def shift(pool: pd.DataFrame, company: str, position: int, origin) -> Shift:
    """m_{c,k} at `origin` (F-B1, F-B3) from the deviations known at the origin."""
    g = known(pool, origin)
    g = g[(g["group"] == GROUPS[company]) & (g["position"] == int(position))]
    own = g.loc[g["company"] == company, "d"]
    n = int(len(own))
    means = g.groupby("company")["d"].mean()  # companies with >= 1 known deviation, the company itself included
    group_mean = float(means.mean()) if len(means) else float("nan")
    d_mean = float(own.mean()) if n else float("nan")
    if n < MIN_N:
        return Shift(company, int(position), 0.0, n, d_mean, group_mean, 0.0, int(len(means)))
    w = n / (n + SHRINK)
    return Shift(company, int(position), float(w * d_mean + (1 - w) * group_mean), n, d_mean, group_mean, w,
                 int(len(means)))


def group_pool(table: pd.DataFrame, group: str, skip: tuple = ()) -> pd.DataFrame:
    """Deviations of every company in `group` (BUILDERS), except the builders named in `skip` (a nowcast that
    already built its own companies' deviations passes its own builder)."""
    parts = []
    for ref in BUILDERS.get(group, []):
        if ref in skip:
            continue
        mod, fn = ref.split(":")
        parts.append(getattr(importlib.import_module(mod), fn)(table))
    parts = [p for p in parts if len(p)]
    if not parts:
        return empty()
    out = pd.concat(parts, ignore_index=True)
    return out[out["group"] == group].reset_index(drop=True)


def scaled(midpoint: float, m: float) -> float:
    """The B3 midpoint: midpoint x exp(m)."""
    return float(midpoint * np.exp(m))
