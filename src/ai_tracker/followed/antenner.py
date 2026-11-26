"""Antenner: one row per followed question (register 2026-11-26 "F0", (c)).

Per question: the question, its latest reading (the question's main reading), what changed against last month (the
as-of day minus one calendar month: the reading, its quarter t and the facts the question lists) and the next unseen
reading. A description: no alarm levels, the questions are not weighed together.

A question takes part through `antenna(report) -> dict` (common.antenna_row); a question without it gets a row that
says so. Each question is computed twice, on the day and a month earlier, from rows known on each day.
"""

from __future__ import annotations

import inspect
from datetime import date

import pandas as pd

from ai_tracker import observations

QUESTION = "Vad säger de följda frågorna nu, och vad har ändrats sedan förra månaden?"
NAME = "antenner"


def previous(as_of) -> str:
    """The comparison day: the as-of day minus one calendar month."""
    return str((pd.Timestamp(as_of) - pd.DateOffset(months=1)).date())


def _compute(mod, as_of, table):
    if table is not None and "table" in inspect.signature(mod.compute).parameters:
        return mod.compute(as_of, table=table)
    return mod.compute(as_of)


def changes(prev: dict | None, cur: dict) -> list[str]:
    """What differs between two antenna rows: the reading, its quarter and each fact (in the current row's order)."""
    if prev is None:
        return ["ingen rad förra månaden"]
    out = []
    if prev.get("outcome") != cur.get("outcome") or prev.get("reading") != cur.get("reading"):
        out.append(f"utslag: {prev.get('reading') or '–'} → {cur.get('reading') or '–'}")
    if prev.get("t") != cur.get("t"):
        out.append(f"kvartal: {prev.get('t') or '–'} → {cur.get('t') or '–'}")
    pf, cf = prev.get("facts") or {}, cur.get("facts") or {}
    for k in list(cf) + [k for k in pf if k not in cf]:
        if pf.get(k) != cf.get(k):
            out.append(f"{k}: {pf.get(k, '–')} → {cf.get(k, '–')}")
    return out


def compute(as_of, table: pd.DataFrame | None = None, modules: dict | None = None) -> dict:
    from ai_tracker.followed import questions

    when = str(pd.Timestamp(as_of).date())
    prev_day = previous(when)
    mods = {k: m for k, m in (questions() if modules is None else modules).items() if k != NAME}
    if table is None and any("table" in inspect.signature(m.compute).parameters for m in mods.values()):
        table = observations.load()
    rows = []
    for name, mod in mods.items():
        row = {"key": name, "question": getattr(mod, "QUESTION", name), "has_antenna": hasattr(mod, "antenna")}
        try:
            if row["has_antenna"]:
                cur = mod.antenna(_compute(mod, when, table))
                prev = mod.antenna(_compute(mod, prev_day, table))
                row.update(cur, key=name, current=cur, previous=prev, changes=changes(prev, cur))
        except Exception as e:  # one question's failure is shown, not hidden, and does not stop the others
            row["error"] = f"{type(e).__name__}: {e}"
        rows.append(row)
    return {"question": QUESTION, "as_of": when, "previous": prev_day, "generated": str(date.today()), "rows": rows}


def _cell(s) -> str:
    return str(s if s not in (None, "") else "–").replace("|", "\\|").replace("\n", " ")


def render(r: dict) -> str:
    out = [f"# Antenner per {r['as_of']}", "",
           f"En rad per följd fråga: senaste utslaget (frågans huvudläsning), vad som ändrats mot {r['previous']} och "
           "nästa osedda läsning. Bara data kända på respektive dag. En beskrivning: inga larmnivåer, och frågorna vägs "
           "inte ihop. Registret: `docs/mattregister.md`, 2026-11-26 F0, avsnitt (c).", "",
           f"| Fråga | Senaste utslag | Ändrat mot {r['previous']} | Nästa osedda läsning |", "|---|---|---|---|"]
    for x in r["rows"]:
        q = f"**{x['key']}**: {x['question']}"
        if x.get("error"):
            out.append(f"| {_cell(q)} | fel vid beräkningen: {_cell(x['error'])} | – | – |")
        elif not x["has_antenna"]:
            out.append(f"| {_cell(q)} | ingen antenn (modulen har ingen `antenna`) | – | – |")
        else:
            reading = f"{x['reading']} ({x['t'] or '–'})"
            ch = "; ".join(x["changes"]) or "inget ändrat"
            out.append(f"| {_cell(q)} | {_cell(reading)} | {_cell(ch)} | {_cell(x['next_unseen'])} |")
    for x in r["rows"]:
        if x.get("facts"):
            out += ["", f"## {x['key']}", ""] + [f"- {k}: {v}" for k, v in x["facts"].items()]
    return "\n".join(out) + "\n"
