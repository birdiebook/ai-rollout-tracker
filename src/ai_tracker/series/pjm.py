"""G7: PJM capacity auctions (RPM Base Residual Auction) and PJM's annual long-term load forecast.

Release-dated: every row carries the posting date of the auction results or of the load forecast report
(sources/pjm.py, with the evidence per date). Both are known before their period ends (auction results 10-36
months before the delivery year; a load forecast report in January of its vintage year), so lag_days is negative
(warehouse check known_from_after_period_end allows known_from >= period end + lag_days).

Not published: PJM has no open licence for the website (legal page not reachable, Data Miner 2 terms forbid
non-members to republish data). See docs/kallor/el_datacenter.md.
"""

from __future__ import annotations

from functools import partial

from ai_tracker.catalog import Spec
from ai_tracker.sources import pjm

LICENSE = ("PJM, no open licence. Website legal page (www.pjm.com/about-pjm/legal.aspx) redirects to /not-found "
           "(2026-11-23). Data Miner 2 terms: 'you may use the Data and the Tools for your internal business use or "
           "commercial purposes, including publishing and making derivatives of the Data, Members may republish "
           "data, however non-members are specifically prohibited from republishing data.' Stored for analysis, "
           "not published.")

BRA_SOURCE = "PJM RPM: rpm-auctions-resource-clearing-price-summary.xlsx och BRA-resultatfiler (www.pjm.com)"
LF_SOURCE = "PJM Load Forecast Report: <år>-load-report-data.xlsx och -tables.xlsx (www.pjm.com)"
BRA_NOTE = ("period = leveransårets startår (2025 = DY 2025/26). known_from = dagen då BRA-resultatet publicerades "
            "(pjm.BRA_POSTED, med belägg); DY 2007/08-2013/14 och 2015/16-2018/19 dateras konservativt till första "
            "daterade rapport som anger värdet. Aktualitet: nästa BRA avser ett leveransår 1-3 år fram, så den nyaste "
            "perioden ligger i framtiden; gräns 30 dagar efter dess slut.")
LF_NOTE = ("period = rapportens årgång V, värdet = prognosen för år V+h. known_from = rapportens publiceringsdag "
           "(pjm.LF_POSTED). Aktualitet: rapporten kommer i januari, gräns 60 dagar efter årgångens slut.")

BRA_SPECS = [
    Spec(key="pjm_bra_rcp_rto_a", branch="G7", label="PJM kapacitetsauktion (BRA), clearingpris RTO",
         unit="USD per MW-dag", freq="A", source=BRA_SOURCE, fetch=partial(pjm.bra, "rcp_rto"), lag_days=-1400,
         license=LICENSE, revised=False, publish=False,
         question="Hur mycket betalar marknaden för att säkra kapacitet när datacenterlasten växer?",
         note=BRA_NOTE + " Produkt: enda produkten, Annual (2014/15-2017/18) eller CP (2018/19-).",
         max_age_days=30),
    Spec(key="pjm_bra_rcp_dom_a", branch="G7", label="PJM kapacitetsauktion (BRA), clearingpris Dominion (DOM)",
         unit="USD per MW-dag", freq="A", source=BRA_SOURCE, fetch=partial(pjm.bra, "rcp_dom"), lag_days=-1400,
         license=LICENSE, revised=False, publish=False,
         question="Prissätts kapacitet i Virginia, världens största datacenterkluster, högre än i resten av PJM?",
         note=BRA_NOTE + " DOM är egen LDA i RPM från DY 2025/26 (tidigare FRR eller inte modellerad).",
         max_age_days=30),
    Spec(key="pjm_bra_cleared_rto_a", branch="G7", label="PJM kapacitetsauktion (BRA), clearad kapacitet RTO",
         unit="MW (UCAP)", freq="A", source=BRA_SOURCE, fetch=partial(pjm.bra, "cleared_rto"), lag_days=-1400,
         license=LICENSE, revised=False, publish=False,
         question="Hur mycket kapacitet säkras för leveransåret, och räcker den till lasten?",
         note=BRA_NOTE + " Total Annual Equivalent Resources Cleared, från DY 2020/21 (100 % CP).",
         max_age_days=30),
]

_LF = {
    "peak": ("Sommartopp", "MW", "Hur högt väntar PJM att toppen ligger om h år, och hur flyttas prognosen?"),
    "energy": ("Årlig nettoenergi", "GWh", "Hur mycket el väntar PJM att lasten drar om h år?"),
    "adj": ("Lastjustering för stora laster (främst datacenter), sommartopp", "MW",
            "Hur stor del av prognosen är uttryckligen nya stora laster, och hur flyttas den?"),
}

LF_SPECS = [
    Spec(key=f"pjm_lf_{q}_{area}_h{h}", branch="G7",
         label=f"PJM lastprognos, {name.lower() if q != 'adj' else name[0].lower() + name[1:]}, "
               f"{pjm.LF_AREAS[area][1]}, {h} år fram",
         unit=unit, freq="A", source=LF_SOURCE, fetch=partial(pjm.load_forecast, f"{q}_{area}_h{h}"),
         lag_days=-366, license=LICENSE, revised=True, publish=False, question=question,
         note=LF_NOTE + (" Tabell B-9 'Adjustments Above Embedded', maskinläsbar från 2025 (äldre bara i PDF)."
                         if q == "adj" else " Sommartopp = max juni-augusti (= tabell B-1), energi = årssumma "
                                            "(= tabell E-1), 50/50-prognos inklusive lastjusteringar."),
         max_age_days=60)
    for q, (name, unit, question) in _LF.items() for area in pjm.LF_AREAS for h in pjm.HORIZONS
]

SPECS = BRA_SPECS + LF_SPECS
