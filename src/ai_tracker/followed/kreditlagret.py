"""KL1 "Kreditlagret": the monthly report of the followed question (register 2026-11-25 "KL1" and its addendum).

"Ändras finansieringens pris och tillgång i de yttre lagren, och följer investeringstakten där med?"

The report runs along the chain price -> dependence -> willingness/ability, outer layer against inner layer. Per
measure: level, pace, change in pace and surprise, computed by the state engine's per-series measures
(state.measures.measure_path: shares and rates in percentage points over four quarters, amounts as log x100 a year,
change in pace against two quarters earlier, surprise against the naive baseline B1), with series keys and known_from.
The generic parts (loading as of a day, measures, next filings, tables) live in followed/common.py (register F0); the
registered KL1 reading below is KL1's own and is not the symmetric F0 template (register F0: KL1 is unchanged).
Then the registered reading, applied mechanically (`reading`), the lab and venture tables from the extraction, what to
watch next (filing dates estimated from each company's last eight filings) and the caveats.

Only rows known on the as-of date are used: the observation table through observations.as_of semantics (known_from <=
as-of) and the curated rows with filed <= as-of. compute(d, table) equals compute(d, table truncated at d).
"""

from __future__ import annotations

import math
from datetime import date

import pandas as pd

from ai_tracker.followed import common as C
from ai_tracker.series import kreditlagret as S

QUESTION = ("Ändras finansieringens pris och tillgång i de yttre lagren, och följer investeringstakten där med?")
# registered limits (register entry, (c))
RATE_RISE = 0.25  # pp over four quarters
DEP_RISE = 5.0  # pp of capex over four quarters
CAPEX_FALL = -5.0  # change in pace, log x100
EQUAL_SHARE = 0.5  # the inner fell at least half as much as the outer
PRICE_DEP = ("rate_eff", "fcfgap", "netdebt", "leases")
LIMIT = {"rate_eff": RATE_RISE, "fcfgap": DEP_RISE, "netdebt": DEP_RISE, "leases": DEP_RISE}
SPREAD_ISSUERS = {"orcl": "outer", "meta": "inner", "googl": "inner", "amzn": "inner"}
FILERS = {"orcl": "capex_orcl", "msft": "capex_msft", "googl": "capex_googl", "amzn": "capex_amzn",
          "meta": "capex_meta", "crwv": "capex_crwv", "nbis": "capex_nbis", "iren": "capex_iren", "nvda": "rev_nvda"}
FILER_NAMES = {**S.NAMES, "nvda": "Nvidia"}
GUIDANCE = {  # (lo, hi) of calendar-year capex guidance, as in the catalog
    "msft": ("guid_capex_msft_cy_lo", "guid_capex_msft_cy_hi"), "googl": ("guid_capex_googl_cy_lo", "guid_capex_googl_cy_hi"),
    "amzn": ("guid_capex_amzn_cy_lo", "guid_capex_amzn_cy_hi"), "meta": ("guid_capex_meta_cy_lo", "guid_capex_meta_cy_hi"),
}
DIRECTIONS = ("guid_capex_amzn_cy_dir_yoy", "guid_capex_googl_cy_dir_yoy", "guid_capex_meta_cy_dir_yoy",
              "plan_orcl_capex_y_dir_yoy", "plan_googl_capex_y_dir_yoy", "plan_amzn_cash_capex_y_dir_yoy",
              "guid_capex_msft_fy_dir_prior_fy")
POWER = ("plan_crwv_contracted_power_asof_value", "plan_crwv_active_power_asof_value")
MAX_LAG = 200  # days from quarter end: a longer first appearance is a comparative in a later filing
REGISTERED = "2026-11-25"  # the register entry; quarters known by then were seen before it (entry, (e); X23, point 4)
LABEL = {"kl_leases_msft_cond": "Microsoft (inkl. villkorade, från 2026Q2)",
         "plan_crwv_contracted_power_asof_value": "CoreWeave, kontrakterad", "plan_crwv_active_power_asof_value":
         "CoreWeave, aktiv", "kl_coupon_out_crwv_q": "CoreWeave"}


# ------------------------------------------------------------------ measures


_num = C.num
measure = C.measure  # level, pace, change in pace and surprise of one series, with its path
_at = C.at
_minus = C.minus


# ------------------------------------------------------------------ the registered reading


def measures_of(entity: str) -> list[str]:
    """Price/dependence measures registered for an entity (a layer or an outer company)."""
    out = []
    for m in PRICE_DEP:
        if entity in ("outer", "inner") or entity in S.COMPANIES[m]:
            out.append(m)
    return out


def condition_a(entity: str, t: str | None, ms: dict[str, dict]) -> tuple[bool | None, list[str], dict]:
    """A: at t-2 a price or dependence measure of the entity rose by at least its limit. (value, missing, paces)."""
    t2 = _minus(t, 2)
    paces, missing = {}, []
    for m in measures_of(entity):
        p = _at(ms[f"kl_{m}_{entity}"], t2, "pace")
        paces[m] = p
        if p is None and t2 is not None:
            missing.append(f"kl_{m}_{entity} (takt vid {t2})")
    if any(p is not None and p >= LIMIT[m] for m, p in paces.items()):
        return True, missing, paces
    if t2 is None or missing:
        return None, missing, paces
    return False, missing, paces


