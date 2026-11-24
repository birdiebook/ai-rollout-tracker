"""Useful lives of servers (track P2a): loader, step series, catalog, sample check and corpus. Synthetic, no network."""

from __future__ import annotations

import csv
import re
import hashlib

import pandas as pd
import pytest

from ai_tracker import catalog
from ai_tracker.sources import guidance_capex as gc
from ai_tracker.sources import useful_lives as ul
from ai_tracker.sources import useful_lives_corpus as corpus
from ai_tracker import useful_lives_check as chk

URL = "https://www.sec.gov/Archives/edgar/data/1/{folder}/doc.htm"


def _row(**kw) -> dict:
    acc = kw.pop("accession", "0000000001-22-000001")
    base = {c: "" for c in ul.COLUMNS}
    base.update(company="amzn", row_type="policy", asset_class="servers", class_code="SERVERS", life_lo="4",
                life_hi="4", period_end="2021-12-31", filed="2022-02-04", accepted="2022-02-03T18:00:00.000Z",
                doc_type="10-K", source_url=URL.format(folder=acc.replace("-", "")), accession=acc,
                locator="sentence #3", sentence_sha256="a" * 64, note="synthetic")
    base.update(kw)
    return base


def _write(tmp_path, rows) -> str:
    path = tmp_path / "useful_lives.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ul.COLUMNS)
        w.writeheader()
        for i, r in enumerate(rows):
            w.writerow({"id": r.pop("id", f"r{i}"), **r})
    return path


def _fixture() -> list[dict]:
    """Amazon-like history: servers 4 years, changed to 5 from 2022 (announced in the 10-K for 2021), then 6 from
    2024 (announced in the 8-K for 2023Q4, the 10-K repeats it); a subset back to 5 from 2025; network separate."""
    a1, a2, a3, a4 = ("0000000001-22-000001", "0000000001-23-000002", "0000000001-24-000003",
                      "0000000001-24-000004")
    return [
        _row(id="p21", accession=a1),
        _row(id="c22", accession=a1, row_type="change", life_lo="5", life_hi="5", old_lo="4", old_hi="4",
             effective="2022-01-01", locator="sentence #9"),
        _row(id="c22n", accession=a1, row_type="change", asset_class="networking equipment", class_code="NETWORK",
             life_lo="6", life_hi="6", old_lo="5", old_hi="5", effective="2022-01-01", locator="sentence #9"),
        _row(id="e22", accession=a1, row_type="effect", ref="c22", asset_class="", class_code="", life_lo="",
             life_hi="", effect_value="-3100", effect_unit="MUSD", effect_metric="depreciation",
             effect_basis="expected", effect_start="2022-01-01", effect_end="2022-12-31", locator="sentence #10"),
        _row(id="p22", accession=a2, life_lo="5", life_hi="5", period_end="2022-12-31", filed="2023-02-03",
             accepted="2023-02-02T18:00:00.000Z"),
        _row(id="c24", accession=a3, row_type="change", life_lo="6", life_hi="6", old_lo="5", old_hi="5",
             effective="2024-01-01", period_end="2023-12-31", doc_type="8-K EX-99.1", filed="2024-02-01",
             accepted="2024-02-01T21:00:00.000Z"),
        _row(id="p23", accession=a4, life_lo="5", life_hi="5", period_end="2023-12-31", filed="2024-02-02",
             accepted="2024-02-01T21:30:00.000Z"),
        _row(id="c25s", accession="0000000001-25-000005", row_type="change", asset_class="a subset of servers",
             class_code="SERVERS_SUBSET", life_lo="5", life_hi="5", old_lo="6", old_hi="6", effective="2025-01-01",
             period_end="2024-12-31", filed="2025-02-07", accepted="2025-02-06T21:30:00.000Z"),
    ]


@pytest.fixture
def df(tmp_path):
    return ul.load(_write(tmp_path, _fixture()))


# ------------------------------------------------------------------ loader

def test_load_ok(df):
    assert len(df) == 8
    assert df["known_from"].dtype.kind == "M"
    assert df.loc[df["id"] == "e22", "effect_value"].item() == -3100


@pytest.mark.parametrize("change,msg", [
    ({"row_type": "x"}, "row_type"),
    ({"class_code": "SERVER"}, "class_code"),
    ({"life_lo": "6", "life_hi": "4"}, "life_lo <= life_hi"),
    ({"life_hi": ""}, "life_hi required"),
    ({"sentence_sha256": "abc"}, "64 hex"),
    ({"locator": "#3"}, "locator"),
    ({"locator": "absent"}, "absent"),
    ({"period_end": "2022-02-04"}, "before the filing date"),
    ({"accepted": "2022-01-01T10:00:00.000Z"}, "does not match"),
    ({"effective": "2022-01-01"}, "policy row"),
    ({"source_url": "https://example.com/x"}, "EDGAR"),
    ({"accession": "0000000009-22-000009", "source_url": URL.format(folder="000000000122000001")}, "folder"),
])
def test_load_rejects_policy(tmp_path, change, msg):
    with pytest.raises(ul.CsvError, match=msg):
        ul.load(_write(tmp_path, [_row(**change)]))


