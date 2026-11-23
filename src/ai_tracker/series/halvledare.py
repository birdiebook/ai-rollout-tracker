"""Semiconductors and memory (lead L6, branch G6): AMD, Broadcom, Marvell, Micron, Nvidia and ASML.

Quarterly, release-dated (known_from = filing date of the 10-Q/10-K or 6-K; every filing a vintage):
- totals from companyfacts (ai_tracker.sources.sec): revenue, capex (cash purchases of property and
  equipment), inventories (instants, ai_tracker.sources.sec_instant);
- segment / end-market revenue from each filing's XBRL instance (ai_tracker.sources.sec_segment),
  split into one series per definition at declared breaks (as in series/sec_segments.py);
- Nvidia's capex gap in FY2023 (own tag nvda:PurchasesOfPropertyAndEquipmentAndIntangibleAssets) and its
  supply and capacity purchase obligations (dimensional instants) from the instances;
- ASML net sales and net bookings from its 6-K results press releases (ai_tracker.sources.asml_sec).

Fiscal calendars (calendar quarter = the one containing the fiscal quarter's midpoint, sec.calendar_quarter),
lag_days, freshness bounds and checks against reported figures: docs/kallor/halvledare.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.series.sec import LICENSE, NVDA_MAX_AGE_DAYS
from ai_tracker.series.sec_segments import REVENUE, SEG, PROD, Line, checked_regimes
from ai_tracker.series.tsmc import LICENSE as SIXK_LICENSE
from ai_tracker.sources import asml_sec, sec, sec_instant, sec_segment

SOURCE = "SEC EDGAR XBRL companyfacts"
SOURCE_SEG = "SEC EDGAR XBRL instances (segment dimensions)"
SOURCE_INST = "SEC EDGAR XBRL instances"
SOURCE_ASML = "SEC EDGAR, ASML Form 6-K (kvartalsrapport, pressmeddelande)"

AMD, AVGO, AVGO_LTD, AVAGO, MRVL, MRVL_GRP, MU, NVDA = 2488, 1730168, 1649338, 1441634, 1835632, 1058057, 723125, 1045810


@dataclass(frozen=True)
class Company:
    name: str
    ciks: tuple[int, ...]  # successor first; predecessors carry the older history (same fiscal calendar)
    revenue: tuple[str, ...]
    lag_days: int  # conservative days from calendar quarter end to the first filing (leakage check if < 0)
    max_age_days: int | None  # freshness bound override (None = derived from lag_days), reason in AGE_NOTE
    calendar: str  # fiscal calendar, Swedish, for the note


# max_age = largest observed days from calendar quarter end to the first own filing (2015-2026, comparatives
# in later filings excluded), rounded up, + 92 + 30.
COMPANIES = {
    "amd": Company("AMD", (AMD,), ("RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueGoodsNet"),
                   25, 60 + 92 + 30, "52/53 veckor, kvartal slutar sista lördagen i mar/jun/sep/dec"),
    "avgo": Company("Broadcom", (AVGO, AVGO_LTD, AVAGO), tuple(REVENUE), 25, 85 + 92 + 30,
                    "52/53 veckor till söndagen närmast 31 okt: nov–jan räknas som Q4, aug–okt som Q3"),
    "mrvl": Company("Marvell", (MRVL, MRVL_GRP), tuple(REVENUE), 25, 90 + 92 + 30,
                    "52/53 veckor till lördagen närmast 31 jan: som Nvidia, aug–okt räknas som Q3"),
    "mu": Company("Micron", (MU,), tuple(REVENUE), -31, 30 + 92 + 30,
                  "52/53 veckor till torsdagen närmast 31 aug: sep–nov räknas som Q4 och lämnas in före "
                  "kalenderkvartalets slut, därför lag_days = -31 (som Oracle)"),
    "nvda": Company("Nvidia", (NVDA,), tuple(REVENUE), 25, NVDA_MAX_AGE_DAYS,
                    "52/53 veckor till sista söndagen i jan: aug–okt räknas som Q3 (docs/kallor/sec.md)"),
}

CAPEX = {
    "amd": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "mu": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    # Nvidia: 'Purchases related to property and equipment and intangible assets'. FY2023 10-Qs and the
    # FY2022/FY2023 10-Ks used an own tag, read from the instances (nvda_capex_own_tag).
    "nvda": ["PaymentsToAcquireProductiveAssets", "PaymentsToAcquirePropertyPlantAndEquipment"],
}
NVDA_CAPEX_OWN = "PurchasesOfPropertyAndEquipmentAndIntangibleAssets"
INVENTORY = "InventoryNet"

# Nvidia's outstanding inventory purchase and long-term supply and capacity obligations: a plain tag to
# FY2026 Q2, then dimensional members of the commitments table (renamed twice, values carried over).
OTHER_AX = "OtherCommitmentsAxis"
NVDA_PO = [
    ("PurchaseObligation", frozenset()),
    ("PurchaseObligation", frozenset({(OTHER_AX, "ManufacturingProductionAndLongTermSupplyAndCapacityAgreementCommitmentsMember")})),
    ("OtherCommitment", frozenset({(OTHER_AX, "ManufacturingProductionAndLongTermSupplyAndCapacityAgreementCommitmentsMember")})),
    ("OtherCommitment", frozenset({(OTHER_AX, "SupplyAndCapacityCommitmentsMember")})),
]
NVDA_INSTANCES_SINCE = "2012-01-01"

SINCE = {AMD: "2018-01-01", AVGO: "2018-01-01", MRVL: "2021-01-01", MU: "2017-01-01"}

LINES = [
    Line(("rev_amd_datacenter",), AMD, ((SEG, "DataCenterMember"), (SEG, "DatacenterMember")),
         "Data Center (AMD)", lag_days=COMPANIES["amd"].lag_days),
    Line(("rev_avgo_semis",), AVGO, ((SEG, "SemiconductorSolutionsMember"),),
         "Semiconductor solutions (Broadcom)", lag_days=COMPANIES["avgo"].lag_days),
    Line(("rev_mrvl_datacenter",), MRVL, ((PROD, "DataCenterMember"),),
         "Data center, slutmarknad (Marvell)", lag_days=COMPANIES["mrvl"].lag_days),
    Line(("rev_mu_cnbu",), MU, ((SEG, "CNBUMember"),),
         "Compute and Networking Business Unit (Micron, till FY2025 Q3)", lag_days=COMPANIES["mu"].lag_days),
    Line(("rev_mu_cmbu",), MU, ((SEG, "CMBUMember"),),
         "Cloud Memory Business Unit (Micron, från FY2025 Q4)", lag_days=COMPANIES["mu"].lag_days),
]
# AMD's six 10-Qs filed 2023-05-03 to 2024-10-30 carry rotated segment members: DataCenterMember holds
# Gaming, GamingMember holds Client and ClientMember holds Data Center, for the current quarter and the
# comparatives alike (e.g. Q1 2024: ClientMember 2,337 = AMD's reported Data Center revenue, DataCenterMember
# 922 = Gaming). The 10-Ks (DatacenterMember) and the 10-Qs from 2025 are labelled correctly and restate the
# same quarters with the right values. Per filing, the member that carries Data Center is used instead.
AMD_ROTATED = ("2023-05-03", "2023-08-02", "2023-11-01", "2024-05-01", "2024-07-31", "2024-10-30")
MEMBER_OVERRIDES: dict[str, dict[str, tuple[tuple[str, str], ...]]] = {
    "rev_amd_datacenter": {d: ((SEG, "ClientMember"),) for d in AMD_ROTATED},
}
LINE_COMPANY = {AMD: "amd", AVGO: "avgo", MRVL: "mrvl", MU: "mu"}
DISCONTINUED = {
    "rev_mu_cnbu": "Micron ersatte sina fyra affärsenheter med CMBU, CDBU, MCBU och AEBU i 10-K för FY2025 "
                   "(2025-10-03); CNBU rapporteras inte efter FY2025 Q3 (mar–maj 2025).",
}


# ------------------------------------------------------------------ companyfacts: flows and instants


def _flow_sources(company: str, tags: list[str] | tuple[str, ...]) -> list[list[sec.Fact]]:
    ciks = COMPANIES[company].ciks
    return [[f for cik in ciks for f in sec.facts(sec.companyfacts(cik), tag)] for tag in tags]


@lru_cache(maxsize=None)
def revenue_series(company: str) -> pd.DataFrame:
    return sec.contiguous_tail(sec.vintages(_flow_sources(company, COMPANIES[company].revenue)))


@lru_cache(maxsize=None)
def quarters(company: str) -> dict[pd.Timestamp, pd.Period]:
    """Fiscal quarter end -> calendar quarter, from the company's revenue facts."""
    return sec_instant.fiscal_quarters(_flow_sources(company, COMPANIES[company].revenue))


