"""AN1: Anthropic's reported (GAAP) revenue and results as catalog series (register 2026-11-27 "AN1"), publish=False.

From curated/anthropic_gaap.csv (sources/anthropic_gaap.py), release-dated: known_from = the filing date of the first
prospectus stating a value, and a new version only when a later one changes it (entry, (c)).

    lab_gaap_anthropic_<item>_q     quarterly table (MD&A, unaudited), calendar quarters          revenue, compute, opinc
    lab_gaap_anthropic_<item>_a     financial statements, year ended December 31                  all items
    lab_gaap_anthropic_<item>_ytd   financial statements, six or nine months from January 1,      all items
                                    period = the quarter the period ends in

Items: revenue, compute (compute and infrastructure, an expense by nature), opinc (operating income or loss, signed),
cost_of_revenue (the functional note), gross_profit (derived: revenue - cost of revenue, same document and column), cfo
(net cash from operating activities, signed), capex (purchases of property and equipment) and prepay_leased
(prepayments for leased assets and equipment), the last two as positive outflows.

Never mixed with the run-rate series (lab_rev_anthropic_*): run-rate is the company's own annualised pace on a day, not
reported revenue. Not in any branch index, no core series, no state.
"""

from __future__ import annotations

from ai_tracker.catalog import Spec
from ai_tracker.sources import anthropic_gaap as A

SOURCE = ("Kurerad extraktion (curated/anthropic_gaap.csv) ur SEC EDGAR, Anthropic, PBC: S-1, S-1/A och 424B4 "
          "(HTML-tabeller, deterministisk tolkning)")
LICENSE = "SEC EDGAR: public information (sec.gov/privacy). Bara extraherade siffror med källhänvisning"
ITEM_SV = {
    "revenue": "intäkter",
    "compute": "kostnader för compute och infrastruktur",
    "opinc": "rörelseresultat",
    "cost_of_revenue": "kostnad för intäkter",
    "gross_profit": "bruttoresultat (härlett)",
    "cfo": "kassaflöde från den löpande verksamheten",
    "capex": "investeringar i materiella anläggningstillgångar (capex)",
    "prepay_leased": "förskott för leasade tillgångar och utrustning",
}
ITEM_NOTE = {
    "revenue": "Raden \"Revenue\".",
    "compute": "Raden \"Compute and infrastructure\": kostnad efter slag (all compute, även träning och forskning), "
               "inte kostnad för intäkter.",
    "opinc": "Raden \"Operating income (loss)\" eller \"Operating loss\", med tecken (förlust negativ).",
    "cost_of_revenue": "Raden \"Cost of revenue\" i noten om kostnader efter funktion (Supplemental Operating Expense "
                       "Information). Bara compute för kundernas arbetslaster och viss personal och overhead; "
                       "compute för träning och forskning ligger i Research and development.",
    "gross_profit": "Härlett: intäkter minus kostnad för intäkter ur samma dokument och kolumn. Står inte i "
                    "dokumenten (bolaget redovisar sedan bytet till kostnader efter slag inte bruttoresultat).",
    "cfo": "Raden \"Net cash provided by (used in) operating activities\", med tecken.",
    "capex": "Raden \"Purchases of property and equipment\", som positivt utflöde (tabellens parentes vänd).",
    "prepay_leased": "Raden \"Prepayments for leased assets and equipment\", som positivt utflöde. Finns från S-1/A "
                     "2026-11-02 (inte i S-1). Läggs inte ihop med capex.",
}
KIND_SV = {"q": ("per kvartal", "Q", "kvartalstabellen i MD&A (ogranskad)"),
           "a": ("per år", "A", "de finansiella rapporterna, helår"),
           "ytd": ("hittills i år", "Q", "de finansiella rapporterna, sex eller nio månader från 1 januari; period = "
                                       "kvartalet då perioden slutar")}
MAX_AGE = {"q": 240, "ytd": 240, "a": 460}  # next figures: the first periodic reports (10-K for 2026, 10-Q for 2027Q1)


def keys() -> list[tuple[str, str]]:
    out = [(i, "q") for i in ("revenue", "compute", "opinc")]
    for kind in ("a", "ytd"):
        out += [(i, kind) for i in ("revenue", "compute", "opinc", "cost_of_revenue", "gross_profit", "cfo", "capex",
                                    "prepay_leased")]
    return out


def _specs() -> list[Spec]:
    if not A.CSV_PATH.exists():
        return []
    out = []
    for item, kind in keys():
        key = A.series_key(item, kind)
        what, freq, where = KIND_SV[kind]

        def fetch(key=key):
            return A.versions(A.load(), key)

        out.append(Spec(
            key=key, branch="G4", label=f"Anthropic, {ITEM_SV[item]}, {what} (GAAP, redovisad)", unit="MUSD",
            freq=freq, source=SOURCE, fetch=fetch, lag_days=0, license=LICENSE, revised=True, publish=False,
            question="Vad har frontlabbet Anthropic faktiskt redovisat i intäkter, kostnader och kassaflöde?",
            note=f"{ITEM_NOTE[item]} Ur {where}. known_from = inlämningsdatum för det första prospekt som anger "
                 f"värdet (S-1 2026-10-26, S-1/A 2026-11-02, 2026-11-10, 2026-11-17, 424B4 2026-11-19); en senare "
                 f"ändring blir en ny version. Redovisade tal, blandas aldrig med run-rate (lab_rev_anthropic_*). "
                 f"Aktualitet: nästa värden kommer med de första periodiska rapporterna, gräns {MAX_AGE[kind]} dagar. "
                 f"Registret 2026-11-27 AN1; se docs/kallor/anthropic_gaap.md.",
            max_age_days=MAX_AGE[kind]))
    return out


SPECS = _specs()

# Accepted gaps (warehouse.KNOWN_GAP_PERIODS): the prospectuses state six and nine months only, so a year-to-date
# series has no Q4 (the year is the _a series) and no Q1 between them; the S-1 has no prepayments line (ABSENT).
_YTD_NOT_STATED = {"2025Q4": "prospekten anger bara sex och nio månader; helåret står i _a-serien",
                   "2026Q1": "prospekten anger bara sex och nio månader"}
KNOWN_GAP_PERIODS: dict[str, dict[str, str]] = {
    A.series_key(i, "ytd"): dict(_YTD_NOT_STATED)
    for i in ("revenue", "compute", "opinc", "cost_of_revenue", "gross_profit", "cfo", "capex", "prepay_leased")
}
KNOWN_GAP_PERIODS[A.series_key("prepay_leased", "ytd")]["2026Q2"] = ("S-1:s kassaflödesanalys har ingen rad för "
                                                                     "förskotten (från S-1/A 2026-11-02)")
