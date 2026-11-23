"""Segment revenue from XBRL instances: extraction, vintage dating, definition-break split.

Synthetic instance documents and facts, no network. Values in USD millions (x 1e6 in the facts).
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import catalog, observations, warehouse
from ai_tracker.series import sec_segments as seg_series
from ai_tracker.sources import sec, sec_segment as ss

M = 1e6
SEG, PROD = "StatementBusinessSegmentsAxis", "ProductOrServiceAxis"
CONCEPTS = list(seg_series.REVENUE)


def context(cid, start, end, dims=()):
    members = "".join(f'<xbrldi:explicitMember dimension="{a}">{m}</xbrldi:explicitMember>' for a, m in dims)
    segment = f"<xbrli:segment>{members}</xbrli:segment>" if dims else ""
    period = (f"<xbrli:startDate>{start}</xbrli:startDate><xbrli:endDate>{end}</xbrli:endDate>" if start
              else f"<xbrli:instant>{end}</xbrli:instant>")
    return (f'<xbrli:context id="{cid}"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">1</xbrli:identifier>'
            f"{segment}</xbrli:entity><xbrli:period>{period}</xbrli:period></xbrli:context>")


def instance(contexts, facts) -> bytes:
    body = "".join(contexts) + (
        '<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>'
        '<xbrli:unit id="shares"><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unit>')
    for concept, cid, val, *unit in facts:
        body += f'<{concept} contextRef="{cid}" unitRef="{unit[0] if unit else "usd"}" decimals="-6">{val}</{concept}>'
    return ('<?xml version="1.0"?><xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" '
            'xmlns:xbrldi="http://xbrl.org/2006/xbrldi" xmlns:us-gaap="http://fasb.org/us-gaap/2024" '
            'xmlns:amzn="http://www.amazon.com/20240930" xmlns:iso4217="http://www.xbrl.org/2003/iso4217">'
            + body + "</xbrli:xbrl>").encode()


AWS = (SEG, "amzn:AmazonWebServicesSegmentMember")
MARKER = ("ConsolidationItemsAxis", "us-gaap:OperatingSegmentsMember")
DOC = instance(
    [context("q", "2026-07-01", "2026-09-30", [AWS]),
     context("ytd", "2026-01-01", "2026-09-30", [AWS, MARKER]),  # older filings add the segment marker
     context("q_prod", "2026-07-01", "2026-09-30", [AWS, (PROD, "us-gaap:ServiceMember")]),  # sub-split
     context("q_na", "2026-07-01", "2026-09-30", [(SEG, "amzn:NorthAmericaSegmentMember")]),
     context("q_tot", "2026-07-01", "2026-09-30"),
     context("inst", None, "2026-09-30", [AWS])],
    [("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "q", 46_000 * M),
     ("us-gaap:Revenues", "q", 99 * M),  # lower-priority concept for the same period: ignored
     ("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "ytd", 125_000 * M),
     ("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "q_prod", 1 * M),
     ("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "q_na", 2 * M),
     ("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "q_tot", 3 * M),
     ("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "inst", 4 * M),
     ("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "q", 5, "shares")])


def filing(filed, form="10-Q"):
    return ss.Filing(1, f"acc-{filed}", filed, form)


def test_parse_instance_reads_dimensions_and_skips_instants():
    facts = ss.parse_instance(DOC)
    assert len(facts) == 7  # the instant fact is not a duration
    q = [f for f in facts if f.dims == frozenset({("StatementBusinessSegmentsAxis", "AmazonWebServicesSegmentMember")})]
    assert {(f.concept, f.value, f.unit) for f in q} == {
        ("RevenueFromContractWithCustomerExcludingAssessedTax", 46_000 * M, "USD"), ("Revenues", 99 * M, "USD"),
        ("RevenueFromContractWithCustomerExcludingAssessedTax", 5.0, "shares")}


def test_segment_extraction_one_member_only():
    got = ss.to_facts(ss.parse_instance(DOC), filing("2026-10-30"), CONCEPTS, SEG, "AmazonWebServicesSegmentMember")
    assert [(str(f.start.date()), str(f.end.date()), f.val / M) for f in got] == [
        ("2026-01-01", "2026-09-30", 125_000), ("2026-07-01", "2026-09-30", 46_000)]
    assert all(f.filed == pd.Timestamp("2026-10-30") and f.accn == "acc-2026-10-30" for f in got)


def test_10k_quarterly_notes_are_ignored():
    got = ss.to_facts(ss.parse_instance(DOC), filing("2027-02-05", "10-K"), CONCEPTS, SEG,
                      "AmazonWebServicesSegmentMember")
    assert [f.val / M for f in got] == [125_000]  # the 9M YTD stays, the 3-month fact is dropped


def test_member_alternatives_first_match_per_filing(monkeypatch):
    old = instance([context("q", "2015-01-01", "2015-03-31", [(PROD, "amzn:AmazonWebServicesMember")])],
                   [("us-gaap:SalesRevenueNet", "q", 1_566 * M)])
    docs = {filing("2015-04-24"): ss.parse_instance(old), filing("2026-10-30"): ss.parse_instance(DOC)}
    monkeypatch.setattr(ss, "company_facts", lambda cik, since, concepts: tuple((f, tuple(d)) for f, d in docs.items()))
    got = ss.member_facts((1,), "2015-01-01", tuple(CONCEPTS), ((SEG, "AmazonWebServicesSegmentMember"),
                                                                  (PROD, "AmazonWebServicesMember")))
    assert sorted(f.val / M for f in got) == [1_566, 46_000, 125_000]


def test_instance_name():
    assert ss.instance_name(["a-20260930.htm", "a-20260930_htm.xml", "a-20260930_cal.xml", "FilingSummary.xml",
                             "R1.htm"]) == "a-20260930_htm.xml"
    assert ss.instance_name(["msft-20150930.xml", "msft-20150930_lab.xml", "msft-20150930_pre.xml", "R2.xml",
                             "msft-20150930.xsd"]) == "msft-20150930.xml"
    assert ss.instance_name(["doc.htm", "doc.txt"]) is None


# ------------------------------------------------------------------ vintages and definition breaks


def fact(start, end, val, filed, form="10-Q"):
    return sec.Fact(pd.Timestamp(start), pd.Timestamp(end), val * M, pd.Timestamp(filed), form, f"acc-{filed}")


def latest(df):
    return df.sort_values("known_from").groupby("period")["value"].last().to_dict()


def first_known(df):
    return {p: str(d.date()) for p, d in df.groupby("period")["known_from"].min().items()}


def test_vintage_dating_3month_facts_and_q4_from_10k():
    facts = [fact("2025-01-01", "2025-03-31", 10_000, "2025-04-30"),
             fact("2025-04-01", "2025-06-30", 12_000, "2025-07-30"), fact("2025-01-01", "2025-06-30", 22_000, "2025-07-30"),
             fact("2025-07-01", "2025-09-30", 15_000, "2025-10-30"), fact("2025-01-01", "2025-09-30", 37_000, "2025-10-30"),
             fact("2025-01-01", "2025-12-31", 55_000, "2026-02-05", "10-K"),
             fact("2025-07-01", "2025-09-30", 15_200, "2026-10-29")]  # small restatement as next year's comparative
    df = sec.vintages([facts])
    assert latest(df) == {"2025Q1": 10_000, "2025Q2": 12_000, "2025Q3": 15_200, "2025Q4": 18_000}
    assert first_known(df) == {"2025Q1": "2025-04-30", "2025Q2": "2025-07-30", "2025Q3": "2025-10-30",
                               "2025Q4": "2026-02-05"}
    assert ss.definition_breaks(facts) == []  # 1.3 % is a revision, not a new definition
    for p, kf in zip(df["period"], df["known_from"]):
        assert kf >= pd.Period(p, "Q").end_time.normalize()


# Old definition reported through the FY2024 10-K; from the next 10-Q on, a recast (-17 %) is rolled out
# over the prior-year comparatives filing by filing (a Microsoft-style fiscal year ending in June).
OLD = [fact("2023-07-01", "2023-09-30", 24, "2023-10-24"),
       fact("2023-10-01", "2023-12-31", 26, "2024-01-30"), fact("2023-07-01", "2023-12-31", 50, "2024-01-30"),
       fact("2024-01-01", "2024-03-31", 27, "2024-04-25"), fact("2023-07-01", "2024-03-31", 77, "2024-04-25"),
       fact("2023-07-01", "2024-06-30", 105, "2024-07-30", "10-K")]
NEW = [fact("2024-07-01", "2024-09-30", 24, "2024-10-30"), fact("2023-07-01", "2023-09-30", 20, "2024-10-30"),
       fact("2024-10-01", "2024-12-31", 26, "2025-01-29"), fact("2024-07-01", "2024-12-31", 50, "2025-01-29"),
       fact("2023-10-01", "2023-12-31", 21.5, "2025-01-29"), fact("2023-07-01", "2023-12-31", 41.5, "2025-01-29"),
       fact("2025-01-01", "2025-03-31", 27, "2025-04-30"), fact("2024-07-01", "2025-03-31", 77, "2025-04-30"),
       fact("2024-01-01", "2024-03-31", 22, "2025-04-30"), fact("2023-07-01", "2024-03-31", 63.5, "2025-04-30"),
       fact("2024-07-01", "2025-06-30", 107, "2025-07-30", "10-K"),
       fact("2023-07-01", "2024-06-30", 87.5, "2025-07-30", "10-K")]


def test_resegmentation_is_detected_once_and_split():
    facts = OLD + NEW
    breaks = ss.definition_breaks(facts)
    assert breaks == [pd.Timestamp("2024-10-30")]  # later recast filings are the same break
    old, new = (sec.vintages([r]) for r in ss.regimes(facts, breaks))
    # the old definition keeps its own history; nothing of the recast leaks into it
    assert latest(old) == {"2023Q3": 24, "2023Q4": 26, "2024Q1": 27, "2024Q2": 28}
    assert set(old["known_from"]) <= {f.filed for f in OLD}
    # the new definition: recast history dated by the filings that recast it, no splice with the old values
    assert latest(new) == {"2023Q3": 20, "2023Q4": 21.5, "2024Q1": 22, "2024Q2": 24, "2024Q3": 24, "2024Q4": 26,
                           "2025Q1": 27, "2025Q2": 30}
    assert first_known(new)["2023Q3"] == "2024-10-30" and first_known(new)["2024Q2"] == "2025-07-30"
    assert new.groupby("period").size().max() == 1  # no revisions: each period has one definition


def test_undeclared_break_fails_the_fetch():
    line = seg_series.Line(("rev_x",), 1, ((SEG, "X"),), "X")
    with pytest.raises(seg_series.DefinitionBreakError, match="2024-10-30"):
        seg_series.checked_regimes(line, OLD + NEW)
    declared = seg_series.Line(("rev_x_old", "rev_x_new"), 1, ((SEG, "X"),), "X", breaks=("2024-10-30",))
    assert [len(r) for r in seg_series.checked_regimes(declared, OLD + NEW)] == [len(OLD), len(NEW)]


def test_offset_fiscal_quarter_passes_leakage_check_with_negative_lag():
    # Oracle-style quarter Sep-Nov: calendar Q4 by midpoint, filed before Dec 31
    df = sec.vintages([[fact("2025-09-01", "2025-11-30", 8, "2025-12-11")]])
    assert latest(df) == {"2025Q4": 8}
    spec = next(s for s in seg_series.SPECS if s.key == "rev_orcl_cloud")
    spec = catalog.Spec(**{**spec.__dict__, "fetch": lambda: None})
    table = observations.new_rows(spec, df[["period", "value", "known_from"]], observations._empty())
    checks = warehouse.run_checks(warehouse.connect(table, [spec]))
    assert all(v.empty for v in checks.values()), {k: v for k, v in checks.items() if len(v)}


def test_catalog_entries():
    keys = {s.key for s in seg_series.SPECS}
    assert {"rev_aws", "rev_google_cloud", "rev_msft_intelligent_cloud_fy25", "rev_msft_cloud",
            "rev_nvda_datacenter", "rev_orcl_cloud"} <= keys
    assert catalog.validate(seg_series.SPECS) == []
    assert all(s.freq == "Q" and s.branch == "G4" and s.publish and s.revised for s in seg_series.SPECS)
    for line in seg_series.LINES:
        assert len(line.keys) == len(line.breaks) + 1
        assert not line.regime_notes or len(line.regime_notes) == len(line.keys)
