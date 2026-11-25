"""JSON Schema (draft 2020-12) of every bundle document, and validation.

The schemas live in src/ai_tracker/site_bundle/schema/*.json and are copied into the bundle under schema/, so the
front end can validate (or generate types) against exactly the files Python validated against. `common.json` holds
the shared definitions ($defs); the other files reference it by relative $ref.
"""

from __future__ import annotations

import fnmatch
import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SCHEMA_DIR = Path(__file__).with_name("schema")
BASE = "https://birdiebook.github.io/ai-rollout-tracker/schema/v1/"

# Document path pattern -> schema name (first match wins).
ROUTES: list[tuple[str, str]] = [
    ("manifest.json", "manifest"),
    ("overview.json", "overview"),
    ("flow.json", "flow"),
    ("branch/*.json", "branch"),
    ("series/index.json", "series_index"),
    ("series/*.json", "series"),
    ("nowcast/d2.json", "horizons"),
    ("nowcast/*.json", "nowcast"),
    ("regime.json", "regime"),
    ("method.json", "method"),
    ("withheld.json", "withheld"),
    ("story/index.json", "story_index"),
    ("story/*.json", "story"),
    ("report/index.json", "report_index"),
    ("report/*.json", "report"),
    ("letters.json", "letters"),
    ("letters/*.json", "publication"),
    ("reports/*.json", "publication"),
]


def schema_for(path: str) -> str:
    for pat, name in ROUTES:
        if fnmatch.fnmatchcase(path, pat):
            return name
    raise KeyError(f"no schema for bundle path {path!r}")


def names() -> list[str]:
    return sorted(p.stem for p in SCHEMA_DIR.glob("*.json"))


@lru_cache(maxsize=1)
def _registry() -> Registry:
    resources = []
    for p in SCHEMA_DIR.glob("*.json"):
        s = json.loads(p.read_text(encoding="utf-8"))
        resources.append((s["$id"], Resource.from_contents(s)))
    return Registry().with_resources(resources)


@lru_cache(maxsize=None)
def validator(name: str) -> Draft202012Validator:
    s = json.loads((SCHEMA_DIR / f"{name}.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(s)
    return Draft202012Validator(s, registry=_registry())


def errors(path: str, doc) -> list[str]:
    v = validator(schema_for(path))
    out = []
    for e in sorted(v.iter_errors(doc), key=lambda e: list(e.absolute_path)):
        loc = "/".join(str(x) for x in e.absolute_path)
        out.append(f"{path}#/{loc}: {e.message[:300]}")
    return out


def validate(docs: dict[str, object]) -> list[str]:
    """Schema errors of every document (path -> doc); empty = valid."""
    out = []
    for path, doc in docs.items():
        out.extend(errors(path, doc))
    return out
