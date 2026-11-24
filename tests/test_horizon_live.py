"""D2 live (nowcast/horizon_live.py): origin logic and the closed holdout, immutable files, no future data, error
pools from development origins and live files only, and scoring per horizon. Synthetic fixtures only, no network."""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from ai_tracker import pipeline
from ai_tracker.factor import guard
from ai_tracker.nowcast import engine, horizon, horizon_live as HL, n1, n4

TS = pd.Timestamp
Q = "Q-DEC"
QS = pd.period_range("2014Q1", "2028Q4", freq=Q)
ENDS = QS.end_time.normalize()
FIRST = TS("2027-01-20")
SECOND = TS("2027-04-20")


def _rows(series, periods, values, known_from, freq="Q", source="release"):
    return pd.DataFrame({"series": series, "freq": freq, "period": [str(p) for p in periods],
                         "value": np.asarray(values, dtype=float), "known_from": pd.to_datetime(list(known_from)),
                         "source": source, "fetched_at": TS("2026-11-24")})


def _path(n, seed, drift=0.04, sd=0.03, start=100.0):
    rng = np.random.default_rng(seed)
    return start * np.exp(np.cumsum(drift + sd * rng.standard_normal(n)))


def make_table() -> pd.DataFrame:
    """2014Q1-2028Q4, each quarter filed 25-34 days after its end (so the table also holds 'future' rows that a live
    run at 2027-01-20 must not see), full-year guidance for Y known at the end of October of Y-1."""
    parts, capex = [], {}
    for i, c in enumerate(n1.COMPANIES):
        v = _path(len(QS), 1 + i, start=1000 * (i + 1))
        kf = ENDS + pd.Timedelta(days=25 + 3 * i)
        capex[c] = (v, kf)
        parts.append(_rows(c, QS, v, kf))
    total = sum(v for v, _ in capex.values())
    kf_total = pd.DatetimeIndex(np.max(np.vstack([kf.values for _, kf in capex.values()]), axis=0))
    parts.append(_rows(n1.TARGET, QS, total, kf_total))
    lease = _path(len(QS), 9, start=50)
    parts.append(_rows("fin_lease_meta", QS, lease, ENDS + pd.Timedelta(days=34)))
    years = sorted({q.year for q in QS})
    for series, (prefix, lse) in n1.B2_GUIDANCE.items():
        v = pd.Series(capex[series][0], index=QS)
        if lse:
            v = v + pd.Series(lease, index=QS)
        full = v.groupby(v.index.year).sum()
        yp = [pd.Period(str(y), freq="Y-DEC") for y in years[1:]]
        kf = [TS(f"{y - 1}-10-30") for y in years[1:]]
        mid = np.array([1.03 * full[y] for y in years[1:]])
        parts.append(_rows(f"{prefix}_lo", yp, 0.98 * mid, kf, freq="A"))
        parts.append(_rows(f"{prefix}_hi", yp, 1.02 * mid, kf, freq="A"))
    for i, c in enumerate(n4.COMPONENTS):
        parts.append(_rows(c, QS, _path(len(QS), 10 + i, start=300 * (i + 1)), ENDS + pd.Timedelta(days=25 + 3 * i)))
    for i, c in enumerate(n4.RPO.components):
        parts.append(_rows(c, QS, _path(len(QS), 20 + i, start=900 * (i + 1)), ENDS + pd.Timedelta(days=26 + 2 * i)))
    return pd.concat(parts, ignore_index=True)


@pytest.fixture(scope="module")
def table():
    return make_table()


@pytest.fixture(scope="module")
def first(table):
    return HL.payload(table, FIRST)


@pytest.fixture(scope="module")
def live_dir(table, tmp_path_factory):
    """forecasts/ with the live D2 files of 2027-01-20 and 2027-04-20, each written on its own day."""
    root = tmp_path_factory.mktemp("forecasts")
    for o in (FIRST, SECOND):
        HL.write_live(table, o, root / HL.DIR, today=o)
    return root


def _strip(p: dict) -> dict:
    return json.loads(json.dumps(p))


# ------------------------------------------------------------------ origins and the holdout


def test_first_live_origin_and_registered_days():
    assert HL.FIRST_LIVE == FIRST == guard.LIVE_FROM["D2"]
    assert HL.is_origin("2027-01-20") and HL.is_origin("2027-04-20") and HL.is_origin("2028-10-20")
    assert not HL.is_origin("2026-10-20")  # registered N1 day, but inside D2's holdout
    assert not HL.is_origin("2025-07-20") and not HL.is_origin("2027-01-21") and not HL.is_origin("2027-02-20")
    assert HL.file_stem(FIRST) == "2026Q4"


