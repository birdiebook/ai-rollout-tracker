"""D2 live: the registered forecasts 1-8 quarters ahead (nowcast/horizon.py) as a shadow product in the live register
(docs/mattregister.md "2026-11-23 - D2: prognoser 1-8 kvartal (förregistrering, F-E7)" and "2026-11-24 - D2: n i
holdout-testet räknas i prognosdagar (före öppning)", with F-E6, G-C and F-C7).

    python -m ai_tracker.pipeline d2-live      on a registered origin (quarter end + 20 days) from 2027-01-20

What is written, once per origin: forecasts/d2/<quarter>.json (quarter = the calendar quarter that ended 20 days
before the origin, as N1/N4), never rewritten (engine.write_live opens with mode "x"). It holds, for both targets
(capex_hyp4 and rev_cloud3), every model's path for h = 1-8 (target quarter = L + h, L = the latest quarter known at
the origin), the champion per horizon, V_kedja as a shadow and each model's stored error distribution per h where the
pool allows (G-C, F-C7).

Holdout (G-E). D2's holdout stays closed: with n < 8 origins in every horizon group no holdout test is made, and
V_kedja goes straight into the live register as a shadow (F-E6). So nothing here computes a forecast at an origin
inside the holdout (2025-07-01 to the day before FIRST_LIVE): the live forecast passes guard.check(live=True), which
allows only an origin on or after guard.LIVE_FROM["D2"], and the error pools hold only
- the development origins' errors (origins <= 2025-06-30, horizon.frame), and
- the errors of committed live D2 files,
each from its outcome's first-vintage known_from and only if that is on or before the live origin (F-C4, F-C7).
Development-origin errors whose outcome became known after 2025-06-30 enter the live pool like any other error once
known; they are not a holdout evaluation (the holdout is defined by origin), and they are never reported as MAE.

Champion per horizon group (fixed here, the instruction "best baseline"; docs/resultat/d2_utveckling.md): the
baseline with the lowest mean MAE over the group's horizons in the development run (on the baselines' common rows).
capex: B2 for h1-2 and h3-4, B1 for h5-8; cloud: B1 for every group (B2 is registered for capex only). If the
champion is not available at an origin the file falls back to B1, then B0, and says so. V_kedja is a shadow
everywhere; promotion would need a new register entry (the live register is the final test, G-E).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from ai_tracker.factor import guard
from ai_tracker.nowcast import engine, horizon, intervals, n1

DIR = "d2"
FIRST_LIVE = guard.LIVE_FROM[horizon.FAMILY]
UNIT = "MUSD"
SHADOW = "V_kedja"
CHAMPION = {  # development run 2026-11-24, mean MAE per group on the baselines' common rows (d2_utveckling.md)
    "capex": {"h1–2": "B2", "h3–4": "B2", "h5–8": "B1"},
    "cloud": {"h1–2": "B1", "h3–4": "B1", "h5–8": "B1"},
}
FALLBACK = ("B1", "B0")
REGISTER_REF = ('docs/mattregister.md, "2026-11-23 – D2: prognoser 1–8 kvartal" and "2026-11-24 – D2: n i '
                'holdout-testet räknas i prognosdagar"')
STATUS_SCORED = "utfall"


def group_of(h: int) -> str:
    return next(g for g, hs in horizon.GROUPS.items() if h in hs)


def is_origin(day) -> bool:
    """A registered D2 origin (calendar quarter end + 20 days) on or after the first live origin."""
    day = pd.Timestamp(day).normalize()
    return day >= FIRST_LIVE and n1.origin_for(n1.target_quarter(day)) == day


def file_stem(origin) -> str:
    return str(n1.target_quarter(pd.Timestamp(origin)))


def _finite(x) -> bool:
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x) and x > 0


def champion_for(target: str, h: int, levels: dict) -> tuple[str, str]:
    """(model, note): the registered champion of h's group, else the first available of FALLBACK."""
    c = CHAMPION[target][group_of(h)]
    for m in (c, *FALLBACK):
        if _finite(levels.get(m, {}).get(h)):
            return m, "" if m == c else f"{c} not available; fell back to {m}"
    return c, f"{c} not available, and no fallback either"


