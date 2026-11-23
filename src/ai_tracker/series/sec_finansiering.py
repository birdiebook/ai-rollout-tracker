"""SEC EDGAR XBRL (companyfacts): financing of the build-out (lead L5) for MSFT, GOOGL, AMZN, META, ORCL, CRWV.

Flows (cash-flow and income statement, YTD-differenced like capex): proceeds from issuance of long-term debt,
repayments of debt, interest expense. Stocks (balance sheet at the fiscal quarter end): long-term debt including
the current portion, finance-lease liabilities, operating-lease liabilities, cash and marketable securities.
`*_hyp4` = MSFT + GOOGL + AMZN + META, a version only once all four have filed (as in series/sec.py).

Release-dated: known_from = the EDGAR filing date of the filing(s) a value is computed from; restatements are
later versions. Tags per company and measure were checked against companyfacts on 2026-11-23, see
docs/kallor/finansiering.md. Leases signed but not yet commenced (text, agent-extracted) are in
series/lease_commitments.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.series import sec as sec_series
from ai_tracker.sources import sec
from ai_tracker.sources import sec_financing as sf

COMPANIES = {
    "msft": ("Microsoft", (789019,)),
    "googl": ("Alphabet", (1652044, 1288776)),
    "amzn": ("Amazon", (1018724,)),
    "meta": ("Meta", (1326801,)),
    "orcl": ("Oracle", (1341439,)),
    "crwv": ("CoreWeave", (1769628,)),
}
HYP4 = ("msft", "googl", "amzn", "meta")
# Oracle's fiscal quarters end in Aug/Nov/Feb/May and are filed ~10-20 days later, before the end of the
# calendar quarter they map to (midpoint rule); -31 allows that in the known_from_after_period_end check.
LAG = {"orcl": -31}

# Concept patterns for the zero fill (sources/sec_financing.zero_facts): a filing is filled with 0 only if its
# instance has no concept matching `pattern` (minus `exclude`), so a company-specific tag blocks the fill.
DEBT_NAMES = r"(Debt|Notes|Borrowing|Loan|Credit)"
ISSUE_PATTERN = r"^Proceeds\w*" + DEBT_NAMES
REPAY_PATTERN = r"^(Repayments\w*|ProceedsFromRepaymentsOf\w*)" + DEBT_NAMES
ZERO_EXCLUDE = r"Short|CommercialPaper|ThreeMonthsOrLess|Receivable|AvailableForSale|Investment|Deposit|Lease"


@dataclass(frozen=True)
class Flow:
    tags: dict[str, tuple[str, ...]]  # company -> tag priority list
    zero: tuple[str, str] | None = None  # (pattern, exclude) for the zero fill, None = no zero fill
    derive_q1: bool = False  # add Q1 = 6M YTD - Q2 3-month (same filing)


@dataclass(frozen=True)
class Stock:
    # company -> formulas (fallback order); formula = components summed; component = tag priority list
    formulas: dict[str, tuple[tuple[tuple[str, ...], ...], ...]]


def _total_or_parts(total: str, current: str, noncurrent: str):
    return (((total,),), ((current,), (noncurrent,)))


OP_LEASE = _total_or_parts("OperatingLeaseLiability", "OperatingLeaseLiabilityCurrent",
                           "OperatingLeaseLiabilityNoncurrent")
FIN_LEASE = _total_or_parts("FinanceLeaseLiability", "FinanceLeaseLiabilityCurrent", "FinanceLeaseLiabilityNoncurrent")
LTD_PARTS = (("LongTermDebtNoncurrent",), ("LongTermDebtCurrent",))
CASH = ("CashAndCashEquivalentsAtCarryingValue",)

MEASURES: dict[str, Flow | Stock] = {
    "debt_issued": Flow({
        "msft": ("ProceedsFromDebtMaturingInMoreThanThreeMonths",),
        "googl": ("ProceedsFromDebtNetOfIssuanceCosts",),
        "amzn": ("ProceedsFromIssuanceOfLongTermDebt",),
        "meta": ("ProceedsFromIssuanceOfLongTermDebt", "ProceedsFromDebtNetOfIssuanceCosts"),
        # Oracle switches tags between filings; term-loan draws were tagged as lines of credit in FY2025 Q1
        "orcl": ("ProceedsFromIssuanceOfSeniorLongTermDebt", "ProceedsFromIssuanceOfLongTermDebt",
                 "ProceedsFromLongTermLinesOfCredit", "ProceedsFromIssuanceOfDebt", "ProceedsFromDebtNetOfIssuanceCosts"),
        "crwv": ("ProceedsFromIssuanceOfLongTermDebt",),
    }, zero=(ISSUE_PATTERN, ZERO_EXCLUDE)),
    "debt_repaid": Flow({
        "msft": ("RepaymentsOfDebtMaturingInMoreThanThreeMonths",),
        "googl": ("RepaymentsOfDebtAndCapitalLeaseObligations", "RepaymentsOfDebt"),
        "amzn": ("RepaymentsOfLongTermDebt", "RepaymentsOfDebt"),
        "meta": ("RepaymentsOfLongTermDebt",),
        "orcl": ("RepaymentsOfDebt", "RepaymentsOfLongTermDebt"),
        "crwv": ("RepaymentsOfLongTermDebt",),
    }, zero=(REPAY_PATTERN, ZERO_EXCLUDE)),
    "interest_exp": Flow({
        "msft": ("InterestExpenseNonoperating", "InterestExpense"),
        "googl": ("InterestExpenseNonoperating", "InterestExpense"),
        "amzn": ("InterestExpenseNonoperating", "InterestExpense"),
        "meta": ("InterestExpenseDebt", "InterestExpenseNonoperating", "InterestExpense"),
        "orcl": ("InterestExpense",),
        "crwv": ("InterestExpenseDebt",),
    }, derive_q1=True),
    "lt_debt": Stock({
        "msft": (LTD_PARTS, (("LongTermDebt",),)),
        "googl": (LTD_PARTS,),
        "amzn": (LTD_PARTS,),
        # Meta had no current maturities until 2026Q3: noncurrent alone when the current portion is not tagged
        "meta": (LTD_PARTS, (("LongTermDebtNoncurrent",),)),
        "orcl": ((("LongTermNotesAndLoans",), ("NotesPayableCurrent",)),),
        "crwv": ((("DebtInstrumentCarryingAmount",),),),
    }),
    "fin_lease_liab": Stock({
        "msft": ((("FinanceLeaseLiability",),),),
        "googl": FIN_LEASE, "amzn": FIN_LEASE, "orcl": FIN_LEASE, "crwv": FIN_LEASE,
        "meta": FIN_LEASE,  # 10-K only: published as the annual series fin_lease_liab_meta_a
    }),
    "op_lease_liab": Stock({c: OP_LEASE for c in COMPANIES}),
    "cash_sec": Stock({
        "msft": ((("CashCashEquivalentsAndShortTermInvestments",),),),
        "googl": ((("CashCashEquivalentsAndShortTermInvestments",),), (CASH, ("MarketableSecuritiesCurrent",))),
        "amzn": ((CASH, ("MarketableSecuritiesCurrent",)),),
        "meta": ((CASH, ("MarketableSecuritiesCurrent", "AvailableForSaleSecuritiesDebtSecuritiesCurrent")),),
        "orcl": ((CASH, ("AvailableForSaleSecuritiesDebtSecuritiesCurrent",)),),
        "crwv": ((CASH, ("MarketableSecuritiesCurrent",)),),
    }),
}
HYP4_MEASURES = ("debt_issued", "debt_repaid", "lt_debt", "interest_exp", "op_lease_liab", "cash_sec")
QUARTERLY = {m: [c for c in COMPANIES if not (m == "fin_lease_liab" and c == "meta")] for m in MEASURES}

LABELS = {
    "debt_issued": ("Emission av långfristig skuld (likvid)", "Hur mycket nytt lån tar bolagen upp för utbyggnaden?"),
    "debt_repaid": ("Amortering av skuld (likvid)", "Hur mycket av den gamla skulden betalas tillbaka?"),
    "interest_exp": ("Räntekostnad", "Vad kostar skuldfinansieringen?"),
    "lt_debt": ("Långfristig skuld inkl. kortfristig del (balans)", "Hur stor är skulden som bär utbyggnaden?"),
    "fin_lease_liab": ("Skuld för finansiell leasing (balans)", "Hur mycket kapacitet finansieras via finansiell leasing?"),
    "op_lease_liab": ("Skuld för operationell leasing (balans)", "Hur mycket hyrd kapacitet (datacenter) ligger i balansen?"),
    "cash_sec": ("Likvida medel och kortfristiga placeringar (balans)", "Hur stor är kassan som kan bära investeringarna?"),
}
# what is not obvious from the tag names (Swedish, for the catalog note)
NOTES = {
    ("debt_issued", "googl"): "Alphabets rad 'Proceeds from issuance of debt' omfattar även annan upplåning än obligationer.",
    ("debt_repaid", "googl"): "Alphabets rad 'Repayments of debt' omfattar även annan upplåning; före 2024 troligen också "
                              "amortering på finansiell leasing (ej verifierat).",
    ("lt_debt", "googl"): "Bokfört värde, obligationer. 2020–2024 taggade Alphabet balansraden inkl. finansiell leasing "
                          "(annan tagg); serien börjar därför 2024Q4.",
    ("lt_debt", "orcl"): "Notes payable and other borrowings, kortfristiga + långfristiga (inkl. företagscertifikat).",
    ("lt_debt", "crwv"): "DebtInstrumentCarryingAmount (nominellt utestående), ~1 % över bokfört värde; balansraderna "
                         "taggas med egna taggar från 2026Q2.",
    ("lt_debt", "meta"): "Långfristig del ensam när kortfristig del saknas (Meta hade inga förfall inom ett år före 2026Q3).",
    ("interest_exp", "meta"): "Meta redovisar räntekostnaden bara i vissa 10-Q; Q1 härleds som 6M − Q2 ur samma rapport.",
    ("cash_sec", "orcl"): "Likvida medel + marketable securities (AFS, kortfristiga).",
}


@lru_cache(maxsize=None)
def _cfs(company: str) -> tuple[tuple[int, dict], ...]:
    return tuple((cik, sec.companyfacts(cik)) for cik in COMPANIES[company][1])


@lru_cache(maxsize=None)
def _report_dates(company: str) -> frozenset:
    return frozenset().union(*(sf.report_dates(cf) for _, cf in _cfs(company)))


REFUSED: dict[tuple[str, str], list[str]] = {}  # (measure, company) -> filings the zero fill refused (gap left)


@lru_cache(maxsize=None)
def flow_sources(measure: str, company: str) -> tuple[tuple[sec.Fact, ...], ...]:
    m = MEASURES[measure]
    tags = list(m.tags[company])
    sources = [[f for _, cf in _cfs(company) for f in sec.facts(cf, t)] for t in tags]
    if m.derive_q1:
        sources += [sf.derived_first_quarters(fs) for fs in sources]
    if m.zero:
        zeros, refused = [], []
        for cik, cf in _cfs(company):
            z, r = sf.zero_facts(cik, cf, tags, *m.zero)
            zeros += z
            refused += r
        REFUSED[(measure, company)] = refused
        sources.append(zeros)
    return tuple(tuple(s) for s in sources if s)


def _stock_frame(formula, company: str) -> pd.DataFrame:
    parts = []
    for component in formula:
        srcs = [[f for _, cf in _cfs(company) for f in sf.instant_facts(cf, t)] for t in component]
        parts.append(sf.stock_vintages(srcs, set(_report_dates(company))))
    if any(p.empty for p in parts):
        return pd.DataFrame(columns=["period", "value", "known_from"])
    return sf.sum_frames(parts)


@lru_cache(maxsize=None)
def company_series(measure: str, company: str) -> pd.DataFrame:
    """Release-dated quarterly rows (MUSD) for one measure and company, without gaps."""
    m = MEASURES[measure]
    if isinstance(m, Flow):
        df = sec.vintages([list(s) for s in flow_sources(measure, company)])
    else:
        df = sf.first_available([_stock_frame(f, company) for f in m.formulas[company]])
    return sec.contiguous_tail(df[["period", "value", "known_from"]].reset_index(drop=True))


@lru_cache(maxsize=None)
def hyp4_series(measure: str) -> pd.DataFrame:
    return sec.contiguous_tail(sec.aggregate({c: company_series(measure, c) for c in HYP4}))


@lru_cache(maxsize=None)
def annual_q4(measure: str, company: str) -> pd.DataFrame:
    """Year-end balances only (calendar Q4), as annual rows: for a company that discloses a balance only in 10-Ks."""
    df = sf.first_available([_stock_frame(f, company) for f in MEASURES[measure].formulas[company]])
    df = df[df["period"].str.endswith("Q4")].copy()
    df["period"] = df["period"].str[:4]
    years = sorted(set(df["period"]))
    gaps = [i for i in range(1, len(years)) if int(years[i]) != int(years[i - 1]) + 1]
    if gaps:
        df = df[df["period"] >= years[gaps[-1]]]
    return df.reset_index(drop=True)


def _fetch(fn, *args):
    def fetch() -> pd.DataFrame:
        return fn(*args)[["period", "value", "known_from"]].copy()

    return fetch


def _describe(measure: str, company: str) -> str:
    m = MEASURES[measure]
    if isinstance(m, Flow):
        text = "Taggar: " + ", ".join(m.tags[company])
        if m.zero:
            text += ". Rapport utan raden (kontrollerat i XBRL-instansen) = 0"
        if m.derive_q1:
            text += ". Q1 = 6M − Q2 där kvartalet saknas"
    else:
        text = "Formel: " + " | ".join(" + ".join("/".join(c) for c in f) for f in m.formulas[company])
    extra = NOTES.get((measure, company))
    return text + (". " + extra if extra else "")


def _spec(measure: str, company: str | None) -> Spec:
    label, question = LABELS[measure]
    if company is None:
        key, who = f"{measure}_hyp4", "MSFT+GOOGL+AMZN+META"
        note = "Summa av fyra bolag; en version finns först när alla fyra har lämnat in. known_from = senaste inlämningen."
        fetch = _fetch(hyp4_series, measure)
    else:
        key, who = f"{measure}_{company}", COMPANIES[company][0]
        note = _describe(measure, company)
        fetch = _fetch(company_series, measure, company)
    return Spec(key=key, branch="G5", label=f"{label}, {who}", unit="MUSD", freq="Q", source=sec_series.SOURCE,
                fetch=fetch, lag_days=LAG.get(company, 25), license=sec_series.LICENSE, revised=True, publish=True,
                question=question, note=note)


SPECS = ([_spec(m, c) for m in MEASURES for c in QUARTERLY[m]]
         + [_spec(m, None) for m in HYP4_MEASURES]
         + [Spec(key="fin_lease_liab_meta_a", branch="G5", label=f"{LABELS['fin_lease_liab'][0]}, Meta (årsskifte)",
                 unit="MUSD", freq="A", source=sec_series.SOURCE, fetch=_fetch(annual_q4, "fin_lease_liab", "meta"),
                 lag_days=25, license=sec_series.LICENSE, revised=True, publish=True,
                 question=LABELS["fin_lease_liab"][1],
                 note=_describe("fin_lease_liab", "meta") + ". Meta redovisar skulden bara i 10-K, därför årsserie "
                      "(balans 31 december).")])
