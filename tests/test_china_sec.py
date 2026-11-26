"""China via SEC (CN1): Alibaba and Baidu 6-K parsing, definition eras, Baidu text coding, its check, H.10 and US$.

Synthetic fixtures (plain text as tsmc_sec.to_text gives it), no network. Values in RMB millions unless stated.
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import catalog, licenses
from ai_tracker.series import china_sec as series_mod
from ai_tracker.sources import china_parse as cp
from ai_tracker.sources import china_sec as cs
from ai_tracker.sources import china_text as ct
from ai_tracker.sources import fed_h10, guidance_capex
from ai_tracker import china_text_check as chk

Q = lambda s: pd.Period(s, freq="Q-DEC")  # noqa: E731

# ------------------------------------------------------------------ Alibaba fixtures

BABA_HEAD = ("EX-99.1 2 tm1_ex99-1.htm EXHIBIT 99.1 Exhibit 99.1 Alibaba Group Announces {title} Results "
             "H ong Kong, China, {date} - Alibaba Group Holding Limited today announced its financial results. ")
BABA_SEG = ("The following table sets forth a breakdown of our revenue by segment for the periods indicated: "
            "Three months ended {md}, {y0} {y1} RMB RMB US$ YoY % Change (in millions, except percentages) "
            "Taobao and Tmall Group: China commerce retail 72,425 79,661 10,986 10 % "
            "{label} {v0} {v1} 3,465 4 % Digital Media and Entertainment Group 4,000 5,000 700 25 % ")
BABA_FCF = ("The following table sets forth a reconciliation of net cash provided by operating activities to free cash "
            "flow for the periods indicated: Three months ended {md}, {ytd}{y0} {y1} RMB RMB US$ {extra}"
            "(in millions of RMB) Net cash provided by operating activities 30,000 40,000 5,500 {ocf_ytd}"
            "Less: Purchase of property and equipment (excluding land use rights and construction in progress relating "
            "to office campuses) {c} Less: Acquisition of intangible assets (100 ) (200 ) (30 ) Free cash flow 1 2 3 ")


def baba_release(title="June Quarter 2023", date="August 10, 2023", md="June 30", y0=2022, y1=2023,
                 label="Cloud Intelligence Group", v0="24,127", v1="25,123", capex="(6,000 ) (7,500 ) (1,034 )",
                 ytd="", extra="", ocf_ytd=""):
    return (BABA_HEAD.format(title=title, date=date)
            + BABA_SEG.format(md=md, y0=y0, y1=y1, label=label, v0=v0, v1=v1)
            + BABA_FCF.format(md=md, y0=y0, y1=y1, c=capex, ytd=ytd, extra=extra, ocf_ytd=ocf_ytd))


def test_baba_release_parses_cloud_row_and_capex():
    rel = cp.parse_baba(baba_release())
    assert rel.quarter == Q("2023Q2") and rel.dateline == pd.Timestamp("2023-08-10")
    assert rel.figures["rev_cloud"] == {Q("2023Q2"): (25123.0, "cloud intelligence group"),
                                        Q("2022Q2"): (24127.0, "cloud intelligence group")}
    assert rel.figures["capex"][Q("2023Q2")][0] == 7500.0  # an outflow in the table, stored positive
    assert rel.figures["capex"][Q("2022Q2")][0] == 6000.0
    assert "office campuses" in rel.figures["capex"][Q("2023Q2")][1]


def test_baba_footnote_marker_and_percentages_are_dropped():
    text = baba_release(label="Cloud computing (3)", v0="12,437 8 %", v1="16,051")
    rel = cp.parse_baba(text)
    assert rel.figures["rev_cloud"][Q("2023Q2")][0] == 16051.0
    assert rel.figures["rev_cloud"][Q("2022Q2")][0] == 12437.0


def test_baba_ytd_header_gives_six_amounts():
    text = baba_release(title="September Quarter 2023", md="September 30", ytd="Six months ended September 30, ",
                        extra="RMB RMB US$ ", ocf_ytd="60,000 70,000 9,600 ",
                        capex="(6,000 ) (7,500 ) (1,034 ) (9,000 ) (12,000 ) (1,650 )")
    rel = cp.parse_baba(text)
    assert rel.quarter == Q("2023Q3")
    assert rel.figures["capex"] == {Q("2023Q3"): (7500.0, rel.figures["capex"][Q("2023Q3")][1]),
                                    Q("2022Q3"): (6000.0, rel.figures["capex"][Q("2022Q3")][1])}


def test_baba_row_with_wrong_number_of_amounts_is_not_used():
    rel = cp.parse_baba(baba_release(v0="24,127", v1="25,123 999"))  # four amounts after the label
    assert "rev_cloud" not in rel.figures and "capex" in rel.figures
    assert cp.parse_baba(baba_release(v1="25,123 999", capex="(6,000 ) (7,500 )")) is None  # nothing readable


def test_baba_title_variants():
    assert cp.baba_quarter(BABA_HEAD.format(title="March Quarter and Full Fiscal Year 2019", date="x")) == Q("2019Q1")
    assert cp.baba_quarter(BABA_HEAD.format(title="March Quarter 2024 and Fiscal Year 2024", date="x")) == Q("2024Q1")
    assert cp.baba_quarter("ANNOUNCEMENT OF THE SEPTEMBER QUARTER 2025 RESULTS Hong Kong") == Q("2025Q3")
    assert cp.baba_quarter("Alibaba Group Announces Share Repurchase Results") is None


def test_baba_segment_quarter_must_be_the_release_quarter():
    text = baba_release(title="September Quarter 2023")  # the table is for June: not the reported quarter
    assert cp.parse_baba(text) is None


def test_dateline_and_signoff():
    assert cp.dateline("BEIJING, China, Nov. 18, 2025 /PRNewswire/ Baidu") == pd.Timestamp("2025-11-18")
    assert cp.dateline("text Hong Kong, May 15, 2025 As at the date of this results announcement") == \
        pd.Timestamp("2025-05-15")
    assert cp.dateline("no city here") is None


# ------------------------------------------------------------------ Baidu fixtures

BIDU_HEAD = ("EX-99.1 2 d1dex991.htm EX-99.1 Exhibit 99.1 Baidu Announces {title} Results BEIJING, China, {date} – "
             "Baidu, Inc. today announced unaudited financial results. ")
ENT = "Baidu excl. iQIYI iQIYI Baidu, Inc. "
HDR_PLAIN = ("Baidu, Inc. Condensed Consolidated Statements of Cash Flows (In millions, unaudited) "
             "Three months ended September 30, 2024 (RMB) Three months ended June 30, 2025 (RMB) "
             "Three months ended September 30, 2025 (RMB) Three months ended September 30, 2025 (US$) " + ENT * 4)
HDR_SPLIT = ("Baidu, Inc. Condensed Consolidated Statements of Cash Flows (In millions, unaudited) "
             "Three months ended Three months ended Three months ended Three months ended September 30, June 30, "
             "September 30, September 30, 2024 2025 2025 2025 (RMB) (RMB) (RMB) (US$) Baidu Baidu Baidu Baidu excl. "
             "Baidu, excl. Baidu, excl. Baidu, excl. Baidu, iQIYI iQIYI Inc. iQIYI iQIYI Inc. iQIYI iQIYI Inc. "
             "iQIYI iQIYI Inc. ")
CF_ROWS = ("Net cash provided by operating activities 1 2 3 4 5 6 7 8 9 10 11 12 "
           "Less: Capital expenditures {capex} Free cash flow 1 2 3 4 5 6 7 8 9 10 11 12 ")
CAPEX_OK = ("(1,637 ) (8 ) (1,645 ) (3,779 ) (21 ) (3,800 ) (3,378 ) (23 ) (3,401 ) (475 ) (3 ) (478 )")


def bidu_release(header=HDR_PLAIN, capex=CAPEX_OK, title="Third Quarter 2025", date="Nov. 18, 2025"):
    return BIDU_HEAD.format(title=title, date=date) + "Financial results ... " + header + CF_ROWS.format(capex=capex)


@pytest.mark.parametrize("header", [HDR_PLAIN, HDR_SPLIT])
def test_bidu_capex_table_both_header_layouts(header):
    rel = cp.parse_bidu(bidu_release(header))
    assert rel.quarter == Q("2025Q3")
    assert rel.figures["capex_total"] == {Q("2024Q3"): (1645.0, "less: capital expenditures"),
                                          Q("2025Q2"): (3800.0, "less: capital expenditures"),
                                          Q("2025Q3"): (3401.0, "less: capital expenditures")}
    assert {q: v for q, (v, _) in rel.figures["capex_core"].items()} == {Q("2024Q3"): 1637.0, Q("2025Q2"): 3779.0,
                                                                         Q("2025Q3"): 3378.0}


def test_bidu_total_must_be_core_plus_iqiyi():
    bad = CAPEX_OK.replace("(1,645 )", "(1,700 )")
    assert cp.parse_bidu(bidu_release(capex=bad)) is None


def test_bidu_wrong_amount_count_or_header_is_not_used():
    assert cp.parse_bidu(bidu_release(capex=CAPEX_OK.rsplit(" (3 )", 1)[0])) is None
    no_usd = HDR_PLAIN.replace("Three months ended September 30, 2025 (US$) ", "")
    assert cp.parse_bidu(bidu_release(header=no_usd)) is None
    swapped = HDR_PLAIN.replace(ENT * 4, "iQIYI Baidu excl. iQIYI Baidu, Inc. " * 4)  # first entity not Baidu
    assert cp.parse_bidu(bidu_release(header=swapped)) is None


def test_bidu_title_quarter():
    assert cp.bidu_quarter(BIDU_HEAD.format(title="Fourth Quarter and Fiscal Year 2019", date="x")) == Q("2019Q4")
    assert cp.bidu_quarter("Baidu Announces Pricing of Notes") is None


# ------------------------------------------------------------------ eras and vintages


def test_era_vintages_new_value_and_rounding():
    era = cs.Era("k", "2020-01-01", None, "d")
    rows = [("2020-02-01", "2019Q4", 100.0), ("2020-02-01", "2018Q4", 80.0), ("2021-02-01", "2020Q4", 120.0),
            ("2021-02-01", "2019Q4", 100.4)]  # within rounding: no new vintage
    df = cs.era_vintages(rows, era)
    assert list(df.period) == ["2018Q4", "2019Q4", "2020Q4"]
    assert list(df.known_from) == [pd.Timestamp("2020-02-01")] * 2 + [pd.Timestamp("2021-02-01")]


def test_undeclared_restatement_raises_and_declared_is_a_vintage():
    rows = [("2020-02-01", "2019Q4", 100.0), ("2021-02-01", "2019Q4", 103.0)]
    with pytest.raises(cs.DefinitionBreakError):
        cs.era_vintages(rows, cs.Era("k", "2020-01-01", None, "d"))
    df = cs.era_vintages(rows, cs.Era("k", "2020-01-01", None, "d", revisions=("2021-02-01",)))
    assert df.value.tolist() == [100.0, 103.0]


def test_rows_outside_the_era_are_ignored():
    old, new = cs.Era("old", "2019-01-01", "2020-12-31", "a"), cs.Era("new", "2021-01-01", None, "b")
    rows = [("2020-02-01", "2019Q4", 100.0), ("2021-02-01", "2019Q4", 130.0), ("2021-02-01", "2020Q4", 140.0)]
    assert cs.era_vintages(rows, old).value.tolist() == [100.0]
    assert cs.era_vintages(rows, new).set_index("period").value.to_dict() == {"2019Q4": 130.0, "2020Q4": 140.0}


def test_release_in_no_declared_era_is_reported():
    rel = cp.Release("baba", Q("2014Q3"), figures={"capex": {Q("2014Q3"): (1.0, "x")}})
    f = cs.Filing(1, "0001-14-000001", "2014-11-04", "", "6-K", "p.htm")
    assert cs.undeclared([(f, "p.htm", rel)], "baba", "capex") == ["2014-11-04"]


def test_declared_eras_do_not_overlap():
    for eras in cs.ERAS.values():
        spans = sorted((e.first, e.last or "9999") for e in eras)
        assert all(a[1] < b[0] for a, b in zip(spans, spans[1:]))


def test_candidate_docs_order():
    f = cs.Filing(1, "a", "2024-11-15", "", "6-K", "x_6k.htm")
    index = {"directory": {"item": [{"name": "x_ex99-2.htm", "size": "947457"}, {"name": "x_ex99-1.htm",
              "size": "597628"}, {"name": "x_6k.htm", "size": "9295"}, {"name": "R1.htm", "size": "50000"},
             {"name": "x_ex99-3.htm", "size": "11000"}]}}
    assert cs.candidate_docs(f, index) == ["x_ex99-1.htm", "x_ex99-2.htm"]


# EDGAR's filing index page (-index.htm), cut down: the document table and the data-file table, an iXBRL link, the
# complete submission text file with an empty Type cell.
INDEX_HTM = """
<table class="tableFile" summary="Document Format Files">
<tr><th scope="col">Seq</th><th scope="col">Description</th><th scope="col">Document</th><th scope="col">Type</th>
<th scope="col">Size</th></tr>
<tr><td scope="row">1</td><td scope="row">6-K</td>
<td scope="row"><a href="/Archives/edgar/data/1329099/000119312521014247/x_6k.htm">x_6k.htm</a></td>
<td scope="row">6-K</td><td scope="row">9295</td></tr>
<tr class="evenRow"><td scope="row">2</td><td scope="row">EX-99.1</td>
<td scope="row"><a href="/ix?doc=/Archives/edgar/data/1329099/000119312521014247/x_ex99-1.htm">x_ex99-1.htm</a>
 &nbsp;&nbsp;<span class="label">iXBRL</span></td>
