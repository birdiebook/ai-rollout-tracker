"""Arena (LMArena) leaderboards, honestly dated: the top rating per published leaderboard.

Two public records, both on Hugging Face (CC BY 4.0, see LICENSE):

1. The dataset `lmarena-ai/leaderboard-dataset` (one parquet per subset, `full` split = every published
   leaderboard, column `leaderboard_publish_date`). It was created on 2026-04-02 with the history uploaded in bulk;
   since then every leaderboard arrives in a commit titled "Update <subset> for <date>". Checked 2026-11-24: every
   publish date from 2026-04-02 has such a commit (0-9 days after the date), and the rows of the 195 older dates were
   identical in the 2026-04-03 revision and the current one.
   But the bulk history is censored: models that were later renamed or removed are missing (2024-01-09 lacks
   `gpt-4-turbo`, the published #1; 2023-05-08 lacks every proprietary model, so its "top" is vicuna-13b). The rows
   that are there equal the published values exactly.
2. The old Space `lmarena-ai/arena-leaderboard`: `elo_results_YYYYMMDD.pkl` committed at the time (2023-05-20 to
   2025-09-03), the complete published tables. Pickles are read with a restricted unpickler (every global is a
   harmless stub, nothing from the file is executed), and the table is rebuilt from the raw arrays.

Per leaderboard (subset, publish date) the source is chosen in this order:
- the Space pickle (same date, or named one day off), if one of its tables equals the dataset's `overall` rows on that date exactly (that tells which
  table Arena itself treats as the published `overall`); evidence = first commit adding the file; "release";
- the dataset, if a titled commit exists; evidence = that commit's UTC date; "release";
- else the dataset bulk upload: evidence = 2026-04-02, source "backfill" (censored, see above).
Space files with no equal dataset board are added as their own boards, with the table that the latest earlier matched
file used (2025-08-15, 08-22, 08-29). known_from of a monthly value is never before max(publish date, evidence) (sources/vintages.py).

Scale notes from the dataset card (not corrected here): Elo until 2024-01-08, Bradley-Terry from 2024-01-09; style
control default and offset 2025-05-16; frequency re-weighting 2025-07-23; display names instead of API names from
2026-10-20. Ratings are relative to the pool, anchored on a reference model.
"""

from __future__ import annotations

import io
import os
import pickle
import re
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from ai_tracker import config, http
from ai_tracker.sources import vintages

HF = "https://huggingface.co"
DATASET = "lmarena-ai/leaderboard-dataset"
SPACE = "lmarena-ai/arena-leaderboard"
SOURCE = "arena"
RAW = config.REPO / "data" / "raw" / "arena"
DATASET_CREATED = pd.Timestamp("2026-04-02")  # "initial commit" / "add historical data", 2026-04-02T19:50Z
CATEGORY = "overall"
# Tables in the Space pickles that may hold a subset's overall board (old flat layout, then text/...).
PICKLE_TABLES = {
    "text": ("full", "full_old", "text/full", "elo_rating_median", "elo_rating_online", "elo_rating_final"),
    "text_style_control": ("full_style_control", "text/full_style_control"),
    "webdev": (),
}
# Reference model for the anchor-free gap (present in every text board from 2023-12-15; renamed 2026-10-20).
REFERENCE = ("mixtral-8x7b-instruct-v0.1", "Mixtral 8x7B Instruct v0.1")
MATCH_ATOL = 1e-6
MIN_COMMON = 5
LICENSE = ("CC BY 4.0 (dataset card `license: cc-by-4.0`, huggingface.co/datasets/lmarena-ai/leaderboard-dataset); "
           "Space files: same publisher, used only as dated evidence and complete tables; credit LMArena")

_TITLE = re.compile(r"^Update (\S+) for (\d{4}-\d{2}-\d{2})$")
_PKL = re.compile(r"^elo_results_(\d{8})\.pkl$")


# ------------------------------------------------------------------ git evidence

