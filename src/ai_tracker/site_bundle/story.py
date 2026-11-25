"""W13: the monthly story (månadens berättelse), selected by the pre-registered rule in docs/mattregister.md
("2026-11-25 – W13: urvalsregel för månadens berättelse").

`select` is the rule: a pure function from one month's inputs (the month's record, the previous month's record, the
A5 reconciliations of both, the live nowcast outcomes and the C4 section) to the month's cards, in the registered
order and within the registered caps. No clock, no randomness: the same inputs give the same document.
`docs` gathers those inputs from a site.data.Record for every month of the record's history and returns the bundle
documents story/<YYYY-MM>.json and story/index.json.

The rule only selects and orders. It computes no new measure: states, indices, percentiles, intervals, errors and the
C4 shifts and breaks come from the record, the committed forecast files and the snapshots.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable

import pandas as pd

from ai_tracker.letter import BANNED_WORDS, change_text, month_sv, pace_text
from ai_tracker.site.render import num
from ai_tracker.state import register as R

ENTRY = "2026-11-25 – W13: urvalsregel för månadens berättelse"
HIGH, LOW = 95.0, 5.0  # extreme percentile zones (K5, K6): >= HIGH or <= LOW
ZONE_BOUND = {"övre": "≥ 95", "nedre": "≤ 5"}  # a card names only its own zone's bound (R-W3)
CAP = 8  # event cards (K1-K6) per month
TYPE_CAPS = {"K4": 3, "K5": 3, "K6": 2}
EVENT_TYPES = ("K1", "K2", "K3", "K4", "K5", "K6")
TYPE_LABEL = {
    "K0": "Läget",
    "K1": "Tillståndsskifte",
    "K2": "Regimskifte",
    "K3": "Nytt skarpt utfall",
    "K4": "Strukturbrott",
    "K5": "Kärnserie i extrem percentil",
    "K6": "Avstämning i extrem percentil",
    "K9": "Inga utslag",
}
CONDITION_TEXT = {
    "K1": "tillståndsskifte i en gren",
    "K2": "regimskifte enligt C4",
    "K3": "nytt skarpt utfall",
    "K4": "strukturbrott enligt C4",
    "K5": "räknad kärnserie i extrem percentil för förändring i takt (≤ 5 eller ≥ 95)",
    "K6": "avstämning i extrem percentil för takt (≤ 5 eller ≥ 95)",
}
NEEDS_PREVIOUS = ("K1", "K5", "K6")
TYPE_PLURAL = {"K1": "tillståndsskiften", "K2": "regimskiften", "K3": "nya skarpa utfall", "K4": "strukturbrott",
               "K5": "kärnserier i extrem percentil", "K6": "avstämningar i extrem percentil"}
# Alarm words (the register entry): never in a generated text, next to the letter's judging words.
ALARM_WORDS = re.compile(r"\b(larm\w*|varning\w*|kris\w*|rekord\w*|dramatisk\w*|kollaps\w*|ras|rasar|rasade|rusar|"
                         r"rusade|chock\w*|oroväckande|alarmerande)\b", re.IGNORECASE)
STATE_ORDER = {R.STATE_BRAKE: -1, R.STATE_STABLE: 0, R.STATE_ACCEL: 1}
DIRECTION_WORD = {1: "accelererar", 0: "stabil", -1: "bromsar in"}
SHIFT_DIRECTION = {"inbromsning": -1, "expansion": 1}
LEVELS = ("50", "80", "95")
INTERVAL_WHERE = {
    3: "utanför 95 %-intervallet",
    2: "inom 95 % men utanför 80 %-intervallet",
    1: "inom 80 % men utanför 50 %-intervallet",
    0: "inom 50 %-intervallet",
    None: "utan lagrade intervall",
}
MONTHS_SHORT = ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]
MONTHS_SV = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober",
             "november", "december"]


def rule() -> dict:
    return {"register": "docs/mattregister.md", "entry": ENTRY, "cap": CAP, "type_caps": dict(TYPE_CAPS),
            "high": HIGH, "low": LOW, "order": list(EVENT_TYPES)}


# ------------------------------------------------------------------ text helpers


def _r(x, digits: int = 5):
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(x):
        return None
    return float(f"{x:.{digits}g}") if x else 0.0


def day_sv(day: str | None) -> str:
    if not day:
        return "–"
    t = pd.Timestamp(day)
    return f"{t.day} {MONTHS_SV[t.month - 1]} {t.year}"


def period_sv(period: str | None) -> str:
    if not period:
        return "–"
    if re.fullmatch(r"\d{4}-\d{2}", period):
        return month_sv(period)
    m = re.fullmatch(r"(\d{4})Q([1-4])", period)
    if m:
        return f"kvartal {m.group(2)} {m.group(1)}"
    return period


def pct(p) -> str:
    return num(p, 1)


def zone_of(p) -> str | None:
    if p is None or not math.isfinite(p):
        return None
    return "övre" if p >= HIGH else "nedre" if p <= LOW else None


def _plural(n: int, one: str, many: str) -> str:
    return f"{({0: 'inga', 1: 'ett'}.get(n, str(n)))} {one if n == 1 else many}"


def _count_word(n: int) -> str:
    return {0: "ingen", 1: "en"}.get(n, str(n))


def texts(doc: dict) -> list[str]:
    """Every generated text of a story document (for the neutrality test)."""
    out = [doc.get("headline") or ""]
    for c in doc.get("cards", []):
        out += [c.get("title") or "", c.get("text") or "", (c.get("link") or {}).get("label") or ""]
    return out


def neutral(text: str) -> bool:
    return not BANNED_WORDS.search(text) and not ALARM_WORDS.search(text)


# ------------------------------------------------------------------ the rule


def _counted(branches: dict | None) -> dict[str, tuple[str, dict]]:
    """key -> (branch code, measure) of the counted series of a record (series_used)."""
    out: dict[str, tuple[str, dict]] = {}
    for code in sorted(branches or {}):
        for m in (branches[code] or {}).get("series_used") or []:
            k = m.get("series")
            if k and k not in out:
                out[k] = (code, m)
    return out


def _previous_note(prev: dict | None, field: str, zone: str) -> tuple[float | None, str]:
    if prev is None:
        return None, "räknades inte förra månaden"
    p = prev.get(field)
    if p is None or not math.isfinite(p):
        return None, "saknade percentil förra månaden"
    z = zone_of(p)
    if z is None:
        return _r(p), f"percentil {pct(p)} förra månaden, utanför zonerna"
    return _r(p), f"percentil {pct(p)} förra månaden, i den {z} zonen"


def _track(history: dict | None, month: str, field: str) -> dict | None:
    """The record's values of `field` for one series per month up to `month` (from `history`: month -> measure)."""
    if not history:
        return None
    months = sorted(m for m in history if m <= month)
    if not months:
        return None
    return {"field": field, "months": months, "values": [_r((history[m] or {}).get(field)) for m in months]}


