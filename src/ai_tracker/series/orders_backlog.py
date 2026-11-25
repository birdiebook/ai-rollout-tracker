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
    "orders_new_contracts": "Order bland nya kontrakt (utan konverterade reservationer)",
    "orders_converted": "Reservationer som blev order",
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


# Series notes after review R19 (correction track X16, 2026-11-25). Swedish, like the rest of the catalog text.
GEV_NEW = "ob_gev_orders_new_contracts_gas_power_equipment_q_level_gw"
GEV_CONVERTED = "ob_gev_orders_converted_gas_power_equipment_q_level_gw"
_GEV_INTAKE = (f"Kvartalets orderingång i GW är summan av {GEV_NEW} och {GEV_CONVERTED}. Den bildas inte som "
               "serie. Orderstocken i GW går ihop med båda: förra kvartalets orderstock + order + konverteringar − "
               "levererade GW (som inte kodas) = orderstocken, inom 1 GW. 2025Q1 ('gas turbine orders') har en annan "
               "uppställning och skarvas inte (registret 2026-11-25, rättning efter R19).")
EXTRA_NOTES = {
    GEV_NEW: "Bara ordren bland kvartalets nya kontrakt. Reservationer som blev order i kvartalet ingår inte. "
             + _GEV_INTAKE,
    GEV_CONVERTED: "Reservationer av leveransplatser som blev order i kvartalet. " + _GEV_INTAKE,
}
DLR_SHARE_NOTE = (
    "Vilken andel totalen gäller anges inte i pressmeddelandena före 2025. Andelen står i texten från 2025Q1 och i "
    "tabellen från 2025Q3. Tidigare kvartal kodas som Digital Realtys andel (tolkning 9). Belägg: tabellens summa "
    "2025Q1 och 2025Q2 är lika med textens tal vid Digital Realtys andel, och tilläggsmaterialets tolvmånaderssummor "
    "från 2025Q1 lägger ihop 2024Q2–2024Q4 som de rapporterades. För 2021Q4–2024Q1 är andelen obelagd: fotnoten till "
    "ett närliggande mått bytte behandling av samägda bolag 2023Q1 och 2024Q1. Pröva inte serien som kärnserie innan "
    "basen är belagd (granskning R19, F-4).")
ETN_SCOPE_NOTE = (
    "Omfattning: tillväxten anges utan bas, alltså inte som organisk. Pressmeddelandet säger inte om köpta bolags "
    "orderstock "
    "ingår. Fibrebond (köpt 2025-04-01) redovisas i Electrical Americas och Boyd Thermal (köpt 2026-03-12) i "
    "Electrical Global. Från 2026Q1 heter talet 'total backlog' (granskning R19, N-5).")


def _extra_note(key: str, d: dict) -> str:
    if key in EXTRA_NOTES:
        return EXTRA_NOTES[key] + " "
    if d["company"] == "dlr" and d["measure"] == "leases_signed" and d["component"] == "dlr_share":
        return DLR_SHARE_NOTE + " "
    if d["company"] == "etn" and d["measure"] == "backlog" and d["organic"] == "unspecified":
        return ETN_SCOPE_NOTE + " "
    return ""


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

        note = (f"Bolagets ord: {stated}. " + _extra_note(key, d)
                + "Talen som de står i pressmeddelandet, daterade med 8-K:ns inlämningsdag. "
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
