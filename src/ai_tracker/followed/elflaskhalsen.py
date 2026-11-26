"""EL1 "Elflaskhalsen": the monthly report of the followed question (register 2026-11-26 "EL1").

"Blir el den bindande begränsningen för utbyggnaden?"

Read with F0's symmetric rule (common.read_rule): the pace of four leading quantities on the power side (price, load,
grid backlog in MUSD, gas-turbine backlog in GW) against the change in pace of two following quantities (the inner
layer's capex over four quarters, Digital Realty's signed MW over four quarters), sign -1, k = 2, one row per pair.
The main reading is the grid backlog against the inner layer's capex.

Derived quantities (keys el1_*) are not catalog series: they are computed here from catalog series with
aggregate.derive (a version only once every input is known, known_from = the latest input) and measured with
common.path_measures (the formulas of state.measures). Monthly inputs become quarters by a twelve-month mean ending with
the quarter's last month (register EL1, (b)).

Only rows known on the as-of date are used: the table is cut at the day before anything is computed, so
compute(d, table) equals compute(d, table truncated at d).
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from ai_tracker import observations
from ai_tracker.followed import aggregate as A
from ai_tracker.followed import common as C
from ai_tracker.state import measures as M

QUESTION = "Blir el den bindande begränsningen för utbyggnaden?"
REGISTERED = "2026-11-26"  # the register entry; every quarter published by then was known before it (entry, (f))
FIRST_UNSEEN = "2026Q4"  # the first quarter whose filings come after the entry (entry, (g))

# ------------------------------------------------------------------ inputs (register EL1, (b))

PPI = "us_ppi_elec_commercial_m"
AREAS = {"pjm": "PJM", "erco": "ERCOT", "soco": "Southern Company", "azps": "Arizona Public Service",
         "srp": "Salt River Project"}
LOAD = tuple(f"eia930_avg_{a}_m" for a in AREAS)
DOM = "eia930_avg_pjm_dom_m"  # a subregion of PJM: shown on its own, never added to PJM
GW = "ob_gev_backlog_and_slot_reservations_gas_power_equipment_end_level_gw"
DLR_MW = "ob_dlr_leases_signed_total_dlr_share_q_level_mw"
CAPEX_INNER = "kl_capex4_inner"


def _mean12(series: tuple[str, ...]) -> tuple[A.Term, ...]:
    """The twelve-month mean of the sum of `series` (months m, m-1, ..., m-11)."""
    return tuple(A.Term(s, k, 1.0 / 12.0) for s in series for k in range(12))


FORMULAS = {
    "el1_pris4": A.Formula("el1_pris4", _mean12((PPI,))),
    "el1_last4": A.Formula("el1_last4", _mean12(LOAD)),
    "el1_last4_dom": A.Formula("el1_last4_dom", _mean12((DOM,))),
    "el1_ob_nat": A.Formula("el1_ob_nat", (A.Term("rpo_pwr"), A.Term("rpo_etn"))),
    "el1_dlr_mw4": A.Formula("el1_dlr_mw4", A.sum4(DLR_MW)),
}
MONTHLY = {"el1_pris4", "el1_last4", "el1_last4_dom"}
DERIVED_UNIT = {"el1_pris4": "index dec 1990=100", "el1_last4": "MW", "el1_last4_dom": "MW", "el1_ob_nat": "MUSD",
                "el1_dlr_mw4": "MW"}

# ------------------------------------------------------------------ the locked reading (register EL1, (c))

X = {"pris": "el1_pris4", "last": "el1_last4", "nat": "el1_ob_nat", "gw": GW}
Y = {"capex": CAPEX_INNER, "dlr": "el1_dlr_mw4"}
G = {"pris": 5.0, "last": 2.0, "nat": 10.0, "gw": 10.0}  # log x100 per year
H = {"capex": 5.0, "dlr": 10.0}  # log x100
K = 2
SIGN = -1
MAIN = ("nat", "capex")
PAIRS = [MAIN] + [(x, y) for y in Y for x in X if (x, y) != MAIN]

XNAME = {"pris": "Elpris (PPI, kommersiella kunder)", "last": "Last (fem balansområden)",
         "nat": "Orderstock elnät (Quanta + Eaton, MUSD)", "gw": "Orderstock gasturbiner (GE Vernova, GW)"}
YNAME = {"capex": "capex inre lagret", "dlr": "tecknade MW (Digital Realty)"}

# ------------------------------------------------------------------ description only (no rule)

CONTEXT = {
    "x": ["rpo_pwr", "rpo_etn", "rpo_gev_equipment", "ob_gev_backlog_gas_power_equipment_end_level_gw",
          "ob_gev_slot_reservations_gas_power_equipment_end_level_gw",
          "ob_gev_backlog_electrification_equipment_end_level_musd"],
    "y": ["kl_capex4_outer", "lease_uncommenced_googl", "lease_uncommenced_amzn", "lease_uncommenced_meta",
          "lease_uncommenced_orcl"],
    "suppliers": ["capex_pwr", "capex_etn", "capex_gev"],
}
PLANS = ("plan_crwv_contracted_power_asof_value", "plan_crwv_active_power_asof_value",
         "plan_amzn_power_added_12m_asof_value", "plan_orcl_power_added_q_asof_value")
INNER = {"msft": "capex_msft", "googl": "capex_googl", "amzn": "capex_amzn", "meta": "capex_meta"}
FILERS = {**INNER, "dlr": DLR_MW, "pwr": "rpo_pwr", "etn": "rpo_etn", "gev": GW}
FILER_NAMES = {"msft": "Microsoft", "googl": "Alphabet", "amzn": "Amazon", "meta": "Meta", "dlr": "Digital Realty",
               "pwr": "Quanta Services", "etn": "Eaton", "gev": "GE Vernova"}
LABEL = {
    "el1_pris4": "Elpris, PPI kommersiella kunder (tolv månader)", "el1_last4": "Last, fem områden (tolv månader)",
    "el1_last4_dom": "Last, Dominion (tolv månader)", "el1_ob_nat": "Orderstock elnät, Quanta + Eaton",
    "el1_dlr_mw4": "Tecknade MW, Digital Realty (fyra kvartal)", GW: "Gasturbiner, orderstock och reservationer",
    "rpo_pwr": "Quanta Services, RPO", "rpo_etn": "Eaton, orderstock", "rpo_gev_equipment": "GE Vernova, RPO utrustning",
    "ob_gev_backlog_gas_power_equipment_end_level_gw": "Gasturbiner, orderstock",
    "ob_gev_slot_reservations_gas_power_equipment_end_level_gw": "Gasturbiner, reservationer",
    "ob_gev_backlog_electrification_equipment_end_level_musd": "GE Vernova, orderstock Electrification",
    CAPEX_INNER: "Capex inre lagret (fyra kvartal)", "kl_capex4_outer": "Capex yttre lagret (fyra kvartal)",
    "lease_uncommenced_googl": "Alphabet, leasing som inte börjat", "lease_uncommenced_amzn":
        "Amazon, leasing som inte börjat", "lease_uncommenced_meta": "Meta, leasing som inte börjat",
    "lease_uncommenced_orcl": "Oracle, leasing som inte börjat", "capex_pwr": "Quanta Services, capex i kvartalet",
    "capex_etn": "Eaton, capex i kvartalet", "capex_gev": "GE Vernova, capex i kvartalet",
}


def used_series() -> set[str]:
    """Every catalog series the report reads."""
    out = {GW, CAPEX_INNER, *CONTEXT["x"], *CONTEXT["y"], *CONTEXT["suppliers"], *PLANS, *FILERS.values()}
    for f in FORMULAS.values():
        out.update(f.components)
    return out


# ------------------------------------------------------------------ derived measures


def derived_rows(f: A.Formula, table: pd.DataFrame) -> pd.DataFrame:
    """Release-dated quarterly rows of a derived quantity (period, value, known_from, source). A monthly formula is
    derived per month and only the quarter's last month is kept, labelled with its quarter."""
    if f.key in MONTHLY:
        rows = A.derive(f, table, freq="M")
        if rows.empty:
            return rows
        per = [pd.Period(p, freq="M") for p in rows["period"]]
        keep = [p.month % 3 == 0 for p in per]
        rows = rows[keep].copy()
        rows["period"] = [C.quarter(p) for p, k in zip(per, keep) if k]
        return rows.reset_index(drop=True)
    return A.derive(f, table)