def test_load_rejects_change_and_effect(tmp_path):
    ch = dict(row_type="change", life_lo="5", life_hi="5", effective="2022-01-01")
    with pytest.raises(ul.CsvError, match="both or neither"):
        ul.load(_write(tmp_path, [_row(**ch, old_lo="4")]))
    with pytest.raises(ul.CsvError, match="effective"):
        ul.load(_write(tmp_path, [_row(row_type="change", life_lo="5", life_hi="5")]))
    with pytest.raises(ul.CsvError, match="days after the filing"):
        ul.load(_write(tmp_path, [_row(**{**ch, "effective": "2023-07-01"})]))
    eff = dict(row_type="effect", ref="c", asset_class="", class_code="", life_lo="", life_hi="", effect_value="-1",
               effect_unit="MUSD", effect_metric="depreciation", effect_basis="expected", effect_start="2022-01-01",
               effect_end="2022-12-31")
    with pytest.raises(ul.CsvError, match="not an earlier change row"):
        ul.load(_write(tmp_path, [_row(**eff)]))
    with pytest.raises(ul.CsvError, match="actual effect"):
        ul.load(_write(tmp_path, [_row(id="c", **ch), _row(**{**eff, "effect_basis": "actual"})]))
    with pytest.raises(ul.CsvError, match="diluted_eps"):
        ul.load(_write(tmp_path, [_row(id="c", **ch), _row(**{**eff, "effect_metric": "diluted_eps"})]))
    with pytest.raises(ul.CsvError, match="no life/class"):
        ul.load(_write(tmp_path, [_row(id="c", **ch), _row(**{**eff, "class_code": "SERVERS"})]))


def test_stop_rows(tmp_path):
    stop = dict(row_type="stop", life_lo="", life_hi="", period_end="2022-12-31", filed="2023-02-03",
                accepted="2023-02-02T18:00:00.000Z", accession="0000000001-23-000002",
                source_url=URL.format(folder="000000000123000002"))
    ok = ul.load(_write(tmp_path, [_row(), _row(id="s", **stop, locator="absent", sentence_sha256=ul.EMPTY_SHA256)]))
    assert ul.stopped(ok, "amzn", "servers")["id"] == "s"
    assert ul.stopped(ok, "amzn", "network") is None
    with pytest.raises(ul.CsvError, match="no numbers"):
        ul.load(_write(tmp_path, [_row(**{**stop, "life_hi": "4"})]))
    with pytest.raises(ul.CsvError, match="10-K"):
        ul.load(_write(tmp_path, [_row(**{**stop, "doc_type": "10-Q"})]))


# ------------------------------------------------------------------ series

def test_series_steps_and_vintages(df):
    hi = ul.series_frame(df, "amzn", "servers", "hi")
    got = {(r.period, r.value, str(r.known_from.date())) for r in hi.itertuples()}
    assert got == {
        ("2021Q4", 4.0, "2022-02-04"),  # policy and the old life of the change agree: one row
        ("2022Q1", 5.0, "2022-02-04"),  # new life from the effective quarter, known before it ended
        ("2022Q4", 5.0, "2023-02-03"),
        ("2023Q4", 5.0, "2024-02-01"),  # old life of the 2024 change (8-K first)
        ("2024Q1", 6.0, "2024-02-01"),
    }  # the 10-K of 2024-02-02 repeats 5 for 2023Q4: no new row; the subset change is not in the series


def test_policy_wins_within_a_document(tmp_path):
    rows = [_row(life_lo="3", life_hi="3"),
            _row(id="c", row_type="change", life_lo="5", life_hi="5", old_lo="4", old_hi="4", effective="2022-01-01")]
    hi = ul.series_frame(ul.load(_write(tmp_path, rows)), "amzn", "servers", "hi")
    assert hi.set_index("period")["value"].to_dict() == {"2021Q4": 3.0, "2022Q1": 5.0}


def test_later_document_with_new_value_is_a_vintage(tmp_path):
    rows = [_row(), _row(id="b", accession="0000000001-22-000009", source_url=URL.format(folder="000000000122000009"),
                         life_lo="5", life_hi="5", filed="2022-03-01", accepted="2022-03-01T12:00:00.000Z")]
    hi = ul.series_frame(ul.load(_write(tmp_path, rows)), "amzn", "servers", "hi")
    assert list(hi["value"]) == [4.0, 5.0] and list(hi["period"]) == ["2021Q4", "2021Q4"]


