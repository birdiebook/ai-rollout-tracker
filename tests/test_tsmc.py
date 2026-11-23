"""TSMC monthly revenue from 6-K filings: parsing of every report layout, vintages and known_from (no network)."""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import catalog, http, observations
from ai_tracker.series import tsmc as tsmc_series
from ai_tracker.sources import tsmc_sec as t

P = lambda s: pd.Period(s, freq="M")  # noqa: E731

# Trimmed copies of real report texts (contact details removed), one per layout.
R2002 = ("TSMC Monthly Sales Report - October 2002 Hsin-Chu, Taiwan, November 7, 2002- TSMC today announced that "
         "net sales for October 2002 totaled NT$15,231 million, while revenues from January to October 2002 were "
         "NT$135,038 million. # # # Sales Report: (Unit: NT$ million) ------------------ Net Sales 2002/(1)/ 2001 "
         "Growth ------------------ October 15,231 10,338 47.3% ------------ January through October 135,038 "
         "103,096 31.0% 1) Sales volume (NT$: Thousand) ------ Time Items 2002 2001 Changes (%) ----- Oct Invoice "
         "amount 15,345,452 10,024,151 5,321,301 53.08%")
R2004 = ("TSMC Monthly Sales Report - January 2004 today announced that net sales for January 2004 totaled "
         "NT$19,156 million, an increase of 45.9 percent. Sales Report: (Unit: NT$ million) ------------- "
         "2004/(1)/ 2003 Growth Rate ------------- Net Sales for January 19,156 13,129 45.9% ---------")
R2005 = ("TSMC Monthly Sales Report – January 2005 today announced that net sales for January 2005 totaled "
         "NT$20,843 million. Sales Report: (Unit: NT$million, except for EPS) 2005 * 2004 Growth Rate (%) Net Sales "
         "for January 20,843 19,156 8.8 * Year 2005 figures have not been audited. 1) Sales volume (in NT$: "
         "thousand) Period Items 2005 2004 Jan. Invoice amount 17,548,625 16,715,242 Jan. Net sales 20,842,779 "
         "19,155,894")
R2010 = ("TSMC May 2010 Sales Report today announced its net sales for May 2010: on an unconsolidated basis, net "
         "sales were approximately NT$33.84 billion. On a consolidated basis, net sales for May 2010 were "
         "approximately NT$34.82 billion. TSMC Sales Report (Unconsolidated): (Unit: NT$ million) Net Sales 2010 * "
         "2009 Increase (Decrease) % May 33,839 24,474 38.3 January through May 155,697 83,778 85.8 TSMC Sales "
         "Report (Consolidated): (Unit: NT$ million) Net Sales 2010 * 2009 Increase (Decrease) % May 34,819 25,247 "
         "37.9 January through May 160,815 87,197 84.4 1) Sales volume (in NT$ thousand) Period Items 2010 2009 May "
         "Net sales 33,839,484 24,473,921 Jan.-May Net sales 155,697,223 83,778,364")
R2013 = ("TSMC January 2013 Sales Report today announced its net sales for January 2013: On a consolidated basis, "
         "net sales for January 2013 were approximately NT$47.44 billion. TSMC Sales Report (Consolidated): (Unit: "
         "NT$ million) Period January 2013 December 2012 M-o-M Increase (Decrease) % January 2012 Y-o-Y Increase "
         "(Decrease) % Net Sales 47,439 37,154 27.7 34,606 37.1 * January and December 2012 figures have been "
         "recalculated based on IFRS 1. Sales volume (in NT$ thousands) Period Items 2013 2012 Jan. Net sales "
         "47,438,687 34,606,486")
R2014 = ("TSMC April 2014 Revenue Report today announced its net revenues for April 2014: On a consolidated basis, "
         "revenues for April 2014 were approximately NT$61.89 billion. TSMC Revenue Report (Consolidated): (Unit: "
         "NT$ million) Period April 2014 March 2014 M-o-M Increase (Decrease) % April 2013 Y-o-Y Increase "
         "(Decrease) % January to April 2014 January to April 2013 Y-o-Y Increase (Decrease) % Net Revenues 61,887 "
         "49.956 23.9 50,071 23.6 210,103 182,826 14.9")
