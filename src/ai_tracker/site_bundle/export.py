"""Assemble the bundle's documents from ai_tracker.site.data (the same record, views and licence rule as the old site).

Every view is built by site.data / site.flow / site.probabilities; this module only re-cuts them into one document per
page or entity, adds the per-series documents (levels, measures, measure history, versions) and the overview facts,
and runs every value through the licence gate (site_bundle.gate) before it is returned.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ai_tracker import catalog, config, evaluation, observations
from ai_tracker.nowcast import intervals
from ai_tracker.site import data as D
from ai_tracker.site import flow as F
from ai_tracker.site import probabilities as P
from ai_tracker.site_bundle import gate as G
from ai_tracker.site_bundle import vintages as V
from ai_tracker.state import register as R
from ai_tracker.state import snapshot as S
from ai_tracker.state.measures import Context, measure_path, rule_for

STATUS = {"skarp": "live", "rekonstruerad": "reconstructed"}
STATES = [R.STATE_ACCEL, R.STATE_STABLE, R.STATE_BRAKE, R.STATE_FEW_FAMILIES, R.STATE_FEW, "inga registrerade kärnserier"]
# Fields of a measure kept per month in a series' measure history (columnar, see series_doc).
HISTORY_FIELDS = ("latest_period", "known_from", "pace", "change_in_pace", "pace_percentile", "change_percentile",
                  "direction", "valid")


class GateError(RuntimeError):
    """The licence scan found a withheld series outside a withheld list: nothing is written."""


# ------------------------------------------------------------------ helpers


def record_meta(rec: D.Record) -> dict:
    m = rec.meta()
    return {"status": STATUS[m["kind"]], **m}


def _n(x, digits: int = 5):
    return D._num(x, digits)


def _sv_number(n: int) -> str:
    return {0: "ingen", 1: "en"}.get(n, str(n))


def headline(rec: D.Record, branches: dict[str, dict]) -> dict:
    """The data behind the start page's sentence: counts per state and the state changes since last month."""
    counts = {s: 0 for s in STATES}
    changes = []
    for code, v in branches.items():
        counts[v["state"]] = counts.get(v["state"], 0) + 1
        prev = v.get("previous")
        if prev is not None and v.get("state_changed"):
            changes.append({"code": code, "name": v["name"], "from": prev.get("state"), "to": v["state"]})
    with_state = counts[R.STATE_ACCEL] + counts[R.STATE_STABLE] + counts[R.STATE_BRAKE]
    parts = [f"{_sv_number(counts[R.STATE_ACCEL])} accelererar",
             f"{_sv_number(counts[R.STATE_STABLE])} {'är stabil' if counts[R.STATE_STABLE] == 1 else 'är stabila'}",
             f"{_sv_number(counts[R.STATE_BRAKE])} bromsar in"]
    sentence = f"Av {with_state} grenar med tillstånd: {', '.join(parts[:2])} och {parts[2]}."
    if changes:
        change = "Sedan förra månaden: " + "; ".join(f"{c['code']} {c['from']} → {c['to']}" for c in changes) + "."
    else:
        change = "Inget tillstånd har ändrats sedan förra månaden."
    return {"month": rec.month, "n_branches": len(branches), "n_with_state": with_state, "counts": counts,
            "changes": changes, "sentence": sentence, "change_sentence": change}


def stripes(rec: D.Record) -> dict:
    """State stripes: branch x month, columnar (index, state), and the record kind per month."""
    months = sorted({h["month"] for hs in rec.history.values() for h in hs})
    kinds = {}
    rows = []
    for code in catalog.BRANCHES:
        by = {h["month"]: h for h in rec.history[code]}
        for m, h in by.items():
            kinds[m] = h["kind"]
        rows.append({"code": code, "name": catalog.BRANCHES[code],
                     "index": [_n(by[m]["index"], 4) if m in by else None for m in months],
                     "state": [by[m]["state"] if m in by else None for m in months],
                     "n_series": [by[m]["n_series"] if m in by else None for m in months],
                     "n_families": [by[m].get("n_families") if m in by else None for m in months],
                     "index_v1": [_n(by[m].get("index_v1"), 4) if m in by else None for m in months],
                     "state_v1": [by[m].get("state_v1") if m in by else None for m in months]})
    return {"months": months, "kind": [kinds.get(m) for m in months], "rows": rows,
            "thresholds": {"braking_at_most": R.BRAKING, "accelerating_at_least": R.ACCELERATING}}


