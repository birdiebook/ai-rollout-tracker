"""Depreciation and PP&E from SEC XBRL: YTD differencing, Q4 = FY - 9M, restatements, splices, balances, aggregates.

Synthetic companyfacts-shaped fixtures and instance documents, no network. Values in USD millions (x 1e6 in facts).
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import catalog, warehouse
from ai_tracker.series import sec_avskrivningar as m
from ai_tracker.series.sec_segments import DefinitionBreakError
from ai_tracker.sources import sec, sec_custom, sec_segment

M = 1e6
OCF = "NetCashProvidedByUsedInOperatingActivities"


def fact(start, end, val, filed, form="10-Q", accn=None):
    return {"start": start, "end": end, "val": int(val * M), "filed": filed, "form": form,
            "accn": accn or f"acc-{filed}", "fy": 0, "fp": "x"}


def inst(end, val, filed, form="10-Q", accn=None):
    return {"end": end, "val": int(val * M), "filed": filed, "form": form, "accn": accn or f"acc-{filed}"}


def companyfacts(**tags):
    return {"facts": {"us-gaap": {t: {"units": {"USD": rows}} for t, rows in tags.items()}}}


def latest(df):
    return df.sort_values("known_from").groupby("period")["value"].last().round(3).to_dict()


def first_known(df):
    return {p: str(d.date()) for p, d in df.groupby("period")["known_from"].min().items()}


@pytest.fixture(autouse=True)
def clear_caches():
    for f in (m.flow_series, m.balance_series, m.fiscal_quarters, m.hyp4_series, m.aws_series):
        f.cache_clear()
    yield
    for f in (m.flow_series, m.balance_series, m.fiscal_quarters, m.hyp4_series, m.aws_series):
        f.cache_clear()


def use(monkeypatch, by_cik: dict[int, dict]):
    monkeypatch.setattr(m, "_cf", lambda cik: by_cik.get(cik, {"facts": {}}))


# A calendar year of cash-flow D&A: YTD in 10-Qs, the full year in the 10-K.
DEP_2025 = [
    fact("2025-01-01", "2025-03-31", 10, "2025-04-30"),
    fact("2025-01-01", "2025-06-30", 21, "2025-07-30"),
    fact("2025-01-01", "2025-09-30", 33, "2025-10-30"),
    fact("2025-01-01", "2025-12-31", 46, "2026-02-01", "10-K"),
]


def test_ytd_differencing_and_q4_from_full_year(monkeypatch):
    use(monkeypatch, {m.META: companyfacts(DepreciationDepletionAndAmortization=DEP_2025)})
    monkeypatch.setitem(m.COMPANIES, "meta", m.COMPANIES["meta"].__class__(
        **{**m.COMPANIES["meta"].__dict__, "dep": m.Flow(tags=(("DepreciationDepletionAndAmortization",),))}))
    df = m.flow_series("dep", "meta")
    assert latest(df) == {"2025Q1": 10, "2025Q2": 11, "2025Q3": 12, "2025Q4": 13}
    # Q4 = FY - 9M, known only with the 10-K; no value before its period ends
    assert first_known(df) == {"2025Q1": "2025-04-30", "2025Q2": "2025-07-30", "2025Q3": "2025-10-30",
                               "2025Q4": "2026-02-01"}
    assert all(k >= pd.Period(p, "Q").end_time.normalize() for p, k in zip(df.period, df.known_from))


def _meta_with(flow):
    c = m.COMPANIES["meta"]
    return c.__class__(**{**c.__dict__, "dep": flow})


def test_small_restatement_is_a_vintage_and_large_one_must_be_declared(monkeypatch):
    base = [fact(r["start"], r["end"], r["val"] / M * 100, r["filed"], r["form"]) for r in DEP_2025]
    rows = base + [fact("2025-01-01", "2025-03-31", 1010, "2026-04-30")]  # 1% restated comparative
    use(monkeypatch, {m.META: companyfacts(DepreciationDepletionAndAmortization=rows)})
    monkeypatch.setitem(m.COMPANIES, "meta", _meta_with(m.Flow(tags=(("DepreciationDepletionAndAmortization",),))))
    df = m.flow_series("dep", "meta")
    q1 = df[df.period == "2025Q1"].sort_values("known_from")
    assert list(q1.value.round(3)) == [1000, 1010] and str(q1.known_from.iloc[-1].date()) == "2026-04-30"

    m.flow_series.cache_clear()
    big = base + [fact("2025-01-01", "2025-03-31", 800, "2026-04-30")]  # -20%: a reclassification
    use(monkeypatch, {m.META: companyfacts(DepreciationDepletionAndAmortization=big)})
    with pytest.raises(DefinitionBreakError, match="2026-04-30"):
        m.flow_series("dep", "meta")
    m.flow_series.cache_clear()
    monkeypatch.setitem(m.COMPANIES, "meta", _meta_with(
        m.Flow(tags=(("DepreciationDepletionAndAmortization",),), breaks=("2026-04-30",))))
    assert latest(m.flow_series("dep", "meta"))["2025Q1"] == 800  # declared: a new vintage under the same key


def test_tag_splice_per_quarter_and_regime_cut(monkeypatch):
    # Old tag carries 2018, the new one 2019 (and a different-definition full year 2018 that must not be used).
    old = [fact("2018-01-01", "2018-03-31", 5, "2018-04-30"), fact("2018-01-01", "2018-06-30", 11, "2018-07-30"),
           fact("2018-01-01", "2018-09-30", 18, "2018-10-30"), fact("2018-01-01", "2018-12-31", 26, "2019-02-01", "10-K")]
    new = [fact("2018-01-01", "2018-12-31", 99, "2019-02-01", "10-K"),
           fact("2019-01-01", "2019-03-31", 9, "2019-04-30"), fact("2019-01-01", "2019-06-30", 19, "2019-07-30")]
    use(monkeypatch, {m.META: companyfacts(DepreciationAndAmortization=old, DepreciationDepletionAndAmortization=new)})
    monkeypatch.setitem(m.COMPANIES, "meta", _meta_with(
        m.Flow(tags=(("DepreciationAndAmortization", "DepreciationDepletionAndAmortization"),))))
    got = latest(m.flow_series("dep", "meta"))
    assert got == {"2018Q1": 5, "2018Q2": 6, "2018Q3": 7, "2018Q4": 8, "2019Q1": 9, "2019Q2": 10}

    m.flow_series.cache_clear()  # one definition regime: only periods from 2019 (Amazon's ASC 842 line)
    monkeypatch.setitem(m.COMPANIES, "meta", _meta_with(
        m.Flow(tags=(("DepreciationAndAmortization", "DepreciationDepletionAndAmortization"),),
               first_start="2019-01-01")))
    assert latest(m.flow_series("dep", "meta")) == {"2019Q1": 9, "2019Q2": 10}


def test_oracle_sum_uses_both_rows_of_the_same_filing(monkeypatch):
    dep = [fact("2025-06-01", "2025-08-31", 1, "2025-09-10", accn="q1"),
           fact("2025-06-01", "2025-11-30", 3, "2025-12-10", accn="q2")]
    amort = [fact("2025-06-01", "2025-08-31", 0.5, "2025-09-10", accn="q1"),
             fact("2025-06-01", "2025-11-30", 0.9, "2025-12-10", accn="q2"),
             fact("2025-06-01", "2026-02-28", 1.2, "2026-03-10", accn="q3")]  # no Depreciation in q3: no sum
    use(monkeypatch, {m.ORCL: companyfacts(Depreciation=dep, AmortizationOfIntangibleAssets=amort)})
    df = m.flow_series("dep", "orcl")
    # Jun-Aug -> Q3, Sep-Nov -> Q4 (midpoint rule), filed before the calendar quarter ends (lag_days -31)
    assert latest(df) == {"2025Q3": 1.5, "2025Q4": 2.4}
    assert first_known(df) == {"2025Q3": "2025-09-10", "2025Q4": "2025-12-10"}
    assert latest(m.flow_series("dep_ppe", "orcl")) == {"2025Q3": 1, "2025Q4": 2}


# ------------------------------------------------------------------ balances

ORCL_OCF = [fact("2025-06-01", "2025-08-31", 1, "2025-09-10"), fact("2025-06-01", "2025-11-30", 2, "2025-12-10"),
            fact("2025-06-01", "2026-02-28", 3, "2026-03-10"), fact("2025-06-01", "2026-05-31", 4, "2026-06-20", "10-K")]


def test_instant_balances_map_to_fiscal_quarters(monkeypatch):
    net = [inst("2025-08-31", 100, "2025-09-10"), inst("2025-11-30", 110, "2025-12-10"),
           inst("2025-10-15", 999, "2025-12-10"),  # not a fiscal quarter end (e.g. an acquisition date): dropped
           inst("2025-08-31", 101, "2026-09-10")]  # restated comparative a year later: new vintage
    use(monkeypatch, {m.ORCL: companyfacts(**{OCF: ORCL_OCF, m.NET_B: net})})
    df = m.balance_series("net", "orcl")
    assert latest(df) == {"2025Q3": 101, "2025Q4": 110}
    assert first_known(df) == {"2025Q3": "2025-09-10", "2025Q4": "2025-12-10"}


MSFT_OCF = [fact("2025-07-01", "2025-09-30", 1, "2025-10-29"), fact("2025-07-01", "2025-12-31", 2, "2026-01-28")]


def test_gross_is_net_plus_accumulated_from_the_same_filing_and_family(monkeypatch):
    tags = {
        OCF: MSFT_OCF,
        m.NET_B: [inst("2025-09-30", 300, "2025-10-29", accn="a"), inst("2025-12-31", 320, "2026-01-28", accn="b")],
        m.ACC_B: [inst("2025-09-30", 100, "2025-10-29", accn="a"), inst("2025-12-31", 110, "2026-01-28", accn="b")],
        # A gross tag that is a subtotal must not be used
        "PropertyPlantAndEquipmentGross": [inst("2025-12-31", 333, "2026-01-28", accn="b")],
        # Family A (with finance leases) wins where it has both parts; its net alone (no accumulated) gives no gross
        m.NET_A: [inst("2025-12-31", 320, "2026-01-28", accn="b"), inst("2025-09-30", 300, "2025-10-29", accn="a")],
        m.ACC_A: [inst("2025-12-31", 110, "2026-01-28", accn="b")],
    }
    use(monkeypatch, {m.MSFT: companyfacts(**tags)})
    assert latest(m.balance_series("gross", "msft")) == {"2025Q3": 400, "2025Q4": 430}
    assert latest(m.balance_series("net", "msft")) == {"2025Q3": 300, "2025Q4": 320}


def test_custom_balance_fills_a_quarter_from_the_instance(monkeypatch):
    goog = m.COMPANIES["googl"]
    tags = {OCF: [fact("2020-01-01", "2020-03-31", 1, "2020-04-29"), fact("2020-01-01", "2020-06-30", 2, "2020-07-31")],
            m.NET_A: [inst("2020-06-30", 79, "2020-07-31")]}
    use(monkeypatch, {m.GOOGL: companyfacts(**tags)})
    filing = sec_segment.Filing(m.GOOGL, "acc-q1", "2020-04-29", "10-Q")
    doc = _instance([_ctx("i", None, "2020-03-31")],
                    [(f"goog:{goog.custom_balances[0].concepts[0]}", "i", 77 * M)])
    monkeypatch.setattr(sec_custom, "_filings", lambda cik, since, until: ((filing, doc),))
    sec_custom.instant_facts.cache_clear()
    try:
        assert latest(m.balance_series("net", "googl")) == {"2020Q1": 77, "2020Q2": 79}
    finally:
        sec_custom.instant_facts.cache_clear()


# ------------------------------------------------------------------ instances (company-specific concepts)


def _ctx(cid, start, end, dims=()):
    members = "".join(f'<xbrldi:explicitMember dimension="{a}">{v}</xbrldi:explicitMember>' for a, v in dims)
    segment = f"<xbrli:segment>{members}</xbrli:segment>" if dims else ""
    period = (f"<xbrli:startDate>{start}</xbrli:startDate><xbrli:endDate>{end}</xbrli:endDate>" if start
              else f"<xbrli:instant>{end}</xbrli:instant>")
    return (f'<xbrli:context id="{cid}"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">1'
            f"</xbrli:identifier>{segment}</xbrli:entity><xbrli:period>{period}</xbrli:period></xbrli:context>")


def _instance(contexts, facts) -> bytes:
    body = "".join(contexts) + '<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>'
    for concept, cid, val in facts:
        body += f'<{concept} contextRef="{cid}" unitRef="usd" decimals="-6">{val}</{concept}>'
    return ('<?xml version="1.0"?><xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" '
            'xmlns:xbrldi="http://xbrl.org/2006/xbrldi" xmlns:us-gaap="http://fasb.org/us-gaap/2024" '
            'xmlns:msft="http://www.microsoft.com/20250930" xmlns:goog="http://www.google.com/20200331" '
            'xmlns:iso4217="http://www.xbrl.org/2003/iso4217">' + body + "</xbrli:xbrl>").encode()


def test_plain_facts_keep_only_undimensioned_contexts_and_skip_10k_quarters():
    doc = _instance(
        [_ctx("q", "2025-10-01", "2025-12-31"), _ctx("ytd", "2025-07-01", "2025-12-31"),
         _ctx("seg", "2025-10-01", "2025-12-31", [("StatementBusinessSegmentsAxis", "msft:CloudMember")])],
        [("msft:DepreciationAmortizationAndOther", "q", 9_000 * M),
         ("msft:DepreciationAmortizationAndOther", "ytd", 17_000 * M),
         ("msft:DepreciationAmortizationAndOther", "seg", 1 * M)])
    dims = sec_segment.parse_instance(doc, {"DepreciationAmortizationAndOther"})
    q = sec_custom.plain_facts(dims, sec_segment.Filing(1, "acc-1", "2026-01-28", "10-Q"),
                               ["DepreciationAmortizationAndOther"])
    assert [(str(f.start.date()), f.val / M, str(f.filed.date())) for f in q] == [
        ("2025-07-01", 17_000, "2026-01-28"), ("2025-10-01", 9_000, "2026-01-28")]
    k = sec_custom.plain_facts(dims, sec_segment.Filing(1, "acc-2", "2026-07-29", "10-K"),
                               ["DepreciationAmortizationAndOther"])
    assert [f.val / M for f in k] == [17_000]  # the 3-month fact in a 10-K is ignored


def test_microsoft_line_from_instances(monkeypatch):
    rows = [sec.Fact(pd.Timestamp("2025-07-01"), pd.Timestamp("2025-09-30"), 8 * M, pd.Timestamp("2025-10-29"), "10-Q", "a"),
            sec.Fact(pd.Timestamp("2025-07-01"), pd.Timestamp("2025-12-31"), 17 * M, pd.Timestamp("2026-01-28"), "10-Q", "b"),
            sec.Fact(pd.Timestamp("2025-07-01"), pd.Timestamp("2026-06-30"), 40 * M, pd.Timestamp("2026-07-29"), "10-K", "c"),
            sec.Fact(pd.Timestamp("2025-07-01"), pd.Timestamp("2026-03-31"), 27 * M, pd.Timestamp("2026-04-29"), "10-Q", "d")]
    seen = {}

    def fake(cik, concepts, since, until):
        seen["args"] = (cik, concepts)
        return tuple(rows)

    monkeypatch.setattr(sec_custom, "duration_facts", fake)
    monkeypatch.setitem(m.COMPANIES, "msft", m.COMPANIES["msft"].__class__(
        **{**m.COMPANIES["msft"].__dict__, "dep": m.Flow(custom=m.COMPANIES["msft"].dep.custom)}))
    df = m.flow_series("dep", "msft")
    assert seen["args"] == (m.MSFT, ("DepreciationAmortizationAndOther",))
    # June fiscal year: Jul-Sep = 2025Q3; Q4 FY = Apr-Jun 2026 = FY - 9M
    assert latest(df) == {"2025Q3": 8, "2025Q4": 9, "2026Q1": 10, "2026Q2": 13}


def test_summed_instants_pair_by_filing():
    a = [m.sec_instant.Instant(pd.Timestamp("2025-12-31"), 3.0, pd.Timestamp("2026-02-01"), "10-K", "x"),
         m.sec_instant.Instant(pd.Timestamp("2025-12-31"), 3.0, pd.Timestamp("2026-04-30"), "10-Q", "y")]
    b = [m.sec_instant.Instant(pd.Timestamp("2025-12-31"), 1.0, pd.Timestamp("2026-02-01"), "10-K", "x")]
    got = sec_custom.summed_instants([a, b])
    assert [(g.val, g.accn) for g in got] == [(4.0, "x")]


# ------------------------------------------------------------------ aggregates and catalog


def test_hyp4_exists_after_the_fourth_filing_and_is_dated_by_it(monkeypatch):
    def frame(rows):
        return pd.DataFrame([(p, v, pd.Timestamp(k)) for p, v, k in rows], columns=["period", "value", "known_from"])

    parts = {"msft": frame([("2026Q3", 11, "2026-10-28")]), "googl": frame([("2026Q3", 8, "2026-10-29")]),
             "amzn": frame([("2026Q3", 21, "2026-10-30"), ("2026Q2", 20, "2026-07-31")]),
             "meta": frame([("2026Q3", 7, "2026-10-22"), ("2026Q3", 8, "2027-10-21")])}
    monkeypatch.setattr(m, "company_series", lambda measure, c: parts[c])
    df = m.hyp4_series("dep")
    assert list(df.itertuples(index=False, name=None)) == [
        ("2026Q3", 47.0, pd.Timestamp("2026-10-30")), ("2026Q3", 48.0, pd.Timestamp("2027-10-21"))]


def test_catalog_entries():
    specs = catalog.by_key(m.SPECS)
    expected = ({f"{p}_{c}" for p in ("dep", "dep_ppe", "ppe_net") for c in m.COMPANIES}
                | {f"ppe_gross_{c}" for c in ("msft", "googl", "meta", "crwv")}
                | {"dep_hyp4", "dep_ppe_hyp4", "ppe_net_hyp4", "dep_aws"})
    assert set(specs) == expected
    assert not {"ppe_gross_amzn", "ppe_gross_orcl", "ppe_gross_hyp4"} & set(specs)
    for s in specs.values():
        assert (s.branch, s.unit, s.freq, s.publish, s.revised) == ("G5", "MUSD", "Q", True, True)
        assert s.license.startswith("public:") and s.note
    assert specs["dep_orcl"].lag_days == -31 and specs["ppe_net_orcl"].lag_days == -31
    assert catalog.validate(m.SPECS) == []
    assert set(catalog.by_key()) >= expected  # discovered by the catalog


def test_release_dated_output_passes_data_tests(monkeypatch):
    use(monkeypatch, {m.ORCL: companyfacts(**{OCF: ORCL_OCF, m.NET_B: [inst("2025-08-31", 100, "2025-09-10"),
                                                                        inst("2025-11-30", 110, "2025-12-10")],
                                             "Depreciation": [f for f in ORCL_OCF],
                                             "AmortizationOfIntangibleAssets": [f for f in ORCL_OCF]})})
    rows = []
    for key, df in (("dep_orcl", m.flow_series("dep", "orcl")), ("ppe_net_orcl", m.balance_series("net", "orcl"))):
        d = df[["period", "value", "known_from"]].copy()
        d.insert(0, "series", key)
        rows.append(d)
    table = pd.concat(rows, ignore_index=True)
    table["freq"] = "Q"
    table["source"] = "release"
    table["fetched_at"] = pd.Timestamp("2026-11-24")
    checks = warehouse.run_checks(warehouse.connect(table, list(m.SPECS)))
    for name in ("unique_key", "known_from_after_period_end", "no_gaps", "freq_matches_catalog"):
        assert checks[name].empty, name


def test_aws_quarters_start_when_10q_segment_facts_start(monkeypatch):
    def f(start, end, val, filed, form="10-Q"):
        return sec.Fact(pd.Timestamp(start), pd.Timestamp(end), val * M, pd.Timestamp(filed), form, f"acc-{filed}")

    facts = [f("2023-01-01", "2023-12-31", 12, "2024-02-02", "10-K"),  # full years only before 2025
             f("2024-01-01", "2024-12-31", 14, "2025-02-07", "10-K"),
             f("2025-01-01", "2025-03-31", 4, "2025-05-02"), f("2024-01-01", "2024-03-31", 3, "2025-05-02"),
             f("2025-01-01", "2025-06-30", 9, "2025-08-01"), f("2024-01-01", "2024-06-30", 6.5, "2025-08-01"),
             f("2025-01-01", "2025-09-30", 15, "2025-10-31"), f("2024-01-01", "2024-09-30", 10, "2025-10-31")]
    seen = {}

    def fake(ciks, since, concepts, members):
        seen["args"] = (ciks, concepts, members)
        return facts

    monkeypatch.setattr(sec_segment, "member_facts", fake)
    df = m.aws_series()
    assert seen["args"] == ((m.AMZN,), m.AWS_CONCEPTS, m.AWS_MEMBERS)
    assert latest(df) == {"2024Q1": 3, "2024Q2": 3.5, "2024Q3": 3.5, "2024Q4": 4, "2025Q1": 4, "2025Q2": 5,
                          "2025Q3": 6}
    # 2024 quarters are known only from the 2025 comparatives; Q4 2024 = FY (10-K) - 9M (10-Q 2025-10-31)
    assert first_known(df)["2024Q1"] == "2025-05-02" and first_known(df)["2024Q4"] == "2025-10-31"


# P1's CoreWeave rounding test passed without the filter (R14, A-6a): the filter is tested by
# tests/test_r14_avskrivningar.py::test_coreweave_rounding_filter_drops_a_difference_of_rounded_comparatives.


# ------------------------------------------------------------------ restatements through year-to-date totals (R14 R-1)


def F(start, end, val, filed, form="10-Q", accn=None):
    return sec.Fact(pd.Timestamp(start), pd.Timestamp(end), val * M, pd.Timestamp(filed), form, accn or f"acc-{filed}")


def implied(facts):
    return [(str(f.start.date()), str(f.end.date()), round(f.val / M, 3), str(f.filed.date()))
            for f in sec_custom.implied_by_ytd(facts)[len(facts):]]


def test_ytd_minus_three_months_restates_the_previous_quarter_of_the_same_filing():
    rows = [F("2025-07-01", "2025-09-30", 1234, "2025-10-29"),
            F("2025-07-01", "2025-12-31", 2345, "2026-01-28"), F("2025-10-01", "2025-12-31", 1234, "2026-01-28")]
    assert implied(rows) == [("2025-07-01", "2025-09-30", 1111, "2026-01-28")]
    # dated to the filing and carrying its accession, so it is one version of that filing
    assert sec_custom.implied_by_ytd(rows)[-1].accn == "acc-2026-01-28"


def test_implied_value_needs_one_filing_an_earlier_value_and_more_than_rounding():
    q1 = F("2025-07-01", "2025-09-30", 1234, "2025-10-29")
    ytd, q2 = F("2025-07-01", "2025-12-31", 2345, "2026-01-28"), F("2025-10-01", "2025-12-31", 1234, "2026-01-28")
    # YTD and 3-month figure from different filings: nothing implied
    assert implied([q1, ytd, F("2025-10-01", "2025-12-31", 1234, "2026-02-15")]) == []
    # the period was never filed: no new period (coverage is unchanged)
    assert implied([ytd, q2]) == []
    # the filing reports the period itself: the reported value is used as it is
    assert implied([q1, ytd, q2, F("2025-07-01", "2025-09-30", 1201, "2026-01-28")]) == []
    # 10-K: its 3-month figures are the unaudited quarterly note
    assert implied([F("2025-07-01", "2026-03-31", 3456, "2026-04-29"),
                    F("2025-07-01", "2026-06-30", 4567, "2026-07-29", "10-K"),
                    F("2026-04-01", "2026-06-30", 1234, "2026-07-29", "10-K")]) == []
    # millions: a difference of two rounded figures that is 1 off is rounding (Microsoft 20,116 - 7,734 = 12,382)
    assert implied([F("2024-07-01", "2024-12-31", 12383, "2026-01-28"), F("2024-07-01", "2025-03-31", 20116, "2026-04-29"),
                    F("2025-01-01", "2025-03-31", 7734, "2026-04-29")]) == []


def test_rounding_tolerance_follows_the_reporting_unit():
    """Meta tags Depreciation in 0.01 bn: 6,670 - 3,350 = 3,320 against 3,330 filed is rounding, 3,150 is not."""
    q1 = F("2025-01-01", "2025-03-31", 3330, "2025-04-30")
    assert implied([q1, F("2025-01-01", "2025-06-30", 6670, "2025-07-30"), F("2025-04-01", "2025-06-30", 3350, "2025-07-30")]) == []
    assert implied([q1, F("2025-01-01", "2025-06-30", 6500, "2025-07-30"),
                    F("2025-04-01", "2025-06-30", 3350, "2025-07-30")]) == [("2025-01-01", "2025-03-31", 3150, "2025-07-30")]
    # in millions the same 10 MUSD gap is a revision
    assert implied([F("2025-01-01", "2025-03-31", 3331, "2025-04-30"), F("2025-01-01", "2025-06-30", 6671, "2025-07-30"),
                    F("2025-04-01", "2025-06-30", 3351, "2025-07-30")]) == [("2025-01-01", "2025-03-31", 3320, "2025-07-30")]


def test_implied_restatement_is_a_vintage_and_passes_the_stop_rule(monkeypatch):
    rows = (F("2025-07-01", "2025-09-30", 1234, "2025-10-29"),
            F("2025-07-01", "2025-12-31", 2345, "2026-01-28"), F("2025-10-01", "2025-12-31", 1234, "2026-01-28"))
    monkeypatch.setattr(sec_custom, "duration_facts", lambda cik, concepts, since, until: rows)
    msft = m.COMPANIES["msft"]
    monkeypatch.setitem(m.COMPANIES, "msft", msft.__class__(**{**msft.__dict__, "dep": m.Flow(custom=msft.dep.custom)}))
    with pytest.raises(DefinitionBreakError, match="2026-01-28"):  # -10% only through the total: still a break
        m.flow_series("dep", "msft")
    m.flow_series.cache_clear()
    monkeypatch.setitem(m.COMPANIES, "msft", msft.__class__(
        **{**msft.__dict__, "dep": m.Flow(custom=msft.dep.custom, breaks=("2026-01-28",))}))
    df = m.flow_series("dep", "msft")
    q = df[df.period == "2025Q3"].sort_values("known_from")
    assert [(v, str(k.date())) for v, k in zip(q.value.round(3), q.known_from)] == [(1234, "2025-10-29"), (1111, "2026-01-28")]
