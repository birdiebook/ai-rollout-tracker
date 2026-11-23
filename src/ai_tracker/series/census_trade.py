"""G6: US goods imports from Taiwan and South Korea (Census FT-900, country totals), monthly.

Mirror data for server and chip shipments from Taiwanese ODMs and Korean memory makers. Totals, not HS
8471/8473/8542: the HS detail needs api.census.gov, which requires a key (BLOCKED).
known_from = max(month end + 41 days, documented first release). The FT-900 came 32-41 days after month
end in 2017-2026 (first ALFRED vintage of IMP5830); later releases are in LATE. Before 2017-11 there is
no release evidence here, so shutdown delays then (e.g. 2013) are not covered: backfill only.
"""

from __future__ import annotations

from functools import partial

from ai_tracker import publication
from ai_tracker.catalog import Spec
from ai_tracker.sources import census_trade

LICENSE = ("US federal work, free under 17 U.S.C. § 105 (not quoted from census.gov). Census citation "
           "policy: \"Proper citation ensures that Census Bureau statistical products and research can be "
           "discovered, reused, replicated for verification, and credited for recognition\". "
           "Source: U.S. Census Bureau, U.S. International Trade in Goods and Services.")
LAG_DAYS = 41
LATE = {"2018-11": "2019-02-06", "2018-12": "2019-03-06", "2019-01": "2019-03-27", "2019-02": "2019-04-17",
        "2020-03": "2020-06-04", "2025-08": "2025-11-19", "2025-09": "2025-12-11", "2025-11": "2026-01-29",
        "2025-12": "2026-02-19"}
COUNTRIES = {"5830": ("tw", "Taiwan"), "5800": ("kr", "Sydkorea")}

SPECS = [
    Spec(
        key=f"us_imports_{code}_m",
        branch="G6",
        label=f"USA:s varuimport från {name}",
        unit="MUSD, ej säsongsrensad",
        freq="M",
        source=f"US Census Bureau, FT-900 country.xlsx (CTY_CODE {cty})",
        fetch=partial(census_trade.fetch, cty),
        lag_days=LAG_DAYS,
        license=LICENSE,
        revised=True,
        publish=True,
        question="Hur mycket hårdvara skeppas från Asiens leverantörskedja till USA?",
        note="Totalimport, inte HS 8471/8473/8542 (kräver Census API-nyckel). Backfill = dagens vintage.",
    )
    for cty, (code, name) in COUNTRIES.items()
]
for _s in SPECS:
    publication.LATE_RELEASES.setdefault(_s.key, {}).update(LATE)
