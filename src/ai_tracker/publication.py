"""Publication calendar: when a value was really known.

`Spec.lag_days` is the usual delay after period end. Releases that came later than usual are listed
in LATE_RELEASES with their documented date (and the source in docs/publiceringskalender.md), and

    known_from = max(period end + lag_days, documented release date)

Release-dated sources (SEC filings, company press releases) carry their own date and skip this.
Pattern from kpif-nowcast (K11 audit), generalised to any period frequency.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# series key -> {period string: release date}
LATE_RELEASES: dict[str, dict[str, str]] = {}


def period_end(periods: pd.PeriodIndex) -> pd.DatetimeIndex:
    """Last calendar day of each period (midnight)."""
    return pd.DatetimeIndex(periods.end_time.normalize())


def known_from(series: str, periods: pd.PeriodIndex, lag_days: int,
               late: dict[str, dict[str, str]] | None = None) -> pd.DatetimeIndex:
    """max(period end + lag, documented release date) per period."""
    base = period_end(periods) + pd.Timedelta(days=lag_days)
    dates = (LATE_RELEASES if late is None else late).get(series, {})
    if not dates:
        return base
    extra = pd.DatetimeIndex([pd.Timestamp(dates[str(p)]) if str(p) in dates else pd.NaT for p in periods])
    later = np.asarray(extra > base)
    return pd.DatetimeIndex(np.where(later, extra.to_numpy(), base.to_numpy()))