def _known(table: pd.DataFrame, origin) -> pd.DataFrame:
    return table[pd.to_datetime(table["known_from"]) <= pd.Timestamp(origin)]


# ------------------------------------------------------------------ error pools (F-C7)


def _files(live_dir) -> list[Path]:
    return sorted(Path(live_dir).glob("*.json")) if live_dir else []


def live_frame(files, t: pd.DataFrame, target: horizon.Target, origin) -> pd.DataFrame:
    """Errors of committed live D2 files whose outcome (first vintage in `t`) is known at `origin`, in the layout of
    horizon.frame. A file at or after `origin` is ignored, and an outcome known at the file's own origin never
    enters (it would not be a forecast). Break quarters (F-B8) are not scored."""
    origin = pd.Timestamp(origin)
    outcomes = engine.first_vintages(t, target.key)
    brk = horizon.target_breaks(t, target)
    rows = []
    for f in files:
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        o = pd.Timestamp(d["origin"])
        tgt = (d.get("targets") or {}).get(target.name) or {}
        if d.get("nowcast") != "D2" or o >= origin or not tgt.get("base"):
            continue
        base = pd.Period(tgt["base"], freq=horizon.Q)
        for hs, p in (tgt.get("paths") or {}).items():
            h, q = int(hs), base + int(hs)
            if q not in outcomes.index or q in brk:
                continue
            kf = pd.Timestamp(outcomes.at[q, "known_from"])
            if kf <= o or kf > origin:
                continue
            y = float(outcomes.at[q, "value"])
            row = {"origin": o, "base": base, "h": h, "quarter": q, "outcome": y, "outcome_known_from": kf,
                   "n_train": (tgt.get("n_train") or {}).get(hs, 0)}
            for m in target.models:
                lv = (p.get("models") or {}).get(m)
                row[m] = engine.log_error(float(lv), y) if _finite(lv) else float("nan")
            rows.append(row)
    cols = ["origin", "base", "h", "quarter", "outcome", "outcome_known_from", "n_train", *target.models]
    return pd.DataFrame(rows, columns=cols)


def pools(t: pd.DataFrame, target: horizon.Target, origin, live_dir=None) -> dict:
    """h -> (errors per model, known_from, live index), index = the forecast's origin date. `t` is the prepared table
    of the rows known at `origin`. Development origins only (<= DEV_END, horizon.dev_origins) plus live files."""
    dev = horizon.frame(t, target, horizon.dev_origins())
    live = live_frame(_files(live_dir), t, target, origin)
    both = pd.concat([x for x in (dev, live) if len(x)], ignore_index=True) if len(dev) or len(live) else dev
    out = {}
    for h in horizon.HORIZONS:
        g = both[both["h"] == h] if len(both) else both
        idx = pd.Index(pd.to_datetime(g["origin"]).dt.date.astype(str), name="origin")
        e = pd.DataFrame(g[list(target.models)].to_numpy(dtype=float), index=idx, columns=list(target.models))
        kf = pd.Series(pd.to_datetime(g["outcome_known_from"]).to_numpy(), index=idx)
        live_idx = idx[(pd.to_datetime(g["origin"]) > guard.DEV_END).to_numpy()]
        out[h] = (e, kf, live_idx)
    return out


def distributions(path: horizon.Path, t: pd.DataFrame, origin, live_dir=None) -> dict:
    """h -> the `distribution` block (intervals.live_block) of every model for that horizon."""
    pl = pools(t, path.target, origin, live_dir)
    out = {}
    for h in horizon.HORIZONS:
        logs = {m: (100 * math.log(v) if _finite(v := path.levels.get(m, {}).get(h)) else float("nan"))
                for m in path.target.models}
        e, kf, live_idx = pl[h]
        out[str(h)] = intervals.live_block(logs, e, kf, origin, live_index=live_idx)
    return out


# ------------------------------------------------------------------ live file


def _clean(x):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else x


