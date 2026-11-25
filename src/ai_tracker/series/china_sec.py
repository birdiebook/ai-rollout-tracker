"""China via SEC (track CN1): Alibaba's cloud segment and capex, Baidu's capex and AI cloud revenue, from 6-K releases.

Catalog series, not core series: they are not in any branch index or state rule (register entry 2026-11-25 CN1).
Cloud revenue in G4, capex in G5, in RMB millions as reported (MRMB), release-dated: known_from = the 6-K filing date.
Every segment re-definition is its own series (_v1, _v2, ...), never spliced. Baidu's AI Cloud Infra and Baidu Core
non-online marketing revenue are stated only in sentences: curated extraction (curated/china_text.csv), publish=False
until the extraction review has passed. The US$ views (*_usd) divide by the quarterly mean of the Fed H.10 rate.
See docs/kallor/kina_sec.md.
"""

from __future__ import annotations

import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.series.tsmc import sixk_license
from ai_tracker.sources import china_sec, china_text, fed_h10, sec

SOURCE = "SEC EDGAR, {name} Form 6-K (kvartalsrapport, pressmeddelande, tabell)"
SOURCE_TEXT = "Kurerad extraktion (curated/china_text.csv), SEC EDGAR, Baidu Form 6-K (pressmeddelande, mening)"
LICENSE = {c: sixk_license(n) for c, n in china_sec.NAMES.items()}
FED_LICENSE = ("Public domain (Board of Governors of the Federal Reserve System, www.federalreserve.gov/disclaimer.htm): "
               "\"Unless otherwise indicated, information on Board's website is in the public domain and may be "
               "copied and distributed without permission. Please cite to the Board as the source of the "
               "information.\" Source: Federal Reserve Board, H.10 Foreign Exchange Rates.")
FX_LAG_DAYS = 10  # H.10 comes every Monday with the previous week's rates; 10 days after quarter end is a margin

# Observed 2015-2026 (Alibaba) and 2020-2026 (Baidu): days from calendar quarter end to the 6-K filing, largest.
MAX_LAG = {"baba": 78, "bidu": 64}
CALENDAR = {"baba": "räkenskapsår till 31 mars, kvartalen slutar på kalenderkvartalens slut (juni = kalender-Q2)",
            "bidu": "kalenderår"}


def _max_age(company: str) -> int:
    return MAX_LAG[company] + 92 + 30


def table_rows(company: str, measure: str, key: str) -> pd.DataFrame:
    return sec.contiguous_tail(china_sec.series(company, measure, key))


def _fetch_table(company: str, measure: str, key: str):
    def fetch() -> pd.DataFrame:
        return table_rows(company, measure, key)
    return fetch


def _fetch_text(key: str):
    def fetch() -> pd.DataFrame:
        return sec.contiguous_tail(china_text.series_rows(key))
    return fetch


def to_usd(rows: pd.DataFrame, fx: pd.Series) -> pd.DataFrame:
    """MUSD rows from MRMB rows: value / quarterly mean CNY per USD; known_from = max(row, quarter end + FX_LAG_DAYS).

    Quarters without a mean rate (fewer than fed_h10.MIN_DAYS quoted days) are left out.
    """
    out = []
    for r in rows.itertuples(index=False):
        q = pd.Period(r.period, freq="Q-DEC")
        if q not in fx.index:
            continue
        fx_known = q.end_time.normalize() + pd.Timedelta(days=FX_LAG_DAYS)
        out.append((r.period, float(r.value) / float(fx[q]), max(pd.Timestamp(r.known_from), fx_known)))
    df = pd.DataFrame(out, columns=["period", "value", "known_from"])
    return df.sort_values(["known_from", "period"], ignore_index=True)


def _fetch_usd(company: str, measure: str, key: str):
    def fetch() -> pd.DataFrame:
        return to_usd(table_rows(company, measure, key), fed_h10.quarterly_mean(fed_h10.daily("ch")))
    return fetch


TABLE = {  # key: (company, measure, branch, label, question)
    "rev_baba_cloud_v1": ("baba", "rev_cloud", "G4", "Alibaba, molnsegmentet före DingTalk (2015Q2–2021Q1)",
                          "Hur växte Alibabas moln innan DingTalk flyttades in?"),
    "rev_baba_cloud_v2": ("baba", "rev_cloud", "G4", "Alibaba, molnsegmentet med DingTalk (2020Q2–2023Q1)",
                          "Hur växte Alibabas moln med DingTalk, före omorganisationen 2023?"),
    "rev_baba_cloud_v3": ("baba", "rev_cloud", "G4", "Alibaba, Cloud Intelligence Group (2022Q3–2026Q1)",
                          "Hur snabbt växer Kinas största moln, före sammanslagningen med T-Head?"),
    "rev_baba_cloud_v4": ("baba", "rev_cloud", "G4", "Alibaba, AI Cloud and Compute Services (från 2025Q2)",
                          "Hur snabbt växer Kinas största moln, med Alibabas chipenhet T-Head?"),
    "capex_baba_v1": ("baba", "capex", "G5", "Alibaba, capex (anläggningstillgångar och immateriella, till 2018Q1)",
                      "Hur mycket investerade Alibaba innan definitionen ändrades 2018?"),
    "capex_baba_v2": ("baba", "capex", "G5", "Alibaba, capex (anläggningstillgångar utan kontorscampus)",
                      "Hur mycket investerar Kinas största molnbolag i datacenter och servrar?"),
    "capex_bidu": ("bidu", "capex_total", "G5", "Baidu, capex (Baidu, Inc.)",
                   "Hur mycket investerar Baidu, inklusive iQIYI?"),
    "capex_bidu_core": ("bidu", "capex_core", "G5", "Baidu, capex utan iQIYI (Baidu Core)",
                        "Hur mycket investerar Baidus AI- och sökverksamhet, utan videotjänsten iQIYI?"),
}
OPEN_TABLE = ("rev_baba_cloud_v4", "capex_baba_v2", "capex_bidu", "capex_bidu_core")  # with a US$ view

