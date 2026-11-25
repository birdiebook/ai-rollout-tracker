"""Q1: price at a rolling capability threshold. Threshold within one board, missing reference, name forms, dating,
as_of truncation, frontier price and the ECI variant. Fixtures only, no network."""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import catalog, licenses, observations
from ai_tracker.series import price_rolling as pr

T = pd.Timestamp


def board(published, ratings, evidence=None, source="release"):
    return (T(published), pd.Series(ratings, dtype=float), T(evidence or published), source, "test")


def snaps(rows):
    """rows: (snapshot_date, key, provider, input_per_m, output_per_m)."""
    df = pd.DataFrame(rows, columns=["snapshot_date", "key", "provider", "input_per_m", "output_per_m"])
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    df["sha"] = df["snapshot_date"].dt.strftime("%Y%m%d")
    return df


PAIRS = pd.DataFrame([("front", "k-front", "openai"), ("mid", "k-mid", "openai"), ("mid-high", "k-mid", "openai"),
                      ("cheap", "k-cheap", "openai"), ("weak", "k-weak", "openai")],
                     columns=["name", "key", "provider"])
PRICES = [("2024-01-20", "k-front", "openai", 30.0, 60.0), ("2024-01-20", "k-mid", "openai", 3.0, 15.0),
          ("2024-01-20", "k-cheap", "openai", 1.0, 2.0), ("2024-01-20", "k-weak", "openai", 0.1, 0.2)]


def blend(i, o):
    return (3 * i + o) / 4


def build(boards, lag=6, last="2024-07", prices=PRICES, pairs=PAIRS, **kw):
    return pr.build(boards, snaps(prices), lag, pd.Period(last, "M"), pairs_at=lambda when: pairs, **kw)


# reference board for 2024-07 with L = 6: the latest board published by 2024-01-31; its top is "front"
REF = board("2024-01-20", {"front": 1250, "mid": 1200, "cheap": 1150, "weak": 1100})


# ------------------------------------------------------------------ threshold within one board

def test_reference_is_the_top_of_the_board_for_m_minus_l_and_its_rating_in_the_current_board():
    now = board("2024-07-20", {"front": 1300, "mid": 1290, "mid-high": 1305, "cheap": 1299.9, "new-top": 1400})
    t = build([REF, now])
    row = t[t["period"] == "2024-07"].iloc[0]
    assert row["reference"] == "front" and row["via"] == ""
    assert row["threshold"] == 1300  # front's rating in the July board, not in the January board
    # k-mid qualifies through its best variant (mid-high 1305); cheap (1299.9) does not; new-top is unmapped
    assert row["key"] == "k-mid" and row["name"] == "mid-high"
    assert row["value"] == pytest.approx(blend(3.0, 15.0))
    assert row["board"] == T("2024-07-20") and row["ref_board"] == T("2024-01-20")


def test_scale_shift_in_the_current_board_cancels():
    ratings = {"front": 1300, "mid": 1300, "cheap": 1250}
    a = build([REF, board("2024-07-20", ratings)])
    b = build([REF, board("2024-07-20", {k: v + 180 for k, v in ratings.items()})])
    assert a["value"].tolist() == b["value"].tolist()
    assert a.iloc[-1]["key"] == "k-mid"  # equal to the threshold qualifies (inclusive)


def test_first_month_is_first_bt_month_plus_lag():
    boards = [REF, board("2024-07-20", {"front": 1300, "cheap": 1310})]
    assert build(boards, lag=6, last="2024-07")["period"].tolist() == ["2024-07"]
    assert build(boards, lag=12, last="2024-12").empty  # first month with L = 12 is 2025-01


def test_threshold_binds_by_construction_as_the_frontier_moves():
    """The reference moves with the frontier: a model that cleared last half-year's frontier may not clear the next."""
    boards = [REF, board("2024-02-20", {"front": 1250, "next": 1290, "mid": 1200, "cheap": 1150}),
              board("2024-07-20", {"front": 1300, "next": 1340, "mid": 1300, "cheap": 1280}),
              board("2024-08-20", {"front": 1300, "next": 1340, "mid": 1300, "cheap": 1280})]
    pairs = pd.concat([PAIRS, pd.DataFrame([("next", "k-next", "openai")], columns=PAIRS.columns)])
    prices = PRICES + [("2024-01-20", "k-next", "openai", 10.0, 30.0)]
    t = build(boards, last="2024-08", pairs=pairs, prices=prices)
    by = t.set_index("period")
    assert by.loc["2024-07", "reference"] == "front" and by.loc["2024-07", "key"] == "k-mid"
    assert by.loc["2024-08", "reference"] == "next" and by.loc["2024-08", "key"] == "k-next"


