"""SEC EDGAR XBRL: depreciation and property & equipment (G5), MSFT, GOOGL, AMZN, META, ORCL and CoreWeave, quarterly.

Follows the money from capex into the P&L: depreciation is where the capex of 2024-2026 lands in 2026-2031, and net PP&E
is the capital base a revenue requirement is computed on (tracks P2b and N7). Catalog series, not core series.

- dep_<co>: the depreciation (and amortization) add-back of the cash-flow statement, as labelled by the company.
- dep_ppe_<co>: depreciation of property and equipment only (no amortization of acquired intangibles), from the PP&E
  note where it is tagged per quarter.
- ppe_net_<co>, ppe_gross_<co>: balances at fiscal quarter end; gross = net + accumulated depreciation from the same
  filing and tag family (gross tags are sometimes subtotals).
- dep_hyp4, dep_ppe_hyp4, ppe_net_hyp4: MSFT + GOOGL + AMZN + META with sec.aggregate (a version exists once all four
  are known; known_from = the latest filing). No ppe_gross_hyp4: Amazon tags gross PP&E only at fiscal year end.
- dep_aws: AWS segment depreciation and amortization (dimensional fact in Amazon's filings, quarterly from 2025).

Release-dated: known_from = 10-Q/10-K filing date, every filing a vintage; YTD differencing, Q4 = FY - 9M and the
calendar mapping are those of ai_tracker.sources.sec, balances those of sec_instant. Restatements of more than 2% are
declared per series after review (`breaks`); an undeclared one stops the fetch (DefinitionBreakError). Tag choices are
pre-registered in docs/mattregister.md (2026-11-24, P1); tags, splices and checks: docs/kallor/sec_avskrivningar.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.series.sec import LICENSE, OCF, REVENUE
from ai_tracker.series.sec_segments import SEG, DefinitionBreakError
from ai_tracker.sources import sec, sec_custom, sec_instant, sec_segment

SOURCE = "SEC EDGAR XBRL companyfacts"
SOURCE_INSTANCE = "SEC EDGAR XBRL instances"
HYP4 = ("msft", "googl", "amzn", "meta")

# Balance-sheet tag families: (net, accumulated depreciation). The family that includes finance-lease right-of-use
# assets in its name comes first; in every overlap the two nets are identical (docs/kallor/sec_avskrivningar.md).
NET_A = "PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization"
ACC_A = "PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAccumulatedDepreciationAndAmortization"
NET_B = "PropertyPlantAndEquipmentNet"
ACC_B = "AccumulatedDepreciationDepletionAndAmortizationPropertyPlantAndEquipment"
FAMILIES = ((NET_A, ACC_A), (NET_B, ACC_B))


@dataclass(frozen=True)
class Custom:
    """Company-specific concepts read from filing instances (companyfacts has only standard taxonomies)."""

    cik: int
    concepts: tuple[str, ...]  # duration: concept priority list; balances: (net, accumulated)
    since: str = "2009-01-01"
    until: str = "9999-12-31"


@dataclass(frozen=True)
class Flow:
    """How one flow series is read.

    `tags` are parts; each part is a companyfacts tag priority list (spliced per quarter by sec.quarters_at). Two or
    more parts are summed per filing and period (each part then has one tag). `custom` replaces the tags.
    """

    tags: tuple[tuple[str, ...], ...] = ()
    custom: Custom | None = None
    first_start: str | None = None  # one definition regime: only facts whose period starts on or after this date
    breaks: tuple[str, ...] = ()  # declared restatements > 2% (filing dates), reviewed
    description: str = ""  # Swedish, for the note


@dataclass(frozen=True)
class Company:
    name: str
    ciks: tuple[int, ...]
    lag_days: int
    max_age_days: int | None
    calendar: str  # Swedish
    dep: Flow
    dep_ppe: Flow
    leases: str  # Swedish: are finance-lease right-of-use assets in PP&E?
    gross: bool = True  # gross and accumulated depreciation tagged every quarter
    custom_balances: tuple[Custom, ...] = ()  # extra (net, accumulated) sources from instances
    balance_breaks: dict = field(default_factory=dict)  # "net"/"gross" -> declared restatements


MSFT, GOOGL, GOOG_INC, AMZN, META, ORCL, CRWV = 789019, 1652044, 1288776, 1018724, 1326801, 1341439, 1769628

COMPANIES: dict[str, Company] = {
    "msft": Company(
        "Microsoft", (MSFT,), 25, None, "räkenskapsår till 30 juni, kvartal = kalenderkvartal",
        dep=Flow(custom=Custom(MSFT, ("DepreciationAmortizationAndOther",)), breaks=("2026-01-28",),
                 description="Raden 'Depreciation, amortization, and other' (egen tagg msft:DepreciationAmortizationAndOther, "
                             "ur varje inlämnings XBRL-instans). Från 10-Q:n 2026-01-28 flyttades belopp ur 'other' till "
                             "förluster på investeringar, och FY2025 räknades om; kvartal till och med 2024Q3 ligger kvar "
                             "på den gamla basen, så serien är ingen ren avskrivningsserie."),
        dep_ppe=Flow(tags=(("Depreciation",),),
                     description="'Depreciation expense' i noten om anläggningstillgångar (us-gaap:Depreciation), per "
                                 "kvartal från FY2025. Taggas avrundat till 0,1 miljard USD."),
        leases="Tillgångar under finansiell leasing ingår i 'Property and equipment' (leasingnoten anger dem som "
               "property and equipment, at cost, och accumulated depreciation)."),
    "googl": Company(
        "Alphabet", (GOOGL, GOOG_INC), 25, None, "kalenderår",
        dep=Flow(tags=(("Depreciation",),), first_start="2021-01-01",
                 description="Raden 'Depreciation of property and equipment' (us-gaap:Depreciation) i definitionen från "
                             "10-K för 2023: utan nedskrivningar, och amortering på immateriella tillgångar ligger i "
                             "'Other'. De äldre egna taggarna (depreciation and impairment, 2014–2022) skarvas inte."),
        dep_ppe=Flow(tags=(("Depreciation",),), first_start="2021-01-01",
                     description="Samma rad och samma värden som dep_googl (kassaflödesraden är bara avskrivningar på "
                                 "anläggningstillgångar)."),
        leases="Från 2019 taggas 'Property and equipment, net' som anläggningstillgångar inklusive nyttjanderätter under "
               "finansiell leasing, med samma värde som PropertyPlantAndEquipmentNet i överlappen.",
        custom_balances=(Custom(GOOGL, ("PropertyPlantandEquipmentandFinanceLeaseRightofUseAssetafterAccumulatedDepreciation"
                                        "andAmortization",
                                        "PropertyPlantandEquipmentandFinanceLeaseRightofUseAssetAccumulatedDepreciation"
                                        "andAmortization"), since="2020-01-01", until="2020-06-30"),)),
    "amzn": Company(
        "Amazon", (AMZN,), 25, None, "kalenderår",
        dep=Flow(tags=(("DepreciationDepletionAndAmortization",),), first_start="2019-01-01", breaks=("2023-04-28",),
                 description="Raden 'Depreciation and amortization of property and equipment and capitalized content "
                             "costs, operating lease assets, and other' (us-gaap:DepreciationDepletionAndAmortization), "
                             "från 2019 då operationella leasingtillgångar kom in (ASC 842, utan omräkning). Innehåller "
                             "aktiverat video- och musikinnehåll. 10-Q:n 2023-04-28 räknade om 2022Q1 med +2,4 %."),
        dep_ppe=Flow(tags=(("Depreciation",),),
                     description="'Depreciation and amortization expense' (us-gaap:Depreciation): avskrivningar på "
                                 "anläggningstillgångar i noten om anläggningstillgångar (helår) och summan av segmenten i "
                                 "segmentnoten (10-Q från 2025, med 2024 som jämförelse). Per kvartal från 2024."),
        leases="Tillgångar under finansiell leasing ingår i 'Property and equipment, net' (taggad som "
               "anläggningstillgångar inklusive nyttjanderätter under finansiell leasing).",
        gross=False),
    "meta": Company(
        "Meta", (META,), 25, None, "kalenderår",
        dep=Flow(tags=(("DepreciationDepletionAndAmortization",),), breaks=("2014-04-25",),
                 description="Raden 'Depreciation and amortization' (us-gaap:DepreciationDepletionAndAmortization). "
                             "10-Q:n 2014-04-25 räknade om 2013Q1 med −3,3 %."),
        dep_ppe=Flow(tags=(("Depreciation",),),
                     description="'Depreciation expense' i noten om anläggningstillgångar (us-gaap:Depreciation), per "
                                 "kvartal från 2019."),
        leases="Från 2019 taggas 'Property and equipment, net' som anläggningstillgångar inklusive nyttjanderätter under "
               "finansiell leasing."),
    "orcl": Company(
        "Oracle", (ORCL,), -31, -3 + 92 + 30,
        "räkenskapsår till 31 maj, kvartal slutar aug/nov/feb/maj: sep–nov räknas som Q4 och lämnas in före "
        "kalenderkvartalets slut, därför lag_days = -31 (som rev_orcl)",
        dep=Flow(tags=(("Depreciation",), ("AmortizationOfIntangibleAssets",)),
                 description="Summan av raderna 'Depreciation' och 'Amortization of intangible assets' "
                             "(us-gaap:Depreciation + us-gaap:AmortizationOfIntangibleAssets) ur samma inlämning."),
        dep_ppe=Flow(tags=(("Depreciation",),), description="Raden 'Depreciation' (us-gaap:Depreciation)."),
        leases="Nyttjanderätter under finansiell leasing ingår i 'Property, plant and equipment, net' (10-K 2026-06-22: "
               "FinanceLeaseRightOfUseAssetStatementOfFinancialPositionExtensibleList = PropertyPlantAndEquipmentNet).",
        gross=False),
    "crwv": Company(
        "CoreWeave", (CRWV,), 45, 61 + 92 + 30, "kalenderår; 10-Q 38–45 dagar och 10-K 61 dagar efter kvartalet",
        dep=Flow(tags=(("DepreciationDepletionAndAmortization",),),
                 description="Raden 'Depreciation and amortization' (us-gaap:DepreciationDepletionAndAmortization)."),
        dep_ppe=Flow(tags=(("Depreciation",),),
                     description="'Depreciation' i noten om anläggningstillgångar (us-gaap:Depreciation). Taggas "
                                 "avrundat till 0,1 miljard USD och kan därför ligga över dep_crwv."),
        leases="'Property and equipment, net' har samma värde som taggen för anläggningstillgångar inklusive "
               "nyttjanderätter under finansiell leasing, alltså ingår finansiell leasing."),
}

AWS_CONCEPTS = ("Depreciation", "DepreciationDepletionAndAmortization")
AWS_MEMBERS = ((SEG, "AmazonWebServicesSegmentMember"),)
AWS_SINCE = "2015-01-01"
AWS_BREAKS: tuple[str, ...] = ()


# ------------------------------------------------------------------ facts


def _cf(cik: int) -> dict:
    return sec.companyfacts(cik)


def flow_sources(company: str, flow: Flow) -> list[list[sec.Fact]]:
    """Priority list of fact lists (one per tag), or one summed list, for a flow."""
    c = COMPANIES[company]
    if flow.custom is not None:
        cu = flow.custom
        sources = [list(sec_custom.duration_facts(cu.cik, cu.concepts, cu.since, cu.until))]
    elif len(flow.tags) == 1:
        sources = [[f for cik in c.ciks for f in sec.facts(_cf(cik), tag)] for tag in flow.tags[0]]
    else:
        if any(len(part) != 1 for part in flow.tags):
            raise ValueError("summed parts take one tag each")
        sources = [sec_custom.summed([[f for cik in c.ciks for f in sec.facts(_cf(cik), part[0])]
                                      for part in flow.tags])]
    if flow.first_start:
        sources = [sec_custom.starting_from(fs, flow.first_start) for fs in sources]
    return sources


def _as_facts(instants: list[sec_instant.Instant]) -> list[sec.Fact]:
    """Instants as zero-length sec.Facts, for sec_segment.definition_breaks."""
    return [sec.Fact(i.end, i.end, i.val, i.filed, i.form, i.accn) for i in instants]


def checked(name: str, facts: list[sec.Fact], declared: tuple[str, ...]) -> None:
    """Raise DefinitionBreakError if the restatements > 2% found differ from the declared ones."""
    found = [str(d.date()) for d in sec_segment.definition_breaks(facts)]
    if found != list(declared):
        raise DefinitionBreakError(f"{name}: detected restatements > 2% at {found}, declared {list(declared)}; "
                                   "review and declare (docs/kallor/sec_avskrivningar.md)")


def balance_sources(company: str, part: str) -> list[list[sec_instant.Instant]]:
    """Priority list of instant lists for 'net' or 'gross' (= net + accumulated, same filing and family)."""
    c = COMPANIES[company]
    out = []
    for net, acc in FAMILIES:
        nets = [f for cik in c.ciks for f in sec_instant.facts(_cf(cik), net)]
        if part == "net":
            out.append(nets)
        else:
            accs = [f for cik in c.ciks for f in sec_instant.facts(_cf(cik), acc)]
            out.append(sec_custom.summed_instants([nets, accs]))
    for cu in c.custom_balances:
        nets = list(sec_custom.instant_facts(cu.cik, cu.concepts[0], cu.since, cu.until))
        if part == "net":
            out.append(nets)
        else:
            accs = list(sec_custom.instant_facts(cu.cik, cu.concepts[1], cu.since, cu.until))
            out.append(sec_custom.summed_instants([nets, accs]))
    return out


@lru_cache(maxsize=None)
def fiscal_quarters(company: str) -> dict[pd.Timestamp, pd.Period]:
    """Fiscal quarter end -> calendar quarter, from the company's operating cash flow and revenue facts."""
    c = COMPANIES[company]
    flows = [[f for cik in c.ciks for f in sec.facts(_cf(cik), tag)] for tag in (*OCF, *REVENUE)]
    return sec_instant.fiscal_quarters(flows)


