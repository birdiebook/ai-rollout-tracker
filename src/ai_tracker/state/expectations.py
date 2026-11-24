"""F1: the snapshot section "expectations", group "Förväntningar mot utfall" (docs/mattregister.md, 2026-11-24 "F1:
revideringar av guidance och överraskning mot guidance").

Revision index (rolling 4 quarters is the main measure, the quarter beside it) and surprise against guidance per
company and as an index. Measured and shown, never counted in a branch's diffusion index (`in_diffusion` is always
False), no pace: level and percentile against the measure's own history as known on the computation date.

Everything is computed from inputs known on `when` only (observation rows and curated CSV rows with
known_from <= when), so the section equals the catalog series' as_of(when) (tests/test_guidance_revisions.py).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from ai_tracker.series import guidance_revisions as GR
from ai_tracker.state import register as R
from ai_tracker.state.measures import percentile

SECTION = "expectations"
RECENT_EVENTS = 12
NOTE = ("Förväntningar mot utfall (register F1): bolagens revideringar av sin egen guidance och utfallet mot den. "
        "Ingen takt, nivå och percentil mot egen historik. Räknas inte i grenarnas diffusionsindex.")


def _num(x):
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def _latest_per_period(versions: pd.DataFrame) -> pd.DataFrame:
    if versions is None or versions.empty:
        return versions
    v = versions.sort_values("known_from", kind="stable")
    return v.groupby("period", sort=True).tail(1).sort_values("period").reset_index(drop=True)


def _index_entry(versions: pd.DataFrame, value: str, freq: str) -> dict:
    """Latest period, latest period with a value, and its percentile against the history of latest values."""
    latest = _latest_per_period(versions)
    if latest is None or latest.empty:
        return {"latest": None, "latest_with_value": None}
    hist = latest[value].astype(float).to_numpy()
    finite = latest[np.isfinite(hist)]

    def row(r) -> dict:
        d = {k: (_num(r[k]) if k not in ("period", "known_from", "companies") else r[k]) for k in r.index}
        d.update({k: int(d[k]) for k in d if k.startswith("n") and d[k] is not None})  # counts
        d["known_from"] = str(pd.Timestamp(r["known_from"]).date())
        return d

    out = {"latest": row(latest.iloc[-1]), "latest_with_value": None}
    if len(finite):
        r = finite.iloc[-1]
        entry = row(r)
        entry["percentile"] = percentile(float(r[value]), finite[value].astype(float).to_numpy(), R.MIN_HISTORY[freq])
        entry["n_history"] = int(len(finite))
        out["latest_with_value"] = entry
    return out


def _events(ev: pd.DataFrame) -> tuple[list[dict], dict]:
    if ev is None or ev.empty:
        return [], {}
    e = ev.sort_values("known_from", kind="stable")
    recent = [{"company": r.company, "measure": r.measure, "period": r.period, "definition": r.definition,
               "chain": r.chain, "known_from": str(pd.Timestamp(r.known_from).date()), "direction": int(r.direction),
               "size": _num(r.size)} for r in e.tail(RECENT_EVENTS).itertuples(index=False)]
    years = pd.to_datetime(e["known_from"]).dt.year
    counts = {}
    for (c, y), g in e.groupby([e["company"], years]):
        counts.setdefault(c, {})[str(y)] = {"n": int(len(g)), "up": int((g["direction"] == 1).sum()),
                                            "unchanged": int((g["direction"] == 0).sum()),
                                            "down": int((g["direction"] == -1).sum())}
    return recent, counts


def _companies(s: pd.DataFrame) -> list[dict]:
    out = []
    if s is None or s.empty:
        return out
    for c, g in s.sort_values("outcome_known_from").groupby("company", sort=True):
        r = g.iloc[-1]
        freq = "A" if r["freq"] == "A" else "Q"
        out.append({"company": c, "measure": r["measure"], "period": r["period"],
                    "known_from": str(pd.Timestamp(r["outcome_known_from"]).date()),
                    "outcome": _num(r["outcome"]), "guidance": _num(r["guidance"]),
                    "guidance_known_from": str(pd.Timestamp(r["guidance_known_from"]).date()),
                    "surprise": _num(r["s"]), "z": _num(r["z"]), "n_past": int(r["n_past"]),
                    "surprise_percentile": percentile(float(r["s"]), g["s"].astype(float).to_numpy(),
                                                      R.MIN_HISTORY[freq]),
                    "mean_surprise": _num(g["s"].mean()), "n": int(len(g))})
    return out


def section(when, table: pd.DataFrame, csv: pd.DataFrame | None = None) -> dict:
    """The section as of `when` (pure apart from reading the curated CSV when `csv` is None)."""
    when = pd.Timestamp(when).normalize()
    t = table[table["series"].isin(GR.COMPONENTS)].copy() if table is not None else pd.DataFrame()
    if len(t):
        t["known_from"] = pd.to_datetime(t["known_from"])
        t = t[t["known_from"] <= when]
    csv = GR.load_csv() if csv is None else csv
    if csv is not None and len(csv):
        csv = csv[pd.to_datetime(csv["known_from"]) <= when]
    out = GR.compute(t, csv, when)
    recent, counts = _events(out["events"])
    return {
        "group": GR.GROUP,
        "in_diffusion": False,
        "note": NOTE,
        "rules": {"deadband_log100": GR.DEADBAND, "same_event_days": GR.SAME_EVENT_DAYS,
                  "min_events": GR.MIN_EVENTS, "main_window_quarters": GR.MAIN_WINDOW,
                  "coverage_from": str(GR.COVERAGE_FROM), "min_past_surprises": GR.MIN_PAST,
                  "min_companies": GR.MIN_COMPONENTS, "definition_breaks": sorted(GR.DEFINITION_BREAKS)},
        "revisions": {f"window_{w}q": _index_entry(out["index"][w], "index", "Q") for w in GR.WINDOWS},
        "events_recent": recent,
        "events_per_company_year": counts,
        "surprise": {"companies": _companies(out["surprises"]),
                     "index": _index_entry(out["surprise_index"], "value", "Q")},
    }


def safe_section(when, table: pd.DataFrame) -> dict:
    """`section`, with a failure recorded in the section instead of stopping the snapshot (descriptive group)."""
    try:
        return section(when, table)
    except Exception as e:  # noqa: BLE001 - the branch states are the record; this group is descriptive
        return {"group": GR.GROUP, "in_diffusion": False, "error": f"{type(e).__name__}: {e}"}
