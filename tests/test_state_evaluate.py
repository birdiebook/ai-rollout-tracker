"""T1: the pre-registered test of the state rule (state.evaluate, register 2026-11-25). Synthetic data, no network."""

from __future__ import annotations

import functools
import json
import random
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest

from ai_tracker.state import __main__ as cli
from ai_tracker.state import branch as B
from ai_tracker.state import evaluate as EV
from ai_tracker.state import measures as M
from ai_tracker.state import register as R

FETCHED = pd.Timestamp("2026-11-23")
START, END, VINTAGE = "2014-07", "2017-12", "2019-12-31"


def spec(key, branch="G4"):
    from ai_tracker import catalog

    return catalog.Spec(key=key, branch=branch, label=key, unit="MUSD", freq="M", source="test",
                        fetch=lambda: pd.Series(dtype=float), lag_days=0, license="unverified")


def monthly(key, values, start="2012-07", lag_days=10, known_from=None):
    pi = pd.period_range(start, periods=len(values), freq="M")
    kf = (pd.DatetimeIndex(pi.end_time.normalize()) + pd.Timedelta(days=lag_days)) if known_from is None \
        else pd.DatetimeIndex([pd.Timestamp(known_from)] * len(values))
    return pd.DataFrame({"series": key, "freq": "M", "period": [str(p) for p in pi], "value": np.asarray(values, float),
                         "known_from": kf, "source": "release", "fetched_at": FETCHED})


def growth(kind: str, n: int, phase: float, rng) -> np.ndarray:
    t = np.arange(n)
    if kind == "persistent":  # pace follows a 48-month cycle: states hold for long runs and the outcome follows
        return (0.2 + 0.3 * np.sin(2 * np.pi * t / 48 + phase)) / 12 + 0.002 * rng.standard_normal(n)
    if kind == "random":  # the level is a random walk: the next change in pace is independent of the state
        return 0.01 + 0.03 * rng.standard_normal(n)
    raise ValueError(kind)


def world(kind: str, branches=("G4", "G5"), n: int = 90, seed: int = 1, extra=None):
    rng = np.random.default_rng(seed)
    tables, specs, core = [], [], {}
    for b, phase in zip(branches, (0.0, 1.7, 3.1)):
        keys = []
        for j in range(3):
            k = f"syn_{b.lower()}_{j}"
            g = growth(kind, n, phase + 0.15 * j, rng)
            tables.append(monthly(k, 100 * np.exp(np.cumsum(g))))
            specs.append(spec(k, b))
            keys.append(k)
        core[b] = keys
    if extra is not None:
        tables.append(extra)
    return ctx_of(pd.concat(tables, ignore_index=True), specs, core), list(core)


def ctx_of(table, specs, core):
    return M.Context(table, specs={s.key: s for s in specs}, core=core, derived={}, families={},
                     forecasts=M.config.REPO / "no-forecasts-here")


@pytest.fixture(scope="module")
def persistent():
    ctx, br = world("persistent")
    return EV.run(ctx, start=START, end=END, vintage=VINTAGE, n_perm=499, branches=br)


@pytest.fixture(scope="module")
def random_world():
    ctx, br = world("random", seed=2)
    return EV.run(ctx, start=START, end=END, vintage=VINTAGE, n_perm=499, branches=br)


# ------------------------------------------------------------------ the rule and the register


def test_classify_equals_the_engine_rule_at_the_registered_thresholds():
    rnd = random.Random(7)
    accel, brake = EV.THRESHOLDS[EV.REGISTERED]
    for _ in range(2000):
        n = rnd.randint(0, 12)
        x = Fraction(rnd.randint(0, 2 * max(n, 1)), 2 * max(n, 1))
        assert EV.classify(x, n, R.MIN_FAMILIES, R.STATE_FEW_FAMILIES, accel, brake) == B.state_v2(x, n)
        assert EV.classify(x, n, R.MIN_SERIES, R.STATE_FEW, accel, brake) == B.state_of(float(x), n)
    assert EV.classify(Fraction(2, 3), 3, 3, "f", accel, brake) == R.STATE_STABLE  # 0.667 < 0.67, compared exactly
    assert EV.classify(Fraction(3, 5), 3, 3, "f", *EV.THRESHOLDS["0,60/0,40"]) == R.STATE_ACCEL
    assert EV.classify(Fraction(7, 10), 3, 3, "f", *EV.THRESHOLDS["0,75/0,25"]) == R.STATE_STABLE


