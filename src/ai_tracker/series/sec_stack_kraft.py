"""Power, cooling, grid build-out and data-centre operators from SEC XBRL (track S2, run 14): catalog series.

Vertiv, GE Vernova, Eaton and Quanta Services (all measures in G7), Equinix and Digital Realty (revenue and RPO in G4,
capex in G5, as CoreWeave). Quarterly, MUSD, release-dated: known_from = filing date of the 10-Q/10-K, every filing a
vintage, YTD differencing, Q4 = FY - 9M and the midpoint calendar mapping of ai_tracker.sources.sec.

- Total revenue and capex from companyfacts (sec.facts). Digital Realty's companyfacts lacks its 10-Qs filed
  2026-07-31 and 2026-10-30, so its flows are read from every filing's own XBRL instance instead (facts without
  dimensions = Digital Realty Trust, Inc.; in three filings of 2010-2011 LegalEntityAxis = ParentCompanyMember).
  A lower-priority tag is not used from a filing where it holds another line (same_line).
- Segment revenue from the instances: a fact counts only when its context dimensions are exactly one of the declared
  sets (segment member plus the consolidation marker the company uses), and lines are split into one key per
  definition at declared breaks (as series/sec_segments.py). Vertiv: gross (with intersegment sales) and external.
- Remaining performance obligations (Eaton: its firm order backlog, tagged as RPO) as balances (sec_rpo): total only.
  Vertiv tags no RPO; the facts it tags as RevenueRemainingPerformanceObligation are the timing of noncurrent deferred
  revenue, so there is no rpo_vrt (BLOCKED in XBRL).

Tag choice, members, breaks and checks are pre-registered in docs/mattregister.md (2026-11-25, S2, and the amendment
X15 after review R18) and documented in docs/kallor/sec_stack_kraft.md. Catalog series, not core series: they are not
in the branch index.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.series.neoclouds import rounding_revisions_dropped
from ai_tracker.series.sec import LICENSE
from ai_tracker.series.sec_segments import REVENUE, DefinitionBreakError
from ai_tracker.sources import sec, sec_custom, sec_rpo, sec_segment

SOURCE = "SEC EDGAR XBRL companyfacts"
SOURCE_INST = "SEC EDGAR XBRL instances"
SOURCE_SEG = "SEC EDGAR XBRL instances (segment dimensions)"
SOURCE_RPO = "SEC EDGAR XBRL instances (RPO)"

VRT, GEV, ETN, ETN_CORP, PWR, EQIX, DLR = 1674101, 1996810, 1551182, 31277, 1050915, 1101239, 1297996
RFCC = "RevenueFromContractWithCustomerExcludingAssessedTax"
SEG, CONS, PROD = "StatementBusinessSegmentsAxis", "ConsolidationItemsAxis", "ProductOrServiceAxis"
LAG_DAYS = 25


@dataclass(frozen=True)
class Company:
    name: str
    ciks: tuple[int, ...]  # successor first; a predecessor carries the older history (same fiscal calendar)
    rev: tuple[str, ...]  # tag priority list (docs/mattregister.md, S2)
    capex: tuple[str, ...]
    capex_line: str  # the company's own cash-flow label, Swedish note
    datacenter: bool  # Equinix, Digital Realty: revenue and RPO in G4, capex in G5; else everything in G7
    max_age_days: int  # largest observed days from quarter end to the first own 10-Q/10-K (2015-2026) + 92 + 30
    instances_since: str | None = None  # flows read from the instances (companyfacts incomplete), first filing date
    cik_since: tuple[tuple[int, str], ...] = ()  # (cik, first filing date used): a CIK's earlier filings are dropped


COMPANIES = {
    "vrt": Company("Vertiv", (VRT,), (RFCC,), ("PaymentsToAcquirePropertyPlantAndEquipment",),
                   "'Capital expenditures' (raden 'Investments in capitalized software' ingår inte)", False, 72 + 92 + 30),
    "gev": Company("GE Vernova", (GEV,), (RFCC,), ("PaymentsToAcquireProductiveAssets",),
                   "'Additions to property, plant, and equipment and internal-use software'", False, 37 + 92 + 30),
    # Eaton plc's own 10-Q filed 2012-11-14 is the pre-merger shell's (zero sales for Q3 2012); Eaton Corporation's
    # filings carry that period.
    "etn": Company("Eaton", (ETN, ETN_CORP), (RFCC, "SalesRevenueNet"), ("PaymentsToAcquirePropertyPlantAndEquipment",),
                   "'Capital expenditures for property, plant and equipment'", False, 60 + 92 + 30,
                   cik_since=((ETN, "2013-01-01"),)),
    "pwr": Company("Quanta Services", (PWR,), (RFCC, "SalesRevenueServicesNet"),
                   ("PaymentsToAcquirePropertyPlantAndEquipment",), "'Capital expenditures'", False, 61 + 92 + 30),
    # The older capex tag is the same line in the 10-Qs 2010-2018; the two filings where it holds a property purchase
    # instead (10-K 2011-02-25, 10-Q 2011-04-29) are dropped by same_line (register 2026-11-25, X15).
    "eqix": Company("Equinix", (EQIX,), (RFCC, "Revenues"), ("PaymentsToAcquireOtherPropertyPlantAndEquipment",
                                                              "PaymentsToAcquirePropertyPlantAndEquipment"),
                    "'Purchases of other property, plant and equipment', i 10-Q 2010–2014 'Purchases of property, plant "
                    "and equipment' (raden 'Real estate acquisitions' ingår inte)", True, 61 + 92 + 30),
    "dlr": Company("Digital Realty", (DLR,), ("Revenues",), ("PaymentsToDevelopRealEstateAssets",),
                   "'Improvements to investments in real estate' (förvärv och investeringar i intresseföretag ingår inte)",
                   True, 62 + 92 + 30, instances_since="2009-01-01"),
}
CIK_NOTE = {"vrt": "1674101 (f.d. GS Acquisition Holdings Corp; som Vertiv från 10-K 2020-03-12)",
            "gev": "1996810 (Form 10 utan XBRL; historiken börjar med jämförelsetalen i 10-Q 2024)",
            "etn": "1551182 (Eaton Corporation plc) och föregångaren 31277 (Eaton Corporation, till 10-Q 2012-10-31)",
            "pwr": "1050915", "eqix": "1101239",
            "dlr": "1297996 (companyfacts saknar 10-Q 2026-07-31 och 2026-10-30, därför ur instanserna)"}


# ------------------------------------------------------------------ fact filters

# A 10-Q's primary statements report the current period and the same period a year earlier: a comparative ends about
# 13-15 months before the filing date. A 10-Q fact ending more than this many days before its filing is a mis-dated
# context (Equinix's 10-Q 2025-04-30 tags Q1 2025 revenue with the dates of Q1 2023) and is dropped (register
# 2026-11-25, S2 amendment). Flows and balances only: a segment note after a re-segmentation recasts older quarters
# (Eaton's 10-Q 2020-04-30 has 2018), so segment revenue is not filtered (register 2026-11-25, X15, review R18-9).
MAX_10Q_AGE_DAYS = 550


def plausible(f) -> bool:
    """False for a 10-Q fact (or balance) dated more than MAX_10Q_AGE_DAYS before the filing."""
    return not (f.form.startswith("10-Q") and (f.filed - f.end).days > MAX_10Q_AGE_DAYS)


def kept(facts, cik: int, company: str, age_rule: bool = True) -> list:
    """Facts that pass `plausible` (unless age_rule is False) and the company's per-CIK first filing date."""
    since = dict(COMPANIES[company].cik_since).get(cik)
    return [f for f in facts if (not age_rule or plausible(f)) and (since is None or f.filed >= pd.Timestamp(since))]