def missing_next(f: A.Formula, table: pd.DataFrame, period: str | None, when) -> dict:
    """What the quarter after `period` still lacks on `when`: {"period", "inputs": {series: [periods]}}."""
    if period is None:
        return {}
    nxt = C.plus(period, 1)
    if f.key in MONTHLY:
        last_month = str(pd.Period(nxt, freq=A.QFREQ).asfreq("M", "end"))
        miss = A.missing(f, table, last_month, when, freq="M")
    else:
        miss = A.missing(f, table, nxt, when)
    by: dict[str, list[str]] = {}
    for s, p in miss:
        by.setdefault(s, []).append(p)
    return {"period": nxt, "inputs": {s: sorted(ps) for s, ps in by.items()}}


def derived_measure(key: str, table: pd.DataFrame, when) -> dict:
    """measure()-shaped dict of a derived quantity as of `when` (the table is already cut at `when`)."""
    f = FORMULAS[key]
    base = {"series": key, "derived": True, "components": list(f.components), "unit": DERIVED_UNIT[key],
            "method": "log", "pace_unit": "log ×100 per år", "surprise_basis": "B1 drift (log x100)"}
    rows = derived_rows(f, table)
    if rows.empty:
        return {**base, "available": False, "missing_next": {}}
    last = rows.sort_values("known_from", kind="stable").groupby("period").last()
    pm = C.path_measures(last["value"].to_dict(), "log")
    ok = pm[pm["level"].notna()]
    p = ok.index[-1]
    sources = sorted(set(rows["source"]))
    r = ok.loc[p]
    out = {**base, "available": True, "period": p, "known_from": str(pd.Timestamp(last.loc[p, "known_from"]).date()),
           "level": C.num(r["level"]), "pace": C.num(r["pace"]), "change": C.num(r["change"]),
           "surprise": C.num(r["surprise"]), "sources": sources,
           "path": {q: {c: C.num(v) for c, v in pm.loc[q, ["level", "pace", "change"]].items()} for q in pm.index}}
    out["missing_next"] = missing_next(f, table, p, when)
    return out