# ------------------------------------------------------------------ missing reference

def test_missing_reference_uses_the_next_model_of_the_reference_board_with_overlap_offset():
    # exp-top is the reference (top of the January board) but is gone in July; "mid" is next and overlaps 4 times
    early = [board(f"2024-01-{d:02d}", {"exp-top": 1250, "mid": 1250 - diff, "cheap": 1100})
             for d, diff in ((10, 10), (12, 20), (15, 30), (20, 40))]
    now = board("2024-07-20", {"mid": 1300, "cheap": 1330, "weak": 1320})
    row = build(early + [now]).iloc[-1]
    # median of the latest three differences (20, 30, 40) = 30 -> threshold 1330
    assert row["threshold"] == pytest.approx(1330.0) and row["via"] == "mid" and row["reference"] == "exp-top"
    assert row["key"] == "k-cheap"  # weak (1320) is below


def test_successor_needs_three_earlier_boards_known_at_the_version_date():
    early = [board("2024-01-10", {"exp-top": 1250, "mid": 1240, "cheap": 1200}),
             board("2024-01-12", {"exp-top": 1250, "mid": 1240, "cheap": 1200})]
    later_documented = board("2024-01-15", {"exp-top": 1250, "mid": 1240, "cheap": 1200}, evidence="2024-08-10")
    now = board("2024-07-20", {"mid": 1300, "cheap": 1320})
    t = build(early + [later_documented, now], last="2024-07")
    # at month end only two overlap boards are known -> mid fails; cheap (next) has only two as well -> no value; the
    # third board becomes known 2024-08-10 and gives the first row then
    assert len(t) == 1 and t.iloc[0]["known_from"] == T("2024-08-10") and t.iloc[0]["via"] == "mid"


def test_no_successor_gives_a_gap_not_a_guess():
    t = build([board("2024-01-20", {"exp-top": 1250, "gone": 1240}), board("2024-07-20", {"cheap": 1300})])
    assert t.empty


def test_overlap_counts_one_version_per_board():
    two_versions = [board("2024-01-10", {"exp-top": 1250, "mid": 1240}),
                    board("2024-01-10", {"exp-top": 1251, "mid": 1240}, evidence="2024-01-12"),
                    board("2024-01-15", {"exp-top": 1250, "mid": 1240})]
    t = build(two_versions + [board("2024-07-20", {"mid": 1300, "cheap": 1320})])
    assert t.empty  # two boards, not three versions
    three = two_versions + [board("2024-01-20", {"exp-top": 1250, "mid": 1240})]
    assert build(three + [board("2024-07-20", {"mid": 1300, "cheap": 1320})]).iloc[0]["via"] == "mid"


# ------------------------------------------------------------------ name forms

def test_display_names_rename_and_ambiguity():
    lk = pr.Lookup(pd.Series({"Gemini 2.5 Pro": 1400.0, "gpt-4-1106-preview": 1250.0, "X 1": 1.0, "x-1": 2.0}))
    assert lk.find("gemini-2.5-pro") == "Gemini 2.5 Pro"
    assert lk.find("gpt-4-turbo") == "gpt-4-1106-preview"  # documented rename (arena_map)
    assert lk.find("x 1") is None  # two names with the same normalized form: no match
    assert lk.find("x-1") == "x-1"  # the exact name wins
    assert pr.norm("Claude Opus 4.6 (High)") == pr.norm("claude-opus-4-6-high")