def same_line(sources: list[list[sec.Fact]]) -> list[list[sec.Fact]]:
    """Drop a lower-priority tag's facts from every filing where it differs from a higher-priority tag (same period).

    In such a filing the lower tag holds another line: Equinix's PaymentsToAcquirePropertyPlantAndEquipment is a
    property purchase in the 10-K 2011-02-25 and the 10-Q 2011-04-29, the capex line in its other filings (register
    2026-11-25, X15).
    """
    out: list[list[sec.Fact]] = []
    for k, facts in enumerate(sources):
        higher = {(f.accn, f.start, f.end): f.val for fs in sources[:k] for f in fs}
        other_line = {f.accn for f in facts
                      if (f.accn, f.start, f.end) in higher and abs(higher[(f.accn, f.start, f.end)] - f.val) > sec.TOL}
        out.append([f for f in facts if f.accn not in other_line])
    return out


# ------------------------------------------------------------------ total revenue and capex

# Digital Realty's 10-Q 2010-11-09, 10-K/A 2011-03-25 and 10-Q 2011-05-09 carry LegalEntityAxis on every fact: Digital
# Realty Trust, Inc. as ParentCompanyMember, the partnership as DigitalRealtyTrustLPMember (same values). Used for a tag
# only in a filing without undimensioned facts of it (register 2026-11-25, X15).
PARENT = frozenset({("LegalEntityAxis", "ParentCompanyMember")})


