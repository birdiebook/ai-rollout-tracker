"""Network, optics and servers (track S1, branch G6): the layers between the chips and the data centre, from SEC XBRL.

Arista, Cisco, Coherent, Lumentum, Super Micro, Dell, HPE and Celestica, quarterly, release-dated (known_from = the
10-Q/10-K filing date, every filing a vintage). Catalog series, not core series.

- rev_<co>: total revenue (companyfacts, ai_tracker.sources.sec: YTD differencing, Q4 = FY - 9M, midpoint calendar
  mapping, restatements as vintages);
- inv_<co>: inventories at fiscal quarter end (companyfacts instants, ai_tracker.sources.sec_instant);
- segment and product-line revenue from each filing's XBRL instance (ai_tracker.sources.sec_segment), with exactly the
  given dimension set (one segment or product member, or Dell's product x segment pairs), one series per definition;
- purchase_oblig_<co>, deferred_rev_anet, rpo_<co>: balances (companyfacts or instances), dated like the inventories so
  that a balance and the flows of the same fiscal quarter share a period label (for RPO this differs from sec_rpo.py,
  which uses the balance date's own calendar quarter; the same for calendar-quarter companies).

Definition breaks (sec_segment.definition_breaks, a restatement of an earlier-filed value by more than 2%) are checked
for every segment line and every balance series except inventories, and must equal the declared ones, otherwise the
fetch fails (DefinitionBreakError). Segment lines also skip a Q4 = FY - 9M across a basis change below 2% (same_basis,
register amendment after review R17). A declared segment break splits the line into separate keys (never spliced); a
declared balance restatement is a version unless the filing's text says the definition changed. Tags, members, breaks,
calendars and hand checks are pre-registered in docs/mattregister.md (2026-11-25, S1) and documented in
docs/kallor/sec_stack_nat.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.series.sec import LICENSE, REVENUE
from ai_tracker.series.sec_segments import PROD, SEG, DefinitionBreakError
from ai_tracker.sources import sec, sec_custom, sec_instant, sec_segment

SOURCE = "SEC EDGAR XBRL companyfacts"
SOURCE_SEG = "SEC EDGAR XBRL instances (segment dimensions)"
SOURCE_INST = "SEC EDGAR XBRL instances"
INCL = "RevenueFromContractWithCustomerIncludingAssessedTax"
INVENTORY = "InventoryNet"
RPO = "RevenueRemainingPerformanceObligation"

ANET, CSCO, COHR, LITE, SMCI, DELL, HPE, CLS = 1596532, 858877, 820318, 1633978, 1375365, 1571996, 1645590, 1030894


@dataclass(frozen=True)
class Company:
    name: str
    cik: int
    revenue: tuple[str, ...]  # companyfacts tag priority list; also the concepts read for segment lines
    since: str  # first filing date scanned in the instances (segment lines)
    lag_days: int
    max_age_days: int  # largest observed lag (days, calendar quarter end to first own filing) + 92 + 30
    calendar: str  # Swedish, for the note
    # Total revenue restatements > 2% (register amendment 2026-11-25): scope changes (discontinued operations,
    # spin-offs) make rev_<co> read only filings from the last one; corrections of the same definition stay versions.
    rev_scope_breaks: tuple[str, ...] = ()
    rev_revisions: tuple[str, ...] = ()
    rev_note: str = ""  # Swedish


# max_age: largest observed days from the calendar quarter's end to the first own filing (2015-2026, comparatives in
# later filings excluded), + 92 + 30; docs/kallor/sec_stack_nat.md, "Kalender".
COMPANIES: dict[str, Company] = {
    "anet": Company("Arista Networks", ANET, tuple(REVENUE), "2014-06-01", 25, 56 + 92 + 30,
                    "kalenderår; 10-Q och 10-K 31–56 dagar efter kvartalet"),
    "csco": Company("Cisco", CSCO, tuple(REVENUE), "2016-01-01", 25, 71 + 92 + 30,
                    "52/53 veckor till sista lördagen i juli; kvartal slutar i slutet av okt/jan/apr/jul: aug–okt "
                    "räknas som Q3 och nov–jan som Q4 (mittpunktsregeln), ungefär en månad efter kalenderkvartalet"),
    "cohr": Company("Coherent", COHR, tuple(REVENUE), "2016-01-01", 25, 60 + 92 + 30,
                    "till 30 juni, kvartal = kalenderkvartal (II-VI till 2022)",
                    rev_scope_breaks=("2014-08-28",), rev_revisions=("2012-02-08",),
                    rev_note="Läser inlämningar från 10-K 2014-08-28, då produktlinjen tellurium redovisades som avvecklad "
                             "verksamhet och tidigare år räknades om (−3,4 %). Omräkningen 2012-02-08 (+2,0 % för ett "
                             "kvartal 2010) förklaras inte i textblocken och påverkar inte serien."),
    "lite": Company("Lumentum", LITE, (INCL, *REVENUE), "2015-08-01", 25, 64 + 92 + 30,
                    "52/53 veckor till lördagen närmast 30 juni, kvartal slutar nära kalenderkvartalets slut"),
    "smci": Company("Super Micro Computer", SMCI, tuple(REVENUE), "2016-01-01", 25, 81 + 92 + 30,
                    "till 30 juni, kvartal = kalenderkvartal",
                    rev_revisions=("2019-05-17",),
                    rev_note="Omräkningen i 10-K och 10-Q/A 2019-05-17 (efter revisionsutskottets utredning, ±3–4 % för "
                             "kvartal 2015–2017) är en rättelse av samma definition och ger versioner."),
    "dell": Company("Dell Technologies", DELL, tuple(REVENUE), "2016-06-01", 25, 90 + 92 + 30,
                    "52/53 veckor till fredagen närmast 31 januari: aug–okt räknas som Q3 och nov–jan som Q4 "
                    "(mittpunktsregeln), ungefär en månad efter kalenderkvartalet",
                    rev_scope_breaks=("2017-06-09", "2022-03-24"),
                    rev_note="Läser inlämningar från 10-K 2022-03-24, där VMware (avknoppat 2021-11) redovisas som "
                             "avvecklad verksamhet och tidigare år räknades om. Tidigare brott: Dell Services, DSG och ECD "
                             "som avvecklad verksamhet (10-Q 2017-06-09)."),
    "hpe": Company("Hewlett Packard Enterprise", HPE, tuple(REVENUE), "2015-11-01", 25, 83 + 92 + 30,
                   "till 31 oktober, kvartal slutar 31 jan/apr/jul/okt: aug–okt räknas som Q3 och "
                   "nov–jan som Q4 (mittpunktsregeln), en månad efter kalenderkvartalet",
                   rev_scope_breaks=("2017-06-08", "2018-06-07"),
                   rev_note="Läser inlämningar från 10-Q 2018-06-07, där Enterprise Services (Everett, till DXC 2017-04) "
                            "och mjukvaran (Seattle, till Micro Focus 2017-09) redovisas som avvecklad verksamhet i alla "
                            "jämförelsetal."),
    "cls": Company("Celestica", CLS, tuple(REVENUE), "2024-01-01", 25, 58 + 92 + 30,
                   "kalenderår; 10-K och 10-Q med US GAAP från 10-K för 2024 (2025-03-03), tidigare 20-F och 6-K"),
}


# ------------------------------------------------------------------ segment and product lines


def dims(*pairs: tuple[str, str]) -> frozenset:
    return frozenset(pairs)


@dataclass(frozen=True)
class SegLine:
    """One reported revenue line; `keys` has one series key per definition regime (len(breaks) + 1)."""

    keys: tuple[str, ...]
    company: str
    members: tuple[frozenset, ...]  # alternative dimension sets of the same line; per filing the first one found wins
    label: str  # Swedish
    breaks: tuple[str, ...] = ()  # declared definition breaks: the filings where a new definition starts (split dates)
    regime_notes: tuple[str, ...] = ()
    discontinued: str = ""  # Swedish reason, when the last regime is no longer reported
    description: str = ""  # Swedish, what the line contains
    caveat: str = ""  # Swedish; replaces SEG_CAVEAT when set
    # What definition_breaks must find, when it differs from `breaks`: a realignment whose first filing restates by less
    # than 2% is flagged only at the next filing (HPE's Server, register amendment 2026-11-25). None = `breaks`.
    detected: tuple[str, ...] | None = None


def _seg(member: str) -> frozenset:
    return dims((SEG, member))


def _prod(member: str) -> frozenset:
    return dims((PROD, member))


ISG, ESG = (SEG, "InfrastructureSolutionsGroupMember"), (SEG, "EnterpriseSolutionsGroupMember")

LINES = [
    SegLine(("rev_csco_networking",), "csco", (_prod("NetworkingMember"), _prod("NetworkingRevenueMember")),
            "Produktkategorin Networking (Cisco)",
            description="Switchar, routrar, trådlöst, servrar (UCS) och IoT; produktkategori från FY2024 med FY2023 "
                        "som jämförelse (10-K 2024-09-05 taggar den som NetworkingRevenueMember)."),
    SegLine(("rev_csco_infra_platforms",), "csco", (_prod("InfrastructurePlatformsMember"),),
            "Produktkategorin Infrastructure Platforms (Cisco, FY2018–FY2021)",
            discontinued="Cisco ersatte kategorierna i FY2022 (10-Q 2021-11-23).",
            description="Switchar, routrar, trådlöst och datacenter (servrar); produktkategori FY2018–FY2021."),
    SegLine(("rev_cohr_networking",), "cohr", (_seg("NetworkingSegmentMember"),),
            "Segmentet Networking (Coherent, FY2023–FY2025)",
            discontinued="Coherent ersatte segmenten med Datacenter & Communications och Industrial i FY2026 "
                         "(10-Q 2025-11-05).",
            description="Optiska transceivrar och komponenter för datacenter och telekom; segment efter förvärvet av "
                        "Coherent Inc. (2022-07), med FY2022 som jämförelse."),
    SegLine(("rev_cohr_datacom",), "cohr", (_seg("DatacenterAndCommunicationsSegmentMember"),),
            "Segmentet Datacenter & Communications (Coherent)",
            description="Segment från FY2026 med FY2025 som jämförelse."),
    SegLine(("rev_lite_opcomms",), "lite", (_seg("OpticalCommunicationsSegmentMember"),),
            "Segmentet Optical Communications (Lumentum, till FY2023)",
            discontinued="Lumentum ersatte segmenten med Cloud & Networking och Industrial Tech i FY2024 "
                         "(10-Q 2023-11-08).",
            description="Optiska komponenter och moduler för telekom, datacom och 3D-avkänning."),
    SegLine(("rev_lite_cloud_networking",), "lite", (_seg("CloudNetworkingSegmentMember"),),
            "Segmentet Cloud & Networking (Lumentum, FY2024–FY2025)",
            discontinued="Lumentum har ett rapporterbart segment från FY2026 (10-Q 2025-11-05) och delar intäkterna "
                         "i Components och Systems.",
            description="Segment från FY2024 med FY2023 som jämförelse."),
    SegLine(("rev_lite_components",), "lite", (_seg("ComponentsMember"),), "Components (Lumentum)",
            description="Intäktsrad från FY2026 (ett rapporterbart segment), med FY2025 som jämförelse."),
    SegLine(("rev_lite_systems",), "lite", (_seg("SystemsMember"),), "Systems (Lumentum)",
            description="Intäktsrad från FY2026 (ett rapporterbart segment), med FY2025 som jämförelse."),
    SegLine(("rev_dell_isg",), "dell", (dims(ISG), dims(ESG)), "Segmentet Infrastructure Solutions Group (Dell)",
            description="Servrar, nät och lagring. Hette Enterprise Solutions Group till 10-Q 2018-06-12. EMC ingår från "
                        "fusionen 2016-09-07 (10-Q 2016-12-09), och nivån mer än fördubblas från 2016Q2 till 2016Q4. "
                        "Det är inte organisk tillväxt, och serien är jämförbar över tid först från 2017Q1."),
    SegLine(("rev_dell_servers_networking",), "dell",
            (dims((PROD, "ServersAndNetworkingMember"), ISG), dims((PROD, "ServersAndNetworkingMember"), ESG)),
            "Servers and networking inom ISG (Dell, till FY2026 Q3)",
            discontinued="Dell delar raden i AI-optimerade och traditionella servrar och nät från 10-K för FY2026 "
                         "(2026-03-16).",
            description="Alla servrar och nätprodukter i ISG, både traditionella och AI-optimerade. ISG omfattar EMC "
                        "från fusionen 2016-09-07 (10-Q 2016-12-09). I raden syns inget nivåskifte av samma storlek "
                        "som i ISG, men hur mycket av EMC som ingår går inte att skilja ut, så kvartalen före 2017Q1 "
                        "jämförs bara med förbehåll."),
    SegLine(("rev_dell_ai_servers",), "dell", (dims((PROD, "AIOptimizedServersAndNetworkingMember"), ISG),),
            "AI-optimerade servrar och nät inom ISG (Dell)",
            description="Rad från 10-K för FY2026 (2026-03-16), med FY2025 som jämförelse.",
            caveat="Dells egen avgränsning av AI-optimerade servrar och nät. Lagring, tjänster och AI-system i andra "
                   "rader ingår inte, och raden säger inget om slutkundens användning."),
    SegLine(("rev_dell_traditional_servers",), "dell", (dims((PROD, "TraditionalServersAndNetworkingMember"), ISG),),
            "Traditionella servrar och nät inom ISG (Dell)",
            description="Rad från 10-K för FY2026 (2026-03-16), med FY2025 som jämförelse."),
    SegLine(("rev_hpe_server_fy24", "rev_hpe_server_fy26"), "hpe", (_seg("ServerSegmentMember"),), "Server (HPE)",
            breaks=("2026-03-10",), detected=("2026-06-02",),
            regime_notes=("Segmentdefinition FY2024–FY2025 (Compute och HPC & AI slogs ihop; inlämnat 2024-03 till "
                          "2025-12), med FY2023 som jämförelse.",
                          "Definition efter HPE:s omorganisation från 2025-11-01 (inlämnat från 2026-03-10): en "
                          "produktkategori i segmentet Cloud & AI, med FY2025 omräknat med ungefär +2 %."),
            description="HPE:s servrar (traditionella och AI-system)."),
    SegLine(("rev_hpe_dc_networking",), "hpe", (_seg("DataCenterNetworkingMember"),),
            "Data Center Networking (HPE)",
            description="Produktkategori i segmentet Networking från FY2026, med FY2025 som jämförelse. Juniper ingår "
                        "från förvärvet 2025-07."),
    SegLine(("rev_cls_ccs",), "cls", (_seg("CCSSegmentMember"),),
            "Segmentet Connectivity & Cloud Solutions (Celestica)",
            description="Servrar, lagring och nätutrustning (bland annat switchar) för molnbolag och företag; "
                        "segmentet finns i US GAAP-inlämningarna från 10-K för 2024."),
]


def exact_facts(dim_facts, f: sec_segment.Filing, concepts: list[str], want: frozenset,
                unit: str = "USD") -> list[sec.Fact]:
    """sec.Facts whose context dimensions are exactly `want` (plus, optionally, the operating-segment marker).

    The same rule as sec_segment.to_facts, for any number of dimensions (Dell tags product x segment). Within one
    filing, the first concept in `concepts` that has a period wins, and a context without the marker before one with
    it. 3-month facts in 10-Ks (the unaudited quarterly note) are ignored, as in sec.facts.
    """
    by_period: dict[tuple, tuple[tuple, float]] = {}
    for d in dim_facts:
        if d.unit != unit or d.concept not in concepts or set(d.dims) - sec_segment.NEUTRAL_DIMS != set(want):
            continue
        if f.form.startswith("10-K") and sec._is_quarter(d.start, d.end):
            continue
        rank = (concepts.index(d.concept), len(d.dims))
        key = (d.start, d.end)
        if key not in by_period or rank < by_period[key][0]:
            by_period[key] = (rank, d.value)
    filed = pd.Timestamp(f.filed)
    return [sec.Fact(s, e, v, filed, f.form, f.accession) for (s, e), (_, v) in sorted(by_period.items())]


def line_facts(line: SegLine) -> list[sec.Fact]:
    c = COMPANIES[line.company]
    out: list[sec.Fact] = []
    for f, dfs in sec_segment.company_facts(c.cik, c.since, c.revenue):
        for want in line.members:
            got = exact_facts(list(dfs), f, list(c.revenue), want)
            if got:
                out += got
                break
    return out


def checked_regimes(name: str, facts: list[sec.Fact], declared: tuple[str, ...],
                    detected: tuple[str, ...] | None = None) -> list[list[sec.Fact]]:
    """Facts split at the declared breaks; DefinitionBreakError if definition_breaks finds anything other than
    `detected` (default: the declared breaks)."""
    found = [str(d.date()) for d in sec_segment.definition_breaks(facts)]
    expected = list(declared if detected is None else detected)
    if found != expected:
        raise DefinitionBreakError(f"{name}: detected definition breaks {found}, declared {expected}; "
                                   "review and declare (docs/kallor/sec_stack_nat.md)")
    return sec_segment.regimes(facts, [pd.Timestamp(b) for b in declared])


def restating_filings(facts: list[sec.Fact]) -> set[pd.Timestamp]:
    """Filing dates that change an earlier-filed value of the same (start, end) by more than sec.TOL."""
    latest: dict[tuple, float] = {}
    out = set()
    for filed in sorted({f.filed for f in facts}):
        batch = [f for f in facts if f.filed == filed]
        if any((f.start, f.end) in latest and abs(f.val - latest[(f.start, f.end)]) > sec.TOL for f in batch):
            out.add(filed)
        for f in batch:
            latest[(f.start, f.end)] = f.val
    return out


def same_basis(facts: list[sec.Fact]) -> sec.BasisCheck:
    """sec.vintages basis check (register amendment 2026-11-25 after review R17).

    A differenced quarter (in practice Q4 = FY - 9M) is not used when the closing fact's filing restates earlier-filed
    values of the line, the base was filed before it, and the base's own filing restated nothing: the 10-K then brings
    a new basis that the 9M is not on (Dell ISG, 10-K 2022-03-24). When the base's filing restated values too, the new
    basis was already in the 10-Qs and the 10-K only carries it back to earlier years (Dell ASC 606, HPE Server FY2025,
    Cisco's yearly reclassifications). The quarter then waits for a pair on one basis (the next 10-K, by sec's pairing).
    """
    restating = restating_filings(facts)

    def ok(closing: sec.Fact, base: sec.Fact) -> bool:
        return not (base.filed < closing.filed and closing.filed in restating and base.filed not in restating)

    return ok


@lru_cache(maxsize=None)
def line_series(line: SegLine) -> tuple[pd.DataFrame, ...]:
    """Release-dated quarterly rows (MUSD) per definition regime, each without gaps."""
    regs = checked_regimes(line.keys[0], line_facts(line), line.breaks, line.detected)
    return tuple(sec.contiguous_tail(sec.vintages([reg], basis_ok=same_basis(reg))) for reg in regs)


# ------------------------------------------------------------------ totals (companyfacts)


def _cf(company: str) -> dict:
    return sec.companyfacts(COMPANIES[company].cik)


def revenue_sources(company: str) -> list[list[sec.Fact]]:
    cf = _cf(company)
    return [sec.facts(cf, tag) for tag in COMPANIES[company].revenue]


def revenue_scope_sources(company: str) -> list[list[sec.Fact]]:
    """Revenue facts of the current scope: restatements > 2% must be declared (scope breaks or revisions), and only
    filings from the last scope break are read."""
    c = COMPANIES[company]
    sources = revenue_sources(company)
    checked_regimes(f"rev_{company}", [f for fs in sources for f in fs],
                    tuple(sorted(c.rev_scope_breaks + c.rev_revisions)))
    if not c.rev_scope_breaks:
        return sources
    first = pd.Timestamp(max(c.rev_scope_breaks))
    return [[f for f in fs if f.filed >= first] for fs in sources]


@lru_cache(maxsize=None)
def revenue_series(company: str) -> pd.DataFrame:
    return sec.contiguous_tail(sec.vintages(revenue_scope_sources(company)))


@lru_cache(maxsize=None)
def quarters(company: str) -> dict[pd.Timestamp, pd.Period]:
    """Fiscal quarter end -> calendar quarter, from the company's revenue facts."""
    return sec_instant.fiscal_quarters(revenue_sources(company))


