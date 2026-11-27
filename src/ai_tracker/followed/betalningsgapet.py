"""BG1 "Betalningsgapet": the monthly report of the followed question (register 2026-11-26 "BG1").

"Växer de intäkter som ska bära investeringarna (molnintäkter, AI-nyckeltal, RPO och frontlabbens intäkter) i takt med
intäktskravet från avskrivningar och kapitalkostnad, eller öppnas eller sluts gapet?"

The quantities are sums and ratios of catalog series, derived here with F0's aggregate.derive (the A5/KL1 vintage rule:
a version only once every component has one, known_from = the latest component). No new catalog series (register BG1:
nothing new is fetched or extracted):

    krav(M, r)     sum dep_<c> over four quarters + r x sum ppe_net_<c> at quarter end          MUSD per year
    moln(M)        sum of the cloud revenue over four quarters (CLOUD_REV)                       MUSD
    rpo(M)         sum rpo_<c> at quarter end (a balance)                                         MUSD
    gap_moln(M, r) 100 x krav / moln                                                              % of cloud revenue
    gap_rpo(M, r)  100 x krav / rpo                                                               % of RPO
    capex4(M)      sum capex_<c> over four quarters                                               MUSD

M is the cloud four (Microsoft, Alphabet, Amazon, Oracle), the cloud four without Oracle, or one company (the four and
CoreWeave). Per quantity: level, pace (log x100 a year), change in pace (against two quarters earlier) and surprise
against B1, with F0's path_measures (the state.measures formulas). The gap's pace is the requirement's pace minus the
bearing revenue's pace.

The reading is F0's symmetric rule, one row per X (register BG1, (c)): X = the pace of a gap, Y = the change in pace of
capex4 with the same members, g = 5, h = 5, k = 2, sign -1. The main reading is gap_moln(cloud four, r = 0.10).

Anthropic's reported (GAAP) figures from the registration statement (register 2026-11-27 "AN1", (f)) are shown in
section 5 as table rows and a quarter table beside the run-rate, outside the rule; no reading changes.

Only rows known on the as-of date are used (known_from <= as-of); compute(d, table) equals compute(d, table truncated
at d). A description: no alarm levels, no chosen direction, no p-values.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from ai_tracker.followed import common as C
from ai_tracker.followed.aggregate import Formula, Term, derive, missing, sum4

QUESTION = ("Växer de intäkter som ska bära investeringarna (molnintäkter, AI-nyckeltal, RPO och frontlabbens intäkter) "
            "i takt med intäktskravet från avskrivningar och kapitalkostnad, eller öppnas eller sluts gapet?")
REGISTERED = "2026-11-26"  # the register entry; every quarter known by then was known before the entry (entry, (e))

# registered parameters (register entry, (c))
G, H, K, SIGN = 5.0, 5.0, 2, -1
R_MAIN = 0.10  # midpoint of P2b's registered interval 0.08-0.12
R_SENS = (0.0, 0.08, 0.12)

CLOUD4 = ("msft", "googl", "amzn", "orcl")
CLOUD3 = ("msft", "googl", "amzn")
COMPANIES = (*CLOUD4, "crwv")
CLOUD_REV = {"msft": "rev_msft_cloud", "googl": "rev_google_cloud", "amzn": "rev_aws", "orcl": "rev_orcl_cloud",
             "crwv": "rev_crwv"}
NAMES = {"msft": "Microsoft", "googl": "Alphabet", "amzn": "Amazon", "orcl": "Oracle", "crwv": "CoreWeave",
         "moln4": "molnfyran", "moln3": "molnfyran utan Oracle"}
GROUPS = {"moln4": CLOUD4, "moln3": CLOUD3, **{c: (c,) for c in COMPANIES}}
FILERS = {c: f"capex_{c}" for c in COMPANIES}

# context (register entry, (d)): catalog series shown with their measures, table rows, regime markers
P2B = ("x_dep_rev", "x_capcost_rev_r08", "x_capcost_rev_r12", "x_dep_rev_aws", "x_rpo_cover")
RPO_NEAR = ("rpo_msft_12m", "rpo_orcl_12m", "rpo_googl_24m", "rpo_crwv_24m")
KPIS = ("kpi_msft_azure_growth_v2", "kpi_msft_azure_growth_v3", "kpi_msft_azure_growth_cc_v3",
        "kpi_msft_ai_business_runrate", "kpi_amzn_aws_ai_runrate", "kpi_googl_cloud_backlog")
LABS = ("lab_rev_anthropic_company_run_rate", "lab_rev_anthropic_company_run_rate_s1",
        "lab_rev_anthropic_claude_code_run_rate")
# Anthropic's reported (GAAP) figures from the registration statement (register 2026-11-27 "AN1", (f)): table rows and a
# quarter table, outside the rule. Never mixed with the run-rate series in a series or a ratio.
LABS_GAAP = ("lab_gaap_anthropic_revenue_q", "lab_gaap_anthropic_revenue_a", "lab_gaap_anthropic_opinc_q",
             "lab_gaap_anthropic_cfo_ytd")
GAAP_Q = {"revenue": "lab_gaap_anthropic_revenue_q", "compute": "lab_gaap_anthropic_compute_q",
          "opinc": "lab_gaap_anthropic_opinc_q"}
RUN_RATES = ("lab_rev_anthropic_company_run_rate", "lab_rev_anthropic_company_run_rate_s1")
LIVES = {"msft": "useful_life_servers_msft", "googl": "useful_life_servers_googl", "amzn": "useful_life_servers_amzn",
         "orcl": "useful_life_servers_orcl", "crwv": "useful_life_computer_equipment_crwv"}
LIFE_WINDOW = 7  # X's pace at q uses the quarters q-7..q
MSFT_OLD_BASIS_LAST = "2024Q2"  # Microsoft's depreciation line is on the old basis through this quarter (P2b, R14)
BLOCKED = (
    "OpenAI: ingen registreringsansökan på EDGAR, och openai.com nekas av proxyn (docs/kallor/labbintakter.md).",
)

# ------------------------------------------------------------------ formulas


def _rtag(r: float) -> str:
    return f"r={C.fmt(r, 2)}"


def krav_terms(members, r: float) -> tuple[Term, ...]:
    """Four quarters of depreciation plus r x the net PP&E at quarter end, summed over the members."""
    out: list[Term] = []
    for c in members:
        out += sum4(f"dep_{c}")
    if r:
        out += [Term(f"ppe_net_{c}", 0, r) for c in members]
    return tuple(out)


def moln_terms(members) -> tuple[Term, ...]:
    return tuple(t for c in members for t in sum4(CLOUD_REV[c]))


def rpo_terms(members) -> tuple[Term, ...]:
    return tuple(Term(f"rpo_{c}") for c in members)


def capex_terms(members) -> tuple[Term, ...]:
    return tuple(t for c in members for t in sum4(f"capex_{c}"))


def formula(kind: str, who: str, r: float | None = None) -> Formula:
    """The registered quantity `kind` (krav, moln, rpo, capex4, gap_moln, gap_rpo) for the members of `who`."""
    m = GROUPS[who]
    name = NAMES[who]
    if kind == "krav":
        return Formula(f"krav({name}, {_rtag(r)})", krav_terms(m, r))
    if kind == "moln":
        return Formula(f"moln({name})", moln_terms(m))
    if kind == "rpo":
        return Formula(f"rpo({name})", rpo_terms(m))
    if kind == "capex4":
        return Formula(f"capex4({name})", capex_terms(m))
    if kind == "gap_moln":
        return Formula(f"gap_moln({name}, {_rtag(r)})", krav_terms(m, r), moln_terms(m), 100.0)
    if kind == "gap_rpo":
        return Formula(f"gap_rpo({name}, {_rtag(r)})", krav_terms(m, r), rpo_terms(m), 100.0)
    raise KeyError(kind)


def quantity(f: Formula, rows: pd.DataFrame, when, unit: str) -> dict:
    """A derived quantity as of `when`, in the shape of common.measure (so read_measures and measure_table take it).

    rows must already hold only rows known on `when`. Adds "kf" {quarter: known_from}, "components" and "missing_next"
    (the components the next quarter still lacks on the day)."""
    d = derive(f, rows)
    base = {"series": f.key, "unit": unit, "components": list(f.components), "method": "log"}
    if d.empty:
        return {**base, "available": False, "path": {}, "kf": {}, "missing_next": []}
    last = d.sort_values("known_from", kind="stable").groupby("period").last()
    pm = C.path_measures(last["value"].to_dict(), "log")
    path = {q: {c: C.num(r[c]) for c in ("level", "pace", "change", "surprise")} for q, r in pm.iterrows()}
    known = [q for q, r in path.items() if r["level"] is not None]
    t = max(known, key=lambda q: pd.Period(q, freq=C.QFREQ))
    kf = {str(q): str(pd.Timestamp(v).date()) for q, v in last["known_from"].items()}
    p = path[t]
    return {**base, "available": True, "period": t, "known_from": kf[t], "level": p["level"], "pace": p["pace"],
            "change": p["change"], "surprise": p["surprise"], "surprise_basis": "B1", "pace_unit": "log × 100",
            "path": {q: {c: r[c] for c in ("level", "pace", "change")} for q, r in path.items()}, "kf": kf,
            "missing_next": [f"{s} {p_}" for s, p_ in missing(f, rows, C.plus(t, 1), when)]}


# ------------------------------------------------------------------ readings

UNIT = {"krav": "MUSD per år", "moln": "MUSD", "rpo": "MUSD", "capex4": "MUSD", "gap_moln": "% av molnintäkterna",
        "gap_rpo": "% av RPO"}


def reading_specs() -> list[dict]:
    """The registered rows (register entry, (c)): id, label, X (kind, who, r), Y's members."""
    out = [{"id": "main", "label": "Huvudläsning: gapet mot molnintäkterna, molnfyran, r = 0,10", "kind": "gap_moln",
            "who": "moln4", "r": R_MAIN},
           {"id": "rpo", "label": "Gapet mot RPO, molnfyran, r = 0,10", "kind": "gap_rpo", "who": "moln4", "r": R_MAIN}]
    out += [{"id": f"r{int(round(100 * r)):02d}", "label": f"Känslighet: gapet mot molnintäkterna, molnfyran, "
             f"r = {C.fmt(r, 2)}" + (" (bara avskrivningar)" if r == 0 else ""), "kind": "gap_moln", "who": "moln4",
             "r": r} for r in R_SENS]
    out.append({"id": "rpo_ex_orcl", "label": "Känslighet: gapet mot RPO utan Oracle, r = 0,10", "kind": "gap_rpo",
                "who": "moln3", "r": R_MAIN})
    for c in COMPANIES:
        out += [{"id": f"{c}_moln", "label": f"{NAMES[c]}: gapet mot molnintäkterna", "kind": "gap_moln", "who": c,
                 "r": R_MAIN, "company": True},
                {"id": f"{c}_rpo", "label": f"{NAMES[c]}: gapet mot RPO", "kind": "gap_rpo", "who": c, "r": R_MAIN,
                 "company": True}]
    return out