# ------------------------------------------------------------------ series


@lru_cache(maxsize=None)
def flow_series(measure: str, company: str) -> pd.DataFrame:
    """Release-dated quarterly rows (MUSD) of dep or dep_ppe for one company, without gaps."""
    flow = getattr(COMPANIES[company], measure)
    sources = flow_sources(company, flow)
    checked(f"{measure}_{company}", [f for fs in sources for f in fs], flow.breaks)
    return sec.contiguous_tail(sec.vintages(sources))


@lru_cache(maxsize=None)
def balance_series(part: str, company: str) -> pd.DataFrame:
    """Release-dated quarterly balances (MUSD) at fiscal quarter end, 'net' or 'gross', without gaps."""
    c = COMPANIES[company]
    sources = balance_sources(company, part)
    quarters = fiscal_quarters(company)
    checked(f"ppe_{part}_{company}", _as_facts([f for fs in sources for f in fs if f.end in quarters]),
            c.balance_breaks.get(part, ()))
    return sec.contiguous_tail(sec_instant.vintages(sources, quarters))


@lru_cache(maxsize=None)
def aws_series() -> pd.DataFrame:
    facts = sec_segment.member_facts((AMZN,), AWS_SINCE, AWS_CONCEPTS, AWS_MEMBERS)
    checked("dep_aws", facts, AWS_BREAKS)
    return sec.contiguous_tail(sec.vintages([facts]))