def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def update_clone(url: str, clone: Path) -> None:
    """Blobless clone without checkout and without LFS content (only commits and trees are needed)."""
    env = {**os.environ, "GIT_LFS_SKIP_SMUDGE": "1"}
    if (clone / ".git").exists():
        subprocess.run(["git", "-C", str(clone), "fetch", "--quiet", "origin"], check=True, env=env,
                       capture_output=True)
        subprocess.run(["git", "-C", str(clone), "update-ref", "HEAD", "FETCH_HEAD"], check=True, env=env)
        return
    clone.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout", url, str(clone)],
                   check=True, env=env)


def parse_dataset_log(log: str) -> dict[tuple[str, str], pd.Timestamp]:
    """`git log --format=%cI|%s` of the dataset -> (subset, publish date) -> UTC date of the first titled commit."""
    out: dict[tuple[str, str], pd.Timestamp] = {}
    for line in log.splitlines():
        if "|" not in line:
            continue
        ts, title = line.split("|", 1)
        m = _TITLE.match(title.strip())
        if m:
            day = pd.Timestamp(ts).tz_convert("UTC").tz_localize(None).normalize()
            key = (m[1], m[2])
            out[key] = min(out.get(key, day), day)
    return out


def parse_space_log(log: str) -> dict[str, tuple[pd.Timestamp, str]]:
    """`git log --diff-filter=A --no-renames --format=C|%cI --name-only` of the Space ->
    publish date -> (UTC date of the first commit adding elo_results_<date>.pkl, file name)."""
    out: dict[str, tuple[pd.Timestamp, str]] = {}
    day = None
    for line in log.splitlines():
        line = line.strip()
        if line.startswith("C|"):
            day = pd.Timestamp(line[2:]).tz_convert("UTC").tz_localize(None).normalize()
        elif line and day is not None and (m := _PKL.match(line)):
            date = pd.Timestamp(m[1]).strftime("%Y-%m-%d")
            if date not in out or day < out[date][0]:
                out[date] = (day, line)
    return out


# ------------------------------------------------------------------ restricted unpickler

class _Stub:
    """Stand-in for every global a pickle names: records arguments and state, runs nothing."""

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj.args, obj.state = args, None
        return obj

    def __init__(self, *args, **kwargs):
        pass

    def __setstate__(self, state):
        self.state = state

    def __call__(self, *args, **kwargs):  # pragma: no cover - only reached through REDUCE on an instance
        return _Stub(*args)


class _SafeUnpickler(pickle.Unpickler):
    def find_class(self, module, name):  # never imports anything
        return type(f"{module}.{name}", (_Stub,), {"qual": f"{module}.{name}"})


def safe_load(data: bytes):
    return _SafeUnpickler(io.BytesIO(data)).load()


def _array(obj) -> np.ndarray:
    """numpy array from a `_reconstruct` stub with BUILD state (version, shape, dtype, fortran, data)."""
    if not hasattr(obj, "state"):
        return np.asarray(obj, dtype=object)
    if not (isinstance(obj.state, tuple) and len(obj.state) == 5):
        raise ValueError(f"not a numpy array: {getattr(obj, 'qual', type(obj))}")  # e.g. a pandas 3 string array
    _, shape, dtype, _, data = obj.state
    code = dtype.args[0]
    if isinstance(data, (list, tuple)) or code == "O":
        return np.array(list(data), dtype=object).reshape(shape)
    return np.frombuffer(data, dtype=np.dtype(code)).reshape(shape)


def _index(ix) -> list | None:
    qual = getattr(ix, "qual", "")
    if qual.endswith("_new_Index"):
        data = ix.args[1]["data"]
        try:
            return list(_array(data)) if hasattr(data, "state") else list(data)
        except (ValueError, TypeError):
            return None
    return None


