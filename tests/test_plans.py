"""Multi-year plans (step 2, D1): candidate selection, the curated CSV loader, series and the sampling check.

No network. Fixture sentences are synthetic (company-like wording, made-up numbers), so no source text is copied
into the repo.
"""

from __future__ import annotations

import csv

import pandas as pd
import pytest

from ai_tracker import catalog, plans_check
from ai_tracker.sources import guidance_capex as gc
from ai_tracker.sources import plans
from ai_tracker.sources import plans_corpus as pc

# ------------------------------------------------------------------ candidate selection


@pytest.mark.parametrize("sentence, why", [
    ("We are increasing our investment in capital expenditures in 2031 to approximately $99 billion.", "dollar"),
    ("We now have 1.1 GW of active power and 3.3 GW of contracted power.", "power"),
    ("We expect capital expenditures to grow meaningfully in 2032.", "horizon"),
    ("We will roughly double our total data center footprint over the next two years.", "horizon"),
    ("We expect capex to be higher next year.", "forward"),
    ("Revenue backlog was $77.7 billion at quarter end.", "dollar"),
])
def test_candidates_are_selected_broadly_in_any_tense(sentence, why):
    assert pc.is_candidate(sentence, 2030) == why


@pytest.mark.parametrize("sentence", [
    "Revenue was $12.3 billion, up 10%.",  # a number but no plan keyword
    "Our investments in marketable securities were $4.5 billion.",  # 'invest' not about infrastructure
    "The data center segment performed well.",  # keyword but nothing forward or numeric
])
def test_non_candidates(sentence):
    assert pc.is_candidate(sentence, 2030) is None


def test_candidates_carry_locator_and_hash():
    text = ("Intro sentence here. We expect capital expenditures to grow meaningfully in 2032. Revenue was $5 "
            "billion.")
    doc = pc.Document("meta", "8-K EX-99.1", "https://www.sec.gov/x.htm", "0000000000-30-000001", "2030-10-29",
                      "2030-10-29T20:00:00.000Z", "8-K", "2.02")
    out = pc.candidates(doc, text)
    assert [c["k"] for c in out] == [1]
    assert out[0]["sha256"] == gc.sentence_hash(gc.sentences(text)[1])


def test_msft_call_dates_follow_the_results_8k():
    d = pc.Document("msft", "8-K EX-99.1", "https://www.sec.gov/a.htm", "a", "2030-10-29", "", "8-K", "2.02,9.01")
    (call,) = pc.msft_call_documents([d])
    assert call.url.endswith("fy-2031/earnings-fy-2031-q1") and call.filed == "2030-10-29"


# ------------------------------------------------------------------ CSV loader

SHA = "a" * 64


def row(**kw) -> dict:
    base = {"id": "meta-p01", "company": "meta", "measure": "CAPEX", "kind": "direction", "value_lo": "",
            "value_hi": "", "unit": "code", "direction_code": "2", "direction_base": "yoy", "horizon": "Y",
            "year_basis": "CY", "period_start": "2031-01-01", "period_end": "2031-12-31", "scope": "global",
            "definition": "META_CAPEX_INCL_FL", "filed": "2030-10-29", "accepted": "2030-10-29T20:00:00.000Z",
            "doc_type": "8-K EX-99.1", "source_url": "https://www.sec.gov/x.htm", "accession": "0000000000-30-1",
            "locator": "CFO outlook; sentence #3", "sentence_sha256": SHA, "xref": "", "note": ""}
    return base | kw


def write(tmp_path, rows) -> object:
    p = tmp_path / "plans.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=plans.COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return p


BACKLOG = dict(id="crwv-b1", company="crwv", measure="BACKLOG", kind="reported", value_lo="50000",
               value_hi="50000", unit="MUSD", direction_code="", direction_base="", horizon="ASOF",
               period_start="2030-09-30", period_end="2030-09-30", definition="CRWV_BACKLOG", filed="2030-11-10",
               accepted="2030-11-10T21:00:00.000Z")


def test_valid_rows_load(tmp_path):
    df = plans.load(write(tmp_path, [row(), row(id="crwv-b1", **{k: v for k, v in BACKLOG.items() if k != "id"})]))
    assert len(df) == 2 and df["known_from"].iloc[0] == pd.Timestamp("2030-10-29")


@pytest.mark.parametrize("bad, msg", [
    (dict(period_start="2030-01-01", period_end="2030-12-31", kind="approx", value_lo="9", value_hi="9",
          unit="MUSD", direction_code="", direction_base=""), "guidance_capex"),  # current year: E1's domain
    (dict(period_end="2030-06-30", period_start="2030-01-01"), "period ended"),
    (dict(definition="NOPE"), "unknown definition"),
    (dict(direction_code="3"), "direction"),
    (dict(kind="range", value_lo="9", value_hi="8", unit="MUSD", direction_code="", direction_base=""), "value_lo >"),
    (dict(kind="approx", value_lo="9", value_hi="9", unit="MW"), "unit"),
    (dict(locator="somewhere"), "locator"),
    (dict(sentence_sha256="xyz"), "sha256"),
    (dict(accepted="2030-11-20T20:00:00.000Z"), "accepted"),
    (dict(horizon="OPEN", kind="direction"), "OPEN"),
])
def test_invalid_rows_are_refused(tmp_path, bad, msg):
    with pytest.raises(plans.CsvError, match=msg):
        plans.load(write(tmp_path, [row(**bad)]))


def test_reported_value_cannot_postdate_its_document(tmp_path):
    with pytest.raises(plans.CsvError, match="ASOF"):
        plans.load(write(tmp_path, [row(**(BACKLOG | dict(filed="2030-09-01", accepted="")))]))


