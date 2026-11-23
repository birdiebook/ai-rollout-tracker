"""CLI.

    python -m ai_tracker.nowcast n1 --origin YYYY-MM-DD      live forecast -> forecasts/n1/<quarter>.json (never overwrites)
    python -m ai_tracker.nowcast backtest n1                 pre-registered backtest, logged to experiments/runs/
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ai_tracker import evaluation, observations
from ai_tracker.nowcast import n1

FORECASTS = evaluation.REPO / "forecasts"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ai_tracker.nowcast")
    sub = ap.add_subparsers(dest="cmd", required=True)
    live = sub.add_parser("n1", help="live N1 forecast")
    live.add_argument("--origin", required=True, help="forecast date; registered: quarter end + 20 days")
    live.add_argument("--out-dir", default=str(FORECASTS / "n1"))
    live.add_argument("--table", default=None, help="observation table (default data/observations.parquet)")
    bt = sub.add_parser("backtest", help="run a registered backtest")
    bt.add_argument("nowcast", choices=["n1"])
    args = ap.parse_args(argv)

    if args.cmd == "n1":
        table = observations.load(Path(args.table) if args.table else None)
        path = n1.write_live(table, args.origin, args.out_dir)
        print(f"wrote {path}")
        return 0
    out = n1.run_backtest(observations.load())
    print(n1.format_report(out))
    for key in ("N1", "N1b"):
        print(f"{key} logged to {out[key]['log']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
