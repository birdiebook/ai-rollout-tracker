"""G6: monthly US imports of computers, computer parts and integrated circuits by HS code and country (Census API).

Track M2 (register 2026-11-24, docs/kallor/census_hs.md). Catalog series, not core series. Needs CENSUS_API_KEY:
until it is set the fetch is skipped and the series are left out of the freshness check (ai_tracker.keyed).

General imports, total value (GEN_VAL_MO), US dollars -> MUSD, not seasonally adjusted, from 2013-01. HS detail is
released with the FT-900, so known_from follows series/census_trade.py: max(month end + 41 days, LATE). The API
has the latest vintage only (annual revision in June): the first fetch is backfill, later changes are revisions
dated by the fetch day. The US HS nomenclature changed in 2017-01 and 2022-01 (HS 2017, HS 2022; in 2022 the new
heading 8524 took flat panel display modules out of other headings, possibly 8473.30); the series are not spliced.
"""

from __future__ import annotations

from functools import partial

from ai_tracker import keyed, publication
from ai_tracker.catalog import Spec
from ai_tracker.series.census_trade import LAG_DAYS, LATE
from ai_tracker.sources import census_hs

# HS code -> (Swedish label, question)
CODES = {
    "8471": ("HS 8471 datorer och datorenheter (alla)",
             "Hur mycket datorer och datorenheter importerar USA, och från vilka länder?"),
    "847150": ("HS 8471.50 processorenheter (bland annat servrar)",
               "Hur mycket servrar och andra processorenheter importerar USA, och varifrån?"),
    "847180": ("HS 8471.80 andra datorenheter",
               "Hur mycket andra datorenheter (bland annat enheter som byggs in i servrar) importerar USA, och varifrån?"),
    "847330": ("HS 8473.30 delar och tillbehör till datorer",
               "Hur mycket datordelar (bland annat kort och moduler till servrar) importerar USA, och varifrån?"),
    "8542": ("HS 8542 integrerade kretsar",
             "Hur mycket integrerade kretsar importerar USA, och varifrån?"),
}
# key suffix -> (CTY_CODE in the API, Swedish name); "-" is the API's total for all countries
GEOS = {
    "tw": ("5830", "Taiwan"), "mx": ("2010", "Mexiko"), "vn": ("5520", "Vietnam"), "my": ("5570", "Malaysia"),
    "th": ("5490", "Thailand"), "cn": ("5700", "Kina"), "world": (census_hs.WORLD, "hela världen"),
}
COMMODITIES = tuple(CODES)
COUNTRIES = tuple(c for c, _ in GEOS.values() if c != census_hs.WORLD)
NOTICE = "This product uses the Census Bureau Data API but is not endorsed or certified by the Census Bureau."
LICENSE = ("US federal work, free under 17 U.S.C. § 105; the API's dataset metadata (imports/hs.json) gives "
           "\"license\": \"http://creativecommons.org/publicdomain/zero/1.0/\". Census Data API Terms of Service: "
           f"services that use the API \"should display the following notice prominently\": \"{NOTICE}\" "
           "Source: U.S. Census Bureau, USA Trade, monthly imports by HS (api.census.gov).")
NOTE = ("Census API (intltrade/imports/hs, GEN_VAL_MO = general imports), ej säsongsrensad. Kräver CENSUS_API_KEY: "
        "utan nyckeln hoppas hämtningen över och serien är undantagen från aktualitetskontrollen (keyed.py). "
        "known_from = FT-900:s kalender (månadsslut + 41 dagar, sena releaser i census_trade.LATE). Backfill = dagens "
        "vintage. En månad utan post i svaret räknas som 0. HS-brott 2017-01 och 2022-01 skarvas inte. Katalogserie, "
        "inte kärnserie (register 2026-11-24, M2).")


def key(code: str, geo: str) -> str:
    return f"us_imp_hs{code}_{geo}_m"


def _spec(code: str, geo: str) -> Spec:
    label, question = CODES[code]
    cty, name = GEOS[geo]
    return Spec(
        key=key(code, geo), branch="G6", label=f"USA:s import av {label} från {name}",
        unit="MUSD, ej säsongsrensad", freq="M",
        source=f"US Census Bureau API, intltrade/imports/hs (I_COMMODITY {code}, CTY_CODE {cty}, GEN_VAL_MO)",
        fetch=partial(census_hs.fetch, cty, code, COMMODITIES, COUNTRIES), lag_days=LAG_DAYS, license=LICENSE,
        revised=True, publish=True, question=question, note=NOTE)


SPECS = [_spec(c, g) for c in CODES for g in GEOS]
keyed.register([s.key for s in SPECS], census_hs.KEY_ENV)
for _s in SPECS:
    publication.LATE_RELEASES.setdefault(_s.key, {}).update(LATE)
