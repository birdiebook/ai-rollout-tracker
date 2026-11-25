"""Review R24 (docs/granskning/r24-tillstandsregeln.md): independent checks of T1's test of the state rule
(state/evaluate.py, register 2026-11-25 "T1").

Passing tests pin properties that hold. A strict xfail marks every confirmed defect: it fails while the defect is
there and turns into a failure (XPASS) when it is fixed, so the fix track removes the marker.
Synthetic fixtures, no network. The real-data checks (marked real_data) skip without the observation table.
"""

from __future__ import annotations

import re
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
import test_state_evaluate as TE
from conftest import real_table_exists

from ai_tracker import catalog, config, observations
from ai_tracker.state import branch as B
from ai_tracker.state import evaluate as EV
from ai_tracker.state import measures as M
from ai_tracker.state import register as R

RESULT_DOC = config.REPO / "docs" / "resultat" / "t1_tillstandsregeln.md"
FETCHED = pd.Timestamp("2026-11-23")


# ------------------------------------------------------------------ helpers


def literal_today(table: pd.DataFrame, month, vintage) -> pd.DataFrame:
    """'Today's data for month m' built literally for one month (register (a)): per series the periods with a row
    known on m, each with the value and source of its latest row known on V; known_from = the month end m."""
    when = EV.month_end(month)
    t = table[table["known_from"] <= pd.Timestamp(vintage)].sort_values(["series", "period", "known_from"],
                                                                         kind="mergesort")
    known = t[t["known_from"] <= when][["series", "period"]].drop_duplicates()
    latest = t.drop_duplicates(["series", "period"], keep="last")
    return latest.merge(known, on=["series", "period"]).assign(known_from=when).reset_index(drop=True)


def rows(key, freq, periods, values, known_from, source="release"):
    return pd.DataFrame({"series": key, "freq": freq, "period": [str(p) for p in periods],
                         "value": np.asarray(values, float), "known_from": pd.DatetimeIndex(known_from),
                         "source": source, "fetched_at": FETCHED})


def spec(key, freq, unit="MUSD", branch="G5"):
    return catalog.Spec(key=key, branch=branch, label=key, unit=unit, freq=freq, source="test",
                        fetch=lambda: pd.Series(dtype=float), lag_days=0, license="test")


def mixed_world(seed: int = 3):
    """G5 with a derived quarterly share (both components revised), a weekly series and a monthly series, all with
    a second vintage that arrives inside the window."""
    rng = np.random.default_rng(seed)
    q = pd.period_range("2010Q1", "2017Q4", freq="Q-DEC")
    qe = pd.DatetimeIndex(q.end_time.normalize())
    num = 100 * np.exp(np.cumsum(0.03 + 0.05 * rng.standard_normal(len(q))))
    den = 300 * np.exp(np.cumsum(0.02 + 0.03 * rng.standard_normal(len(q))))
    w = pd.period_range("2012-01-02", "2017-12-31", freq="W-SUN")
    we = pd.DatetimeIndex(w.end_time.normalize())
    wk = 50 * np.exp(np.cumsum(0.003 + 0.03 * rng.standard_normal(len(w))))
    mo = pd.period_range("2010-01", "2017-12", freq="M")
    me = pd.DatetimeIndex(mo.end_time.normalize())
    mv = 80 * np.exp(np.cumsum(0.01 + 0.03 * rng.standard_normal(len(mo))))
    parts = [
        rows("syn_num", "Q", q, num, qe + pd.Timedelta(days=30)),
        rows("syn_num", "Q", q, num * np.exp(0.08 * rng.standard_normal(len(q))), qe + pd.Timedelta(days=300)),
        rows("syn_den", "Q", q, den, qe + pd.Timedelta(days=40)),
        rows("syn_den", "Q", q, den * np.exp(0.05 * rng.standard_normal(len(q))), qe + pd.Timedelta(days=200)),
        rows("syn_w", "W", w, wk, we + pd.Timedelta(days=3)),
        rows("syn_w", "W", w, wk * np.exp(0.10 * rng.standard_normal(len(w))), we + pd.Timedelta(days=120)),
        rows("syn_m", "M", mo, mv, me + pd.Timedelta(days=15)),
        rows("syn_m", "M", mo, mv * np.exp(0.06 * rng.standard_normal(len(mo))), me + pd.Timedelta(days=150)),
    ]
    specs = {s.key: s for s in (spec("syn_num", "Q"), spec("syn_den", "Q"),
                                spec("syn_w", "W", unit="nedladdningar per vecka"), spec("syn_m", "M"))}
    return {"table": pd.concat(parts, ignore_index=True), "specs": specs,
            "core": {"G5": ["syn_ratio", "syn_w", "syn_m"]},
            "derived": {"syn_ratio": ("syn_num", "syn_den", 100.0, "share", "Q", "G5")}, "families": {},
            "forecasts": config.REPO / "no-forecasts-here"}


