"""R29 adversarial review of run 17 (S1, AN1, QA1, PV1): docs/granskning/r29_korning17.md. No network.

Evidence was read on 2026-11-27 in the code, the register, the observation table (876 series, fetched 2026-11-27), the
five Anthropic prospectuses (S-1, three S-1/A, 424B4) and nine Quanta 10-Q/10-K fetched again from www.sec.gov
(generic client identity from the environment, one request at a time, nothing saved in the shared cache). Only ids,
numbers and dates are kept here, never filing text.

- Pinned: the five register entries of 2026-11-27 as R29 read them, 24 AN1 values and 16 QA1 rows that R29 read in the
  filings with its own parser (lxml, not the project's line list).
- Properties that hold: PV1's months and weeks give the quarter R29 computed by hand, and a mirrored price gives the
  mirrored outcome on the real table.
- Findings R29-2 to R29-5 were strict xfails; X26 (register 2026-11-27 X26) fixed them and they are plain tests now.
  R29-2 is fixed by rows beside the locked ones (geometric mean), so the locked arithmetic mean is pinned as it is.
"""

from __future__ import annotations

import hashlib
import inspect
import math

import numpy as np
import pandas as pd
import pytest

from ai_tracker import config
from ai_tracker.followed import elflaskhalsen as E
from ai_tracker.followed import prisvolym as P
from ai_tracker.sources import acquisitions as ACQ
from ai_tracker.sources import anthropic_gaap as AG

REGISTER = config.REPO / "docs" / "mattregister.md"
RESULTS = config.REPO / "docs" / "resultat"

# ------------------------------------------------------------------ pinned: the register entries R29 read

ENTRIES = {  # heading -> sha256 of the entry's text after the heading line, up to the next "### "
    "### 2026-11-27 – S1: symmetriska rader bredvid låsta regler":
        "a1ba35dfb6b862819cd45a49ca8ef862c0ad019cef2d944f6f3c6b56d0441da3",
    "### 2026-11-27 – AN1: Anthropics redovisade (GAAP) intäkter och resultatposter ur registreringsprospektet "
    "(katalogserier, före extraktion)":
        "77cb2a755383dee44b547a7af69d77c3724765489c6898a02589d17099a66a4b",
    "### 2026-11-27 – AN1, tillägg efter extraktionen: tolkningar (inga regler ändrade)":
        "2808cbf490a522bc03807e3ef8e203d0b538ce4c5954a9dea35caa68a36df9d9",
    "### 2026-11-27 – QA1: Quantas förvärv som data i LT1:s förvärvsmärke (rättning efter R28-7, ingen regel ändras)":
        "2011713905097074f28bf947eb595ae7e18cd56a4c9aac154f2c340fe2efa3e3",
    "### 2026-11-27 – PV1: följd fråga om pris mot volym (prisfall vid fast förmåga mot användningens takt)":
        "8a6b17da259a3cbdfcf3e4dd90196f79d11dcb971007d7839025ec91e0ec87e4",
}


def test_register_entries_are_the_ones_r29_reviewed():
    text = REGISTER.read_text(encoding="utf-8")
    for head, digest in ENTRIES.items():
        assert head + "\n" in text, head
        entry = text.split(head + "\n", 1)[1].split("\n### ", 1)[0]
        assert hashlib.sha256(entry.encode("utf-8")).hexdigest() == digest, head


# ------------------------------------------------------------------ pinned: AN1 values R29 read in the filings