def month_branches(rec: D.Record, month: str) -> dict | None:
    if month in rec.live:
        return rec.live[month]["branches"]
    return rec._computed.get(month)


def measure_history(rec: D.Record) -> dict[str, dict]:
    """key -> columnar history of the record's measures per month (live snapshot or the reconstruction), for the
    series the branches measured that month. Exactly what each month's record held, never recomputed."""
    months = sorted({h["month"] for hs in rec.history.values() for h in hs})
    acc: dict[str, list[tuple[str, str, bool, dict]]] = {}
    for m in months:
        branches = month_branches(rec, m) or {}
        kind = "skarp" if m in rec.live else "rekonstruerad"
        for b in branches.values():
            for lst, counted in (("series_used", True), ("series_not_counted", False)):
                for x in b.get(lst) or []:
                    key = x.get("series")
                    if key:
                        acc.setdefault(key, []).append((m, kind, counted, x))
    out = {}
    for key, items in acc.items():
        seen, rows = set(), []
        for m, kind, counted, x in items:
            if m in seen:  # a series in two branches' lists: the first one (counted lists come first per branch)
                continue
            seen.add(m)
            rows.append((m, kind, counted, x))
        doc = {"months": [r[0] for r in rows], "kind": [r[1] for r in rows], "counted": [r[2] for r in rows]}
        for f in HISTORY_FIELDS:
            vals = [r[3].get(f) for r in rows]
            doc[f] = [_n(v) if isinstance(v, float) else v for v in vals]
        out[key] = doc
    return out


def _levels(key: str, ctx: Context, as_of) -> dict | None:
    s = observations.as_of(key, as_of, ctx.rows(key))
    s = s.dropna()
    if s.empty:
        return None
    return {"as_of": str(pd.Timestamp(as_of).date()), "periods": [str(p) for p in s.index],
            "values": [V._r(v) for v in s.to_numpy()]}


def _row_sources(rows: pd.DataFrame, as_of) -> dict:
    r = rows[rows["known_from"] <= pd.Timestamp(as_of)]
    counts = {str(k): int(v) for k, v in r["source"].value_counts().items()}
    b = r[r["source"] == "backfill"]
    return {"counts": counts, "backfill_last_known": str(pd.Timestamp(b["known_from"].max()).date()) if len(b) else None}


def licence_block(key: str, ctx: Context) -> dict:
    meta = D.series_meta(key, ctx)
    spec = ctx.specs.get(key)
    if spec is not None:
        text = spec.license
    else:
        parts = [ctx.specs.get(k) for k in ctx.derived.get(key, ())[:2]]
        text = "; ".join(f"{p.key}: {p.license}" for p in parts if p)
    return {"short": meta["license"], "text": text,
            "attribution": f"Källa: {meta['source']}. Licens: {meta['license']}. Bearbetning: ai-rollout-tracker."}


