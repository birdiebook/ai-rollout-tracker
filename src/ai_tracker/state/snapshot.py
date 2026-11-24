"""Monthly snapshot (live record) and the historical backcast (reconstruction, not a record).

Snapshot date: the last calendar day of the month (the register does not name a day; see
docs/resultat/tillstand.md). `write` refuses a date that is not a month end, a date after today (UTC), and an
existing file (opened with mode "x"): a snapshot is written once and never rewritten, the git timestamp is the proof.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ai_tracker import catalog, config, evaluation, observations
from ai_tracker.state import register as R
from ai_tracker.state.branch import branch, reconciliations
from ai_tracker.state.measures import Context

SNAPSHOTS = config.REPO / "snapshots"
BACKCAST = config.REPO / "outputs" / "state_backcast.csv"
BACKCAST_LABEL = "rekonstruerad (as-of-backcast, inte ett skarpt register)"
INDEX_RULE_NOTE = ("index och state följer v2 (en röst per källfamilj, minst min_families räknade familjer, "
                   "registret 2026-11-24). v1 (en röst per serie, minst min_series serier) står under v1 i varje gren.")


def utc_today() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(timezone.utc).date())


def month_end(month) -> pd.Timestamp:
    return pd.Period(month, freq="M").end_time.normalize()


def is_month_end(day) -> bool:
    day = pd.Timestamp(day).normalize()
    return day == month_end(day.to_period("M"))


def _clean(x):
    """JSON-safe: NaN/inf -> None, numpy scalars -> Python."""
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if hasattr(x, "item") and not isinstance(x, (str, bytes)):
        x = x.item()
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def register_sha256(path: Path | None = None) -> str:
    return hashlib.sha256(Path(path or R.REGISTER_PATH).read_bytes()).hexdigest()


def compute(when, ctx: Context) -> dict:
    """The state of every branch as of `when` (pure: no git, no clock)."""
    when = pd.Timestamp(when).normalize()
    return {code: branch(code, when, ctx) for code in catalog.BRANCHES}


def build(when, table: pd.DataFrame | None = None, ctx: Context | None = None) -> dict:
    when = pd.Timestamp(when).normalize()
    ctx = ctx or Context(observations.load() if table is None else table)
    t = ctx.table
    return _clean({
        "snapshot": str(when.to_period("M")),
        "date": str(when.date()),
        "record": "skarp ögonblicksbild",
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": evaluation.git_sha(),
        "register_sha256": register_sha256(),
        "table_max_fetched_at": str(pd.Timestamp(t["fetched_at"].max()).date()) if len(t) else None,
        "rules": {"deadband_sd": R.DEADBAND, "accelerating_at_least": R.ACCELERATING, "braking_at_most": R.BRAKING,
                  "index_rule": R.INDEX_RULE, "index_rule_note": INDEX_RULE_NOTE, "min_families": R.MIN_FAMILIES,
                  "families": {code: ctx.families.get(code, {}) for code in catalog.BRANCHES},
                  "min_series": R.MIN_SERIES, "min_history": R.MIN_HISTORY, "pace_lag": R.PACE_LAG,
                  "change_lag": R.CHANGE_LAG, "doubling_window_months": R.DOUBLING_WINDOW,
                  "backfill_gated": sorted(R.BACKFILL_GATED), "backfill_flagged": sorted(R.BACKFILL_FLAGGED),
                  "own_snapshot_months": R.OWN_SNAPSHOT_MONTHS, "g1_selected_benchmarks": ctx.selection(when),
                  "reconciliations": list(ctx.reconciliations)},
        "branches": compute(when, ctx),
        "reconciliations": reconciliations(when, ctx),
    })


def path_for(when, out_dir: Path | None = None) -> Path:
    return Path(out_dir or SNAPSHOTS) / f"{pd.Timestamp(when).to_period('M')}.json"


def regime_section(when, table: pd.DataFrame, out_dir: Path | None = None) -> dict:
    """C4 (regime and breaks) as its own section, not part of the branch states (c4_spec section 1). Chained on the
    previous month's snapshot section when it exists. A failure is recorded in the section, never stops the snapshot."""
    from ai_tracker.regime import live as regime_live  # heavy (factor model); only for live snapshots

    prev_path = path_for(month_end(pd.Timestamp(when).to_period("M") - 1), out_dir)
    previous = None
    if prev_path.is_file():
        previous = json.loads(prev_path.read_text(encoding="utf-8")).get(regime_live.SECTION)
        if previous is not None and not previous.get("ms"):  # an earlier failed section: start a new chain
            previous = None
    try:
        return regime_live.section(table, when, previous)
    except Exception as e:  # noqa: BLE001 - the branch states are the record; C4 is descriptive (F-D6)
        return {"spec_version": regime_live.SPEC_LOCK, "model": "C4", "ms": None, "bocpd": None,
                "error": f"{type(e).__name__}: {e}"}