def a_history(entity: str, ms: dict[str, dict]) -> dict:
    """How often A has held (register X23, point 4): quarters where at least one price or dependence measure of the
    entity reaches its limit, of the quarters where at least one of them has a pace, over the history known on the day."""
    paths = {m: (ms[f"kl_{m}_{entity}"].get("path") or {}) for m in measures_of(entity)}
    quarters = sorted(set().union(*[set(p) for p in paths.values()]))
    held = known = 0
    first = last = None
    for q in quarters:
        paces = {m: p.get(q, {}).get("pace") for m, p in paths.items()}
        if all(v is None for v in paces.values()):
            continue
        known += 1
        first, last = first or q, q
        held += any(v is not None and v >= LIMIT[m] for m, v in paces.items())
    return {"held": held, "of": known, "first": first, "last": last}


def reading(a: bool | None, d_outer: float | None, d_inner: float | None) -> str:
    """The registered outcome from A, the outer and the inner change in capex pace (log x100)."""
    if d_outer is not None and d_inner is not None and d_outer <= CAPEX_FALL and d_inner <= CAPEX_FALL \
            and d_inner <= EQUAL_SHARE * d_outer:
        return "emot_2"
    if a is True:
        if d_outer is None:
            return "kan_inte_avgoras"
        if d_outer > CAPEX_FALL:
            return "emot_1"
        if d_inner is None:
            return "kan_inte_avgoras"
        return "stoder" if d_inner > CAPEX_FALL else "blandat"
    if a is False and d_outer is not None and d_inner is not None:
        return "inget"
    return "kan_inte_avgoras"


OUTCOME = {
    "stoder": "talar för mekanismen (pris eller beroende steg först, sedan föll takten i yttre lagret medan det inre höll)",
    "emot_1": "talar emot (1): pris eller beroende steg, men takten i yttre lagret höll eller steg",
    "emot_2": "talar emot (2): takten föll i båda lagren, och det inre minst hälften så mycket (efterfrågan, inte "
              "finansiering)",
    "blandat": "blandat: pris eller beroende steg och takten föll i båda lagren, men det inre mindre än hälften så mycket",
    "inget": "inget av mönstren",
    "kan_inte_avgoras": "kan inte avgöras (ett mått som regeln behöver saknas)",
}


def apply_reading(entity: str, ms: dict[str, dict]) -> dict:
    cap = ms[f"kl_capex4_{entity}"]
    t = cap.get("period") if cap.get("available") else None
    a, missing, paces = condition_a(entity, t, ms)
    d_out = cap.get("change") if cap.get("available") else None
    inner = ms["kl_capex4_inner"]
    d_in = inner.get("change") if inner.get("available") else None
    if t is None:
        missing.append(f"kl_capex4_{entity} (inget kvartal känt på dagen)")
    elif d_out is None:
        missing.append(f"kl_capex4_{entity} (förändring i takt vid {t})")
    if d_in is None:
        missing.append("kl_capex4_inner (förändring i takt)")
    out = reading(a, d_out, d_in)
    return {"entity": entity, "t": t, "t_minus_2": _minus(t, 2), "a": a, "paces_t_minus_2": paces,
            "capex_change_outer": d_out, "capex_change_inner": d_in, "inner_period": inner.get("period"),
            "outcome": out, "text": OUTCOME[out], "missing": missing if out == "kan_inte_avgoras" else [],
            "a_history": a_history(entity, ms)}


# ------------------------------------------------------------------ context blocks


_asof = C.asof_rows


def spreads(table: pd.DataFrame, when) -> list[dict]:
    out = []
    for c, layer in SPREAD_ISSUERS.items():
        d = _asof(table, f"spread_issue_{c}_q", when)
        if d.empty:
            continue
        last = d.iloc[-1]
        prev = d.iloc[-2] if len(d) > 1 else None
        out.append({"company": c, "layer": layer, "series": f"spread_issue_{c}_q", "period": str(last.period),
                    "value": float(last.value), "known_from": str(pd.Timestamp(last.known_from).date()),
                    "prev_period": None if prev is None else str(prev.period),
                    "prev_value": None if prev is None else float(prev.value), "n_quarters": int(len(d))})
    return out


