"""Indeed Hiring Lab AI tracker: share of job postings mentioning AI, daily, per country.

Source: github.com/hiring-lab/ai-tracker (CC BY 4.0). The repo's git history is the vintage archive:
every commit on the default branch that adds a new version of the AI postings CSV is one vintage, and
each value gets known_from = the UTC day after the first default-branch commit that contained it (midnight).
The +1 day margin (R1 review, docs/granskning/r1_lackage.md 1 and 7): most commits are local, so the push time
is unknown (api.github.com is refused); with as_of's convention (an origin date is the end of that day) a
version is thus counted a full day after its commit day. Several versions committed on one UTC day collapse to
the last of them.
Changed values in later commits become revisions (the whole history is recomputed at every refresh).

The data repo is kept as a blobless clone under data/raw/indeed/ai-tracker (never in the repo tree);
blobs of the CSV versions are fetched on demand by git. Merge commits count, branch commits do not
(`--first-parent`): data on a branch was not public until merged.

File history (checked 2026-11-23): AI_posting_<date>_clean.csv (2024-04 to 2024-08), ai-postings.csv
(2024-09), AI_posting.csv (2024-10 onwards). Columns and date formats vary between versions (ISO dates
or Excel-style D/M/YY; value column '% of job postings', 'ma_share_perc', 'ai_share', 'AI_share_postings').
"""

from __future__ import annotations

import io
import re
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from ai_tracker.http import RAW_DIR

REPO_URL = "https://github.com/hiring-lab/ai-tracker"
CLONE_DIR = RAW_DIR / "indeed" / "ai-tracker"
FILE_RE = re.compile(r"(?i)^(ai_posting[^/]*|ai-postings)\.csv$")  # excludes GenAI_* / genai-*
VALUE_COLUMNS = ("AI_share_postings", "ai_share", "ma_share_perc", "% of job postings")
ATOL = 1e-6  # percentage points; Excel-saved versions round to 10 significant digits


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def sync(clone_dir: Path = CLONE_DIR, url: str = REPO_URL) -> Path:
    """Blobless clone on first use, fetch afterwards. Plain git over HTTPS (git's own User-Agent)."""
    if (clone_dir / ".git").exists() or (clone_dir / "HEAD").exists():
        _git(clone_dir, "fetch", "--quiet", "origin")
    else:
        clone_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout", url, str(clone_dir)],
                       check=True, capture_output=True, text=True)
    return clone_dir


def _default_ref(repo: Path) -> str:
    for ref in ("origin/HEAD", "origin/main", "origin/master", "HEAD"):
        try:
            _git(repo, "rev-parse", "--verify", "--quiet", ref)
            return ref
        except subprocess.CalledProcessError:
            continue
    raise RuntimeError(f"no default branch in {repo}")


def vintages(repo: Path, ref: str | None = None) -> list[tuple[pd.Timestamp, str, str]]:
    """(commit time UTC, blob sha, path) for each new AI-postings CSV blob, oldest first."""
    ref = ref or _default_ref(repo)
    out, seen = [], set()
    log = _git(repo, "log", "--first-parent", "--reverse", "--format=%H %ct", ref)
    for line in log.splitlines():
        sha, ts = line.split()
        for entry in _git(repo, "ls-tree", "-r", "--format=%(objectname) %(path)", sha).splitlines():
            blob, path = entry.split(" ", 1)
            if FILE_RE.match(path) and blob not in seen:
                seen.add(blob)
                out.append((pd.Timestamp(int(ts), unit="s"), blob, path))  # naive UTC
    return out


def _dates(raw: pd.Series) -> pd.DatetimeIndex:
    s = raw.astype(str).str.strip()
    if s.str.contains("/").any():  # Excel export: D/M/YY (checked: first field reaches 31, second 12)
        return pd.DatetimeIndex(pd.to_datetime(s, format="%d/%m/%y"))
    return pd.DatetimeIndex(pd.to_datetime(s, format="%Y-%m-%d"))


def parse_csv(text: str) -> pd.DataFrame:
    """One CSV version -> columns date, country, value (percent of postings)."""
    df = pd.read_csv(io.StringIO(text))
    value_col = next((c for c in VALUE_COLUMNS if c in df.columns), None)
    if value_col is None or "jobcountry" not in df.columns:
        raise ValueError(f"unknown AI postings layout: {list(df.columns)}")
    out = pd.DataFrame({"date": _dates(df.iloc[:, 0]), "country": df["jobcountry"].astype(str).str.upper(),
                        "value": pd.to_numeric(df[value_col], errors="coerce")})
    out = out.dropna(subset=["value"])
    if out.duplicated(["date", "country"]).any():
        raise ValueError("duplicate (date, country) rows")
    return out


def vintage_rows(versions: list[tuple[pd.Timestamp, pd.DataFrame]]) -> pd.DataFrame:
    """Rows (country, period, value, known_from): a value enters when it first appears or changes.

    Values that disappear in a later version (e.g. a dropped country) are not deleted: the last
    published value stays the latest known one.
    """
    latest: dict[tuple[str, pd.Timestamp], float] = {}
    rows = []
    for kf, df in sorted(versions, key=lambda x: x[0]):
        for country, d, v in df[["country", "date", "value"]].itertuples(index=False):
            key = (country, d)
            old = latest.get(key)
            if old is None or not np.isclose(old, v, rtol=0, atol=ATOL):
                latest[key] = v
                rows.append((country, d, float(v), kf))
    return pd.DataFrame(rows, columns=["country", "period", "value", "known_from"])


KNOWN_MARGIN = pd.Timedelta(days=1)


def known_from(commit_time: pd.Timestamp) -> pd.Timestamp:
    """Commit time (UTC) -> known_from: the start of the next UTC day (see module docstring)."""
    return pd.Timestamp(commit_time).normalize() + KNOWN_MARGIN


def rows_from_repo(repo: Path, ref: str | None = None) -> pd.DataFrame:
    by_day: dict[pd.Timestamp, str] = {}
    for ts, blob, _ in vintages(repo, ref):  # oldest first: the last version of a day wins
        by_day[known_from(ts)] = blob
    versions = [(kf, parse_csv(_git(repo, "cat-file", "-p", blob))) for kf, blob in by_day.items()]
    return vintage_rows(versions)


@lru_cache(maxsize=1)
def all_rows() -> pd.DataFrame:
    """Every vintage row for every country (cached per process: one sync for all country specs)."""
    return rows_from_repo(sync())


def fetch(country: str) -> pd.DataFrame:
    """Release-dated rows for one country: period (day), value, known_from."""
    rows = all_rows()
    return rows[rows["country"] == country][["period", "value", "known_from"]].reset_index(drop=True)
