"""G1: how far open-weights models trail the closed frontier, and Chinese labs the rest (track Q2).

Register 2026-11-25, "Q2: gapet mellan öppna och stängda modeller och Kinas gap"; doc docs/kallor/g1_oppen_stangd.md.
Catalog series, not core series.

Two groups per measure: the follower F (open weights; Chinese labs) and the leader L (closed weights; every other
classified lab).

Arena, within one board (`arena.subset_boards("text")`, overall). For a version of month m with cut-off c (month end +
1 day for the first version, register 2026-11-25 X20; else the evidence day), the known boards are those published <=
end of m with evidence <= c; b(s) is the latest known board published <= end of s, for each month s from s0 to m.
- F(m), L(m): the top rating of each group in b(m). gap = L(m) - F(m), context only.
- The leader frontier at month s is the leader model of b(s) with the highest rating there (ties: name); its rating is
  read in b(m) under any name of its class (sources/arena_meta.name_classes). If it is not in b(m), the next leader
  model of b(s) by rating that is in b(m) is used (counted in `fallbacks`).
- s* = the first month s in [s0, m] whose leader frontier, read in b(m), is >= F(m); lag = m - s* in whole months.
  F(m) > L(m): the follower leads, lag = 0 (the floor). s* = s0: censored (lag >= m - s0), no value.
- known_from = max(version day, month end + 1 day); source "backfill" when b(m) or b(s*) exists only in the dataset's
  bulk upload.

Epoch ECI (one scale over time): F(t), L(t) = the best ECI of each group among models with `date` <= end of t;
lag = t - min{s >= s0: L(s) >= F(t)} months, floor 0 when F(t) > L(t), censored when s* = s0; gap = L(t) - F(t).
For open vs closed, an open model is open from max(date, weights release) and closed before (register 2026-11-25,
X20 after review R23: model_origin.ECI_WEIGHTS_RELEASE, else Epoch's `Accessibility notes`; a note that says the
weights come later without a date leaves the model out of that measure).
ECI is re-estimated and the classification is today's: the history is a backfill (Series, observations dates it
month end + lag_days), later fetches add fetch and revision rows.
"""

from __future__ import annotations

from functools import lru_cache, partial

import numpy as np
import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.sources import model_origin as mo

TOL = 1e-9
KINDS = ("open", "china")
FOLLOW, LEAD = "follow", "lead"
Board = tuple  # (published, ratings by name, evidence, source, origin)


# ------------------------------------------------------------------ helpers

def months_between(a: pd.Period, b: pd.Period) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month)


def group_open(weights: str | None) -> str | None:
    return FOLLOW if weights == mo.OPEN else LEAD if weights == mo.CLOSED else None


def group_china(chinese: bool | None) -> str | None:
    return FOLLOW if chinese is True else LEAD if chinese is False else None


def norm_boards(boards: list[Board]) -> list[Board]:
    out = []
    for published, ratings, evidence, source, origin in boards:
        published = pd.Timestamp(published).normalize()
        evidence = max(pd.Timestamp(evidence).normalize(), published)  # never known before its own date
        out.append((published, ratings.dropna().astype(float), evidence, source, origin))
    return sorted(out, key=lambda b: (b[0], b[2]))


def board_groups(boards: list[Board], classify) -> list[dict[str, dict[str, str]]]:
    """Per board: kind -> {name: follow/lead} (unclassified names absent). `classify(name, date)` ->
    (weights, organization, step_w, step_o), e.g. arena_meta.Classifier.classify."""
    out = []
    for published, ratings, *_ in boards:
        g = {"open": {}, "china": {}}
        for name in ratings.index:
            w, org, _sw, _so = classify(name, published)
            go = group_open(w)
            if go:
                g["open"][name] = go
            gc = group_china(mo.is_chinese(mo.country(org)))
            if gc:
                g["china"][name] = gc
        out.append(g)
    return out


def _ranking(ratings: pd.Series, groups: dict[str, str], which: str) -> list[str]:
    names = [n for n in ratings.index if groups.get(n) == which]
    return sorted(names, key=lambda n: (-float(ratings[n]), n))


# ------------------------------------------------------------------ Arena (pure)

