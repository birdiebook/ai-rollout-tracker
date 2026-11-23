"""SEC EDGAR XBRL: balance-sheet (instant) facts per fiscal quarter, with vintages (known_from = filing date).

sec.py handles duration facts (flows: revenue, capex). Balance-sheet items (inventories, purchase
obligations) are instant facts: a value as of a date, with no start. companyfacts lists them without a
`start` field, and sec.facts skips them. This module reads them from companyfacts, and from a filing's
own XBRL instance when the fact is company-specific or dimensional (companyfacts has neither).

Quarter mapping. An instant is kept only when its date is a fiscal quarter end of the company, taken
from its duration facts (`fiscal_quarters`, e.g. revenue): other dates (an acquisition date, an
accounting-change opening balance) are dropped. The instant then gets the calendar quarter of that fiscal
quarter (sec.calendar_quarter, midpoint rule), so a balance and the flows of the same fiscal quarter
share a period label.

Vintages (leakage-critical), as in sec.vintages: for every filing date d, each quarter end takes the
latest fact filed <= d (priority list over sources: the first source with a fact for that date), and a
row is emitted when a calendar quarter's value is new or changed by more than sec.TOL. A balance repeated
as a comparative gives no new row; a restated one is a new vintage dated by the restating filing.
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree

import pandas as pd

from ai_tracker.sources import sec, sec_segment


@dataclass(frozen=True)
class Instant:
    end: pd.Timestamp
    val: float
    filed: pd.Timestamp
    form: str
    accn: str

    @property
    def rank(self) -> tuple:
        return (self.filed, self.form.endswith("/A"), self.accn)


def facts(cf: dict, tag: str, taxonomy: str = "us-gaap", unit: str = "USD") -> list[Instant]:
    """Instant facts for one concept from 10-Q/10-K-family filings in a companyfacts JSON."""
    concept = cf.get("facts", {}).get(taxonomy, {}).get(tag)
    if not concept:
        return []
    return [Instant(pd.Timestamp(f["end"]), float(f["val"]), pd.Timestamp(f["filed"]), f["form"], f.get("accn", ""))
            for f in concept.get("units", {}).get(unit, [])
            if "start" not in f and str(f.get("form", "")).startswith(sec.FORMS)]


def parse_instants(raw: bytes, concepts: set[str], dims: frozenset = frozenset(),
                   unit: str = "USD") -> list[tuple[str, pd.Timestamp, float]]:
    """(concept, date, value) for instant facts of `concepts` whose context dimensions are exactly `dims`.

    `dims` is a set of (axis, member) local names; empty = the non-dimensional (consolidated) fact.
    """
    X, D = sec_segment.XBRLI, sec_segment.XBRLDI
    root = ElementTree.fromstring(raw)
    contexts = {}
    for c in root.iter(X + "context"):
        inst = c.find(f"{X}period/{X}instant")
        if inst is None:
            continue
        cd = frozenset((sec_segment._local(m.get("dimension")), sec_segment._local(m.text or ""))
                       for m in c.iter(D + "explicitMember"))
        if cd == dims:
            contexts[c.get("id")] = pd.Timestamp(inst.text.strip())
    units = {}
    for u in root.iter(X + "unit"):
        m = u.find(f"{X}measure")
        units[u.get("id")] = sec_segment._local(m.text) if m is not None and m.text else ""
    out = []
    for el in root:
        if not isinstance(el.tag, str) or el.get("contextRef") not in contexts:
            continue
        name = el.tag.rsplit("}", 1)[-1]
        if name not in concepts or units.get(el.get("unitRef")) != unit:
            continue
        try:
            out.append((name, contexts[el.get("contextRef")], float((el.text or "").strip())))
        except ValueError:
            continue
    return out


def instance_instants(filings_raw: list[tuple[sec_segment.Filing, bytes]], concept: str,
                      dims: frozenset = frozenset(), unit: str = "USD") -> list[Instant]:
    """Instant facts of one concept and dimension set across filings (one value per date and filing)."""
    out = []
    for f, raw in filings_raw:
        seen = set()
        for _, end, val in parse_instants(raw, {concept}, dims, unit):
            if end not in seen:
                seen.add(end)
                out.append(Instant(end, val, pd.Timestamp(f.filed), f.form, f.accession))
    return out


def fiscal_quarters(flow_sources: list[list[sec.Fact]]) -> dict[pd.Timestamp, pd.Period]:
    """Fiscal quarter end -> calendar quarter, from a company's duration facts (all filings)."""
    return {end: sec.calendar_quarter(q.start, q.end) for end, q in sec.quarters_at(flow_sources).items()}


def vintages(sources: list[list[Instant]], quarters: dict[pd.Timestamp, pd.Period],
             scale: float = 1e-6) -> pd.DataFrame:
    """Release-dated quarterly rows (period, value * scale, known_from, fiscal_end), sorted by known_from.

    `sources` is a priority list (one list per concept or member). Dates that are not fiscal quarter ends
    in `quarters` are dropped.
    """
    allf = [f for fs in sources for f in fs if f.end in quarters]
    cutoffs = sorted({f.filed for f in allf})
    last: dict[str, float] = {}
    rows = []
    for d in cutoffs:
        by_end: dict[pd.Timestamp, Instant] = {}
        for fs in sources:
            latest: dict[pd.Timestamp, Instant] = {}
            for f in fs:
                if f.filed <= d and f.end in quarters and (f.end not in latest or f.rank > latest[f.end].rank):
                    latest[f.end] = f
            for end, f in latest.items():
                by_end.setdefault(end, f)
        by_period: dict[str, Instant] = {}
        for end, f in by_end.items():
            p = str(quarters[end])
            if p not in by_period or end > by_period[p].end:
                by_period[p] = f
        for p, f in sorted(by_period.items()):
            if p not in last or abs(last[p] - f.val) > sec.TOL:
                last[p] = f.val
                rows.append((p, f.val * scale, d, f.end))
    df = pd.DataFrame(rows, columns=["period", "value", "known_from", "fiscal_end"])
    return df.sort_values(["known_from", "period"], ignore_index=True)
