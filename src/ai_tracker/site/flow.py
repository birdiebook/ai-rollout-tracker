"""The flow view (track E2): the chain L1 -> L9 of docs/steg2/plan.md, section 2, as one page (flode.html).

Per lead: the state of its branch(es) from the same record as the rest of the site (live snapshot or the labelled
reconstruction), 1-3 key series with level, pace and change in pace (the registered measures, as_of the record date),
and the relevant nowcast (the champion's latest live forecast with its 80 % interval, else the backtest summary).
Between the leads: the A5 reconciliation ratios, placed by the lead span registered in series.avstamning (a ratio
spanning La-Lb with a < b sits between L(b-1) and Lb; a ratio within one lead is shown in that lead).

The key series are a fixed presentation choice (which series illustrate a lead), not a selection on the data; they
are listed here so they can be reviewed. Withheld series (publish=False) are only named, in the withheld list.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ai_tracker.series import avstamning
from ai_tracker.state import branch as BR
from ai_tracker.state.measures import measure


@dataclass(frozen=True)
class Lead:
    code: str
    name: str
    short: tuple[str, ...]  # the name in at most two lines for the chain diagram
    content: str
    branches: tuple[str, ...]
    series: tuple[str, ...]  # catalog keys or register entries (placeholders resolve through the branch record)
    nowcasts: tuple[str, ...]


LEADS: list[Lead] = [
    Lead("L1", "Förmåga och kostnad", ("Förmåga och", "kostnad"), "Vad modellerna klarar och vad det kostar",
         ("G1", "G2"), ("g1_epoch_eci_frontier", "g1_epoch_train_compute_frontier", "g2_price_at_capability_gpqa"), ()),
    Lead("L2", "Användning", ("Användning",), "Hur mycket AI används, av vem", ("G3",),
         ("btos_ai_use_<aktiv regim>", "g3_pypi_openai_wed", "g3_wiki_chatgpt_en"), ("n5",)),
    Lead("L3", "Intäkter", ("Intäkter",), "Pengar som kommer in", ("G4",),
         ("rev_aws", "rev_google_cloud", "rev_msft_cloud"), ("n4",)),
    Lead("L4", "Kontrakterad efterfrågan", ("Kontrakterad", "efterfrågan"),
         "Pengar som är utlovade men inte intäktsförda (RPO)", ("G4",), ("rpo_hyp4",), ("n6",)),
    Lead("L5", "Investeringar och finansiering", ("Investeringar,", "finansiering"), "Capex, kassaflöde och skuld",
         ("G5",), ("capex_hyp4", "capex_ocf_hyp4", "debt_issued_hyp4"), ("n1",)),
    Lead("L6", "Halvledare och minne", ("Halvledare", "och minne"), "Chips, minne, utrustning", ("G6",),
         ("tsmc_revenue_m", "rev_nvda_datacenter", "us_imports_tw_m"), ("n2", "n3")),
    Lead("L7", "El och byggen", ("El och", "byggen"), "Fysisk kapacitet", ("G7", "G5"),
         ("us_constr_datacenter", "eia930_avg_pjm_dom_m", "us_elec_sales_com_va_m"), ()),
    Lead("L8", "Effekter", ("Effekter",), "Arbete och produktivitet", ("G8",), ("ai_postings_share_us_d",), ()),
    Lead("L9", "Forskning och förväntningar", ("Forskning,", "förväntningar"), "Fältets tempo och omvärldens förväntningar",
         ("G9",), ("g9_arxiv_cs_lg", "g9_epoch_notable_models", "g9_epoch_open_weights_share"), ()),
]
LEAD_INDEX = {lead.code: i for i, lead in enumerate(LEADS)}

RECON_SHORT = {"x_capex_cloud": "Capex / moln", "x_rpo_cover": "RPO / capex", "x_nvda_capex": "Nvidia / capex",
               "x_debt_capex": "Skuld / capex", "x_capex_ocf": "Capex / OCF",
               "x_dep_rev": "Avskrivningar / intäkter", "x_capcost_rev_r08": "Kapitalkostnad (8 %) / intäkter",
               "x_capcost_rev_r12": "Kapitalkostnad (12 %) / intäkter", "x_dep_capex": "Avskrivningar / capex",
               "x_dep_rev_aws": "AWS: avskrivningar / intäkter"}


def lead_span(key: str) -> tuple[int, int] | None:
    """(first, last) lead number of a reconciliation from series.avstamning ("L3–L5" -> (3, 5))."""
    r = avstamning.BY_KEY.get(key)
    nums = [int(x) for x in re.findall(r"L(\d)", r.lead)] if r else []
    if not nums:
        return None
    return min(nums), max(nums)


def _find(rec_branches: dict, name: str) -> tuple[dict | None, str | None, bool]:
    """(measure, branch, counted) of a key or register entry in the record's branches."""
    for code, b in rec_branches.items():
        for lst, counted in (("series_used", True), ("series_not_counted", False)):
            for m in b.get(lst, []) or []:
                if m.get("series") == name or (m.get("entry") == name and m.get("series")):
                    return m, code, counted
    return None, None, False


