"""Review R25 of the owner-decision track (auto14k/agarbeslut, docs/granskning/r25_agarbeslut.md).

Passing tests: no Microsoft figure of the committed curated CSV survives `expectations.withhold` with the catalog's
publish flags; the surprise index reads no row of Microsoft or Amazon (so its Microsoft components are not read);
Amazon's published 2026 series changes definition (the fact behind R25-2).
Strict xfail until auto14k/x22-agarbeslut, now passing: R25-1, the surprise index lists only the guid_capex_* series of
the companies whose rows it reads (Meta and Alphabet); R25-2, a published guid_capex_* series that changes definition
within a period says so in its note. Synthetic tables and the committed CSV only, no network.
"""

from __future__ import annotations

import json
import math

import pandas as pd
import pytest

from ai_tracker import catalog, licenses
from ai_tracker.series import guidance_revisions as GR
from ai_tracker.sources import guidance_capex as GC
from ai_tracker.state import expectations as EX
from ai_tracker.state import snapshot as S
from tests.test_agarbeslut import WHEN, _capex_world, _series
from tests.test_guidance_revisions import csv_rows

INDEX_KEYS = ("f1_surprise_index", "f1_surprise_index_n")


@pytest.fixture(autouse=True)
def _index_from_2016(monkeypatch):
    monkeypatch.setattr(GR, "COVERAGE_FROM", pd.Period("2016Q1", "Q-DEC"))


def _catalog_publishable():
    specs = catalog.by_key()
    return lambda k: bool(k in specs and specs[k].publish)


def _numbers(obj, path="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _numbers(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _numbers(v, f"{path}[{i}]")
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool) and math.isfinite(obj):
        yield path, float(obj)


def _microsoft_only_figures(csv: pd.DataFrame) -> set[float]:
    """Microsoft's values, event sizes and break sizes in the curated CSV, minus numbers another company also has."""
    st = GR.statements(None, csv)
    ev, br = GR.events(st), GR.break_statements(st)

    def finite(xs):
        return {float(x) for x in xs if x is not None and isinstance(x, (int, float)) and math.isfinite(float(x))}

    msft = finite(csv.loc[csv["company"] == "msft", "value_lo"]) | finite(csv.loc[csv["company"] == "msft", "value_hi"])
    msft |= finite(ev.loc[ev["company"] == "msft", "size"]) | finite(br.loc[br["company"] == "msft", "size"])
    msft |= finite(br.loc[br["company"] == "msft", "prev_value"]) | finite(br.loc[br["company"] == "msft", "value"])
    other = finite(csv.loc[csv["company"] != "msft", "value_lo"]) | finite(ev.loc[ev["company"] != "msft", "size"])
    return {x for x in msft - other if x != 0.0}


def test_no_microsoft_figure_of_the_committed_csv_survives_the_public_section():
    """The committed curated CSV (Microsoft's rows from microsoft.com, class okänd) through the real section and the
    real publish flags: no number from Microsoft's rows and not the break's reason text."""
    csv = GC.load()
    figures = _microsoft_only_figures(csv)
    # not vacuous (175 000 is also Alphabet's 2026 low end, so it cannot be told apart and is not searched for)
    assert {190000.0, 170000.0} <= figures and any(-9 < f < -8 for f in figures)
    sec = S._clean(EX.section("2026-11-30", None, csv))
    before = [v for _p, v in _numbers(sec)]
    assert any(math.isclose(v, f, abs_tol=1e-9) for v in before for f in figures)  # the section had them
    out = EX.withhold(sec, _catalog_publishable())
    assert out["values_withheld_companies"] == ["msft"]
    hits = [(p, v) for p, v in _numbers(out) for f in figures if math.isclose(v, f, abs_tol=1e-9)]
    assert hits == []
    text = json.dumps(out, ensure_ascii=False)
    for reason in GR.DEFINITION_BREAKS.values():
        assert reason not in text and "175bn" not in text


