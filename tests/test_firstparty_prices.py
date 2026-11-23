"""B5: first-party price snapshots, the LiteLLM cross-check and the own-snapshot G2 series (fixtures, no network)."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest

from ai_tracker import catalog
from ai_tracker.series import firstparty_prices as series
from ai_tracker.series import price_capability as pc
from ai_tracker.sources import firstparty_prices as fp
from ai_tracker.sources import model_map


@pytest.fixture(autouse=True)
def _anthropic_collected(monkeypatch, request):
    """The collector logic is tested as if Anthropic were collected; in production it is paused (see below)."""
    if request.node.name == "test_anthropic_is_paused_pending_owner_decision":
        return
    from dataclasses import replace

    providers = dict(fp.PROVIDERS)
    providers["anthropic"] = replace(providers["anthropic"], status="OK")
    monkeypatch.setattr(fp, "PROVIDERS", providers)


def test_anthropic_is_paused_pending_owner_decision():
    assert fp.PROVIDERS["anthropic"].status == "BLOCKED" and fp.collected() == []

T = pd.Timestamp

# Shape of platform.claude.com/docs/en/about-claude/pricing.md as fetched 2026-11-23 (rows abridged).
PAGE = """---
title: Pricing
---

Intro.

## Model pricing

The following table shows pricing for all Claude models:

