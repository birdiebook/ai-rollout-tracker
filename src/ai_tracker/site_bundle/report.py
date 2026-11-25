"""W14: the quarterly report (kvartalsrapporten, ai_tracker.quarterly) as bundle documents.

    report/<YYYYQn>.json   one quarter: the chain L1-L9 over the quarter, the reconciliations, the live nowcasts
                           against their outcomes, the regime (C4), data and method, and generated sentences
    report/index.json      every quarter with its kind and the day it became known

Built on ai_tracker.quarterly: the facts are its *_facts functions (the same ones the Markdown report renders), fed
with the months of the site's record (site.data.Record: the live snapshots, or the reconstruction at each month
end, exactly what the stripes show). Nothing is recomputed here: states, indices, ratio measures, scores, intervals
and C4 values come from the record, the committed forecast files and the snapshots. This module only selects,
rounds and writes sentences.

Time travel: every value in a quarter's document was known on its `known` day (the last month's record: its month
end, or the live snapshot's date if later). The table is cut to the quarter's end (quarterly.make_inputs), and the
document carries no later day. The first live quarterly report is the first quarter whose three months all have a
live snapshot (2027Q1 with the first snapshot 2026-11-30); every earlier quarter is labelled reconstructed.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from ai_tracker import catalog
from ai_tracker import quarterly as Q
from ai_tracker.letter import BANNED_WORDS, month_sv
from ai_tracker.site import data as D
from ai_tracker.site.render import num
from ai_tracker.state import branch as BR
from ai_tracker.state import register as R
from ai_tracker.state import snapshot as S

LIVE_STATUS = {Q.LIVE: "live", Q.RECON: "reconstructed"}
STATE_ORDER = [R.STATE_ACCEL, R.STATE_STABLE, R.STATE_BRAKE, R.STATE_FEW]
ALARM_WORDS = re.compile(r"\b(larm\w*|varning\w*|kris\w*|rekord\w*|dramatisk\w*|kollaps\w*|ras|rasar|rasade|rusar|"
                         r"rusade|chock\w*|oroväckande|alarmerande)\b", re.IGNORECASE)


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


def _count(n: int) -> str:
    return {0: "ingen", 1: "en"}.get(n, _int(n))


def _many(n: int) -> str:
    """A count of a plural noun: "inga", "1", "2 410"."""
    return "inga" if n == 0 else _int(n)


def _plural(n: int, one: str, many: str) -> str:
    return f"{({0: 'inga', 1: 'ett'}.get(n, _int(n)))} {one if n == 1 else many}"


def _n_word(n: int, one: str, many: str) -> str:
    """"En avstämning", "3 avstämningar" (sentence start, common gender)."""
    return f"En {one}" if n == 1 else f"{_int(n)} {many}"


def _int(n: int) -> str:
    return num(n, 0)


def _plain(text: str) -> str:
    return re.sub(r"`", "", text)


def quarter_sv(q) -> str:
    return Q.quarter_sv(q)


def neutral(text: str) -> bool:
    return not BANNED_WORDS.search(text) and not ALARM_WORDS.search(text)


def texts(doc) -> list[str]:
    """Every generated sentence of a document (for the neutrality test)."""
    out = []
    if isinstance(doc, dict):
        for k, v in doc.items():
            if k in ("text", "headline", "recon_note") and isinstance(v, str):
                out.append(v)
            elif k == "sentences" and isinstance(v, list):
                out += [x for x in v if isinstance(x, str)]
            else:
                out += texts(v)
    elif isinstance(doc, list):
        for v in doc:
            out += texts(v)
    return out


# ------------------------------------------------------------------ the record's months


def first_live_quarter(rec: D.Record) -> str:
    """The first quarter whose three months can all have a live snapshot: the quarter of the first live month when
    that month opens its quarter, else the next quarter."""
    month = pd.Period(rec.first_live or pd.Timestamp(rec.first_live_date).to_period("M"), "M")
    q = month.asfreq("Q")
    return str(q if month == q.asfreq("M", "s") else q + 1)


def _month(rec: D.Record, month: str) -> Q.Month | None:
    """A month of the record as the quarterly report's input: the live snapshot, or the record's reconstruction at
    the month end (only before the first live snapshot: a later month without one is a gap, never reconstructed)."""
    date = S.month_end(month)
    if month in rec.live:
        doc = rec.live[month]
        return Q.Month(month, date, Q.LIVE, doc, doc.get("_file") or f"snapshots/{month}.json")
    if rec.first_live is not None and month >= rec.first_live:
        return None
    doc = {"branches": rec.compute(month), "reconciliations": S._clean(BR.reconciliations(date, rec.ctx))}
    return Q.Month(month, date, Q.RECON, doc, None)


def known_day(m: Q.Month) -> str:
    end = str(m.date.date())
    return max(end, str(m.doc.get("date") or end)) if m.kind == Q.LIVE else end


def quarters(rec: D.Record) -> list[str]:
    """Complete quarters of the record's history (all three months in it)."""
    months = sorted({h["month"] for hs in rec.history.values() for h in hs})
    have = set(months)
    out = []
    for q in sorted({str(pd.Period(m, "M").asfreq("Q")) for m in months}):
        p = pd.Period(q, "Q")
        three = [str(m) for m in pd.period_range(p.asfreq("M", "s"), p.asfreq("M", "e"), freq="M")]
        if all(m in have for m in three):
            out.append(q)
    return out


