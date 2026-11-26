"""LT1 "Ledtid i stacken": the followed question's supplier aggregates as catalog series (register 2026-11-26 "LT1").

    lt1_rpo_power      rpo_etn + rpo_pwr                          power and grid: firm-order backlog and RPO, MUSD
    lt1_rpo_net        rpo_csco + rpo_dell + rpo_smci             networking and servers: RPO, MUSD
    lt1_dlr_bookings4  ob_dlr_leases_signed_total_dlr_share_q_level_musd over four quarters (Digital Realty's new
                       leases, annualized rent at its share; S3 extraction), MUSD per year

Sums of the members' components (followed.aggregate), not means: a version exists only when every member has filed
for the period, dated by the latest component used. Members are chosen by definition and series start (register entry,
(a)). publish=False. Not in any branch index, no core series, no state. The measures and the reading come from
ai_tracker.followed.ledtid.
"""

from __future__ import annotations

import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.followed.aggregate import Formula, Term, derive, sum4
from ai_tracker.series import sec as _sec

POWER = ("etn", "pwr")
NET = ("csco", "dell", "smci")
DLR_BOOKINGS = "ob_dlr_leases_signed_total_dlr_share_q_level_musd"
NAMES = {"etn": "Eaton", "pwr": "Quanta Services", "csco": "Cisco", "dell": "Dell", "smci": "Super Micro"}
SOURCE = "Härledd (LT1) ur SEC EDGAR XBRL-serier och extraherade serier i katalogen"
LICENSE = _sec.LICENSE

FORMULAS = {
    "lt1_rpo_power": Formula("lt1_rpo_power", tuple(Term(f"rpo_{c}") for c in POWER)),
    "lt1_rpo_net": Formula("lt1_rpo_net", tuple(Term(f"rpo_{c}") for c in NET)),
    "lt1_dlr_bookings4": Formula("lt1_dlr_bookings4", sum4(DLR_BOOKINGS)),
}


def _fetch(f: Formula):
    def fetch(table: pd.DataFrame | None = None) -> pd.DataFrame:
        from ai_tracker import observations  # lazy: observations -> catalog -> series -> this module

        t = observations.load() if table is None else table
        return derive(f, t[t["series"].isin(f.components)])

    return fetch


_COMMON = ("LT1 (följd fråga, register 2026-11-26). Summa av medlemmarnas komponenter; en version finns först när alla "
           "har lämnat in, och known_from = den senaste komponenten. Räknas inte i grenarnas diffusionsindex. "
           "publish=False. ")

SPECS = [
    Spec(key="lt1_rpo_power", branch="G7", label="Orderstock och RPO, kraft och elnät (Eaton, Quanta Services)",
         unit="MUSD", freq="Q", source=SOURCE, fetch=_fetch(FORMULAS["lt1_rpo_power"]), lag_days=25, license=LICENSE,
         revised=True, publish=False, components=FORMULAS["lt1_rpo_power"].components,
         question="Vänder leverantörernas orderstock i kraft och elnät före eller efter köparnas capex-takt?",
         note=_COMMON + "Eatons orderstock av fasta order (taggad som RPO) plus Quantas RPO, balans vid kvartalets slut. "
              "Förvärv ger nivåskiften (Eaton: Fibrebond 2025-04, Boyd Thermal 2026-03). Aktualitet: gräns 182 dagar, "
              "som rpo_etn.", max_age_days=182),
    Spec(key="lt1_rpo_net", branch="G6", label="RPO, nät och servrar (Cisco, Dell, Super Micro)", unit="MUSD", freq="Q",
         source=SOURCE, fetch=_fetch(FORMULAS["lt1_rpo_net"]), lag_days=25, license=LICENSE, revised=True,
         publish=False, components=FORMULAS["lt1_rpo_net"].components,
         question="Vänder leverantörernas RPO i nät och servrar före eller efter köparnas capex-takt?",
         note=_COMMON + "Ciscos och Dells RPO har stora tjänstedelar, och deras balanser har räkenskapskvartalets "
              "kalenderkvartal (upp till en månad efter kalenderkvartalet, S1). Splunk ingår i Cisco från 2024-03. "
              "Aktualitet: gräns 212 dagar, som Dells serier (S1).", max_age_days=212),
    Spec(key="lt1_dlr_bookings4", branch="G4",
         label="Tecknade nya hyresavtal över fyra kvartal (hyra per år), Digital Realty, Digital Realtys andel",
         unit="MUSD per år", freq="Q", source=SOURCE, fetch=_fetch(FORMULAS["lt1_dlr_bookings4"]), lag_days=25,
         license=LICENSE, revised=True, publish=False, components=FORMULAS["lt1_dlr_bookings4"].components,
         question="Vänder datacenterbolagets nya avtal före eller efter köparnas capex-takt?",
         note=_COMMON + "Ur S3:s extraktion (publish=False i väntan på granskningen); andelen är obelagd 2021Q4–2024Q1 "
              "(S3, tolkning 9). Aktualitet: gräns 200 dagar, som komponenten.", max_age_days=200),
]
KNOWN_GAPS: dict[str, str] = {}