def test_pipeline_d2_due_only_on_n1_days_from_the_first_live_origin():
    days = pd.date_range("2026-01-01", "2028-12-31")
    d2 = [day for day in days if pipeline.d2_due(day)]
    n1_days = [day for day in days if pipeline.n1_due(day)]
    assert d2 == [day for day in n1_days if day >= FIRST] and len(d2) == 8
    d = pipeline.due_for("d2", FIRST)
    assert d.period == "2026Q4" and d.path().as_posix().endswith("forecasts/d2/2026Q4.json")
    assert {x.nowcast for x in pipeline.due(FIRST)} >= {"n1", "n4", "n6", "d2"}
    assert {x.nowcast for x in pipeline.due("2026-10-20")} >= {"n1"} and "d2" not in {
        x.nowcast for x in pipeline.due("2026-10-20")}


def test_guard_allows_live_only_from_the_first_live_origin(table):
    for o in ("2025-07-20", "2026-01-20", "2026-10-20", "2027-01-19"):  # the holdout stays closed, live or not
        with pytest.raises(guard.HoldoutClosed):
            guard.check(o, family="D2", live=True)
    with pytest.raises(guard.HoldoutClosed):  # without live=True even a live origin is refused (development runs)
        guard.check(FIRST, family="D2")
    assert guard.check(FIRST, family="D2", live=True) == FIRST
    with pytest.raises(guard.HoldoutClosed):  # live=True opens nothing for other families
        guard.check(FIRST, family="X9", live=True)
    t = horizon.prepare(table)
    with pytest.raises(guard.HoldoutClosed):
        horizon.forecast(t, horizon.CAPEX, "2026-10-20", live=True)
    with pytest.raises(guard.HoldoutClosed):
        HL.payload(table, "2026-10-20")
    with pytest.raises(guard.HoldoutClosed):
        horizon.forecast(t, horizon.CAPEX, FIRST)  # the development path stays closed


def test_pools_hold_no_holdout_origin(table, live_dir):
    t = horizon.prepare(HL._known(table, SECOND))
    for target in horizon.TARGETS.values():
        for h, (e, kf, live_idx) in HL.pools(t, target, SECOND, live_dir / HL.DIR).items():
            o = pd.to_datetime(pd.Series(e.index))
            assert ((o <= guard.DEV_END) | (o >= FIRST)).all(), (target.name, h)
            assert (o < SECOND).all() and list(live_idx) == [str(x.date()) for x in o if x >= FIRST]
            assert (kf <= SECOND).all() or e.empty


# ------------------------------------------------------------------ the file


def test_file_has_both_targets_all_models_and_champion_per_group(first):
    assert first["nowcast"] == "D2" and first["quarter"] == "2026Q4" and first["registered_origin"]
    for name, target in horizon.TARGETS.items():
        tg = first["targets"][name]
        assert tg["base"] == "2026Q3"  # 2026Q4 is filed after the origin
        assert sorted(tg["paths"], key=int) == [str(h) for h in horizon.HORIZONS]
        for hs, p in tg["paths"].items():
            h = int(hs)
            assert p["quarter"] == str(pd.Period("2026Q3", Q) + h)
            assert set(p["models"]) == set(target.models)
            assert all(v is not None and v > 0 for v in p["models"].values()), (name, h)
            assert p["champion"] == HL.CHAMPION[name][HL.group_of(h)] and p["value"] == p["models"][p["champion"]]
        assert tg["shadow"] == ["V_kedja"]
    cap = first["targets"]["capex"]["paths"]
    assert cap["1"]["champion"] == cap["4"]["champion"] == "B2" and cap["5"]["champion"] == cap["8"]["champion"] == "B1"
    assert {p["champion"] for p in first["targets"]["cloud"]["paths"].values()} == {"B1"}


def test_quantiles_where_pools_allow(first):
    for name, target in horizon.TARGETS.items():
        dist = first["targets"][name]["distribution"]
        for hs, block in dist.items():
            for m, b in block["models"].items():
                if b["method"] is None:
                    assert b["n_pool"] < 8
                    continue
                assert b["n_pool"] >= 8 and b["n_live"] == 0  # no live file before the first origin
                lv = first["targets"][name]["paths"][hs]["models"][m]
                lo, hi = b["intervals"]["80"]
                assert lo < b["quantiles"]["0.5"] < hi and lo < lv * 1.5
        assert dist["1"]["models"]["B0"]["method"] is not None  # long development pools for the baselines