@lru_cache(maxsize=None)
def inventory_series(company: str) -> pd.DataFrame:
    facts = sec_instant.facts(_cf(company), INVENTORY)
    return sec.contiguous_tail(sec_instant.vintages([facts], quarters(company)))


# ------------------------------------------------------------------ balances: obligations, contract liabilities, RPO


UUPO = "UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount"
UUPO_AXIS = "UnrecordedUnconditionalPurchaseObligationByCategoryOfItemPurchasedAxis"
PCOMMIT = "PurchaseCommitmentRemainingMinimumAmountCommitted"
ANET_RPO = ("RevenueRemainingPerformanceObligationIncludingContractLiabilitiesDeferredRevenueAndOther"
            "PerformanceObligationsAmount")
ANET_PO_SINCE = "2016-02-25"  # first filing whose note states the total non-cancellable purchase commitments
CSCO_PO_SINCE = "2021-05-25"  # first filing of the inventory purchase commitments table in its current tagging
ANET_RPO_SINCE = "2023-02-14"  # first filing of Arista's total RPO tag (the narrower us-gaap RPO before it is left out)
# Arista's 10-Qs of 2025 tag the current total RPO with a context one year early (10-Q 2025-05-07: $3.7 billion "as of
# March 31, 2025" in a 2024-03-31 context). In those filings the fact is re-dated to the filing's own balance date.
ANET_RPO_REDATED = {"2025-05-07": ("2024-03-31", "2025-03-31"), "2025-08-06": ("2024-06-30", "2025-06-30"),
                    "2025-11-05": ("2024-09-30", "2025-09-30")}
