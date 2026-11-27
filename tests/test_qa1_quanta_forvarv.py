"""QA1: Quanta's acquisitions as data in LT1's acquisition mark (register 2026-11-27 QA1, after R28-7).

- curated/acquisitions.csv loads and validates; ids, events, quarters and closing dates agree; no source text is stored
- marks(): one mark per event, the latest consideration known on the day, nothing before the first filing
- LT1: Quanta's marks follow the documented ones in L1 and only in L1, with offset and direction; a mark never changes
  an outcome (the reading on synthetic data is the same with and without the marks)
- the self-check's patterns (amounts in millions, billions and table thousands, counts, dates) on known sentences
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import acquisitions_check as K
from ai_tracker.followed import ledtid as L
from ai_tracker.sources import acquisitions as A
from ai_tracker.sources import guidance_capex as gc


@pytest.fixture(scope="module")
def df():
    return A.load()


def test_csv_loads_and_every_event_has_one_quarter(df):
    assert list(df.columns[:-1]) == A.COLUMNS and df["id"].is_unique
    assert set(df["company"]) == {"pwr"}
    assert set(df["row_type"]) <= set(A.ROW_TYPES)
    assert df.groupby("event")["quarter"].nunique().max() == 1
    closed = df[df["closed"] != ""]
    assert all(A.quarter_of(c) == q for c, q in zip(closed["closed"], closed["quarter"]))
    assert (closed["closed"] >= A.SINCE).all()


def test_csv_holds_no_source_text(df):
    # figures with a source reference only: the sentence is a hash, notes are short and in the agent's own words
    assert "quote" not in df.columns and "sentence" not in df.columns
    assert df["sentence_sha256"].str.fullmatch(r"[0-9a-f]{64}").all()
    assert (df["note"].str.len() <= 160).all()


def test_every_quarter_from_2023_is_coded_as_acquisitions_or_none(df):
    qs = [str(q) for q in pd.period_range("2023Q1", "2026Q3", freq="Q")]
    coded = set(df["quarter"])
    assert set(qs) <= coded
    none = set(df.loc[df["row_type"] == "none", "quarter"])
    assert none == {"2023Q2", "2024Q4", "2026Q1"}


def test_counts_add_up_to_the_new_businesses_per_quarter(df):
    # the businesses a filing counts for a period, less the previous filing's count, are the quarter's new ones
    label_n = {"pwr-2023Q1": 3, "pwr-2023Q3": 1, "pwr-2024Q1": 3, "pwr-2024Q2": 2, "pwr-2025Q1": 2, "pwr-2025Q2": 2,
               "pwr-2025Q4": 3, "pwr-2026Q2": 3, "pwr-2026Q3": 2}
    labels = df[df["row_type"].isin(A.MARK_TYPES)].groupby("event")["label"].last()
    for ev, n in label_n.items():
        assert labels[ev].startswith(f"Quanta, {n} förvärv")
    counts = df[df["row_type"].isin(("count", "none"))].dropna(subset=["n_businesses"])
    by = {(r.event, r.period_stated): int(r.n_businesses) for r in counts.itertuples()}
    assert by[("pwr-2026Q3", "9 mån 2026")] - by[("pwr-2026Q2", "6 mån 2026")] == 2
    assert by[("pwr-2025Q4", "helår 2025")] - by[("pwr-2025Q3-dsi", "9 mån 2025")] == 3
    assert by[("pwr-2024Q4", "helår 2024")] == by[("pwr-2024Q3", "9 mån 2024")] == 8


def test_marks_follow_known_from_and_the_latest_consideration(df):
    before = {a for _, a, _ in A.marks("pwr", "2026-07-29", df)}
    after = {a for _, a, _ in A.marks("pwr", "2026-07-30", df)}
    assert "2026Q2" not in before and "2026Q3" not in before
    assert {"2026Q2", "2026Q3"} <= after  # the 10-Q for 2026Q2 also states a closing on 2026-07-10
    cei = {a: n for n, a, _ in A.marks("pwr", "2024-08-01", df) if n.startswith("Quanta–Cupertino")}
    assert cei == {"2024Q3": "Quanta–Cupertino Electric"}  # known, no consideration yet
    by_day = {d: [n for n, _, _ in A.marks("pwr", d, df) if n.startswith("Quanta–Cupertino")][0]
              for d in ("2024-10-31", "2025-02-20", "2026-02-19")}
    assert by_day == {"2024-10-31": "Quanta–Cupertino Electric (1 968 MUSD)",
                      "2025-02-20": "Quanta–Cupertino Electric (cirka 2 040 MUSD)",
                      "2026-02-19": "Quanta–Cupertino Electric (2 035 MUSD)"}
    assert all(a != "2026Q1" for _, a, _ in A.marks("pwr", None, df))  # the quarter with no acquisition


def test_l1_marks_list_documented_then_quanta_with_direction():
    m = L.acquisition_quarters("L1")["2026Q2"]
    assert m.startswith("Eaton–Fibrebond a + 4, ned; Eaton–Boyd Thermal a + 1, upp; ")
    assert "Quanta, 2 förvärv 2025Q1 (589 MUSD, 3 mån 2025) a + 5, ned" in m
    assert "Quanta, 2 förvärv 2025Q2 (816 MUSD, 6 mån 2025) a + 4, ned" in m
    assert m.endswith("Quanta, 3 förvärv 2026Q2 (1 430 MUSD, 6 mån 2026) a, upp")
    q3 = L.acquisition_quarters("L1")["2026Q3"]
    assert "Quanta–Dynamic Systems (1 673 MUSD) a + 4, ned" in q3 and "2026Q3 (1 800 MUSD, 9 mån 2026) a, upp" in q3


def test_quanta_marks_only_l1_and_respect_the_day():
    assert L.acquisition_quarters("L2") == {"2024Q1": "Cisco–Splunk a, upp", "2024Q2": "Cisco–Splunk a + 1, upp",
                                            "2025Q1": "Cisco–Splunk a + 4, ned", "2025Q2": "Cisco–Splunk a + 5, ned"}
    for row in ("L3", "O1", "O2"):
        assert L.acquisition_quarters(row) == {}
    old = L.acquisition_quarters("L1", "2025-11-27")
    assert not any("2026Q2" in v for v in old.values())  # not filed by then
    assert "Quanta, 2 förvärv 2025Q2" in old["2025Q2"]


def _ms(xs: dict[str, float], ys: dict[str, float]) -> dict[str, dict]:
    def m(key, ch):
        return {"series": key, "available": True, "period": max(ch), "known_from": "2026-11-03",
                "path": {q: {"level": 1.0, "pace": 0.0, "change": v} for q, v in ch.items()}}
    return {"lt1_rpo_power": m("lt1_rpo_power", xs), "kl_capex4_inner": m("kl_capex4_inner", ys)}


def test_a_mark_never_changes_an_outcome(monkeypatch):
    qs = [str(q) for q in pd.period_range("2024Q1", "2026Q3", freq="Q")]
    xs = {q: 0.0 for q in qs} | {"2026Q2": 16.5}
    ys = {q: 0.0 for q in qs} | {"2026Q3": 9.6}
    ms = _ms(xs, ys)
    with_marks = L.reading("L1", "inner", "fore", 2, ms)
    monkeypatch.setattr(L, "ACQ_COMPANIES", {})
    monkeypatch.setattr(L, "ACQUISITIONS", {})
    without = L.reading("L1", "inner", "fore", 2, ms)
    keys = ("outcome", "origin", "t", "decided_at")
    assert {k: with_marks.get(k) for k in keys} == {k: without.get(k) for k in keys}
    assert with_marks["origin_acquisition"] and "Quanta, 3 förvärv 2026Q2" in with_marks["origin_acquisition"]
    assert without["origin_acquisition"] is None


def test_check_patterns_on_known_forms():
    row = pd.Series({"row_type": "consideration", "consideration_musd": 1799.666, "n_businesses": None, "closed": ""})
    assert K.numbers_in(row, "Fair value of total consideration transferred or estimated to be transferred $ 1,799,666")
    assert not K.numbers_in(row, "Fair value of total consideration $ 1,799,667")
    row2 = row.copy()
    row2["consideration_musd"] = 2040
    assert K.numbers_in(row2, "The aggregate consideration for the acquisition was approximately $ 2.04 billion")
    row3 = row.copy()
    row3["consideration_musd"] = 300
    assert K.numbers_in(row3, "was approximately $ 300 million, consisting of")
    cnt = pd.Series({"row_type": "none", "consideration_musd": None, "n_businesses": 3, "closed": ""})
    assert K.numbers_in(cnt, "We acquired three business during the six months ended June 30, 2023.")
    dt = pd.Series({"row_type": "acquisition", "consideration_musd": None, "n_businesses": 1, "closed": "2023-08-30"})
    assert K.numbers_in(dt, "On August 30, 2023, we completed an acquisition in which")
    assert not K.numbers_in(dt, "On August 31, 2023, we completed an acquisition in which")


def test_check_row_finds_moved_sentences():
    text = "First sentence here. On July 25, 2025, Quanta completed the acquisition of a business. Last one."
    sents = A.sentences(text)
    k = next(i for i, s in enumerate(sents) if "July 25" in s)
    row = pd.Series({"row_type": "acquisition", "consideration_musd": None, "n_businesses": 1, "closed": "2025-07-25",
                     "locator": f"sentence #{k}", "sentence_sha256": gc.sentence_hash(sents[k])})
    assert K.check_row(row, text) == "ok"
    assert K.check_row(row.copy().replace({f"sentence #{k}": "sentence #0"}), text) == "moved"
    assert K.check_row(row, "Nothing about it.") == "sentence_not_found"


def test_load_rejects_a_closing_outside_its_quarter(tmp_path, df):
    bad = df.drop(columns="known_from").astype(object).where(df.drop(columns="known_from").notna(), "")
    bad = bad.astype(str).replace({"nan": ""})
    i = bad.index[bad["closed"] == "2024-07-17"][0]
    bad.loc[i, "quarter"] = "2024Q2"
    bad.loc[bad["event"] == bad.loc[i, "event"], "quarter"] = "2024Q2"
    p = tmp_path / "a.csv"
    bad.to_csv(p, index=False)
    with pytest.raises(A.CsvError, match="not in quarter"):
        A.load(p)
