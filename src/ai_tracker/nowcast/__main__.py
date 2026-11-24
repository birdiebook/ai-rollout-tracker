"""CLI.

    python -m ai_tracker.nowcast n1 --origin YYYY-MM-DD      live forecast -> forecasts/n1/<quarter>.json (never overwrites)
    python -m ai_tracker.nowcast n2 --origin YYYY-MM-DD [--refresh]
                                                             live forecast -> forecasts/n2/<month>.json (never overwrites)
    python -m ai_tracker.nowcast n3|n4|n6 --origin YYYY-MM-DD
                                                             live forecast -> forecasts/<nowcast>/<quarter>.json
    python -m ai_tracker.nowcast n5 --origin YYYY-MM-DD      live forecast -> forecasts/n5/<collection end>.json
    python -m ai_tracker.nowcast backtest n1|n2|n3|n4|n5|n6|n7
                                                             pre-registered backtest, logged to experiments/runs/
                                                             (n7: backtest only, no live forecast)

The scheduled routine is `python -m ai_tracker.pipeline live`; these commands are for manual runs.
`python -m ai_tracker.nowcast_n2 ...` and `python -m ai_tracker.nowcast_n2.backtest` are compatibility shims for n2.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ai_tracker import evaluation, observations
from ai_tracker.nowcast import n1, n2, n3, n4, n5, n6, n7

STEP2 = {"n3": n3, "n4": n4, "n5": n5, "n6": n6}
BACKTEST_ONLY = {"n7": n7}  # registered backtest; no live forecast is built (docs/resultat/n7.md)

FORECASTS = evaluation.REPO / "forecasts"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ai_tracker.nowcast")
    sub = ap.add_subparsers(dest="cmd", required=True)
    live = sub.add_parser("n1", help="live N1 forecast")
    live.add_argument("--origin", required=True, help="forecast date; registered: quarter end + 20 days")
    live.add_argument("--out-dir", default=str(FORECASTS / "n1"))
    live.add_argument("--table", default=None, help="observation table (default data/observations.parquet)")
    n2.add_live_args(sub.add_parser("n2", help="live N2 forecast (prints the written file)"))
    for name in STEP2:
        p = sub.add_parser(name, help=f"live {name.upper()} forecast (registered origin only)")
        p.add_argument("--origin", required=True)
        p.add_argument("--out-dir", default=None)
        p.add_argument("--table", default=None, help="observation table (default data/observations.parquet)")
    bt = sub.add_parser("backtest", help="run a registered backtest")
    bt.add_argument("nowcast", choices=["n1", "n2", *STEP2, *BACKTEST_ONLY])
    args = ap.parse_args(argv)

    if args.cmd in STEP2:
        table = observations.load(Path(args.table) if args.table else None)
        path = STEP2[args.cmd].write_live(table, args.origin, args.out_dir or FORECASTS / args.cmd)
        print(f"wrote {path}")
        return 0
    if args.cmd == "backtest" and (args.nowcast in STEP2 or args.nowcast in BACKTEST_ONLY):
        m = {**STEP2, **BACKTEST_ONLY}[args.nowcast]
        out = m.backtest()
        print(m.format_report(out))
        print(f"logged to {out['log']}")
        return 0

    if args.cmd == "n1":
        table = observations.load(Path(args.table) if args.table else None)
        path = n1.write_live(table, args.origin, args.out_dir)
        print(f"wrote {path}")
        return 0
    if args.cmd == "n2":
        n2.run_live(args)
        return 0
    if args.nowcast == "n2":
        n2.main_backtest()
        return 0
    out = n1.run_backtest(observations.load())
    print(n1.format_report(out))
    for key in ("N1", "N1b"):
        print(f"{key} logged to {out[key]['log']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