# Filings after the ASC 606 adoption (2018-01-01): the three 10-Qs of 2018 tag the balance sheet lines "Deferred revenue"
# and "Deferred revenue, non-current" as DeferredRevenue*, and use ContractWithCustomerLiabilityCurrent for another item
# (10-Q 2018-11-05: 10.9 of contract liabilities in other current liabilities; review R17-1).
ANET_ASC606 = "2018-04-01"
# First ASC 606 quarter-end balance. Modified retrospective adoption: the 2017-12-31 comparative is ASC 605, and the
# 2018-01-01 opening balance is not a quarter end (review R17-3).
ANET_CL_FIRST = "2018-03-31"


def first_per_filing(sources: list[list[sec_instant.Instant]]) -> list[sec_instant.Instant]:
    """One instant per (filing, date): the first source in the priority list that has it."""
    out: dict[tuple, sec_instant.Instant] = {}
    for fs in sources:
        for f in fs:
            out.setdefault((f.accn, f.end), f)
    return sorted(out.values(), key=lambda f: (f.filed, f.end))


def from_filed(facts: list[sec_instant.Instant], first: str) -> list[sec_instant.Instant]:
    t = pd.Timestamp(first)
    return [f for f in facts if f.filed >= t]


def redated(facts: list[sec_instant.Instant], fixes: dict[str, tuple[str, str]]) -> list[sec_instant.Instant]:
    """Instants with the balance date corrected in the listed filings (filed -> (tagged date, true date))."""
    out = []
    for f in facts:
        fix = fixes.get(str(f.filed.date()))
        if fix and f.end == pd.Timestamp(fix[0]):
            f = sec_instant.Instant(pd.Timestamp(fix[1]), f.val, f.filed, f.form, f.accn)
        out.append(f)
    return out


