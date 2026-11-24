"""Branch aggregation (register section 2): direction per series, diffusion index and state.

Two index rules (register 2026-11-24, "Diffusionsindex v2"):
- v2, the official rule from the snapshot 2026-11-30: one vote per source family. A family's vote is the mean of
  (d + 1) / 2 over its counted series; the index is the mean of the votes of families with at least one counted
  series; fewer than MIN_FAMILIES counted families -> STATE_FEW_FAMILIES (index still shown).
- v1, the rule of section 2: one vote per series, fewer than MIN_SERIES series -> STATE_FEW. Computed and published
  alongside under the name v1.
Which series count, and their directions, are the same for both rules.
"""

from __future__ import annotations

import re
from fractions import Fraction

import pandas as pd

from ai_tracker import catalog, observations, warehouse
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
        end = pd.PeriodIndex(rows["period"].unique(), freq=catalog.FREQS.get(freq, freq)).end_time.max().normalize()
        age, bound = (when - end).days, warehouse.max_age_days(spec)
        if age > bound:
            return f"inaktuell: {k} senaste period slutade för {age} dagar sedan (gräns {bound})"
    return ""


def resolve_all(entry: str, when, ctx: Context) -> list[tuple[str | None, str]]:
    """A register entry -> [(series key or None, note)] on `when`. `<valda>` gives one key per selected benchmark
    (ctx.selection(when)); every other entry gives one (see `resolve`)."""
    if R.SELECTED_PLACEHOLDER in entry:
        slugs = ctx.selection(pd.Timestamp(when))
        if not slugs:
            return [(None, f"{entry}: ingen vald benchmark på beräkningsdagen")]
        return [(entry.replace(R.SELECTED_PLACEHOLDER, s), f"vald benchmark {s}") for s in slugs]
    return [resolve(entry, when, ctx)]


def benchmark_guard(key: str, when, ctx: Context) -> str:
    """A selected benchmark that, with what is known on `when`, is saturated (frontier > 0.90) or retired (its
    newest month with an Epoch run ended more than 90 days before `when`) is not counted, also before its
    successor is registered. '' = no objection. `superseded_by` is metadata without dated history: it takes
    effect through a registered replacement (series.epoch_hub.REPLACEMENTS), and the 90-day rule catches a
    benchmark that Epoch stops running."""
    when = pd.Timestamp(when)
    front = observations.as_of(key, when, ctx.rows(key))
    if len(front) and front.max() > R.REPLACE_ABOVE:
        return f"mättad: frontvärde {front.max():.3f} > {R.REPLACE_ABOVE} känt på beräkningsdagen"
    runs_key = key.replace(R.BENCH_FRONTIER_PREFIX, R.BENCH_RUNS_PREFIX, 1)
    runs = observations.as_of(runs_key, when, ctx.rows(runs_key))
    active = runs[runs > 0]
    if len(active):
        last_end = active.index.max().end_time.normalize()
        if (when - last_end).days > R.RETIRE_AFTER_DAYS:
            return (f"avslutad: senaste kända månad med Epoch-körning är {active.index.max()} "
                    f"(mer än {R.RETIRE_AFTER_DAYS} dagar före beräkningsdagen)")
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
        end = pd.PeriodIndex(rows["period"].unique(), freq={"2W": "W-SUN", "W": "W-SUN"}.get(freq, freq)).end_time.max()
        cand = (end, int(m.group(1)), key)
        best = cand if best is None or cand > best else best
    if best is None:
        return None, f"{entry}: ingen regim känd på beräkningsdagen"
    return best[2], f"aktiv regim {best[2]}"


def state_of(index: float | Fraction | None, n: int, minimum: int | None = None, few: str | None = None) -> str:
    """Registered state rule. The index is compared unrounded (2/3 = 0.667 is below 0.67: stable).
    Default: v1 (n = counted series, fewer than MIN_SERIES -> STATE_FEW); `state_v2` passes the family minimum.

    An exact index (a Fraction, as v2 computes it) is compared exactly with the register's decimal thresholds
    (0.67 = 67/100). A float index is compared with the float thresholds: v1 is one division of small integers,
    so its float lies on the same side as the exact value (review R9, N1)."""
    if n < (R.MIN_SERIES if minimum is None else minimum) or index is None:
        return R.STATE_FEW if few is None else few
    accel, brake = R.ACCELERATING, R.BRAKING
    if isinstance(index, Fraction):
        accel, brake = Fraction(str(accel)), Fraction(str(brake))
    if index >= accel:
        return R.STATE_ACCEL
    if index <= brake:
        return R.STATE_BRAKE
    return R.STATE_STABLE


def state_v2(index: float | Fraction | None, n_families: int) -> str:
    """v2 state: the same thresholds, fewer than MIN_FAMILIES counted families -> STATE_FEW_FAMILIES."""
    return state_of(index, n_families, R.MIN_FAMILIES, R.STATE_FEW_FAMILIES)


def diffusion(directions: list[int]) -> float | None:
    if not directions:
        return None
    return (sum(d == 1 for d in directions) + 0.5 * sum(d == 0 for d in directions)) / len(directions)


