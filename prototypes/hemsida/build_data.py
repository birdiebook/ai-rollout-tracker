"""Data for the website prototypes (prototypes/hemsida/*.html). Writes prototypes/hemsida/data/*.json (gitignored).

    PYTHONPATH=src python prototypes/hemsida/build_data.py [--site DIR] [--table PATH]

Two inputs, both licence-gated the same way as the real site:
- the JSON the existing site build writes (`python -m ai_tracker.site build --out DIR`), which already applies the
  publish rule in ai_tracker.site.data (withheld series reduced to branch aggregates). Copied as-is.
- the observation table, read for the time-travel prototype: every version (period, value, known_from) of a few
  Spec.publish=True series, so the browser can replay "what did we know on date X" (as_of) itself.

Prototype only: no analysis is added here. The browser computes the registered pace measure (12-month change in log
x100, docs/mattregister.md section 1) on each vintage for display; the real site will take measures from the pipeline.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path

import pandas as pd

from ai_tracker import catalog

HERE = Path(__file__).resolve().parent
OUT = HERE / "data"

# The G6 core series (docs/mattregister.md section 5), all Spec.publish=True. Monthly, so as_of is meaningful.
VINTAGE_SERIES = ["us_ip_semis_m", "us_ip_computers_m", "tsmc_revenue_m", "us_imports_tw_m", "us_imports_kr_m"]
FIRST_PERIOD = "2016-01"
FIRST_KNOWN = "2019-01-01"


def vintages(table: Path) -> dict:
    df = pd.read_parquet(table, columns=["series", "period", "value", "known_from", "source"])
    specs = catalog.by_key()
    out = {}
    for key in VINTAGE_SERIES:
        spec = specs[key]
        if not spec.publish:  # the licence gate, as on the site
            continue
        d = df[(df.series == key) & (df.period >= FIRST_PERIOD)].copy()
        d["known_from"] = pd.to_datetime(d.known_from).dt.strftime("%Y-%m-%d")
        # Rows known before FIRST_KNOWN collapse into their latest pre-FIRST_KNOWN version (keeps the file small;
        # the replay starts at FIRST_KNOWN).
        early = d[d.known_from < FIRST_KNOWN].sort_values("known_from").groupby("period").tail(1)
        early = early.assign(known_from=FIRST_KNOWN)
        late = d[d.known_from >= FIRST_KNOWN]
        d = pd.concat([early, late]).drop_duplicates(["period", "known_from"], keep="last")
        d = d.sort_values(["period", "known_from"])
        rows = [[p, round(float(v), 4), k] for p, v, k in zip(d.period, d.value, d.known_from)
                if v is not None and not (isinstance(v, float) and math.isnan(v))]
        out[key] = {
            "label": spec.label, "unit": spec.unit, "source": spec.source, "license": spec.license,
            "revised": bool(spec.revised), "question": spec.question, "rows": rows,
        }
    return {"first_known": FIRST_KNOWN, "series": out}


def nowcast_n2(table: Path, first: str = "2019-01") -> dict:
    """N2 (TSMC monthly revenue) pseudo-out-of-sample backtest, per month, from the registered code (n2.run and
    n2.interval_scores, the same numbers the site's calibration table summarises). For the champion and the best
    naive baseline: forecast level, the outcome's 50/80/95 % interval at the origin (from the error pool known at the
    origin) and the first-vintage outcome. Error e = 100 log(f/y), so the outcome quantile 1-p is f exp(-e_p/100)."""
    from ai_tracker.nowcast import n2

    t = pd.read_parquet(table)
    frame = n2.run(t)
    scored = n2.interval_scores(frame)
    fv = n2.first_vintages(t)
    models = [n2.CHAMPION, "B1"]
    out_rows = []
    for _, r in scored[scored.model.isin(models)].iterrows():
        p = r.period
        if str(p) < first or p not in fv.index or r.method is None:
            continue
        y = float(fv.at[p, "value"])
        f = y * math.exp(r.error / 100)

        def q(pp):
            return round(f * math.exp(-r[f"eq_{pp}"] / 100), 1)

        out_rows.append({"period": str(p), "model": r.model, "origin": r.origin.strftime("%Y-%m-%d"),
                         "outcome_known_from": pd.Timestamp(fv.at[p, "known_from"]).strftime("%Y-%m-%d"),
                         "y": round(y, 1), "f": round(f, 1), "e": round(float(r.error), 3),
                         "lo95": q("0.975"), "lo80": q("0.9"), "lo50": q("0.75"),
                         "hi50": q("0.25"), "hi80": q("0.1"), "hi95": q("0.025"),
                         "hit50": int(r.hit_50), "hit80": int(r.hit_80), "hit95": int(r.hit_95),
                         "pit": round(float(r.pit), 4), "n_pool": int(r.n_pool)})
    return {"target": n2.TARGET, "champion": n2.CHAMPION, "baseline": "B1", "unit": "mn TWD",
            "note": "pseudo-out-of-sample backtest (rolling origin, dag 5 i månaden efter), inte skarpa prognoser",
            "rows": out_rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", type=Path, required=True, help="output dir of `python -m ai_tracker.site build`")
    ap.add_argument("--table", type=Path, default=None, help="observation table (default: the catalog default)")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ["oversikt.json", "prognoser.json", "flode.json", "build.json", "metod.json"]:
        src = a.site / "data" / name
        if src.exists():
            shutil.copy(src, OUT / name)
    (OUT / "gren").mkdir(exist_ok=True)
    for src in (a.site / "data" / "gren").glob("*.json"):
        shutil.copy(src, OUT / "gren" / src.name)
    from ai_tracker import observations
    table = a.table or observations.PATH
    (OUT / "vintages_g6.json").write_text(json.dumps(vintages(table), ensure_ascii=False, separators=(",", ":")))
    (OUT / "nowcast_n2.json").write_text(json.dumps(nowcast_n2(table), ensure_ascii=False, separators=(",", ":")))
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