# (series, period) -> (value MUSD, known_from = filing date of the first prospectus stating it). R29 read every one of
# the 297 CSV values with its own lxml table reading of fresh copies; these are the ones BG1 shows and the sums use.
AN1 = {
    ("lab_gaap_anthropic_revenue_q", "2025Q1"): (376.0, "2026-10-26"),
    ("lab_gaap_anthropic_revenue_q", "2025Q4"): (2040.0, "2026-10-26"),
    ("lab_gaap_anthropic_revenue_q", "2026Q2"): (11555.0, "2026-10-26"),
    ("lab_gaap_anthropic_revenue_q", "2026Q3"): (16956.0, "2026-11-02"),
    ("lab_gaap_anthropic_compute_q", "2025Q1"): (944.0, "2026-10-26"),
    ("lab_gaap_anthropic_compute_q", "2026Q3"): (9863.0, "2026-11-02"),
    ("lab_gaap_anthropic_opinc_q", "2025Q1"): (-935.0, "2026-10-26"),
    ("lab_gaap_anthropic_opinc_q", "2026Q2"): (974.0, "2026-10-26"),
    ("lab_gaap_anthropic_opinc_q", "2026Q3"): (-567.0, "2026-11-02"),
    ("lab_gaap_anthropic_revenue_a", "2023"): (41.0, "2026-10-26"),
    ("lab_gaap_anthropic_revenue_a", "2024"): (386.0, "2026-10-26"),
    ("lab_gaap_anthropic_revenue_a", "2025"): (4585.0, "2026-10-26"),
    ("lab_gaap_anthropic_compute_a", "2025"): (7326.0, "2026-10-26"),
    ("lab_gaap_anthropic_opinc_a", "2025"): (-8060.0, "2026-10-26"),
    ("lab_gaap_anthropic_cost_of_revenue_a", "2024"): (752.0, "2026-10-26"),
    ("lab_gaap_anthropic_cost_of_revenue_a", "2025"): (2773.0, "2026-10-26"),
    ("lab_gaap_anthropic_gross_profit_a", "2025"): (1812.0, "2026-10-26"),
    ("lab_gaap_anthropic_cfo_a", "2025"): (-2637.0, "2026-10-26"),
    ("lab_gaap_anthropic_cfo_ytd", "2026Q2"): (3929.0, "2026-10-26"),
    ("lab_gaap_anthropic_cfo_ytd", "2026Q3"): (6569.0, "2026-11-02"),
    ("lab_gaap_anthropic_capex_a", "2025"): (131.0, "2026-10-26"),
    ("lab_gaap_anthropic_capex_ytd", "2026Q3"): (925.0, "2026-11-02"),
    ("lab_gaap_anthropic_prepay_leased_ytd", "2026Q3"): (1955.0, "2026-11-02"),
    ("lab_gaap_anthropic_revenue_ytd", "2026Q3"): (33242.0, "2026-11-02"),
}


def test_an1_values_r29_read_in_the_prospectuses():
    df = AG.load()
    for (key, period), (value, kf) in AN1.items():
        v = AG.versions(df, key)
        row = v[v["period"] == period]
        assert len(row) == 1, (key, period)  # one version: no prospectus changed a value
        assert row["value"].iloc[0] == value, (key, period)
        assert str(row["known_from"].iloc[0].date()) == kf, (key, period)


def test_an1_quarters_add_up_to_the_year_and_the_year_to_date():
    df = AG.load()
    lv = AG.latest_values(df)
    for item in ("revenue", "compute", "opinc"):
        q = {p: lv[(f"lab_gaap_anthropic_{item}_q", p)] for p in ("2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1",
                                                                  "2026Q2", "2026Q3")}
        assert sum(q[f"2025Q{i}"] for i in range(1, 5)) == lv[(f"lab_gaap_anthropic_{item}_a", "2025")]
        assert sum(q[f"2026Q{i}"] for i in range(1, 4)) == lv[(f"lab_gaap_anthropic_{item}_ytd", "2026Q3")]
        assert q["2026Q1"] + q["2026Q2"] == lv[(f"lab_gaap_anthropic_{item}_ytd", "2026Q2")]


# ------------------------------------------------------------------ pinned: QA1 rows R29 read in Quanta's filings

