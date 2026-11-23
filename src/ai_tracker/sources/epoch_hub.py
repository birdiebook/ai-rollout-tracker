"""Epoch AI data hub: benchmark runs, ECI, notable-models database, ML hardware.

Licence (README in every Epoch ZIP, checked in phase 1): "Epoch AI's data is free to use, distribute, and
reproduce provided the source and authors are credited under the Creative Commons Attribution license"
(CC BY 4.0).

known_from rules (docs/mattregister.md, 2026-11-23; docs/kallor/epoch_arxiv.md):
- Benchmark runs by Epoch itself: per run `Started at`. A monthly frontier for month m uses only runs
  started before the end of m and gets known_from = first day of m+1 (release-dated rows).
- ECI and the models database are re-estimated and back-filled, so their history is source="backfill";
  only our own weekly snapshots get a real known_from (handled by observations.new_rows).
- Hardware: release date of the spec, but prices are added later: backfill, revised.

Pure functions (parsers and derivations) take DataFrames so they can be tested without the network.
"""

from __future__ import annotations

import io
import zipfile
from datetime import date
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from ai_tracker import config, http

BASE = "https://epoch.ai/data/"
SOURCE = "epoch"
LICENSE = ("CC BY 4.0 (Epoch AI README: \"free to use, distribute, and reproduce provided the source and "
           "authors are credited\")")
RUNS_LEDGER = config.REPO / "data" / "epoch" / "benchmark_runs.parquet"
SCORE_COLUMN = "Best score (across scorers)"

# ------------------------------------------------------------------ download


@lru_cache(maxsize=None)
def _zip_bytes(name: str) -> bytes:
    return http.get(BASE + name, SOURCE).content  # raw copy saved under data/raw/epoch/<date>/


def read_zip(content: bytes) -> dict[str, bytes]:
    """{path inside zip: bytes} for every CSV/JSON file."""
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        return {n: z.read(n) for n in z.namelist() if n.endswith((".csv", ".json"))}


def _csv(files: dict[str, bytes], name: str) -> pd.DataFrame:
    match = [k for k in files if k == name or k.endswith("/" + name)]
    if not match:
        raise KeyError(f"{name} not in zip")
    return pd.read_csv(io.BytesIO(files[match[0]]))


def benchmark_files() -> dict[str, bytes]:
    return read_zip(_zip_bytes("benchmark_data.zip"))


def model_files() -> dict[str, bytes]:
    return read_zip(_zip_bytes("ai_models.zip"))


def hardware_files() -> dict[str, bytes]:
    return read_zip(_zip_bytes("ml_hardware.zip"))


# ------------------------------------------------------------------ benchmark runs


def epoch_runs(files: dict[str, bytes]) -> pd.DataFrame:
    """All Epoch-run results: benchmark (file stem), model, score, started_at (UTC).

    Epoch's own runs are the CSV files that are not `*_external.csv` and carry `Started at`. The score column
    and scale come from benchmark_metadata.csv where the file is listed there, else `Best score (across scorers)`.
    Rows without `Started at` or score are dropped (no honest known_from). One row per (benchmark, model):
    the best score and the start of that run.
    """
    meta = _csv(files, "benchmark_metadata.csv")
    meta = meta[meta["source_file"].notna()].set_index("source_file")
    frames = []
    for path, content in sorted(files.items()):
        name = Path(path).name
        if not name.endswith(".csv") or name.endswith("_external.csv"):
            continue
        if name in ("benchmark_metadata.csv", "model_metadata.csv") or "epoch_capabilities_index" in path:
            continue
        df = pd.read_csv(io.BytesIO(content))
        if "Started at" not in df.columns or "Model version" not in df.columns:
            continue
        col, scale = SCORE_COLUMN, 1.0
        if name in meta.index:
            col = meta.loc[name, "score_column"] if isinstance(meta.loc[name, "score_column"], str) else col
            scale = float(meta.loc[name, "scale"]) if pd.notna(meta.loc[name, "scale"]) else 1.0
        if col not in df.columns:
            continue
        out = pd.DataFrame({
            "benchmark": name.removesuffix(".csv"),
            "model": df["Model version"].astype(str),
            "score": pd.to_numeric(df[col], errors="coerce") * scale,
            "started_at": pd.to_datetime(df["Started at"], errors="coerce", utc=True, format="mixed"),
        }).dropna(subset=["score", "started_at"])
        frames.append(out)
    if not frames:
        return pd.DataFrame(columns=["benchmark", "model", "score", "started_at"])
    runs = pd.concat(frames, ignore_index=True)
    best = runs.sort_values(["score", "started_at"], ascending=[False, True])
    return best.drop_duplicates(["benchmark", "model"]).sort_values(["benchmark", "started_at"]).reset_index(drop=True)


