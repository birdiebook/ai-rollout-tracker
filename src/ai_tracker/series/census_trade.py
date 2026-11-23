"""G6: US goods imports from Taiwan and South Korea (Census FT-900, country totals), monthly.

Mirror data for server and chip shipments from Taiwanese ODMs and Korean memory makers. Totals, not HS
8471/8473/8542: the HS detail needs api.census.gov, which requires a key (BLOCKED).
known_from = max(month end + 41 days, documented first release). The FT-900 came 32-41 days after month
end in 2017-2026 (first ALFRED vintage of IMP5830, with ALFRED's 0.0 placeholders not counted as releases);
later releases are in LATE. Before 2017-11 the evidence is the FT-900 press releases themselves
(census.gov/foreign-trade/Press-Release/ft900/ft900_YYMM.pdf, "FOR RELEASE", read for every month 2006-2017 in
the R1 review, docs/granskning/r1_lackage.md): 2006-2012 the release came 42-45 days after month end, so months
before 2013 get month end + 45 days (before 2006 unverified, same rule); the 2013 shutdown months are in LATE.
"""

from __future__ import annotations

from functools import partial

import pandas as pd

from ai_tracker import publication
from ai_tracker.catalog import Spec
from ai_tracker.sources import census_trade

LICENSE = ("US federal work, free under 17 U.S.C. § 105 (not quoted from census.gov). Census citation "
           "policy: \"Proper citation ensures that Census Bureau statistical products and research can be "
           "discovered, reused, replicated for verification, and credited for recognition\". "
           "Source: U.S. Census Bureau, U.S. International Trade in Goods and Services.")
LAG_DAYS = 41
LAG_DAYS_BEFORE_2013 = 45  # FT-900 2006-2012: 42-45 days after month end (R1, section 3.3)
LATE = {"2013-08": "2013-10-24", "2013-09": "2013-11-14",  # 2013 shutdown, ft900_1308.pdf / ft900_1309.pdf
        "2018-11": "2019-02-06", "2018-12": "2019-03-06", "2019-01": "2019-03-27", "2019-02": "2019-04-17",
        "2020-03": "2020-06-04", "2025-08": "2025-11-19", "2025-09": "2025-12-11",
        "2025-10": "2026-01-08",  # ft900_2510.pdf; ALFRED's 2025-12-11 vintage had a 0.0 placeholder (R1, 3.2)
        "2025-11": "2026-01-29", "2025-12": "2026-02-19"}
_PRE_2013 = pd.period_range("1985-01", "2012-12", freq="M")
LATE.update({str(p): str((p.end_time.normalize() + pd.Timedelta(days=LAG_DAYS_BEFORE_2013)).date())
             for p in _PRE_2013})
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
