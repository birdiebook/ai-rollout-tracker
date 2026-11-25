"""R21 review of CN1, China via SEC (docs/granskning/r21-kina-sec.md). Synthetic fixtures, no network.

Evidence was read on 2026-11-25 in the original documents, fetched again from www.sec.gov with the project's generic
client (22 results releases, two 20-F instances, both companyfacts) and from www.federalreserve.gov (H.10 history and
15 archived weekly releases). Every fetched release was byte-identical to CN1's raw copy. Only ids, numbers, dates and
SHA-256 prefixes are kept here, never source text; the fixtures below are synthetic text in the releases' layouts.

- Passing tests: era boundaries as stated in the releases, no splice across eras, filing-date dating, Alibaba's fiscal
  quarters on calendar quarters, the third Baidu header layout and the iQIYI dash, the 55-day rule on its own, the US$
  dating, the H.10 licence part, the 26 curated rows as read by R21, and two wordings of the text coding.
- Confirmed defects, strict xfail until fixed in auto14k/x18-kina-sec, now passing: R21-1 (v4 label), R21-2 (the doc's
  "under 1 %" claim), R21-3 (the registered companyfacts check for Alibaba's capex is not run), R21-4 (capex_baba_v1
  does not say it holds licensed video copyrights).
"""

from __future__ import annotations

import hashlib
import re

import pandas as pd

from ai_tracker import china_crosscheck, config, licenses
from ai_tracker.series import china_sec as series_mod
from ai_tracker.sources import china_parse as cp
from ai_tracker.sources import china_sec as cs
from ai_tracker.sources import china_text as ct
from ai_tracker.sources import fed_h10, sec

SOURCE_DOC = config.REPO / "docs" / "kallor" / "kina_sec.md"
Q = lambda s: pd.Period(s, freq="Q-DEC")  # noqa: E731


def specs() -> dict:
    return {s.key: s for s in series_mod.SPECS}


# ------------------------------------------------------------------ eras (point 2)

# (key, first release, last release) as R21 read them in the releases themselves: the first segment table (2016-08-11),
# "Beginning on April 1, 2021 ... DingTalk ... Comparative figures were reclassified" (2021-08-03), the six business
# groups with DingTalk inside Cloud Intelligence Group (2023-08-10, one release), "Starting from the quarter ended
# September 30, 2023 ... DingTalk ... to All others" in the 2023-11-16 release itself, "Cloud Intelligence Group and
# T-Head were combined" (2026-08-20); capex: one PP&E-and-intangibles line to 2018-05-04, the line with licensed
# copyrights (2018-08-23, one release), PP&E split from copyrights and intangibles from 2018-11-02.
ERAS_READ = {
    ("baba", "rev_cloud"): [("rev_baba_cloud_v1", "2016-08-11", "2021-05-13"), ("rev_baba_cloud_v2", "2021-08-03",
                            "2023-05-18"), ("", "2023-08-10", "2023-08-10"), ("rev_baba_cloud_v3", "2023-11-16",
                            "2026-05-13"), ("rev_baba_cloud_v4", "2026-08-20", None)],
    ("baba", "capex"): [("capex_baba_v1", "2015-01-29", "2018-05-04"), ("", "2018-08-23", "2018-08-23"),
                        ("capex_baba_v2", "2018-11-02", None)],
    ("bidu", "capex_total"): [("capex_bidu", "2020-03-04", None)],
    ("bidu", "capex_core"): [("capex_bidu_core", "2020-03-04", None)],
}


def test_era_boundaries_are_the_ones_stated_in_the_releases():
    got = {k: [(e.key, e.first, e.last) for e in v] for k, v in cs.ERAS.items()}
    assert got == ERAS_READ
    assert all(not e.revisions for v in cs.ERAS.values() for e in v)  # no in-era restatement was found