def benchmark_stats(runs: pd.DataFrame, when) -> pd.DataFrame:
    """Per benchmark, using only runs started on or before `when`: n_models, frontier, last_run."""
    when = _utc(when)
    known = runs[runs["started_at"] <= when]
    g = known.groupby("benchmark")
    return pd.DataFrame({"n_models": g["model"].nunique(), "frontier": g["score"].max(),
                         "last_run": g["started_at"].max()})


def _ranked(stats: pd.DataFrame) -> pd.DataFrame:
    # most Epoch-run models first; ties broken by name so the ranking is deterministic
    return stats.reset_index().sort_values(["n_models", "benchmark"], ascending=[False, True]).set_index("benchmark")


SELECTION_DATE = "2026-11-23"
SELECT_N, SELECT_MAX_FRONTIER = 3, 0.80
REPLACE_ABOVE, SUCCESSOR_MAX_FRONTIER = 0.90, 0.70


def select_benchmarks(runs: pd.DataFrame, when=SELECTION_DATE, n: int = SELECT_N,
                      max_frontier: float = SELECT_MAX_FRONTIER) -> pd.DataFrame:
    """Registered rule (mattregister 2026-11-23): the n benchmarks with most Epoch-run models among those whose
    frontier on `when` is < max_frontier. Coverage only, never the development of the scores."""
    end_of_day = pd.Timestamp(when) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    stats = benchmark_stats(runs, end_of_day)
    return _ranked(stats[stats["frontier"] < max_frontier]).head(n)


def apply_successor_rule(selected: list[str], runs: pd.DataFrame, when, retired: list[str] | None = None
                         ) -> tuple[list[str], list[tuple[str, str]]]:
    """Successor rule: a selected benchmark whose frontier on `when` is > 0.90 is replaced by the next one in the
    same ranking (most Epoch-run models on `when`) among those with frontier < 0.70, not selected or retired before.
    Returns (new selection in the same slots, [(replaced, successor)])."""
    stats = benchmark_stats(runs, when)
    ranked = _ranked(stats)
    used = set(selected) | set(retired or [])
    out, swaps = list(selected), []
    for i, b in enumerate(selected):
        if b in stats.index and stats.loc[b, "frontier"] > REPLACE_ABOVE:
            pool = ranked[(ranked["frontier"] < SUCCESSOR_MAX_FRONTIER) & ~ranked.index.isin(list(used))]
            if pool.empty:
                continue  # no eligible successor: keep it, and report it
            succ = pool.index[0]
            out[i] = succ
            used.add(succ)
            swaps.append((b, succ))
    return out, swaps


def _utc(when) -> pd.Timestamp:
    t = pd.Timestamp(when)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def monthly_frontier(runs: pd.DataFrame, last_month: pd.Period) -> pd.DataFrame:
    """As-of-correct monthly frontier for one benchmark's runs (columns score, started_at).

    For month m: frontier = best score among runs started before the end of m (runs started later do not
    count, even if their model was released earlier); runs = number of runs started in m.
    Rows from the first month with a run to `last_month` (inclusive; pass only complete months).
    """
    if runs.empty:
        return pd.DataFrame(columns=["frontier", "runs"])
    started = runs["started_at"].dt.tz_convert("UTC").dt.tz_localize(None)
    months = pd.period_range(started.min().to_period("M"), last_month, freq="M")
    run_month = started.dt.to_period("M")
    rows = []
    for m in months:
        end = m.end_time  # last instant of the month
        rows.append((m, runs.loc[(started <= end).to_numpy(), "score"].max(), int((run_month == m).sum())))
    out = pd.DataFrame(rows, columns=["period", "frontier", "runs"]).set_index("period")
    out.index = pd.PeriodIndex(out.index, freq="M")
    return out


