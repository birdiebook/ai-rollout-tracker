"""CLI, see ai_tracker.site_bundle."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import pandas as pd


def build_real(out: Path, today=None, history_from=None, checks: bool = True, series=None,
               budgets: bool = True) -> dict:
    from ai_tracker import observations
    from ai_tracker.site import build as SB
    from ai_tracker.site import data as D
    from ai_tracker.site_bundle import build as B
    from ai_tracker.site_bundle import export as E
    from ai_tracker.state.measures import Context

    table = observations.load()
    if table.empty:
        raise SystemExit(f"no observation table at {observations.PATH}: run the weekly fetch first")
    ctx = Context(table)
    if checks:
        SB.run_checks(ctx.table)  # the same warehouse checks as the old site: a failure stops the bundle
    today = pd.Timestamp(today).normalize() if today else D.utc_today()
    docs = E.assemble(ctx, today=today, history_from=history_from or D.HISTORY_FROM, series=series)
    files = B.serialise(docs, E.build_info(), str(today.date()), synthetic=False, enforce_budgets=budgets)
    B.write(files, out)
    return json.loads(files["manifest.json"])


def build_fixtures(out: Path) -> dict:
    from ai_tracker.site_bundle import build as B
    from ai_tracker.site_bundle import export as E
    from ai_tracker.site_bundle import synthetic as SY

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ctx = SY.context(root)
        paths = SY.write_inputs(root, ctx)
        docs = E.assemble(ctx, today=SY.TODAY, history_from=SY.HISTORY_FROM, calibration=SY.calibration(),
                          commits=SY.commits, **paths)
    info = {"built_utc": SY.BUILT_UTC, "git_sha": SY.GIT_SHA, "repo": "https://github.com/birdiebook/ai-rollout-tracker"}
    files = B.serialise(docs, info, SY.TODAY, synthetic=True)
    B.write(files, out)
    return json.loads(files["manifest.json"])


def validate_dir(path: Path) -> list[str]:
    """Schema errors and licence violations of a written bundle (the catalog's withheld keys, or the synthetic
    world's for a synthetic bundle), and manifest checksums."""
    import hashlib

    from ai_tracker.site_bundle import build as B
    from ai_tracker.site_bundle import gate as G
    from ai_tracker.site_bundle import schema as SC
    from ai_tracker.state.measures import Context
    from ai_tracker import observations

    docs = B.read(path)
    man = docs.get("manifest.json") or {}
    errs = SC.validate(docs)
    if man.get("synthetic"):
        from ai_tracker.site_bundle import synthetic as SY

        ctx = Context(observations._empty(), specs=SY.specs(), derived={})
    else:
        ctx = Context(observations._empty())
    errs += G.scan({k: v for k, v in docs.items()}, ctx)
    for f in man.get("files", []):
        p = Path(path) / f["path"]
        if not p.is_file():
            errs.append(f"{f['path']}: listed in the manifest but missing")
        elif hashlib.sha256(p.read_bytes()).hexdigest() != f["sha256"]:
            errs.append(f"{f['path']}: sha256 differs from the manifest")
    return errs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ai_tracker.site_bundle",
                                 description=sys.modules["ai_tracker.site_bundle"].__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", default=None, help="observation table (default: data/observations.parquet + shared base)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="the real bundle from the observation table, snapshots/ and forecasts/")
    b.add_argument("--out", default=None, help="default web-data/")
    b.add_argument("--today", default=None, help="build as of this date (default: today UTC)")
    b.add_argument("--history-from", default=None, help="first month of the state stripes (default 2023-01)")
    b.add_argument("--skip-checks", action="store_true", help="do not run the warehouse checks (local use only)")
    b.add_argument("--series", nargs="*", default=None, help="only these per-series documents (development)")
    b.add_argument("--no-budgets", action="store_true", help="report but do not enforce the size budgets")
    f = sub.add_parser("fixtures", help="the synthetic bundle the front-end tracks develop against")
    f.add_argument("--out", default=None, help="default web-data-fixtures/")
    v = sub.add_parser("validate", help="schema, licence scan and checksums of a written bundle")
    v.add_argument("dir")
    s = sub.add_parser("sizes", help="size report from a written bundle's manifest")
    s.add_argument("dir")
    sb = sub.add_parser("scan-build", help="licence scan of the built site (web/build) and of the web sources")
    sb.add_argument("dir", help="the output of `npm run build` (web/build)")
    sb.add_argument("--src", default=None, help="also scan the front-end sources (web/src) for withheld keys and labels")
    a = ap.parse_args(argv)

    from ai_tracker import observations
    from ai_tracker.site_bundle import build as B

    if a.table:
        observations.PATH = Path(a.table)
    try:
        if a.cmd == "build":
            from ai_tracker.site import build as SB

            try:
                man = build_real(Path(a.out or B.OUT_DIR), a.today, a.history_from, not a.skip_checks, a.series,
                                 budgets=not a.no_budgets)
            except SB.ChecksFailed as e:
                print(f"::error::{e}. The bundle is not built.", file=sys.stderr)
                return 1
            print(B.size_report(man))
        elif a.cmd == "fixtures":
            man = build_fixtures(Path(a.out or B.FIXTURES_DIR))
            print(B.size_report(man))
        elif a.cmd == "validate":
            errs = validate_dir(Path(a.dir))
            for e in errs[:50]:
                print(e, file=sys.stderr)
            print(f"{len(errs)} problems")
            return 1 if errs else 0
        elif a.cmd == "scan-build":
            from ai_tracker.site_bundle import scan_build as SB2

            errs = SB2.scan_build(Path(a.dir), Path(a.src) if a.src else None)
            for e in errs[:50]:
                print(f"::error::{e}", file=sys.stderr)
            print(f"scan-build: {len(errs)} withheld keys or labels outside a withheld list in {a.dir}"
                  + (f" and {a.src}" if a.src else ""))
            return 1 if errs else 0
        elif a.cmd == "sizes":
            man = json.loads((Path(a.dir) / "manifest.json").read_text(encoding="utf-8"))
            print(B.size_report(man, top=25))
    except (B.BundleError, RuntimeError) as e:
        print(f"::error::{e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