# ------------------------------------------------------------------ compute


def _cut(table: pd.DataFrame | None, when: pd.Timestamp) -> pd.DataFrame:
    table = observations.load() if table is None else table
    t = table[table["series"].isin(used_series())].copy()
    t["known_from"] = pd.to_datetime(t["known_from"])
    if "fetched_at" in t:
        t["fetched_at"] = pd.to_datetime(t["fetched_at"])
    return t[t["known_from"] <= when].reset_index(drop=True)


def plans(table: pd.DataFrame, when) -> list[dict]:
    out = []
    for k in PLANS:
        d = C.asof_rows(table, k, when)
        if d.empty:
            continue
        last = d.iloc[-1]
        out.append({"series": k, "period": str(last.period), "value": float(last.value),
                    "known_from": str(pd.Timestamp(last.known_from).date())})
    return out


def next_unseen(r: dict) -> tuple[str, str | None]:
    """The first reading with a Y quarter published after the entry: the inner layer's capex for max(next quarter,
    2026Q4) once all four inner companies have filed (estimated end of quarter + each company's median lag)."""
    y = r["measures"].get(CAPEX_INNER, {})
    t = y.get("period") if y.get("available") else None
    target = FIRST_UNSEEN if t is None else max(C.plus(t, 1), FIRST_UNSEEN, key=lambda q: pd.Period(q, freq=A.QFREQ))
    end = pd.Period(target, freq=A.QFREQ).end_time.normalize()
    lags = {x["company"]: x["lag_days_median"] for x in r["next_filings"]}
    if any(c not in lags for c in INNER):
        return f"inre lagrets capex för {target} när alla fyra har lämnat in (ingen uppskattning ännu)", None
    day = str((end + pd.Timedelta(days=max(lags[c] for c in INNER))).date())
    text = f"inre lagrets capex för {target} när alla fyra har lämnat in, omkring {day}"
    if "dlr" in lags:
        text += f"; Digital Realty {target} omkring {(end + pd.Timedelta(days=lags['dlr'])).date()}"
    return text, day


