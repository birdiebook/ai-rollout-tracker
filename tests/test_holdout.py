"""Holdout opening for C3 and C4 (docs/holdout_logg.md): the guards, the F-E6 rule on the holdout, DF as a live
shadow (same model as the backtest) and the C4 section of the monthly snapshot (same rules as the stored sequence).
Synthetic fixtures only, no network."""

from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from ai_tracker import holdout
from ai_tracker.factor import guard
from ai_tracker.nowcast import df
from ai_tracker.regime import guard as regime_guard
from ai_tracker.regime import live as regime_live
from ai_tracker.regime import realtime as rt
from ai_tracker.state import snapshot as S

TS = pd.Timestamp


# ------------------------------------------------------------------ guards


def test_c3_and_c4_open_d2_closed():
    assert guard.HOLDOUT_OPEN and regime_guard.HOLDOUT_OPEN  # opened 2026-11-24, docs/holdout_logg.md
    assert "D2" not in guard.OPEN_FAMILIES
    guard.check("2026-10-20")
    regime_guard.check("2026-10-31")
    with pytest.raises(guard.HoldoutClosed):
        guard.check("2025-07-20", family="D2")


# ------------------------------------------------------------------ F-E6 on the holdout


def _frames(n_hold=17, df_gain=3.0, seed=0, b3_better=False):
    """Monthly frame 2021-01..2026-10 (origin day 5 of the next month, outcome known day 10)."""
    rng = np.random.default_rng(seed)
    idx = pd.period_range("2021-01", "2026-10", freq="M")
    origin = [(m + 1).start_time + pd.Timedelta(days=4) for m in idx]
    kf = [(m + 1).start_time + pd.Timedelta(days=9) for m in idx]
    e2 = rng.normal(0, 6, len(idx))
    f = pd.DataFrame({"origin": origin, "outcome_known_from": kf, "e_B0": e2 * 2, "e_B1": e2 * 1.6, "e_B2": e2,
                      "e_DF": e2 * (1 - df_gain / 10)}, index=idx)
    f["e_B3"] = e2 * (0.5 if b3_better else 0.95)
    f["df_capex"], f["df_demand"] = 0.1, -0.1
    hold = holdout.holdout_rows(f, "N2")
    keep = hold.cumsum() <= n_hold
    full = f[~hold | keep]
    dev = f[(pd.to_datetime(f["origin"]) <= guard.DEV_END) & (pd.to_datetime(f["outcome_known_from"]) <= guard.DEV_END)]
    return dev.drop(columns=["e_B3"]), full


def test_holdout_window_by_origin_until_first_live():
    _dev, full = _frames()
    h = full[holdout.holdout_rows(full, "N2")]
    assert str(h.index.min()) == "2025-06" and str(h.index.max()) == "2026-10"  # 2025-06: origin 2025-07-05 (F-E1)
    assert len(h) == 17  # F-E2: 2026-10 (origin 2026-11-05) is in the holdout, 2026-11 (2026-12-05) is live


def test_rule_passes_conditionally_and_uses_b3_registered_p():
    dev, full = _frames(df_gain=4.0, seed=1)
    r = holdout.evaluate_df("N2", dev, full)
    assert r["test"] and r["n"] == 17 and r["comparator"] == "B2"
    assert r["family_p"] == {"B3": 0.0294}
    p = r["dm_p"]
    assert r["holm"]["DF"] == pytest.approx(min(1.0, 2 * p) if p < 0.0294 else max(p, 2 * 0.0294))
    assert r["passed"] and r["beats_current_champion"] and r["outcome"] == "villkorad"


def test_rule_pass_against_comparator_but_not_champion_is_shadow():
    dev, full = _frames(df_gain=4.0, seed=1, b3_better=True)
    r = holdout.evaluate_df("N2", dev, full)
    assert r["passed"] and r["beats_current_champion"] is False and r["outcome"] == "skugga"


def test_rule_fails_when_df_is_worse():
    dev, full = _frames(df_gain=-3.0, seed=2)
    r = holdout.evaluate_df("N2", dev, full)
    assert r["test"] and not r["passed"] and r["outcome"] == "skugga"


def test_small_holdout_is_not_tested():
    dev, full = _frames(n_hold=7)
    r = holdout.evaluate_df("N2", dev, full)
    assert r["n"] == 7 and r["test"] is False and r["outcome"] == "skugga" and "dm_p" not in r


# ------------------------------------------------------------------ DF as a live shadow


class _FakeVintage:
    """mean_over depends on the origin and the months, so every origin has its own factor path."""

    def __init__(self, origin):
        self.o = pd.Timestamp(origin).toordinal()
        self.fits = {b: SimpleNamespace(keys=["a", "b"]) for b in df.BLOCKS}

    def mean_over(self, block, months):
        k = 1.0 if block == "capex" else -0.5
        return float(np.mean([np.sin(k * (m.ordinal + 0.001 * self.o)) for m in months]))