def life_changes(table: pd.DataFrame, when) -> list[dict]:
    """Every quarter where a stated useful life (servers; CoreWeave: computer equipment) differs from the previous stated
    value of the same series, known on `when` (register entry, (d))."""
    out = []
    for c, base in LIVES.items():
        for end in ("hi", "lo"):
            d = C.asof_rows(table, f"{base}_{end}", when)
            prev = None
            for r in d.itertuples(index=False):
                v = float(r.value)
                if prev is not None and v != prev:
                    out.append({"company": c, "series": f"{base}_{end}", "end": end, "period": str(r.period),
                                "from": prev, "to": v, "known_from": str(pd.Timestamp(r.known_from).date())})
                prev = v
    return sorted(out, key=lambda x: (x["period"], x["company"], x["end"]))


def flags(spec: dict, origin: str | None, changes: list[dict]) -> list[str]:
    """Regime markers for the deciding origin q: a change of a member's highest stated useful life in q-7..q, and
    Microsoft's old depreciation basis in the window. They change no outcome."""
    if origin is None:
        return []
    members = GROUPS[spec["who"]]
    lo = pd.Period(origin, freq=C.QFREQ) - LIFE_WINDOW
    hi = pd.Period(origin, freq=C.QFREQ)
    out = []
    for x in changes:
        if x["end"] == "hi" and x["company"] in members and lo <= pd.Period(x["period"], freq=C.QFREQ) <= hi:
            out.append(f"nyttjandeperioden för {NAMES[x['company']]} ändrades {x['period']} ({C.fmt(x['from'], 0)} → "
                       f"{C.fmt(x['to'], 0)} år, högsta värdet, known_from {x['known_from']})")
    if "msft" in members and lo <= pd.Period(MSFT_OLD_BASIS_LAST, freq=C.QFREQ):
        out.append(f"Microsofts avskrivningar i fönstret {lo}–{hi} har kvartal på den gamla basen (till och med "
                   f"{MSFT_OLD_BASIS_LAST})")
    return out


