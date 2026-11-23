"""Versioned observations: (series, freq, period, value, known_from, source, fetched_at).

A backtest or a monthly snapshot must only see what was known on its date. `as_of(series, date)`
returns exactly that. Pattern from kpif-nowcast, generalised to mixed frequencies (D/W/M/Q/A) and to
release-dated sources.

How known_from is set:
- Release-dated rows (fetch returns a DataFrame with known_from, e.g. SEC filings): the source's own
  date. Every filing is its own vintage, so revisions are real vintages from day one. source="release".
- Lag-based, first load (backfill): period end + publication lag (publication.py). Values are today's
  vintage, so revisions leak into the backfill. source="backfill".
- Lag-based, later fetches: a new period gets min(period end + lag, fetch date); a changed value
  (revision) gets known_from = fetch date. source="fetch" / "revision".
- Never before a fetch that did not have it: a lag-dated period (also "backfill" rows in a release-dated
  frame) that is new to the table was absent from every earlier successful fetch of the series, so its
  known_from is at least the day after the latest such fetch (capped at today's fetch date). This keeps a
  delayed release that is missing from publication.LATE_RELEASES (the next shutdown) from being back-dated
  to the lag rule. Earlier fetches are read from the fetch log (data/fetch_log.parquet: series, fetched_at,
  n_periods, last_period, rows_added; one row per successful fetch, also when nothing new arrived) and from
  the table's own fetched_at. Document-dated rows (SEC filing dates etc.) keep their document date.

as_of convention: `as_of(series, when)` includes rows with known_from == when. A forecast origin (a date at
midnight) means the end of that day, and a value released on a day counts as known on that day. Sources
whose known_from has a time of day (none since the Indeed +1 day margin) are known from that instant.

Storage: data/observations.parquet and data/fetch_log.parquet (not committed, rebuilt by
`python -m ai_tracker.observations`).

Shared base (parallel agent tracks, docs/drift.md "Delad data"). With AI_TRACKER_SHARED_DATA set (environment,
.env.local or .env; see config.get) to a directory holding a base observations.parquet + fetch_log.parquet, the
default table becomes a two-layer view:
- load() / load_log() return base ∪ track. On an identical (series, period, known_from) the track row wins; in
  the fetch log, on an identical (series, fetched_at).
- Writes (save via upsert, append_log, drop_series) go only to the track's own data/ files; the base is read-only.
- drop_series (a rebuild) cannot delete base rows, so it records the keys in data/rebuilt_series.json and the
  view hides the base's rows of those series. `python -m ai_tracker.datamerge` then replaces them in the base.
The base is layered only under the default table: with no `path` argument and PATH unchanged. An explicit path,
or PATH set by a `--table` option, reads that file alone. Unset (default): one table, as before.
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from ai_tracker import catalog, config, publication

DEFAULT_PATH = config.REPO / "data" / "observations.parquet"
PATH = DEFAULT_PATH
COLUMNS = ["series", "freq", "period", "value", "known_from", "source", "fetched_at"]
LOG_COLUMNS = ["series", "fetched_at", "n_periods", "last_period", "rows_added"]
KEY = ["series", "period", "known_from"]
LOG_KEY = ["series", "fetched_at"]
SHARED_ENV = "AI_TRACKER_SHARED_DATA"


def _shared_dir() -> Path | None:
    value = config.get(SHARED_ENV)
    return Path(value).expanduser() if value else None


# Directory of the read-only base table (None = no shared base). Resolved once at import.
SHARED_DIR: Path | None = _shared_dir()


def base_path() -> Path | None:
    """The shared base table under the default table, or None (unset, PATH changed, or the base is PATH itself)."""
    if SHARED_DIR is None or PATH != DEFAULT_PATH:
        return None
    base = SHARED_DIR / "observations.parquet"
    try:
        if base.resolve() == PATH.resolve():
            return None
    except OSError:
        pass
    return base


def rebuilt_path(path: Path | None = None) -> Path:
    """Series whose base rows the track hides (rebuilt in the track), next to the track table."""
    return (path or PATH).with_name("rebuilt_series.json")


def load_rebuilt(path: Path | None = None) -> list[str]:
    p = rebuilt_path(path)
    return sorted(json.loads(p.read_text(encoding="utf-8"))) if p.exists() else []


def _add_rebuilt(keys: list[str], path: Path | None = None) -> None:
    keys = sorted(set(load_rebuilt(path)) | set(keys))
    p = rebuilt_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(keys, indent=1) + "\n", encoding="utf-8")


def combine(base: pd.DataFrame, track: pd.DataFrame, hide: list[str] | set[str] = (),
            key: list[str] = KEY) -> pd.DataFrame:
    """base ∪ track: base rows of `hide` are dropped, and on an identical `key` the track row wins."""
    base = base[~base["series"].isin(list(hide))]
    if track.empty:
        return base.reset_index(drop=True)
    if base.empty:
        return track.reset_index(drop=True)
    # Only base rows that the track overrides go; duplicates inside one layer are left as they are (the fetch
    # log has one row per fetch call, so two calls on one day are two rows).
    won = pd.MultiIndex.from_frame(track[key].astype(str))
    base = base[~pd.MultiIndex.from_frame(base[key].astype(str)).isin(won)]
    return pd.concat([base, track[base.columns]], ignore_index=True)


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="datetime64[ns]" if c in ("known_from", "fetched_at") else
                                      float if c == "value" else object) for c in COLUMNS})


def read_table(path: Path) -> pd.DataFrame:
    """One parquet file as an observation table (empty if missing), without any shared base."""
    if not path.exists():
        return _empty()
    df = pd.read_parquet(path)
    for c in ("known_from", "fetched_at"):
        df[c] = pd.to_datetime(df[c])
    return df


def load(path: Path | None = None) -> pd.DataFrame:
    """The table at `path`; with no `path`, the default table, layered over the shared base if one is set."""
    track = read_table(path or PATH)
    base = base_path() if path is None else None
    if base is None:
        return track
    return combine(read_table(base), track, load_rebuilt())


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    """Atomic write (temp file + rename): a reader in another worktree sees the old or the new file, never half."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    df.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def save(df: pd.DataFrame, path: Path | None = None) -> None:
    """Write the track table (never the shared base)."""
    write_parquet(df, path or PATH)


