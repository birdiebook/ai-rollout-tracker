"""Branch aggregation (register section 2): direction per series, diffusion index and state."""

from __future__ import annotations

import re

import pandas as pd

from ai_tracker import catalog, warehouse
from ai_tracker.state import register as R
from ai_tracker.state.measures import Context, measure

# A derived series is as fresh as its stalest component.
DERIVED_COMPONENTS = {"capex_ocf_hyp4": ("capex_hyp4", "ocf_hyp4")}


def stale_reason(key: str, when, ctx: Context) -> str:
    """Register amendment 2026-11-23: a series whose newest period known on `when` is older than its
    freshness bound (warehouse.max_age_days, same rule as the weekly check) is not counted. '' = fresh."""
    specs = catalog.by_key()
    when = pd.Timestamp(when)
    for k in DERIVED_COMPONENTS.get(key, (key,)):
        spec = specs.get(k)
        if spec is None:
            continue
        rows = ctx.rows(k)
        rows = rows[rows["known_from"] <= when]
        if rows.empty:
            return f"inaktuell: {k} har inga data kända på beräkningsdagen"
        freq = rows["freq"].iloc[0]
        end = pd.PeriodIndex(rows["period"], freq=catalog.FREQS.get(freq, freq)).end_time.max().normalize()
        age, bound = (when - end).days, warehouse.max_age_days(spec)
        if age > bound:
            return f"inaktuell: {k} senaste period slutade för {age} dagar sedan (gräns {bound})"
    return ""


def resolve(entry: str, when, ctx: Context) -> tuple[str | None, str]:
    """A register entry -> series key on `when`. `<aktiv regim>`: the regime series with the latest period known.

    Regime series are <prefix>v<n>. The active regime is the one whose latest known observation (as of `when`)
    ends last; ties go to the higher version. Pace is then computed within that regime only, and there is no
    fallback to an earlier regime when the active one is too short.
    """
    if R.REGIME_PLACEHOLDER not in entry:
        return entry, ""
    prefix = entry.replace(R.REGIME_PLACEHOLDER, "")
    pat = re.compile(re.escape(prefix) + R.REGIME_SUFFIX + "$")
    when = pd.Timestamp(when)
    best = None
    for key in ctx.keys():
        m = pat.match(key)
        if not m:
            continue
        rows = ctx.rows(key)
        rows = rows[rows["known_from"] <= when]
        if rows.empty:
            continue
        freq = rows["freq"].iloc[0]
        end = pd.PeriodIndex(rows["period"], freq={"2W": "W-SUN", "W": "W-SUN"}.get(freq, freq)).end_time.max()
        cand = (end, int(m.group(1)), key)
        best = cand if best is None or cand > best else best
    if best is None:
        return None, f"{entry}: ingen regim känd på beräkningsdagen"
    return best[2], f"aktiv regim {best[2]}"


def state_of(index: float | None, n: int) -> str:
    """Registered state rule. The index is compared unrounded (2/3 = 0.667 is below 0.67: stable)."""
    if n < R.MIN_SERIES or index is None:
        return R.STATE_FEW
    if index >= R.ACCELERATING:
        return R.STATE_ACCEL
    if index <= R.BRAKING:
        return R.STATE_BRAKE
    return R.STATE_STABLE


def diffusion(directions: list[int]) -> float | None:
    if not directions:
        return None
    return (sum(d == 1 for d in directions) + 0.5 * sum(d == 0 for d in directions)) / len(directions)


def branch(code: str, when, ctx: Context) -> dict:
    entries = R.core_entries(code, ctx.core)
    used, not_counted = [], []
    for entry in entries:
        key, note = resolve(entry, when, ctx)
        if key is None:
            not_counted.append({"entry": entry, "series": None, "reason": note})
            continue
        m = measure(key, when, ctx)
        m["entry"] = entry
        if note:
            m["resolved"] = note
        stale = stale_reason(key, when, ctx)
        if stale and m["valid"]:
            m["valid"], m["reason"] = False, stale
        (used if m["valid"] else not_counted).append(m)
    dirs = [m["direction"] for m in used]
    index = diffusion(dirs)
    return {
        "branch": code,
        "registered_entries": entries,
        "n_series": len(used),
        "n_up": sum(d == 1 for d in dirs),
        "n_neutral": sum(d == 0 for d in dirs),
        "n_down": sum(d == -1 for d in dirs),
        "index": index,
        "state": state_of(index, len(used)) if entries else "inga registrerade kärnserier",
        "series_used": used,
        "series_not_counted": not_counted,
    }
