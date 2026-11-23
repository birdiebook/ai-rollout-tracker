"""Scheduled jobs (GitHub Actions) and the scorecard.

    python -m ai_tracker.pipeline weekly [keys...]   refresh catalog series, run warehouse checks (exit 1 on a failed
                                                     check) and the freshness check (exit 2 if only series are stale)
    python -m ai_tracker.pipeline due [--today D]    which live forecasts are due today (UTC); read-only
    python -m ai_tracker.pipeline live               run every live routine whose registered origin is today
    python -m ai_tracker.pipeline n2-live            N2 only (day 5: previous month)
    python -m ai_tracker.pipeline n1-live            N1 only (quarter end + 20 days: the quarter just ended)
    python -m ai_tracker.pipeline scorecard          forecasts/SCORECARD.md: live forecasts vs first-vintage outcome
    python -m ai_tracker.pipeline publish PATH...    git-commit new forecast files + SCORECARD.md, or new snapshots (CI)

Timing rule. A live forecast is only made on its registered origin, and the origin is *today* in UTC: the routine
refreshes its series and then reads them with as_of(origin). Every row fetched today has known_from <= today, so the
information set is what was known on the origin day. A missed origin is not made up later (`python -m ai_tracker.nowcast
n1|n2` still allows a manual run with an explicit --origin). If the registered day falls on a weekend it is kept, never
shifted.

Immutability. A forecast file that exists is never rewritten (the writers open with mode "x"), a due origin whose
file exists is skipped, and `publish` refuses a path that is already in HEAD.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ai_tracker import catalog, config, observations, warehouse
from ai_tracker.nowcast import engine, intervals, n1, n2

FORECASTS = config.REPO / "forecasts"
SCORECARD = FORECASTS / "SCORECARD.md"
BOT_NAME = "github-actions[bot]"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
NOWCASTS = {  # forecasts/<dir>: label, target, variants in display order
    "n1": ("N1", n1.TARGET, n1.VARIANTS),
    "n2": ("N2", n2.TARGET, n2.VARIANTS),
}
SEC_MESSAGE = (
    "SEC_USER_AGENT is not set. sec.gov requires a declared User-Agent with a contact address and this project "
    "uses no fallback. Add the repository secret SEC_USER_AGENT = 'ai-rollout-tracker <contact address>' "
    "(Settings > Secrets and variables > Actions), or set it in .env locally."
)


def utc_today() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(timezone.utc).date())


# ------------------------------------------------------------------ origin days


@dataclass(frozen=True)
class Due:
    nowcast: str  # "n1" | "n2"
    origin: pd.Timestamp
    period: str  # target period, e.g. "2026-11" or "2026Q4"

    def path(self, root: Path | None = None) -> Path:
        return Path(root or FORECASTS) / self.nowcast / f"{self.period}.json"


def n2_due(today) -> Due | None:
    today = pd.Timestamp(today).normalize()
    month = n2.target_for(today)
    return Due("n2", today, str(month)) if n2.origin_for(month) == today else None


def n1_due(today) -> Due | None:
    today = pd.Timestamp(today).normalize()
    q = n1.target_quarter(today)
    return Due("n1", today, str(q)) if n1.origin_for(q) == today else None


def due(today) -> list[Due]:
    return [d for d in (n2_due(today), n1_due(today)) if d is not None]


# ------------------------------------------------------------------ helpers


def _gh_output(**kv: str) -> None:
    """Step outputs for GitHub Actions (no-op elsewhere). Never pass secrets here."""
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            for k, v in kv.items():
                f.write(f"{k}={v}\n")


def _annotate(level: str, msg: str) -> None:
    print(f"::{level}::{msg}" if os.environ.get("GITHUB_ACTIONS") == "true" else f"{level.upper()}: {msg}")


def require_sec(keys: list[str] | None = None) -> None:
    """Fail fast with a clear message if SEC series are to be fetched and no User-Agent is configured."""
    specs = [s for s in catalog.ALL if not keys or s.key in keys]
    if any(s.source.startswith("SEC") for s in specs) and not config.get("SEC_USER_AGENT"):
        raise SystemExit(SEC_MESSAGE)


def _refresh(keys: list[str] | None) -> list[str]:
    """Refresh `keys` (None = the whole catalog); returns the keys that failed."""
    status = observations.refresh(keys)
    return [k for k, v in status.items() if v.startswith("FAILED")]


# ------------------------------------------------------------------ weekly

STALE_EXIT = 2  # only stale series: the table itself is sound, so the workflow still saves the cache


def weekly(keys: list[str] | None = None, today=None) -> int:
    """Refresh, then the integrity checks (exit 1) and the freshness check on `keys` or the catalog (exit 2).

    A failed fetch alone is a warning: the stored data may still be fresh. Once a series is past its bound
    (warehouse.fresh) the job fails, and the message says whether this run's fetch failed too.
    """
    require_sec(keys)
    unknown = set(keys or []) - set(catalog.by_key())
    if unknown:
        raise SystemExit(f"unknown series: {sorted(unknown)}")
    today = pd.Timestamp(today or utc_today())
    failed = _refresh(keys)
    for k in failed:
        _annotate("warning", f"fetch failed: {k}")
    con = warehouse.connect()
    results = warehouse.run_checks(con)
    bad = {name: df for name, df in results.items() if len(df)}
    for name, df in results.items():
        print(f"{name:40s} {'ok' if df.empty else f'{len(df)} violations'}")
        if len(df):
            print(df.head(10).to_string())
    stale = warehouse.fresh(con, today)
    if keys:
        stale = stale[stale["series"].isin(keys)]
    lines = [line + (" - fetch FAILED this run" if k in failed else " - fetch ok but no new period")
             for k, line in zip(stale["series"], warehouse.describe_stale(stale))]
    print(f"{'fresh':40s} {'ok' if stale.empty else f'{len(stale)} stale series (as of {today.date()})'}")
    for line in lines:
        print("  " + line)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"Weekly fetch: {len(failed)} failed series, {len(bad)} failed checks, "
                    f"{len(stale)} stale series\n\n")
            for k in failed:
                f.write(f"- fetch failed: `{k}`\n")
            for name in bad:
                f.write(f"- check failed: `{name}`\n")
            for line in lines:
                f.write(f"- stale: {line}\n")
            if lines:
                f.write("\nSee docs/drift.md (Aktualitet) for how to handle a stale series.\n")
    if bad:
        _annotate("error", f"data checks failed: {', '.join(bad)}")
        return 1
    if lines:
        _annotate("error", f"{len(lines)} stale series (see docs/drift.md, Aktualitet): " + "; ".join(lines))
        return STALE_EXIT
    return 0


# ------------------------------------------------------------------ live


# Inputs of the B2 (guidance) variant, refreshed together with target and indicators before a live forecast.
LIVE_PREFIXES = {"n2": ("tsmc_guid_",), "n1": ("guid_capex_", "capex_", "fin_lease_")}


def live_keys(nowcast: str) -> list[str]:
    base = [n2.TARGET, *n2.INDICATORS] if nowcast == "n2" else [n1.TARGET, *n1.INDICATORS]
    extra = [s.key for s in catalog.ALL if s.key.startswith(LIVE_PREFIXES[nowcast]) and not s.closed]
    return list(dict.fromkeys(base + extra))


def run_live(d: Due, root: Path | None = None, table: pd.DataFrame | None = None, refresh: bool = True,
             today=None) -> Path | None:
    """Write the live forecast for `d` once. Returns the new path, or None if it already existed."""
    today = pd.Timestamp(today or utc_today())
    if d.origin != today:
        raise ValueError(f"{d.nowcast} origin {d.origin.date()} is not today ({today.date()}): not a live run")
    path = d.path(root)
    if path.exists():
        print(f"{path} exists; live forecasts are never rewritten. Skipping.")
        return None
    if refresh:
        keys = live_keys(d.nowcast)
        require_sec(keys)
        failed = _refresh(keys)
        if failed:  # a forecast is made once; better to retry the same day than to freeze one on stale data
            raise SystemExit(f"refresh failed for {failed}; no forecast written. Re-run the workflow today.")
    table = observations.load() if table is None else table
    if d.nowcast == "n2":
        out = n2.write(d.origin, table, path.parent, today=today)
    else:
        out = n1.write_live(table, d.origin, path.parent, today=today)
    assert Path(out) == path, (out, path)
    print(f"wrote {out}")
    return Path(out)


def live(only: str | None = None, root: Path | None = None, refresh: bool = True, today=None,
         table: pd.DataFrame | None = None) -> list[Path]:
    today = pd.Timestamp(today or utc_today())
    todo = [d for d in due(today) if only in (None, d.nowcast)]
    if not todo:
        print(f"{today.date()} is not a registered origin{' for ' + only if only else ''}; nothing to do.")
    written = [p for d in todo if (p := run_live(d, root, table, refresh, today)) is not None]
    if written:
        scorecard(root=root, table=table)
    rel = [str(p.relative_to(config.REPO)) if p.is_relative_to(config.REPO) else str(p) for p in written]
    _gh_output(written=" ".join(rel))
    return written


# ------------------------------------------------------------------ scorecard


def _num(x) -> float:
    return float("nan") if x is None else float(x)


def score(root: Path | None = None, table: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    """One row per live forecast file; errors (100 * log forecast/outcome) against the first vintage."""
    root = Path(root or FORECASTS)
    table = observations.load() if table is None else table
    out = {}
    for sub, (_, default_target, variants) in NOWCASTS.items():
        rows = []
        for f in sorted((root / sub).glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            target = d.get("target", default_target)
            period = d.get("quarter") or d.get("month")
            origin = pd.Timestamp(d["origin"])
            fv = engine.first_vintage(table, target)
            fkf = engine.first_known_from(table, target) if len(fv) else pd.Series(dtype="datetime64[ns]")
            fv.index, fkf.index = fv.index.astype(str), fkf.index.astype(str)
            row = {"period": period, "origin": origin.date().isoformat(), "champion": d["champion"],
                   "forecast": _num(d["value"]), "outcome": float("nan"), "known_from": "", "status": "väntar"}
            if period in fv.index:
                kf = pd.Timestamp(fkf[period])
                row["known_from"] = kf.date().isoformat()
                if kf <= origin:  # cannot happen through the routine; never score a known number
                    row["status"] = "utfall känt vid origin, räknas inte"
                else:
                    row["outcome"] = float(fv[period])
                    row["status"] = "utfall"
            for v in variants:
                x = _num(d.get("variants", {}).get(v))
                ok = math.isfinite(x) and math.isfinite(row["outcome"]) and x > 0
                row[f"err_{v}"] = engine.log_error(x, row["outcome"]) if ok else float("nan")
            row["err_champion"] = row.get(f"err_{d['champion']}", float("nan"))
            if intervals.ENABLED:  # grind G-C: scores of the distribution stored in the file, never recomputed
                _score_distribution(row, d, variants)
            rows.append(row)
        out[sub] = pd.DataFrame(rows)
    return out


DIST_FIELDS = ("crps", "pit", *(f"hit_{intervals.level_key(L)}" for L in intervals.LEVELS))


def _score_distribution(row: dict, d: dict, variants) -> None:
    """Columns <field>_<variant> (crps, pit, hit_50/80/95) and the champion's stored intervals (interval_<L>,
    in levels) from the file's `distribution` block. NaN where the file has none or no outcome is known."""
    block = d.get("distribution") or {}
    champ = (block.get("models") or {}).get(d["champion"]) or {}
    for L in intervals.LEVELS:
        k = intervals.level_key(L)
        row[f"interval_{k}"] = (champ.get("intervals") or {}).get(k)
    for v in [*variants, "champion"]:
        model = d["champion"] if v == "champion" else v
        sc = intervals.score_live(block, model, row[f"err_{v}"]) if row["status"] == "utfall" else {}
        for f in DIST_FIELDS:
            row[f"{f}_{v}"] = sc.get(f, float("nan"))


