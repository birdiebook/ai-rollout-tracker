"""G5: Census Construction Spending (C30), private data-center construction, monthly (SAAR and NSA).

known_from = max(month end + LAG_DAYS, documented first release). Normal release: first business day of
the second month after, 29-35 days after month end in 2011-2026 (first ALFRED vintage of the same
release's total private series TLPRVCONS that contains the month). Releases later than that (shutdowns
2013, 2018-19, 2025 and the catch-up schedule into 2026) are listed in LATE with their documented date.
The xlsx holds only the latest vintage: history before our first fetch is backfill with revisions in it.
"""

from __future__ import annotations

from functools import partial

from ai_tracker import publication
from ai_tracker.catalog import Spec
from ai_tracker.sources import census_c30

LICENSE = ("US federal work, free under 17 U.S.C. § 105 (not quoted from census.gov). Census citation "
           "policy: \"Proper citation ensures that Census Bureau statistical products and research can be "
           "discovered, reused, replicated for verification, and credited for recognition\". Source line: "
           "\"Source: U.S. Census Bureau, Construction Spending\".")
LAG_DAYS = 35
# First release of month m (ALFRED vintage dates of TLPRVCONS, checked 2026-11-23) when later than end + 35 days.
LATE = {"2018-11": "2019-02-01", "2018-12": "2019-03-04", "2019-01": "2019-03-13", "2025-08": "2025-11-17",
        "2025-09": "2026-01-21", "2025-10": "2026-01-21", "2025-11": "2026-02-27", "2025-12": "2026-02-27",
        "2026-01": "2026-03-23", "2026-02": "2026-05-07", "2026-03": "2026-05-07"}


def _spec(kind: str) -> Spec:
    sa = kind == "sa"
    return Spec(
        key="us_constr_datacenter" + ("" if sa else "_nsa"),
        branch="G5",
        label="Privata byggutgifter, datacenter (USA)" + (", säsongsrensad årstakt" if sa else ", ej säsongsrensad"),
        unit="MUSD, SAAR" if sa else "MUSD (månad)",
        freq="M",
        source="US Census Bureau, Construction Spending (C30), " + census_c30.FILES[kind],
        fetch=partial(census_c30.fetch, kind),
        lag_days=LAG_DAYS,
        license=LICENSE,
        revised=True,  # p/r flags: the two latest months are revised monthly, annual revision in July
        publish=True,
        question="Hur mycket byggs det i datacenter just nu (byggnader, inte servrar)?",
        note="Strukturer, inte utrustning (servrar och rack ingår inte). Kategorin finns från 2014-01; "
             "allt före första egna hämtningen är backfill (dagens vintage). Se docs/kallor/census_eu.md.",
    )


SPECS = [_spec("sa"), _spec("nsa")]
for _s in SPECS:
    publication.LATE_RELEASES.setdefault(_s.key, {}).update(LATE)
