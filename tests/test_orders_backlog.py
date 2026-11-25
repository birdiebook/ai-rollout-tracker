"""Track S3: orders and backlog in earnings releases (synthetic fixtures, no network)."""

from __future__ import annotations

import csv

import pandas as pd
import pytest

from ai_tracker import catalog, licenses, orders_check
from ai_tracker.sources import guidance_capex, orders_backlog as ob, orders_backlog_corpus as corpus

URL = "https://www.sec.gov/Archives/edgar/data/1674101/000162828025000001/ex991.htm"


def _row(**kw) -> dict:
    """A valid value row; keyword arguments override columns."""
    base = dict(id="vrt-2025-04-23-01", company="vrt", row_type="value", measure="orders", segment="total",
                component="all", window="q", form="yoy_pct", organic="organic", unit="pct", value="13", qualifier="",
                metric_as_stated="organic orders", fiscal_period="2025Q1", period_end="2025-03-31",
                filed="2025-04-23", accepted="2025-04-23T06:30:00.000Z", release_date="2025-04-23",
                form_type="8-K", exhibit="EX-99.1", source_url=URL, accession="0001628280-25-000001",
                locator="sentence #4", sentence_sha256="a" * 64, note="")
    base.update(kw)
    if base["row_type"] == "stop":
        base.update(value="", qualifier="", locator="absent", sentence_sha256=ob.EMPTY_SHA256)
    return base


def _release(n: int, filed: str, end: str, fp: str) -> dict:
    acc = f"0001628280-25-00000{n}"
    return dict(filed=filed, accepted=f"{filed}T06:30:00.000Z", release_date=filed, period_end=end, fiscal_period=fp,
                accession=acc, source_url=URL.replace("000162828025000001", acc.replace("-", "")))


R1 = _release(1, "2025-04-23", "2025-03-31", "2025Q1")
R2 = _release(2, "2025-07-30", "2025-06-30", "2025Q2")
R3 = _release(3, "2025-10-22", "2025-09-30", "2025Q3")
R4 = _release(4, "2026-02-11", "2025-12-31", "2025Q4")


def _write(tmp_path, rows) -> pd.DataFrame:
    p = tmp_path / "orders_backlog.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ob.COLUMNS)
        w.writeheader()
        for i, r in enumerate(rows):
            w.writerow({**r, "id": f"t-{i:02d}"})
    return ob.load(p)


# ------------------------------------------------------------------ parser

@pytest.mark.parametrize("text, want", [
    ("Strong orders COLUMBUS, Ohio [April 27, 2022] – Vertiv Holdings Co", "2022-04-27"),
    ("Guidance COLUMBUS, Ohio October 26, 2022 – Vertiv", "2022-10-26"),
    ("capital use CAMBRIDGE, Mass., (Apr. 25, 2024) – GE Vernova Inc.", "2024-04-25"),
    ("Midpoint DUBLIN--(BUSINESS WIRE)--February 4, 2022--Power management", "2022-02-04"),
    ("guidance DUBLIN — April 30, 2024 — Intelligent power", "2024-04-30"),
    ("ROUND ROCK, Texas — Sept. 1, 2026 — Dell Technologies", "2026-09-01"),
    ("REDWOOD CITY, Calif., Feb. 16, 2022 /PRNewswire/ -- 2021", "2022-02-16"),
    ("Results Dallas, TX — July 24, 2025 — Digital Realty", "2025-07-24"),
    ("for the quarter ended March 31, 2024. Revenue grew.", None),
])
def test_dateline(text, want):
    assert corpus.dateline(text) == want


def test_release_exhibit_prefers_ex991_then_ex99_never_ex992():
    assert corpus.release_exhibit([("EX-99.2", "a/s.htm"), ("EX-99.1", "a/r.htm")]) == ("EX-99.1", "a/r.htm")
    assert corpus.release_exhibit([("8-K", "a/k.htm"), ("EX-99", "a/r.htm")]) == ("EX-99", "a/r.htm")
    assert corpus.release_exhibit([("EX-99.2", "a/s.htm")]) is None


