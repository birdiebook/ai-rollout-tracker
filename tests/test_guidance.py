"""Guidance (phase 4, E1): TSMC 6-K guidance parser, the curated capex CSV loader and the sampling check (no network).

Fixture texts are synthetic: they follow the layouts of TSMC's releases and presentations (and of capex outlook
sentences) with made-up numbers, so no source text is copied into the repo.
"""

from __future__ import annotations

import csv

import pandas as pd
import pytest

from ai_tracker import guidance_check
from ai_tracker.sources import guidance_capex as gc
from ai_tracker.sources import tsmc_guidance as tg

Q = lambda s: pd.Period(s, freq="Q-DEC")  # noqa: E731

# ------------------------------------------------------------------ TSMC fixtures (synthetic, real layouts)

USD_RELEASE = (
    "TSMC Reports Third Quarter EPS of NT$9.99 ... revenue for the third quarter ended September 30, 2025 ... "
    "Gross margin for the quarter was 59.5%. Based on the Company's current business outlook, management expects "
    "the overall performance for fourth quarter 2025 to be as follows: • Revenue is expected to be between "
    "US$30.1 billion and US$31.3 billion; And, based on the exchange rate assumption of 1 US dollar to 30.25 NT "
    "dollars, • Gross profit margin is expected to be between 57% and 59%; • Operating profit margin is expected "
    "to be between 46.5% and 48.5%. The management further expects the 2025 capital budget to be between US$40 "
    "billion and US$42 billion. TSMC's 2025 third quarter consolidated results: (Unit: NT$ million)")
PRESENTATION_TABLE = (  # the closed quarter's guidance appears in the results table before the new outlook
    "Selected Items 3Q25 Guidance Net Revenue (US$ billions) 31.00 29.8-31.0 Gross Margin 59.5% 55.5%-57.5% "
    "© 2025 TSMC 4Q25 Guidance Based on our current business outlook, management expects: ▪ Revenue to be between "
    "US$30.1 billion and US$31.3 billion And, based on the exchange rate assumption of 1 US dollar to 30.25 NT "
    "dollars, management expects: ▪ Gross profit margin to be between 57% and 59% ▪ Operating profit margin to be "
    "between 46.5% and 48.5%")
TWD_RELEASE_2011 = (  # press release without the FX number (it came in the presentation the next day)
    "For the first quarter of 2011, we expect the demand to be stronger than seasonal. Based on our current "
    "business outlook and exchange rate assumption, management expects overall performance for first quarter 2011 "
    "to be as follows: • Revenue is expected to be between NT$101 billion and NT$103 billion; • Gross profit "
    "margin is expected to be between 45% and 47%; • Operating profit margin is expected to be between 33% and 35%.")
TWD_PRESENTATION_2011 = (
    "Capital Expenditures (In US millions) 1Q11 Guidance Based on our current business outlook and exchange rate "
    "assumption, management expects: Revenue to be between NT$101 billion and NT$103 billion, at a forecast "
    "exchange rate of 29.10 NT dollars to 1 US dollar Gross profit margin to be between 45% and 47% Operating "
    "profit margin to be between 33% and 35%")
BOTH_BASES_2006 = (  # 2006Q2: parent-only first, then consolidated
    "2Q'06 Guidance Revenues to be between NT$78 billion and NT$80 billion; consolidated revenue to be between "
    "NT$79 billion and NT$81 billion Gross profit margin to be between 46% and 48%; consolidated gross profit margin "
    "to be between 47% and 49% Operating profit margin to be between 39% and 41% on both bases")
MID_QUARTER_2009 = (
    "TSMC now expects first-quarter revenue to be between NT$35 billion and NT$37 billion, higher than the previous "
    "expectation of between NT$31 billion and NT$34 billion. TSMC's expectation for first-quarter gross profit "
    "margin is now between 13% and 15%, and operating profit margin is between -3% and -1%, compared with the "
    "previous guidance.")
NEXT_QUARTER_2015 = (
    "The company now expects its third-quarter revenue to be between NT$210 billion and NT$212 billion, and both "
    "margins to be within the range of its July guidance. The company further expects its fourth-quarter revenue "
    "will experience a sequential decline and is likely to be between NT$197 billion and NT$203 billion.")
