"""Leases signed but not yet commenced, per company: agent-extracted from 10-Q/10-K lease notes.

Source: curated/lease_commitments.csv (sources/lease_commitments.py, docs/kallor/finansiering.md). One value per
filing (the total; parts summed), dated by the filing date. Reviewed by R5 and corrected (X3, 2026-11-24):
publish=True (numbers with source references only, never text).

A definition break starts a new series: from the balance date in BREAKS the company's amount covers more than before,
so the earlier series is closed and a new key (lease_uncommenced_<company>_<suffix>) continues it.
"""

from __future__ import annotations

import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.sources import lease_commitments as lc
from ai_tracker.sources import sec

NAMES = {"msft": "Microsoft", "googl": "Alphabet", "amzn": "Amazon", "meta": "Meta", "orcl": "Oracle",
         "crwv": "CoreWeave"}
LAG = {"orcl": -31}  # Oracle files ~10-20 days after its quarter end, before the mapped calendar quarter ends
DEFINITION = {
    "msft": "operationell + finansiell leasing (en summa från FY2025 Q4); till och med 2026-03-31",
    "googl": "framtida leasingbetalningar, odiskonterade (10-K: kort- + långfristiga)",
    "amzn": "totalkolumnen i raden 'Leases not yet commenced' i åtagandetabellen; från 2020Q4",
    "meta": "operationell + finansiell leasing; 2024Q1–Q3 bara operationell",
    "orcl": "ytterligare leasingåtaganden; före FY2025 bara operationell, i 10-Q nov 2022–nov 2024 ur MD&A; "
            "serien börjar 2023Q4 (10-Q:n för aug 2023 anger inget belopp)",
    "crwv": "summa framtida odiskonterade leasingbetalningar",
}
# company -> (first balance date of the new definition, key suffix, Swedish definition, reason the old one closed)
BREAKS = {
    "msft": ("2026-06-30", "cond",
             "som tidigare, men från 2026-06-30 ingår avtal som gäller först när vissa avtalsvillkor är uppfyllda "
             "('subject to certain contractual conditions being met')",
             "Microsoft breddade beloppet 2026-06-30 (villkorade avtal ingår); fortsätter som "
             "lease_uncommenced_msft_cond"),
}


def _rows(company: str, part: str) -> pd.DataFrame:
    df = lc.load()
    if company in BREAKS:
        start = BREAKS[company][0]
        df = df[(df["company"] != company) | ((df["period"] >= start) == (part == "new"))]
    return df


def frame(company: str, part: str = "old") -> pd.DataFrame:
    if not lc.PATH.exists():
        return pd.DataFrame(columns=["period", "value", "known_from"])
    return sec.contiguous_tail(lc.series_frame(_rows(company, part), company))


def _spec(company: str, part: str = "old") -> Spec:
    new = part == "new"
    brk = BREAKS.get(company)
    key = f"lease_uncommenced_{company}" + (f"_{brk[1]}" if new else "")
    definition = brk[2] if new else DEFINITION[company]
    closed = bool(brk) and not new
    return Spec(key=key, branch="G5",
                label=f"Tecknade leasingavtal som ännu inte börjat, {NAMES[company]}"
                      + (" (inklusive villkorade avtal)" if new else ""), unit="MUSD", freq="Q",
                source="Kurerad extraktion (curated/lease_commitments.csv) ur 10-Q/10-K, SEC EDGAR",
                fetch=lambda c=company, p=part: frame(c, p), lag_days=LAG.get(company, 25),
                license="SEC EDGAR: public information (sec.gov/privacy). Bara extraherade siffror med "
                        "källhänvisning publiceras, aldrig text",
                revised=True, publish=True, closed=closed,
                question="Hur mycket datacenterkapacitet är redan kontrakterad men ännu inte i balansräkningen?",
                note=f"{definition}. Agentextraherat, stickprov med python -m ai_tracker.lease_check; granskat av "
                     "R5 och rättat (X3)." + (f" Avslutad: {brk[3]}." if closed else ""))


SPECS = [_spec(c) for c in NAMES] + [_spec(c, "new") for c in BREAKS]