def test_parse_index_reads_type_and_archive_url():
    page = ('<tr><td>1</td><td>EX-99.1</td><td><a href="/Archives/edgar/data/1/0001/r.htm">r.htm</a></td>'
            '<td>EX-99.1</td></tr><tr><td>2</td><td></td><td><a href="/ix?doc=/Archives/edgar/data/1/0001/k.htm">'
            'k.htm</a> iXBRL</td><td>8-K</td></tr>')
    assert corpus.parse_index(page) == [("EX-99.1", "https://www.sec.gov/Archives/edgar/data/1/0001/r.htm"),
                                        ("8-K", "https://www.sec.gov/Archives/edgar/data/1/0001/k.htm")]


def test_reading_set_is_candidates_and_the_sentence_after():
    text = ("Revenue grew. Orders were up 12% this quarter. The rise came from data centers. Backlog was strong. "
            "Net income was $5 million.")
    rs = corpus.reading_set(text)
    assert rs == {1: "candidate", 2: "after"}  # 'Backlog was strong' has no digit


def test_gap_rule_takes_the_8k_filed_with_the_10q():
    filings = [
        {"form": "8-K", "filed": "2025-04-23", "accession": "a1", "items": "2.02,9.01", "accepted": "1",
         "report_date": "2025-04-23"},
        {"form": "10-Q", "filed": "2025-04-23", "accession": "q1", "items": "", "accepted": "2",
         "report_date": "2025-03-31"},
        {"form": "8-K", "filed": "2025-07-23", "accession": "a2", "items": "2.01,9.01", "accepted": "3",
         "report_date": "2025-07-23"},
        {"form": "10-Q", "filed": "2025-07-23", "accession": "q2", "items": "", "accepted": "4",
         "report_date": "2025-06-30"},
    ]
    got = [(f["accession"], via) for f, via in corpus.select_filings(filings, "2025-01-01", "2025-12-31")]
    assert got == [("a1", "item_2.02"), ("a2", "gap_rule")]


# ------------------------------------------------------------------ number and hash check

@pytest.mark.parametrize("value, unit, sentence", [
    (7400, "MUSD", "backlog increased to $7.4 billion"),
    (9700, "MUSD", "Total orders of $ 9.7 B with orders exceeding revenue"),
    (5029, "MUSD", "Orders $5,029 $4,018 25%"),
    (30.75, "MUSD", "0-1 MW $30,750 128 $240 9.9"),
    (-40, "pct", "Orders $1,150 $1,919 (40)% Revenues"),
    (51.2, "pct", "orders increased 51.2% compared with"),
    (1.0, "ratio", "The book-to-bill ratio was 1.0x for first quarter 2023."),
    (50, "GW", "backlog and slot reservation agreements grew from 50 to 55 GW"),
    (7, "GW", "Signed 7 gigawatts of gas turbine orders"),
    (21.7, "MW", "All Regions 0-1 MW $72,517 240 $303 21.7 $278"),
])
def test_number_in_accepts_the_written_forms(value, unit, sentence):
    assert orders_check.number_in(value, unit, sentence)


@pytest.mark.parametrize("value, unit, sentence", [
    (7400, "MUSD", "backlog increased to $7.9 billion"),
    (17, "pct", "orders were up 117% sequentially"),
    (1.2, "ratio", "orders rose 21% to $1.25 billion"),
])
def test_number_in_rejects_other_numbers(value, unit, sentence):
    assert not orders_check.number_in(value, unit, sentence)


def test_check_row_hash_moved_and_number():
    text = "Revenue grew. Organic orders increased 13% from the prior year quarter. Margins rose."
    s = guidance_capex.sentences(text)[1]
    row = pd.Series(_row(sentence_sha256=guidance_capex.sentence_hash(s), locator="sentence #1", value=13))
    assert orders_check.check_row(row, text) == "ok"
    assert orders_check.check_row(row, "A new first sentence. " + text) == "moved"
    other = row.copy()
    other["value"] = 14
    assert orders_check.check_row(other, text) == "number_not_in_sentence"
    assert orders_check.check_row(row, text.replace("13%", "15%")) == "sentence_not_found"