EARTHQUAKE_2016 = (
    "The Company now expects first quarter revenue to be between NT$200 billion to NT$202 billion. Versus the prior "
    "guidance, a more favorable exchange rate assumption (USD:NTD of 1:33.10 versus 1:32.40 on January 14) offsets "
    "the impact. Gross profit margin is expected to be between 43% and 45%.")
FX_BEFORE_ANCHOR_2012 = (
    "Based on our current business outlook and exchange rate assumption of 1 US dollar to 29.60 NT dollars, "
    "management expects overall performance for second quarter 2012 to be as follows: • Revenue is expected to be "
    "between NT$125 billion and NT$127 billion;")
PAST_QUARTER_FIRST = (  # the reported quarter is named before the anchor and must not be taken as the guided one
    "Revenue for the first quarter 2019 reached the low end of guidance. Based on our current business outlook, "
    "management expects the overall performance for second quarter 2019 to be as follows: • Revenue is expected to "
    "be between US$7.5 billion and US$7.6 billion;")
OCR_PRESENTATION = (
    "1Q14 Guidance TSMC Based on our current business outlook and exchange rate assumption, management expects: "
    "Revenue to be between NT$ 135 billion and NT$ 137 billion, at a forecast exchange rateof30NT dollars to1USdollar "
    "Grossprofit margin tobe between 44.5% and46.5% Operating profit margin tobe between 32%and34%")
MONTHLY = "TSMC October 2026 Revenue Report ... revenue for October 2026 was approximately NT$586.89 billion."


def test_parse_usd_release_with_fx_and_margins():
    g = tg.parse_guidance(USD_RELEASE)
    assert g.quarter == Q("2025Q4") and g.currency == "USD"
    assert g.values == {"rev_lo": 30100.0, "rev_hi": 31300.0, "fx": 30.25, "gm_lo": 57.0, "gm_hi": 59.0,
                        "om_lo": 46.5, "om_hi": 48.5}


def test_presentation_ignores_closed_quarter_table():
    g = tg.parse_guidance(PRESENTATION_TABLE)
    assert g.quarter == Q("2025Q4")
    assert (g.values["rev_lo"], g.values["gm_lo"], g.values["fx"]) == (30100.0, 57.0, 30.25)


def test_parse_twd_release_without_fx_and_presentation_with_fx():
    r = tg.parse_guidance(TWD_RELEASE_2011)
    assert r.quarter == Q("2011Q1") and r.currency == "TWD" and "fx" not in r.values
    assert (r.values["rev_lo"], r.values["rev_hi"]) == (101000.0, 103000.0)
    p = tg.parse_guidance(TWD_PRESENTATION_2011)
    assert p.quarter == Q("2011Q1") and p.values["fx"] == 29.10


def test_consolidated_range_preferred():
    g = tg.parse_guidance(BOTH_BASES_2006)
    assert (g.values["rev_lo"], g.values["rev_hi"]) == (79000.0, 81000.0)
    assert (g.values["gm_lo"], g.values["gm_hi"]) == (47.0, 49.0)


def test_mid_quarter_update_with_negative_margin():
    g = tg.parse_guidance(MID_QUARTER_2009)
    assert (g.values["rev_lo"], g.values["rev_hi"]) == (35000.0, 37000.0)
    assert (g.values["om_lo"], g.values["om_hi"]) == (-3.0, -1.0) and g.values["gm_lo"] == 13.0


def test_next_quarter_range_in_same_statement():
    g = tg.parse_guidance(NEXT_QUARTER_2015)
    assert g.values["rev_lo"] == 210000.0
    assert g.next_quarter == (4, {"rev_lo": 197000.0, "rev_hi": 203000.0})


def test_to_range_and_usd_ntd_fx():
    g = tg.parse_guidance(EARTHQUAKE_2016)
    assert (g.values["rev_lo"], g.values["rev_hi"], g.values["fx"]) == (200000.0, 202000.0, 33.10)


def test_fx_stated_just_before_anchor():
    assert tg.parse_guidance(FX_BEFORE_ANCHOR_2012).values["fx"] == 29.60


def test_past_quarter_before_anchor_is_not_the_guided_quarter():
    assert tg.parse_guidance(PAST_QUARTER_FIRST).quarter == Q("2019Q2")


