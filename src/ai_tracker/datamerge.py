"""Merge a track's data into the shared base table, behind the data checks.

    python -m ai_tracker.datamerge <track_data_dir> [--into <base_dir>] [--series KEY ...] [--replace KEY ...]
                                   [--today D] [--dry-run]

<track_data_dir> is a worktree's data/ (observations.parquet, fetch_log.parquet, rebuilt_series.json). The base
defaults to AI_TRACKER_SHARED_DATA, else this checkout's data/.

Per series in the track table or its rebuilt list (or only --series):
- added:     not in the base; the track's rows are appended.
- replaced:  rebuilt in the track (drop_series / `observations --rebuild` writes rebuilt_series.json) or named in
             --replace: the base's rows of the series are removed and the track's rows take their place.
- updated:   in both; base ∪ track, the track row wins on an identical (series, period, known_from). An
             incremental fetch over the shared base stores only its new rows, so this appends them.
- unchanged: nothing new.
The fetch log is merged the same way (base ∪ track for the merged series, track wins on (series, fetched_at)).

Gate: the warehouse checks (all of them, on the whole merged table) and freshness (warehouse.fresh on `today`,
for the merged series) must pass, else nothing is written and the exit code is 1. Writes are atomic (temp file
+ rename), under a lock file, and the previous base files are kept in <base_dir>/merge_backups/ (last 20).
Idempotent: a second run finds every series unchanged and writes nothing.

Run it from a checkout whose catalog contains the track's series (series_in_catalog, freq_matches_catalog):
merge the track's code first, then its data.
"""

from __future__ import annotations

import argparse
import fcntl
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ai_tracker import catalog, config, observations, warehouse

TABLE = "observations.parquet"
LOG = "fetch_log.parquet"
KEEP_BACKUPS = 20


@dataclass
class Result:
    added: dict[str, int] = field(default_factory=dict)  # series -> rows
    replaced: dict[str, tuple[int, int]] = field(default_factory=dict)  # series -> (base rows before, rows after)
    updated: dict[str, int] = field(default_factory=dict)  # series -> rows added or overridden
    unchanged: list[str] = field(default_factory=list)
    failed: dict[str, pd.DataFrame] = field(default_factory=dict)  # check name -> violations
    stale: pd.DataFrame = field(default_factory=pd.DataFrame)
    rows_before: int = 0
    rows_after: int = 0
    log_rows_added: int = 0
    written: bool = False

    @property
    def changed(self) -> bool:
        return bool(self.added or self.replaced or self.updated or self.log_rows_added)

    @property
    def ok(self) -> bool:
        return not self.failed and self.stale.empty

    def summary(self) -> str:
        lines = [f"added     {len(self.added):3d} series  " + _fmt(self.added),
                 f"replaced  {len(self.replaced):3d} series  " +
                 ", ".join(f"{k} ({a}->{b} rows)" for k, (a, b) in sorted(self.replaced.items())),
                 f"updated   {len(self.updated):3d} series  " + _fmt(self.updated),
                 f"unchanged {len(self.unchanged):3d} series",
                 f"rows      {self.rows_before} -> {self.rows_after} ({self.rows_after - self.rows_before:+d}); "
                 f"fetch log +{self.log_rows_added}"]
        for name, df in self.failed.items():
            lines.append(f"CHECK FAILED {name}: {len(df)} violations")
            lines.append(df.head(10).to_string())
        if len(self.stale):
            lines.append(f"STALE {len(self.stale)} merged series:")
            lines += ["  " + line for line in warehouse.describe_stale(self.stale)]
        lines.append("written" if self.written else
                     "NOT written: checks failed" if not self.ok else
                     "nothing to merge" if not self.changed else "dry run: not written")
        return "\n".join(lines)


def _fmt(d: dict[str, int]) -> str:
    return ", ".join(f"{k} (+{n})" for k, n in sorted(d.items()))


def _rows(df: pd.DataFrame) -> set[tuple]:
    return set(map(tuple, df[observations.COLUMNS].astype(str).to_numpy()))