QA1 = {  # id -> (row_type, the figure R29 read: closing day, count or consideration in MUSD), filed
    "pwr-2023Q3-02": ("count", 4, "2023-11-02"),
    "pwr-2023Q3-03": ("consideration", 622.474, "2023-11-02"),
    "pwr-2023Q4-02": ("consideration", 300.0, "2023-11-02"),
    "pwr-2024Q2-04": ("count", 5, "2024-08-01"),
    "pwr-2024Q2-05": ("consideration", 540.168, "2024-08-01"),
    "pwr-2024Q3-cei-01": ("acquisition", "2024-07-17", "2024-08-01"),
    "pwr-2024Q3-cei-02": ("consideration", 1967.723, "2024-10-31"),
    "pwr-2024Q3-02": ("count", 8, "2024-10-31"),
    "pwr-2025Q2-01": ("count", 4, "2025-07-31"),
    "pwr-2025Q3-dsi-01": ("acquisition", "2025-07-25", "2025-07-31"),
    "pwr-2025Q3-dsi-04": ("consideration", 1673.326, "2026-02-19"),
    "pwr-2025Q4-02": ("count", 8, "2026-02-19"),
    "pwr-2026Q2-02": ("acquisition", "2026-06-18", "2026-07-30"),
    "pwr-2026Q2-03": ("consideration", 1430.107, "2026-07-30"),
    "pwr-2026Q3-04": ("count", 5, "2026-10-29"),
    "pwr-2026Q3-05": ("consideration", 1799.666, "2026-10-29"),
}


def test_qa1_rows_r29_read_in_the_filings():
    df = ACQ.load().set_index("id")
    for rid, (kind, fig, filed) in QA1.items():
        r = df.loc[rid]
        assert r["row_type"] == kind and r["filed"] == filed, rid
        if kind == "count":
            assert r["n_businesses"] == fig, rid
        elif kind == "consideration":
            assert math.isclose(r["consideration_musd"], fig), rid
        else:
            assert r["closed"] == fig and r["quarter"] == ACQ.quarter_of(fig), rid
    # the 2026Q1 10-Q states that no acquisition was completed in the quarter
    assert df.loc["pwr-2026Q1-01", "row_type"] == "none"


def test_qa1_mark_moves_the_change_in_pace_up_at_a_and_a1_down_at_a4_and_a5():
    from ai_tracker.followed import ledtid as L

    marks = L.acquisition_quarters("L1", "2026-11-27")
    assert "Quanta, 3 förvärv 2026Q2" in marks["2026Q2"] and "2026Q2 (" in marks["2026Q2"]
    q2 = [m for m in marks["2026Q2"].split("; ") if m.startswith("Quanta, 3 förvärv 2026Q2")][0]
    assert q2.endswith("a, upp")
    assert any(m.startswith("Quanta, 3 förvärv 2026Q2") and m.endswith("a + 4, ned") for m in marks["2027Q2"].split("; "))


# ------------------------------------------------------------------ PV1: aggregation and symmetry


def _row(series, freq, period, value, kf):
    return {"series": series, "freq": freq, "period": period, "value": float(value), "known_from": pd.Timestamp(kf),
            "source": "release", "fetched_at": pd.Timestamp("2026-11-27")}


