"""Correction track X5 (review R8, docs/granskning/r8_g2_arena.md): versioned Arena boards (R-1), dated price
corrections (R-2), price checks (R-3, R-4) and Gemini's stable aliases (R-5). Fixtures only, no network."""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker.series import arena_price as ap
from ai_tracker.sources import arena, arena_map

T = pd.Timestamp
SUB = "text"


def _commits(rows):
    """rows: (sha, ISO day, title), oldest first."""
    return [(sha, T(day), title) for sha, day, title in rows]


COMMITS = _commits([
    ("a" * 40, "2026-04-02", "add historical data"),            # 0 bulk
    ("b" * 40, "2026-05-02", "Update text for 2026-05-01"),     # 1 board 05-01
    ("c" * 40, "2026-05-12", "Update text for 2026-05-11"),     # 2 board 05-11
    ("d" * 40, "2026-07-07", "Update text for 2026-05-01"),     # 3 re-upload of 05-01
    ("e" * 40, "2026-07-29", "Remove erroneously published variant rows from text"),  # 4 untitled rewrite
    ("f" * 40, "2026-08-02", "Update text for 2026-08-01"),     # 5 board 08-01
])


def _rows(boards: dict[str, dict[str, float]]) -> pd.DataFrame:
    return pd.DataFrame([(m, r, d) for d, b in boards.items() for m, r in b.items()],
                        columns=["model_name", "rating", "leaderboard_publish_date"])


BULK = {"x": 1000.0, "mixtral-8x7b-instruct-v0.1": 900.0}
V1 = {"x": 1100.0, "y": 1050.0}


# ------------------------------------------------------------------ R-1: versions of a rewritten board

def test_version_plan_change_points_and_few_revisions():
    plan, revs = arena.version_plan(SUB, COMMITS, ["2025-01-01", "2026-05-01", "2026-05-11", "2026-08-01"])
    p = {d: [(str(v["evidence"].date()), v["start"], v["end"], v["rev"]) for v in vs] for d, vs in plan.items()}
    assert p["2026-05-01"] == [("2026-05-02", 1, 3, 2), ("2026-07-07", 3, 4, 3), ("2026-07-29", 4, None, None)]
    assert p["2026-05-11"] == [("2026-05-12", 2, 4, 2), ("2026-07-29", 4, None, None)]
    assert p["2025-01-01"] == [("2026-04-02", 0, 4, 2), ("2026-07-29", 4, None, None)]  # bulk board, untitled rewrite
    assert p["2026-08-01"] == [("2026-08-02", 5, None, None)]  # after the rewrite: a single version
    assert {v["source"] for v in plan["2025-01-01"]} == {"backfill"}
    assert revs == {2: "c" * 40, 3: "d" * 40}  # two revisions read for five closed versions


def test_board_versions_date_each_value_by_its_commit_and_collapse_equal_uploads():
    plan, revs = arena.version_plan(SUB, COMMITS, ["2025-01-01", "2026-05-01", "2026-05-11"])
    rev = {2: _rows({"2025-01-01": BULK, "2026-05-01": V1, "2026-05-11": {"x": 1200.0}}),
           3: _rows({"2025-01-01": BULK, "2026-05-01": V1, "2026-05-11": {"x": 1200.0}})}  # re-upload unchanged
    head = _rows({"2025-01-01": BULK, "2026-05-01": {"x": 1090.0, "y": 1050.0}, "2026-05-11": {"x": 1200.0}})
    vs = arena.board_versions(plan, head, rev)
    assert [(str(e.date()), float(r.max())) for e, r, _ in vs["2026-05-01"]] == [("2026-05-02", 1100.0),
                                                                                 ("2026-07-29", 1090.0)]
    assert [str(e.date()) for e, _, _ in vs["2026-05-11"]] == ["2026-05-12"]  # unchanged: first date kept
    assert [str(e.date()) for e, _, _ in vs["2025-01-01"]] == ["2026-04-02"]


def test_missing_revision_never_back_dates_the_head_rows():
    plan, _ = arena.version_plan(SUB, COMMITS, ["2026-05-01"])
    head = _rows({"2026-05-01": {"x": 1090.0}})
    vs = arena.board_versions(plan, head, {2: None, 3: None})
    assert [(str(e.date()), float(r.max())) for e, r, _ in vs["2026-05-01"]] == [("2026-07-29", 1090.0)]


def test_versioned_board_gives_a_later_vintage_not_a_back_dated_value():
    plan, _ = arena.version_plan(SUB, COMMITS, ["2026-05-01"])
    rev = {2: _rows({"2026-05-01": {**V1, "mixtral-8x7b-instruct-v0.1": 900.0}}),
           3: _rows({"2026-05-01": {**V1, "mixtral-8x7b-instruct-v0.1": 900.0}})}
    head = _rows({"2026-05-01": {"x": 1090.0, "y": 1050.0, "mixtral-8x7b-instruct-v0.1": 900.0}})
    versions = arena.board_versions(plan, head, rev)
    bl = arena.boards(head, SUB, {(SUB, "2026-05-01"): T("2026-07-29")}, {}, {}, versions=versions)
    assert [(b[2], float(b[1].max()), b[4]) for b in bl] == [(T("2026-05-02"), 1100.0, "dataset"),
                                                            (T("2026-07-29"), 1090.0, "dataset-v2")]
    rows = arena.monthly_rows(arena.summarize(bl), "top", pd.Period("2026-05", "M"))
    assert list(zip(rows["value"], rows["known_from"])) == [(1100.0, T("2026-06-01")), (1090.0, T("2026-07-29"))]


