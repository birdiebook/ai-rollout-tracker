"""A5 reconciliations (ai_tracker.series.avstamning and the state group "Avstämningar"). Fixtures only, no network.

Vintage and known_from logic, rolling 4-quarter sums, stock vs flow (RPO balance), the poison test (no future row
changes anything known on a date), the catalog contract, and the separate group in state, snapshot, letter and site.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from ai_tracker import catalog, letter as L, observations
from ai_tracker.series import avstamning as A
from ai_tracker.site import data as D
from ai_tracker.state import branch as B
from ai_tracker.state import measures as M
from ai_tracker.state import register as R
from ai_tracker.state import snapshot as S

FETCHED = pd.Timestamp("2026-11-23")


def rows(key, periods, values, known_from, source="release"):
    return pd.DataFrame({"series": key, "freq": "Q", "period": list(periods), "value": np.asarray(values, float),
                         "known_from": pd.to_datetime(list(known_from)), "source": source, "fetched_at": FETCHED})


def got(df):
    return {(r.period, str(r.known_from.date())): pytest.approx(r.value) for r in df.itertuples()}


def quarterly(key, n=28, start="2019Q1", g=0.04, level=100.0, lag=30, seed=0):
    q = pd.period_range(start, periods=n, freq="Q")
    rng = np.random.default_rng(seed)
    v = level * np.exp(np.cumsum(g + 0.03 * rng.standard_normal(n)))
    kf = pd.DatetimeIndex(q.end_time.normalize()) + pd.Timedelta(days=lag)
    return rows(key, [str(p) for p in q], v, kf)


def world():
    """Every component of every reconciliation, 28 quarters, with a few revisions."""
    keys = sorted({c for r in A.RECONS for c in r.components})
    t = pd.concat([quarterly(k, seed=i, lag=25 + 3 * i) for i, k in enumerate(keys)], ignore_index=True)
    rev = t[t["period"].isin(["2022Q2", "2023Q4"])].copy()
    rev["value"] *= 1.07
    rev["known_from"] += pd.Timedelta(days=120)
    return pd.concat([t, rev], ignore_index=True)


# ------------------------------------------------------------------ vintages and known_from


def test_same_quarter_ratio_exists_only_when_all_components_filed_and_is_dated_by_the_latest():
    capex = rows("capex_hyp4", ["2025Q1", "2025Q1"], [60.0, 66.0], ["2025-04-30", "2025-08-01"])
    aws = rows("rev_aws", ["2025Q1"], [10.0], ["2025-05-01"])
    gc = rows("rev_google_cloud", ["2025Q1"], [10.0], ["2025-04-25"])
    msft = rows("rev_msft_cloud", ["2025Q1", "2025Q2"], [10.0, 11.0], ["2025-04-29", "2025-07-29"])
    d = A.derive(A.BY_KEY["x_capex_cloud"], pd.concat([capex, aws, gc, msft]))
    # nothing before AWS (the last component) filed on 2025-05-01; a capex restatement is a new version;
    # 2025Q2 has only Microsoft, so no version
    assert got(d) == {("2025Q1", "2025-05-01"): 2.0, ("2025Q1", "2025-08-01"): 2.2}
    assert set(d["source"]) == {"derived"}


def test_unchanged_value_gives_no_new_version_and_backfill_input_is_labelled():
    capex = rows("capex_hyp4", ["2025Q1"], [50.0], ["2025-05-01"])
    ocf = rows("ocf_hyp4", ["2025Q1", "2025Q1"], [100.0, 100.0], ["2025-05-02", "2025-08-01"], source="backfill")
    d = A.derive(A.BY_KEY["x_capex_ocf"], pd.concat([capex, ocf]))
    assert got(d) == {("2025Q1", "2025-05-02"): 50.0}
    assert list(d["source"]) == ["backfill"]


def test_x_capex_ocf_matches_the_registered_capex_ocf_hyp4():
    t = world()
    x = A.derive(A.BY_KEY["x_capex_ocf"], t)
    ctx = M.Context(t, specs={}, core={}, derived=R.DERIVED)
    y = ctx.rows("capex_ocf_hyp4")
    assert got(x) == got(y)


# ------------------------------------------------------------------ rolling sums and stock vs flow


def test_rolling_four_quarter_sum_needs_all_four_quarters_known_on_the_date():
    q = ["2024Q2", "2024Q3", "2024Q4", "2025Q1"]
    capex = rows("capex_hyp4", q, [10.0, 10.0, 10.0, 10.0], ["2024-08-01", "2024-11-01", "2025-02-01", "2025-05-01"])
    debt = rows("debt_issued_hyp4", q[1:], [4.0, 4.0, 4.0], ["2024-11-02", "2025-02-02", "2025-05-02"])
    rec = A.BY_KEY["x_debt_capex"]
    assert A.derive(rec, pd.concat([capex, debt])).empty  # debt 2024Q2 is missing: no 4-quarter sum
    debt = pd.concat([debt, rows("debt_issued_hyp4", ["2024Q2"], [8.0], ["2024-08-03"])])
    # a revision of the oldest quarter in the window is a new version for 2025Q1 (and only for windows holding it)
    late = rows("debt_issued_hyp4", ["2024Q2"], [0.0], ["2025-09-01"])
    d = A.derive(rec, pd.concat([capex, debt, late]))
    assert got(d) == {("2025Q1", "2025-05-02"): 20.0 / 40.0, ("2025Q1", "2025-09-01"): 12.0 / 40.0}
    assert A.inputs_for(rec, pd.Period("2025Q1", "Q"))[1] == [("capex_hyp4", p) for p in reversed(q)]


def test_rpo_is_a_balance_and_is_not_summed_capex_is_a_four_quarter_flow():
    q = ["2024Q2", "2024Q3", "2024Q4", "2025Q1"]
    capex = rows("capex_hyp4", q, [10.0, 20.0, 30.0, 40.0], ["2024-08-01", "2024-11-01", "2025-02-01", "2025-05-01"])
    rpo = rows("rpo_hyp4", q, [1000.0, 1100.0, 1200.0, 500.0], ["2024-08-01", "2024-11-01", "2025-02-01", "2025-05-03"])
    rpo_rev = rows("rpo_hyp4", ["2024Q4"], [9999.0], ["2025-06-01"])  # restated earlier balance
    rec = A.BY_KEY["x_rpo_cover"]
    assert rec.num == (A.Term("rpo_hyp4", 1),) and rec.den == (A.Term("capex_hyp4", 4),)
    d = A.derive(rec, pd.concat([capex, rpo, rpo_rev]))
    # 2025Q1: the 2025Q1 balance (500) over 10+20+30+40; the 2024Q4 balance restatement does not touch 2025Q1.
    # Earlier quarters lack four capex quarters.
    assert got(d) == {("2025Q1", "2025-05-03"): 500.0 / 100.0}


def test_nvda_uses_the_same_calendar_quarter_label_as_its_component():
    capex = rows("capex_hyp4", ["2025Q3"], [100.0], ["2025-10-30"])
    nvda = rows("rev_nvda_datacenter", ["2025Q3", "2025Q2"], [50.0, 40.0], ["2025-11-19", "2025-08-27"])
    d = A.derive(A.BY_KEY["x_nvda_capex"], pd.concat([capex, nvda]))
    assert got(d) == {("2025Q3", "2025-11-19"): 0.5}


# ------------------------------------------------------------------ no leak (poison)


@pytest.mark.parametrize("when", ["2022-06-30", "2024-01-31", "2025-12-31"])
def test_future_component_rows_never_change_what_is_known_on_a_date(when):
    t = world()
    when = pd.Timestamp(when)
    poison = t[t["known_from"] <= when].copy()
    poison["value"] = poison["value"] * 1000 + 7  # a wild revision of every known value ...
    poison["known_from"] = when + pd.Timedelta(days=1)  # ... known the day after
    poisoned = pd.concat([t, poison], ignore_index=True)
    truncated = t[t["known_from"] <= when]
    for rec in A.RECONS:
        clean = observations.as_of(rec.key, when, _table(A.derive(rec, t), rec.key))
        assert observations.as_of(rec.key, when, _table(A.derive(rec, poisoned), rec.key)).equals(clean)
        assert observations.as_of(rec.key, when, _table(A.derive(rec, truncated), rec.key)).equals(clean)
        d = A.derive(rec, t)
        assert (d["known_from"] > when).any()  # the poison would have mattered had it leaked


def _table(d: pd.DataFrame, key: str) -> pd.DataFrame:
    return d.assign(series=key, freq="Q", fetched_at=FETCHED)[observations.COLUMNS]


def _ctx(t: pd.DataFrame) -> M.Context:
    derived = pd.concat([_table(A.derive(r, t), r.key) for r in A.RECONS], ignore_index=True)
    return M.Context(pd.concat([t, derived], ignore_index=True), specs=catalog.by_key(), core={}, derived={},
                     forecasts=M.config.REPO / "no-forecasts-here", selection=lambda when: [])


def test_reconciliation_measures_ignore_future_rows():
    t = world()
    when = pd.Timestamp("2025-06-30")
    base = B.reconciliations(when, _ctx(t))
    poison = t[t["known_from"] <= when].copy()
    poison["value"] *= 3.0
    poison["known_from"] = when + pd.Timedelta(days=1)
    assert B.reconciliations(when, _ctx(pd.concat([t, poison], ignore_index=True))) == base


# ------------------------------------------------------------------ catalog contract


def test_specs_are_derived_catalog_series_publishable_only_with_their_components():
    specs = catalog.by_key()
    assert A.KEYS == R.RECONCILIATIONS
    for rec in A.RECONS:
        s = specs[rec.key]
        assert s.components == rec.components and s.freq == "Q" and s.revised
        assert s.publish == all(specs[c].publish for c in s.components)
        assert R.METHOD_OVERRIDES[rec.key] == "log"
    assert catalog.validate() == []
    bad = catalog.Spec(key="zz_x", branch="G5", label="x", unit="kvot", freq="Q", source="t", fetch=lambda: None,
                       lag_days=0, license="checked", publish=True, components=("zz_hidden",))
    hidden = catalog.Spec(key="zz_hidden", branch="G5", label="h", unit="MUSD", freq="Q", source="t",
                          fetch=lambda: None, lag_days=0, license="unverified")
    assert any("every component publishable" in e for e in catalog.validate([bad, hidden]))
    assert any("unknown components" in e for e in catalog.validate([bad]))


def test_rpo_capex_and_debt_terms_match_the_register():
    text = R.REGISTER_PATH.read_text(encoding="utf-8")
    entry = text.split("### 2026-11-23 – A5")[1].split("\n### ")[0]
    for key in A.KEYS:
        assert f"`{key}`" in entry
    assert A.BY_KEY["x_debt_capex"].num == (A.Term("debt_issued_hyp4", 4),)
    assert A.BY_KEY["x_capex_cloud"].den == A.CLOUD and A.BY_KEY["x_capex_ocf"].scale == 100.0


def test_refresh_runs_derived_series_after_their_components(monkeypatch):
    calls = []

    def mk(key, components=()):
        def fetch():
            calls.append(key)
            return pd.Series(dtype=float)
        return catalog.Spec(key=key, branch="G5", label=key, unit="MUSD", freq="Q", source="t", fetch=fetch,
                            lag_days=0, license="unverified", components=components)

    monkeypatch.setattr(catalog, "ALL", [mk("a_derived", ("z_comp",)), mk("z_comp")])
    monkeypatch.setattr(observations, "upsert", lambda spec, values: 0)
    observations.refresh()
    assert calls == ["z_comp", "a_derived"]


def test_fetch_reads_the_table_and_new_rows_keep_component_dates():
    t = world()
    spec = catalog.by_key()["x_capex_cloud"]
    out = spec.fetch(t)
    assert list(out.columns) == ["period", "value", "known_from", "source"]
    new = observations.new_rows(spec, out, observations._empty(), fetched_at=FETCHED)
    assert len(new) == len(out) and set(new["source"]) == {"derived"}
    assert list(new["known_from"]) == list(out["known_from"])


# ------------------------------------------------------------------ separate group: state, snapshot, letter, site


def test_reconciliations_never_count_in_a_branch(monkeypatch):
    t = world()
    ctx = _ctx(t)
    ctx.core = {"G5": ["capex_hyp4", "x_capex_cloud"]}
    b = B.branch("G5", "2025-06-30", ctx)
    assert [m["series"] for m in b["series_used"]] == ["capex_hyp4"]
    assert any(m["series"] == "x_capex_cloud" and "avstämning" in m["reason"] for m in b["series_not_counted"])
    for code in catalog.BRANCHES:
        assert not set(R.core_entries(code)) & set(R.RECONCILIATIONS)


def test_snapshot_has_its_own_section_with_level_pace_and_change(monkeypatch):
    t = world()
    ctx = _ctx(t)
    doc = S.build("2025-12-31", ctx=ctx)
    rec = doc["reconciliations"]
    assert rec["group"] == "Avstämningar" and rec["in_diffusion"] is False
    assert [m["series"] for m in rec["series"]] == R.RECONCILIATIONS
    for m in rec["series"]:
        assert m["method"] == "log" and m["in_diffusion"] is False
        assert {"level", "pace", "change_in_pace", "latest_period", "known_from"} <= set(m)
    m = {x["series"]: x for x in rec["series"]}["x_capex_ocf"]
    lv = observations.as_of("x_capex_ocf", "2025-12-31", ctx.rows("x_capex_ocf"))
    assert m["pace"] == pytest.approx(100 * (np.log(lv.iloc[-1]) - np.log(lv.iloc[-5])))
    assert doc["rules"]["reconciliations"] == R.RECONCILIATIONS
    json.dumps(doc)
    used = {m["series"] for b in doc["branches"].values() for m in b["series_used"]}
    assert not used & set(R.RECONCILIATIONS)


def test_letter_lists_reconciliations_under_their_own_heading(tmp_path):
    ctx = _ctx(world())
    text = L.letter("2025-12", ctx, snapshots_dir=tmp_path / "s", forecasts_dir=tmp_path / "f", reconstructed=True,
                    today="2026-11-23")
    section = text.split(L.RECONCILIATION_HEADING + "\n")[1].split("\n## ")[0]
    for key in R.RECONCILIATIONS:
        assert f"`{key}`" in section
    assert "Förändring i takt" in section and "diffusionsindex" in section


def test_letter_and_site_withhold_a_reconciliation_that_may_not_be_published(tmp_path):
    ctx = _ctx(world())
    secret = ctx.specs["x_rpo_cover"]
    ctx.specs = {**ctx.specs, "x_rpo_cover": catalog.Spec(**{**secret.__dict__, "publish": False})}
    text = L.letter("2025-12", ctx, snapshots_dir=tmp_path / "s", forecasts_dir=tmp_path / "f", reconstructed=True,
                    today="2026-11-23")
    section = text.split(L.RECONCILIATION_HEADING + "\n")[1].split("\n## ")[0]
    assert "x_rpo_cover" not in section and "x_capex_cloud" in section
    assert "`x_rpo_cover`" in text.split(L.WITHHELD_HEADING)[1]
    rec = D.Record(ctx, tmp_path / "s", "2026-01-15", history_from="2025-12")
    view = D.reconciliation_view(rec)
    assert view["available"] and "x_rpo_cover" not in [s["key"] for s in view["series"]]
    assert [w["key"] for w in view["withheld"]] == ["x_rpo_cover"]
