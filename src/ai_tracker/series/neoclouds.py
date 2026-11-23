"""Neoclouds and Oracle (lead L5): revenue (G4), capex and operating cash flow (G5), quarterly, release-dated.

- Oracle, CoreWeave and IREN from companyfacts (ai_tracker.sources.sec): known_from = 10-Q/10-K filing date,
  every filing a vintage, YTD differencing and the midpoint calendar mapping of sec.calendar_quarter.
- Nebius from its 6-K results releases (ai_tracker.sources.nebius_sec): it files a 20-F, whose XBRL is annual
  only; known_from = the 6-K filing date.

Oracle's fiscal quarters end in Aug/Nov/Feb/May and map to the calendar quarter containing their midpoint
(Sep-Nov = Q4), the same mapping as rev_orcl_cloud, rpo_orcl and the financing series. They are filed before
that calendar quarter ends, hence lag_days = -31 (as for rev_orcl_cloud). RPO, debt, leases and Oracle's cloud
segment revenue are in series/sec_rpo.py, series/sec_finansiering.py and series/sec_segments.py.
Tags, checks against reported figures and the candidates left out: docs/kallor/neoclouds.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.series.sec import LICENSE, OCF, REVENUE
from ai_tracker.sources import nebius_sec, sec

SOURCE = "SEC EDGAR XBRL companyfacts"
SOURCE_NBIS = "SEC EDGAR, Nebius Form 6-K (kvartalsrapport, pressmeddelande)"
CAPEX = ("PaymentsToAcquirePropertyPlantAndEquipment",)
NBIS_LICENSE = ("SEC: \"Information presented on sec.gov is considered public information and may be copied or further "
                "distributed by users of the web site without the SEC's permission. Please consider appropriate citation "
                "to the SEC as the source.\" (sec.gov/privacy, checked 2026-11-23). Statutory filing (Form 6-K) by Nebius "
                "Group; only extracted figures with source citation are published, never text.")


@dataclass(frozen=True)
class Company:
    name: str
    cik: int
    tags: dict[str, tuple[str, ...]]  # measure -> tag priority list (companyfacts); empty for Nebius
    lag_days: int
    max_age_days: int  # largest observed days from calendar quarter end to the first own filing + 92 + 30
    calendar: str  # Swedish, for the note


# max_age: observed 2015-2026 (Oracle), 2025-2026 (CoreWeave, IREN, Nebius); comparatives in later filings excluded.
COMPANIES = {
    "orcl": Company("Oracle", 1341439, {"rev": tuple(REVENUE), "capex": CAPEX, "ocf": tuple(OCF)}, -31, -3 + 92 + 30,
                    "räkenskapsår till 31 maj, kvartal slutar aug/nov/feb/maj: sep–nov räknas som Q4 och lämnas in "
                    "före kalenderkvartalets slut (8–21 dagar före), därför lag_days = -31 (som rev_orcl_cloud)"),
    "crwv": Company("CoreWeave", 1769628, {"rev": tuple(REVENUE), "capex": CAPEX, "ocf": tuple(OCF)}, 45, 61 + 92 + 30,
                    "kalenderår; 10-Q 38–45 dagar och 10-K 61 dagar efter kvartalet"),
    "iren": Company("IREN", 1878848, {"capex": CAPEX, "ocf": tuple(OCF)}, 40, 58 + 92 + 30,
                    "räkenskapsår till 30 juni, kvartal = kalenderkvartal; 10-Q 36–38 dagar och 10-K 58 dagar efter "
                    "kvartalet; 10-Q/10-K först från FY2026 (tidigare 20-F med bara årlig XBRL)"),
    "nbis": Company("Nebius", nebius_sec.CIK, {}, 45, 51 + 92 + 30,
                    "kalenderår; 6-K med pressmeddelandet 31–51 dagar efter kvartalet (2024–2026)"),
}

LABELS = {
    "rev": ("Intäkter", "G4", "Hur snabbt växer intäkterna hos neomolnen och Oracle?"),
    "capex": ("Capex (köp av anläggningstillgångar)", "G5",
              "Hur mycket investerar neomolnen och Oracle i AI-kapacitet, utanför de fyra största?"),
    "ocf": ("Operativt kassaflöde", "G5", "Hur stor del av investeringarna bär det egna kassaflödet?"),
}
DESCRIPTION = {
    ("rev", "nbis"): "Rad 'Revenues' i tabellen Consolidated results (koncernen: Nebius AI-moln, Avride, TripleTen; "
                     "Toloka avvecklad från Q2 2025).",
    ("capex", "nbis"): "Rad 'Purchases of property (, plant) and equipment (and intangible assets)' i Selected "
                       "consolidated cash flow data, som positivt belopp.",
    ("ocf", "nbis"): "Rad '... operating activities – continuing operations' i Selected consolidated cash flow data.",
    ("capex", "crwv"): "Kontant capex ur kassaflödet. CoreWeaves egen capex-siffra i pressmeddelandet är periodiserad "
                       "(inkl. obetalda leveranser) och därför högre; leverantörsfinansierade GPU:er syns inte här.",
}


def rounding_revisions_dropped(df: pd.DataFrame) -> pd.DataFrame:
    """Drop later versions that only round the previous value to whole millions (thousands -> millions).

    CoreWeave reported in thousands to the 2025 10-K and in millions from 2026; a comparative such as
    1,212.788 -> 1,212 is rounding, not a revision.
    """
    keep, last = [], {}
    for i, r in df.sort_values(["known_from", "period"]).iterrows():
        prev = last.get(r.period)
        if prev is not None and float(r.value).is_integer() and abs(r.value - prev) < 1.0:
            continue
        last[r.period] = r.value
        keep.append(i)
    return df.loc[keep].sort_values(["known_from", "period"], ignore_index=True)


@lru_cache(maxsize=1)
def nebius_releases() -> tuple:
    return tuple(nebius_sec.releases())


@lru_cache(maxsize=None)
def company_series(measure: str, company: str) -> pd.DataFrame:
    """Release-dated quarterly rows (MUSD) for one measure and company, without gaps."""
    if company == "nbis":
        df = nebius_sec.vintages(list(nebius_releases()), measure)
    else:
        c = COMPANIES[company]
        cf = sec.companyfacts(c.cik)
        df = sec.vintages([sec.facts(cf, t) for t in c.tags[measure]])
    return sec.contiguous_tail(rounding_revisions_dropped(df[["period", "value", "known_from"]]))


def _fetch(measure: str, company: str):
    def fetch() -> pd.DataFrame:
        return company_series(measure, company)[["period", "value", "known_from"]].copy()

    return fetch


def _spec(measure: str, company: str) -> Spec:
    c = COMPANIES[company]
    label, branch, question = LABELS[measure]
    if company == "nbis":
        source, lic = SOURCE_NBIS, NBIS_LICENSE
        note = ("Release-daterad: known_from = 6-K:ns inlämningsdatum (pressmeddelandet samma dag eller dagen före). "
                + DESCRIPTION[(measure, company)] + " Från pressmeddelandet 2025-08-07 (Toloka avvecklad, "
                "jämförelsetal omräknade); tidigare pressmeddelanden har en annan bas och läses inte.")
    else:
        source, lic = SOURCE, LICENSE
        note = f"Taggar: {', '.join(c.tags[measure])}. CIK {c.cik}."
        if (measure, company) in DESCRIPTION:
            note += " " + DESCRIPTION[(measure, company)]
    note += (f" Räkenskapsår: {c.calendar}. Aktualitet: gräns {c.max_age_days} dagar = största observerade avstånd från "
             "kalenderkvartalets slut till första inlämningen + 92 + 30 (docs/kallor/neoclouds.md).")
    return Spec(key=f"{measure}_{company}", branch=branch, label=f"{label}, {c.name}", unit="MUSD", freq="Q",
                source=source, fetch=_fetch(measure, company), lag_days=c.lag_days, license=lic, revised=True,
                publish=True, question=question, note=note, max_age_days=c.max_age_days)


SPECS = ([_spec(m, co) for co in ("orcl", "crwv", "nbis") for m in ("rev", "capex", "ocf")]
         + [_spec(m, "iren") for m in ("capex", "ocf")])