def key_series(name: str, rec, D) -> dict:
    """One key series: the record's measure (or the same measure engine as_of the record date for a series outside
    the core lists), through the site's licence rule."""
    ctx = rec.ctx
    m, code, counted = _find(rec.branches, name)
    if m is None:
        if "<" in name or (name not in ctx.specs and name not in ctx.derived):
            return {"missing": True, "entry": name}
        m = measure(name, rec.when, ctx)
        stale = BR.stale_reason(name, rec.when, ctx)
        if stale and m.get("valid"):
            m["valid"], m["reason"] = False, stale
        code = None
    key = m.get("series")
    if not D.publishable(key, ctx):
        return {"withheld": D.withheld_entry(key, ctx, counted=counted)}
    out = D.series_entry(m, rec.when, ctx, with_path=True)
    out.update(counted=counted, branch=code, in_core=code is not None)
    return out


def nowcast_summary(n: dict, cal: dict | None) -> dict:
    """The lead's nowcast: the latest live forecast (champion value, 80 % interval) and the backtest summary."""
    latest = None
    fc = [f for f in n.get("forecasts") or [] if f.get("value") is not None]
    if fc:
        f = sorted(fc, key=lambda f: str(f.get("period")))[-1]
        latest = {"period": f.get("period"), "origin": f.get("origin"), "champion": f.get("champion"),
                  "value": f.get("value"), "interval_80": (f.get("intervals") or {}).get("80"), "file": f.get("file")}
    champ = n.get("champion")
    bt = None
    if cal:
        row = next((r for r in cal.get("rows", []) if r["model"] == champ), None)
        bt = {"model": champ, "mae": cal.get("champion_mae"), "error": cal.get("error"),
              **({k: row.get(k) for k in ("n", "first", "last", "crps", "calibrated", "coverage_80", "band_80")}
                 if row else {})}
    return {"id": n["id"], "label": n["label"], "title": n["title"], "unit": n.get("unit"),
            "decimals": n.get("decimals", 0), "error_unit": n.get("error_unit"), "champion": champ,
            "latest": latest, "next_origin": n.get("next_origin"), "next_period": n.get("next_period"),
            "results_doc": n.get("results_doc"), "backtest": bt}


def recon_entry(m: dict, rec, D) -> dict:
    key = m.get("series")
    span = lead_span(key)
    r = avstamning.BY_KEY.get(key)
    base = {"key": key, "short": RECON_SHORT.get(key, key), "span": list(span) if span else None,
            "lead": r.lead if r else None}
    if not D.publishable(key, rec.ctx):
        return {**base, "withheld": D.withheld_entry(key, rec.ctx, counted=False)}
    e = D.series_entry(m, rec.when, rec.ctx, with_path=True)
    e.update(base, question=r.question if r else e.get("question"))
    return e


def flow_view(rec, branch_views: dict, nowcast_doc: dict, calibration: dict, D) -> dict:
    """The JSON document behind flode.html. `D` is ai_tracker.site.data (passed in to avoid an import cycle)."""
    nowcasts = {n["id"]: n for n in nowcast_doc.get("nowcasts", [])}
    withheld: list[dict] = []
    seen: set[str] = set()

    def hold(w: dict):
        if w["key"] not in seen:
            seen.add(w["key"])
            withheld.append(w)

    leads = []
    for lead in LEADS:
        series, n_hidden = [], 0
        for name in lead.series:
            s = key_series(name, rec, D)
            if s.get("missing"):
                continue
            if "withheld" in s:
                hold(s["withheld"])
                n_hidden += 1
                continue
            series.append(s)
        states = []
        for code in lead.branches:
            v = branch_views.get(code, {})
            states.append({"code": code, "name": v.get("name"), "state": v.get("state"), "index": v.get("index"),
                           "n_series": v.get("n_series"), "n_up": v.get("n_up"), "n_neutral": v.get("n_neutral"),
                           "n_down": v.get("n_down"), "n_withheld_counted": v.get("n_withheld_counted"),
                           "has_core": v.get("has_core"), "delta_index": v.get("delta_index"),
                           "state_changed": v.get("state_changed")})
        leads.append({"code": lead.code, "name": lead.name, "short": list(lead.short), "content": lead.content,
                      "branches": states, "series": series, "n_withheld": n_hidden,
                      "nowcasts": [nowcast_summary(nowcasts[k], calibration.get(k)) for k in lead.nowcasts
                                   if k in nowcasts]})
    recons = []
    doc = rec.reconciliations or {}
    for m in doc.get("series", []):
        e = recon_entry(m, rec, D)
        if "withheld" in e:  # only the lead span and a count stay outside the withheld list
            hold(e["withheld"])
            e = {"hidden": True, "span": e["span"], "lead": e["lead"]}
        recons.append(e)
    return {"record": rec.meta(), "leads": leads, "reconciliations": recons,
            "reconciliations_available": bool(doc), "withheld": withheld}