def _monthly(series, values: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame([_row(series, "M", m, v, pd.Period(m, freq="M").end_time.normalize() + pd.Timedelta(days=1))
                         for m, v in values.items()])


STEP = {**{str(m): 2.0 for m in pd.period_range("2024-01", "2024-08", freq="M")},
        **{str(m): 0.5 for m in pd.period_range("2024-09", "2026-06", freq="M")}}  # a price step in the quarter's last month


def _change(values: dict[str, float], geometric: bool = False) -> dict[str, float]:
    q = P.monthly_quarters(_monthly(P.PRICE_GPQA, values), (P.PRICE_GPQA,), geometric=geometric)
    pm = P.C.path_measures({k: v for k, (v, _) in q.items()}, "log")
    return {k: float(v) for k, v in pm["change"].dropna().items()}


def test_pv1_quarter_is_the_mean_of_its_three_months_r29_by_hand():
    q = P.monthly_quarters(_monthly(P.PRICE_GPQA, STEP), (P.PRICE_GPQA,))
    assert math.isclose(q["2024Q3"][0], (2.0 + 2.0 + 0.5) / 3.0)
    assert q["2024Q3"][1] == "2024-10-01"


def test_pv1_mirrored_price_gives_the_mirrored_change_in_pace():
    """R29-2, fixed in X26: the geometric rows (H-G, a-G, b-G) are exactly symmetric."""
    up = _change(STEP, geometric=True)
    down = _change({m: 1.0 / v for m, v in STEP.items()}, geometric=True)
    assert up and set(up) == set(down)
    for q in up:
        assert math.isclose(up[q], -down[q], abs_tol=1e-6), (q, up[q], down[q])


def test_pv1_locked_arithmetic_mean_stays_as_registered_and_is_not_symmetric():
    """X26 adds rows beside the locked ones: the locked arithmetic mean is unchanged, and R29's step example holds."""
    up = _change(STEP)
    down = _change({m: 1.0 / v for m, v in STEP.items()})
    assert (round(up["2025Q3"], 1), round(down["2025Q3"], 1)) == (28.8, -69.3)  # no impulse one way, one the other
    assert any(not math.isclose(up[q], -down[q], abs_tol=1e-6) for q in up)


def test_pv1_report_says_the_history_is_a_backfill():
    doc = (RESULTS / "prisvolym.md").read_text(encoding="utf-8")
    caveats = doc.split("## 5. Förbehåll", 1)[1].split("\n## ", 1)[0]
    assert "backfill" in caveats.lower() or "i efterhand" in caveats


# ------------------------------------------------------------------ QA1: mark text on historical days


def test_qa1_label_states_only_what_was_filed_on_the_day():
    m = [x for x in ACQ.marks("pwr", "2024-02-25") if x[1] == "2024Q1"]
    assert m and "3 förvärv" not in m[0][0]


def test_qa1_cupertino_has_its_first_stated_consideration():
    m = [x for x in ACQ.marks("pwr", "2024-08-15") if "Cupertino" in x[0]]
    assert m and "MUSD" in m[0][0]


# ------------------------------------------------------------------ S1: EL1-S text after QA1


def test_el1s_text_does_not_say_quanta_is_unchecked():
    phrase = "Quantas förvärv är inte kontrollerade"
    assert phrase not in inspect.getsource(E)
    assert phrase not in (RESULTS / "elflaskhalsen.md").read_text(encoding="utf-8")


# ------------------------------------------------------------------ real table: R29's own recomputation


def _latest(t: pd.DataFrame, s: str, day: str) -> pd.Series:
    x = t[(t["series"] == s) & (pd.to_datetime(t["known_from"]) <= pd.Timestamp(day))]
    return x.sort_values("known_from", kind="stable").groupby("period")["value"].last()


@pytest.mark.real_data
def test_pv1_side_reading_a_recomputed_without_the_module():
    """Arena price quarter means and their change in pace, computed here with pandas only, equal the report's."""
    from ai_tracker import observations

    t = observations.load()
    m = _latest(t, P.PRICE_ARENA, "2026-11-27")
    m.index = pd.PeriodIndex(m.index.astype(str), freq="M")
    q = {}
    for p in sorted({x.asfreq("Q-DEC") for x in m.index}):
        ms = [p.asfreq("M", "start") + i for i in range(3)]
        if all(x in m.index for x in ms):
            q[p] = float(np.mean([m[x] for x in ms]))
    s = pd.Series(q).sort_index()
    y = 100 * np.log(s)
    pace = y - y.shift(4)
    change = (pace - pace.shift(2)).dropna().round(1)
    mine = {str(k): float(v) for k, v in change.items()}
    assert mine == {"2025Q3": 441.0, "2025Q4": 346.0, "2026Q1": 3.0, "2026Q2": -37.7, "2026Q3": 0.0}
    r = P.compute("2026-11-27", t)["readings"]["a"]
    assert r["outcome"] == P.C.NEITHER
    assert [(d["origin"], d["outcome"]) for d in r["decided"]] == [("2025Q3", P.C.AGAINST), ("2025Q4", P.C.AGAINST)]