def write(when, table: pd.DataFrame | None = None, out_dir: Path | None = None, today=None,
          regime: bool | None = None) -> Path:
    """`regime`: include the C4 section (default: from regime.live.FIRST_LIVE, the first snapshot after the holdout)."""
    when = pd.Timestamp(when).normalize()
    today = pd.Timestamp(today).normalize() if today is not None else utc_today()
    if when > today:
        raise ValueError(f"{when.date()} is in the future (today {today.date()} UTC): as_of would not be the real "
                         "information set")
    if not is_month_end(when):
        raise ValueError(f"{when.date()} is not the last day of its month (the registered snapshot date)")
    path = path_for(when, out_dir)
    if path.exists():
        raise FileExistsError(f"{path} exists; snapshots are never rewritten")
    table = observations.load() if table is None else table
    data = build(when, table)
    if regime is None:
        from ai_tracker.regime.live import FIRST_LIVE

        regime = when >= FIRST_LIVE
    if regime:
        from ai_tracker.regime.live import SECTION

        data[SECTION] = _clean(regime_section(when, table, out_dir))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:  # 'x' = fail if it appeared meanwhile
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path


def due(today=None, out_dir: Path | None = None) -> bool:
    """True when today (UTC) is the last day of a month and that month's snapshot is not written yet."""
    today = pd.Timestamp(today).normalize() if today is not None else utc_today()
    return is_month_end(today) and not path_for(today, out_dir).exists()


def backcast(start: str, end: str, table: pd.DataFrame | None = None, out: Path | None = None) -> pd.DataFrame:
    """As-of state at every month end from `start` to `end` (YYYY-MM), one row per month and branch.
    index/state are the official rule (v2, register 2026-11-24); index_v1/state_v1 the rule of section 2.

    Reconstructed from today's table: each month sees only rows with known_from <= its month end, but rows
    dated by publication lag (source="backfill") carry today's vintage. Not a live record.
    """
    ctx = Context(observations.load() if table is None else table)
    rows = []
    for month in pd.period_range(start, end, freq="M"):
        when = month_end(month)
        for code, b in compute(when, ctx).items():
            rows.append({
                "month": str(month), "date": str(when.date()), "branch": code, "index": b["index"],
                "state": b["state"], "n_families": b["n_families"], "index_v1": b["v1"]["index"],
                "state_v1": b["v1"]["state"], "n_series": b["n_series"], "n_up": b["n_up"],
                "n_neutral": b["n_neutral"], "n_down": b["n_down"],
                "families": ";".join(f"{f['family']}:{f['vote']:.3f}" for f in b["families"] if f["vote"] is not None),
                "series": ";".join(f"{m['series']}:{m['direction']:+d}" for m in b["series_used"]),
                "label": BACKCAST_LABEL,
            })
    df = pd.DataFrame(rows)
    if out is not False:
        out = Path(out or BACKCAST)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
    return df


def rule_comparison(df: pd.DataFrame, last: int = 6) -> str:
    """Markdown table of a backcast's last `last` months: index, state and counts per branch under v1 and v2."""
    def num(x) -> str:
        return "–" if x is None or (isinstance(x, float) and not math.isfinite(x)) else f"{x:.2f}".replace(".", ",")

    months = sorted(df["month"].astype(str).unique())[-last:]
    d = df[df["month"].astype(str).isin(months)].sort_values(["branch", "month"])
    lines = ["| Gren | Månad | Index v1 | Tillstånd v1 | Serier | Index v2 | Tillstånd v2 | Källor |",
             "|---|---|---|---|---|---|---|---|"]
    for r in d.itertuples(index=False):
        idx1 = None if pd.isna(r.index_v1) else float(r.index_v1)
        idx2 = None if pd.isna(r.index) else float(r.index)
        lines.append(f"| {r.branch} | {r.month} | {num(idx1)} | {r.state_v1} | {int(r.n_series)} | {num(idx2)} | "
                     f"{r.state} | {int(r.n_families)} |")
    return "\n".join(lines) + "\n"