def compute(as_of, table: pd.DataFrame | None = None) -> dict:
    when = pd.Timestamp(as_of)
    t = _cut(table, when)
    ctx = M.Context(table=t)
    ms: dict[str, dict] = {}
    for key in FORMULAS:
        ms[key] = derived_measure(key, t, when)
    for key in (GW, CAPEX_INNER, *CONTEXT["x"], *CONTEXT["y"], *CONTEXT["suppliers"]):
        if key not in ms:
            ms[key] = C.measure(key, when, ctx)
    readings = {}
    for x, y in PAIRS:
        r = C.read_measures(ms[X[x]], ms[Y[y]], x_stat="pace", g=G[x], h=H[y], k=K, sign=SIGN)
        readings[f"{x}|{y}"] = {**r, "x": x, "y": y}
    report = {
        "question": QUESTION, "as_of": str(when.date()), "generated": str(date.today()),
        "seen_before_register": str(when.date()) <= REGISTERED,
        "params": {"g": G, "h": H, "k": K, "sign": SIGN, "main": "|".join(MAIN)},
        "measures": ms, "readings": readings, "plans": plans(t, when),
        "next_filings": C.next_filings(t, when, FILERS),
    }
    report["next_unseen"], report["next_unseen_date"] = next_unseen(report)
    return report


# ------------------------------------------------------------------ render

_f = C.fmt


def _who(key: str) -> str:
    return LABEL.get(key, key)


def _level(unit: str):
    if unit == "MUSD":
        return C.fmt_bn
    if unit in ("MW", "GW"):
        return lambda x: "–" if C.num(x) is None else f"{_f(x, 0 if unit == 'MW' else 1)} {unit}"
    return lambda x: _f(x, 1)


def _table(ms: dict, keys: list[str]) -> list[str]:
    lines = list(C.TABLE_HEAD)
    for k in keys:
        unit = ms[k].get("unit") or ""
        lines.append(C.measure_table(ms, [k], _level(unit), _who)[-1])
    return lines


def _missing_lines(ms: dict, keys: list[str]) -> list[str]:
    out = []
    for k in keys:
        mn = ms[k].get("missing_next") or {}
        if mn.get("inputs"):
            parts = []
            for s, ps in mn["inputs"].items():
                parts.append(f"`{s}` {ps[0]}" if len(ps) == 1 else f"`{s}` {ps[0]}–{ps[-1]}")
            out.append(f"- {_who(k)}: {mn['period']} saknar på dagen {', '.join(parts)}.")
    return out


def short(r: dict) -> str:
    """The outcome with the impulse's direction for 'talar för' and 'talar emot'."""
    o = next((x for x in r["origins"] if x["origin"] == r["origin"]), None)
    text = C.OUTCOME_TEXT[r["outcome"]]
    if o is not None and r["outcome"] in (C.FOR, C.AGAINST):
        text += ", uppåt" if o["direction"] > 0 else ", nedåt"
    return text