def _link(kind: str, label: str, id_: str | None = None, slug: str | None = None) -> dict:
    return {"kind": kind, "id": id_, "slug": slug, "label": label}


def _interval_class(outcome, intervals: dict | None) -> int | None:
    if outcome is None or not intervals or any(not intervals.get(k) for k in LEVELS):
        return None
    for cls, k in ((0, "50"), (1, "80"), (2, "95")):
        lo, hi = intervals[k]
        if lo is None or hi is None:
            return None
        if min(lo, hi) <= outcome <= max(lo, hi):
            return cls
    return 3


def select(inp: dict, publishable: Callable[[str], bool], label: Callable[[str], str]) -> dict:
    """The rule applied to one month. `inp`:

    month, kind ("skarp"/"rekonstruerad"), known (YYYY-MM-DD), branches (code -> record branch), branch_names,
    previous (YYYY-MM or None), prev_branches (or None), recon / prev_recon (lists of A5 measures, prev None without a
    comparison), outcomes (scorecard rows of the committed forecast files, see `outcome_rows`), regime (None, or
    {"blocks": [{block, label, shift, p_slow}], "breaks": [{series, branch, latest_period, p_recent}]} from the
    month's live snapshot), history (series key -> {month: measure}, the record's measures per month) and
    recon_history (the same for the A5 series).
    """
    month, known = inp["month"], inp["known"]
    status = "live" if inp["kind"] == "skarp" else "reconstructed"
    names = inp.get("branch_names") or {}
    branches = inp.get("branches") or {}
    prev_month, prev = inp.get("previous"), inp.get("prev_branches")
    has_prev = prev_month is not None and prev is not None
    start = str(pd.Period(month, "M").start_time.date())
    cand: dict[str, list[tuple[tuple, dict]]] = {t: [] for t in EVENT_TYPES}
    withheld = {t: 0 for t in EVENT_TYPES}

    # K1: state changes
    if has_prev:
        for code in sorted(branches):
            cur, p = branches.get(code) or {}, prev.get(code)
            if not p or cur.get("state") == p.get("state"):
                continue
            idx, pidx = cur.get("index"), p.get("index")
            delta = idx - pidx if idx is not None and pidx is not None else None
            a, b = STATE_ORDER.get(p.get("state")), STATE_ORDER.get(cur.get("state"))
            direction = None if a is None or b is None else (1 if b > a else -1)
            name = names.get(code, code)
            n_s = cur.get("n_series") or 0
            counts = (f"{_count_word(cur.get('n_up') or 0)} accelererar, {_count_word(cur.get('n_neutral') or 0)} "
                      f"{'är stabil' if (cur.get('n_neutral') or 0) == 1 else 'är stabila'} och "
                      f"{_count_word(cur.get('n_down') or 0)} bromsar in")
            text = (f"Diffusionsindex {num(pidx, 3)} i {month_sv(prev_month)} och {num(idx, 3)} i {month_sv(month)}"
                    + (f" ({num(delta, 3, signed=True)})" if delta is not None else "") + ". "
                    + (f"Av {n_s} räknade serier: {counts}. " if n_s else "")
                    + f"Gränserna är {num(R.BRAKING, 2)} (bromsar in) och {num(R.ACCELERATING, 2)} (accelererar).")
            title = f"{code} {name}: {p.get('state')} → {cur.get('state')}"
            card = {"type": "K1", "id": f"k1-{code}", "title": title,
                    "text": text, "direction": direction, "link": _link("branch", f"Till grenen {code}", code),
                    "facts": {"branch": code, "name": name, "from": p.get("state"), "to": cur.get("state"),
                              "index": _r(idx, 4), "prev_index": _r(pidx, 4), "delta_index": _r(delta, 4),
                              "n_series": cur.get("n_series"), "n_up": cur.get("n_up"),
                              "n_neutral": cur.get("n_neutral"), "n_down": cur.get("n_down")},
                    "track": None}
            cand["K1"].append(((-round(abs(delta or 0.0), 6), code), card))  # rounded: float noise is no order

    # K2 and K4: C4 in the month's live snapshot
    regime = inp.get("regime") or {}
    for i, b in enumerate(regime.get("blocks") or []):
        shift = b.get("shift")
        if not shift:
            continue
        p = b.get("p_slow")
        rule_text = ("Ett skifte till inbromsning rapporteras när P(inbromsning) är minst 0,8 två månader i rad"
                     if shift == "inbromsning" else
                     "Ett skifte till expansion rapporteras när P(inbromsning) är högst 0,2 två månader i rad")
        card = {"type": "K2", "id": f"k2-{b.get('block')}", "title": f"Regimskifte i blocket {b.get('label')}: {shift}",
                "text": f"P(inbromsning) är {num(p, 2)} i {month_sv(month)}. {rule_text} (G-D, C4).",
                "direction": SHIFT_DIRECTION.get(shift), "link": _link("regime", "Till regimsidan"),
                "facts": {"block": b.get("block"), "label": b.get("label"), "shift": shift, "p_slow": _r(p, 3)},
                "track": None}
        cand["K2"].append(((i,), card))
    for x in regime.get("breaks") or []:
        key = x.get("series")
        if not key or not publishable(key):
            withheld["K4"] += 1
            continue
        p = x.get("p_recent")
        card = {"type": "K4", "id": f"k4-{key}", "title": f"Strukturbrott i {label(key)} ({x.get('branch')})",
                "text": (f"C4 rapporterar ett brott i takten (BOCPD, G-D) för senaste perioden "
                         f"{period_sv(x.get('latest_period'))}. Sannolikheten för en kort körlängd (0–2 perioder) "
                         f"är {num(p, 2)}."),
                "direction": None, "link": _link("series", "Till serien", key),
                "facts": {"series": key, "label": label(key), "branch": x.get("branch"),
                          "latest_period": x.get("latest_period"), "p_recent": _r(p, 3)},
                "track": _track((inp.get("history") or {}).get(key), month, "pace")}
        cand["K4"].append(((-round(p or 0.0, 6), key), card))

    # K3: new live outcomes
    for r in inp.get("outcomes") or []:
        kf, origin = r.get("known_from"), r.get("origin")
        if r.get("status") != "utfall" or not kf or not origin or not (start <= kf <= known) or origin > known:
            continue
        if not r.get("publishable"):
            withheld["K3"] += 1
            continue
        cls = _interval_class(r.get("outcome"), r.get("intervals"))
        err = r.get("err_champion")
        dec = r.get("decimals") or 0
        unit = r.get("unit") or ""
        parts = [(f"Prognos {num(r.get('forecast'), dec)} {unit} ({r.get('champion')}, prognosdag {day_sv(origin)}). "
                  f"Utfall {num(r.get('outcome'), dec)} {unit}, känt {day_sv(kf)}. "
                  f"Fel huvudmodell {num(err, 1, signed=True)} ({r.get('error_unit')}, positivt = prognosen låg över "
                  f"utfallet).")]
        for k, word in (("baseline", "Naiv baslinje"), ("guidance", "Guidance")):
            v = r.get(k)
            if v and v.get("err") is not None:
                parts.append(f"{word} {v['variant']}: fel {num(v['err'], 1, signed=True)}.")
        period = r.get("period")
        card = {"type": "K3", "id": f"k3-{r['nowcast']}-{period}",
                "title": f"{r.get('label')} {r.get('title')}, {period_sv(period)}: utfallet {INTERVAL_WHERE[cls]}",
                "text": " ".join(parts), "direction": None,
                "link": _link("nowcast", f"Till prognosen {r.get('label')} {period_sv(period)}", r["nowcast"],
                              r.get("slug")),
                "facts": {k: r.get(k) for k in ("nowcast", "label", "title", "period", "origin", "file", "slug",
                                                 "champion", "unit", "decimals", "error_unit", "forecast",
                                                 "outcome", "known_from", "intervals", "baseline", "guidance")}
                | {"interval_class": cls, "err_champion": _r(err)},
                "track": None}
        key3 = (-(cls if cls is not None else -1), -round(abs(err or 0.0), 6), r["nowcast"], period or "")
        cand["K3"].append((key3, card))

    # K5: counted core series entering an extreme zone of the change-in-pace percentile
    if has_prev:
        cur_c, prev_c = _counted(branches), _counted(prev)
        for key in sorted(cur_c):
            code, m = cur_c[key]
            p = m.get("change_percentile")
            z = zone_of(p)
            if not m.get("valid") or z is None:
                continue
            pm = (prev_c.get(key) or (None, None))[1]
            if pm is not None and zone_of(pm.get("change_percentile")) == z:
                continue
            if not publishable(key):
                withheld["K5"] += 1
                continue
            pp, note = _previous_note(pm, "change_percentile", z)
            d = m.get("direction")
            inv = m.get("method") in ("doubling", "halving")
            text = (f"Takten är {pace_text(m, with_unit=True)}, och förändringen i takt är {change_text(m)}. Det är "
                    f"percentil {pct(p)} av seriens egen historik, i den {z} zonen ({ZONE_BOUND[z]}). Jämförelse: "
                    f"{note}. Seriens riktning i {code}: {DIRECTION_WORD.get(d, '–')}."
                    + (" För fördubblings- och halveringstid betyder en högre percentil en längre tid." if inv else ""))
            card = {"type": "K5", "id": f"k5-{key}",
                    "title": f"{label(key)} ({code}): förändringen i takt i percentil {pct(p)}", "text": text,
                    "direction": d, "link": _link("series", "Till serien", key),
                    "facts": _percentile_facts(key, label(key), code, m, "change_percentile", z, pp, note),
                    "track": _track((inp.get("history") or {}).get(key), month, "change_percentile")}
            cand["K5"].append(((-round(abs(p - 50.0), 6), key), card))

    # K6: reconciliations entering an extreme zone of the pace percentile
    if has_prev and inp.get("prev_recon") is not None:
        prev_r = {m.get("series"): m for m in inp["prev_recon"] if m.get("series")}
        for m in sorted(inp.get("recon") or [], key=lambda m: m.get("series") or ""):
            key = m.get("series")
            p = m.get("pace_percentile")
            z = zone_of(p)
            if not key or z is None:
                continue
            pm = prev_r.get(key)
            if pm is not None and zone_of(pm.get("pace_percentile")) == z:
                continue
            if not publishable(key):
                withheld["K6"] += 1
                continue
            pp, note = _previous_note(pm, "pace_percentile", z)
            if pm is None:
                note = "inget mått förra månaden"
            text = (f"Takten i kvoten är {pace_text(m, with_unit=True)}. Det är percentil {pct(p)} av kvotens egen "
                    f"historik, i den {z} zonen ({ZONE_BOUND[z]}). Jämförelse: {note}. Avstämningarna räknas inte i "
                    f"grenarnas diffusionsindex (A5).")
            card = {"type": "K6", "id": f"k6-{key}", "title": f"{label(key)}: takten i percentil {pct(p)}",
                    "text": text, "direction": 1 if z == "övre" else -1,
                    "link": _link("series", "Till avstämningen", key),
                    "facts": _percentile_facts(key, label(key), None, m, "pace_percentile", z, pp, note),
                    "track": _track((inp.get("recon_history") or {}).get(key), month, "pace_percentile")}
            cand["K6"].append(((-round(abs(p - 50.0), 6), key), card))

    # order, per-type caps, total cap
    qualified = {t: len(cand[t]) for t in EVENT_TYPES}
    events: list[dict] = []
    omitted = {t: 0 for t in EVENT_TYPES}
    for t in EVENT_TYPES:
        ordered = [c for _, c in sorted(cand[t], key=lambda kc: kc[0])]
        keep = ordered[:TYPE_CAPS.get(t, len(ordered))]
        omitted[t] += len(ordered) - len(keep)
        for c in keep:
            if len(events) < CAP:
                events.append(c)
            else:
                omitted[t] += 1

    cards = [_k0(inp, has_prev, status)]
    if not events:
        cards.append(_k9(month, has_prev))
    cards += events
    for i, c in enumerate(cards):
        c["rank"] = i
        c["type_label"] = TYPE_LABEL[c["type"]]
        c["status"] = status
    n_events = len(events)
    by_type = {t: sum(1 for c in events if c["type"] == t) for t in EVENT_TYPES}
    if n_events:
        parts = [f"{by_type[t]} {TYPE_LABEL[t].lower() if by_type[t] == 1 else TYPE_PLURAL[t]}" for t in EVENT_TYPES
                 if by_type[t]]
        headline = (f"{month_sv(month).capitalize()}: {n_events} kort enligt den "
                    f"förregistrerade regeln ({', '.join(parts)}).")
    else:
        headline = f"{month_sv(month).capitalize()}: inget av regelns villkor uppfylldes."
    return {"month": month, "month_sv": month_sv(month), "kind": inp["kind"], "status": status, "known": known,
            "previous": prev_month if has_prev else None, "rule": rule(), "headline": headline,
            "n_events": n_events, "types": by_type, "qualified": qualified, "omitted": omitted,
            "withheld": withheld, "cards": cards}


