"""Network, optics and servers (S1): fiscal-calendar mapping, segment breaks, product x segment members, balances.

Synthetic companyfacts and instance fixtures, no network. Values in USD millions (x 1e6 in XBRL facts).
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import catalog, licenses, observations, warehouse
from ai_tracker.series import sec_stack_nat as s
from ai_tracker.series.sec_segments import PROD, SEG, DefinitionBreakError
from ai_tracker.sources import sec, sec_instant, sec_segment as ss

M = 1e6
T = pd.Timestamp


def latest(df):
    return df.sort_values("known_from").groupby("period")["value"].last().to_dict()


def first_known(df):
    return {p: str(d.date()) for p, d in df.groupby("period")["known_from"].min().items()}


def duration(start, end, val, filed, form="10-Q", accn=None):
    return {"start": start, "end": end, "val": val * M, "filed": filed, "form": form, "accn": accn or f"acc-{filed}"}


def instant(end, val, filed, form="10-Q", accn=None):
    return {"end": end, "val": val * M, "filed": filed, "form": form, "accn": accn or f"acc-{filed}"}


def companyfacts(**tags) -> dict:
    return {"facts": {"us-gaap": {t: {"units": {"USD": rows}} for t, rows in tags.items()}}}


@pytest.fixture
def company(monkeypatch):
    """A test company 'tst' (HPE-style fiscal year to 31 October) whose companyfacts the test sets."""
    holder = {}
    monkeypatch.setitem(s.COMPANIES, "tst", s.Company("Test", 1, tuple(s.REVENUE), "2020-01-01", 25, 83 + 92 + 30,
                                                      "test"))
    monkeypatch.setattr(sec, "companyfacts", lambda cik: holder["cf"])
    for f in (s.revenue_series, s.quarters, s.inventory_series, s.balance_series):
        f.cache_clear()
    yield holder
    for f in (s.revenue_series, s.quarters, s.inventory_series, s.balance_series):
        f.cache_clear()


# HPE-style fiscal year ending 31 October: Nov-Jan, Feb-Apr, May-Jul, Aug-Oct.
FY26 = [
    duration("2025-11-01", "2026-01-31", 100, "2026-03-10"),
    duration("2026-02-01", "2026-04-30", 110, "2026-06-02"),
    duration("2025-11-01", "2026-04-30", 210, "2026-06-02"),
    duration("2026-05-01", "2026-07-31", 120, "2026-09-03"),
    duration("2025-11-01", "2026-07-31", 330, "2026-09-03"),
    duration("2025-11-01", "2026-10-31", 470, "2026-12-15", "10-K"),
    duration("2026-08-01", "2026-10-31", 999, "2026-12-15", "10-K"),  # 10-K quarterly note: ignored
]


# ------------------------------------------------------------------ fiscal calendar


def test_october_fiscal_year_maps_by_midpoint_and_q4_is_fy_minus_9m(company):
    company["cf"] = companyfacts(Revenues=FY26)
    df = s.revenue_series("tst")
    # Nov-Jan = calendar Q4 of the previous year, Aug-Oct = Q3 (midpoint rule); Aug-Oct = FY - 9M = 470 - 330
    assert latest(df) == {"2025Q4": 100, "2026Q1": 110, "2026Q2": 120, "2026Q3": 140}
    assert first_known(df)["2026Q3"] == "2026-12-15"


def test_balances_take_the_fiscal_quarter_label_and_pass_the_leakage_check(company):
    company["cf"] = companyfacts(
        Revenues=FY26,
        InventoryNet=[instant("2026-01-31", 50, "2026-03-10"), instant("2026-04-30", 55, "2026-06-02"),
                      instant("2026-01-31", 50, "2026-06-02"),  # comparative repeat: no new row
                      instant("2026-03-15", 1, "2026-06-02")],  # not a fiscal quarter end: dropped
        RevenueRemainingPerformanceObligation=[instant("2026-01-31", 400, "2026-03-10"),
                                               instant("2026-04-30", 420, "2026-06-02")])
    inv = s.inventory_series("tst")
    # the 31 January balance belongs to the Nov-Jan fiscal quarter = 2025Q4, like the flows (not 2026Q1)
    assert latest(inv) == {"2025Q4": 50, "2026Q1": 55}
    assert len(inv) == 2
    s.BALANCE_BY_KEY["rpo_tst"] = s.BalanceSeries("rpo_tst", "tst", "rpo", "test")
    try:
        rpo = s.balance_series("rpo_tst")
    finally:
        del s.BALANCE_BY_KEY["rpo_tst"]
    assert latest(rpo) == {"2025Q4": 400, "2026Q1": 420}
    spec = next(x for x in s.SPECS if x.key == "rev_hpe")
    rows = s.revenue_series("tst")[["period", "value", "known_from"]]
    spec = catalog.Spec(**{**spec.__dict__, "fetch": lambda: None})
    table = observations.new_rows(spec, rows, observations._empty())
    checks = warehouse.run_checks(warehouse.connect(table, [spec]))
    assert all(v.empty for v in checks.values()), {k: v for k, v in checks.items() if len(v)}


# ------------------------------------------------------------------ scope breaks in total revenue


def test_revenue_scope_break_reads_only_the_current_scope(company, monkeypatch):
    old = [duration("2016-11-01", "2017-01-31", 300, "2017-03-01"), duration("2017-02-01", "2017-04-30", 310, "2017-06-01"),
           duration("2016-11-01", "2017-04-30", 610, "2017-06-01")]
    # a spin-off: the next year's 10-Q restates the comparatives (-30%) on the continuing scope
    new = [duration("2017-11-01", "2018-01-31", 220, "2018-03-01"), duration("2016-11-01", "2017-01-31", 210, "2018-03-01"),
           duration("2018-02-01", "2018-04-30", 230, "2018-06-01"), duration("2017-02-01", "2017-04-30", 217, "2018-06-01"),
           duration("2017-11-01", "2018-04-30", 450, "2018-06-01"), duration("2016-11-01", "2017-04-30", 427, "2018-06-01")]
    company["cf"] = companyfacts(Revenues=old + new)
    with pytest.raises(DefinitionBreakError):
        s.revenue_series("tst")  # undeclared
    s.revenue_series.cache_clear()
    monkeypatch.setitem(s.COMPANIES, "tst", s.Company("Test", 1, tuple(s.REVENUE), "2020-01-01", 25, 205, "test",
                                                      rev_scope_breaks=("2018-03-01",)))
    allv = sec.vintages(s.revenue_scope_sources("tst"))
    # only the continuing scope: 2016Q4 and 2017Q1 have no version at the old level, and are known from the restating
    # filings
    assert sorted(map(tuple, allv[["period", "value"]].values.tolist())) == [
        ("2016Q4", 210), ("2017Q1", 217), ("2017Q4", 220), ("2018Q1", 230)]
    assert first_known(allv) == {"2016Q4": "2018-03-01", "2017Q1": "2018-06-01", "2017Q4": "2018-03-01",
                                 "2018Q1": "2018-06-01"}
    # the published series starts after the gap (2017Q2-Q3 are not reported on the new scope)
    assert latest(s.revenue_series("tst")) == {"2017Q4": 220, "2018Q1": 230}


def test_revenue_correction_is_declared_and_stays_a_version(company, monkeypatch):
    rows = [duration("2025-11-01", "2026-01-31", 100, "2026-03-10"),
            duration("2025-11-01", "2026-01-31", 105, "2026-06-02", "10-Q/A")]  # +5%: a correction
    company["cf"] = companyfacts(Revenues=rows)
    monkeypatch.setitem(s.COMPANIES, "tst", s.Company("Test", 1, tuple(s.REVENUE), "2020-01-01", 25, 205, "test",
                                                      rev_revisions=("2026-06-02",)))
    df = s.revenue_series("tst")
    assert df[["period", "value"]].values.tolist() == [["2025Q4", 100], ["2025Q4", 105]]


# ------------------------------------------------------------------ segment lines


def dimfact(dims, start, end, val, concept="Revenues"):
    return ss.DimFact(concept, T(start), T(end), frozenset(dims), val * M, "USD")


ISG = (SEG, "InfrastructureSolutionsGroupMember")
AI = (PROD, "AIOptimizedServersAndNetworkingMember")


def test_exact_facts_product_by_segment():
    f = ss.Filing(1, "acc-1", "2026-06-09", "10-Q")
    dfs = [dimfact([AI, ISG], "2026-01-31", "2026-05-01", 16_000),
           dimfact([ISG], "2026-01-31", "2026-05-01", 22_000),  # the segment alone: not the product line
           dimfact([AI, ISG, ("StatementGeographicalAxis", "US")], "2026-01-31", "2026-05-01", 9_000),  # extra dim
           dimfact([AI, ISG, ("ConsolidationItemsAxis", "OperatingSegmentsMember")], "2025-01-31", "2025-05-02", 1_000)]
    got = s.exact_facts(dfs, f, list(s.REVENUE), s.dims(AI, ISG))
    assert [(str(x.end.date()), x.val / M) for x in got] == [("2025-05-02", 1_000), ("2026-05-01", 16_000)]
    # the one-dimension case gives the same facts as sec_segment.to_facts
    one = s.exact_facts(dfs, f, list(s.REVENUE), s.dims(ISG))
    assert one == ss.to_facts(dfs, f, list(s.REVENUE), *ISG)


def segment_data(recast_first: float, recast_second: float):
    """A server line recast in two filings: +recast_first in the first FY2026 10-Q, +recast_second in the next."""
    m = (SEG, "ServerSegmentMember")
    q = lambda d: ss.Filing(1, f"acc-{d}", d, "10-Q")  # noqa: E731
    return (
        (q("2025-03-07"), (dimfact([m], "2024-11-01", "2025-01-31", 4_000),)),
        (q("2025-06-04"), (dimfact([m], "2025-02-01", "2025-04-30", 4_100),
                           dimfact([m], "2024-11-01", "2025-04-30", 8_100))),
        (q("2026-03-10"), (dimfact([m], "2025-11-01", "2026-01-31", 6_000),
                           dimfact([m], "2024-11-01", "2025-01-31", 4_000 * (1 + recast_first)))),
        (q("2026-06-02"), (dimfact([m], "2026-02-01", "2026-04-30", 6_500),
                           dimfact([m], "2025-11-01", "2026-04-30", 12_500),
                           dimfact([m], "2025-02-01", "2025-04-30", 4_100 * (1 + recast_second)),
                           dimfact([m], "2024-11-01", "2025-04-30", 4_000 * (1 + recast_first) + 4_100 * (1 + recast_second)))),
    )


def test_segment_break_splits_into_regimes_and_is_never_spliced(monkeypatch):
    monkeypatch.setattr(ss, "company_facts", lambda cik, since, concepts: segment_data(0.10, 0.10))
    monkeypatch.setitem(s.COMPANIES, "tst", s.Company("Test", 1, tuple(s.REVENUE), "2020-01-01", 25, 205, "test"))
    members = (s.dims((SEG, "ServerSegmentMember")),)
    with pytest.raises(DefinitionBreakError):
        s.line_series(s.SegLine(("brk_a",), "tst", members, "x"))  # undeclared
    old, new = s.line_series(s.SegLine(("brk_old", "brk_new"), "tst", members, "x", breaks=("2026-03-10",)))
    assert latest(old) == {"2024Q4": 4_000, "2025Q1": 4_100}  # never rewritten with the new definition
    # the new regime has the recast comparatives; 2025Q2-Q3 are missing, so the series starts at 2025Q4
    assert latest(new) == {"2025Q4": 6_000, "2026Q1": 6_500}
    assert new["known_from"].min() >= pd.Timestamp("2026-03-10")


def test_segment_split_at_the_realignment_when_detection_comes_later(monkeypatch):
    # HPE pattern: +1.8% in the first filing of the new structure (below 2%), +2.5% in the next
    monkeypatch.setattr(ss, "company_facts", lambda cik, since, concepts: segment_data(0.018, 0.025))
    monkeypatch.setitem(s.COMPANIES, "tst", s.Company("Test", 1, tuple(s.REVENUE), "2020-01-01", 25, 205, "test"))
    members = (s.dims((SEG, "ServerSegmentMember")),)
    with pytest.raises(DefinitionBreakError):  # declared at the realignment, but detection finds the later filing
        s.line_series(s.SegLine(("hpe_a", "hpe_b"), "tst", members, "x", breaks=("2026-03-10",)))
    old, new = s.line_series(s.SegLine(("hpe_old", "hpe_new"), "tst", members, "x", breaks=("2026-03-10",),
                                       detected=("2026-06-02",)))
    assert latest(old) == {"2024Q4": 4_000, "2025Q1": 4_100}  # the +1.8% recast is not a version of the old line
    assert pd.Timestamp("2026-03-10") <= new["known_from"].min()


def test_catalog_lines_declare_their_regimes():
    for line in s.LINES:
        assert len(line.keys) == len(line.breaks) + 1
        assert not line.regime_notes or len(line.regime_notes) == len(line.keys)
        assert line.detected is None or len(line.detected) == len(line.breaks)


# ------------------------------------------------------------------ purchase obligations and other balances


def test_purchase_obligations_as_instants_from_companyfacts(company, monkeypatch):
    company["cf"] = companyfacts(
        Revenues=FY26,
        PurchaseObligation=[instant("2026-01-31", 1_000, "2026-03-10"), instant("2026-04-30", 1_400, "2026-06-02"),
                            instant("2026-04-30", 1_450, "2026-09-03", "10-Q/A"),  # restated: a version (+3.6%)
                            instant("2026-07-31", 2_000, "2026-09-03")])
    s.BALANCE_BY_KEY["purchase_oblig_tst"] = s.BalanceSeries("purchase_oblig_tst", "tst", "purchase_oblig", "test",
                                                             breaks=("2026-09-03",))
    monkeypatch.setattr(s, "balance_sources", lambda key: [sec_instant.facts(company["cf"], "PurchaseObligation")])
    try:
        df = s.balance_series("purchase_oblig_tst")
        s.balance_series.cache_clear()
        s.BALANCE_BY_KEY["purchase_oblig_tst"] = s.BalanceSeries("purchase_oblig_tst", "tst", "purchase_oblig", "t")
        with pytest.raises(DefinitionBreakError):  # an undeclared restatement > 2% stops the fetch
            s.balance_series("purchase_oblig_tst")
    finally:
        del s.BALANCE_BY_KEY["purchase_oblig_tst"]
    assert latest(df) == {"2025Q4": 1_000, "2026Q1": 1_450, "2026Q2": 2_000}
    assert first_known(df) == {"2025Q4": "2026-03-10", "2026Q1": "2026-06-02", "2026Q2": "2026-09-03"}


def instance(contexts, facts) -> bytes:
    body = "".join(contexts) + '<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>'
    for concept, cid, val in facts:
        body += f'<{concept} contextRef="{cid}" unitRef="usd" decimals="-6">{val}</{concept}>'
    return ('<?xml version="1.0"?><xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" '
            'xmlns:xbrldi="http://xbrl.org/2006/xbrldi" xmlns:us-gaap="http://fasb.org/us-gaap/2025" '
            'xmlns:anet="http://www.arista.com/20250331" xmlns:iso4217="http://www.xbrl.org/2003/iso4217">'
            + body + "</xbrli:xbrl>").encode()


def context(cid, end, dims=()):
    members = "".join(f'<xbrldi:explicitMember dimension="{a}">{m}</xbrldi:explicitMember>' for a, m in dims)
    segment = f"<xbrli:segment>{members}</xbrli:segment>" if dims else ""
    return (f'<xbrli:context id="{cid}"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">1'
            f"</xbrli:identifier>{segment}</xbrli:entity><xbrli:period><xbrli:instant>{end}</xbrli:instant>"
            "</xbrli:period></xbrli:context>")


def test_cisco_style_dimensional_commitments_win_over_the_plain_tag():
    inv = ("us-gaap:" + s.UUPO_AXIS, "us-gaap:InventoriesMember")
    old = ss.Filing(1, "acc-o", "2021-05-25", "10-Q")
    new = ss.Filing(1, "acc-n", "2021-11-23", "10-Q")
    doc_old = instance([context("i", "2021-04-24")], [("us-gaap:" + s.UUPO, "i", 6_000 * M)])
    doc_new = instance([context("i", "2021-10-30"), context("i_inv", "2021-10-30", [inv])],
                       [("us-gaap:" + s.UUPO, "i_inv", 7_000 * M), ("us-gaap:" + s.UUPO, "i", 7_900 * M)])
    raw = [(old, doc_old), (new, doc_new)]
    sources = [sec_instant.instance_instants(raw, s.UUPO, s.dims((s.UUPO_AXIS, "InventoriesMember"))),
               sec_instant.instance_instants(raw, s.UUPO)]
    quarters = {T("2021-04-24"): pd.Period("2021Q1", "Q-DEC"), T("2021-10-30"): pd.Period("2021Q3", "Q-DEC")}
    assert latest(sec_instant.vintages(sources, quarters)) == {"2021Q1": 6_000, "2021Q3": 7_000}


def test_arista_rpo_redated_in_the_listed_filings():
    tagged = [sec_instant.Instant(T("2024-03-31"), 2_600 * M, T("2024-05-08"), "10-Q", "a"),
              sec_instant.Instant(T("2024-03-31"), 3_700 * M, T("2025-05-07"), "10-Q", "b"),  # really 2025-03-31
              sec_instant.Instant(T("2025-12-31"), 6_100 * M, T("2026-02-17"), "10-K", "c")]
    got = s.redated(tagged, s.ANET_RPO_REDATED)
    assert [(str(f.end.date()), f.val / M) for f in got] == [
        ("2024-03-31", 2_600), ("2025-03-31", 3_700), ("2025-12-31", 6_100)]
    assert ss.definition_breaks(s.as_facts(got)) == []  # without the fix it looked like a 42% restatement
    assert ss.definition_breaks(s.as_facts(tagged)) == [T("2025-05-07")]


def test_arista_contract_liabilities_sum_parts_of_one_filing():
    cf = companyfacts(
        ContractWithCustomerLiabilityCurrent=[instant("2018-09-30", 500, "2018-11-05"),
                                              instant("2018-12-31", 520, "2019-02-15", "10-K")],
        ContractWithCustomerLiabilityNoncurrent=[instant("2018-12-31", 210, "2019-02-15", "10-K")],
        DeferredRevenueCurrent=[instant("2016-12-31", 300, "2017-02-17", "10-K"),  # ASC 605: not used
                                instant("2018-09-30", 499, "2018-11-05")],
        DeferredRevenueNoncurrent=[instant("2016-12-31", 100, "2017-02-17", "10-K"),
                                   instant("2018-09-30", 200, "2018-11-05")])
    got = s.anet_contract_liabilities(cf)
    # 2018-09-30: current from the new tag, noncurrent from the old tag of the same filing; 2016 is before ASC 606
    assert [(str(f.end.date()), f.val / M) for f in got] == [("2018-09-30", 700), ("2018-12-31", 730)]


def test_from_filed_and_first_per_filing():
    a = sec_instant.Instant(T("2015-09-30"), 4.5 * M, T("2015-11-06"), "10-Q", "x")
    b = sec_instant.Instant(T("2016-12-31"), 400 * M, T("2017-02-17"), "10-K", "y")
    assert s.from_filed([a, b], s.ANET_PO_SINCE) == [b]
    b2 = sec_instant.Instant(T("2016-12-31"), 1 * M, T("2017-02-17"), "10-K", "y")
    assert s.first_per_filing([[b], [b2, a]]) == [a, b]


# ------------------------------------------------------------------ catalog


def test_catalog_entries():
    keys = {x.key for x in s.SPECS}
    assert {"rev_anet", "inv_anet", "purchase_oblig_anet", "deferred_rev_anet", "rpo_anet", "rev_csco",
            "rev_csco_networking", "purchase_oblig_csco", "rpo_csco", "rev_cohr", "rev_cohr_datacom", "rev_lite",
            "rev_lite_cloud_networking", "purchase_oblig_lite", "rev_smci", "purchase_oblig_smci", "rpo_smci",
            "rev_dell", "rev_dell_isg", "rev_dell_ai_servers", "rpo_dell", "rev_hpe", "rev_hpe_server_fy26",
            "rev_hpe_dc_networking", "rpo_hpe", "rev_cls", "rev_cls_ccs"} <= keys
    assert catalog.validate(s.SPECS) == []
    assert catalog.validate() == []  # no key clashes with the rest of the catalog (capex_mu stays in halvledare)
    assert all(x.freq == "Q" and x.branch == "G6" and x.unit == "MUSD" and x.publish and x.revised for x in s.SPECS)
    assert {licenses.verdict(x).klass for x in s.SPECS} == {licenses.JA}
    assert {x.key for x in s.SPECS if x.closed} == {
        "rev_csco_infra_platforms", "rev_cohr_networking", "rev_lite_opcomms", "rev_lite_cloud_networking",
        "rev_dell_servers_networking", "rev_hpe_server_fy24"}
    assert all(x.max_age_days is None for x in s.SPECS if x.closed)
    assert all(x.max_age_days and "Aktualitet" in x.note for x in s.SPECS if not x.closed)