@pytest.fixture(scope="module")
def persistent_run():
    ctx, br = TE.world("persistent")
    return EV.run(ctx, start=TE.START, end=TE.END, vintage=TE.VINTAGE, n_perm=199, branches=br)


@pytest.fixture(scope="module")
def random_run():
    ctx, br = TE.world("random", seed=7)  # a seed where both horizons have >= 20 predictions (tested)
    return EV.run(ctx, start=TE.START, end=TE.END, vintage=TE.VINTAGE, n_perm=199, branches=br)


# ------------------------------------------------------------------ point 2: today's data for month m


def test_revised_table_equals_the_literal_definition_for_derived_weekly_and_monthly_series():
    """R24 point 2: as_of(m) on revised_table = 'the periods known at m with their latest vintage', also for a
    derived ratio (both components revised) and a weekly (sub-monthly) series. Records compared in full."""
    w = mixed_world()
    ctx = M.Context(**w)
    rctx = EV.revised_context(ctx, "2019-12-31")
    months = list(pd.period_range("2016-01", "2017-06", freq="M"))
    rt = EV.records(ctx, months, ["G5"])
    rv = EV.records(rctx, months, ["G5"])
    differs = 0
    for m in months:
        lit = M.Context(**{**w, "table": literal_today(w["table"], m, "2019-12-31")})
        assert EV.records(lit, [m], ["G5"])[("G5", str(m))] == rv[("G5", str(m))], m
        differs += rt[("G5", str(m))] != rv[("G5", str(m))]
    assert differs > 0  # the revisions change something, so the comparison is not empty


def test_revised_state_never_uses_rows_known_after_the_vintage():
    w = mixed_world()
    late = w["table"].copy()
    late["value"] = late["value"] * 50 + 3
    late["known_from"] = pd.Timestamp("2020-01-01")  # after V
    a = EV.records(EV.revised_context(M.Context(**w), "2019-12-31"), [pd.Period("2016-09", "M")], ["G5"])
    wl = {**w, "table": pd.concat([w["table"], late], ignore_index=True)}
    b = EV.records(EV.revised_context(M.Context(**wl), "2019-12-31"), [pd.Period("2016-09", "M")], ["G5"])
    assert a == b


def test_gate_on_todays_data_can_open_when_backfilled_history_is_revised_and_the_run_reports_it():
    """R24-5 (note): own_months on the revised table counts the first known_from of periods whose latest row is
    not backfill. A backfilled history revised later by non-backfill rows then looks like old own snapshots, and the
    gated series counts in 'today's data' while it is gated in real time. The registered report catches it."""
    key = "g9_epoch_notable_models"  # a real gated key (rule_for reads R.BACKFILL_GATED), monthly, no override
    assert key in R.BACKFILL_GATED and key not in R.METHOD_OVERRIDES
    rng = np.random.default_rng(5)
    mo = pd.period_range("2012-07", "2017-12", freq="M")
    me = pd.DatetimeIndex(mo.end_time.normalize())
    v = 100 * np.exp(np.cumsum(0.01 + 0.03 * rng.standard_normal(len(mo))))
    gated = pd.concat([rows(key, "M", mo, v, me + pd.Timedelta(days=10), source="backfill"),
                       rows(key, "M", mo, v * 1.01, [pd.Timestamp("2018-06-01")] * len(mo))], ignore_index=True)
    ctx, br = TE.world("persistent", branches=("G4",), extra=gated)
    ctx = TE.ctx_of(ctx.table, [*ctx.specs.values(), TE.spec(key, "G4")], {"G4": [*ctx.core["G4"], key]})
    res = EV.run(ctx, start="2016-01", end="2016-06", vintage="2019-12-31", n_perm=19, branches=br)
    assert res["gated_counted_months"]["realtime"] == 0
    assert res["gated_counted_months"]["revised"] > 0


# ------------------------------------------------------------------ point 2: outcome and persistence


