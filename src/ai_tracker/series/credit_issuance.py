"""Spread at issuance and registered bond issuance per quarter (track KR1): catalog series, not core series.

Source: curated/credit_issuance.csv (sources/credit_issuance.py, docs/kallor/kredit_emission.md). One row per tranche of
the registered bond offerings of Microsoft, Alphabet, Amazon, Meta, Oracle and CoreWeave since 2020, read from the
final pricing term sheets (FWP) on EDGAR. Series by calendar quarter of the pricing date:

    issuance_<co>_q          principal of the company's USD tranches (fixed and floating), MUSD
    spread_issue_ai_q        principal-weighted mean spread over the US Treasury benchmark, USD fixed rate, all issuers
    spread_issue_ai_7_12y_q  the same, tenors that round to 7-12 years (6.5 <= tenor < 12.5)
    spread_issue_<co>_q      the same per issuer, for issuers with at least four quarters with such a tranche

A quarter without an eligible tranche has no value (a gap, listed in KNOWN_GAPS). A quarter's version is known from
max(the day after the quarter, the latest filing of its tranches); an unfinished quarter has no value. Not in any
branch state, diffusion index or rate. publish=False until the extraction review has passed (register 2026-11-25, KR1).
"""

from __future__ import annotations

from ai_tracker.catalog import Spec
from ai_tracker.sources import credit_issuance as ci

SOURCE = "Kurerad extraktion (curated/credit_issuance.csv) ur villkorsbilagor (FWP) på SEC EDGAR"
LICENSE = ("SEC EDGAR: public information (sec.gov/privacy). Bara extraherade siffror med källhänvisning publiceras, "
           "aldrig text")
MAX_AGE = 1100  # issuance is irregular: an issuer can stay out of the market for years
COVERAGE = ("Bara den registrerade obligationsmarknaden (villkorsbilagor på EDGAR): privata placeringar, 144A, "
            "SPV-finansiering, företagscertifikat, banklån och terminslån ingår inte. ")
DATING = ("Ett kvartal utan tranche har inget värde (lucka, inte noll). Värdet är känt från dagen efter kvartalet, eller "
          "från den senaste inlämningen om den är senare. ")
AGE_NOTE = f"Aktualitet: emission är oregelbunden, gräns {MAX_AGE} dagar. "
REVIEW = "publish=False tills extraktionsgranskningen har godkänt. Se docs/kallor/kredit_emission.md."
SPREAD_RULE = ("Principalvägt medelvärde av den angivna spreaden mot den amerikanska statsobligationen (bp), över tranchar "
               "i USD med fast ränta. Rörlig ränta och annan valuta ingår inte. ")
MIX_NOTE = ("Blandar emittenter med olika kreditbetyg (från AAA till BBB), så serien rör sig också när mixen av "
            "emittenter och löptider ändras. ")


def _fetch_issuance(company: str):
    def fetch():
        return ci.issuance(ci.load(), company)

    return fetch


def _fetch_spread(companies, band):
    def fetch():
        return ci.spread(ci.load(), companies, band)

    return fetch


def _spec(key: str, label: str, unit: str, fetch, question: str, note: str) -> Spec:
    return Spec(key=key, branch="G5", label=label, unit=unit, freq="Q", source=SOURCE, fetch=fetch, lag_days=1,
                license=LICENSE, revised=True, publish=False, question=question,
                note=note + AGE_NOTE + REVIEW, max_age_days=MAX_AGE)


def _specs() -> tuple[list[Spec], dict[str, str]]:
    if not ci.PATH.exists():
        return [], {}
    df = ci.load()
    specs = []
    for co in ci.issuers(df):
        name = ci.COMPANIES[co]
        specs.append(_spec(
            f"issuance_{co}_q", f"Registrerade obligationer i USD, emitterat belopp, {name}", "MUSD",
            _fetch_issuance(co), "Hur mycket lånar bolaget upp på den registrerade obligationsmarknaden?",
            f"Summa av nominellt belopp för {name}s tranchar i USD (fast och rörlig ränta) efter prisdag. Annan "
            f"valuta ingår inte. Stäms av mot debt_issued_{co} (täckningsgraden i källdokumentet). " + COVERAGE
            + DATING))
    specs.append(_spec(
        "spread_issue_ai_q", "Spread vid emission, AI-tunga emittenter (alla löptider)", "bp",
        _fetch_spread(None, None), "Vad kostar krediten för bolagen som bär AI-utbyggnaden?",
        SPREAD_RULE + "Alla emittenter: Microsoft, Alphabet, Amazon, Meta, Oracle (CoreWeave har inga registrerade "
                      "obligationer). " + MIX_NOTE + COVERAGE + DATING))
    specs.append(_spec(
        "spread_issue_ai_7_12y_q", "Spread vid emission, AI-tunga emittenter, löptid 7–12 år", "bp",
        _fetch_spread(None, ci.BAND_7_12), "Vad kostar krediten, med löptidsmixen hållen fast?",
        SPREAD_RULE + "Bara löptid som avrundad till hela år är 7–12 (6,5 ≤ löptid < 12,5). " + MIX_NOTE + COVERAGE
        + DATING))
    for co in ci.spread_issuers(df):
        name = ci.COMPANIES[co]
        specs.append(_spec(
            f"spread_issue_{co}_q", f"Spread vid emission, {name} (alla löptider)", "bp",
            _fetch_spread((co,), None), "Vad kostar krediten för bolaget, och ändras det?",
            SPREAD_RULE + f"Bara {name}. Löptidsmixen skiljer sig mellan emissionerna. " + COVERAGE + DATING))
    gaps = {s.key: "issuance is irregular: a quarter without a tranche has no value (KR1)" for s in specs}
    return specs, gaps


SPECS, KNOWN_GAPS = _specs()