def _series(obj) -> pd.Series | None:
    """{model: rating} dict, a pandas Series stub, or a DataFrame stub with a `rating` column."""
    if isinstance(obj, dict):
        try:
            return pd.Series({str(k): float(v) for k, v in obj.items()}, dtype=float) if obj else None
        except (TypeError, ValueError):
            return None
    qual = getattr(obj, "qual", "")
    state = getattr(obj, "state", None)
    if not isinstance(state, dict) or "_mgr" not in state:
        return None
    mgr = state["_mgr"]
    if qual.endswith("Series"):  # SingleBlockManager state: ([index], [values], ...)
        names = _index(mgr.state[0][0])
        return pd.Series(_array(mgr.state[1][0]).astype(float), index=names) if names else None
    if qual.endswith("DataFrame"):  # BlockManager args: (blocks, [columns, index])
        blocks, axes = mgr.args
        cols, rows = _index(axes[0]), _index(axes[1])
        if not cols or not rows or "rating" not in cols:
            return None
        want = cols.index("rating")
        for b in blocks:
            values, place = b.args[0], b.args[1]
            if getattr(place, "qual", "").endswith("slice"):
                place = list(range(*[a for a in place.args if a is not None]))
            place = list(np.atleast_1d(place))
            if want in place:
                v = _array(values)
                return pd.Series(np.asarray(v[place.index(want)], dtype=float), index=rows)
    return None


def pickle_tables(data: bytes) -> dict[str, pd.Series]:
    """Every candidate table in an elo_results pickle: path -> ratings by model."""
    obj = safe_load(data)
    out = {}

    def walk(node, path):
        if not isinstance(node, dict):
            return
        if "leaderboard_table_df" in node:
            s = _series(node["leaderboard_table_df"])
            if s is not None:
                out["/".join(path)] = s
        for k, v in node.items():
            if k in ("elo_rating_median", "elo_rating_online", "elo_rating_final") and not path:
                s = _series(v)
                if s is not None:
                    out[k] = s
            elif isinstance(v, dict):
                walk(v, path + (k,))
    walk(obj, ())
    return out


def match_table(tables: dict[str, pd.Series], rows: pd.Series, candidates: tuple[str, ...]) -> str | None:
    """The candidate table whose ratings equal `rows` (dataset overall board) on every common model."""
    for name in candidates:
        t = tables.get(name)
        if t is None:
            continue
        j = pd.concat([t.rename("p"), rows.rename("d")], axis=1, join="inner")
        if len(j) >= MIN_COMMON and np.allclose(j["p"], j["d"], rtol=0, atol=MATCH_ATOL):
            return name
    return None


# ------------------------------------------------------------------ boards

def _near(date: str) -> list[str]:
    d = pd.Timestamp(date)
    return [date] + [(d + pd.Timedelta(days=k)).strftime("%Y-%m-%d") for k in (-1, 1)]


def board_events(dataset: pd.DataFrame, subset: str, ds_evidence: dict[tuple[str, str], pd.Timestamp],
                 space: dict[str, tuple[pd.Timestamp, str]], pickles: dict[str, dict[str, pd.Series]],
                 created: pd.Timestamp = DATASET_CREATED) -> pd.DataFrame:
    """One row per published board: published, top, top_model, ref, n_models, evidence, source, origin.

    `dataset`: overall rows of the subset (model_name, rating, leaderboard_publish_date); `pickles`: file name ->
    tables (only the Space files that could be read)."""
    rows, used, matched = [], set(), {}
    for date, grp in dataset.groupby("leaderboard_publish_date"):
        ratings = grp.set_index("model_name")["rating"].astype(float)
        board, evidence, source, origin = ratings, None, "release", "dataset"
        for near in _near(date):  # the Space file may be named one day off
            if near in space and space[near][1] in pickles:
                name = match_table(pickles[space[near][1]], ratings, PICKLE_TABLES.get(subset, ()))
                if name is not None:
                    board, evidence, origin = pickles[space[near][1]][name], space[near][0], f"space:{name}"
                    used.add(space[near][1])
                    matched[pd.Timestamp(near)] = name
                    break
        if evidence is None and (subset, date) in ds_evidence:
            evidence = ds_evidence[(subset, date)]
        if evidence is None:
            evidence, source, origin = created, "backfill", "dataset-bulk"
        board = board.dropna()
        ref = next((board[r] for r in REFERENCE if r in board.index), np.nan)
        rows.append((pd.Timestamp(date), float(board.max()), str(board.idxmax()), float(ref), len(board),
                     evidence, source, origin))
    # Space boards with no equal dataset board (e.g. 2025-08-15/22/29: the dataset has 08-14/21/28 with other
    # values): still published, dated records. The table is the one the latest earlier matched file used.
    for date, (day, file) in sorted(space.items()):
        if file in used or file not in pickles:
            continue
        before = [d for d in matched if d < pd.Timestamp(date)]
        name = matched[max(before)] if before else None
        if name is None or name not in pickles[file]:
            continue
        board = pickles[file][name].dropna()
        ref = next((board[r] for r in REFERENCE if r in board.index), np.nan)
        rows.append((pd.Timestamp(date), float(board.max()), str(board.idxmax()), float(ref), len(board), day,
                     "release", f"space-unmatched:{name}"))
    return pd.DataFrame(rows, columns=["published", "top", "top_model", "ref", "n_models", "evidence", "source",
                                       "origin"]).sort_values("published").reset_index(drop=True)