def test_orcl_and_crwv_current_year_capex_is_allowed(tmp_path):
    r = row(id="crwv-c1", company="crwv", kind="range", value_lo="20000", value_hi="23000", unit="MUSD",
            direction_code="", direction_base="", period_start="2030-01-01", period_end="2030-12-31",
            definition="CRWV_CAPEX", filed="2030-05-14", accepted="")
    assert len(plans.load(write(tmp_path, [r]))) == 1


# ------------------------------------------------------------------ series


def test_series_keys_periods_and_vintages(tmp_path):
    rows = [
        row(),
        row(id="meta-p02", filed="2030-12-01", accepted=""),  # same value later: no new vintage
        row(id="crwv-c1", company="crwv", kind="range", value_lo="20000", value_hi="23000", unit="MUSD",
            direction_code="", direction_base="", period_start="2030-01-01", period_end="2030-12-31",
            definition="CRWV_CAPEX", filed="2030-05-14", accepted=""),
        row(id="crwv-c2", company="crwv", kind="range", value_lo="12000", value_hi="14000", unit="MUSD",
            direction_code="", direction_base="", period_start="2030-01-01", period_end="2030-12-31",
            definition="CRWV_CAPEX", filed="2030-11-10", accepted=""),  # lowered: new vintage
        row(**(BACKLOG | {"id": "crwv-b1"})),
        row(id="msft-x1", company="msft", measure="CAPACITY", kind="approx", value_lo="2", value_hi="2",
            unit="multiple", direction_code="", direction_base="", horizon="SPAN", year_basis="FY",
            period_start="2030-10-29", period_end="2032-10-31", definition="MSFT_DC_FOOTPRINT", filed="2030-10-29",
            accepted=""),
    ]
    df = plans.load(write(tmp_path, rows))
    keys = set(plans.long_rows(df)["key"])
    assert keys == {"plan_meta_capex_incl_fl_y_dir_yoy", "plan_crwv_capex_y_lo", "plan_crwv_capex_y_hi",
                    "plan_crwv_backlog_asof_value", "plan_msft_dc_footprint_span2y_value"}
    meta = plans.series_frame(df, "plan_meta_capex_incl_fl_y_dir_yoy")
    assert list(meta["period"]) == ["2031"] and list(meta["value"]) == [2.0]
    hi = plans.series_frame(df, "plan_crwv_capex_y_hi")
    assert list(hi["value"]) == [23000.0, 14000.0]
    bl = plans.series_frame(df, "plan_crwv_backlog_asof_value")
    assert list(bl["period"]) == ["2030Q3"]

    specs = plans.specs(write(tmp_path, rows))
    assert not catalog.validate(specs)
    by = {s.key: s for s in specs}
    assert by["plan_crwv_backlog_asof_value"].freq == "Q" and by["plan_crwv_backlog_asof_value"].lag_days >= 0
    assert by["plan_msft_dc_footprint_span2y_value"].lag_days <= -(pd.Timestamp("2032-12-31")
                                                                    - pd.Timestamp("2030-10-29")).days
    assert all(s.publish for s in specs)  # R5 reviewed, X3 corrected


# ------------------------------------------------------------------ sampling check


@pytest.mark.parametrize("value, unit, text", [
    (85000, "MUSD", "to approximately $85 billion"),
    (1500000, "MUSD", "about $1.5 trillion"),
    (450, "MUSD", "$450 million"),
    (3300, "MW", "3.3 GW of contracted power"),
    (590, "MW", "approximately 590 MW of active power"),
    (2.0, "multiple", "roughly double our footprint"),
    (1.8, "multiple", "increase AI capacity by over 80%"),
    (34000, "MUSD", "in the range of $34-39 billion"),
    (1000, "MW", "we added another gigawatt of capacity"),
])
def test_number_patterns(value, unit, text):
    assert any(__import__("re").search(p, text, flags=2) for p in plans_check.number_patterns(value, unit))


def test_table_total_in_millions():
    r = pd.Series(row(**(BACKLOG | {"measure": "COMMIT", "definition": "ORCL_UNCOND_OBLIG", "value_lo": 13309.0,
                                     "value_hi": 13309.0})))
    assert plans_check.sentence_ok(r, "obligations were as follows (in millions): Fiscal 2027 $ 1,841 Total $ 13,309")
    assert not plans_check.sentence_ok(r, "obligations were as follows: Total $ 13,309")


def test_check_row_ok_moved_and_missing():
    text = "First sentence. Revenue backlog was $55.6 billion at quarter end. Last one."
    s = gc.sentences(text)[1]
    r = pd.Series(row(**(BACKLOG | {"locator": "release; sentence #1", "sentence_sha256": gc.sentence_hash(s),
                                     "value_lo": 55600.0, "value_hi": 55600.0})))
    assert plans_check.check_row(r, text) == "ok"
    assert plans_check.check_row(r, "Moved here. " + text) == "moved"
    assert plans_check.check_row(r.copy().pipe(lambda x: x.where(x.index != "value_lo", 55700.0))
                                 .pipe(lambda x: x.where(x.index != "value_hi", 55700.0)), text) \
        == "number_not_in_sentence"
    assert plans_check.check_row(r, "Nothing relevant.") == "sentence_not_found"


def test_curated_csv_is_valid():
    """The committed CSV loads and its catalog entries are valid (no network)."""
    if not plans.PATH.exists():
        pytest.skip("no curated CSV yet")
    df = plans.load()
    assert len(df) and df["id"].is_unique
    assert not catalog.validate(plans.specs())