@pytest.mark.parametrize("m", ["2016-03", "2016-09", "2017-03"])
def test_persistence_uses_only_the_vintage_at_m(m):
    """R24 point 2: the persistence baseline reads nothing after m (the T1 truncation test cuts at m + h only)."""
    ctx, br = TE.world("persistent")
    when = EV.month_end(m)
    cut = TE.ctx_of(ctx.table[ctx.table["known_from"] <= when].reset_index(drop=True), list(ctx.specs.values()),
                    ctx.core)
    later = ctx.table[ctx.table["known_from"] <= when].copy()
    later["value"] = later["value"] * 1000 + 7
    later["known_from"] = when + pd.Timedelta(days=1)
    wild = TE.ctx_of(pd.concat([ctx.table, later], ignore_index=True), list(ctx.specs.values()), ctx.core)
    for rec in EV.records(ctx, [pd.Period(m, "M")], br).values():
        for h in EV.HORIZONS:
            ref = EV.series_outcomes(EV.PathCache(ctx), rec, h)[1]
            assert EV.series_outcomes(EV.PathCache(cut), rec, h)[1] == ref
            assert EV.series_outcomes(EV.PathCache(wild), rec, h)[1] == ref
            assert any(u is not None for _, u in ref)


@pytest.mark.parametrize("accelerating,expected", [(True, 1), (False, -1)])
def test_doubling_time_outcome_has_the_registered_sign(accelerating, expected):
    """R24 point 2: a shorter doubling time is acceleration (sigma = -1), in the outcome as in the state."""
    key = "syn_g1_front"
    t = np.arange(84)
    slope = 0.02 + (0.0008 * t if accelerating else 0.08 - 0.0008 * t)
    df = TE.monthly(key, 1e20 * np.exp(np.cumsum(slope)), start="2010-01")
    ctx = TE.ctx_of(df, [TE.spec(key, "G1")], {"G1": [key]})
    assert M.rule_for(key, ctx).method == "doubling"
    meas, path = M.measure_path(key, "2016-06-30", ctx)
    assert meas["direction_sign"] == -1
    p_m = M.measure_path(key, "2015-12-31", ctx)[0]["latest_period"]
    u = EV.series_direction(EV.PathCache(ctx), key, meas["direction_sign"], p_m, "2016-06-30")
    raw = path.loc[path.index[-1], "pace"] - path.loc[p_m, "pace"]
    assert u == expected and np.sign(raw) == -expected


def test_persistence_at_h6_is_the_states_own_change_in_pace(persistent_run, random_run):
    """R24-1 (property): at h = 6 (= CHANGE_LAG for monthly series, 2 quarters for quarterly) the persistence
    direction of a series is the sign of its registered change in pace at m, the same comparison that gives the
    state its direction (only without the deadband). So H at h = 6 equals the persistence credit whenever no series
    sits in the deadband with a sign that flips the branch."""
    ctx, br = TE.world("random", seed=7)
    cache = EV.PathCache(ctx)
    n = 0
    for (code, month), rec in EV.records(ctx, list(pd.period_range("2015-06", "2017-06", freq="M")), br).items():
        _out, pers = EV.series_outcomes(cache, rec, 6)
        for s, (_f, u) in zip(rec["series"], pers):
            meas = M.measure(s["series"], EV.month_end(month), ctx)
            if u is None:
                continue
            assert u == int(np.sign(meas["direction_sign"] * meas["change_in_pace"])), (code, month, s["series"])
            n += 1
    assert n > 100
    for run in (persistent_run, random_run):
        t = run["b"]["v2"][EV.REGISTERED][6]
        assert t["H"] == pytest.approx(t["persistence_same"])


def test_in_the_persistent_world_the_registered_rule_recommends_review(persistent_run):
    """R24-1: even where the states carry information, persistence carries the same, so (b) is never 'godkänt'
    and condition 2 fires. The rule tests the state against its own unthresholded input."""
    d = persistent_run["decision"]
    assert d["b_not_above"] and d["review_recommended"] and not d["positive_result"]


# ------------------------------------------------------------------ point 3: permutation, Holm


def test_holm_family_is_one_rule_and_two_horizons(random_run):
    for rule in EV.RULES:
        t = random_run["b"][rule][EV.REGISTERED]
        ph = EV.holm({h: t[h]["p"] for h in EV.HORIZONS})
        pl = EV.holm({h: t[h]["p_low"] for h in EV.HORIZONS})
        for h in EV.HORIZONS:
            assert t[h]["p_holm"] == ph[h] and t[h]["p_low_holm"] == pl[h]
            k = t[h]["p"] * (random_run["n_perm"] + 1)
            assert abs(k - round(k)) < 1e-9 and 1 <= round(k) <= random_run["n_perm"] + 1  # (1 + #) / (N + 1)