def test_every_definition_is_its_own_series_never_spliced():
    keys = [e.key for v in cs.ERAS.values() for e in v if e.key]
    assert len(keys) == len(set(keys))
    assert set(keys) == set(series_mod.TABLE)
    # the DingTalk boundary as it happened: 2020Q2 is 12,345 in v1 (2020-08-20) and 12,437 restated in v2 (2021-08-03)
    rows = [("2020-08-20", "2020Q2", 12345.0), ("2020-08-20", "2019Q2", 7787.0), ("2021-08-03", "2020Q2", 12437.0),
            ("2021-08-03", "2021Q2", 16051.0)]
    eras = dict((e.key, e) for e in cs.ERAS[("baba", "rev_cloud")])
    v1 = cs.era_vintages(rows, eras["rev_baba_cloud_v1"]).set_index("period")
    v2 = cs.era_vintages(rows, eras["rev_baba_cloud_v2"]).set_index("period")
    assert v1.value.to_dict() == {"2019Q2": 7787.0, "2020Q2": 12345.0}
    assert v2.value.to_dict() == {"2020Q2": 12437.0, "2021Q2": 16051.0}
    assert v2.known_from["2020Q2"] == pd.Timestamp("2021-08-03")  # the restated comparative is dated by its release


# ------------------------------------------------------------------ calendar and dating (point 3)


def test_alibaba_fiscal_quarters_are_calendar_quarters():
    head = "EX-99.1 Exhibit 99.1 Alibaba Group Announces {} Results Hangzhou, China, {} - text. "
    assert cp.baba_quarter(head.format("June Quarter 2016", "August 11, 2016")) == Q("2016Q2")  # FY2017 Q1
    assert cp.baba_quarter(head.format("December Quarter 2024", "February 20, 2025")) == Q("2024Q4")  # FY2025 Q3
    assert cp.baba_quarter(head.format("March Quarter 2015 and Full Fiscal Year 2015", "May 7, 2015")) == Q("2015Q1")
    hkex = ("(Stock Code: 9988) ANNOUNCEMENT OF THE MARCH QUARTER 2026 RESULTS AND FISCAL YEAR 2026 ANNUAL RESULTS "
            "The board of directors")
    assert cp.baba_quarter(hkex) == Q("2026Q1")
    assert cp.quarter_of("June", "30", "2016") == Q("2016Q2") and cp.quarter_of("March", "31", "2026") == Q("2026Q1")


def test_known_from_is_the_filing_date_and_an_unchanged_comparative_keeps_it():
    era = cs.Era("k", "2020-01-01", None, "d")
    rows = [("2023-11-16", "2023Q3", 27648.0), ("2023-11-16", "2022Q3", 27035.0),
            ("2024-11-15", "2023Q3", 27648.0), ("2024-11-15", "2024Q3", 29610.0)]
    df = cs.era_vintages(rows, era).set_index("period")
    assert df.known_from.to_dict() == {"2022Q3": pd.Timestamp("2023-11-16"), "2023Q3": pd.Timestamp("2023-11-16"),
                                       "2024Q3": pd.Timestamp("2024-11-15")}
    assert all(kf >= pd.Period(p, freq="Q-DEC").end_time.normalize() for p, kf in df.known_from.items())


# ------------------------------------------------------------------ Baidu layouts seen in the corpus (point 4)

CF_HEAD = ("Condensed Consolidated Statements of Cash Flows (In millions, unaudited) Three months ended March 31, 2024 "
           "(RMB) Three months ended December 31, 2024 (RMB) Three months ended March 31, 2025 (RMB) Three months "
           "ended March 31, 2025 (US$) ")
TOP_ALIGNED = "Baidu iQIYI Baidu, " * 4 + "excl. Inc. " * 4  # the 2025-05-21 layout ("iQIYI" of col 1 is not repeated)
ROWS = "Net cash provided by operating activities 1 2 3 4 5 6 7 8 9 10 11 12 Less: Capital expenditures {} Free cash "


def bidu(header_entities: str, capex: str) -> str:
    return ("EX-99.1 Exhibit 99.1 Baidu Announces First Quarter 2025 Results BEIJING, China, May 21, 2025 – Baidu, "
            "Inc. today announced. " + CF_HEAD + header_entities + ROWS.format(capex))


def test_bidu_top_aligned_header_layout_parses():
    rel = cp.parse_bidu(bidu(TOP_ALIGNED, "(2,016 ) (22 ) (2,038 ) (2,312 ) (21 ) (2,333 ) (2,869 ) (31 ) (2,900 ) "
                                          "(395 ) (4 ) (399 )"))
    assert rel.quarter == Q("2025Q1")
    assert {q: v for q, (v, _) in rel.figures["capex_total"].items()} == {Q("2024Q1"): 2038.0, Q("2024Q4"): 2333.0,
                                                                          Q("2025Q1"): 2900.0}
    assert {q: v for q, (v, _) in rel.figures["capex_core"].items()} == {Q("2024Q1"): 2016.0, Q("2024Q4"): 2312.0,
                                                                         Q("2025Q1"): 2869.0}


