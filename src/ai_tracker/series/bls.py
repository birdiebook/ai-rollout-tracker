"""G4 and G7: BLS consumer price index for electricity and producer price indexes for data processing and hosting and
for commercial electric power, monthly, from download.bls.gov.

Each value is dated by BLS's own release and revision rules (sources/bls.py, docs/mattregister.md 2026-11-24 M1):
CPI NSA is final when released; CPI SA is revised each February for 5 years; PPIs are revised monthly for 4 months.
Not core series. See docs/kallor/makro_bea_bls.md.
"""

from __future__ import annotations

from functools import partial

from ai_tracker.catalog import Spec
from ai_tracker.sources import bls

LICENSE = ("Public domain (BLS, www.bls.gov/opub/copyright-information.htm): \"You are free to use our public domain "
           "material without specific permission, although we do ask that you cite the Bureau of Labor Statistics "
           "as the source.\" Source: U.S. Bureau of Labor Statistics.")
LAG_DAYS = 20  # CPI and PPI come 9-17 days after the month in normal times (news-release archive 2002-2026)

SERIES = [  # key, branch, BLS id, label, unit, question, note
    ("us_cpi_electricity_nsa_m", "G7", "CUUR0000SEHF01",
     "KPI-U el, USA-genomsnitt", "index 1982-84=100, ej säsongsrensat",
     "Hur snabbt stiger elpriset för hushållen?",
     "Slutlig vid publicering. known_from = releasedagen enligt BLS arkiv över nyhetsreleaser."),
    ("us_cpi_electricity_sa_m", "G7", "CUSR0000SEHF01",
     "KPI-U el, USA-genomsnitt, säsongsrensad", "index 1982-84=100, SA",
     "Hur snabbt stiger elpriset för hushållen, rensat för säsong?",
     "Säsongsfaktorerna revideras varje februari för fem år: värden dateras till den senaste revideringen."),
    ("us_ppi_data_processing_m", "G4", "PCU518210518210",
     "PPI databehandling, hosting och relaterade tjänster (NAICS 518210)", "index dec 2000=100, ej säsongsrensat",
     "Stiger eller faller priset som moln- och hostingbolagen tar ut?",
     "Revideras månadsvis i fyra månader: preliminära värden dateras till filens datum, slutliga till release m+4."),
    ("us_ppi_elec_commercial_m", "G7", "PCU22112222112242",
     "PPI eldistribution, kommersiella kunder", "index, ej säsongsrensat",
     "Hur snabbt stiger elpriset för kommersiella kunder, där de flesta datacenter finns?",
     "Revideras månadsvis i fyra månader: preliminära värden dateras till filens datum, slutliga till release m+4."),
]

# no_gaps exemptions (warehouse.KNOWN_GAPS): October 2025 is "-" with footnote X in the CPI files, "Data unavailable
# due to the 2025 lapse in appropriations", and the news-release archive lists it as not published. It stays a gap.
KNOWN_GAPS = {
    "us_cpi_electricity_nsa_m": "CPI October 2025 never collected (2025 lapse in appropriations, BLS footnote X)",
    "us_cpi_electricity_sa_m": "CPI October 2025 never collected (2025 lapse in appropriations, BLS footnote X)",
}

SPECS = [
    Spec(
        key=key,
        branch=branch,
        label=f"{label} (USA)",
        unit=unit,
        freq="M",
        source=f"BLS flat file {bls.SERIES[sid][1]} ({sid}), download.bls.gov",
        fetch=partial(bls.release_rows, sid),
        lag_days=LAG_DAYS,
        license=LICENSE,
        revised=True,
        publish=True,
        question=question,
        note=note,
    )
    for key, branch, sid, label, unit, question, note in SERIES
]