def _mark_inputs(info: engine.InfoSet, target: horizon.Target, L) -> None:
    """The input log: the target's last five quarters (B0, B1) and V_kedja's regressor series at L and L-4."""
    info.mark(target.key, [p for p in pd.period_range(L - 4, L, freq=horizon.Q) if p in info.get(target.key).index])
    for key in (horizon.RPO.key, horizon.X_KEY):
        s = info.get(key)
        info.mark(key, [p for p in (L - 4, L) if p in s.index])


def target_payload(t: pd.DataFrame, target: horizon.Target, origin, live_dir=None) -> dict:
    info = engine.InfoSet(t, origin)
    p = horizon.forecast(t, target, origin, horizon.target_breaks(t, target), live=True, info=info)
    out = {"target": target.key, "label": target.label, "unit": UNIT, "models": list(target.models),
           "shadow": [SHADOW], "champion_by_group": CHAMPION[target.name],
           "base": str(p.base) if p.base is not None else None, "base_value": None, "paths": {},
           "unavailable": p.reasons, "n_train": {str(h): n for h, n in p.n_train.items()},
           "v_kedja_coef": {str(h): c for h, c in p.coef.items()}, "v_kedja_regressors": p.regressors,
           "b2_sources": {c: {str(h): s for h, s in v.items()} for c, v in p.b2_sources.items()}}
    if p.base is None:
        return out
    out["base_value"] = _clean(float(info.get(target.key)[p.base]))
    for h in horizon.HORIZONS:
        champ, note = champion_for(target.name, h, p.levels)
        lv = {m: _clean(p.levels.get(m, {}).get(h)) for m in target.models}
        out["paths"][str(h)] = {"quarter": str(p.base + h), "group": group_of(h), "champion": champ,
                                "value": lv.get(champ), "models": lv, **({"note": note} if note else {})}
    if intervals.ENABLED:
        out["distribution"] = distributions(p, t, origin, live_dir)
    _mark_inputs(info, target, p.base)
    out["inputs"] = info.inputs()
    return out


def payload(table: pd.DataFrame, origin, live_dir=None) -> dict:
    """The live D2 file for `origin` from the rows known at the origin (as_of for every input)."""
    origin = guard.check(origin, "D2 live", family=horizon.FAMILY, live=True)
    t = horizon.prepare(_known(table, origin))
    return {
        "nowcast": "D2", "product": "skugga (shadow): horisontprognoser 1–8 kvartal", "quarter": file_stem(origin),
        "origin": origin.date().isoformat(), "registered_origin": is_origin(origin),
        "first_live_origin": FIRST_LIVE.date().isoformat(), "register": REGISTER_REF,
        "horizons": list(horizon.HORIZONS), "groups": {g: list(hs) for g, hs in horizon.GROUPS.items()},
        "error_space": "100 * (log forecast - log outcome)",
        "targets": {name: target_payload(t, tg, origin, live_dir) for name, tg in horizon.TARGETS.items()},
    }


def write_live(table: pd.DataFrame, origin, out_dir, today=None) -> Path:
    """forecasts/d2/<quarter>.json, written once. Refuses an origin that is not a registered D2 origin from
    FIRST_LIVE on (an origin inside the holdout raises HoldoutClosed), a future origin and an existing file, before
    anything is computed."""
    origin = pd.Timestamp(origin)
    guard.check(origin, "D2 live", family=horizon.FAMILY, live=True)
    if not is_origin(origin):
        raise ValueError(f"{origin.date()} is not a registered D2 origin (quarter end + 20 days from "
                         f"{FIRST_LIVE.date()})")
    path = Path(out_dir) / f"{file_stem(origin)}.json"
    return engine.write_live(path, origin, lambda: payload(table, origin, live_dir=Path(out_dir)), today)


# ------------------------------------------------------------------ scorecard


