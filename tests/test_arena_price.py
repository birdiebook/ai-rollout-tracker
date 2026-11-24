"""G2A: price at fixed Arena capability. Reference-relative threshold, mapping, as-of logic, no future data.
Fixtures only, no network."""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import catalog, config
from ai_tracker.series import arena_price as ap
from ai_tracker.sources import arena_map, model_map

T = pd.Timestamp
CHAIN = (("ref", "Ref"), ("succ", "Succ"), ("succ2", "Succ2"))


def board(published, ratings, evidence=None, source="release"):
    return (T(published), pd.Series(ratings, dtype=float), T(evidence or published), source, "test")


def snaps(rows):
    """rows: (snapshot_date, key, provider, input_per_m, output_per_m)."""
    df = pd.DataFrame(rows, columns=["snapshot_date", "key", "provider", "input_per_m", "output_per_m"])
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    df["sha"] = df["snapshot_date"].dt.strftime("%Y%m%d")
    return df


PAIRS = pd.DataFrame([("ref", "k-ref", "openai"), ("cheap", "k-cheap", "openai"), ("cheap-high", "k-cheap", "openai"),
                      ("weak", "k-weak", "openai"), ("other", "k-other", "gemini")],
                     columns=["name", "key", "provider"])
PRICES = [("2024-02-20", "k-ref", "openai", 30.0, 60.0), ("2024-02-20", "k-cheap", "openai", 1.0, 4.0),
          ("2024-02-20", "k-weak", "openai", 0.1, 0.4), ("2024-02-20", "k-other", "gemini", 2.0, 2.0)]


def build(boards, prices=PRICES, last="2024-03", pairs=PAIRS):
    return ap.build(boards, snaps(prices), CHAIN, pd.Period(last, "M"), pairs_at=lambda when: pairs)


# ------------------------------------------------------------------ threshold


def test_threshold_is_the_reference_in_the_same_board_and_scale_shifts_cancel():
    ratings = {"ref": 1200, "cheap": 1190, "cheap-high": 1205, "weak": 1100, "other": 1300}
    a = build([board("2024-03-10", ratings)], last="2024-03")
    shifted = build([board("2024-03-10", {k: v + 250 for k, v in ratings.items()})], last="2024-03")
    assert a["value"].tolist() == shifted["value"].tolist()
    # k-cheap qualifies through its best variant (cheap-high 1205 >= 1200); k-weak does not
    assert a.iloc[0]["key"] == "k-cheap" and a.iloc[0]["name"] == "cheap-high"
    assert a.iloc[0]["value"] == pytest.approx((3 * 1.0 + 4.0) / 4)
    assert a.iloc[0]["threshold"] == 1200 and a.iloc[0]["reference"] == "ref"


def test_threshold_inclusive_and_api_name_before_display_name():
    b = board("2024-03-10", {"ref": 1200, "Ref": 1150, "succ": 1190})
    assert ap.threshold(b, [], CHAIN) == (1200.0, "ref")
    disp = board("2026-10-25", {"Ref": 1150})
    assert ap.threshold(disp, [], CHAIN) == (1150.0, "ref")
    t = build([board("2024-03-10", {"ref": 1200, "cheap": 1200, "weak": 1199.9})])
    assert t.iloc[0]["key"] == "k-cheap"  # equal to the reference qualifies, just below does not


def test_successor_offset_from_three_earlier_boards_only():
    earlier = [board(f"2024-0{m}-01", {"ref": 1200, "succ": 1200 - d}) for m, d in ((1, 10), (2, 20), (3, 30), (4, 40))]
    b = board("2024-05-01", {"succ": 1000})
    # latest 3 overlaps: diffs 20, 30, 40 -> median 30
    assert ap.threshold(b, earlier, CHAIN) == (1030.0, "succ")
    # a later board (published after b) never enters the offset
    later = earlier + [board("2024-06-01", {"ref": 1200, "succ": 1100})]
    assert ap.threshold(b, later, CHAIN) == (1030.0, "succ")
    # fewer than 3 overlaps -> next successor; none qualifies -> no threshold
    assert ap.threshold(b, earlier[:2], CHAIN) is None
    b2 = board("2024-05-01", {"succ": 1000, "succ2": 900})
    e2 = earlier[:2] + [board(f"2024-0{m}-15", {"ref": 1200, "succ2": 1150}) for m in (1, 2, 3)]
    assert ap.threshold(b2, e2, CHAIN) == (950.0, "succ2")


