"""LT1 "Ledtid i stacken": the monthly report of the followed question (register 2026-11-26 "LT1").

"Rör sig order och orderstock hos leverantörerna (kraft, kylning, elnät, nät, servrar, datacenterleasing) före eller
efter capex-takten hos hyperskalarna och de yttre lagren, och ändras ledtiden?"

Suppliers (L1 power and grid RPO, L2 networking and server RPO, L3 Equinix RPO, O1 Eaton's organic order growth, O2
Digital Realty's new leases over four quarters) against buyers (capex over four quarters, inner and outer layer as KL1).
Every reading is F0's symmetric rule (common.read_rule) with the registered parameters: X = change in pace, Y = change in
pace, g = h = 5 for buyers and 10 for suppliers (log x100), k = 2 and k = 4, sign +1, both directions ("före": X =
supplier, Y = buyer; "efter": the roles swapped), one row per X. The lead time is described, not read: for k = 4, the
quarters from an origin to the quarter that decided a "talar för".

Only rows known on the as-of date: the table is cut at the day before anything is derived (the lt1_ aggregates and KL1's
capex sums are derived here from their components with the catalog's own formulas, so the report does not depend on
when the derived rows were last fetched). compute(d, table) equals compute(d, table cut at d).
"""

from __future__ import annotations

from datetime import date
from statistics import median

import numpy as np
import pandas as pd

from ai_tracker import observations
from ai_tracker.followed import aggregate as A
from ai_tracker.followed import common as C
from ai_tracker.series import kreditlagret as KS
from ai_tracker.series import ledtid as LS
from ai_tracker.state import measures as M

QUESTION = ("Rör sig order och orderstock hos leverantörerna (kraft, kylning, elnät, nät, servrar, datacenterleasing) "
            "före eller efter capex-takten hos hyperskalarna och de yttre lagren, och ändras ledtiden?")
REGISTERED = "2026-11-26"  # the register entry; every quarter known by then was known before it (entry, (f))

# ------------------------------------------------------------------ registered parameters (entry, (c))

G_BUYER = 5.0  # g = h for the buyers' capex over four quarters, change in pace, log x100
G_SUPPLIER = 10.0  # g = h for the suppliers' backlog and orders, change in pace, log x100
WINDOWS = (2, 4)
SIGN = 1
LEAD_WINDOW = 4  # the lead time is described on the k = 4 readings
MAIN = ("L1", "inner", "fore", 2)

EATON_ORDERS = "ob_etn_orders_electrical_americas_ttm_yoy_pct_organic_pct"
BUYERS = {"inner": "kl_capex4_inner", "outer": "kl_capex4_outer"}
BUYER_NAMES = {"inner": "K-inre (Microsoft, Alphabet, Amazon, Meta)", "outer": "K-yttre (Oracle, CoreWeave, Nebius, IREN)"}
BUYER_SHORT = {"inner": "K-inre", "outer": "K-yttre"}
SUPPLIERS = {  # row -> (series, name, from the S3 extraction)
    "L1": ("lt1_rpo_power", "L1 Kraft och elnät (Eaton, Quanta)", False),
    "L2": ("lt1_rpo_net", "L2 Nät och servrar (Cisco, Dell, Super Micro)", False),
    "L3": ("rpo_eqix", "L3 Datacenter (Equinix, RPO)", False),
    "O1": (EATON_ORDERS, "O1 Eatons order (Electrical Americas, organisk, 12 mån)", True),
    "O2": ("lt1_dlr_bookings4", "O2 Digital Realtys nya avtal (fyra kvartal)", True),
}
ROWS = [(s, "inner") for s in SUPPLIERS] + [("L1", "outer")]
DIRECTIONS = {"fore": "före", "efter": "efter"}
# documented acquisitions per row: (name, quarter a); origins a, a+1, a+4 and a+5 are marked (entry, (c))
ACQUISITIONS = {"L1": (("Eaton–Fibrebond", "2025Q2"), ("Eaton–Boyd Thermal", "2026Q1")),
                "L2": (("Cisco–Splunk", "2024Q1"),)}
