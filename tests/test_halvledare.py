"""Semiconductors (L6): balance-sheet instants, own-tag facts, member overrides, ASML 6-K parsing, catalog.

Synthetic fixtures, no network. Values in USD/EUR millions (x 1e6 in XBRL facts).
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import catalog, observations, warehouse
from ai_tracker.series import halvledare as h
from ai_tracker.series.sec_segments import SEG
from ai_tracker.sources import asml_sec, sec, sec_instant, sec_segment as ss

M = 1e6


def latest(df):
    return df.sort_values("known_from").groupby("period")["value"].last().to_dict()


def first_known(df):
    return {p: str(d.date()) for p, d in df.groupby("period")["known_from"].min().items()}


# ------------------------------------------------------------------ instants (inventories, obligations)

# Nvidia-style fiscal year (52/53 weeks to late January): quarters end late Apr/Jul/Oct/Jan.
NVDA_REV = [sec.Fact(pd.Timestamp(s), pd.Timestamp(e), 1 * M, pd.Timestamp(f), "10-Q", "a")
            for s, e, f in [("2025-01-27", "2025-04-27", "2025-05-28"), ("2025-04-28", "2025-07-27", "2025-08-27"),
                            ("2025-07-28", "2025-10-26", "2025-11-19")]]


def companyfacts_instants(rows, tag="InventoryNet"):
    return {"facts": {"us-gaap": {tag: {"units": {"USD": [
        {"end": e, "val": v * M, "filed": f, "form": form, "accn": f"acc-{f}"} for e, v, f, form in rows]
        + [{"start": "2025-01-27", "end": "2025-04-27", "val": 1, "filed": "2025-05-28", "form": "10-Q"}]}}}}}


def test_instants_map_to_the_fiscal_quarter_and_are_dated_by_filing():
    cf = companyfacts_instants([
        ("2025-04-27", 11_333, "2025-05-28", "10-Q"),
        ("2025-07-27", 14_962, "2025-08-27", "10-Q"),
        ("2025-04-27", 11_333, "2025-08-27", "10-Q"),   # comparative repeat: no new vintage
        ("2025-10-26", 19_784, "2025-11-19", "10-Q"),
        ("2025-07-27", 15_000, "2025-11-19", "10-Q/A"),  # restated: a new vintage dated by the restating filing
        ("2025-09-15", 1, "2025-11-19", "10-Q"),        # not a fiscal quarter end: dropped
        ("2025-04-27", 5, "2025-05-28", "8-K"),          # not a 10-Q/10-K: dropped
    ])
    facts = sec_instant.facts(cf, "InventoryNet")
    assert len(facts) == 6  # the duration fact and the 8-K are skipped
    df = sec_instant.vintages([facts], sec_instant.fiscal_quarters([NVDA_REV]))
    # late-October balance = the Aug-Oct fiscal quarter = calendar Q3 (midpoint rule), like the flows
    assert latest(df) == {"2025Q1": 11_333, "2025Q2": 15_000, "2025Q3": 19_784}
    assert first_known(df) == {"2025Q1": "2025-05-28", "2025Q2": "2025-08-27", "2025Q3": "2025-11-19"}
    assert len(df) == 4


def test_instant_sources_priority_per_date():
    q = sec_instant.fiscal_quarters([NVDA_REV])
    old = [sec_instant.Instant(pd.Timestamp("2025-04-27"), 10 * M, pd.Timestamp("2025-05-28"), "10-Q", "a"),
           sec_instant.Instant(pd.Timestamp("2025-07-27"), 99 * M, pd.Timestamp("2025-08-27"), "10-Q", "b")]
    new = [sec_instant.Instant(pd.Timestamp("2025-07-27"), 12 * M, pd.Timestamp("2025-08-27"), "10-Q", "b"),
           sec_instant.Instant(pd.Timestamp("2025-10-26"), 13 * M, pd.Timestamp("2025-11-19"), "10-Q", "c")]
    assert latest(sec_instant.vintages([new, old], q)) == {"2025Q1": 10, "2025Q2": 12, "2025Q3": 13}


def instance(contexts, facts) -> bytes:
    body = "".join(contexts) + '<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>'
    for concept, cid, val in facts:
        body += f'<{concept} contextRef="{cid}" unitRef="usd" decimals="-6">{val}</{concept}>'
    return ('<?xml version="1.0"?><xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" '
            'xmlns:xbrldi="http://xbrl.org/2006/xbrldi" xmlns:us-gaap="http://fasb.org/us-gaap/2025" '
            'xmlns:nvda="http://www.nvidia.com/2025" xmlns:iso4217="http://www.xbrl.org/2003/iso4217">'
            + body + "</xbrli:xbrl>").encode()


def context(cid, end, start=None, dims=()):
    members = "".join(f'<xbrldi:explicitMember dimension="{a}">{m}</xbrldi:explicitMember>' for a, m in dims)
    segment = f"<xbrli:segment>{members}</xbrli:segment>" if dims else ""
    period = (f"<xbrli:startDate>{start}</xbrli:startDate><xbrli:endDate>{end}</xbrli:endDate>" if start
              else f"<xbrli:instant>{end}</xbrli:instant>")
    return (f'<xbrli:context id="{cid}"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">1'
            f"</xbrli:identifier>{segment}</xbrli:entity><xbrli:period>{period}</xbrli:period></xbrli:context>")


SUPPLY = ("us-gaap:OtherCommitmentsAxis", "nvda:SupplyAndCapacityCommitmentsMember")
CLOUD = ("us-gaap:OtherCommitmentsAxis", "nvda:CloudServiceAgreementCommitmentsMember")
DOC = instance(
    [context("i", "2025-10-26"), context("i_sup", "2025-10-26", dims=[SUPPLY]), context("i_cl", "2025-10-26", dims=[CLOUD]),
     context("ytd", "2025-10-26", "2025-01-27"), context("q", "2025-10-26", "2025-07-28")],
    [("us-gaap:PurchaseObligation", "i", 45_000 * M), ("us-gaap:OtherCommitment", "i_sup", 50_300 * M),
     ("us-gaap:OtherCommitment", "i_cl", 26_000 * M), ("us-gaap:PurchaseObligation", "ytd", 1 * M),
     ("nvda:PurchasesOfPropertyAndEquipmentAndIntangibleAssets", "ytd", 4_000 * M),
     ("nvda:PurchasesOfPropertyAndEquipmentAndIntangibleAssets", "q", 1_500 * M)])


def test_parse_instants_exact_dimensions():
    assert sec_instant.parse_instants(DOC, {"PurchaseObligation"}) == [
        ("PurchaseObligation", pd.Timestamp("2025-10-26"), 45_000 * M)]  # the duration fact is not an instant
    dims = frozenset({("OtherCommitmentsAxis", "SupplyAndCapacityCommitmentsMember")})
    assert [v / M for _, _, v in sec_instant.parse_instants(DOC, {"OtherCommitment"}, dims)] == [50_300]
    f = ss.Filing(1, "acc-1", "2025-11-19", "10-Q")
    got = sec_instant.instance_instants([(f, DOC)], "OtherCommitment", dims)
    assert [(i.end, i.val / M, i.filed) for i in got] == [(pd.Timestamp("2025-10-26"), 50_300, pd.Timestamp("2025-11-19"))]


def test_own_tag_duration_facts_from_instances():
    q10 = ss.Filing(1, "acc-q", "2025-11-19", "10-Q")
    k10 = ss.Filing(1, "acc-k", "2026-02-25", "10-K")
    got = h.plain_duration_facts([(q10, DOC), (k10, DOC)], h.NVDA_CAPEX_OWN)
    # the 10-Q gives YTD and quarter; the 10-K's 3-month fact is skipped (quarterly note), as in sec.facts
    assert sorted((str(f.start.date()), f.val / M, f.form) for f in got) == [
        ("2025-01-27", 4_000, "10-K"), ("2025-01-27", 4_000, "10-Q"), ("2025-07-28", 1_500, "10-Q")]


# ------------------------------------------------------------------ AMD member override


def test_member_override_per_filing(monkeypatch):
    def dimfacts(member, value, end="2024-03-30"):
        return ss.DimFact("RevenueFromContractWithCustomerExcludingAssessedTax", pd.Timestamp("2023-12-31"),
                          pd.Timestamp(end), frozenset({(SEG, member)}), value * M, "USD")

    rotated = ss.Filing(h.AMD, "acc-r", h.AMD_ROTATED[3], "10-Q")
    correct = ss.Filing(h.AMD, "acc-c", "2025-05-07", "10-Q")
    data = ((rotated, (dimfacts("DataCenterMember", 922), dimfacts("ClientMember", 2_337))),
            (correct, (dimfacts("DataCenterMember", 2_337), dimfacts("ClientAndGamingMember", 2_290))))
    monkeypatch.setattr(ss, "company_facts", lambda cik, since, concepts: data)
    got = h.line_facts(h.LINES[0])
    assert [(f.filed.date().isoformat(), f.val / M) for f in got] == [(h.AMD_ROTATED[3], 2_337), ("2025-05-07", 2_337)]
    assert ss.definition_breaks(got) == []


# ------------------------------------------------------------------ ASML 6-K press releases

REL_2026Q3 = ("EX-99.1 ASML reports €11.7 billion total net sales and €5.0 billion net income in Q3 2026 VELDHOVEN, "
              "October 14, 2026 – Today, ASML Holding NV (ASML) has published its 2026 third-quarter results. "
              "(Figures in millions of euros unless otherwise indicated) Q2 2026 Q3 2026 Total net sales 9,326 11,662 "
              "...of which Installed Base Management sales 1 2,762 3,289 Gross profit 5,035 6,700")
REL_2025Q4 = ("ASML reports €32.7 billion total net sales in 2025 Today ASML has published its 2025 fourth-quarter and "
              "full-year results. • Quarterly net bookings in Q4 of €13.2 billion (Figures in millions of euros unless "
              "otherwise indicated) Q3 2025 Q4 2025 FY 2024 FY 2025 Total net sales 7,516 9,718 28,263 32,667 New "
              "lithography systems sold (units) 66 94 380 300 Net bookings 2 5,399 13,158 18,899 3 28,035 3 Backlog 4 "
              "35,938 38,797 Gross profit 3,880 5,068 (2) Net bookings include all system sales orders and "
              "inflation-related adjustments, for which written authorizations have been accepted. (3) The sum.")
REL_2018Q1 = ("ASML reports first-quarter results today ASML publishes its 2018 first-quarter results. (Figures in "
              "millions of euros unless otherwise indicated) Q4 2017 1 Q1 2018 Net sales 2,561 2,285 Net bookings 3 "
              "2,935 2,442 Gross profit 1,156 1,113")
REL_2017Q4 = ("ASML publishes its 2017 fourth-quarter results (Figures in millions of euros unless otherwise indicated) "
              "Q3 2017 Q4 2017 FY 2016 FY 2017 Net sales 2,447 2,561 6,795 9,053 Net bookings (3) 2,154 2,935 5,396 "
              "9,358 Systems backlog (3) 5,693 6,685")
REL_2014Q4 = ("ASML today publishes its 2014 fourth-quarter results. (Figures in millions of euros unless otherwise "
              "indicated) Q4 2014 Q3 2014 FY 2014 FY 2013 Net sales 1,494 1,322 5,856 5,245 Net bookings 1,387 * 1,397 "
              "4,902 * 4,644 Net bookings (units) 51 * 47")
REL_2013Q3 = ("ASML today publishes 2013 third-quarter results. (Figures in millions of euros unless otherwise indicated) "
              "Q3 2013 Q2 2013 Net sales 1,318 1,187 of which service 359 271 Net bookings, excluding EUV 1,415 1,065 "
              "Net bookings, excluding EUV (units) 51 38")
REL_2009Q3 = ("ASML announces 2009 Third Quarter Results ASML today announces 2009 third quarter results according to "
              "US GAAP as follows: • Q3 2009 net sales of EUR 555 million versus Q2 2009 net sales of EUR 277 million "
              "(Q3 2008 net sales of EUR 696 million). • Q3 2009 net bookings valued at EUR 777 million with 35 systems")


def figures(rel, measure):
    return {str(q): v for q, (v, _) in rel.figures.get(measure, {}).items()}


@pytest.mark.parametrize("text,sales,bookings", [
    (REL_2026Q3, {"2026Q2": 9_326, "2026Q3": 11_662}, {}),
    (REL_2025Q4, {"2025Q3": 7_516, "2025Q4": 9_718}, {"2025Q3": 5_399, "2025Q4": 13_158}),
    (REL_2018Q1, {"2017Q4": 2_561, "2018Q1": 2_285}, {"2017Q4": 2_935, "2018Q1": 2_442}),
    (REL_2017Q4, {"2017Q3": 2_447, "2017Q4": 2_561}, {"2017Q3": 2_154, "2017Q4": 2_935}),
    (REL_2014Q4, {"2014Q4": 1_494, "2014Q3": 1_322}, {"2014Q4": 1_387, "2014Q3": 1_397}),
    (REL_2013Q3, {"2013Q3": 1_318, "2013Q2": 1_187}, {"2013Q3": 1_415, "2013Q2": 1_065}),
    (REL_2009Q3, {"2009Q3": 555, "2009Q2": 277, "2008Q3": 696}, {"2009Q3": 777}),
])
def test_parse_release_layouts(text, sales, bookings):
    rel = asml_sec.parse_release(text)
    assert figures(rel, "net_sales") == sales
    assert figures(rel, "net_bookings") == bookings
    assert str(rel.quarter) == max(sales)


def test_bookings_definitions_carry_label_and_footnote():
    defs = {d for _, d in asml_sec.parse_release(REL_2025Q4).figures["net_bookings"].values()}
    assert defs == {"net bookings | net bookings include all system sales orders and inflation-related adjustments, "
                    "for which written authorizations have been accepted."}
    assert {d for _, d in asml_sec.parse_release(REL_2013Q3).figures["net_bookings"].values()} == {
        "net bookings, excluding euv"}


def test_non_release_and_miscounted_row_are_rejected():
    assert asml_sec.parse_release("ASML announces the appointment of a new CFO to the Board") is None
    bad = REL_2013Q3.replace("Net sales 1,318 1,187", "Net sales 1,318 1,187 12,345")
    assert asml_sec.parse_release(bad) is None  # three values for two columns: not used


def test_asml_vintages_and_regime_selection():
    items = [("2025-10-15", asml_sec.parse_release(REL_2025Q4.replace("9,718", "9,700"))),
             ("2026-01-28", asml_sec.parse_release(REL_2025Q4)),
             ("2013-10-16", asml_sec.parse_release(REL_2013Q3))]
    df = asml_sec.vintages(items, "net_sales")
    assert df[df.period == "2025Q4"][["value", "known_from"]].values.tolist() == [
        [9_700, pd.Timestamp("2025-10-15")], [9_718, pd.Timestamp("2026-01-28")]]  # a restatement is a later vintage
    assert first_known(df)["2025Q3"] == "2025-10-15"
    _, lo, hi, test, _ = next(b for b in h.ASML_BOOKINGS if b[0] == "asml_net_bookings_ex_euv")
    ex = asml_sec.vintages(items, "net_bookings", keep=lambda q, d: lo <= q <= hi and test(d))
    assert set(ex.period) == {"2013Q2", "2013Q3"}


def test_release_of_skips_non_results_months_and_reads_exhibits(monkeypatch):
    f = asml_sec.Filing("0001-26-1", "2026-10-14", "6-K", "form6-k.htm")
    monkeypatch.setattr(asml_sec, "candidate_docs", lambda f: ["press.htm", "form6-k.htm"])
    monkeypatch.setattr(asml_sec, "_cached_get", lambda url: (REL_2026Q3 if url.endswith("press.htm") else "6-K cover").encode())
    assert str(asml_sec.release_of(f).quarter) == "2026Q3"
    assert asml_sec.release_of(asml_sec.Filing("0001-26-2", "2026-03-11", "6-K", "agm.htm")) is None


# ------------------------------------------------------------------ catalog and leakage check


def test_catalog_entries():
    keys = {s.key for s in h.SPECS}
    assert {"rev_amd", "rev_amd_datacenter", "capex_amd", "rev_avgo", "rev_avgo_semis", "rev_mrvl",
            "rev_mrvl_datacenter", "rev_mu", "rev_mu_cnbu", "rev_mu_cmbu", "capex_mu", "inv_mu", "capex_nvda",
            "inv_nvda", "purchase_oblig_nvda", "asml_net_sales", "asml_net_bookings"} <= keys
    assert catalog.validate(h.SPECS) == []
    assert catalog.validate() == []  # no key clashes with the rest of the catalog
    assert all(s.freq == "Q" and s.branch == "G6" and s.publish and s.revised for s in h.SPECS)
    assert {s.key for s in h.SPECS if s.closed} == {"rev_mu_cnbu", "asml_net_bookings_2006", "asml_net_bookings_ex_euv",
                                                    "asml_net_bookings"}


def test_micron_offset_quarter_passes_leakage_check():
    # Micron FQ1 (Sep-Nov) = calendar Q4 by midpoint, filed before Dec 31: allowed by lag_days = -31
    df = sec.vintages([[sec.Fact(pd.Timestamp("2025-08-29"), pd.Timestamp("2025-11-27"), 13_643 * M,
                                 pd.Timestamp("2025-12-18"), "10-Q", "a")]])
    assert latest(df) == {"2025Q4": 13_643}
    spec = next(s for s in h.SPECS if s.key == "rev_mu")
    spec = catalog.Spec(**{**spec.__dict__, "fetch": lambda: None})
    table = observations.new_rows(spec, df[["period", "value", "known_from"]], observations._empty())
    checks = warehouse.run_checks(warehouse.connect(table, [spec]))
    assert all(v.empty for v in checks.values()), {k: v for k, v in checks.items() if len(v)}