# ------------------------------------------------------------------ sections


def _mref(m: Q.Month | None) -> dict | None:
    if m is None:
        return None
    return {"month": m.month, "month_sv": month_sv(m.month), "kind": m.kind, "known": known_day(m),
            "file": m.file if m.kind == Q.LIVE else None}


def _cell(m: Q.Month, b: dict) -> dict:
    return {"month": m.month, "kind": m.kind, "index": _r(b.get("index")), "state": b.get("state") or R.STATE_FEW,
            "n_series": b.get("n_series"), "n_up": b.get("n_up"), "n_neutral": b.get("n_neutral"),
            "n_down": b.get("n_down")}


def summary_section(inp: Q.Inputs) -> tuple[dict, list[dict]]:
    f = Q.summary_facts(inp)
    path = f["path"]
    last = inp.months[-1]
    base_sv = month_sv(inp.base.month) if inp.base else None
    counts = {s: 0 for s in STATE_ORDER}
    for st, codes in f["groups"]:
        counts[st if st in counts else R.STATE_FEW] = counts.get(st if st in counts else R.STATE_FEW, 0) + len(codes)
    with_state = counts[R.STATE_ACCEL] + counts[R.STATE_STABLE] + counts[R.STATE_BRAKE]
    stable = f"{_count(counts[R.STATE_STABLE])} {'är stabil' if counts[R.STATE_STABLE] == 1 else 'är stabila'}"
    head = (f"Vid kvartalets slut ({month_sv(last.month)}) accelererar "
            f"{'ingen' if not counts[R.STATE_ACCEL] else _int(counts[R.STATE_ACCEL])} av {with_state} "
            f"grenar med tillstånd, {stable} och {_count(counts[R.STATE_BRAKE])} bromsar in.")
    if counts[R.STATE_FEW]:
        head += f" {counts[R.STATE_FEW]} {'gren har' if counts[R.STATE_FEW] == 1 else 'grenar har'} för få serier."
    sentences = []
    if inp.base is None:
        sentences.append("Ingen månad före kvartalet att jämföra med.")
    elif f["changed"]:
        sentences.append(f"Tillståndet vid kvartalets slut skilde sig från {base_sv} i {len(f['changed'])} av "
                         f"{len(catalog.BRANCHES)} grenar: "
                         + "; ".join(f"{c['code']} {c['name']} från {c['from']} till {c['to']}" for c in f["changed"])
                         + ".")
    else:
        sentences.append(f"Inget tillstånd vid kvartalets slut skilde sig från {base_sv}.")
    if f["seqs"]:
        sentences.append("Bytte tillstånd mer än en gång under kvartalet: " + "; ".join(
            f"{x['code']} " + " → ".join(s for _, s in x["steps"]) for x in f["seqs"]) + ".")
    if f["moved"]:
        sentences.append("Störst indexförändring över kvartalet: "
                         + ", ".join(f"{c} {num(d, 2, signed=True)}" for c, d in f["moved"]) + ".")
    elif inp.base is not None:
        sentences.append("Inget index ändrades över kvartalet (avrundat till två decimaler).")
    branches = []
    for r in f["rows"]:
        branches.append({"code": r["code"], "name": r["name"],
                         "path": [_cell(m, c) for m, c in zip(path, r["cells"])],
                         "delta_index": _r(r["delta"]), "from": r["from"], "to": r["to"],
                         "state_changed": r["state_changed"] if r["has_base"] else None, "flips": r["flips"]})
    summary = {"headline": head, "sentences": sentences, "counts": counts, "n_with_state": with_state,
               "changed": [{"code": c["code"], "name": c["name"], "from": c["from"], "to": c["to"]}
                           for c in f["changed"]],
               "repeated": [{"code": x["code"], "steps": [{"month": m, "state": s or R.STATE_FEW} for m, s in x["steps"]]}
                            for x in f["seqs"]],
               "moved": [{"code": c, "delta_index": _r(d)} for c, d in f["moved"]],
               "groups": [{"state": st, "codes": list(codes)} for st, codes in f["groups"]]}
    return summary, branches