ACQ_OFFSETS = (0, 1, 4, 5)
UNCHECKED_ACQ = "Förvärv hos Quanta, Dell, Super Micro och Equinix är inte kontrollerade."

CONTEXT = {  # (title, keys): measures shown as context, not read
    "members": ("Medlemmarna i L1 och L2, och leverantörer utanför aggregaten",
                ["rpo_etn", "rpo_pwr", "rpo_gev", "rpo_csco", "rpo_dell", "rpo_smci", "rpo_anet", "rpo_hpe"]),
    "orders": ("Order och orderstock ur pressmeddelandena (S3, publish=False i väntan på granskningen)",
               ["ob_gev_orders_total_q_level_musd", "ob_gev_backlog_total_end_level_musd",
                "ob_dell_orders_ai_servers_q_level_musd", "ob_dell_backlog_ai_servers_end_level_musd",
                "ob_dlr_leases_signed_total_dlr_share_q_level_musd"]),
    "revenue": ("Leverantörernas intäkter (leveranser)",
                ["rev_etn", "rev_pwr", "rev_gev", "rev_vrt", "rev_csco", "rev_dell", "rev_smci", "rev_anet",
                 "rev_eqix", "rev_dlr"]),
    "buyers": ("Capex över fyra kvartal per köpare",
               [f"kl_capex4_{c}" for c in (*KS.INNER, *KS.OUTER)]),
}
WHO = {"etn": "Eaton", "pwr": "Quanta Services", "gev": "GE Vernova", "vrt": "Vertiv", "csco": "Cisco", "dell": "Dell",
       "smci": "Super Micro", "anet": "Arista", "hpe": "HPE", "eqix": "Equinix", "dlr": "Digital Realty",
       EATON_ORDERS: "O1 Eaton, order (Electrical Americas, organisk, 12 mån)", "lt1_rpo_power": "L1 Kraft och elnät", "lt1_rpo_net": "L2 Nät och servrar", "lt1_dlr_bookings4":
       "O2 Digital Realty, nya avtal (fyra kvartal)", "kl_capex4_inner": "K-inre", "kl_capex4_outer": "K-yttre",
       "ob_gev_orders_total_q_level_musd": "GE Vernova, order (kvartal)",
       "ob_gev_backlog_total_end_level_musd": "GE Vernova, orderstock",
       "ob_dell_orders_ai_servers_q_level_musd": "Dell, AI-order (kvartal)",
       "ob_dell_backlog_ai_servers_end_level_musd": "Dell, AI-orderstock",
       "ob_dlr_leases_signed_total_dlr_share_q_level_musd": "Digital Realty, nya avtal (kvartal)",
       **{f"kl_capex4_{c}": KS.NAMES[c] for c in (*KS.INNER, *KS.OUTER)}}
# filings that bring each quantity's next quarter (company -> a quarterly series that its periodic filing carries)
FILERS = {**{c: f"capex_{c}" for c in (*KS.INNER, *KS.OUTER)}, "etn": "rpo_etn", "pwr": "rpo_pwr", "csco": "rpo_csco",
          "dell": "rpo_dell", "smci": "rpo_smci", "eqix": "rpo_eqix", "dlr": "ob_dlr_leases_signed_total_dlr_share_q_level_musd"}
MEMBERS = {"inner": KS.INNER, "outer": KS.OUTER, "L1": LS.POWER, "L2": LS.NET, "L3": ("eqix",), "O1": ("etn",),
           "O2": ("dlr",)}


# ------------------------------------------------------------------ the table on the day


def formulas() -> dict[str, A.Formula]:
    """Every derived input of the report: the lt1_ aggregates and KL1's capex sums (inner, outer, per buyer)."""
    out = dict(LS.FORMULAS)
    out["kl_capex4_inner"] = KS.formula("capex4", "inner")
    out["kl_capex4_outer"] = KS.formula("capex4", "outer")
    for c in (*KS.INNER, *KS.OUTER):
        out[f"kl_capex4_{c}"] = KS.formula("capex4", c)
    return out


