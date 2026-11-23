"""PyPI downloads per day and project from BigQuery (bigquery-public-data.pypi.file_downloads), track B1.

The table is partitioned by DATE(timestamp) and clustered by file.project. Queries read only the columns
`timestamp` and `file.project`, only the partitions of the days asked for, and return aggregate counts per
(day, project): a public CC BY 4.0 dataset (docs.pypi.org/api/bigquery), so the CSV may be a public artifact.

Cost (dry runs and a calibration 2026-11-23, docs/kallor/utvecklaradoption.md): the estimate already reflects
the clustering and equals the billed bytes, and every (project, day) costs at least one storage block (about
0.01-0.05 GB) however small the project. An exact daily history 2016 -> 2026-06 for the twelve projects is about
1.7 TB, far above the budget. So the backfill reads one fixed weekday per week (Wednesday, UTC), each AI project
from its first year: about 220 GB. Exact daily counts come for free from pypistats (sources/pypistats.py).

BigQuery only runs in GitHub Actions (keyless OIDC, sandbox quota of 1 TB/month shared by all tracks). Every
query is dry-run first; a run is refused when the estimate is above its cap, and maximum_bytes_billed is set
just above the estimate. Estimated, processed and billed bytes per query go to bytes.json next to the CSV.

Raw layout: RAW_DIR/pypi_bq/<fetch date>/<kind>_<start>_<end>.csv (+ bytes.json); kind "wed" covers the
Wednesdays in [start, end), kind "daily" every day. For each day the newest fetch that covered it wins.

    python -m ai_tracker.sources.pypi_bq dryrun   [--out DIR]   estimates only (free)
    python -m ai_tracker.sources.pypi_bq backfill [--out DIR]   Wednesdays 2016 -> about 25 weeks ago, per year
    python -m ai_tracker.sources.pypi_bq incremental            exact daily, new days or the last 3 weeks (manual;
                                                                about 15 GB a run: pypistats is the weekly source)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from ai_tracker import http

TABLE = "bigquery-public-data.pypi.file_downloads"
# file.project is the normalised project name (lower case, '-' separators) -> first year queried
FIRST_YEAR = {"openai": 2020, "anthropic": 2023, "google-generativeai": 2023, "google-genai": 2024, "langchain": 2022,
              "langchain-core": 2023, "transformers": 2019, "torch": 2018, "llama-index": 2023, "mcp": 2024,
              "requests": 2016, "numpy": 2016}
PROJECTS = list(FIRST_YEAR)
CONTROL = "requests"  # always downloaded: a day without a `requests` row is a gap in the table, not a zero
SAMPLE_WEEKDAY = 2  # Wednesday (Monday = 0)
BACKFILL_START = date(2016, 1, 1)
REREAD_DAYS = 21  # the incremental job re-reads the last three weeks (late-ingested rows become revisions)
# The backfill stops where pypistats' 180-day window (the free weekly refresh) still overlaps by about a week.
PYPISTATS_OVERLAP_DAYS = 173
# Byte caps (GB = 1e9 bytes), from the dry runs 2026-11-23 (docs/kallor/utvecklaradoption.md).
BACKFILL_MAX_GB = 240.0
INCREMENTAL_MAX_GB = 20.0
SOURCE_DIR = "pypi_bq"
_FILE = re.compile(r"(daily|wed)_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\.csv$")


@dataclass(frozen=True)
class Query:
    kind: str  # "wed" (Wednesdays only) or "daily"
    start: date
    end: date  # exclusive
    projects: tuple[str, ...]

    @property
    def days(self) -> list[date]:
        n = (self.end - self.start).days
        days = [self.start + timedelta(days=i) for i in range(n)]
        return [d for d in days if d.weekday() == SAMPLE_WEEKDAY] if self.kind == "wed" else days

    @property
    def filename(self) -> str:
        return f"{self.kind}_{self.start.isoformat()}_{self.end.isoformat()}.csv"

    def sql(self) -> str:
        return sql(self.start, self.end, list(self.projects), self.days if self.kind == "wed" else None)


def covered_days(kind: str, start: str, end: str) -> pd.DatetimeIndex:
    days = pd.date_range(start, pd.Timestamp(end) - pd.Timedelta(days=1), freq="D")
    return days[days.dayofweek == SAMPLE_WEEKDAY] if kind == "wed" else days


def sql(start: date, end: date, projects: list[str] | None = None, days: list[date] | None = None) -> str:
    """Downloads per (day, project) for days in [start, end) (or only `days`). Reads timestamp and file.project."""
    names = ", ".join(f"'{p}'" for p in (projects or PROJECTS))
    only = ""
    if days is not None:
        only = "  AND DATE(timestamp) IN (" + ", ".join(f"'{d.isoformat()}'" for d in days) + ")\n"
    return (
        "-- PyPI downloads per day and project (aggregates of a public CC BY 4.0 dataset)\n"
        "SELECT DATE(timestamp) AS day, file.project AS project, COUNT(*) AS downloads\n"
        f"FROM `{TABLE}`\n"
        f"WHERE timestamp >= TIMESTAMP('{start.isoformat()}') AND timestamp < TIMESTAMP('{end.isoformat()}')\n"
        f"{only}"
        f"  AND file.project IN ({names})\n"
        "GROUP BY day, project\nORDER BY day, project\n")


def year_chunks(start: date, end: date) -> list[tuple[date, date]]:
    """[start, end) split at 1 January: one query per calendar year keeps each job small and capped."""
    out, cur = [], start
    while cur < end:
        nxt = min(date(cur.year + 1, 1, 1), end)
        out.append((cur, nxt))
        cur = nxt
    return out


def last_monday(today: date) -> date:
    """Monday of the current week: queries end at the last complete W-SUN week."""
    return today - timedelta(days=today.weekday())


def backfill_end(today: date) -> date:
    """A Monday about 25 weeks back: pypistats (180 days) covers everything after it, with a few days of overlap."""
    return last_monday(today - timedelta(days=PYPISTATS_OVERLAP_DAYS))


def backfill_queries(today: date) -> list[Query]:
    """Wednesdays, one query per year, with the projects whose first year has come."""
    return [Query("wed", s, e, tuple(p for p in PROJECTS if FIRST_YEAR[p] <= s.year))
            for s, e in year_chunks(BACKFILL_START, backfill_end(today))]


# ------------------------------------------------------------------ bq CLI (Actions only)


def _project() -> str:
    p = os.environ.get("GCP_PROJECT_ID") or os.environ.get("CLOUDSDK_CORE_PROJECT")
    if not p:
        raise RuntimeError("GCP_PROJECT_ID is not set: BigQuery jobs run in GitHub Actions only")
    return p


def _bq(args: list[str], stdin: str | None = None) -> str:
    r = subprocess.run(["bq", "--headless", f"--project_id={_project()}", *args], input=stdin, text=True,
                       capture_output=True, check=False)
    if r.returncode:
        raise RuntimeError(f"bq {args[0]} failed ({r.returncode}): {(r.stderr or r.stdout)[-800:]}")
    return r.stdout


def dry_run_bytes(query: str) -> int:
    out = _bq(["query", "--use_legacy_sql=false", "--dry_run", "--format=json"], query)
    return int(json.loads(out)["statistics"]["totalBytesProcessed"])


def run_query(query: str, max_bytes: int) -> tuple[str, dict]:
    """Run with a hard cap; returns (CSV text, byte statistics of the finished job)."""
    job_id = f"b1_pypi_{uuid.uuid4().hex[:16]}"
    csv = _bq([f"--job_id={job_id}", "query", "--use_legacy_sql=false", "--format=csv", "--max_rows=10000000",
               f"--maximum_bytes_billed={max_bytes}"], query)
    stats: dict = {"job_id": job_id}
    try:
        job = json.loads(_bq(["--location=US", "--format=json", "show", "-j", job_id]))
        st = job.get("statistics", {})
        stats["processed"] = int(st.get("totalBytesProcessed", 0))
        stats["billed"] = int(st.get("query", {}).get("totalBytesBilled", 0))
    except Exception as exc:  # noqa: BLE001 - statistics are a record, not a reason to lose the result
        stats["stats_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
    return _csv_body(csv), stats


def _csv_body(text: str) -> str:
    """bq may print status lines before the CSV: keep from the header on."""
    i = text.find("day,project,downloads")
    if i < 0:
        raise RuntimeError(f"no CSV header in bq output: {text[:300]!r}")
    return text[i:]


# ------------------------------------------------------------------ jobs


def _gb(n: int | float | None) -> float | None:
    return None if n is None else round(n / 1e9, 3)


def _record(q: Query) -> dict:
    return {"kind": q.kind, "start": q.start.isoformat(), "end": q.end.isoformat(), "projects": list(q.projects),
            "days": len(q.days)}


def plan(queries: list[Query]) -> list[dict]:
    """Dry-run every query (free). One record per query with the estimate."""
    return [dict(_record(q), estimated=dry_run_bytes(q.sql())) for q in queries]


def execute(queries: list[Query], out_dir: Path, cap_gb: float) -> list[dict]:
    """Dry-run all queries, refuse if the total estimate is above `cap_gb`, then run each with its own cap."""
    out_dir.mkdir(parents=True, exist_ok=True)
    records = plan(queries)
    total = sum(r["estimated"] for r in records)
    print(f"estimated total {_gb(total)} GB over {len(records)} queries (cap {cap_gb} GB)")
    if total > cap_gb * 1e9:
        _write_log(out_dir, records, refused=True)
        raise RuntimeError(f"estimate {_gb(total)} GB above cap {cap_gb} GB: refusing")
    for q, r in zip(queries, records):
        cap = int(r["estimated"] * 1.05) + 50_000_000  # billed = estimate in the calibration; small margin
        body, stats = run_query(q.sql(), cap)
        (out_dir / q.filename).write_text(body, encoding="utf-8")
        r.update(stats, rows=body.count("\n") - 1)
        print(f"{q.filename}: estimated {_gb(r['estimated'])} GB, processed {_gb(r.get('processed'))} GB, "
              f"billed {_gb(r.get('billed'))} GB, {r['rows']} rows")
        _write_log(out_dir, records)  # after every query, so a later failure keeps the record
    return records


def _write_log(out_dir: Path, records: list[dict], refused: bool = False) -> None:
    log = {"table": TABLE, "refused": refused, "queries": records,
           "estimated_gb": _gb(sum(r["estimated"] for r in records)),
           "billed_gb": _gb(sum(r.get("billed", 0) for r in records))}
    (out_dir / "bytes.json").write_text(json.dumps(log, indent=1) + "\n", encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary and (refused or all("billed" in r or "stats_error" in r for r in records)):
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"PyPI BigQuery: estimated {log['estimated_gb']} GB, billed {log['billed_gb']} GB"
                    f"{' (REFUSED or dry run)' if refused else ''}\n\n")
            for r in records:
                f.write(f"- {r['kind']} {r['start']}..{r['end']}: est {_gb(r['estimated'])} GB, "
                        f"billed {_gb(r.get('billed'))} GB\n")


def dryrun(out_dir: Path, today: date | None = None) -> list[dict]:
    """Estimates only (free): the backfill per year and one exact incremental window."""
    today = today or date.today()
    end = last_monday(today)
    records = plan(backfill_queries(today) + [Query("daily", end - timedelta(days=7), end, tuple(PROJECTS))])
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_log(out_dir, records, refused=True)  # nothing ran
    for r in records:
        print(f"{r['kind']} {r['start']}..{r['end']} ({r['days']} days): estimated {_gb(r['estimated'])} GB")
    print(f"backfill total {_gb(sum(r['estimated'] for r in records[:-1]))} GB")
    return records


def backfill(out_dir: Path, today: date | None = None) -> list[dict]:
    return execute(backfill_queries(today or date.today()), out_dir, BACKFILL_MAX_GB)


def _files(root: Path, kinds: tuple[str, ...] = ("daily", "wed")) -> list[tuple[Path, re.Match]]:
    out = []
    for f in root.glob("*/*.csv"):
        m = _FILE.search(f.name)
        if m and m.group(1) in kinds:
            out.append((f, m))
    return sorted(out, key=lambda x: (x[0].parent.name, x[0].name))


def stored_days(root: Path, kinds: tuple[str, ...] = ("daily", "wed")) -> pd.DatetimeIndex:
    """Days covered by any stored query under `root` (RAW_DIR/pypi_bq)."""
    days = set()
    for _, m in _files(root, kinds):
        days.update(covered_days(*m.groups()))
    return pd.DatetimeIndex(sorted(days))


def incremental_window(root: Path, today: date) -> tuple[date, date] | None:
    """[start, end) for an exact daily run: the last REREAD_DAYS days, or from the day after the last stored
    exact day if that is earlier (a hole is filled)."""
    end = last_monday(today)
    start = end - timedelta(days=REREAD_DAYS)
    days = stored_days(root, ("daily",))
    if len(days) and days.max().date() + timedelta(days=1) < start:
        start = days.max().date() + timedelta(days=1)
    return (start, end) if start < end else None


def incremental(root: Path | None = None, today: date | None = None) -> list[dict]:
    """Exact daily counts for recent days into RAW_DIR/pypi_bq/<today>/ (manual fallback for pypistats)."""
    today = today or date.today()
    root = root or http.RAW_DIR / SOURCE_DIR
    window = incremental_window(root, today)
    if window is None:
        print("nothing new")
        return []
    return execute([Query("daily", *window, tuple(PROJECTS))], root / today.isoformat(), INCREMENTAL_MAX_GB)


# ------------------------------------------------------------------ reading the stored queries


def load_daily(root: Path | None = None, kinds: tuple[str, ...] = ("daily", "wed")
               ) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    """Stored counts as a wide frame (index = covered day, one column per project) and the days covered.

    For every day the newest fetch that covered it wins, with all its projects (a project absent from that
    query on that day had zero downloads, or was not asked for before its first year: also 0). A covered day
    without a `requests` row is a gap in the table: the whole row is NaN.
    """
    root = root or http.RAW_DIR / SOURCE_DIR
    files = _files(root, kinds)
    if not files:
        raise FileNotFoundError(f"no stored PyPI BigQuery results under {root} (run the BigQuery job)")
    owner: dict[pd.Timestamp, Path] = {}
    for f, m in files:  # later (newer fetch) files overwrite the owner of their days
        for d in covered_days(*m.groups()):
            owner[d] = f
    covered = pd.DatetimeIndex(sorted(owner))
    parts = []
    for f in set(owner.values()):
        df = pd.read_csv(f, dtype={"project": str})
        df["day"] = pd.to_datetime(df["day"])
        parts.append(df[df["day"].map(owner.get) == f])
    rows = pd.concat(parts, ignore_index=True)
    wide = rows.pivot_table(index="day", columns="project", values="downloads", aggfunc="sum")
    wide = wide.reindex(index=covered, columns=PROJECTS).fillna(0.0)
    gap = ~covered.isin(rows.loc[rows["project"] == CONTROL, "day"])
    wide.loc[gap, :] = float("nan")
    return wide, covered


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ai_tracker.sources.pypi_bq")
    ap.add_argument("mode", choices=["dryrun", "backfill", "incremental"])
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--force", action="store_true", help="backfill even if sampled days are stored")
    a = ap.parse_args(argv)
    root = http.RAW_DIR / SOURCE_DIR
    if a.mode == "incremental":
        incremental(a.out)
    elif a.mode == "backfill":
        if a.out is None and not stored_days(root, ("wed",)).empty and not a.force:
            print(f"sampled PyPI days already stored under {root}: not running the backfill again (--force)")
            return 0
        backfill(a.out or root / date.today().isoformat())
    else:
        dryrun(a.out or root.with_name(SOURCE_DIR + "_dryrun") / date.today().isoformat())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