def test_registered_constants_are_in_the_register_entry():
    text = R.REGISTER_PATH.read_text(encoding="utf-8")
    i = text.index("### 2026-11-25 – T1: test av tillståndsregeln (förregistrering, före körning)")
    j = text.find("\n### ", i + 5)
    entry = text[i:] if j < 0 else text[i:j]
    for needle in ("2024-01 till 2026-10", "2026-11-25", "h ∈ {3, 6}", "om **6 månader**", "**9 999 permutationer**",
                   "**20261125**", "minst 20 prediktioner", "< **0,70**", "> **0,02**", "0,60/0,40", "0,75/0,25",
                   "{v2 h = 3, v2 h = 6}", "p_ned", "p < 0,10 vid minst en horisont", "till och med 2025-06"):
        assert needle in entry, needle
    assert (EV.START, EV.END, EV.VINTAGE, EV.HORIZONS, EV.BLOCK) == ("2024-01", "2026-10", "2026-11-25", (3, 6), 6)
    assert (EV.N_PERM, EV.SEED, EV.MIN_PRED, EV.ALPHA, EV.KAPPA_MIN, EV.HARD_FLIP_MAX) == \
        (9999, 20261125, 20, 0.10, 0.70, 0.02)
    assert EV.DEV_END == "2025-06" and set(EV.THRESHOLDS) == {"0,67/0,33", "0,60/0,40", "0,75/0,25"}
    assert EV.THRESHOLDS[EV.REGISTERED] == (Fraction(67, 100), Fraction(33, 100))


# ------------------------------------------------------------------ (a) today's data for month m


def test_revised_table_keeps_periods_known_at_m_with_their_latest_vintage():
    rows = pd.DataFrame({
        "series": "s", "freq": "M", "period": ["2020-01", "2020-01", "2020-01", "2020-02"],
        "value": [1.0, 2.0, 3.0, 5.0],
        "known_from": pd.to_datetime(["2020-02-10", "2020-06-01", "2021-01-05", "2020-03-10"]),
        "source": ["fetch", "revision", "revision", "fetch"], "fetched_at": FETCHED})
    rev = EV.revised_table(rows, "2020-12-31").set_index("period")
    assert rev.loc["2020-01", "value"] == 2.0 and rev.loc["2020-01", "known_from"] == pd.Timestamp("2020-02-10")
    assert rev.loc["2020-01", "source"] == "revision" and len(rev) == 2
    from ai_tracker import observations

    assert list(observations.as_of("s", "2020-02-29", EV.revised_table(rows, "2020-12-31"))) == [2.0]  # only Jan
    assert list(observations.as_of("s", "2020-03-31", EV.revised_table(rows, "2021-12-31"))) == [3.0, 5.0]


def test_no_revisions_give_full_agreement_and_no_exposure(persistent):
    for rule in EV.RULES:
        a = persistent["a"][rule][EV.REGISTERED]["pooled"]
        assert a["agree"] == 1.0 and a["kappa"] == pytest.approx(1.0) and a["hard_flips"] == 0.0
        assert a["exposed_series_share"] == 0.0 and a["mean_abs_index_diff"] == 0.0
    assert persistent["gated_counted_months"] == {"realtime": 0, "revised": 0}