def table_on(as_of, table: pd.DataFrame | None = None) -> pd.DataFrame:
    """The observation table cut at `as_of` (known_from <= as_of), with the derived inputs re-derived from it."""
    t = observations.load() if table is None else table
    t = t.copy()
    t["known_from"] = pd.to_datetime(t["known_from"])
    t = t[t["known_from"] <= pd.Timestamp(as_of)]
    fs = formulas()
    parts = [t[~t["series"].isin(fs)]]
    for key, f in fs.items():
        d = A.derive(f, t[t["series"].isin(f.components)])
        if d.empty:
            continue
        d = d.assign(series=key, freq="Q", fetched_at=pd.NaT)
        parts.append(d[observations.COLUMNS])
    out = pd.concat(parts, ignore_index=True)
    out["fetched_at"] = pd.to_datetime(out["fetched_at"])
    return out


# ------------------------------------------------------------------ measures


def yoy_measure(table: pd.DataFrame, key: str, when) -> dict:
    """A growth rate against a year earlier in percent (S3's ttm yoy series) as measures (register entry, (a), O1):
    pace = 100 ln(1 + v/100) (log x100 over a year), change = pace - pace two quarters earlier, level = v, no surprise
    (B1 is not registered for a growth rate). Same keys as common.measure."""
    d = C.asof_rows(table, key, when)
    if d.empty:
        return {"series": key, "available": False}
    s = pd.Series(d["value"].to_numpy(dtype=float), index=pd.PeriodIndex(d["period"].astype(str), freq=C.QFREQ))
    s = s.sort_index()
    s = s.reindex(pd.period_range(s.index[0], s.index[-1], freq=C.QFREQ))
    pace = 100.0 * np.log1p(s.where(s > -100.0) / 100.0)
    change = pace - pace.shift(C.CHANGE_LAG)
    last = str(s.index[-1])
    kf = d.set_index(d["period"].astype(str))["known_from"]
    path = {str(p): {"level": C.num(s[p]), "pace": C.num(pace[p]), "change": C.num(change[p])} for p in s.index}
    return {"series": key, "available": True, "period": last, "known_from": str(pd.Timestamp(kf[last]).date()),
            "level": C.num(s.iloc[-1]), "pace": C.num(pace.iloc[-1]), "change": C.num(change.iloc[-1]),
            "surprise": None, "surprise_basis": "B1 inte registrerad för en tillväxttakt", "pace_unit": "log ×100 per år",
            "unit": "%", "method": "yoy", "path": path}


def measure_of(key: str, table: pd.DataFrame, when, ctx: M.Context) -> dict:
    return yoy_measure(table, key, when) if key == EATON_ORDERS else C.measure(key, when, ctx)


# ------------------------------------------------------------------ readings (entry, (c))


def limits(direction: str) -> tuple[float, float]:
    """(g, h) of a direction: X's limit and Y's limit, each the limit of its quantity."""
    return (G_SUPPLIER, G_BUYER) if direction == "fore" else (G_BUYER, G_SUPPLIER)


def acquisition_quarters(row: str) -> dict[str, str]:
    """{origin quarter: acquisition} for the origins whose change in pace an acquisition touches."""
    out = {}
    for name, a in ACQUISITIONS.get(row, ()):
        for j in ACQ_OFFSETS:
            out.setdefault(C.plus(a, j), name)
    return out


def origins(x: dict, y: dict, t: str | None, *, g: float, h: float, k: int) -> list[dict]:
    """Every origin before t with X known, with its outcome (the rows behind read_rule's history counts)."""
    if t is None:
        return []
    tp = pd.Period(t, freq=C.QFREQ)
    qs = sorted({q for q in x if pd.Period(q, freq=C.QFREQ) < tp}, key=lambda q: pd.Period(q, freq=C.QFREQ))
    out = [C.origin_outcome(q, x, y, t, g=g, h=h, k=k, sign=SIGN) for q in qs]
    return [o for o in out if o["x"] is not None]


