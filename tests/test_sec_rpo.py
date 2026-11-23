"""RPO from XBRL instances: instant parsing with typed dimensions, total and timing split, stock vintages.

Synthetic instance documents and facts, no network. Values in USD millions (x 1e6 in the facts).
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import catalog, observations, warehouse
from ai_tracker.series import sec_rpo as rpo_series
from ai_tracker.series.sec_segments import DefinitionBreakError
from ai_tracker.sources import sec, sec_rpo
from ai_tracker.sources.sec_segment import Filing

M = 1e6
AXIS = "us-gaap:" + sec_rpo.START_AXIS


def context(cid, instant, explicit=(), typed=None, start=None):
    members = "".join(f'<xbrldi:explicitMember dimension="{a}">{m}</xbrldi:explicitMember>' for a, m in explicit)
    if typed:
        members += (f'<xbrldi:typedMember dimension="{AXIS}"><us-gaap:{sec_rpo.START_AXIS.replace("Axis", "Domain")}>'
                    f"{typed}</us-gaap:{sec_rpo.START_AXIS.replace('Axis', 'Domain')}></xbrldi:typedMember>")
    segment = f"<xbrli:segment>{members}</xbrli:segment>" if members else ""
    period = (f"<xbrli:startDate>{start}</xbrli:startDate><xbrli:endDate>{instant}</xbrli:endDate>" if start
              else f"<xbrli:instant>{instant}</xbrli:instant>")
    return (f'<xbrli:context id="{cid}"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">1</xbrli:identifier>'
            f"{segment}</xbrli:entity><xbrli:period>{period}</xbrli:period></xbrli:context>")


def instance(contexts, facts) -> bytes:
    body = "".join(contexts) + ('<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>'
                                '<xbrli:unit id="pure"><xbrli:measure>xbrli:pure</xbrli:measure></xbrli:unit>')
    for concept, cid, val, *unit in facts:
        unit_attr = "" if unit and unit[0] is None else f' unitRef="{unit[0] if unit else "usd"}"'
        body += f'<{concept} contextRef="{cid}"{unit_attr}>{val}</{concept}>'
    return ('<?xml version="1.0"?><xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" '
            'xmlns:xbrldi="http://xbrl.org/2006/xbrldi" xmlns:us-gaap="http://fasb.org/us-gaap/2024" '
            'xmlns:msft="http://www.microsoft.com/20260930" xmlns:iso4217="http://www.xbrl.org/2003/iso4217">'
            + body + "</xbrli:xbrl>").encode()


RPO, PCT, P1 = (f"us-gaap:{c}" for c in (sec_rpo.RPO, sec_rpo.PCT, sec_rpo.PERIOD1))
COMMERCIAL = ("us-gaap:MajorCustomersAxis", "msft:CommercialCustomersMember")

# Microsoft-style: undimensioned total, a customer part, a 12-month first bucket and its customer twin.
MSFT_DOC = instance(
    [context("i", "2026-09-30"), context("c", "2026-09-30", [COMMERCIAL]),
     context("b1", "2026-09-30", typed="2026-10-01"), context("cb1", "2026-09-30", [COMMERCIAL], typed="2026-10-01"),
     context("dur", "2026-09-30", start="2026-07-01")],
    [(RPO, "i", 683_000 * M), (RPO, "c", 677_000 * M), (PCT, "b1", "0.30", "pure"), (PCT, "cb1", "0.25", "pure"),
     (P1, "b1", "P12M", None), (P1, "cb1", "P12M", None), (RPO, "dur", 1 * M)])

# Oracle-style: 12-month bucket tagged with a stale start date (a real slip), then two later buckets.
ORCL_DOC = instance(
    [context("i", "2026-02-28"), context("b1", "2026-02-28", typed="2025-12-01"),
     context("b2", "2026-02-28", typed="2026-12-01"), context("b3", "2026-02-28", typed="2028-12-01")],
    [(RPO, "i", 552_600 * M), (PCT, "b1", "0.12", "pure"), (P1, "b1", "P12M", None),
     (PCT, "b2", "0.31", "pure"), (P1, "b2", "P2Y", None), (PCT, "b3", "0.35", "pure")])

# Amazon-style: the total carries only the start-date axis (one bucket), Period1 = weighted average life.
AMZN_DOC = instance(
    [context("b", "2026-09-30", typed="2026-10-01"),
     context("oai", "2026-03-31", [("us-gaap:MajorCustomersAxis", "amzn:OpenAIMember")], typed="2026-10-01")],
    [(RPO, "b", 578_000 * M), (P1, "b", "P6Y1M6D", None), (RPO, "oai", 38_000 * M)])


def filing(filed, form="10-Q"):
    return Filing(1, f"acc-{filed}", filed, form)


def fact(instant, val, filed, form="10-Q"):
    t = pd.Timestamp(instant)
    return sec.Fact(t, t, val * M, pd.Timestamp(filed), form, f"acc-{filed}")


def latest(df):
    return df.sort_values("known_from").groupby("period")["value"].last().round(3).to_dict()


def test_parse_instants_reads_typed_dimensions_and_skips_durations():
    facts = sec_rpo.parse_instants(MSFT_DOC)
    assert len(facts) == 6  # the duration-context fact is not a balance
    b1 = [f for f in facts if f.dims == frozenset({(sec_rpo.START_AXIS, "2026-10-01")})]
    assert {(f.concept, f.text, f.unit) for f in b1} == {(sec_rpo.PCT, "0.30", "pure"), (sec_rpo.PERIOD1, "P12M", "")}


def test_months():
    assert [sec_rpo.months(d) for d in ("P12M", "P1Y", "P2Y", "P48M", "P6Y1M6D", "")] == [12, 12, 24, 48, None, None]


def test_total_and_near_split_use_company_total_only():
    got = sec_rpo.filing_facts(filing("2026-10-28"), sec_rpo.parse_instants(MSFT_DOC), horizon=12)
    assert [(str(f.end.date()), f.val / M) for f in got["total"]] == [("2026-09-30", 683_000)]
    assert got["near"][0].val / M == pytest.approx(204_900)  # 30 % of the total, not the customer part's 25 %
    assert got["later"][0].val / M == pytest.approx(478_100)
    assert all(f.filed == pd.Timestamp("2026-10-28") and f.start == f.end for f in got["total"] + got["near"])


def test_first_bucket_is_the_earliest_start_even_if_mis_dated():
    got = sec_rpo.filing_facts(filing("2026-03-11"), sec_rpo.parse_instants(ORCL_DOC), horizon=12)
    assert got["near"][0].val / M == pytest.approx(0.12 * 552_600)


def test_horizon_change_fails():
    with pytest.raises(sec_rpo.HorizonError, match="acc-2026-03-11"):
        sec_rpo.filing_facts(filing("2026-03-11"), sec_rpo.parse_instants(ORCL_DOC), horizon=24)


def test_later_buckets_only_give_no_share():
    doc = instance([context("i", "2026-02-28"), context("b2", "2026-02-28", typed="2026-12-01")],
                   [(RPO, "i", 100 * M), (PCT, "b2", "0.31", "pure"), (P1, "b2", "P24M", None)])
    assert sec_rpo.filing_facts(filing("2026-03-11"), sec_rpo.parse_instants(doc), horizon=24)["near"] == []


def test_undimensioned_shares_need_a_declaration():
    doc = instance([context("i", "2018-08-31")], [(RPO, "i", 31_300 * M), (PCT, "i", "0.64", "pure")])
    facts = sec_rpo.parse_instants(doc)
    assert sec_rpo.filing_facts(filing("2018-09-19"), facts, 12)["near"] == []
    assert sec_rpo.filing_facts(filing("2018-09-19"), facts, 12, undimensioned=True)["near"][0].val / M == \
        pytest.approx(0.64 * 31_300)
    own = instance([context("i", "2017-12-31")], [(RPO, "i", 61_000 * M), (
        f"msft:{sec_rpo.MSFT_PCT_12M}", "i", "0.60", "pure")])
    assert sec_rpo.filing_facts(filing("2018-01-31"), sec_rpo.parse_instants(own), 12)["near"][0].val / M == \
        pytest.approx(36_600)


def test_start_date_only_total_amazon():
    got = sec_rpo.filing_facts(filing("2026-10-30"), sec_rpo.parse_instants(AMZN_DOC), horizon=None)
    assert [(str(f.end.date()), f.val / M) for f in got["total"]] == [("2026-09-30", 578_000)]  # not the customer part
    assert got["near"] == [] and got["later"] == []


def test_stock_vintages_no_differencing_and_restatement_is_a_vintage():
    facts = [fact("2026-03-31", 100, "2026-04-30"), fact("2026-06-30", 120, "2026-07-30"),
             fact("2026-03-31", 100.2, "2026-07-30"),  # rounding: no new row
             fact("2026-03-31", 104, "2026-10-28", "10-Q/A")]  # restated: new vintage
    df = sec_rpo.stock_vintages(facts)
    assert latest(df) == {"2026Q1": 104, "2026Q2": 120}  # balances, not differences
    q1 = df[df["period"] == "2026Q1"]
    assert list(q1["known_from"].dt.strftime("%Y-%m-%d")) == ["2026-04-30", "2026-10-28"]
    assert list(q1["value"]) == [100, 104]


def test_oracle_balance_date_maps_to_its_calendar_quarter_and_passes_leakage_check():
    df = sec_rpo.stock_vintages([fact("2025-11-30", 523_300, "2025-12-11"), fact("2026-02-28", 552_600, "2026-03-11")])
    assert latest(df) == {"2025Q4": 523_300, "2026Q1": 552_600}
    spec = next(s for s in rpo_series.SPECS if s.key == "rpo_orcl")
    assert spec.lag_days == -31
    spec = catalog.Spec(**{**spec.__dict__, "fetch": lambda: None})
    table = observations.new_rows(spec, df[["period", "value", "known_from"]], observations._empty())
    checks = warehouse.run_checks(warehouse.connect(table, [spec]))
    assert all(v.empty for v in checks.values()), {k: v for k, v in checks.items() if len(v)}


def test_undeclared_definition_break_fails():
    c = rpo_series.Company("x", "X", 1, "2020-01-01", None)
    facts = [fact("2026-03-31", 100, "2026-04-30"), fact("2026-03-31", 110, "2026-07-30")]  # +10 % recast
    with pytest.raises(DefinitionBreakError, match="2026-07-30"):
        rpo_series.checked_breaks(c, facts)


def test_hyp4_exists_only_when_all_four_have_filed(monkeypatch):
    frames = {k: pd.DataFrame({"period": ["2026Q3"], "value": [v], "known_from": [pd.Timestamp(d)]})
              for k, v, d in [("msft", 683_000, "2026-10-28"), ("googl", 567_700, "2026-10-29"),
                              ("amzn", 578_000, "2026-10-30"), ("orcl", 664_000, "2026-09-11")]}
    monkeypatch.setattr(rpo_series, "company_series", lambda key, part="total": frames[key])
    rpo_series.hyp4_series.cache_clear()
    try:
        df = rpo_series.hyp4_series()
    finally:
        rpo_series.hyp4_series.cache_clear()
    assert df.to_dict("records") == [{"period": "2026Q3", "value": 2_492_700, "known_from": pd.Timestamp("2026-10-30")}]


def test_catalog_entries():
    keys = {s.key for s in rpo_series.SPECS}
    assert keys == {"rpo_msft", "rpo_msft_12m", "rpo_msft_after12m", "rpo_googl", "rpo_googl_24m",
                    "rpo_googl_after24m", "rpo_amzn", "rpo_orcl", "rpo_orcl_12m", "rpo_orcl_after12m",
                    "rpo_crwv", "rpo_crwv_24m", "rpo_crwv_after24m", "rpo_hyp4"}
    assert catalog.validate(rpo_series.SPECS) == []
    assert all(s.freq == "Q" and s.branch == "G4" and s.publish and s.revised for s in rpo_series.SPECS)
