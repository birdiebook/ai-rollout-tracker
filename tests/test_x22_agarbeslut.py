"""Fix track X22 after review R25 (docs/granskning/r25_agarbeslut.md).

R25-1: the surprise index lists the guid_capex_* series of Meta and Alphabet only (the rows it reads) and is withheld
explicitly until the owner decides, with that as its public reason (Spec.withheld_reason). R25-2: a guid_capex_*
version from a row with another definition than the version before it is a definition switch: the series' note names
it and the monthly letter writes the switch, not "tidigare <value>". Synthetic CSV files and the committed CSV only,
no network.
"""

from __future__ import annotations

import csv
import dataclasses
import json

import pandas as pd

from ai_tracker import catalog, letter as L
from ai_tracker.series import guidance_revisions as GR
from ai_tracker.site import data as D
from ai_tracker.sources import guidance_capex as GC
from ai_tracker.state.measures import Context

OBS_COLUMNS = ["series", "freq", "period", "value", "known_from", "source", "fetched_at"]


def _write(path, rows):
    """rows: (company, period, kind, value or direction code, definition, filed)."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=GC.COLUMNS)
        w.writeheader()
        for i, (company, period, kind, v, definition, filed) in enumerate(rows):
            direction = kind == "direction"
            w.writerow({"id": f"x22-{i}", "company": company, "horizon": "CY", "period": period,
                        "period_start": f"{period}-01-01", "period_end": f"{period}-12-31", "kind": kind,
                        "value_lo": "" if direction else v, "value_hi": "" if direction else v,
                        "unit": "code" if direction else "MUSD", "direction_code": v if direction else "",
                        "direction_base": "yoy" if direction else "", "definition": definition, "filed": filed,
                        "accepted": "", "doc_type": "8-K", "source_url": f"https://www.sec.gov/Archives/x22-{i}.htm",
                        "accession": "", "locator": "sentence #1", "sentence_sha256": "0" * 64, "note": ""})
    return path


def _world(tmp_path):
    return _write(tmp_path / "guidance_capex.csv", [
        ("amzn", "2025", "approx", 100, "AMZN_CASH_CAPEX", "2025-02-06"),
        ("amzn", "2025", "approx", 110, "AMZN_CASH_CAPEX", "2025-07-31"),  # a revision: same definition
        ("amzn", "2026", "approx", 200, "AMZN_CAPEX_UNSPEC", "2026-02-05"),
        ("amzn", "2026", "approx", 200, "AMZN_CAPEX_UNSPEC", "2026-04-09"),  # repeated: no version
        ("amzn", "2026", "approx", 220, "AMZN_CASH_CAPEX", "2026-10-29"),  # the switch (as amzn-18)
        ("googl", "2026", "direction", 2, "GOOGL_TECH_INFRA", "2026-02-05"),
        ("googl", "2026", "direction", 2, "GOOGL_CAPEX", "2026-06-04"),  # another definition, same code: no version
    ])


# ------------------------------------------------------------------ R25-2


def test_a_definition_switch_is_found_and_named_in_the_note(tmp_path):
    p = _world(tmp_path)
    df = GC.load(p)
    switch = [("2026", "2026-10-29", "AMZN_CAPEX_UNSPEC", "AMZN_CASH_CAPEX")]
    assert GC.definition_switches(df, "amzn", "CY", "lo") == switch
    assert GC.definition_switches(df, "amzn", "CY", "hi") == switch
    assert GC.definition_switches(df, "googl", "CY", "dir", "yoy") == []
    # the series itself is unchanged: one series, both versions
    rows = GC.series_frame(df, "amzn", "CY", "lo")
    assert list(zip(rows["period"], rows["value"])) == [("2025", 100.0), ("2025", 110.0), ("2026", 200.0),
                                                         ("2026", 220.0)]
    notes = {s.key: s.note for s in GC.specs(p)}
    for key in ("guid_capex_amzn_cy_lo", "guid_capex_amzn_cy_hi"):
        assert "Definitionsbyte inom en period, inte en revidering (F1): 2026: AMZN_CAPEX_UNSPEC → AMZN_CASH_CAPEX " \
               "(2026-10-29)." in notes[key], key
    assert "definitionsbyte" not in notes["guid_capex_googl_cy_dir_yoy"].lower()
    assert GC.definition_switch("guid_capex_amzn_cy_lo", "2026", pd.Timestamp("2026-10-29"), p) == (
        "AMZN_CAPEX_UNSPEC", "AMZN_CASH_CAPEX")
    assert GC.definition_switch("guid_capex_amzn_cy_lo", "2025", "2025-07-31", p) is None  # a revision
    assert GC.definition_switch("guid_capex_amzn_cy_lo", "2026", "2026-02-05", p) is None  # a new period
    assert GC.definition_switch("capex_amzn", "2026", "2026-10-29", p) is None  # not a guidance series


def test_the_letter_writes_the_switch_not_an_earlier_value(tmp_path, monkeypatch):
    monkeypatch.setattr(GC, "PATH", _world(tmp_path))
    text = L.guidance_was("guid_capex_amzn_cy_lo", "2026", 200.0, pd.Timestamp("2026-10-29"))
    assert text == " (definitionsbyte från AMZN_CAPEX_UNSPEC till AMZN_CASH_CAPEX, inte en revidering)"
    assert "tidigare" not in text and not L.BANNED_WORDS.search(text)
    assert L.guidance_was("guid_capex_amzn_cy_lo", "2025", 100.0, pd.Timestamp("2025-07-31")) == " (tidigare 100)"
    assert L.guidance_was("guid_capex_amzn_cy_lo", "2026", float("nan"), pd.Timestamp("2026-02-05")) == ""


def test_the_committed_amazon_switch_in_the_letter_and_the_note():
    """The case R25-2 found: the October letter wrote '2026: 220 000 MUSD (tidigare 200 000)'."""
    text = L.guidance_was("guid_capex_amzn_cy_lo", "2026", 200000.0, pd.Timestamp("2026-10-29"))
    assert "definitionsbyte från AMZN_CAPEX_UNSPEC till AMZN_CASH_CAPEX" in text and "200" not in text
    spec = catalog.by_key()["guid_capex_amzn_cy_hi"]
    assert spec.publish and "2026: AMZN_CAPEX_UNSPEC → AMZN_CASH_CAPEX (2026-10-29)" in spec.note
    # Meta's 2026 revisions keep their earlier value
    meta = GC.series_frame(GC.load(), "meta", "CY", "lo")
    two = meta[meta["period"] == "2026"].iloc[:2]
    assert len(two) == 2
    assert L.guidance_was("guid_capex_meta_cy_lo", "2026", two["value"].iloc[0], two["known_from"].iloc[1]).startswith(
        " (tidigare ")


# ------------------------------------------------------------------ R25-1


def _ctx():
    return Context(table=pd.DataFrame(columns=OBS_COLUMNS))


def test_the_withheld_index_gives_the_pending_owner_decision_as_its_public_reason():
    ctx = _ctx()
    for key in ("f1_surprise_index", "f1_surprise_index_n"):
        entry = D.withheld_entry(key, ctx, counted=False)
        assert entry["why"] == GR.AWAITING_OWNER[key] and "väntar på ägarbeslut" in entry["why"]
        assert "guid_capex_" not in json.dumps(entry, ensure_ascii=False)
        assert not D.publishable(key, ctx)
        assert all(D.publishable(k, ctx) for k in catalog.by_key()[key].components)
    # the pooled revision series still name the series they are withheld for
    pooled = D.withheld_entry("f1_rev_index_4q", ctx, counted=False)["why"]
    assert pooled.startswith("härledd ur serier som inte publiceras: ") and "guid_capex_msft_cy_lo" in pooled
    assert "guid_capex_amzn" not in pooled  # Amazon's are published


def test_a_withheld_reason_needs_publish_false():
    spec = catalog.by_key()["f1_surprise_index"]
    assert catalog.validate([spec]) == []
    errors = catalog.validate([dataclasses.replace(spec, publish=True)])
    assert "f1_surprise_index: withheld_reason needs publish=False" in errors
    other = catalog.by_key()["f1_surprise_meta_capex"]
    assert other.publish and other.withheld_reason == "" and D.why_withheld(dataclasses.replace(
        other, publish=False)) == "inte godkänd för publicering i katalogen (publish=False)"