def _quarter_target(monkeypatch, frame):
    tgt = df.Target("T", "B1", ("B0", "B1"), ("DF",), pd.Period("2023Q1", "Q-DEC"), lambda t: frame,
                    df._quarter_months)
    monkeypatch.setitem(df.TARGETS, "T", tgt)
    return tgt


def _quarter_frame(n=30, seed=4):
    rng = np.random.default_rng(seed)
    idx = pd.period_range("2017Q1", periods=n, freq="Q-DEC")
    return pd.DataFrame({"origin": [q.end_time.normalize() + pd.Timedelta(days=20) for q in idx],
                         "outcome_known_from": [q.end_time.normalize() + pd.Timedelta(days=30) for q in idx],
                         "e_B0": rng.normal(0, 5, n), "e_B1": rng.normal(1, 4, n)}, index=idx)


def test_live_shadow_equals_the_backtest_row(monkeypatch):
    frame = _quarter_frame()
    tgt = _quarter_target(monkeypatch, frame)
    vf = lambda t, o: _FakeVintage(o)  # noqa: E731
    bt = df.run(tgt, pd.DataFrame({"known_from": []}), vintage_fn=vf, dev=False)
    p = frame.index[-1]
    o = frame.at[p, "origin"]
    table = pd.DataFrame({"known_from": [o]})
    live = df.live_shadow("T", table, o, p, 1000.0, vintage_fn=vf)
    rhat = bt.at[p, "e_DF"] - bt.at[p, "e_B1"]
    assert live["n_train"] == bt.at[p, "n_train"] >= df.MIN_TRAIN
    assert live["r_hat"] == pytest.approx(rhat)
    assert live["value"] == pytest.approx(1000.0 * np.exp(rhat / 100))


def test_live_shadow_ignores_rows_not_known_on_the_origin(monkeypatch):
    frame = _quarter_frame()
    _quarter_target(monkeypatch, frame)
    vf = lambda t, o: _FakeVintage(o)  # noqa: E731
    p = frame.index[-1]
    o = frame.at[p, "origin"]
    poisoned = frame.copy()
    poisoned.loc[frame.index[-2], "outcome_known_from"] = o + pd.Timedelta(days=1)
    a = df.live_shadow("T", pd.DataFrame({"known_from": [o]}), o, p, 1000.0, vintage_fn=vf)
    _quarter_target(monkeypatch, poisoned)
    b = df.live_shadow("T", pd.DataFrame({"known_from": [o]}), o, p, 1000.0, vintage_fn=vf)
    assert b["n_train"] == a["n_train"] - 1


def test_attach_live_records_failure_without_raising(monkeypatch):
    def boom(*a, **k):
        raise ValueError("no data")

    monkeypatch.setattr(df, "live_shadow", boom)
    pl = df.attach_live({"variants": {"B1": 1.0}}, "N1", pd.DataFrame(), "2026-10-20", pd.Period("2026Q3", "Q-DEC"),
                        {"B1": 1.0})
    assert pl["variants"]["DF"] is None and "no data" in pl["df"]["reason"]


def test_live_shadow_without_main_forecast():
    d = df.live_shadow("N1", pd.DataFrame({"known_from": []}), "2025-04-20", pd.Period("2025Q1", "Q-DEC"), None)
    assert d["value"] is None and "B1" in d["reason"]


# ------------------------------------------------------------------ C4 in the snapshot


def test_chained_state_rule_equals_the_stored_sequence():
    rng = np.random.default_rng(7)
    p = rng.choice([0.05, 0.1, 0.5, 0.85, 0.95, np.nan], size=80, p=[0.25, 0.15, 0.1, 0.2, 0.25, 0.05])
    dates = rt.month_ends("2018-01-31", "2024-08-31")
    ref = rt.state_sequence(pd.Series(p, index=pd.DatetimeIndex(dates)))
    state, prev = None, None
    for i, v in enumerate(p):
        state = regime_live.next_state(state, prev, v, consecutive=i > 0)
        assert state == ref.iloc[i], i
        prev = v


def test_chained_break_rule_equals_reported_breaks():
    rng = np.random.default_rng(3)
    rows = []
    for i, d in enumerate(rt.month_ends("2020-01-31", "2023-12-31")):
        rows.append({"date": d, "series": "m", "freq": "M", "latest_period": str(pd.Timestamp(d).to_period("M") - 1),
                     "p_recent": float(rng.choice([0.1, 0.9]))})
        q = (pd.Timestamp(d).to_period("Q") - 1)
        rows.append({"date": d, "series": "q", "freq": "Q", "latest_period": str(q),
                     "p_recent": float(rng.choice([0.1, 0.85]))})
    b = rt.reported_breaks(pd.DataFrame(rows))
    memory, flags = {}, []
    for r in rows:
        f = regime_live.is_break(r, memory)
        if f:
            memory[r["series"]] = {"period": r["latest_period"], "freq": r["freq"]}
        flags.append(f)
    ref = b.sort_values(["date", "series"])["break"].tolist()
    mine = pd.DataFrame(rows).assign(br=flags).sort_values(["date", "series"])["br"].tolist()
    assert mine == ref and any(ref)


