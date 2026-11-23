"""Settings from the environment, then .env.local, then .env (both gitignored). Never log the values.

.env holds secrets (copied between worktrees); .env.local holds per-worktree settings that scripts write, e.g.
AI_TRACKER_SHARED_DATA from scripts/new_track.sh (docs/drift.md, "Delad data").
"""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _dotenv(path: Path) -> dict[str, str]:
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def get(name: str, default: str | None = None) -> str | None:
    """Environment variable, else .env.local, else .env in the repo root, else default. Empty strings count as
    missing."""
    value = os.environ.get(name) or _dotenv(REPO / ".env.local").get(name) or _dotenv(REPO / ".env").get(name)
    return value or default


def require(name: str) -> str:
    value = get(name)
    if not value:
        raise RuntimeError(f"{name} is not set (see .env.example)")
    return value
