"""The new site (web/) deploys under /next/ beside the current site without being able to break it (docs/steg3/webb.md).
Static checks of the workflows and the web project's pinning. No network, no Node needed."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"


def _load(name: str) -> dict:
    return yaml.safe_load((WF / name).read_text(encoding="utf-8"))


def _on(wf: dict) -> dict:
    return wf.get("on", wf.get(True))  # PyYAML reads the key `on` as True


def test_single_deploy_job_includes_next_only_when_it_built():
    wf = _load("pages.yml")
    jobs = wf["jobs"]
    assert jobs["next"]["uses"] == "./.github/workflows/pages-next.yml"
    assert jobs["next"]["with"]["bundle"] == "real"
    assert jobs["build"]["needs"] == "next"
    # the current site is built even when `next` failed
    assert "!cancelled()" in jobs["build"]["if"]
    steps = jobs["build"]["steps"]
    dl = next(s for s in steps if s.get("uses", "").startswith("actions/download-artifact"))
    assert dl["if"] == "needs.next.result == 'success'"
    assert dl["with"] == {"name": "web-next", "path": "site/next"}
    # /next/ is added after the old site is built and before the one Pages artifact is uploaded
    names = [s.get("uses", s.get("run", "")) for s in steps]
    i_site = next(i for i, n in enumerate(names) if "ai_tracker.site build" in n)
    i_up = next(i for i, n in enumerate(names) if n.startswith("actions/upload-pages-artifact"))
    assert i_site < steps.index(dl) < i_up
    assert "needs.build.result == 'success'" in jobs["deploy"]["if"]
    deployers = [n for n, j in jobs.items() for s in j.get("steps", []) if s.get("uses", "").startswith("actions/deploy-pages")]
    assert deployers == ["deploy"]


def test_pages_next_never_deploys_and_gates_the_build():
    wf = _load("pages-next.yml")
    on = _on(wf)
    assert {"push", "pull_request", "workflow_dispatch", "workflow_call"} <= set(on)
    assert wf["permissions"] == {"contents": "read"}
    steps = wf["jobs"]["web"]["steps"]
    text = json.dumps(steps)
    assert "deploy-pages" not in text and "upload-pages-artifact" not in text
    for cmd in ("npm ci", "npm run check", "npm test", "npm run build", "npm run external-hosts", "npm run budget",
                "playwright test", "ai_tracker.site_bundle build", "REQUIRE_REAL_BUNDLE=1"):
        assert cmd in text, cmd
    up = next(s for s in steps if s.get("with", {}).get("name") == "web-next")
    assert up["with"]["path"] == "web/build"


def test_web_dependencies_are_pinned_and_locked():
    pkg = json.loads((ROOT / "web" / "package.json").read_text(encoding="utf-8"))
    for section in ("dependencies", "devDependencies"):
        for name, ver in pkg.get(section, {}).items():
            assert ver[0].isdigit(), f"{name}@{ver} is not an exact version"
    assert (ROOT / "web" / "package-lock.json").exists()