def test_bidu_iqiyi_dash_is_zero():
    ent = "Baidu excl. iQIYI iQIYI Baidu, Inc. " * 4
    rel = cp.parse_bidu(bidu(ent, "(1,928 ) (51 ) (1,979 ) (1,920 ) (9 ) (1,929 ) (1,295 ) — (1,295 ) (189 ) — (189 )"))
    assert rel.figures["capex_total"][Q("2025Q1")][0] == rel.figures["capex_core"][Q("2025Q1")][0] == 1295.0


# ------------------------------------------------------------------ RMB/USD (point 6)


def test_quarterly_mean_needs_55_quoted_days_in_a_finished_quarter():
    days = pd.bdate_range("2026-01-01", "2026-03-31")  # 64 business days
    later = pd.Series(7.0, index=pd.bdate_range("2026-04-01", "2026-04-10"))  # the quarter is over
    for n, has_mean in ((54, False), (55, True)):
        rates = pd.concat([pd.Series(7.0, index=days[:n]), later])
        assert (Q("2026Q1") in fed_h10.quarterly_mean(rates).index) is has_mean, n


def test_usd_view_is_never_dated_before_the_rmb_row_or_the_rate():
    rows = pd.DataFrame({"period": ["2026Q2", "2026Q3"], "value": [48437.0, 60973.0],
                         "known_from": [pd.Timestamp("2026-08-20"), pd.Timestamp("2026-10-05")]})
    fx = pd.Series({Q("2026Q2"): 6.8048, Q("2026Q3"): 6.7406})
    out = series_mod.to_usd(rows, fx).set_index("period")
    for p, r in rows.set_index("period").iterrows():
        assert out.known_from[p] >= r.known_from
        assert out.known_from[p] >= Q(p).end_time.normalize() + pd.Timedelta(days=series_mod.FX_LAG_DAYS)
    assert round(out.value["2026Q2"], 1) == round(48437.0 / 6.8048, 1)


def test_h10_licence_part_is_public_domain_and_no_fred_copy():
    assert licenses.licence_verdict(series_mod.FED_LICENSE).klass == licenses.JA
    for key in series_mod.OPEN_TABLE:
        s = specs()[f"{key}_usd"]
        assert "federalreserve.gov" in s.source and not re.search(r"\b(?:AL)?FRED\b|stlouisfed", s.source)


# ------------------------------------------------------------------ text rows read by R21 (point 4, extraction)

