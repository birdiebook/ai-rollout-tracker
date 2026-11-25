"""Fix track X20 after review R23 of Q2 (docs/granskning/r23-oppen-stangd.md). Synthetic fixtures, no network.

Register 2026-11-25, X20: the first version of a month counts states documented by month end + 1 day (R23-1, R23-2),
and an open ECI model is open from its documented weights release, closed before (R23-3).
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker.series import open_gap as og
from ai_tracker.sources import model_origin as mo
from ai_tracker.sources import vintages

T = pd.Timestamp
US, CN = mo.US, mo.CHINA
W = {f"c{i}": mo.CLOSED for i in range(5)} | {f"o{i}": mo.OPEN for i in range(3)}


def board(day, ratings, evidence=None, source="release"):
    return (T(day), pd.Series(ratings, dtype=float), T(evidence or day), source, "test")


def classify(name, _date):
    return W.get(name), None, "test", "test"


def eci_rows(rows):
    return pd.DataFrame(rows, columns=["Model", "eci", "date", "Accessibility group", "Country (of organization)"])


def notes(rows):
    return pd.DataFrame(rows, columns=["Model", "Open model weights?", "Country (of organization)",
                                       "Accessibility notes"])


# ------------------------------------------------------------------ R23-1, R23-2: cut-off of the first version

def test_vintages_last_day_state_documented_next_day_is_the_first_version():
    ev = pd.DataFrame({"published": [T("2026-09-25"), T("2026-09-30")], "value": [1.0, 2.0],
                       "evidence": [T("2026-09-26"), T("2026-10-01")], "source": ["release", "backfill"]})
    rows = vintages.monthly(ev, pd.Period("2026-10", "M"))
    sep = rows[rows["period"] == "2026-09"]
    # one row, not two on the same day: the first version already knows the state documented on month end + 1
    assert list(sep["value"]) == [2.0] and list(sep["known_from"]) == [T("2026-10-01")]
    assert list(sep["source"]) == ["backfill"]
    assert not rows.duplicated(["period", "known_from"]).any()


def test_vintages_month_whose_only_state_is_documented_next_day_gets_a_row():
    # Before X20 the base day was evaluated with cut-off month end and the month had no row at all.
    ev = pd.DataFrame({"published": [T("2026-09-30")], "value": [5.0], "evidence": [T("2026-10-01")],
                       "source": ["release"]})
    rows = vintages.monthly(ev, pd.Period("2026-09", "M"))
    assert list(rows["period"]) == ["2026-09"] and rows["known_from"].iloc[0] == T("2026-10-01")


def test_vintages_state_documented_on_the_second_day_still_waits_for_its_evidence():
    ev = pd.DataFrame({"published": [T("2026-09-25"), T("2026-09-30")], "value": [1.0, 2.0],
                       "evidence": [T("2026-09-26"), T("2026-10-02")], "source": ["release", "release"]})
    rows = vintages.monthly(ev, pd.Period("2026-09", "M"))
    assert list(rows["value"]) == [1.0, 2.0] and list(rows["known_from"]) == [T("2026-10-01"), T("2026-10-02")]


def test_arena_build_last_day_board_is_in_the_first_version_with_month_end_plus_one():
    boards = [board("2026-08-20", {"c1": 1500, "o1": 1450}, evidence="2026-08-21"),
              board("2026-09-25", {"c1": 1500, "c2": 1510, "o1": 1490}, evidence="2026-09-26"),
              board("2026-09-30", {"c1": 1500, "c2": 1510, "c3": 1530, "o1": 1490}, evidence="2026-10-01")]
    t = og.arena_build(boards, classify, pd.Period("2026-09", "M"))
    gap = og.arena_series(t, "open", "gap")
    sep = gap[gap["period"] == "2026-09"]
    assert list(sep["value"]) == [pytest.approx(40)] and list(sep["known_from"]) == [T("2026-10-01")]
    sep_t = t[(t["kind"] == "open") & (t["period"] == "2026-09")]
    assert set(sep_t["board"]) == {T("2026-09-30")}  # never a version on the 09-25 board


# ------------------------------------------------------------------ R23-3: weights release in Epoch's notes

@pytest.mark.parametrize("note, expected", [
    ("Weights released on Hugging Face 2026-11-04; API since 2026-10-23.", "2026-11-04"),
    ("Full weights were released with OpenMDW-1.1 license on June 4, 2026.", "2026-06-04"),  # "1.1" is no sentence end
    ("Weights released 4 March 2024.", "2024-03-04"),
    ("Weights were released later, on Sept 4, 2026.", "2026-09-04"),
    ("Weights will be released on 2026-12-01.", mo.PENDING),  # a promised date is not a release
    ('"The model weights of GLM-5.3 will be publicly available soon in two weeks." (as of 2026/08/14).', mo.PENDING),
    ("MIT license for weights", None),
    ("Only the Nano model was released on 2025-12-15. Weights for the rest: TBD.", None),  # date not in a weights sentence
    (None, None),
    ("", None),
])
def test_weights_release_reads_a_past_tense_weights_sentence(note, expected):
    assert mo.weights_release(note) == expected


def test_eci_frame_release_steps():
    rows = eci_rows([("A", 150, "2026-10-23", "Open weights", CN), ("B", 140, "2026-08-14", "Open weights", CN),
                     ("C", 130, "2026-06-04", "Open weights", US), ("D", 120, "2026-05-01", "Open weights", CN),
                     ("E", 160, "2026-05-01", "Closed weights", US)])
    am_ = notes([("A", "Yes", CN, "Weights released on Hugging Face 2026-11-04; API since 2026-10-23."),
                 ("B", "Yes", CN, '"The model weights will be publicly available soon." (as of 2026/08/14).'),
                 ("C", "Yes", US, "Full weights were released on June 4, 2026."),
                 ("D", "Yes", CN, '"The weights will be released soon."')])
    f = og.eci_frame(rows, am_, {}, releases={"D": ("2026-05-20", "ref")}).set_index("model")
    assert f.loc["A", "open_from"] == T("2026-11-04") and f.loc["A", "step_release"] == "note"
    assert pd.isna(f.loc["B", "weights"]) and f.loc["B", "step_weights"] == "pending_release"
    assert bool(f.loc["B", "chinese"])  # still in the China measure
    assert f.loc["C", "open_from"] == T("2026-06-04") and f.loc["C", "step_release"] == "note"
    assert f.loc["D", "open_from"] == T("2026-05-20") and f.loc["D", "step_release"] == "curated"  # table wins
    assert pd.isna(f.loc["E", "open_from"]) and f.loc["E", "step_release"] == ""


def test_eci_release_before_date_keeps_the_date():
    rows = eci_rows([("A", 150, "2026-10-23", "Open weights", CN)])
    am_ = notes([("A", "Yes", CN, "Weights released on 2026-10-01.")])
    assert og.eci_frame(rows, am_, {}).loc[0, "open_from"] == T("2026-10-23")


def test_eci_model_counts_as_closed_until_its_weights_are_released():
    # P is the best model of all in 2026-10 but only API: it is the closed top that month, the open top from 2026-11.
    rows = eci_rows([("C", 100, "2026-01-10", "Closed weights", US), ("O", 90, "2026-02-10", "Open weights", CN),
                     ("C2", 105, "2026-06-10", "Closed weights", US), ("P", 110, "2026-10-23", "Open weights", CN)])
    am_ = notes([("P", "Yes", CN, "Weights released on Hugging Face 2026-11-04; API since 2026-10-23.")])
    f = og.eci_frame(rows, am_, {})
    t = og.eci_build(f, "open", pd.Period("2026-11", "M")).set_index("period")
    assert t.loc["2026-10", "lead_model"] == "P" and t.loc["2026-10", "follow_model"] == "O"
    assert t.loc["2026-10", "gap"] == pytest.approx(20)
    assert t.loc["2026-11", "follow_model"] == "P" and t.loc["2026-11", "lead_model"] == "C2"
    assert t.loc["2026-11", "lag"] == 0 and t.loc["2026-11", "status"] == "leads"
    china = og.eci_build(f, "china", pd.Period("2026-11", "M")).set_index("period")
    assert china.loc["2026-10", "follow_model"] == "P"  # the country does not wait for the weights


def test_eci_pending_release_without_date_is_left_out_of_open_measure_only():
    rows = eci_rows([("C", 100, "2026-01-10", "Closed weights", US), ("O", 90, "2026-02-10", "Open weights", CN),
                     ("G", 99, "2026-08-14", "Open weights", CN)])
    am_ = notes([("G", "Yes", CN, '"The model weights will be publicly available soon in two weeks."')])
    f = og.eci_frame(rows, am_, {}, releases={})
    t = og.eci_build(f, "open", pd.Period("2026-08", "M")).set_index("period")
    assert t.loc["2026-08", "follow_model"] == "O" and t.loc["2026-08", "lead_model"] == "C"
    c = og.eci_build(f, "china", pd.Period("2026-08", "M")).set_index("period")
    assert c.loc["2026-08", "follow_model"] == "G"


def test_curated_weights_release_rows_have_a_reference_and_a_date():
    for model, (day, ref) in mo.ECI_WEIGHTS_RELEASE.items():
        assert T(day) == T(day).normalize() and len(ref) > 40, model


# ------------------------------------------------------------------ R23-9: Epoch's organization strings

def test_org_country_quotes_epochs_spelling():
    assert "'Nous Research'" in mo.ORG_COUNTRY["nousresearch"][1]
    assert "'Nvidia'" in mo.ORG_COUNTRY["nvidia"][1]