# ------------------------------------------------------------------ context


def table_rows(table: pd.DataFrame, keys, when, ctx) -> list[dict]:
    """Latest and previous value known on `when` per irregular series (KPIs, labs): description only."""
    out = []
    for k in keys:
        d = C.asof_rows(table, k, when)
        spec = ctx.specs.get(k)
        row = {"series": k, "label": spec.label if spec else k, "unit": spec.unit if spec else "", "n": int(len(d)),
               "period": None, "value": None, "known_from": None, "prev_period": None, "prev_value": None}
        if not d.empty:
            last = d.iloc[-1]
            row.update(period=str(last.period), value=float(last.value),
                       known_from=str(pd.Timestamp(last.known_from).date()))
            if len(d) > 1:
                prev = d.iloc[-2]
                row.update(prev_period=str(prev.period), prev_value=float(prev.value))
        out.append(row)
    return out


def lab_quarters(table: pd.DataFrame, when) -> list[dict]:
    """Anthropic's reported revenue per quarter known on `when`, with revenue x 4, compute as % of revenue, the operating
    result and, beside them, the latest run-rate known at the quarter's end (known_from <= quarter end and <= `when`;
    register AN1, (f)). A description: the two measures are never combined."""
    rev = C.asof_rows(table, GAAP_Q["revenue"], when)
    comp = C.asof_rows(table, GAAP_Q["compute"], when).set_index("period")["value"].to_dict()
    opi = C.asof_rows(table, GAAP_Q["opinc"], when).set_index("period")["value"].to_dict()
    rr = []
    for k in RUN_RATES:
        d = C.asof_rows(table, k, when)
        rr += [(pd.Timestamp(r.period), float(r.value), pd.Timestamp(r.known_from), k) for r in d.itertuples()]
    out = []
    for r in rev.itertuples(index=False):
        end = pd.Period(str(r.period), freq=C.QFREQ).end_time.normalize()
        v = float(r.value)
        known = [x for x in rr if x[0] <= end and x[2] <= end]
        last = max(known, key=lambda x: (x[0], x[2])) if known else None
        c = comp.get(r.period)
        out.append({"period": str(r.period), "revenue": v, "x4": 4.0 * v,
                    "compute_pct": None if c is None or not v else 100.0 * float(c) / v,
                    "opinc": None if opi.get(r.period) is None else float(opi[r.period]),
                    "known_from": str(pd.Timestamp(r.known_from).date()),
                    "run_rate": None if last is None else {"date": str(last[0].date()), "value": last[1],
                                                           "known_from": str(last[2].date()), "series": last[3]}})
    return out