@lru_cache(maxsize=None)
def capex_series(company: str) -> pd.DataFrame:
    sources = _flow_sources(company, CAPEX[company])
    if company == "nvda":
        sources.insert(1, nvda_capex_own_tag())
    return sec.contiguous_tail(sec.vintages(sources))


@lru_cache(maxsize=None)
def inventory_series(company: str) -> pd.DataFrame:
    ciks = COMPANIES[company].ciks
    facts = [f for cik in ciks for f in sec_instant.facts(sec.companyfacts(cik), INVENTORY)]
    return sec.contiguous_tail(sec_instant.vintages([facts], quarters(company)))


# ------------------------------------------------------------------ XBRL instances


@lru_cache(maxsize=None)
def instances(cik: int, since: str) -> tuple[tuple[sec_segment.Filing, bytes], ...]:
    out = []
    for f in sec_segment.filings(cik, since):
        raw = sec_segment.instance(f)
        if raw is not None:
            out.append((f, raw))
    return tuple(out)


def plain_duration_facts(filings_raw, concept: str) -> list[sec.Fact]:
    """Non-dimensional duration facts of one (possibly company-specific) concept, as sec.Facts.

    3-month facts in 10-Ks are skipped, as in sec.facts.
    """
    out = []
    for f, raw in filings_raw:
        seen = set()
        for d in sec_segment.parse_instance(raw, {concept}):
            if d.dims or d.unit != "USD" or (d.start, d.end) in seen:
                continue
            if f.form.startswith("10-K") and sec._is_quarter(d.start, d.end):
                continue
            seen.add((d.start, d.end))
            out.append(sec.Fact(d.start, d.end, d.value, pd.Timestamp(f.filed), f.form, f.accession))
    return out