def release_frame(values: pd.Series, lag_days: int = 1) -> pd.DataFrame:
    """Monthly values -> release-dated rows with known_from = period end + lag_days."""
    kf = pd.DatetimeIndex(values.index.end_time.normalize()) + pd.Timedelta(days=lag_days)
    return pd.DataFrame({"period": [str(p) for p in values.index], "value": values.to_numpy(dtype=float),
                         "known_from": kf})


def with_revisions(frame: pd.DataFrame, key: str, table: pd.DataFrame | None = None,
                   today: date | None = None) -> pd.DataFrame:
    """Release-dated rows plus a revision row (known_from = today) for every period whose newest computed value
    differs from the newest stored one while that computed row's (period, known_from) is already stored.

    observations.new_rows only adds unseen (period, known_from) pairs, so without this a changed source value
    (a re-run that replaces an earlier one, a late-published run with an old `Started at`) would be dropped.
    """
    if table is None:
        from ai_tracker import observations  # lazy: observations -> catalog -> series -> this module

        table = observations.load()
    stored = table[table["series"] == key]
    if stored.empty or frame.empty:
        return frame
    today_ts = pd.Timestamp(today or date.today())
    latest_stored = stored.sort_values("known_from").groupby("period")["value"].last()
    seen = set(zip(stored["period"], pd.to_datetime(stored["known_from"])))
    newest = frame.sort_values("known_from").groupby("period").tail(1)
    extra = []
    for p, v, kf in newest[["period", "value", "known_from"]].itertuples(index=False):
        if p in latest_stored.index and (p, pd.Timestamp(kf)) in seen and \
                not np.isclose(latest_stored[p], v, rtol=0, atol=1e-12) and pd.Timestamp(kf) <= today_ts:
            extra.append((p, float(v), today_ts))
    if not extra:
        return frame
    return pd.concat([frame, pd.DataFrame(extra, columns=["period", "value", "known_from"])], ignore_index=True)


def last_complete_month(today: date | None = None) -> pd.Period:
    return pd.Period(pd.Timestamp(today or date.today()), freq="M") - 1