def _ratio(r: dict) -> dict:
    m = r["m"]
    pace, chg = m.get("pace"), m.get("change_in_pace")
    text = f"{r['label']}: nivå {num(m.get('level'), 3)} ({m.get('latest_period') or '–'})"
    if pace is not None:
        text += f", takt {num(pace, 1, signed=True)} log×100 per år"
    if chg is not None:
        text += f", förändring i takt {num(chg, 1, signed=True)}"
    if m.get("pace_percentile") is not None:
        text += f", takten på percentil {num(m.get('pace_percentile'), 0)} i sin egen historik"
    text += "."
    if r["base_level"] is not None:
        text += f" Före kvartalet: {num(r['base_level'], 3)} ({r['base_period'] or '–'})."
    return {"key": r["key"], "label": r["label"], "leads": r["leads"], "latest_period": m.get("latest_period"),
            "known_from": m.get("known_from"), "level": _r(m.get("level")), "pace": _r(pace),
            "pace_unit": m.get("pace_unit"), "change_in_pace": _r(chg), "pace_percentile": _r(m.get("pace_percentile")),
            "change_percentile": _r(m.get("change_percentile")), "n_pace": m.get("n_pace"),
            "direction": m.get("direction"),
            "valid": m.get("valid"), "base_level": _r(r["base_level"]), "base_period": r["base_period"], "text": text}


def chain_section(inp: Q.Inputs) -> tuple[list[dict], list[dict], int]:
    leads, ratios = [], {}
    for f in Q.flow_facts(inp):
        for r in f["ratios"]:
            ratios.setdefault(r["key"], _ratio(r))
        bs = f["branches"]
        # the branches' states are drawn next to the text; the sentence names only state changes and the ratios
        moved = [f"{b['code']} {' → '.join(b['state'])}" for b in bs if len(set(b["state"])) > 1]
        if not bs:
            text = "Ledet har ingen egen gren."
        elif moved:
            text = "Tillstånd vid varje månadsslut: " + "; ".join(moved) + "."
        else:
            text = ("Samma tillstånd vid varje månadsslut." if len(bs) == 1 else
                    "Grenarna hade samma tillstånd vid varje månadsslut.")
        n_r = len(f["ratios"])
        if not f["keys"]:
            text += " Inga registrerade avstämningar för ledet."
        elif n_r:
            text += f" {_n_word(n_r, 'avstämning', 'avstämningar')} med data vid kvartalets slut."
        else:
            text += " Ledets registrerade avstämningar har inga data som får visas vid kvartalets slut."
        if f["withheld"]:
            text += f" {_n_word(f['withheld'], 'avstämning', 'avstämningar')} visas inte av licensskäl."
        leads.append({"lead": f["lead"], "name": f["name"], "branches": [b["code"] for b in bs],
                      "ratios": [r["key"] for r in f["ratios"]], "n_ratios_withheld": f["withheld"], "text": text})
    n_withheld = sum(1 for k in _registered(inp) if not Q.publishable(k, inp))
    return leads, list(ratios.values()), n_withheld


def _registered(inp: Q.Inputs) -> set[str]:
    return {m["series"] for m in (inp.months[-1].doc.get("reconciliations") or {}).get("series", [])}


def _iv(x) -> list | None:
    if isinstance(x, (list, tuple)) and len(x) == 2 and all(v is not None for v in x):
        return [_r(x[0], 6), _r(x[1], 6)]
    return None


