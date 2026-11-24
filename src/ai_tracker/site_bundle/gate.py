"""The licence gate of the bundle: ONE rule (ai_tracker.site.data.publishable) and one scanner.

Rule. A series may be shown with values only when `site.data.publishable(key, ctx)` is true (Spec.publish=True; a
derived series: every component). The exporter asks only this module, and this module only asks site.data, so the
old site and the bundle can never disagree.

Scan. After the documents are assembled and before anything is written, `scan(docs, ctx)` walks every JSON value of
every document. A withheld key (any series of the catalog, the derived series or the nowcast targets that is not
publishable) may only appear inside a list under a key named "withheld", and every entry of such a list may only
carry the fields of `WITHHELD_FIELDS` (names and reasons, never numbers). A withheld key anywhere else, as a dict key
or inside any string (word-bounded), is a violation and stops the build.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator

from ai_tracker.site import data as D
from ai_tracker.state.measures import Context

WITHHELD_FIELDS = frozenset({"key", "label", "source", "license", "why", "counted", "branch"})
WITHHELD_LIST_KEYS = frozenset({"withheld"})


def publishable(key: str | None, ctx: Context) -> bool:
    """The site's rule, unchanged (site.data.publishable)."""
    return D.publishable(key, ctx)


def candidate_keys(ctx: Context) -> set[str]:
    """Every series name the bundle could mention: catalog, derived series, nowcast targets and their components."""
    keys = set(ctx.specs) | set(ctx.derived) | set(D.NOWCAST_DERIVED)
    for comps in D.NOWCAST_DERIVED.values():
        keys |= set(comps)
    return keys


def withheld_keys(ctx: Context) -> set[str]:
    return {k for k in candidate_keys(ctx) if not publishable(k, ctx)}


def _pattern(keys: Iterable[str]) -> re.Pattern | None:
    keys = sorted(set(keys), key=len, reverse=True)
    if not keys:
        return None
    return re.compile(r"(?<![A-Za-z0-9_])(?:" + "|".join(re.escape(k) for k in keys) + r")(?![A-Za-z0-9_])")


def _walk(x, path: str, pat: re.Pattern, out: list[str]) -> None:
    if isinstance(x, dict):
        for k, v in x.items():
            p = f"{path}.{k}"
            if pat.search(str(k)):
                out.append(f"{p}: withheld key used as a dict key")
            if k in WITHHELD_LIST_KEYS and isinstance(v, list):
                for i, w in enumerate(v):
                    if not isinstance(w, dict):
                        out.append(f"{p}[{i}]: a withheld entry must be an object")
                        continue
                    extra = set(w) - WITHHELD_FIELDS
                    if extra:
                        out.append(f"{p}[{i}]: fields not allowed in a withheld entry: {sorted(extra)}")
                    for f, val in w.items():
                        if isinstance(val, (int, float)) and not isinstance(val, bool):
                            out.append(f"{p}[{i}].{f}: a withheld entry carries no numbers")
                continue
            _walk(v, p, pat, out)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            _walk(v, f"{path}[{i}]", pat, out)
    elif isinstance(x, str):
        m = pat.search(x)
        if m:
            out.append(f"{path}: names withheld series {m.group(0)!r} outside a withheld list")


def scan(docs: dict[str, object], ctx: Context | None = None, keys: Iterable[str] | None = None) -> list[str]:
    """Violations of the licence rule in `docs` (path -> JSON document); empty = clean."""
    keys = set(keys) if keys is not None else withheld_keys(ctx)
    out: list[str] = []
    pat = _pattern(keys)
    for name, doc in docs.items():
        if pat is not None and pat.search(name):
            out.append(f"{name}: a file is named after a withheld series")
        if pat is None:
            continue
        _walk(doc, name, pat, out)
    return out


def iter_withheld(x) -> Iterator[dict]:
    """Every entry of every withheld list in a document."""
    if isinstance(x, dict):
        for k, v in x.items():
            if k in WITHHELD_LIST_KEYS and isinstance(v, list):
                yield from (w for w in v if isinstance(w, dict))
            else:
                yield from iter_withheld(v)
    elif isinstance(x, list):
        for v in x:
            yield from iter_withheld(v)