def render(r: dict) -> str:
    ms = r["measures"]
    p = r["params"]
    out = [f"# Elflaskhalsen per {r['as_of']}", "", f"**Frågan:** {r['question']}", "",
           "Elsidan (pris, last och orderstock för elnät och gasturbiner) mot utbyggnadens takt (capex i det inre lagret "
           "och tecknade MW hos Digital Realty). Takt = 100 × ln(värdet / värdet fyra kvartal tidigare). Förändring i "
           "takt = mot två kvartal tidigare. Överraskning = mot den naiva baslinjen B1 (samma takt som de fyra senaste "
           "kvartalen). Månadsserier blir kvartal som medel av de tolv månader som slutar med kvartalets sista månad. "
           "Bara data kända på dagen. Registret: `docs/mattregister.md`, 2026-11-26 EL1.", ""]

    out += ["## 1. Elsidan: pris och last", "",
            "PPI för el till kommersiella kunder (BLS) och medellast per månad ur EIA-930, summerad över PJM, ERCOT, "
            "Southern Company, APS och SRP. Dominion är en delregion av PJM och visas för sig.", ""]
    keys = ["el1_pris4", "el1_last4", "el1_last4_dom"]
    out += _table(ms, keys)
    out += _missing_lines(ms, keys)
    if "backfill" in (ms["el1_last4"].get("sources") or []):
        out += ["", "Lasten är backfill: EIA-930 har inga daterade versioner före 2026-11-23, så äldre månader har "
                "dagens värden (revideringar läcker in), och när EIA:s justerade kolumn först publicerades är inte belagt."]

    out += ["", "## 2. Elsidan: orderstock för elnät och gasturbiner", "",
            "Orderstock för elnät = Quantas RPO + Eatons totala orderstock (fasta order) vid kvartalets slut. "
            "Gasturbiner = GE Vernovas orderstock och reservationer av leveransplatser i GW (extraktion ur "
            "pressmeddelanden, `publish=False`).", ""]
    keys = ["el1_ob_nat", GW, "rpo_pwr", "rpo_etn", "rpo_gev_equipment",
            "ob_gev_backlog_gas_power_equipment_end_level_gw",
            "ob_gev_slot_reservations_gas_power_equipment_end_level_gw",
            "ob_gev_backlog_electrification_equipment_end_level_musd"]
    out += _table(ms, keys)
    out += _missing_lines(ms, ["el1_ob_nat"])

    out += ["", "## 3. Utbyggnadens takt", "",
            "Capex över fyra kvartal (KL1:s lageraggregat) och Digital Realtys tecknade hyresavtal i MW över fyra "
            "kvartal (bolagets andel, extraktion, `publish=False`). Yttre lagret och leasing som inte börjat är "
            "beskrivning och ingår inte i läsregeln.", ""]
    keys = [CAPEX_INNER, "el1_dlr_mw4", *CONTEXT["y"]]
    out += _table(ms, keys)
    out += _missing_lines(ms, ["el1_dlr_mw4"])

    out += ["", "## 4. Leverantörernas egen capex (beskrivning)", "",
            "Kvartalets capex, takt mot samma kvartal året före. Om leverantörerna bygger ut sin egen kapacitet lättar "
            "flaskhalsen med tiden.", ""]
    out += _table(ms, CONTEXT["suppliers"])
    if r["plans"]:
        out += ["", "**Kraftplaner** (senaste uttalande per serie, MW):", ""]
        for x in r["plans"]:
            out.append(f"- `{x['series']}` {x['period']}: {_f(x['value'], 0)} MW (known_from {x['known_from']})")

    out += ["", "## 5. Läsregeln, mekaniskt", "",
            f"F0:s symmetriska regel: X:s takt mot Y:s förändring i takt, tecken −1, fönster {p['k']} kvartal efter "
            "ursprunget. Gränser (låsta): " + ", ".join(f"{XNAME[x]} ±{_f(G[x], 1)}" for x in X) + "; "
            + ", ".join(f"{YNAME[y]} ±{_f(H[y], 1)}" for y in Y) + ". En rad per par, ingen sammanslagning.", "",
            "- **Talar för, uppåt:** elsidan stramades åt (X ≥ +g) och takten bromsade (Y ≤ −h). **Talar för, nedåt:** "
            "elsidan lättade (X ≤ −g) och takten ökade (Y ≥ +h).",
            "- **Talar emot:** takten följde elsidan åt samma håll. Uppåt pekar det på en gemensam efterfrågan och på "
            "att elen inte band, nedåt på att efterfrågan föll.",
            "- En negativ förändring i takt betyder att tillväxten avtar, inte att capex minskar. Utslaget är en "
            "beskrivning, inget test.", "",
            "Takten för X gör att en ihållande åtstramning räknas som en impuls varje kvartal. Har X impulser åt bara "
            "ett håll avgörs utslaget i praktiken av Y, och den andra riktningen prövas inte. Hur ofta det hänt står "
            "under varje rad.", ""]
    if r.get("seen_before_register"):
        out += [f"Alla kvartal i den här läsningen var publicerade före registerposten {REGISTERED}, och Y:s senaste "
                "värden för capex var sedda före posten (posten, avsnitt (f)). Läsningen är därför inget utfall på "
                f"osedda data. Den första osedda läsningen: {r['next_unseen']}.", ""]
    for y in Y:
        out += [f"**Mot {YNAME[y]}:**", ""]
        for x in X:
            rr = r["readings"][f"{x}|{y}"]
            label = f"{XNAME[x]}{' (huvudläsning)' if (x, y) == MAIN else ''}"
            lines = C.reading_lines(rr, label)
            lines[0] = lines[0].replace(f"**{label}:** {rr['text']}", f"**{label}:** {short(rr)}", 1)
            out += lines
        out.append("")

    out += ["## 6. Att bevaka", "", "Nästa inlämning per bolag, uppskattad som nästa kvartals slut plus medianen av "
            "avståndet för de åtta senaste inlämningarna:", ""]
    for x in r["next_filings"]:
        late = (f" (väntas nu; därefter {x['then_period']} omkring {x['then_estimated']})" if x["overdue"] else "")
        out.append(f"- {FILER_NAMES[x['company']]}: {x['next_period']} omkring {x['estimated']}{late} "
                   f"(median {x['lag_days_median']} dagar, senast {x['last_filed']}, `{x['series']}`)")
    out += [f"- Månadsserierna (PPI, EIA-930) fyller kvartalet efter hand. Första osedda läsningen: {r['next_unseen']}.",
            "", "## 7. Förbehåll", "",
            "- Med 3–30 kvartal per rad och åtta rader är detta en beskrivning och inget test. Några rader väntas ge "
            "\"talar för\" eller \"talar emot\" av en slump, och förändringen i takt vänder ofta av sig själv.",
            "- Elnät och gasturbiner drivs också av annat än datacenter: elbolagens nät, förnybart, industri och export. "
            "Quantas RPO omfattar förnybart, telekom och rörledningar, och Eatons orderstock gäller hela bolaget.",
            "- Förvärv blåser upp orderstockens takt: Prolec GE i GE Vernovas orderstock från 2026Q1, Boyd Thermal i "
            "Eatons Electrical Global från 2026-03-12 (R19).",
            "- Elpriset är reglerade tariffer som speglar bränsle och nätkostnader med fördröjning, inte knapphetspriset. "
            "PPI-serien är regeldaterad, så det senaste kvartalet släpar. Elpriset har en nominell drift uppåt.",
            "- Lasten är medellast och inte topplast, påverkas av väder och täcker fem områden, inte hela USA.",
            "- Gasturbinerna och Digital Realtys MW är en extraktion (S3, granskad i R19, `publish=False`). Digital "
            "Realtys andel före 2025 är inte belagd (R19, F-4).",
            "- Y för capex är hela capex, där servrar och chip är största delen. En begränsning i el syns troligen "
            "tidigare i byggen och leasing.",
            "- \"Bindande\" kan inte visas: regeln ser samvariation i riktning, inte ett skuggpris, och X och Y har en "
            "gemensam drivkraft.",
            "- Utanför ramen: köer för nätanslutning (LBNL), ERCOT:s kö för stora laster, PJM:s kapacitetspriser "
            "(klass `nej`, visas inte) och EIA-860M. Förslag med licensfråga, se registret, avsnitt (i).", ""]
    return "\n".join(out)