def lag(o: dict) -> int | None:
    """Quarters from an origin to the quarter that decided it (only for "talar för")."""
    if o["outcome"] != C.FOR or not o["decided_at"]:
        return None
    return int((pd.Period(o["decided_at"], freq=C.QFREQ) - pd.Period(o["origin"], freq=C.QFREQ)).n)


def reading(row: str, buyer: str, direction: str, k: int, ms: dict[str, dict]) -> dict:
    sup, buy = ms[SUPPLIERS[row][0]], ms[BUYERS[buyer]]
    mx, my = (sup, buy) if direction == "fore" else (buy, sup)
    g, h = limits(direction)
    r = C.read_measures(mx, my, x_stat="change", g=g, k=k, h=h, sign=SIGN)
    acq = acquisition_quarters(row)
    hist = origins(C.series_of(mx, "change"), C.series_of(my, "change"), r["t"], g=g, h=h, k=k)
    for o in hist + r["origins"]:
        # the mark goes where the supplier's change in pace is read: the origin in "före" (X = supplier), the
        # deciding quarter in "efter" (Y = supplier); the outcome is not changed (register entry, (c), "Förvärv")
        o["acquisition"] = acq.get(o["origin"]) if direction == "fore" else acq.get(o["decided_at"] or "")
    lags = [{"origin": o["origin"], "direction": o["direction"], "lag": lag(o), "acquisition": o["acquisition"]}
            for o in hist if lag(o) is not None]
    picked = next((o for o in r["origins"] if o["origin"] == r["origin"]), None)
    r.update(row=row, buyer=buyer, direction=direction, k=k, history_rows=hist, lags=lags,
             origin_acquisition=picked["acquisition"] if picked else None)
    return r


def lead_time(r: dict) -> dict:
    """The latest lead time and the median of the earlier ones in one k = 4 reading (a description)."""
    lags = r["lags"]
    if not lags:
        return {"n": 0, "latest": None, "latest_origin": None, "median_before": None, "n_before": 0}
    before = [x["lag"] for x in lags[:-1]]
    return {"n": len(lags), "latest": lags[-1]["lag"], "latest_origin": lags[-1]["origin"],
            "median_before": float(median(before)) if before else None, "n_before": len(before),
            "by_origin": [(x["origin"], x["lag"], x["direction"]) for x in lags]}


# ------------------------------------------------------------------ next filings and the unseen reading


def next_of(quantity: str, t: str | None, filings: list[dict]) -> dict:
    """When the quantity's next quarter (t + 1) becomes known: every member must have filed it."""
    if t is None:
        return {"quantity": quantity, "period": None, "estimated": None, "missing": list(MEMBERS[quantity])}
    p = C.plus(t, 1)
    by = {f["company"]: f for f in filings}
    days, missing = [], []
    for c in MEMBERS[quantity]:
        f = by.get(c)
        if f is None:
            missing.append(c)
            continue
        if pd.Period(f["last_period"], freq=C.QFREQ) >= pd.Period(p, freq=C.QFREQ):
            continue
        steps = (pd.Period(p, freq=C.QFREQ) - pd.Period(f["next_period"], freq=C.QFREQ)).n
        days.append(pd.Timestamp(f["estimated"]) + pd.Timedelta(days=91 * max(steps, 0)))
    est = str(max(days).date()) if days and not missing else None
    return {"quantity": quantity, "period": p, "estimated": est, "missing": missing}