# ------------------------------------------------------------------ as-of logic


def test_month_uses_latest_board_known_at_month_end_and_prices_at_month_end():
    boards = [board("2024-02-05", {"ref": 1200, "cheap": 1150, "cheap-high": 1150, "other": 1210}),
              board("2024-02-25", {"ref": 1200, "cheap": 1201, "other": 1210})]
    prices = PRICES + [("2024-03-05", "k-weak", "openai", 0.01, 0.01)]  # after Feb month end: not for Feb
    t = build(boards, prices, last="2024-02")
    assert len(t) == 1
    r = t.iloc[0]
    assert r["board"] == T("2024-02-25") and r["key"] == "k-cheap"
    assert r["known_from"] == T("2024-03-01") and r["source"] == "release"


def test_board_documented_later_adds_a_vintage_on_its_evidence_date():
    boards = [board("2024-02-05", {"ref": 1200, "other": 1210}),
              board("2024-02-25", {"ref": 1200, "cheap": 1201}, evidence="2024-04-02", source="backfill")]
    t = build(boards, last="2024-03")
    feb = t[t["period"] == "2024-02"]
    assert feb["known_from"].tolist() == [T("2024-03-01"), T("2024-04-02")]
    assert feb["key"].tolist() == ["k-other", "k-cheap"]
    assert feb["source"].tolist() == ["release", "backfill"]
    # March: the backfilled board is still the latest published, but not known at the end of March either
    mar = t[t["period"] == "2024-03"]
    assert mar["known_from"].tolist() == [T("2024-04-01"), T("2024-04-02")]


def test_no_future_data_later_boards_and_prices_do_not_change_past_months():
    boards = [board("2024-02-05", {"ref": 1200, "cheap": 1201})]
    base = build(boards, last="2024-02")
    more = build(boards + [board("2024-03-10", {"ref": 900, "weak": 1000})],
                 PRICES + [("2024-03-20", "k-weak", "openai", 0.001, 0.001)], last="2024-03")
    pd.testing.assert_frame_equal(base, more[more["period"] == "2024-02"].reset_index(drop=True))
    assert more[more["period"] == "2024-03"].iloc[0]["key"] == "k-weak"


def test_elo_boards_ignored_and_reseller_rows_excluded():
    boards = [board("2024-01-05", {"ref": 1000, "weak": 1100}),  # Elo era (before 2024-01-09): ignored
              board("2024-01-20", {"ref": 1200, "cheap": 1201})]
    prices = [("2024-01-15", "k-cheap", "openai", 1.0, 4.0), ("2024-01-15", "k-weak", "openai", 0.1, 0.4),
              ("2024-01-15", "k-cheap", "azure", 0.5, 0.5)]  # same key under another provider: not first-party
    t = build(boards, prices, last="2024-01")
    assert t.iloc[0]["key"] == "k-cheap" and t.iloc[0]["value"] == pytest.approx(1.75)
    assert t.iloc[0]["board"] == T("2024-01-20")


def test_no_value_without_qualifying_priced_model():
    t = build([board("2024-02-05", {"ref": 1200, "weak": 1100})], last="2024-02")
    assert t.iloc[0]["key"] == "k-ref"  # the reference itself qualifies when priced
    t = build([board("2024-02-05", {"weak": 1300})], last="2024-02")  # no reference, no successor
    assert t.empty