def instance_flow_facts(cik: int, tag: str, since: str) -> list[sec.Fact]:
    """Per filing the undimensioned facts of `tag`, or else those with exactly LegalEntityAxis = ParentCompanyMember."""
    out: list[sec.Fact] = []
    for f, raw in sec_custom._filings(cik, since, "9999-12-31"):
        dfs = sec_segment.parse_instance(raw, {tag})
        out += sec_custom.plain_facts(dfs, f, [tag]) or exact_facts(dfs, f, (tag,), PARENT)
    return out


def flow_sources(company: str, tags: tuple[str, ...]) -> list[list[sec.Fact]]:
    """One fact list per tag (priority order): companyfacts over all CIKs, or the instances (Digital Realty).

    A lower-priority tag's facts are dropped from filings where it holds another line (same_line).
    """
    c = COMPANIES[company]
    if c.instances_since:
        return same_line([kept(instance_flow_facts(cik, tag, c.instances_since), cik, company)
                          for tag in tags for cik in c.ciks[:1]])
    return same_line([[f for cik in c.ciks for f in kept(sec.facts(sec.companyfacts(cik), tag), cik, company)]
                      for tag in tags])


@lru_cache(maxsize=None)
def flow_vintages(measure: str, company: str) -> pd.DataFrame:
    """All vintages (period, value, known_from, fiscal_end) before the gap and rounding filters (for the checks)."""
    c = COMPANIES[company]
    return sec.vintages(flow_sources(company, c.rev if measure == "rev" else c.capex))


@lru_cache(maxsize=None)
def flow_series(measure: str, company: str) -> pd.DataFrame:
    df = flow_vintages(measure, company)[["period", "value", "known_from"]]
    return sec.contiguous_tail(rounding_revisions_dropped(df))


# ------------------------------------------------------------------ segment revenue


@dataclass(frozen=True)
class SegLine:
    """One segment revenue line; `keys` has one series key per definition regime (len(breaks) + 1)."""

    keys: tuple[str, ...]
    company: str
    cik: int
    since: str  # first filing date scanned
    dimsets: tuple[frozenset, ...]  # alternatives: exact context dimensions; per filing the first with facts wins
    label: str
    breaks: tuple[str, ...] = ()  # declared definition breaks (filing dates)
    regime_notes: tuple[str, ...] = ()
    note: str = ""  # key into SEG_NOTE; default the company


def _seg(member: str, marker: str | None = None) -> frozenset:
    return frozenset({(SEG, member)} | ({(CONS, marker)} if marker else set()))


def _etn(stem: str) -> tuple[frozenset, ...]:
    """Eaton's electrical segment: the name from 2021, then the name in the 10-Qs of 2020; no marker first."""
    return tuple(_seg(m, k) for m in (f"{stem}SegmentMember", f"{stem}Member") for k in (None, "OperatingSegmentsMember"))


