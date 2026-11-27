"""DA1: Dell's, Super Micro's and Equinix's acquisitions in LT1's acquisition mark for L2 and L3 (register 2026-11-27 DA1).

- the coded companies are exactly the members of L2 and L3 whose acquisitions are not documented by name (Dell, Super
  Micro, Equinix); HPE and Arista are not members and are not coded
- every quarter 2023Q1 to the latest filed one is coded per company, as acquisitions or none
- Dell's quarter a is the series' quarter of the fiscal quarter (register DA1, point 3)
- marks follow known_from, carry the latest consideration known on the day, and only reach L2 and L3
- a mark never changes an outcome
- the report says which companies are coded and which are not
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker.followed import ledtid as L
from ai_tracker.series import ledtid as LS
from ai_tracker.sources import acquisitions as A

NEW = ("dell", "smci", "eqix")


@pytest.fixture(scope="module")
def df():
    return A.load()


def test_coded_companies_are_the_members_of_l2_and_l3():
    assert L.ACQ_COMPANIES["L2"] == ("dell", "smci") and L.ACQ_COMPANIES["L3"] == ("eqix",)
    # Cisco is in L2 with its documented Splunk only; HPE and Arista are context, not members (register DA1, point 1)
    assert set(L.ACQ_COMPANIES["L2"]) | {"csco"} == set(LS.NET) and L.MEMBERS["L3"] == ("eqix",)
    assert "hpe" not in A.COMPANIES and "anet" not in A.COMPANIES
    assert {"rpo_hpe", "rpo_anet"} <= set(L.CONTEXT["members"][1])


@pytest.mark.parametrize("company,last", [("dell", "2026Q2"), ("smci", "2026Q3"), ("eqix", "2026Q3")])
def test_every_quarter_from_2023_is_coded(df, company, last):
    d = df[df["company"] == company]
    qs = {str(q) for q in pd.period_range("2023Q1", last, freq="Q")}
    assert set(d["quarter"]) == qs  # nothing before 2023Q1 (register DA1, point 2), nothing not yet filed
    marked = set(d.loc[d["row_type"].isin(A.MARK_TYPES), "quarter"])
    none = set(d.loc[d["row_type"] == "none", "quarter"])
    assert marked.isdisjoint(none) and marked | none == qs
    expected = {"dell": {"2023Q3", "2025Q4"}, "smci": {"2023Q2"}, "eqix": {"2025Q2", "2025Q4"}}[company]
    assert marked == expected


def test_dell_quarter_a_is_the_fiscal_quarter():
    # Dell's fiscal year ends around January 31: February to April is quarter 1 in rpo_dell (S1)
    assert A.quarter_of("2026-04-15", "dell") == "2026Q1"
    assert A.quarter_of("2026-02-15", "dell") == "2026Q1"
    assert A.quarter_of("2023-10-20", "dell") == "2023Q3"
    assert A.quarter_of("2026-01-15", "dell") == "2025Q4"
    assert A.quarter_of("2026-04-15", "smci") == "2026Q2" == A.quarter_of("2026-04-15", "eqix")


def test_load_rejects_a_quarter_before_2023(tmp_path, df):
    bad = df.drop(columns="known_from").astype(object).where(df.drop(columns="known_from").notna(), "")
    bad = bad.astype(str).replace({"nan": ""})
    i = bad.index[bad["id"] == "dell-2023Q1-01"][0]
    bad.loc[i, "quarter"] = "2022Q4"
    p = tmp_path / "a.csv"
    bad.to_csv(p, index=False)
    with pytest.raises(A.CsvError, match="before 2023Q1"):
        A.load(p)


def test_marks_follow_known_from_and_the_consideration(df):
    assert A.marks("dell", "2026-03-15", df) == [("Dell–Moogsoft", "2023Q3", "2023-12-08")]
    assert ("Dell, ej namngivet förvärv 2025Q4", "2025Q4", "2026-03-16") in A.marks("dell", "2026-03-16", df)
    assert A.marks("smci", "2023-08-27", df) == []
    assert A.marks("smci", None, df) == [("Super Micro–Gemini Open Cloud Computing (2,5 MUSD)", "2023Q2", "2023-08-28")]
    assert A.marks("eqix", "2025-07-29", df) == []
    tim = [m for m in A.marks("eqix", "2025-07-30", df) if "TIM" in m[0]]
    assert tim == [("Equinix–TIM NextGen DC, tre datacenter i Filippinerna (183 MUSD)", "2025Q2", "2025-07-30")]


def test_l2_and_l3_marks_with_direction():
    l2 = L.acquisition_quarters("L2")
    assert l2["2025Q4"] == "Dell, ej namngivet förvärv 2025Q4 a, upp"
    assert l2["2026Q1"] == "Dell, ej namngivet förvärv 2025Q4 a + 1, upp"
    assert l2["2024Q3"] == ("Dell–Moogsoft a + 4, ned; Super Micro–Gemini Open Cloud Computing (2,5 MUSD) a + 5, ned")
    assert "2026Q2" not in l2  # L2's main origin per 2026-11-27 has no mark
    l3 = L.acquisition_quarters("L3")
    assert l3["2026Q2"] == "Equinix–TIM NextGen DC, tre datacenter i Filippinerna (183 MUSD) a + 4, ned"
    assert l3["2026Q4"] == "Equinix, ej namngivet förvärv 2025Q4 a + 4, ned"
    old = L.acquisition_quarters("L2", "2025-11-27")
    assert "2025Q4" not in old  # the 10-K for Dell's fiscal 2026 was filed 2026-03-16


def _ms(row_key: str, xs: dict[str, float], ys: dict[str, float]) -> dict[str, dict]:
    def m(key, ch):
        return {"series": key, "available": True, "period": max(ch), "known_from": "2026-11-03",
                "path": {q: {"level": 1.0, "pace": 0.0, "change": v} for q, v in ch.items()}}
    return {row_key: m(row_key, xs), "kl_capex4_inner": m("kl_capex4_inner", ys)}


@pytest.mark.parametrize("row,direction", [("L2", "fore"), ("L2", "efter"), ("L3", "fore"), ("L3", "efter")])
def test_a_mark_never_changes_an_outcome(monkeypatch, row, direction):
    qs = [str(q) for q in pd.period_range("2024Q1", "2026Q3", freq="Q")]
    sup = {q: 0.0 for q in qs} | {"2025Q4": 35.7, "2026Q2": 12.0}
    buy = {q: 0.0 for q in qs} | {"2025Q2": 6.0, "2026Q1": 9.6}
    ms = _ms(L.SUPPLIERS[row][0], sup, buy)
    keys = ("outcome", "origin", "t", "decided_at")
    with_marks = L.reading(row, "inner", direction, 4, ms)
    assert any(o.get("acquisition") for o in with_marks["history_rows"] + with_marks["origins"])  # a mark is there
    monkeypatch.setattr(L, "ACQ_COMPANIES", {})
    monkeypatch.setattr(L, "ACQUISITIONS", {})
    without = L.reading(row, "inner", direction, 4, ms)
    assert {k: with_marks.get(k) for k in keys} == {k: without.get(k) for k in keys}
    assert [o["outcome"] for o in with_marks["history_rows"]] == [o["outcome"] for o in without["history_rows"]]


def test_report_text_names_what_is_coded_and_what_is_not():
    t = L.UNCHECKED_ACQ
    assert "Dells, Super Micros och Equinix förvärv (L2 och L3) är kodade" in t
    assert "Ciscos förvärv utom Splunk är inte kontrollerade" in t
    assert "HPE:s och Aristas förvärv är inte kodade" in t
    assert "Förvärv hos Dell, Super Micro och Equinix är inte" not in t
    lines = L._acquisition_lines({"acquisitions": {c: A.marks(c, "2026-11-27") for c in ("pwr", *NEW)}})
    assert [x.split(" förvärv per kvartal")[0] for x in lines] == ["- Quantas", "- Dells", "- Super Micros", "- Equinix"]
    assert "2025Q2: TIM NextGen DC, tre datacenter i Filippinerna (183 MUSD), känt från 2025-07-30" in lines[3]