# ------------------------------------------------------------------ compute


def _components() -> set[str]:
    out = set()
    for who in GROUPS:
        for kind in ("gap_moln", "gap_rpo", "capex4"):
            out |= set(formula(kind, who, R_MAIN).components)
    return out


def compute(as_of, table: pd.DataFrame | None = None) -> dict:
    """The report as of `as_of`. Each reading gets "seen" (register X25, point 1): True when every value its outcome
    rests on is the same in the report as of the register day; always True up to the register day."""
    when = pd.Timestamp(as_of)
    table, ctx = C.prepare(table)
    r = _compute(when, table, ctx)
    reg = _compute(pd.Timestamp(REGISTERED), table, ctx) if when > pd.Timestamp(REGISTERED) else None
    reg_by = {} if reg is None else {x["id"]: x for x in reg["readings"]}
    for x in r["readings"]:
        if reg is None:
            x["seen"] = True
            continue
        now = (C.series_of(r["quantities"][x["x_series"]], "pace"), C.series_of(r["quantities"][x["y_series"]], "change"))
        then = (C.series_of(reg["quantities"][x["x_series"]], "pace"),
                C.series_of(reg["quantities"][x["y_series"]], "change"))
        x["seen"] = x["id"] in reg_by and C.same_inputs(x, *now, *then)
    r["seen_before_register"] = all(x["seen"] for x in r["readings"])
    r["main_seen"] = next(x["seen"] for x in r["readings"] if x["id"] == "main")
    return r


def _compute(when: pd.Timestamp, table: pd.DataFrame, ctx) -> dict:
    rows = table[(table["known_from"] <= when) & table["series"].isin(_components())]

    q: dict[str, dict] = {}

    def get(kind: str, who: str, r: float | None = None) -> dict:
        f = formula(kind, who, r)
        if f.key not in q:
            q[f.key] = quantity(f, rows, when, UNIT[kind])
        return q[f.key]

    for who in ("moln4", *COMPANIES):
        get("krav", who, R_MAIN)
        get("moln", who)
        get("rpo", who)
        get("capex4", who)
    get("krav", "moln4", 0.0)
    changes = life_changes(table, when)
    readings = []
    for spec in reading_specs():
        mx = get(spec["kind"], spec["who"], spec["r"])
        my = get("capex4", spec["who"])
        r = C.read_measures(mx, my, x_stat="pace", g=G, k=K, h=H, sign=SIGN)
        r.update(id=spec["id"], label=spec["label"], who=spec["who"], company=bool(spec.get("company")),
                 flags=flags(spec, r["origin"], changes))
        readings.append(r)

    main_t = q[formula("capex4", "moln4").key].get("period")
    rpo4, rpo_o = q[formula("rpo", "moln4").key], q[formula("rpo", "orcl").key]
    share = None
    if rpo4.get("available") and C.at(rpo_o, rpo4["period"], "level") is not None:
        share = 100.0 * C.at(rpo_o, rpo4["period"], "level") / rpo4["level"]
    return {
        "question": QUESTION, "as_of": str(when.date()), "generated": str(date.today()),
        "params": {"g": G, "h": H, "k": K, "sign": SIGN, "r_main": R_MAIN, "r_sens": list(R_SENS)},
        "quantities": q, "readings": readings, "main_t": main_t,
        "context": C.measures((*P2B, *RPO_NEAR), when, ctx),
        "orcl_rpo_share": {"period": rpo4.get("period"), "value": share},
        "kpis": table_rows(table, KPIS, when, ctx), "labs": table_rows(table, LABS, when, ctx),
        "labs_gaap": table_rows(table, LABS_GAAP, when, ctx), "lab_quarters": lab_quarters(table, when),
        "blocked": list(BLOCKED),
        "life_changes": changes, "next_filings": C.next_filings(table, when, FILERS),
    }