def anet_contract_liabilities(cf: dict) -> list[sec_instant.Instant]:
    """Current + noncurrent contract liabilities from the same filing (ASC 606 basis, balance dates from 2018-03-31).

    Per filing and balance date, DeferredRevenueCurrent/-Noncurrent (filings from ANET_ASC606) come before
    ContractWithCustomerLiabilityCurrent/-Noncurrent: in the 2018 10-Qs the DeferredRevenue* tags are the balance sheet
    lines.
    """
    parts = []
    for new, old in (("ContractWithCustomerLiabilityCurrent", "DeferredRevenueCurrent"),
                     ("ContractWithCustomerLiabilityNoncurrent", "DeferredRevenueNoncurrent")):
        parts.append(first_per_filing([from_filed(sec_instant.facts(cf, old), ANET_ASC606), sec_instant.facts(cf, new)]))
    first = pd.Timestamp(ANET_CL_FIRST)
    return [f for f in sec_custom.summed_instants(parts) if f.end >= first]


@dataclass(frozen=True)
class BalanceSeries:
    key: str
    company: str
    measure: str  # purchase_oblig, deferred_rev, rpo
    tags: str  # Swedish note: tags and members
    source: str = SOURCE
    breaks: tuple[str, ...] = ()  # declared restatements > 2% (filing dates), reviewed


