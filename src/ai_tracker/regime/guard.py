"""Holdout guard for C4 (register G-E, F-D6, F-E3, F-E4; docs/steg2/c4_spec.md section 5).

Same guard as C3 (factor.guard: DEV_END = 2025-06-30, HoldoutClosed, dev_table) with C4's own flag: the holdout is
opened once per method family (F-E3). Any MS estimate, BOCPD run, reported shift or break, or evaluation with a
computation date after DEV_END raises HoldoutClosed while HOLDOUT_OPEN is False. C3's factors keep their own guard,
so a C4 computation after DEV_END also needs C3's holdout to be open.
"""

from __future__ import annotations

import pandas as pd

from ai_tracker.factor.guard import DEV_END, HOLDOUT_START, HoldoutClosed, dev_table  # noqa: F401

HOLDOUT_OPEN = True  # opened 2026-11-24 for C4 with C3, after the owner's approval (G-E), docs/holdout_logg.md


def check(date, what: str = "regime") -> pd.Timestamp:
    date = pd.Timestamp(date)
    if date > DEV_END and not HOLDOUT_OPEN:
        raise HoldoutClosed(f"{what}: computation date {date.date()} is after {DEV_END.date()}; "
                            f"the C4 holdout is closed (G-E)")
    return date