# ------------------------------------------------------------------ render

_f = C.fmt


def _key(kind: str, who: str, r: float | None = None) -> str:
    return formula(kind, who, r).key


def _who(key: str) -> str:
    return key


def _qtable(q: dict, keys: list[str], level_fmt) -> list[str]:
    return C.measure_table(q, keys, level_fmt, _who)


def _value(x: float | None, unit: str) -> str:
    if x is None:
        return "–"
    if unit == "MUSD":
        return C.fmt_bn(x)
    if unit == "%":
        return C.fmt_pct(x)
    return f"{_f(x, 1)} {unit}".strip()


def render(r: dict) -> str:
    q = r["quantities"]
    out = [f"# Betalningsgapet per {r['as_of']}", "", f"**Frågan:** {r['question']}", "",
           "Intäktskrav = avskrivningar över fyra kvartal + r × anläggningstillgångar netto vid kvartalets slut (hela "
           "bolaget, bara kapitalet). Bärande intäkter = molnintäkter över fyra kvartal (Microsoft Cloud, Google Cloud, "
           "AWS, Oracles moln, CoreWeaves intäkter) eller RPO vid kvartalets slut. Gapet = 100 × intäktskrav / bärande "
           "intäkter. Molnfyran = Microsoft, Alphabet, Amazon och Oracle, som summor av komponenterna. Takt = "
           "årsförändring i log × 100, så gapets takt är intäktskravets takt minus intäkternas: positiv = gapet öppnas, "
           "negativ = gapet sluts. Förändring i takt = mot två kvartal tidigare. Överraskning = mot den naiva baslinjen "
           "B1. Bara data kända på dagen. Registret: `docs/mattregister.md`, 2026-11-26 BG1.", ""]

    out += ["## 1. Molnfyran: intäktskrav, bärande intäkter och investeringstakt", ""]
    out += _qtable(q, [_key("krav", "moln4", R_MAIN), _key("krav", "moln4", 0.0), _key("moln", "moln4"),
                       _key("rpo", "moln4"), _key("capex4", "moln4")], C.fmt_bn)
    out += ["", "**Gapet** (procent av molnintäkterna respektive av RPO):", ""]
    out += _qtable(q, [_key("gap_moln", "moln4", R_MAIN), *[_key("gap_moln", "moln4", x) for x in R_SENS],
                       _key("gap_rpo", "moln4", R_MAIN), _key("gap_rpo", "moln3", R_MAIN)], C.fmt_pct)
    nxt = q[_key("gap_moln", "moln4", R_MAIN)]
    if nxt.get("available"):
        miss = nxt["missing_next"]
        out += ["", f"Nästa kvartal ({C.plus(nxt['period'], 1)}) för molnfyran saknar på dagen: "
                + (", ".join(f"`{m}`" for m in miss) if miss else "inget") + "."]

    out += ["", "## 2. Per bolag (r = 0,10)", ""]
    out += _qtable(q, [_key("gap_moln", c, R_MAIN) for c in COMPANIES], C.fmt_pct)
    out += [""]
    out += _qtable(q, [_key("gap_rpo", c, R_MAIN) for c in COMPANIES], C.fmt_pct)
    out += ["", "Komponenterna per bolag:", ""]
    out += _qtable(q, [k for c in COMPANIES for k in (_key("krav", c, R_MAIN), _key("moln", c), _key("rpo", c),
                                                      _key("capex4", c))], C.fmt_bn)

    p = r["params"]
    out += ["", "## 3. Läsregeln, mekaniskt", "",
            f"F0:s symmetriska regel, en rad per X. X = gapets takt (gräns ±{_f(p['g'], 0)} log × 100 per år), Y = "
            f"förändring i capex-takt för samma bolag (gräns ±{_f(p['h'], 0)}), fönster {p['k']} kvartal, tecken −. "
            "Gapet öppnas (X ≥ +5) och capex-takten faller med minst 5 först: talar för. Gapet sluts (X ≤ −5) och "
            "capex-takten stiger med minst 5 först: talar för. Motsatt rörelse först: talar emot. Håller capex-takten "
            "sig inom ±5: inget av mönstren, så regeln skiljer inte \"stöder fortsatt takt\" från \"ingen effekt\". "
            "Utslaget är en beskrivning, inget test.", "",
            "Intäktskravet innehåller capex (nettot växer med investeringarna, avskrivningarna följer efter). En "
            "uthållig acceleration i capex höjer därför både X och Y och läses som talar emot. Ett utslag som talar "
            "emot är ett svagare belägg mot mekanismen än ett som talar för är belägg för den. Raden med r = 0 är minst "
            "direkt kopplad.", ""]
    unseen = [x for x in r["readings"] if x.get("seen") is False]
    if not unseen:
        out += [f"Alla läsningar nedan vilar bara på värden som var kända före registerposten {REGISTERED}, och P2b:s "
                "kvoter och KL1:s capex-takt för de inre bolagen var sedda före posten (posten, avsnitt (e)). Ingen av "
                f"läsningarna är därför ett utfall på osedda data. Den första osedda läsningen kommer med inlämningar "
                f"efter {REGISTERED} (avsnitt 7). Sedda data avgörs per läsning (X25, punkt 1).", ""]
    else:
        out += [f"{len(unseen)} av {len(r['readings'])} läsningar vilar på värden som blev kända efter registerposten "
                f"{REGISTERED} och är märkta **osedd** nedan. De övriga vilar bara på värden som var kända före posten. "
                "Sedda data avgörs per läsning (X25, punkt 1).", ""]
    for x in r["readings"]:
        if x["id"] == "msft_moln":
            out += ["", "**Bolagsrader** (bisak, samma gränser, Y = bolagets egen capex-takt):", ""]
        out += C.reading_lines(x, x["label"])
        if x["id"] == "main":
            out.append("  " + C.seen_text(x.get("seen"), REGISTERED))
        elif x.get("seen") is False:
            out.append(f"  **Osedd:** läsningen vilar på värden som blev kända efter registerposten {REGISTERED}.")
        for fl in x["flags"]:
            out.append(f"  Märkning: {fl}.")

    out += ["", "## 4. Sammanhang", "",
            "**P2b:s avstämningar** (hyp4 mot totala intäkter, AWS-segmentet och RPO mot capex; katalogserier):", ""]
    ctx = r["context"]
    out += C.measure_table(ctx, list(P2B), lambda v: _f(v, 2), _who)
    out += ["", "**RPO på kort sikt** (andelen inom 12 eller 24 månader enligt bolaget, belopp ungefärliga):", ""]
    out += C.measure_table(ctx, list(RPO_NEAR), C.fmt_bn, _who)
    sh = r["orcl_rpo_share"]
    if sh["value"] is not None:
        out += ["", f"Oracles andel av molnfyrans RPO vid {sh['period']}: **{C.fmt_pct(sh['value'])}**. RPO är klumpig: "
                "enstaka mycket stora avtal flyttar ett kvartal, och raden utan Oracle i avsnitt 3 visar hur mycket "
                "Oracle betyder."]
    out += ["", "Bolagens guidance för molnintäkter finns inte i katalogen, så B1 är enda baslinjen för intäkterna."]

    out += ["", "## 5. AI-nyckeltal och labbens intäkter (tabellrader, ingår inte i regeln)", ""]
    for x in r["kpis"] + r["labs"]:
        if x["value"] is None:
            out.append(f"- {x['label']}: inget värde känt på dagen (`{x['series']}`)")
            continue
        prev = ("" if x["prev_value"] is None else
                f"; före: {_value(x['prev_value'], x['unit'])} ({x['prev_period']})")
        out.append(f"- {x['label']}: **{_value(x['value'], x['unit'])}** ({x['period']}{prev}); {x['n']} {'värde' if x['n'] == 1 else 'värden'}, "
                   f"known_from {x['known_from']}, `{x['series']}`")
    out += ["", "AI-nyckeltalen är oregelbundna och har definitionsbrott (Azure v1–v3). Run-rate är bolagets egen "
            "årstakt vid en tidpunkt och inte redovisad intäkt, och den blandas inte med GAAP-tal.", ""]
    out += _lab_gaap_lines(r)
    out += [f"- **BLOCKED:** {b}" for b in r["blocked"]]

    out += ["", "## 6. Nyttjandeperioder (regimmarkörer)", "",
            "Kvartal där ett angivet värde skiljer sig från det föregående i samma serie (servrar; CoreWeave: "
            "datorutrustning). Det lägsta värdet blandar punkter och intervall, så en ändring där kan vara en "
            "formulering. Märkningarna i avsnitt 3 läser bara det högsta värdet.", ""]
    if r["life_changes"]:
        for x in r["life_changes"]:
            out.append(f"- {NAMES[x['company']]} {x['period']}: {'högsta' if x['end'] == 'hi' else 'lägsta'} "
                       f"{_f(x['from'], 0)} → {_f(x['to'], 0)} år (known_from {x['known_from']}, `{x['series']}`)")
    else:
        out.append("- Inga ändringar kända på dagen.")

    out += ["", "## 7. Att bevaka", "", "Nästa inlämning per bolag, uppskattad som nästa kvartals slut plus medianen av "
            "avståndet för de åtta senaste inlämningarna:", ""]
    for x in r["next_filings"]:
        late = (f" (väntas nu, inte i tabellen ännu; därefter {x['then_period']} omkring {x['then_estimated']})"
                if x["overdue"] else "")
        out.append(f"- {NAMES[x['company']]}: {x['next_period']} omkring {x['estimated']}{late} "
                   f"(median {x['lag_days_median']} dagar, spann {x['lag_days_range'][0]}–{x['lag_days_range'][1]}, "
                   f"senast {x['last_filed']})")
    text, day = next_unseen(r)
    out += ["", f"Nästa osedda läsning: {text}."]

    out += ["", "## 8. Förbehåll", "",
            "- Med cirka 7 ursprung med X i molnfyrans historik är detta en beskrivning och inget test. Ett mönster kan "
            "vara slump, och ett utslag som talar för visar inte orsaken.",
            "- Intäktskravet är härlett med ett antagande: r är ett registrerat intervall och ingen skattning av "
            "bolagens kapitalkostnad. Raderna med r = 0, 0,08 och 0,12 visar känsligheten. Drift, el, personal och skatt "
            "ingår inte.",
            "- Täljaren är hela bolagets kapital och nämnaren bara molnet eller orderstocken. Gapets nivå är ingen "
            "marginal och ingen avkastning. Amazons och Microsofts anläggningstillgångar omfattar mer än molnet. "
            "AWS-segmentets egen kvot står i avsnitt 4.",
            "- Definitionerna skiljer sig: Microsoft Cloud innehåller kommersiell Office 365, LinkedIn och Dynamics, "
            "Oracles moln innehåller SaaS och Google Cloud innehåller Workspace. Oracles avskrivningar innehåller "
            "amortering på immateriella tillgångar, Amazons och Microsofts rader mer än avskrivningar på "
            "anläggningstillgångar.",
            "- Regimbrott: ändrade nyttjandeperioder flyttar avskrivningarna utan att kapaciteten ändras (avsnitt 6). "
            "Microsofts avskrivningsrad ligger på den gamla basen till och med 2024Q2, så X:s takt till och med 2026Q1 "
            "jämför fönster med olika bas för Microsoft och molnfyran (märkt i avsnitt 3).",
            "- RPO är klumpig (till exempel OpenAI hos Oracle) och en balans, medan intäktskravet är ett flöde per år.",
            "- Oracles kvartal slutar en månad före kalenderkvartalet (mittpunktsregeln), och Oracle lämnar in tidigare "
            "än de andra.",
            "- CoreWeaves serier börjar 2024, och nettot av anläggningstillgångar först 2024Q4. Bolagsraden har därför "
            "få kvartal.",
            "- Labbens run-rate är inte redovisad intäkt. Anthropics redovisade tal kommer ur registreringsprospektet "
            "(AN1) och står bara som beskrivning i avsnitt 5. OpenAI är BLOCKED.",
            ""]
    return "\n".join(out)