def _interval_lines(df: pd.DataFrame, variants) -> list[str]:
    """Scorecard section for the stored distributions (only with intervals.ENABLED)."""
    if "crps_champion" not in df:
        return []
    keys = [intervals.level_key(L) for L in intervals.LEVELS]
    lines = ["", f"### Intervall ({intervals.REGISTER_REF})", "",
             "| Period | " + " | ".join(f"{k} % intervall huvudmodell" for k in keys) + " |",
             "|" + "---|" * (1 + len(keys))]
    for r in df.itertuples(index=False):
        r = r._asdict()
        cells = [f"{_fmt(r[f'interval_{k}'][0])} – {_fmt(r[f'interval_{k}'][1])}" if r[f"interval_{k}"] else ""
                 for k in keys]
        lines.append(f"| {r['period']} | " + " | ".join(cells) + " |")
    scored = df[df["status"] == "utfall"]
    if len(scored):
        lines += ["", "| Variant | n | " + " | ".join(f"Täckning {k} %" for k in keys) + " | CRPS |",
                  "|" + "---|" * (3 + len(keys))]
        for v in ["champion", *variants]:
            g = scored[scored[f"crps_{v}"].notna()]
            name = "huvudmodell" if v == "champion" else v
            cov = " | ".join(_fmt(g[f"hit_{k}_{v}"].mean(), 2) if len(g) else "" for k in keys)
            lines.append(f"| {name} | {len(g)} | {cov} | {_fmt(g[f'crps_{v}'].mean(), 2) if len(g) else ''} |")
        lines += ["", "Täckningen blir meningsfull först efter många utfall (för N2 cirka 12 månader)."]
    return lines


