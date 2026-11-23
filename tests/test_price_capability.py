"""G2 price at fixed capability: prices, threshold, as-of logic and the model mapping (fixtures, no network)."""

from __future__ import annotations

import re

import pandas as pd
import pytest

from ai_tracker import catalog, config
from ai_tracker.series import price_capability as pc
from ai_tracker.sources import epoch_capability, litellm_prices, model_map

T = pd.Timestamp


def snaps(rows):
    """rows: (snapshot_date, key, provider, input_per_m, output_per_m)."""
    df = pd.DataFrame(rows, columns=["snapshot_date", "key", "provider", "input_per_m", "output_per_m"])
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    df["sha"] = df["snapshot_date"].dt.strftime("%Y%m%d")
    return df


MAPPING = pd.DataFrame([("a-1", "openai", "A"), ("b-1", "openai", "B"), ("alias", "openai", "A"),
                        ("alias", "openai", "C")], columns=["key", "provider", "model"])
RELEASE = {"A": T("2025-01-10"), "B": T("2025-01-10"), "C": T("2025-03-15")}


def build(rows, capability, threshold=100.0, end="2025-06-30", mapping=MAPPING):
    return pc.build(snaps(rows), lambda when: capability, RELEASE, threshold, T(end), mapping)


# ------------------------------------------------------------------ prices


def test_blended_is_three_to_one():
    assert pc.blended(3.0, 15.0) == pytest.approx(6.0)  # Claude 3.5 Sonnet, matches Epoch's reference
    assert list(pc.blended([1.0, 0.0], [5.0, 4.0])) == pytest.approx([2.0, 1.0])


def test_extract_modes_zero_prices_and_reasoning_output():
    snap = {
        "sample_spec": {"mode": "one of: chat, embedding"},
        "m-chat": {"mode": "chat", "litellm_provider": "openai", "input_cost_per_token": 1e-6, "output_cost_per_token": 4e-6},
        "m-resp": {"mode": "responses", "litellm_provider": "openai", "input_cost_per_token": 2e-5, "output_cost_per_token": 8e-5},
        "m-embed": {"mode": "embedding", "litellm_provider": "openai", "input_cost_per_token": 1e-7, "output_cost_per_token": 1e-7},
        "m-free": {"mode": "chat", "litellm_provider": "gemini", "input_cost_per_token": 0, "output_cost_per_token": 0},
        "m-think": {"mode": "chat", "litellm_provider": "gemini", "input_cost_per_token": 1.5e-7,
                    "output_cost_per_token": 6e-7, "output_cost_per_reasoning_token": 3.5e-6},
    }
    rows = {r[0]: r for r in litellm_prices.extract(snap)}
    assert set(rows) == {"m-chat", "m-resp", "m-think"}
    assert rows["m-chat"][2:] == pytest.approx((1.0, 4.0))
    assert rows["m-think"][3] == pytest.approx(3.5)  # reasoning-mode output price


def test_sample_commits_last_per_week_and_month():
    ts = pd.to_datetime(["2025-01-27T10:00Z", "2025-01-29T10:00Z",  # same week, 29th is the week's last
                         "2025-01-31T23:30Z", "2025-02-01T01:00Z",  # 31st: last of January; 1 Feb: same W-SUN week
                         "2025-02-10T08:00Z"], utc=True)
    commits = pd.DataFrame({"sha": list("abcde"), "ts": ts})
    s = litellm_prices.sample_commits(commits)
    assert list(s["sha"]) == ["c", "d", "e"]  # c = January's last; d = that week's last; e = Feb's last
    assert s["snapshot_date"].iloc[0] == T("2025-01-31")


# ------------------------------------------------------------------ threshold and as-of


def test_threshold_is_inclusive_and_filters():
    rows = [("2025-01-20", "a-1", "openai", 1.0, 1.0), ("2025-01-20", "b-1", "openai", 0.1, 0.1)]
    t = build(rows, {"A": 100.0, "B": 100.0 - 1e-6})
    assert t.loc[pd.Period("2025-01", "M"), "value"] == pytest.approx(1.0)  # A at threshold counts, cheaper B not
    assert t.loc[pd.Period("2025-01", "M"), "model"] == "A"


def test_price_first_seen_after_month_end_does_not_count():
    rows = [("2025-01-20", "a-1", "openai", 4.0, 4.0),
            ("2025-02-01", "a-1", "openai", 4.0, 4.0), ("2025-02-01", "b-1", "openai", 1.0, 1.0)]
    t = build(rows, {"A": 120.0, "B": 120.0}, end="2025-02-28")
    assert t.loc[pd.Period("2025-01", "M"), "value"] == pytest.approx(4.0)
    assert t.loc[pd.Period("2025-02", "M"), "value"] == pytest.approx(1.0)


def test_month_end_state_is_used():
    # price cut mid-month, then raised again before month end: the month-end snapshot counts
    rows = [("2025-01-15", "a-1", "openai", 1.0, 1.0), ("2025-01-31", "a-1", "openai", 2.0, 2.0)]
    t = build(rows, {"A": 120.0}, end="2025-01-31")
    assert t["value"].tolist() == pytest.approx([2.0])