def nvda_capex_own_tag() -> list[sec.Fact]:
    return plain_duration_facts(instances(NVDA, NVDA_INSTANCES_SINCE), NVDA_CAPEX_OWN)


@lru_cache(maxsize=None)
def nvda_purchase_obligations() -> pd.DataFrame:
    filings_raw = list(instances(NVDA, NVDA_INSTANCES_SINCE))
    sources = [sec_instant.instance_instants(filings_raw, concept, dims) for concept, dims in NVDA_PO]
    return sec.contiguous_tail(sec_instant.vintages(sources, quarters("nvda")))


def line_facts(line: Line) -> list[sec.Fact]:
    """sec.Facts of one line across filings (sec_segment.member_facts, with per-filing member overrides)."""
    overrides = MEMBER_OVERRIDES.get(line.keys[0], {})
    out = []
    for f, dfs in sec_segment.company_facts(line.cik, SINCE[line.cik], tuple(REVENUE)):
        for axis, m in overrides.get(f.filed, line.members):
            got = sec_segment.to_facts(list(dfs), f, list(REVENUE), axis, m)
            if got:
                out += got
                break
    return out


@lru_cache(maxsize=None)
def line_series(line: Line) -> tuple[pd.DataFrame, ...]:
    facts = line_facts(line)
    return tuple(sec.contiguous_tail(sec.vintages([reg])) for reg in checked_regimes(line, facts))


