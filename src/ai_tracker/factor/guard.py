"""Holdout guard for the complex method families C3 and C4 (docs/mattregister.md G-E, F-E1-F-E6).

The holdout (forecast origins 2025-07-01 to the day before each target's first live origin) is CLOSED. Any factor
estimate, factor path, DF forecast or DF error with an origin (computation date) after DEV_END raises HoldoutClosed.
Opening it is a commit that sets HOLDOUT_OPEN = True after the owner's approval, logged in docs/holdout_logg.md with
date, git sha and what is evaluated (G-E). It is opened once per family (F-E3) and C4 must be locked first (F-E4).
"""

from __future__ import annotations

import pandas as pd

DEV_END = pd.Timestamp("2025-06-30")
HOLDOUT_START = pd.Timestamp("2025-07-01")
HOLDOUT_OPEN = False  # set only by the orchestrator after the owner's approval (G-E)


class HoldoutClosed(RuntimeError):
    """An origin after the development period was requested while the holdout is closed."""


def check(origin, what: str = "factor") -> pd.Timestamp:
    origin = pd.Timestamp(origin)
    if origin > DEV_END and not HOLDOUT_OPEN:
        raise HoldoutClosed(f"{what}: origin {origin.date()} is after {DEV_END.date()}; the C3 holdout is closed (G-E)")
    return origin


def dev_table(table: pd.DataFrame) -> pd.DataFrame:
    """The rows known on or before DEV_END: a development run cannot see anything published later (F-E1)."""
    return table[pd.to_datetime(table["known_from"]) <= DEV_END]
