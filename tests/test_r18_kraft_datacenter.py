"""R18 review of S2, power, cooling, grid and data-centre companies (docs/granskning/r18-kraft-datacenter.md).

Fixtures only, no network. The numbers are the companies' own figures as filed (USD millions), read off the
documents on www.sec.gov for the review (accessions in the review doc). Passing tests pin properties that hold;
every confirmed defect is a strict xfail that flips when it is fixed.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ai_tracker.series import sec_stack_kraft as sk
from ai_tracker.sources import sec, sec_custom, sec_segment
from ai_tracker.sources.sec_segment import DimFact, Filing

M = 1e6
T = pd.Timestamp
DOC = Path(__file__).resolve().parents[1] / "docs" / "kallor" / "sec_stack_kraft.md"
OTHER, PPE = "PaymentsToAcquireOtherPropertyPlantAndEquipment", "PaymentsToAcquirePropertyPlantAndEquipment"


def F(start, end, val, filed, form="10-Q"):
    return sec.Fact(T(start), T(end), val * M, T(filed), form, f"acc-{filed}")


def first_known(df):
    return {p: str(d.date()) for p, d in df.groupby("period")["known_from"].min().items()}


def latest(df):
    return df.sort_values("known_from").groupby("period")["value"].last().to_dict()


@pytest.fixture(autouse=True)
def clear_caches():
    sk.flow_vintages.cache_clear()
    sk.flow_series.cache_clear()
    yield
    sk.flow_vintages.cache_clear()
    sk.flow_series.cache_clear()


def cf_doc(rows):
    """companyfacts JSON from (tag, start, end, value, filed, form) rows."""
    facts: dict = {}
    for tag, s, e, v, d, form in rows:
        facts.setdefault(tag, {"units": {"USD": []}})["units"]["USD"].append(
            {"start": s, "end": e, "val": v * M, "filed": d, "form": form, "accn": f"acc-{d}"})
    return {"facts": {"us-gaap": facts}}


# ------------------------------------------------------------------ point 2: filters and GE Vernova history


def test_550_day_rule_margin_over_the_comparatives_read_today():
    # Among the facts the S2 code reads today, the oldest kept 10-Q fact ends 408 days before its filing (Equinix,
    # Digital Realty), and the one fact the rule drops is Equinix's Q1 2025 revenue tagged with the dates of Q1 2023
    # (10-Q 2025-04-30: the statement has only the columns Q1 2025 = 2,225 and Q1 2024 = 2,127). Not universal:
    # Eaton's 10-Q 2020-04-30 recasts 2018 segment quarters (578 days), see R18-1 in the review doc.
    comparative = F("2024-01-01", "2024-03-31", 2127, "2025-04-30")
    oldest_kept = F("2023-01-01", "2023-03-31", 1, "2024-05-12")  # 408 days
    misdated = F("2023-01-01", "2023-03-31", 2225, "2025-04-30")  # 761 days
    assert [sk.plausible(f) for f in (comparative, oldest_kept, misdated)] == [True, True, False]
    assert (misdated.filed - misdated.end).days > sk.MAX_10Q_AGE_DAYS > (oldest_kept.filed - oldest_kept.end).days + 100


def test_gev_flows_use_only_its_own_10q_and_10k(monkeypatch):
    # GE Vernova's Form 10 (10-12B 2024-02-15, 10-12B/A 2024-03-05) has no XBRL; its 8-K 2024-04-02 has. Only
    # 10-Q/10-K facts filed by GE Vernova itself enter the series: 2023 comes from the comparatives of 2024.
    doc = cf_doc([
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "2023-01-01", "2023-03-31", 9999, "2024-04-02", "8-K"),
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "2023-01-01", "2023-03-31", 6822, "2024-04-30", "10-Q"),
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "2024-01-01", "2024-03-31", 7260, "2024-04-30", "10-Q"),
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "2023-01-01", "2023-09-30", 23194, "2024-10-23", "10-Q"),
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "2023-01-01", "2023-12-31", 33239, "2025-02-06", "10-K"),
    ])
    monkeypatch.setattr(sk.sec, "companyfacts", lambda cik: doc)
    df = sk.flow_vintages("rev", "gev")
    assert latest(df) == {"2023Q1": 6822, "2023Q4": 33239 - 23194, "2024Q1": 7260}
    assert first_known(df) == {"2023Q1": "2024-04-30", "2023Q4": "2025-02-06", "2024Q1": "2024-04-30"}
    assert sk.COMPANIES["gev"].ciks == (sk.GEV,)


def test_gev_recast_2026_splits_electrification_only():
    # 10-Q 2026-04-22 recast Q1 2025: Electrification 1,879 -> 1,840 (-2.08 %), Power 4,423 -> 4,449 (+0.59 %).
    def facts(old, new):
        return [F("2025-01-01", "2025-03-31", old, "2025-04-23"), F("2025-04-01", "2025-06-30", 1, "2025-07-23"),
                F("2026-01-01", "2026-03-31", 2, "2026-04-22"), F("2025-01-01", "2025-03-31", new, "2026-04-22")]
    assert sec_segment.definition_breaks(facts(1879, 1840)) == [T("2026-04-22")]
    assert sec_segment.definition_breaks(facts(4423, 4449)) == []
    line = next(x for x in sk.SEG_LINES if x.keys[0].startswith("rev_gev_electrification"))
    old, new = sk.checked_regimes(line.keys, line.breaks, facts(1879, 1840))
    assert {f.filed for f in old} == {T("2025-04-23"), T("2025-07-23")} and {f.filed for f in new} == {T("2026-04-22")}


def test_dlr_instance_flows_ignore_the_partnership_contexts():
    # The 10-K/10-Q of Digital Realty Trust, Inc. and Digital Realty Trust, L.P. is one document; the partnership's
    # facts carry LegalEntityAxis and are not read.
    f = Filing(sk.DLR, "acc-q", "2026-07-31", "10-Q")
    dfs = [DimFact("PaymentsToDevelopRealEstateAssets", T("2026-01-01"), T("2026-06-30"), frozenset(), 1784.229 * M, "USD"),
           DimFact("PaymentsToDevelopRealEstateAssets", T("2026-01-01"), T("2026-06-30"),
                   frozenset({("LegalEntityAxis", "DigitalRealtyTrustLPMember")}), 1.0, "USD")]
    got = sec_custom.plain_facts(dfs, f, ["PaymentsToDevelopRealEstateAssets"])
    assert [(x.val / M, str(x.filed.date())) for x in got] == [(1784.229, "2026-07-31")]


# ------------------------------------------------------------------ R18-1: Eaton's electrical segments in 2020


ETN_2020Q1 = (Filing(sk.ETN, "0001551182-20-000127", "2020-04-30", "10-Q"),
              [DimFact(sk.RFCC, T("2020-01-01"), T("2020-03-31"),
                       frozenset({(sk.SEG, "ElectricalAmericasMember")}), 1788 * M, "USD"),
               DimFact(sk.RFCC, T("2019-01-01"), T("2019-03-31"),
                       frozenset({(sk.SEG, "ElectricalAmericasMember")}), 1961 * M, "USD")])
ETN_2021Q1 = (Filing(sk.ETN, "0001551182-21-000120", "2021-05-04", "10-Q"),
              [DimFact(sk.RFCC, T("2021-01-01"), T("2021-03-31"),
                       frozenset({(sk.SEG, "ElectricalAmericasSegmentMember")}), 1622 * M, "USD"),
               DimFact(sk.RFCC, T("2020-01-01"), T("2020-03-31"),
                       frozenset({(sk.SEG, "ElectricalAmericasSegmentMember")}), 1788 * M, "USD")])


def test_etn_member_names_from_2021_are_read():
    line = next(x for x in sk.SEG_LINES if x.keys[0] == "rev_etn_electrical_americas")
    got = sk.line_facts_from([ETN_2021Q1], line)
    assert sorted((str(x.end.date()), x.val / M) for x in got) == [("2020-03-31", 1788), ("2021-03-31", 1622)]


@pytest.mark.xfail(strict=True, reason="R18-1: the 2020 10-Qs use ElectricalAmericasMember/ElectricalGlobalMember")
def test_etn_2020_10q_segment_names_are_read():
    # 10-Q 2020-04-30, 2020-07-29 and 2020-11-03 tag the new segments as ElectricalAmericasMember and
    # ElectricalGlobalMember (from the 10-K 2021-02-24: ...SegmentMember). The series takes 2020Q1-Q3 only from the
    # comparatives a year later, and the 2018-2019 recast quarters in 10-Q 2020-04-30 are lost.
    line = next(x for x in sk.SEG_LINES if x.keys[0] == "rev_etn_electrical_americas")
    df = sec.vintages([sk.line_facts_from([ETN_2020Q1, ETN_2021Q1], line)])
    assert first_known(df)["2020Q1"] == "2020-04-30"
    assert latest(df)["2019Q1"] == 1961


# ------------------------------------------------------------------ R18-2: Equinix capex in the 10-Qs


EQIX_ROWS = [
    # 10-K 2011-02-25: 'Purchases of other PP&E' 579.397; the old tag holds 'Purchase of Amsterdam IBX property'
    (OTHER, "2010-01-01", "2010-12-31", 579.397, "2011-02-25", "10-K"),
    (PPE, "2010-01-01", "2010-12-31", 14.861, "2011-02-25", "10-K"),
    (PPE, "2010-01-01", "2010-09-30", 436.046, "2010-10-29", "10-Q"),
    (OTHER, "2010-01-01", "2010-09-30", 436.046, "2011-10-28", "10-Q"),
    # 2016: 'Purchases of other property, plant and equipment' in every 10-Q; the 10-Q 2016-11-04 tags it PPE
    (OTHER, "2016-01-01", "2016-03-31", 197.7, "2016-05-09", "10-Q"),
    (OTHER, "2016-01-01", "2016-06-30", 447.567, "2016-08-08", "10-Q"),
    (PPE, "2016-01-01", "2016-09-30", 727.044, "2016-11-04", "10-Q"),
    (PPE, "2016-07-01", "2016-09-30", 279.477, "2016-11-04", "10-Q"),
    (OTHER, "2016-01-01", "2016-09-30", 727.044, "2017-11-03", "10-Q"),
    (OTHER, "2016-07-01", "2016-09-30", 279.477, "2017-11-03", "10-Q"),
]


@pytest.fixture
def eqix_capex(monkeypatch):
    doc = cf_doc(EQIX_ROWS)
    monkeypatch.setattr(sk.sec, "companyfacts", lambda cik: doc)
    return sk.flow_vintages("capex", "eqix")


def test_eqix_capex_never_differences_the_amsterdam_purchase(eqix_capex):
    # The old tag's FY2010 fact in the 10-K 2011 is another line; FY - 9M across the two would be -421.2.
    assert (eqix_capex["value"] > 0).all()
    assert latest(eqix_capex)["2010Q4"] == pytest.approx(579.397 - 436.046)
    assert latest(eqix_capex)["2016Q3"] == pytest.approx(279.477)


@pytest.mark.xfail(strict=True, reason="R18-2: 10-Q facts under PaymentsToAcquirePropertyPlantAndEquipment are unused")
def test_eqix_capex_first_version_from_the_10q_that_reports_it(eqix_capex):
    assert first_known(eqix_capex)["2016Q3"] == "2016-11-04"


# ------------------------------------------------------------------ R18-4: shared instance selection


@pytest.mark.xfail(strict=True, reason="R18-4: sec_segment.instance_name picks defnref.xml (2009-2011 filings)")
def test_instance_name_skips_defnref():
    names = ["defnref.xml", "dlr-20100930.xml", "dlr-20100930_cal.xml", "dlr-20100930_def.xml",
             "dlr-20100930_lab.xml", "dlr-20100930_pre.xml", "FilingSummary.xml", "R1.xml", "d10q.htm"]
    assert sec_segment.instance_name(names) == "dlr-20100930.xml"


def test_instance_name_later_filings():
    assert sec_segment.instance_name(["dlr-20110630.xml", "dlr-20110630_cal.xml", "FilingSummary.xml"]) == \
        "dlr-20110630.xml"
    assert sec_segment.instance_name(["vrt-20260930.htm", "vrt-20260930_htm.xml", "vrt-20260930_lab.xml"]) == \
        "vrt-20260930_htm.xml"


# ------------------------------------------------------------------ misleading statements in the source doc


@pytest.mark.xfail(strict=True, reason="R18-1/R18-2/R18-3: statements in docs/kallor/sec_stack_kraft.md")
@pytest.mark.parametrize("claim", [
    # R18-1: 10-Q 2020-04-30 has Q1 2019 and all quarters of 2018-2019 for the new segments
    "2020 års 10-Q har inga kvartalsvisa jämförelsetal för 2019",
    # R18-2: the old tag is the 10-Q line 2010-2018; the one deviating overlap is FY2010 in the 10-K 2011-02-25
    "Raden taggades då `PaymentsToAcquirePropertyPlantAndEquipment`",
    # R18-3: EMEA has had the largest intersegment sales since 2022Q1 (2026Q3: EMEA 279.0, Asia Pacific 228.8)
    "Asia Pacific har störst intern försäljning",
])
def test_source_doc_statements(claim):
    assert claim not in DOC.read_text(encoding="utf-8")