def update_runs_ledger(runs: pd.DataFrame, today: date | None = None, path: Path | None = None) -> pd.DataFrame:
    """Keep (benchmark, model, started_at, score, first_seen): measures Epoch's real publication delay later."""
    path = path or RUNS_LEDGER
    today_ts = pd.Timestamp(today or date.today())
    new = runs.assign(first_seen=today_ts)
    if path.exists():
        old = pd.read_parquet(path)
        keys = ["benchmark", "model", "started_at", "score"]
        merged = new.merge(old[keys + ["first_seen"]], on=keys, how="left", suffixes=("", "_old"))
        new["first_seen"] = merged["first_seen_old"].fillna(merged["first_seen"]).to_numpy()
        gone = old.merge(new[keys], on=keys, how="left", indicator=True)
        new = pd.concat([old[gone["_merge"].eq("left_only").to_numpy()], new], ignore_index=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    new.to_parquet(path, index=False)
    return new


@lru_cache(maxsize=None)
def _runs() -> pd.DataFrame:
    runs = epoch_runs(benchmark_files())
    update_runs_ledger(runs)
    return runs


def benchmark_series(benchmark: str, column: str, key: str) -> pd.DataFrame:
    """Fetch function body for g1_epoch_bench_* series."""
    runs = _runs()
    mf = monthly_frontier(runs[runs["benchmark"] == benchmark], last_complete_month())
    if mf.empty:
        raise RuntimeError(f"no Epoch runs for {benchmark}")
    return with_revisions(release_frame(mf[column].astype(float), lag_days=1), key)


# ------------------------------------------------------------------ ECI and models database


def eci_scores(files: dict[str, bytes]) -> pd.DataFrame:
    df = _csv(files, "eci_scores.csv")
    return pd.DataFrame({"model": df["Model"], "eci": pd.to_numeric(df["eci"], errors="coerce"),
                         "date": pd.to_datetime(df["date"], errors="coerce")}).dropna()


def frontier_by_date(dates: pd.Series, values: pd.Series, periods: pd.PeriodIndex) -> pd.Series:
    """Highest value among items dated on or before each period's end (carry-forward max)."""
    d = pd.to_datetime(dates)
    v = pd.to_numeric(values, errors="coerce")
    ok = d.notna() & v.notna()
    d, v = d[ok], v[ok]
    out = [v[d <= p.end_time].max() if (d <= p.end_time).any() else np.nan for p in periods]
    return pd.Series(out, index=periods, dtype=float)


def complete_periods(first: pd.Timestamp, freq: str, today: date | None = None) -> pd.PeriodIndex:
    """Periods from the one containing `first` to the last one that has ended before today."""
    from ai_tracker.catalog import FREQS

    alias = FREQS[freq]
    last = pd.Period(pd.Timestamp(today or date.today()), freq=alias) - 1
    return pd.period_range(pd.Period(first, freq=alias), last, freq=alias)


def eci_frontier(files: dict[str, bytes], today: date | None = None) -> pd.Series:
    e = eci_scores(files)
    periods = complete_periods(e["date"].min(), "W", today)
    return frontier_by_date(e["date"], e["eci"], periods)


def models_frame(files: dict[str, bytes], name: str) -> pd.DataFrame:
    df = _csv(files, name)
    df["Publication date"] = pd.to_datetime(df["Publication date"], errors="coerce")
    return df.dropna(subset=["Publication date"])


MODELS_START = "2010-01"
OPEN_SHARE_START = "2015Q1"


def notable_per_month(notable: pd.DataFrame, today: date | None = None, start: str = MODELS_START) -> pd.Series:
    """Number of notable models by publication month (zeros are real zeros), complete months only."""
    periods = complete_periods(pd.Timestamp(start), "M", today)
    counts = notable["Publication date"].dt.to_period("M").value_counts()
    return pd.Series([int(counts.get(p, 0)) for p in periods], index=periods, dtype=float)


def open_weights_share(notable: pd.DataFrame, today: date | None = None, start: str = OPEN_SHARE_START) -> pd.Series:
    """Share of notable models with open weights per publication quarter, among models where Epoch states it
    (`Open model weights?` Yes/No; blank is excluded). Complete quarters only."""
    periods = complete_periods(pd.Period(start, freq="Q-DEC").start_time, "Q", today)
    flag = notable["Open model weights?"].map({"Yes": 1.0, "No": 0.0})
    q = notable["Publication date"].dt.to_period("Q-DEC")
    share = flag.groupby(q).mean()
    return pd.Series([share.get(p, np.nan) for p in periods], index=periods, dtype=float)


def train_compute_frontier(models: pd.DataFrame, today: date | None = None, start: str = MODELS_START) -> pd.Series:
    """Largest training compute (FLOP) among all models published up to each month end."""
    periods = complete_periods(pd.Timestamp(start), "M", today)
    return frontier_by_date(models["Publication date"], models["Training compute (FLOP)"], periods)


# ------------------------------------------------------------------ hardware


HW_START = "2016"


def hw_price_performance(hw: pd.DataFrame, today: date | None = None, start: str = HW_START) -> pd.Series:
    """Best 16-bit FLOP/s per release-price USD among accelerators released up to each year end.

    16-bit = `Tensor-FP16/BF16 performance (FLOP/s)`, else `FP16 (half precision) performance (FLOP/s)`.
    Epoch's own `Price-performance` column uses the fastest precision (FP32 -> FP8/FP4 over time), which mixes
    precisions; we keep one precision. Before 2016 too few accelerators have both a 16-bit figure and a price.
    """
    perf = pd.to_numeric(hw["Tensor-FP16/BF16 performance (FLOP/s)"], errors="coerce").fillna(
        pd.to_numeric(hw["FP16 (half precision) performance (FLOP/s)"], errors="coerce"))
    pp = perf / pd.to_numeric(hw["Release price (USD)"], errors="coerce")
    periods = complete_periods(pd.Timestamp(f"{start}-01-01"), "A", today)
    return frontier_by_date(hw["Release date"], pp, periods)