def nowcast_section(inp: Q.Inputs) -> tuple[list[dict], dict]:
    f = Q.forecast_facts(inp)
    out = []
    for x in f["nowcasts"]:
        info = D.NOWCAST_INFO.get(x["sub"], {})
        spec = inp.ctx.specs.get(x["target"])
        show, files, variants = x["show"], x["files"], x["variants"]
        new = []
        for origin, d, p in x["new"]:
            new.append({"period": d.get("quarter") or d.get("month") or d.get("period"), "origin": str(origin.date()),
                        "file": p, "champion": d.get("champion"), "value": _r(d.get("value"), 6) if show else None,
                        "variants": {v: _r((d.get("variants") or {}).get(v), 6) for v in variants} if show else None})
        outcomes = []
        if x["fresh"] is not None and show:
            files_by_origin = {str(o.date()): p for o, _d, p in files}
            for r in x["fresh"].to_dict("records"):
                file = files_by_origin.get(r.get("origin"))
                slug = (file or "").rsplit("/", 1)[-1].removesuffix(".json") or None
                ivs = {k: _iv(r.get(f"interval_{k}")) for k in ("50", "80", "95")}
                outcomes.append({"period": r["period"], "origin": r.get("origin"), "file": file,
                                 "slug": re.sub(r"[^A-Za-z0-9_.-]", "_", slug) if slug else None,
                                 "champion": r.get("champion"), "forecast": _r(r.get("forecast"), 6),
                                 "outcome": _r(r.get("outcome"), 6), "known_from": r.get("known_from"),
                                 "err_champion": _r(r.get("err_champion")),
                                 "errors": {v: _r(r.get(f"err_{v}")) for v in variants if r.get(f"err_{v}") is not None},
                                 "intervals": ivs if all(ivs.values()) else None})
        n_fresh = 0 if x["fresh"] is None else len(x["fresh"])
        n_scored = 0 if x["scored"] is None else len(x["scored"])
        metrics = [{"variant": m["variant"], "role": m["role"], "n": m["n"], "mae": _r(m["mae"]), "bias": _r(m["bias"]),
                    "delta_mae": _r(m["delta_mae"]),
                    "coverage": {k: ({"rate": _r(c["rate"]), "lo": _r(c["lo"]), "hi": _r(c["hi"]), "n": c["n"]}
                                     if c else None) for k, c in m["coverage"].items()}}
                   for m in x["metrics"]]
        champion = files[-1][1].get("champion") if files else None
        if not files:
            text = f"Inga skarpa prognoser med prognosdag till och med {day_sv(inp.end)}."
        else:
            text = (f"{_plural(len(files), 'skarp prognos', 'skarpa prognoser').capitalize()} med prognosdag till och med "
                    f"{day_sv(inp.end)}, varav {_count(len(new))} i kvartalet. Huvudmodell i den senaste: {champion}.")
            if f["error"]:
                text += " Scorecarden kunde inte beräknas."
            elif x["scored"] is not None:
                text += (f" {_plural(n_fresh, 'utfall', 'utfall').capitalize()} blev kända i kvartalet, och "
                         f"{_count(n_scored)} av {x['n_files_scored']} prognoser har utfall hittills.")
                if n_scored:
                    text += " Med så få utfall kan skillnaderna mellan varianterna och mot baslinjen vara slump."
        if x["changes"]:
            text += " Byte av huvudmodell i prognosfilerna: " + "; ".join(
                f"{c['from']} till {c['to']} från prognosdag {day_sv(c['origin'])}" for c in x["changes"]) + "."
        out.append({"id": x["sub"], "label": x["label"], "title": x["title"], "publishable": show,
                    "target": x["target"] if show else None, "unit": (spec.unit if spec else info.get("unit", "")) if show else None,
                    "decimals": info.get("decimals", 0), "error_unit": Q._err_unit(x["sub"]),
                    "origin_rule": x["origin_rule"], "champion": champion, "n_files": len(files), "new": new,
                    "outcomes": outcomes, "n_outcomes": n_fresh, "n_scored": n_scored,
                    "n_files_scored": x["n_files_scored"], "metrics": metrics if show else [],
                    "changes": x["changes"],
                    "decisions": [_plain(d) for d in x["decisions"]], "text": text})
    news = (f"{_plural(f['n_new'], 'ny skarp prognos', 'nya skarpa prognoser').capitalize()} och "
            f"{_plural(f['n_out'], 'nytt utfall', 'nya utfall')} i kvartalet.")
    return out, {"n_new": f["n_new"], "n_outcomes": f["n_out"], "n_d2": f["n_d2"], "error": f["error"], "text": news}


