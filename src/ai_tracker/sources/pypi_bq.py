"""PyPI downloads per day and project from BigQuery (bigquery-public-data.pypi.file_downloads), track B1.

The table is partitioned by DATE(timestamp) and clustered by file.project. The query reads only the columns
`timestamp` and `file.project` and only the partitions in [start, end), and returns aggregate counts per
(day, project): a public CC BY 4.0 dataset (docs.pypi.org/api/bigquery), so the CSV may be a public artifact.

BigQuery only runs in GitHub Actions (keyless OIDC, sandbox quota of 1 TB/month shared by all tracks). Every
query is dry-run first; a run is refused when the estimate is above its cap, and maximum_bytes_billed is set
to the cap. Estimated, processed and billed bytes per query go to bytes.json next to the CSV
(docs/kallor/utvecklaradoption.md keeps the record).

Raw layout: RAW_DIR/pypi_bq/<fetch date>/daily_<start>_<end>.csv (+ bytes.json). For each day, the newest
fetch that covered it wins (a re-read of recent weeks replaces late-ingested counts).

    python -m ai_tracker.sources.pypi_bq dryrun   [--out DIR]   estimates only (free)
    python -m ai_tracker.sources.pypi_bq backfill [--out DIR]   2016-01-01 .. last Sunday, one query per year
    python -m ai_tracker.sources.pypi_bq incremental            new days (+ re-read of 3 weeks) into RAW_DIR
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import uuid
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from ai_tracker import http

TABLE = "bigquery-public-data.pypi.file_downloads"
# file.project is the normalised project name (lower case, '-' separators).
PROJECTS = ["openai", "anthropic", "google-generativeai", "google-genai", "langchain", "langchain-core",
            "transformers", "torch", "llama-index", "mcp", "requests", "numpy"]
CONTROL = "requests"  # always downloaded: a day without a `requests` row is a gap in the table, not a zero
BACKFILL_START = date(2016, 1, 1)
REREAD_DAYS = 21  # the incremental job re-reads the last three weeks (late-ingested rows become revisions)
# Byte caps (GB = 1e9 bytes). Sized from the dry run 2026-11-23 (docs/kallor/utvecklaradoption.md).
BACKFILL_MAX_GB = 300.0
INCREMENTAL_MAX_GB = 15.0
SOURCE_DIR = "pypi_bq"
_FILE = re.compile(r"daily_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\.csv$")


def sql(start: date, end: date, projects: list[str] | None = None) -> str:
    """Downloads per (day, project) for days in [start, end). Reads timestamp and file.project only."""
    names = ", ".join(f"'{p}'" for p in (projects or PROJECTS))
    return (
        "-- PyPI downloads per day and project (aggregates of a public CC BY 4.0 dataset)\n"
        "SELECT DATE(timestamp) AS day, file.project AS project, COUNT(*) AS downloads\n"
        f"FROM `{TABLE}`\n"
        f"WHERE timestamp >= TIMESTAMP('{start.isoformat()}') AND timestamp < TIMESTAMP('{end.isoformat()}')\n"
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
    """Monday of the current week: the backfill ends at the last complete W-SUN week."""
    return today - timedelta(days=today.weekday())


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


def plan(chunks: list[tuple[date, date]]) -> list[dict]:
    """Dry-run every chunk (free). Returns one record per chunk with the estimate."""
    return [{"start": s.isoformat(), "end": e.isoformat(), "estimated": dry_run_bytes(sql(s, e))} for s, e in chunks]


def execute(chunks: list[tuple[date, date]], out_dir: Path, cap_gb: float) -> list[dict]:
    """Dry-run all chunks, refuse if the total estimate is above `cap_gb`, then run each with its own cap."""
    out_dir.mkdir(parents=True, exist_ok=True)
    records = plan(chunks)
    total = sum(r["estimated"] for r in records)
    print(f"estimated total {_gb(total)} GB over {len(records)} queries (cap {cap_gb} GB)")
    if total > cap_gb * 1e9:
        _write_log(out_dir, records, refused=True)
        raise RuntimeError(f"estimate {_gb(total)} GB above cap {cap_gb} GB: refusing")
    for r in records:
        s, e = date.fromisoformat(r["start"]), date.fromisoformat(r["end"])
        cap = int(r["estimated"] * 1.1) + 100_000_000  # the estimate is an upper bound; 10 % + 0.1 GB margin
        body, stats = run_query(sql(s, e), cap)
        (out_dir / f"daily_{r['start']}_{r['end']}.csv").write_text(body, encoding="utf-8")
        r.update(stats, rows=body.count("\n") - 1)
        print(f"{r['start']}..{r['end']}: estimated {_gb(r['estimated'])} GB, processed "
              f"{_gb(r.get('processed'))} GB, billed {_gb(r.get('billed'))} GB, {r['rows']} rows")
    _write_log(out_dir, records)
    return records


def _write_log(out_dir: Path, records: list[dict], refused: bool = False) -> None:
    log = {"table": TABLE, "projects": PROJECTS, "refused": refused, "queries": records,
           "estimated_gb": _gb(sum(r["estimated"] for r in records)),
           "billed_gb": _gb(sum(r.get("billed", 0) for r in records))}
    (out_dir / "bytes.json").write_text(json.dumps(log, indent=1) + "\n", encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"PyPI BigQuery: estimated {log['estimated_gb']} GB, billed {log['billed_gb']} GB"
                    f"{' (REFUSED)' if refused else ''}\n\n")
            for r in records:
                f.write(f"- {r['start']}..{r['end']}: est {_gb(r['estimated'])} GB, billed {_gb(r.get('billed'))} GB\n")


def dryrun(out_dir: Path, today: date | None = None) -> list[dict]:
    """Estimates only, per year of the backfill and for one incremental window. Dry runs are free."""
    today = today or date.today()
    end = last_monday(today)
    records = plan(year_chunks(BACKFILL_START, end))
    s = end - timedelta(days=REREAD_DAYS)
    records += [dict(r, kind="incremental") for r in plan([(s, end)])]
    # Probe: does the estimate reflect clustering? Same day with one project vs every project.
    d0, d1 = end - timedelta(days=8), end - timedelta(days=7)
    for kind, projects in (("probe_one_project", [CONTROL]), ("probe_twelve_projects", PROJECTS)):
        records.append({"start": d0.isoformat(), "end": d1.isoformat(), "kind": kind,
                        "estimated": dry_run_bytes(sql(d0, d1, projects))})
    unfiltered = sql(d0, d1).split("  AND file.project")[0] + "GROUP BY day, project\n"
    records.append({"start": d0.isoformat(), "end": d1.isoformat(), "kind": "probe_no_project_filter",
                    "estimated": dry_run_bytes(unfiltered)})
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_log(out_dir, records, refused=True)  # nothing ran
    for r in records:
        print(f"{r['start']}..{r['end']}: estimated {_gb(r['estimated'])} GB")
    return records


def backfill(out_dir: Path, today: date | None = None) -> list[dict]:
    end = last_monday(today or date.today())
    return execute(year_chunks(BACKFILL_START, end), out_dir, BACKFILL_MAX_GB)


def stored_days(root: Path) -> pd.DatetimeIndex:
    """Days covered by any stored query under `root` (RAW_DIR/pypi_bq)."""
    days = set()
    for f in root.glob("*/daily_*.csv"):
        m = _FILE.search(f.name)
        days.update(pd.date_range(m.group(1), pd.Timestamp(m.group(2)) - pd.Timedelta(days=1)))
    return pd.DatetimeIndex(sorted(days))


def incremental_window(root: Path, today: date) -> tuple[date, date] | None:
    """[start, end) for the weekly job: the last REREAD_DAYS days plus any later day not stored yet; None if the
    store is empty (cold start: the caller runs the backfill)."""
    days = stored_days(root)
    if days.empty:
        return None
    end = last_monday(today)
    start = min(end - timedelta(days=REREAD_DAYS), (days.max() + pd.Timedelta(days=1)).date())
    return (start, end) if start < end else None


def incremental(root: Path | None = None, today: date | None = None) -> list[dict]:
    """Weekly job: query new days (+ re-read) into RAW_DIR/pypi_bq/<today>/; cold start = backfill."""
    today = today or date.today()
    root = root or http.RAW_DIR / SOURCE_DIR
    out_dir = root / today.isoformat()
    if stored_days(root).empty:
        print("no stored PyPI days: running the backfill")
        return backfill(out_dir, today)
    window = incremental_window(root, today)
    if window is None:
        print("nothing new")
        return []
    return execute([window], out_dir, INCREMENTAL_MAX_GB)


# ------------------------------------------------------------------ reading the stored queries


def load_daily(root: Path | None = None) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    """Stored counts as a wide frame (index day, one column per project) and the days covered.

    For every day the newest fetch that covered it wins, with all its projects (a project absent from that
    query on that day had zero downloads). A covered day without a `requests` row is a gap in the table: the
    whole row is NaN.
    """
    root = root or http.RAW_DIR / SOURCE_DIR
    files = sorted(root.glob("*/daily_*.csv"), key=lambda f: (f.parent.name, f.name))
    if not files:
        raise FileNotFoundError(f"no stored PyPI BigQuery results under {root} (run the BigQuery job)")
    owner: dict[pd.Timestamp, Path] = {}
    for f in files:  # later (newer fetch) files overwrite the owner of their days
        m = _FILE.search(f.name)
        for d in pd.date_range(m.group(1), pd.Timestamp(m.group(2)) - pd.Timedelta(days=1)):
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
    a = ap.parse_args(argv)
    if a.mode == "incremental":
        incremental(a.out)
    else:
        out = a.out or http.RAW_DIR / SOURCE_DIR / date.today().isoformat()
        (dryrun if a.mode == "dryrun" else backfill)(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