def monthly_rows(events: pd.DataFrame, column: str, last_month: pd.Period) -> pd.DataFrame:
    """Release-dated monthly rows for `column` ("top" or "gap" = top - reference)."""
    ev = events.assign(value=events["top"] - events["ref"] if column == "gap" else events[column])
    return vintages.monthly(ev[["published", "value", "evidence", "source"]], last_month)


# ------------------------------------------------------------------ fetch

def _dataset_sha(clone: Path) -> str:
    return _git(clone, "rev-parse", "HEAD").strip()


def read_dataset(subset: str, sha: str) -> pd.DataFrame:
    url = f"{HF}/datasets/{DATASET}/resolve/{sha}/{subset}/full-00000-of-00001.parquet"
    r = http.get(url, SOURCE, save=False, timeout=300)
    df = pd.read_parquet(io.BytesIO(r.content), columns=["model_name", "rating", "category",
                                                        "leaderboard_publish_date"])
    df = df[df["category"] == CATEGORY].drop(columns="category").reset_index(drop=True)
    p = http.raw_path(SOURCE, url, ".overall.parquet")  # raw copy with fetch date (overall rows only)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p, index=False)
    return df


def read_pickle(name: str, cache: Path = RAW / "space_pkl") -> bytes | None:
    """A Space file (immutable LFS content), cached; None if it cannot be fetched."""
    p = cache / name
    if p.exists() and p.stat().st_size:
        return p.read_bytes()
    try:
        r = http.get(f"{HF}/spaces/{SPACE}/resolve/main/{name}", SOURCE, save=False, timeout=120)
    except Exception:  # noqa: BLE001 - a missing file only means that board falls back to the dataset
        return None
    if not r.content.startswith(b"\x80"):  # not a pickle (e.g. "Entry not found")
        return None
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(r.content)
    return r.content


@lru_cache(maxsize=1)
def _evidence() -> tuple[dict, dict, str]:
    ds_clone, sp_clone = RAW / "dataset_repo", RAW / "space_repo"
    update_clone(f"{HF}/datasets/{DATASET}", ds_clone)
    update_clone(f"{HF}/spaces/{SPACE}", sp_clone)
    ds = parse_dataset_log(_git(ds_clone, "log", "--format=%cI|%s"))
    sp = parse_space_log(_git(sp_clone, "log", "--diff-filter=A", "--no-renames", "--format=C|%cI",
                              "--name-only", "--", "elo_results_*.pkl"))
    head = set(_git(sp_clone, "ls-tree", "--name-only", "HEAD").split())
    sp = {d: v for d, v in sp.items() if v[1] in head}  # only files still in the Space
    return ds, sp, _dataset_sha(ds_clone)


@lru_cache(maxsize=None)
def events(subset: str) -> pd.DataFrame:
    ds_ev, space, sha = _evidence()
    dataset = read_dataset(subset, sha)
    pickles = {}
    if PICKLE_TABLES.get(subset):
        for date, (_, name) in sorted(space.items()):
            if (data := read_pickle(name)) is not None:
                pickles[name] = pickle_tables(data)
    return board_events(dataset, subset, ds_ev, space, pickles)


def series(subset: str, column: str) -> pd.DataFrame:
    """Fetch body for the g1_arena_* series (complete months only)."""
    return monthly_rows(events(subset), column, vintages.last_complete_month())
