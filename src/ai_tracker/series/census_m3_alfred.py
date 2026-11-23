"""G6: US computer/electronics new orders (Census M3), monthly, via ALFRED. PENDING REPLACEMENT.

Interim source: ALFRED gives real vintages without a key, but FRED/ALFRED terms restrict use "in
connection with ... machine learning" (decision 2026-11: prefer primary sources). Census M3 is only
machine-readable through api.census.gov, which requires a (free) API key that has not been registered;
the econ/currentdata export returned HTTP 400. Replace with the Census API once a key exists, and keep
publish=False until then. Fed G.17 moved to the primary source (series/fed_g17.py). See
docs/kallor/census_eu.md and docs/kallor/fed_g17.md.
"""

from __future__ import annotations

from functools import partial

from ai_tracker.catalog import Spec
from ai_tracker.sources import alfred

LICENSE = ("Public Domain: Citation Requested (ALFRED/FRED series tag). FRED legal page: \"These series may "
           "be under copyright or in the public domain and may be used without permission, provided you do "
           "not engage in any prohibited use. When using, please cite the data source and acknowledge that "
           "you obtained the data from FRED\". Source: Census (M3) via ALFRED.")

SPECS = [
    Spec(
        key="us_orders_computers_electronics_m",
        branch="G6",
        label="Nyorder, datorer och elektroniska produkter (USA, M3)",
        unit="MUSD, SA",
        freq="M",
        source="Census M3 via ALFRED (A34SNO)",
        fetch=partial(alfred.fetch_release_rows, "A34SNO"),
        lag_days=26,  # release-dated rows; advance durable goods report 21-29 days after month end
        license=LICENSE,
        revised=True,
        publish=False,  # pending: replace ALFRED with the Census API (needs a key); FRED terms restrict ML use
        question="Hur stor är efterfrågan på datorer och elektronik från amerikansk industri?",
        note="Riktiga vintages från ALFRED (första vintage 2011-06-24). Första värdet kommer i förhandsrapporten "
             "om varaktiga varor, reviderat i den fullständiga M3-rapporten. Interimskälla: ska ersättas "
             "med Census API när en nyckel finns.",
    ),
]
