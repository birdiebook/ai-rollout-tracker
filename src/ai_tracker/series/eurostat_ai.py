"""G3: Eurostat `isoc_eb_ai`, share of enterprises (10+ employed) using at least one AI technology, annual.

EU27, Sweden, Germany, France (the US is not in the survey). From 2023: 2021 used another list of AI
technologies and 2022 was not asked, so 2021 is left out (a one-point regime with a gap).
"""

from __future__ import annotations

from functools import partial

from ai_tracker.catalog import Spec
from ai_tracker.sources import eurostat_ai

LICENSE = ("CC BY 4.0. Eurostat copyright notice: \"The copyright for the editorial content of this website, "
           "which is owned by the EU, is licensed under the Creative Commons Attribution 4.0 International "
           "licence. This means that you can re-use the content provided you acknowledge the source and "
           "indicate any changes you have made.\"")
GEOS = {"EU27_2020": ("eu27", "EU27"), "SE": ("se", "Sverige"), "DE": ("de", "Tyskland"), "FR": ("fr", "Frankrike")}
INDIC = "E_AI_TANY"
FIRST_YEAR = 2023


def _fetch(geo: str):
    return eurostat_ai.series(eurostat_ai.fetch_long(tuple(GEOS), INDIC), geo, INDIC, FIRST_YEAR)


SPECS = [
    Spec(
        key=f"eu_ai_ent_{code}",
        branch="G3",
        label=f"Andel företag (10+ anställda) som använder minst en AI-teknik, {name}",
        unit="% av företag",
        freq="A",
        source="Eurostat isoc_eb_ai (E_AI_TANY, GE10, C10-S951_X_K)",
        fetch=partial(_fetch, geo),
        lag_days=31,  # target: release in December of the survey year (ESMS 8.1); +31 days margin
        license=LICENSE,
        revised=True,  # late countries and updates (last data update 2026-06-15); API has only the latest version
        publish=True,
        question="Hur stor andel av företagen i Europa använder AI, och hur ligger Sverige till?",
        note="Från 2025 ingår en åttonde teknik (generering av bild, video, ljud, E_AI_TPVSG) i 'minst en'. "
             "Eurostat flaggar inget brott, men definitionen breddas. Se docs/kallor/census_eu.md.",
    )
    for geo, (code, name) in GEOS.items()
]