def company_series(measure: str, company: str) -> pd.DataFrame:
    if measure in ("dep", "dep_ppe"):
        return flow_series(measure, company)
    return balance_series(measure.removeprefix("ppe_"), company)


@lru_cache(maxsize=None)
def hyp4_series(measure: str) -> pd.DataFrame:
    return sec.contiguous_tail(sec.aggregate({c: company_series(measure, c) for c in HYP4}))


# ------------------------------------------------------------------ catalog


def _fetch(measure: str, company: str | None):
    def fetch() -> pd.DataFrame:
        if measure == "dep_aws":
            df = aws_series()
        elif company is None:
            df = hyp4_series(measure)
        else:
            df = company_series(measure, company)
        return df[["period", "value", "known_from"]].copy()

    return fetch


LABELS = {
    "dep": ("Avskrivningar enligt kassaflödesanalysen",
            "Hur snabbt växer avskrivningarna, där capex 2024–2026 hamnar i resultatet?"),
    "dep_ppe": ("Avskrivningar på anläggningstillgångar",
                "Hur snabbt växer avskrivningarna på den fysiska kapaciteten, utan förvärvade immateriella tillgångar?"),
    "ppe_net": ("Anläggningstillgångar, netto",
                "Hur stor är den investerade kapitalbasen som avskrivningar och avkastningskrav räknas på?"),
    "ppe_gross": ("Anläggningstillgångar, brutto",
                  "Hur stor är anläggningsstocken före avskrivningar, och hur stor del är redan avskriven?"),
}
CAVEAT = ("Omfattar alla anläggningstillgångar (kontor, lager, nät, datacenter), inte bara AI-servrar. "
          "Nyttjandeperioden är ett redovisningsval.")