def test_servers_network_feeds_both_families(df, tmp_path):
    net = ul.series_frame(df, "amzn", "network", "lo")
    assert net.set_index("period")["value"].to_dict() == {"2021Q4": 5.0, "2022Q1": 6.0}
    rows = [_row(asset_class="servers and network equipment", class_code="SERVERS_NETWORK", life_lo="2",
                 life_hi="6")]
    d2 = ul.load(_write(tmp_path, rows))
    assert ul.series_frame(d2, "amzn", "servers", "lo")["value"].tolist() == [2.0]
    assert ul.series_frame(d2, "amzn", "network", "hi")["value"].tolist() == [6.0]


def test_mid_quarter_effective_date(tmp_path):
    rows = [_row(row_type="change", life_lo="5", life_hi="5", old_lo="4", old_hi="4", effective="2022-06-01",
                 period_end="2022-08-31", filed="2022-09-13", accepted="2022-09-12T20:00:00.000Z")]
    hi = ul.series_frame(ul.load(_write(tmp_path, rows)), "amzn", "servers", "hi")
    assert hi.set_index("period")["value"].to_dict() == {"2022Q1": 4.0, "2022Q2": 5.0}


def test_up_to_gives_only_hi(tmp_path):
    d = ul.load(_write(tmp_path, [_row(life_lo="", life_hi="6")]))
    assert ul.series_frame(d, "amzn", "servers", "lo").empty
    assert ul.series_frame(d, "amzn", "servers", "hi")["value"].tolist() == [6.0]


def test_in_effect_as_of(df):
    s = ul.in_effect("amzn", "servers", "hi", as_of="2023-06-30", end="2024Q2", df=df)
    assert s[pd.Period("2021Q4", "Q-DEC")] == 4.0
    assert s[pd.Period("2022Q3", "Q-DEC")] == 5.0  # carried from the effective quarter
    assert s[pd.Period("2024Q2", "Q-DEC")] == 5.0  # the 2024 change is not known on 2023-06-30
    s2 = ul.in_effect("amzn", "servers", "hi", as_of="2024-02-01", end="2024Q2", df=df)
    assert s2[pd.Period("2024Q2", "Q-DEC")] == 6.0
    assert ul.in_effect("amzn", "servers", "hi", as_of="2022-01-01", df=df).empty


def test_changes_joins_effects(df):
    ch = ul.changes(df)
    assert set(ch["id"]) == {"c22", "c22n", "c24", "c25s"}
    assert ch.loc[ch["id"] == "c22", "effect_value"].item() == -3100
    assert ch.loc[ch["id"] == "c24", "effect_value"].isna().all()


def test_specs_from_fixture(tmp_path, monkeypatch):
    from ai_tracker.series import useful_lives as series

    monkeypatch.setattr(ul, "PATH", _write(tmp_path, _fixture()))
    specs, gaps = series._specs()
    keys = {s.key for s in specs}
    assert keys == {"useful_life_servers_amzn_lo", "useful_life_servers_amzn_hi", "useful_life_network_amzn_lo",
                    "useful_life_network_amzn_hi"}
    assert set(gaps) == keys
    s = next(x for x in specs if x.key == "useful_life_servers_amzn_hi")
    assert s.branch == "G5" and s.freq == "Q" and s.publish and s.lag_days == -400 and s.max_age_days == 550
    assert catalog.validate(specs) == []
    assert list(s.fetch()["value"]) == list(ul.series_frame(ul.load(), "amzn", "servers", "hi")["value"])


def test_catalog_has_no_errors():
    assert [e for e in catalog.validate() if e.startswith("useful_life_")] == []


# ------------------------------------------------------------------ sample check

@pytest.mark.parametrize("value,sentence", [
    (6, "we increased the useful life of servers from four to six years"),
    (4, "we increased the useful life of servers from four to six years"),
    (4.5, "an increase in their estimated useful life to four and a half years"),
    (5.5, "Servers and network assets 5.5 years Buildings 25 to 30 years"),
    (2, "computer equipment, two to six years; buildings"),
    (4, "servers from 4 to 5.5 years"),
])
def test_life_patterns_match(value, sentence):
    assert any(re.search(p, sentence, re.I) for p in chk.life_patterns(value))


def test_life_patterns_reject():
    assert not any(re.search(p, "servers 16 years", re.I) for p in chk.life_patterns(6))
    assert not any(re.search(p, "six servers. Ten years later", re.I) for p in chk.life_patterns(6))


