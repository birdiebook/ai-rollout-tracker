"""R8 review of the G2A Arena price series (docs/granskning/r8_g2_arena.md). Fixtures only, no network.

Pins two properties the review relies on; the third test (dataset evidence date, finding F-4a) was a strict xfail
until correction track X5 fixed it (R-1).
"""

from __future__ import annotations

import pandas as pd
from ai_tracker.series import arena_price as ap
from ai_tracker.sources import arena

T = pd.Timestamp
CHAIN = (("ref", "Ref"), ("succ", "Succ"))
PAIRS = pd.DataFrame([("ref", "k-ref", "openai"), ("cheap", "k-cheap", "openai")], columns=["name", "key", "provider"])


def _snaps(rows):
    df = pd.DataFrame(rows, columns=["snapshot_date", "key", "provider", "input_per_m", "output_per_m"])
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    df["sha"] = df["snapshot_date"].dt.strftime("%Y%m%d")
    return df


def test_deprecation_date_added_after_month_end_does_not_change_that_month():
    """A deprecation date that LiteLLM adds only after month end (even if the date itself lies before it) must not
    remove the key from that month: only the month-end snapshot's metadata counts (no look-ahead)."""
    boards = [(T("2024-01-20"), pd.Series({"ref": 1200.0, "cheap": 1201.0}), T("2024-01-20"), "release", "t")]
    s = _snaps([("2024-01-31", "k-ref", "openai", 30.0, 60.0), ("2024-01-31", "k-cheap", "openai", 1.0, 4.0),
                ("2024-02-20", "k-ref", "openai", 30.0, 60.0), ("2024-02-20", "k-cheap", "openai", 1.0, 4.0)])
    deps = pd.DataFrame({"snapshot_date": pd.to_datetime(["2024-01-31", "2024-02-20"]),
                         "sha": ["20240131", "20240220"], "key": ["", "k-cheap"],
                         "deprecation_date": pd.to_datetime([pd.NaT, "2024-01-15"])})
    t = ap.build(boards, s, CHAIN, pd.Period("2024-02", "M"), pairs_at=lambda when: PAIRS, deprecations=deps)
    assert t.set_index("period")["key"].to_dict() == {"2024-01": "k-cheap", "2024-02": "k-ref"}


def test_series_value_is_month_end_price_even_when_a_later_board_adds_a_vintage():
    """A board documented after month end changes the board, never the month-end price."""
    boards = [(T("2024-01-10"), pd.Series({"ref": 1200.0}), T("2024-01-10"), "release", "t"),
              (T("2024-01-25"), pd.Series({"ref": 1200.0, "cheap": 1210.0}), T("2024-02-10"), "release", "t")]
    s = _snaps([("2024-01-31", "k-ref", "openai", 30.0, 60.0), ("2024-01-31", "k-cheap", "openai", 1.0, 4.0),
                ("2024-02-05", "k-cheap", "openai", 0.1, 0.1)])
    t = ap.build(boards, s, CHAIN, pd.Period("2024-01", "M"), pairs_at=lambda when: PAIRS)
    assert list(t["known_from"]) == [T("2024-02-01"), T("2024-02-10")]
    assert list(t["value"]) == [37.5, 1.75]  # 2024-02-05 price cut is not used for January


def test_reuploaded_board_is_dated_by_the_commit_that_holds_the_values_used():
    log = ("2026-07-07T23:19:30+00:00|Update text for 2026-06-10\n"
           "2026-06-11T04:00:00+00:00|Update text for 2026-06-10\n")
    assert arena.parse_dataset_log(log)[("text", "2026-06-10")] == T("2026-07-07")