def _lab_gaap_lines(r: dict) -> list[str]:
    """Section 5, Anthropic's reported figures (register AN1, (f)): table rows and the quarter table."""
    out = ["**Anthropics redovisade tal (GAAP, ur S-1, S-1/A och 424B4; registret 2026-11-27 AN1):**", ""]
    for x in r["labs_gaap"]:
        if x["value"] is None:
            out.append(f"- {x['label']}: inget värde känt på dagen (`{x['series']}`)")
            continue
        prev = ("" if x["prev_value"] is None else f"; före: {_value(x['prev_value'], x['unit'])} ({x['prev_period']})")
        out.append(f"- {x['label']}: **{_value(x['value'], x['unit'])}** ({x['period']}{prev}); {x['n']} "
                   f"{'värde' if x['n'] == 1 else 'värden'}, known_from {x['known_from']}, `{x['series']}`")
    qs = r["lab_quarters"]
    if not qs:
        return out + ["", "Inga redovisade kvartal kända på dagen.", ""]
    out += ["", "| Kvartal | Intäkt | Intäkt × 4 | Compute, % av intäkten | Rörelseresultat | known_from | Senaste "
                "run-rate känd vid kvartalets slut |", "|---|---|---|---|---|---|---|"]
    for q in qs:
        rr = q["run_rate"]
        rr_text = ("–" if rr is None else f"{C.fmt_bn(rr['value'])} per {rr['date']} (känd {rr['known_from']}, "
                   f"`{rr['series']}`)")
        out.append(f"| {q['period']} | {C.fmt_bn(q['revenue'])} | {C.fmt_bn(q['x4'])} | "
                   f"{'–' if q['compute_pct'] is None else C.fmt_pct(q['compute_pct'])} | "
                   f"{'–' if q['opinc'] is None else C.fmt_bn(q['opinc'])} | {q['known_from']} | {rr_text} |")
    out += ["", "**Skillnaden mot run-rate.** Den redovisade intäkten är summan av det som intäktsförts under kvartalet "
            "(GAAP). Run-rate är bolagets egen årstakt vid en dag: konsumtionsavgifter under 28 dagar × 13 plus "
            "månatliga abonnemang × 12 (S-1:s definition, ej GAAP och inte granskad av tredje part; nyhetsrummets äldre "
            "värden anger inget beräkningssätt). Intäkt × 4 är bara kvartalet uppräknat till ett år. I ett bolag som "
            "växer snabbt ligger run-rate vid kvartalets slut över kvartalets intäkt × 4, och de två mäter alltså "
            "olika saker. De blandas aldrig i en serie eller en kvot, och run-rate-kolumnen visar bara vad bolaget "
            "hade sagt när kvartalet slutade.",
            "",
            "Compute och infrastruktur är en kostnad efter slag och omfattar också träning och forskning; kostnaden för "
            "intäkter (noten om kostnader efter funktion, `lab_gaap_anthropic_cost_of_revenue_*`) är bara compute för "
            "kundernas arbetslaster med mera. Labbets kostnader för compute är till stor del molnens intäkter. Labbets "
            "intäkter läggs inte till molnintäkterna i regeln: en del av dem säljs via molnen (Bedrock, Vertex) och "
            "skulle räknas två gånger. Ingen känslighetsrad i regeln (AN1, (f)): kvartalen börjar 2025Q1, så takten "
            "för en summa över fyra kvartal finns först för 2026Q4.", ""]
    return out