def test_a_revision_changes_the_revised_state_exactly_as_the_definition_says():
    rng = np.random.default_rng(11)
    n = 90
    wild = monthly("syn_g4_0", 100 * np.exp(np.cumsum(0.01 + 0.05 * rng.standard_normal(n))),
                   known_from="2019-06-15")  # every value revised, known after the whole window
    ctx, br = world("persistent", branches=("G4",), extra=wild)
    res = EV.run(ctx, start=START, end=END, vintage=VINTAGE, n_perm=99, branches=br)
    a = res["a"]["v1"][EV.REGISTERED]["pooled"]
    assert a["exposed_series_share"] == pytest.approx(1 / 3)  # one of three counted series
    assert a["n_changed"] > 0 and a["agree"] < 1.0
    # the revised state for month m = the engine's state on the periods known at m with the revised values
    m = "2016-06"
    when = EV.month_end(m)
    t = ctx.table
    known = t[(t["series"] == "syn_g4_0") & (t["known_from"] <= when)]["period"].unique()
    manual = pd.concat([t[t["series"] != "syn_g4_0"],
                        wild[wild["period"].isin(known)].assign(known_from=pd.Timestamp("2000-01-01"))])
    mctx = ctx_of(manual, list(ctx.specs.values()), ctx.core)
    assert res["states"][f"G4 {m}"]["revised_v1"] == B.branch("G4", when, mctx)["v1"]["state"]


def test_kappa_and_agreement_on_known_examples():
    A, S, D, F = R.STATE_ACCEL, R.STATE_STABLE, R.STATE_BRAKE, R.STATE_FEW_FAMILIES
    assert EV.kappa([(A, A), (S, S), (D, D)]) == pytest.approx(1.0)
    assert EV.kappa([(A, A), (A, A)]) is None  # one category: expected agreement 1
    # 2x2: po = 0.5, pe = 0.5 -> kappa 0
    assert EV.kappa([(A, A), (A, S), (S, A), (S, S)]) == pytest.approx(0.0)
    g = EV.agreement([(A, D), (A, A), (F, F), (F, S), (S, S)])
    assert g["n_all"] == 5 and g["n"] == 4  # (för få, för få) is outside S
    assert g["n_hard"] == 1 and g["hard_flips"] == 0.25 and g["agree"] == 0.5


# ------------------------------------------------------------------ (b) outcome, baselines, permutation


def test_persistent_world_states_carry_information(persistent):
    for h in EV.HORIZONS:
        t = persistent["b"]["v2"][EV.REGISTERED][h]
        assert t["tested"] and t["n"] >= EV.MIN_PRED
        assert t["n_accel"] > 0 and t["n_brake"] > 0
        assert t["H"] > 0.7 and t["chance"] < 0.6 and t["p_holm"] < 0.05
        assert t["p_low_holm"] > 0.5


RANDOM_SEEDS = tuple(range(1, 11))  # R24-3: the size over many seeds, not one chosen seed
RANDOM_BRANCHES = ("G4", "G5", "G6")  # three branches: both horizons have >= 20 predictions in most seeds


@functools.lru_cache(maxsize=1)
def random_world_tests() -> tuple[dict, ...]:
    """The registered v2 test at h = 3 and 6 in the random world for every seed in RANDOM_SEEDS (199 permutations),
    with the registered Holm adjustment and the 'godkänt' criterion. Computed once per session."""
    months = list(pd.period_range(START, END, freq="M"))
    out = []
    for seed in RANDOM_SEEDS:
        ctx, br = world("random", branches=RANDOM_BRANCHES, seed=seed)
        rows = EV.information_rows(EV.records(ctx, months, br), EV.PathCache(ctx), END, br)
        tests = {h: EV.information(rows[h], "v2", EV.REGISTERED, br, 199) for h in EV.HORIZONS}
        ph = EV.holm({h: t["p"] for h, t in tests.items()})
        passed = [h for h, t in tests.items() if ph[h] < EV.ALPHA and t["H"] > (t["persistence_same"] or 0.0)]
        out.append({"seed": seed, "tests": tests, "p_holm": ph, "positive": bool(passed)})
    return tuple(out)


def test_random_world_states_carry_no_information(random_world):
    """R24-3: without information the registered test keeps its size over many seeds, and it actually runs. The run
    passed in (any seed) only has to be consistent: a horizon is tested exactly when it has >= 20 predictions."""
    for h in EV.HORIZONS:
        t = random_world["b"]["v2"][EV.REGISTERED][h]
        assert t["tested"] == (t["n"] >= EV.MIN_PRED)
        if not t["tested"]:
            assert t["p"] == 1.0 and t["p_low"] == 1.0
    runs = random_world_tests()
    tests = [t for r in runs for t in r["tests"].values()]
    tested = [t for t in tests if t["tested"]]
    assert len(tested) >= 0.8 * len(tests)  # the test ran in most seeds and horizons
    p = np.array([t["p"] for t in tested])
    p_low = np.array([t["p_low"] for t in tested])
    assert (p < 0.10).mean() <= 0.25 and (p_low < 0.10).mean() <= 0.25  # nominal 0.10 one-sided, each tail
    assert np.mean([t["H"] - t["chance"] for t in tested]) < 0.05  # no information on average
    assert sum(r["positive"] for r in runs) <= 2  # 'godkänt' at most rarely