BALANCES = [
    BalanceSeries("purchase_oblig_anet", "anet", "purchase_oblig",
                  f"Tagg: {PCOMMIT} utan dimension ur instanserna, i inlämningar från {ANET_PO_SINCE} ('non-cancellable "
                  "purchase commitments', inte bokförda). Ordalydelsen ändras: 10-K 2016-02-25 och 10-Q 2016-05-05 "
                  "knyter beloppet till 'our contract manufacturers and suppliers', 10-Q 2016-08-05 till 10-Q 2017-11-03 "
                  "anger ett odelat belopp, och från 10-K 2018-02-20 anges totalen och delen till kontraktstillverkare "
                  "och leverantörer var för sig (taggen är totalen; delen var 147,9 av 195,1 MUSD 2017-12-31). Om "
                  "beloppen 2015Q4–2017Q3 är totalen eller delen går inte att avgöra ur texten, och det finns inga "
                  "jämförelsetal att pröva.", SOURCE_INST),
    BalanceSeries("purchase_oblig_csco", "csco", "purchase_oblig",
                  f"Tagg: {UUPO} med {UUPO_AXIS} = InventoriesMember, och samma tagg utan dimension, ur instanserna, i "
                  f"inlämningar från {CSCO_PO_SINCE} ('inventory purchase commitments with contract manufacturers and "
                  "suppliers').", SOURCE_INST),
    BalanceSeries("purchase_oblig_lite", "lite", "purchase_oblig",
                  f"Tagg: {PCOMMIT} utan dimension ur instanserna ('purchase obligations': bindande åtaganden att köpa "
                  "lager och andra åtaganden).", SOURCE_INST),
    BalanceSeries("purchase_oblig_smci", "smci", "purchase_oblig",
                  "Tagg: PurchaseObligation utan dimension ('remaining non-cancelable commitments' för lager och annat, "
                  "inklusive närstående)."),
    BalanceSeries("deferred_rev_anet", "anet", "deferred_rev",
                  "Balansräkningens 'Deferred revenue' + 'Deferred revenue, non-current' ur samma inlämning: "
                  "DeferredRevenueCurrent + DeferredRevenueNoncurrent i 10-Q under 2018 (inlämningar från "
                  f"{ANET_ASC606}), annars ContractWithCustomerLiabilityCurrent + ContractWithCustomerLiabilityNoncurrent. "
                  "I 10-Q 2018-11-05 är ContractWithCustomerLiabilityCurrent en annan post (övriga kortfristiga skulder). "
                  f"Balanser från {ANET_CL_FIRST}, den första ASC 606-balansen vid ett kvartalsslut: Arista bytte "
                  "2018-01-01 med den modifierade retroaktiva metoden, så balansen 2017-12-31 är ASC 605 och ingår inte."),
    BalanceSeries("rpo_anet", "anet", "rpo",
                  f"Egen tagg anet:{ANET_RPO} ur instanserna, från 10-K {ANET_RPO_SINCE}: 'deferred revenue, contract "
                  "liabilities and other performance obligations'. Den smalare us-gaap-taggen före dess ingår inte. "
                  "Tre 10-Q 2025 (2025-05-07, 2025-08-06, 2025-11-05) taggar balansen med ett datum ett år för tidigt; "
                  "den dateras om till inlämningens balansdag.",
                  SOURCE_INST),
    BalanceSeries("rpo_csco", "csco", "rpo", f"Tagg: {RPO} utan dimension."),
    BalanceSeries("rpo_smci", "smci", "rpo", f"Tagg: {RPO} utan dimension."),
    BalanceSeries("rpo_dell", "dell", "rpo", f"Tagg: {RPO} utan dimension."),
    BalanceSeries("rpo_hpe", "hpe", "rpo",
                  f"Tagg: {RPO} utan dimension. Enligt HPE:s egen text är det förutbetalda intäkter (deferred revenue): "
                  "'the aggregate amount of remaining performance obligations, or deferred revenue' (10-K 2022-12-08 "
                  "till 10-Q 2024-03-05) och 'the aggregate amount of deferred revenue' (från 10-Q 2024-06-05). Dells och "
                  "Ciscos RPO är förutbetalda plus ofakturerade belopp, så nivåerna är inte jämförbara. Juniper ingår "
                  "från förvärvet 2025-07-02 (cirka 2,5 mdr USD 2025-10-31 enligt 10-K 2025-12-18)."),
]
BALANCE_BY_KEY = {b.key: b for b in BALANCES}


