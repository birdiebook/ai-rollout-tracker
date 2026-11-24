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

# ------------------------------------------------------------------ track M1: release archive, real vintages
# GDP contributions (NIPA table 1.5.2), real GDP growth, and imports of computers, peripherals and parts (tables
# 4.2.2, 4.2.5, 4.2.6). Release-dated: known_from = "Data published" of each archived release since 2017-10-27;
# values first published earlier get that first archived date. Definitions in docs/mattregister.md (2026-11-24, M1).
# Not core series. The categories are broader than AI. See docs/kallor/makro_bea_bls.md.

ARCHIVE_SOURCE = "BEA NIPA release archive (apps.bea.gov/histdata), {table}, {code}"
ARCHIVE_NOTE = "Riktiga vintages ur BEA:s releasearkiv från 2017-10-27. Kategorin är bredare än AI."
ARCHIVE_SERIES = [  # key, branch, codes, label, unit, table, question
    ("ai_invest_contrib_gross", "G5", ("Y034RY", "B985RY"),
     "Bidrag till real BNP-tillväxt från informationsbehandlingsutrustning och programvara",
     "procentenheter, årstakt (SAAR)", "tabell 1.5.2 rad 31 + 38",
     "Hur mycket av USA:s BNP-tillväxt kommer från investeringar i IT-utrustning och programvara?"),
    ("us_gdp_contrib_info_proc_eq", "G5", "Y034RY",
     "Bidrag till real BNP-tillväxt från informationsbehandlingsutrustning",
     "procentenheter, årstakt (SAAR)", "tabell 1.5.2 rad 31",
     "Hur mycket bidrar investeringar i IT-utrustning till BNP-tillväxten?"),
    ("us_gdp_contrib_computers", "G5", "B935RY",
     "Bidrag till real BNP-tillväxt från datorer och kringutrustning",
     "procentenheter, årstakt (SAAR)", "tabell 1.5.2 rad 32",
     "Hur mycket bidrar investeringar i datorer och servrar till BNP-tillväxten?"),
    ("us_gdp_contrib_software", "G5", "B985RY",
     "Bidrag till real BNP-tillväxt från programvara",
     "procentenheter, årstakt (SAAR)", "tabell 1.5.2 rad 38",
     "Hur mycket bidrar investeringar i programvara till BNP-tillväxten?"),
    ("us_gdp_real_growth", "G5", "A191RL",
     "Real BNP-tillväxt",
     "procent, årstakt (SAAR)", "tabell 1.5.2 rad 1",
     "Hur stor är BNP-tillväxten som bidragen ska jämföras med?"),
    ("us_imp_computers_nom", "G6", "B852RC",
     "Import av datorer, kringutrustning och delar",
     "MUSD, SAAR, löpande priser", "tabell 4.2.5/4.2.5B",
     "Hur mycket datorutrustning importerar USA?"),
    ("us_imp_computers_real", "G6", "B852RX",
     "Import av datorer, kringutrustning och delar, real",
     "MUSD, SAAR, kedjade dollar (basår enligt vintage)", "tabell 4.2.6/4.2.6B",
     "Hur snabbt växer USA:s import av datorutrustning i volym?"),
    ("us_imp_computers_contrib_imp", "G6", "B852RZ",
     "Bidrag till real importtillväxt från datorer, kringutrustning och delar",
     "procentenheter, årstakt (SAAR)", "tabell 4.2.2 rad 35",
     "Hur stor del av importtillväxten är datorutrustning?"),
]

SPECS += [
    Spec(
        key=key,
        branch=branch,
        label=f"{label} (USA)",
        unit=unit,
        freq="Q",
        source=ARCHIVE_SOURCE.format(table=table, code=" + ".join(codes) if isinstance(codes, tuple) else codes),
        fetch=partial(bea_nipa.archive_rows, codes),
        lag_days=LAG_DAYS,
        license=LICENSE,
        revised=True,
        publish=True,
        question=question,
        note=ARCHIVE_NOTE + (" Summan tas ur samma vintage; BEA avrundar till två decimaler."
                             if isinstance(codes, tuple) else "")
             + (" Basåret för kedjade dollar byts vid omläggningar: jämför nivåer bara inom en vintage."
                if codes == "B852RX" else ""),
    )
    for key, branch, codes, label, unit, table, question in ARCHIVE_SERIES
]