def _percentile_facts(key, lab, code, m, field, zone, pp, note) -> dict:
    return {"series": key, "label": lab, "branch": code, "latest_period": m.get("latest_period"),
            "known_from": m.get("known_from"), "method": m.get("method"),
            "measure_freq": m.get("measure_freq") or m.get("freq"), "pace": _r(m.get("pace")),
            "pace_unit": m.get("pace_unit"), "change_in_pace": _r(m.get("change_in_pace")), "field": field,
            "percentile": _r(m.get(field)), "zone": zone, "prev_percentile": pp, "prev_note": note}


def _k0(inp: dict, has_prev: bool, status: str) -> dict:
    branches, prev = inp.get("branches") or {}, inp.get("prev_branches") or {}
    counts = {s: 0 for s in (R.STATE_ACCEL, R.STATE_STABLE, R.STATE_BRAKE, R.STATE_FEW)}
    for b in branches.values():
        s = (b or {}).get("state") or R.STATE_FEW
        counts[s if s in counts else R.STATE_FEW] += 1
    with_state = counts[R.STATE_ACCEL] + counts[R.STATE_STABLE] + counts[R.STATE_BRAKE]
    stable = f"{_count_word(counts[R.STATE_STABLE])} {'är stabil' if counts[R.STATE_STABLE] == 1 else 'är stabila'}"
    text = (f"Av {with_state} grenar med tillstånd: {_count_word(counts[R.STATE_ACCEL])} accelererar, {stable} och "
            f"{_count_word(counts[R.STATE_BRAKE])} bromsar in.")
    if counts[R.STATE_FEW]:
        text += f" {counts[R.STATE_FEW]} {'gren har' if counts[R.STATE_FEW] == 1 else 'grenar har'} för få serier."
    moves = None
    if has_prev:
        up = down = same = 0
        for code, b in branches.items():
            p = prev.get(code) or {}
            i, j = (b or {}).get("index"), p.get("index")
            if i is None or j is None:
                continue
            d = round(i, 2) - round(j, 2)
            if abs(d) < 1e-9:
                same += 1
            elif d > 0:
                up += 1
            else:
                down += 1
        moves = {"up": up, "down": down, "same": same}
        text += (f" Mot {month_sv(inp['previous'])}: {_count_word(up)} med högre index, {_count_word(down)} med "
                 f"lägre och {_count_word(same)} med samma (två decimaler).")
    else:
        text += " Ingen föregående månad att jämföra med."
    title = f"Läget i {month_sv(inp['month'])}" + (" (rekonstruerat)" if status == "reconstructed" else "")
    return {"type": "K0", "id": "k0", "title": title, "text": text, "direction": None,
            "link": _link("start", "Till läget"),
            "facts": {"counts": counts, "n_with_state": with_state, "moves": moves,
                      "previous": inp.get("previous") if has_prev else None},
            "track": None}