def lag_in_board(m: pd.Period, bm: Board, gm: dict[str, str], history: list[tuple[pd.Period, Board, dict]],
                 find=lambda n: n) -> dict | None:
    """One version of month m. `history`: [(s, b(s), groups of b(s))] for s = s0..m (s0 = first month whose board has a
    leader model), with b(m) last. `find`: name -> class id."""
    ratings = bm[1]
    follow = _ranking(ratings, gm, FOLLOW)
    lead = _ranking(ratings, gm, LEAD)
    if not follow or not lead:
        return None
    f_top, l_top = float(ratings[follow[0]]), float(ratings[lead[0]])
    by_cls: dict[str, float] = {}
    for n, r in ratings.items():
        c = find(n)
        by_cls[c] = max(by_cls.get(c, -np.inf), float(r))
    out = {"follow_model": follow[0], "follow": f_top, "lead_model": lead[0], "lead": l_top, "gap": l_top - f_top,
           "board": bm[0], "board_source": bm[3], "s0": history[0][0] if history else None, "s_star": None,
           "reach_model": None, "reach": np.nan, "fallbacks": 0, "reach_fallback": False, "missing": 0, "lag": None,
           "status": "", "s_star_source": None}
    if f_top > l_top + TOL:
        out.update(lag=0, status="leads")
        return out
    for s, bs, gs in history:
        rank = _ranking(bs[1], gs, LEAD)
        hit = next(((k, n) for k, n in enumerate(rank) if find(n) in by_cls), None)
        if hit is None:
            out["missing"] += 1
            continue
        k, n = hit
        out["fallbacks"] += int(k > 0)
        r = by_cls[find(n)]
        if r >= f_top - TOL:
            out.update(s_star=s, reach_model=n, reach=r, s_star_source=bs[3], reach_fallback=k > 0)
            break
    if out["s_star"] is None:  # cannot happen: b(m)'s own leader top reaches F(m)
        out["status"] = "no_reach"
        return out
    if out["s_star"] == out["s0"]:
        out["status"] = "censored"
        return out
    out.update(lag=months_between(out["s_star"], m), status="lag")
    return out


def arena_build(boards: list[Board], classify, last_month: pd.Period, find=lambda n: n,
                first_month: pd.Period | None = None) -> pd.DataFrame:
    """Every version of every month: period, known_from, kind, lag, gap, source, gap_source + diagnostics.
    Only versions whose (lag, gap) differ from the month's previous version per kind are kept per series later
    (`arena_series`)."""
    bs = norm_boards(boards)
    groups = board_groups(bs, classify)
    if not bs:
        return pd.DataFrame()
    start = first_month or bs[0][0].to_period("M")
    rows = []
    for m in pd.period_range(start, last_month, freq="M") if start <= last_month else []:
        end = m.end_time.normalize()
        cand = [i for i, b in enumerate(bs) if b[0] <= end]
        if not cand:
            continue
        base = end + pd.Timedelta(days=1)
        days = sorted({base} | {bs[i][2] for i in cand if bs[i][2] > end})
        for day in days:
            known = [i for i in cand if bs[i][2] <= day]  # first version: evidence <= end + 1 day (X20, R23-1)
            if not known:
                continue
            bm = known[-1]  # latest published (ties: latest evidence)
            months = pd.period_range(bs[known[0]][0].to_period("M"), m, freq="M")
            per_s = []
            for s in months:
                ks = [i for i in known if bs[i][0] <= s.end_time.normalize()]
                if ks:
                    per_s.append((s, ks[-1]))
            for kind in KINDS:
                hist, started = [], False
                for s, i in per_s:
                    started = started or any(v == LEAD for v in groups[i][kind].values())
                    if started:
                        hist.append((s, bs[i], groups[i][kind]))
                if not hist:
                    continue
                hist[-1] = (m, bs[bm], groups[bm][kind])
                res = lag_in_board(m, bs[bm], groups[bm][kind], hist, find)
                if res is None:
                    continue
                backfill = res["board_source"] == "backfill" or res["s_star_source"] == "backfill"
                rows.append({"period": str(m), "known_from": max(day, base), "kind": kind,
                             "lag_source": "backfill" if backfill else "release",
                             "gap_source": "backfill" if res["board_source"] == "backfill" else "release", **res})
    return pd.DataFrame(rows)


def arena_series(table: pd.DataFrame, kind: str, column: str) -> pd.DataFrame:
    """Release-dated rows (period, value, known_from, source) of one series from arena_build: a version is kept when
    the value differs from the month's previous kept version. Censored versions carry no value."""
    cols = ["period", "value", "known_from", "source"]
    if table.empty:
        return pd.DataFrame(columns=cols)
    t = table[table["kind"] == kind].sort_values(["period", "known_from"])
    src = "lag_source" if column == "lag" else "gap_source"
    rows = []
    for period, g in t.groupby("period", sort=True):
        prev = None
        for _, r in g.iterrows():
            v = r[column]
            if v is None or (isinstance(v, float) and np.isnan(v)):
                continue
            v = float(v)
            if prev is None or not np.isclose(v, prev, rtol=0, atol=1e-9):
                rows.append((period, v, r["known_from"], r[src]))
                prev = v
    return pd.DataFrame(rows, columns=cols)