# id, period, value (RMB bn), filed, accession, sha256 prefix: all 26 rows; R21 read every sentence (measure and
# quarter) and checked 18 year-over-year pairs against the implied prior-year value (all within rounding)
TEXT_ROWS = [
    ("bidu-2025-11-18-ai_cloud_infra", "2025Q3", 4.2, "2025-11-18", "0001193125-25-285391", "d53c9476308cf992"),
    ("bidu-2026-02-26-ai_cloud_infra", "2025Q4", 5.8, "2026-02-26", "0001193125-26-076505", "483f55b35c9bcdc1"),
    ("bidu-2026-05-18-ai_cloud_infra", "2026Q1", 8.8, "2026-05-18", "0001193125-26-228123", "1d78813183d74181"),
    ("bidu-2026-08-18-ai_cloud_infra", "2026Q2", 7.3, "2026-08-18", "0001193125-26-355431", "49017a27e8c18d17"),
    ("bidu-2026-11-16-ai_cloud_infra", "2026Q3", 8.2, "2026-11-16", "0001193125-26-462286", "8ebb159c58acb83c"),
    ("bidu-2020-11-17-core_nonads", "2020Q3", 2.9, "2020-11-17", "0001193125-20-295510", "dc518a3ff738c1db"),
    ("bidu-2021-02-22-core_nonads", "2020Q4", 4.2, "2021-02-22", "0001193125-21-049165", "be279e7e5925c475"),
    ("bidu-2021-05-20-core_nonads", "2021Q1", 4.2, "2021-05-20", "0001193125-21-167243", "d0a11f90ef70a736"),
    ("bidu-2021-08-13-core_nonads", "2021Q2", 5.0, "2021-08-13", "0001193125-21-245436", "67d4af356ced18dd"),
    ("bidu-2021-11-18-core_nonads", "2021Q3", 5.2, "2021-11-18", "0001193125-21-333786", "4bc075acf3de85bc"),
    ("bidu-2022-03-01-core_nonads", "2021Q4", 6.9, "2022-03-01", "0001193125-22-061674", "ed518c99796b8fc3"),
    ("bidu-2022-05-27-core_nonads", "2022Q1", 5.7, "2022-05-27", "0001193125-22-161778", "d5cb2f9d8dd572b6"),
    ("bidu-2022-08-31-core_nonads", "2022Q2", 6.1, "2022-08-31", "0001193125-22-234500", "4dc49830f1908e6d"),
    ("bidu-2022-11-23-core_nonads", "2022Q3", 6.5, "2022-11-23", "0001193125-22-291565", "742359ba2526b92a"),
    ("bidu-2023-02-22-core_nonads", "2022Q4", 7.6, "2023-02-22", "0001193125-23-044848", "791504e577e1b835"),
    ("bidu-2023-05-16-core_nonads", "2023Q1", 6.4, "2023-05-16", "0001193125-23-145594", "2d5cdefa762641f1"),
    ("bidu-2023-08-22-core_nonads", "2023Q2", 6.8, "2023-08-22", "0001193125-23-217413", "842af003f5b99734"),
    ("bidu-2023-11-21-core_nonads", "2023Q3", 6.9, "2023-11-21", "0001193125-23-281151", "2dd598fd36c47b98"),
    ("bidu-2024-02-28-core_nonads", "2023Q4", 8.3, "2024-02-28", "0001193125-24-050652", "34b24b6186a6c523"),
    ("bidu-2024-05-16-core_nonads", "2024Q1", 6.8, "2024-05-16", "0001193125-24-140513", "eb21fd9cf064d360"),
    ("bidu-2024-08-22-core_nonads", "2024Q2", 7.5, "2024-08-22", "0001193125-24-204906", "436087d97adf65af"),
    ("bidu-2024-11-21-core_nonads", "2024Q3", 7.7, "2024-11-21", "0001193125-24-263052", "45af8b7b073d8307"),
    ("bidu-2025-02-18-core_nonads", "2024Q4", 9.8, "2025-02-18", "0001193125-25-028182", "18ed38012d7ebb35"),
    ("bidu-2025-05-21-core_nonads", "2025Q1", 9.4, "2025-05-21", "0001193125-25-123961", "2c788a3304ef71e3"),
    ("bidu-2025-08-20-core_nonads", "2025Q2", 10.0, "2025-08-20", "0001193125-25-183792", "c665a967d7c68da6"),
    ("bidu-2025-11-18-core_nonads", "2025Q3", 9.3, "2025-11-18", "0001193125-25-285391", "197847b0e961a6cd"),
]
REVIEWED_CSV_SHA256 = "ed0199ba92589f107dc59520f57c914235ddc55dcf73c8f386f7f98d9bd57d3d"


def test_curated_text_rows_are_the_rows_r21_read():
    df = ct.load()
    got = sorted((r.id, r.period, float(r.value), r.filed, r.accession, r.sentence_sha256[:16])
                 for r in df.itertuples(index=False))
    assert got == sorted(TEXT_ROWS)
    # a change to the file means rows that R21 has not read: review them again
    assert hashlib.sha256(ct.CSV_PATH.read_bytes()).hexdigest() == REVIEWED_CSV_SHA256