def test_block_permutation_keeps_its_size_with_persistent_independent_sequences():
    """R24 point 3: predictions and outcomes are independent two-state Markov chains (stay probability 0.9, runs
    longer than the 6-month block). The one-sided test at 0.10 does not reject much more often than 10 %."""
    rng = np.random.default_rng(11)

    def chain(n, states):
        x = [rng.choice(states)]
        for _ in range(n - 1):
            x.append(x[-1] if rng.random() < 0.9 else rng.choice(states))
        return np.array(x)

    p = [EV.permutation_test([(chain(31, [1, 0]), chain(31, [1, -1])) for _ in range(5)], n_perm=99, seed=r)["p"]
         for r in range(150)]
    assert np.mean(np.array(p) < 0.10) <= 0.18


def test_v1_float_index_and_exact_reclassification_agree_for_every_small_count():
    """R24 point 'record()': the engine classifies v1 on a float, record() re-classifies exactly. They agree for
    every split of up to 60 counted series, so the self-check cannot raise spuriously or hide a disagreement."""
    accel, brake = EV.THRESHOLDS[EV.REGISTERED]
    for n in range(1, 61):
        for up in range(n + 1):
            for neutral in range(n - up + 1):
                dirs = [1] * up + [0] * neutral + [-1] * (n - up - neutral)
                exact = EV.classify(Fraction(2 * up + neutral, 2 * n), n, R.MIN_SERIES, R.STATE_FEW, accel, brake)
                assert B.state_of(B.diffusion(dirs), n) == exact, (n, up, neutral)


# ------------------------------------------------------------------ point 5: decision rule on the real numbers


def _decision(hits3: int):
    a = {"v2": {EV.REGISTERED: {"pooled": {"kappa": 0.8250886375147729, "hard_flips": 0.0}}}}
    p = {3: 0.1841, 6: 0.2605}
    ph, pl = EV.holm(p), EV.holm({3: 0.8201, 6: 0.7603})
    b = {"v2": {EV.REGISTERED: {
        3: {"H": hits3 / 57, "persistence_same": 40.0 / 57, "chance": 0.6815461407751414, "p": p[3],
            "p_holm": ph[3], "p_low_holm": pl[3]},
        6: {"H": 35 / 46, "persistence_same": 35.0 / 46, "chance": 0.7062963019804932, "p": p[6],
            "p_holm": ph[6], "p_low_holm": pl[6]}}}}
    return EV.decision(a, b)


def test_decision_on_the_real_numbers_turns_on_two_hits_at_h3():
    assert ph_round(EV.holm({3: 0.1841, 6: 0.2605})) == {3: 0.3682, 6: 0.3682}
    assert not _decision(42)["review_recommended"] and not _decision(41)["review_recommended"]
    d = _decision(40)
    assert d["review_recommended"] and d["b_not_above"] and not d["positive_result"]


def ph_round(d):
    return {k: round(v, 4) for k, v in d.items()}


# ------------------------------------------------------------------ point 6: the committed synthetic tests


@pytest.mark.xfail(strict=True, reason="R24-3: the committed random-world test holds for its seed (2), not in "
                                       "general: with seeds 1-40 it holds in 15, four of them with an untested "
                                       "horizon (n < 20)")
def test_committed_random_world_test_holds_for_another_seed():
    ctx, br = TE.world("random", seed=1)
    res = EV.run(ctx, start=TE.START, end=TE.END, vintage=TE.VINTAGE, n_perm=199, branches=br)
    TE.test_random_world_states_carry_no_information(res)


# ------------------------------------------------------------------ point 5: result text


def _paragraphs() -> list[str]:
    """Paragraphs and bullets of the result doc, whitespace collapsed (line breaks inside a sentence do not count)."""
    parts = re.split(r"\n\s*\n|\n- ", RESULT_DOC.read_text(encoding="utf-8"))
    return [" ".join(p.split()) for p in parts if p.strip()]


@pytest.mark.xfail(strict=True, reason="R24-1: the result doc reads H = persistence at h = 6 (and in G4/G5) as a "
                                       "finding; it is the same comparison by construction")
def test_result_doc_says_persistence_at_h6_is_the_state_by_construction():
    assert any("persistens" in p.lower() and "h = 6" in p and "konstruktion" in p for p in _paragraphs())


