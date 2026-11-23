"""G7: EIA-930 hourly demand, monthly average and peak, for balancing areas with heavy data-centre build-out.

PJM (with the Dominion zone as a PJM sub-region), ERCOT, Southern Company (Georgia Power and others), and the two
Phoenix utilities APS and SRP. Lag-dated (sources/eia930.py): EIA rewrites its files daily, so the history is
backfill with today's values and revisions leak into it; from the first fetch on, new months and revisions are
dated by the fetch.
"""

from __future__ import annotations

from functools import partial

from ai_tracker.catalog import Spec
from ai_tracker.sources import eia930

LICENSE = ("Public domain (www.eia.gov/about/copyrights_reuse.php): \"U.S. government publications are in "
           "the public domain and are not subject to copyright protection. You may use and/or distribute any "
           "of our data, files, databases, reports, graphs, charts, and other information products...\"")

NAMES = {"pjm": "PJM", "pjm_dom": "PJM Dominion-zonen (DOM)", "erco": "ERCOT", "soco": "Southern Company",
         "azps": "Arizona Public Service", "srp": "Salt River Project"}
STATS = {"avg_mw": ("medellast", "Hur mycket el drar området i genomsnitt, och växer det där datacentren byggs?"),
         "peak_mw": ("högsta timlast", "Hur nära kapacitetsgränsen kommer området under månadens topptimme?")}

SPECS = [
    Spec(
        key=f"eia930_{stat.split('_')[0]}_{area}_m",
        branch="G7",
        label=f"Elförbrukning, {label}, {name} (EIA-930)",
        unit="MW",
        freq="M",
        source=f"EIA-930 Hourly Electric Grid Monitor, sexmånadersfiler "
               f"({'SUBREGION' if eia930.AREAS[area][0] == 'SUBREGION' else 'BALANCE'})",
        fetch=partial(eia930.fetch, area, stat),
        lag_days=7,  # hourly data appear the next day; a month is complete a few days after its end
        license=LICENSE,
        revised=True,
        publish=True,
        question=question,
        note=("Lokal kalendermånad. " + ("Demand (MW), ej rensad (delregion). " if area == "pjm_dom" else
              "Demand (MW) (Adjusted), EIA:s rensade serie. ") +
              "Historiken är backfill med dagens värden (revideringar läcker); revideringar efter första "
              "hämtningen får hämtdatum."),
    )
    for area, name in NAMES.items() for stat, (label, question) in STATS.items()
]
