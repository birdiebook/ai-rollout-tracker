"""Assemble the site's data (pure Python dicts, JSON-safe). See ai_tracker.site for the layout and the rules.

Everything a page shows goes through this module, so the licence rule is enforced in one place: a series is shown
with values only when `publishable` (Spec.publish=True; a derived series: all components). A withheld series is
reduced to `withheld_entry` (key, label, source, licence, why), and branch-level aggregates.
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ai_tracker import catalog, config, evaluation, observations, pipeline
from ai_tracker.nowcast import horizon, horizon_live, intervals, n1, n3, n4, n5, n6
from ai_tracker.nowcast import n2
from ai_tracker.nowcast import n2 as n2_live
from ai_tracker.site import flow as F
from ai_tracker.site import probabilities as P
from ai_tracker.state import branch as BR
from ai_tracker.state import register as R
from ai_tracker.state import snapshot as S
from ai_tracker.state.measures import Context, measure_path

RECON_LABEL = "rekonstruerad historik, inte ett skarpt underlag"
LIVE_LABEL = "skarp ögonblicksbild"
DEFAULT_REPO = "birdiebook/ai-rollout-tracker"
HISTORY_FROM = "2023-01"

# docs/plan.md, section 3 (the question each branch answers)
BRANCH_QUESTIONS = {
    "G1": "Ökar förmågan i samma takt?",
    "G2": "Hur snabbt faller priset per förmåga?",
    "G3": "Hur brett och djupt används AI?",
    "G4": "Går det att tjäna pengar på det?",
    "G5": "Hur stor är capex, och hur finansieras den?",
    "G6": "Hur går leveranskedjan?",
    "G7": "Räcker kraft och nät?",
    "G8": "Syns effekter i ekonomin?",
    "G9": "Hur snabbt rör sig fältet?",
}

# Derived series (register.DERIVED) have no Spec: label and unit for the site.
DERIVED_META = {
    "capex_ocf_hyp4": ("Capex i procent av operativt kassaflöde, MSFT+GOOGL+AMZN+META", "%"),
}

# Registered variants (docs/mattregister.md sections 3 and 4, B2 entries), in Swedish for the nowcast page.
NOWCAST_INFO = {
    "n1": {
        "title": "Capex för de fyra största molnbolagen",
        "frequency": "kvartal",
        "origin_rule": "kvartalets slut + 20 dagar, före den första rapporten",
        "results_doc": "docs/resultat/n1.md",
        "variants": {
            "B0": "slumpvandring: förra kvartalet",
            "B1": "drift: förra kvartalet × medel av de fyra senaste kvartalens tillväxt",
            "V1": "B1 + bridge (OLS) på import från Taiwan och datacenterbyggande",
            "V2": "som V1, med ridge",
            "B2": "bolagens guidance (Meta, Alphabet), annars B1",
            "B3": "B2 korrigerad för bolagens systematiska avvikelse mot sin egen guidance",
            "DF": "B1 + OLS på faktormodellens förändring (skuggvariant)",
        },
    },
    "n2": {
        "title": "TSMC:s månadsintäkt",
        "frequency": "månad",
        "origin_rule": "dag 5 i månaden efter, före publiceringen runt den 10:e",
        "results_doc": "docs/resultat/n2.md",
        "variants": {
            "B0": "slumpvandring: förra månaden",
            "B1": "säsongsnaiv tillväxt",
            "V1": "B1 + ridge på import från Taiwan",
            "B2": "TSMC:s kvartalsguidance utslagen per månad",
            "B3": "B2 korrigerad för TSMC:s systematiska avvikelse mot sin egen guidance",
            "DF": "B2 + OLS på faktormodellens förändring (skuggvariant)",
        },
    },
    "n3": {
        "title": "Nvidias datacenterintäkter",
        "frequency": "kvartal (Nvidias räkenskapskvartal, märkt med kalenderkvartalet för mittpunkten)",
        "origin_rule": "räkenskapskvartalets slut + 14 dagar, före rapporten",
        "results_doc": "docs/resultat/n3.md",
        "variants": {
            "B0": "slumpvandring: förra kvartalet",
            "B1": "drift: förra kvartalet × medel av de fyra senaste kvartalens tillväxt",
            "B2": "Nvidias intäktsguidance (mittpunkt) × senast kända datacenterandel (villkorad: granskning R5)",
            "DF": "B1 + OLS på faktormodellens förändring (skuggvariant)",
        },
    },
    "n4": {
        "title": "Molnintäkter (AWS + Google Cloud + Microsoft Cloud)",
        "frequency": "kvartal",
        "origin_rule": "kvartalets slut + 20 dagar, före den första rapporten",
        "results_doc": "docs/resultat/n4.md",
        "target_label": "Molnintäkter, summa AWS + Google Cloud + Microsoft Cloud", "unit": "MUSD",
        "source": "SEC EDGAR XBRL (segmentintäkter)", "license": "offentlig information (SEC)",
        "components": list(n4.COMPONENTS),
        "variants": {
            "B0": "slumpvandring: förra kvartalet",
            "B1": "drift: förra kvartalet × medel av de fyra senaste kvartalens tillväxt",
            "V1": "B1 + OLS på senast kända kvartalstillväxt i RPO-summan",
            "DF": "B1 + OLS på faktormodellens förändring (skuggvariant)",
        },
    },
    "n5": {
        "title": "Andel amerikanska företag som använder AI (BTOS, aktiv regim)",
        "frequency": "varannan vecka",
        "origin_rule": "dagen före den schemalagda publiceringen. B1 kräver 7 tidigare publiceringar i samma "
                       "frågeregim, och regimen v3 har högst 6 cykler, så ingen skarp prognos görs i v3",
        "results_doc": "docs/resultat/n5.md",
        "decimals": 1, "error_unit": "procentenheter",
        "variants": {
            "B0": "senaste värdet",
            "B1": "drift över de 6 senaste cyklerna inom regimen",
        },
    },
    "n6": {
        "title": "Kontrakterad efterfrågan (RPO, MSFT + GOOGL + AMZN + ORCL)",
        "frequency": "kvartal",
        "origin_rule": "kvartalets slut + 20 dagar",
        "results_doc": "docs/resultat/n6.md",
        "variants": {
            "B0": "slumpvandring: förra kvartalet",
            "B1": "drift: förra kvartalet × medel av de fyra senaste kvartalens tillväxt",
            "V1": "B1 + OLS på senast kända kvartalstillväxt i molnintäkterna (N4)",
        },
    },
}
NOWCAST_DERIVED = {n4.TARGET: n4.COMPONENTS}
NOWCAST_MODULES = {"n1": (n1.TARGET, n1.VARIANTS + ["DF"], n1.CHAMPION),
                   "n2": (n2.TARGET, n2.VARIANTS + ["DF"], n2_live.CHAMPION),
                   "n3": (n3.TARGET, n3.VARIANTS + ["DF"], n3.CHAMPION),
                   "n4": (n4.TARGET, n4.VARIANTS + ["DF"], n4.CHAMPION),
                   "n5": (n5.key(n5.VERSIONS[-1]), n5.VARIANTS, n5.CHAMPION),
                   "n6": (n6.TARGET, n6.VARIANTS, n6.CHAMPION)}

# Per-series fields copied from a measure (state.measures.measure) to the site. Anything not listed stays out.
SERIES_FIELDS = ("series", "entry", "resolved", "method", "freq", "measure_freq", "latest_period", "known_from",
                 "sources", "level", "pace_unit", "pace", "change_in_pace", "pace_percentile", "change_percentile",
                 "n_pace", "n_change", "surprise", "surprise_basis", "sd_change", "deadband", "direction", "flag",
                 "reason", "own_snapshot_months", "valid")
FORECAST_FIELDS = ("nowcast", "target", "month", "quarter", "origin", "registered_origin", "unit", "champion",
                   "value", "variants")


def repo_url() -> str:
    return f"https://github.com/{os.environ.get('GITHUB_REPOSITORY') or DEFAULT_REPO}"


def utc_today() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(timezone.utc).date())


# ------------------------------------------------------------------ licences


def publishable(key: str | None, ctx: Context) -> bool:
    """May values of `key` be shown? Spec.publish=True; a derived series needs every component publishable."""
    if not key:
        return False
    if key in NOWCAST_DERIVED:  # a nowcast target summed from components (N4): every component publishable
        return all(publishable(c, ctx) for c in NOWCAST_DERIVED[key])
    if key in ctx.derived:
        num, den = ctx.derived[key][:2]
        return publishable(num, ctx) and publishable(den, ctx)
    spec = ctx.specs.get(key)
    return bool(spec and spec.publish)


def short_license(text: str) -> str:
    """A short label for a catalog licence text (the full text is on the method page)."""
    t = (text or "").strip()
    low = t.lower()
    if not t or low.startswith("unverified"):
        return "inte kontrollerad"
    if low.startswith("derived"):
        parts = [p for p, k in (("MIT (LiteLLM)", "mit"), ("CC BY 4.0 (Epoch AI)", "cc by 4.0")) if k in low]
        return " + ".join(parts) or "härledd"
    if low.startswith("cc by 4.0"):
        return "CC BY 4.0"
    if low.startswith("cc0"):
        return "CC0 1.0"
    if "sec.gov" in low or low.startswith("sec"):
        return "offentlig information (SEC)"
    if "public domain" in low or "17 u.s.c" in low:
        return "public domain (amerikansk myndighet)"
    return t.split(" (")[0][:60]


def source_family(source: str) -> str:
    return (source or "").split(",")[0].split(" (")[0].strip()


def why_withheld(spec: catalog.Spec | None) -> str:
    if spec is None:
        return "okänd serie"
    if spec.withheld_reason.strip():
        return spec.withheld_reason.strip()
    if spec.license.strip().lower().startswith("unverified"):
        return "licensen är inte kontrollerad"
    return "inte godkänd för publicering i katalogen (publish=False)"


def notices(key: str, ctx: Context) -> list[str]:
    """Notices the terms of `key`'s sources require to be displayed with its data (Spec.notice), for a derived series
    or a nowcast target those of its components."""
    if key in NOWCAST_DERIVED:
        keys = list(NOWCAST_DERIVED[key])
    elif key in ctx.derived:
        keys = list(ctx.derived[key][:2])
    else:
        spec = ctx.specs.get(key)
        keys = [key, *(spec.components if spec else ())]
    out: list[str] = []
    for k in keys:
        spec = ctx.specs.get(k)
        if spec and spec.notice and spec.notice not in out:
            out.append(spec.notice)
    return out


def site_notices(ctx: Context) -> list[str]:
    """The notices of publishable series that have rows in the table: shown in the footer of every page (the Census
    Data API's terms ask for its notice to be displayed prominently, review R13-2)."""
    t = ctx.table
    present = set(t["series"].unique()) if len(t) else set()
    return sorted({s.notice for s in ctx.specs.values() if s.notice and s.publish and s.key in present})


def series_meta(key: str, ctx: Context) -> dict:
    if key in ctx.derived:
        num, den = ctx.derived[key][:2]
        label, unit = DERIVED_META.get(key, (key, ""))
        specs = [ctx.specs.get(num), ctx.specs.get(den)]
        sources = sorted({s.source for s in specs if s})
        lic = sorted({short_license(s.license) for s in specs if s})
        return {"label": label, "unit": unit, "question": "", "source": "; ".join(sources),
                "license": "; ".join(lic), "derived_from": [num, den]}
    spec = ctx.specs.get(key)
    if spec is None:
        return {"label": key, "unit": "", "question": "", "source": "", "license": ""}
    return {"label": spec.label, "unit": spec.unit, "question": spec.question, "source": spec.source,
            "license": short_license(spec.license)}


def withheld_entry(key: str, ctx: Context, counted: bool) -> dict:
    """All the site says about a withheld series: name, source, licence, why, and whether it counts in the index."""
    spec = ctx.specs.get(key)
    if key in ctx.derived:
        bad = [k for k in ctx.derived[key][:2] if not publishable(k, ctx)]
        reason = "härledd ur serier som inte publiceras: " + ", ".join(bad)
    elif spec is not None and spec.components and not spec.publish:
        bad = [k for k in spec.components if not publishable(k, ctx)]
        reason = "härledd ur serier som inte publiceras: " + ", ".join(bad) if bad else why_withheld(spec)
    else:
        reason = why_withheld(spec)
    return {"key": key, "label": spec.label if spec else key, "source": spec.source if spec else "",
            "license": short_license(spec.license) if spec else "", "why": reason, "counted": counted}


# ------------------------------------------------------------------ numbers


def _num(x, digits: int = 5):
    """Round to `digits` significant digits; NaN/inf/None -> None."""
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(x):
        return None
    if x == 0:
        return 0.0
    return float(f"{x:.{digits}g}")


CHART_YEARS = 10  # the charts show the last ten years; percentiles and the SD use the full history


def path_json(path: pd.DataFrame | None, when=None) -> dict | None:
    """Pace and change-in-pace history: periods where the pace exists, the last CHART_YEARS years before `when`."""
    if path is None or path.empty:
        return None
    p = path[path["pace"].notna() | path["change"].notna()]
    if when is not None and len(p):
        first = str(pd.Timestamp(when).year - CHART_YEARS)
        p = p[[str(i)[:4] > first for i in p.index]]
    if p.empty:
        return None
    return {"periods": [str(i) for i in p.index], "pace": [_num(v) for v in p["pace"]],
            "change": [_num(v) for v in p["change"]]}


def series_entry(m: dict, when, ctx: Context, with_path: bool = True) -> dict:
    out = {k: (_num(m[k]) if isinstance(m[k], float) else m[k]) for k in SERIES_FIELDS if k in m}
    key = m.get("series")
    out.update(series_meta(key, ctx))
    out["key"] = key
    if with_path:
        try:
            _, path = measure_path(key, when, ctx)
        except (KeyError, ValueError):
            path = None
        out["path"] = path_json(path, when)
    return out


# ------------------------------------------------------------------ record and history


def live_snapshots(snapshots_dir: Path) -> dict[str, dict]:
    """Committed monthly snapshots (the record), by month."""
    out = {}
    for f in sorted(Path(snapshots_dir).glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("branches"):
            d["_file"] = f"snapshots/{f.name}"
            out[str(d.get("snapshot") or f.stem)] = d
    return out


def last_month_end(today) -> pd.Timestamp:
    today = pd.Timestamp(today).normalize()
    return today if S.is_month_end(today) else S.month_end(today.to_period("M") - 1)


def next_month_end(today) -> pd.Timestamp:
    return S.month_end(pd.Timestamp(today).to_period("M"))


def aggregate(b: dict) -> dict:
    """Index, state and counts of a branch record. `index`/`state` are the official rule of the record
    (`rule_version`; v2 = one vote per source family from 2026-11-30). A record written before v2 has no
    rule_version: its index is v1, and index_v1/state_v1 repeat it."""
    out = {k: b.get(k) for k in ("index", "state", "n_series", "n_up", "n_neutral", "n_down")}
    v1 = b.get("v1") or {"index": b.get("index"), "state": b.get("state")}
    out.update(rule_version=b.get("rule_version") or "v1", n_families=b.get("n_families"),
               index_v1=v1.get("index"), state_v1=v1.get("state"))
    return out


def families_view(b: dict, ctx: Context) -> tuple[list[dict], int]:
    """The counted source families of a branch (index v2) whose counted series may all be shown, with their vote,
    and the number of counted families with a withheld series (counted in the index, neither named nor voted here)."""
    shown, hidden = [], 0
    for f in b.get("families") or []:
        keys = f.get("series") or []
        if not keys or f.get("vote") is None:
            continue
        if all(publishable(k, ctx) for k in keys):
            shown.append({"family": f["family"], "series": list(keys), "n_series": len(keys),
                          "vote": _num(f["vote"], 4)})
        else:
            hidden += 1
    return shown, hidden


class Record:
    """The current branch states and the monthly index history (live snapshots where they exist)."""

    def __init__(self, ctx: Context, snapshots_dir: Path, today, history_from: str = HISTORY_FROM):
        self.ctx = ctx
        self.today = pd.Timestamp(today).normalize()
        self.live = live_snapshots(snapshots_dir)
        self._computed: dict[str, dict] = {}
        if self.live:
            self.month = max(self.live)
            snap = self.live[self.month]
            self.when = pd.Timestamp(snap["date"])
            self.kind, self.label, self.file = "skarp", LIVE_LABEL, snap["_file"]
            self.branches = snap["branches"]
            self.selected = (snap.get("rules") or {}).get("g1_selected_benchmarks")
            self.reconciliations = snap.get("reconciliations")  # None in a snapshot written before A5
        else:
            self.when = last_month_end(self.today)
            self.month = str(self.when.to_period("M"))
            self.kind, self.label, self.file = "rekonstruerad", RECON_LABEL, None
            self.branches = self.compute(self.month)
            self.selected = ctx.selection(self.when)
            self.reconciliations = S._clean(BR.reconciliations(self.when, ctx))
        first_live = min(self.live) if self.live else None
        self.first_live = first_live
        self.first_live_date = (self.live[first_live]["date"] if first_live else
                                str(max(next_month_end(self.today), S.month_end("2026-11")).date()))
        start = min(pd.Period(history_from, "M"), pd.Period(self.month, "M"))
        self.history: dict[str, list[dict]] = {code: [] for code in catalog.BRANCHES}
        for month in pd.period_range(start, self.month, freq="M"):
            m = str(month)
            if m in self.live:
                branches, kind = self.live[m]["branches"], "skarp"
            elif first_live is None or m < first_live:
                branches, kind = self.compute(m), "rekonstruerad"
            else:
                continue  # a month after the first live snapshot without one: a gap, never reconstructed
            for code in catalog.BRANCHES:
                if code in branches:
                    self.history[code].append({"month": m, "kind": kind, **aggregate(branches[code])})

    def compute(self, month: str) -> dict:
        if month not in self._computed:
            self._computed[month] = S._clean(S.compute(S.month_end(month), self.ctx))
        return self._computed[month]

    def previous(self, code: str) -> dict | None:
        h = self.history[code]
        prev = str(pd.Period(self.month, "M") - 1)
        return next((p for p in h if p["month"] == prev), None)

    def meta(self) -> dict:
        return {"kind": self.kind, "label": self.label, "month": self.month, "date": str(self.when.date()),
                "file": self.file, "first_live_date": self.first_live_date,
                "live_months": sorted(self.live), "recon_label": RECON_LABEL}


# ------------------------------------------------------------------ views


def change_vs_previous(cur: dict, prev: dict | None) -> dict:
    if prev is None:
        return {"previous": None, "delta_index": None, "state_changed": None}
    d = (None if cur.get("index") is None or prev.get("index") is None else _num(cur["index"] - prev["index"], 4))
    return {"previous": prev, "delta_index": d, "state_changed": cur.get("state") != prev.get("state")}


def branch_view(code: str, rec: Record) -> dict:
    ctx, when = rec.ctx, rec.when
    b = rec.branches.get(code, {})
    counted, not_counted, withheld = [], [], []
    for m in b.get("series_used", []):
        if publishable(m.get("series"), ctx):
            counted.append(series_entry(m, when, ctx))
        else:
            withheld.append(withheld_entry(m["series"], ctx, counted=True))
    for m in b.get("series_not_counted", []):
        key = m.get("series")
        if key is None:
            not_counted.append({"key": None, "entry": m.get("entry"), "reason": m.get("reason", ""), "label": m.get("entry")})
        elif publishable(key, ctx):
            not_counted.append(series_entry(m, when, ctx))
        else:
            withheld.append(withheld_entry(key, ctx, counted=False))
    cur = aggregate(b)
    families, families_withheld = families_view(b, ctx)
    view = {"code": code, "name": catalog.BRANCHES[code], "question": BRANCH_QUESTIONS.get(code, ""), **cur,
            "families": families, "n_families_withheld": families_withheld,
            **change_vs_previous(cur, rec.previous(code)), "n_withheld": len(withheld),
            "n_withheld_counted": sum(w["counted"] for w in withheld), "has_core": bool(R.core_entries(code, ctx.core)),
            "counted": counted, "not_counted": not_counted, "withheld": withheld, "history": rec.history[code]}
    if code == "G1" and rec.selected is not None:
        view["selected_benchmarks"] = list(rec.selected)
    return view


def reconciliation_view(rec: Record) -> dict:
    """The A5 reconciliations for the method page: level, pace and change in pace per publishable series, from the
    same record as the branches (the live snapshot, or the reconstruction). Not part of any branch."""
    doc = rec.reconciliations
    if not doc:
        return {"available": False, "series": [], "withheld": []}
    shown, withheld = [], []
    for m in doc.get("series", []):
        key = m.get("series")
        if publishable(key, rec.ctx):
            shown.append(series_entry(m, rec.when, rec.ctx, with_path=False))
        elif key:
            withheld.append(withheld_entry(key, rec.ctx, counted=False))
    return {"available": True, "group": doc.get("group"), "note": doc.get("note"), "date": str(rec.when.date()),
            "kind": rec.kind, "series": shown, "withheld": withheld}


def overview(rec: Record, branches: dict[str, dict]) -> dict:
    tiles = []
    for code, v in branches.items():
        tiles.append({k: v[k] for k in ("code", "name", "question", "index", "state", "n_series", "n_up", "n_neutral",
                                        "n_down", "rule_version", "n_families", "index_v1", "state_v1", "previous",
                                        "delta_index", "state_changed", "n_withheld", "n_withheld_counted",
                                        "has_core")}
                     | {"history": [{k: h[k] for k in ("month", "kind", "index", "state", "n_series", "n_families",
                                                       "index_v1", "state_v1")}
                                    for h in v["history"]]})
    return {"record": rec.meta(), "branches": tiles}


def _target_history(key: str, ctx: Context, when) -> dict | None:
    if not publishable(key, ctx):
        return None
    s = observations.as_of(key, when, ctx.rows(key))
    if s.empty:
        return None
    s = s[s.index >= s.index.max() - (40 if s.index.freqstr.startswith("M") else 14)]
    return {"periods": [str(p) for p in s.index], "values": [_num(v, 6) for v in s.to_numpy()]}


def next_origin(nowcast: str, today, root: Path, horizon_days: int = 200,
                schedule_file: Path | None = None) -> tuple[str, str] | None:
    """The next forecast day without a file under `root`. `schedule_file`: N5's BTOS schedule (Context.btos_schedule)."""
    day = pd.Timestamp(today).normalize()
    for i in range(horizon_days):
        d = pipeline.due_for(nowcast, day + pd.Timedelta(days=i), schedule_file)
        if d is not None and not d.path(root).exists():
            return str(d.origin.date()), d.period
    return None


def nowcasts(ctx: Context, forecasts_dir: Path, today, calibration: dict | None = None) -> dict:
    forecasts_dir = Path(forecasts_dir)
    try:
        scores = pipeline.score(forecasts_dir, ctx.table)
    except Exception as e:  # noqa: BLE001 - a scoring failure must not take the site down; say so on the page
        scores, error = {}, f"{type(e).__name__}: {e}"
    else:
        error = None
    out = []
    for sub, (target, variants, champion) in NOWCAST_MODULES.items():
        info = NOWCAST_INFO[sub]
        files = []
        for f in sorted((forecasts_dir / sub).glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            rec = {k: d[k] for k in FORECAST_FIELDS if k in d}
            rec["value"] = _num(rec.get("value"), 6)
            rec["variants"] = {k: _num(v, 6) for k, v in (rec.get("variants") or {}).items()}
            rec["period"] = d.get("quarter") or d.get("month") or d.get("period")
            rec["file"] = f"forecasts/{sub}/{f.name}"
            if intervals.ENABLED:  # grind G-C: the champion's stored central intervals, in levels (no error pool)
                rec["intervals"] = _champion_intervals(d)
            files.append(rec)
        df = scores.get(sub)
        rows = [] if df is None or df.empty else [
            {k: (_num(v, 6) if isinstance(v, float) else v) for k, v in r.items()} for r in df.to_dict("records")]
        scored = [r for r in rows if r.get("status") == "utfall"]
        summary = []
        for v in ["champion", *variants]:
            e = [r.get(f"err_{v}") for r in scored if r.get(f"err_{v}") is not None]
            summary.append({"variant": v, "n": len(e), "mae": _num(sum(abs(x) for x in e) / len(e), 4) if e else None,
                            "bias": _num(sum(e) / len(e), 4) if e else None})
        coverage = _coverage(scored, variants) if intervals.ENABLED else []
        spec = ctx.specs.get(target)
        nxt = next_origin(sub, today, forecasts_dir, schedule_file=ctx.btos_schedule)
        out.append({
            "id": sub, "label": sub.upper(), "title": info["title"], "target": target,
            "target_label": spec.label if spec else info.get("target_label", target),
            "unit": spec.unit if spec else info.get("unit", ""),
            "source": spec.source if spec else info.get("source", ""),
            "license": short_license(spec.license) if spec else info.get("license", ""),
            "decimals": info.get("decimals", 0), "error_unit": info.get("error_unit", "100 × log"),
            "frequency": info["frequency"], "origin_rule": info["origin_rule"], "results_doc": info["results_doc"],
            "champion": champion, "shadows": [v for v in variants if v != champion],
            "variants": [{"id": v, "text": info["variants"].get(v, v)} for v in variants],
            "next_origin": nxt[0] if nxt else None, "next_period": nxt[1] if nxt else None,
            "forecasts": files, "scorecard": rows, "summary": summary, "scorecard_error": error,
            "coverage": coverage, "interval_levels": [intervals.level_key(L) for L in intervals.LEVELS]
            if intervals.ENABLED else [],
            "history": _target_history(target, ctx, today),
            "backtest_calibration": (calibration or {}).get(sub),
        })
    return {"nowcasts": out, "horizons": horizons(ctx, forecasts_dir, today)}


def horizons(ctx: Context, forecasts_dir: Path, today) -> dict:
    """D2 (horizons 1-8, shadow): the newest live file's paths and fan per target (values only for a publishable
    target), and the per-h scorecard summary. Before the first live file: only the rule and the next origin."""
    forecasts_dir = Path(forecasts_dir)
    error = None
    try:
        latest = horizon_live.latest(forecasts_dir)
        scores = horizon_live.score(forecasts_dir, ctx.table)
    except Exception as e:  # noqa: BLE001 - a failure must not take the site down; say so on the page
        latest, scores, error = None, pd.DataFrame(), f"{type(e).__name__}: {e}"
    nxt = next_origin("d2", today, forecasts_dir, horizon_days=400)
    targets = []
    for name, tg in horizon.TARGETS.items():
        show = publishable(tg.key, ctx)
        tp = ((latest or {}).get("targets") or {}).get(name)
        rec = {"id": f"d2-{name}", "name": name, "target": tg.key, "label": tg.label, "unit": horizon_live.UNIT,
               "publishable": show, "models": list(tg.models), "champion_by_group": horizon_live.CHAMPION[name],
               "base": tp.get("base") if tp else None, "fan": None, "paths": [], "history": None, "summary": []}
        if show and tp and tp.get("base"):
            fan = horizon_live.band(tp)
            rec["fan"] = {"periods": fan["periods"], "champion": fan["champion"],
                          "values": [_num(v, 6) for v in fan["values"]],
                          "intervals": {k: {"lo": [_num(v, 6) for v in iv["lo"]], "hi": [_num(v, 6) for v in iv["hi"]]}
                                        for k, iv in fan["intervals"].items()}}
            for i, (hs, p) in enumerate(sorted(tp["paths"].items(), key=lambda kv: int(kv[0]))):
                rec["paths"].append({"h": int(hs), "quarter": p["quarter"], "champion": p["champion"],
                                     "value": _num(p.get("value"), 6),
                                     "models": {m: _num(v, 6) for m, v in (p.get("models") or {}).items()},
                                     "interval_80": [rec["fan"]["intervals"]["80"]["lo"][i + 1],
                                                     rec["fan"]["intervals"]["80"]["hi"][i + 1]]})
            rec["history"] = _target_history(tg.key, ctx, today)
        if show and len(scores):
            rec["summary"] = [{k: (_num(v, 4) if isinstance(v, float) else v) for k, v in r.items()}
                              for r in horizon_live.summary(scores, name) if r["n"]]
        targets.append(rec)
    return {"first_live": str(horizon_live.FIRST_LIVE.date()), "origin": (latest or {}).get("origin"),
            "file": (latest or {}).get("file"), "next_origin": nxt[0] if nxt else None,
            "next_period": nxt[1] if nxt else None, "groups": {g: list(hs) for g, hs in horizon.GROUPS.items()},
            "interval_levels": [intervals.level_key(L) for L in intervals.LEVELS], "targets": targets,
            "error": error}


def _champion_intervals(d: dict) -> dict | None:
    """{"50": [lo, hi], "80": ..., "95": ...} of the champion's stored distribution, or None."""
    m = ((d.get("distribution") or {}).get("models") or {}).get(d.get("champion")) or {}
    iv = m.get("intervals")
    if not iv:
        return None
    return {k: [_num(lo, 6), _num(hi, 6)] for k, (lo, hi) in iv.items()}


def _coverage(scored: list[dict], variants) -> list[dict]:
    """Per variant: n scored with a stored distribution, coverage per level and mean CRPS (scorecard rows)."""
    out = []
    for v in ["champion", *variants]:
        g = [r for r in scored if r.get(f"crps_{v}") is not None]
        row = {"variant": v, "n": len(g), "crps": _num(sum(r[f"crps_{v}"] for r in g) / len(g), 4) if g else None}
        for L in intervals.LEVELS:
            k = intervals.level_key(L)
            hits = [r[f"hit_{k}_{v}"] for r in g if r.get(f"hit_{k}_{v}") is not None]
            row[f"coverage_{k}"] = _num(sum(hits) / len(hits), 3) if hits else None
            row[f"band_{k}"] = [_num(x, 3) for x in intervals.binomial_band(len(hits), L)] if hits else None
        out.append(row)
    return out


def method(ctx: Context) -> dict:
    families: dict[tuple[str, str], dict] = {}
    for s in ctx.specs.values():
        fam = families.setdefault((source_family(s.source), s.license), {
            "source": source_family(s.source), "license": short_license(s.license), "license_text": s.license,
            "branches": set(), "n_series": 0, "n_published": 0})
        fam["branches"].add(s.branch)
        fam["n_series"] += 1
        fam["n_published"] += int(bool(s.publish))
    rows = sorted(({**f, "branches": sorted(f["branches"])} for f in families.values()),
                  key=lambda f: (min(f["branches"]), f["source"]))
    withheld = sorted((withheld_entry(s.key, ctx, counted=False) | {"branch": s.branch}
                       for s in ctx.specs.values() if not s.publish), key=lambda w: (w["branch"], w["key"]))
    for w in withheld:
        w.pop("counted")
    return {"sources": rows, "withheld": withheld, "n_series": len(ctx.specs),
            "n_published": sum(bool(s.publish) for s in ctx.specs.values()),
            "index_families": index_families(ctx)}


def index_families(ctx: Context) -> list[dict]:
    """The registered source-family table (register 2026-11-24, index v2) per branch: family id, its expanded core
    entries that may be shown (and placeholders), and the number of withheld entries (not named). A family whose id
    is itself a withheld series key (an unlisted entry is its own family, named after it) is left out: the withheld
    list names that series."""
    out = []
    for code in catalog.BRANCHES:
        fam_of = R.entry_families(code, ctx.core, ctx.families)
        for fam in dict.fromkeys(fam_of.values()):
            if (fam in ctx.specs or fam in ctx.derived) and not publishable(fam, ctx):
                continue
            entries = [e for e, f in fam_of.items() if f == fam]
            shown = [e for e in entries if "<" in e or publishable(e, ctx)]
            out.append({"branch": code, "family": fam, "entries": shown, "n_withheld": len(entries) - len(shown)})
    return out


def letters(letters_dir: Path) -> dict:
    """The monthly letters (docs/manadsbrev/<YYYY-MM>.md), newest first: month, title, kind, file and the Markdown.
    The letters are written by ai_tracker.letter under the same licence rule as the site."""
    from ai_tracker import letter as L  # lazy: the letter module imports this one

    out = []
    for f in sorted(Path(letters_dir).glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].md"), reverse=True):
        md = f.read_text(encoding="utf-8")
        meta = L.parse(md)
        out.append({"month": f.stem, "month_sv": L.month_sv(f.stem), "title": meta["title"], "kind": meta["kind"],
                    "file": f"docs/manadsbrev/{f.name}", "page": f"manadsbrev-{f.stem}.html", "markdown": md})
    return {"letters": out}


def reports(reports_dir: Path) -> dict:
    """The quarterly reports (docs/kvartalsrapport/<YYYYQn>.md), newest first: quarter, title, kind, file and the
    Markdown. Written by ai_tracker.quarterly under the same licence rule as the site."""
    from ai_tracker import quarterly as Q  # lazy: the report module imports this one

    out = []
    for f in sorted(Path(reports_dir).glob("[0-9][0-9][0-9][0-9]Q[1-4].md"), reverse=True):
        md = f.read_text(encoding="utf-8")
        meta = Q.parse(md)
        out.append({"quarter": f.stem, "quarter_sv": Q.quarter_sv(f.stem), "title": meta["title"],
                    "kind": meta["kind"], "file": f"docs/kvartalsrapport/{f.name}",
                    "page": f"kvartalsrapport-{f.stem.lower()}.html", "markdown": md})
    return {"reports": out}


def build_meta(rec: Record) -> dict:
    t = rec.ctx.table
    return {"built_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "git_sha": evaluation.git_sha(),
            "repo": repo_url(), "table_max_fetched_at": (str(pd.Timestamp(t["fetched_at"].max()).date())
                                                         if len(t) else None),
            "notices": site_notices(rec.ctx), "record": rec.meta()}


def assemble(ctx: Context | None = None, snapshots_dir: Path | None = None, forecasts_dir: Path | None = None,
             today=None, history_from: str = HISTORY_FROM, letters_dir: Path | None = None,
             reports_dir: Path | None = None, calibration: dict | None = None) -> dict:
    """Every JSON document of the site: {"oversikt": ..., "gren/G1": ..., "flode": ..., "prognoser": ...,
    "metod": ..., "manadsbrev": ..., "kvartalsrapport": ..., "build": ...}. `calibration` (nowcast id -> backtest
    calibration, see site.probabilities) is computed from the table when not given."""
    ctx = ctx or Context(observations.load())
    today = pd.Timestamp(today).normalize() if today is not None else utc_today()
    rec = Record(ctx, Path(snapshots_dir or S.SNAPSHOTS), today, history_from)
    branches = {code: branch_view(code, rec) for code in catalog.BRANCHES}
    if calibration is None:
        calibration = P.backtest_calibration(ctx.table) if intervals.ENABLED else {}
    prog = nowcasts(ctx, Path(forecasts_dir or config.REPO / "forecasts"), today, calibration)
    prog["regime"] = P.regime_view(rec.live, lambda k: publishable(k, ctx))
    prog["record"] = rec.meta()
    docs = {"oversikt": overview(rec, branches), "flode": F.flow_view(rec, branches, prog, calibration, sys.modules[__name__]),
            "prognoser": prog,
            "metod": {**method(ctx), "reconciliations": reconciliation_view(rec)}, "manadsbrev": letters(Path(letters_dir or config.REPO / "docs" / "manadsbrev")),
            "kvartalsrapport": reports(Path(reports_dir or config.REPO / "docs" / "kvartalsrapport")),
            "build": build_meta(rec)}
    for code, v in branches.items():
        docs[f"gren/{code}"] = {"record": rec.meta(), **v}
    return docs
