"""Useful lives of servers and network equipment per company (track P2a): sparse step values dated by filing.

Source: curated/useful_lives.csv (sources/useful_lives.py, docs/kallor/nyttjandeperioder.md). Catalog series, not
core series: they are not in any branch state, diffusion index or rate. A value exists only where a document states
it (policy at the balance date, or a new life from the quarter a change applies); a gap does not mean the life
changed, so every series is in KNOWN_GAPS and users take the latest known value (useful_lives.in_effect).

publish=True: numbers from public SEC filings with source references, never text (register 2026-11-24, P2a).
"""

from __future__ import annotations

from ai_tracker.catalog import Spec
from ai_tracker.sources import useful_lives as ul

FAMILY_LABEL = {
    "servers": "servrar",
    "network": "nätverksutrustning",
    "computer_equipment": "datorutrustning (bredare klass med servrar)",
    "tech_infra": "teknisk infrastruktur (bredare klass med servrar)",
    "other": "annan bredare klass med servrar",
}
BOUND_LABEL = {"lo": "lägsta", "hi": "högsta"}
LAG = -(ul.MAX_LEAD_DAYS)  # a change can be announced before the quarter it applies in
MAX_AGE = 550  # one 10-K a year (balance date + 2-3 months) plus margin
LICENSE = ("SEC EDGAR: public information (sec.gov/privacy). Bara extraherade siffror med källhänvisning publiceras, "
           "aldrig text")


def _specs() -> tuple[list[Spec], dict[str, str]]:
    if not ul.PATH.exists():
        return [], {}
    df = ul.load()
    specs, gaps = [], {}
    for company, name in ul.COMPANIES.items():
        for family in ul.FAMILIES:
            stop = ul.stopped(df, company, family)
            for bound in ("lo", "hi"):
                frame = ul.series_frame(df, company, family, bound)
                if frame.empty:
                    continue
                key = f"useful_life_{family}_{company}_{bound}"
                classes = sorted(set(df[(df["company"] == company)
                                        & df["class_code"].isin(ul.FAMILIES[family])]["asset_class"].str.lower()))

                def fetch(c=company, f=family, b=bound):
                    return ul.series_frame(ul.load(), c, f, b)

                closed = stop is not None
                note = (f"Bolagets klass(er): {'; '.join(classes)}. Glesa stegvärden: ett värde bara där ett dokument "
                        f"anger det (policy vid balansdagen eller ny period från kvartalet där en ändring gäller), "
                        f"daterat med inlämningsdagen. Agentextraherat, stickprov med python -m "
                        f"ai_tracker.useful_lives_check. Se docs/kallor/nyttjandeperioder.md. "
                        + (f"Avslutad: bolaget slutade ange perioden i 10-K {stop['filed']} ({stop['id']})."
                           if closed else f"Aktualitet: ett 10-K om året, gräns {MAX_AGE} dagar."))
                specs.append(Spec(
                    key=key, branch="G5", label=f"Nyttjandeperiod för {FAMILY_LABEL[family]}, {name}, "
                                                f"{BOUND_LABEL[bound]} (år)",
                    unit="år", freq="Q",
                    source="Kurerad extraktion (curated/useful_lives.csv) ur 10-K/10-Q/8-K, SEC EDGAR",
                    fetch=fetch, lag_days=LAG, license=LICENSE, revised=True, publish=True,
                    question="Hur länge skriver bolaget av sina servrar, och när ändrades det?",
                    note=note, closed=closed, max_age_days=None if closed else MAX_AGE))
                gaps[key] = "sparse step values: a value only where a filing states the life"
    return specs, gaps


SPECS, KNOWN_GAPS = _specs()
