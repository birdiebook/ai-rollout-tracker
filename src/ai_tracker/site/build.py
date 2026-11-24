"""Write site/ from the assembled documents (ai_tracker.site.data) and the rendered pages (ai_tracker.site.render)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from ai_tracker import catalog, config, observations, warehouse
from ai_tracker.site import data as D
from ai_tracker.site import render as H
from ai_tracker.state.measures import Context

SITE_DIR = config.REPO / "site"
STATIC = Path(__file__).with_name("static")
# The only external host a page may load from (a pinned charting library, if ever needed). Today nothing external
# is loaded: the charts are inline SVG drawn by assets/app.js. Links (<a href>) to the repository are not loads.
ALLOWED_EXTERNAL_HOSTS = {"cdn.jsdelivr.net"}


class ChecksFailed(RuntimeError):
    pass


def run_checks(table: pd.DataFrame) -> None:
    """The warehouse data tests (warehouse.CHECKS). A failure stops the build: nothing is written or deployed."""
    con = warehouse.connect(table)
    bad = {name: len(df) for name, df in warehouse.run_checks(con).items() if len(df)}
    if bad:
        raise ChecksFailed(f"warehouse checks failed: {bad}")


def pages(docs: dict) -> dict[str, str]:
    """Relative path -> HTML."""
    build = docs["build"]
    out = {"index.html": H.overview_page(docs["oversikt"], build), "flode.html": H.flow_page(docs["flode"], build),
           "prognoser.html": H.nowcast_page(docs["prognoser"], build),
           "metod.html": H.method_page(docs["metod"], build),
           "manadsbrev.html": H.letters_page(docs["manadsbrev"], build),
           "kvartalsrapport.html": H.reports_page(docs["kvartalsrapport"], build)}
    for letter in docs["manadsbrev"]["letters"]:
        out[letter["page"]] = H.letter_page(letter, build)
    for report in docs["kvartalsrapport"]["reports"]:
        out[report["page"]] = H.report_page(report, build)
    for code in catalog.BRANCHES:
        out[f"gren-{code.lower()}.html"] = H.branch_page(docs[f"gren/{code}"], build)
    return out


def write(docs: dict, site_dir: Path = SITE_DIR) -> list[Path]:
    site_dir = Path(site_dir)
    if site_dir.exists():  # empty it but keep the folder (it may be a running server's cwd)
        for p in site_dir.iterdir():
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    (site_dir / "data" / "gren").mkdir(parents=True, exist_ok=True)
    (site_dir / "assets").mkdir(parents=True, exist_ok=True)
    written = []
    for name, doc in docs.items():
        if name == "manadsbrev":  # the letters are pages; their Markdown is not repeated in the JSON
            doc = {"letters": [{k: v for k, v in x.items() if k != "markdown"} for x in doc["letters"]]}
        if name == "kvartalsrapport":  # likewise the quarterly reports
            doc = {"reports": [{k: v for k, v in x.items() if k != "markdown"} for x in doc["reports"]]}
        path = site_dir / "data" / f"{name}.json"
        path.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
        written.append(path)
    for name, html in pages(docs).items():
        path = site_dir / name
        path.write_text(html, encoding="utf-8")
        written.append(path)
    for f in STATIC.iterdir():
        if f.is_file():
            shutil.copyfile(f, site_dir / "assets" / f.name)
            written.append(site_dir / "assets" / f.name)
    (site_dir / ".nojekyll").write_text("", encoding="utf-8")
    return written


def build(site_dir: Path = SITE_DIR, table: pd.DataFrame | None = None, ctx: Context | None = None,
          snapshots_dir: Path | None = None, forecasts_dir: Path | None = None, today=None,
          history_from: str = D.HISTORY_FROM, checks: bool = True, letters_dir: Path | None = None,
          reports_dir: Path | None = None, calibration: dict | None = None) -> list[Path]:
    if ctx is None:
        ctx = Context(observations.load() if table is None else table)
    if checks:
        run_checks(ctx.table)
    docs = D.assemble(ctx, snapshots_dir, forecasts_dir, today, history_from, letters_dir, reports_dir, calibration)
    return write(docs, site_dir)
