"""N4: cloud revenue, rev_aws + rev_google_cloud + rev_msft_cloud (docs/mattregister.md "Steg 2", G-B, with R6's F-B4,
F-B7, F-B8, F-B9-F-B11 adopted verbatim). Shared machinery: quarterly.py and engine.py.

    python -m ai_tracker.nowcast backtest n4
    python -m ai_tracker.nowcast n4 --origin YYYY-MM-DD      live forecast -> forecasts/n4/<quarter>.json (never rewritten)

- Target `rev_cloud3`: the sum of the three components per calendar quarter, first version where all three exist
  (built here from the components' vintages, known_from = the latest component filing; sec.aggregate).
- Origin: calendar quarter end + 20 days (as N1). Target = the quarter just ended.
- B0, B1: quarterly.py. Definition breaks (F-B8, > 2 % restated comparative in a component) are not scored and B1's
  window may not cross one.
- V1 (F-B7): B1 + OLS of B1's miss on x = the latest known q/q log growth x 100 of the RPO sum (N6's target, MSFT +
  GOOGL + AMZN + ORCL, the latest quarter where all four are known), each training row with x as known at its own
  origin. At least 12 complete rows (F-B4).
- Holm family for step 2: {V1, DF}. DF (track C3) is not implemented here and enters with p = 1 (F-B9).
"""

from __future__ import annotations

import pandas as pd

from ai_tracker import observations
from ai_tracker.nowcast import n1, quarterly

TARGET = "rev_cloud3"
COMPONENTS = ("rev_aws", "rev_google_cloud", "rev_msft_cloud")
RPO = quarterly.Aggregate("rpo_hyp4", ("rpo_msft", "rpo_googl", "rpo_amzn", "rpo_orcl"))
VARIANTS = ["B0", "B1", "V1"]
MODELS = ["V1"]
FAMILY = ["V1", "DF"]
REVIEW_REQUIRED: dict[str, str] = {}  # V1 uses no extracted values (XBRL facts only)
CHAMPION = "B1"  # register: B1 unless a variant passes the rule (docs/resultat/n4.md)
FIRST_LIVE = pd.Timestamp("2027-01-20")  # 2026Q4
LABEL_SV = "Molnintäkter: AWS + Google Cloud + Microsoft Cloud"

origin_for = n1.origin_for
target_quarter = n1.target_quarter

SPEC = quarterly.Spec(
    nowcast="n4", label="N4", target=quarterly.Aggregate(TARGET, COMPONENTS), origin_for=origin_for,
    target_quarter=target_quarter, variants=VARIANTS, models=MODELS, family=FAMILY, review_required=REVIEW_REQUIRED,
    regressor=RPO, champion=CHAMPION)


def outcome_table(table: pd.DataFrame) -> pd.DataFrame:
    """The rows of the derived target (for the scorecard)."""
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