@pytest.mark.xfail(strict=True, reason="R24-2: the registered persistence over all months with an outcome "
                                       "(0,61 and 0,56) is not reported")
def test_result_doc_reports_persistence_over_all_months():
    assert any("persistens" in p.lower() and "alla månader" in p and "0,61" in p and "0,56" in p
               for p in _paragraphs())


@pytest.mark.xfail(strict=True, reason="R24-4: the pre-entry backcast file held the state, index and direction per "
                                       "series for every month, not only the counts")
def test_result_doc_discloses_what_the_pre_entry_backcast_file_held():
    text = RESULT_DOC.read_text(encoding="utf-8")
    start = text.index("**Synligt före posten:**")
    bullet = " ".join(text[start:text.index("\n- **", start)].split())
    assert "per månad" in bullet and "riktning" in bullet


# ------------------------------------------------------------------ real data (skipped without the table)


def needs_table(f):
    return pytest.mark.real_data(pytest.mark.skipif(not real_table_exists(), reason="no observation table")(f))


G67 = {"G6": R.core_entries("G6"), "G7": R.core_entries("G7")}


@pytest.fixture(scope="module")
def real():
    t = observations.load()
    keys = [k for ks in G67.values() for k in ks]
    t = t[t["series"].isin(keys) & (t["known_from"] <= pd.Timestamp(EV.VINTAGE))]
    missing = [k for k in keys if not (t["series"] == k).any()]
    if missing:
        pytest.skip(f"not in the table: {', '.join(missing)}")
    return t.reset_index(drop=True)


def _change_in_pace(t: pd.DataFrame, key: str, month: str, today: bool) -> tuple[float, int]:
    """Own computation: log x100 pace over 12 months, change over 6 months, deadband 0.25 x expanding SD."""
    g = t[t["series"] == key].sort_values("known_from", kind="mergesort")
    when = EV.month_end(month)
    known = set(g.loc[g["known_from"] <= when, "period"])
    g = g[g["period"].isin(known) & ((g["known_from"] <= when) | today)]
    s = g.groupby("period")["value"].last()
    s.index = pd.PeriodIndex(s.index, freq="M")
    x = s.reindex(pd.period_range(s.index.min(), s.index.max(), freq="M"))
    pace = 100 * np.log(x) - 100 * np.log(x.shift(12))
    ch = pace - pace.shift(6)
    band = 0.25 * float(np.std(ch.dropna(), ddof=1))
    c = float(ch.iloc[-1])
    return c, (1 if c > band else -1 if c < -band else 0)


@needs_table
@pytest.mark.parametrize("key,month,rt,td", [("us_ip_computers_m", "2025-10", (-0.4, 0), (-11.6, -1)),
                                             ("us_ip_semis_m", "2025-10", (2.0, 0), (-4.6, -1)),
                                             ("us_elec_sales_com_az_m", "2025-06", (4.5, 1), (-9.5, -1)),
                                             ("us_elec_sales_com_ga_m", "2025-06", (5.4, 1), (-4.5, -1))])
def test_real_hand_checks_in_the_result_doc(real, key, month, rt, td):
    for today, (value, direction) in ((False, rt), (True, td)):
        c, d = _change_in_pace(real, key, month, today)
        assert round(c, 1) == value and d == direction, (key, month, today, c, d)


@needs_table
@pytest.mark.parametrize("month,code,realtime,revised", [("2025-10", "G6", "stabil", "bromsar in"),
                                                         ("2025-06", "G7", "accelererar", "stabil"),
                                                         ("2024-05", "G6", "stabil", "accelererar")])
def test_real_literal_todays_data_gives_the_reported_change(real, month, code, realtime, revised):
    ctx = M.Context(real)
    lit = M.Context(literal_today(real, month, EV.VINTAGE))
    when = EV.month_end(month)
    assert B.branch(code, when, ctx)["state"] == realtime
    assert B.branch(code, when, lit)["state"] == revised
    assert EV.records(EV.revised_context(ctx, EV.VINTAGE), [pd.Period(month, "M")], [code])[(code, month)]["state_v2"] \
        == revised


def test_review_doc_exists_and_names_every_correction():
    text = (config.REPO / "docs" / "granskning" / "r24-tillstandsregeln.md").read_text(encoding="utf-8")
    for k in ("R24-1", "R24-2", "R24-3", "R24-4", "R24-5", "R24-6"):
        assert f"| {k} |" in text, k
