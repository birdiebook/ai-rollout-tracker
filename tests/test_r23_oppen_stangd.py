"""Review R23 of track Q2 (open against closed weights and the China gap, G1): docs/granskning/r23-oppen-stangd.md.

Synthetic fixtures, no network. Passing tests pin properties that the review verified on real data. The tests for the
confirmed defects R23-1 to R23-3 were strict xfail; fix track X20 fixed them and removed the markers with the
assertions unchanged (tests/test_x20_oppen_stangd.py has the fix's own tests).
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import catalog
from ai_tracker.series import open_gap as og
from ai_tracker.sources import arena_meta as am
from ai_tracker.sources import model_origin as mo
from ai_tracker.sources import vintages

T = pd.Timestamp
US, CN = mo.US, mo.CHINA


def board(day, ratings, evidence=None, source="release"):
    return (T(day), pd.Series(ratings, dtype=float), T(evidence or day), source, "test")


def by_table(weights, orgs=None):
    orgs = orgs or {}

    def classify(name, _date):
        return weights.get(name), orgs.get(name), "test", "test"
    return classify


W = {f"c{i}": mo.CLOSED for i in range(5)} | {f"o{i}": mo.OPEN for i in range(3)}


def last_value(table, kind, column, period):
    rows = og.arena_series(table, kind, column)
    rows = rows[rows["period"] == period].sort_values("known_from")
    return rows.iloc[-1]


def _meta(rows):
    return pd.DataFrame(rows, columns=am.META_COLUMNS).assign(date=lambda d: pd.to_datetime(d["date"]))


# ------------------------------------------------------------------ R23-1 (must_fix): board documented on month end + 1

def test_last_day_board_documented_next_day_enters_its_month():
    # Real case: text 2026-09-30 (top gemini-4-argon-high), evidence 2026-10-01; the gap for 2026-09 stays at the
    # 2026-09-25 board's 27.06 instead of 42.58 (2026-04 likewise).
    boards = [
        board("2026-08-20", {"c1": 1500, "o1": 1450}, evidence="2026-08-21"),
        board("2026-09-25", {"c1": 1500, "c2": 1510, "o1": 1490}, evidence="2026-09-26"),
        board("2026-09-30", {"c1": 1500, "c2": 1510, "c3": 1530, "o1": 1490}, evidence="2026-10-01"),
    ]
    t = og.arena_build(boards, by_table(W), pd.Period("2026-09", "M"))
    assert last_value(t, "open", "gap", "2026-09")["value"] == pytest.approx(40)  # c3 1530 - o1 1490


def test_vintages_monthly_keeps_a_last_day_state_documented_next_day():
    ev = pd.DataFrame({"published": [T("2026-09-25"), T("2026-09-30")], "value": [1.0, 2.0],
                       "evidence": [T("2026-09-26"), T("2026-10-01")], "source": ["release", "release"]})
    rows = vintages.monthly(ev, pd.Period("2026-09", "M")).sort_values("known_from")
    assert rows.iloc[-1]["value"] == 2.0


def test_vintages_monthly_adds_a_version_for_evidence_two_days_after():
    # The defect is narrow: evidence on month end + 2 days or later does give a new version (holds today).
    ev = pd.DataFrame({"published": [T("2026-09-25"), T("2026-09-30")], "value": [1.0, 2.0],
                       "evidence": [T("2026-09-26"), T("2026-10-02")], "source": ["release", "release"]})
    rows = vintages.monthly(ev, pd.Period("2026-09", "M")).sort_values("known_from")
    assert list(rows["value"]) == [1.0, 2.0] and list(rows["known_from"]) == [T("2026-10-01"), T("2026-10-02")]
    boards = [board("2026-08-20", {"c1": 1500, "o1": 1450}),
              board("2026-09-25", {"c1": 1500, "c2": 1510, "o1": 1490}, evidence="2026-09-26"),
              board("2026-09-30", {"c1": 1500, "c2": 1510, "c3": 1530, "o1": 1490}, evidence="2026-10-02")]
    t = og.arena_build(boards, by_table(W), pd.Period("2026-09", "M"))
    assert last_value(t, "open", "gap", "2026-09")["value"] == pytest.approx(40)


# ------------------------------------------------------------------ R23-3 (should_fix): ECI open before the weights

def test_eci_model_with_weights_after_month_end_is_not_open_that_month():
    rows = pd.DataFrame([
        ("GPT-A", 160.3, "2026-03-05", "Closed weights", US),
        ("GPT-B", 162.8, "2026-04-23", "Closed weights", US),
        ("GPT-C", 169.2, "2026-09-03", "Closed weights", US),
        ("Kimi K3", 158.6, "2026-07-16", "Open weights", CN),
        ("Kimi K3.1 Pro", 161.2, "2026-10-23", "Open weights", CN),
    ], columns=["Model", "eci", "date", "Accessibility group", "Country (of organization)"])
    models = pd.DataFrame([("Kimi K3.1 Pro", "Yes", CN, "Kimi K3.1 Pro License (MIT-style). Weights released on "
                                                       "Hugging Face 2026-11-04; API since 2026-10-23.")],
                          columns=["Model", "Open model weights?", "Country (of organization)", "Accessibility notes"])
    t = og.eci_build(og.eci_frame(rows, models, {}), "open", pd.Period("2026-10", "M")).set_index("period")
    assert t.loc["2026-10", "follow_model"] == "Kimi K3"  # then lag 7 (GPT-A, 2026-03) and gap 10.6, not 6 and 8.0


# ------------------------------------------------------------------ properties that hold

def test_per_board_label_keeps_a_model_closed_until_its_weights_are_labelled_open():
    # Real case: minimax-m2.7 is "Proprietary" up to 2026-04-13 and MIT from 2026-04-14 in Arena's own rows.
    meta = _meta([
        ("m", "2026-04-10", "Proprietary", "minimax", 100, "dataset"),
        ("m", "2026-04-14", "MIT", "minimax", 120, "dataset"),
        ("c", "2026-04-10", "Proprietary", "openai", 900, "dataset"),
        ("c", "2026-04-14", "Proprietary", "openai", 950, "dataset"),
    ])
    clf = am.Classifier(meta, mo.Classes(), {})
    boards = og.norm_boards([board("2026-04-10", {"m": 1400, "c": 1450}), board("2026-04-14", {"m": 1400, "c": 1450})])
    g = og.board_groups(boards, clf.classify)
    assert g[0]["open"] == {"m": og.LEAD, "c": og.LEAD}  # no follower yet: the month has no open value
    assert g[1]["open"]["m"] == og.FOLLOW
    assert clf.classify("m", T("2026-04-12"))[:3] == (mo.CLOSED, "minimax", "earlier")  # never a later "open"


def test_frontier_is_chosen_in_b_s_and_read_in_b_m():
    # Feb's frontier is c2 (top of the Feb board), read in March at 1200 < 1250, so Feb does not reach even though c1
    # is higher in March. The order inside b(s) decides, the ratings come from b(m) only.
    boards = [board("2024-01-10", {"c0": 1000, "o1": 900}),
              board("2024-02-10", {"c0": 1000, "c1": 1050, "c2": 1100, "o1": 900}),
              board("2024-03-10", {"c0": 1000, "c1": 1300, "c2": 1200, "o1": 1250})]
    mar = og.arena_build(boards, by_table(W), pd.Period("2024-03", "M"))
    mar = mar[(mar["kind"] == "open") & (mar["period"] == "2024-03")].iloc[-1]
    assert mar["s_star"] == pd.Period("2024-03", "M") and mar["lag"] == 0 and mar["status"] == "lag"
    assert mar["reach_model"] == "c1" and mar["gap"] == pytest.approx(50)


def test_lag_is_backfill_when_b_s_star_is_bulk_only_and_gap_stays_release():
    boards = [board("2025-10-10", {"c0": 1000, "o1": 900}, evidence="2025-10-11"),
              board("2025-11-20", {"c0": 1000, "c1": 1100, "o1": 900}, evidence="2026-04-02", source="backfill"),
              board("2026-05-10", {"c0": 1000, "c1": 1100, "c2": 1200, "o1": 1050}, evidence="2026-05-11")]
    t = og.arena_build(boards, by_table(W), pd.Period("2026-05", "M"))
    lag = last_value(t, "open", "lag", "2026-05")
    gap = last_value(t, "open", "gap", "2026-05")
    assert lag["value"] == 6 and lag["source"] == "backfill"  # s* = 2025-11, a bulk-only board
    assert gap["source"] == "release"


def test_earlier_month_board_documented_later_changes_the_month_only_from_its_evidence():
    # b(Feb) for the March value is the Feb board known at the version cut-off: the late Feb board counts only from
    # its evidence day (2024-04-15), never before.
    boards = [board("2024-01-10", {"c0": 1000, "o1": 900}),
              board("2024-02-05", {"c0": 1000, "c1": 1020, "o1": 900}),
              board("2024-02-25", {"c0": 1000, "c1": 1020, "c2": 1100, "o1": 900}, evidence="2024-04-15",
                    source="backfill"),
              board("2024-03-10", {"c0": 1000, "c1": 1020, "c2": 1100, "c3": 1200, "o1": 1050})]
    t = og.arena_build(boards, by_table(W), pd.Period("2024-03", "M"))
    rows = og.arena_series(t, "open", "lag")
    mar = rows[rows["period"] == "2024-03"].sort_values("known_from")
    assert list(mar["known_from"]) == [T("2024-04-01"), T("2024-04-15")]
    assert list(mar["value"]) == [0.0, 1.0]  # first: Feb front c1 1020 < 1050; then the late Feb board's c2 1100
    assert list(mar["source"]) == ["release", "backfill"]


def test_eci_china_s0_is_the_first_non_chinese_model_of_any_weights_class():
    # As registered: s0 for the China measure is the first month with a non-Chinese model, open or closed. An open
    # model one month before the closed frontier is enough to leave the early months uncensored (real case: LLaMA-65B
    # 2023-02-24 before GPT-4 2023-03-14 gives China lags from 2023-09 that the doc calls lower bounds).
    rows = pd.DataFrame([
        ("LLaMA", 101.5, "2023-02-24", "Open weights", US),
        ("GPT-4", 121.6, "2023-03-14", "Closed weights", US),
        ("Qwen", 101.8, "2023-09-25", "Open weights", CN),
    ], columns=["Model", "eci", "date", "Accessibility group", "Country (of organization)"])
    f = og.eci_frame(rows, None, {})
    china = og.eci_build(f, "china", pd.Period("2023-09", "M")).set_index("period")
    assert china.loc["2023-09", "lag"] == 6 and china.loc["2023-09", "s_star"] == "2023-03"
    opn = og.eci_build(f, "open", pd.Period("2023-09", "M")).set_index("period")
    assert opn.loc["2023-09", "status"] == "censored"  # the open measure's s0 is GPT-4's month


def test_eci_series_are_backfill_dated_month_end_plus_seven():
    specs = catalog.by_key()
    for key in ("g1_open_lag_months_eci", "g1_open_gap_eci", "g1_china_lag_months_eci", "g1_china_gap_eci"):
        s = specs[key]
        assert s.lag_days == 7 and s.revised and s.freq == "M"
    for key in ("g1_open_lag_months_arena", "g1_china_gap_arena"):
        assert specs[key].lag_days == 1