def guidance(table: pd.DataFrame, when) -> list[dict]:
    """Latest calendar-year capex guidance per inner company (midpoint) and the guided pace against the previous
    calendar year's outcome, where the F1 outcome definition exists (Meta incl. finance leases, Alphabet)."""
    from ai_tracker.series import guidance_revisions as F1

    year = pd.Timestamp(when).year
    out = []
    for c, (lo_k, hi_k) in GUIDANCE.items():
        lo, hi = _asof(table, lo_k, when), _asof(table, hi_k, when)
        for y in (year, year + 1):
            lo_y, hi_y = lo[lo["period"].astype(str) == str(y)], hi[hi["period"].astype(str) == str(y)]
            if lo_y.empty:
                continue
            lv = float(lo_y.value.iloc[-1])
            hv = float(hi_y.value.iloc[-1]) if not hi_y.empty else lv
            kf = max([lo_y.known_from.iloc[-1]] + ([hi_y.known_from.iloc[-1]] if not hi_y.empty else []))
            row = {"company": c, "year": y, "lo": lv, "hi": hv, "mid": (lv + hv) / 2,
                   "known_from": str(pd.Timestamp(kf).date()), "series": f"{lo_k}, {hi_k}", "guided_pace": None}
            if c in F1.CAPEX_SURPRISE:
                comps = F1.CAPEX_SURPRISE[c][1]
                prev = 0.0
                ok = True
                for comp in comps:
                    d = _asof(table, comp, when)
                    q = d[d["period"].astype(str).str.startswith(str(y - 1))]
                    if len(q) != 4:
                        ok = False
                        break
                    prev += float(q.value.sum())
                if ok and prev > 0:
                    row["guided_pace"] = 100.0 * math.log(row["mid"] / prev)
                    row["outcome_definition"] = " + ".join(comps)
            out.append(row)
    return out


def directions(table: pd.DataFrame, when) -> list[dict]:
    out = []
    for k in DIRECTIONS:
        d = _asof(table, k, when)
        for r in d.itertuples(index=False):
            if pd.Timestamp(r.known_from) >= pd.Timestamp(when) - pd.Timedelta(days=400):
                out.append({"series": k, "period": str(r.period), "code": float(r.value),
                            "known_from": str(pd.Timestamp(r.known_from).date())})
    return out


def revisions(table: pd.DataFrame, when) -> list[dict]:
    """F1 capex revision events of the last 365 days, per company (up, unchanged, down)."""
    from ai_tracker.series import guidance_revisions as F1

    csv = F1.load_csv()
    if csv is None:
        return []
    csv = csv[pd.to_datetime(csv["known_from"]) <= pd.Timestamp(when)]
    t = table[table["known_from"] <= pd.Timestamp(when)]
    ev = F1.events(F1.statements(t, csv))
    ev = ev[(ev["measure"] == "capex") & (pd.to_datetime(ev["known_from"]) > pd.Timestamp(when) - pd.Timedelta(days=365))]
    out = []
    for c, g in ev.groupby("company"):
        out.append({"company": c, "up": int((g["direction"] > 0).sum()), "unchanged": int((g["direction"] == 0).sum()),
                    "down": int((g["direction"] < 0).sum()), "last": str(pd.to_datetime(g["known_from"]).max().date())})
    return out


def next_filings(table: pd.DataFrame, when, n: int = 8) -> list[dict]:
    """Next filing per company: the next calendar quarter's end + the median lag of its last `n` first filings."""
    return C.next_filings(table, when, FILERS, n=n, max_lag=MAX_LAG)


def extraction(when, csv: pd.DataFrame | None = None) -> dict:
    """Rows of curated/kreditlagret.csv known on `when`, grouped for the report."""
    from ai_tracker.sources import kreditlagret as kl

    if csv is None:
        csv = kl.load() if kl.CSV_PATH.exists() else pd.DataFrame(columns=kl.COLUMNS)
    d = csv[csv["filed"] <= str(pd.Timestamp(when).date())]
    rows = [{k: r[k] for k in ("id", "company", "instrument", "field", "value", "unit", "period", "filed", "form",
                               "qualifier", "note")} for _, r in d.iterrows()]
    return {"rows": rows, "n": len(rows)}


def coupon_rows(csv: pd.DataFrame | None, when) -> pd.DataFrame | None:
    from ai_tracker.sources import kreditlagret as kl

    if csv is None:
        if not kl.CSV_PATH.exists():
            return None
        csv = kl.load()
    return csv[csv["filed"] <= str(pd.Timestamp(when).date())]


def convertible_mix(csv: pd.DataFrame, period: str) -> dict:
    """CoreWeave's weighted rate without convertibles at `period` and four quarters earlier, and the convertibles'
    share of outstanding (a description, register X23, point 4)."""
    ex = S.coupon_out(csv, "crwv", convertibles=False).set_index("period")["value"]
    prev = str(pd.Period(period, freq="Q-DEC") - 4)
    d = csv[(csv["company"] == "crwv") & (csv["field"] == "outstanding")]
    d = d[d["period"].map(lambda x: str(pd.Period(pd.Timestamp(x), freq="Q-DEC"))) == period]
    total = d["value"].astype(float).sum()
    conv = d[d["instrument"].str.contains(S.CONVERTIBLE)]["value"].astype(float).sum()
    r = csv[(csv["company"] == "crwv") & (csv["field"] == "rate_pct") & csv["instrument"].str.contains(S.CONVERTIBLE)
            & (csv["period"].map(lambda x: str(pd.Period(pd.Timestamp(x), freq="Q-DEC"))) == period)]
    rates = r["value"].astype(float)
    allr = S.coupon_out(csv, "crwv").set_index("period")["value"]
    return {"value_ex_conv": _num(ex.get(period)), "value_ex_conv_prev": _num(ex.get(prev)),
            "value_prev": _num(allr.get(prev)), "prev_period": prev,
            "conv_share": _num(conv / total) if total > 0 else None,
            "conv_rate_lo": _num(rates.min()) if len(rates) else None,
            "conv_rate_hi": _num(rates.max()) if len(rates) else None}


