"""Lab revenue registry (track B6): post parser, curated CSV loader, series and row verification (no network).

Fixture markup and sentences are synthetic: they follow the layout of a newsroom post with made-up numbers, so no
source text is copied into the repo.
"""

from __future__ import annotations

import csv

import pandas as pd
import pytest

from ai_tracker import catalog
from ai_tracker.series import lab_revenue as series
from ai_tracker.sources import lab_revenue as lr

POST_HTML = """<html><head><title>Example Lab raises a round</title>
<meta property="article:published_time" content="2031-03-04T00:00:00.000Z"/>
<meta property="article:modified_time" content="2031-05-01T00:00:00.000Z"/>
<script type="application/ld+json">{"datePublished":"2031-03-04T00:00:00.000Z"}</script></head><body>
<p class="x_reading-column post-text">We are pleased to announce a new round. Our run-rate revenue reached over
$3.5 billion in February 2031, up from approximately $900 million at the start of 2030.</p>
<ul><li class="x post-text">Product X now generates $120 million in run-rate revenue.</li></ul>
<p class="footer">Unrelated $5 billion footer revenue sentence.</p></body></html>"""

S1 = ("Our run-rate revenue reached over $3.5 billion in February 2031, up from approximately $900 million at the "
      "start of 2030.")


def _row(**kw) -> dict:
    row = {"id": "x-01", "lab": "anthropic", "scope": "company", "measure": "RUN_RATE", "qualifier": "over",
           "value": "3500", "unit": "MUSD", "period": "2031-02-28", "period_end": "2031-02-28",
           "known_from": "2031-03-04", "doc_type": "newsroom", "accession": "", "modified": "2031-05-01",
           "source_url": "https://www.example.com/news/round", "locator": "sentence #1",
           "sentence_sha256": lr.sentence_hash(S1), "note": ""}
    row.update(kw)
    return row


def _write(tmp_path, rows) -> object:
    p = tmp_path / "lab_revenue.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=lr.COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return p


# ------------------------------------------------------------------ parsing

def test_parse_post_dates_body_and_sentences():
    post = lr.parse_post("https://www.example.com/news/round", POST_HTML)
    assert post.published == "2031-03-04" and post.modified == "2031-05-01"
    assert post.title == "Example Lab raises a round"
    assert "footer" not in post.body  # only post-text paragraphs and list items
    assert post.sentences[1] == S1
    assert post.sentences[2].startswith("Product X")


def test_candidates_find_revenue_sentences_with_amounts():
    post = lr.parse_post("https://www.example.com/news/round", POST_HTML)
    c = lr.candidates([post])
    assert list(c["locator"]) == ["sentence #1", "sentence #2"]
    assert (c["published"] == "2031-03-04").all()


def test_sentence_hash_normalises_whitespace():
    assert lr.sentence_hash("a  b\n c ") == lr.sentence_hash("a b c")


# ------------------------------------------------------------------ loader

def test_load_valid_row(tmp_path):
    df = lr.load(_write(tmp_path, [_row()]))
    assert df.loc[0, "value"] == 3500 and df.loc[0, "known_from"] == pd.Timestamp("2031-03-04")


@pytest.mark.parametrize("bad, match", [
    ({"period": "2031-03-10", "period_end": "2031-03-10"}, "after the statement's publication"),
    ({"doc_type": "DRS"}, "confidential draft"),
    ({"doc_type": "S-1/A", "accession": ""}, "accession"),
    ({"measure": "RUN_RATE_S1"}, "S-1-defined"),
    ({"period": "2031-02"}, "period = period_end"),
    ({"measure": "REVENUE_CY", "period": "2030", "period_end": "2030-06-30"}, "YYYY-12-31"),
    ({"qualifier": "about"}, "qualifier"),
    ({"lab": "acme"}, "scheme"),
    ({"sentence_sha256": "abc"}, "64 hex"),
    ({"value": "-1"}, "positive"),
    ({"modified": "2031-01-01"}, "modified before published"),
    ({"locator": "paragraph 2"}, "sentence #"),
])
def test_load_rejects(tmp_path, bad, match):
    with pytest.raises(lr.CsvError, match=match):
        lr.load(_write(tmp_path, [_row(**bad)]))


def test_load_rejects_duplicate_id(tmp_path):
    with pytest.raises(lr.CsvError, match="duplicate"):
        lr.load(_write(tmp_path, [_row(), _row()]))


# ------------------------------------------------------------------ series

