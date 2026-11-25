"""Track S2: power, cooling, grid and data-centre companies from SEC XBRL (series/sec_stack_kraft.py).

Synthetic facts and companyfacts documents, no network. Values in USD millions (x 1e6 in the facts).
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import catalog, licenses
from ai_tracker.series import sec as sec_series
from ai_tracker.series import sec_stack_kraft as sk
from ai_tracker.series.sec_segments import DefinitionBreakError
from ai_tracker.sources import sec, sec_rpo
from ai_tracker.sources.sec_segment import DimFact, Filing

M = 1e6
T = pd.Timestamp
RFCC = sk.RFCC


def filing(filed, form="10-Q", cik=sk.GEV):
    return Filing(cik, f"acc-{filed}", filed, form)


def dim(start, end, val, dims, concept=RFCC):
    return DimFact(concept, T(start), T(end), frozenset(dims), val * M, "USD")


def latest(df):
    return df.sort_values("known_from").groupby("period")["value"].last().to_dict()


def first_known(df):
    return {p: str(d.date()) for p, d in df.groupby("period")["known_from"].min().items()}


# ------------------------------------------------------------------ segment facts


GEV_POWER = sk.SEG_LINES[0]
POWER = {(sk.SEG, "PowerSegmentMember"), (sk.CONS, sk.GEV_MARKER)}


def test_exact_dimensions_only():
    f = filing("2026-10-28")
    dfs = [dim("2026-07-01", "2026-09-30", 6067, POWER),
           dim("2026-07-01", "2026-09-30", 6038, {(sk.SEG, "PowerSegmentMember"), (sk.CONS, "OperatingSegmentsMember")}),
           dim("2026-07-01", "2026-09-30", 2864, POWER | {(sk.PROD, "ProductMember")}),  # a part: another axis
           dim("2026-07-01", "2026-09-30", 9999, {(sk.SEG, "PowerSegmentMember")}),  # no marker: not this definition
           dim("2026-01-01", "2026-09-30", 16516, POWER)]
    got = sk.exact_facts(dfs, f, (RFCC,), frozenset(POWER))
    assert [(str(x.start.date()), x.val / M) for x in got] == [("2026-01-01", 16516), ("2026-07-01", 6067)]
    assert all(x.filed == T("2026-10-28") and x.accn == "acc-2026-10-28" for x in got)


def test_10k_quarter_facts_are_ignored_and_first_concept_wins():
    k = filing("2026-01-29", "10-K")
    dfs = [dim("2025-10-01", "2025-12-31", 5748, POWER), dim("2025-01-01", "2025-12-31", 19845, POWER),
           dim("2025-01-01", "2025-12-31", 1, POWER, concept="Revenues")]
    got = sk.exact_facts(dfs, k, ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"), frozenset(POWER))
    assert [(str(x.start.date()), str(x.end.date()), x.val / M) for x in got] == [("2025-01-01", "2025-12-31", 19845)]


def test_alternatives_first_dimension_set_per_filing():
    line = next(x for x in sk.SEG_LINES if x.keys[0] == "rev_etn_electrical_americas")
    plain, marked = line.dimsets[:2]  # the 2021 name; the 2020 name follows (X15)
    pairs = [(filing("2026-05-05", cik=sk.ETN), [dim("2026-01-01", "2026-03-31", 3600, plain),
                                                  dim("2026-01-01", "2026-03-31", 3600, marked)]),
             (filing("2026-07-31", cik=sk.ETN), [dim("2026-04-01", "2026-06-30", 3951, marked)])]  # marker only
    got = sk.line_facts_from(pairs, line)
    assert [(str(x.filed.date()), x.val / M) for x in got] == [("2026-05-05", 3600), ("2026-07-31", 3951)]


def seg_facts_recast(rel):
    """Three 10-Qs; the third recasts the prior-year quarter by `rel`."""
    out = []
    for filed, q, val, prior in (("2025-04-23", ("2025-01-01", "2025-03-31"), 1879, None),
                                 ("2025-07-23", ("2025-04-01", "2025-06-30"), 2201, None),
                                 ("2026-04-22", ("2026-01-01", "2026-03-31"), 2959, 1879 * (1 + rel))):
        f = filing(filed)
        out.append(sec.Fact(T(q[0]), T(q[1]), val * M, T(filed), "10-Q", f.accession))
        if prior:
            out.append(sec.Fact(T("2025-01-01"), T("2025-03-31"), prior * M, T(filed), "10-Q", f.accession))
    return out


def test_recast_over_two_percent_needs_a_declared_break():
    with pytest.raises(DefinitionBreakError):
        sk.checked_regimes(("rev_x",), (), seg_facts_recast(-0.021))
    regs = sk.checked_regimes(("rev_x_fy24", "rev_x_fy26"), ("2026-04-22",), seg_facts_recast(-0.021))
    assert [len(r) for r in regs] == [2, 2]
    old, new = (sec.vintages([r]) for r in regs)
    assert latest(old) == {"2025Q1": 1879 * M * 1e-6, "2025Q2": 2201}
    assert latest(new)["2025Q1"] == pytest.approx(1879 * 0.979)
    # a small recast is an ordinary version, no break
    assert sk.checked_regimes(("rev_x",), (), seg_facts_recast(0.006))[0] == seg_facts_recast(0.006)


def test_gev_electrification_is_split_at_the_declared_break():
    line = next(x for x in sk.SEG_LINES if x.keys[0].startswith("rev_gev_electrification"))
    assert line.keys == ("rev_gev_electrification_fy24", "rev_gev_electrification_fy26")
    assert line.breaks == ("2026-04-22",) and len(line.regime_notes) == 2


# ------------------------------------------------------------------ fact filters


def test_misdated_10q_fact_is_dropped():
    good = sec.Fact(T("2024-01-01"), T("2024-03-31"), 2128 * M, T("2025-04-30"), "10-Q", "a")
    bad = sec.Fact(T("2023-01-01"), T("2023-03-31"), 2225 * M, T("2025-04-30"), "10-Q", "a")  # Equinix 2025
    annual = sec.Fact(T("2021-01-01"), T("2021-12-31"), 1 * M, T("2024-02-16"), "10-K", "k")  # 10-K comparatives stay
    assert [sk.plausible(f) for f in (good, bad, annual)] == [True, False, True]
    assert sk.kept([good, bad, annual], sk.EQIX, "eqix") == [good, annual]


def test_eaton_shell_filing_is_dropped_for_the_plc_only():
    shell = sec.Fact(T("2012-07-01"), T("2012-09-30"), 0.0, T("2012-11-14"), "10-Q", "s")
    corp = sec.Fact(T("2012-07-01"), T("2012-09-30"), 3950 * M, T("2012-10-31"), "10-Q", "c")
    assert sk.kept([shell], sk.ETN, "etn") == []
    assert sk.kept([corp], sk.ETN_CORP, "etn") == [corp]


# ------------------------------------------------------------------ total flows: predecessor, Q4 = FY - 9M


def cf_doc(tag, facts):
    return {"facts": {"us-gaap": {tag: {"units": {"USD": [
        {"start": s, "end": e, "val": v * M, "filed": d, "form": form, "accn": f"acc-{d}"}
        for s, e, v, d, form in facts]}}}}}


def test_eaton_q4_2012_is_successor_fy_minus_predecessor_9m(monkeypatch):
    corp = cf_doc("SalesRevenueNet", [("2012-01-01", "2012-09-30", 12036, "2012-10-31", "10-Q"),
                                      ("2012-07-01", "2012-09-30", 3950, "2012-10-31", "10-Q")])
    plc = cf_doc("SalesRevenueNet", [("2012-07-01", "2012-09-30", 0, "2012-11-14", "10-Q"),  # the shell
                                     ("2012-01-01", "2012-12-31", 16311, "2013-02-28", "10-K")])
    monkeypatch.setattr(sk.sec, "companyfacts", lambda cik: {sk.ETN: plc, sk.ETN_CORP: corp}[cik])
    sk.flow_vintages.cache_clear()
    try:
        df = sk.flow_vintages("rev", "etn")
    finally:
        sk.flow_vintages.cache_clear()
    assert latest(df) == {"2012Q3": 3950, "2012Q4": 16311 - 12036}
    assert first_known(df) == {"2012Q3": "2012-10-31", "2012Q4": "2013-02-28"}
    assert (df["value"] > 0).all()  # the shell's zero never becomes a version


def test_dlr_flows_come_from_the_instances(monkeypatch):
    calls = []

    def fake(cik, tag, since):
        calls.append((cik, tag, since))
        return [sec.Fact(T("2026-01-01"), T("2026-06-30"), 1784.229 * M, T("2026-07-31"), "10-Q", "q2"),
                sec.Fact(T("2026-01-01"), T("2026-09-30"), 3166.212 * M, T("2026-10-30"), "10-Q", "q3")]

    monkeypatch.setattr(sk, "instance_flow_facts", fake)
    monkeypatch.setattr(sk.sec, "companyfacts", lambda cik: pytest.fail("DLR must not read companyfacts"))
    sk.flow_vintages.cache_clear()
    try:
        df = sk.flow_vintages("capex", "dlr")
    finally:
        sk.flow_vintages.cache_clear()
    assert calls == [(sk.DLR, "PaymentsToDevelopRealEstateAssets", "2009-01-01")]
    assert latest(df)["2026Q3"] == pytest.approx(1381.983)
    assert first_known(df)["2026Q3"] == "2026-10-30"


# ------------------------------------------------------------------ balances


def inst(concept, instant, val, dims=(), unit="USD"):
    return sec_rpo.InstantFact(concept, T(instant), frozenset(dims), str(val), unit)


START = sec_rpo.START_AXIS


def test_balance_total_member_and_single_bucket():
    gev = next(b for b in sk.BALANCES if b.keys == ("rpo_gev_equipment",))
    total = next(b for b in sk.BALANCES if b.keys == ("rpo_gev",))
    etn = next(b for b in sk.BALANCES if b.keys == ("rpo_etn",))
    f = filing("2026-10-28")
    facts = [inst(sec_rpo.RPO, "2026-09-30", 196721 * M), inst(sec_rpo.RPO, "2026-09-30", 104054 * M, [(sk.PROD, "ProductMember")]),
             inst(sec_rpo.RPO, "2026-09-30", 92667 * M, [(sk.PROD, "ServiceMember")])]
    assert [x.val / M for x in sk.balance_facts_from([(f, facts)], total)] == [196721]
    assert [x.val / M for x in sk.balance_facts_from([(f, facts)], gev)] == [104054]
    # Eaton from 2024Q2: the backlog is a single start-date bucket with its 12-month share; read as the total
    e = filing("2026-11-03", cik=sk.ETN)
    bucket = [inst(sec_rpo.RPO, "2026-09-30", 26.2e9, [(START, "2026-10-01")]),
              inst(sec_rpo.PCT, "2026-09-30", 0.72, [(START, "2026-10-01")], "pure")]
    got = sk.balance_facts_from([(e, bucket)], etn)
    assert [(str(x.end.date()), x.val / M) for x in got] == [("2026-09-30", 26200)]


def test_several_amount_buckets_are_not_a_total():
    # Vertiv-style: amounts per start date only (the timing of noncurrent deferred revenue), no total
    b = next(x for x in sk.BALANCES if x.keys == ("rpo_pwr",))
    facts = [inst(sec_rpo.RPO, "2026-09-30", v * M, [(START, s)]) for s, v in (("2027-10-01", 115.0), ("2028-10-01", 6.0))]
    assert sk.balance_facts_from([(filing("2026-10-28"), facts)], b) == []


def test_balance_vintages_restated_and_repeated():
    b = sk.BALANCES[0]
    f1, f2 = filing("2026-07-22"), filing("2026-10-28")
    pairs = [(f1, [inst(sec_rpo.RPO, "2026-06-30", 176284 * M)]),
             (f2, [inst(sec_rpo.RPO, "2026-06-30", 176284 * M), inst(sec_rpo.RPO, "2026-09-30", 196721 * M)])]
    df = sec_rpo.stock_vintages(sk.balance_facts_from(pairs, b))
    assert latest(df) == {"2026Q2": 176284, "2026Q3": 196721}
    assert first_known(df) == {"2026Q2": "2026-07-22", "2026Q3": "2026-10-28"}  # a comparative is no new version


# ------------------------------------------------------------------ catalog


KEYS = {"rev_vrt", "capex_vrt", "rev_gev", "capex_gev", "rev_etn", "capex_etn", "rev_pwr", "capex_pwr", "rev_eqix",
        "capex_eqix", "rev_dlr", "capex_dlr", "rev_gev_power", "rev_gev_wind", "rev_gev_electrification_fy24",
        "rev_gev_electrification_fy26", "rev_etn_electrical_americas", "rev_etn_electrical_global", "rev_vrt_americas",
        "rev_vrt_apac", "rev_vrt_emea", "rpo_gev", "rpo_gev_equipment", "rpo_gev_services", "rpo_pwr", "rpo_etn",
        "rpo_eqix", "rev_vrt_americas_net", "rev_vrt_apac_net", "rev_vrt_emea_net"}


def test_catalog_entries():
    specs = {s.key: s for s in sk.SPECS}
    assert set(specs) == KEYS
    assert "rpo_vrt" not in catalog.by_key()  # Vertiv tags no RPO (BLOCKED in XBRL)
    by_key = catalog.by_key()
    for key, s in specs.items():
        assert by_key[key].key == key  # discovered by the catalog
        assert (s.freq, s.unit, s.publish, s.revised) == ("Q", "MUSD", True, True)
        assert s.license == sec_series.LICENSE
        assert licenses.verdict(s, by_key).klass == licenses.JA
        assert s.note.strip()
        datacenter = key.endswith(("_eqix", "_dlr"))
        if not datacenter:
            assert s.branch == "G7"
        elif key.startswith("capex_"):
            assert s.branch == "G5"
        else:
            assert s.branch == "G4"
    assert specs["rev_gev_electrification_fy24"].closed and specs["rev_gev_electrification_fy24"].max_age_days is None
    assert not specs["rev_gev_electrification_fy26"].closed
    assert specs["rev_dlr"].source == sk.SOURCE_INST and specs["rev_eqix"].source == sk.SOURCE
    assert specs["rpo_etn"].label.startswith("Orderstock")
    assert catalog.validate(list(specs.values())) == []


def test_freshness_bounds_follow_the_observed_filing_lags():
    for co, c in sk.COMPANIES.items():
        assert c.max_age_days - 92 - 30 in range(30, 80)
    assert sk.COMPANIES["vrt"].max_age_days == 72 + 122 and sk.COMPANIES["dlr"].max_age_days == 62 + 122
