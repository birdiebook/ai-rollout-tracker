from __future__ import annotations

import argparse
import importlib
import re
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ai_tracker.jobs")
    ap.add_argument("job")
    ap.add_argument("--out", default="out")
    a = ap.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9_]+", a.job):
        raise SystemExit("invalid job name")
    mod = importlib.import_module(f"ai_tracker.jobs.{a.job}")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    mod.run(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
