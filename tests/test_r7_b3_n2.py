"""Review R7 (docs/granskning/r7_b3_n2.md): independent checks of N2's B3 (track C2).

Synthetic fixtures only, no network. Findings that are bugs are marked xfail(strict=True): when a bug is fixed the
test starts to pass, the strict marker turns that into a failure, and the marker is removed.

- R7-F1: the F-B3 group mean for "quarterly revenue" (TSMC, Nvidia) ignores Nvidia's deviations although Nvidia's
  guidance (`nvda_guid_rev_mid`, approved by R5 for 2017Q2-) and outcome (`rev_nvda`) are in the table. The register
  text says the group mean covers every company with the same guided quantity and at least one known deviation.
- R7-F2: evaluate_step2 takes "the current champion" from n2.CHAMPION at run time. Once B3 is champion, a rerun puts
  B3 in its own comparator set and tests B3 against itself (F-B10's comparator is the champion when step 2 was
  registered, B2). The reverted commit ad5c8fd had the fix (CHAMPION_AT_STEP2).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from ai_tracker.nowcast import b3, n2


def _rows(series, freq, periods, values, known_from):
    return pd.DataFrame({"series": series, "freq": freq, "period": [str(p) for p in periods],
                         "value": np.asarray(values, dtype=float), "known_from": pd.to_datetime(known_from),
                         "source": "release", "fetched_at": pd.Timestamp("2026-11-24")})


@pytest.fixture(scope="module")
def tsmc_and_nvda():
    """TSMC monthly revenue with quarterly NT$ guidance (midpoint 2 % under the outcome), and Nvidia's quarterly
    revenue with guidance 5 % under it, both with known_from dates in real time."""
    rng = np.random.default_rng(11)
    months = pd.period_range("2010-01", "2016-12", freq="M")
    rev = 1e5 * np.exp(np.cumsum(0.01 + 0.04 * rng.standard_normal(len(months))))
    y = pd.Series(rev, index=months)
    kf = [(p + 1).start_time + pd.Timedelta(days=9) for p in months]
    actual = y.groupby(y.index.asfreq("Q-DEC")).sum()
    qs = list(actual.index)
    mid = [actual[q] / math.exp(0.02) for q in qs]
    qkf = [q.start_time + pd.Timedelta(days=14) for q in qs]
    nq = pd.period_range("2010Q1", "2016Q4", freq="Q-DEC")
    nrev = 1e3 * np.exp(np.cumsum(0.02 + 0.05 * rng.standard_normal(len(nq))))
    nkf = [q.end_time.normalize() + pd.Timedelta(days=30) for q in nq]
    gkf = [q.start_time + pd.Timedelta(days=25) for q in nq]
    return pd.concat([
        _rows(n2.TARGET, "M", months, rev, kf),
        _rows("tsmc_guid_rev_twd_lo", "Q", qs, [m * 0.99 for m in mid], qkf),
        _rows("tsmc_guid_rev_twd_hi", "Q", qs, [m * 1.01 for m in mid], qkf),
        _rows("rev_nvda", "Q", nq, nrev, nkf),
        _rows("rev_nvda_datacenter", "Q", nq, nrev * 0.5, nkf),
        _rows("nvda_guid_rev_mid", "Q", nq, nrev / math.exp(0.05), gkf),
        _rows("nvda_guid_rev_lo", "Q", nq, nrev / math.exp(0.05) * 0.98, gkf),
        _rows("nvda_guid_rev_hi", "Q", nq, nrev / math.exp(0.05) * 1.02, gkf),
    ], ignore_index=True)


def test_r7_tsmc_alone_in_group_makes_shrinkage_a_no_op(tsmc_and_nvda):
    """As implemented today (and as C2 reported): with TSMC alone in the group, m_k = TSMC's own mean d at k."""
    t = tsmc_and_nvda
    records = n2.build_records(n2.slim(t), n2.first_vintages(n2.slim(t)).index.max())
    pool = n2.b3_pool(t, records, n2.first_vintages(n2.slim(t)))
    origin = n2.origin_for(pd.Period("2015-06", "M"))
    s = b3.shift(pool, "tsmc", 3, origin)
    own = b3.known(pool, origin)
    own = own[(own["company"] == "tsmc") & (own["position"] == 3)]
    assert s.group_n == 1 and s.n == len(own) >= 4
    assert s.m == pytest.approx(own["d"].mean(), abs=1e-15) == pytest.approx(s.group_mean, abs=1e-15)


@pytest.mark.xfail(strict=True, reason="R7-F1: Nvidia's deviations are not in the 'quarterly_revenue' group mean "
                                       "(no Nvidia builder in b3.BUILDERS) although its guidance is in the table")
def test_r7_f1_group_mean_includes_nvidia_when_its_guidance_is_in_the_table(tsmc_and_nvda):
    pool = b3.group_pool(tsmc_and_nvda, "quarterly_revenue")
    assert "nvda" in set(pool["company"])
    origin = n2.origin_for(pd.Period("2015-06", "M"))
    assert b3.shift(pool, "tsmc", 1, origin).group_n == 2


def _frame(seed=4, n=180):
    rng = np.random.default_rng(seed)
    e2 = rng.normal(2, 2, n)
    b = rng.normal(0, 3, n)
    idx = pd.period_range("2012-01", periods=n, freq="M")
    return pd.DataFrame({"e_B0": b * 1.5, "e_B1": b * 1.2, "e_V1": b * 1.2, "e_B2": e2,
                         "e_B3": e2 * 0.3 + rng.normal(0, 0.2, n), "n_train": 100}, index=idx)


def test_r7_step2_comparator_is_b2_with_the_champion_at_registration():
    s = n2.evaluate(_frame()).step2
    assert n2.CHAMPION == "B2"  # the reviewed state: the champion change waits for this review
    assert s["comparator"] == "B2" and s["passed"] == {"B3": True}


@pytest.mark.xfail(strict=True, reason="R7-F2: with CHAMPION = 'B3' evaluate_step2 puts B3 in its own comparator "
                                       "set (F-B10 means the champion when step 2 was registered, B2)")
def test_r7_f2_step2_comparator_stays_b2_after_b3_is_champion(monkeypatch):
    monkeypatch.setattr(n2, "CHAMPION", "B3")
    s = n2.evaluate(_frame()).step2
    assert "B3" not in s["candidates"]
    assert s["comparator"] == "B2" and s["passed"] == {"B3": True} and s["champion"] == "B3"
