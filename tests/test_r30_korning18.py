"""R30 independent review of run 18 (B18 owner decisions 1-3, DA1 acquisitions in L2 and L3):
docs/granskning/r30_korning18.md. No network.

Evidence was read on 2026-11-27 in the code, the register, the observation table (876 series) and all 48 Dell, Super
Micro and Equinix 10-Q/10-K documents behind DA1's 47 rows, fetched again from www.sec.gov with the generic client
identity from the environment (saved only in R30's scratch directory). Only ids, numbers and dates are kept here, never
filing text.

- Pinned: the two register entries of run 18 as R30 read them, 16 DA1 rows that R30 read in the filings, and the
  quarters and directions of the L2 and L3 marks per reading day.
- Properties that hold: L2's readings per 2026-11-27 recomputed straight from observations.parquet with pandas (no
  project module) give the outcomes in the report, and the DA1 bound of 28.7 bn USD.
- Findings R30-1 to R30-3 are strict xfails.
"""

from __future__ import annotations

import hashlib
import math
import re

import pandas as pd
import pytest

from ai_tracker import config
from ai_tracker.followed import ledtid as L
from ai_tracker.sources import acquisitions as ACQ

REGISTER = config.REPO / "docs" / "mattregister.md"
SOURCE_DOC = config.REPO / "docs" / "kallor" / "ledtid.md"


def _entry(head: str) -> str:
    text = REGISTER.read_text(encoding="utf-8")
    return text.split(head + "\n", 1)[1].split("\n### ", 1)[0]


# ------------------------------------------------------------------ pinned: the register entries R30 read

ENTRIES = {
    "### 2026-11-27 – DA1: förvärv hos Dell, Super Micro och Equinix i LT1:s förvärvsmärke (L2 och L3, ingen regel "
    "ändras)": "fd537a3448bbf98c4506b9f5b2bf3de18b28ec18efedbabc1b45cbaa840632a9",
    "### 2026-11-27 – B18: ägarbeslut efter R29": "e73950e43ee9e3df7d6fda194a8202c569aa9fce4cfe8faf6ec921ec04bb9543",
}


@pytest.mark.parametrize("head", list(ENTRIES))
def test_register_entries_of_run_18_are_as_r30_read_them(head):
    assert hashlib.sha256(_entry(head).encode("utf-8")).hexdigest() == ENTRIES[head]


# ------------------------------------------------------------------ pinned: DA1 rows R30 read in the filings

# id -> (accession, filed, locator, quarter a, what R30 read in the sentence at the locator)
READ = {
    "dell-2023Q3-moog-01": ("0001571996-23-000046", "2023-12-08", "sentence #799", "2023Q3",
                            "Moogsoft goodwill in the three months to 2023-11-03"),
    "dell-2023Q3-moog-02": ("0001571996-24-000036", "2024-03-25", "sentence #2770", "2023Q3",
                            "Moogsoft goodwill in the fiscal year to 2024-02-02"),
    "dell-2023Q4-01": ("0001571996-24-000036", "2024-03-25", "sentence #1816", "2023Q4",
                       "acquisitions 126 for the year (127 in nine months, #170 of the 10-Q)"),
    "dell-2024Q3-01": ("0001571996-24-000143", "2024-12-10", "sentence #166", "2024Q3", "nil for nine months"),
    "dell-2024Q4-01": ("0001571996-25-000034", "2025-03-25", "sentence #1827", "2024Q4", "nil for the year"),
    "dell-2025Q3-01": ("0001571996-25-000127", "2025-12-09", "sentence #160", "2025Q3", "no acquisition line"),
    "dell-2025Q4-01": ("0001571996-26-000008", "2026-03-16", "sentence #2609", "2025Q4",
                       "goodwill acquired 61 (ISG), none in nine months; cash 84 at #1725"),
    "dell-2026Q2-01": ("0001571996-26-000046", "2026-09-08", "sentence #149", "2026Q2", "no acquisition line"),
    "smci-2023Q2-gem-01": ("0001375365-23-000036", "2023-08-28", "sentence #1459", "2023Q2",
                           "closing 2023-04-17; the 10-Q filed 2023-05-05 does not name Gemini"),
    "smci-2023Q2-gem-02": ("0001375365-23-000036", "2023-08-28", "sentence #1458", "2023Q2", "2.5 with 0.3 held back"),
    "smci-2024Q2-01": ("0001375365-25-000004", "2025-02-25", "sentence #1853", "2024Q2", "0.296 = the holdback"),
    "eqix-2025Q2-tim-01": ("0001101239-25-000029", "2025-07-30", "sentence #288", "2025Q2",
                           "TIM NextGen DC, three data centers in the Philippines, closed 2025-06-02, 183"),
    "eqix-2025Q3-01": ("0001101239-25-000062", "2025-10-29", "sentence #205", "2025Q3", "182 in nine months"),
    "eqix-2025Q4-01": ("0001101239-26-000032", "2026-02-11", "sentence #1467", "2025Q4",
                       "251 for the year against 182 in nine months; goodwill additions EMEA 11 at #2682"),
    "eqix-2026Q2-01": ("0001101239-26-000147", "2026-07-29", "sentence #203", "2026Q2", "nil for six months"),
    "eqix-2026Q3-01": ("0001101239-26-000180", "2026-10-28", "sentence #205", "2026Q3", "nil for nine months"),
}