def _spec(measure: str, company: str | None) -> Spec:
    label, question = LABELS[measure]
    balance = measure.startswith("ppe_")
    if company is None:
        key, who, lag, max_age, source = f"{measure}_hyp4", "MSFT+GOOGL+AMZN+META", 25, None, SOURCE
        note = ("Summa av fyra bolag per kalenderkvartal; en version finns först när alla fyra har lämnat in, "
                "known_from = senaste inlämningen. Bolagens definitioner skiljer sig (se bolagsserierna).")
    else:
        c = COMPANIES[company]
        key, who, lag, max_age = f"{measure}_{company}", c.name, c.lag_days, c.max_age_days
        if balance:
            note = ("Balans vid räkenskapskvartalets slut. "
                    + ("Netto: " + ", ".join(f for f, _ in FAMILIES) if measure == "ppe_net" else
                       "Brutto = netto + ackumulerade avskrivningar ur samma inlämning ("
                       + "; ".join(f"{n} + {a}" for n, a in FAMILIES) + ")")
                    + ". " + c.leases)
            source = SOURCE_INSTANCE if c.custom_balances else SOURCE
        else:
            flow = getattr(c, measure)
            note = flow.description
            source = SOURCE_INSTANCE if flow.custom else SOURCE
        note += f" Räkenskapsår: {c.calendar}. CIK {', '.join(map(str, c.ciks))}."
        if max_age is not None:
            note += (f" Aktualitet: gräns {max_age} dagar = största observerade avstånd från kalenderkvartalets slut "
                     "till första inlämningen + 92 + 30 (som neoclouds).")
    note += " " + CAVEAT
    return Spec(key=key, branch="G5", label=f"{label}, {who}", unit="MUSD", freq="Q", source=source,
                fetch=_fetch(measure, company), lag_days=lag, license=LICENSE, revised=True, publish=True,
                question=question, note=note.strip(), max_age_days=max_age)


def _aws_spec() -> Spec:
    return Spec(key="dep_aws", branch="G5", label="Avskrivningar, AWS-segmentet (Amazon)", unit="MUSD", freq="Q",
                source="SEC EDGAR XBRL instances (segment dimensions)", fetch=_fetch("dep_aws", None), lag_days=25,
                license=LICENSE, revised=True, publish=True,
                question="Hur snabbt växer avskrivningarna i AWS, där Amazons molnkapacitet finns?",
                note=("Segmentets 'Depreciation and amortization expense' (us-gaap:Depreciation, äldre "
                      "DepreciationDepletionAndAmortization, med StatementBusinessSegmentsAxis = "
                      "AmazonWebServicesSegmentMember). Per kvartal i 10-Q från 2025-05 (2025Q1 med 2024 som "
                      "jämförelse), tidigare bara helår. " + CAVEAT))


MEASURES = ("dep", "dep_ppe", "ppe_net", "ppe_gross")
SPECS = ([_spec(m, c) for c in COMPANIES for m in MEASURES if m != "ppe_gross" or COMPANIES[c].gross]
         + [_spec(m, None) for m in ("dep", "dep_ppe", "ppe_net")]
         + [_aws_spec()])
