"""CLI, see ai_tracker.state."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd

from ai_tracker import evaluation, observations
from ai_tracker.state import snapshot
from ai_tracker.state.branch import reconciliations
from ai_tracker.state.measures import Context


def _gh_output(**kv: str) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            for k, v in kv.items():
                f.write(f"{k}={v}\n")


def _fmt(x) -> str:
    return "–" if x is None else f"{x:.2f}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ai_tracker.state",
                                 description=sys.modules["ai_tracker.state"].__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", default=None, help="observation table (default data/observations.parquet)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("--date", required=True)
    s.add_argument("--out-dir", default=None)
    sh = sub.add_parser("show")
    sh.add_argument("--date", required=True)
    b = sub.add_parser("backcast")
    b.add_argument("--start", default="2019-01")
    b.add_argument("--end", required=True)
    b.add_argument("--out", default=None)
    b.add_argument("--compare", type=int, default=0, metavar="N",
                   help="also print a Markdown table v1 vs v2 for the last N months (register 2026-11-24)")
    d = sub.add_parser("due")
    d.add_argument("--today", default=None)
    e = sub.add_parser("evaluate", help="T1: pre-registered test of the state rule (register 2026-11-25)")
    e.add_argument("--start", default=None, help="first month end (default the registered 2024-01)")
    e.add_argument("--end", default=None, help="last month end (default the registered 2026-10)")
    e.add_argument("--vintage", default=None, help="V, the day of 'today's data' (default the registered 2026-11-25)")
    e.add_argument("--perm", type=int, default=None, help="permutations (default the registered 9999)")
    e.add_argument("--out", default=None, help="result JSON (default outputs/t1_tillstandsregeln.json)")
    e.add_argument("--no-log", action="store_true", help="do not write a run log to experiments/runs/")
    a = ap.parse_args(argv)
    if a.table:
        observations.PATH = Path(a.table)

    if a.cmd == "snapshot":
        path = snapshot.write(a.date, observations.load(), Path(a.out_dir) if a.out_dir else None)
        rel = path.resolve().relative_to(snapshot.config.REPO) if path.resolve().is_relative_to(snapshot.config.REPO) else path
        print(f"wrote {rel}")
        _gh_output(written=str(rel))
        return 0
    if a.cmd == "show":
        ctx = Context(observations.load())
        for code, br in snapshot.compute(a.date, ctx).items():
            v1 = br["v1"]
            print(f"{code}  index {_fmt(br['index'])}  {br['state']:28s} källor={br['n_families']} n={br['n_series']} "
                  f"(+{br['n_up']} 0:{br['n_neutral']} -{br['n_down']})  v1 {_fmt(v1['index'])} {v1['state']}")
        rec = reconciliations(pd.Timestamp(a.date).normalize(), ctx)
        print(f"{rec['group']} (inte i något grenindex)")
        for m in rec["series"]:
            print(f"  {m['series']:16s} {m.get('latest_period', '–'):8s} nivå {_fmt(m.get('level'))}  "
                  f"takt {_fmt(m.get('pace'))}  förändring {_fmt(m.get('change_in_pace'))}  {m.get('reason', '')}")
        return 0
    if a.cmd == "backcast":
        df = snapshot.backcast(a.start, a.end, out=Path(a.out) if a.out else None)
        print(f"wrote {a.out or snapshot.BACKCAST} ({len(df)} rows, {snapshot.BACKCAST_LABEL})")
        if a.compare:
            print(snapshot.rule_comparison(df, a.compare), end="")
        return 0
    if a.cmd == "evaluate":
        from ai_tracker.state import evaluate as EV

        vintage = a.vintage or EV.VINTAGE
        if pd.Timestamp(vintage) > snapshot.utc_today():
            raise SystemExit(f"vintage {vintage} is in the future (today {snapshot.utc_today().date()} UTC)")
        res = EV.run(start=a.start or EV.START, end=a.end or EV.END, vintage=vintage,
                     n_perm=EV.N_PERM if a.perm is None else a.perm)
        out = Path(a.out) if a.out else snapshot.config.REPO / "outputs" / "t1_tillstandsregeln.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(EV._clean(res), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(EV.markdown(res))
        print(f"wrote {out} ({EV.LABEL})")
        if not a.no_log:
            print(f"logged {evaluation.log_run('t1_state_rule', EV.run_log_rows(res))}")
        return 0
    today = pd.Timestamp(a.today) if a.today else snapshot.utc_today()
    is_due = snapshot.due(today)
    print(f"{today.date()}: {'snapshot due' if is_due else 'no snapshot due'}")
    _gh_output(due="true" if is_due else "false", date=str(today.date()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