@pytest.fixture(scope="module")
def df():
    return ACQ.load()


@pytest.mark.parametrize("rid", list(READ))
def test_da1_rows_r30_read_in_the_filings(df, rid):
    acc, filed, loc, q, _ = READ[rid]
    r = df.set_index("id").loc[rid]
    assert (r["accession"], r["filed"], r["locator"], r["quarter"]) == (acc, filed, loc, q)


def test_da1_consideration_and_closing_dates_r30_read(df):
    d = df.set_index("id")
    assert float(d.loc["smci-2023Q2-gem-02", "consideration_musd"]) == 2.5
    assert d.loc["smci-2023Q2-gem-01", "closed"] == "2023-04-17"
    assert float(d.loc["eqix-2025Q2-tim-02", "consideration_musd"]) == 183.0
    assert d.loc["eqix-2025Q2-tim-01", "closed"] == "2025-06-02"
    assert d.loc["dell-2023Q3-moog-01", "closed"] == ""  # Dell states the fiscal quarter, not a day


# ------------------------------------------------------------------ pinned: marks per reading day

def test_l2_and_l3_marks_land_in_the_quarter_and_direction_r30_derived():
    l2 = L.acquisition_quarters("L2", "2026-11-27")
    assert l2["2023Q3"].startswith("Dell–Moogsoft a, upp")  # fiscal Q3 to 2023-11-03 = rpo_dell 2023Q3
    assert l2["2024Q4"] == "Dell–Moogsoft a + 5, ned"
    assert l2["2025Q4"] == "Dell, ej namngivet förvärv 2025Q4 a, upp" and l2["2026Q1"].endswith("a + 1, upp")
    assert "2026Q2" not in l2  # L2's main origin carries no mark
    assert l2["2023Q2"] == "Super Micro–Gemini Open Cloud Computing (2,5 MUSD) a, upp"
    l3 = L.acquisition_quarters("L3", "2026-11-27")
    assert l3["2025Q2"].endswith("(183 MUSD) a, upp") and l3["2026Q3"].endswith("(183 MUSD) a + 5, ned")
    # from the filing day of the first document only
    assert not any("Moogsoft" in v for v in L.acquisition_quarters("L2", "2023-12-07").values())
    assert any("Moogsoft" in v for v in L.acquisition_quarters("L2", "2023-12-08").values())
    assert not any("ej namngivet" in v for v in L.acquisition_quarters("L2", "2026-03-15").values())
    assert L.acquisition_quarters("L3", "2025-07-29") == {}


# ------------------------------------------------------------------ property: L2 recomputed without the project

def _levels(t: pd.DataFrame, series: str) -> dict[str, float]:
    d = t[t["series"] == series].sort_values(["period", "known_from", "fetched_at"]).drop_duplicates("period", keep="last")
    return {str(p): float(v) for p, v in zip(d["period"], d["value"])}


def _q(q: str, j: int) -> str:
    return str(pd.Period(q, freq="Q") + j)


def _change(level: dict[str, float]) -> dict[str, float]:
    y = {q: 100 * math.log(v) for q, v in level.items() if v > 0}
    pace = {q: y[q] - y[_q(q, -4)] for q in y if _q(q, -4) in y}
    return {q: pace[q] - pace[_q(q, -2)] for q in pace if _q(q, -2) in pace}


@pytest.fixture(scope="module")
def real():
    from ai_tracker import observations

    t = observations.load()
    if t.empty or "rpo_dell" not in set(t["series"]):
        pytest.skip("no real observation table")
    return t[t["known_from"] <= pd.Timestamp("2026-11-27")]


