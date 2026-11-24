"""Probabilities on the site (track E4): backtest calibration of every nowcast target and the C4 regime view.

Backtest calibration. For N1-N6 the registered interval evaluation (grind G-C, `intervals.evaluate`, "full" period)
is recomputed at build time with the registered code on the current table: coverage per level (50/80/95 %) with the
binomial 90 % band, mean CRPS and the calibration verdict per model, plus the champion's backtest MAE. The registered
first run is the one written up in docs/resultat/n<k>.md; with newer data the pseudo-out-of-sample sample grows, so
the page says "beräknad vid bygget". A failure for one target is reported on the page and never stops the build.

Regime (C4). The live value of the regime probability is stored in the monthly snapshot (F-D1) and never recomputed:
the site only reads it. The snapshot key is "regime"; the accepted shape (the C4 wiring may use either spelling) is

    "regime": {"spec_version": "c4-v1",
               "blocks" | "ms": {"capex": {"p_slow": 0.12, "state": "expansion", "shift": null,
                                            "n_months": 140, "first_month": "2014-12", "reason": ""}, ...},
               "breaks": [{"series": ..., "branch": ..., "latest_period": ..., "p_recent": ..., "freq": ...}, ...]
                 | "bocpd": [{... , "break": true}, ...]}

A reconstructed (pre-snapshot) month never gets a regime value: C4 is guarded by its holdout and its live values
exist only from the first snapshot after it is opened. Breaks name a series; a withheld series is only counted.
"""

from __future__ import annotations

import math

import pandas as pd

from ai_tracker.nowcast import intervals

BLOCK_LABELS = {"capex": "capex och leverantörsled", "demand": "efterfrågan"}
SLOW_KEYS = ("p_slow", "p_slowdown", "p_inbromsning")


def _f(x, digits: int = 4):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return float(f"{x:.{digits}g}") if math.isfinite(x) else None


# ------------------------------------------------------------------ backtest calibration (G-C)


def _cal_rows(res: dict) -> list[dict]:
    cal = res.get("calibration")
    if cal is None or len(cal) == 0:
        return []
    out = []
    for r in cal.to_dict("records"):
        row = {"model": r["model"], "n": int(r["n"]), "first": r.get("first"), "last": r.get("last"),
               "n_student_t": int(r.get("n_student_t") or 0), "n_empirical": int(r.get("n_empirical") or 0),
               "crps": _f(r.get("crps")), "calibrated": bool(r.get("calibrated")),
               "pit_mean": _f(r.get("pit_mean"), 3), "pit_var": _f(r.get("pit_var"), 3)}
        for L in intervals.LEVELS:
            k = intervals.level_key(L)
            row[f"coverage_{k}"] = _f(r.get(f"coverage_{k}"), 3)
            row[f"band_{k}"] = [_f(x, 3) for x in (r.get(f"band_{k}") or [None, None])]
            row[f"holm_{k}"] = _f(r.get(f"holm_{k}"), 3)
        out.append(row)
    return out


def _mae_from_eval(ev: dict, champion: str) -> dict | None:
    full = (ev or {}).get("full") or {}
    m = (full.get("metrics") or {}).get(champion)
    if not m:
        return None
    return {"mae": _f(m.get("MAE")), "n": int(m.get("n") or full.get("n") or 0),
            "first": str(full.get("first")) if full.get("first") is not None else None,
            "last": str(full.get("last")) if full.get("last") is not None else None}


def _n1(table):
    from ai_tracker.nowcast import n1

    errors = n1.backtest_unit(table, n1.TARGET, n1.b3_deviations(table))
    return n1.evaluate_intervals(errors)["full"], _mae_from_eval(n1.evaluate(errors, pooled=False), n1.CHAMPION)


def _n2(table):
    from ai_tracker.nowcast import n2

    frame = n2.run(table)
    res = n2.evaluate(frame)
    s = res.summary
    row = s[(s["period"] == "full") & (s["variant"] == n2.CHAMPION)]
    mae = None
    if len(row):
        r = row.iloc[0]
        first, _, last = str(r["range"]).partition("..")
        mae = {"mae": _f(r["MAE"]), "n": int(r["n"]), "first": first, "last": last}
    return n2.evaluate_intervals(frame)["full"], mae


