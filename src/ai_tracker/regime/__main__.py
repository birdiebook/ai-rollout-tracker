"""python -m ai_tracker.regime: C4 development run (computation dates 2012-01-31 to 2025-06-30, holdout closed).

Writes data/derived/c4/{ms,bocpd}.parquet (never committed) and prints the F-D6 summaries for the development period.
"""

from __future__ import annotations

import json
import time

import pandas as pd

from ai_tracker import config, evaluation, observations
from ai_tracker.regime import evaluate, guard
from ai_tracker.regime import realtime as rt

OUT = config.REPO / "data" / "derived" / "c4"


def main() -> int:
    t0 = time.time()
    table = guard.dev_table(observations.load())
    ms_f, b_f = rt.run(table, rt.DEV_START, guard.DEV_END,
                       progress=lambda d: print(f"{d.date()} {time.time() - t0:.0f}s", flush=True))
    states = rt.reported_states(ms_f)
    breaks = rt.reported_breaks(b_f)
    OUT.mkdir(parents=True, exist_ok=True)
    states.to_parquet(OUT / "ms.parquet")
    breaks.to_parquet(OUT / "bocpd.parquet")
    freq = evaluate.frequency(states, breaks, rt.DEV_START, guard.DEV_END)
    recl = evaluate.reclassification(table, states, rt.DEV_START, guard.DEV_END)
    assoc = evaluate.association(states, evaluate._main_errors(table), rt.DEV_START, guard.DEV_END)
    print(json.dumps({"frequency": freq, "reclassification": recl,
                      "association": {f"{k[0]}/{k[1]}": v for k, v in assoc.items()}}, indent=1, default=str))
    rows = [{"target": f"C4 {b}", "variant": "MS", "period": f"dev ..{guard.DEV_END.date()}",
             "n": v["dates_with_p"], "MAE": None, "dm_p_vs_baseline": None} for b, v in freq["ms"].items()]
    evaluation.log_run("c4_regime_development", rows)
    print(f"done in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