# ------------------------------------------------------------------ Epoch ECI (pure)

ECI_COLUMNS = ["model", "date", "eci", "weights", "chinese", "step_weights", "step_country", "open_from",
               "step_release"]


def eci_frame(eci_scores: pd.DataFrame, all_models: pd.DataFrame | None = None,
              curated: dict | None = None, releases: dict | None = None) -> pd.DataFrame:
    """model, date, eci, weights, chinese, step_weights, step_country, open_from, step_release (register order:
    eci_scores.csv, then all_ai_models.csv for the same Model, then model_origin.ECI_MODELS, else left out).

    open_from (open models only) = max(date, weights release), the release from `releases` (default
    model_origin.ECI_WEIGHTS_RELEASE, step_release "curated"), else from the model's `Accessibility notes` in
    all_ai_models.csv ("note"), else the date ("date"). A note that says the weights come later and gives no date
    leaves the model out of the open-vs-closed measure (weights None, step_weights "pending_release")."""
    curated = mo.ECI_MODELS if curated is None else curated
    releases = mo.ECI_WEIGHTS_RELEASE if releases is None else releases
    am = pd.DataFrame(columns=["Model", "Open model weights?", "Country (of organization)"]) if all_models is None \
        else all_models
    am = am.dropna(subset=["Model"]).drop_duplicates("Model").set_index("Model")
    notes = am["Accessibility notes"] if "Accessibility notes" in am.columns else pd.Series(dtype=object)
    rows = []
    for _, r in eci_scores.iterrows():
        model = str(r["Model"])
        eci = pd.to_numeric(r.get("eci"), errors="coerce")
        date = pd.to_datetime(r.get("date"), errors="coerce")
        if pd.isna(eci) or pd.isna(date):
            continue
        grp = r.get("Accessibility group")
        w = {"Open weights": mo.OPEN, "Closed weights": mo.CLOSED}.get(grp if isinstance(grp, str) else "")
        sw = "eci" if w else ""
        if not w and model in am.index:
            w = {"Yes": mo.OPEN, "No": mo.CLOSED}.get(str(am.loc[model, "Open model weights?"]).strip())
            sw = "all_models" if w else ""
        cn = mo.is_chinese(r.get("Country (of organization)"))
        sc = "eci" if cn is not None else ""
        if cn is None and model in am.index:
            cn = mo.is_chinese(am.loc[model, "Country (of organization)"])
            sc = "all_models" if cn is not None else ""
        cur = curated.get(model)
        if cur is not None:
            cw, ccountry, _ref = cur
            if not w and cw:
                w, sw = cw, "curated"
            if cn is None and ccountry:
                cn, sc = mo.is_chinese(ccountry), "curated"
        date = date.normalize()
        open_from, sr = pd.NaT, ""
        if w == mo.OPEN:
            if model in releases:
                release, sr = releases[model][0], "curated"
            else:
                release = mo.weights_release(notes.get(model))
                sr = "note" if release else "date"
            if release == mo.PENDING:
                w, sw, sr = None, "pending_release", "pending"
            else:
                open_from = max(date, pd.Timestamp(release).normalize()) if release else date
        rows.append((model, date, float(eci), w, cn, sw or "none", sc or "none", open_from, sr))
    return pd.DataFrame(rows, columns=ECI_COLUMNS)