def test_series_frame_restated_value_adds_no_vintage(tmp_path):
    rows = [_row(),
            _row(id="x-02", known_from="2031-04-01", modified=""),  # same period and value, later post
            _row(id="x-03", known_from="2031-04-02", value="3600", modified=""),  # revised statement: new vintage
            _row(id="x-04", period="2030-01-01", period_end="2030-01-01", value="900", qualifier="approx"),
            _row(id="x-05", scope="claude_code", value="120")]
    df = lr.load(_write(tmp_path, rows))
    s = lr.series_frame(df, "anthropic", "company", "RUN_RATE")
    assert list(zip(s["period"], s["value"])) == [("2030-01-01", 900.0), ("2031-02-28", 3500.0),
                                                   ("2031-02-28", 3600.0)]
    assert lr.series_frame(df, "anthropic", "claude_code", "RUN_RATE")["value"].tolist() == [120.0]
    assert lr.series_frame(df, "anthropic", "company", "RUN_RATE_S1").empty


# ------------------------------------------------------------------ verification

def test_check_row_against_post():
    post = lr.parse_post("https://www.example.com/news/round", POST_HTML)
    assert lr.check_row(_row(), post) == []
    assert lr.check_row(_row(value="900", qualifier="approx", period="2030-01-01", period_end="2030-01-01"),
                        post) == []
    assert any("hash differs" in e for e in lr.check_row(_row(locator="sentence #2"), post))
    assert any("not stated" in e for e in lr.check_row(_row(value="3000"), post))
    assert any("document date" in e for e in lr.check_row(_row(known_from="2031-03-05"), post))
    assert any("beyond" in e for e in lr.check_row(_row(locator="sentence #9"), post))


def test_fetch_document_dates_sec_filing_by_edgar_index(monkeypatch):
    class R:
        def __init__(self, text):
            self.text = text

    pages = {
        "https://www.sec.gov/Archives/edgar/data/1/000000000031000001/0000000000-31-000001-index.htm":
            '<div class="infoHead">Filing Date</div>\n   <div class="info">2031-03-06</div>',
        "https://www.sec.gov/Archives/edgar/data/1/000000000031000001/doc.htm":
            "<html><body><p>Risk factors.</p><p>" + S1 + "</p></body></html>",
    }
    monkeypatch.setattr(lr.http, "get", lambda url, source, **kw: R(pages[url]))
    row = _row(doc_type="S-1/A", accession="0000000000-31-000001", measure="RUN_RATE_S1", modified="",
               source_url="https://www.sec.gov/Archives/edgar/data/1/000000000031000001/doc.htm",
               known_from="2031-03-06")
    post = lr.fetch_document(row)
    assert post.published == "2031-03-06"
    assert lr.check_row(row, post) == []


# ------------------------------------------------------------------ the curated registry itself

def test_curated_csv_is_valid_and_first_party_only():
    df = lr.load()
    assert len(df) >= 10
    assert (df["period_end"] <= df["known_from"]).all()
    newsroom = df[df["doc_type"] == "newsroom"]
    assert newsroom["source_url"].str.startswith("https://www.anthropic.com/news/").all()
    sec = df[df["doc_type"] != "newsroom"]
    assert sec["source_url"].str.startswith(lr.SEC_ARCHIVE).all()
    assert not df["doc_type"].isin(lr.REFUSED_FORMS).any()


def test_specs_are_labelled_reported_and_valid():
    specs = series.SPECS
    keys = {s.key for s in specs}
    assert {"lab_rev_anthropic_company_run_rate", "lab_rev_anthropic_company_run_rate_s1",
            "lab_rev_anthropic_claude_code_run_rate"} <= keys
    assert all(s.label.endswith("(rapporterad)") and s.branch == "G4" and not s.publish for s in specs)
    assert catalog.validate(specs) == []
    for s in specs:
        frame = s.fetch()
        assert {"period", "value", "known_from"} <= set(frame.columns) and not frame.empty
        assert (pd.PeriodIndex(frame["period"], freq="D").end_time.normalize()
                <= pd.to_datetime(frame["known_from"])).all()


def test_paused_hosts_refuse_without_explicit_opt_in(monkeypatch):
    calls = []
    monkeypatch.setattr(lr.http, "get", lambda url, source, **kw: calls.append(url))
    with pytest.raises(lr.SourcePaused, match="www.anthropic.com"):
        lr.fetch_post("https://www.anthropic.com/news/x")
    with pytest.raises(lr.SourcePaused):
        lr.fetch_document(_row(source_url="https://www.anthropic.com/news/x"))
    assert calls == []
    with pytest.raises(AttributeError):  # opted in: the request goes out (the stub returns None)
        lr.fetch_post("https://www.anthropic.com/news/x", allow_paused=True)
    assert calls == ["https://www.anthropic.com/news/x"]
