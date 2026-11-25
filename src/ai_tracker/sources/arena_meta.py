"""Arena (LMArena) model metadata: licence and organization per board, and name classes (track Q2).

Read only from Arena's own records (register 2026-11-25, Q2):
- the dataset `lmarena-ai/leaderboard-dataset`, subset `text`, `full` split, category `overall`, at the HEAD revision
  that `arena.subset_boards` reads: columns model_name, organization, license, vote_count, leaderboard_publish_date;
- the Space `lmarena-ai/arena-leaderboard`: `leaderboard_table_<YYYYMMDD>.csv` (columns key, License, Organization),
  committed 2023-06 - 2025-08 alongside the elo_results pickles. Tables without a `key` column (the first ten, 2023)
  name models by display name only and are not used.

Classification (`classify`), per name and board, in the registered order:
1. the board's own dataset row (same publish date);
2. else Arena's latest record of the same model (any name of its class) dated <= the board: dataset rows of other
   boards, Space tables dated by the date in their file name;
3. else Arena's earliest later record: the weights only when it says closed (weights are never withdrawn, so a later
   "closed" holds earlier too; a later "open" may be a later release), the organization always;
4. else model_origin.ARENA_MODELS (open only from its documented release date);
5. else left out.
Licence "Proprietary" = closed; any other non-empty value = open weights (Arena names the weights' licence).
"""

from __future__ import annotations

import io
import re
from functools import lru_cache

import numpy as np
import pandas as pd

from ai_tracker import http
from ai_tracker.sources import arena
from ai_tracker.sources import model_origin as mo

SUBSET = "text"
CLOSED_LICENSE = "Proprietary"
META_COLUMNS = ["name", "date", "license", "organization", "vote_count", "origin"]
DISPLAY_BEFORE, DISPLAY_AFTER = pd.Timestamp("2026-10-15"), pd.Timestamp("2026-10-20")  # API -> display names
EARLY_DISPLAY = (pd.Timestamp("2026-10-13"), pd.Timestamp("2026-10-15"))  # first display names, one board early
_CSV = re.compile(r"^leaderboard_table_(\d{8})\.csv$")


def weights_of(license_text) -> str | None:
    s = license_text.strip() if isinstance(license_text, str) else ""
    if not s:
        return None
    return mo.CLOSED if s == CLOSED_LICENSE else mo.OPEN


# ------------------------------------------------------------------ parsing (pure)

def dataset_meta(rows: pd.DataFrame) -> pd.DataFrame:
    """Dataset rows (model_name, organization, license, vote_count, category, leaderboard_publish_date) -> META_COLUMNS
    for category overall. A name listed twice on one date keeps its first non-empty fields."""
    df = rows[rows["category"] == arena.CATEGORY] if "category" in rows else rows
    out = pd.DataFrame({
        "name": df["model_name"].astype(str),
        "date": pd.to_datetime(df["leaderboard_publish_date"]),
        "license": df["license"].fillna("").astype(str).str.strip(),
        "organization": df["organization"].fillna("").astype(str).str.strip(),
        "vote_count": pd.to_numeric(df.get("vote_count", pd.Series(np.nan, index=df.index)), errors="coerce"),
        "origin": "dataset",
    })
    out = out.sort_values(["date", "name"], kind="stable")
    agg = out.groupby(["name", "date"], sort=False).agg(
        license=("license", lambda s: next((x for x in s if x), "")),
        organization=("organization", lambda s: next((x for x in s if x), "")),
        vote_count=("vote_count", "max"), origin=("origin", "first")).reset_index()
    return agg[META_COLUMNS].reset_index(drop=True)


def space_table_meta(name: str, content: bytes) -> pd.DataFrame | None:
    """One Space `leaderboard_table_<date>.csv` -> META_COLUMNS, or None when it has no `key` column."""
    m = _CSV.match(name)
    if not m:
        return None
    t = pd.read_csv(io.BytesIO(content), dtype=str)
    t.columns = [c.strip() for c in t.columns]
    if "key" not in t.columns:
        return None
    org = t["Organization"] if "Organization" in t.columns else pd.Series("", index=t.index)
    return pd.DataFrame({
        "name": t["key"].astype(str).str.strip(),
        "date": pd.Timestamp(m[1]),
        "license": t["License"].fillna("").astype(str).str.strip() if "License" in t.columns else "",
        "organization": org.fillna("").astype(str).str.strip(),
        "vote_count": np.nan,
        "origin": f"space:{name}",
    })[META_COLUMNS]