def next_unseen(r: dict) -> tuple[str, str | None]:
    """The earliest new reading of any row after the register day, and the main reading's next quarter."""
    nx = r["next"]
    cands = []
    for row, buyer in ROWS:
        for direction in DIRECTIONS:
            q = nx.get(buyer if direction == "fore" else row)  # a new t comes with Y's next quarter
            if q and q["estimated"] and q["estimated"] > REGISTERED:
                cands.append((q["estimated"], row, buyer, direction, q["period"]))
    if not cands:
        return f"med inlämningar efter {REGISTERED} (inga uppskattade ännu)", None
    day, row, buyer, direction, period = min(cands)
    text = f"{row} {DIRECTIONS[direction]} {BUYER_SHORT[buyer]} med {period} omkring {day}"
    main = nx.get("inner") or {}
    if main.get("estimated") and main["estimated"] > REGISTERED and (row, buyer, direction) != MAIN[:3]:
        text += (f"; huvudläsningen (L1 före K-inre) när alla fyra i inre lagret har lämnat in {main['period']}, "
                 f"omkring {main['estimated']}")
    return text, day


# ------------------------------------------------------------------ compute


def missing_members(key: str, table: pd.DataFrame, m: dict, when) -> list[str]:
    """Members that lack the quarter after an aggregate's latest one, when another member already has it."""
    f = formulas().get(key)
    if f is None:
        return []
    comps = table[table["series"].isin(f.components)]
    if comps.empty:
        return []
    latest = max(pd.Period(p, freq=C.QFREQ) for p in comps["period"])
    p = str(latest) if not m.get("available") else C.plus(m["period"], 1)
    if pd.Period(p, freq=C.QFREQ) > latest:
        return []
    return [f"{s} ({q})" for s, q in A.missing(f, comps, p, when)]


def compute(as_of, table: pd.DataFrame | None = None) -> dict:
    when = pd.Timestamp(as_of)
    t = table_on(when, table)
    ctx = M.Context(table=t)
    keys = [v[0] for v in SUPPLIERS.values()] + list(BUYERS.values())
    keys += [k for _, ks in CONTEXT.values() for k in ks if k not in keys]
    ms = {k: measure_of(k, t, when, ctx) for k in keys}
    readings = [reading(row, buyer, d, k, ms) for row, buyer in ROWS for d in DIRECTIONS for k in WINDOWS]
    lead = {f"{r['row']}|{r['buyer']}|{r['direction']}": lead_time(r) for r in readings if r["k"] == LEAD_WINDOW}
    filings = C.next_filings(t, when, FILERS)
    nx = {}
    for q in ("inner", "outer", *SUPPLIERS):
        key = BUYERS.get(q) or SUPPLIERS[q][0]
        nx[q] = next_of(q, ms[key].get("period") if ms[key].get("available") else None, filings)
    from ai_tracker.followed import kreditlagret as KL

    try:
        guidance = KL.guidance(t, when)
    except Exception as e:  # context only: a failure is shown, not hidden
        guidance = [{"error": f"{type(e).__name__}: {e}"}]
    used = [ms[k] for k in (*[v[0] for v in SUPPLIERS.values()], *BUYERS.values()) if ms[k].get("available")]
    newest = max((m["known_from"] for m in used), default=None)
    return {
        "question": QUESTION, "as_of": str(when.date()), "generated": str(date.today()), "registered": REGISTERED,
        "seen_before_register": newest is None or newest <= REGISTERED, "newest_known_from": newest,
        "params": {"g_buyer": G_BUYER, "g_supplier": G_SUPPLIER, "windows": list(WINDOWS), "sign": SIGN},
        "measures": ms, "readings": readings, "lead": lead, "main": list(MAIN),
        "missing": {k: missing_members(k, t, ms[k], when) for k in formulas() if k in ms},
        "next_filings": filings, "next": nx, "guidance": guidance,
    }


def find(r: dict, row: str, buyer: str, direction: str, k: int) -> dict:
    return next(x for x in r["readings"] if (x["row"], x["buyer"], x["direction"], x["k"]) == (row, buyer, direction, k))


# ------------------------------------------------------------------ render

_f = C.fmt
SHORT = {C.FOR: "talar för", C.AGAINST: "talar emot", C.NEITHER: "inget av mönstren", C.UNDECIDED: "kan inte avgöras"}


