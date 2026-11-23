"""Financing series (A3): balances as vintages, tag formulas, the zero fill and derived first quarters.

Synthetic companyfacts-shaped fixtures, no network. Values in USD millions (x 1e6 in the facts).
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import catalog
from ai_tracker.series import sec_finansiering as fin
from ai_tracker.sources import sec
from ai_tracker.sources import sec_financing as sf

M = 1e6


def inst(end, val, filed, form="10-Q", accn=None):
    return {"end": end, "val": int(val * M), "filed": filed, "form": form, "accn": accn or f"acc-{filed}"}


def dur(start, end, val, filed, form="10-Q", accn=None):
    return {"start": start, "end": end, "val": int(val * M), "filed": filed, "form": form,
            "accn": accn or f"acc-{filed}"}


def cf(**tags):
    return {"facts": {"us-gaap": {t: {"units": {"USD": rows}} for t, rows in tags.items()}}}


def latest(df):
    return df.sort_values("known_from").groupby("period")["value"].last().to_dict()


def first_known(df):
    return {p: str(d.date()) for p, d in df.groupby("period")["known_from"].min().items()}


# ------------------------------------------------------------------ balances


def test_report_dates_take_the_latest_common_end():
    # a 10-K repeats three years equally often; a stray subsequent-event instant is not a report date
    c = cf(Revenues=[dur("2024-01-01", "2024-12-31", 1, "2025-02-01", "10-K", "k"),
                     dur("2023-01-01", "2023-12-31", 1, "2025-02-01", "10-K", "k"),
                     dur("2022-01-01", "2022-12-31", 1, "2025-02-01", "10-K", "k")],
           Debt=[inst("2024-12-31", 5, "2025-02-01", "10-K", "k"), inst("2023-12-31", 4, "2025-02-01", "10-K", "k"),
                 inst("2025-01-20", 9, "2025-02-01", "10-K", "k")],
           **{f"Bal{i}": [inst("2024-12-31", i, "2025-02-01", "10-K", "k")] for i in range(4)})
    assert sf.report_dates(c) == {pd.Timestamp("2024-12-31")}


def test_balance_vintages_restated_comparative_is_a_later_version():
    c = cf(Debt=[inst("2025-03-31", 100, "2025-04-30", accn="q1"), inst("2024-12-31", 90, "2025-04-30", accn="q1"),
                 inst("2025-06-30", 120, "2025-07-30", accn="q2"), inst("2024-12-31", 90, "2025-07-30", accn="q2"),
                 inst("2026-03-31", 130, "2026-04-29", accn="q5"), inst("2025-03-31", 101, "2026-04-29", accn="q5"),
                 inst("2025-02-14", 999, "2025-04-30", accn="q1")])  # not a report date: dropped
    ends = {pd.Timestamp(e) for e in ("2024-12-31", "2025-03-31", "2025-06-30", "2026-03-31")}
    df = sf.stock_vintages([sf.instant_facts(c, "Debt")], ends)
    assert latest(df) == {"2024Q4": 90, "2025Q1": 101, "2025Q2": 120, "2026Q1": 130}
    assert first_known(df) == {"2024Q4": "2025-04-30", "2025Q1": "2025-04-30", "2025Q2": "2025-07-30",
                               "2026Q1": "2026-04-29"}
    assert len(df[df["period"] == "2025Q1"]) == 2  # original and restated version
    for p, kf in zip(df["period"], df["known_from"]):
        assert kf >= pd.Period(p, "Q").start_time  # never before the quarter starts


def test_oracle_quarter_end_maps_by_midpoint():
    assert str(sf.calendar_quarter(pd.Timestamp("2026-08-31"))) == "2026Q3"
    assert str(sf.calendar_quarter(pd.Timestamp("2026-11-30"))) == "2026Q4"
    assert str(sf.calendar_quarter(pd.Timestamp("2027-02-28"))) == "2027Q1"
    assert str(sf.calendar_quarter(pd.Timestamp("2026-05-31"))) == "2026Q2"
    assert str(sf.calendar_quarter(pd.Timestamp("2026-09-30"))) == "2026Q3"


def test_tag_priority_per_quarter_end():
    c = cf(New=[inst("2025-06-30", 50, "2025-07-30")], Old=[inst("2025-03-31", 40, "2025-04-30"),
                                                            inst("2025-06-30", 49, "2025-07-30")])
    ends = {pd.Timestamp("2025-03-31"), pd.Timestamp("2025-06-30")}
    df = sf.stock_vintages([sf.instant_facts(c, "New"), sf.instant_facts(c, "Old")], ends)
    assert latest(df) == {"2025Q1": 40, "2025Q2": 50}


def frame(rows):
    return pd.DataFrame([(p, v, pd.Timestamp(d)) for p, v, d in rows], columns=["period", "value", "known_from"])


def test_sum_needs_every_component_and_is_dated_by_the_latest():
    a = frame([("2025Q1", 10, "2025-04-30"), ("2025Q2", 11, "2025-07-30")])
    b = frame([("2025Q1", 1, "2025-05-02")])
    s = sf.sum_frames([a, b])
    assert latest(s) == {"2025Q1": 11}
    assert first_known(s) == {"2025Q1": "2025-05-02"}


def test_first_available_takes_each_period_from_one_formula():
    a = frame([("2025Q2", 20, "2025-07-30")])
    b = frame([("2025Q1", 9, "2025-04-30"), ("2025Q2", 99, "2025-07-01")])
    s = sf.first_available([a, b])
    assert latest(s) == {"2025Q1": 9, "2025Q2": 20}
    assert first_known(s)["2025Q2"] == "2025-07-30"  # b's earlier date for Q2 is not used


# ------------------------------------------------------------------ flows: gap fillers


def test_derived_first_quarter_from_same_filing():
    fs = sec.facts(cf(Int=[dur("2025-01-01", "2025-06-30", 30, "2025-07-30", accn="q2"),
                           dur("2025-04-01", "2025-06-30", 16, "2025-07-30", accn="q2"),
                           dur("2025-01-01", "2025-09-30", 50, "2025-10-30", accn="q3"),
                           dur("2025-07-01", "2025-09-30", 20, "2025-10-30", accn="q3")]), "Int")
    derived = sf.derived_first_quarters(fs)
    assert [(str(f.start.date()), str(f.end.date()), f.val / M) for f in derived] == [("2025-01-01", "2025-03-31", 14)]
    df = sec.vintages([fs, derived])
    assert latest(df) == {"2025Q1": 14, "2025Q2": 16, "2025Q3": 20}
    assert first_known(df)["2025Q1"] == "2025-07-30"  # not before the filing it comes from


FIN_TOTAL = "NetCashProvidedByUsedInFinancingActivities"


def zero_cf():
    return cf(**{
        FIN_TOTAL: [dur("2025-07-01", "2025-09-30", -5, "2025-10-29", accn="a1"),
                    dur("2024-07-01", "2024-09-30", -4, "2025-10-29", accn="a1"),
                    dur("2025-07-01", "2025-12-31", -9, "2026-01-28", accn="a2"),
                    dur("2025-10-01", "2025-12-31", -4, "2026-01-28", accn="a2"),
                    dur("2014-07-01", "2014-09-30", -1, "2014-10-20", accn="old")],
        "Proceeds": [dur("2025-07-01", "2025-12-31", 7, "2026-01-28", accn="a2")]})


def test_zero_candidates_current_period_only_and_not_where_tagged():
    z = sf.zero_candidates(zero_cf(), ["Proceeds"])
    assert set(z) == {"a1"}  # a2 has the tag, "old" is before ZERO_SINCE
    assert [(str(f.start.date()), str(f.end.date()), f.val) for f in z["a1"]] == [("2025-07-01", "2025-09-30", 0.0)]


def xbrl(*concepts):
    body = "".join(f'<{c} contextRef="c1" unitRef="usd">1</{c}>' for c in concepts)
    return f'<xbrl xmlns="http://www.xbrl.org/2003/instance">{body}</xbrl>'.encode()


def test_instance_concepts_reads_all_namespaces():
    raw = xbrl("us-gaap:RepaymentsOfDebt", "orcl:ProceedsFromTermLoans") + b"<dei:DocumentType>10-Q</dei:DocumentType>"
    assert sf.instance_concepts(raw) == {"RepaymentsOfDebt", "ProceedsFromTermLoans"}


@pytest.mark.parametrize("concepts, filled", [
    (("us-gaap:RepaymentsOfDebt", "orcl:ProceedsFromRepaymentsOfShortTermBorrowings"), True),
    (("us-gaap:RepaymentsOfDebt", "orcl:ProceedsFromTermLoans"), False),  # company tag: no fill
    (("us-gaap:ProceedsFromLongTermLinesOfCredit",), False),
    (("us-gaap:ProceedsFromSaleOfAvailableForSaleSecuritiesDebt",), True),
])
def test_zero_fill_is_refused_when_the_instance_has_a_matching_concept(monkeypatch, concepts, filled):
    monkeypatch.setattr(sf.sec_segment, "instance", lambda f: xbrl(*concepts))
    zeros, refused = sf.zero_facts(1, zero_cf(), ["Proceeds"], fin.ISSUE_PATTERN, fin.ZERO_EXCLUDE)
    assert bool(zeros) is filled and bool(refused) is not filled


def test_zero_fill_gives_zero_quarters_and_q4_from_fy(monkeypatch):
    monkeypatch.setattr(sf.sec_segment, "instance", lambda f: xbrl("us-gaap:NetIncomeLoss"))
    c = cf(**{FIN_TOTAL: [dur("2025-07-01", "2025-09-30", -5, "2025-10-29", accn="q1"),
                          dur("2025-07-01", "2025-12-31", -9, "2026-01-28", accn="q2"),
                          dur("2025-07-01", "2026-03-31", -9, "2026-04-29", accn="q3")],
              "Proceeds": [dur("2025-07-01", "2026-06-30", 0, "2026-07-29", "10-K", accn="k")]})
    zeros, _ = sf.zero_facts(1, c, ["Proceeds"], fin.ISSUE_PATTERN, fin.ZERO_EXCLUDE)
    df = sec.vintages([sec.facts(c, "Proceeds"), zeros])
    assert latest(df) == {"2025Q3": 0, "2025Q4": 0, "2026Q1": 0, "2026Q2": 0}


# ------------------------------------------------------------------ catalog


def test_catalog_entries():
    specs = {s.key: s for s in fin.SPECS}
    assert not catalog.validate(fin.SPECS)
    assert {f"{m}_{c}" for m in fin.MEASURES for c in fin.QUARTERLY[m]} <= set(specs)
    assert "fin_lease_liab_meta" not in specs and specs["fin_lease_liab_meta_a"].freq == "A"
    assert {f"{m}_hyp4" for m in fin.HYP4_MEASURES} <= set(specs)
    assert all(specs[k].lag_days == -31 for k in specs if k.endswith("_orcl"))
    assert all(s.publish and s.branch == "G5" for s in fin.SPECS)
    other = {s.key for s in catalog.ALL} - set(specs)
    assert not other & set(specs)