GEV_MARKER = "OperatingSegmentsExcludingIntersegmentEliminationMember"
SEG_LINES = [
    SegLine(("rev_gev_power",), "gev", GEV, "2024-01-01", (_seg("PowerSegmentMember", GEV_MARKER),), "Power (GE Vernova)"),
    SegLine(("rev_gev_wind",), "gev", GEV, "2024-01-01", (_seg("WindSegmentMember", GEV_MARKER),), "Wind (GE Vernova)"),
    # Effective 2026-01-01 GE Vernova moved a component of Electrification Software into Gas Power (Power segment); the
    # 10-Qs from 2026-04-22 recast 2025 by -1.4 to -2.1 % (Power +0.5 to +0.6 %, below the threshold: versions).
    SegLine(("rev_gev_electrification_fy24", "rev_gev_electrification_fy26"), "gev", GEV, "2024-01-01",
            (_seg("ElectrificationSegmentMember", GEV_MARKER),), "Electrification (GE Vernova)", breaks=("2026-04-22",),
            regime_notes=("Segmentdefinition före omorganisationen 2026 (inlämnat 2024-04 till 2026-01).",
                          "Omräknad definition från 2026 (inlämnat från 2026-04): en del av Electrification Software "
                          "flyttades till Gas Power i Power-segmentet.")),
    # The 10-Qs of 2020 name the segments ElectricalAmericasMember / ElectricalGlobalMember, the filings from the 10-K
    # 2021-02-24 ...SegmentMember; identical values in the overlap (register 2026-11-25, X15, review R18-1).
    SegLine(("rev_etn_electrical_americas",), "etn", ETN, "2020-01-01", _etn("ElectricalAmericas"),
            "Electrical Americas (Eaton)"),
    SegLine(("rev_etn_electrical_global",), "etn", ETN, "2020-01-01", _etn("ElectricalGlobal"),
            "Electrical Global (Eaton)"),
    SegLine(("rev_vrt_americas",), "vrt", VRT, "2020-01-01", (_seg("AmericasSegmentMember", "OperatingSegmentsMember"),),
            "Americas (Vertiv)"),
    SegLine(("rev_vrt_apac",), "vrt", VRT, "2020-01-01", (_seg("AsiaPacificSegmentMember", "OperatingSegmentsMember"),),
            "Asia Pacific (Vertiv)"),
    SegLine(("rev_vrt_emea",), "vrt", VRT, "2020-01-01", (_seg("EMEASegmentMember", "OperatingSegmentsMember"),),
            "Europe, Middle East & Africa (Vertiv)"),
    # External sales per segment: the member without a marker (register 2026-11-25, X15, review R18-3)
    SegLine(("rev_vrt_americas_net",), "vrt", VRT, "2020-01-01", (_seg("AmericasSegmentMember"),),
            "Americas, extern försäljning (Vertiv)", note="vrt_net"),
    SegLine(("rev_vrt_apac_net",), "vrt", VRT, "2020-01-01", (_seg("AsiaPacificSegmentMember"),),
            "Asia Pacific, extern försäljning (Vertiv)", note="vrt_net"),
    SegLine(("rev_vrt_emea_net",), "vrt", VRT, "2020-01-01", (_seg("EMEASegmentMember"),),
            "Europe, Middle East & Africa, extern försäljning (Vertiv)", note="vrt_net"),
]
SEG_NOTE = {
    "gev": "Segmentets intäkter före eliminering av interna intäkter (ConsolidationItemsAxis = "
           "OperatingSegmentsExcludingIntersegmentEliminationMember), som i segmentnoten.",
    "etn": "Segmentets intäkter (medlemmen utan markör, annars med OperatingSegmentsMember; identiska). Namnet utan "
           "'Segment' i 10-Q 2020, med 'Segment' från 10-K 2021-02-24 (identiska i överlappet). Bara inlämningar från "
           "2020, eftersom ElectricalAmericasMember användes för ett äldre segment i 10-K för 2012. Kvartalen 2018–2019 "
           "är omräknade jämförelsetal i 10-Q 2020-04-30.",
    "vrt": "Segmentets intäkter inklusive försäljning till andra segment (ConsolidationItemsAxis = "
           "OperatingSegmentsMember), som i segmentnotens rad 'Sales'; summan av segmenten är större än bolagets "
           "intäkter. Den interna andelen har vuxit (EMEA 5 % 2020Q1, 34 % 2026Q3). Extern försäljning: rev_vrt_*_net.",
    "vrt_net": "Segmentets externa försäljning ('Net sales', medlemmen utan markör). Summan av de tre segmenten är "
               "bolagets intäkter (rev_vrt). Bruttot med försäljning till andra segment: rev_vrt_americas, rev_vrt_apac "
               "och rev_vrt_emea.",
}


def exact_facts(dim_facts, f: sec_segment.Filing, concepts: tuple[str, ...], dims: frozenset,
                unit: str = "USD") -> list[sec.Fact]:
    """sec.Facts of one filing whose context dimensions are exactly `dims`; per period the first concept wins.

    As in sec.facts, 3-month facts in 10-Ks (the unaudited quarterly note) are ignored.
    """
    by_period: dict[tuple, tuple[int, float]] = {}
    for d in dim_facts:
        if d.unit != unit or d.concept not in concepts or frozenset(d.dims) != dims:
            continue
        if f.form.startswith("10-K") and sec._is_quarter(d.start, d.end):
            continue
        rank = concepts.index(d.concept)
        if (d.start, d.end) not in by_period or rank < by_period[(d.start, d.end)][0]:
            by_period[(d.start, d.end)] = (rank, d.value)
    filed = pd.Timestamp(f.filed)
    return [sec.Fact(s, e, v, filed, f.form, f.accession) for (s, e), (_, v) in sorted(by_period.items())]