def test_check_row(tmp_path):
    text = ("Intro sentence. Property is depreciated. Effective January 1, 2022, we changed our estimate of the useful "
            "lives of our servers from four years to five years. This reduced depreciation by $3.1 billion. End.")
    sents = gc.sentences(text)
    k = next(i for i, s in enumerate(sents) if "servers" in s)
    base = _row(row_type="change", effective="2022-01-01", locator=f"sentence #{k}",
                sentence_sha256=gc.sentence_hash(sents[k]))
    row = pd.Series({**base, "life_lo": 5.0, "life_hi": 5.0, "old_lo": 4.0, "old_hi": 4.0}, dtype=object)
    assert chk.check_row(row, text) == "ok"
    moved = row.copy()
    moved["locator"] = "sentence #0"
    assert chk.check_row(moved, text) == "moved"
    bad = row.copy()
    bad["life_hi"] = 6.0
    assert chk.check_row(bad, text) == "number_not_in_sentence"
    gone = row.copy()
    gone["sentence_sha256"] = "b" * 64
    assert chk.check_row(gone, text) == "sentence_not_found"
    eff = pd.Series({"row_type": "effect", "effect_value": -3100.0, "effect_unit": "MUSD",
                     "locator": f"sentence #{k + 1}", "sentence_sha256": gc.sentence_hash(sents[k + 1])})
    assert chk.check_row(eff, text) == "ok"


def test_check_stop_absent_and_dates():
    row = pd.Series({"row_type": "stop", "locator": "absent", "asset_class": "servers"})
    assert chk.check_row(row, "We depreciate equipment. Buildings 30 years.") == "ok"
    assert chk.check_row(row, "Servers are depreciated over 6 years.") == "class_still_stated"
    assert chk.check_row(row, "It is three years for our servers and more.") == "class_still_stated"
    assert chk.check_row(row, "Servers and networking equipment Five to six years.") == "ok"
    net = pd.Series({"row_type": "stop", "locator": "absent", "asset_class": "networking equipment"})
    assert chk.check_row(net, "Servers and networking equipment Five to six years.") == "ok"
    assert chk.check_row(net, "Networking equipment Five to six years.") == "class_still_stated"
    r = pd.Series({"accession": "a", "filed": "2024-02-02", "accepted": "2024-02-01T21:30:00.000Z"})
    assert chk.check_dates(r, {"a": {"filed": "2024-02-02", "accepted": "2024-02-01T21:30:00.000Z"}}) == "ok"
    assert chk.check_dates(r, {"a": {"filed": "2024-02-03", "accepted": "x"}}).startswith("filed_differs")
    assert chk.check_dates(r, {}) == "accession_not_in_submissions"


def test_effect_patterns_eps():
    assert any(re.search(p, "or $0.06 per diluted share", re.I) for p in chk.effect_patterns(0.06, "USD per share"))
    assert any(re.search(p, "by $988 million", re.I) for p in chk.effect_patterns(-988, "MUSD"))


# ------------------------------------------------------------------ corpus

@pytest.mark.parametrize("sentence,expected", [
    ("We changed the estimated useful life of our servers from five to six years.", True),
    ("Servers and network assets 5.5 years Buildings 25 to 30 years", True),
    ("computer equipment, two to six years; buildings and improvements, five to 15 years", True),
    ("This change in estimate reduced depreciation expense by $1.2 billion.", True),
    ("Server products and cloud services revenue increased 22%.", False),
    ("We have been in business for twenty years.", False),
])
def test_is_candidate(sentence, expected):
    assert corpus.is_candidate(sentence) is expected


def test_parse_index_and_scope():
    page = ('<table><tr><td>1</td><td>Press release</td><td><a href="/Archives/edgar/data/1/2/ex991.htm">ex991.htm'
            '</a></td><td>EX-99.1</td></tr><tr><td>2</td><td></td><td><a href="/Archives/edgar/data/1/2/x.jpg">x</a>'
            '</td><td>GRAPHIC</td></tr></table>')
    assert corpus.parse_index(page) == [("EX-99.1", "https://www.sec.gov/Archives/edgar/data/1/2/ex991.htm")]
    f = {"form": "8-K", "items": "2.02,9.01", "filed": "2020-01-30"}
    assert corpus.in_scope(f) and not corpus.in_scope({**f, "items": "8.01"})
    assert corpus.in_scope({**f, "form": "10-Q/A", "items": ""}) and not corpus.in_scope({**f, "filed": "2017-12-29"})


def test_candidates_carry_document_fields():
    doc = corpus.Document("meta", "10-K", URL.format(folder="1"), "0000000001-22-000001", "2022-02-03",
                          "2022-02-02T21:00:00.000Z", "10-K", "", "2021-12-31")
    text = "Intro. Our servers and network assets have an estimated useful life of four years. Next."
    out = corpus.candidates(doc, text)
    assert len(out) == 1 and out[0]["k"] == 1 and out[0]["report_date"] == "2021-12-31"
    assert out[0]["sha256"] == hashlib.sha256(out[0]["sentence"].encode()).hexdigest()