def series_doc(key: str, rec: D.Record, history: dict[str, dict], recon_keys: set[str], core_keys: set[str]) -> dict:
    ctx, when, today = rec.ctx, rec.when, rec.today
    spec = ctx.specs.get(key)
    meta = D.series_meta(key, ctx)
    m, branch_code, counted = F._find(rec.branches, key)
    in_record = m is not None
    try:
        computed, path = measure_path(key, when, ctx)
    except (KeyError, ValueError):
        computed, path = None, None
    if m is None:
        m = computed
    measure = None
    if m is not None:
        measure = {k: (_n(m[k]) if isinstance(m[k], float) else m[k]) for k in D.SERIES_FIELDS if k in m}
    try:
        rule = rule_for(key, ctx)
        agg = rule.agg
    except KeyError:
        rule, agg = None, None
    rows = ctx.rows(key)
    freq = spec.freq if spec else (ctx.derived[key][4] if key in ctx.derived else None)
    branch = spec.branch if spec else (ctx.derived[key][5] if key in ctx.derived else None)
    return {
        "key": key, "label": meta["label"], "unit": meta["unit"], "freq": freq, "branch": branch,
        "branch_name": catalog.BRANCHES.get(branch, ""), "question": meta["question"], "source": meta["source"],
        "source_family": D.source_family(meta["source"]), "license": licence_block(key, ctx),
        "revised": bool(spec.revised) if spec else True, "lag_days": spec.lag_days if spec else None,
        "derived_from": meta.get("derived_from"), "core": key in core_keys, "reconciliation": key in recon_keys,
        "in_record": in_record, "counted": bool(counted) if in_record else False, "record_branch": branch_code,
        "method": rule.method if rule else None, "aggregation": agg if freq in R.SUBMONTHLY else None,
        "measure_as_of": str(when.date()), "measure": measure, "measure_path": D.path_json(path, when),
        "measure_history": history.get(key),
        "levels": _levels(key, ctx, today), "rows": _row_sources(rows, today) if len(rows) else None,
        "versions": V.encode(rows, today, agg=agg if freq == "D" else None),
    }


def series_index_entry(doc: dict) -> dict:
    lv, vs, m = doc.get("levels") or {}, doc.get("versions") or {}, doc.get("measure") or {}
    return {"key": doc["key"], "label": doc["label"], "branch": doc["branch"], "freq": doc["freq"], "unit": doc["unit"],
            "source_family": doc["source_family"], "license": doc["license"]["short"], "core": doc["core"],
            "counted": doc["counted"], "reconciliation": doc["reconciliation"],
            "first_period": (lv.get("periods") or [None])[0], "latest_period": (lv.get("periods") or [None])[-1],
            "n_versions": vs.get("n_versions", 0), "direction": m.get("direction"), "valid": m.get("valid")}


def publishable_series(ctx: Context) -> list[str]:
    keys = [k for k, s in ctx.specs.items() if s.publish]
    keys += [k for k in ctx.derived if G.publishable(k, ctx)]
    return sorted(k for k in set(keys) if G.publishable(k, ctx))


def core_keys(ctx: Context) -> set[str]:
    return {k for code in catalog.BRANCHES for k in R.core_entries(code, ctx.core) if "<" not in k}


def _gate_nowcast(n: dict, ctx: Context) -> dict:
    """A nowcast whose target is not publishable keeps only its rule and name (none today; the scan checks)."""
    if G.publishable(n.get("target"), ctx):
        return {"publishable": True, **n}
    keep = ("id", "label", "title", "frequency", "origin_rule", "results_doc", "champion", "shadows", "variants",
            "next_origin", "next_period", "decimals", "error_unit", "interval_levels")
    return {"publishable": False, **{k: n.get(k) for k in keep}, "target": None,
            "withheld": [D.withheld_entry(n["target"], ctx, counted=False)]}


