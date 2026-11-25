"""Review R22 of track Q1 (price at a rolling capability threshold, series/price_rolling.py).

Passing tests: registered properties that hold but had no test. Strict xfails: defects found by the review
(docs/granskning/r22-rorlig-troskel.md, R22-1 .. R22-5); each one flips to XPASS (and fails) when the defect is fixed,
so the test must then be turned into a normal test. Fixtures only, no network.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from ai_tracker.series import price_rolling as pr

T = pd.Timestamp
DOC = Path(__file__).resolve().parents[1] / "docs" / "kallor" / "g2_rorlig_troskel.md"


def board(published, ratings, evidence=None, source="release"):
    return (T(published), pd.Series(ratings, dtype=float), T(evidence or published), source, "test")


def snaps(rows):
    """rows: (snapshot_date, key, provider, input_per_m, output_per_m)."""
    df = pd.DataFrame(rows, columns=["snapshot_date", "key", "provider", "input_per_m", "output_per_m"])
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    df["sha"] = df["snapshot_date"].dt.strftime("%Y%m%d")
    return df


PAIRS = pd.DataFrame([("front", "k-front", "openai"), ("mid", "k-mid", "openai"), ("cheap", "k-cheap", "openai"),
                      ("weak", "k-weak", "openai")], columns=["name", "key", "provider"])
PRICES = [("2024-01-20", "k-front", "openai", 30.0, 60.0), ("2024-01-20", "k-mid", "openai", 3.0, 15.0),
          ("2024-01-20", "k-cheap", "openai", 1.0, 2.0), ("2024-01-20", "k-weak", "openai", 0.1, 0.2)]
REF = board("2024-01-20", {"front": 1250, "mid": 1200, "cheap": 1150, "weak": 1100})


def blend(i, o):
    return (3 * i + o) / 4


def build(boards, lag=6, last="2024-07", prices=PRICES, pairs=PAIRS, **kw):
    return pr.build(boards, snaps(prices), lag, pd.Period(last, "M"), pairs_at=lambda when: pairs, **kw)


def section(n: int) -> str:
    text = DOC.read_text(encoding="utf-8")
    m = re.search(rf"^## {n}\..*?(?=^## {n + 1}\.|\Z)", text, flags=re.M | re.S)
    assert m, f"section {n} missing in {DOC.name}"
    return m.group(0)


# ------------------------------------------------------------------ properties that hold (no test before R22)

def test_reference_tie_is_broken_by_name():
    ref = board("2024-01-20", {"b-top": 1250, "a-top": 1250, "mid": 1200})
    now = board("2024-07-20", {"a-top": 1300, "b-top": 1400, "mid": 1320, "cheap": 1350})
    row = build([ref, now]).iloc[0]
    assert row["reference"] == "a-top" and row["threshold"] == 1300  # alphabetical first of the tied pair


def test_successor_candidates_are_ranks_two_to_eleven_only():
    names = [f"n{i:02d}" for i in range(2, 13)]  # ranks 2..12 below the reference
    ratings = {"exp-top": 1300, **{n: 1290 - i for i, n in enumerate(names)}}
    early = [board(f"2024-01-{d:02d}", ratings) for d in (10, 12, 15, 20)]
    pairs = pd.concat([PAIRS, pd.DataFrame([("n12", "k-mid", "openai"), ("n11", "k-mid", "openai")],
                                           columns=PAIRS.columns)])
    # only rank 12 (n12) is left in July: outside the ten candidates -> a gap, no guess
    assert build(early + [board("2024-07-20", {"n12": 1400, "cheap": 1450})], pairs=pairs).empty
    # rank 11 (n11) is the tenth candidate and carries the threshold
    row = build(early + [board("2024-07-20", {"n11": 1400, "cheap": 1450})], pairs=pairs).iloc[0]
    assert row["via"] == "n11" and row["threshold"] == pytest.approx(1400 + 1300 - (1290 - 9))


def test_successor_overlap_never_counts_a_version_of_the_current_board():
    early = [board("2024-01-10", {"exp-top": 1250, "mid": 1240}), board("2024-01-12", {"exp-top": 1250, "mid": 1240})]
    v1 = board("2024-07-20", {"exp-top": 1300, "mid": 1290, "cheap": 1320})
    v2 = board("2024-07-20", {"mid": 1300, "cheap": 1320}, evidence="2024-07-25")  # same board, reference dropped
    # b(m) is v2; v1 is the same publish date, so only two earlier boards overlap -> no successor value
    assert build(early + [v1, v2]).empty


def test_bulk_only_current_board_is_backfill_for_rolling_and_frontier():
    now = board("2024-07-20", {"front": 1300, "mid": 1310}, evidence="2024-07-30", source="backfill")
    assert build([REF, now])["source"].tolist() == ["backfill"]
    front = build([board("2024-01-25", {"front": 1300, "mid": 1290}, source="backfill")], lag=0, last="2024-01")
    assert front["source"].tolist() == ["backfill"]


def test_reference_board_documented_after_month_end_gives_a_dated_version():
    # the reference month's last board is documented only on 2024-08-09 (after the end of m = 2024-07)
    late_ref = board("2024-01-28", {"newer": 1290, "front": 1250, "mid": 1200}, evidence="2024-08-09")
    now = board("2024-07-20", {"newer": 1330, "front": 1300, "mid": 1310, "cheap": 1300})
    pairs = pd.concat([PAIRS, pd.DataFrame([("newer", "k-newer", "openai")], columns=PAIRS.columns)])
    prices = PRICES + [("2024-01-20", "k-newer", "openai", 20.0, 20.0)]
    t = build([REF, late_ref, now], pairs=pairs, prices=prices)
    assert t["known_from"].tolist() == [T("2024-08-01"), T("2024-08-09")]
    assert t["reference"].tolist() == ["front", "newer"]  # never the later board before its evidence date
    assert t["ref_board"].tolist() == [T("2024-01-20"), T("2024-01-28")]


def test_eci_variant_drops_keys_retired_by_month_end():
    eci = pd.DataFrame({"model": ["A", "B"], "organization": "x",
                        "release": pd.to_datetime(["2024-05-01", "2024-06-01"]), "eci": [130.0, 131.0]})
    gpqa = pd.DataFrame(columns=["version", "model", "organization", "release", "score", "known_from"])
    mapping = pd.DataFrame([("A", "k-a", "openai"), ("B", "k-b", "openai")], columns=["model", "key", "provider"])
    prices = snaps([("2025-05-20", "k-a", "openai", 1.0, 1.0), ("2025-05-20", "k-b", "openai", 2.0, 2.0)])
    epoch = {"eci": eci, "gpqa": gpqa}
    m = pd.Period("2025-06", "M")
    assert pr.build_eci(prices, epoch, m, mapping=mapping).loc[m, "key"] == "k-b"  # B >= threshold (B, 131)
    prices_a = snaps([("2025-05-20", "k-a", "openai", 1.0, 1.0), ("2025-05-20", "k-b", "openai", 2.0, 2.0)])
    eci_a = eci.assign(eci=[131.0, 130.0])  # A is the frontier and the cheapest
    deps = pd.DataFrame({"sha": ["20250520"], "key": ["k-a"], "deprecation_date": [T("2025-06-15")]})
    t = pr.build_eci(prices_a, {"eci": eci_a, "gpqa": gpqa}, m, mapping=mapping, deprecations=deps)
    assert m not in t.index  # k-a retired by month end; k-b (130) is below the threshold 131


# ------------------------------------------------------------------ defects (strict xfail)

@pytest.mark.xfail(strict=True, reason="R22-1: a board published on the last day and documented the next day is "
                                       "never used for that month (the version day coincides with month end + 1)")
def test_month_end_board_documented_next_day_gives_a_version():
    boards = [REF, board("2024-07-10", {"front": 1300, "mid": 1310}),
              board("2024-07-31", {"front": 1300, "cheap": 1300}, evidence="2024-08-01")]
    t = build(boards)
    # vintages.py: a board published by month end but documented later adds a version on its evidence date
    assert t.iloc[-1]["board"] == T("2024-07-31") and t.iloc[-1]["key"] == "k-cheap"


@pytest.mark.xfail(strict=True, reason="R22-2: two observed renames without overlap are not in RENAMES "
                                       "(chatgpt-4o-latest 2024-09-04 -> chatgpt-4o-latest-20240808 2024-09-15, "
                                       "claude-opus-4-6-thinking 2026-08-11 -> claude-opus-4-6-high 2026-08-12)")
def test_observed_no_overlap_renames_are_found():
    assert pr.Lookup(pd.Series({"chatgpt-4o-latest-20240808": 1316.0})).find("chatgpt-4o-latest") \
        == "chatgpt-4o-latest-20240808"
    assert pr.Lookup(pd.Series({"claude-opus-4-6-high": 1502.8})).find("claude-opus-4-6-thinking") \
        == "claude-opus-4-6-high"


@pytest.mark.xfail(strict=True, reason="R22-3: the successor offset can be measured up to 359 days before b(m) "
                                       "and the table does not show its age")
def test_successor_offset_age_is_visible():
    early = [board(f"2024-01-{d:02d}", {"exp-top": 1250, "mid": 1240, "cheap": 1100}) for d in (10, 12, 15)]
    t = build(early + [board("2024-07-20", {"mid": 1300, "cheap": 1330})])
    assert "delta_from" in t.columns and t.iloc[0]["delta_from"] == T("2024-01-10")


@pytest.mark.xfail(strict=True, reason="R22-4: the level check (section 7) covers only the Arena variants; the ECI "
                                       "variant equals its floor in 7 of 18 months (2025-05 - 2025-11)")
def test_level_check_covers_the_eci_variant():
    assert "ECI" in section(7)


@pytest.mark.xfail(strict=True, reason="R22-5: caveat 5 says the successor error is not measured; R22 measured it "
                                       "(spread between valid candidates up to 25 points with year-old offsets)")
def test_successor_caveat_reports_the_measured_error():
    assert "inte mätt" not in section(9)
