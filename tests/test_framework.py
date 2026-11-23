"""Tests for the copied framework: catalog, observations (known_from, revisions, as_of), checks, evaluation."""

from __future__ import annotations

import math
from datetime import date

import numpy as np
import pandas as pd
import pytest

from ai_tracker import catalog, evaluation, observations, publication, warehouse


def spec(key="s", freq="M", lag=10, **kw) -> catalog.Spec:
    return catalog.Spec(key=key, branch="G6", label=key, unit="x", freq=freq, source="test",
                        fetch=lambda: pd.Series(dtype=float), lag_days=lag, license="unverified", **kw)


def monthly(values, start="2026-01"):
    return pd.Series(values, index=pd.period_range(start, periods=len(values), freq="M"), dtype=float)


# ------------------------------------------------------------------ catalog


def test_real_catalog_is_valid():
    assert catalog.validate() == []


def test_validate_catches_problems():
    bad = [spec("a"), spec("a"), spec("b", freq="X"),
           catalog.Spec("c", "G0", "c", "x", "M", "t", lambda: None, 0, license=""),
           spec("d", publish=True)]
    errors = " ".join(catalog.validate(bad))
    for needle in ("duplicate key", "unknown freq", "unknown branch", "licence missing", "publish=True"):
        assert needle in errors


# ------------------------------------------------------------------ publication


@pytest.mark.parametrize("freq,period,end", [("D", "2026-03-05", "2026-03-05"), ("W", "2026-03-05", "2026-03-08"),
                                             ("M", "2026-02", "2026-02-28"), ("Q", "2026Q1", "2026-03-31"),
                                             ("A", "2025", "2025-12-31")])
def test_period_end_all_frequencies(freq, period, end):
    p = observations.to_periods([period], freq)
    assert publication.period_end(p)[0] == pd.Timestamp(end)


def test_late_release_only_moves_later():
    p = observations.to_periods(["2026-01", "2026-02"], "M")
    late = {"s": {"2026-01": "2026-03-01", "2026-02": "2026-03-01"}}  # second is earlier than end+lag
    kf = publication.known_from("s", p, 10, late=late)
    assert list(kf) == [pd.Timestamp("2026-03-01"), pd.Timestamp("2026-03-10")]


# ------------------------------------------------------------------ observations


def test_backfill_fetch_revision_and_as_of(tmp_path):
    path = tmp_path / "obs.parquet"
    s = spec(lag=10)
    assert observations.upsert(s, monthly([1, 2, 3]), fetched_at=date(2026, 4, 20), path=path) == 3
    t = observations.load(path)
    assert set(t["source"]) == {"backfill"}
    assert t.loc[t["period"] == "2026-03", "known_from"].iloc[0] == pd.Timestamp("2026-04-10")

    # next fetch: new period dated min(end+lag, fetch), revised value dated at fetch
    n = observations.upsert(s, monthly([1, 2, 3.5, 4]), fetched_at=date(2026, 5, 5), path=path)
    assert n == 2
    t = observations.load(path)
    rev = t[t["source"] == "revision"].iloc[0]
    assert (rev["period"], rev["known_from"]) == ("2026-03", pd.Timestamp("2026-05-05"))
    new = t[t["source"] == "fetch"].iloc[0]
    assert (new["period"], new["known_from"]) == ("2026-04", pd.Timestamp("2026-05-05"))

    # nothing changes on an identical fetch
    assert observations.upsert(s, monthly([1, 2, 3.5, 4]), fetched_at=date(2026, 5, 6), path=path) == 0

    # as_of sees the old vintage before the revision, and never a value before its known_from
    before = observations.as_of("s", "2026-05-01", t)
    assert before.loc[pd.Period("2026-03", "M")] == 3 and pd.Period("2026-04", "M") not in before.index
    after = observations.as_of("s", "2026-05-05", t)
    assert after.loc[pd.Period("2026-03", "M")] == 3.5 and after.loc[pd.Period("2026-04", "M")] == 4


def test_release_dated_rows_keep_every_vintage():
    s = spec("capex", freq="Q")
    filings = pd.DataFrame({"period": ["2025Q4", "2026Q1", "2025Q4"], "value": [10.0, 12.0, 10.5],
                            "known_from": ["2026-01-30", "2026-04-29", "2026-04-29"]})
    rows = observations.new_rows(s, filings, observations._empty(), fetched_at=date(2026, 5, 1))
    assert len(rows) == 3 and set(rows["source"]) == {"release"}
    again = observations.new_rows(s, filings, rows, fetched_at=date(2026, 5, 2))
    assert again.empty
    q4 = observations.as_of("capex", "2026-02-01", rows)
    assert list(q4.index) == [pd.Period("2025Q4", "Q-DEC")] and q4.iloc[0] == 10.0
    assert observations.as_of("capex", "2026-04-29", rows).loc[pd.Period("2025Q4", "Q-DEC")] == 10.5


# ------------------------------------------------------------------ warehouse checks


def table_for(specs_values, fetched=date(2026, 6, 1)):
    t = observations._empty()
    for s, v in specs_values:
        t = pd.concat([t, observations.new_rows(s, v, t, fetched)], ignore_index=True)
    return t


def test_checks_pass_on_clean_mixed_frequency_table():
    m, q = spec("m"), spec("q", freq="Q", lag=30)
    t = table_for([(m, monthly([1, 2, 3])), (q, pd.Series([5.0, 6.0], index=pd.period_range("2025Q3", periods=2, freq="Q")))])
    results = warehouse.run_checks(warehouse.connect(t, [m, q]))
    assert all(df.empty for df in results.values()), {k: v for k, v in results.items() if len(v)}


def test_checks_catch_violations():
    m = spec("m")
    t = table_for([(m, monthly([1, 2, 3, 4]))])
    t = t[t["period"] != "2026-02"]  # gap
    leak = t.iloc[[0]].assign(period="2026-05", known_from=pd.Timestamp("2026-05-10"))  # known before period end
    dup = t.iloc[[0]]
    stranger = t.iloc[[0]].assign(series="unknown")
    t = pd.concat([t, leak, dup, stranger], ignore_index=True)
    r = warehouse.run_checks(warehouse.connect(t, [m]))
    for name in ("no_gaps", "known_from_after_period_end", "unique_key", "series_in_catalog"):
        assert len(r[name]), name


# ------------------------------------------------------------------ evaluation


def test_t_p_value_known():
    assert evaluation.t_two_sided_p(2.0, 10) == pytest.approx(0.0734, abs=1e-4)
    assert evaluation.t_two_sided_p(0.0, 10) == pytest.approx(1.0)


def test_dm_identical_and_clearly_different():
    rng = np.random.default_rng(0)
    e = rng.normal(size=60)
    assert math.isnan(evaluation.dm_test(e, e).p)
    r = evaluation.dm_test(e * 0.2, e * 2)
    assert r.mean_diff < 0 and r.p < 0.01


def test_holm():
    adj = evaluation.holm({"a": 0.01, "b": 0.04, "c": 0.03, "d": float("nan")})
    assert adj["a"] == pytest.approx(0.03) and adj["c"] == pytest.approx(0.06) and adj["b"] == pytest.approx(0.06)
    assert math.isnan(adj["d"])