def _who(key: str) -> str:
    if key in WHO:
        return WHO[key]
    for c, n in WHO.items():
        if key.endswith(f"_{c}"):
            return n
    return key


def _level(m_unit: str):
    def f(x):
        if C.num(x) is None:
            return "–"
        return C.fmt_bn(x) if m_unit == "MUSD" else C.fmt(x, 1) + (" %" if m_unit == "%" else f" {m_unit}")
    return f


def _table(ms: dict, keys: list[str]) -> list[str]:
    lines = list(C.TABLE_HEAD)
    for k in keys:
        lines += C.measure_table({k: ms[k]}, [k], _level(ms[k].get("unit", "MUSD")), _who)[2:]
    return lines


def _cell(r: dict) -> str:
    o = next((x for x in r["origins"] if x["origin"] == r["origin"]), None)
    s = f"**{SHORT[r['outcome']]}**"
    if o is not None:
        s += f": {o['origin']} X {_f(o['x'], 1, True)}"
        if o["decided_at"]:
            s += f", Y {_f(o['y'], 1, True)} vid {o['decided_at']}"
        if o.get("acquisition"):
            s += f" (förvärv i fönstret: {o['acquisition']})"
        if r["outcome"] in (C.UNDECIDED, C.NEITHER) and o.get("reason"):
            s += f" ({o['reason']})"
    elif r.get("reason"):
        s += f" ({r['reason']})"
    return s


def _tried(r: dict) -> str:
    h = r["history"]
    if not h["n_x"]:
        return "X saknas"
    up, dn = h["by_direction"]["up"], h["by_direction"]["down"]
    return (f"{h['n_tested']} av {h['n_x']} ({h['first']}–{h['last']}); upp {h['impulses_up']} "
            f"({up[C.FOR]}/{up[C.AGAINST]}/{up[C.NEITHER]}/{up[C.UNDECIDED]}), ned {h['impulses_down']} "
            f"({dn[C.FOR]}/{dn[C.AGAINST]}/{dn[C.NEITHER]}/{dn[C.UNDECIDED]})")