def _fmt(x, nd=1) -> str:
    return "" if x is None or (isinstance(x, float) and not math.isfinite(x)) else f"{x:,.{nd}f}".replace(",", " ")


def render(scores: dict[str, pd.DataFrame], today=None) -> str:
    today = pd.Timestamp(today or utc_today())
    lines = ["# Scorecard – skarpa prognoser", "",
             "Genereras av `python -m ai_tracker.pipeline scorecard`. Prognosfilerna i `forecasts/<nowcast>/` "
             "läses, aldrig ändras. Utfall = **första vintage** (tidigaste `known_from`). "
             "Fel = 100 · (log prognos − log utfall). Huvudmodellen är den som stod i filen när prognosen gjordes; "
             "övriga varianter är skuggor.", "",
             f"Uppdaterad {today.date()}.", ""]
    for sub, df in scores.items():
        label, target, variants = NOWCASTS[sub]
        lines += [f"## {label} – `{target}`", ""]
        if df.empty:
            lines += ["Inga skarpa prognoser än.", ""]
            continue
        head = ["Period", "Origin", "Huvudmodell", "Prognos", "Utfall", "Känt från", "Fel huvudmodell",
                *[f"Fel {v}" for v in variants], "Status"]
        lines += ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"]
        for r in df.itertuples(index=False):
            r = r._asdict()
            cells = [r["period"], r["origin"], r["champion"], _fmt(r["forecast"]), _fmt(r["outcome"]),
                     r["known_from"], _fmt(r["err_champion"], 2), *[_fmt(r[f"err_{v}"], 2) for v in variants],
                     r["status"]]
            lines.append("| " + " | ".join(str(c) for c in cells) + " |")
        scored = df[df["status"] == "utfall"]
        lines += ["", f"Utvärderade: {len(scored)} av {len(df)}."]
        if len(scored):
            lines += ["", "| Variant | n | MAE | Bias |", "|---|---|---|---|"]
            for v in ["champion", *variants]:
                e = scored[f"err_{v}"].dropna()
                name = "huvudmodell" if v == "champion" else v
                lines.append(f"| {name} | {len(e)} | {_fmt(e.abs().mean(), 2)} | {_fmt(e.mean(), 2)} |")
            lines += ["", "Få utfall: skillnader mellan varianter kan vara slump."]
        lines += _interval_lines(df, variants)
        lines.append("")
    return "\n".join(lines)