def test_stop_check_flags_a_sentence_that_still_states_the_definition():
    stop = pd.Series(_row(row_type="stop", organic="organic", window="q"))
    assert orders_check.check_row(stop, "Revenue grew. Organic orders rose 9% in the quarter.").startswith("still")
    # a twelve-month figure or a currency basis is not the quarterly organic figure
    assert orders_check.check_row(stop, "Trailing twelve-month organic orders rose 9%.") == "ok"
    assert orders_check.check_row(stop, "Orders rose 9% (excluding foreign exchange).") == "ok"
    # a headline bullet is its own statement
    backlog = pd.Series(_row(row_type="stop", measure="backlog", window="end", form="level", organic="na", unit="MUSD"))
    assert orders_check.check_row(backlog, "• Strong backlog execution • Net sales of $1.2 billion") == "ok"
    assert orders_check.check_row(backlog, "• Record backlog of $1.2 billion").startswith("still")


def test_release_date_check_wants_the_dateline_unless_it_is_after_the_filing():
    row = pd.Series(_row(filed="2026-02-03", release_date=""))
    assert orders_check.check_release_date(row, "DUBLIN — February 26, 2026 — Eaton") == "ok"  # a typo: left empty
    row2 = pd.Series(_row(filed="2025-07-31", release_date="2025-07-30"))
    assert orders_check.check_release_date(row2, "Calif. - July 30, 2025 - Equinix") == "ok"
    assert orders_check.check_release_date(row2, "Calif. - July 31, 2025 - Equinix").startswith("release_date_differs")


# ------------------------------------------------------------------ dating and the scheme

def test_known_from_is_the_filing_date(tmp_path):
    df = _write(tmp_path, [_row(**R1)])
    assert df["known_from"].iloc[0] == pd.Timestamp("2025-04-23")


@pytest.mark.parametrize("bad", [
    {"release_date": "2025-04-24"},  # dated after the filing
    {"release_date": "2025-04-15"},  # more than three days before it
    {"period_end": "2025-04-30"},  # period after the filing
    {"accepted": "2025-04-27T06:30:00.000Z"},
    {"form": "level"},  # a level in pct
    {"organic": "na"},  # a growth rate needs its basis
    {"window": "end"},  # orders are a flow
    {"segment": "power"},  # not a Vertiv segment
    {"qualifier": "nearly"},
    {"accession": "0001628280-25-000009"},  # not the URL's folder
])
def test_load_rejects_rows_outside_the_scheme(tmp_path, bad):
    with pytest.raises(ob.CsvError):
        _write(tmp_path, [_row(**bad)])


def test_a_stop_is_never_coded_in_an_extra_document(tmp_path, monkeypatch):
    monkeypatch.setitem(ob.EXTRA_DOCUMENTS, R2["accession"], "preliminary")
    with pytest.raises(ob.CsvError, match="regular release"):
        _write(tmp_path, [_row(**R1), _row(row_type="stop", **R2)])
    with pytest.raises(ob.CsvError, match="regular release"):
        _write(tmp_path, [_row(**R1), _row(row_type="stop", form_type="8-K/A", **R3)])


def test_period_of_fiscal_quarters_and_years():
    assert ob.period_of("2024-02-02", "end") == "2023Q4"  # Dell FY2024 Q4 -> calendar quarter of its midpoint
    assert ob.period_of("2024-05-03", "q") == "2024Q1"
    assert ob.period_of("2026-01-30", "fy") == "2025"
    assert ob.freq_of("fy") == "A" and ob.freq_of("ttm") == "Q"


# ------------------------------------------------------------------ vintages, stops and gaps

