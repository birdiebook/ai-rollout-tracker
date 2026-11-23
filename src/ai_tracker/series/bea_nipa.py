"""G5: BEA private fixed investment in information processing equipment and software, quarterly.

Current dollars, seasonally adjusted at annual rates, millions of USD (NIPA table 5.3.5 / 1.5.5).
Flat files hold only the latest vintage: everything before our first fetch is backfill and carries later
revisions (advance -> second -> third estimate -> annual and comprehensive revisions). Leakage flag.
known_from = max(quarter end + 31 days, documented first release): the advance GDP estimate came 25-31
days after the quarter in 2013-2026 (first ALFRED vintage of A679RC1Q027SBEA containing the quarter);
later releases (shutdowns) are listed in LATE.
"""

from __future__ import annotations

from functools import partial

from ai_tracker import publication
from ai_tracker.catalog import Spec
from ai_tracker.sources import bea_nipa

LICENSE = ("US federal work, free under 17 U.S.C. § 105 (BEA's own policy page could not be read). FRED tags "
           "the BEA series \"Public Domain: Citation Requested\". Source: U.S. Bureau of Economic Analysis.")
LAG_DAYS = 31
LATE = {"2013Q3": "2013-11-07", "2018Q4": "2019-02-28", "2025Q3": "2025-12-23", "2025Q4": "2026-02-20"}
SERIES = {  # key -> (NIPA code, label)
    "us_pfi_info_proc_eq_sw": ("A679RC", "Privata investeringar i informationsbehandlingsutrustning och programvara"),
    "us_pfi_info_proc_eq": ("Y034RC", "Privata investeringar i informationsbehandlingsutrustning"),
    "us_pfi_computers": ("B935RC", "Privata investeringar i datorer och kringutrustning"),
    "us_pfi_software": ("B985RC", "Privata investeringar i programvara"),
}

SPECS = [
    Spec(
        key=key,
        branch="G5",
        label=f"{label} (USA)",
        unit="MUSD, SAAR, löpande priser",
        freq="Q",
        source=f"BEA NIPA flat file NipaDataQ.txt ({code})",
        fetch=partial(bea_nipa.fetch, code),
        lag_days=LAG_DAYS,
        license=LICENSE,
        revised=True,
        publish=True,
        question="Hur mycket investerar amerikanska företag i IT-utrustning och programvara?",
        note="Bara senaste vintage: backfill med revideringar (läckagerisk). Se docs/kallor/census_eu.md.",
    )
    for key, (code, label) in SERIES.items()
]
for _s in SPECS:
    publication.LATE_RELEASES.setdefault(_s.key, {}).update(LATE)
