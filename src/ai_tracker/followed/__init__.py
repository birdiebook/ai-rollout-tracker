"""Followed questions: questions the owner reads monthly, outside the branches (no state, no index, no core series).

Each question has a registered entry in docs/mattregister.md, catalog series with publish=False and a report:

    python -m ai_tracker.followed <question> --as-of YYYY-MM-DD [--json PATH] [--out PATH]
    python -m ai_tracker.followed antenner --as-of YYYY-MM-DD      one row per question (register F0, (c))

A question is any module in this package with `compute(as_of, ...)` and `render(report)` (found by `questions()`, no
registration). It may expose `antenna(report) -> dict` (common.antenna_row) for the overview. The shared engine is
followed/common.py and followed/aggregate.py (register 2026-11-26 "F0").

Reports use only rows known on the as-of date (observations.as_of semantics: known_from <= as-of).
"""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType


def questions() -> dict[str, ModuleType]:
    """{name: module} for every module of the package with callable compute and render, sorted by name."""
    out = {}
    for info in sorted(pkgutil.iter_modules(__path__), key=lambda i: i.name):
        if info.ispkg or info.name.startswith("_"):
            continue
        mod = importlib.import_module(f"{__name__}.{info.name}")
        if callable(getattr(mod, "compute", None)) and callable(getattr(mod, "render", None)):
            out[info.name] = mod
    return out