def _change(rows: pd.DataFrame, companies: tuple[str, ...]) -> pd.DataFrame:
    """Scale the values of `companies` and add one more statement for each of them."""
    d = rows.copy()
    d[["value_lo", "value_hi"]] = d[["value_lo", "value_hi"]].astype(float)
    m = d["company"].isin(companies)
    d.loc[m, ["value_lo", "value_hi"]] *= 1.37
    defs = {"msft": "MSFT_CAPEX_INCL_FL", "amzn": "AMZN_CASH_CAPEX", "meta": "META_CAPEX_INCL_FL",
            "googl": "GOOGL_CAPEX"}
    extra = csv_rows([{"company": c, "period": "2024", "kind": "approx", "lo": 777, "definition": defs[c],
                       "filed": "2024-09-03", "id": f"r25-{c}"} for c in companies])
    return pd.concat([d, extra], ignore_index=True)


@pytest.mark.parametrize("key", INDEX_KEYS)
def test_the_surprise_index_reads_no_row_of_microsoft_or_amazon(key):
    """Same proof as the track's for the company surprises, applied to the index (R25-1)."""
    table, rows = _capex_world()
    base = _series(key, table, rows)
    out = GR.compute(table, rows, WHEN)
    assert "meta" in ",".join(out["surprise_index"]["companies"])  # the index holds a CSV company
    pd.testing.assert_frame_equal(base, _series(key, table, _change(rows, ("msft", "amzn"))))
    if key == "f1_surprise_index":  # the perturbation is real: Meta's rows do move it
        assert not base.equals(_series(key, table, _change(rows, ("meta",))))


def _definition_switches(df: pd.DataFrame, key: str) -> list[tuple[str, str, str, str]]:
    """(period, known_from, old definition, new definition) where a new version of the series comes from a row with
    another definition than the version before it (same filter as guidance_capex.series_frame)."""
    company, hz, measure, *base = key.removeprefix("guid_capex_").split("_", 3)
    col = GC.MEASURES[measure]
    d = df[(df["company"] == company) & (df["horizon"] == hz.upper())].copy()
    if measure == "dir":
        d = d[(d["kind"] == "direction") & (d["direction_base"] == base[0])]
    else:
        d = d[d["kind"] != "direction"]
    d = d.dropna(subset=[col])
    d["p"] = [GC._period(r) for _, r in d.iterrows()]
    out, last = [], {}
    for r in d.sort_values("known_from", kind="stable").itertuples(index=False):
        v = getattr(r, col)
        if r.p in last and last[r.p][0] == v:
            continue
        if r.p in last and last[r.p][1] != r.definition:
            out.append((r.p, str(pd.Timestamp(r.known_from).date()), last[r.p][1], r.definition))
        last[r.p] = (v, r.definition)
    return out


def test_the_amazon_switch_is_in_the_published_series():
    """The fact behind R25-2: Amazon's 2026 value goes from 200 000 (AMZN_CAPEX_UNSPEC) to 220 000 (AMZN_CASH_CAPEX)."""
    df = GC.load()
    assert _definition_switches(df, "guid_capex_amzn_cy_lo") == [
        ("2026", "2026-10-29", "AMZN_CAPEX_UNSPEC", "AMZN_CASH_CAPEX")]
    assert catalog.by_key()["guid_capex_amzn_cy_lo"].publish
    rows = GC.series_frame(df, "amzn", "CY", "lo")
    assert list(rows.loc[rows["period"] == "2026", "value"]) == [200000.0, 220000.0]  # one series, two versions


def test_a_published_guidance_series_names_a_definition_switch_within_a_period():
    """R25-2, fixed in auto14k/x22-agarbeslut: the note names the switch (guidance_capex.switch_note)."""
    df = GC.load()
    specs = catalog.by_key()
    bad = []
    for s in GC.specs(GC.PATH):
        note = specs[s.key].note
        for period, kf, old, new in _definition_switches(df, s.key):
            if specs[s.key].publish and not ("definitionsbyte" in note.lower() and period in note):
                bad.append((s.key, period, kf, old, new))
    assert bad == []


@pytest.mark.parametrize("key", INDEX_KEYS)
def test_the_surprise_index_lists_only_the_rows_it_reads(key):
    """R25-1, fixed in auto14k/x22-agarbeslut: the components are Meta's and Alphabet's (GR.CSV_READS)."""
    spec = catalog.by_key()[key]
    reads = licenses.CURATED_READS[key][1]
    gate = {k for k in spec.components if k.startswith("guid_capex_")}
    assert {GR.csv_company(k) for k in gate} <= set(reads)