# ------------------------------------------------------------------ antenna (register F0, (c))

SHORT = C.OUTCOME_TEXT


def next_unseen(r: dict) -> tuple[str, str | None]:
    """The next reading on a quarter not known at the register entry: the earliest estimated filing after REGISTERED
    (that company's rows), and the cloud four's main reading once all four have filed."""
    cands = []
    for x in r["next_filings"]:
        if x["estimated"] > REGISTERED:
            cands.append((x["estimated"], x["company"], x["next_period"], x["overdue"]))
        elif x["overdue"] and x["then_estimated"] and x["then_estimated"] > REGISTERED:
            cands.append((x["then_estimated"], x["company"], x["then_period"], False))
    if not cands:
        return f"med inlämningar efter {REGISTERED} (inga uppskattade ännu)", None
    day, c, period, overdue = min(cands)
    text = f"{NAMES[c]} {period} omkring {day}{' (väntas nu)' if overdue else ''}, bolagsraderna"
    four = [x for x in cands if x[1] in CLOUD4 and x[2] == period]
    if {x[1] for x in four} == set(CLOUD4):
        text += f"; molnfyrans huvudläsning när alla fyra har lämnat in (uppskattat {max(x[0] for x in four)})"
    return text, day


def antenna(r: dict) -> dict:
    """BG1's row in `antenner`: the main reading and, as facts, the other rows' outcomes and the main numbers."""
    by = {x["id"]: x for x in r["readings"]}
    main = by["main"]
    facts = {}
    for x in r["readings"]:
        if x["id"] != "main":  # always the row's own quarter, so an unchanged row is not listed as changed (R28-3)
            facts[x["label"]] = f"{SHORT[x['outcome']]} ({x['t'] or '–'})"
    gap = r["quantities"][_key("gap_moln", "moln4", R_MAIN)]
    cap = r["quantities"][_key("capex4", "moln4")]
    facts["Gapets takt mot molnintäkterna, molnfyran"] = (f"{_f(gap.get('pace'), 1, True)} ({gap.get('period') or '–'})"
                                                         if gap.get("available") else "–")
    facts["Förändring i capex-takt, molnfyran"] = (f"{_f(cap.get('change'), 1, True)} ({cap.get('period') or '–'})"
                                                  if cap.get("available") else "–")
    h = main["history"]
    facts["Impulser i huvudläsningens historik"] = f"upp {h['impulses_up']}, ned {h['impulses_down']}, av {h['n_x']}"
    facts["Huvudläsningen på osedda data"] = "nej" if main.get("seen", True) else "ja"
    text, day = next_unseen(r)
    inputs = {"x": formula("gap_moln", "moln4", R_MAIN).components, "y": formula("capex4", "moln4").components,
              "x_stat": "takt", "sign": SIGN}
    return C.antenna_row(QUESTION, main["outcome"], SHORT[main["outcome"]], main["t"], facts, text, day, inputs)
