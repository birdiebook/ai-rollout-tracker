"""Fix track X8 after review R11 of F1 (docs/granskning/r11_revideringar.md): break statements, the numeric-only
sensitivity, TSMC's US$ sensitivity, Meta's surprise start, the widened candidate rule and the publish gate.
Synthetic fixtures and the committed curated CSV only, no network.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from ai_tracker import catalog, guidance_check
from ai_tracker.series import guidance_revisions as GR
from ai_tracker.sources import guidance_capex
from ai_tracker.sources import tsmc_usd_revenue as TU
from ai_tracker.state import expectations as E
from tests.test_guidance_revisions import _world, csv_rows, obs


@pytest.fixture
def from_2016(monkeypatch):
    monkeypatch.setattr(GR, "COVERAGE_FROM", pd.Period("2016Q1", "Q-DEC"))


# ------------------------------------------------------------------ R11-1: breaks


MSFT_ROWS = [{"id": "m-1", "company": "msft", "kind": "approx", "lo": 190, "definition": "MSFT_CAPEX_INCL_FL",
              "period": "2026", "filed": "2026-04-29"},
             {"id": "m-2", "company": "msft", "kind": "approx", "lo": 175, "definition": "MSFT_CAPEX_INCL_FL",
              "period": "2026", "filed": "2026-07-29"},
             {"id": "m-3", "company": "msft", "kind": "approx", "lo": 170, "definition": "MSFT_CAPEX_INCL_FL",
              "period": "2026", "filed": "2026-10-28"}]


def test_a_break_row_is_reported_with_its_size_and_the_next_row_is_a_revision(monkeypatch):
    monkeypatch.setattr(GR, "DEFINITION_BREAKS", {"m-2": "test break"})
    st = GR.statements(None, csv_rows(MSFT_ROWS))
    ev = GR.events(st)
    assert list(ev["ref"]) == ["m-3"] and ev["prev_ref"].iloc[0] == "m-2" and ev["direction"].iloc[0] == -1
    assert ev["size"].iloc[0] == pytest.approx(100 * math.log(170 / 175))
    b = GR.break_statements(st)
    assert list(b["ref"]) == ["m-2"] and b["prev_ref"].iloc[0] == "m-1"
    assert b["size"].iloc[0] == pytest.approx(100 * math.log(175 / 190)) and b["reason"].iloc[0] == "test break"


def test_a_break_without_an_earlier_statement_has_no_size(monkeypatch):
    monkeypatch.setattr(GR, "DEFINITION_BREAKS", {"m-1": "first row"})
    b = GR.break_statements(GR.statements(None, csv_rows(MSFT_ROWS)))
    assert list(b["ref"]) == ["m-1"] and b["prev_ref"].iloc[0] is None and np.isnan(b["size"].iloc[0])


def test_the_registered_break_on_the_curated_csv():
    if not guidance_capex.PATH.exists():
        pytest.skip("curated CSV missing")
    st = GR.statements(None, guidance_capex.load())
    b = GR.break_statements(st)
    assert list(b["ref"]) == ["msft-r11f1"] and b["prev_ref"].iloc[0] == "msft-26"
    assert b["size"].iloc[0] == pytest.approx(100 * math.log(175 / 190))
    ev = GR.events(st)
    m = ev[(ev["company"] == "msft") & (ev["period"] == "CY:2026")]
    assert list(m["ref"]) == ["msft-29"]  # the break row itself is no revision


# ------------------------------------------------------------------ R11-6: numeric-only sensitivity


def test_numeric_only_index_leaves_out_direction_chains(from_2016):
    ev = GR.events(GR.statements(None, csv_rows([
        {"lo": 100, "hi": 110, "filed": "2025-01-29"}, {"lo": 110, "hi": 120, "filed": "2025-02-20"},
        {"lo": 120, "hi": 130, "filed": "2025-03-10"}, {"lo": 130, "hi": 140, "filed": "2025-03-25"},
        {"period": "2026", "kind": "direction", "code": 1, "filed": "2025-01-29"},
        {"period": "2026", "kind": "direction", "code": 1, "filed": "2025-02-20"},
        {"period": "2026", "kind": "direction", "code": 1, "filed": "2025-03-10"}])))
    num = GR.numeric_only(ev)
    assert set(num["chain"]) == {"num"} and len(num) == 3 and len(ev) == 5
    main = GR.revision_index(ev, 1, "2025-04-15", start=pd.Period("2025Q1", "Q-DEC")).iloc[-1]
    only = GR.revision_index(num, 1, "2025-04-15", start=pd.Period("2025Q1", "Q-DEC")).iloc[-1]
    assert main["index"] == pytest.approx((3 + 0.5 * 2) / 5) and only["index"] == pytest.approx(1.0)


# ------------------------------------------------------------------ R11-7: TSMC in US$


def test_usd_revenue_sentence_parse():
    text = ("Hsinchu, Taiwan. TSMC today announced consolidated revenue of NT$262.23 billion. In US dollars, fourth "
            "quarter revenue was $8.25 billion, which increased 32.9% year-over-year. In US dollar terms revenue grew.")
    recs = TU.parse(text, "2017-01-12")
    assert len(recs) == 1 and recs[0]["period"] == "2016Q4" and recs[0]["value"] == pytest.approx(8250.0)
    assert len(recs[0]["sentence_sha256"]) == 64
    assert TU.parse("In US dollars, third quarter revenue was US$46.72 billion", "2026-10-15")[0]["period"] == "2026Q3"
    assert TU.reported_quarter("2026-04-16", 1) == pd.Period("2026Q1", "Q-DEC")
    assert TU.parse("Third quarter revenue was $9.40 billion.", "2019-10-17") == []


def _usd_table(periods, outcomes, out_kf, lo, hi, g_kf):
    return pd.concat([obs("tsmc_rev_usd_q", "Q", periods, outcomes, out_kf),
                      obs("tsmc_guid_rev_usd_lo", "Q", periods, lo, g_kf),
                      obs("tsmc_guid_rev_usd_hi", "Q", periods, hi, g_kf)], ignore_index=True)


def test_usd_surprise_and_fx_part():
    t = _usd_table(["2017Q2", "2017Q3", "2017Q4"], [7000.0, 8320.0, 9210.0],
                   ["2017-07-13", "2017-10-19", "2018-01-18"], [6900.0, 8150.0, 9000.0], [7000.0, 8250.0, 9100.0],
                   ["2017-04-13", "2017-07-13", "2017-10-19"])
    ntd = pd.DataFrame({"company": "tsmc", "period": ["2017Q3", "2017Q4"], "s": [3.0, 1.0]})
    u = GR.tsmc_usd_surprises(t, ntd)
    assert list(u["period"]) == ["2017Q3", "2017Q4"]  # US$ guidance from 2017Q3 only
    r = u.iloc[0]
    assert r["s"] == pytest.approx(100 * math.log(8320 / 8200)) and r["fx"] == pytest.approx(3.0 - r["s"])
    assert (u["guidance_known_from"] < u["outcome_known_from"]).all()
    # guidance first known on the outcome day is not used
    late = t.copy()
    late.loc[late["series"].str.startswith("tsmc_guid") & (late["period"] == "2017Q4"), "known_from"] = \
        pd.Timestamp("2018-01-18")
    assert list(GR.tsmc_usd_surprises(late, ntd)["period"]) == ["2017Q3"]


def test_usd_sensitivity_is_not_in_the_surprise_index():
    table, csv = _world()
    out = GR.compute(table, csv, "2020-06-30")
    assert "tsmc_usd" not in set(out["surprises"]["company"]) and "surprises_tsmc_usd" in out


# ------------------------------------------------------------------ R11-5: Meta's 2020 rows


def test_meta_2020_rows_count_as_revisions_but_the_surprise_starts_in_2021_as_registered():
    csv = csv_rows([{"period": "2020", "kind": "approx", "lo": 16000, "filed": "2020-07-30"},
                    {"period": "2020", "kind": "approx", "lo": 16000, "filed": "2020-10-29"},
                    {"period": "2021", "lo": 21000, "hi": 23000, "filed": "2020-10-29"}])
    q = [f"{y}Q{k}" for y in (2020, 2021) for k in (1, 2, 3, 4)]
    kf = [pd.Period(p, "Q-DEC").end_time.normalize() + pd.Timedelta(days=30) for p in q]
    t = pd.concat([obs("capex_meta", "Q", q, [4000.0] * 8, kf), obs("fin_lease_meta", "Q", q, [100.0] * 8, kf)],
                  ignore_index=True)
    ev = GR.events(GR.statements(None, csv))
    assert list(ev["period"]) == ["CY:2020"] and ev["direction"].iloc[0] == 0
    s = GR.surprises(t, csv)
    assert list(s.loc[s["company"] == "meta", "period"]) == ["2021"]


# ------------------------------------------------------------------ R11-1: widened candidate rule


SENTS = ["Outside of this useful life impact, our calendar year 2026 CapEx investment expectations remain unchanged.",
         "However, the shift from finance to operating leases adjusts our expectation to approximately $175 billion.",
         "Now, moving to our outlook.", "Cash paid for P, P, and E was $5.3 billion."]


def test_the_sentence_after_a_capex_sentence_is_a_candidate():
    c = guidance_capex.candidates(SENTS)
    assert c[0] == "capex" and c[1] == "next" and 2 not in c and 3 not in c
    assert guidance_check.uncoded_next_sentences(SENTS, set(), set()) == [1]
    assert guidance_check.uncoded_next_sentences(SENTS, {1}, set()) == []
    sha = guidance_capex.sentence_hash(SENTS[1])
    assert guidance_check.uncoded_next_sentences(SENTS, set(), {sha}) == []


def test_neighbour_check_reads_each_document_once_and_reports_hits():
    csv = csv_rows([{"id": "x", "lo": 1, "hi": 2, "filed": "2026-07-29"}])
    csv["source_url"], csv["locator"], csv["sentence_sha256"] = "https://example.org/a", "sentence #0", "0" * 64
    calls = []
    res = guidance_check.neighbour_check(csv, fetch=lambda u: calls.append(u) or " ".join(SENTS))
    assert calls == ["https://example.org/a"]
    assert list(res["status"]) == ["read"] and int(res["sentence"].iloc[0]) == 1


# ------------------------------------------------------------------ R11-4 and the new series


def test_new_series_and_the_publish_gate():
    specs = catalog.by_key()
    usd = specs["tsmc_rev_usd_q"]
    assert usd.publish and usd.freq == "Q" and not usd.components
    s = specs["f1_surprise_tsmc_usd"]
    assert s.publish and "tsmc_rev_usd_q" in s.components
    for key in GR.CSV_BASED:
        assert not specs[key].publish and set(GR.csv_component_keys()) <= set(specs[key].components)
    assert catalog.validate() == []


def test_section_reports_the_sensitivities(from_2016):
    table, csv = _world()
    sec = E.section("2019-12-31", table, csv)
    assert set(sec["revisions_numeric_only"]) == {"window_1q", "window_4q"}
    comp = sec["composition_main_window"]
    main = sec["revisions"]["window_4q"]["latest"]
    assert comp["period"] == main["period"]
    assert comp["numbers"]["n"] + comp["directions"]["n"] == main["n"]
    assert comp["numbers"]["up"] + comp["directions"]["up"] == main["n_up"]
    assert sec["break_statements"] == [] and "tsmc_usd_sensitivity" in sec["surprise"]