def balance_sources(key: str) -> list[list[sec_instant.Instant]]:
    """Priority list of instant lists for one balance series."""
    b = BALANCE_BY_KEY[key]
    c = COMPANIES[b.company]
    if key == "purchase_oblig_anet":
        return [list(sec_custom.instant_facts(c.cik, PCOMMIT, ANET_PO_SINCE))]
    if key == "purchase_oblig_csco":
        filings_raw = list(sec_custom._filings(c.cik, CSCO_PO_SINCE, "9999-12-31"))
        return [sec_instant.instance_instants(filings_raw, UUPO, dims((UUPO_AXIS, "InventoriesMember"))),
                sec_instant.instance_instants(filings_raw, UUPO)]
    if key == "purchase_oblig_lite":
        return [list(sec_custom.instant_facts(c.cik, PCOMMIT, c.since))]
    if key == "purchase_oblig_smci":
        return [sec_instant.facts(_cf(b.company), "PurchaseObligation")]
    if key == "deferred_rev_anet":
        return [anet_contract_liabilities(_cf(b.company))]
    if key == "rpo_anet":
        return [redated(list(sec_custom.instant_facts(c.cik, ANET_RPO, ANET_RPO_SINCE)), ANET_RPO_REDATED)]
    if b.measure == "rpo":
        return [sec_instant.facts(_cf(b.company), RPO)]
    raise KeyError(key)


