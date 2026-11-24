"""G7: EIA-930 hourly demand, monthly average and peak, for balancing areas with heavy data-centre build-out.

PJM (with the Dominion zone as a PJM sub-region), ERCOT, Southern Company (Georgia Power and others), and the two
Phoenix utilities APS and SRP. Lag-dated (sources/eia930.py): EIA rewrites its files daily, so the history is
backfill with today's values and revisions leak into it; from the first fetch on, new months and revisions are
dated by the fetch.

Backfill dating (R3, fixed in X2): known_from = max(month end + lag, first publication of the data element).
- First publication (eia.gov, read 2026-11-23): balancing-authority demand on 2016-07-25 (press release press437 and
  Today in Energy 27212, "Hourly information on U.S. electricity supply, demand, and flows is now available"); demand
  by sub-region on 2019-08-21 (Today in Energy 40993, the Hourly Electric Grid Monitor beta "incorporates two new
  data elements: ... hourly subregional demand"). Months before that are dated to that day.
- Lag: 7 days for the BA series (EIA: demand about one hour after the hour; the newest month is complete two days
  after its end). 31 days for the Dominion sub-region: the about page says "Demand by subregion, where available,
  is available on a lag of 1-30 days" and the form allows a month.
- Not determinable: when the column "Demand (MW) (Adjusted)" was introduced (docs/kallor/eia930.md flags it).
"""

from __future__ import annotations

from functools import partial

import pandas as pd

from ai_tracker import publication
from ai_tracker.catalog import Spec
from ai_tracker.sources import eia930

LICENSE = ("Public domain (www.eia.gov/about/copyrights_reuse.php): \"U.S. government publications are in "
           "the public domain and are not subject to copyright protection. You may use and/or distribute any "
           "of our data, files, databases, reports, graphs, charts, and other information products...\"")

NAMES = {"pjm": "PJM", "pjm_dom": "PJM Dominion-zonen (DOM)", "erco": "ERCOT", "soco": "Southern Company",
         "azps": "Arizona Public Service", "srp": "Salt River Project"}
STATS = {"avg_mw": ("medellast", "Hur mycket el drar området i genomsnitt, och växer det där datacentren byggs?"),
         "peak_mw": ("högsta timlast", "Hur nära kapacitetsgränsen kommer området under månadens topptimme?")}

# first public release of each data element (file kind), see the module docstring
FIRST_PUBLISHED = {"BALANCE": "2016-07-25", "SUBREGION": "2019-08-21"}
LAG_DAYS = {"BALANCE": 7, "SUBREGION": 31}


def kind(area: str) -> str:
    return eia930.AREAS[area][0]


def first_published(area: str) -> dict[str, str]:
    """Months up to the first publication -> its date (publication.known_from takes the later of this and lag)."""
    day = pd.Timestamp(FIRST_PUBLISHED[kind(area)])
    y, h = eia930.FIRST[kind(area)]
    months = pd.period_range(pd.Timestamp(y, 1 if h == 1 else 7, 1), day, freq="M")
    return {str(m): FIRST_PUBLISHED[kind(area)] for m in months}


SPECS = [
    Spec(
        key=f"eia930_{stat.split('_')[0]}_{area}_m",
        branch="G7",
        label=f"Elförbrukning, {label}, {name} (EIA-930)",
        unit="MW",
        freq="M",
        source=f"EIA-930 Hourly Electric Grid Monitor, sexmånadersfiler ({kind(area)})",
        fetch=partial(eia930.fetch, area, stat),
        lag_days=LAG_DAYS[kind(area)],
        license=LICENSE,
        revised=True,
        publish=True,
        question=question,
        note=("Lokal kalendermånad. " + ("Demand (MW), ej rensad (delregion). " if area == "pjm_dom" else
              "Demand (MW) (Adjusted), EIA:s rensade serie. ") +
              "Historiken är backfill med dagens värden (revideringar läcker), daterad tidigast vid första "
              f"publicering ({FIRST_PUBLISHED[kind(area)]}); revideringar efter första hämtningen får hämtdatum." +
              (" Fördröjning 31 dagar (EIA: delregioner 1–30 dagar)." if kind(area) == "SUBREGION" else
               " Ej belagt när kolumnen Demand (MW) (Adjusted) infördes.")),
    )
    for area, name in NAMES.items() for stat, (label, question) in STATS.items()
]
for _s in SPECS:
    publication.LATE_RELEASES.setdefault(_s.key, {}).update(first_published(_s.key.split("_", 2)[2][:-2]))