def eci_build(frame: pd.DataFrame, kind: str, last_month: pd.Period) -> pd.DataFrame:
    """Monthly lag and gap for one kind: period, lag, gap, follow, lead, follow_model, lead_model, s_star,
    reach_model, status. Months from the first with both groups to last_month."""
    grp = [group_open(w) for w in frame["weights"]] if kind == "open" else [group_china(c) for c in frame["chinese"]]
    f = frame.assign(group=grp).dropna(subset=["group"]).sort_values(["date", "model"])
    cols = ["period", "lag", "gap", "follow", "lead", "follow_model", "lead_model", "s_star", "reach_model", "status"]
    # open vs closed: an open model is a follower from open_from and a leader (closed) from its date until then
    no_dates = pd.Series(pd.NaT, index=f.index, dtype="datetime64[ns]")
    opens = pd.to_datetime(f["open_from"]) if kind == "open" and "open_from" in f else no_dates
    follow = f["group"] == FOLLOW
    f = f.assign(follow_from=opens.fillna(f["date"]).where(follow),
                 lead_until=opens.where(follow & (opens > f["date"])).where(follow, pd.Timestamp.max))
    if f.empty or f["follow_from"].isna().all() or f["lead_until"].isna().all():
        return pd.DataFrame(columns=cols)
    lead_start = f.loc[f["lead_until"].notna(), "date"].min()
    first = max(f["follow_from"].min(), lead_start).to_period("M")
    s0 = lead_start.to_period("M")

    def top(which: str, s: pd.Period):
        end = s.end_time.normalize()
        if which == FOLLOW:
            g = f[f["follow_from"] <= end]
        else:
            g = f[(f["date"] <= end) & (f["lead_until"] > end)]
        if g.empty:
            return np.nan, None
        best = g.sort_values(["eci", "model"], ascending=[False, True]).iloc[0]
        return float(best["eci"]), best["model"]

    lead_by_s = {s: top(LEAD, s) for s in pd.period_range(s0, last_month, freq="M")} if s0 <= last_month else {}
    rows = []
    for t in pd.period_range(first, last_month, freq="M") if first <= last_month else []:
        fv, fm = top(FOLLOW, t)
        lv, lm = lead_by_s[t]
        row = {"period": str(t), "lag": None, "gap": lv - fv, "follow": fv, "lead": lv, "follow_model": fm,
               "lead_model": lm, "s_star": None, "reach_model": None, "status": ""}
        if fv > lv + TOL:
            row.update(lag=0, status="leads")
        else:
            s_star = next(s for s in pd.period_range(s0, t, freq="M") if lead_by_s[s][0] >= fv - TOL)
            row.update(s_star=str(s_star), reach_model=lead_by_s[s_star][1])
            if s_star == s0:
                row["status"] = "censored"
            else:
                row.update(lag=months_between(s_star, t), status="lag")
        rows.append(row)
    return pd.DataFrame(rows, columns=cols)


def eci_values(table: pd.DataFrame, column: str) -> pd.Series:
    """Monthly Series (PeriodIndex) for observations (backfill on first load); censored months are absent."""
    t = table.dropna(subset=[column])
    t = t[t[column].map(lambda v: v is not None)]
    return pd.Series(t[column].astype(float).to_numpy(), index=pd.PeriodIndex(t["period"], freq="M"), dtype=float)


# ------------------------------------------------------------------ fetch

@lru_cache(maxsize=1)
def arena_inputs():
    from ai_tracker.sources import arena, arena_meta

    boards = arena.subset_boards("text")
    meta = arena_meta.meta()
    classes = arena_meta.name_classes(meta)
    clf = arena_meta.Classifier(meta, classes)
    return boards, meta, classes, clf


@lru_cache(maxsize=1)
def arena_table() -> pd.DataFrame:
    from ai_tracker.sources import vintages

    boards, _meta, classes, clf = arena_inputs()
    return arena_build(boards, clf.classify, vintages.last_complete_month(), find=classes.find)


def fetch_arena(kind: str, column: str) -> pd.DataFrame:
    return arena_series(arena_table(), kind, column)


@lru_cache(maxsize=1)
def eci_inputs() -> pd.DataFrame:
    from ai_tracker.sources import epoch_hub as e

    return eci_frame(e._csv(e.benchmark_files(), "eci_scores.csv"), e._csv(e.model_files(), "all_ai_models.csv"))


@lru_cache(maxsize=None)
def eci_table(kind: str) -> pd.DataFrame:
    from ai_tracker.sources import epoch_hub as e

    return eci_build(eci_inputs(), kind, e.last_complete_month())


def fetch_eci(kind: str, column: str) -> pd.Series:
    return eci_values(eci_table(kind), column)


# ------------------------------------------------------------------ catalog

ARENA_LICENSE = ("CC BY 4.0 (LMArena leaderboard dataset card `license: cc-by-4.0`); Space files (elo_results pickles, "
                 "leaderboard_table CSVs) used as dated boards and metadata; credit LMArena")
ECI_LICENSE = ("CC BY 4.0 (Epoch AI README: \"free to use, distribute, and reproduce provided the source and authors "
               "are credited\")")
