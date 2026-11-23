"""G6: US semiconductor production (Fed G.17) and computer/electronics new orders (Census M3), monthly.

Both from ALFRED with real vintages (no API key): every value is stored with the ALFRED vintage date in
which it first appeared or changed, so revisions are real vintages, not backfill.
Why not the primary source: federalreserve.gov (G.17) is refused by the proxy; Census M3 is only
machine-readable through api.census.gov, which requires an API key (and the econ/currentdata export
returned HTTP 400). See docs/kallor/census_eu.md.
"""

from __future__ import annotations

from functools import partial

from ai_tracker.catalog import Spec
from ai_tracker.sources import alfred

LICENSE = ("Public Domain: Citation Requested (ALFRED/FRED series tag). FRED legal page: \"These series may "
           "be under copyright or in the public domain and may be used without permission, provided you do "
           "not engage in any prohibited use. When using, please cite the data source and acknowledge that "
           "you obtained the data from FRED\". Source: Board of Governors (G.17) / Census (M3) via ALFRED.")

SPECS = [
    Spec(
        key="us_ip_semis_m",
        branch="G6",
        label="Industriproduktion, halvledare och elektroniska komponenter (USA, NAICS 3344)",
        unit="index 2017=100, SA",
        freq="M",
        source="Federal Reserve G.17 via ALFRED (IPG3344S)",
        fetch=partial(alfred.fetch_release_rows, "IPG3344S"),
        lag_days=16,  # release-dated rows; first release 14-18 days after month end (2015-2026), 2025 shutdown later
        license=LICENSE,
        revised=True,
        publish=False,  # FRED terms restrict some uses (decision 2026-11: prefer primary sources)
        question="Hur snabbt växer amerikansk halvledartillverkning?",
        note="Riktiga vintages från ALFRED (första vintage 2015-02-18; äldre värden får det datumet).",
    ),
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
        publish=False,
        question="Hur stor är efterfrågan på datorer och elektronik från amerikansk industri?",
        note="Riktiga vintages från ALFRED (första vintage 2011-06-24). Första värdet kommer i förhandsrapporten "
             "om varaktiga varor, reviderat i den fullständiga M3-rapporten.",
    ),
]
