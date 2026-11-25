"""Fix track X19 after review R22 of Q1 (series/price_rolling.py; register "2026-11-25 – X19"): the median over the
valid successor candidates, the two added renames under display names, the version on month end + 1 and the floor
diagnostics. Fixtures only, no network."""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker.series import price_rolling as pr

T = pd.Timestamp


def board(published, ratings, evidence=None, source="release"):
    return (T(published), pd.Series(ratings, dtype=float), T(evidence or published), source, "test")


def snaps(rows):
    df = pd.DataFrame(rows, columns=["snapshot_date", "key", "provider", "input_per_m", "output_per_m"])
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    df["sha"] = df["snapshot_date"].dt.strftime("%Y%m%d")
    return df


def blend(i, o):
    return (3 * i + o) / 4


NAMES = ["a", "b", "c", "q1", "q2", "q3"]
PAIRS = pd.DataFrame([(n, f"k-{n}", "openai") for n in NAMES], columns=["name", "key", "provider"])
PRICES = [("2024-01-20", "k-a", "openai", 9.0, 9.0), ("2024-01-20", "k-b", "openai", 8.0, 8.0),
          ("2024-01-20", "k-c", "openai", 7.0, 7.0), ("2024-01-20", "k-q1", "openai", 3.0, 3.0),
          ("2024-01-20", "k-q2", "openai", 2.0, 2.0), ("2024-01-20", "k-q3", "openai", 1.0, 1.0)]


def build(boards, lag=6, last="2024-07", prices=PRICES, pairs=PAIRS, **kw):
    return pr.build(boards, snaps(prices), lag, pd.Period(last, "M"), pairs_at=lambda when: pairs, **kw)


# reference "top" (exp name) is gone in July; a, b and c are ranks 2-4 with offsets 10, 20 and 30
EARLY = [board(f"2024-01-{d:02d}", {"top": 1300, "a": 1290, "b": 1280, "c": 1270}) for d in (10, 12, 15, 20)]


# ------------------------------------------------------------------ median over the valid candidates (R22-3)

def test_threshold_is_the_median_over_the_valid_candidates():
    # implied thresholds: a 1300 + 10 = 1310, b 1290 + 20 = 1310, c 1340 + 30 = 1370 (c drifted up) -> median 1310
    now = board("2024-07-20", {"a": 1300, "b": 1290, "c": 1340, "q1": 1312, "q2": 1309, "q3": 1200})
    row = build(EARLY + [now]).iloc[-1]
    assert row["threshold"] == pytest.approx(1310.0) and row["via"] == "a, b, c" and row["n_successors"] == 3
    assert row["threshold_spread"] == pytest.approx(60.0)
    assert row["delta_from"] == T("2024-01-12") and row["delta_to"] == T("2024-01-20")  # the latest three boards
    assert row["key"] == "k-q1"  # q2 (1309) is below the median threshold


def test_an_outlier_first_candidate_no_longer_sets_the_threshold():
    # a (rank 2) implies 1270 + 10 = 1280, far below b and c (1310 and 1312): the first-candidate rule would let q2
    # (1290) qualify, the median (1310) does not
    now = board("2024-07-20", {"a": 1270, "b": 1290, "c": 1282, "q1": 1311, "q2": 1290, "q3": 1200})
    row = build(EARLY + [now]).iloc[-1]
    assert row["threshold"] == pytest.approx(1310.0) and row["key"] == "k-q1"


def test_even_number_of_candidates_takes_the_mean_of_the_middle_two():
    now = board("2024-07-20", {"a": 1300, "b": 1300, "q1": 1316, "q2": 1314})  # c absent: 1310 and 1320
    row = build(EARLY + [now]).iloc[-1]
    assert row["threshold"] == pytest.approx(1315.0) and row["via"] == "a, b" and row["key"] == "k-q1"


def test_reference_found_directly_has_no_successor_diagnostics():
    now = board("2024-07-20", {"top": 1320, "q1": 1321})
    row = build(EARLY + [now]).iloc[-1]
    assert row["via"] == "" and row["n_successors"] == 0 and pd.isna(row["delta_from"])
    assert row["threshold_spread"] == 0


def test_the_candidate_order_does_not_change_the_value():
    """The same three implied thresholds in another rank order give the same threshold and value."""
    early = [board(f"2024-01-{d:02d}", {"top": 1300, "c": 1290, "a": 1280, "b": 1270}) for d in (10, 12, 15, 20)]
    # implied: c 1300 + 10 = 1310, a 1290 + 20 = 1310, b 1340 + 30 = 1370 (b is now the drifting one)
    now = board("2024-07-20", {"c": 1300, "a": 1290, "b": 1340, "q1": 1312, "q2": 1309, "q3": 1200})
    row = build(early + [now]).iloc[-1]
    assert row["threshold"] == pytest.approx(1310.0) and row["via"] == "c, a, b" and row["key"] == "k-q1"


