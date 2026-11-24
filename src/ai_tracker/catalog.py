"""Data catalog: every series in the observation table, with metadata.

One `Spec` per series: branch (G1-G9, docs/plan.md), label, unit, frequency, source, licence,
how to fetch it, publication lag (-> known_from) and whether it gets revised.

Fetch contract. `Spec.fetch()` returns either
- a pd.Series indexed by period (any pandas period frequency matching `Spec.freq`), or
- a pd.DataFrame with columns period, value, known_from: for release-dated sources where each value
  carries its real release date (e.g. SEC filings with their `filed` date). Then known_from comes
  from the source, not from `lag_days`. An optional `source` column labels rows (default "release";
  "backfill" for rows dated by period end + lag because no dated document exists).

Series live in ai_tracker/series/<source>.py (SPECS list), discovered automatically.
`python -m ai_tracker.catalog` prints the catalog as Markdown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

BRANCHES = {
    "G1": "Förmåga",
    "G2": "Kostnad",
    "G3": "Användning",
    "G4": "Intäkter",
    "G5": "Investeringar och finansiering",
    "G6": "Utbud och halvledare",
    "G7": "Fysiska flaskhalsar",
    "G8": "Arbete och produktivitet",
    "G9": "Forskning och öppet ekosystem",
}

# Period frequencies used on the observation table (pandas period aliases).
# "2W" = ISO fortnight (Census BTOS cycles): stored as the W-SUN week the fortnight ends; consecutive
# fortnights are numbered by ISO year * 26 + fortnight (see observations.fortnight_ordinal).
FREQS = {"D": "D", "W": "W-SUN", "2W": "W-SUN", "M": "M", "Q": "Q-DEC", "A": "Y-DEC"}


@dataclass
class Spec:
    key: str
    branch: str  # G1..G9
    label: str  # Swedish, for the dashboard
    unit: str
    freq: str  # one of FREQS
    source: str
    fetch: Callable[[], pd.Series | pd.DataFrame] = field(repr=False)
    lag_days: int  # typical days after period end until published (conservative); ignored for release-dated rows
    license: str  # licence or terms, as checked in phase 1 ("unverified" until then)
    revised: bool = False
    publish: bool = False  # may derived values be shown on the public dashboard? Only after the licence check
    question: str = ""  # one line: what this series tells us about its branch
    note: str = ""
    # Freshness (warehouse.fresh): max days from the newest period's end to today; None = derived from
    # freq + lag_days. Override only with a documented reason in `note`.
    max_age_days: int | None = None
    closed: bool = False  # the series has ended (regime closed, table discontinued): no freshness check
    # Derived from other catalog series (read from the observation table): refreshed after every other series,
    # and publish=True needs every component publishable.
    components: tuple[str, ...] = ()
    # A notice the source's terms require to be displayed with the data (e.g. the Census Data API's), quoted in
    # `license`. The site shows it with the series' attribution and in the footer once the series has rows.
    notice: str = ""


def _all() -> list[Spec]:
    from ai_tracker.series import discover

    return discover()


ALL: list[Spec] = _all()


def by_key(specs: list[Spec] | None = None) -> dict[str, Spec]:
    return {s.key: s for s in (ALL if specs is None else specs)}


def validate(specs: list[Spec] | None = None) -> list[str]:
    """Problems with the catalog; empty list = valid. Run by tests/test_catalog.py."""
    specs = ALL if specs is None else specs
    errors = []
    seen = set()
    for s in specs:
        if s.key in seen:
            errors.append(f"{s.key}: duplicate key")
        seen.add(s.key)
        if s.branch not in BRANCHES:
            errors.append(f"{s.key}: unknown branch {s.branch!r}")
        if s.freq not in FREQS:
            errors.append(f"{s.key}: unknown freq {s.freq!r}")
        if not s.license.strip():
            errors.append(f"{s.key}: licence missing (write 'unverified' until checked)")
        if s.publish and s.license.strip().lower() == "unverified":
            errors.append(f"{s.key}: publish=True needs a checked licence")
        if s.max_age_days is not None and s.max_age_days <= 0:
            errors.append(f"{s.key}: max_age_days must be positive")
        if (s.closed or s.max_age_days is not None) and not s.note.strip():
            errors.append(f"{s.key}: closed or max_age_days needs a reason in note")
        if s.notice and s.notice not in s.license:
            errors.append(f"{s.key}: notice must be quoted in license (the terms that require it)")
    keys = {**by_key(), **{s.key: s for s in specs}}  # components may live in other modules
    for s in specs:
        missing = [c for c in s.components if c not in keys]
        if missing:
            errors.append(f"{s.key}: unknown components {missing}")
        if s.publish and any(c in keys and not keys[c].publish for c in s.components):
            errors.append(f"{s.key}: publish=True needs every component publishable")
    return errors


def to_markdown(specs: list[Spec] | None = None) -> str:
    specs = ALL if specs is None else specs
    lines = ["# Datakatalog", ""]
    if not specs:
        return "\n".join(lines + ["Inga serier ännu (läggs till i fas 2)."]) + "\n"
    for code, name in BRANCHES.items():
        rows = [s for s in specs if s.branch == code]
        if not rows:
            continue
        lines += [f"## {code} {name}", "", "| Nyckel | Serie | Enhet | Frekv. | Källa | Licens | Publiceras |",
                  "|---|---|---|---|---|---|---|"]
        lines += [f"| `{s.key}` | {s.label} | {s.unit} | {s.freq} | {s.source} | {s.license} | "
                  f"{'ja' if s.publish else 'nej'} |" for s in rows]
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    print(to_markdown())