def test_only_complete_months_and_no_value_without_qualifying_model():
    rows = [("2024-12-20", "a-1", "openai", 1.0, 1.0)]
    t = build(rows, {"A": 120.0}, end="2025-03-30")  # March not complete
    # December 2024: A not released yet (2025-01-10) -> no value; Jan, Feb complete
    assert [str(p) for p in t.index] == ["2025-01", "2025-02"]


def test_reseller_row_with_mapped_key_is_excluded():
    rows = [("2025-01-20", "a-1", "azure", 0.01, 0.01), ("2025-01-20", "b-1", "openai", 2.0, 2.0)]
    t = build(rows, {"A": 120.0, "B": 120.0})
    assert t.iloc[0]["key"] == "b-1"


def test_rolling_alias_follows_latest_released_model():
    cap = {"A": 90.0, "C": 130.0}
    rows = [(d, "alias", "openai", 1.0, 1.0) for d in ("2025-01-20", "2025-02-20", "2025-03-20")]
    t = build(rows, cap, end="2025-03-31")
    # before C's release the alias serves A (below threshold); from 2025-03-15 it serves C
    assert [str(p) for p in t.index] == ["2025-03"]
    assert t.iloc[0]["model"] == "C"
    kc = pc.key_capability({"A": 90.0}, RELEASE, T("2025-03-31"), MAPPING)
    assert "alias" not in kc  # the served model (C) has no known capability -> the key has none


def test_gpqa_capability_uses_run_dates():
    runs = epoch_capability.parse_gpqa(
        pd.DataFrame({"Model version": ["x_high", "x_low"], "Organization": ["O", "O"],
                      "Release date": ["2024-12-01", "2024-12-01"], "mean_score": [0.8, 0.6],
                      "Started at": ["2025-01-27T00:00:00.000Z", "2025-01-02T10:00:00.000Z"]}),
        pd.DataFrame({"model_version": ["x_high", "x_low"], "model_group": ["X", "X"]}))
    assert runs["known_from"].tolist() == [T("2025-02-03"), T("2025-01-09")]
    at = pc.capability_gpqa(runs)
    assert at(T("2025-01-31")) == {"X": 0.6}  # the high-effort run is not known yet
    assert at(T("2025-02-28")) == {"X": 0.8}


def test_eci_capability_uses_release_date():
    eci = epoch_capability.parse_eci(pd.DataFrame({"Model": ["A", "B"], "Organization": ["O", "O"],
                                                   "date": ["2025-01-10", "2025-05-01"], "eci": [140.0, 150.0]}))
    assert pc.capability_eci(eci)(T("2025-02-28")) == {"A": 140.0}


# ------------------------------------------------------------------ mapping


def test_mapping_is_valid():
    assert model_map.problems() == []


@pytest.mark.parametrize("key,provider,ok", [
    ("o3-2025-04-16", "openai", True), ("azure/o3-mini-2025-01-31", "openai", False),
    ("openrouter/openai/o1-mini", "openai", False), ("gemini/gemini-2.5-pro", "gemini", True),
    ("gemini-2.5-pro", "vertex_ai-language-models", False), ("gemini/gemini-flash-latest", "gemini", False),
    ("us/claude-opus-4-6", "anthropic", False), ("fast/claude-opus-4-6", "anthropic", False),
    ("deepseek-chat", "deepseek", True), ("deepseek/deepseek-chat", "deepseek", True),
    ("dashscope/deepseek-v4-pro", "dashscope", True),  # passes the key rule but is not in MODEL_MAP for DeepSeek
    ("together_ai/Qwen/Qwen3.6-27B", "together_ai", False), ("meta/muse-spark-1.2-contributor", "meta", False),
])
def test_first_party_rule(key, provider, ok):
    assert model_map.is_first_party(key, provider) is ok


def test_mapping_uses_developer_channel_only():
    km = model_map.key_models()
    assert not km["key"].str.startswith("dashscope/deepseek").any()  # Alibaba reselling DeepSeek
    assert set(km.loc[km["model"].str.startswith("Claude"), "provider"]) == {"anthropic"}
    assert set(km.loc[km["model"].str.startswith("Gemini"), "provider"]) == {"gemini"}
    assert model_map.MODEL_MAP["o1"] == ("openai", ("o1-2024-12-17", "o1"))


def test_problems_catches_bad_mapping():
    bad = {"X": ("openai", ("azure/x",)), "Y": ("openai", ()), "Z1": ("openai", ("k",)), "Z2": ("openai", ("k",))}
    text = " ".join(model_map.problems(bad))
    assert "not first-party" in text and "no keys" in text and "not a rolling alias" in text


# ------------------------------------------------------------------ register and catalog


def test_thresholds_are_written_in_the_register():
    reg = (config.REPO / "docs" / "mattregister.md").read_text(encoding="utf-8")
    section = reg[reg.index("## Ändringar"):]
    assert re.search(r"141,16", section) and re.search(r"0,767676", section)
    assert pc.ECI_THRESHOLD == 141.16 and pc.GPQA_THRESHOLD == 0.767676


def test_specs_in_catalog():
    specs = catalog.by_key()
    for key in ("g2_price_at_capability", "g2_price_at_capability_gpqa"):
        s = specs[key]
        assert (s.branch, s.freq, s.lag_days, s.revised) == ("G2", "M", 0, True)
        assert "MIT" in s.license and "CC BY" in s.license
