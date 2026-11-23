"""Company guidance, release-dated (phase 4, track E1): TSMC quarterly outlook and hyperscaler capex guidance.

TSMC: parsed deterministically from its 6-K earnings filings (ai_tracker.sources.tsmc_guidance). One series per
field; period = the quarter guided; known_from = filing date of the first filing stating the value; a mid-quarter
update is a new vintage. Revenue ranges are in the currency TSMC stated them in: NT$ until 2017Q2, US$ from
2017Q3 (no conversion here).

Hyperscaler capex: extracted by reading the documents (agent extraction), stored as numbers and references
only in curated/guidance_capex.csv and loaded by ai_tracker.sources.guidance_capex. Guidance is for a fiscal or
calendar year or for the next quarter and its definition differs per company (see docs/kallor/guidance.md), so
these series are kept per company, definition and horizon and never summed.

Guidance is known before its period ends, so lag_days is negative (the warehouse check
known_from_after_period_end allows known_from >= period end + lag_days).
"""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.series.tsmc import LICENSE as TSMC_LICENSE
from ai_tracker.sources import guidance_capex, tsmc_guidance

TSMC_SOURCE = "SEC EDGAR, TSMC Form 6-K (kvartalsrapport: pressmeddelande och presentation)"
TSMC_LAG = -120  # earliest: 2015-09-23 for 2015Q4 (99 days before quarter end)


@lru_cache(maxsize=1)
def _tsmc_records() -> pd.DataFrame:
    return tsmc_guidance.records()


def _tsmc(field: str, currency: str | None = None):
    def fetch() -> pd.DataFrame:
        return tsmc_guidance.vintages(_tsmc_records(), field, currency)
    return fetch


_TSMC = [
    # key, field, currency, label, unit
    ("tsmc_guid_rev_twd_lo", "rev_lo", "TWD", "TSMC:s guidance, kvartalsintäkt, lägsta (NT$, t.o.m. 2017Q2)", "mn TWD"),
    ("tsmc_guid_rev_twd_hi", "rev_hi", "TWD", "TSMC:s guidance, kvartalsintäkt, högsta (NT$, t.o.m. 2017Q2)", "mn TWD"),
    ("tsmc_guid_rev_usd_lo", "rev_lo", "USD", "TSMC:s guidance, kvartalsintäkt, lägsta (US$, från 2017Q3)", "MUSD"),
    ("tsmc_guid_rev_usd_hi", "rev_hi", "USD", "TSMC:s guidance, kvartalsintäkt, högsta (US$, från 2017Q3)", "MUSD"),
    ("tsmc_guid_fx", "fx", None, "TSMC:s antagna växelkurs i guidance", "TWD per USD"),
    ("tsmc_guid_gm_lo", "gm_lo", None, "TSMC:s guidance, bruttomarginal, lägsta", "%"),
    ("tsmc_guid_gm_hi", "gm_hi", None, "TSMC:s guidance, bruttomarginal, högsta", "%"),
    ("tsmc_guid_om_lo", "om_lo", None, "TSMC:s guidance, rörelsemarginal, lägsta", "%"),
    ("tsmc_guid_om_hi", "om_hi", None, "TSMC:s guidance, rörelsemarginal, högsta", "%"),
]

TSMC_SPECS = [
    Spec(key=key, branch="G6", label=label, unit=unit, freq="Q", source=TSMC_SOURCE, fetch=_tsmc(field, cur),
         lag_days=TSMC_LAG, license=TSMC_LICENSE, revised=True, publish=True,
         question="Vad väntade TSMC sig av kvartalet när det började (baslinje B2 för N2)?",
         note="period = kvartalet som guidas; known_from = 6-K:ns inlämningsdatum (första dokument med värdet). "
              "Uppdateringar mitt i kvartalet är nya vintages. Koncernbas från 2006Q2. Se docs/kallor/guidance.md.")
    for key, field, cur, label, unit in _TSMC
]

CAPEX_SPECS = guidance_capex.specs()

SPECS = TSMC_SPECS + CAPEX_SPECS
