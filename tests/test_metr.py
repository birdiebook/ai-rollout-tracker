"""METR parser and the as-of frontier with update-log dates (fixtures, no network)."""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker.sources import metr

YAML = """
benchmark_name: METR-Horizon-v1.1
results:
  old_model:
    metrics: {p50_horizon_length: {estimate: 10.0}, is_sota: true}
    release_date: 2025-01-10
  claude_opus_4_6_inspect:
    metrics: {p50_horizon_length: {estimate: 700.0}, is_sota: true}
    release_date: 2026-02-05
  gpt_5_4:
    metrics: {p50_horizon_length: {estimate: 300.0}, is_sota: false}
    release_date: 2026-03-05
  new_top_inspect:
    metrics: {p50_horizon_length: {estimate: 1000.0}, is_sota: true}
    release_date: 2026-04-07
  no_metrics:
    release_date: 2026-04-07
"""

PAGE = """<h1 id="updates">Updates</h1><ul>
<li><strong>September 8th, 2026:</strong> Clarified that this page is no longer actively updated.</li>
<li><strong>May 8th, 2026:</strong> Added New Top and notice that &ldquo;Measurements above 16 hrs are unreliable&rdquo;</li>
<li><strong>April 10th, 2026:</strong> Added GPT-5.4.</li>
<li><strong>March 3rd, 2026:</strong> Corrected a regularization mistake.</li>
<li><strong>February 20th, 2026:</strong> Added Claude Opus 4.6 and GPT-5.3-Codex.</li>
<li><strong>August 6th, 2025:</strong> Added GPT-5, gpt-oss-120b, and Claude Opus 4.1</li>
</ul>"""


def test_parse_log_and_names():
    log = metr.parse_update_log(PAGE)
    assert log[0][0] == pd.Timestamp("2026-09-08") and len(log) == 6
    assert metr.added_names(log[1][1]) == ["New Top"]
    assert metr.added_names(log[4][1]) == ["Claude Opus 4.6", "GPT-5.3-Codex"]
    assert metr.added_names(log[5][1]) == ["GPT-5", "gpt-oss-120b", "Claude Opus 4.1"]
    assert metr.norm("claude_opus_4_6_inspect") == metr.norm("Claude Opus 4.6")


def test_known_from_is_log_date_but_not_before_correction():
    res = metr.parse_results(YAML)
    assert len(res) == 4  # model without metrics skipped
    kf = dict(zip(res["key"], metr.known_from_dates(res, metr.parse_update_log(PAGE))))
    assert kf["old_model"] == pd.Timestamp("2026-03-03")  # not in the log: present before the correction
    assert kf["claude_opus_4_6_inspect"] == pd.Timestamp("2026-03-03")  # added 02-20, corrected 03-03
    assert kf["gpt_5_4"] == pd.Timestamp("2026-04-10")
    assert kf["new_top_inspect"] == pd.Timestamp("2026-05-08")


def test_frontier_vintages_as_of():
    res = metr.parse_results(YAML)
    res["kf"] = metr.known_from_dates(res, metr.parse_update_log(PAGE))
    f = metr.frontier_vintages(res["release_date"], res["p50"], res["kf"])
    apr = f[f["period"] == "2026-04"]
    # before 05-08 the April frontier is the February model; New Top only from its publication date
    assert list(zip(apr["value"], apr["known_from"])) == [(700.0, pd.Timestamp("2026-05-01")),
                                                          (1000.0, pd.Timestamp("2026-05-08"))]
    jan = f[f["period"] == "2025-01"].iloc[0]
    assert (jan["value"], jan["known_from"]) == (10.0, pd.Timestamp("2026-03-03"))
    assert f["period"].iloc[-1] == "2026-04"  # ends at the last release month
    assert (f["known_from"] >= pd.PeriodIndex(f["period"], freq="M").end_time.normalize()).all()


def test_metr_spec_is_reference():
    from ai_tracker.series import metr as sm

    assert sm.SPECS[0].note.startswith("REFERENSSERIE")
    assert sm.SPECS[0].branch == "G1"


@pytest.mark.parametrize("text", ["Corrected a mistake.", "This page is now live!"])
def test_non_additions_have_no_names(text):
    assert metr.added_names(text) == []