def test_champion_falls_back_to_b1_then_b0():
    lv = {"B2": {1: float("nan")}, "B1": {1: 5.0}, "B0": {1: 4.0}}
    assert HL.champion_for("capex", 1, lv) == ("B1", "B2 not available; fell back to B1")
    assert HL.champion_for("capex", 1, {"B0": {1: 4.0}})[0] == "B0"
    assert HL.champion_for("cloud", 1, lv) == ("B1", "")


def test_no_future_data(table, first):
    """The table holds rows up to 2029; the file at 2027-01-20 equals the one built from the rows known then, and
    poison rows filed after the origin (revisions and new quarters) change nothing."""
    known = HL._known(table, FIRST)
    assert pd.to_datetime(table["known_from"]).max() > FIRST + pd.Timedelta(days=365)
    poison = []
    for s, g in known.groupby("series"):
        r = g.drop_duplicates("period").copy()
        r["value"] *= 5.0
        r["known_from"] = FIRST + pd.Timedelta(days=1)
        poison.append(r)
    poisoned = pd.concat([known, *poison], ignore_index=True)
    a = _strip(first)
    assert a == _strip(HL.payload(known, FIRST)) == _strip(HL.payload(poisoned, FIRST))
    for tg in first["targets"].values():
        assert all(pd.Timestamp(i["known_from"]) <= FIRST for i in tg["inputs"]) and tg["inputs"]


def test_written_once_and_never_rewritten(table, live_dir, tmp_path):
    path = live_dir / HL.DIR / "2026Q4.json"
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        HL.write_live(table, FIRST, live_dir / HL.DIR, today=FIRST)
    assert path.read_bytes() == before
    d = pipeline.Due("d2", FIRST, "2026Q4")
    assert pipeline.run_live(d, root=live_dir, table=table, refresh=False, today=FIRST) is None
    assert path.read_bytes() == before
    with pytest.raises(ValueError):  # a future origin: as_of would not be the real information set
        HL.write_live(table, "2027-07-20", tmp_path, today=FIRST)
    with pytest.raises(ValueError):  # not a registered origin
        HL.write_live(table, "2027-01-21", tmp_path, today="2027-01-21")
    with pytest.raises(guard.HoldoutClosed):
        HL.write_live(table, "2026-10-20", tmp_path, today="2026-10-20")
    assert not list(tmp_path.glob("*.json"))
    assert pipeline.FORECAST_PATH.fullmatch("forecasts/d2/2026Q4.json")


def test_pipeline_live_writes_d2_on_its_origin(table, tmp_path):
    written = pipeline.live(only="d2", root=tmp_path, table=table, refresh=False, today=FIRST)
    assert [p.name for p in written] == ["2026Q4.json"] and written[0].parent.name == "d2"
    assert "## D2 – prognoser 1–8 kvartal (skugga)" in (tmp_path / "SCORECARD.md").read_text(encoding="utf-8")
    assert pipeline.live(only="d2", root=tmp_path, table=table, refresh=False, today="2026-10-20") == []
    assert set(pipeline.live_keys("d2")) >= {n1.TARGET, *n1.COMPANIES, *n4.COMPONENTS, *n4.RPO.components}


def test_a_live_error_enters_the_pool_of_its_horizon_once_its_outcome_is_known(table, live_dir):
    d = json.loads((live_dir / HL.DIR / "2027Q1.json").read_text(encoding="utf-8"))
    for name in horizon.TARGETS:
        block = d["targets"][name]["distribution"]
        # at 2027-04-20 the h=1 outcome of 2027-01-20 (2026Q4, filed late January) is known, h=2 (2027Q1) is not
        assert block["1"]["models"]["B0"]["n_live"] == 1
        assert all(block[str(h)]["models"]["B0"]["n_live"] == 0 for h in range(2, 9))
    t = horizon.prepare(HL._known(table, SECOND))
    lf = HL.live_frame(sorted((live_dir / HL.DIR).glob("*.json")), t, horizon.CAPEX, SECOND)
    assert list(lf["h"]) == [1] and lf["origin"].iloc[0] == FIRST
    y = engine.first_vintages(t, n1.TARGET).at[pd.Period("2026Q4", Q), "value"]
    f = json.loads((live_dir / HL.DIR / "2026Q4.json").read_text(encoding="utf-8"))
    assert lf["B1"].iloc[0] == pytest.approx(engine.log_error(f["targets"]["capex"]["paths"]["1"]["models"]["B1"], y))


