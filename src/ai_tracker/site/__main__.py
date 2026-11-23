"""CLI, see ai_tracker.site."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ai_tracker import observations
from ai_tracker.site import build as B
from ai_tracker.site import data as D


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ai_tracker.site", description=sys.modules["ai_tracker.site"].__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", default=None, help="observation table (default data/observations.parquet)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--out", default=str(B.SITE_DIR))
    b.add_argument("--history-from", default=D.HISTORY_FROM, help="first month of the index history (YYYY-MM)")
    b.add_argument("--today", default=None, help="build as of this date (default: today UTC)")
    b.add_argument("--skip-checks", action="store_true", help="do not run the warehouse checks (local use only)")
    a = ap.parse_args(argv)
    if a.table:
        observations.PATH = Path(a.table)
    if not observations.PATH.exists():
        print(f"no observation table at {observations.PATH}: run the weekly fetch first", file=sys.stderr)
        return 1
    try:
        written = B.build(Path(a.out), today=a.today, history_from=a.history_from, checks=not a.skip_checks)
    except B.ChecksFailed as e:
        print(f"::error::{e}. The site is not built.", file=sys.stderr)
        return 1
    print(f"wrote {len(written)} files to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