# ------------------------------------------------------------------ compute


def keys() -> dict[str, list[str]]:
    groups = {"price": [], "dependence": [], "ability": []}
    for m, group in (("rate_eff", "price"), ("fcfgap", "dependence"), ("netdebt", "dependence"),
                     ("leases", "dependence"), ("capex4", "ability"), ("rpo_add4", "ability")):
        for who in ("outer", *[c for c in S.COMPANIES[m] if c in S.OUTER], "inner",
                    *[c for c in S.COMPANIES[m] if c not in S.OUTER]):
            groups[group].append(f"kl_{m}_{who}")
    groups["price"].append("kl_coupon_out_crwv_q")
    groups["ability"] += list(POWER)
    return groups


def compute(as_of, table: pd.DataFrame | None = None, csv: pd.DataFrame | None = None) -> dict:
    when = pd.Timestamp(as_of)
    table, ctx = C.prepare(table)
    groups = keys()
    ms = {k: measure(k, when, ctx) for g in groups.values() for k in g}
    readings = {e: apply_reading(e, ms) for e in ("outer", *S.OUTER)}
    cur = coupon_rows(csv, when)
    crwv_cov = None
    if cur is not None and not cur.empty:
        co = S.coupon_out(cur, "crwv")
        if not co.empty:
            last = co.iloc[-1]
            crwv_cov = {"period": last.period, "value": float(last.value), "coverage": float(last.coverage),
                        "known_from": str(pd.Timestamp(last.known_from).date())}
            crwv_cov.update(convertible_mix(cur, last.period))
    return {
        "question": QUESTION, "as_of": str(when.date()), "generated": str(date.today()),
        "seen_before_register": str(when.date()) <= REGISTERED,
        "groups": groups, "measures": ms, "readings": readings,
        "limits": {"rate_rise_pp": RATE_RISE, "dependence_rise_pp": DEP_RISE, "capex_fall": CAPEX_FALL,
                   "equal_share": EQUAL_SHARE},
        "spreads": spreads(table, when), "guidance": guidance(table, when), "directions": directions(table, when),
        "revisions": revisions(table, when), "next_filings": next_filings(table, when),
        "extraction": extraction(when, cur), "coupon_out_crwv": crwv_cov,
    }


# ------------------------------------------------------------------ render


_f = C.fmt
_bn = C.fmt_bn


def _who(key: str) -> str:
    if key in LABEL:
        return LABEL[key]
    for w, n in S.NAMES.items():
        if key.endswith(f"_{w}") or key.endswith(f"_{w}_q"):
            return n[0].upper() + n[1:]
    return key


def _table(ms: dict, keys: list[str], level_fmt) -> list[str]:
    return C.measure_table(ms, keys, level_fmt, _who)


_pct = C.fmt_pct


