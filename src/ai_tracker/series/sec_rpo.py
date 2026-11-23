"""SEC EDGAR XBRL instances: remaining performance obligations (RPO), contracted demand (lead L4), G4.

Total RPO per company (MSFT, GOOGL, AMZN, ORCL, CRWV), the amount expected within the first timing bucket
and the rest (where tagged: 12 months for MSFT and ORCL, 24 months for GOOGL and CRWV; Amazon tags no
split), and the sum rpo_hyp4 (MSFT + GOOGL + AMZN + ORCL). Point-in-time balances: period = calendar
quarter of the balance date, known_from = filing date, restatements are vintages. Extraction and vintage
logic: ai_tracker.sources.sec_rpo. Tags, mapping and checks: docs/kallor/rpo.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.series.sec import LICENSE
from ai_tracker.series.sec_segments import DefinitionBreakError
from ai_tracker.sources import sec, sec_rpo, sec_segment

SOURCE = "SEC EDGAR XBRL instances (RPO)"
QUESTION = "Hur stor är den kontrakterade efterfrågan som ännu inte blivit intäkt?"


@dataclass(frozen=True)
class Company:
    key: str  # series key suffix
    name: str
    cik: int
    since: str  # first filing date scanned (ASC 606 adoption)
    horizon: int | None  # months of the first timing bucket; None = no split tagged
    undimensioned: bool = False  # an undimensioned us-gaap percentage is the horizon share (Oracle FY2019-21)
    breaks: tuple[str, ...] = ()  # declared definition breaks of the total (filing dates)
    lag_days: int = 25
    note: str = ""


COMPANIES = [
    Company("msft", "Microsoft", 789019, "2017-07-01", 12,
            note="Totalt RPO (inklusive den mindre icke-kommersiella delen). Andel inom 12 månader: "
                 "egen tagg RevenueRemainingPerformanceObligationPercentageOfRevenueExpectedToBeRecognized"
                 "OverNext12Months i 10-Q för FY2018, därefter us-gaap-tidsdimensionen."),
    Company("googl", "Alphabet", 1652044, "2018-01-01", 24,
            note="Alphabet anger bara andelen inom 24 månader (inte 12)."),
    Company("amzn", "Amazon", 1018724, "2018-01-01", None,
            note="Amazon taggar ingen tidsuppdelning, bara vägd återstående löptid. Från 2020Q3 taggas "
                 "totalen med startdatumdimensionen (en enda hink)."),
    # Oracle's fiscal quarters end in Nov/Feb/May/Aug. Period = calendar quarter of the balance date, so the
    # 30 Nov balance is Q4 and is filed ~10 Dec, before the quarter ends: lag_days -31 allows that.
    Company("orcl", "Oracle", 1341439, "2018-01-01", 12, undimensioned=True, lag_days=-31,
            note="Balansdag i slutet av nov/feb/maj/aug: kalenderkvartalet för balansdagen (30 nov = Q4), "
                 "alltså en månad före kalenderkvartalets slut. Andel inom 12 månader: odimensionerad "
                 "procent FY2019-FY2021 (enligt 10-Q-texten de närmaste 12 månaderna), därefter tidsdimensionen."),
    Company("crwv", "CoreWeave", 1769628, "2025-01-01", 24,
            note="CoreWeave anger andelen inom 24 månader (inte 12). RPO är inte bolagets 'revenue backlog' "
                 "i pressmeddelandet (som inte taggas i XBRL)."),
]
BY_KEY = {c.key: c for c in COMPANIES}
HYP4 = ("msft", "googl", "amzn", "orcl")
PARTS = ("total", "near", "later")


@lru_cache(maxsize=None)
def company_facts(key: str) -> dict[str, list[sec.Fact]]:
    """sec.Facts per part (total, near, later) over all filings of one company."""
    c = BY_KEY[key]
    out: dict[str, list[sec.Fact]] = {p: [] for p in PARTS}
    for f, facts in sec_rpo.company_instants(c.cik, c.since):
        for part, got in sec_rpo.filing_facts(f, list(facts), c.horizon, c.undimensioned).items():
            out[part] += got
    return out


def checked_breaks(c: Company, total: list[sec.Fact]) -> list[pd.Timestamp]:
    found = [str(d.date()) for d in sec_segment.definition_breaks(total)]
    if found != list(c.breaks):
        raise DefinitionBreakError(f"rpo_{c.key}: detected definition breaks {found}, declared {list(c.breaks)}; "
                                   "review and declare (docs/kallor/rpo.md)")
    return [pd.Timestamp(b) for b in c.breaks]


@lru_cache(maxsize=None)
def company_series(key: str, part: str = "total") -> pd.DataFrame:
    """Release-dated quarterly rows (MUSD) of one part, without gaps. Only one definition regime is supported:
    a declared break would need new keys (see sec_segments for the pattern)."""
    c = BY_KEY[key]
    facts = company_facts(key)
    if checked_breaks(c, facts["total"]):
        raise NotImplementedError(f"rpo_{key}: definition break declared; add a key per regime first")
    return sec.contiguous_tail(sec_rpo.stock_vintages(facts[part]))


@lru_cache(maxsize=None)
def hyp4_series() -> pd.DataFrame:
    return sec.contiguous_tail(sec.aggregate({k: company_series(k) for k in HYP4}))


def _fetch(key: str | None, part: str):
    def fetch() -> pd.DataFrame:
        df = hyp4_series() if key is None else company_series(key, part)
        return df[["period", "value", "known_from"]].copy()

    return fetch


def series_key(key: str, part: str) -> str:
    c = BY_KEY[key]
    return {"total": f"rpo_{key}", "near": f"rpo_{key}_{c.horizon}m", "later": f"rpo_{key}_after{c.horizon}m"}[part]


def _spec(key: str, part: str) -> Spec:
    c = BY_KEY[key]
    label = {"total": "Återstående prestationsåtaganden (RPO)",
             "near": f"RPO som väntas bli intäkt inom {c.horizon} månader",
             "later": f"RPO som väntas bli intäkt efter {c.horizon} månader"}[part]
    note = "Balans vid kvartalets slut (stock), inte flöde. " + c.note
    if part != "total":
        note += (f" Beräknat som total × andel inom {c.horizon} månader ur samma inlämning; andelen är avrundad "
                 "(oftast hela procent, Microsoft i steg om 5), så beloppet är ungefärligt.")
    return Spec(key=series_key(key, part), branch="G4", label=f"{label}, {c.name}", unit="MUSD", freq="Q",
                source=SOURCE, fetch=_fetch(key, part), lag_days=c.lag_days, license=LICENSE, revised=True,
                publish=True, question=QUESTION, note=note.strip())


SPECS = [_spec(c.key, p) for c in COMPANIES for p in (PARTS if c.horizon else ("total",))] + [
    Spec(key="rpo_hyp4", branch="G4", label="Återstående prestationsåtaganden (RPO), MSFT+GOOGL+AMZN+ORCL",
         unit="MUSD", freq="Q", source=SOURCE, fetch=_fetch(None, "total"), lag_days=25, license=LICENSE,
         revised=True, publish=True, question=QUESTION,
         note=("Summa av fyra bolag per kalenderkvartal för balansdagen; en version finns först när alla fyra "
               "har lämnat in, known_from = senaste inlämningen. Oracles balansdag ligger en månad före "
               "de övrigas (30 nov i Q4)."))]