def line_facts_from(filings_facts, line: SegLine) -> list[sec.Fact]:
    """sec.Facts of one line over (filing, dimensional facts) pairs: per filing the first matching dimension set."""
    out: list[sec.Fact] = []
    for f, dfs in filings_facts:
        for dims in line.dimsets:
            got = exact_facts(list(dfs), f, tuple(REVENUE), dims)
            if got:
                out += got
                break
    return out


@lru_cache(maxsize=None)
def seg_facts(line: SegLine) -> tuple[sec.Fact, ...]:
    facts = line_facts_from(sec_segment.company_facts(line.cik, line.since, tuple(REVENUE)), line)
    return tuple(kept(facts, line.cik, line.company, age_rule=False))  # no 550-day rule for segments (X15)


def checked_regimes(keys: tuple[str, ...], breaks: tuple[str, ...], facts: list[sec.Fact]) -> list[list[sec.Fact]]:
    """Facts per definition regime; DefinitionBreakError if the detected breaks differ from the declared ones."""
    found = [str(d.date()) for d in sec_segment.definition_breaks(facts)]
    if found != list(breaks):
        raise DefinitionBreakError(f"{keys[0]}: detected definition breaks {found}, declared {list(breaks)}; "
                                   "review and declare (docs/kallor/sec_stack_kraft.md)")
    return sec_segment.regimes(facts, [pd.Timestamp(b) for b in breaks])


@lru_cache(maxsize=None)
def seg_series(line: SegLine) -> tuple[pd.DataFrame, ...]:
    regs = checked_regimes(line.keys, line.breaks, list(seg_facts(line)))
    return tuple(sec.contiguous_tail(sec.vintages([reg])) for reg in regs)


# ------------------------------------------------------------------ RPO (balances)


@dataclass(frozen=True)
class Balance:
    keys: tuple[str, ...]
    company: str
    cik: int
    since: str  # first filing date scanned
    dims: frozenset  # empty = the total (sec_rpo.totals); else the RPO amount with exactly these dimensions
    label: str
    note: str
    breaks: tuple[str, ...] = ()


BALANCES = [
    Balance(("rpo_gev",), "gev", GEV, "2024-01-01", frozenset(), "Återstående prestationsåtaganden (RPO), GE Vernova",
            "Totalt RPO utan dimension."),
    Balance(("rpo_gev_equipment",), "gev", GEV, "2024-01-01", frozenset({(PROD, "ProductMember")}),
            "RPO för utrustning, GE Vernova", "RPO med ProductOrServiceAxis = ProductMember (utrustning)."),
    Balance(("rpo_gev_services",), "gev", GEV, "2024-01-01", frozenset({(PROD, "ServiceMember")}),
            "RPO för tjänster, GE Vernova", "RPO med ProductOrServiceAxis = ServiceMember (tjänster)."),
    Balance(("rpo_pwr",), "pwr", PWR, "2018-01-01", frozenset(), "Återstående prestationsåtaganden (RPO), Quanta Services",
            "Totalt RPO utan dimension. Inte bolagets 'total backlog', som också räknar med uppskattade avrop under "
            "ramavtal (MSA) och inte taggas."),
    Balance(("rpo_etn",), "etn", ETN, "2020-01-01", frozenset(), "Orderstock (fasta order), Eaton",
            "Eatons 'total backlog' (order som kunderna är fast bundna till), taggad som RevenueRemainingPerformance"
            "Obligation: utan dimension 2020Q3–2024Q1, därefter med bara startdatumaxeln (en hink)."),
    Balance(("rpo_eqix",), "eqix", EQIX, "2018-01-01", frozenset(), "Återstående prestationsåtaganden (RPO), Equinix",
            "Totalt RPO utan dimension."),
]


def balance_facts_from(filings_instants, b: Balance) -> list[sec.Fact]:
    """sec.Facts (start = end = balance date) of one balance over (filing, RPO instant facts) pairs."""
    out: list[sec.Fact] = []
    for f, facts in filings_instants:
        if not b.dims:
            out += sec_rpo.filing_facts(f, list(facts), None)["total"]
            continue
        filed, seen = pd.Timestamp(f.filed), set()
        for x in facts:
            if x.concept == sec_rpo.RPO and x.unit == "USD" and x.dims == b.dims and x.instant not in seen:
                seen.add(x.instant)
                out.append(sec.Fact(x.instant, x.instant, x.value, filed, f.form, f.accession))
    return out


