"""Holdout guard for the complex method families C3, C4 and D2 (docs/mattregister.md G-E, F-E1-F-E6).

The holdout (forecast origins 2025-07-01 to the day before each target's first live origin) was OPENED for C3 on
2026-11-24 (docs/holdout_logg.md, owner approval in docs/beslutslogg.md). While a family is closed, any factor
estimate, factor path, DF forecast or DF error with an origin (computation date) after DEV_END raises HoldoutClosed.
Opening it is a commit that sets HOLDOUT_OPEN = True after the owner's approval, logged in docs/holdout_logg.md with
date, git sha and what is evaluated (G-E). It is opened once per family (F-E3) and C4 must be locked first (F-E4).

Families: `HOLDOUT_OPEN` is C3's flag (and C4's, which builds on C3's factors). Any other complex family passes its
name to `check` (e.g. family="D2") and is open only when the name is in `OPEN_FAMILIES`, so opening one family never
opens another.

Live runs of a closed family (`LIVE_FROM`): a family whose holdout is never tested (D2: n < 8 origins per horizon
group, register entry "2026-11-24 - D2: n i holdout-testet räknas i prognosdagar", F-E6) goes straight into the live
register as a shadow. `check(..., live=True)` then allows an origin on or after the family's first live origin, and
only that: an origin inside the holdout (after DEV_END and before the first live origin) still raises, live or not,
so the holdout is never computed and never evaluated. A development run never passes live=True.
"""

from __future__ import annotations

import pandas as pd

DEV_END = pd.Timestamp("2025-06-30")
HOLDOUT_START = pd.Timestamp("2025-07-01")
HOLDOUT_OPEN = True  # opened 2026-11-24 for C3 after the owner's approval (G-E), docs/holdout_logg.md
OPEN_FAMILIES: frozenset[str] = frozenset()  # other families opened the same way, e.g. {"D2"}
# First live origin per closed family that goes live as a shadow without a holdout test (F-E6). D2: N1/N4's first
# live origin (2026Q4 + 20 days); the holdout ends the day before (F-E2, holdout.FIRST_LIVE).
LIVE_FROM: dict[str, pd.Timestamp] = {"D2": pd.Timestamp("2027-01-20")}


class HoldoutClosed(RuntimeError):
    """An origin after the development period was requested while the holdout is closed."""


def check(origin, what: str = "factor", family: str | None = None, live: bool = False) -> pd.Timestamp:
    """The origin, or HoldoutClosed if it is after DEV_END while the family's holdout is closed (family None = C3).
    live=True also allows an origin on or after the family's first live origin (LIVE_FROM), never one inside the
    holdout."""
    origin = pd.Timestamp(origin)
    is_open = HOLDOUT_OPEN if family is None else family in OPEN_FAMILIES
    if live and family in LIVE_FROM and origin >= LIVE_FROM[family]:
        return origin
    if origin > DEV_END and not is_open:
        raise HoldoutClosed(f"{what}: origin {origin.date()} is after {DEV_END.date()}; the "
                            f"{family or 'C3'} holdout is closed (G-E)")
    return origin


def dev_table(table: pd.DataFrame) -> pd.DataFrame:
    """The rows known on or before DEV_END: a development run cannot see anything published later (F-E1)."""
    return table[pd.to_datetime(table["known_from"]) <= DEV_END]