def score(root, table: pd.DataFrame) -> pd.DataFrame:
    """One row per (file, target, h): the stored forecasts against the first vintage of L + h. Errors 100 * log;
    distribution scores (crps, pit, hit_<L>) of the distribution stored in the file, never recomputed."""
    files = sorted((Path(root) / DIR).glob("*.json"))
    if not files:
        return pd.DataFrame()
    t = horizon.prepare(table)
    rows = []
    for name, target in horizon.TARGETS.items():
        outcomes = engine.first_vintages(t, target.key)
        brk = horizon.target_breaks(t, target)
        for f in files:
            d = json.loads(f.read_text(encoding="utf-8"))
            tgt = (d.get("targets") or {}).get(name) or {}
            origin = pd.Timestamp(d["origin"])
            for hs, p in sorted((tgt.get("paths") or {}).items(), key=lambda kv: int(kv[0])):
                h, q = int(hs), pd.Period(p["quarter"], freq=horizon.Q)
                row = {"target": name, "key": target.key, "file": f"forecasts/{DIR}/{f.name}",
                       "origin": origin.date().isoformat(), "base": tgt.get("base"), "h": h, "group": group_of(h),
                       "quarter": str(q), "champion": p["champion"], "forecast": _num(p.get("value")),
                       "outcome": float("nan"), "known_from": "", "status": "väntar"}
                if q in outcomes.index:
                    kf = pd.Timestamp(outcomes.at[q, "known_from"])
                    row["known_from"] = kf.date().isoformat()
                    if kf <= origin:
                        row["status"] = "utfall känt vid origin, räknas inte"
                    elif q in brk:
                        row["status"] = "definitionsbrott, räknas inte"
                    else:
                        row["outcome"], row["status"] = float(outcomes.at[q, "value"]), STATUS_SCORED
                models = p.get("models") or {}
                for m in target.models:
                    x = _num(models.get(m))
                    ok = math.isfinite(x) and x > 0 and math.isfinite(row["outcome"])
                    row[f"err_{m}"] = engine.log_error(x, row["outcome"]) if ok else float("nan")
                row["err_champion"] = row.get(f"err_{p['champion']}", float("nan"))
                block = (tgt.get("distribution") or {}).get(hs) or {}
                for m in [*target.models, "champion"]:
                    model = p["champion"] if m == "champion" else m
                    sc = intervals.score_live(block, model, row[f"err_{m}"]) if row["status"] == STATUS_SCORED else {}
                    for k in ("crps", "pit", *(f"hit_{intervals.level_key(L)}" for L in intervals.LEVELS)):
                        row[f"{k}_{m}"] = sc.get(k, float("nan"))
                rows.append(row)
    return pd.DataFrame(rows)


def summary(df: pd.DataFrame, target: str) -> list[dict]:
    """Per h: n scored rows (= origins, one row per origin and h), MAE and bias per model and for the champion,
    and the champion's coverage and CRPS on the rows with a stored distribution."""
    out = []
    tg = horizon.TARGETS[target]
    s = df[(df["target"] == target) & (df["status"] == STATUS_SCORED)] if len(df) else df
    for h in horizon.HORIZONS:
        g = s[s["h"] == h] if len(s) else s
        row = {"h": h, "group": group_of(h), "n": int(len(g))}
        for m in ["champion", *tg.models]:
            e = g[f"err_{m}"].dropna() if len(g) else pd.Series(dtype=float)
            row[f"n_{m}"] = int(len(e))
            row[f"mae_{m}"] = float(e.abs().mean()) if len(e) else None
            row[f"bias_{m}"] = float(e.mean()) if len(e) else None
        c = g[g["crps_champion"].notna()] if len(g) else g
        row["n_dist"] = int(len(c))
        row["crps"] = float(c["crps_champion"].mean()) if len(c) else None
        for L in intervals.LEVELS:
            k = intervals.level_key(L)
            row[f"coverage_{k}"] = float(c[f"hit_{k}_champion"].mean()) if len(c) else None
        out.append(row)
    return out


def _num(x) -> float:
    return float("nan") if x is None else float(x)


def _fmt(x, nd=1, signed=False) -> str:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return ""
    return f"{x:+,.{nd}f}".replace(",", " ") if signed else f"{x:,.{nd}f}".replace(",", " ")