def render(r: dict) -> str:
    ms = r["measures"]
    p = r["params"]
    out = [f"# Ledtid i stacken per {r['as_of']}", "", f"**Frågan:** {r['question']}", "",
           "Leverantörer: L1 kraft och elnät (orderstock och RPO, Eaton och Quanta), L2 nät och servrar (RPO, Cisco, "
           "Dell och Super Micro), L3 datacenter (Equinix RPO), O1 Eatons organiska order (Electrical Americas, tolv "
           "månader) och O2 Digital Realtys nya avtal över fyra kvartal. Köpare: capex över fyra kvartal i inre lagret "
           "(Microsoft, Alphabet, Amazon, Meta) och yttre lagret (Oracle, CoreWeave, Nebius, IREN). Takt = förändring "
           "över fyra kvartal i log × 100. Förändring i takt = mot två kvartal tidigare. Överraskning = mot den naiva "
           "baslinjen B1. Bara data kända på dagen. Registret: `docs/mattregister.md`, 2026-11-26 LT1.", ""]
    out += ["**O1 och O2 kommer ur S3:s extraktion ur pressmeddelanden. Serierna har `publish=False` i väntan på "
            "granskningen av extraktionen.**", ""]

    out += ["## 1. Läsregeln, mekaniskt", "",
            f"F0:s symmetriska regel. X och Y är förändring i takt. Gränser: köparnas capex ±{_f(p['g_buyer'], 0)}, "
            f"leverantörernas orderstock och order ±{_f(p['g_supplier'], 0)} (log × 100), samma gräns för en storhet "
            "som X (impuls) och som Y (följer). Fönster k = 2 och k = 4 kvartal, tecken +. \"Före\": X = leverantören, "
            "Y = köparen. \"Efter\": X = köparen, Y = leverantören. Utslaget gäller det senaste ursprunget med impuls "
            "bland t − k … t − 1, där t är Y:s senaste kvartal. Det är en beskrivning, inget test.", "",
            "Före och efter är inte varandras motsats: två utjämnade serier som rör sig ihop kan ge \"talar för\" i "
            "båda riktningarna, och då säger regeln inte vilken som kom först.", ""]
    if r.get("seen_before_register"):
        out += [f"Alla kvartal i läsningen var kända före registerposten {r['registered']} (posten, avsnitt (e) och "
                "(f)). Läsningen är därför inget utfall på osedda data.", ""]
    main = find(r, *r["main"])
    out += C.reading_lines(main, "Huvudläsning, L1 före K-inre, k = 2") + [""]
    out += ["| Leverantör | Köpare | Riktning | k | t | Utslag (ursprung, X, Y) | Prövad / ursprung med X; impulser "
            "(för/emot/inget/kan inte avgöras) |", "|---|---|---|---|---|---|---|"]
    for x in r["readings"]:
        out.append(f"| {SUPPLIERS[x['row']][1]}{' (S3)' if SUPPLIERS[x['row']][2] else ''} | {BUYER_SHORT[x['buyer']]} "
                   f"| {DIRECTIONS[x['direction']]} | {x['k']} | {x['t'] or '–'} | {_cell(x)} | {_tried(x)} |")

    out += ["", "## 2. Ledtiden (beskrivning)", "",
            f"I läsningarna med k = {LEAD_WINDOW}: kvartal från ursprunget till kvartalet som avgjorde ett \"talar för\". "
            "Senaste ledtiden mot medianen av de tidigare i samma rad. Ingen gräns för \"ändrad\"; med få ursprung kan en "
            "skillnad vara slump.", ""]
    for key, lt in r["lead"].items():
        row, buyer, direction = key.split("|")
        label = f"{SUPPLIERS[row][1]} {DIRECTIONS[direction]} {BUYER_SHORT[buyer]}"
        if not lt["n"]:
            out.append(f"- {label}: inget \"talar för\" i historiken.")
            continue
        items = ", ".join(f"{q} {lag} ({'upp' if d > 0 else 'ned'})" for q, lag, d in lt["by_origin"])
        med = "–" if lt["median_before"] is None else _f(lt["median_before"], 1)
        out.append(f"- {label}: senaste {lt['latest']} kvartal ({lt['latest_origin']}), median av de {lt['n_before']} "
                   f"tidigare {med}. Per ursprung: {items}.")

    out += ["", "## 3. Måtten", "", "**Storheterna i läsregeln:**", ""]
    out += _table(ms, [v[0] for v in SUPPLIERS.values()] + list(BUYERS.values()))
    out += ["", "O1 är en tillväxttakt: takten är 100 × ln(1 + v/100), och överraskning mot B1 är inte registrerad för "
            "den. RPO och orderstock är balanser; förändringen är order minus leveranser, plus valuta och förvärv."]
    miss = {k: v for k, v in r["missing"].items() if v}
    if miss:
        out += ["", "Aggregat som väntar på en medlem: " + "; ".join(f"`{k}` saknar {', '.join(v)}"
                                                                   for k, v in miss.items()) + "."]
    for title, ks in CONTEXT.values():
        out += ["", f"**{title}** (sammanhang, ingår inte i läsregeln):", ""] + _table(ms, ks)
    g = [x for x in r["guidance"] if "error" not in x]
    if g:
        out += ["", "**Köparnas capex-guidance för kalenderåret** (förväntad capex; mittpunkt, guidad takt mot föregående "
                "års utfall där F1:s definition finns; ingår inte i läsregeln):", ""]
        for x in g:
            gp = "" if x["guided_pace"] is None else f", guidad takt {_f(x['guided_pace'], 1, True)}"
            out.append(f"- {KS.NAMES[x['company']]} {x['year']}: {C.fmt_bn(x['lo'])}–{C.fmt_bn(x['hi'])}{gp}; "
                       f"known_from {x['known_from']}")
    for x in r["guidance"]:
        if "error" in x:
            out += ["", f"Guidance kunde inte läsas: {x['error']}."]

    out += ["", "## 4. Att bevaka", "", "Nästa kvartal per storhet, när alla dess medlemmar har lämnat in (uppskattat ur "
            "de åtta senaste inlämningarna per bolag):", ""]
    for q, x in r["next"].items():
        name = BUYER_NAMES.get(q) or SUPPLIERS[q][1]
        if x["period"] is None:
            out.append(f"- {name}: inget kvartal känt på dagen.")
        else:
            miss = f" (ingen historik för {', '.join(x['missing'])})" if x["missing"] else ""
            out.append(f"- {name}: {x['period']} omkring {x['estimated'] or '–'}{miss}")
    text, _day = next_unseen(r)
    out += ["", f"Nästa osedda läsning: {text}."]

    out += ["", "## 5. Förbehåll", "",
            "- Med 10–27 ursprung per rad, och färre med impuls, är detta en beskrivning och inget test. Ett mönster kan "
            "vara slump, och ett utfall som talar för mekanismen visar inte orsaken.",
            "- RPO och orderstock är inte orderingång. Ciscos och Dells RPO har stora tjänstedelar. Ciscos och Dells "
            "balanser har räkenskapskvartalets kalenderkvartal, upp till en månad efter kalenderkvartalets slut.",
            "- Leverantörerna säljer också till andra än AI-köparna: Quanta och Eaton till elbolag och industri, Cisco och "
            "Dell till företag. Ett utslag säger inget om hur stor del som gäller AI.",
            "- Förvärv ger nivåskiften. Belagda förvärv märks i tabellen (Cisco–Splunk 2024Q1, Eaton–Fibrebond 2025Q2, "
            f"Eaton–Boyd Thermal 2026Q1). {UNCHECKED_ACQ}",
            "- O1 och O2 är S3:s extraktion (publish=False i väntan på granskningen). Digital Realtys andel är obelagd "
            "2021Q4–2024Q1 (S3, tolkning 9).",
            "- Vertiv är BLOCKED (inget RPO i XBRL, och S3:s orderserier slutar 2025Q4). GE Vernovas RPO och order är för "
            "korta för läsregeln och visas som sammanhang. Yttre lagrets förändring i capex-takt finns först när "
            "serien har sex kvartal.",
            "- Historiken räknas på läsdagens vintage, så revideringar kan ändra äldre utfall (F0).", ""]
    return "\n".join(out)


