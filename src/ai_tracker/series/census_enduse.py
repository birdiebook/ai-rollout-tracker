"""G6: annual US imports of computers, computer accessories and semiconductors by country (Census end-use, no key).

Track M2 (register 2026-11-24, docs/kallor/census_hs.md). Catalog series, not core series. Source: the Census file
"Annual Country by 5-digit End-Use Code" (sources/census_enduse.py), US dollars -> MUSD, not seasonally adjusted.
known_from = 31 Dec + 191 days (10 July, 9 July in leap years): the file is replaced at the FT-900 Annual Revision,
which came 2-9 June in 2017-2026 (final_YYYY.pdf, "FOR RELEASE"); the 2026 file's server Last-Modified is the
release minute (2026-06-09 12:31 GMT). That earlier vintages of the file came at the same release is unverified
(web.archive.org is blocked from the session), so the rule keeps a month's margin. Backfill = the vintage of
2026-06-09: values for 2016-2024 carry later revisions.

Classification seam 2018|2019 (review R13-4): Census reclassified end-use codes with January 2022 statistics and
restated 2019-2021 at the 2022-06-07 annual revision (notices/20220308_enduse_changes.pdf), so 2016-2018 follow the
older end-use mapping and 2019-2025 the newer one. World 2019, revision 2021 -> 2022: computers +7, accessories -28,
semiconductors -301 MUSD (-0.56 %). Not spliced.
"""

from __future__ import annotations

from functools import partial

from ai_tracker.catalog import Spec
from ai_tracker.series.census_trade import LICENSE
from ai_tracker.sources import census_enduse

LAG_DAYS = 191
# end-use code -> (key part, file description, Swedish label)
END_USES = {
    "21300": ("Computers", "datorer"),
    "21301": ("Computer accessories", "datortillbehör och datordelar"),
    "21320": ("Semiconductors", "halvledare"),
}
# key suffix -> (CTY_CODE in the file, Swedish name)
GEOS = {
    "tw": ("5830", "Taiwan"), "mx": ("2010", "Mexiko"), "vn": ("5520", "Vietnam"), "my": ("5570", "Malaysia"),
    "th": ("5490", "Thailand"), "cn": ("5700", "Kina"), "world": ("0000", "hela världen"),
}
QUESTION = {
    "21300": "Hur mycket datorer och servrar importerar USA, och från vilka länder?",
    "21301": "Hur mycket datordelar och tillbehör (bland annat serverkomponenter) importerar USA, och varifrån?",
    "21320": "Hur mycket halvledare importerar USA, och varifrån?",
}
NOTE = ("Årssumma, ej säsongsrensad, Census end-use (5-siffrig kod). Filen ersätts vid FT-900:s årsrevision i juni "
        "och har ingen versionshistorik: backfill = vintage 2026-06-09. known_from = 10 juli året efter "
        "(årsrevisionen kom 2–9 juni 2017–2026). Brott i end-use-klassificeringen mellan 2018 och 2019: Census "
        "omklassificerade koderna från januari 2022 och lade in ändringen för 2019–2021, så 2016–2018 följer den äldre "
        "klassificeringen (världen 2019: halvledare −301 MUSD, −0,56 %). Skarvas inte. Månadsdata per land finns bara "
        "i Census API (nyckel), se us_imp_hs*_m. Katalogserie, inte kärnserie (register 2026-11-24, M2).")


def key(end_use: str, geo: str) -> str:
    return f"us_imp_eu{end_use}_{geo}_a"


def _spec(end_use: str, geo: str) -> Spec:
    desc, label = END_USES[end_use]
    cty, name = GEOS[geo]
    return Spec(
        key=key(end_use, geo), branch="G6", label=f"USA:s import av {label} från {name} (end-use {end_use}), per år",
        unit="MUSD per år, ej säsongsrensad", freq="A",
        source=f"US Census Bureau, Annual Country by 5-digit End-Use Code, enduse_imports.xlsx "
               f"(CTY_CODE {cty}, END_USE {end_use})",
        fetch=partial(census_enduse.fetch, cty, end_use, desc), lag_days=LAG_DAYS, license=LICENSE, revised=True,
        publish=True, question=QUESTION[end_use], note=NOTE)


SPECS = [_spec(e, g) for e in END_USES for g in GEOS]