TEXT = {  # key: (branch, label, question, closed, definition)
    "rev_bidu_ai_cloud_infra": (
        "G4", "Baidu, intäkt från AI Cloud Infra (ur text)",
        "Hur snabbt växer Baidus AI-infrastruktur i molnet?", False,
        "Meningen \"Revenue from AI Cloud Infra was/reached RMB X billion\" för rapportkvartalet (från 2025Q3). "
        "AI Cloud Infra = \"AI infrastructure and platform services within AI Cloud serving enterprises and the "
        "public sector\". Ej reviderad av revisor: bolagets interna redovisning."),
    "rev_bidu_core_nonads": (
        "G4", "Baidu Core, intäkter utanför annonser (ur text, 2020Q3–2025Q3)",
        "Hur växte Baidus intäkter utanför annonser, där AI Cloud är den största delen?", True,
        "Meningen om Baidu Cores \"non-online marketing revenue\" (2020-11 – 2021-05 \"non-marketing revenue\") för "
        "rapportkvartalet. Bredare än AI Cloud (även Apollo, enheter med mera). Avslutad: från 2026-02 heter Baidu "
        "Core \"Baidu General Business\" med en annan uppdelning, och måttet anges inte längre."),
}


def _era(key: str) -> china_sec.Era:
    company, measure = TABLE[key][:2]
    return next(e for e in china_sec.ERAS[(company, measure)] if e.key == key)


def _table_spec(key: str) -> Spec:
    company, measure, branch, label, question = TABLE[key]
    era = _era(key)
    closed = era.last is not None
    span = f"pressmeddelanden {era.first} – {era.last}" if closed else f"pressmeddelanden från {era.first}"
    note = (f"Release-daterad: known_from = 6-K:ns inlämningsdatum. Definition: {era.definition} ({span}). "
            "Varje omdefinition är en egen serie och skarvas aldrig. Jämförelsetal som ändras mer än 0,5 MRMB är nya "
            f"vintages. Räkenskapsår: {CALENDAR[company]}. ")
    if closed:
        note += "Avslutad: definitionen ersattes av en ny (egen serie). "
    else:
        note += (f"Aktualitet: gräns {_max_age(company)} dagar = största observerade avstånd från kvartalets slut till "
                 "6-K:n + 92 + 30. ")
    note += "Se docs/kallor/kina_sec.md."
    return Spec(key=key, branch=branch, label=label, unit="MRMB", freq="Q",
                source=SOURCE.format(name=china_sec.NAMES[company]), fetch=_fetch_table(company, measure, key),
                lag_days=MAX_LAG[company], license=LICENSE[company], revised=True, publish=True, question=question,
                note=note, max_age_days=None if closed else _max_age(company), closed=closed)


def _usd_spec(key: str) -> Spec:
    company, measure, branch, label, question = TABLE[key]
    note = (f"US$-vy av {key}: MRMB delat med kvartalets medelkurs (CNY per USD, medel av de dagliga kurserna i "
            "Fed:s H.10, samma data som DEXCHUS, hämtad från federalreserve.gov). known_from = max(RMB-radens "
            f"known_from, kvartalets slut + {FX_LAG_DAYS} dagar). Kurserna har bara aktuell vintage. "
            f"Aktualitet: gräns {_max_age(company)} dagar som för RMB-serien. Se docs/kallor/kina_sec.md.")
    return Spec(key=f"{key}_usd", branch=branch, label=f"{label}, i US$", unit="MUSD", freq="Q",
                source=SOURCE.format(name=china_sec.NAMES[company]) + "; omräknad med Federal Reserve H.10 "
                "(kvartalsmedel av dagliga kurser, federalreserve.gov)",
                fetch=_fetch_usd(company, measure, key), lag_days=MAX_LAG[company],
                license=f"derived: {LICENSE[company]} + {FED_LICENSE}", revised=True, publish=True,
                question=question, note=note, max_age_days=_max_age(company))


def _text_spec(key: str) -> Spec:
    branch, label, question, closed, definition = TEXT[key]
    note = ("Release-daterad: known_from = 6-K:ns inlämningsdatum. " + definition + " Belopp i miljarder RMB med en "
            "decimal, lagrat ×1000 som MRMB (precision ±50 MRMB). Kodat med reglerna i registerposten 2026-11-25 CN1; "
            "kontroll: python -m ai_tracker.china_text_check. publish=False tills extraktionsgranskningen är godkänd. ")
    if not closed:
        note += f"Aktualitet: gräns {_max_age('bidu')} dagar. "
    note += "Se docs/kallor/kina_sec.md."
    return Spec(key=key, branch=branch, label=label, unit="MRMB", freq="Q", source=SOURCE_TEXT,
                fetch=_fetch_text(key), lag_days=MAX_LAG["bidu"], license=LICENSE["bidu"], revised=False,
                publish=False, question=question, note=note, max_age_days=None if closed else _max_age("bidu"),
                closed=closed)


SPECS = ([_table_spec(k) for k in TABLE] + [_usd_spec(k) for k in OPEN_TABLE] + [_text_spec(k) for k in TEXT])