def test_reference_found_under_its_display_name_after_the_switch():
    ref = board("2025-10-17", {"gemini-2.5-pro": 1450, "mid": 1420})
    now = board("2026-10-28", {"Gemini 2.5 Pro": 1440, "Mid": 1445})
    pairs = pd.DataFrame([("Mid", "k-mid", "openai")], columns=["name", "key", "provider"])
    t = build([ref, now], lag=12, last="2026-10", pairs=pairs,
              prices=[("2026-10-20", "k-mid", "openai", 1.0, 4.0)])
    row = t[t["period"] == "2026-10"].iloc[0]
    assert row["reference"] == "gemini-2.5-pro" and row["via"] == "" and row["threshold"] == 1440


# ------------------------------------------------------------------ dating

def test_known_from_and_later_documented_boards():
    boards = [REF, board("2024-07-10", {"front": 1300, "mid": 1310}),
              board("2024-07-25", {"front": 1300, "cheap": 1300}, evidence="2024-08-05")]
    t = build(boards)
    assert t["known_from"].tolist() == [T("2024-08-01"), T("2024-08-05")]
    assert t["key"].tolist() == ["k-mid", "k-cheap"]
    # a later board with the same value adds no version
    same = [REF, board("2024-07-10", {"front": 1300, "mid": 1310}),
            board("2024-07-25", {"front": 1300, "mid": 1310}, evidence="2024-08-05")]
    assert len(build(same)) == 1


def test_board_published_after_month_end_never_counts():
    t = build([REF, board("2024-07-10", {"front": 1300, "mid": 1310}),
               board("2024-08-02", {"front": 1300, "cheap": 1300})])
    assert t["key"].tolist() == ["k-mid"]


def test_price_after_month_end_never_counts():
    prices = PRICES + [("2024-08-01", "k-cheap", "openai", 0.01, 0.01)]
    t = build([REF, board("2024-07-20", {"front": 1300, "cheap": 1300})], prices=prices)
    assert t.iloc[0]["value"] == pytest.approx(blend(1.0, 2.0))


def test_reference_as_known_at_the_version_date_and_the_literal_sensitivity():
    # the board for the reference month (published 2024-01-25) is documented only on 2024-04-02 (bulk upload)
    gap = board("2024-01-25", {"newer": 1290, "front": 1250, "mid": 1200}, evidence="2024-04-02", source="backfill")
    now = board("2024-07-20", {"newer": 1330, "front": 1300, "mid": 1310, "cheap": 1300})
    pairs = pd.concat([PAIRS, pd.DataFrame([("newer", "k-newer", "openai")], columns=PAIRS.columns)])
    prices = PRICES + [("2024-01-20", "k-newer", "openai", 20.0, 20.0)]
    t = build([REF, gap, now], pairs=pairs, prices=prices)
    row = t.iloc[0]
    assert row["reference"] == "newer" and row["source"] == "backfill"  # the reference board is bulk-only
    lit = build([REF, gap, now], pairs=pairs, prices=prices, literal_reference=True)
    assert lit.iloc[0]["reference"] == "front" and lit.iloc[0]["source"] == "release"


def test_as_of_truncates_to_what_was_known():
    boards = [REF, board("2024-07-10", {"front": 1300, "mid": 1310}),
              board("2024-07-25", {"front": 1300, "cheap": 1300}, evidence="2024-08-05")]
    t = build(boards)
    table = t.assign(series="g2_price_rolling6_arena", freq="M", fetched_at=T("2026-11-25"))
    table = table[observations.COLUMNS]
    assert observations.as_of("g2_price_rolling6_arena", "2024-07-31", table).empty
    first = observations.as_of("g2_price_rolling6_arena", "2024-08-01", table)
    assert first.iloc[-1] == pytest.approx(blend(3.0, 15.0))
    later = observations.as_of("g2_price_rolling6_arena", "2024-08-05", table)
    assert later.iloc[-1] == pytest.approx(blend(1.0, 2.0))


# ------------------------------------------------------------------ frontier price

def test_frontier_price_is_the_top_rated_priced_model():
    now = board("2024-01-25", {"exp-top": 1400, "front": 1300, "mid": 1290, "mid-high": 1300, "cheap": 1100})
    t = build([now], lag=0, last="2024-01")
    row = t.iloc[0]
    # exp-top is not priced; front and mid-high tie at 1300 -> the cheaper of the two keys
    assert row["threshold"] == 1300 and row["key"] == "k-mid" and row["n_qualifying"] == 2
    assert row["value"] == pytest.approx(blend(3.0, 15.0))


