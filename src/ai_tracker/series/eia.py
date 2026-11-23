"""G7: EIA Electric Power Monthly, commercial-sector retail electricity sales (data-centre states, US).

Data centres are mostly billed as commercial customers, so commercial sales in the states with the
largest data-centre build-out are a direct (if noisy) proxy for their power draw. Vintages from the EPM
back-issue archive (sources/eia_epm.py); periods before 2012-11 are backfill (final values, leakage).
"""

from __future__ import annotations

from functools import partial

from ai_tracker.catalog import Spec
from ai_tracker.sources import eia_epm

LICENSE = ("Public domain (www.eia.gov/about/copyrights_reuse.php): \"U.S. government publications are in "
           "the public domain and are not subject to copyright protection. You may use and/or distribute any "
           "of our data, files, databases, reports, graphs, charts, and other information products...\"")

NAMES = {**eia_epm.STATES, "US": "USA totalt"}


def _key(area: str) -> str:
    return "us_elec_sales_com_m" if area == "US" else f"us_elec_sales_com_{area.lower()}_m"


SPECS = [
    Spec(
        key=_key(area),
        branch="G7",
        label=f"Elförsäljning till kommersiell sektor, {name} (EIA)",
        unit="GWh per månad",
        freq="M",
        source="EIA Electric Power Monthly, tabell 5.4.A (back issues) och EIA-861M sales_revenue.xlsx",
        fetch=partial(eia_epm.fetch, area),
        lag_days=58,  # median first release ~57 days after month end (EPM ~24th of month m+2)
        license=LICENSE,
        revised=True,
        publish=True,
        question="Växer elbehovet där datacentren byggs, och i vilken takt?",
        note="Avrundat till hela GWh som i EPM. Perioder före 2012-11 är backfill (slutliga värden).",
    )
    for area, name in NAMES.items()
]