def _rec(p_capex, p_demand, bocpd_rows=()):
    return {"ms": {"capex": {"p_slow": p_capex, "n_series": 20}, "demand": {"p_slow": p_demand, "n_series": 10}},
            "bocpd": list(bocpd_rows)}


@pytest.fixture
def c4_open(monkeypatch):
    monkeypatch.setattr(regime_guard, "HOLDOUT_OPEN", True)


def test_section_chains_on_previous_snapshot(monkeypatch, c4_open):
    monkeypatch.setattr(rt, "compute", lambda table, d: _rec(
        0.9, 0.1, [{"branch": "G7", "series": "s", "freq": "M", "latest_period": "2026-11", "p_recent": 0.9}]))
    prev = {"date": "2026-11-30", "chain": "x", "blocks": {"capex": {"p_inbromsning": 0.85, "state": "expansion"},
                                                           "demand": {"p_inbromsning": 0.5, "state": "inbromsning"}},
            "break_memory": {"s": {"period": "2026-09", "freq": "M"}}}
    s = regime_live.section(pd.DataFrame(), "2026-12-31", prev)
    assert s["blocks"]["capex"]["state"] == "inbromsning" and s["blocks"]["capex"]["shift"] == "inbromsning"
    assert s["blocks"]["demand"]["state"] == "inbromsning" and s["blocks"]["demand"]["shift"] is None
    assert s["breaks"] == []  # 2026-11 is within 3 months of the break at 2026-09
    assert s["chain"].startswith("föregående ögonblicksbild")
    # a month gap breaks the pair: the state is kept
    s2 = regime_live.section(pd.DataFrame(), "2027-01-31", prev)
    assert s2["blocks"]["capex"]["state"] == "expansion"


def test_first_section_uses_the_seed(monkeypatch, c4_open):
    monkeypatch.setattr(rt, "compute", lambda table, d: _rec(
        0.1, float("nan"), [{"branch": "G7", "series": "s", "freq": "M", "latest_period": "2026-10", "p_recent": 0.95}]))
    seed = lambda table, d: {"date": "2026-10-31", "chain": "rekonstruerad", "break_memory": {},  # noqa: E731
                             "blocks": {"capex": {"p_slow": 0.15, "state": "inbromsning"}}}
    s = regime_live.section(pd.DataFrame(), "2026-11-30", None, seed_fn=seed)
    assert s["blocks"]["capex"]["state"] == "expansion" and s["blocks"]["capex"]["shift"] == "expansion"
    assert s["blocks"]["demand"]["state"] is None and s["blocks"]["demand"]["p_inbromsning"] is None
    assert [b["series"] for b in s["breaks"]] == ["s"] and s["break_memory"]["s"]["period"] == "2026-10"


def test_snapshot_has_regime_section_from_first_live(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "compute", lambda when, ctx: {"G6": {"index": 1.0, "state": "x"}})
    monkeypatch.setattr(S, "reconciliations", lambda when, ctx: {})
    calls = []

    def fake(table, when, previous):
        calls.append((str(pd.Timestamp(when).date()), previous))
        return {"model": "C4", "blocks": {"capex": {"p_inbromsning": 0.3}}, "date": str(pd.Timestamp(when).date())}

    monkeypatch.setattr(regime_live, "section", fake)
    t = pd.DataFrame({"series": ["a"], "freq": ["M"], "period": ["2026-01"], "value": [1.0],
                      "known_from": [TS("2026-02-01")], "source": ["x"], "fetched_at": [TS("2026-02-01")]})
    p = S.write("2026-10-31", t, tmp_path, today="2026-12-31")
    assert regime_live.SECTION not in json.loads(p.read_text(encoding="utf-8")) and not calls
    p = S.write("2026-11-30", t, tmp_path, today="2026-12-31")
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d[regime_live.SECTION]["blocks"]["capex"]["p_inbromsning"] == 0.3 and calls[-1] == ("2026-11-30", None)
    S.write("2026-12-31", t, tmp_path, today="2026-12-31")
    assert calls[-1][1]["date"] == "2026-11-30"  # chained on the previous snapshot's section
    assert set(d["branches"]) == {"G6"}  # the branch states are untouched


def test_snapshot_regime_failure_is_recorded(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "compute", lambda when, ctx: {})
    monkeypatch.setattr(S, "reconciliations", lambda when, ctx: {})

    def boom(*a):
        raise RuntimeError("factor failed")

    monkeypatch.setattr(regime_live, "section", boom)
    t = pd.DataFrame({"series": ["a"], "freq": ["M"], "period": ["2026-01"], "value": [1.0],
                      "known_from": [TS("2026-02-01")], "source": ["x"], "fetched_at": [TS("2026-02-01")]})
    d = json.loads(S.write("2026-11-30", t, tmp_path, today="2026-12-31").read_text(encoding="utf-8"))
    assert "factor failed" in d[regime_live.SECTION]["error"]