# ------------------------------------------------------------------ retired models

def test_retired_key_does_not_count():
    deps = pd.DataFrame({"sha": ["20240120"], "key": ["k-cheap"], "deprecation_date": [T("2024-06-30")]})
    t = build([REF, board("2024-07-20", {"front": 1300, "mid": 1300, "cheap": 1300})], deprecations=deps)
    assert t.iloc[0]["key"] == "k-mid"


# ------------------------------------------------------------------ ECI variant

def eci_inputs():
    eci = pd.DataFrame({"model": ["A", "B", "C", "D"], "organization": "x",
                        "release": pd.to_datetime(["2024-03-01", "2024-06-01", "2025-02-01", "2025-05-01"]),
                        "eci": [125.0, 130.0, 135.0, 128.0]})
    gpqa = pd.DataFrame(columns=["version", "model", "organization", "release", "score", "known_from"])
    mapping = pd.DataFrame([("A", "k-a", "openai"), ("B", "k-b", "openai"), ("C", "k-c", "openai"),
                            ("D", "k-d", "openai")], columns=["model", "key", "provider"])
    prices = snaps([("2024-01-20", "k-a", "openai", 1.0, 1.0), ("2024-01-20", "k-b", "openai", 10.0, 10.0),
                    ("2025-01-20", "k-c", "openai", 5.0, 5.0), ("2025-01-20", "k-b", "openai", 10.0, 10.0),
                    ("2025-04-20", "k-d", "openai", 0.5, 0.5), ("2025-04-20", "k-b", "openai", 10.0, 10.0),
                    ("2025-04-20", "k-c", "openai", 5.0, 5.0)])
    return prices, {"eci": eci, "gpqa": gpqa}, mapping


def test_eci_threshold_is_the_frontier_twelve_months_earlier_with_coverage_floor():
    prices, epoch, mapping = eci_inputs()
    t = pr.build_eci(prices, epoch, pd.Period("2025-06", "M"), mapping=mapping)
    # frontier by 2024-05 is 125 (< 128 floor): no value before 2025-06; 2025-06 uses the 2024-06 frontier (B, 130)
    assert [str(p) for p in t.index] == ["2025-06"]
    row = t.iloc[0]
    assert row["threshold"] == 130 and row["reference"] == "B"
    # D (128) is below, C (135) and B qualify -> C is cheaper
    assert row["key"] == "k-c" and row["value"] == pytest.approx(5.0)


def test_eci_floor_can_be_lowered_and_release_dates_count():
    prices, epoch, mapping = eci_inputs()
    t = pr.build_eci(prices, epoch, pd.Period("2025-03", "M"), mapping=mapping, floor=0)
    by = t["key"].to_dict()
    # 2025-01: threshold = frontier by 2024-01 -> none released (no row); 2025-03: frontier by 2024-03 = A (125);
    # A, B and C (released 2025-02-01) qualify; the 2025-01-20 snapshot has no price for k-a, so C sets the minimum
    assert pd.Period("2025-01", "M") not in by and by[pd.Period("2025-03", "M")] == "k-c"
    assert t.loc[pd.Period("2025-03", "M"), "n_qualifying"] == 2
    # D (released 2025-05-01) does not count in 2025-04 even with a price, B (130 >= 125) does
    t4 = pr.build_eci(prices, epoch, pd.Period("2025-04", "M"), mapping=mapping, floor=0)
    assert t4.loc[pd.Period("2025-04", "M"), "key"] == "k-c" and t4.loc[pd.Period("2025-04", "M"), "n_qualifying"] == 2


# ------------------------------------------------------------------ catalog and licence

def test_specs_and_licence_classes():
    specs = {s.key: s for s in pr.SPECS}
    assert set(specs) == {"g2_price_rolling12_arena", "g2_price_rolling6_arena", "g2_price_frontier_arena",
                          "g2_price_rolling12_eci"}
    assert catalog.validate(pr.SPECS) == []
    for k, s in specs.items():
        assert s.branch == "G2" and s.freq == "M" and s.publish
        klass = licenses.classify(s)[0]
        assert klass == ("ja" if k == "g2_price_rolling12_eci" else "okänd")