def test_text_coding_handles_the_2021_wording_and_the_2026_fiscal_year_heading():
    q4 = ct.Doc("2021-02-22", "2021-02-19T22:55:35.000Z", "6-K", "a", "u", Q("2020Q4"),
                "Baidu Announces Fourth Quarter and Fiscal Year 2020 Results. Fourth Quarter 2020 Results. Non-marketing "
                "revenue from Baidu Core reached RMB 4.2 billion, increasing 52% year over year. Fiscal Year 2020 "
                "Results. Non-marketing revenue from Baidu Core reached RMB 12.4 billion, increasing 28% year over "
                "year.")
    rows, uncoded, _ = ct.code_doc(q4)
    assert [(r.series, r.period, r.value) for r in rows] == [("rev_bidu_core_nonads", "2020Q4", 4.2)]
    assert len(uncoded) == 1
    q4_2026 = ct.Doc("2026-02-26", "2026-02-26T21:01:17.000Z", "6-K", "b", "u", Q("2025Q4"),
                     "Baidu Announces Fourth Quarter and Fiscal Year 2025 Results. AI Cloud Infra. Revenue from AI Cloud "
                     "Infra was RMB 5.8 billion in the fourth quarter of 2025, up 1% year over year. Fiscal Year 2025 "
                     "Results for Baidu. Revenue from AI Cloud Infra was RMB 19.8 billion in 2025.")
    rows, uncoded, _ = ct.code_doc(q4_2026)
    assert [(r.series, r.period, r.value) for r in rows] == [("rev_bidu_ai_cloud_infra", "2025Q4", 5.8)]
    assert [w for _, _, w in uncoded] == ["after the fiscal-year heading (annual figures)"]


def test_text_series_wait_for_publication_and_table_series_publish():
    s = specs()
    assert not s["rev_bidu_ai_cloud_infra"].publish and not s["rev_bidu_core_nonads"].publish
    assert all(s[k].publish for k in series_mod.TABLE)


# ------------------------------------------------------------------ confirmed defects (fixed in X18)


def test_v4_label_does_not_name_a_start_the_series_does_not_have():
    assert "2025Q2" not in specs()["rev_baba_cloud_v4"].label


def test_doc_does_not_claim_all_boundary_restatements_are_small():
    doc = re.sub(r"\s+", " ", SOURCE_DOC.read_text(encoding="utf-8"))
    assert "Omräkningarna vid gränserna är små (under 1 %)" not in doc


def _fake_series(company: str, measure: str, key: str) -> pd.DataFrame:
    """Quarters as CN1 computed them (R21 checked the sums against the 20-F lines): v1 FY2017, v2 FY2020."""
    data = {"capex_baba_v1": {"2016Q2": 2794.0, "2016Q3": 3348.0, "2016Q4": 3246.0, "2017Q1": 2832.0},
            "capex_baba_v2": {"2019Q2": 5856.0, "2019Q3": 9176.0, "2019Q4": 5749.0, "2020Q1": 3881.0}}.get(key, {})
    return pd.DataFrame({"period": list(data), "value": list(data.values()),
                         "known_from": [pd.Timestamp("2020-07-09")] * len(data)})


def _fact(val: float, start: str, end: str, filed: str) -> dict:
    return {"val": val, "start": start, "end": end, "form": "20-F", "filed": filed, "accn": "0000000000-00-000000",
            "fy": int(end[:4]), "fp": "FY"}


def _fake_companyfacts(cik: int) -> dict:
    if cik == cs.CIKS["bidu"]:
        return {"facts": {"us-gaap": {china_crosscheck.BIDU_CAPEX: {"units": {"CNY": []}}}}}
    return {"facts": {"us-gaap": {  # Alibaba's companyfacts, as read by R21 (millions x 1e6)
        "PaymentsToAcquireOtherPropertyPlantAndEquipment": {"units": {"CNY": [
            _fact(5680e6, "2016-04-01", "2017-03-31", "2018-07-27"),
            _fact(24662e6, "2019-04-01", "2020-03-31", "2020-07-09")]}},
        "PaymentsToAcquireIntangibleAssets": {"units": {"CNY": [
            _fact(6540e6, "2016-04-01", "2017-03-31", "2018-07-27")]}}}}}


def test_crosscheck_runs_the_registered_companyfacts_check_for_alibaba(monkeypatch):
    monkeypatch.setattr(cs, "series", _fake_series)
    monkeypatch.setattr(cs, "filings", lambda *a, **k: [])  # no 20-F instance: only companyfacts can answer
    monkeypatch.setattr(sec, "companyfacts", _fake_companyfacts)
    res = china_crosscheck.run()
    got = {(r.series, r.fy_end): r.diff for r in res.itertuples(index=False) if r.company == "baba"}
    assert abs(got[("capex_baba_v2", "2020-03-31")]) < 0.5
    assert abs(got[("capex_baba_v1", "2017-03-31")]) < 0.5


def test_capex_v1_note_says_it_holds_licensed_copyrights():
    note = specs()["capex_baba_v1"].note.lower()
    assert "upphovsr" in note or "copyright" in note