R2026 = ("TSMC October 2026 Revenue Report today announced its net revenue for October 2026: On a consolidated "
         "basis, revenue for October 2026 was approximately NT$586.89 billion, an increase of 14.7 percent. TSMC "
         "October Revenue Report (Consolidated): (Unit:NT$ million) Period October 2026 September 2026 M-o-M "
         "Increase (Decrease) % October 2025 Y-o-Y Increase (Decrease) % January to October 2026 January to "
         "October 2025 Y-o-Y Increase (Decrease) % Net Revenue 586,890 511,857 14.7 367,473 59.7 4,485,617 "
         "3,130,437 43.3 1. Revenue (in NT$ thousands) Period Items 2026 2025 Oct. Net Revenue 586,890,319 "
         "367,473,051 Jan.~Oct. Net Revenue 4,485,617,293 3,130,436,902")
OTHER = ("TSMC Reports First Quarter EPS of NT$1.10. TSMC today announced consolidated revenue of NT$87.5 billion "
         "for the first quarter ended March 31, 2008.")


def test_to_text_strips_markup():
    assert t.to_text("<p>Net&nbsp;Sales<br/>\n  <b>47,439</b></p><script>x()</script>") == "Net Sales 47,439"


@pytest.mark.parametrize("text,period,cons,uncons,comparatives", [
    (R2002, "2002-10", None, 15231.0, {"unconsolidated": {"2001-10": 10338.0}}),
    (R2004, "2004-01", None, 19156.0, {"unconsolidated": {"2003-01": 13129.0}}),
    (R2005, "2005-01", None, 20842.779, {"unconsolidated": {"2004-01": 19156.0}}),
    (R2010, "2010-05", 34819.0, 33839.484, {"unconsolidated": {"2009-05": 24474.0},
                                            "consolidated": {"2009-05": 25247.0}}),
    (R2013, "2013-01", 47438.687, None, {"consolidated": {"2012-12": 37154.0, "2012-01": 34606.0}}),
    (R2014, "2014-04", 61887.0, None, {"consolidated": {"2014-03": 49956.0, "2013-04": 50071.0}}),
    (R2026, "2026-10", 586890.319, None, {"consolidated": {"2026-09": 511857.0, "2025-10": 367473.0}}),
])
def test_parse_report_layouts(text, period, cons, uncons, comparatives):
    rep = t.parse_report(text)
    assert rep.period == P(period)
    assert rep.consolidated == pytest.approx(cons) if cons else rep.consolidated is None
    assert rep.unconsolidated == pytest.approx(uncons) if uncons else rep.unconsolidated is None
    got = {b: {str(p): v for p, v in c.items()} for b, c in rep.comparatives.items()}
    assert got == comparatives


def test_sentence_fallback_without_table():
    rep = t.parse_report("TSMC June 2006 Sales Report: On a consolidated basis, net sales for June 2006 were "
                         "NT$ 27,647 million, an increase of 1.9 percent.")
    assert rep.period == P("2006-06") and rep.consolidated == 27647.0


def test_non_report_filing_is_ignored():
    assert t.parse_report(OTHER) is None


def test_thousands_section_never_overrides_a_different_figure():
    # a thousands figure that disagrees with the table (e.g. a different basis) must not replace it
    text = R2013.replace("47,438,687", "41,000,000")
    assert t.parse_report(text).consolidated == 47439.0


# ------------------------------------------------------------------ vintages and known_from


def rep(period, value, comps=None):
    return t.Report(P(period), consolidated=value,
                    comparatives={"consolidated": {P(k): v for k, v in (comps or {}).items()}})


def test_vintages_known_from_is_filing_date_and_restatements_are_new_vintages():
    items = [
        ("2012-02-10", rep("2012-01", 34569.0)),
        ("2013-01-10", rep("2012-12", 37114.0, {"2011-12": 30000.0})),
        ("2013-02-08", rep("2013-01", 47438.687, {"2012-12": 37154.0, "2012-01": 34606.0})),  # IFRS restatement
        ("2013-03-08", rep("2013-02", 41182.0, {"2013-01": 47439.0})),  # rounding only: no new vintage
    ]
    df = t.vintages(items, "consolidated")
    rows = {(r.period, r.known_from.strftime("%Y-%m-%d")): r.value for r in df.itertuples()}
    assert rows == {
        ("2011-12", "2013-01-10"): 30000.0,  # first known through a comparative, a year later
        ("2012-01", "2012-02-10"): 34569.0, ("2012-01", "2013-02-08"): 34606.0,
        ("2012-12", "2013-01-10"): 37114.0, ("2012-12", "2013-02-08"): 37154.0,
        ("2013-01", "2013-02-08"): 47438.687, ("2013-02", "2013-03-08"): 41182.0,
    }