def render(r: dict) -> str:
    ms, g = r["measures"], r["groups"]
    out = [f"# Kreditlagret per {r['as_of']}", "", f"**Frågan:** {r['question']}", "",
           "Yttre lagret: Oracle, CoreWeave, Nebius och IREN, och labben som tabellrader. Inre lagret: Microsoft, "
           "Alphabet, Amazon och Meta. Takt = förändring över fyra kvartal (procentenheter för andelar och räntor, "
           "log × 100 för belopp). Förändring i takt = mot två kvartal tidigare. Överraskning = mot den naiva "
           "baslinjen B1 (samma takt som de fyra senaste kvartalen). Bara data kända på dagen. Registret: "
           "`docs/mattregister.md`, 2026-11-25 KL1.", ""]

    out += ["## 1. Pris på skuld", "", "Effektiv ränta = räntekostnad över fyra kvartal / genomsnittlig långfristig skuld "
            "(efter aktiverad ränta, så den blir lägre hos bolag som bygger mycket). Microsofts räntekostnad innehåller "
            "ränta på finansiell leasing, men nämnaren är bara skulden. Microsofts tal, och därmed inre lagrets, är "
            "alltså ränta på skuld och leasing tillsammans och inte priset på skuld.", ""]
    out += _table(ms, [k for k in g["price"] if k.startswith("kl_rate_eff")], _pct)
    co = r.get("coupon_out_crwv")
    m = ms.get("kl_coupon_out_crwv_q", {})
    if co:
        out += ["", f"CoreWeave, angiven effektiv ränta på utestående skuld (vägd, hela procent i tabellen): "
                f"**{_f(co['value'], 1)} %** vid {co['period']} (täckning {_f(100 * co['coverage'], 0)} % av "
                f"utestående, known_from {co['known_from']}, `kl_coupon_out_crwv_q`). Takt: {_f(m.get('pace'), 1, True)} "
                f"procentenheter, förändring i takt {_f(m.get('change'), 1, True)}."]
        if co.get("conv_share"):
            out[-1] += (f" Konvertibler (angiven ränta {_f(co['conv_rate_lo'], 0)}–{_f(co['conv_rate_hi'], 0)} %) är "
                        f"{_f(100 * co['conv_share'], 1)} % av utestående. Utan konvertibler: "
                        f"{_pct(co.get('value_ex_conv'))} vid {co['period']} och {_pct(co.get('value_ex_conv_prev'))} "
                        f"vid {co.get('prev_period')}. Med konvertibler: {_pct(co['value'])} och "
                        f"{_pct(co.get('value_prev'))}. Skillnaden visar hur mycket mixen med konvertibler betyder.")
        elif co.get("conv_share") == 0:
            out[-1] += " Inga konvertibler i skuldtabellen."
    if r["spreads"]:
        out += ["", "Spread vid emission (KR1, registrerade obligationer, bp; oregelbundet, ingår inte i läsregeln):", ""]
        for s in r["spreads"]:
            prev = "" if s["prev_value"] is None else f", före: {_f(s['prev_value'], 0)} bp ({s['prev_period']})"
            out.append(f"- {S.NAMES[s['company']]} ({'yttre' if s['layer'] == 'outer' else 'inre'}): "
                       f"{_f(s['value'], 0)} bp i {s['period']}{prev}; known_from {s['known_from']}, `{s['series']}`")
    out += ["", "## 2. Beroende av extern finansiering", ""]
    for name, prefix in (("(capex − OCF) / capex", "kl_fcfgap"), ("(emitterad − amorterad skuld) / capex", "kl_netdebt"),
                         ("tecknade leasingavtal som inte börjat / capex", "kl_leases")):
        out += [f"**{name}**, fyra kvartal, procent av capex:", ""]
        out += _table(ms, [k for k in g["dependence"] if k.startswith(prefix + "_")], _pct) + [""]

    out += ["## 3. Vilja och förmåga att investera", "", "**Capex över fyra kvartal** (takt = årsförändring i log × 100):",
            ""]
    out += _table(ms, [k for k in g["ability"] if k.startswith("kl_capex4")], _bn)
    out += ["", "**Tillskott till RPO över fyra kvartal** (takt = log av tillskottet mot de fyra kvartalen före; klumpigt):",
            ""]
    out += _table(ms, [k for k in g["ability"] if k.startswith("kl_rpo_add4")], _bn)
    out += ["", "**CoreWeaves effekt** (MW, takt = log × 100 över fyra kvartal):", ""]
    out += _table(ms, list(POWER), lambda x: _f(x, 0) + " MW" if _num(x) is not None else "–")
    if r["guidance"]:
        out += ["", "**Capex-guidance för kalenderår** (mittpunkt; guidad takt mot föregående års utfall där F1:s "
                "definition finns):", ""]
        for x in r["guidance"]:
            gp = "" if x["guided_pace"] is None else f", guidad takt {_f(x['guided_pace'], 1, True)}"
            out.append(f"- {S.NAMES[x['company']]} {x['year']}: {_bn(x['lo'])}–{_bn(x['hi'])}{gp}; known_from "
                       f"{x['known_from']}")
    if r["directions"]:
        out += ["", "**Riktningskoder** för capex-planer (−2..+2 mot föregående år), uttalade det senaste året:", ""]
        for x in r["directions"]:
            out.append(f"- `{x['series']}` {x['period']}: {_f(x['code'], 0, True)} (known_from {x['known_from']})")
    if r["revisions"]:
        out += ["", "**F1: revideringar av capex-guidance de senaste 365 dagarna** (upp / oförändrad / ned):", ""]
        for x in r["revisions"]:
            out.append(f"- {S.NAMES.get(x['company'], x['company'])}: {x['up']} / {x['unchanged']} / {x['down']} "
                       f"(senast {x['last']})")

    out += ["", "## 4. Läsregeln, mekaniskt", "",
            f"Gränser (låsta): A = vid t − 2 har den effektiva räntan en takt ≥ +{_f(RATE_RISE, 2)} procentenheter "
            f"eller ett beroendemått ≥ +{_f(DEP_RISE, 0)}. Capex-takten föll om förändringen i takt ≤ {_f(CAPEX_FALL, 0)}. "
            "Lika fall: inre ≤ 0,5 × yttre. En negativ förändring i takt betyder att tillväxten avtar, inte att capex "
            "minskar. Utslaget är en beskrivning, inget test.", "",
            "Regeln läser bara uppgång i pris och beroende: A kräver en takt på minst gränsen. Ett fall i pris och "
            "beroende följt av högre capex-takt blir \"inget av mönstren\". Hur ofta A har gällt står under varje "
            "utslag. När A nästan alltid gäller, avgörs utslaget i praktiken av capex-takten. En regel som läser båda "
            "riktningarna kräver en ny daterad registerpost.", ""]
    if r.get("seen_before_register"):
        oracle = next((x for x in r["next_filings"] if x["company"] == "orcl"), None)
        when = f", för Oracle omkring {oracle['estimated']}" if oracle and oracle["estimated"] > REGISTERED else ""
        out += ["Alla kvartal i den här läsningen var kända före registerposten 2026-11-25, och flera av dem var sedda "
                "före posten (posten, avsnitt (e)). Läsningen är därför inget utfall på osedda data. Den första läsningen "
                f"på osedda kvartal kommer med inlämningar efter 2026-11-25{when}.", ""]
    for e, x in r["readings"].items():
        who = "Yttre lagret (huvudläsning)" if e == "outer" else f"{S.NAMES[e]} mot inre lagret"
        paces = ", ".join(f"{k} {_f(v, 1, True)}" for k, v in x["paces_t_minus_2"].items())
        out.append(f"- **{who}:** {x['text']}. t = {x['t'] or '–'}; A = {x['a']}"
                   f" (takt vid {x['t_minus_2'] or '–'}: {paces or '–'}); förändring i capex-takt yttre "
                   f"{_f(x['capex_change_outer'], 1, True)}, inre {_f(x['capex_change_inner'], 1, True)} "
                   f"({x['inner_period'] or '–'}).")
        h = x.get("a_history") or {}
        if h.get("of"):
            out.append(f"  A har gällt i {h['held']} av {h['of']} kvartal med minst en takt ({h['first']}–{h['last']}).")
        if x["missing"]:
            out.append(f"  Saknas: {'; '.join(x['missing'])}.")

    out += ["", "## 5. Labben och utvecklar- och SPV-kanalen (tabellrader ur inlämningarna)", ""]
    out += _lab_lines(r["extraction"]["rows"])

    out += ["", "## 6. Att bevaka", "", "Nästa inlämning per bolag, uppskattad som nästa kvartals slut plus medianen av "
            "avståndet för de åtta senaste inlämningarna:", ""]
    for x in r["next_filings"]:
        late = (f" (väntas nu, inte i tabellen ännu; därefter {x['then_period']} omkring {x['then_estimated']})"
                if x["overdue"] else "")
        out.append(f"- {FILER_NAMES[x['company']]}: {x['next_period']} omkring {x['estimated']}{late} "
                   f"(median {x['lag_days_median']} dagar, spann {x['lag_days_range'][0]}–{x['lag_days_range'][1]}, "
                   f"senast {x['last_filed']})")
    out += ["- Anthropic: första periodrapporten efter börsnoteringen; ingen historik att uppskatta från.", "",
            "## 7. Förbehåll", "",
            "- Med cirka 8–12 kvartal per mått är detta en beskrivning och inget test. Ett mönster kan vara slump.",
            "- RPO är klumpig: enstaka mycket stora avtal flyttar ett kvartal.",
            "- Neomolnens serier börjar 2024, så yttre lagrets takt och förändring i takt finns bara för de senaste "
            "kvartalen. Nebius och IREN saknar skuldserier och ingår bara i capex och (capex − OCF) / capex.",
            "- Den effektiva räntan är efter aktiverad ränta. Microsofts räntekostnad innehåller ränta på finansiell "
            "leasing. CoreWeaves räntor i skuldtabellen står i hela procent."
            + (" Konvertiblerna sänker den vägda räntan (avsnitt 1)." if (co or {}).get("conv_share") else ""),
            "- Regeln läser bara uppgång i pris och beroende. Hur ofta A har gällt står i avsnitt 4.",
            "- Utanför ramen: privat kredit utanför EDGAR, labbens oregistrerade skuld, spreadar på andrahandsmarknaden "
            "(licens) och 144A-affärer utan 8-K. OpenAI har ingen registreringsansökan på EDGAR."
            + (" SpaceX:s skuld gäller hela koncernen (uppskjutning, Starlink och xAI)."
               if any(x["company"] == "spacex" for x in r["extraction"]["rows"]) else ""),
            "- Nyhetsuppgifter om kreditbetyg (KBRA, Moody's) är sekundära och används inte som data.", ""]
    return "\n".join(out)