def log_path(path: Path | None = None) -> Path:
    """The fetch log lives next to the observation table."""
    return (path or PATH).with_name("fetch_log.parquet")


def read_log(p: Path) -> pd.DataFrame:
    """One fetch-log file (empty if missing), without any shared base."""
    if not p.exists():
        return pd.DataFrame({c: pd.Series(dtype="datetime64[ns]" if c == "fetched_at" else
                                          "int64" if c in ("n_periods", "rows_added") else object)
                             for c in LOG_COLUMNS})
    df = pd.read_parquet(p)
    df["fetched_at"] = pd.to_datetime(df["fetched_at"])
    return df


def load_log(path: Path | None = None) -> pd.DataFrame:
    """Fetch log for the table at `path` (empty if none); with no `path`, base ∪ track like load()."""
    track = read_log(log_path(path))
    base = base_path() if path is None else None
    if base is None:
        return track
    return combine(read_log(log_path(base)), track, key=LOG_KEY)


def append_log(entries: pd.DataFrame, path: Path | None = None) -> None:
    """Append to the track's own fetch log (never the shared base's)."""
    if entries.empty:
        return
    p = log_path(path)
    old = read_log(p)
    out = entries[LOG_COLUMNS] if old.empty else pd.concat([old, entries[LOG_COLUMNS]], ignore_index=True)
    write_parquet(out, p)


def absent_fetches(spec: catalog.Spec, table: pd.DataFrame, log: pd.DataFrame | None = None):
    """Function period -> dates of earlier successful fetches of `spec` that provably did not contain that
    period (only asked for periods not in the table).

    - Fetch dates in the table's fetched_at: every value such a fetch returned is stored, so a period that is
      not in the table was not in it.
    - Fetch log entries: the stored rows may be gone (drop_series before a rebuild), so only a fetch whose
      newest period is before the period counts. A late-filled hole inside the range is not caught.
    """
    in_table = pd.to_datetime(table.loc[table["series"] == spec.key, "fetched_at"]).unique()
    logged = log[log["series"] == spec.key].dropna(subset=["last_period"]) if log is not None and len(log) \
        else None
    if logged is not None and len(logged):
        last = to_periods(logged["last_period"], spec.freq)
        log_dates = pd.to_datetime(logged["fetched_at"]).to_numpy()
    else:
        last, log_dates = None, None

    def dates(period: str) -> pd.DatetimeIndex:
        out = list(in_table)
        if last is not None:
            p = to_periods([period], spec.freq)[0]
            out += list(log_dates[np.asarray(last < p)])
        return pd.DatetimeIndex(sorted(set(out)))
    return dates