# ------------------------------------------------------------------ renames (R22-2)

def test_added_renames_and_display_names():
    assert pr.RENAMES["chatgpt-4o-latest"] == "chatgpt-4o-latest-20240808"
    assert pr.RENAMES["claude-opus-4-6-thinking"] == "claude-opus-4-6-high"
    # the renamed name under its display name (after the switch in 2026-10)
    assert pr.Lookup(pd.Series({"Claude Opus 4.6 (High)": 1501.7, "Claude Opus 4.6": 1496.3})) \
        .find("claude-opus-4-6-thinking") == "Claude Opus 4.6 (High)"
    # the old name itself wins over the rename; an ambiguous form gives no match
    assert pr.Lookup(pd.Series({"claude-opus-4-6-thinking": 1.0, "claude-opus-4-6-high": 2.0})) \
        .find("claude-opus-4-6-thinking") == "claude-opus-4-6-thinking"
    assert pr.Lookup(pd.Series({"Claude Opus 4.6 (High)": 1.0, "claude opus 4.6 high": 2.0})) \
        .find("claude-opus-4-6-thinking") is None


def test_reference_found_under_its_rename_needs_no_successor():
    ref = board("2024-01-20", {"claude-opus-4-6-thinking": 1300, "a": 1290})
    now = board("2024-07-20", {"claude-opus-4-6-high": 1305, "q1": 1306, "q2": 1304})
    row = build([ref, now]).iloc[-1]
    assert row["reference"] == "claude-opus-4-6-thinking" and row["via"] == "" and row["threshold"] == 1305
    assert row["key"] == "k-q1"


# ------------------------------------------------------------------ the version on month end + 1 (R22-1)

def test_month_end_board_documented_next_day_is_in_the_first_version_only():
    ref = board("2024-01-20", {"a": 1300, "b": 1200})
    boards = [ref, board("2024-07-10", {"a": 1300, "q3": 1200, "b": 1301}),
              board("2024-07-31", {"a": 1300, "q2": 1300}, evidence="2024-08-01"),
              board("2024-07-31", {"a": 1300, "q3": 1300}, evidence="2024-08-03")]
    t = build(boards)
    # one version per date: 2024-08-01 already uses the board documented that day; the later version of the same
    # board (documented 2024-08-03) adds its own version
    assert t["known_from"].tolist() == [T("2024-08-01"), T("2024-08-03")]
    assert t["key"].tolist() == ["k-q2", "k-q3"] and t["known_from"].is_unique


def test_board_documented_two_days_after_month_end_is_still_a_later_version():
    ref = board("2024-01-20", {"a": 1300, "b": 1200})
    boards = [ref, board("2024-07-10", {"a": 1300, "b": 1301}),
              board("2024-07-31", {"a": 1300, "q2": 1300}, evidence="2024-08-02")]
    t = build(boards)
    assert t["known_from"].tolist() == [T("2024-08-01"), T("2024-08-02")]
    assert t["key"].tolist() == ["k-b", "k-q2"]


# ------------------------------------------------------------------ floor diagnostics (R22-4 and section 7)

def test_floor_is_the_cheapest_mapped_priced_key_without_threshold():
    ref = board("2024-01-20", {"a": 1300, "b": 1200})
    now = board("2024-07-20", {"a": 1300, "b": 1305, "q3": 1100})
    row = build([ref, now]).iloc[-1]
    assert row["key"] == "k-b" and row["value"] == pytest.approx(8.0)
    assert row["floor"] == pytest.approx(blend(1.0, 1.0))  # q3 is below the threshold but sets the floor


def test_eci_table_has_the_floor():
    eci = pd.DataFrame({"model": ["A", "B", "C"], "organization": "x",
                        "release": pd.to_datetime(["2024-05-01", "2024-06-01", "2024-06-15"]),
                        "eci": [130.0, 131.0, 120.0]})
    gpqa = pd.DataFrame(columns=["version", "model", "organization", "release", "score", "known_from"])
    mapping = pd.DataFrame([("A", "k-a", "openai"), ("B", "k-b", "openai"), ("C", "k-c", "openai")],
                           columns=["model", "key", "provider"])
    prices = snaps([("2025-05-20", "k-a", "openai", 1.0, 1.0), ("2025-05-20", "k-b", "openai", 2.0, 2.0),
                    ("2025-05-20", "k-c", "openai", 0.5, 0.5)])
    m = pd.Period("2025-06", "M")
    t = pr.build_eci(prices, {"eci": eci, "gpqa": gpqa}, m, mapping=mapping)
    assert t.loc[m, "key"] == "k-b" and t.loc[m, "value"] == pytest.approx(2.0)
    assert t.loc[m, "floor"] == pytest.approx(0.5)  # C (ECI 120) is below the threshold but is the cheapest
