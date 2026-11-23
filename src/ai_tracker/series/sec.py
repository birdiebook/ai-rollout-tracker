"""SEC EDGAR XBRL (companyfacts): hyperscaler capex, finance leases, operating cash flow, revenue.

Release-dated: every value carries the `filed` date of the filing(s) it was computed from, and later
restatements are new vintages. Quarterly logic (YTD differencing, Q4 = FY - 9M, calendar mapping) is in
ai_tracker.sources.sec. Tags per company were checked against companyfacts on 2026-11-23; tag choices,
splices and known issues are documented in docs/kallor/sec.md.
"""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.sources import sec

# Google Inc. (CIK 1288776) is Alphabet's predecessor; its filings carry the pre-2015 history.
COMPANIES = {
    "msft": ("Microsoft", (789019,)),
    "googl": ("Alphabet", (1652044, 1288776)),
    "amzn": ("Amazon", (1018724,)),
    "meta": ("Meta", (1326801,)),
    "nvda": ("Nvidia", (1045810,)),
}
HYP4 = ("msft", "googl", "amzn", "meta")

REVENUE = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"]
OCF = ["NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"]

# Tags per measure and company, in priority order (first tag with a value for a quarter wins).
TAGS: dict[str, dict[str, list[str]]] = {
    # Gross cash purchases of property and equipment as tagged in the cash-flow statement.
    # Amazon: only the gross tag (from 2017Q3). Its older tags are net of proceeds and incentives
    # (PaymentsToAcquirePropertyPlantAndEquipment to 2017Q1; PaymentsForProceedsFromProductiveAssets
    # switched from net to gross in 2018 under the same tag), so they are not spliced on.
    "capex": {
        "msft": ["PaymentsToAcquirePropertyPlantAndEquipment"],
        "googl": ["PaymentsToAcquirePropertyPlantAndEquipment"],
        "amzn": ["PaymentsToAcquireProductiveAssets"],
        "meta": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    },
    # Principal repayments of finance (before ASC 842: capital) leases.
    "fin_lease": {
        "msft": ["FinanceLeasePrincipalPayments"],
        "googl": ["FinanceLeasePrincipalPayments"],
        "amzn": ["FinanceLeasePrincipalPayments", "RepaymentsOfLongTermCapitalLeaseObligations"],
        "meta": ["FinanceLeasePrincipalPayments", "RepaymentsOfLongTermCapitalLeaseObligations"],
    },
    "ocf": {c: OCF for c in HYP4},
    "rev": {c: REVENUE for c in COMPANIES},
}

LABELS = {
    "capex": ("Capex (köp av anläggningstillgångar)", "Vilken investeringstakt i AI-infrastruktur syns i kassaflödet?"),
    "fin_lease": ("Amortering på finansiell leasing", "Hur mycket kapacitet finansieras via leasing i stället för capex?"),
    "ocf": ("Operativt kassaflöde", "Hur stor del av kassaflödet tar investeringarna?"),
    "rev": ("Intäkter", "Hur utvecklas intäkterna mot investeringarna?"),
}
BRANCH = {"capex": "G5", "fin_lease": "G5", "ocf": "G5", "rev": "G4"}
# NVDA's fiscal quarter ends ~4 weeks after the calendar quarter it maps to: first filing 45-77 days after
# the calendar quarter end (10-K up to mid-March), so the derived bound (25 + 92 + 30) is too tight.
NVDA_MAX_AGE_DAYS = 77 + 92 + 30

LICENSE = ("public: 'Information presented on sec.gov is considered public information and may be copied "
           "or further distributed by users of the web site without the SEC's permission' (sec.gov/privacy, "
           "checked 2026-11-23)")
SOURCE = "SEC EDGAR XBRL companyfacts"


@lru_cache(maxsize=None)
def company_series(measure: str, company: str) -> pd.DataFrame:
    """Release-dated quarterly rows (MUSD) for one measure and company, without gaps."""
    ciks = COMPANIES[company][1]
    sources = [[f for cik in ciks for f in sec.facts(sec.companyfacts(cik), tag)] for tag in TAGS[measure][company]]
    return sec.contiguous_tail(sec.vintages(sources))


@lru_cache(maxsize=None)
def hyp4_series(measure: str) -> pd.DataFrame:
    return sec.contiguous_tail(sec.aggregate({c: company_series(measure, c) for c in HYP4}))


def _fetch(measure: str, company: str | None):
    def fetch() -> pd.DataFrame:
        df = hyp4_series(measure) if company is None else company_series(measure, company)
        return df[["period", "value", "known_from"]].copy()

    return fetch


def _spec(measure: str, company: str | None) -> Spec:
    label, question = LABELS[measure]
    if company is None:
        key, who = f"{measure}_hyp4", "MSFT+GOOGL+AMZN+META"
        note = "Summa av fyra bolag; en version finns först när alla fyra har lämnat in. known_from = senaste inlämningen."
    else:
        key, who = f"{measure}_{company}", COMPANIES[company][0]
        note = "Taggar: " + ", ".join(TAGS[measure][company])
    max_age = None
    if company == "nvda":
        max_age = NVDA_MAX_AGE_DAYS
        note += (". Aktualitet: NVDA:s kvartal slutar sista veckan i jan/apr/jul/okt, så rapporten kommer 45–77 "
                 f"dagar efter kalenderkvartalets slut (2009–2026); gräns 77 + 92 + 30 = {NVDA_MAX_AGE_DAYS} dagar.")
    return Spec(key=key, branch=BRANCH[measure], label=f"{label}, {who}", unit="MUSD", freq="Q", source=SOURCE,
                fetch=_fetch(measure, company), lag_days=25, license=LICENSE, revised=True, publish=True,
                question=question, note=note, max_age_days=max_age)


SPECS = ([_spec(m, c) for m in ("capex", "fin_lease", "ocf") for c in HYP4]
         + [_spec(m, None) for m in ("capex", "fin_lease", "ocf")]
         + [_spec("rev", c) for c in COMPANIES])