<td scope="row">EX-99.1</td><td scope="row">597628</td></tr>
<tr><td scope="row">3</td><td scope="row">EX-99.2</td>
<td scope="row"><a href="/Archives/edgar/data/1329099/000119312521014247/x_ex99-2.htm">x_ex99-2.htm</a></td>
<td scope="row">EX-99.2</td><td scope="row">947457</td></tr>
<tr><td scope="row">&nbsp;</td><td scope="row">Complete submission text file</td>
<td scope="row"><a href="/Archives/edgar/data/1329099/000119312521014247/0001193125-21-014247.txt">0001193125-21-014247.txt</a></td>
<td scope="row">&nbsp;</td><td scope="row">1600000</td></tr>
</table>
<table class="tableFile" summary="Data Files">
<tr><td scope="row">4</td><td scope="row">XBRL SCHEMA FILE</td>
<td scope="row"><a href="/Archives/edgar/data/1329099/000119312521014247/x-20210131.xsd">x-20210131.xsd</a></td>
<td scope="row">EX-101.SCH</td><td scope="row">3100</td></tr>
</table>
"""


def test_index_htm_items():
    assert cs.index_htm_items(INDEX_HTM) == [
        {"name": "x_6k.htm", "size": "9295"}, {"name": "x_ex99-1.htm", "size": "597628"},
        {"name": "x_ex99-2.htm", "size": "947457"}, {"name": "0001193125-21-014247.txt", "size": "1600000"},
        {"name": "x-20210131.xsd", "size": "3100"}]


def _http_error(status):
    import requests
    r = requests.Response()
    r.status_code = status
    return requests.HTTPError(f"{status} error", response=r)


def _fake_get(index_status=None, htm=INDEX_HTM):
    calls = []

    def get(url, retries=2):
        calls.append(url.rsplit("/", 1)[-1])
        if url.endswith("index.json"):
            if index_status:
                raise _http_error(index_status)
            return b'{"directory": {"item": [{"name": "x_ex99-1.htm", "size": "597628"}]}}'
        if url.endswith("-index.htm"):
            return htm.encode()
        raise AssertionError(url)
    return get, calls


def test_filing_index_reads_index_json_first(monkeypatch):
    get, calls = _fake_get()
    monkeypatch.setattr(cs, "cached_get", get)
    f = cs.Filing(1329099, "0001193125-21-014247", "2021-01-29", "", "6-K", "x_6k.htm")
    assert cs.filing_index(f)["directory"]["item"] == [{"name": "x_ex99-1.htm", "size": "597628"}]
    assert calls == ["index.json"]


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_filing_index_falls_back_to_index_htm_on_5xx(monkeypatch, status):
    get, calls = _fake_get(index_status=status)
    monkeypatch.setattr(cs, "cached_get", get)
    f = cs.Filing(1329099, "0001193125-21-014247", "2021-01-29", "", "6-K", "x_6k.htm")
    index = cs.filing_index(f)
    assert calls == ["index.json", "0001193125-21-014247-index.htm"]
    assert cs.candidate_docs(f, index) == ["x_ex99-1.htm", "x_ex99-2.htm"]  # the same documents as index.json lists


@pytest.mark.parametrize("status", [403, 404, 429])
def test_filing_index_raises_4xx(monkeypatch, status):
    get, calls = _fake_get(index_status=status)
    monkeypatch.setattr(cs, "cached_get", get)
    f = cs.Filing(1329099, "0001193125-21-014247", "2021-01-29", "", "6-K", "x_6k.htm")
    with pytest.raises(Exception) as e:
        cs.filing_index(f)
    assert e.value.response.status_code == status
    assert calls == ["index.json"]


def test_filing_index_fallback_without_documents_raises(monkeypatch):
    get, _ = _fake_get(index_status=502, htm="<html>maintenance</html>")
    monkeypatch.setattr(cs, "cached_get", get)
    f = cs.Filing(1329099, "0001193125-21-014247", "2021-01-29", "", "6-K", "x_6k.htm")
    with pytest.raises(RuntimeError, match="lists no documents"):
        cs.filing_index(f)


# ------------------------------------------------------------------ Baidu text coding


def doc(text, quarter="2025Q3", filed="2025-11-18"):
    return ct.Doc(filed, f"{filed}T14:00:00.000Z", "6-K", "0001-25-000001", "https://www.sec.gov/x.htm", Q(quarter),
                  text)


def test_text_coding_was_and_reached():
    d = doc("Baidu Announces Third Quarter 2025 Results. In the third quarter of 2025, revenue from AI Cloud Infra "
            "reached RMB 4.2 billion, up 33% year over year. Revenue from Baidu Core was RMB24.7 billion, and "
            "non-online marketing revenue was RMB9.3 billion ($1.31 billion), up 21% year over year.")
    rows, uncoded, kept = ct.code_doc(d)
    got = {r.series: (r.period, r.value) for r in rows}
    assert got == {"rev_bidu_ai_cloud_infra": ("2025Q3", 4.2), "rev_bidu_core_nonads": ("2025Q3", 9.3)}
    r = next(r for r in rows if r.series == "rev_bidu_ai_cloud_infra")
    k = int(r.locator.removeprefix("sentence #"))
    assert r.sentence_sha256 == guidance_capex.sentence_hash(guidance_capex.sentences(d.text)[k])
    assert uncoded == []


def test_text_hedged_other_quarter_and_full_year_are_not_coded():
    d = doc("Baidu Announces Third Quarter 2025 Results. “Non-online marketing revenue exceeded RMB 10 billion,” he "
            "said. Revenue from AI Cloud Infra was approximately RMB 20 billion for the full year 2025. Revenue from "
            "AI Cloud Infra was RMB 3.1 billion in the second quarter of 2025. Revenue from AI Cloud Infra was RMB "
            "4.2 billion in the third quarter of 2025.")
    rows, uncoded, _ = ct.code_doc(d)
    assert [(r.series, r.value) for r in rows] == [("rev_bidu_ai_cloud_infra", 4.2)]
    reasons = sorted(w for _, _, w in uncoded)
    assert len(reasons) == 3 and any("another quarter" in w for w in reasons)
    assert any("full or fiscal year" in w for w in reasons) and any("hedged" in w for w in reasons)


def test_text_q4_release_codes_only_before_the_fiscal_year_heading():
    d = doc("Baidu Announces Fourth Quarter and Fiscal Year 2024 Results. Fourth Quarter 2024 Results. Non-online "
            "marketing revenue was RMB9.8 billion, up 18% year over year. Fiscal Year 2024 Results. Non-online "
            "marketing revenue was RMB31.7 billion, up 12% year over year.", quarter="2024Q4", filed="2025-02-18")
    rows, uncoded, _ = ct.code_doc(d)
    assert [(r.series, r.period, r.value) for r in rows] == [("rev_bidu_core_nonads", "2024Q4", 9.8)]
    assert [w for _, _, w in uncoded] == ["after the fiscal-year heading (annual figures)"]


def test_text_two_amounts_for_one_series_raise():
    d = doc("Baidu Announces Third Quarter 2025 Results. Non-online marketing revenue was RMB9.3 billion. Later, "
            "non-online marketing revenue was RMB9.5 billion.")
    with pytest.raises(ct.CodingError):
        ct.code_doc(d)


def test_text_rows_round_trip_and_series_scale(tmp_path):
    d = doc("Baidu Announces Third Quarter 2025 Results. Non-online marketing revenue reached 2.9 billion ($434 "
            "million), increasing 14% year over year.")
    rows, _, _ = ct.code_doc(d)
    path = tmp_path / "china_text.csv"
    ct.write(rows, path)
    df = ct.series_rows("rev_bidu_core_nonads", path)
    assert df.value.tolist() == [2900.0] and df.known_from.tolist() == [pd.Timestamp("2025-11-18")]


def test_check_row_statuses():
    text = "First sentence here. Non-online marketing revenue was RMB9.3 billion, up 21%. Last one."
    sent = guidance_capex.sentences(text)[1]
    row = pd.Series({"locator": "sentence #1", "sentence_sha256": guidance_capex.sentence_hash(sent), "value": 9.3})
    assert chk.check_row(row, text) == "ok"
    assert chk.check_row(row.copy().replace({"sentence #1": "sentence #0"}), text) == "moved"
    assert chk.check_row(row, "Something else entirely. Nothing.") == "sentence_not_found"
    assert chk.check_row(pd.Series({**row.to_dict(), "value": 9.4}), text) == "number_not_in_sentence"
    assert chk.number_in(10.0, "was RMB10.0 billion") and chk.number_in(10.0, "was RMB 10 billion")
    assert not chk.number_in(0.3, "was RMB10.3 billion")


def test_check_dates():
    subs = {"a": {"filed": "2025-11-18", "accepted": "2025-11-18T14:00:09.000Z"}}
    row = pd.Series({"accession": "a", "filed": "2025-11-18", "accepted": "2025-11-18T14:00:09.000Z"})
    assert chk.check_dates(row, subs) == "ok"
    assert chk.check_dates(pd.Series({**row.to_dict(), "filed": "2025-11-17"}), subs).startswith("filed_differs")
    assert chk.check_dates(pd.Series({**row.to_dict(), "accession": "b"}), subs) == "accession_not_in_submissions"


# ------------------------------------------------------------------ H.10 and the US$ view

H10_PAGE = ("<p>Release Date: <strong>Monday, November 23, 2026</strong></p><table>"
            + "".join(f"<tr><th>{d}</th><td>{v}</td></tr>" for d, v in
                      [("1-JUL-26", "7.0000"), ("2-JUL-26", "ND"), ("3-JUL-26", "6.0000")]) + "</table>")


def test_h10_page_parse():
    rates, rel = fed_h10.parse_page(H10_PAGE)
    assert rates.to_dict() == {pd.Timestamp("2026-07-01"): 7.0, pd.Timestamp("2026-07-03"): 6.0}
    assert rel == pd.Timestamp("2026-11-23")


def test_quarterly_mean_needs_enough_days():
    days = pd.bdate_range("2026-01-01", "2026-03-31")
    rates = pd.Series(7.0, index=days)
    assert fed_h10.quarterly_mean(rates).to_dict() == {Q("2026Q1"): 7.0}
    assert fed_h10.quarterly_mean(rates.iloc[:40]).empty  # too few quoted days, and the quarter is not over


def test_to_usd_divides_and_dates():
    rows = pd.DataFrame({"period": ["2026Q1", "2026Q2"], "value": [700.0, 690.0],
                         "known_from": [pd.Timestamp("2026-05-13"), pd.Timestamp("2026-07-05")]})
    fx = pd.Series({Q("2026Q1"): 7.0, Q("2026Q2"): 6.9})
    out = series_mod.to_usd(rows, fx).set_index("period")
    assert out.value.round(6).to_dict() == {"2026Q1": 100.0, "2026Q2": 100.0}
    assert out.known_from["2026Q1"] == pd.Timestamp("2026-05-13")
    assert out.known_from["2026Q2"] == pd.Timestamp("2026-07-10")  # quarter end + 10 days is later
    assert series_mod.to_usd(rows, fx.iloc[:1]).period.tolist() == ["2026Q1"]


# ------------------------------------------------------------------ catalog


def test_catalog_entries():
    specs = catalog.by_key(series_mod.SPECS)
    assert catalog.validate(series_mod.SPECS) == []
    for key in ("rev_baba_cloud_v1", "rev_baba_cloud_v2", "rev_baba_cloud_v3", "capex_baba_v1",
                "rev_bidu_core_nonads"):
        assert specs[key].closed
    for key, s in specs.items():
        assert s.branch == ("G5" if key.startswith("capex") else "G4")
        assert s.publish == (not key.startswith("rev_bidu_")), key  # text series wait for the extraction review
        assert licenses.verdict(s).klass == licenses.JA, key
        assert "FRED" not in s.source  # the H.10 copy is from federalreserve.gov, not FRED (licenses: alfred)
    assert {k for k in specs if k.endswith("_usd")} == {f"{k}_usd" for k in series_mod.OPEN_TABLE}
    assert all(specs[k].unit == "MRMB" for k in specs if not k.endswith("_usd"))