# ------------------------------------------------------------------ scoring per horizon


def test_each_horizon_is_scored_when_its_outcome_arrives(table, live_dir):
    mid = HL._known(table, "2027-06-01")  # 2026Q4 and 2027Q1 filed, 2027Q2 not yet
    s = HL.score(live_dir, mid)
    assert len(s) == 2 * 2 * 8  # files x targets x h
    f1 = s[s["origin"] == "2027-01-20"]
    for name in horizon.TARGETS:
        g = f1[f1["target"] == name].set_index("h")
        assert list(g.loc[[1, 2], "status"]) == ["utfall", "utfall"]
        assert (g.loc[3:, "status"] == "väntar").all()
    f2 = s[s["origin"] == "2027-04-20"]
    assert list(f2[f2["target"] == "capex"].set_index("h").loc[[1, 2], "status"]) == ["utfall", "väntar"]
    full = HL.score(live_dir, table)
    assert (full["status"] == "utfall").all()  # every outcome up to 2028Q4 is in the table
    r = full[(full["target"] == "capex") & (full["origin"] == "2027-01-20") & (full["h"] == 8)].iloc[0]
    t = horizon.prepare(table)
    fv = engine.first_vintages(t, n1.TARGET).at[pd.Period("2028Q3", Q), "value"]
    assert r["quarter"] == "2028Q3" and r["outcome"] == pytest.approx(fv)
    assert r["err_champion"] == pytest.approx(engine.log_error(r["forecast"], fv)) == pytest.approx(r["err_B1"])
    assert math.isfinite(r["crps_champion"])  # the stored distribution is scored, not rebuilt
    summ = {x["h"]: x for x in HL.summary(full, "capex")}
    assert summ[1]["n"] == 2 and summ[8]["n"] == 2 and summ[1]["mae_champion"] >= 0
    md = "\n".join(HL.render(full))
    assert "### Capex" in md and "| 8 | 2 |" in md
    assert "Inga D2-prognoser än" in "\n".join(HL.render(pd.DataFrame()))


def test_first_vintage_is_the_outcome_not_a_revision(table, live_dir):
    q = pd.Period("2026Q4", Q)
    first_v = table[(table.series == n1.TARGET) & (table.period == str(q))]["value"].iloc[0]
    rev = pd.concat([table, _rows(n1.TARGET, [q], [first_v * 2], [TS("2027-09-01")], source="revision")],
                    ignore_index=True)
    r = HL.score(live_dir, rev)
    row = r[(r["target"] == "capex") & (r["origin"] == "2027-01-20") & (r["h"] == 1)].iloc[0]
    assert row["outcome"] == pytest.approx(first_v)


def test_scorecard_and_site_show_d2(table, live_dir):
    out = pipeline.scorecard(root=live_dir, table=table, today="2029-06-01")
    md = out.read_text(encoding="utf-8")
    assert "## D2 – prognoser 1–8 kvartal (skugga)" in md and "| 2027-01-20 | 2026Q3 | 8 | 2028Q3 |" in md
    from ai_tracker.site import data as D, render as R
    from ai_tracker.state.measures import Context

    ctx = Context(table)
    v = D.horizons(ctx, live_dir, TS("2027-05-01"))
    assert v["origin"] == "2027-04-20" and v["next_origin"] == "2027-07-20"
    for t in v["targets"]:
        if t["publishable"]:
            assert t["fan"]["periods"][0] == t["base"] and len(t["fan"]["periods"]) == 9
            assert len(t["paths"]) == 8 and t["fan"]["intervals"]["95"]["lo"][0] == t["fan"]["values"][0]
        else:
            assert t["fan"] is None and not t["paths"]
    html = R.horizons_section(v, {"repo": "https://example.invalid/repo"})
    assert 'id="d2"' in html and "D2: prognoser 1–8 kvartal" in html
    empty = D.horizons(ctx, live_dir / "none", TS("2026-11-24"))
    assert empty["origin"] is None and empty["next_origin"] == "2027-01-20"
    assert "Inga D2-prognoser än" in R.horizons_section(empty, {"repo": "x"})