def test_vintages_feed_as_of_without_leakage():
    s = catalog.Spec("tsmc_x", "G6", "x", "mn TWD", "M", "test", lambda: None, 10, "unverified", revised=True)
    items = [("2013-01-10", rep("2012-12", 37114.0)),
             ("2013-02-08", rep("2013-01", 47438.687, {"2012-12": 37154.0}))]
    new = observations.new_rows(s, t.vintages(items, "consolidated"), observations._empty())
    assert set(new["source"]) == {"release"}
    assert observations.as_of("tsmc_x", "2013-02-07", new).to_dict() == {P("2012-12"): 37114.0}
    assert observations.as_of("tsmc_x", "2013-02-08", new).to_dict() == {P("2012-12"): 37154.0,
                                                                         P("2013-01"): 47438.687}


def test_specs_are_valid_and_fetch_uses_reports(monkeypatch):
    assert catalog.validate(tsmc_series.SPECS) == []
    tsmc_series._reports.cache_clear()
    monkeypatch.setattr(t, "reports", lambda: [(t.Filing("a", "2010-06-10", "6-K", "d.htm"), t.parse_report(R2010))])
    by = catalog.by_key(tsmc_series.SPECS)
    cons, parent = by["tsmc_revenue_m"].fetch(), by["tsmc_revenue_parent_m"].fetch()
    tsmc_series._reports.cache_clear()
    assert list(cons.columns) == ["period", "value", "known_from"]
    assert cons.set_index("period")["value"].to_dict() == {"2009-05": 25247.0, "2010-05": 34819.0}
    assert (cons["known_from"] == pd.Timestamp("2010-06-10")).all()
    assert parent.set_index("period")["value"].to_dict() == {"2009-05": 24474.0, "2010-05": pytest.approx(33839.484)}


# ------------------------------------------------------------------ EDGAR access (mocked)


class Resp:
    def __init__(self, payload=None, content=b""):
        self._payload, self.content = payload, content

    def json(self):
        return self._payload


def test_filings_reads_all_submission_files_and_skips_paper(monkeypatch):
    recent = {"form": ["6-K", "4", "6-K/A"], "filingDate": ["2026-11-10", "2026-11-10", "2026-11-12"],
              "accessionNumber": ["0001-26-2", "0001-26-3", "0001-26-4"], "primaryDocument": ["r.htm", "f.xml", "a.htm"]}
    old = {"form": ["6-K", "6-K"], "filingDate": ["2002-01-25", "2002-11-07"],
           "accessionNumber": ["9999-02-1", "0001-02-1"], "primaryDocument": ["x.paper", "d6k.txt"]}
    pages = {t.SUBMISSIONS.format(cik=t.CIK): {"filings": {"recent": recent, "files": [{"name": "old.json"}]}},
             t.SUBMISSIONS_FILE.format(name="old.json"): old}
    monkeypatch.setattr(http, "get", lambda url, source, **kw: Resp(pages[url]))
    fs = t.filings()
    assert [(f.filed, f.form, f.document) for f in fs] == [
        ("2002-11-07", "6-K", "d6k.txt"), ("2026-11-10", "6-K", "r.htm"), ("2026-11-12", "6-K/A", "a.htm")]
    assert fs[1].url == "https://www.sec.gov/Archives/edgar/data/1046179/0001262/r.htm"


def test_document_text_reuses_raw_copy_from_earlier_day(monkeypatch, tmp_path):
    monkeypatch.setattr(http, "RAW_DIR", tmp_path)
    f = t.Filing("0001-26-2", "2026-11-10", "6-K", "r.htm")
    old = http.raw_path(t.SOURCE, f.url, day=pd.Timestamp("2026-01-01").date())
    old.parent.mkdir(parents=True)
    old.write_bytes(b"<p>cached</p>")

    def no_network(*a, **kw):
        raise AssertionError("should use the cached copy")

    monkeypatch.setattr(http, "get", no_network)
    assert t.document_text(f) == "cached"


def test_twse_current_parses_roc_month(monkeypatch):
    row = {"公司代號": "2330", "資料年月": "11510", "營業收入-當月營收": "586890319",
           "營業收入-上月營收": "511857399", "營業收入-去年當月營收": "367473051"}
    monkeypatch.setattr(http, "get", lambda url, source, **kw: Resp([{"公司代號": "1101"}, row]))
    assert t.twse_current() == {P("2026-10"): 586890.319, P("2026-09"): 511857.399, P("2025-10"): 367473.051}