def test_squashed_pdf_text():
    g = tg.parse_guidance(OCR_PRESENTATION)
    assert g.values == {"rev_lo": 135000.0, "rev_hi": 137000.0, "fx": 30.0, "gm_lo": 44.5, "gm_hi": 46.5,
                        "om_lo": 32.0, "om_hi": 34.0}


def test_non_guidance_documents():
    assert tg.parse_guidance(MONTHLY) is None
    assert tg.parse_guidance("Revenue for the quarter was NT$100 billion, in line with guidance.") is None


def _f(acc: str, filed: str, accepted: str | None = None) -> tg.Filing:
    return tg.Filing(acc, filed, accepted or f"{filed}T07:00:00.000Z", "6-K", "d6k.htm")


def test_guided_quarter_must_match_filing_date():
    with pytest.raises(tg.ParseError):
        tg.records([(_f("a", "2025-07-17"), [("x.htm", USD_RELEASE)])])  # text guides 2025Q4, filed in Q3


def test_records_and_vintages_known_from_is_filing_date():
    items = [
        (_f("a1", "2011-01-27"), [("pr.htm", TWD_RELEASE_2011)]),
        (_f("a2", "2011-01-28"), [("pres.htm", TWD_PRESENTATION_2011)]),
        (_f("a3", "2011-03-09"), [("upd.htm", MID_QUARTER_2009.replace("NT$35 billion", "NT$104 billion")
                                    .replace("NT$37 billion", "NT$106 billion"))]),
        (_f("a0", "2006-01-26"), [("old.htm", TWD_RELEASE_2011.replace("first quarter 2011", "first quarter 2006"))]),
    ]
    recs = tg.records(items)
    assert set(recs["period"]) == {"2011Q1"}  # 2006Q1 (parent-only basis) is dropped
    lo = tg.vintages(recs, "rev_lo", "TWD")
    assert list(zip(lo["value"], lo["known_from"].dt.strftime("%Y-%m-%d"))) == [
        (101000.0, "2011-01-27"), (104000.0, "2011-03-09")]  # the presentation repeat adds no row
    fx = tg.vintages(recs, "fx")
    assert list(fx["known_from"].dt.strftime("%Y-%m-%d")) == ["2011-01-28"]  # first document with the FX value
    # every value is dated by a filing that contains it, never earlier
    for field in ("rev_lo", "rev_hi", "fx", "gm_lo", "om_hi"):
        for p, v, kf in tg.vintages(recs, field).itertuples(index=False):
            src = recs[(recs["period"] == p) & (recs[field] == v)]
            assert pd.Timestamp(src["filed"].min()) == kf


def test_next_quarter_rows_and_currency_filter():
    items = [(_f("b1", "2015-09-23"), [("u.htm", NEXT_QUARTER_2015)]),
             (_f("b2", "2015-10-15"), [("r.htm", USD_RELEASE.replace("US$", "NT$").replace("fourth quarter 2025",
                                                                                        "fourth quarter 2015"))])]
    recs = tg.records(items)
    assert sorted(recs["period"]) == ["2015Q3", "2015Q4", "2015Q4"]
    q4 = tg.vintages(recs, "rev_lo", "TWD").query("period == '2015Q4'")
    assert list(q4["value"]) == [197000.0, 30100.0] and q4["known_from"].min() == pd.Timestamp("2015-09-23")
    assert tg.vintages(recs, "rev_lo", "USD").empty


# ------------------------------------------------------------------ capex CSV loader

SENT = "We expect full-year 2031 capital expenditures to be in the range of $40-45 billion."


def _row(**kw) -> dict:
    base = dict(id="x-01", company="meta", horizon="CY", period="2031", period_start="2031-01-01",
                period_end="2031-12-31", kind="range", value_lo="40000", value_hi="45000", unit="MUSD",
                direction_code="", direction_base="", definition="META_CAPEX_INCL_FL", filed="2030-10-29",
                accepted="2030-10-29T20:07:58.000Z", doc_type="8-K EX-99.1",
                source_url="https://www.sec.gov/Archives/edgar/data/1/2/x.htm", accession="0000000001-30-000001",
                locator="CFO outlook commentary; sentence #3", sentence_sha256=gc.sentence_hash(SENT), note="")
    base.update(kw)
    return base


