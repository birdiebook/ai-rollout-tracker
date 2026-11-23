"""Company AI KPIs (track B4): loader, series, candidate selection and the sampling check. Synthetic fixtures, no
network (the committed curated CSV is read, but no document is fetched)."""

import csv

import pandas as pd
import pytest

from ai_tracker import ai_kpis_check as chk
from ai_tracker.series import ai_kpis as series
from ai_tracker.sources import ai_kpis, ai_kpis_corpus as corp, guidance_capex

SENT = "The Gemini App now has over 650 million monthly active users."


def _row(**kw):
    r = {"id": "t-1", "company": "googl", "definition": "GOOGL_GEMINI_APP_MAU", "kind": "min", "value_lo": "650",
         "value_hi": "650", "unit": "miljoner användare", "code": "", "capacity_time": "", "freq": "M",
         "period": "2025-10", "period_basis": "document_date", "filed": "2025-10-29",
         "accepted": "2025-10-29T20:01:00.000Z", "doc_type": "8-K EX-99.1",
         "source_url": "https://www.sec.gov/Archives/edgar/data/1652044/x/ex991.htm", "accession": "0001652044-25-1",
         "locator": "sentence #15", "sentence_sha256": guidance_capex.sentence_hash(SENT), "note": ""}
    r.update(kw)
    return r


def _write(tmp_path, rows):
    p = tmp_path / "ai_kpis.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ai_kpis.COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return p


def test_load_valid_row(tmp_path):
    df = ai_kpis.load(_write(tmp_path, [_row()]))
    assert df["value_lo"].iloc[0] == 650 and df["known_from"].iloc[0] == pd.Timestamp("2025-10-29")


@pytest.mark.parametrize("bad, msg", [
    ({"definition": "NOPE"}, "unknown definition"),
    ({"unit": "MUSD"}, "!= definition"),
    ({"period": "2025-11"}, "before its period"),
    ({"accepted": "2025-10-20T20:00:00.000Z"}, "does not match the filing date"),
    ({"kind": "range"}, "needs value_lo"),
    ({"code": "1"}, "only for capacity rows"),
    ({"locator": "somewhere"}, "locator"),
    ({"sentence_sha256": "abc"}, "64 hex"),
])
def test_load_rejects(tmp_path, bad, msg):
    with pytest.raises(ai_kpis.CsvError, match=msg):
        ai_kpis.load(_write(tmp_path, [_row(**bad)]))


def test_capacity_rows(tmp_path):
    cap = _row(id="c-1", definition="GOOGL_CAPACITY_CURRENT", kind="code", value_lo="", value_hi="", unit="kod",
               code="1", capacity_time="current", freq="Q", period="2025Q3")
    assert ai_kpis.load(_write(tmp_path, [cap]))["code"].iloc[0] == 1
    with pytest.raises(ai_kpis.CsvError, match="capacity_time"):
        ai_kpis.load(_write(tmp_path, [{**cap, "capacity_time": "forward"}]))
    with pytest.raises(ai_kpis.CsvError, match="code in -2..2"):
        ai_kpis.load(_write(tmp_path, [{**cap, "code": "3"}]))


def test_forward_row_may_precede_its_period(tmp_path):
    r = _row(id="f-1", definition="MSFT_AI_BUSINESS_RUNRATE_EXPECTED", company="msft", unit="MUSD", value_lo="10000",
             value_hi="10000", period="2024-12", period_basis="forward", filed="2024-10-30",
             accepted="2024-10-30T20:00:00.000Z")
    assert len(ai_kpis.load(_write(tmp_path, [r]))) == 1


def test_series_frame_first_document_counts(tmp_path):
    rows = [_row(), _row(id="t-2", filed="2025-10-30", accepted=""),  # repeat: no new row
            _row(id="t-3", period="2026-02", filed="2026-02-04", accepted="", value_lo="750", value_hi="750")]
    f = ai_kpis.series_frame(ai_kpis.load(_write(tmp_path, rows)), "GOOGL_GEMINI_APP_MAU")
    assert f["period"].tolist() == ["2025-10", "2026-02"]
    assert f["known_from"].tolist() == [pd.Timestamp("2025-10-29"), pd.Timestamp("2026-02-04")]


def test_specs_gaps_and_inactive(tmp_path, monkeypatch):
    rows = [_row(), _row(id="t-3", period="2026-02", filed="2026-02-04", accepted="", value_lo="750",
                         value_hi="750"),
            _row(id="o-1", definition="META_AI_MAU", company="meta", period="2024-04", filed="2024-04-24",
                 accepted="", value_lo="1000", value_hi="1000", kind="approx")]
    monkeypatch.setattr(ai_kpis, "PATH", _write(tmp_path, rows))
    specs, gaps = series._specs()
    by = {s.key: s for s in specs}
    assert "kpi_googl_gemini_app_mau" in gaps  # 2025-10 and 2026-02, months between missing
    assert by["kpi_meta_ai_mau"].closed and not by["kpi_googl_gemini_app_mau"].closed
    assert all(not s.publish for s in specs)


