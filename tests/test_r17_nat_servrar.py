"""Review R17 of track S1 (network, optics and servers): properties that hold, and strict xfails for the defects.

Synthetic companyfacts and instance fixtures modelled on the filings named in docs/granskning/r17-nat-servrar.md, no
network. Values in USD millions (x 1e6 in XBRL facts).
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import licenses
from ai_tracker.series import sec_stack_nat as s
from ai_tracker.series.sec_segments import SEG
from ai_tracker.sources import sec, sec_segment as ss

M = 1e6
T = pd.Timestamp


def duration(start, end, val, filed, form="10-Q"):
    return {"start": start, "end": end, "val": val * M, "filed": filed, "form": form, "accn": f"acc-{filed}"}


def instant(end, val, filed, form="10-Q"):
    return {"end": end, "val": val * M, "filed": filed, "form": form, "accn": f"acc-{filed}"}


def companyfacts(**tags) -> dict:
    return {"facts": {"us-gaap": {t: {"units": {"USD": rows}} for t, rows in tags.items()}}}


def versions(df, period):
    return [round(v, 3) for v in df[df["period"] == period].sort_values("known_from")["value"]]


@pytest.fixture
def company(monkeypatch):
    """A test company 'tst' whose companyfacts the test sets (Cisco-style fiscal year, last Saturday of July)."""
    holder = {}
    monkeypatch.setitem(s.COMPANIES, "tst", s.Company("Test", 1, tuple(s.REVENUE), "2020-01-01", 25, 193, "test"))
    monkeypatch.setattr(sec, "companyfacts", lambda cik: holder["cf"])
    for f in (s.revenue_series, s.quarters, s.inventory_series, s.balance_series):
        f.cache_clear()
    yield holder
    for f in (s.revenue_series, s.quarters, s.inventory_series, s.balance_series):
        f.cache_clear()


# ------------------------------------------------------------------ properties that hold (passing)


@pytest.mark.parametrize("start,end,quarter", [
    ("2026-07-26", "2026-10-24", "2026Q3"),  # Cisco Q1 FY2027 (Aug-Oct)
    ("2025-10-26", "2026-01-24", "2025Q4"),  # Cisco Q2 FY2026 (Nov-Jan)
    ("2026-01-25", "2026-04-25", "2026Q1"),  # Cisco Q3 FY2026 (Feb-Apr)
    ("2021-01-24", "2021-05-01", "2021Q1"),  # Cisco Q3 FY2021, a 14-week quarter ending in May
    ("2026-05-02", "2026-07-31", "2026Q2"),  # Dell Q2 FY2027 (May-Jul)
    ("2025-11-01", "2026-01-30", "2025Q4"),  # Dell Q4 FY2026 (Nov-Jan)
    ("2025-11-01", "2026-01-31", "2025Q4"),  # HPE Q1 FY2026 (Nov-Jan)
    ("2025-08-01", "2025-10-31", "2025Q3"),  # HPE Q4 FY2025 (Aug-Oct)
    ("2026-06-28", "2026-10-03", "2026Q3"),  # Lumentum Q1 FY2027 (14 weeks)
    ("2025-09-28", "2026-01-03", "2025Q4"),  # Lumentum quarter ending in early January
    ("2026-07-01", "2026-09-30", "2026Q3"),  # Coherent and Super Micro (fiscal year to 30 June)
])
def test_midpoint_rule_maps_each_fiscal_calendar(start, end, quarter):
    assert str(sec.calendar_quarter(T(start), T(end))) == quarter


def test_july_fiscal_year_q4_is_fy_minus_9m_and_balances_take_the_fiscal_quarter_label(company):
    # Cisco FY2026 shape (10-Q 2026-05-19 and 10-K 2026-09-02): Q4 = 63,325 - 46,073 = 17,252, mapped to 2026Q2
    rev = [duration("2025-07-27", "2025-10-25", 14_900, "2025-11-18"),
           duration("2025-10-26", "2026-01-24", 15_300, "2026-02-17"),
           duration("2025-07-27", "2026-01-24", 30_200, "2026-02-17"),
           duration("2026-01-25", "2026-04-25", 15_873, "2026-05-19"),
           duration("2025-07-27", "2026-04-25", 46_073, "2026-05-19"),
           duration("2025-07-27", "2026-07-25", 63_325, "2026-09-02", "10-K")]
    company["cf"] = companyfacts(Revenues=rev,
                                 InventoryNet=[instant("2026-01-24", 3_000, "2026-02-17"),
                                               instant("2026-04-25", 3_200, "2026-05-19"),
                                               instant("2026-07-25", 3_400, "2026-09-02", "10-K")])
    df = s.revenue_series("tst")
    assert versions(df, "2026Q2") == [17_252]
    assert df[df["period"] == "2026Q2"]["known_from"].tolist() == [T("2026-09-02")]
    inv = s.inventory_series("tst")
    # a 24 January balance closes the Nov-Jan fiscal quarter, so it is 2025Q4 like the flows of that quarter
    assert versions(inv, "2025Q4") == [3_000] and versions(inv, "2026Q2") == [3_400]
    filed = {T(r["filed"]) for r in rev}
    assert set(df["known_from"]) <= filed and set(inv["known_from"]) <= filed  # known_from = a filing date


def test_scope_breaks_and_revisions_match_the_register():
    c = s.COMPANIES
    assert max(c["dell"].rev_scope_breaks) == "2022-03-24"
    assert max(c["hpe"].rev_scope_breaks) == "2018-06-07"
    assert max(c["cohr"].rev_scope_breaks) == "2014-08-28"
    assert c["smci"].rev_revisions == ("2019-05-17",) and not c["smci"].rev_scope_breaks
    assert all(not c[k].rev_scope_breaks for k in ("anet", "csco", "lite", "cls"))


def test_hpe_server_is_split_at_the_realignment_not_at_the_detection():
    line = next(x for x in s.LINES if x.keys[0] == "rev_hpe_server_fy24")
    assert line.keys == ("rev_hpe_server_fy24", "rev_hpe_server_fy26")
    assert line.breaks == ("2026-03-10",) and line.detected == ("2026-06-02",)


def test_arista_rpo_redating_moves_each_fact_forward_one_year_to_the_filings_own_quarter_end():
    for filed, (tagged, true) in s.ANET_RPO_REDATED.items():
        assert T(true) == T(tagged) + pd.DateOffset(years=1)
        assert T(true) == T(true).to_period("Q").end_time.normalize()
        assert 0 < (T(filed) - T(true)).days < 60


def test_every_s1_series_says_it_is_not_ai_revenue_and_carries_the_sec_licence():
    for x in s.SPECS:
        assert x.license == s.LICENSE and x.publish
        assert licenses.verdict(x).klass == licenses.JA
        assert "inte AI" in x.note or "Dells egen avgränsning" in x.note, x.key


# ------------------------------------------------------------------ confirmed defects (strict xfail)


@pytest.mark.xfail(strict=True, reason="R17-1: deferred_rev_anet takes a different line item as its current part "
                                       "(Arista 10-Q 2018-11-05: 10.9 contract liabilities in other current liabilities)")
def test_r17_1_arista_deferred_revenue_2018q3_is_the_balance_sheet_line():
    # 10-Q 2018-11-05 (0001596532-18-000233): balance sheet "Deferred revenue 318,850" and "Deferred revenue,
    # non-current 211,005" (= "Deferred revenue, ending balance $529,855"); ContractWithCustomerLiabilityCurrent 10.9 is
    # "$10.9 million of our contract liabilities ... included in 'Other current liabilities'"
    cf = companyfacts(ContractWithCustomerLiabilityCurrent=[instant("2018-09-30", 10.9, "2018-11-05")],
                      ContractWithCustomerLiability=[instant("2018-09-30", 25.295, "2018-11-05")],
                      DeferredRevenueCurrent=[instant("2018-09-30", 318.85, "2018-11-05")],
                      DeferredRevenueNoncurrent=[instant("2018-09-30", 211.005, "2018-11-05")])
    got = s.anet_contract_liabilities(cf)
    assert [(str(f.end.date()), round(f.val / M, 3)) for f in got] == [("2018-09-30", 529.855)]


@pytest.mark.xfail(strict=True, reason="R17-3: the 2017-12-31 balance is ASC 605 (modified retrospective adoption), "
                                       "spliced with the ASC 606 balances")
def test_r17_3_arista_contract_liabilities_start_with_the_first_asc606_balance():
    # 10-Q 2018-11-05: ASC 606 adopted 2018-01-01 with the modified retrospective method; $16.5 million of deferred
    # revenue reclassified to other liabilities at 2018-01-01 (beginning balance 498,740 vs 515,262 at 2017-12-31)
    cf = companyfacts(DeferredRevenueCurrent=[instant("2017-12-31", 327.706, "2018-05-04"),
                                              instant("2018-03-31", 274.677, "2018-05-04")],
                      DeferredRevenueNoncurrent=[instant("2017-12-31", 187.556, "2018-05-04"),
                                                 instant("2018-03-31", 181.377, "2018-05-04")])
    got = s.anet_contract_liabilities(cf)
    assert [str(f.end.date()) for f in got] == ["2018-03-31"]


def dell_isg_fy2022():
    """Dell ISG around FY2022, the values of 10-K 2021-03-26, 10-Qs 2021-06-07/09-03/12-03, 10-K 2022-03-24 (new basis:
    FY2021 recast +1.27%), 10-Qs 2022-06-06/09-01/12-05 (FY2022 quarters recast +1.4-1.6%) and 10-K 2023-03-30."""
    isg = ((SEG, "InfrastructureSolutionsGroupMember"),)
    q = lambda d, form="10-Q": ss.Filing(1, f"acc-{d}", d, form)  # noqa: E731
    f = lambda start, end, v: ss.DimFact("Revenues", T(start), T(end), frozenset(isg), v * M, "USD")  # noqa: E731
    fy21, fy22 = ("2020-02-01", "2021-01-29"), ("2021-01-30", "2022-01-28")
    return (
        (q("2021-03-26", "10-K"), (f(*fy21, 32_588),)),
        (q("2021-06-07"), (f("2021-01-30", "2021-04-30", 7_911),)),
        (q("2021-09-03"), (f("2021-05-01", "2021-07-30", 8_432), f("2021-01-30", "2021-07-30", 16_343))),
        (q("2021-12-03"), (f("2021-07-31", "2021-10-29", 8_428), f("2021-01-30", "2021-10-29", 24_771))),
        (q("2022-03-24", "10-K"), (f(*fy22, 34_366), f(*fy21, 33_002))),
        (q("2022-06-06"), (f("2021-01-30", "2021-04-30", 8_033),)),
        (q("2022-09-01"), (f("2021-05-01", "2021-07-30", 8_550), f("2021-01-30", "2021-07-30", 16_583))),
        (q("2022-12-05"), (f("2021-07-31", "2021-10-29", 8_564), f("2021-01-30", "2021-10-29", 25_147))),
        (q("2023-03-30", "10-K"), (f(*fy22, 34_366),)),
    )


def test_dell_fixture_restatements_stay_below_the_break_threshold(monkeypatch):
    monkeypatch.setattr(ss, "company_facts", lambda cik, since, concepts: dell_isg_fy2022())
    monkeypatch.setitem(s.COMPANIES, "tst", s.Company("Test", 1, tuple(s.REVENUE), "2016-06-01", 25, 212, "test"))
    line = s.SegLine(("isg_tst",), "tst", (s.dims((SEG, "InfrastructureSolutionsGroupMember")),), "x")
    s.line_series.cache_clear()
    (df,) = s.line_series(line)
    s.line_series.cache_clear()
    # what the S1 code publishes: the first Q4 FY2022 is 34,366 - 24,771 (old-basis 9M), the second 34,366 - 25,147
    assert versions(df, "2021Q4") == [9_595, 9_219]
    assert versions(df, "2021Q3") == [8_428, 8_564]


@pytest.mark.xfail(strict=True, reason="R17-2: Q4 = FY (new basis, 10-K 2022-03-24) - 9M (old basis, 10-Q 2021-12-03) "
                                       "is published as the first version of rev_dell_isg 2021Q4")
def test_r17_2_q4_is_not_computed_across_a_basis_change(monkeypatch):
    monkeypatch.setattr(ss, "company_facts", lambda cik, since, concepts: dell_isg_fy2022())
    monkeypatch.setitem(s.COMPANIES, "tst", s.Company("Test", 1, tuple(s.REVENUE), "2016-06-01", 25, 212, "test"))
    line = s.SegLine(("isg_tst",), "tst", (s.dims((SEG, "InfrastructureSolutionsGroupMember")),), "x")
    s.line_series.cache_clear()
    try:
        (df,) = s.line_series(line)
    finally:
        s.line_series.cache_clear()
    # the 10-K that supplies FY2022 also recast FY2021 (+1.27%): its FY2022 is on the new basis, the 9M on file is not
    assert set(versions(df, "2021Q4")) == {9_219}


@pytest.mark.xfail(strict=True, reason="R17-4: rev_dell_isg includes the EMC merger (2016-09-07) without saying so")
def test_r17_4_dell_isg_note_names_the_emc_merger():
    spec = next(x for x in s.SPECS if x.key == "rev_dell_isg")
    assert "EMC" in spec.note


@pytest.mark.xfail(strict=True, reason="R17-5: Arista's purchase commitments change wording in 10-K 2018-02-20 (total "
                                       "and the part to contract manufacturers), not documented")
def test_r17_5_arista_purchase_commitments_note_names_the_2018_wording_change():
    spec = next(x for x in s.SPECS if x.key == "purchase_oblig_anet")
    assert "2018-02-20" in spec.note


@pytest.mark.xfail(strict=True, reason="R17-6: HPE's tagged RPO is its deferred revenue by its own text")
def test_r17_6_hpe_rpo_note_says_it_is_deferred_revenue():
    spec = next(x for x in s.SPECS if x.key == "rpo_hpe")
    assert "deferred revenue" in spec.note or "förutbetalda intäkter" in spec.note