def as_facts(instants: list[sec_instant.Instant]) -> list[sec.Fact]:
    """Instants as zero-length sec.Facts, for sec_segment.definition_breaks."""
    return [sec.Fact(i.end, i.end, i.val, i.filed, i.form, i.accn) for i in instants]


@lru_cache(maxsize=None)
def balance_series(key: str) -> pd.DataFrame:
    b = BALANCE_BY_KEY[key]
    q = quarters(b.company)
    sources = balance_sources(key)
    checked_regimes(key, as_facts([f for fs in sources for f in fs if f.end in q]), b.breaks)
    return sec.contiguous_tail(sec_instant.vintages(sources, q))


# ------------------------------------------------------------------ catalog

QUESTION = ("Hur snabbt växer lagren mellan chip och datacenter (nät, optik och servrar), och var byggs lager och "
            "åtaganden upp?")
CAVEAT = ("Bolaget säljer också till kunder utanför AI och datacenter, så serien är inte AI-intäkter eller AI-efterfrågan.")
SEG_CAVEAT = ("Segment- eller produktintäkter är inte AI-intäkter: raderna innehåller också traditionella servrar, "
              "företagsnät, telekom eller industri.")
LABELS = {
    "purchase_oblig": "Inköpsåtaganden",
    "deferred_rev": "Kontraktsskulder (förutbetalda intäkter)",
    "rpo": "Återstående prestationsåtaganden (RPO)",
}
BALANCE_NOTE = {
    "purchase_oblig": "Utestående åtaganden vid räkenskapskvartalets slut (balans), inte bokförda. ",
    "deferred_rev": "Balans vid räkenskapskvartalets slut: kortfristig + långfristig. ",
    "rpo": "Balans vid räkenskapskvartalets slut (stock), med räkenskapskvartalets kalenderkvartal (som lager). ",
}