def method_doc(ctx: Context, rec: D.Record) -> dict:
    m = D.method(ctx)
    fams = m.get("index_families") or []
    branches = []
    for code, name in catalog.BRANCHES.items():
        shown, withheld = [], []
        for e in R.core_entries(code, ctx.core):
            if "<" in e or G.publishable(e, ctx):
                shown.append(e)
            else:
                withheld.append(D.withheld_entry(e, ctx, counted=True) | {"branch": code})
        branches.append({"code": code, "name": name, "question": D.BRANCH_QUESTIONS.get(code, ""),
                         "core": shown, "withheld": withheld,
                         "families": [{k: f[k] for k in ("family", "entries", "n_withheld")}
                                      for f in fams if f["branch"] == code]})
    leads = []
    for lead in F.LEADS:
        leads.append({"code": lead.code, "name": lead.name, "short": list(lead.short), "content": lead.content,
                      "branches": list(lead.branches),
                      "series": [s for s in lead.series if "<" in s or G.publishable(s, ctx)],
                      "n_series_withheld": sum(1 for s in lead.series if "<" not in s and not G.publishable(s, ctx)),
                      "nowcasts": list(lead.nowcasts)})
    rules = {"deadband_sd": R.DEADBAND, "accelerating_at_least": R.ACCELERATING, "braking_at_most": R.BRAKING,
             "index_rule": R.INDEX_RULE, "min_families": R.MIN_FAMILIES,
             "min_series": R.MIN_SERIES, "min_history": R.MIN_HISTORY, "pace_lag": R.PACE_LAG,
             "change_lag": R.CHANGE_LAG, "doubling_window_months": R.DOUBLING_WINDOW,
             "own_snapshot_months": R.OWN_SNAPSHOT_MONTHS,
             "backfill_gated": sorted(k for k in R.BACKFILL_GATED if G.publishable(k, ctx) or k not in ctx.specs),
             "backfill_flagged": sorted(k for k in R.BACKFILL_FLAGGED if G.publishable(k, ctx))}
    nowcasts = [{"id": k, "title": v["title"], "frequency": v["frequency"], "origin_rule": v["origin_rule"],
                 "results_doc": v["results_doc"], "variants": [{"id": a, "text": b} for a, b in v["variants"].items()]}
                for k, v in D.NOWCAST_INFO.items()]
    try:
        reg_sha = S.register_sha256()
    except OSError:
        reg_sha = None
    return {"record": record_meta(rec), "register": {"file": "docs/mattregister.md", "sha256": reg_sha},
            "rules": rules, "states": STATES, "branches": branches, "leads": leads, "nowcasts": nowcasts,
            "interval_levels": [intervals.level_key(L) for L in intervals.LEVELS] if intervals.ENABLED else [],
            "reconciliations": {"group": R.RECONCILIATION_GROUP,
                                "keys": [k for k in ctx.reconciliations if G.publishable(k, ctx)]},
            "labels": {"reconstructed": D.RECON_LABEL, "live": D.LIVE_LABEL},
            "sources": m["sources"], "n_series": m["n_series"], "n_published": m["n_published"],
            "n_withheld": len(m["withheld"])}


def letters_docs(letters_dir: Path, reports_dir: Path) -> dict[str, dict]:
    letters = D.letters(letters_dir)["letters"]
    reports = D.reports(reports_dir)["reports"]
    docs = {}
    idx_l, idx_r = [], []
    for x in letters:
        path = f"letters/{x['month']}.json"
        docs[path] = {"month": x["month"], "month_sv": x["month_sv"], "title": x["title"], "kind": x["kind"],
                      "file": x["file"], "markdown": x["markdown"]}
        idx_l.append({k: x[k] for k in ("month", "month_sv", "title", "kind", "file")} | {"doc": path})
    for x in reports:
        path = f"reports/{x['quarter']}.json"
        docs[path] = {"quarter": x["quarter"], "quarter_sv": x["quarter_sv"], "title": x["title"], "kind": x["kind"],
                      "file": x["file"], "markdown": x["markdown"]}
        idx_r.append({k: x[k] for k in ("quarter", "quarter_sv", "title", "kind", "file")} | {"doc": path})
    docs["letters.json"] = {"letters": idx_l, "reports": idx_r}
    return docs


# ------------------------------------------------------------------ assemble