def test_description_after_r24_constant_up_and_persistence_against_the_state(persistent):
    """R24-2 and R24-1 (description, decides nothing): the up share on the predicted months is the hit rate of a
    constant 'up' there, and at h = 6 (the change lag) persistence never points against the state."""
    for h in EV.HORIZONS:
        t = persistent["b"]["v2"][EV.REGISTERED][h]
        rows = [r for r in persistent["rows"][h]
                if r[f"pred_v2_{EV.REGISTERED}"] != 0 and r["outcome_v2"] not in (None, 0)]
        assert len(rows) == t["n"] == sum(t["persistence_vs_state"].values())
        assert t["up_share_predicted"] == pytest.approx(np.mean([r["outcome_v2"] == 1 for r in rows]))
    assert persistent["b"]["v2"][EV.REGISTERED][6]["persistence_vs_state"]["opposite"] == 0


def test_permutation_p_is_roughly_uniform_without_information():
    rng = np.random.default_rng(0)
    ps = np.array([EV.permutation_test([(rng.choice([-1, 0, 0, 1], 34), rng.choice([-1, 0, 1], 34)) for _ in range(9)],
                                       n_perm=199, seed=s)["p"] for s in range(60)])
    assert 0.0 < (ps < 0.1).mean() < 0.25 and 0.3 < (ps < 0.5).mean() < 0.7


def test_constant_states_cannot_be_detected_by_a_within_branch_permutation():
    pred = [np.ones(12, dtype=int), -np.ones(12, dtype=int)]
    out = [np.ones(12, dtype=int), -np.ones(12, dtype=int)]
    r = EV.permutation_test(list(zip(pred, out)), n_perm=99)
    assert r["H"] == 1.0 and r["p"] == 1.0  # every permutation gives the same hit rate


def test_block_order_keeps_blocks_whole_and_months_once():
    rng = np.random.default_rng(0)
    for n in (1, 6, 28, 31):
        o = EV.block_order(n, 6, rng)
        assert sorted(o) == list(range(n))
        starts = [i for i in range(n) if o[i] % 6 == 0]
        for s in starts:  # a block runs from a multiple of 6 to the next one (or the end)
            k = o[s]
            length = min(6, n - k)
            assert list(o[s:s + length]) == list(range(k, k + length))


def test_aggregate_uses_family_votes_and_exact_ties():
    assert EV.aggregate([("a", 1), ("a", -1), ("b", 1)], "v2") == 1  # votes 1/2 and 1 -> 3/4
    assert EV.aggregate([("a", 1), ("a", 1), ("b", -1)], "v2") is None  # votes 1 and 0 -> 1/2: no outcome
    assert EV.aggregate([("a", 1), ("a", 1), ("b", -1)], "v1") == 1  # 2/3
    assert EV.aggregate([("a", None), ("b", None)], "v1") is None
    assert EV.aggregate([("a", 0), ("b", -1)], "v2") == -1