def _rows(df: pd.DataFrame) -> pd.DataFrame:
    return df[["period", "value", "known_from"]].copy()


def _company_note(company: str) -> str:
    c = COMPANIES[company]
    note = f" Räkenskapsår: {c.calendar}. CIK {c.cik}."
    if c.max_age_days:
        note += (f" Aktualitet: gräns {c.max_age_days} dagar = största observerade avstånd från kalenderkvartalets slut "
                 "till första egna inlämningen + 92 + 30 (docs/kallor/sec_stack_nat.md).")
    return note


def _spec(key: str, label: str, fetch, company: str, note: str, source: str = SOURCE, closed: bool = False) -> Spec:
    c = COMPANIES[company]
    return Spec(key=key, branch="G6", label=label, unit="MUSD", freq="Q", source=source, fetch=fetch,
                lag_days=c.lag_days, license=LICENSE, revised=True, publish=True, question=QUESTION,
                note=(note + _company_note(company)).strip(),
                max_age_days=None if closed else c.max_age_days, closed=closed)


def _specs() -> list[Spec]:
    specs = []
    for co, c in COMPANIES.items():
        specs.append(_spec(f"rev_{co}", f"Intäkter, {c.name}", lambda co=co: _rows(revenue_series(co)), co,
                           "Totala intäkter. Taggar: " + ", ".join(c.revenue) + ". " + (c.rev_note + " " if c.rev_note
                                                                                         else "") + CAVEAT))
        specs.append(_spec(f"inv_{co}", f"Varulager, {c.name}", lambda co=co: _rows(inventory_series(co)), co,
                           f"Tagg: {INVENTORY} (balansdag = räkenskapskvartalets slut). " + CAVEAT))
    for line in LINES:
        for i, key in enumerate(line.keys):
            superseded = i < len(line.keys) - 1
            closed = superseded or bool(line.discontinued)
            members = "; ".join(" × ".join(f"{a}={m}" for a, m in sorted(w)) for w in line.members)
            note = f"{line.description} Medlemmar: {members}."
            if line.regime_notes:
                note += " " + line.regime_notes[i]
            if superseded:
                note += " Avslutad: ersatt av nästa definition efter ett definitionsbrott."
            elif line.discontinued:
                note += " Avslutad: " + line.discontinued
            specs.append(_spec(key, f"Intäkter, {line.label}", lambda line=line, i=i: _rows(line_series(line)[i]),
                               line.company, note + " " + (line.caveat or SEG_CAVEAT), source=SOURCE_SEG,
                               closed=closed))
    for b in BALANCES:
        c = COMPANIES[b.company]
        specs.append(_spec(b.key, f"{LABELS[b.measure]}, {c.name}", lambda key=b.key: _rows(balance_series(key)),
                           b.company, BALANCE_NOTE[b.measure] + b.tags + " " + CAVEAT, source=b.source))
    return specs


SPECS = _specs()