def vote_exact(directions: list[int]) -> Fraction | None:
    """A family's vote (v2), exactly: the mean of (d + 1) / 2 over its counted series (1, 1/2 or 0 for one series)."""
    if not directions:
        return None
    return Fraction(sum(d + 1 for d in directions), 2 * len(directions))


def vote(directions: list[int]) -> float | None:
    """A family's vote (v2) as a float (stored in the snapshot), the nearest float to `vote_exact`."""
    v = vote_exact(directions)
    return None if v is None else float(v)


def diffusion_v2_exact(family_directions: dict[str, list[int]]) -> Fraction | None:
    """index_v2, exactly: the mean of the family votes over families with at least one counted series. The state is
    decided on this value, so a float mean can never fall on the wrong side of a threshold (review R9, N1)."""
    votes = [v for v in (vote_exact(d) for d in family_directions.values()) if v is not None]
    return sum(votes, Fraction(0)) / len(votes) if votes else None


def diffusion_v2(family_directions: dict[str, list[int]]) -> float | None:
    """index_v2 as a float (stored in the snapshot), the nearest float to `diffusion_v2_exact`."""
    x = diffusion_v2_exact(family_directions)
    return None if x is None else float(x)


def family_of(fam: str, entry: str, key: str | None) -> str:
    """The family of a resolved series. A family id with `<valda>` takes the selected benchmark of the key."""
    if R.SELECTED_PLACEHOLDER not in fam or key is None or R.SELECTED_PLACEHOLDER not in entry:
        return fam
    head, tail = entry.split(R.SELECTED_PLACEHOLDER, 1)
    slug = key[len(head): len(key) - len(tail) if tail else None]
    return fam.replace(R.SELECTED_PLACEHOLDER, slug)


def branch(code: str, when, ctx: Context) -> dict:
    entries = R.core_entries(code, ctx.core)
    fam_of = R.entry_families(code, ctx.core, ctx.families)
    used, not_counted = [], []
    family_order: list[str] = []
    for entry in entries:
        for key, note in resolve_all(entry, when, ctx):
            fam = family_of(fam_of[entry], entry, key)
            if fam not in family_order:
                family_order.append(fam)
            if key is None:
                not_counted.append({"entry": entry, "series": None, "family": fam, "reason": note})
                continue
            if key not in ctx.specs and key not in ctx.derived:
                not_counted.append({"entry": entry, "series": key, "family": fam,
                                    "reason": f"{note}: serien saknas i katalogen"})
                continue
            if key in R.RECONCILIATIONS:  # register A5: never in a branch index
                not_counted.append({"entry": entry, "series": key, "family": fam,
                                    "reason": "avstämning (A5): räknas inte i grenarnas diffusionsindex"})
                continue
            m = measure(key, when, ctx)
            m["entry"] = entry
            m["family"] = fam
            if note:
                m["resolved"] = note
            stale = stale_reason(key, when, ctx)
            if stale and m["valid"]:
                m["valid"], m["reason"] = False, stale
            guard = benchmark_guard(key, when, ctx) if R.SELECTED_PLACEHOLDER in entry else ""
            if guard and m["valid"]:
                m["valid"], m["reason"] = False, guard
            (used if m["valid"] else not_counted).append(m)
    dirs = [m["direction"] for m in used]
    counts = {"n_series": len(used), "n_up": sum(d == 1 for d in dirs), "n_neutral": sum(d == 0 for d in dirs),
              "n_down": sum(d == -1 for d in dirs)}
    index_v1 = diffusion(dirs)
    by_family = {f: [m["direction"] for m in used if m["family"] == f] for f in family_order}
    families = [{"family": f, "series": [m["series"] for m in used if m["family"] == f], "vote": vote(d)}
                for f, d in by_family.items()]
    n_families = sum(1 for d in by_family.values() if d)
    exact = diffusion_v2_exact(by_family)
    index = None if exact is None else float(exact)
    none = "inga registrerade kärnserier"
    return {
        "branch": code,
        "registered_entries": entries,
        "rule_version": R.INDEX_RULE,
        **counts,
        "n_families": n_families,
        "index": index,
        "state": state_v2(exact, n_families) if entries else none,
        "families": families,
        "v1": {"index": index_v1, "state": state_of(index_v1, len(used)) if entries else none, **counts},
        "series_used": used,
        "series_not_counted": not_counted,
    }


RECONCILIATION_NOTE = ("Avstämningar mellan leden (register A5): härledda kvoter, takt = årsförändring i log(kvot) "
                       "×100. Räknas inte i grenarnas diffusionsindex.")


def reconciliations(when, ctx: Context) -> dict:
    """Measures of the A5 reconciliation series as of `when` (register 2026-11-23), a group of its own.

    Same measure engine as the branches (as_of(when), expanding statistics); `valid` means the measure is complete
    (and fresh), never that the series counts anywhere: `in_diffusion` is always False. Keys missing from the
    catalog of `ctx` are left out (test contexts)."""
    out = []
    for key in ctx.reconciliations:
        if key not in ctx.specs:
            continue
        m = measure(key, when, ctx)
        stale = stale_reason(key, when, ctx)
        if stale and m["valid"]:
            m["valid"], m["reason"] = False, stale
        m["in_diffusion"] = False
        out.append(m)
    return {"group": R.RECONCILIATION_GROUP, "in_diffusion": False, "note": RECONCILIATION_NOTE, "series": out}