_ARENA_SRC = "LMArena (HF-dataset + Space-filer)"
_ECI_SRC = "Epoch AI benchmarkhubben (ECI) och modelldatabasen"
_ARENA_NOTE = ("Inom en tavla (Arena text, overall): eftersläpningen är antalet månader sedan den ledande gruppens "
               "front (dess toppmodell i månadens tavla, läst i den aktuella tavlan) först nådde den följande gruppens "
               "topp. Golvet 0 när den följande gruppen leder; censurerad (inget värde) när fronten redan nåddes "
               "första månaden. Klassning ur Arenas egna fält (license, organization), kurerade reserver i "
               "sources/model_origin.py. known_from = senare av tavlans belägg och månadsslut + 1 dag. Katalogserie, "
               "inte kärnserie. Se docs/kallor/g1_oppen_stangd.md")
_ECI_NOTE = ("Epoch ECI, en skala över tiden: eftersläpning = månader sedan den ledande gruppens bästa ECI först "
             "nådde den följande gruppens bästa. Golvet 0, censurerad när fronten nåddes första månaden. Klassning ur "
             "Accessibility group och Country (of organization), reserv all_ai_models.csv. En öppen modell räknas "
             "som öppen från sitt dokumenterade viktsläpp och som stängd före det. ECI skattas om och klassningen är "
             "dagens: historiken är återfylld (source=backfill, known_from nominellt månadsslut + 7 dagar), senare "
             "hämtningar ger revisioner. Kina-måttets värden 2023-09 – 2024-04 är undre gränser. Katalogserie. Se "
             "docs/kallor/g1_oppen_stangd.md")

_DEFS = [
    ("open", "lag", "g1_open_lag_months_{}", "{}: öppna modellers eftersläpning mot stängda", "månader",
     "Hur många månader efter den stängda fronten når de bästa öppna modellerna samma nivå?"),
    ("open", "gap", "g1_open_gap_{}", "{}: stängd topp minus öppen topp", "{}",
     "Hur stort är avståndet mellan bästa stängda och bästa öppna modell (positivt = stängda före)?"),
    ("china", "lag", "g1_china_lag_months_{}", "{}: kinesiska labbs eftersläpning mot övriga", "månader",
     "Hur många månader efter övriga labbs front når de bästa kinesiska modellerna samma nivå?"),
    ("china", "gap", "g1_china_gap_{}", "{}: övrigas topp minus kinesisk topp", "{}",
     "Hur stort är avståndet mellan bästa icke-kinesiska och bästa kinesiska modell (positivt = övriga före)?"),
]


def _specs() -> list[Spec]:
    out = []
    for kind, column, key, label, unit, question in _DEFS:
        out.append(Spec(key=key.format("arena"), branch="G1", label=label.format("Arena"),
                        unit=unit.format("Arena-poäng (samma tavla)"), freq="M", source=_ARENA_SRC,
                        fetch=partial(fetch_arena, kind, column), lag_days=1, license=ARENA_LICENSE, revised=True,
                        publish=True, question=question, note=_ARENA_NOTE))
        out.append(Spec(key=key.format("eci"), branch="G1", label=label.format("ECI"),
                        unit=unit.format("ECI-poäng"), freq="M", source=_ECI_SRC,
                        fetch=partial(fetch_eci, kind, column), lag_days=7, license=ECI_LICENSE, revised=True,
                        publish=True, question=question, note=_ECI_NOTE))
    return out


SPECS = _specs()


# ------------------------------------------------------------------ coverage (metadata only)

def arena_coverage(boards: list[Board], classify) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(board, name) pairs per classification step for weights and country, and the names left out.
    Columns of the first: what, step, pairs, names. Second: name, what, boards (count), first, last."""
    rows, missing = [], []
    for published, ratings, *_ in norm_boards(boards):
        for name in ratings.index:
            w, org, sw, so = classify(name, published)
            cn = mo.is_chinese(mo.country(org))
            sc = so if cn is not None else ("no_country" if org else "none")
            rows.append(("weights", sw, name))
            rows.append(("country", sc, name))
            if not w:
                missing.append((name, "weights", published))
            if cn is None:
                missing.append((name, "country", published))
    df = pd.DataFrame(rows, columns=["what", "step", "name"])
    cov = df.groupby(["what", "step"]).agg(pairs=("name", "size"), names=("name", "nunique")).reset_index()
    ms = pd.DataFrame(missing, columns=["name", "what", "published"])
    left = ms.groupby(["name", "what"]).agg(boards=("published", "size"), first=("published", "min"),
                                            last=("published", "max")).reset_index() if not ms.empty else ms
    return cov, left
