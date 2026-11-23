"""G6: US industrial production, semiconductors and computers (Fed G.17), monthly, from federalreserve.gov.

Real vintages from the Board's release archive (2016-04-15 onwards, monthly releases and annual
revisions); the newest release from the Data Download Program. known_from = release date. Values first
published before 2016-04-15 get that date (the oldest archived vintage), which is conservative.
The index base year changes at some annual revisions (2017=100 until 2026-11-24, then 2022=100), so levels
are only comparable within one vintage; as_of() always returns one release's values for every month that
release revised. See sources/fed_g17.py and docs/kallor/fed_g17.md.
"""

from __future__ import annotations

from functools import partial

from ai_tracker.catalog import Spec
from ai_tracker.sources import fed_g17

LICENSE = ("Public domain (Board of Governors of the Federal Reserve System, www.federalreserve.gov/disclaimer.htm): "
           "\"Unless otherwise indicated, information on Board's website is in the public domain and may be "
           "copied and distributed without permission. Please cite to the Board as the source of the "
           "information.\" Source: Federal Reserve Board, G.17 Industrial Production and Capacity Utilization.")

LAG_DAYS = 14  # earliest first release in the archive 2016-2026 was 14 days after month end (typical 15-17)

SPECS = [
    Spec(
        key="us_ip_semis_m",
        branch="G6",
        label="Industriproduktion, halvledare och andra elektroniska komponenter (USA, NAICS 3344)",
        unit="index (basår enligt vintage), SA",
        freq="M",
        source="Federal Reserve G.17 (G3344), federalreserve.gov",
        fetch=partial(fed_g17.release_rows, "G3344"),
        lag_days=LAG_DAYS,
        license=LICENSE,
        revised=True,
        publish=True,
        question="Hur snabbt växer amerikansk halvledartillverkning?",
        note="Riktiga vintages ur Fed:s releasearkiv från 2016-04-15. NAICS 334413 publiceras inte separat i G.17; "
             "3344 är den finaste nivån.",
    ),
    Spec(
        key="us_ip_computers_m",
        branch="G6",
        label="Industriproduktion, datorer och kringutrustning (USA, NAICS 3341)",
        unit="index (basår enligt vintage), SA",
        freq="M",
        source="Federal Reserve G.17 (G3341), federalreserve.gov",
        fetch=partial(fed_g17.release_rows, "G3341"),
        lag_days=LAG_DAYS,
        license=LICENSE,
        revised=True,
        publish=True,
        question="Hur snabbt växer amerikansk tillverkning av datorer och servrar?",
        note="Riktiga vintages ur Fed:s releasearkiv från 2016-04-15.",
    ),
]