def _write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=gc.COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return path


def test_loader_known_from_is_filing_date(tmp_path):
    rows = [_row(), _row(id="x-02", filed="2031-01-28", accepted="2031-01-28T21:00:00.000Z", value_lo="42000"),
            _row(id="x-03", kind="direction", period="2032", period_start="2032-01-01", period_end="2032-12-31",
                 value_lo="", value_hi="", unit="code", direction_code="2", direction_base="yoy")]
    df = gc.load(_write(tmp_path / "g.csv", rows))
    assert (df["known_from"] == pd.to_datetime(df["filed"])).all()
    lo = gc.series_frame(df, "meta", "CY", "lo")
    assert list(zip(lo["period"], lo["value"])) == [("2031", 40000.0), ("2031", 42000.0)]
    hi = gc.series_frame(df, "meta", "CY", "hi")
    assert list(hi["value"]) == [45000.0]  # unchanged high end: no new vintage
    d = gc.series_frame(df, "meta", "CY", "dir", "yoy")
    assert list(zip(d["period"], d["value"], d["known_from"])) == [("2032", 2.0, pd.Timestamp("2030-10-29"))]
    assert gc.series_frame(df, "meta", "CY", "dir", "qoq").empty


@pytest.mark.parametrize("bad", [
    dict(filed="2032-01-15", accepted=""),  # document after the guided period ended: an outcome, not guidance
    dict(accepted="2030-11-15T10:00:00.000Z"),  # acceptance far from the filing date
    dict(sentence_sha256="abc"),
    dict(definition="MADE_UP"),
    dict(value_lo="46000"),  # lo > hi
    dict(kind="point", value_hi="46000"),
    dict(kind="direction", direction_code="3", direction_base="yoy"),
    dict(source_url="http://example.com"),
    dict(locator=" "),
])
def test_loader_rejects(tmp_path, bad):
    with pytest.raises(gc.CsvError):
        gc.load(_write(tmp_path / "g.csv", [_row(**bad)]))


def test_curated_csv_is_valid_and_never_dated_before_its_document():
    df = gc.load()
    assert len(df) > 0 and df["id"].is_unique
    assert (df["known_from"] >= pd.to_datetime(df["filed"])).all()
    assert (df["known_from"] <= pd.to_datetime(df["period_end"])).all()
    for spec in gc.specs():
        s = spec.fetch()
        assert not s.empty and (s["known_from"] >= df["known_from"].min()).all()
        # each vintage is dated by a CSV row with that period and filing date
        assert set(zip(s["known_from"])) <= set(zip(df["known_from"]))


def test_sentence_hash_normalises_whitespace():
    assert gc.sentence_hash(" a  b\n c ") == gc.sentence_hash("a b c")
    assert gc.sentences("One sentence. Two $5 billion. three. Four!") == ["One sentence.", "Two $5 billion. three.",
                                                                          "Four!"]


# ------------------------------------------------------------------ sampling check helpers (offline)

def test_number_pattern():
    import re
    assert re.search(guidance_check.number_pattern(29000), "range of $29-34 billion")
    assert re.search(guidance_check.number_pattern(34000), "range of $29-34 billion")
    assert not re.search(guidance_check.number_pattern(3000), "range of $29-34 billion")
    assert re.search(guidance_check.number_pattern(8400), "US$ 8.40 billion")
    assert not re.search(guidance_check.number_pattern(8400), "US$ 8.45 billion")


def test_check_capex_row_locates_by_index_and_hash():
    text = "Intro sentence. Another one. " + SENT + " Closing words."
    row = pd.Series(_row(value_lo=40000.0, value_hi=45000.0, locator="x; sentence #2"))
    assert guidance_check.check_capex_row(row, text) == "ok"
    assert guidance_check.check_capex_row(row, "Extra first. " + text) == "moved"
    assert guidance_check.check_capex_row(row, text.replace("$40-45", "$40-46")) == "sentence_not_found"
    wrong = pd.Series(_row(value_lo=41000.0, value_hi=45000.0, locator="x; sentence #2"))
    assert guidance_check.check_capex_row(wrong, text) == "number_not_in_sentence"