def render(df: pd.DataFrame) -> list[str]:
    """The D2 section of forecasts/SCORECARD.md."""
    lines = ["## D2 – prognoser 1–8 kvartal (skugga)", "",
             f"Registrerat i {REGISTER_REF}. En fil per prognosdag i `forecasts/{DIR}/` med banor för h = 1–8 "
             "(målkvartal = L + h, L = senast kända kvartal på prognosdagen). Huvudmodell per horisontgrupp = bästa "
             "baslinje i utvecklingen (capex: B2 för h1–4, B1 för h5–8; moln: B1), V_kedja är skugga. Varje h "
             "poängsätts när dess utfall (första versionen) kommer. Holdouten är stängd och utvärderas aldrig.", ""]
    if df.empty:
        return lines + [f"Inga D2-prognoser än. Första prognosdag {FIRST_LIVE.date()}.", ""]
    for name, target in horizon.TARGETS.items():
        d = df[df["target"] == name]
        lines += [f"### {target.label} (`{target.key}`)", ""]
        head = ["Origin", "L", "h", "Kvartal", "Huvudmodell", "Prognos", "Utfall", "Känt från", "Fel huvudmodell",
                *[f"Fel {m}" for m in target.models], "Status"]
        lines += ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"]
        for r in d.to_dict("records"):
            cells = [r["origin"], r["base"], r["h"], r["quarter"], r["champion"], _fmt(r["forecast"]),
                     _fmt(r["outcome"]), r["known_from"], _fmt(r["err_champion"], 2, True),
                     *[_fmt(r[f"err_{m}"], 2, True) for m in target.models], r["status"]]
            lines.append("| " + " | ".join(str(c) for c in cells) + " |")
        summ = [s for s in summary(df, name) if s["n"]]
        lines += ["", f"Utvärderade: {int((d['status'] == STATUS_SCORED).sum())} av {len(d)} (prognosdag × h)."]
        if summ:
            keys = [intervals.level_key(L) for L in intervals.LEVELS]
            lines += ["", "| h | n | MAE huvudmodell | " + " | ".join(f"MAE {m}" for m in target.models)
                      + " | Bias huvudmodell | n med fördelning | " + " | ".join(f"Täckning {k} %" for k in keys)
                      + " | CRPS |", "|" + "---|" * (5 + len(target.models) + len(keys) + 1)]
            for s in summ:
                lines.append(f"| {s['h']} | {s['n']} | {_fmt(s['mae_champion'], 2)} | "
                             + " | ".join(_fmt(s[f"mae_{m}"], 2) for m in target.models)
                             + f" | {_fmt(s['bias_champion'], 2, True)} | {s['n_dist']} | "
                             + " | ".join(_fmt(s[f"coverage_{k}"], 2) for k in keys) + f" | {_fmt(s['crps'], 2)} |")
            lines += ["", "n = antal prognosdagar med utfall för h. Horisonterna från samma prognosdag är inte "
                      "oberoende, och få utfall gör skillnader mellan modeller till möjlig slump."]
        lines.append("")
    return lines


def latest(root) -> dict | None:
    """The newest live D2 file (for the site), or None."""
    files = sorted((Path(root) / DIR).glob("*.json"))
    return json.loads(files[-1].read_text(encoding="utf-8")) | {"file": f"forecasts/{DIR}/{files[-1].name}"} \
        if files else None


def band(target_payload: dict, model: str | None = None) -> dict | None:
    """Fan chart data for one target of a live file: periods L..L+8, the champion path (B0's level at L) and the
    central 50/80/95 % intervals per h of the champion's stored distribution (None where the pool is too small)."""
    if not target_payload.get("base"):
        return None
    paths = target_payload["paths"]
    hs = sorted(paths, key=int)
    base = target_payload["base_value"]
    out = {"periods": [target_payload["base"], *[paths[h]["quarter"] for h in hs]],
           "champion": [paths[h]["champion"] for h in hs],
           "values": [base, *[paths[h]["value"] for h in hs]], "intervals": {}}
    for L in intervals.LEVELS:
        k = intervals.level_key(L)
        lo, hi = [base], [base]
        for h in hs:
            m = model or paths[h]["champion"]
            iv = (((target_payload.get("distribution") or {}).get(h) or {}).get("models") or {}).get(m, {})
            pair = (iv.get("intervals") or {}).get(k)
            lo.append(pair[0] if pair else None)
            hi.append(pair[1] if pair else None)
        out["intervals"][k] = {"lo": lo, "hi": hi}
    return out

