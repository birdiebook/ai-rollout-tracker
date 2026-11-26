"""CLI: python -m ai_tracker.followed <question> --as-of YYYY-MM-DD [--json PATH] [--out PATH].

The questions are found, not listed: every module in ai_tracker.followed with compute(as_of) and render(report)
(ai_tracker.followed.questions). `antenner` gives one row per question."""

from __future__ import annotations

import argparse
import json
import sys

from ai_tracker.followed import questions


def main(argv: list[str] | None = None) -> int:
    found = questions()
    ap = argparse.ArgumentParser(prog="python -m ai_tracker.followed", description=__doc__)
    ap.add_argument("question", choices=sorted(found))
    ap.add_argument("--as-of", required=True, help="YYYY-MM-DD: only rows known on this day are used")
    ap.add_argument("--json", help="write the computed report as JSON here")
    ap.add_argument("--out", help="write the Markdown here instead of stdout")
    a = ap.parse_args(argv)
    mod = found[a.question]
    report = mod.compute(a.as_of)
    text = mod.render(report)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1, ensure_ascii=False, default=str)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
