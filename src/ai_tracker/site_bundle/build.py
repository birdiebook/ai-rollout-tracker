"""Write the bundle: documents, schema copies and the manifest; sizes against budgets; schema validation.

Order (nothing is written unless every step passes): assemble (licence scan inside) -> serialise -> schema-validate
every document -> budgets -> write into a fresh temporary directory -> swap it into place.
"""

from __future__ import annotations

import fnmatch
import gzip
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from ai_tracker import config
from ai_tracker.site_bundle import VERSION
from ai_tracker.site_bundle import schema as SC

OUT_DIR = config.REPO / "web-data"
FIXTURES_DIR = config.REPO / "web-data-fixtures"

# Size budgets per document, (raw bytes, gzip bytes); first matching pattern wins. GitHub Pages serves JSON gzipped,
# so gzip is what a visitor downloads; raw bounds parse time and memory. Measured on the real table 2026-11-24
# (docs/steg3/datakontrakt.md, "Storlek"), with headroom for about two years of growth.
BUDGETS: list[tuple[str, tuple[int, int]]] = [
    ("manifest.json", (300_000, 60_000)),
    ("overview.json", (60_000, 12_000)),
    ("flow.json", (200_000, 30_000)),
    ("branch/*.json", (250_000, 40_000)),
    ("series/index.json", (400_000, 40_000)),
    ("series/*.json", (300_000, 75_000)),
    ("nowcast/*.json", (200_000, 40_000)),
    ("regime.json", (100_000, 20_000)),
    ("method.json", (100_000, 20_000)),
    ("withheld.json", (80_000, 15_000)),
    ("story/index.json", (60_000, 12_000)),
    ("story/*.json", (60_000, 12_000)),
    ("letters.json", (50_000, 10_000)),
    ("letters/*.json", (100_000, 30_000)),
    ("reports/*.json", (200_000, 60_000)),
    ("schema/*.json", (60_000, 12_000)),
]
TOTAL_BUDGET = (20_000_000, 4_000_000)
# The start page loads overview + flow: the vision's "<= 100 kB data" (docs/steg3/hemsida_vision.md 6.3). The
# manifest is read at build time (prerender), not by the visitor's start page.
START_PAGE = ("overview.json", "flow.json")
START_PAGE_GZIP_BUDGET = 100_000


class BundleError(RuntimeError):
    pass


