"""Company-disclosed AI KPIs (step 2, track B4): usage (L2), revenue (L3) and capacity statements.

Agent-extracted, stored as numbers and references only in curated/ai_kpis.csv and loaded by
ai_tracker.sources.ai_kpis. One series per definition code (a change of definition is a new series). Disclosure is
irregular: companies state a KPI in some quarters and not in others, so gaps are expected (KNOWN_GAPS below, merged
into warehouse.KNOWN_GAPS) and a missing statement is never a zero. See docs/kallor/ai_nyckeltal.md.

Reviewed by R5 and corrected (X3, 2026-11-24): publish=True (numbers with source references only, never text).
"""

from __future__ import annotations

from ai_tracker.catalog import Spec
from ai_tracker.sources import ai_kpis

BRANCH = {"L2": "G3", "L3": "G4", "cap": "G7"}
QUESTION = {
    "L2": "Hur mycket används bolagets AI-tjänster enligt bolaget självt (led L2)?",
    "L3": "Hur stora är bolagets AI- och molnintäkter enligt bolaget självt (led L3)?",
    "cap": "Säger bolaget att kapaciteten för AI och moln räcker till efterfrågan?",
}
LICENSE = ("SEC EDGAR: public information (sec.gov/privacy); microsoft.com: bara extraherade siffror med "
           "källhänvisning, aldrig text")
# A point-in-time value is stated in the month it refers to (or after the quarter); a Microsoft fiscal year (ends
# June) is stored as its calendar year, so its row comes about 150 days before that period's end.
LAG = {"M": -31, "Q": -92, "A": -200}
FORWARD_LAG = -400  # forward statements (expected run rate, capacity outlook) refer to a period up to a year ahead
MAX_AGE = 400  # irregular disclosure: overdue only when nothing new has come for about a year
# A KPI not stated in the documents of the last ~three quarterly reports (270 days before the newest document in the
# extraction) is treated as discontinued (closed); it reopens when a later extraction finds it again.
INACTIVE_DAYS = 270


def _specs() -> tuple[list[Spec], dict[str, str]]:
    if not ai_kpis.PATH.exists():
        return [], {}
    df = ai_kpis.load()
    newest = df["known_from"].max()
    specs, gaps = [], {}
    for code in sorted(set(df["definition"])):
        d = ai_kpis.DEFINITIONS[code]
        key = ai_kpis.series_key(code)
        frame = ai_kpis.series_frame(df, code)

        def fetch(c=code):
            return ai_kpis.series_frame(ai_kpis.load(), c)

        last_end = max(ai_kpis._period(d.freq, p).end_time for p in frame["period"])
        inactive = (newest - last_end).days > INACTIVE_DAYS
        closed = code in ai_kpis.CLOSED or inactive
        reason = ai_kpis.CLOSED.get(code) or (f"bolaget har inte angett nyckeltalet sedan {last_end.date()} (senaste "
                                              f"dokumentet i extraktionen {newest.date()}); öppnas igen om det kommer "
                                              f"tillbaka" if inactive else "")
        forward = code.endswith(("_FORWARD", "_EXPECTED"))
        note = (f"Definition {code}: {d.text}. Agentextraherat ur bolagets dokument, granskat av R5 och rättat (X3). "
                + (f"Avslutad: {reason}." if closed else
                   f"Aktualitet: oregelbunden rapportering, gräns {MAX_AGE} dagar."))
        specs.append(Spec(key=key, branch=BRANCH[d.lead], label=d.label, unit=d.unit, freq=d.freq,
                          source="Kurerad extraktion (curated/ai_kpis.csv): SEC EDGAR 8-K/10-Q/10-K och "
                                 "Microsofts samtal på microsoft.com",
                          fetch=fetch, lag_days=FORWARD_LAG if forward else LAG[d.freq], license=LICENSE, revised=True, publish=True,
                          question=QUESTION[d.lead], note=note, closed=closed,
                          max_age_days=None if closed else MAX_AGE))
        ords = sorted({ai_kpis._period(d.freq, p).ordinal for p in frame["period"]})
        if ords and ords[-1] - ords[0] + 1 != len(ords):
            gaps[key] = "irregular company disclosure: the KPI is stated in some periods only"
    return specs, gaps


SPECS, KNOWN_GAPS = _specs()
