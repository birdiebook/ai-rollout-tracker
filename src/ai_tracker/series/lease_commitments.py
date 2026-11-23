"""Leases signed but not yet commenced, per company: agent-extracted from 10-Q/10-K lease notes.

Source: curated/lease_commitments.csv (sources/lease_commitments.py, docs/kallor/finansiering.md). One value per
filing (the total; parts summed), dated by the filing date. Not published until the independent review (R5) of the
extraction is done: publish=False.
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
    "msft": "operationell + finansiell leasing (en summa från FY2025 Q4)",
    "googl": "framtida leasingbetalningar, odiskonterade (10-K: kort- + långfristiga)",
    "amzn": "totalkolumnen i raden 'Leases not yet commenced' i åtagandetabellen; från 2020Q4",
    "meta": "operationell + finansiell leasing; 2024Q1–Q3 bara operationell",
    "orcl": "ytterligare leasingåtaganden; före FY2025 bara operationell; luckor 2023–2024 (inget belopp angivet)",
    "crwv": "summa framtida odiskonterade leasingbetalningar",
}


def frame(company: str) -> pd.DataFrame:
    if not lc.PATH.exists():
        return pd.DataFrame(columns=["period", "value", "known_from"])
    return sec.contiguous_tail(lc.series_frame(lc.load(), company))


def _spec(company: str) -> Spec:
    return Spec(key=f"lease_uncommenced_{company}", branch="G5",
                label=f"Tecknade leasingavtal som ännu inte börjat, {NAMES[company]}", unit="MUSD", freq="Q",
                source="Kurerad extraktion (curated/lease_commitments.csv) ur 10-Q/10-K, SEC EDGAR",
                fetch=lambda c=company: frame(c), lag_days=LAG.get(company, 25),
                license="SEC EDGAR: public information (sec.gov/privacy). Bara extraherade siffror med "
                        "källhänvisning publiceras, aldrig text",
                revised=True, publish=False,
                question="Hur mycket datacenterkapacitet är redan kontrakterad men ännu inte i balansräkningen?",
                note=f"{DEFINITION[company]}. Agentextraherat, stickprov med python -m ai_tracker.lease_check; "
                     "granskas av R5 innan användning.")


SPECS = [_spec(c) for c in NAMES]