@lru_cache(maxsize=None)
def balance_facts(b: Balance) -> tuple[sec.Fact, ...]:
    return tuple(kept(balance_facts_from(sec_rpo.company_instants(b.cik, b.since), b), b.cik, b.company))


@lru_cache(maxsize=None)
def balance_series(b: Balance) -> tuple[pd.DataFrame, ...]:
    regs = checked_regimes(b.keys, b.breaks, list(balance_facts(b)))
    return tuple(sec.contiguous_tail(sec_rpo.stock_vintages(reg)) for reg in regs)


# ------------------------------------------------------------------ catalog


def _rows(df: pd.DataFrame) -> pd.DataFrame:
    return df[["period", "value", "known_from"]].copy()


QUESTIONS = {
    "G7rev": "Hur snabbt växer intäkterna hos leverantörerna av kraft, kylning och elnät?",
    "G7capex": "Hur mycket bygger leverantörerna av kraft, kylning och elnät ut sin egen kapacitet?",
    "G7rpo": "Hur stor är orderstocken för kraft- och elnätsutrustning, före leveranserna?",
    "G4rev": "Hur snabbt växer intäkterna hos datacenterbolagen?",
    "G5capex": "Hur mycket bygger datacenterbolagen ut?",
    "G4rpo": "Hur stor är den kontrakterade efterfrågan hos datacenterbolagen?",
}


def _tail(company: str) -> str:
    c = COMPANIES[company]
    return (f" CIK {CIK_NOTE[company]}. Kalenderår. Aktualitet: gräns {c.max_age_days} dagar = största observerade avstånd "
            "från kvartalets slut till första egna 10-Q/10-K (2015–2026) + 92 + 30 (docs/kallor/sec_stack_kraft.md).")


def _spec(key: str, branch: str, label: str, source: str, fetch, company: str, note: str, kind: str,
          closed: bool = False) -> Spec:
    c = COMPANIES[company]
    return Spec(key=key, branch=branch, label=label, unit="MUSD", freq="Q", source=source, fetch=fetch,
                lag_days=LAG_DAYS, license=LICENSE, revised=True, publish=True,
                question=QUESTIONS[branch + kind], note=note + _tail(company),
                max_age_days=None if closed else c.max_age_days, closed=closed)


def _specs() -> list[Spec]:
    specs = []
    for co, c in COMPANIES.items():
        src = SOURCE_INST if c.instances_since else SOURCE
        rev_branch, capex_branch = ("G4", "G5") if c.datacenter else ("G7", "G7")
        capex_label = "Capex (utbyggnad och förbättring av datacenter)" if c.datacenter else \
            "Capex (köp av anläggningstillgångar)"
        specs.append(_spec(f"rev_{co}", rev_branch, f"Intäkter, {c.name}", src, lambda co=co: _rows(flow_series("rev", co)),
                           co, "Taggar: " + ", ".join(c.rev) + ".", "rev"))
        specs.append(_spec(f"capex_{co}", capex_branch, f"{capex_label}, {c.name}", src,
                           lambda co=co: _rows(flow_series("capex", co)), co,
                           f"Tagg: {', '.join(c.capex)}, raden {c.capex_line}.", "capex"))
    for line in SEG_LINES:
        members = "; ".join(", ".join(f"{a}={m}" for a, m in sorted(d)) for d in line.dimsets)
        for i, key in enumerate(line.keys):
            closed = i < len(line.keys) - 1
            note = f"Kontext (exakt): {members}. {SEG_NOTE[line.note or line.company]}"
            if line.regime_notes:
                note += " " + line.regime_notes[i]
            if closed:
                note += " Avslutad: ersatt av nästa definition efter ett definitionsbrott."
            specs.append(_spec(key, "G7", f"Segmentintäkter, {line.label}", SOURCE_SEG,
                               lambda line=line, i=i: _rows(seg_series(line)[i]), line.company, note, "rev", closed))
    for b in BALANCES:
        branch = "G4" if COMPANIES[b.company].datacenter else "G7"
        for i, key in enumerate(b.keys):
            closed = i < len(b.keys) - 1
            note = "Balans vid kvartalets slut (stock), inte flöde. " + b.note
            if closed:
                note += " Avslutad: ersatt av nästa definition efter ett definitionsbrott."
            specs.append(_spec(key, branch, b.label, SOURCE_RPO, lambda b=b, i=i: _rows(balance_series(b)[i]),
                               b.company, note, "rpo", closed))
    return specs


SPECS = _specs()