| Model | Base input tokens | 5m cache writes | 1h cache writes | Cache hits and refreshes | Output tokens |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Claude Fable 5.2 | $8 / MTok | $10 / MTok | $16 / MTok | $0.20 / MTok<sup>1</sup> | $40 / MTok |
| Claude Mythos 5.2 ([limited availability](https://support.claude.com/x)) | $8 / MTok | $10 / MTok | $16 / MTok | $0.20 / MTok<sup>1</sup> | $40 / MTok |
| Claude Opus 5.5 | $4 / MTok | $5 / MTok | $8 / MTok | $0.20 / MTok<sup>2</sup> | $20 / MTok |
| Claude Opus 4.1 ([retired, except on Bedrock](https://platform.claude.com/d)) | $15 / MTok | $18.75 / MTok | $30 / MTok | $1.50 / MTok | $75 / MTok |
| Claude Sonnet 5 | $2 / MTok<sup>3</sup> | $2.50 / MTok | $4 / MTok | $0.20 / MTok | $10 / MTok<sup>3</sup> |
| Claude Haiku 5.5 (for prompts up to 100,000 tokens) | $0.10 / MTok | $0.125 / MTok | $0.20 / MTok | $0.01 / MTok | $0.50 / MTok |
| Claude Haiku 5.5 (for prompts over 100,000 tokens) | $0.50 / MTok | $0.625 / MTok | $1 / MTok | $0.05 / MTok | $2.50 / MTok |

*<sup>1 footnote</sup>*

## Cloud platform pricing

| Model | Base input tokens | Output tokens |
| :---- | :---- | :---- |
| Claude Opus 5.5 | $99 / MTok | $99 / MTok |
"""


# ------------------------------------------------------------------ parser


def test_parse_anthropic_rows_tiers_and_availability():
    df = fp.parse_anthropic(PAGE).set_index(["model", "tier"])
    assert len(df) == 7  # only the "Model pricing" table, not the cloud table below it
    assert df.loc[("Claude Opus 5.5", ""), ["input_per_m", "output_per_m"]].tolist() == [4.0, 20.0]
    assert df.loc[("Claude Sonnet 5", ""), ["input_per_m", "output_per_m"]].tolist() == [2.0, 10.0]  # <sup> stripped
    assert df.loc[("Claude Mythos 5.2", ""), "availability"] == "limited"
    assert df.loc[("Claude Opus 4.1", ""), "availability"] == "retired"
    assert df.loc[("Claude Fable 5.2", ""), "availability"] == "available"
    base = df.loc[("Claude Haiku 5.5", "for prompts up to 100,000 tokens")]
    over = df.loc[("Claude Haiku 5.5", "for prompts over 100,000 tokens")]
    assert bool(base["base_tier"]) and not bool(over["base_tier"])
    assert base["input_per_m"] == pytest.approx(0.10) and over["output_per_m"] == pytest.approx(2.5)


@pytest.mark.parametrize("page", [
    PAGE.replace("## Model pricing", "## Prices"),  # section renamed
    PAGE.replace("Base input tokens", "Input"),  # column renamed
    PAGE.replace("| Claude Opus 5.5 | $4 / MTok", "| Claude Opus 5.5 | four dollars", 1),  # price not parseable
    PAGE.replace("| Claude Opus 5.5 | $4 / MTok", "| Claude Opus 5.5 | $40 / MTok", 1),  # input > output
    PAGE.replace("| $10 / MTok<sup>3</sup> |", "| $10 / MTok<sup>3</sup> | extra |"),  # cell count changed
])
def test_parse_anthropic_fails_loudly_on_layout_change(page):
    with pytest.raises(fp.ParseError):
        fp.parse_anthropic(page)


# ------------------------------------------------------------------ registry and snapshots


def test_blocked_providers_are_never_fetched():
    assert [p.developer for p in fp.collected()] == ["anthropic"]
    for p in fp.PROVIDERS.values():
        assert p.status in {"OK", "BLOCKED"} and p.reason and p.checked
        assert (p.parser is None) == (p.status == "BLOCKED")
        assert p.litellm_provider in model_map.FIRST_PARTY


def test_take_snapshot_appends_once_per_day(tmp_path):
    store = tmp_path / "snapshots.parquet"
    calls = []

    def get(url):
        calls.append(url)
        return PAGE

    now = datetime(2026, 11, 23, 23, 30, tzinfo=timezone.utc)
    assert fp.take_snapshot(store, now=now, get=get) == {"anthropic": "ok 7 rows"}
    assert fp.take_snapshot(store, now=now, get=get) == {"anthropic": "already taken today"}
    assert len(calls) == 1
    later = datetime(2026, 11, 30, 4, 17, tzinfo=timezone.utc)
    fp.take_snapshot(store, now=later, get=get)
    df = fp.load(store)
    assert sorted(df["snapshot_date"].unique()) == [T("2026-11-23"), T("2026-11-30")]
    assert df["fetched_at"].max() == T("2026-11-30 04:17")
    assert df["sha256"].str.len().eq(64).all() and df["url"].eq(fp.PROVIDERS["anthropic"].url).all()


def test_take_snapshot_reports_failure_and_writes_nothing(tmp_path):
    store = tmp_path / "snapshots.parquet"
    status = fp.take_snapshot(store, now=datetime(2026, 11, 23, tzinfo=timezone.utc), get=lambda url: "<html/>")
    assert status["anthropic"].startswith("FAILED: ParseError")
    assert not store.exists()


# ------------------------------------------------------------------ cross-check


def test_crosscheck_match_mismatch_missing():
    rows = fp.parse_anthropic(PAGE)
    lite = [("claude-opus-5-5", "anthropic", 4.0, 20.0), ("claude-sonnet-5", "anthropic", 3.0, 15.0),
            ("claude-fable-5-2", "anthropic", 8.0, 40.0), ("claude-haiku-5-5", "anthropic", 0.09999999999999999, 0.5),
            ("claude-mythos-5-2", "anthropic", 8.0, 40.0),
            ("bedrock/claude-opus-4-1", "bedrock", 15.0, 75.0)]  # reseller rows are ignored
    cc = fp.crosscheck(rows, lite).set_index("key")
    assert cc.loc["claude-opus-5-5", "status"] == "match"
    assert cc.loc["claude-haiku-5-5", "status"] == "match"  # float noise in LiteLLM's per-token price
    assert cc.loc["claude-sonnet-5", "status"] == "mismatch"
    assert cc.loc["claude-mythos-5-2", "status"] == "match"  # not an Epoch model: LiteLLM naming convention
    assert set(cc.loc[cc["model"] == "Claude Opus 4.1", "status"]) == {"missing in LiteLLM"}
    assert "Claude Haiku 5.5" in set(cc["model"]) and len(cc[cc["model"] == "Claude Haiku 5.5"]) == 1  # base tier


def test_litellm_key_candidates():
    assert fp.litellm_key_candidates("Claude Opus 4.7") == ["claude-opus-4-7-20260416", "claude-opus-4-7"]
    assert fp.litellm_key_candidates("Claude Mythos 5.1") == ["claude-mythos-5-1"]


# ------------------------------------------------------------------ series


def store(*snaps):
    """snaps: (snapshot_date, page)."""
    out = [fp.snapshot_rows(fp.PROVIDERS["anthropic"], page, T(day)) for day, page in snaps]
    return pd.concat(out, ignore_index=True)


CAP = {"Claude Haiku 5.5": 0.80, "Claude Sonnet 5": 0.90, "Claude Opus 5.5": 0.94, "Claude Opus 4.1": 0.99,
       "Claude Fable 5.2": 0.96}


def build(s, capability=CAP, end="2027-01-31", threshold=pc.GPQA_THRESHOLD):
    return series.build(s, "anthropic", lambda when: capability, threshold, T(end)).set_index("period")


def test_series_month_value_known_from_and_exclusions():
    t = build(store(("2026-11-23", PAGE)), end="2026-11-30")
    nov = t.loc[pd.Period("2026-11", "M")]
    assert nov["model"] == "Claude Haiku 5.5"  # base tier 0.10/0.50, not the >100k tier
    assert nov["value"] == pytest.approx(pc.blended(0.10, 0.50))
    assert nov["known_from"] == T("2026-12-01")
    # Opus 4.1 (retired) and Mythos (limited, no Epoch name) never count, also with high capability
    assert nov["n_qualifying"] == 4


def test_series_incomplete_month_and_capability_below_threshold():
    assert build(store(("2026-11-23", PAGE)), end="2026-11-29").empty  # November not complete
    low = dict(CAP, **{"Claude Haiku 5.5": 0.70})
    t = build(store(("2026-11-23", PAGE)), capability=low, end="2026-11-30")
    assert t.iloc[0]["model"] == "Claude Sonnet 5"


def test_series_uses_latest_snapshot_and_no_stale_carry_forward():
    cheaper = PAGE.replace("| Claude Haiku 5.5 (for prompts up to 100,000 tokens) | $0.10 / MTok",
                           "| Claude Haiku 5.5 (for prompts up to 100,000 tokens) | $0.05 / MTok")
    s = store(("2026-11-23", PAGE), ("2026-11-30", cheaper), ("2026-12-28", PAGE))
    t = build(s, end="2027-01-31")
    assert t.loc[pd.Period("2026-11", "M"), "value"] == pytest.approx(pc.blended(0.05, 0.50))
    assert t.loc[pd.Period("2026-12", "M"), "snapshot_date"] == T("2026-12-28")
    # January has no snapshot within 7 days before its end: no value, not December's state
    assert pd.Period("2027-01", "M") not in t.index
    s2 = store(("2026-11-23", PAGE))
    assert pd.Period("2026-12", "M") not in build(s2, end="2026-12-31").index


def test_series_capability_as_known_at_month_end():
    runs = pd.DataFrame({"model": ["Claude Haiku 5.5", "Claude Haiku 5.5", "Claude Sonnet 5"],
                         "score": [0.70, 0.90, 0.80],
                         "known_from": [T("2026-10-01"), T("2026-12-05"), T("2026-10-01")]})
    t = series.build(store(("2026-11-23", PAGE), ("2026-12-28", PAGE)), "anthropic", pc.capability_gpqa(runs),
                     pc.GPQA_THRESHOLD, T("2026-12-31")).set_index("period")
    assert t.loc[pd.Period("2026-11", "M"), "model"] == "Claude Sonnet 5"  # Haiku's 0.90 run known only in December
    assert t.loc[pd.Period("2026-12", "M"), "model"] == "Claude Haiku 5.5"


def test_epoch_names_resolve_for_all_available_models():
    rows = fp.parse_anthropic(PAGE)
    avail = rows[rows["availability"] == "available"]["model"].unique()
    assert all(series.epoch_model("anthropic", m) for m in avail)
    assert series.epoch_model("anthropic", "Claude Mythos 5.2") is None
    assert series.epoch_model("anthropic", "GPT-5.5") is None  # an Epoch model, but not Anthropic's


def test_spec_in_catalog():
    spec = catalog.by_key()["g2_fp_price_at_capability_gpqa_anthropic"]
    assert spec.freq == "M" and spec.branch == "G2" and not spec.publish and spec.lag_days == pc.LAG_DAYS
    assert series.LAG_DAYS == 1