def regime_section(inp: Q.Inputs) -> dict:
    f = Q.regime_facts(inp)
    if not f["available"]:
        text = ("Kvartalets månadslägen har inget regimavsnitt (C4). Det lagras bara i skarpa ögonblicksbilder, så "
                "ingen sannolikhet för inbromsning och inget strukturbrott redovisas för kvartalet.")
    else:
        shifts = f["shifts"]
        text = ("Rapporterade regimskiften i kvartalet: "
                + ("; ".join(f"{s['label']}: {s['shift']} från {month_sv(s['month'])}" for s in shifts) if shifts else "inga")
                + f". Rapporterade strukturbrott: {_count(f['n_breaks'])}"
                + (f", varav {_count(f['n_hidden'])} i serier som inte visas av licensskäl" if f["n_hidden"] else "")
                + ".")
        if f["missing"]:
            text += " Utan regimavsnitt: " + ", ".join(month_sv(m) for m in f["missing"]) + "."
    blocks = None
    if f["blocks"] is not None:
        blocks = [{"block": b["block"], "label": b["label"],
                   "cells": [{"month": c["month"], "present": c["present"], "p_slow": _r(c.get("p_slow")),
                              "state": c.get("state"), "shift": c.get("shift"), "reason": c.get("reason")}
                             for c in b["cells"]]} for b in f["blocks"]]
    breaks = None
    if f["breaks"] is not None:
        breaks = [{**b, "p_recent": _r(b["p_recent"])} for b in f["breaks"]]
    return {"available": f["available"], "months": f["months"], "blocks": blocks, "shifts": f["shifts"],
            "breaks": breaks, "n_breaks": f["n_breaks"], "n_breaks_withheld": f["n_hidden"], "missing": f["missing"],
            "text": text}


def data_section(inp: Q.Inputs) -> dict:
    f = Q.data_facts(inp)
    lab = lambda k: Q.name(k, inp)
    s = []
    if f["added"] is not None:
        s.append(f"Nya kärnserier i tillståndet sedan {month_sv(inp.base.month)}: "
                 + (", ".join(lab(k) for k in f["added"]) if f["added"] else "inga") + ".")
        if f["gone"]:
            s.append("Kärnserier som inte längre ingår: " + ", ".join(lab(k) for k in f["gone"]) + ".")
    if f["new_series"] is not None:
        s.append("Nya serier med första hämtning i kvartalet: "
                 + (", ".join(lab(k) for k in f["new_series"]) if f["new_series"] else "inga") + ".")
    else:
        s.append("Nya serier redovisas inte för ett rekonstruerat kvartal: hämtdatum i dagens tabell säger inget om "
                 "kvartalet.")
    s.append(f"{_plural(f['n_revised'], 'redan publicerat värde', 'redan publicerade värden').capitalize()} fick en ny "
             f"version i kvartalet, varav {_count(f['n_notable'])} i "
             f"{_plural(f['n_revised_series'], 'serie', 'serier')} med minst {num(Q.L.REVISION_MIN_PCT, 0)} % "
             f"(andelar: {num(Q.L.REVISION_MIN_PP, 1)} procentenheter).")
    s.append(f"Nya eller ändrade guidancevärden från bolagen: {_many(f['n_guidance'])}. Inaktuella serier vid "
             f"kvartalets slut: {_many(f['n_stale'])}. Serier utan data kända då: {_many(f['n_missing'])}.")
    if f["withheld"]:
        s.append(f"Serier som inte visas av licensskäl ingår i antalen men namnges inte ({f['withheld']}).")
    return {"added": [{"key": k, "label": lab(k)} for k in f["added"]] if f["added"] is not None else None,
            "gone": [{"key": k, "label": lab(k)} for k in f["gone"]] if f["gone"] is not None else None,
            "new_series": [{"key": k, "label": lab(k)} for k in f["new_series"]] if f["new_series"] is not None else None,
            "n_revised": f["n_revised"], "n_notable": f["n_notable"], "n_revised_series": f["n_revised_series"],
            "revised": [{"key": k, "label": lab(k), "n": c} for k, c in f["revised"][:Q.REVISION_ROWS]],
            "n_guidance": f["n_guidance"], "n_stale": f["n_stale"],
            "stale": [{"key": x.key, "label": x.label, "branch": x.branch} for x in f["stale"]],
            "n_missing": f["n_missing"],
            "reviews": [{"date": d, "title": t, "file": p} for d, t, p in f["reviews"]],
            "register": [{"date": str(d.date()), "title": t} for d, t in f["register"]],
            "n_withheld": f["withheld"], "sentences": s}


