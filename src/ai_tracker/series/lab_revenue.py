"""AI labs' self-reported revenue (track B6), from curated/lab_revenue.csv (ai_tracker.sources.lab_revenue).

One series per (lab, scope, measure): run-rate revenue in the newsroom and the S-1-defined Run-Rate Revenue are
different measures and never mixed, nor mixed with audited (GAAP) revenue. Labels carry "(rapporterad)": the
figures are the companies' own statements, unaudited, often a bound ("over $5 billion").

Point-in-time levels (run-rate, ARR) have freq D with period = the date the figure refers to, so known_from >=
period always holds (lag_days 0). Statements are irregular: freshness bound 400 days (max_age_days).
"""

from __future__ import annotations

from ai_tracker.catalog import Spec
from ai_tracker.sources import lab_revenue

LAB_NAMES = {"anthropic": "Anthropic", "openai": "OpenAI", "xai": "xAI", "mistral": "Mistral", "cohere": "Cohere"}
NEWSROOM_LICENCE = ("anthropic.com: konsumentvillkoren omfattar webbplatser; automatisk hämtning pausad i väntan på "
                    "beslut (beslutslogg 2026-11-23). Bara extraherade siffror med källhänvisning, aldrig text. "
                    "Ej kontrollerad för publicering")
SOURCES = {
    "newsroom": ("Bolagets eget nyhetsrum (www.anthropic.com/news), kurerad extraktion i curated/lab_revenue.csv",
                 NEWSROOM_LICENCE),
    "sec": ("SEC EDGAR, Anthropic, PBC registreringsprospekt (S-1/A), kurerad extraktion i curated/lab_revenue.csv",
            "SEC EDGAR: public information (sec.gov/privacy). Bara extraherade siffror med källhänvisning"),
}
QUAL_SV = {"as_stated": "utan förbehåll", "approx": "ungefär", "over": "över (nedre gräns)", "nearly": "nästan"}


def _specs() -> list[Spec]:
    if not lab_revenue.PATH.exists():
        return []
    df = lab_revenue.load()
    out = []
    for (lab, scope, measure), grp in df.groupby(["lab", "scope", "measure"], sort=True):
        kind = "newsroom" if (grp["doc_type"] == "newsroom").all() else "sec"
        source, licence = SOURCES[kind]
        freq = "A" if measure == "REVENUE_CY" else "D"
        quals = ", ".join(QUAL_SV[q] for q in sorted(set(grp["qualifier"])))
        key = f"lab_rev_{lab}_{scope}_{measure.lower()}"
        what = {"RUN_RATE": "run-rate revenue", "RUN_RATE_S1": "Run-Rate Revenue enligt S-1",
                "ARR": "ARR", "REVENUE_CY": "intäkt per kalenderår"}[measure]

        def fetch(lab=lab, scope=scope, measure=measure):
            return lab_revenue.series_frame(lab_revenue.load(), lab, scope, measure)

        out.append(Spec(
            key=key, branch="G4",
            label=f"{LAB_NAMES[lab]}, {what}, {lab_revenue.SCOPES[scope]} (rapporterad)",
            unit="MUSD", freq=freq, source=source, fetch=fetch, lag_days=0, license=licence,
            revised=True, publish=False,
            question="Vilken intäktsnivå säger labbet självt att det har nått, och när sa det det?",
            note=f"Självrapporterat av bolaget, ej reviderat och inte granskat av tredje part; blandas aldrig med "
                 f"redovisade (GAAP) intäkter. Mått: {lab_revenue.MEASURES[measure]}. Värdet är siffran som den "
                 f"uttalades (förbehåll i serien: {quals}). period = datumet siffran avser; known_from = "
                 f"publiceringsdatum (nyhetsrum) eller EDGAR-inlämningsdatum. Aktualitet: oregelbundna "
                 f"uttalanden, gräns 400 dagar. Se docs/kallor/labbintakter.md.",
            max_age_days=400))
    return out


SPECS = _specs()