# ------------------------------------------------------------------ name classes (pure)

def _tokens(name: str) -> tuple[str, ...]:
    return tuple(sorted(t for t in re.split(r"[^a-z0-9]+", name.lower()) if t))


def _unique_matches(left: list[str], right: list[str], key) -> dict[str, str]:
    lk: dict = {}
    rk: dict = {}
    for n in left:
        lk.setdefault(key(n), []).append(n)
    for n in right:
        rk.setdefault(key(n), []).append(n)
    return {lk[k][0]: rk[k][0] for k in lk if k in rk and len(lk[k]) == 1 and len(rk[k]) == 1}


def display_switch_pairs(before: pd.DataFrame, after: pd.DataFrame) -> tuple[dict[str, str], list[str], list[str]]:
    """Mechanical API -> display name pairs between the last API-name board and the first display-name board
    (META_COLUMNS rows of one date each), in the registered order: same name, same normalized name, same set of
    words, same licence and vote count; each rule must match uniquely on both sides. Returns (pairs incl. identical
    names, unmatched API names, unmatched display names)."""
    a = sorted(set(before["name"]))
    b = sorted(set(after["name"]))
    pairs = {n: n for n in set(a) & set(b)}
    rules = [mo.norm, _tokens]
    for rule in rules:
        left = [n for n in a if n not in pairs]
        right = [n for n in b if n not in set(pairs.values())]
        pairs.update(_unique_matches(left, right, rule))
    left = [n for n in a if n not in pairs]
    right = [n for n in b if n not in set(pairs.values())]
    va = before.drop_duplicates("name").set_index("name")
    vb = after.drop_duplicates("name").set_index("name")

    def lv(df):
        return lambda n: (df.loc[n, "license"], df.loc[n, "vote_count"]) if pd.notna(df.loc[n, "vote_count"]) else (n,)
    lk = {n: lv(va)(n) for n in left}
    rk = {n: lv(vb)(n) for n in right}
    pairs.update(_unique_matches(left, right, lambda n: lk.get(n, rk.get(n))))
    left = [n for n in a if n not in pairs]
    right = [n for n in b if n not in set(pairs.values())]
    return pairs, left, right


def early_display_pairs(before: pd.DataFrame, after: pd.DataFrame) -> dict[str, str]:
    """Names that vanish between `before` and `after` and match a new name of `after` with the same normalized name,
    organization and licence (the first display names on 2026-10-15). For review; the reviewed result is used."""
    gone = sorted(set(before["name"]) - set(after["name"]))
    new = sorted(set(after["name"]) - set(before["name"]))
    va = before.drop_duplicates("name").set_index("name")
    vb = after.drop_duplicates("name").set_index("name")
    return {g: n for g, n in _unique_matches(gone, new, mo.norm).items()
            if va.loc[g, "organization"] == vb.loc[n, "organization"] and va.loc[g, "license"] == vb.loc[n, "license"]}


def name_classes(meta: pd.DataFrame, renames=None, extra=None) -> mo.Classes:
    """Name classes from the curated renames, the early display names (2026-10-13 -> 10-15), the mechanical switch
    (2026-10-15 -> 10-20) and DISPLAY_EXTRA."""
    renames = mo.ARENA_RENAMES if renames is None else renames
    extra = mo.DISPLAY_EXTRA if extra is None else extra
    pairs = [(a, b) for a, b, *_ in renames] + [(a, b) for a, b, *_ in extra]
    ds = meta[meta["origin"] == "dataset"]
    for before, after, fn in ((*EARLY_DISPLAY, early_display_pairs), (DISPLAY_BEFORE, DISPLAY_AFTER, None)):
        b0, b1 = ds[ds["date"] == before], ds[ds["date"] == after]
        if b0.empty or b1.empty:
            continue
        got = fn(b0, b1) if fn else display_switch_pairs(b0, b1)[0]
        pairs += [(x, y) for x, y in got.items() if x != y]
    return mo.Classes(pairs)


# ------------------------------------------------------------------ classification (pure)