def scorecard(root: Path | None = None, table: pd.DataFrame | None = None, out: Path | None = None,
              today=None) -> Path:
    root = Path(root or FORECASTS)
    out = Path(out or root / "SCORECARD.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(score(root, table), today), encoding="utf-8")
    print(f"wrote {out}")
    return out


# ------------------------------------------------------------------ publish (CI)


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=check)


SNAPSHOT_PATH = re.compile(r"snapshots/\d{4}-\d{2}\.json")
FORECAST_PATH = re.compile(r"forecasts/[^/]+/[^/]+\.json")


def publish(paths: list[str], repo: Path | None = None, scorecard_path: str = "forecasts/SCORECARD.md") -> bool:
    """Commit new forecast files (and the scorecard) or new monthly snapshots with the bot identity. Does not push.

    Only paths that are not yet in HEAD are committed: a forecast or snapshot that is already committed is never
    committed again, so a second run is a no-op. Returns True if a commit was made.
    """
    repo = Path(repo or config.REPO)
    new = []
    for p in paths:
        if not (FORECAST_PATH.fullmatch(p) or SNAPSHOT_PATH.fullmatch(p)):
            raise SystemExit(f"refusing to publish {p}: only forecasts/<nowcast>/<period>.json "
                             "or snapshots/<YYYY-MM>.json")
        if _git(repo, "cat-file", "-e", f"HEAD:{p}", check=False).returncode == 0:
            print(f"{p} is already committed; live forecasts and snapshots are never re-committed. Skipping.")
            continue
        if not (repo / p).is_file():
            raise SystemExit(f"{p} does not exist")
        new.append(p)
    if not new:
        print("nothing to publish")
        return False
    forecasts = [p for p in new if FORECAST_PATH.fullmatch(p)]
    snapshots = [p for p in new if SNAPSHOT_PATH.fullmatch(p)]
    _git(repo, "add", "--", *new)
    if forecasts and (repo / scorecard_path).is_file():
        _git(repo, "add", "--", scorecard_path)
    staged = _git(repo, "diff", "--cached", "--name-status").stdout.split("\n")
    staged = [line.split("\t") for line in staged if line]
    allowed = set(new) | ({scorecard_path} if forecasts else set())
    if any(f not in allowed for _, f in staged) or any(s != "A" for s, f in staged if f in new):
        raise SystemExit(f"unexpected staged changes: {staged}")
    parts = []
    if forecasts:
        periods = ", ".join(Path(p).parent.name + " " + Path(p).stem for p in forecasts)
        parts.append(f"Live forecast {periods} (origin {utc_today().date()})")
    if snapshots:
        parts.append(f"Monthly snapshot {', '.join(Path(p).stem for p in snapshots)} (written {utc_today().date()})")
    _git(repo, "-c", f"user.name={BOT_NAME}", "-c", f"user.email={BOT_EMAIL}", "commit", "-m", "; ".join(parts))
    print(f"committed {new}")
    return True


