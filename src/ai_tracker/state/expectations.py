"""F1: the snapshot section "expectations", group "Förväntningar mot utfall" (docs/mattregister.md, 2026-11-24 "F1:
revideringar av guidance och överraskning mot guidance").

Revision index (rolling 4 quarters is the main measure, the quarter beside it) and surprise against guidance per
company and as an index. Measured and shown, never counted in a branch's diffusion index (`in_diffusion` is always
False), no pace: level and percentile against the measure's own history as known on the computation date.

Everything is computed from inputs known on `when` only (observation rows and curated CSV rows with
known_from <= when), so the section equals the catalog series' as_of(when) (tests/test_guidance_revisions.py), except
for a closing version dated `when` itself: the register emits it once the quarter's last day has passed, so it is
created the following day and is not in a section computed on that day (R11-2).

Beside the main measures (rättning efter R11): the statements a registered definition break keeps out of the
comparison, with their size against the last statement before the break (R11-1); the revision index over numeric
events only and the composition of the main window by numbers and directions (R11-6); and TSMC's surprise in US$
with the FX part (R11-7). These are sensitivities, not main measures.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Callable

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


def _breaks(b: pd.DataFrame) -> list[dict]:
    if b is None or b.empty:
        return []
    return [{"ref": r.ref, "company": r.company, "measure": r.measure, "period": r.period, "chain": r.chain,
             "known_from": str(pd.Timestamp(r.known_from).date()), "value": _num(r.value), "prev_ref": r.prev_ref,
             "prev_known_from": None if r.prev_known_from is None else str(pd.Timestamp(r.prev_known_from).date()),
             "prev_value": _num(r.prev_value), "size": _num(r.size), "reason": r.reason}
            for r in b.itertuples(index=False)]


def _composition(ev: pd.DataFrame, versions: pd.DataFrame, window: int) -> dict:
    """Counts of the latest window by event type (numbers: chains num and min; directions)."""
    latest = _latest_per_period(versions)
    if ev is None or ev.empty or latest is None or latest.empty:
        return {}
    r = latest.iloc[-1]
    q = pd.Period(r["period"], "Q-DEC")
    e = ev.copy()
    kq = pd.to_datetime(e["known_from"]).dt.to_period("Q-DEC")
    e = e[(kq >= q - (window - 1)) & (kq <= q) & (pd.to_datetime(e["known_from"]) <= pd.Timestamp(r["known_from"]))]
    num = e["chain"].isin(GR.NUMERIC_CHAINS)
    out = {"period": r["period"]}
    for name, part in (("numbers", e[num]), ("directions", e[~num])):
        out[name] = {"n": int(len(part)), "up": int((part["direction"] == 1).sum()),
                     "unchanged": int((part["direction"] == 0).sum()), "down": int((part["direction"] == -1).sum())}
    return out


def _tsmc_usd(u: pd.DataFrame) -> dict:
    if u is None or u.empty:
        return {"latest": None}
    r = u.sort_values("outcome_known_from").iloc[-1]
    v = u.dropna(subset=["s_ntd"])
    return {"latest": {"period": r["period"], "known_from": str(pd.Timestamp(r["outcome_known_from"]).date()),
                       "outcome_musd": _num(r["outcome"]), "guidance_musd": _num(r["guidance"]),
                       "surprise_usd": _num(r["s"]), "surprise_ntd": _num(r["s_ntd"]), "fx_part": _num(r["fx"])},
            "n": int(len(v)), "sd_surprise_ntd": _num(v["s_ntd"].std()) if len(v) > 1 else None,
            "sd_surprise_usd": _num(v["s"].std()) if len(v) > 1 else None,
            "sd_fx_part": _num(v["fx"].std()) if len(v) > 1 else None,
            "note": "Känslighet (R11-7): utfall och guidance i US$; fx_part = s(NT$) − s(US$). Inte i indexet."}


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
        "revisions_numeric_only": {f"window_{w}q": _index_entry(out["index_numeric"][w], "index", "Q")
                                   for w in GR.WINDOWS},
        "composition_main_window": _composition(out["events"], out["index"][GR.MAIN_WINDOW], GR.MAIN_WINDOW),
        "break_statements": _breaks(out["breaks"]),
        "events_recent": recent,
        "events_per_company_year": counts,
        "surprise": {"companies": _companies(out["surprises"]),
                     "index": _index_entry(out["surprise_index"], "value", "Q"),
                     "tsmc_usd_sensitivity": _tsmc_usd(out["surprises_tsmc_usd"])},
    }


# Companies whose statements come from SEC series in the table (TSMC's 6-K, Nvidia's 8-K: GR.table_statements);
# every other company's statements come from the curated CSV (GR.capex_statements).
TABLE_COMPANIES = ("tsmc", "nvda")
WITHHELD_NOTE = ("Värden ur curated/guidance_capex.csv står inte i den publika ögonblicksbilden så länge serierna som "
                 "läser filen har publish=False (R11-4, granskning L3-1): för de bolagen och för revideringsindexet och "
                 "överraskningsindexet bara bolag, period, definition och datum. TSMC och Nvidia (SEC) visas som förut.")
_ID_FIELDS = ("period", "known_from", "companies")
_SURPRISE_ID = ("company", "measure", "period", "known_from", "guidance_known_from")


def from_csv(company) -> bool:
    return company not in TABLE_COMPANIES


def csv_public(publishable: Callable[[str], bool]) -> bool:
    """True when every series that reads the curated CSV may be shown (the owner's decision R11-4)."""
    return all(publishable(k) for k in (*GR.CSV_BASED, *GR.csv_component_keys()))


def _ids(entry):
    return {k: v for k, v in entry.items() if k in _ID_FIELDS} if isinstance(entry, dict) else entry


def withhold(section: dict, publishable: Callable[[str], bool]) -> dict:
    """The section for the public record: no number that comes from the curated CSV while its series are withheld
    (break statements, revision events and counts of the CSV companies, their surprises, the revision index and the
    surprise index, which all read the CSV). TSMC's and Nvidia's statements and surprises are SEC series and stay."""
    if not isinstance(section, dict) or "error" in section or csv_public(publishable):
        return section
    s = copy.deepcopy(section)
    for part in ("revisions", "revisions_numeric_only"):
        for entry in (s.get(part) or {}).values():
            for k in ("latest", "latest_with_value"):
                entry[k] = _ids(entry.get(k))
    if isinstance(s.get("composition_main_window"), dict):
        s["composition_main_window"] = {k: v for k, v in s["composition_main_window"].items() if k == "period"}
    s["break_statements"] = [{k: v for k, v in b.items() if k not in ("value", "prev_value", "size")}
                             if from_csv(b.get("company")) else b for b in s.get("break_statements") or []]
    s["events_recent"] = [{k: v for k, v in e.items() if k not in ("size", "direction")}
                          if from_csv(e.get("company")) else e for e in s.get("events_recent") or []]
    s["events_per_company_year"] = {c: v for c, v in (s.get("events_per_company_year") or {}).items()
                                    if not from_csv(c)}
    sur = s.get("surprise")
    if isinstance(sur, dict):
        sur["companies"] = [{k: v for k, v in c.items() if k in _SURPRISE_ID} if from_csv(c.get("company")) else c
                            for c in sur.get("companies") or []]
        if isinstance(sur.get("index"), dict):
            sur["index"] = {k: _ids(v) for k, v in sur["index"].items()}
    s["values_withheld"] = WITHHELD_NOTE
    return s


def safe_section(when, table: pd.DataFrame) -> dict:
    """`section`, with a failure recorded in the section instead of stopping the snapshot (descriptive group)."""
    try:
        return section(when, table)
    except Exception as e:  # noqa: BLE001 - the branch states are the record; this group is descriptive
        return {"group": GR.GROUP, "in_diffusion": False, "error": f"{type(e).__name__}: {e}"}