class Classifier:
    """classify(name, board date) -> (weights, organization, step_weights, step_org)."""

    def __init__(self, meta: pd.DataFrame, classes: mo.Classes, curated=None):
        self.classes = classes
        self.curated = mo.ARENA_MODELS if curated is None else curated
        m = meta.copy()
        m["cls"] = [classes.find(n) for n in m["name"]]
        m["weights"] = [weights_of(x) for x in m["license"]]
        m = m.sort_values(["date", "origin", "name"], kind="stable")
        ds = m[m["origin"] == "dataset"]
        self.own = {(n, d): (w if isinstance(w, str) else None, o if isinstance(o, str) else "")
                    for n, d, w, o in zip(ds["name"], ds["date"], ds["weights"], ds["organization"])}
        self.by_cls: dict[str, tuple[np.ndarray, list, list]] = {}
        for c, g in m.groupby("cls", sort=False):
            self.by_cls[c] = (g["date"].to_numpy(dtype="datetime64[ns]"),
                              [x if isinstance(x, str) and x else None for x in g["weights"]],
                              [x if isinstance(x, str) and x else None for x in g["organization"]])
        self._memo: dict = {}

    def classify(self, name: str, date: pd.Timestamp) -> tuple[str | None, str | None, str, str]:
        key = (name, date)
        if key in self._memo:
            return self._memo[key]
        w, o = self.own.get(key, (None, ""))
        sw = "own" if w else ""
        so = "own" if o else ""
        dates, ws, orgs = self.by_cls.get(self.classes.find(name), (np.array([], dtype="datetime64[ns]"), [], []))
        d64 = np.datetime64(pd.Timestamp(date), "ns")
        if not w:
            earlier = [x for x, t in zip(ws, dates) if t <= d64 and x]
            later = [x for x, t in zip(ws, dates) if t > d64 and x]
            if earlier:
                w, sw = earlier[-1], "earlier"
            elif later and later[0] == mo.CLOSED:
                w, sw = mo.CLOSED, "later_closed"
        if not o:
            earlier = [x for x, t in zip(orgs, dates) if t <= d64 and x]
            later = [x for x, t in zip(orgs, dates) if t > d64 and x]
            if earlier:
                o, so = earlier[-1], "earlier"
            elif later:
                o, so = later[0], "later"
        cur = self.curated.get(name)
        if cur is None:
            cur = next((self.curated[n] for n in self.curated if self.classes.find(n) == self.classes.find(name)), None)
        if cur is not None:
            cw, released, corg, _ref = cur
            if not w and cw and (cw == mo.CLOSED or (released is not None
                                                     and pd.Timestamp(date) >= pd.Timestamp(released))):
                w, sw = cw, "curated"
            if not o and corg:
                o, so = corg, "curated"
        out = (w, o or None, sw or "none", so or "none")
        self._memo[key] = out
        return out


# ------------------------------------------------------------------ fetch

def _file() -> str:
    return f"{SUBSET}/full-00000-of-00001.parquet"


def read_dataset_meta(sha: str) -> pd.DataFrame:
    """Dataset metadata at revision `sha` (immutable), cached under the raw directory."""
    p = http.RAW_DIR / arena.SOURCE / "meta" / f"{sha}_{SUBSET}.meta.parquet"
    if p.exists() and p.stat().st_size:
        return pd.read_parquet(p)
    url = f"{arena.HF}/datasets/{arena.DATASET}/resolve/{sha}/{_file()}"
    r = http.get(url, arena.SOURCE, save=False, timeout=300)
    rows = pd.read_parquet(io.BytesIO(r.content), columns=["model_name", "organization", "license", "vote_count",
                                                          "category", "leaderboard_publish_date"])
    meta = dataset_meta(rows)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    meta.to_parquet(tmp, index=False)
    tmp.replace(p)
    return meta


def read_space_tables() -> pd.DataFrame:
    """Every Space leaderboard_table CSV with a `key` column, from the Space clone at HEAD (cached by blob)."""
    clone = arena.RAW / "space_repo"
    names = [n for n in arena._git(clone, "ls-tree", "--name-only", "HEAD").split() if _CSV.match(n)]
    cache = http.RAW_DIR / arena.SOURCE / "space_csv"
    frames = []
    for n in sorted(names):
        blob = arena._git(clone, "rev-parse", f"HEAD:{n}").strip()
        p = cache / f"{blob}_{n}"
        if p.exists() and p.stat().st_size:
            content = p.read_bytes()
        else:
            content = arena._git(clone, "show", f"HEAD:{n}").encode()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content)
        t = space_table_meta(n, content)
        if t is not None:
            frames.append(t)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=META_COLUMNS)


@lru_cache(maxsize=1)
def meta() -> pd.DataFrame:
    """Dataset metadata (the revision subset_boards reads) and the Space tables."""
    _, _, sha = arena._evidence()
    return pd.concat([read_dataset_meta(sha), read_space_tables()], ignore_index=True)
