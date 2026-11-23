"""G3: Census BTOS, share of US firms using AI (biweekly, release-dated). One series per wording regime."""

from __future__ import annotations

from functools import partial

from ai_tracker.catalog import Spec
from ai_tracker.sources import census_btos

LICENSE = ("US federal work, free under 17 U.S.C. § 105 (not quoted from census.gov). Census citation "
           "policy: \"Proper citation ensures that Census Bureau statistical products and research can be "
           "discovered, reused, replicated for verification, and credited for recognition\". Source line: "
           "\"Source: U.S. Census Bureau, Business Trends and Outlook Survey (BTOS)\". Experimental product.")

_LABEL = {"use": "Andel företag (USA) som använt AI de senaste två veckorna",
          "expect": "Andel företag (USA) som tror att de använder AI inom sex månader"}
_QUESTION = {"use": "Hur bred är AI-användningen bland amerikanska företag just nu?",
             "expect": "Hur bred förväntas AI-användningen bland amerikanska företag bli inom ett halvår?"}
_WORDING = {"v1": "gamla frågan (\"in producing goods or services\"), cykel 202319–202520",
            "v2": "ny fråga (\"in any of its business functions\"), cykel 202524–202621",
            "v3": "\"Super Intelligence or SI (formerly ... AI)\" och nya exempel, från cykel 202622"}


def _spec(what: str, version: str, stat: str) -> Spec:
    se = stat == "se"
    return Spec(
        key=f"btos_ai_{what}_{version}" + ("_se" if se else ""),
        branch="G3",
        label=_LABEL[what] + (" (standardfel)" if se else "") + f", {version}",
        unit="procentenheter (standardfel)" if se else "% av företag",
        freq="2W",
        source="US Census Bureau, BTOS (National.xlsx, AI Core Questions.xlsx)",
        fetch=partial(census_btos.fetch, what, version, stat),
        lag_days=4,  # release-dated rows: known_from = Publication Date in the file
        license=LICENSE,
        revised=False,  # not verifiable: files are overwritten without history; refetches catch changes
        publish=not se,
        question=_QUESTION[what],
        note=f"Frågelydelse {_WORDING[version]}. Period = veckan då insamlingen slutar. Regimbrott: egen serie "
             "per lydelse, skarvas aldrig. Se docs/kallor/census_eu.md.",
    )


SPECS = [_spec(w, v, s) for w in ("use", "expect") for v in ("v1", "v2", "v3") for s in ("estimate", "se")]