# ------------------------------------------------------------------ mapping


def test_mapping_is_valid_and_first_party():
    assert arena_map.problems() == []
    for provider, keys, names, evidence in arena_map.MODELS:
        assert evidence and all(model_map.is_first_party(k, provider) for k in keys)
        assert not any(p in k for k in keys for p in ("-latest", "chatgpt-4o"))
    assert not any(k in {"gpt-4o", "gpt-4", "gemini/gemini-1.5-pro", "mistral/mistral-medium", "dashscope/qwen-max",
                         "dashscope/qwen-plus"} for _, keys, _, _ in arena_map.MODELS for k in keys)


def test_problems_catch_bad_entries(monkeypatch):
    bad = arena_map.MODELS + [("openai", ("azure/gpt-4o-2024-05-13",), ("gpt-4o-2024-05-13",), "x")]
    monkeypatch.setattr(arena_map, "MODELS", bad)
    errs = arena_map.problems()
    assert any("not first-party" in e for e in errs) and any("mapped twice" in e for e in errs)


def test_rolling_alias_serves_one_version_at_a_time():
    def names(when, key="deepseek-chat"):
        p = arena_map.pairs_at(when)
        return set(p.loc[p["key"] == key, "name"])

    assert names("2024-06-01") == set()
    assert names("2024-12-31") == {"deepseek-v3", "DeepSeek-V3"}
    assert names("2025-03-31") == {"deepseek-v3-0324", "DeepSeek-V3 (0324)"}
    assert names("2025-08-31", "deepseek-reasoner") == {"deepseek-v3.1-thinking", "DeepSeek-V3.1 (Thinking)"}
    assert names("2026-03-31") == {"deepseek-v3.2", "DeepSeek-V3.2"}
    assert names("2026-04-30") == set()  # after the last documented version
    assert names("2024-10-31", "deepseek-coder") == {"deepseek-v2.5", "DeepSeek-V2.5"}
    assert names("2024-12-31", "deepseek-coder") == set()


def test_effort_variants_share_a_key_and_reference_models_are_mapped():
    fp = arena_map.fixed_pairs()
    assert set(fp.loc[fp["name"].isin(["o3-mini", "o3-mini-high", "o3-mini (High)"]), "key"]) == {"o3-mini-2025-01-31"}
    for chain in ap.CHAINS.values():
        for api, display in chain:
            assert {api, display} <= set(fp["name"]), api
    assert not set(arena_map.UNMAPPED) & arena_map.mapped_names()
    assert set(arena_map.UNMAPPED.values()) <= set(arena_map.REASONS)


def test_coverage_marks_unreviewed_names():
    boards = [board("2024-03-10", {"gpt-4-0314": 1200, "gpt-4o-2024-05-13": 1250, "brand-new-model": 1300,
                                   "chatgpt-4o-latest": 1260, "weak": 1000})]
    c = ap.coverage(boards, ap.CHAINS["gpt4"]).set_index("name")["status"].to_dict()
    assert c == {"gpt-4-0314": "mapped", "gpt-4o-2024-05-13": "mapped", "brand-new-model": "unreviewed",
                 "chatgpt-4o-latest": "alias_drifts"}


# ------------------------------------------------------------------ registry


def test_reference_rule_is_written_in_the_doc():
    doc = (config.REPO / "docs" / "kallor" / "g2_arena_pris.md").read_text(encoding="utf-8")
    for variant, chain in ap.CHAINS.items():
        assert f"`{ap.KEYS[variant]}`" in doc
        for api, display in chain:
            assert f"`{api}`" in doc and f'"{display}"' in doc
    assert "2024-01-09" in doc and str(ap.OVERLAP_BOARDS) in doc


def test_specs_in_catalog():
    by = catalog.by_key()
    for key in ap.KEYS.values():
        s = by[key]
        assert s.branch == "G2" and s.freq == "M" and s.lag_days == 1
    assert catalog.validate() == []