def test_first_document_counts_and_a_changed_value_is_a_new_vintage(tmp_path):
    level = dict(form="level", organic="na", unit="MUSD", measure="orders", value="5029")
    rows = [_row(**R1, **level),
            _row(**{**R2, "period_end": R1["period_end"], "fiscal_period": "2025Q1"}, **{**level, "value": "5029"}),
            _row(**{**R3, "period_end": R1["period_end"], "fiscal_period": "2025Q1"}, **{**level, "value": "6263"})]
    df = _write(tmp_path, rows)
    f = ob.series_frame(df, ob.series_key(df.iloc[0]))
    assert list(f["value"]) == [5029.0, 6263.0]
    assert list(f["known_from"]) == [pd.Timestamp(R1["filed"]), pd.Timestamp(R3["filed"])]


def test_bounds_are_in_the_csv_but_not_series_points(tmp_path):
    df = _write(tmp_path, [_row(**R1), _row(**R2), _row(**R3, qualifier="gt", value="100")])
    key = ob.series_key(df.iloc[0])
    assert list(ob.series_frame(df, key)["period"]) == ["2025Q1", "2025Q2"]
    assert ob.catalog_keys(df) == [key]


def test_expected_stop_when_a_regular_release_no_longer_states_a_definition(tmp_path):
    df = _write(tmp_path, [_row(**R1), _row(**R2), _row(**R3, measure="book_to_bill", form="ratio", organic="na",
                                                       unit="ratio", value="1.4")])
    st = ob.expected_stops(df)
    assert list(st.itertuples(index=False, name=None)) == [("vrt", "ob_vrt_orders_total_q_yoy_pct_organic_pct",
                                                            R3["accession"])]
    # a release that states nothing at all must be passed explicitly
    reg = {"vrt": [R1["accession"], R2["accession"], "0001628280-25-000099"]}
    assert list(ob.expected_stops(df[df["accession"] != R3["accession"]], reg)["accession"]) == ["0001628280-25-000099"]


def test_a_comparative_does_not_count_as_stating_the_definition(tmp_path):
    comparative = {**R2, "period_end": R1["period_end"], "fiscal_period": "2025Q1"}
    df = _write(tmp_path, [_row(**R1), _row(**comparative, value="14"),
                           _row(**R2, measure="book_to_bill", form="ratio", organic="na", unit="ratio", value="1.2")])
    assert list(ob.expected_stops(df)["accession"]) == [R2["accession"]]


def test_stop_closes_the_series_and_a_bound_does_not_reopen_it(tmp_path):
    rows = [_row(**R1), _row(**R2), _row(row_type="stop", **R3), _row(**R4, qualifier="gt", value="100")]
    df = _write(tmp_path, rows)
    key = ob.series_key(df.iloc[0])
    assert ob.stopped(df, key) is not None
    rows.append(_row(**_release(5, "2026-04-22", "2026-03-31", "2026Q1"), value="60"))
    df = _write(tmp_path, rows)
    assert ob.stopped(df, key) is None  # stated again as a number: the series continues, the stop stays
    gaps = ob.gap_periods(df, key)
    assert set(gaps) == {"2025Q3", "2025Q4"} and all(v.startswith("stop") for v in gaps.values())
    assert list(ob.series_frame(df, key)["period"]) == ["2025Q1", "2025Q2", "2026Q1"]  # the gap is not filled


# ------------------------------------------------------------------ the committed CSV and the catalog

def test_committed_csv_loads_and_its_stops_follow_the_rule():
    df = ob.load()
    stops = df[df["row_type"] == "stop"]
    got = set(zip(stops["company"], stops.apply(ob.series_key, axis=1), stops["accession"]))
    assert got == set(map(tuple, ob.expected_stops(df).values))
    assert (df["known_from"] == pd.to_datetime(df["filed"])).all()


def test_catalog_series_are_unpublished_sec_extracts_with_class_ja():
    specs = [s for s in catalog.ALL if s.key.startswith("ob_")]
    assert specs and not any(s.publish for s in specs)
    assert {s.branch for s in specs} <= {"G4", "G6", "G7"}
    assert all(licenses.classify(s)[0] == "ja" for s in specs)
    assert not [e for e in catalog.validate() if e.startswith("ob_")]