@pytest.mark.parametrize("m,h", [("2016-03", 3), ("2016-06", 6), ("2017-01", 3)])
def test_outcome_at_m_plus_h_is_unchanged_when_the_table_is_cut_there(m, h):
    ctx, br = world("persistent")
    t_end = EV.month_end(pd.Period(m, freq="M") + h)
    cut = ctx_of(ctx.table[ctx.table["known_from"] <= t_end].reset_index(drop=True), list(ctx.specs.values()), ctx.core)
    cut_m = ctx_of(ctx.table[ctx.table["known_from"] <= EV.month_end(m)].reset_index(drop=True),
                   list(ctx.specs.values()), ctx.core)
    full_rec = EV.records(ctx, [pd.Period(m, freq="M")], br)
    assert EV.records(cut_m, [pd.Period(m, freq="M")], br) == full_rec  # the state at m uses as_of(m) only
    future = ctx.table[ctx.table["known_from"] <= t_end].copy()
    future["value"] = future["value"] * 1000 + 7  # a wild revision of everything ...
    future["known_from"] = t_end + pd.Timedelta(days=1)  # ... known the day after the outcome date
    wild = ctx_of(pd.concat([ctx.table, future], ignore_index=True), list(ctx.specs.values()), ctx.core)
    for rec in full_rec.values():
        ref = EV.series_outcomes(EV.PathCache(ctx), rec, h)
        assert EV.series_outcomes(EV.PathCache(cut), rec, h) == ref
        assert EV.series_outcomes(EV.PathCache(wild), rec, h) == ref
        assert any(u is not None for _, u in ref[0])


def test_outcome_needs_a_later_period():
    ctx, br = world("persistent", branches=("G4",), n=60)  # data end 2017-06: no new period after it
    rec = EV.records(ctx, [pd.Period("2017-09", freq="M")], br)[("G4", "2017-09")]
    out, pers = EV.series_outcomes(EV.PathCache(ctx), rec, 3)
    assert all(u is None for _, u in out) and any(u is not None for _, u in pers)


# ------------------------------------------------------------------ decision rule and output


def _fake(kappa=0.9, hard=0.0, H=(0.6, 0.6), pers=(0.5, 0.5), chance=(0.5, 0.5), p=(0.01, 0.2), p_low=(0.9, 0.9)):
    a = {"v2": {EV.REGISTERED: {"pooled": {"kappa": kappa, "hard_flips": hard}}}}
    ph = EV.holm(dict(zip(EV.HORIZONS, p)))
    pl = EV.holm(dict(zip(EV.HORIZONS, p_low)))
    b = {"v2": {EV.REGISTERED: {h: {"H": H[i], "persistence_same": pers[i], "chance": chance[i], "p": p[i],
                                    "p_holm": ph[h], "p_low_holm": pl[h]} for i, h in enumerate(EV.HORIZONS)}}}
    return EV.decision(a, b)


def test_decision_rule_is_applied_mechanically():
    d = _fake()
    assert d["positive_result"] and d["b_passed_horizons"] == [3] and not d["review_recommended"]
    assert _fake(kappa=0.69)["a_review"] and _fake(kappa=0.69)["review_recommended"]
    assert _fake(hard=0.03)["a_review"] and not _fake(hard=0.02)["a_review"]
    assert not _fake(pers=(0.7, 0.5))["positive_result"]  # significant, but not above persistence
    nb = _fake(H=(0.55, 0.5), pers=(0.6, 0.5), p=(0.3, 0.6))
    assert nb["b_not_above"] and nb["review_recommended"] and nb["b_verdict"] == "inte avgjort"
    assert _fake(p_low=(0.01, 0.9))["b_wrong"]
    inc = _fake(H=(0.6, 0.6), p=(0.3, 0.4))
    assert not inc["review_recommended"] and not inc["positive_result"]  # inconclusive: no recommendation


def test_markdown_and_cli(persistent, tmp_path, monkeypatch, capsys):
    md = EV.markdown(persistent)
    for needle in ("#### (a) v2", "#### (b) v1", "Andra trösklar", "Delperioder", "Beslutsregeln, mekaniskt",
                   "Baslinjer och basfrekvens (v2", "Persistens alla månader med utfall"):
        assert needle in md
    monkeypatch.setattr(EV, "run", lambda **kw: persistent)
    out = tmp_path / "t1.json"
    assert cli.main(["evaluate", "--out", str(out), "--no-log", "--vintage", "2026-01-01"]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["label"] == EV.LABEL and doc["decision"]["b_verdict"] in ("godkänt", "inte avgjort")
    assert "Beslutsregeln" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cli.main(["evaluate", "--out", str(out), "--no-log", "--vintage", "2999-01-01"])
    rows = EV.run_log_rows(persistent)
    assert len(rows) == 6 and {r["target"] for r in rows} == {"T1 state v2", "T1 state v1"}