def _k9(month: str, has_prev: bool) -> dict:
    conds = [{"type": t, "label": CONDITION_TEXT[t], "checked": has_prev or t not in NEEDS_PREVIOUS}
             for t in EVENT_TYPES]
    checked = [c["label"] for c in conds if c["checked"]]
    text = (f"Regelns villkor som prövades: {'; '.join(checked)}. Inget av dem uppfylldes i {month_sv(month)}, "
            "och regeln väljer inga ersättare.")
    if not has_prev:
        text += (" Utan föregående månad kunde tillståndsskiften och extrema percentiler (K1, K5 och K6) inte "
                 "prövas.")
    return {"type": "K9", "id": "k9", "title": f"Inga utslag i {month_sv(month)}", "text": text, "direction": None,
            "link": _link("method", "Till metoden"), "facts": {"conditions": conds}, "track": None}


# ------------------------------------------------------------------ inputs from the record


def outcome_rows(nowcasts: list[dict]) -> list[dict]:
    """K3 candidates: every scorecard row of every committed forecast file, with the champion's stored intervals,
    the naive baseline (B1, else B0) and the guidance variant (B2) where the nowcast has one."""
    out = []
    for n in nowcasts:
        files = {f.get("period"): f for f in n.get("forecasts") or []}
        variants = [v.get("id") for v in n.get("variants") or []]
        base = "B1" if "B1" in variants else "B0" if "B0" in variants else None
        guid = "B2" if "B2" in variants else None
        for r in n.get("scorecard") or []:
            f = files.get(r.get("period")) or {}
            iv = {k: r.get(f"interval_{k}") for k in LEVELS}
            iv = iv if all(iv.values()) else (f.get("intervals") or None)
            slug = (f.get("file") or "").rsplit("/", 1)[-1].removesuffix(".json") or None
            row = {"nowcast": n["id"], "label": n.get("label"), "title": n.get("title"),
                   "publishable": bool(n.get("publishable", True)), "unit": n.get("unit"),
                   "decimals": n.get("decimals") or 0, "error_unit": n.get("error_unit"),
                   "period": r.get("period"), "origin": r.get("origin"), "file": f.get("file"),
                   "slug": re.sub(r"[^A-Za-z0-9_.-]", "_", slug) if slug else None,
                   "champion": r.get("champion"), "status": r.get("status"), "known_from": r.get("known_from"),
                   "forecast": _r(r.get("forecast"), 6), "outcome": _r(r.get("outcome"), 6),
                   "err_champion": r.get("err_champion"),
                   "intervals": {k: [_r(v[0], 6), _r(v[1], 6)] for k, v in iv.items()} if iv else None,
                   "baseline": None, "guidance": None}
            for k, v in (("baseline", base), ("guidance", guid)):
                if v and v != r.get("champion") and r.get(f"err_{v}") is not None:
                    row[k] = {"variant": v, "forecast": _r((f.get("variants") or {}).get(v), 6),
                              "err": _r(r.get(f"err_{v}"))}
            out.append(row)
    return out


