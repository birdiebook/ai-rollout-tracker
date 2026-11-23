"""Catalog entries, one module per source: each module defines SPECS: list[Spec].

Modules are discovered automatically (catalog.ALL), so parallel tracks never edit the same file.
"""

from __future__ import annotations

import importlib
import pkgutil


def discover() -> list:
    specs = []
    for mod in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
        if not mod.name.startswith("_"):
            specs += list(getattr(importlib.import_module(f"{__name__}.{mod.name}"), "SPECS", []))
    return specs