# ------------------------------------------------------------------ antenna (register EL1, (h))


def antenna(r: dict) -> dict:
    """EL1's row in `antenner`: the main reading (grid backlog against the inner layer's capex) and the other seven
    rows, the backlog's pace and the capex change as facts."""
    main = r["readings"]["|".join(MAIN)]
    facts = {}
    for x, y in PAIRS[1:]:
        rr = r["readings"][f"{x}|{y}"]
        facts[f"{XNAME[x]} mot {YNAME[y]}"] = f"{short(rr)} ({rr['t'] or '–'})"
    nat, cap = r["measures"]["el1_ob_nat"], r["measures"][CAPEX_INNER]
    facts["Orderstock elnät, takt"] = f"{_f(nat.get('pace'), 1, True)} ({nat.get('period') or '–'})"
    facts["Capex inre lagret, förändring i takt"] = f"{_f(cap.get('change'), 1, True)} ({cap.get('period') or '–'})"
    hh = main["history"]
    facts["Huvudläsningen, impulser upp/ned"] = f"{hh['impulses_up']}/{hh['impulses_down']} av {hh['n_x']} ursprung"
    return C.antenna_row(QUESTION, main["outcome"], short(main), main["t"], facts, r["next_unseen"],
                         r["next_unseen_date"])