def _regime_month(snap: dict | None, publishable) -> dict | None:
    from ai_tracker.site import probabilities as P

    r = (snap or {}).get("regime")
    if not isinstance(r, dict):
        return None
    blocks = []
    for name, b in P._blocks(r).items():
        if isinstance(b, dict):
            blocks.append({"block": name, "label": P.BLOCK_LABELS.get(name, name), "shift": b.get("shift"),
                           "p_slow": P._p_slow(b)})
    blocks.sort(key=lambda b: (b["block"] not in P.BLOCK_LABELS, list(P.BLOCK_LABELS).index(b["block"])
                               if b["block"] in P.BLOCK_LABELS else 0, b["block"]))
    breaks = [{"series": x.get("series"), "branch": x.get("branch"), "latest_period": x.get("latest_period"),
               "p_recent": x.get("p_recent")} for x in P._breaks(r)]
    return {"blocks": blocks, "breaks": breaks}


def docs(rec, nowcasts: list[dict], publishable: Callable[[str], bool], label: Callable[[str], str]) -> dict[str, dict]:
    """story/<YYYY-MM>.json for every month of the record's history and story/index.json."""
    from ai_tracker import catalog
    from ai_tracker.site_bundle.export import month_branches
    from ai_tracker.state import branch as BR
    from ai_tracker.state import snapshot as S

    months = sorted({h["month"] for hs in rec.history.values() for h in hs})
    kinds = {h["month"]: h["kind"] for hs in rec.history.values() for h in hs}
    outcomes = outcome_rows(nowcasts)
    branches = {m: month_branches(rec, m) or {} for m in months}

    recon: dict[str, list[dict]] = {}
    for m in months:
        if m in rec.live:
            recon[m] = ((rec.live[m].get("reconciliations") or {}).get("series")) or []
        else:
            recon[m] = S._clean(BR.reconciliations(S.month_end(m), rec.ctx)).get("series") or []

    history: dict[str, dict[str, dict]] = {}
    for m in months:
        for code in sorted(branches[m]):
            b = branches[m][code] or {}
            for lst in ("series_used", "series_not_counted"):
                for x in b.get(lst) or []:
                    k = x.get("series")
                    if k:
                        history.setdefault(k, {}).setdefault(m, x)
    recon_history: dict[str, dict[str, dict]] = {}
    for m in months:
        for x in recon[m]:
            if x.get("series"):
                recon_history.setdefault(x["series"], {})[m] = x

    out: dict[str, dict] = {}
    index = []
    for m in months:
        prev = str(pd.Period(m, "M") - 1)
        has_prev = prev in branches
        end = str(S.month_end(m).date())
        snap = rec.live.get(m)
        known = max(end, snap["date"]) if snap else end
        inp = {"month": m, "kind": kinds[m], "known": known, "branches": branches[m],
               "branch_names": dict(catalog.BRANCHES), "previous": prev if has_prev else None,
               "prev_branches": branches[prev] if has_prev else None, "recon": recon[m],
               "prev_recon": recon[prev] if has_prev else None, "outcomes": outcomes,
               "regime": _regime_month(snap, publishable), "history": history, "recon_history": recon_history}
        doc = select(inp, publishable, label)
        out[f"story/{m}.json"] = doc
        index.append({"month": m, "month_sv": doc["month_sv"], "kind": doc["kind"], "known": known,
                      "n_events": doc["n_events"], "types": doc["types"], "headline": doc["headline"]})
    out["story/index.json"] = {"rule": rule(), "latest": months[-1] if months else None, "months": index}
    return out