@pytest.mark.real_data
def test_l2_per_2026_11_27_recomputed_without_the_project(real):
    rpo = {c: _levels(real, f"rpo_{c}") for c in ("csco", "dell", "smci")}
    l2 = {q: sum(rpo[c][q] for c in rpo) for q in set.intersection(*[set(v) for v in rpo.values()])}
    cap = {c: _levels(real, f"capex_{c}") for c in ("msft", "googl", "amzn", "meta")}
    inner = {q: sum(cap[c][_q(q, -j)] for c in cap for j in range(4))
             for q in set.intersection(*[set(v) for v in cap.values()])
             if all(_q(q, -j) in cap[c] for c in cap for j in range(4))}
    x, y = _change(l2), _change(inner)
    assert round(x["2026Q2"], 1) == 25.9 and round(y["2026Q3"], 1) == 9.6  # före: talar för at origin 2026Q2
    assert round(x["2026Q1"], 1) == 24.4 and round(x["2025Q4"], 1) == 35.7
    assert round(y["2025Q2"], 1) == 5.9 and round(x["2025Q3"], 1) == 4.7  # efter k = 4: decided at 2025Q4
    assert abs(y["2026Q1"]) < 5 and abs(y["2025Q4"]) < 5  # efter k = 2: no impulse in the window
    # DA1's bound: the acquired RPO that would bring the change in pace at 2025Q4 under 10
    lo, hi = 0.0, l2["2025Q4"]
    for _ in range(60):
        a = (lo + hi) / 2
        c = _change({q: v - a if pd.Period(q, freq="Q") >= pd.Period("2025Q4", freq="Q") else v
                     for q, v in l2.items()})["2025Q4"]
        lo, hi = (a, hi) if c > 10 else (lo, a)
    assert round(a / 1000, 1) == 28.7


# ------------------------------------------------------------------ findings (strict xfails)


@pytest.mark.real_data
@pytest.mark.xfail(strict=True, reason="R30-1: the report does not say through which quarter each company's filings are "
                                       "coded, so a quarter filed after the coding reads like a quarter without "
                                       "acquisitions (Dell 2026Q3 about 2026-12-09)")
def test_r30_1_lt1_report_states_through_which_quarter_the_acquisitions_are_coded(real):
    from ai_tracker import observations

    text = L.render(L.compute("2026-11-27", observations.load()))
    caveats = text.split("- Förvärv ger nivåskiften.", 1)[1].split("\n## ", 1)[0]
    assert re.search(r"Dell[^.]*till och med 2026Q2", caveats) and re.search(r"Equinix[^.]*till och med 2026Q3", caveats)


@pytest.mark.xfail(strict=True, reason="R30-2: Dell's fiscal quarter ends on the Friday nearest the month end, so the "
                                       "first days of May, August, November and February map to the next quarter")
def test_r30_2_dell_quarter_of_follows_the_fiscal_calendar_at_its_boundaries():
    assert ACQ.quarter_of("2023-11-01", "dell") == "2023Q3"  # fiscal Q3 FY2024 ended 2023-11-03 (10-Q)
    assert ACQ.quarter_of("2023-05-03", "dell") == "2023Q1"  # fiscal Q1 FY2024 ended 2023-05-05
    assert ACQ.quarter_of("2024-02-01", "dell") == "2023Q4"  # fiscal year 2024 ended 2024-02-02


@pytest.mark.xfail(strict=True, reason="R30-2: load() rejects a Dell row whose quarter is the filing's fiscal quarter "
                                       "when the closing day is a few days after the calendar month end")
def test_r30_2_load_accepts_a_dell_closing_in_the_last_days_of_a_fiscal_quarter(tmp_path, df):
    row = df[df["id"] == "dell-2023Q3-moog-01"].iloc[0].to_dict()
    row.update(id="dell-2023Q3-r30-01", event="dell-2023Q3-r30", closed="2023-11-01", quarter="2023Q3")
    p = tmp_path / "acq.csv"
    pd.DataFrame([row])[ACQ.COLUMNS].to_csv(p, index=False)
    assert ACQ.load(p)["quarter"].tolist() == ["2023Q3"]


@pytest.mark.xfail(strict=True, reason="R30-3: the 10-K's goodwill table has 2025 additions of 11 MUSD in EMEA beside "
                                       "TIM's 127 in Asia-Pacific; the description still calls the gap a possible "
                                       "later payment for TIM")
def test_r30_3_equinix_2025q4_description_follows_the_goodwill_table(df):
    note = df.set_index("id").loc["eqix-2025Q4-01", "note"]
    doc = SOURCE_DOC.read_text(encoding="utf-8")
    assert "later payment" not in note
    assert "en senare betalning för TIM" not in doc