def assemble(ctx: Context | None = None, snapshots_dir: Path | None = None, forecasts_dir: Path | None = None,
             today=None, history_from: str = D.HISTORY_FROM, letters_dir: Path | None = None,
             reports_dir: Path | None = None, calibration: dict | None = None,
             series: list[str] | None = None) -> dict[str, dict]:
    """Every document of the bundle except the manifest: {relative path: JSON document}. `series` limits the
    per-series documents (default: every publishable series)."""
    ctx = ctx or Context(observations.load())
    today = pd.Timestamp(today).normalize() if today is not None else D.utc_today()
    rec = D.Record(ctx, Path(snapshots_dir or S.SNAPSHOTS), today, history_from)
    meta = record_meta(rec)
    branches = {code: D.branch_view(code, rec) for code in catalog.BRANCHES}
    if calibration is None:
        calibration = P.backtest_calibration(ctx.table) if intervals.ENABLED else {}
    forecasts_dir = Path(forecasts_dir or config.REPO / "forecasts")
    prog = D.nowcasts(ctx, forecasts_dir, today, calibration)
    regime = P.regime_view(rec.live, lambda k: G.publishable(k, ctx))
    flow = F.flow_view(rec, branches, prog, calibration, sys.modules["ai_tracker.site.data"])
    nowcasts = [_gate_nowcast(n, ctx) for n in prog["nowcasts"]]

    docs: dict[str, dict] = {}
    calendar = [{"id": n["id"], "label": n["label"], "title": n["title"], "champion": n["champion"],
                 "next_origin": n["next_origin"], "next_period": n["next_period"],
                 "n_live": len(n.get("forecasts") or [])} for n in nowcasts]
    hz = prog["horizons"]
    calendar.append({"id": "d2", "label": "D2", "title": "Prognoser 1–8 kvartal (skugga)", "champion": None,
                     "next_origin": hz.get("next_origin"), "next_period": hz.get("next_period"),
                     "n_live": 1 if hz.get("file") else 0})
    m = D.method(ctx)
    tiles = D.overview(rec, branches)["branches"]
    for t in tiles:
        t.pop("history", None)
    docs["overview.json"] = {
        "record": meta, "headline": headline(rec, branches), "branches": tiles, "stripes": stripes(rec),
        "calendar": calendar,
        "regime": {"available": regime["available"],
                   "blocks": [{"block": b["block"], "label": b["label"], **{k: b["latest"].get(k) for k in
                               ("month", "p_slow", "state", "shift")}} for b in regime["blocks"]]},
        "facts": {"n_series": m["n_series"], "n_published": m["n_published"], "n_withheld": len(m["withheld"]),
                  "n_nowcasts": len(nowcasts),
                  "table_max_fetched_at": (str(pd.Timestamp(ctx.table["fetched_at"].max()).date())
                                           if len(ctx.table) else None)},
    }
    docs["flow.json"] = {**flow, "record": meta}
    for code, v in branches.items():
        docs[f"branch/{code}.json"] = {"record": meta, **v}
    for n in nowcasts:
        docs[f"nowcast/{n['id']}.json"] = {"record": meta, **n}
    docs["nowcast/d2.json"] = {"record": meta, **hz}
    docs["regime.json"] = {"record": meta, **regime}
    docs["method.json"] = method_doc(ctx, rec)
    docs["withheld.json"] = {"withheld": m["withheld"], "n": len(m["withheld"])}
    docs.update(letters_docs(Path(letters_dir or config.REPO / "docs" / "manadsbrev"),
                             Path(reports_dir or config.REPO / "docs" / "kvartalsrapport")))

    history = measure_history(rec)
    recon = set(ctx.reconciliations)
    core = core_keys(ctx)
    keys = publishable_series(ctx) if series is None else [k for k in series if G.publishable(k, ctx)]
    index = []
    for key in keys:
        d = series_doc(key, rec, history, recon, core)
        docs[f"series/{key}.json"] = d
        index.append(series_index_entry(d))
    docs["series/index.json"] = {"as_of": str(today.date()), "n": len(index), "series": index}

    bad = G.scan(docs, ctx)
    if bad:
        raise GateError(f"{len(bad)} licence violations, first: {bad[:5]}")
    return docs


def build_info(git_sha: str | None = None, built_utc: str | None = None) -> dict:
    return {"built_utc": built_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "git_sha": git_sha or evaluation.git_sha(), "repo": D.repo_url()}