QUAL = {"at_least": "minst", "up_to": "upp till", "approx": "cirka"}
COUPON_NOTE = {  # the note's qualification, shown on the line (register X23, point 4)
    "anthropic_google_npa_2026": "för lån före noteringen; efter noteringen ska villkoren avtalas",
    "anthropic_amazon_npa_2026": "för lån före noteringen; efter noteringen regleras dragningar i aktier",
}
MARGIN_NOTE = {"crwv_ddtl_2_0_facility": "före femte tillägget och utan investment grade; med investment grade 600–650"}
COUNTERPARTIES = (("anthropic_commit_microsoft", "Microsoft"), ("anthropic_commit_google", "Google"),
                  ("anthropic_commit_amazon", "Amazon"), ("anthropic_commit_spacexai", "SpaceXAI (SpaceX)"),
                  ("anthropic_commit_nscale", "Nscale"), ("anthropic_commit_lambda", "Lambda"))


def _lab_lines(rows: list[dict]) -> list[str]:
    by = {}
    for x in rows:
        by.setdefault((x["instrument"], x["field"], x["period"]), x)

    def val(inst, field, period=""):
        x = by.get((inst, field, period))
        return None if x is None else x

    def num(x) -> float:
        return float(x["value"]) if x else 0.0

    out = []
    ant = [x for x in rows if x["company"] == "anthropic"]
    if not ant:
        out.append("- Anthropic: ingen registreringsansökan känd på dagen.")
    else:
        first = min(x["filed"] for x in ant)
        out.append(f"- **Anthropic** (S-1 och ändringar, första {first}). Läge 2026-09-30:")
        for inst, label in (("anthropic_ar_credit_facility", "säkerställd revolverande kreditfacilitet"),
                            ("anthropic_broadcom_npa_2026", "konvertibelram för hyra (Broadcom), PIK"),
                            ("anthropic_google_npa_2026", "ram Google 2026"), ("anthropic_amazon_npa_2026",
                                                                                "ram Amazon 2026")):
            com = [x for x in ant if x["instrument"] == inst and x["field"] == "commitment"]
            if com:
                last = sorted(com, key=lambda x: x["period"])[-1]
                cp = val(inst, "coupon_pct")
                cps = f", kupong {_f(cp['value'], 2)} %" if cp else ""
                if cp and inst in COUPON_NOTE:
                    cps += f" {COUPON_NOTE[inst]}"
                out.append(f"  - {label}: {_bn(last['value'])} ({last['period']}{cps}; known_from {last['filed']})")
        notes = [x for x in ant if x["field"] == "outstanding" and x["instrument"].startswith("anthropic_amazon_20")]
        if notes:
            tot = sum(float(x["value"]) for x in notes)
            out.append(f"  - utestående konvertibla lån till Amazon: {_bn(tot)}, räntefria (known_from "
                       f"{max(x['filed'] for x in notes)})")
        for inst, label in (("anthropic_oblig_purchase_commitments", "köpåtaganden i tabellen"),
                            ("anthropic_leases_not_commenced", "leasingavtal som inte börjat, cirka"),
                            ("anthropic_oblig_aggregate", "åtaganden totalt enligt bolaget, cirka")):
            x = val(inst, "due_total", "2026-09-30")
            if x:
                out.append(f"  - {label}: {_bn(x['value'])} (known_from {x['filed']})")
        years = [val("anthropic_oblig_purchase_commitments", f"due_{y}", "2026-09-30") for y in range(2026, 2031)]
        if all(years):
            out.append("  - köpåtaganden per år 2026–2030: " + ", ".join(_bn(y["value"]) for y in years))
        cps = [(name, x) for inst, name in COUNTERPARTIES
               for x in [next((y for y in ant if y["instrument"] == inst and y["field"] == "commitment"), None)] if x]
        if cps:
            out.append("  - åtaganden för beräkningskraft per motpart (avtalsmånad): " + ", ".join(
                f"{name} {QUAL.get(x['qualifier'], '')} {_bn(x['value'])} ({x['period']})".replace("  ", " ")
                for name, x in cps) + f"; known_from senast {max(x['filed'] for _, x in cps)}")
    out.append("- OpenAI: ingen registreringsansökan på EDGAR (sökning på namnet 2026-11-25: bara fonder och SPV med "
               "Form D).")
    sx = [x for x in rows if x["company"] == "spacex"]
    if sx:
        last = max(x["period"] for x in sx if x["instrument"] == "spacex_total_debt")
        tot, notes = val("spacex_total_debt", "outstanding", last), val("spacex_notes", "outstanding", last)
        nr, cp = val("spacex_notes", "rate_pct", last), val("spacex_notes", "coupon_pct")
        other, orate = val("spacex_other_financings", "outstanding", last), val("spacex_other_financings", "rate_pct", last)
        valor = [val(f"spacex_valor_{k}", "outstanding", last) for k in ("current", "noncurrent")]
        kf = max(x["filed"] for x in sx if x["period"] == last)
        out.append(f"- **SpaceX** (äger xAI sedan 2026-02-02; 10-Q). Skulden gäller hela koncernen: uppskjutning, "
                   f"Starlink och xAI. Läge {last}:")
        parts = [f"total skuld {_bn(num(tot))}"]
        if notes:
            parts.append(f"SpaceX Notes {_bn(num(notes))} (effektiv ränta {_f(num(nr), 2)} %, vägd kupong "
                         f"{_f(num(cp), 3)} %, emitterade 2026-06)" if nr and cp else f"SpaceX Notes {_bn(num(notes))}")
        if other:
            o = f"övrig finansiering {_bn(num(other))}"
            if all(valor):
                o += (f", varav misslyckade sale-leaseback av AI-hårdvara med Valor (närstående) "
                      f"{_bn(sum(num(v) for v in valor))}")
            parts.append(o)
        out.append(f"  - {'; '.join(parts)}; known_from {kf}")
        if other:  # the rate on other financings, qualified, next to Valor's interest expense (register X24, point 2)
            q = pd.Period(pd.Timestamp(last), freq="Q-DEC")
            prev = str((q - 1).end_time.date())
            ie = val("spacex_valor", "interest_expense_q", last)
            before = [val(f"spacex_valor_{k}", "outstanding", prev) for k in ("current", "noncurrent")]
            said, used = [], [x for x in (ie, orate) if x]
            if ie:
                s = f"räntekostnaden för Valor-avtalen var {_f(num(ie), 0)} MUSD under {q}"
                if all(valor) and all(before):
                    mean = (sum(num(v) for v in valor) + sum(num(v) for v in before)) / 2
                    s += f", cirka {_f(400 * num(ie) / mean, 1)} % per år av Valor-skulden i snitt ({prev} och {last})"
                    used += before
                said.append(s)
            else:
                said.append("räntekostnaden för Valor-avtalen är inte kodad för kvartalet")
            if orate:
                said.append(f"Bolaget anger {_f(num(orate), 1)} % i vägd fast ränta för sina övriga finansieringsavtal, "
                            f"som oftast har maskiner och utrustning som säkerhet. Om Valor-skulden ingår i den räntan "
                            f"framgår inte")
            kf_r = max(x["filed"] for x in used) if used else kf
            out.append(f"  - ränta på övrig finansiering: {'. '.join(said)} (known_from {kf_r})")
        cf = sorted([x for x in sx if x["instrument"] == "spacex_credit_facility" and x["field"] == "commitment"],
                    key=lambda x: x["period"])
        if cf:
            out.append(f"  - kreditfacilitet upp till {_bn(cf[-1]['value'])} ({cf[-1]['period']}, utan säkerhet; "
                       f"known_from {cf[-1]['filed']})")
        xai = [(i, val(i, "principal", "2025-06")) for i in ("spacex_xai_secured_notes", "spacex_xai_fixed_term_loan",
                                                             "spacex_xai_floating_term_loan")]
        if all(x for _, x in xai):
            c1, c2 = val("spacex_xai_secured_notes", "coupon_pct"), val("spacex_xai_fixed_term_loan", "coupon_pct")
            mg = val("spacex_xai_floating_term_loan", "margin_bp")
            out.append(f"  - xAI:s egna lån före köpet (2025-06): säkerställda obligationer {_bn(num(xai[0][1]))} med "
                       f"{_f(num(c1), 1)} %, terminslån {_bn(num(xai[1][1]))} med {_f(num(c2), 2)} % och "
                       f"{_bn(num(xai[2][1]))} med SOFR + {_f(num(mg), 0)} bp; inte kvar i tabellen per {last}")
    meta = [x for x in rows if x["company"] == "meta" and x["instrument"] == "meta_dc_ventures"]
    if meta:
        names = ["Louisiana, med fonder förvaltade av Blue Owl"]
        if any(x["instrument"] == "meta_texas_venture" for x in rows):
            names.append("Texas från 2026-07")
        out.append(f"- **Meta, datacenterbolag** ({'; '.join(names)}). Per balansdag:")
        for period in sorted({x["period"] for x in meta}):
            got = {x["field"]: x for x in meta if x["period"] == period}
            parts = [f"{lab} {_bn(got[f]['value'])}" for f, lab in (("lease_commitment", "leasingåtaganden"),
                                                                     ("rvg_max", "restvärdesgarantier"),
                                                                     ("exposure_max", "största möjliga förlust"))
                     if f in got]
            kf = max(x["filed"] for x in got.values())
            out.append(f"  - {period}: {', '.join(parts)} (known_from {kf})")
    lou = {x["field"]: x for x in rows if x["instrument"] == "meta_louisiana_venture"}
    if lou and not meta:
        parts = [f"{lab} {_bn(lou[f]['value'])}" for f, lab in (("contribution", "Metas insats"),
                                                                 ("lease_commitment", "leasingåtagande cirka"),
                                                                 ("rvg_max", "restvärdesgaranti från"))
                 if f in lou]
        out.append(f"- **Meta, datacenterbolag i Louisiana med fonder förvaltade av Blue Owl**, bildat 2025-10: "
                   f"{', '.join(parts)} (known_from {max(x['filed'] for x in lou.values())})")
    out.append("- Oracle: inga belopp för datacenter-SPV eller samriskbolag i 10-Q och 10-K 2025–2026.")
    crwv = [x for x in rows if x["company"] == "crwv" and x["field"] == "principal"]
    if crwv:
        out.append("- **CoreWeave, nya obligationer** (8-K, senaste sex; konvertibler ingår inte i kupongmåttet):")
        for x in sorted(crwv, key=lambda x: x["period"])[-6:]:
            cp = by.get((x["instrument"], "coupon_pct", ""))
            unit = "MEUR" if x["unit"] == "MEUR" else "MUSD"
            out.append(f"  - {x['period']}: {x['instrument'].removeprefix('crwv_').replace('_', ' ')}, "
                       f"{_f(x['value'], 2 if float(x['value']) < 10 else 0)} {unit}"
                       f"{', kupong ' + _f(cp['value'], 3) + ' %' if cp else ''} (known_from {x['filed']})")
    margins = [x for x in rows if x["company"] == "crwv" and x["field"] == "margin_bp"]
    if margins:
        out.append("- CoreWeave, marginal över SOFR för lånefaciliteter (bp): " + ", ".join(
            f"{x['instrument'].removeprefix('crwv_').replace('_', ' ')} {_f(x['value'], 0)}"
            + (f" ({MARGIN_NOTE[x['instrument']]})" if x["instrument"] in MARGIN_NOTE else "")
            for x in sorted(margins, key=lambda x: x["filed"])))
    return out
