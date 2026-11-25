"""The licence scan of the BUILT site (R-W1 1b): the bundle gate (site_bundle.gate) sees only the bundle, but the
front end also carries data written into web/src by hand (holdout.ts, reconciliations.json, rules.json, ...). This
scan runs on the output of `vite build` and on web/src itself, so a withheld key or label in a constant stops the
pages workflow the same way a leak in the bundle stops the bundle build.

    python -m ai_tracker.site_bundle scan-build web/build [--src web/src]

Rules (withheld = the catalog's withheld keys, or the synthetic world's when the built bundle is synthetic; labels =
the labels of withheld series that are not also the label of a publishable series):

- `data/**/*.json` (the bundle's copy): the bundle gate, `gate.scan`.
- `**/__data.json` (SvelteKit's prerendered load data, devalue-flattened): unflattened, then the gate's walk, so a
  withheld key or label may only stand inside a `withheld` list.
- `**/*.html`: every `withheld:[...]` list in the inline data is cut out, and the rest (markup and data) must hold no
  withheld key. Labels are allowed in the markup: the pages name withheld series with their reason (the rendered
  withheld lists), and a label in a constant is caught in `_app` or `--src`.
- `_app/**/*.{js,json,css}` (code and the constants compiled into it) and every source file under `--src`: no
  withheld key and no withheld label at all.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

from ai_tracker.site_bundle import gate as G

SRC_SUFFIXES = {".ts", ".js", ".mjs", ".json", ".svelte", ".css", ".html"}
APP_SUFFIXES = {".js", ".json", ".css"}
MIN_LABEL = 12  # shorter labels are too generic to search for as text


def withheld_terms(synthetic: bool) -> tuple[set[str], set[str]]:
    """(withheld keys, withheld labels) of the real catalog or of the synthetic world."""
    from ai_tracker import observations
    from ai_tracker.state.measures import Context

    if synthetic:
        from ai_tracker.site_bundle import synthetic as SY

        ctx = Context(observations._empty(), specs=SY.specs(), derived={})
    else:
        ctx = Context(observations._empty())
    keys = G.withheld_keys(ctx)
    shown = {s.label for k, s in ctx.specs.items() if G.publishable(k, ctx)}
    labels = {ctx.specs[k].label for k in keys if k in ctx.specs} - shown
    return keys, {x for x in labels if len(x) >= MIN_LABEL}


def _label_pattern(labels: Iterable[str]) -> re.Pattern | None:
    labels = sorted(set(labels), key=len, reverse=True)
    return re.compile("|".join(re.escape(x) for x in labels)) if labels else None


# ------------------------------------------------------------------ devalue (SvelteKit's __data.json)

_SPECIAL = {-1: None, -2: None, -3: float("nan"), -4: float("inf"), -5: float("-inf"), -6: -0.0}


def unflatten(values: list):
    """devalue.unflatten: the flattened array -> the value (types without a JSON form become their plain parts)."""
    memo: dict[int, object] = {}

    def h(i):
        if isinstance(i, int) and i < 0:
            return _SPECIAL.get(i)
        if i in memo:
            return memo[i]
        v = values[i]
        if isinstance(v, list):
            if v and isinstance(v[0], str):  # [type, ...]: Date, Set, Map, RegExp, BigInt, Object, null-proto
                kind, rest = v[0], v[1:]
                if kind in ("Date", "RegExp", "BigInt", "URL", "URLSearchParams"):
                    out = [kind, *rest]
                elif kind == "null":
                    out = {rest[j]: h(rest[j + 1]) for j in range(0, len(rest), 2)}
                else:
                    out = [kind, *[h(x) if isinstance(x, int) else x for x in rest]]
                memo[i] = out
                return out
            out = []
            memo[i] = out
            out.extend(h(x) for x in v)
            return out
        if isinstance(v, dict):
            out = {}
            memo[i] = out
            for k, x in v.items():
                out[k] = h(x)
            return out
        memo[i] = v
        return v

    return h(0) if values else None


def sveltekit_data(doc) -> list:
    """The nodes of a __data.json, unflattened."""
    if not isinstance(doc, dict):
        return []
    nodes = doc.get("nodes") or []
    return [unflatten(n["data"]) for n in nodes if isinstance(n, dict) and isinstance(n.get("data"), list)]


# ------------------------------------------------------------------ withheld lists in inline JS data (HTML)

_WITHHELD_OPEN = re.compile(r"""(?:\bwithheld|"withheld")\s*:\s*\[""")


def _close(text: str, i: int) -> int:
    """Index after the bracket that closes the one opened just before i (JS strings and escapes respected)."""
    depth, quote = 1, None
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in "\"'`":
            quote = c
        elif c in "[{(":
            depth += 1
        elif c in "]})":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(text)


def strip_withheld_lists(text: str) -> str:
    out, pos = [], 0
    for m in _WITHHELD_OPEN.finditer(text):
        if m.start() < pos:
            continue
        out.append(text[pos:m.start()])
        pos = _close(text, m.end())
    out.append(text[pos:])
    return "".join(out)


# ------------------------------------------------------------------ the scan


def _text_hits(name: str, text: str, kp: re.Pattern | None, lp: re.Pattern | None) -> list[str]:
    out = []
    for pat, what in ((kp, "withheld key"), (lp, "withheld label")):
        if pat is None:
            continue
        found = sorted(set(pat.findall(text)))
        if found:
            out.append(f"{name}: {what} {found[:3]} outside a withheld list")
    return out


def scan_build(build: Path, src: Path | None = None, keys: set[str] | None = None,
               labels: set[str] | None = None) -> list[str]:
    """Violations in a built site (and optionally a source tree); empty = clean. Without `keys`, the terms come from
    the built bundle's manifest (synthetic world or catalog)."""
    build = Path(build)
    if keys is None:
        man = build / "data" / "manifest.json"
        synthetic = bool(json.loads(man.read_text(encoding="utf-8")).get("synthetic")) if man.is_file() else False
        keys, labels = withheld_terms(synthetic)
    labels = labels or set()
    kp, lp = G._pattern(keys), _label_pattern(labels)
    out: list[str] = []
    n = 0
    for p in sorted(build.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(build).as_posix()
        n += 1
        if kp is not None and kp.search(rel):
            out.append(f"{rel}: a file is named after a withheld series")
        if rel.startswith("data/") and p.suffix == ".json":
            out += G.scan({rel: json.loads(p.read_text(encoding="utf-8"))}, keys=keys)
        elif p.name == "__data.json":
            for i, node in enumerate(sveltekit_data(json.loads(p.read_text(encoding="utf-8")))):
                out += G.scan({f"{rel}#node{i}": node}, keys=keys)
                if lp is not None:
                    stripped = strip_withheld_lists(json.dumps(node, ensure_ascii=False))
                    out += _text_hits(f"{rel}#node{i}", stripped, None, lp)
        elif p.suffix == ".html":
            out += _text_hits(rel, strip_withheld_lists(p.read_text(encoding="utf-8", errors="replace")), kp, None)
        elif rel.startswith("_app/") and p.suffix in APP_SUFFIXES:
            out += _text_hits(rel, p.read_text(encoding="utf-8", errors="replace"), kp, lp)
    if n == 0:
        out.append(f"{build}: no files (run the build first)")
    if src is not None:
        out += scan_src(Path(src))
    return out


def scan_src(src: Path, keys: set[str] | None = None, labels: set[str] | None = None) -> list[str]:
    """No withheld key or label of the catalog in any source file of the front end (constants, components, tests):
    the sources are the same whichever bundle the site is built from."""
    if keys is None:
        keys, labels = withheld_terms(False)
    kp, lp = G._pattern(keys), _label_pattern(labels or set())
    out = []
    for p in sorted(Path(src).rglob("*")):
        if p.is_file() and p.suffix in SRC_SUFFIXES:
            out += _text_hits(p.as_posix(), p.read_text(encoding="utf-8", errors="replace"), kp, lp)
    return out
