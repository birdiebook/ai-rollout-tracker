"""Nvidia's revenue outlook for the quarter in progress (step 2, track B4), for N3's baseline B2.

Parsed deterministically from the 8-K earnings releases (ai_tracker.sources.nvda_guidance). period = the calendar
quarter of the guided fiscal quarter (same mapping as rev_nvda / rev_nvda_datacenter); known_from = filing date of
the first filing stating the value. Dollar outlook from 2012Q1 (range until 2012Q4, "$x, plus or minus 2%" from
2013Q1, 3% for the 14-week 2026Q4); before that, 2009Q3-2011Q4, the outlook was a change on the previous quarter in
percent (closed series). See docs/kallor/ai_nyckeltal.md.
"""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.sources import nvda_guidance

SOURCE = "SEC EDGAR, Nvidia Form 8-K Item 2.02 (pressmeddelande EX-99.1 och CFO-kommentar EX-99.2)"
LICENSE = "SEC EDGAR: public information (sec.gov/privacy); bara siffror med källhänvisning"
LAG = -120  # guidance comes 3-5 weeks into the fiscal quarter: 45-70 days before the calendar quarter ends


@lru_cache(maxsize=1)
def _records() -> pd.DataFrame:
    return nvda_guidance.records()


def _fetch(field: str):
    def fetch() -> pd.DataFrame:
        return nvda_guidance.vintages(_records(), field)
    return fetch


_USD = [
    ("nvda_guid_rev_mid", "rev_mid", "Nvidias guidance, kvartalsintäkt, mittpunkt"),
    ("nvda_guid_rev_lo", "rev_lo", "Nvidias guidance, kvartalsintäkt, lägsta (mittpunkt − bandet)"),
    ("nvda_guid_rev_hi", "rev_hi", "Nvidias guidance, kvartalsintäkt, högsta (mittpunkt + bandet)"),
]
_QOQ = [
    ("nvda_guid_rev_qoq_lo", "qoq_lo", "Nvidias guidance, intäkt mot föregående kvartal, lägsta (2009–2011)"),
    ("nvda_guid_rev_qoq_hi", "qoq_hi", "Nvidias guidance, intäkt mot föregående kvartal, högsta (2009–2011)"),
]

SPECS = [
    Spec(key=key, branch="G6", label=label, unit="MUSD", freq="Q", source=SOURCE, fetch=_fetch(field), lag_days=LAG,
         license=LICENSE, revised=True, publish=True,
         question="Vad väntade Nvidia sig av kvartalet när det började (baslinje B2 för N3)?",
         note="period = kalenderkvartalet för det guidade räkenskapskvartalet; known_from = 8-K:ns inlämningsdatum. "
              "Från 2012Q1. Deterministisk tolkning, se docs/kallor/ai_nyckeltal.md. Aktualitet: nästa guidance "
              "kommer 7-9 veckor efter kalenderkvartalets slut (Nvidias räkenskapsår slutar i januari), gräns 75 dagar.",
         max_age_days=75)
    for key, field, label in _USD
] + [
    Spec(key=key, branch="G6", label=label, unit="%", freq="Q", source=SOURCE, fetch=_fetch(field), lag_days=LAG,
         license=LICENSE, revised=True, publish=True,
         question="Vad väntade Nvidia sig av kvartalet (förändring mot föregående kvartal, före 2012)?",
         note="Avslutad: från 2012Q1 guidar Nvidia i dollar (nvda_guid_rev_mid). Se docs/kallor/ai_nyckeltal.md.",
         closed=True)
    for key, field, label in _QOQ
]