# ------------------------------------------------------------------ CLI


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ai_tracker.pipeline", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", default=None, help="observation table (default data/observations.parquet)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("weekly")
    w.add_argument("keys", nargs="*")
    dp = sub.add_parser("due")
    dp.add_argument("--today", default=None, help="date to check (default: today UTC); read-only")
    for name in ("live", "n2-live", "n1-live"):
        p = sub.add_parser(name)
        p.add_argument("--no-refresh", action="store_true", help="use the stored table as is")
    sub.add_parser("scorecard")
    pub = sub.add_parser("publish")
    pub.add_argument("paths", nargs="*")
    a = ap.parse_args(argv)
    if a.table:
        observations.PATH = Path(a.table)

    if a.cmd == "weekly":
        return weekly(a.keys or None)
    if a.cmd == "due":
        today = pd.Timestamp(a.today) if a.today else utc_today()
        todo = [d for d in due(today) if not d.path().exists()]
        for d in due(today):
            print(f"{d.nowcast} origin {d.origin.date()} target {d.period}: "
                  f"{'exists, skip' if d.path().exists() else 'due'}")
        if not todo:
            print(f"{today.date()}: nothing due")
        _gh_output(due="true" if todo else "false", nowcasts=" ".join(d.nowcast for d in todo))
        return 0
    if a.cmd in ("live", "n2-live", "n1-live"):
        live(None if a.cmd == "live" else a.cmd[:2], refresh=not a.no_refresh)
        return 0
    if a.cmd == "scorecard":
        scorecard()
        return 0
    publish(a.paths)
    return 0


if __name__ == "__main__":
    sys.exit(main())