# ------------------------------------------------------------------ antenna (register F0, (c))


def antenna(r: dict) -> dict:
    """LT1's row in `antenner`: the main reading (L1 före K-inre, k = 2) and the other rows' outcomes as facts."""
    main = find(r, *r["main"])
    facts = {}
    for row, buyer in ROWS:
        for d in DIRECTIONS:
            for k in WINDOWS:
                if (row, buyer, d, k) == tuple(r["main"]):
                    continue
                if k == 4 and (row, buyer, d) != ("L1", "inner", "fore"):
                    continue
                x = find(r, row, buyer, d, k)
                facts[f"{row} {DIRECTIONS[d]} {BUYER_SHORT[buyer]}, k = {k}"] = f"{SHORT[x['outcome']]} ({x['t'] or '–'})"
    lt = r["lead"].get("L1|inner|fore") or {}
    facts["Ledtid L1 före K-inre (k = 4), senaste / median tidigare"] = (
        f"{lt.get('latest') if lt.get('latest') is not None else '–'} / "
        f"{_f(lt.get('median_before'), 1)} kvartal")
    for key in ("lt1_rpo_power", "kl_capex4_inner"):
        m = r["measures"][key]
        facts[f"Förändring i takt, {_who(key)}"] = f"{_f(m.get('change'), 1, True)} ({m.get('period') or '–'})"
    text, day = next_unseen(r)
    return C.antenna_row(QUESTION, main["outcome"], SHORT[main["outcome"]], main["t"], facts, text, day)