def not_before_absent_fetch(kf: pd.Timestamp, earlier: pd.DatetimeIndex, fetched: pd.Timestamp) -> pd.Timestamp:
    """known_from of a period new to the table: after every earlier fetch that did not contain it, and never
    after today's fetch that does."""
    prior = earlier[earlier < fetched]
    if len(prior):
        kf = max(kf, prior.max() + pd.Timedelta(days=1))
    return min(kf, fetched)


def to_periods(index, freq: str) -> pd.PeriodIndex:
    return pd.PeriodIndex(index, freq=catalog.FREQS[freq])


def fortnight_ordinal(periods: pd.PeriodIndex) -> np.ndarray:
    """Consecutive number of the ISO fortnight that ends in each W-SUN week.

    Fortnight n of an ISO year covers ISO weeks 2n-1 and 2n; in 53-week years fortnight 26 also takes
    week 53 (21 days). The fortnight is read from the week before the end week, so both cases map right.
    """
    iso = (pd.DatetimeIndex(periods.start_time) - pd.Timedelta(days=7)).isocalendar()
    fortnight = np.minimum((iso["week"].to_numpy(dtype="int64") - 1) // 2 + 1, 26)
    return iso["year"].to_numpy(dtype="int64") * 26 + fortnight - 1


def new_rows(spec: catalog.Spec, values: pd.Series | pd.DataFrame, table: pd.DataFrame,
             fetched_at: date | None = None, log: pd.DataFrame | None = None) -> pd.DataFrame:
    """Rows to append for one fetched vintage of `spec` (pure: does not read or write files).

    `log` is the fetch log (load_log); earlier fetches without a period bound its known_from from below.
    """
    fetched = pd.Timestamp(fetched_at or date.today())
    existing = table[table["series"] == spec.key]
    latest = existing.sort_values("known_from").groupby("period")["value"].last()
    absent = absent_fetches(spec, table, log)
    rows = []

    if isinstance(values, pd.DataFrame):  # release-dated: each row is a vintage with its own date
        df = values.dropna(subset=["value"]).copy()
        df["period"] = [str(p) for p in to_periods(df["period"], spec.freq)]
        df["known_from"] = pd.to_datetime(df["known_from"])
        if "source" not in df:  # optional column, e.g. "backfill" for rows dated by lag rather than a document
            df["source"] = "release"
        stored = set(zip(existing["period"], pd.to_datetime(existing["known_from"])))
        seen = set(stored)
        newest = df.sort_values("known_from").groupby("period").tail(1)
        cols = ["period", "value", "known_from", "source"]
        for p, v, kf, src in df.sort_values("known_from")[cols].itertuples(index=False):
            if (p, kf) not in seen:
                if src == "backfill":  # rule-dated, not a document date
                    if p in latest.index:  # stored earlier, possibly under a later (guarded) date
                        if not np.isclose(latest[p], v, rtol=0, atol=1e-9):
                            rows.append((spec.key, spec.freq, p, float(v), fetched, "revision", fetched))
                        seen.add((p, kf))
                        continue
                    if len(earlier := absent(p)):
                        kf = not_before_absent_fetch(kf, earlier, fetched)
                rows.append((spec.key, spec.freq, p, float(v), kf, src, fetched))
                seen.add((p, kf))
        # Same release date, new value (the source overwrote its file, e.g. a reweighting): a revision
        # that is known from the fetch date, never back-dated to the release.
        for p, v, kf in newest[["period", "value", "known_from"]].itertuples(index=False):
            if (p, kf) in stored and not np.isclose(latest[p], v, rtol=0, atol=1e-9):
                rows.append((spec.key, spec.freq, p, float(v), fetched, "revision", fetched))
        return pd.DataFrame(rows, columns=COLUMNS)

    values = values.dropna().sort_index()
    periods = to_periods(values.index, spec.freq)
    default_kf = publication.known_from(spec.key, periods, spec.lag_days)
    is_backfill = existing.empty
    for p, v, kf in zip(periods, values.to_numpy(), default_kf):
        key = str(p)
        if key not in latest.index:
            if len(earlier := absent(key)):
                kf = not_before_absent_fetch(kf, earlier, fetched)
            elif not is_backfill:
                kf = min(kf, fetched)
            rows.append((spec.key, spec.freq, key, float(v), kf,
                         "backfill" if is_backfill else "fetch", fetched))
        elif not np.isclose(latest[key], v, rtol=0, atol=1e-9):
            rows.append((spec.key, spec.freq, key, float(v), fetched, "revision", fetched))
    return pd.DataFrame(rows, columns=COLUMNS)


def vintage_rows(wide: pd.DataFrame) -> pd.DataFrame:
    """Wide vintages (index observation date, one column per release date) -> release-dated rows.

    Columns period, value, known_from: a row whenever a release adds or changes a value. A value that a
    later release drops keeps its last published value (nothing is deleted).
    """
    rows = []
    prev = pd.Series(np.nan, index=wide.index)
    for vdate in sorted(wide.columns):
        cur = wide[vdate]
        changed = cur.notna() & (prev.isna() | ~np.isclose(cur.fillna(0), prev.fillna(0), rtol=0, atol=1e-9))
        rows += [(obs, cur[obs], vdate) for obs in cur.index[changed]]
        prev = cur.where(cur.notna(), prev)
    return pd.DataFrame(rows, columns=["period", "value", "known_from"])


def drop_series(keys: list[str], path: Path | None = None) -> int:
    """Remove every stored row of `keys` (e.g. after a source switch or a rebuild). Returns rows removed.

    The fetch dates of the dropped rows stay in the fetch log: a rebuild must not forget that an earlier
    fetch did not contain a period.

    Over a shared base the base is not touched: the track's rows are removed, the keys are recorded in
    rebuilt_series.json (the view hides the base's rows), and the count includes the hidden base rows.
    """
    shared = path is None and base_path() is not None
    view = load(path)
    dropped = view[view["series"].isin(keys)]
    if len(dropped):
        log = load_log(path)
        logged = set(zip(log["series"], log["fetched_at"]))
        seen = (dropped.groupby(["series", "fetched_at"])["period"].agg(["nunique", "max"]).reset_index())
        missing = seen[[(s, f) not in logged for s, f in zip(seen["series"], seen["fetched_at"])]]
        append_log(pd.DataFrame({"series": missing["series"], "fetched_at": missing["fetched_at"],
                                 "n_periods": missing["nunique"].astype("int64"), "last_period": missing["max"],
                                 "rows_added": 0}), path)
        track = read_table(path or PATH)
        save(track[~track["series"].isin(keys)].reset_index(drop=True), path)
        if shared:
            _add_rebuilt(sorted(set(dropped["series"])), path)
    return len(dropped)


def upsert(spec: catalog.Spec, values: pd.Series | pd.DataFrame, fetched_at: date | None = None,
           path: Path | None = None) -> int:
    """Append a fetched vintage to the stored table and log the fetch (also when nothing is new). Returns rows
    added."""
    fetched = pd.Timestamp(fetched_at or date.today())
    table = load(path)  # the view (base ∪ track): new rows are new relative to everything known
    new = new_rows(spec, values, table, fetched, load_log(path))
    if len(new):
        track = read_table(path or PATH)  # only the track file is written
        save(new if track.empty else pd.concat([track, new], ignore_index=True), path)
    periods = values["period"] if isinstance(values, pd.DataFrame) else values.dropna().index
    periods = [str(p) for p in to_periods(periods, spec.freq)] if len(periods) else []
    append_log(pd.DataFrame({"series": [spec.key], "fetched_at": [fetched], "n_periods": [len(set(periods))],
                             "last_period": [max(periods) if periods else None], "rows_added": [len(new)]}), path)
    return len(new)


def as_of(series: str, when: pd.Timestamp | str, table: pd.DataFrame | None = None) -> pd.Series:
    """Values of `series` as known on `when` (latest vintage with known_from <= when), on a PeriodIndex."""
    table = load() if table is None else table
    t = table[(table["series"] == series) & (table["known_from"] <= pd.Timestamp(when))]
    if t.empty:
        return pd.Series(dtype=float, name=series)
    s = t.sort_values("known_from").groupby("period")["value"].last()
    s.index = to_periods(s.index, t["freq"].iloc[0])
    return s.sort_index().rename(series)


def refresh(keys: list[str] | None = None) -> dict[str, str]:
    """Fetch every catalog series (or `keys`). One failing source doesn't stop the rest."""
    status = {}
    for spec in catalog.ALL:
        if keys and spec.key not in keys:
            continue
        try:
            n = upsert(spec, spec.fetch())
            status[spec.key] = f"ok +{n}"
        except Exception as exc:  # noqa: BLE001 - report and continue
            status[spec.key] = f"FAILED: {type(exc).__name__}: {str(exc)[:120]}"
        print(f"{spec.key:32s} {status[spec.key]}")
    return status


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    if args[:1] == ["--rebuild"]:  # drop stored rows of the given keys, then fetch them anew
        if not args[1:]:
            sys.exit("--rebuild needs series keys")
        print(f"dropped {drop_series(args[1:])} rows")
        args = args[1:]
    refresh(args or None)