def plan(base: pd.DataFrame, track: pd.DataFrame, rebuilt: list[str], series: list[str] | None = None,
         replace: list[str] | None = None) -> tuple[pd.DataFrame, list[str], Result]:
    """Merged table (pure), the merged series and the per-series classification."""
    rebuilt_set = set(rebuilt) | set(replace or [])
    candidates = set(track["series"]) | rebuilt_set
    if series:
        unknown = set(series) - candidates
        if unknown:
            raise SystemExit(f"not in the track's table or rebuilt list: {sorted(unknown)}")
        candidates = set(series)
    keys = sorted(candidates)
    track = track[track["series"].isin(keys)]
    in_base = set(base["series"])
    replace_set = {k for k in keys if k in rebuilt_set and k in in_base}
    merged = observations.combine(base, track, replace_set)
    res = Result(rows_before=len(base), rows_after=len(merged))
    for k in keys:
        t = track[track["series"] == k]
        if k not in in_base:
            if len(t):
                res.added[k] = len(t)
            else:
                res.unchanged.append(k)
        elif k in replace_set:
            b = base[base["series"] == k]
            if _rows(b) == _rows(t):
                res.unchanged.append(k)
            else:
                res.replaced[k] = (len(b), len(t))
        else:
            new = _rows(merged[merged["series"] == k]) - _rows(base[base["series"] == k])
            if new:
                res.updated[k] = len(new)
            else:
                res.unchanged.append(k)
    return merged, keys, res


def _backup(base_dir: Path) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder = base_dir / "merge_backups"
    folder.mkdir(exist_ok=True)
    for name in (TABLE, LOG):
        if (base_dir / name).exists():
            shutil.copy2(base_dir / name, folder / f"{stamp}_{name}")
    for old in sorted(folder.glob(f"*_{TABLE}"))[:-KEEP_BACKUPS]:
        old.unlink()
        (folder / old.name.replace(TABLE, LOG)).unlink(missing_ok=True)


def merge(track_dir: Path, base_dir: Path, series: list[str] | None = None, replace: list[str] | None = None,
          today=None, specs: list[catalog.Spec] | None = None, dry_run: bool = False) -> Result:
    """Merge `track_dir` into `base_dir` if the checks pass on the result (see module docstring)."""
    track_dir, base_dir = Path(track_dir), Path(base_dir)
    if track_dir.resolve() == base_dir.resolve():
        raise SystemExit(f"track and base are the same directory: {base_dir}")
    if not track_dir.is_dir():
        raise SystemExit(f"no such track data directory: {track_dir}")
    base_dir.mkdir(parents=True, exist_ok=True)
    with open(base_dir / ".merge.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # one merge at a time; readers are safe through the atomic rename
        base = observations.read_table(base_dir / TABLE)
        track = observations.read_table(track_dir / TABLE)
        rebuilt = observations.load_rebuilt(track_dir / TABLE)
        merged, keys, res = plan(base, track, rebuilt, series, replace)

        base_log = observations.read_log(base_dir / LOG)
        track_log = observations.read_log(track_dir / LOG)
        track_log = track_log[track_log["series"].isin(keys)]
        merged_log = observations.combine(base_log, track_log, key=observations.LOG_KEY)
        res.log_rows_added = len(merged_log) - len(base_log)

        con = warehouse.connect(merged, specs)
        res.failed = {name: df for name, df in warehouse.run_checks(con).items() if len(df)}
        stale = warehouse.fresh(con, today)
        res.stale = stale[stale["series"].isin(keys)].reset_index(drop=True)
        if res.ok and res.changed and not dry_run:
            _backup(base_dir)
            observations.write_parquet(merged, base_dir / TABLE)
            observations.write_parquet(merged_log, base_dir / LOG)
            res.written = True
    return res


def default_base() -> Path:
    shared = config.get(observations.SHARED_ENV)
    return Path(shared).expanduser() if shared else config.REPO / "data"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ai_tracker.datamerge", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("track_data_dir", type=Path)
    ap.add_argument("--into", type=Path, default=None, help="base data dir (default AI_TRACKER_SHARED_DATA, "
                                                            "else data/ of this checkout)")
    ap.add_argument("--series", nargs="+", default=None, help="merge only these series")
    ap.add_argument("--replace", nargs="+", default=None,
                    help="also replace these series in the base (a rebuild made without rebuilt_series.json)")
    ap.add_argument("--today", default=None, help="date for the freshness check (default: today UTC)")
    ap.add_argument("--dry-run", action="store_true", help="classify and check, write nothing")
    a = ap.parse_args(argv)
    base_dir = a.into or default_base()
    print(f"merge {a.track_data_dir} -> {base_dir}")
    res = merge(a.track_data_dir, base_dir, a.series, a.replace, a.today, dry_run=a.dry_run)
    print(res.summary())
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