def _step2(mod):
    def run(table):
        out = mod.backtest(table, log=False)
        return (out.get("intervals") or {}).get("full") or {}, _mae_from_eval(out.get("eval"), mod.CHAMPION)
    return run


def runners() -> dict:
    from ai_tracker.nowcast import n3, n4, n5, n6

    return {"n1": _n1, "n2": _n2, "n3": _step2(n3), "n4": _step2(n4), "n5": _step2(n5), "n6": _step2(n6)}


def backtest_calibration(table: pd.DataFrame, only=None) -> dict[str, dict]:
    """{nowcast id: {"available", "rows" (per model), "n_periods", "first", "last", "best_baseline",
    "champion_mae"}}; "error" when the backtest could not run on this table."""
    out = {}
    for sub, run in runners().items():
        if only is not None and sub not in only:
            continue
        try:
            res, mae = run(table)
            rows = _cal_rows(res)
            out[sub] = {"available": bool(rows), "rows": rows, "n_periods": int(res.get("n_periods") or 0),
                        "first": res.get("first"), "last": res.get("last"), "best_baseline": res.get("best_baseline"),
                        "champion_mae": mae, "error": None}
        except Exception as e:  # noqa: BLE001 - one target failing must not take the site down; the page says so
            out[sub] = {"available": False, "rows": [], "champion_mae": None,
                        "error": f"{type(e).__name__}: {str(e)[:200]}"}
    return out


# ------------------------------------------------------------------ regime (C4) from the snapshots


def _p_slow(b: dict):
    for k in SLOW_KEYS:
        if k in b:
            return _f(b.get(k))
    return None


def _blocks(r: dict) -> dict:
    b = r.get("blocks") if isinstance(r.get("blocks"), dict) else r.get("ms")
    return b if isinstance(b, dict) else {}


def _breaks(r: dict) -> list[dict]:
    if isinstance(r.get("breaks"), list):
        return [b for b in r["breaks"] if isinstance(b, dict) and b.get("break", True)]
    if isinstance(r.get("bocpd"), list):
        return [b for b in r["bocpd"] if isinstance(b, dict) and b.get("break")]
    return []


def regime_view(live: dict[str, dict], publishable) -> dict:
    """The regime section from the committed live snapshots (month -> snapshot). `publishable(key)` is the site's
    licence rule. Returns {"available": False, ...} until a snapshot carries a "regime" block."""
    months = sorted(m for m, s in live.items() if isinstance(s.get("regime"), dict))
    blocks: dict[str, dict] = {}
    shifts, breaks, n_withheld = [], [], 0
    spec = None
    for m in months:
        r = live[m]["regime"]
        spec = r.get("spec_version") or spec
        for name, b in _blocks(r).items():
            if not isinstance(b, dict):
                continue
            e = blocks.setdefault(name, {"block": name, "label": BLOCK_LABELS.get(name, name), "history": []})
            h = {"month": m, "p_slow": _p_slow(b), "state": b.get("state"), "shift": b.get("shift"),
                 "n_months": b.get("n_months"), "reason": b.get("reason") or ""}
            e["history"].append(h)
            if h["shift"]:
                shifts.append({"month": m, "block": name, "label": e["label"], "state": h["shift"]})
        for x in _breaks(r):
            key = x.get("series")
            if key and publishable(key):
                breaks.append({"month": m, "series": key, "branch": x.get("branch"),
                               "latest_period": x.get("latest_period"), "p_recent": _f(x.get("p_recent"), 3)})
            else:
                n_withheld += 1
    for e in blocks.values():
        e["latest"] = e["history"][-1]
    return {"available": bool(months), "months": months, "spec_version": spec,
            "blocks": [blocks[k] for k in sorted(blocks, key=lambda k: (k not in BLOCK_LABELS, k))],
            "shifts": shifts, "breaks": breaks, "n_breaks_withheld": n_withheld,
            "block_labels": BLOCK_LABELS}