def test_real_csv_loads_and_every_definition_has_a_series():
    df = ai_kpis.load()
    keys = {s.key for s in series.SPECS}
    assert {ai_kpis.series_key(c) for c in df["definition"]} == keys
    assert set(df["id"]).isdisjoint(set()) and df["id"].is_unique


# ------------------------------------------------------------------ candidates (lesson R2-F1)

@pytest.mark.parametrize("sentence, why", [
    ("We are increasing our investment in AI to approximately $85 billion.", "kpi"),  # present tense
    ("Our first-party models now process 7 billion tokens per minute.", "kpi"),
    ("Customer demand continues to exceed available supply.", "capacity"),  # no number needed
    ("Revenue was $12 billion.", None),
    ("We thank our employees.", None),
])
def test_is_candidate(sentence, why):
    assert corp.is_candidate(sentence) == why


def test_msft_call_dates_follow_the_results_8k():
    docs = [corp.Document("msft", "8-K EX-99.1", "u1", "a1", "2025-10-29", "", "8-K", "2.02,9.01"),
            corp.Document("msft", "8-K EX-99.2", "u2", "a1", "2025-10-29", "", "8-K", "2.02,9.01"),
            corp.Document("msft", "8-K EX-99.1", "u3", "a2", "2026-01-28", "", "8-K", "2.02,9.01"),
            corp.Document("msft", "8-K EX-99.1", "u4", "a3", "2026-09-02", "", "8-K", "7.01,9.01")]
    calls = corp.msft_call_documents(docs)
    assert [(c.label, c.filed) for c in calls] == [("FY2026 Q1", "2025-10-29"), ("FY2026 Q2", "2026-01-28")]
    assert calls[0].url.endswith("/fy-2026/earnings-fy-2026-q1")


def test_exhibit_rows_from_index_page():
    page = ('<tr><td scope="row">1</td><td scope="row">8-K</td><td scope="row"><a href="/ix?doc=/Archives/edgar/'
            'data/1/2/a.htm">a.htm</a></td><td scope="row">8-K</td><td>1</td></tr><tr><td scope="row">2</td><td>PRESS'
            '</td><td><a href="/Archives/edgar/data/1/2/ex991.htm">ex991.htm</a></td><td>EX-99.1</td><td>2</td></tr>')
    assert corp._ROW_RE.findall(page) == [("/ix?doc=/Archives/edgar/data/1/2/a.htm", "8-K"),
                                          ("/Archives/edgar/data/1/2/ex991.htm", "EX-99.1")]


# ------------------------------------------------------------------ sampling check

@pytest.mark.parametrize("value, unit, text", [
    (650, "miljoner användare", "over 650 million monthly active users"),
    (1000, "miljoner användare", "has reached one billion users"),
    (1000, "miljoner användare", "almost 1 billion monthly actives"),
    (13000, "MUSD", "run rate of $13 billion"),
    (450, "MUSD", "a $450 million annualized revenue run-rate"),
    (53000, "antal", "We now have 53,000 Azure AI customers."),
    (100, "biljoner tokens", "over 100 trillion tokens"),
    (7, "miljarder tokens per minut", "7 billion tokens per minute"),
    (38, "%", "31% 7% 38% Windows"),
    (12, "procentenheter", "including 12 points from our AI services"),
])
def test_number_patterns(value, unit, text):
    assert any(__import__("re").search(p, text, 2) for p in chk.number_patterns(value, unit))


def test_check_row_ok_moved_and_errors():
    row = pd.Series(_row(locator="sentence #1", value_lo=650.0, value_hi=650.0))
    assert chk.check_row(row, f"Intro sentence. {SENT}") == "ok"
    assert chk.check_row(row, f"Intro sentence. Another one. {SENT}") == "moved"
    assert chk.check_row(row, "Intro sentence. Something else entirely.") == "sentence_not_found"
    wrong = row.copy()
    wrong["value_lo"] = wrong["value_hi"] = 750.0
    assert chk.check_row(wrong, f"Intro sentence. {SENT}") == "number_not_in_sentence"


def test_capacity_words():
    row = pd.Series({"kind": "code", "code": 1.0})
    assert chk.sentence_ok(row, "Customer demand continues to exceed available supply.")
    assert not chk.sentence_ok(pd.Series({"kind": "code", "code": -2.0}), "Demand continues to exceed supply.")