# ------------------------------------------------------------------ ASML


@lru_cache(maxsize=1)
def asml_releases() -> tuple[tuple[str, asml_sec.Release], ...]:
    return tuple((f.filed, r) for f, r in asml_sec.releases())


Q = lambda s: pd.Period(s, freq="Q-DEC")  # noqa: E731

# Net bookings definition regimes: (key, first quarter, last quarter, label test, note). Reviewed against
# the releases' labels and footnotes on 2026-11-23 (docs/kallor/halvledare.md). 2014Q4-2016Q4 is left out:
# EUV (NXE:3350B) was included from 2014Q4, a 12-month shipment window applied from 2015Q2, and from 2017Q1
# all accepted orders count (incl. metrology and inspection). ASML stopped reporting quarterly net bookings
# after 2025Q4 (the releases from 2026-04-15 have no bookings row), so every regime is closed.
ASML_BOOKINGS = [
    ("asml_net_bookings_2006", Q("2006Q1"), Q("2011Q2"), lambda d: d == "net bookings (sentence)",
     "Definition 2006–2011: alla system (meningar i pressmeddelandet, 'net bookings valued at')."),
    ("asml_net_bookings_ex_euv", Q("2011Q3"), Q("2014Q3"), lambda d: d.startswith("net bookings, excluding euv"),
     "Definition 2011Q3–2014Q3: exklusive EUV ('Net bookings, excluding EUV')."),
    ("asml_net_bookings", Q("2017Q1"), Q("2025Q4"), lambda d: d.startswith("net bookings") and "euv" not in d.split("|")[0],
     "Definition från 2017Q1: alla systemorder med accepterad skriftlig beställning, inklusive metrologi och "
     "inspektion. High-NA EUV ingick inte 2018–2021Q3, och från 2022Q3 ingår inflationsjusteringar (fotnoter). "
     "ASML slutade redovisa orderingång per kvartal efter 2025Q4."),
]
ASML_LAG_DAYS = 30  # results are published 14-29 days after the quarter (2006-2026)


def _asml_fetch(measure: str, lo: pd.Period | None = None, hi: pd.Period | None = None, test=None):
    def fetch() -> pd.DataFrame:
        keep = None if test is None else (lambda q, d: lo <= q <= hi and test(d))
        return sec.contiguous_tail(asml_sec.vintages(list(asml_releases()), measure, keep=keep))[
            ["period", "value", "known_from"]].copy()

    return fetch


def _asml_specs() -> list[Spec]:
    common = dict(branch="G6", unit="MEUR", freq="Q", source=SOURCE_ASML, lag_days=ASML_LAG_DAYS,
                  license=SIXK_LICENSE, revised=True, publish=True,
                  question="Hur mycket litografiutrustning beställs och levereras, före chipkapaciteten?")
    specs = [Spec(key="asml_net_sales", label="ASML:s nettoomsättning", fetch=_asml_fetch("net_sales"),
                  note="Release-daterad: known_from = 6-K:ns inlämningsdatum (samma dag som pressmeddelandet). "
                       "'Net sales', från 2024 'Total net sales' (samma post). US GAAP; ASC 606 från 2018 "
                       "(2017Q4 inte omräknat).", **common)]
    for key, lo, hi, test, note in ASML_BOOKINGS:
        specs.append(Spec(key=key, label=f"ASML:s orderingång (net bookings), {note.split(':')[0].lower()}",
                          fetch=_asml_fetch("net_bookings", lo, hi, test), closed=True,
                          note=note + " Avslutad: definitionen ändrades eller redovisningen upphörde.", **common))
    return specs


