"""F1: guidance revisions and surprise against guidance (ai_tracker.series.guidance_revisions, state.expectations,
sources.tsmc_capex_guidance). Synthetic fixtures only, no network.

Revision sign and size, dead band, new item vs revision (TSMC/Nvidia quarterly guidance), the same-event window,
directions, definition codes and breaks, the revision index (n >= 3, rolling window, closing version, nothing
future-dated), standardisation only after 4 earlier surprises, the surprise index, as_of truncation giving identical
values, the catalog contract and the snapshot section.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from ai_tracker import catalog
from ai_tracker.series import guidance_revisions as GR
from ai_tracker.sources import guidance_capex
from ai_tracker.sources import tsmc_capex_guidance as TC
from ai_tracker.state import expectations as E
from ai_tracker.state import snapshot as S

FETCHED = pd.Timestamp("2026-11-24")
TODAY = pd.Timestamp("2026-11-24")


# ------------------------------------------------------------------ fixtures


@pytest.fixture(autouse=True)
def _index_from_2016(monkeypatch):
    """The synthetic worlds lie before the registered start (2020Q3); the rule is tested on them from 2016Q1."""
    monkeypatch.setattr(GR, "COVERAGE_FROM", pd.Period("2016Q1", "Q-DEC"))


def csv_rows(rows: list[dict]) -> pd.DataFrame:
    """A guidance_capex.load()-shaped frame from short dicts (company, horizon, period, kind, lo, hi, code, filed)."""
    out = []
    for i, r in enumerate(rows):
        kind = r.get("kind", "range")
        lo = r.get("lo", np.nan)
        hi = r.get("hi", lo if kind in ("point", "approx") else np.nan)
        out.append({"id": r.get("id", f"x-{i:02d}"), "company": r.get("company", "meta"),
                    "horizon": r.get("horizon", "CY"), "period": str(r.get("period", "2025")), "kind": kind,
                    "value_lo": lo, "value_hi": hi, "unit": "MUSD" if kind != "direction" else "code",
                    "direction_code": r.get("code", np.nan), "direction_base": r.get("base", "yoy" if kind ==
                                                                                       "direction" else ""),
                    "definition": r.get("definition", "META_CAPEX_INCL_FL"), "filed": r["filed"]})
    df = pd.DataFrame(out)
    df["known_from"] = pd.to_datetime(df["filed"])
    return df


def obs(key, freq, periods, values, known_from):
    return pd.DataFrame({"series": key, "freq": freq, "period": [str(p) for p in periods],
                         "value": np.asarray(values, float), "known_from": pd.to_datetime(list(known_from)),
                         "source": "release", "fetched_at": FETCHED})


def ev_of(csv=None, table=None):
    return GR.events(GR.statements(table, csv))


# ------------------------------------------------------------------ revision events


def test_revision_sign_and_size_from_midpoints():
    ev = ev_of(csv_rows([{"lo": 100, "hi": 110, "filed": "2025-01-29"}, {"lo": 110, "hi": 120, "filed": "2025-04-30"},
                         {"lo": 100, "hi": 104, "filed": "2025-07-30"}]))
    assert list(ev["direction"]) == [1, -1]
    assert ev["size"].iloc[0] == pytest.approx(100 * math.log(115 / 105))
    assert ev["size"].iloc[1] == pytest.approx(100 * math.log(102 / 115))
    assert ev["prev_value"].iloc[0] == pytest.approx(105) and ev["value"].iloc[0] == pytest.approx(115)
    assert str(ev["known_from"].iloc[0].date()) == "2025-04-30"


def test_dead_band_and_restatement_are_unchanged():
    ev = ev_of(csv_rows([{"lo": 100, "hi": 110, "filed": "2025-01-29"},  # 105
                         {"lo": 100, "hi": 110, "filed": "2025-04-30"},  # restated: 0
                         {"lo": 100.5, "hi": 110.5, "filed": "2025-07-30"},  # 105.5: +0.47
                         {"kind": "approx", "lo": 105.0, "filed": "2025-10-29"},  # -0.47
                         {"kind": "approx", "lo": 103.9, "filed": "2026-01-28"}]))  # -1.05
    assert list(ev["direction"]) == [0, 0, 0, -1]
    assert ev["size"].iloc[0] == pytest.approx(0.0)
    assert ev["size"].iloc[1] == pytest.approx(100 * math.log(105.5 / 105))
    assert ev["size"].iloc[3] == pytest.approx(100 * math.log(103.9 / 105))


def test_dead_band_edges():
    assert GR._direction(1.0) == 1 and GR._direction(-1.0) == -1
    assert GR._direction(0.999) == 0 and GR._direction(-0.999) == 0


def test_first_statement_new_definition_and_direction_to_number_are_not_revisions():
    ev = ev_of(csv_rows([
        {"company": "amzn", "kind": "direction", "code": 1, "definition": "AMZN_CASH_CAPEX", "filed": "2025-10-31"},
        {"company": "amzn", "kind": "approx", "lo": 200, "definition": "AMZN_CAPEX_UNSPEC", "filed": "2026-02-05"},
        {"company": "amzn", "kind": "approx", "lo": 220, "definition": "AMZN_CASH_CAPEX", "filed": "2026-10-29"},
        {"company": "meta", "period": "2026", "kind": "approx", "lo": 50, "filed": "2026-01-28"},  # other period
    ]))
    assert ev.empty


def test_directions_compare_codes_without_size():
    ev = ev_of(csv_rows([{"kind": "direction", "code": 1, "filed": "2024-04-24"},
                         {"kind": "direction", "code": 2, "filed": "2024-07-31"},
                         {"kind": "direction", "code": 2, "filed": "2024-10-30"},
                         {"kind": "direction", "code": 0, "filed": "2025-01-29"}]))
    assert list(ev["direction"]) == [1, 0, -1]
    assert ev["size"].isna().all() and set(ev["chain"]) == {"dir:yoy"}


def test_direction_bases_are_separate_chains():
    ev = ev_of(csv_rows([{"company": "msft", "horizon": "FY", "period": "FY2026", "kind": "direction", "code": -1,
                          "base": "growth_vs_prior", "definition": "MSFT_CAPEX_INCL_FL", "filed": "2025-04-30"},
                         {"company": "msft", "horizon": "FY", "period": "FY2026", "kind": "direction", "code": 1,
                          "base": "prior_fy", "definition": "MSFT_CAPEX_INCL_FL", "filed": "2025-07-30"}]))
    assert ev.empty


def test_registered_definition_break_starts_a_new_item(monkeypatch):
    rows = [{"id": "m-1", "company": "msft", "kind": "approx", "lo": 190, "definition": "MSFT_CAPEX_INCL_FL",
             "period": "2026", "filed": "2026-04-29"},
            {"id": "m-2", "company": "msft", "kind": "approx", "lo": 170, "definition": "MSFT_CAPEX_INCL_FL",
             "period": "2026", "filed": "2026-10-28"},
            {"id": "m-3", "company": "msft", "kind": "approx", "lo": 175, "definition": "MSFT_CAPEX_INCL_FL",
             "period": "2026", "filed": "2027-01-28"}]
    assert list(ev_of(csv_rows(rows))["direction"]) == [-1, 1]
    monkeypatch.setitem(GR.DEFINITION_BREAKS, "m-2", "test break")
    ev = ev_of(csv_rows(rows))
    assert len(ev) == 1 and ev["prev_value"].iloc[0] == pytest.approx(170) and ev["direction"].iloc[0] == 1
    # the registered break (R5-F14), moved after R11-1 to the first figure on the narrower basis
    assert "msft-r11f1" in GR.DEFINITION_BREAKS and "msft-29" not in GR.DEFINITION_BREAKS


def test_same_event_window_counts_once_and_updates_the_reference():
    ev = ev_of(csv_rows([{"lo": 100, "hi": 110, "filed": "2025-01-29"},
                         {"lo": 110, "hi": 120, "filed": "2025-04-30"},
                         {"lo": 120, "hi": 130, "filed": "2025-05-03"},  # 3 days later: same event
                         {"lo": 120, "hi": 130, "filed": "2025-07-30"}]))
    assert len(ev) == 2
    assert ev["prev_value"].iloc[1] == pytest.approx(125) and ev["direction"].iloc[1] == 0


def _tsmc_guidance(rows):
    """rows: (quarter, lo, hi, known_from) -> US$ guidance rows; fx 30 at the first statement of each quarter."""
    lo = obs("tsmc_guid_rev_usd_lo", "Q", [r[0] for r in rows], [r[1] for r in rows], [r[3] for r in rows])
    hi = obs("tsmc_guid_rev_usd_hi", "Q", [r[0] for r in rows], [r[2] for r in rows], [r[3] for r in rows])
    first = {}
    for q, _l, _h, kf in rows:
        first.setdefault(q, kf)
    fx = obs("tsmc_guid_fx", "Q", list(first), [30.0] * len(first), list(first.values()))
    return pd.concat([lo, hi, fx], ignore_index=True)


def test_quarterly_guidance_is_a_new_item_and_only_a_mid_quarter_update_is_a_revision():
    t = _tsmc_guidance([("2024Q1", 18000, 18800, "2024-01-18"), ("2024Q2", 19600, 20400, "2024-04-18"),
                        ("2024Q2", 20000, 20800, "2024-05-20"),  # mid-quarter update
                        ("2024Q3", 22400, 23200, "2024-07-18")])
    nv = obs("nvda_guid_rev_mid", "Q", ["2024Q1", "2024Q2", "2024Q3"], [24000, 28000, 32500],
             ["2024-02-21", "2024-05-22", "2024-08-28"])
    ev = ev_of(table=pd.concat([t, nv], ignore_index=True))
    assert len(ev) == 1
    e = ev.iloc[0]
    assert e["company"] == "tsmc" and e["period"] == "Q:2024Q2" and e["direction"] == 1
    assert e["size"] == pytest.approx(100 * math.log(20400 / 20000))


def test_nvidia_before_2017q2_is_left_out():
    nv = obs("nvda_guid_rev_mid", "Q", ["2016Q1", "2016Q1"], [1000, 1100], ["2016-02-17", "2016-03-20"])
    assert GR.table_statements(nv).empty


# ------------------------------------------------------------------ revision index


def _index_events(dates_dirs):
    rows = [{"company": "c", "measure": "capex", "item": f"i{i}", "chain": "num", "period": "CY:2025",
             "definition": "D", "kind": "range", "known_from": pd.Timestamp(d), "ref": f"r{i}",
             "prev_known_from": pd.Timestamp(d) - pd.Timedelta(days=90), "prev_ref": "p", "prev_value": 100.0,
             "value": 100.0 * math.exp(s / 100), "prev_code": np.nan, "code": np.nan, "size": s, "direction": dr}
            for i, (d, dr, s) in enumerate(dates_dirs)]
    return pd.DataFrame(rows, columns=GR.EVENT_COLUMNS)


def test_index_needs_three_events_and_counts_unchanged_as_half():
    ev = _index_events([("2025-01-29", 1, 5.0), ("2025-02-05", 0, 0.0), ("2025-03-10", -1, -3.0),
                        ("2025-04-30", 1, 2.0)])
    q = GR.revision_index(ev, 1, TODAY, start=pd.Period("2025Q1", "Q-DEC"))
    q1 = q[q["period"] == "2025Q1"]
    assert list(q1["n"]) == [1, 2, 3]
    assert q1["index"].iloc[:2].isna().all() and q1["index"].iloc[-1] == pytest.approx(0.5)
    assert q1["median_size"].iloc[-1] == pytest.approx(0.0)
    q2 = q[q["period"] == "2025Q2"]
    assert list(q2["n"]) == [1] and q2["index"].isna().all()
    r4 = GR.revision_index(ev, 4, TODAY, start=pd.Period("2025Q1", "Q-DEC"))
    last = r4[r4["period"] == "2025Q2"].iloc[-1]
    assert last["n"] == 4 and last["index"] == pytest.approx((2 + 0.5) / 4)
    assert str(last["known_from"].date()) == "2025-04-30"


def test_closing_version_for_a_quarter_without_events_and_nothing_future_dated():
    ev = _index_events([("2025-01-29", 1, 5.0), ("2025-02-05", 1, 2.0), ("2025-03-10", 1, 3.0)])
    r4 = GR.revision_index(ev, 4, "2025-08-15", start=pd.Period("2025Q1", "Q-DEC"))
    q2 = r4[r4["period"] == "2025Q2"]
    assert len(q2) == 1 and str(q2["known_from"].iloc[0].date()) == "2025-06-30" and q2["index"].iloc[0] == 1.0
    assert "2025Q3" not in set(r4["period"]) or (r4.loc[r4["period"] == "2025Q3", "known_from"]
                                                  <= pd.Timestamp("2025-08-15")).all()
    assert (r4["known_from"] <= pd.Timestamp("2025-08-15")).all()
    q1 = GR.revision_index(ev, 1, "2025-08-15", start=pd.Period("2025Q1", "Q-DEC"))
    assert q1.loc[q1["period"] == "2025Q2", "n"].tolist() == [0]


# ------------------------------------------------------------------ surprises


def _surprise_frame(company, values, start="2018-01-01", step_days=91, freq="Q"):
    kf = pd.date_range(start, periods=len(values), freq=f"{step_days}D")
    return pd.DataFrame({"company": company, "measure": "revenue", "period": [f"p{i}" for i in range(len(values))],
                         "freq": freq, "index_quarter": [str(pd.Period(d, "Q-DEC")) for d in kf], "outcome": 1.0,
                         "outcome_known_from": kf, "guidance": 1.0, "guidance_known_from": kf, "s": values})


def test_standardisation_only_after_four_earlier_surprises():
    s = GR.standardize(_surprise_frame("tsmc", [1.0, 3.0, 2.0, 4.0, 5.0, -1.0]))
    assert s["z"].iloc[:4].isna().all() and list(s["n_past"]) == [0, 1, 2, 3, 4, 5]
    sd = np.std([1.0, 3.0, 2.0, 4.0], ddof=1)
    assert s["z"].iloc[4] == pytest.approx(5.0 / sd) and s["sd_past"].iloc[4] == pytest.approx(sd)
    assert s["z"].iloc[5] == pytest.approx(-1.0 / np.std([1.0, 3.0, 2.0, 4.0, 5.0], ddof=1))


def test_past_means_outcome_known_strictly_before():
    f = _surprise_frame("tsmc", [1.0, 3.0, 2.0, 4.0, 5.0])
    f.loc[4, "outcome_known_from"] = f.loc[3, "outcome_known_from"]  # same day: not in the past
    s = GR.standardize(f)
    assert s.loc[s["s"] == 5.0, "n_past"].iloc[0] == 3 and s.loc[s["s"] == 5.0, "z"].isna().all()


def test_surprise_index_needs_two_companies_and_versions_per_component():
    a = GR.standardize(_surprise_frame("tsmc", [1.0, 3.0, 2.0, 4.0, 5.0], start="2018-01-10"))
    b = GR.standardize(_surprise_frame("nvda", [2.0, 1.0, 3.0, 2.0, 4.0], start="2018-02-20"))
    s = pd.concat([a, b], ignore_index=True)
    idx = GR.surprise_index(s)
    last_q = a["index_quarter"].iloc[4]
    assert last_q == b["index_quarter"].iloc[4]
    row = idx[idx["period"] == last_q]
    assert len(row) == 1 and row["n"].iloc[0] == 2
    assert row["value"].iloc[0] == pytest.approx((a["z"].iloc[4] + b["z"].iloc[4]) / 2)
    assert row["known_from"].iloc[0] == b["outcome_known_from"].iloc[4]
    assert GR.surprise_index(a).empty  # one company only


def _tsmc_world():
    """TSMC 2016Q1-2019Q4: NT$ guidance until 2017Q2, US$ x fx after; monthly revenue known on the 10th."""
    rows, months = [], []
    for q in pd.period_range("2016Q1", "2019Q4", freq="Q-DEC"):
        start = q.asfreq("M", "s")
        kf = (start.to_timestamp() + pd.Timedelta(days=14))
        rev_q = 300_000 * (1.03 ** (q.ordinal - pd.Period("2016Q1", "Q-DEC").ordinal))
        if q < pd.Period("2017Q3", "Q-DEC"):
            rows += [("tsmc_guid_rev_twd_lo", q, rev_q * 0.97, kf), ("tsmc_guid_rev_twd_hi", q, rev_q * 0.99, kf)]
        else:
            rows += [("tsmc_guid_rev_usd_lo", q, rev_q * 0.97 / 30, kf),
                     ("tsmc_guid_rev_usd_hi", q, rev_q * 0.99 / 30, kf), ("tsmc_guid_fx", q, 30.0, kf)]
        for k, m in enumerate(pd.period_range(start, periods=3, freq="M")):
            months.append((m, rev_q / 3 * (1.0 + 0.01 * k), (m + 1).to_timestamp() + pd.Timedelta(days=9)))
    g = pd.concat([obs(k, "Q", [p], [v], [d]) for k, p, v, d in rows], ignore_index=True)
    m = obs("tsmc_revenue_m", "M", [x[0] for x in months], [x[1] for x in months], [x[2] for x in months])
    return pd.concat([g, m], ignore_index=True)


def test_tsmc_surprise_uses_b2_basis_and_the_guidance_known_before_the_outcome():
    t = _tsmc_world()
    s = pd.DataFrame(GR.tsmc_surprises(t), columns=GR.SURPRISE_COLUMNS)
    assert len(s) == 16 and set(s["company"]) == {"tsmc"}
    r = s[s["period"] == "2018Q2"].iloc[0]
    months = t[(t["series"] == "tsmc_revenue_m") & t["period"].isin(["2018-04", "2018-05", "2018-06"])]
    u = months["value"].sum()
    assert r["outcome"] == pytest.approx(u)
    lo = t[(t["series"] == "tsmc_guid_rev_usd_lo") & (t["period"] == "2018Q2")]["value"].iloc[0]
    hi = t[(t["series"] == "tsmc_guid_rev_usd_hi") & (t["period"] == "2018Q2")]["value"].iloc[0]
    assert r["guidance"] == pytest.approx((lo + hi) / 2 * 30.0)
    assert r["s"] == pytest.approx(100 * math.log(u / ((lo + hi) / 2 * 30.0)))
    assert r["outcome_known_from"] == months["known_from"].max()
    # a mid-quarter update known after the outcome is not used
    late = obs("tsmc_guid_rev_usd_hi", "Q", ["2018Q2"], [hi * 2], [r["outcome_known_from"]])
    s2 = pd.DataFrame(GR.tsmc_surprises(pd.concat([t, late], ignore_index=True)), columns=GR.SURPRISE_COLUMNS)
    assert s2.loc[s2["period"] == "2018Q2", "s"].iloc[0] == pytest.approx(r["s"])


def test_capex_surprise_sums_four_first_vintages_and_uses_the_last_guidance_before():
    q = [f"2024Q{k}" for k in (1, 2, 3, 4)]
    kf = ["2024-04-25", "2024-07-31", "2024-10-30", "2025-01-29"]
    capex = obs("capex_meta", "Q", q, [9.0, 8.0, 8.5, 14.0], kf)
    rev = obs("capex_meta", "Q", ["2024Q1"], [99.0], ["2025-02-03"])  # a later revision is never used
    lease = obs("fin_lease_meta", "Q", q, [0.5, 0.5, 0.6, 0.4], kf)
    csv = csv_rows([{"period": "2024", "lo": 30, "hi": 37, "filed": "2024-02-01"},
                    {"period": "2024", "lo": 38, "hi": 40, "filed": "2024-10-30"},
                    {"period": "2024", "lo": 50, "hi": 60, "filed": "2025-01-29"}])  # same day as outcome: after
    s = GR.capex_surprises(pd.concat([capex, rev, lease], ignore_index=True), csv)
    assert len(s) == 1
    company, _m, period, freq, iq, u, ukf, g, gkf, val = s[0]
    assert (company, period, freq, iq) == ("meta", "2024", "A", "2024Q4")
    assert u == pytest.approx(9 + 8 + 8.5 + 14 + 0.5 + 0.5 + 0.6 + 0.4) and g == pytest.approx(39.0)
    assert str(ukf.date()) == "2025-01-29" and str(gkf.date()) == "2024-10-30"
    assert val == pytest.approx(100 * math.log(u / 39.0))


# ------------------------------------------------------------------ as_of truncation


def _world():
    t = _tsmc_world()
    nv_q = pd.period_range("2017Q2", "2019Q4", freq="Q-DEC")
    nv_g = obs("nvda_guid_rev_mid", "Q", nv_q, [2000 * 1.05 ** i for i in range(len(nv_q))],
               [q.start_time + pd.Timedelta(days=50) for q in nv_q])
    nv_r = obs("rev_nvda", "Q", nv_q, [2000 * 1.05 ** i * (1.04 + 0.01 * (i % 3)) for i in range(len(nv_q))],
               [q.end_time.normalize() + pd.Timedelta(days=55) for q in nv_q])
    update = obs("tsmc_guid_rev_usd_hi", "Q", ["2019Q1"], [11000.0], ["2019-02-15"])
    csv = csv_rows([{"period": "2018", "lo": 10, "hi": 12, "filed": "2017-10-30"},
                    {"period": "2018", "lo": 11, "hi": 13, "filed": "2018-01-30"},
                    {"period": "2018", "lo": 11, "hi": 13, "filed": "2018-04-30"},
                    {"period": "2018", "lo": 12, "hi": 13, "filed": "2018-07-30"},
                    {"period": "2019", "kind": "direction", "code": 1, "filed": "2018-07-30"},
                    {"period": "2019", "kind": "direction", "code": 2, "filed": "2018-10-30"},
                    {"period": "2018", "lo": 12, "hi": 14, "filed": "2018-10-30"},
                    {"company": "amzn", "period": "2019", "kind": "direction", "code": 1,
                     "definition": "AMZN_CASH_CAPEX", "filed": "2018-07-27"},
                    {"company": "amzn", "period": "2019", "kind": "direction", "code": 1,
                     "definition": "AMZN_CASH_CAPEX", "filed": "2018-10-26"},
                    {"company": "googl", "period": "2019", "kind": "approx", "lo": 20, "definition": "GOOGL_CAPEX",
                     "filed": "2019-02-04"},
                    {"company": "googl", "period": "2019", "kind": "approx", "lo": 22, "definition": "GOOGL_CAPEX",
                     "filed": "2019-07-23"},
                    {"period": "2019", "lo": 15, "hi": 17, "filed": "2019-01-30"},
                    {"period": "2019", "lo": 16, "hi": 17, "filed": "2019-04-30"}])
    return pd.concat([t, nv_g, nv_r, update], ignore_index=True), csv


def _latest(df, cols, when):
    d = df[pd.to_datetime(df["known_from"]) <= pd.Timestamp(when)].sort_values("known_from", kind="stable")
    out = d.groupby("period").tail(1).set_index("period")[cols].sort_index()
    out.index = out.index.astype(object)
    return out.astype(float)


@pytest.mark.parametrize("when", ["2018-03-31", "2018-09-30", "2019-02-14", "2019-02-28", "2019-06-30", "2019-12-31"])
def test_as_of_truncation_gives_identical_values(when):
    table, csv = _world()
    full = GR.compute(table, csv, "2020-06-30")
    # computed the day after `when` from what was known on `when`: a closing version dated `when` (a quarter's last
    # day) is emitted once that day has passed (register, R11-2)
    cut = GR.compute(table[table["known_from"] <= pd.Timestamp(when)],
                     csv[csv["known_from"] <= pd.Timestamp(when)], pd.Timestamp(when) + pd.Timedelta(days=1))
    for w in GR.WINDOWS:
        a = _latest(full["index"][w], ["n", "n_up", "n_unchanged", "n_down", "index", "median_size"], when)
        b = _latest(cut["index"][w], ["n", "n_up", "n_unchanged", "n_down", "index", "median_size"], when)
        pd.testing.assert_frame_equal(a, b, check_dtype=False)
    ev_full = full["events"][full["events"]["known_from"] <= pd.Timestamp(when)].reset_index(drop=True)
    pd.testing.assert_frame_equal(ev_full, cut["events"].reset_index(drop=True), check_dtype=False)
    sf = full["surprises"][full["surprises"]["outcome_known_from"] <= pd.Timestamp(when)]
    cols = ["company", "period", "s", "z", "n_past"]
    pd.testing.assert_frame_equal(sf[cols].reset_index(drop=True), cut["surprises"][cols].reset_index(drop=True),
                                  check_dtype=False)
    pd.testing.assert_frame_equal(_latest(full["surprise_index"], ["value", "n"], when),
                                  _latest(cut["surprise_index"], ["value", "n"], when), check_dtype=False)


def test_world_has_events_surprises_and_an_index():
    table, csv = _world()
    out = GR.compute(table, csv, "2020-06-30")
    assert len(out["events"]) >= 6 and set(out["events"]["company"]) >= {"meta", "tsmc", "googl"}
    assert out["surprises"]["z"].notna().sum() >= 10 and len(out["surprise_index"]) > 0
    assert out["index"][4]["index"].notna().sum() >= 2 and out["index"][1]["index"].notna().sum() >= 1


def test_registered_start(monkeypatch):
    monkeypatch.setattr(GR, "COVERAGE_FROM", pd.Period("2020Q3", "Q-DEC"))
    table, csv = _world()
    assert GR.compute(table, csv, "2020-06-30")["index"][4].empty
    assert str(GR.revision_index(GR.events(GR.statements(table, csv)), 4, "2020-12-31")["period"].min()) == "2020Q3"


def test_series_rows_are_release_dated_and_unique():
    table, csv = _world()
    out = GR.compute(table, csv, "2020-06-30")
    for key in GR.KEYS:
        d = GR._series(key, out)
        assert list(d.columns) == ["period", "value", "known_from", "source"]
        assert not d.duplicated(["period", "known_from"]).any()
        assert np.isfinite(d["value"].astype(float)).all()


# ------------------------------------------------------------------ TSMC capex outlook parse


@pytest.mark.parametrize("text, filed, expect", [
    ("2031 capital budget to be between US$40 billion and US$44 billion.", "2031-01-16", ("range", 40000, 44000)),
    ("TSMC further expects the capital expenditures for 2031 to be about US$7 billion.", "2031-01-16",
     ("approx", 7000, 7000)),
    ("2031 capital expenditure to be around US$ 4.5 billion.", "2031-04-20", ("approx", 4500, 4500)),
    ("For year 2031, total capital expenditure for TSMC consolidated group is expected to be in the range of "
     "US$2.1 billion to US$2.3 billion.", "2031-04-20", ("range", 2100, 2300)),
    ("TSMC further raises the capital expenditure estimate for 2031 to be in the range between US$9.1 billion "
     "and US$9.4 billion.", "2031-04-20", ("range", 9100, 9400)),
])
def test_tsmc_capex_parse_accepts_the_registered_form(text, filed, expect):
    r = TC.parse(text, filed)
    assert len(r) == 1 and r[0]["year"] == 2031 and (r[0]["kind"], r[0]["lo"], r[0]["hi"]) == expect
    assert len(r[0]["sentence_sha256"]) == 64


@pytest.mark.parametrize("text, filed", [
    ("The management further expects the 2031 capital budget to be slightly above US$9.5 billion.", "2031-10-13"),
    ("2030 capital expenditures were about US$1.9 billion.", "2031-01-16"),  # an outcome
    ("2029 capital budget to be between US$1 billion and US$2 billion.", "2031-01-16"),  # an earlier year
    ("2031 capital expenditure is expected to be above both the 2030 expenditure of US$1.9 billion.", "2031-10-29"),
    ("Approved capital appropriations of approximately US$4.9 billion.", "2031-02-14"),
])
def test_tsmc_capex_parse_rejects_other_forms(text, filed):
    assert TC.parse(text, filed) == []


def test_tsmc_capex_vintages_drop_repeats():
    recs = pd.DataFrame({"period": ["2031", "2031", "2031"], "lo": [40000.0, 40000.0, 42000.0],
                         "hi": [44000.0, 44000.0, 44000.0], "filed": ["2031-01-16", "2031-04-17", "2031-07-16"],
                         "accepted": "", "accession": ["a", "b", "c"]})
    v = TC.vintages(recs, "lo")
    assert list(v["value"]) == [40000.0, 42000.0]
    t = pd.concat([obs("tsmc_guid_capex_lo", "A", v["period"], v["value"], v["known_from"]),
                   obs("tsmc_guid_capex_hi", "A", ["2031"], [44000.0], ["2031-01-16"])], ignore_index=True)
    ev = ev_of(table=t)
    assert len(ev) == 1 and ev["direction"].iloc[0] == 1 and ev["definition"].iloc[0] == "TSMC_CAPEX_USD"


# ------------------------------------------------------------------ catalog and snapshot


def test_catalog_contract():
    specs = {s.key: s for s in GR.SPECS}
    specs_all = catalog.by_key()
    assert catalog.validate(GR.SPECS) == []
    assert set(GR.KEYS) <= set(catalog.by_key())
    gate = GR.csv_component_keys()
    assert gate and all(k.startswith("guid_capex_") for k in gate)
    for key in GR.KEYS:
        s = specs[key]
        assert s.max_age_days and s.note.startswith("Grupp") and s.branch in ("G5", "G6")
        if key in GR.CSV_BASED:  # reads the curated CSV: declares the rows it reads and follows their gate (R11-4)
            reads = GR.CSV_READS.get(key)
            assert s.components == GR.COMPONENTS + GR.csv_component_keys(reads)
            assert s.publish == (all(specs_all[k].publish for k in GR.csv_component_keys(reads))
                                 and key not in GR.AWAITING_OWNER)
        else:
            assert s.publish and s.components == GR.COMPONENTS
    assert {"tsmc_guid_capex_lo", "tsmc_guid_capex_hi", "tsmc_rev_usd_q"} <= set(specs)


def test_group_is_never_in_a_branch_index():
    from ai_tracker.state import register as R

    core = {k for code in catalog.BRANCHES for k in R.core_entries(code, R.CORE_SERIES)}
    assert not core & set(GR.KEYS)


def test_expectations_section_is_json_clean_and_outside_diffusion():
    table, csv = _world()
    sec = E.section("2019-12-31", table, csv)
    assert sec["in_diffusion"] is False and sec["group"] == GR.GROUP
    text = json.dumps(S._clean(sec), ensure_ascii=False)
    assert "NaN" not in text
    main = sec["revisions"]["window_4q"]
    # 2019Q4 has no event: its closing version is dated 2019-12-31 but emitted once that day has passed (R11-2)
    assert main["latest"]["period"] == "2019Q3"
    after = E.section("2020-01-01", table, csv)["revisions"]["window_4q"]["latest"]
    assert after["period"] == "2019Q4" and after["known_from"] == "2019-12-31"
    assert {c["company"] for c in sec["surprise"]["companies"]} >= {"tsmc", "nvda"}
    assert sec["events_recent"] and sec["events_per_company_year"]["meta"]


def test_expectations_section_equals_catalog_series_as_of():
    table, csv = _world()
    when = "2019-06-30"
    sec = E.section(when, table, csv)
    out = GR.compute(table, csv, "2020-06-30")
    r4 = _latest(out["index"][4], ["index", "n"], when)
    entry = sec["revisions"]["window_4q"]["latest_with_value"]
    assert entry["index"] == pytest.approx(r4.loc[entry["period"], "index"])
    si = _latest(out["surprise_index"], ["value", "n"], when)
    entry = sec["surprise"]["index"]["latest_with_value"]
    assert entry["value"] == pytest.approx(si.loc[entry["period"], "value"])


def test_safe_section_records_a_failure():
    sec = E.safe_section("2026-10-31", "not a table")
    assert sec["in_diffusion"] is False and "error" in sec


def test_snapshot_writer_adds_the_section(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "compute", lambda when, ctx: {"G6": {"index": 1.0, "state": "x"}})
    table, csv = _world()
    monkeypatch.setattr(GR, "load_csv", lambda: csv)
    p = S.write("2019-12-31", table, tmp_path, today="2026-11-23", regime=False)
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d[E.SECTION]["group"] == GR.GROUP and "error" not in d[E.SECTION]


def test_curated_csv_loads_into_statements():
    if not guidance_capex.PATH.exists():
        pytest.skip("curated CSV missing")
    st = GR.capex_statements(guidance_capex.load())
    assert len(st) == len(guidance_capex.load()) and set(st["chain"]) >= {"num", "min"}
    assert any(st["definition"].str.contains("~"))  # msft-r11f1 starts a new item