def dumps(doc) -> bytes:
    return json.dumps(doc, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def budget_for(path: str) -> tuple[int, int]:
    for pat, b in BUDGETS:
        if fnmatch.fnmatchcase(path, pat):
            return b
    raise KeyError(f"no size budget for {path!r}")


def _entry(path: str, data: bytes, schema: str) -> dict:
    return {"path": path, "schema": schema, "bytes": len(data), "gzip_bytes": len(gzip.compress(data, 9, mtime=0)),
            "sha256": hashlib.sha256(data).hexdigest()}


def budget_violations(files: list[dict]) -> list[str]:
    out = []
    for f in files:
        raw, gz = budget_for(f["path"])
        if f["bytes"] > raw or f["gzip_bytes"] > gz:
            out.append(f"{f['path']}: {f['bytes']} B ({f['gzip_bytes']} B gzip) over budget {raw} B ({gz} B gzip)")
    tot_raw, tot_gz = sum(f["bytes"] for f in files), sum(f["gzip_bytes"] for f in files)
    if tot_raw > TOTAL_BUDGET[0] or tot_gz > TOTAL_BUDGET[1]:
        out.append(f"total {tot_raw} B ({tot_gz} B gzip) over budget {TOTAL_BUDGET[0]} B ({TOTAL_BUDGET[1]} B gzip)")
    start = sum(f["gzip_bytes"] for f in files if f["path"] in START_PAGE)
    if start > START_PAGE_GZIP_BUDGET:
        out.append(f"start page data {start} B gzip over budget {START_PAGE_GZIP_BUDGET} B")
    return out


def manifest(docs: dict[str, dict], info: dict, record: dict, today: str, synthetic: bool,
             files: list[dict]) -> dict:
    groups: dict[str, dict] = {}
    for f in files:
        g = f["path"].split("/")[0] if "/" in f["path"] else f["path"]
        e = groups.setdefault(g, {"group": g, "files": 0, "bytes": 0, "gzip_bytes": 0})
        e["files"] += 1
        e["bytes"] += f["bytes"]
        e["gzip_bytes"] += f["gzip_bytes"]
    return {
        "bundle": "ai-rollout-tracker/site-bundle", "version": VERSION, "synthetic": synthetic,
        "built_utc": info["built_utc"], "git_sha": info["git_sha"], "repo": info["repo"], "today": today,
        "snapshot": {k: record.get(k) for k in ("status", "kind", "label", "month", "date", "file",
                                                 "first_live_date", "live_months")},
        "table_max_fetched_at": docs["overview.json"]["facts"]["table_max_fetched_at"],
        "counts": {"series": docs["series/index.json"]["n"], "withheld": docs["withheld.json"]["n"],
                   "nowcasts": len([p for p in docs if p.startswith("nowcast/")])},
        "files": files, "groups": sorted(groups.values(), key=lambda g: g["group"]),
        "totals": {"files": len(files), "bytes": sum(f["bytes"] for f in files),
                   "gzip_bytes": sum(f["gzip_bytes"] for f in files)},
        "budgets": {"per_file": [{"pattern": p, "bytes": b[0], "gzip_bytes": b[1]} for p, b in BUDGETS],
                    "total": {"bytes": TOTAL_BUDGET[0], "gzip_bytes": TOTAL_BUDGET[1]},
                    "start_page": {"files": list(START_PAGE), "gzip_bytes": START_PAGE_GZIP_BUDGET}},
    }


def serialise(docs: dict[str, dict], info: dict, today: str, synthetic: bool = False,
              enforce_budgets: bool = True) -> dict[str, bytes]:
    """path -> bytes of every file of the bundle (documents, schema copies, manifest), validated and within budget."""
    errs = SC.validate(docs)
    if errs:
        raise BundleError(f"{len(errs)} schema errors, first: {errs[:8]}")
    out: dict[str, bytes] = {}
    files = []
    for path in sorted(docs):
        data = dumps(docs[path])
        out[path] = data
        files.append(_entry(path, data, SC.schema_for(path)))
    for p in sorted(SC.SCHEMA_DIR.glob("*.json")):
        data = p.read_bytes()
        out[f"schema/{p.name}"] = data
        files.append(_entry(f"schema/{p.name}", data, "json-schema"))
    man = manifest(docs, info, docs["overview.json"]["record"], today, synthetic, files)
    errs = SC.errors("manifest.json", man)
    if errs:
        raise BundleError(f"manifest schema errors: {errs[:8]}")
    out["manifest.json"] = json.dumps(man, ensure_ascii=False, indent=1).encode("utf-8")
    man_entry = _entry("manifest.json", out["manifest.json"], "manifest")
    if enforce_budgets:
        bad = budget_violations(files + [man_entry])
        if bad:
            raise BundleError(f"{len(bad)} size budget violations: {bad[:8]}")
    return out


def write(files: dict[str, bytes], out_dir: Path) -> list[Path]:
    """Write into a temporary sibling directory, then replace `out_dir` (never a half-written bundle)."""
    out_dir = Path(out_dir)
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f".{out_dir.name}-", dir=out_dir.parent))
    written = []
    try:
        for path, data in files.items():
            p = tmp / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            written.append(out_dir / path)
        if out_dir.exists():
            shutil.rmtree(out_dir)
        tmp.rename(out_dir)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return written


def read(out_dir: Path) -> dict[str, object]:
    """Every JSON file of a written bundle (path -> parsed), the manifest included, schema copies excluded."""
    out_dir = Path(out_dir)
    return {str(p.relative_to(out_dir)): json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(out_dir.rglob("*.json")) if not str(p.relative_to(out_dir)).startswith("schema/")}


def size_report(man: dict, top: int = 10) -> str:
    """A plain-text size report from a manifest: groups, the largest files and the budgets."""
    lines = [f"bundle {man['version']} ({'synthetic' if man['synthetic'] else 'real'}), {man['totals']['files']} files, "
             f"{man['totals']['bytes'] / 1e6:.2f} MB raw, {man['totals']['gzip_bytes'] / 1e6:.2f} MB gzip",
             "", f"{'group':<16}{'files':>7}{'raw kB':>11}{'gzip kB':>10}"]
    for g in man["groups"]:
        lines.append(f"{g['group']:<16}{g['files']:>7}{g['bytes'] / 1e3:>11.1f}{g['gzip_bytes'] / 1e3:>10.1f}")
    lines += ["", f"largest {top} files (raw kB, gzip kB, budget gzip kB):"]
    for f in sorted(man["files"], key=lambda f: -f["gzip_bytes"])[:top]:
        lines.append(f"  {f['path']:<52}{f['bytes'] / 1e3:>9.1f}{f['gzip_bytes'] / 1e3:>9.1f}"
                     f"{budget_for(f['path'])[1] / 1e3:>9.0f}")
    start = sum(f["gzip_bytes"] for f in man["files"] if f["path"] in START_PAGE)
    lines.append(f"\nstart page data (overview + flow): {start / 1e3:.1f} kB gzip (budget {START_PAGE_GZIP_BUDGET / 1e3:.0f} kB)")
    return "\n".join(lines)
