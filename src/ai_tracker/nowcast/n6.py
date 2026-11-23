"""N6: contracted demand, the RPO sum of MSFT, GOOGL, AMZN and ORCL (`rpo_hyp4`), docs/mattregister.md "Steg 2", G-B,
with R6's F-B4, F-B6, F-B8, F-B9-F-B11 adopted verbatim. Shared machinery: quarterly.py and engine.py.

    python -m ai_tracker.nowcast backtest n6
    python -m ai_tracker.nowcast n6 --origin YYYY-MM-DD      live forecast -> forecasts/n6/<quarter>.json (never rewritten)

- Target: first version of the sum where all four are known. RPO is a balance: the calendar quarter of the balance
  date (Oracle 31 Aug = Q3, filed in September, i.e. before the origin; F-B8). The sum is rebuilt here from the
  components with the catalog's own rule (identical to the catalog series rpo_hyp4).
- Origin: calendar quarter end + 20 days. B0 and B1 on the aggregate, without regard to components already known
  (F-B8, the literal naive reading); the number of evaluated quarters with a component known at the origin is reported.
- V1 (F-B6): B1 + OLS of B1's miss on x = the latest known q/q log growth x 100 of the N4 sum (AWS + Google Cloud +
  Microsoft Cloud) at the origin (normally q-1 vs q-2), each training row with x as known at its own origin.
  At least 12 complete rows (F-B4).
- Holm family for step 2: {V1} (F-B9).
"""

from __future__ import annotations

import pandas as pd

from ai_tracker import observations
from ai_tracker.nowcast import n1, n4, quarterly

TARGET = "rpo_hyp4"
COMPONENTS = n4.RPO.components
VARIANTS = ["B0", "B1", "V1"]
MODELS = ["V1"]
FAMILY = ["V1"]
REVIEW_REQUIRED: dict[str, str] = {}
CHAMPION = "B1"  # register: B1 unless a variant passes the rule (docs/resultat/n6.md)
FIRST_LIVE = pd.Timestamp("2027-01-20")  # 2026Q4

origin_for = n1.origin_for
target_quarter = n1.target_quarter

SPEC = quarterly.Spec(
    nowcast="n6", label="N6", target=quarterly.Aggregate(TARGET, COMPONENTS), origin_for=origin_for,
    target_quarter=target_quarter, variants=VARIANTS, models=MODELS, family=FAMILY, review_required=REVIEW_REQUIRED,
    regressor=quarterly.Aggregate(n4.TARGET, n4.COMPONENTS), champion=CHAMPION)


def outcome_table(table: pd.DataFrame) -> pd.DataFrame:
    return quarterly.prepare(table, SPEC)


def backtest(table: pd.DataFrame | None = None, log: bool = True) -> dict:
    table = observations.load() if table is None else table
    out = quarterly.backtest(table, SPEC, log, FIRST_LIVE)
    f = out["frame"]
    out["components_known"] = (f.loc[f["in_period"], "components_known"].value_counts().to_dict() if len(f) else {})
    return out


def format_report(out: dict) -> str:
    return (quarterly.format_report(out, SPEC)
            + f"\ncomponents already filed at the origin (evaluated quarters, count -> quarters): {out['components_known']}")


def write_live(table: pd.DataFrame, origin, out_dir, today=None):
    return quarterly.write_live(table, SPEC, origin, out_dir, today)
