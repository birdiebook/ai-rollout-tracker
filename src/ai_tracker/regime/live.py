"""C4 in the monthly snapshot: P(slowdown) per factor block and the BOCPD break flags, as a separate section.

Specification: docs/steg2/c4_spec.md section 1 ("Skarpt: från den första ögonblicksbilden efter att holdouten har
öppnats. Det skarpa värdet lagras i ögonblicksbilden och räknas aldrig om"). The section is not part of the branch
states: a regime probability or a break never changes a diffusion index or a branch state (F-D5, F-D8). C4 is
descriptive and is never promoted (F-D6).

The reporting rules (F-D2 shifts, F-D4 breaks) need the earlier stored values. Each section stores what the next
month needs (per block the value and the reported state, and per series the latest period of the last reported
break). The chain starts from the previous snapshot's section; the first live snapshot (2026-11-30) has no previous
section and starts from the reconstructed sequence 2012-01-31 to the previous month end (the same computation as the
holdout run, labelled as reconstructed, not a live record).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ai_tracker.regime import bocpd, guard
from ai_tracker.regime import realtime as rt

SECTION = "regime"  # schema shared with site/probabilities.py and quarterly.py (_regime_frames)
SPEC_LOCK = "735dc64"  # commit of docs/steg2/c4_spec.md
FIRST_LIVE = pd.Timestamp("2026-11-30")  # the first snapshot after the holdout was opened (docs/holdout_logg.md)
NOTE = ("C4, beskrivande (F-D6). Påverkar inte grenarnas tillstånd eller diffusionsindex (F-D5, F-D8). "
        "Inbromsning = regimen med lägre faktortakt, inte nödvändigtvis fallande takt (c4_spec avsnitt 7).")
MS_FIELDS = ("mu_slow", "mu_exp", "sd_slow", "sd_exp", "p_stay_slow", "p_stay_exp", "loglik", "n_iter", "converged",
             "first_month", "n_series")


def _f(x):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else x


def next_state(prev_state: str | None, prev_p: float | None, p: float, consecutive: bool) -> str | None:
    """F-D2 for one step (same rule as realtime.state_sequence): expansion from the first value; a shift needs two
    consecutive month values both >= 0.8 (<= 0.2 back); a missing value keeps the state and breaks the pair."""
    if p is None or not np.isfinite(p):
        return prev_state
    state = prev_state or rt.EXPANSION
    pair = consecutive and prev_p is not None and np.isfinite(prev_p)
    if pair and p >= rt.HIGH and prev_p >= rt.HIGH:
        return rt.SLOWDOWN
    if pair and p <= rt.LOW and prev_p <= rt.LOW:
        return rt.EXPANSION
    return state


def is_break(row: dict, memory: dict) -> bool:
    """F-D4 for one series on one date, given the latest period of its last reported break (memory)."""
    p = row.get("p_recent")
    if p is None or not np.isfinite(p) or p < bocpd.THRESHOLD or row.get("latest_period") is None:
        return False
    last = memory.get(row["series"])
    o = rt._ordinal(row["latest_period"], row["freq"])
    return not (last is not None and o - rt._ordinal(last["period"], last["freq"]) <= bocpd.QUIET)


def seed(table: pd.DataFrame, date) -> dict:
    """The carried values for `date` from the reconstructed sequence up to the previous month end (first snapshot)."""
    prev_end = (pd.Timestamp(date).to_period("M") - 1).end_time.normalize()
    ms_f, b_f = rt.run(table, rt.DEV_START, prev_end)
    states = rt.reported_states(ms_f)
    breaks = rt.reported_breaks(b_f)
    last = states[states["date"] == prev_end]
    blocks = {r["block"]: {"p_slow": _f(float(r["p_slow"])), "state": r["state"]} for _, r in last.iterrows()}
    memory = {}
    for _, r in breaks[breaks["break"]].sort_values("date").iterrows():
        memory[r["series"]] = {"period": r["latest_period"], "freq": r["freq"]}
    return {"date": str(prev_end.date()), "blocks": blocks, "break_memory": memory,
            "chain": f"rekonstruerad följd {rt.DEV_START.date()}–{prev_end.date()} (som holdoutkörningen, inte skarp)"}


def carried(previous: dict) -> dict:
    """The carried values from the previous snapshot's section."""
    return {"date": previous["date"], "chain": f"föregående ögonblicksbild {previous['date']}",
            "blocks": {b: {"p_slow": v.get("p_slow"), "state": v.get("state")}
                       for b, v in previous.get("ms", {}).items()},
            "break_memory": dict(previous.get("break_memory", {}))}


def section(table: pd.DataFrame, date, previous: dict | None = None, seed_fn=None) -> dict:
    """The C4 section for the snapshot on `date` (a month end). `previous` = the previous snapshot's section, if any."""
    date = guard.check(date, "C4 snapshot")
    rec = rt.compute(table, date)
    prev = carried(previous) if previous else (seed_fn or seed)(table, date)
    prev_date = pd.Timestamp(prev["date"])
    consecutive = (date.to_period("M") - prev_date.to_period("M")).n == 1
    blocks = {}
    for block in rt.BLOCKS:
        r = rec["ms"][block]
        pb = prev["blocks"].get(block, {})
        p = r.get("p_slow", float("nan"))
        st = next_state(pb.get("state"), pb.get("p_slow") if consecutive else None, p, consecutive)
        blocks[block] = {**{k: _f(r.get(k)) for k in MS_FIELDS}, "p_slow": _f(p), "state": st,
                         "shift": bool(pb.get("state") is not None and st != pb.get("state")),
                         "n_months": int(r.get("n_months") or 0), "reason": r.get("reason") or "",
                         "previous_p": pb.get("p_slow"), "previous_state": pb.get("state")}
    memory = dict(prev["break_memory"])
    series = []
    for row in rec["bocpd"]:
        b = is_break(row, memory)
        if b:
            memory[row["series"]] = {"period": row["latest_period"], "freq": row["freq"]}
        series.append({**{k: _f(row.get(k)) for k in ("branch", "series", "freq", "latest_period", "p_recent",
                                                       "n_periods", "reason")}, "break": bool(b)})
    return {"spec_version": SPEC_LOCK, "code_version": rt.SPEC_VERSION, "model": "C4", "spec": "docs/steg2/c4_spec.md",
            "note": NOTE, "date": str(date.date()), "chain": prev["chain"], "ms": blocks, "bocpd": series,
            "break_memory": memory}
