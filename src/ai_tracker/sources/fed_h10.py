"""Federal Reserve H.10: daily noon buying rates in New York, from the Board's historical-rates pages (track CN1).

Primary source, no key: www.federalreserve.gov/releases/h10/hist/dat00_<code>.htm holds the whole daily history of
one currency (from January 2000 for the Chinese renminbi, code "ch"), in currency units per US dollar, "ND" on days
without a rate. The page carries the date of the weekly H.10 release it belongs to ("Release Date: Monday, ...").

Only the current vintage exists here. Noon buying rates are certified rates of the day and are not revised in
practice; that is an assumption, not checked against archived releases (docs/kallor/kina_sec.md).

Terms (www.federalreserve.gov/disclaimer.htm): "Unless otherwise indicated, information on Board's website is in the
public domain and may be copied and distributed without permission. Please cite to the Board as the source of the
information."
"""

from __future__ import annotations

import re
from functools import lru_cache

import pandas as pd

from ai_tracker import http

SOURCE = "fed_h10"
URL = "https://www.federalreserve.gov/releases/h10/hist/dat00_{code}.htm"
ROW = re.compile(r"<tr[^>]*>\s*<th[^>]*>\s*(\d{1,2}-[A-Z]{3}-\d{2})\s*</th>\s*<td[^>]*>\s*([^<]*?)\s*</td>", re.I)
RELEASE = re.compile(r"Release Date:\s*(?:<[^>]+>\s*)*\w+day,\s*(\w+ \d{1,2}, \d{4})")


def parse_page(page: str) -> tuple[pd.Series, pd.Timestamp | None]:
    """(daily rates on Timestamps, release date) of one historical-rates page; ND days are left out."""
    vals = {}
    for d, v in ROW.findall(page):
        if v.upper() == "ND" or not v:
            continue
        vals[pd.to_datetime(d, format="%d-%b-%y")] = float(v)
    m = RELEASE.search(page)
    return pd.Series(vals, dtype=float).sort_index(), (pd.Timestamp(m.group(1)) if m else None)


@lru_cache(maxsize=None)
def daily(code: str = "ch") -> pd.Series:
    """Daily rates (currency per USD) of one H.10 currency; one request per process."""
    rates, _ = parse_page(http.get(URL.format(code=code), SOURCE).text)
    return rates


MIN_DAYS = 55  # a calendar quarter has 61-64 business days; fewer quoted days than this: no average


def quarterly_mean(rates: pd.Series) -> pd.Series:
    """Mean of the daily rates per calendar quarter (Q-DEC periods); quarters with fewer than MIN_DAYS quoted days
    (the current, unfinished quarter, or a gap in the source) are left out."""
    if rates.empty:
        return pd.Series(dtype=float)
    q = rates.groupby(rates.index.to_period("Q-DEC"))
    out = q.mean()[q.size() >= MIN_DAYS]
    last = rates.index.max()
    return out[[p.end_time.normalize() <= last for p in out.index]]
