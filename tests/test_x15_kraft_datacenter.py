"""Track X15: fixes to S2 after review R18 (docs/granskning/r18-kraft-datacenter.md, register 2026-11-25, X15).

Synthetic facts only, no network. Values in USD millions (x 1e6 in the facts); the numbers are the companies' own
figures where the comment names a filing.
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker.series import sec_stack_kraft as sk
from ai_tracker.sources import sec, sec_segment
from ai_tracker.sources.sec_segment import DimFact, Filing

M = 1e6
T = pd.Timestamp
OTHER, PPE = "PaymentsToAcquireOtherPropertyPlantAndEquipment", "PaymentsToAcquirePropertyPlantAndEquipment"


def F(start, end, val, filed, form="10-Q", accn=None):
    return sec.Fact(T(start), T(end), val * M, T(filed), form, accn or f"acc-{filed}")


def latest(df):
    return df.sort_values("known_from").groupby("period")["value"].last().to_dict()


def first_known(df):
    return {p: str(d.date()) for p, d in df.groupby("period")["known_from"].min().items()}


@pytest.fixture(autouse=True)
def clear_caches():
    for fn in (sk.flow_vintages, sk.flow_series, sk.seg_facts, sk.seg_series):
        fn.cache_clear()
    yield
    for fn in (sk.flow_vintages, sk.flow_series, sk.seg_facts, sk.seg_series):
        fn.cache_clear()


# ------------------------------------------------------------------ R18-2: a tag on another line in one filing


def test_same_line_drops_the_lower_tag_only_from_the_filing_where_it_differs():
    # 10-Q 2011-04-29: 'Purchases of property, plant and equipment' 175,115 is OTHER, 'Purchase of Paris 4 IBX
    # property' 14,951 is PPE. The 10-Q 2012-04-27 tags the same Q1 2011 capex 175,115 as PPE.
    other = [F("2011-01-01", "2011-03-31", 175.115, "2011-04-29")]
    ppe = [F("2011-01-01", "2011-03-31", 14.951, "2011-04-29"), F("2012-01-01", "2012-03-31", 145.49, "2012-04-27"),
           F("2011-01-01", "2011-03-31", 175.115, "2012-04-27"), F("2010-01-01", "2010-09-30", 436.046, "2010-10-29")]
    kept_other, kept_ppe = sk.same_line([other, ppe])
    assert kept_other == other
    assert [(str(f.filed.date()), f.val / M) for f in kept_ppe] == [
        ("2012-04-27", 145.49), ("2012-04-27", 175.115), ("2010-10-29", 436.046)]
    # identical values in one filing (Equinix's parallel tagging 2017-2018) keep both
    both = [F("2017-01-01", "2017-03-31", 277.242, "2017-05-05")]
    assert sk.same_line([both, list(both)]) == [both, both]


def test_eqix_capex_from_2009q3_with_the_older_tag(monkeypatch):
    # Equinix's own figures: 6M/9M 2009 and 2010 under PPE in the 10-Qs 2010, FY 2009/2010 under OTHER in the 10-K
    # 2011-02-25 (where PPE is the Amsterdam purchase), Q1 2010/2011 under OTHER in the 10-Q 2011-04-29.
    rows = [(PPE, "2009-01-01", "2009-06-30", 179.607, "2010-08-04", "10-Q"),
            (PPE, "2010-01-01", "2010-06-30", 292.105, "2010-08-04", "10-Q"),
            (PPE, "2009-01-01", "2009-09-30", 267.802, "2010-10-29", "10-Q"),
            (PPE, "2010-01-01", "2010-09-30", 436.046, "2010-10-29", "10-Q"),
            (OTHER, "2009-01-01", "2009-12-31", 369.542, "2011-02-25", "10-K"),
            (OTHER, "2010-01-01", "2010-12-31", 579.397, "2011-02-25", "10-K"),
            (PPE, "2010-01-01", "2010-12-31", 14.861, "2011-02-25", "10-K"),
            (OTHER, "2010-01-01", "2010-03-31", 143.4, "2011-04-29", "10-Q"),
            (OTHER, "2011-01-01", "2011-03-31", 175.115, "2011-04-29", "10-Q"),
            (PPE, "2011-01-01", "2011-03-31", 14.951, "2011-04-29", "10-Q")]
    facts: dict = {}
    for tag, s, e, v, d, form in rows:
        facts.setdefault(tag, {"units": {"USD": []}})["units"]["USD"].append(
            {"start": s, "end": e, "val": v * M, "filed": d, "form": form, "accn": f"acc-{d}"})
    monkeypatch.setattr(sk.sec, "companyfacts", lambda cik: {"facts": {"us-gaap": facts}})
    df = sk.flow_series("capex", "eqix")
    assert latest(df) == pytest.approx({"2009Q3": 267.802 - 179.607, "2009Q4": 369.542 - 267.802, "2010Q1": 143.4,
                                        "2010Q2": 292.105 - 143.4, "2010Q3": 436.046 - 292.105,
                                        "2010Q4": 579.397 - 436.046, "2011Q1": 175.115})
    assert first_known(df) == {"2009Q3": "2010-10-29", "2009Q4": "2011-02-25", "2010Q1": "2011-04-29",
                               "2010Q2": "2011-04-29", "2010Q3": "2010-10-29", "2010Q4": "2011-02-25",
                               "2011Q1": "2011-04-29"}
    assert (df["value"] > 0).all()


# ------------------------------------------------------------------ R18-1 and R18-9: Eaton's recast history


def test_segment_facts_are_not_cut_by_the_550_day_rule(monkeypatch):
    # 10-Q 2020-04-30 recasts the 2018-2019 quarters to the new segments; 2018Q3 ends 578 days before the filing.
    line = next(x for x in sk.SEG_LINES if x.keys[0] == "rev_etn_electrical_americas")
    f = Filing(sk.ETN, "0001551182-20-000127", "2020-04-30", "10-Q")
    dfs = tuple(DimFact(sk.RFCC, T(s), T(e), frozenset({(sk.SEG, "ElectricalAmericasMember")}), v * M, "USD")
                for s, e, v in (("2018-07-01", "2018-09-30", 1), ("2019-01-01", "2019-03-31", 1961),
                                ("2020-01-01", "2020-03-31", 1788)))
    monkeypatch.setattr(sk.sec_segment, "company_facts", lambda cik, since, concepts: ((f, dfs),))
    got = sk.seg_facts(line)
    assert [str(x.end.date()) for x in got] == ["2018-09-30", "2019-03-31", "2020-03-31"]
    assert (got[0].filed - got[0].end).days == 578 > sk.MAX_10Q_AGE_DAYS
    # flows and balances keep the rule
    assert sk.kept(list(got), sk.ETN, "etn") == list(got[1:])


def test_etn_dimsets_prefer_the_2021_name_without_a_marker():
    line = next(x for x in sk.SEG_LINES if x.keys[0] == "rev_etn_electrical_global")
    assert line.dimsets == (sk._seg("ElectricalGlobalSegmentMember"),
                            sk._seg("ElectricalGlobalSegmentMember", "OperatingSegmentsMember"),
                            sk._seg("ElectricalGlobalMember"), sk._seg("ElectricalGlobalMember", "OperatingSegmentsMember"))
    assert line.since == "2020-01-01"  # ElectricalAmericasMember was an older segment in the 10-K for 2012


# ------------------------------------------------------------------ R18-3: Vertiv external segment sales


def test_vertiv_external_and_gross_lines_read_different_contexts():
    # 10-Q 2026-10-28, EMEA: 'Sales' 823.7 with OperatingSegmentsMember, of which intersegment 279.0 (external 544.7)
    f = Filing(sk.VRT, "acc-q", "2026-10-28", "10-Q")
    emea = (sk.SEG, "EMEASegmentMember")
    dfs = [DimFact(sk.RFCC, T("2026-07-01"), T("2026-09-30"), frozenset({emea}), 544.7 * M, "USD"),
           DimFact(sk.RFCC, T("2026-07-01"), T("2026-09-30"), frozenset({emea, (sk.CONS, "OperatingSegmentsMember")}),
                   823.7 * M, "USD"),
           DimFact(sk.RFCC, T("2026-07-01"), T("2026-09-30"),
                   frozenset({emea, (sk.CONS, "IntersegmentEliminationMember")}), 279.0 * M, "USD")]
    lines = {x.keys[0]: x for x in sk.SEG_LINES}
    net = sk.line_facts_from([(f, dfs)], lines["rev_vrt_emea_net"])
    gross = sk.line_facts_from([(f, dfs)], lines["rev_vrt_emea"])
    assert [x.val / M for x in net] == [544.7] and [x.val / M for x in gross] == [823.7]
    specs = {s.key: s for s in sk.SPECS}
    assert "extern försäljning" in specs["rev_vrt_emea_net"].label and "rev_vrt" in specs["rev_vrt_emea_net"].note


# ------------------------------------------------------------------ R18-4 consequence: Digital Realty 2010-2011


def test_dlr_parent_company_member_only_where_no_plain_fact(monkeypatch):
    tag = "Revenues"
    parent = frozenset({("LegalEntityAxis", "ParentCompanyMember")})
    lp = frozenset({("LegalEntityAxis", "DigitalRealtyTrustLPMember")})
    q3 = Filing(sk.DLR, "0001193125-10-254366", "2010-11-09", "10-Q")  # every fact carries LegalEntityAxis
    q2 = Filing(sk.DLR, "0001193125-11-212571", "2011-08-05", "10-Q")  # Inc. without dimensions
    dfs = {b"q3": [DimFact(tag, T("2010-07-01"), T("2010-09-30"), parent, 237.486 * M, "USD"),
                   DimFact(tag, T("2010-07-01"), T("2010-09-30"), lp, 237.486 * M, "USD")],
           b"q2": [DimFact(tag, T("2011-04-01"), T("2011-06-30"), frozenset(), 263.1 * M, "USD"),
                   DimFact(tag, T("2011-04-01"), T("2011-06-30"), parent, 1.0, "USD"),  # never read here
                   DimFact(tag, T("2011-04-01"), T("2011-06-30"), lp, 2.0, "USD")]}
    monkeypatch.setattr(sk.sec_custom, "_filings", lambda cik, since, until: ((q3, b"q3"), (q2, b"q2")))
    monkeypatch.setattr(sk.sec_segment, "parse_instance", lambda raw, concepts: dfs[raw])
    got = sk.instance_flow_facts(sk.DLR, tag, "2009-01-01")
    assert [(str(x.filed.date()), x.val / M) for x in got] == [("2010-11-09", 237.486), ("2011-08-05", 263.1)]


def test_instance_name_skips_defnref_in_any_case():
    assert sec_segment.instance_name(["DefnRef.xml", "msft-20101231.xml", "msft-20101231_lab.xml"]) == \
        "msft-20101231.xml"
    assert sec_segment.instance_name(["defnref.xml", "FilingSummary.xml"]) is None
