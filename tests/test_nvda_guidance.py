"""Nvidia outlook parser (ai_tracker.sources.nvda_guidance): synthetic fixtures, no network."""

import pandas as pd
import pytest

from ai_tracker.sources import nvda_guidance as ng


def _filing(filed, acc="0001045810-26-000001", items="2.02,9.01", accepted=None):
    return ng.Filing(acc, filed, accepted or f"{filed}T20:20:00.000Z", "8-K", items)


BAND = ("Outlook NVIDIA’s outlook for the third quarter of fiscal 2026 is as follows: • Revenue is expected to be "
        "$54.0 billion, plus or minus 2%. NVIDIA is not assuming any H20 shipments to China in its outlook. • GAAP "
        "and non-GAAP gross margins are expected to be 73.3% and 73.5%, respectively.")
RANGE = ("Outlook Our outlook for the second quarter of fiscal 2013 is as follows: • Revenue is expected to be "
         "between $990 million and $1.05 billion. • GAAP gross margin is expected to be 51.2 percent.")
COMMA = ("Outlook Our outlook for the first quarter of fiscal 2015 is as follows: • Revenue is expected to be "
         "$1,050 million, plus or minus two percent.")
QOQ = {
    "up": ("Outlook The outlook for the third quarter of fiscal 2011 is as follows: · Revenue is expected to be up 3 "
           "to 5 percent from the second quarter.", (3.0, 5.0)),
    "down": ("Outlook The outlook for the second quarter of fiscal 2011 is as follows: · Revenue is expected to be "
             "down seasonally 3 to 5 percent from the first quarter.", (-5.0, -3.0)),
    "flat": ("Outlook The outlook for the first quarter of fiscal 2011 is as follows: · Revenue is expected to be "
             "flat from the fourth quarter.", (0.0, 0.0)),
    "flatband": ("Outlook Our outlook for the fourth quarter of fiscal 2012 is as follows: • Revenue is expected to "
                 "be relatively flat, plus or minus two percent, from the third quarter.", (-2.0, 2.0)),
    "approx": ("Outlook The outlook for the fourth quarter of fiscal 2010 is as follows: · Revenue is expected to be "
               "up slightly, approximately 2 percent, from the third quarter.", (2.0, 2.0)),
    "expects": ("Outlook NVIDIA expects revenue in the third quarter ending October 25, 2009, to be up 5 to 7 "
                "percent over the second quarter.", (5.0, 7.0)),
}


def test_band_statement():
    o = ng.parse_outlook(BAND)
    assert (o.fiscal_quarter, o.fiscal_year, o.kind) == (3, 2026, "usd")
    assert o.values == pytest.approx({"rev_mid": 54000, "band_pct": 2, "rev_lo": 52920, "rev_hi": 55080})
    assert str(o.period) == "2025Q3"  # Q3 FY2026 = Jul-Oct 2025


def test_range_and_comma():
    o = ng.parse_outlook(RANGE)
    assert o.values == pytest.approx({"rev_lo": 990, "rev_hi": 1050, "rev_mid": 1020})
    assert str(o.period) == "2012Q2"
    assert ng.parse_outlook(COMMA).values["rev_mid"] == pytest.approx(1050)


def test_three_percent_band_and_extra_week():
    t = ("Outlook NVIDIA’s outlook for the fourth quarter of fiscal 2027, which includes an additional week, is as "
         "follows: • Revenue is expected to be $130.0 billion, plus or minus 3%.")
    o = ng.parse_outlook(t)
    assert o.values["band_pct"] == 3 and o.values["rev_lo"] == pytest.approx(126100)
    assert str(o.period) == "2026Q4"


@pytest.mark.parametrize("name", sorted(QOQ))
def test_change_statements(name):
    text, (lo, hi) = QOQ[name]
    o = ng.parse_outlook(text)
    assert o.kind == "qoq" and (o.values["qoq_lo"], o.values["qoq_hi"]) == (lo, hi)


def test_expects_form_fiscal_year_from_date():
    o = ng.parse_outlook(QOQ["expects"][0])
    assert (o.fiscal_quarter, o.fiscal_year) == (3, 2010) and str(o.period) == "2009Q3"


def test_boilerplate_mention_is_not_an_outlook():
    t = ("statements as to NVIDIA’s outlook for the third quarter of fiscal 2026 are forward-looking statements "
         "that are subject to risks and uncertainties.")
    assert ng.parse_outlook(t) is None


def test_fiscal_quarter_dates():
    assert ng.fiscal_quarter_dates(2026, 3) == (pd.Timestamp("2025-07-28"), pd.Timestamp("2025-10-26"))
    assert ng.fiscal_quarter_dates(2027, 4) == (pd.Timestamp("2026-10-26"), pd.Timestamp("2027-01-31"))  # 14 weeks
    assert ng.fiscal_quarter_dates(2013, 1) == (pd.Timestamp("2012-01-30"), pd.Timestamp("2012-04-29"))


def test_filing_must_lie_in_guided_fiscal_quarter():
    recs = ng.records([(_filing("2025-08-27"), [("EX-99.1", "pr.htm", BAND)])])
    assert recs["period"].tolist() == ["2025Q3"]
    # a mid-quarter update after the calendar quarter has ended but inside the fiscal quarter is accepted
    assert ng.records([(_filing("2025-10-10"), [("EX-99.1", "pr.htm", BAND)])])["period"].tolist() == ["2025Q3"]
    with pytest.raises(ng.ParseError):  # filed before the guided fiscal quarter began
        ng.records([(_filing("2025-05-28"), [("EX-99.1", "pr.htm", BAND)])])


def test_statement_after_fiscal_quarter_end_is_skipped():
    assert ng.records([(_filing("2025-11-03"), [("EX-99.1", "pr.htm", BAND)])]).empty


def test_vintages_first_filing_and_updates():
    f1, f2 = _filing("2025-08-27", "a-1"), _filing("2025-09-15", "a-2", items="7.01,9.01")
    upd = BAND.replace("$54.0 billion", "$56.0 billion")
    recs = ng.records([(f1, [("EX-99.1", "pr.htm", BAND), ("EX-99.2", "cfo.htm", BAND)]),
                       (f2, [("EX-99.1", "upd.htm", upd)])])
    v = ng.vintages(recs, "rev_mid")
    assert v["value"].tolist() == [54000, 56000]
    assert v["known_from"].tolist() == [pd.Timestamp("2025-08-27"), pd.Timestamp("2025-09-15")]


def test_split_documents():
    raw = ("<SEC-DOCUMENT><DOCUMENT>\n<TYPE>8-K\n<SEQUENCE>1\n<FILENAME>a.htm\n<TEXT><html>cover</html></TEXT>"
           "</DOCUMENT><DOCUMENT>\n<TYPE>EX-99.1\n<SEQUENCE>2\n<FILENAME>pr.htm\n<TEXT><p>Revenue is "
           "expected</p></TEXT></DOCUMENT>")
    docs = ng.split_documents(raw)
    assert [(t, n) for t, n, _ in docs] == [("8-K", "a.htm"), ("EX-99.1", "pr.htm")]
    assert "Revenue is expected" in docs[1][2]