# ------------------------------------------------------------------ catalog


def _rows(df: pd.DataFrame) -> pd.DataFrame:
    return df[["period", "value", "known_from"]].copy()


def _age_note(company: str) -> str:
    c = COMPANIES[company]
    return (f" Räkenskapsår: {c.calendar}. Aktualitet: gräns {c.max_age_days} dagar = största observerade "
            "avstånd från kalenderkvartalets slut till första inlämningen + 92 + 30 (docs/kallor/halvledare.md).")


QUESTION = "Hur snabbt växer leverantörsledet för AI-chip och minne, och var byggs lager och åtaganden upp?"


def _spec(key: str, label: str, fetch, company: str, note: str, source: str = SOURCE, closed: bool = False) -> Spec:
    c = COMPANIES[company]
    return Spec(key=key, branch="G6", label=label, unit="MUSD", freq="Q", source=source, fetch=fetch,
                lag_days=c.lag_days, license=LICENSE, revised=True, publish=True, question=QUESTION,
                note=note + _age_note(company), max_age_days=None if closed else c.max_age_days, closed=closed)


def _company_specs() -> list[Spec]:
    specs = []
    for co in ("amd", "avgo", "mrvl", "mu"):
        specs.append(_spec(f"rev_{co}", f"Intäkter, {COMPANIES[co].name}", lambda co=co: _rows(revenue_series(co)), co,
                           "Taggar: " + ", ".join(COMPANIES[co].revenue) + ". CIK: "
                           + ", ".join(map(str, COMPANIES[co].ciks)) + "."))
    for co in ("amd", "mu", "nvda"):
        tags = list(CAPEX[co]) + ([f"nvda:{NVDA_CAPEX_OWN} (instanser)"] if co == "nvda" else [])
        specs.append(_spec(f"capex_{co}", f"Capex (köp av anläggningstillgångar), {COMPANIES[co].name}",
                           lambda co=co: _rows(capex_series(co)), co, "Taggar: " + ", ".join(tags) + "."))
        specs.append(_spec(f"inv_{co}", f"Varulager, {COMPANIES[co].name}", lambda co=co: _rows(inventory_series(co)),
                           co, f"Tagg: {INVENTORY} (balansdag = räkenskapskvartalets slut)."))
    specs.append(_spec("purchase_oblig_nvda", "Inköps-, leverans- och kapacitetsåtaganden, Nvidia",
                       lambda: _rows(nvda_purchase_obligations()), "nvda",
                       "Utestående åtaganden för lager, långsiktig leverans och kapacitet (balansdag). Taggar: "
                       "PurchaseObligation utan dimension (till FY2026 Q2), därefter OtherCommitmentsAxis-medlemmarna "
                       "ManufacturingProductionAndLongTermSupplyAndCapacityAgreementCommitmentsMember och "
                       "SupplyAndCapacityCommitmentsMember (samma värde för 2026-04-26 under båda namnen).",
                       source=SOURCE_INST))
    for line in LINES:
        co = LINE_COMPANY[line.cik]
        for i, key in enumerate(line.keys):
            closed = i < len(line.keys) - 1 or key in DISCONTINUED
            note = "Medlemmar: " + ", ".join(f"{a}={m}" for a, m in line.members) + "."
            if line.regime_notes:
                note += " " + line.regime_notes[i]
            if key in DISCONTINUED:
                note += " Avslutad: " + DISCONTINUED[key]
            elif closed:
                note += " Avslutad: ersatt av nästa definition efter ett definitionsbrott."
            specs.append(_spec(key, f"Segmentintäkter, {line.label}",
                               lambda line=line, i=i: _rows(line_series(line)[i]), co, note,
                               source=SOURCE_SEG, closed=closed))
    return specs


SPECS = _company_specs() + _asml_specs()