def day_sv(day) -> str:
    t = pd.Timestamp(day)
    return f"{t.day} {Q.L.MONTHS_SV[t.month - 1]} {t.year}"


def withheld_list(inp: Q.Inputs) -> list[dict]:
    """The withheld series the quarter's last month counted or measured, as name-only entries."""
    out, seen = [], set()
    for code in catalog.BRANCHES:
        b = Q.bstate(inp.months[-1], code)
        for lst, counted in (("series_used", True), ("series_not_counted", False)):
            for m in b.get(lst) or []:
                k = m.get("series")
                if k and k not in seen and not Q.publishable(k, inp):
                    seen.add(k)
                    out.append({**D.withheld_entry(k, inp.ctx, counted=counted), "branch": code})
    return out


# ------------------------------------------------------------------ documents


def report_doc(inp: Q.Inputs) -> dict:
    q = str(inp.quarter)
    kind = inp.kind
    summary, branches = summary_section(inp)
    leads, ratios, n_ratios_withheld = chain_section(inp)
    nowcasts, nowcast_news = nowcast_section(inp)
    regime = regime_section(inp)
    data = data_section(inp)
    title = f"Läget i AI-utrullningen, {quarter_sv(q)}" + (" (rekonstruerad)" if kind == Q.RECON else "")
    recon = [m.month for m in inp.months if m.kind == Q.RECON]
    note = None
    if recon:
        note = ("Rekonstruerad, inte en skarp rapport. Det fanns ingen skarp ögonblicksbild för "
                + ", ".join(month_sv(m) for m in recon) + ". De månaderna är beräknade i efterhand vid varje "
                "månadsslut med samma kod och bara data som var känd då, men med dagens versioner av serier som "
                "saknar sparade versioner, så revideringar kan läcka in.")
    known = max(known_day(m) for m in inp.months)
    return {
        "quarter": q, "quarter_sv": quarter_sv(q), "title": title, "kind": kind, "status": LIVE_STATUS[kind],
        "start": str(inp.start.date()), "end": str(inp.end.date()), "known": known,
        "months": [_mref(m) for m in inp.months], "base": _mref(inp.base), "recon_note": note,
        "headline": summary["headline"], "summary": summary, "branches": branches, "chain": leads,
        "ratios": ratios, "n_ratios_withheld": n_ratios_withheld, "nowcasts": nowcasts, "nowcast_news": nowcast_news,
        "regime": regime, "data": data, "withheld": withheld_list(inp),
        "source": {"module": "ai_tracker.quarterly", "markdown": f"docs/kvartalsrapport/{q}.md"},
    }


def docs(rec: D.Record, forecasts_dir: Path, docs_dir: Path,
         log: Callable[[str], None] | None = None) -> dict[str, dict]:
    """report/<YYYYQn>.json for every complete quarter of the record's history and report/index.json."""
    out: dict[str, dict] = {}
    index = []
    regime = sorted((m, s["regime"]) for m, s in rec.live.items() if isinstance(s.get("regime"), dict))
    for q in quarters(rec):
        p = pd.Period(q, "Q")
        months = [_month(rec, str(m)) for m in pd.period_range(p.asfreq("M", "s"), p.asfreq("M", "e"), freq="M")]
        if any(m is None for m in months):
            continue  # a gap month after the first live snapshot: no report (quarterly refuses it too)
        base = _month(rec, str(p.asfreq("M", "s") - 1))
        inp = Q.make_inputs(q, months, base, rec.ctx, forecasts_dir, docs_dir, regime)
        doc = report_doc(inp)
        out[f"report/{q}.json"] = doc
        index.append({"quarter": q, "quarter_sv": doc["quarter_sv"], "title": doc["title"], "kind": doc["kind"],
                      "status": doc["status"], "known": doc["known"], "headline": doc["headline"]})
        if log:
            log(q)
    out["report/index.json"] = {"latest": index[-1]["quarter"] if index else None,
                                "first_live": first_live_quarter(rec), "quarters": index}
    return out
