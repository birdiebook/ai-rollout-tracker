"""Orders, backlog, book-to-bill, gas turbine GW, AI server orders and signed leases from earnings releases (track S3).

Source: curated/orders_backlog.csv (sources/orders_backlog.py, docs/kallor/order_orderstock.md): figures the agent
coded from the press release exhibit of each results 8-K, with locator and sentence hash. One series per definition
(company, measure, segment, component, window, form, organic, unit) with points for at least two periods; different
definitions are never converted or spliced. Dated by the 8-K filing date.

Catalog series, not core series: not in any branch state, diffusion index or rate (register 2026-11-25, S3).
publish=False until the independent review of the extraction has passed.
"""

from __future__ import annotations

from ai_tracker.catalog import Spec
from ai_tracker.sources import orders_backlog as ob

LICENSE = ("SEC EDGAR: public information (sec.gov/privacy). Bara extraherade siffror med källhänvisning publiceras, "
           "aldrig text")
SOURCE = "Kurerad extraktion (curated/orders_backlog.csv) ur resultatpressmeddelanden (8-K, EX-99.1/EX-99), SEC EDGAR"
LAG = 35  # ignored for release-dated rows: results come 3-6 weeks after the quarter
MAX_AGE = {"Q": 200, "A": 430}  # one quarter (or year) plus the filing lag and Dell's fiscal offset

MEASURE = {
    "orders": "Order", "backlog": "Orderstock", "book_to_bill": "Book-to-bill",
    "slot_reservations": "Reservationer av leveransplatser", "backlog_and_slot_reservations":
        "Orderstock och reservationer av leveransplatser", "shipments": "Leveranser", "sales": "Försäljning",
    "leases_signed": "Tecknade nya hyresavtal (hyra per år)", "signed_not_commenced":
        "Tecknade hyresavtal som inte har börjat (hyra per år)", "bookings": "Bokningar",
}
SEGMENT = {
    "total": "", "power": "Power", "wind": "Wind", "electrification": "Electrification", "gas_power": "Gas Power",
    "electrical_americas": "Electrical Americas", "electrical_global": "Electrical Global",
    "electrical": "Electrical (hela sektorn)", "data_centers": "datacenter", "ai_servers": "AI-servrar",
    "gt_1mw": "över 1 MW", "0_1mw": "0–1 MW", "interconnection": "sammankoppling", "other": "övrigt",
}
COMPONENT = {"all": "", "equipment": "utrustning", "services": "service", "dlr_share": "Digital Realtys andel"}
WINDOW = {"q": "kvartal", "ttm": "rullande tolv månader", "ytd": "hittills i räkenskapsåret", "fy": "räkenskapsår",
          "end": "vid periodens slut"}
FORM = {"level": "", "yoy_pct": "förändring mot året före", "qoq_pct": "förändring mot kvartalet före",
        "vs_ye_pct": "förändring mot förra årsskiftet", "ratio": "kvot", "yoy_mult": "multipel av året före"}
ORGANIC = {"organic": "organisk", "cc": "fast valuta", "reported": "rapporterad", "unspecified": "bas ej angiven",
           "na": ""}
UNIT = {"MUSD": "MUSD", "pct": "%", "ratio": "kvot", "GW": "GW", "MW": "MW"}


def _label(d: dict) -> str:
    seg = SEGMENT[d["segment"]]
    comp = COMPONENT[d["component"]]
    if d["company"] == "dlr" and d["component"] == "all":
        comp = "100 % andel"
    parts = [p for p in (seg, comp, WINDOW[d["window"]], FORM[d["form"]], ORGANIC[d["organic"]]) if p]
    return f"{MEASURE[d['measure']]}, {ob.COMPANIES[d['company']]}: {', '.join(parts)} ({UNIT[d['unit']]})"


def _unit(d: dict) -> str:
    if d["unit"] == "MUSD" and d["measure"] in ("leases_signed", "signed_not_commenced"):
        return "MUSD per år"
    return UNIT[d["unit"]]


def _specs() -> tuple[list[Spec], dict[str, dict[str, str]]]:
    if not ob.PATH.exists():
        return [], {}
    df = ob.load()
    specs, gaps = [], {}
    for key in ob.catalog_keys(df):
        rows = ob.definition_rows(df, key)
        d = dict(zip(ob.DEFINITION, ob.definition_of(rows.iloc[0])))
        freq = ob.freq_of(d["window"])
        stop = ob.stopped(df, key)
        closed = stop is not None
        stated = "; ".join(sorted(set(rows[rows["row_type"] == "value"]["metric_as_stated"])))[:200]

        def fetch(k=key):
            return ob.series_frame(ob.load(), k)

        note = (f"Bolagets ord: {stated}. Talen som de står i pressmeddelandet, daterade med 8-K:ns inlämningsdag. "
                "Andra definitioner (organiskt eller inte, kvartal eller tolv månader, procent eller nivå) är egna "
                "serier och skarvas inte. Agentextraherat, stickprov med python -m ai_tracker.orders_check. Se "
                "docs/kallor/order_orderstock.md. "
                + (f"Avslutad: bolaget slutade ange talet i 8-K {stop['filed']} ({stop['id']})." if closed
                   else f"Aktualitet: ett pressmeddelande per kvartal, gräns {MAX_AGE[freq]} dagar."))
        specs.append(Spec(
            key=key, branch=ob.BRANCH[d["company"]], label=_label(d), unit=_unit(d), freq=freq, source=SOURCE,
            fetch=fetch, lag_days=LAG, license=LICENSE, revised=True, publish=False,
            question="Hur snabbt växer order och orderstock före den fysiska utbyggnaden?",
            note=note, closed=closed, max_age_days=None if closed else MAX_AGE[freq]))
        g = ob.gap_periods(df, key)
        if g:
            gaps[key] = g
    return specs, gaps


SPECS, KNOWN_GAP_PERIODS = _specs()
