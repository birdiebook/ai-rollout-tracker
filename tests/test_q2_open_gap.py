"""Q2: lag and gap between open and closed weights, and between Chinese labs and the rest (synthetic data, no network).

Register 2026-11-25 "Q2: gapet mellan öppna och stängda modeller och Kinas gap"; doc docs/kallor/g1_oppen_stangd.md.
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import catalog, licenses, observations
from ai_tracker.series import open_gap as og
from ai_tracker.sources import arena_meta as am
from ai_tracker.sources import model_origin as mo

T = pd.Timestamp


def board(day, ratings, evidence=None, source="release"):
    return (T(day), pd.Series(ratings, dtype=float), T(evidence or day), source, "test")


def table_classifier(weights: dict[str, str], orgs: dict[str, str] | None = None):
    orgs = orgs or {}

    def classify(name, _date):
        return weights.get(name), orgs.get(name), "test", "test"
    return classify


W = {"c1": mo.CLOSED, "c2": mo.CLOSED, "c3": mo.CLOSED, "o1": mo.OPEN, "o2": mo.OPEN}


def _one(table, kind="open", period=None):
    t = table[table["kind"] == kind]
    if period:
        t = t[t["period"] == period]
    return t.sort_values("known_from")


# ------------------------------------------------------------------ Arena, within one board

def test_lag_is_read_within_the_current_board_not_across_boards():
    # Scale shifts by +500 in the last board; the closed top of each earlier month is re-read there.
    boards = [
        board("2024-01-10", {"c1": 1000, "o1": 900}),
        board("2024-02-10", {"c1": 1000, "c2": 1100, "o1": 900}),
        board("2024-03-10", {"c1": 1000, "c2": 1100, "c3": 1200, "o1": 900}),
        board("2024-04-10", {"c1": 1450, "c2": 1600, "c3": 1700, "o1": 1400, "o2": 1610}),
    ]
    t = og.arena_build(boards, table_classifier(W), pd.Period("2024-04", "M"))
    apr = _one(t, period="2024-04").iloc[-1]
    # O(2024-04) = o2 1610; closed fronts read in the April board: Jan c1 1450, Feb c2 1600, Mar c3 1700 -> s* = Mar
    assert apr["follow_model"] == "o2" and apr["lead_model"] == "c3"
    assert apr["s_star"] == pd.Period("2024-03", "M") and apr["lag"] == 1
    assert apr["gap"] == pytest.approx(90)
    # Across boards the open top (1610) would exceed every earlier closed top (<= 1200); that is never done.
    feb = _one(t, period="2024-02").iloc[-1]
    assert feb["status"] == "censored" and pd.isna(feb["lag"])  # o1 900 <= c1 1000 already in the first month


def test_floor_zero_when_open_leads_and_negative_gap():
    boards = [board("2024-01-10", {"c1": 1000, "o1": 900}), board("2024-02-10", {"c1": 1000, "o1": 1050})]
    feb = _one(og.arena_build(boards, table_classifier(W), pd.Period("2024-02", "M")), period="2024-02").iloc[-1]
    assert feb["lag"] == 0 and feb["status"] == "leads" and feb["gap"] == pytest.approx(-50)


def test_fallback_to_next_closed_model_when_the_top_is_gone():
    boards = [
        board("2024-01-10", {"c1": 1000, "o1": 800}),
        board("2024-02-10", {"c2": 1100, "c1": 1050, "o1": 800}),
        board("2024-03-10", {"c1": 1060, "c3": 1200, "o1": 1055}),  # c2 removed
    ]
    mar = _one(og.arena_build(boards, table_classifier(W), pd.Period("2024-03", "M")), period="2024-03").iloc[-1]
    assert mar["status"] == "censored"  # Jan's top c1 is still in March at 1060 >= 1055: reached in the first month
    boards[0] = board("2024-01-10", {"c0": 900, "o1": 800})
    w = {**W, "c0": mo.CLOSED}
    mar = _one(og.arena_build(boards, table_classifier(w), pd.Period("2024-03", "M")), period="2024-03").iloc[-1]
    # Jan: c0 not in March board -> no leader of b(Jan) present (missing); Feb: c2 gone -> fallback c1 1060 >= 1055
    assert mar["missing"] == 1 and mar["fallbacks"] == 1
    assert mar["s_star"] == pd.Period("2024-02", "M") and mar["reach_model"] == "c1" and mar["lag"] == 1


def test_renamed_model_is_found_through_its_class():
    boards = [
        board("2024-01-10", {"c0": 900, "o1": 800}),
        board("2024-02-10", {"gpt-x": 1100, "c1": 1000, "o1": 800}),
        board("2024-03-10", {"GPT X": 1100, "c1": 1000, "c3": 1200, "o1": 1090}),
    ]
    w = {**W, "c0": mo.CLOSED, "gpt-x": mo.CLOSED, "GPT X": mo.CLOSED}
    classes = mo.Classes([("gpt-x", "GPT X")])
    t = og.arena_build(boards, table_classifier(w), pd.Period("2024-03", "M"), find=classes.find)
    mar = _one(t, period="2024-03").iloc[-1]
    assert mar["fallbacks"] == 0 and mar["s_star"] == pd.Period("2024-02", "M") and mar["lag"] == 1
    t2 = og.arena_build(boards, table_classifier(w), pd.Period("2024-03", "M"))  # without the class
    assert _one(t2, period="2024-03").iloc[-1]["fallbacks"] == 1  # falls back to c1 (1000 < 1090): s* = Mar
    assert _one(t2, period="2024-03").iloc[-1]["lag"] == 0


def test_china_uses_country_of_the_organization():
    orgs = {"a": "openai", "b": "deepseek", "c": "alibaba", "d": "google", "e": "Nomic AI"}
    w = {k: mo.CLOSED for k in orgs}
    boards = [
        board("2024-01-10", {"a": 1000, "b": 900, "e": 2000}),
        board("2024-02-10", {"a": 1000, "d": 1100, "b": 950, "c": 1020, "e": 2000}),
    ]
    t = og.arena_build(boards, table_classifier(w, orgs), pd.Period("2024-02", "M"))
    feb = _one(t, "china", "2024-02").iloc[-1]
    # e (no documented country) is left out; Chinese top c 1020; non-Chinese fronts: Jan a 1000, Feb d 1100
    assert feb["follow_model"] == "c" and feb["lead_model"] == "d"
    assert feb["s_star"] == pd.Period("2024-02", "M") and feb["lag"] == 0  # Jan front a (1000) < 1020 <= d (1100)
    assert feb["status"] == "lag"  # not "leads": the follower is behind, but within the current month's front
    assert feb["gap"] == pytest.approx(80)


def test_board_documented_later_adds_a_version_and_never_back_dates():
    boards = [
        board("2024-01-10", {"c1": 1000, "o1": 800}),
        board("2024-02-10", {"c1": 1000, "c2": 1100, "o1": 800}),
        board("2024-03-10", {"c1": 1000, "c2": 1100, "c3": 1200, "o1": 1050}),
        board("2024-03-28", {"c1": 1000, "c2": 1100, "c3": 1200, "o1": 1150}, evidence="2024-04-15",
              source="backfill"),
    ]
    t = og.arena_build(boards, table_classifier(W), pd.Period("2024-04", "M"))
    rows = og.arena_series(t, "open", "lag")
    mar = rows[rows["period"] == "2024-03"].sort_values("known_from")
    assert list(mar["known_from"]) == [T("2024-04-01"), T("2024-04-15")]
    assert list(mar["value"]) == [1.0, 0.0]  # o1 1050 met by c2 (Feb); the later board's o1 1150 only by c3
    assert mar.iloc[0]["source"] == "release" and mar.iloc[-1]["source"] == "backfill"
    assert (rows["known_from"] >= pd.PeriodIndex(rows["period"], freq="M").end_time.normalize()
            + pd.Timedelta(days=1)).all()


def test_as_of_truncation_through_observations(tmp_path):
    boards = [
        board("2024-01-10", {"c1": 1000, "o1": 800}),
        board("2024-02-10", {"c1": 1000, "c2": 1100, "o1": 800}),
        board("2024-03-10", {"c1": 1000, "c2": 1100, "c3": 1200, "o1": 1050}),
        board("2024-03-28", {"c1": 1000, "c2": 1100, "c3": 1200, "o1": 1150}, evidence="2024-04-15"),
    ]
    spec = catalog.by_key()["g1_open_lag_months_arena"]
    rows = og.arena_series(og.arena_build(boards, table_classifier(W), pd.Period("2024-03", "M")), "open", "lag")
    new = observations.new_rows(spec, rows, pd.DataFrame(columns=observations.COLUMNS), fetched_at=T("2026-11-25"),
                                log=pd.DataFrame(columns=observations.LOG_COLUMNS))
    early = observations.as_of(spec.key, "2024-04-10", new)
    late = observations.as_of(spec.key, "2024-04-15", new)
    assert early[pd.Period("2024-03", "M")] == 1.0  # o1 1050 first reached by c2 (Feb)
    assert late[pd.Period("2024-03", "M")] == 0.0  # o1 1150 reached only by c3 in March itself
    assert pd.Period("2024-03", "M") not in observations.as_of(spec.key, "2024-03-31", new).index


# ------------------------------------------------------------------ Arena classification and names

def _meta(rows):
    return pd.DataFrame(rows, columns=am.META_COLUMNS).assign(date=lambda d: pd.to_datetime(d["date"]))


def test_classifier_order_own_earlier_later_closed_curated_none():
    meta = _meta([
        ("m-own", "2024-02-10", "MIT", "deepseek", 10, "dataset"),
        ("m-early", "2024-01-10", "Apache 2.0", "meta", 10, "dataset"),
        ("m-early", "2024-02-10", "", "", 10, "dataset"),
        ("m-late-closed", "2024-03-10", "Proprietary", "openai", 10, "dataset"),
        ("m-late-open", "2024-03-10", "Apache 2.0", "mistral", 10, "dataset"),
        ("m-space", "2024-01-05", "Llama 2 Community", "Meta", None, "space:leaderboard_table_20240105.csv"),
    ])
    curated = {"m-cur": (mo.OPEN, "2024-02-01", "Databricks", "ref"), "m-late-open": (None, None, "", "ref")}
    clf = am.Classifier(meta, mo.Classes(), curated)
    d = T("2024-02-10")
    assert clf.classify("m-own", d)[:3] == (mo.OPEN, "deepseek", "own")
    assert clf.classify("m-early", d)[:3] == (mo.OPEN, "meta", "earlier")
    assert clf.classify("m-late-closed", d)[:4] == (mo.CLOSED, "openai", "later_closed", "later")
    assert clf.classify("m-late-open", d)[0] is None  # a later "open" may be a later release
    assert clf.classify("m-space", d)[:2] == (mo.OPEN, "Meta")
    assert clf.classify("m-cur", d)[:3] == (mo.OPEN, "Databricks", "curated")
    assert clf.classify("m-cur", T("2024-01-15"))[0] is None  # open only from the documented release
    assert clf.classify("nothing", d) == (None, None, "none", "none")
    assert am.weights_of("Proprietary") == mo.CLOSED and am.weights_of(" ") is None
    assert am.weights_of("Other") == mo.OPEN and am.weights_of(float("nan")) is None


def test_classifier_uses_the_name_class():
    meta = _meta([("old-name", "2024-01-10", "Proprietary", "anthropic", 5, "dataset")])
    clf = am.Classifier(meta, mo.Classes([("old-name", "New Name")]), {})
    assert clf.classify("New Name", T("2024-05-01"))[:2] == (mo.CLOSED, "anthropic")


def test_display_switch_rules_are_unique_and_ordered():
    before = _meta([
        ("gpt-4o-2024-05-13", "2026-10-15", "Proprietary", "openai", 100, "dataset"),
        ("claude-3-7-sonnet-20250219-thinking-32k", "2026-10-15", "Proprietary", "anthropic", 50, "dataset"),
        ("command-r", "2026-10-15", "CC-BY-NC-4.0", "cohere", 777, "dataset"),
        ("same", "2026-10-15", "MIT", "x", 1, "dataset"),
        ("dup-a", "2026-10-15", "MIT", "y", 5, "dataset"), ("dup-b", "2026-10-15", "MIT", "y", 5, "dataset"),
    ])
    after = _meta([
        ("GPT-4o (2024-05-13)", "2026-10-20", "Proprietary", "openai", 101, "dataset"),
        ("Claude 3.7 Sonnet (Thinking 32K, 20250219)", "2026-10-20", "Proprietary", "anthropic", 51, "dataset"),
        ("Command R", "2026-10-20", "CC-BY-NC-4.0", "cohere", 777, "dataset"),
        ("same", "2026-10-20", "MIT", "x", 1, "dataset"),
        ("Dup A", "2026-10-21", "MIT", "y", 5, "dataset"),
    ])
    pairs, left, right = am.display_switch_pairs(before, after)
    assert pairs["gpt-4o-2024-05-13"] == "GPT-4o (2024-05-13)"  # normalized
    assert pairs["claude-3-7-sonnet-20250219-thinking-32k"] == "Claude 3.7 Sonnet (Thinking 32K, 20250219)"  # words
    assert pairs["command-r"] == "Command R"  # normalized too
    assert pairs["same"] == "same"
    assert pairs.get("dup-a") == "Dup A" and "dup-b" in left  # normalized unique; dup-b has no partner


def test_vote_count_rule_needs_a_unique_match():
    before = _meta([("aya-x", "2026-10-15", "CC-BY-NC-4.0", "", 10, "dataset"),
                    ("aya-y", "2026-10-15", "CC-BY-NC-4.0", "", 10, "dataset")])
    after = _meta([("Aya Expanse X", "2026-10-20", "CC-BY-NC-4.0", "", 10, "dataset")])
    pairs, left, right = am.display_switch_pairs(before, after)
    assert pairs == {} and set(left) == {"aya-x", "aya-y"} and right == ["Aya Expanse X"]


def test_curated_tables_are_well_formed():
    for key, (country, ref) in mo.ORG_COUNTRY.items():
        assert key == mo.norm(key) and country and ref
    for name, (w, released, org, ref) in mo.ARENA_MODELS.items():
        assert w in (mo.OPEN, mo.CLOSED, None) and ref
        assert (released is not None) == (w == mo.OPEN)
    olds = [a for a, *_ in mo.ARENA_RENAMES]
    assert len(olds) == len(set(olds))
    for a, b, day, ev in mo.ARENA_RENAMES + [(a, b, "2026-10-20", ev) for a, b, ev in mo.DISPLAY_EXTRA]:
        assert a != b and ev and T(day)
    for model, (w, c, ref) in mo.ECI_MODELS.items():
        assert w in (mo.OPEN, mo.CLOSED, None) and ref


def test_country_and_chinese_rules():
    assert mo.country("Zhipu AI") == mo.CHINA and mo.country("zai") == mo.CHINA and mo.country("OpenAI") == mo.US
    assert mo.country("Nomic AI") is None and mo.country("") is None
    assert mo.is_chinese("China") is True and mo.is_chinese("United States of America") is False
    assert mo.is_chinese("China,United States of America") is None and mo.is_chinese(float("nan")) is None
    assert mo.is_chinese("Multinational") is False


def test_space_table_parsing():
    csv = b"key,Model,MT-bench (score),MMLU,License,Organization,Link\nm1,M1,7,0.5,Proprietary,OpenAI,x\n"
    t = am.space_table_meta("leaderboard_table_20240109.csv", csv)
    assert t.iloc[0]["name"] == "m1" and t.iloc[0]["date"] == T("2024-01-09") and t.iloc[0]["license"] == "Proprietary"
    assert am.space_table_meta("leaderboard_table_20230619.csv", b"Model,License\nM1,MIT\n") is None


# ------------------------------------------------------------------ Epoch ECI

def _eci_rows():
    return pd.DataFrame([
        ("C1", 120, "2023-03-14", "Closed weights", "United States of America"),
        ("O1", 110, "2023-07-18", "Open weights", "United States of America"),
        ("C2", 130, "2023-11-06", "Closed weights", "United States of America"),
        ("O2", 125, "2024-04-18", "Open weights", "China"),
        ("X", 140, "2024-05-01", "Other", None),  # all_models -> closed, US
        ("Y", 135, "2024-06-01", "Other", None),  # curated -> open, China
        ("Z", 200, "2024-06-01", "Other", None),  # left out
    ], columns=["Model", "eci", "date", "Accessibility group", "Country (of organization)"])


def test_eci_classification_fallbacks():
    am_ = pd.DataFrame([("X", "No", "United States of America")],
                       columns=["Model", "Open model weights?", "Country (of organization)"])
    f = og.eci_frame(_eci_rows(), am_, {"Y": (mo.OPEN, mo.CHINA, "ref")}).set_index("model")
    assert f.loc["X", "step_weights"] == "all_models" and f.loc["X", "weights"] == mo.CLOSED
    assert f.loc["Y", "step_weights"] == "curated" and f.loc["Y", "chinese"] is True
    assert f.loc["Z", "step_weights"] == "none" and pd.isna(f.loc["Z", "weights"])
    assert f.loc["O2", "chinese"] is True and f.loc["C1", "chinese"] is False


def test_eci_lag_gap_floor_and_censoring():
    am_ = pd.DataFrame([("X", "No", "United States of America")],
                       columns=["Model", "Open model weights?", "Country (of organization)"])
    f = og.eci_frame(_eci_rows(), am_, {"Y": (mo.OPEN, mo.CHINA, "ref")})
    t = og.eci_build(f, "open", pd.Period("2024-06", "M")).set_index("period")
    assert t.loc["2023-07", "status"] == "censored" and pd.isna(t.loc["2023-07", "lag"])  # O1 110 < C1 (first month)
    assert t.loc["2024-04", "lag"] == 5 and t.loc["2024-04", "s_star"] == "2023-11"  # O2 125 first met by C2
    assert t.loc["2024-04", "gap"] == pytest.approx(5)
    assert t.loc["2024-06", "lag"] == 1 and t.loc["2024-06", "reach_model"] == "X"  # Y 135 reached by X (May)
    assert t.index[0] == "2023-07"  # first month with both groups
    s = og.eci_values(t.reset_index(), "lag")
    assert pd.Period("2023-07", "M") not in s.index and s[pd.Period("2024-04", "M")] == 5
    c = og.eci_build(f, "china", pd.Period("2024-06", "M")).set_index("period")
    assert c.loc["2024-04", "follow_model"] == "O2" and c.loc["2024-04", "lead_model"] == "C2"


def test_eci_open_leading_gives_zero():
    rows = pd.DataFrame([("C1", 100, "2024-01-01", "Closed weights", "United States of America"),
                         ("O1", 105, "2024-02-01", "Open weights", "China")],
                        columns=["Model", "eci", "date", "Accessibility group", "Country (of organization)"])
    t = og.eci_build(og.eci_frame(rows, None, {}), "open", pd.Period("2024-03", "M")).set_index("period")
    assert t.loc["2024-02", "lag"] == 0 and t.loc["2024-02", "gap"] == pytest.approx(-5)


# ------------------------------------------------------------------ catalog

KEYS = [f"g1_{k}_{m}_{s}" for k in ("open", "china") for m in ("lag_months", "gap") for s in ("arena", "eci")]


def test_specs_in_catalog_with_licence_and_class():
    specs = catalog.by_key()
    assert all(k in specs for k in KEYS)
    assert not [e for e in catalog.validate([specs[k] for k in KEYS])]
    for k in KEYS:
        s = specs[k]
        assert s.branch == "G1" and s.freq == "M" and s.publish
        assert licenses.classify(s, specs)[0] == (licenses.OKAND if k.endswith("arena") else licenses.JA)


def test_register_entry_precedes_and_names_the_keys():
    from ai_tracker import config

    text = (config.REPO / "docs" / "mattregister.md").read_text(encoding="utf-8")
    entry = text.split("### 2026-11-25 – Q2: gapet mellan öppna och stängda modeller och Kinas gap")[1]
    assert all(f"`{k}`" in entry for k in KEYS)