def test_variant_rows_keep_the_best_row_per_model():
    r = arena.board_ratings(pd.DataFrame({"model_name": ["a", "a", "b"], "rating": [1.0, 3.0, 2.0]}))
    assert r.to_dict() == {"a": 3.0, "b": 2.0} and r.index.is_unique


def test_parse_file_log_is_oldest_first_with_shas():
    log = "\n".join([f"{'f' * 40}|2026-08-02T03:00:00+00:00|Update text for 2026-08-01",
                     f"{'a' * 40}|2026-04-02T19:50:32+00:00|add historical data"])
    c = arena.parse_file_log(log)
    assert [x[0][0] for x in c] == ["a", "f"] and c[0][1] == T("2026-04-02")


# ------------------------------------------------------------------ R-2: dated price corrections

def _snap(day, key, inp, out, provider="gemini"):
    return pd.DataFrame({"snapshot_date": [T(day)], "sha": [day], "key": [key], "provider": [provider],
                         "input_per_m": [inp], "output_per_m": [out]})


def test_price_correction_only_from_the_later_of_effective_and_published():
    key = "gemini/gemini-1.5-pro-002"
    before = ap.apply_corrections(_snap("2024-09-30", key, 3.5, 10.5), T("2024-09-30"))
    after = ap.apply_corrections(_snap("2024-10-31", key, 3.5, 10.5), T("2024-10-31"))
    assert before[["input_per_m", "output_per_m"]].iloc[0].tolist() == [3.5, 10.5]
    assert after[["input_per_m", "output_per_m"]].iloc[0].tolist() == [1.25, 5.0]
    late = [{**ap.PRICE_CORRECTIONS[0], "effective": "2024-10-01", "published": "2024-11-15"}]
    assert ap.apply_corrections(_snap("2024-10-31", key, 3.5, 10.5), T("2024-10-31"), late)["input_per_m"].iloc[0] == 3.5


def test_price_correction_leaves_a_different_litellm_price_alone():
    s = _snap("2024-11-30", "gemini/gemini-1.5-pro-002", 2.0, 8.0)
    assert ap.apply_corrections(s, T("2024-11-30"))["input_per_m"].iloc[0] == 2.0
    other = _snap("2024-11-30", "gemini/gemini-1.5-pro-002", 3.5, 10.5, provider="vertex_ai-language-models")
    assert ap.apply_corrections(other, T("2024-11-30"))["input_per_m"].iloc[0] == 3.5


def test_corrections_and_checks_are_documented():
    for c in ap.PRICE_CORRECTIONS:
        assert c["evidence"] and all(e in ap.PRICE_EVIDENCE for e in c["evidence"])
        assert c["source"] and len(c["old"]) == len(c["new"]) == 2
    for url, read, sha in ap.PRICE_EVIDENCE.values():
        assert url.startswith("https://") and T(read) and len(sha) == 64 and int(sha, 16) >= 0
    statuses = {s for s, _ in ap.PRICE_CHECKS.values()}
    assert statuses <= {"developer_page", "not_listed", "blocked", "disputed"}
    assert ap.DISPUTED == {"mistral/mistral-small-3-2-2506"}
    assert "mistral/mistral-small-3-2-2506" in ap.UNVERIFIED


def test_build_flags_the_check_status_and_can_leave_a_key_out():
    boards = [(T("2024-01-20"), pd.Series({"ref": 1200.0, "cheap": 1201.0}), T("2024-01-20"), "release", "t")]
    pairs = pd.DataFrame([("ref", "k-ref", "openai"), ("cheap", "mistral/mistral-small-3-2-2506", "mistral")],
                         columns=["name", "key", "provider"])
    s = pd.concat([_snap("2024-01-31", "k-ref", 30.0, 60.0, "openai"),
                   _snap("2024-01-31", "mistral/mistral-small-3-2-2506", 0.06, 0.18, "mistral")])
    chain = (("ref", "Ref"),)
    t = ap.build(boards, s, chain, pd.Period("2024-01", "M"), pairs_at=lambda when: pairs)
    assert t.iloc[0]["price_check"] == "disputed"
    t2 = ap.build(boards, s, chain, pd.Period("2024-01", "M"), pairs_at=lambda when: pairs,
                  exclude_keys=("mistral/mistral-small-3-2-2506",))
    assert t2.iloc[0]["key"] == "k-ref" and t2.iloc[0]["price_check"] == "unchecked"


# ------------------------------------------------------------------ R-5: Gemini stable aliases

@pytest.mark.parametrize("when,expected", [("2024-06-30", True), ("2024-08-31", True), ("2024-09-30", False),
                                           ("2024-04-30", False)])
def test_gemini_stable_alias_counts_only_while_001_was_the_only_stable_version(when, expected):
    p = arena_map.pairs_at(when)
    names = set(p.loc[p["key"] == "gemini/gemini-1.5-flash", "name"])
    assert (names == {"gemini-1.5-flash-api-0514", "gemini-1.5-flash-001", "Gemini 1.5 Flash (001)"}) is expected
    assert set(p.loc[p["key"] == "gemini/gemini-1.5-flash", "provider"]) <= {"gemini"}
    assert arena_map.problems() == []
