"""SEC companyfacts -> quarterly vintages: YTD differencing, fiscal years, restatements, aggregates.

Synthetic companyfacts-shaped fixtures, no network. Values are in USD millions (x 1e6 in the facts).
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import catalog, observations, warehouse
from ai_tracker.series import sec as sec_series
from ai_tracker.sources import sec

TAG = "PaymentsToAcquirePropertyPlantAndEquipment"
M = 1e6


def fact(start, end, val, filed, form="10-Q", accn=None):
    return {"start": start, "end": end, "val": int(val * M), "filed": filed, "form": form,
            "accn": accn or f"acc-{filed}-{form}", "fy": 0, "fp": "x"}


def companyfacts(rows, tag=TAG):
    return {"facts": {"us-gaap": {tag: {"units": {"USD": rows}}}}}


def run(rows, tag=TAG):
    return sec.vintages([sec.facts(companyfacts(rows, tag), tag)])


def latest(df):
    return df.sort_values("known_from").groupby("period")["value"].last().to_dict()


def first_known(df):
    return {p: str(d.date()) for p, d in df.groupby("period")["known_from"].min().items()}


# A calendar fiscal year: YTD cash flows in 10-Qs, full year in the 10-K.
CAL_2025 = [
    fact("2025-01-01", "2025-03-31", 10, "2025-04-30"),
    fact("2025-01-01", "2025-06-30", 25, "2025-07-30"),
    fact("2025-01-01", "2025-09-30", 45, "2025-10-30"),
    fact("2025-01-01", "2025-12-31", 70, "2026-02-01", "10-K"),
]


def test_ytd_differencing_and_q4_from_10k():
    df = run(CAL_2025)
    assert latest(df) == {"2025Q1": 10, "2025Q2": 15, "2025Q3": 20, "2025Q4": 25}
    # each quarter is dated by the filing that completes it; Q4 only with the 10-K
    assert first_known(df) == {"2025Q1": "2025-04-30", "2025Q2": "2025-07-30",
                               "2025Q3": "2025-10-30", "2025Q4": "2026-02-01"}


def test_no_value_before_the_needed_filings():
    df = run(CAL_2025)
    for p, kf in zip(df["period"], df["known_from"]):
        assert kf >= pd.Period(p, "Q").end_time.normalize()
    # without the 10-K there is no Q4, whatever else is on file
    assert "2025Q4" not in latest(run(CAL_2025[:3]))


def test_comparative_repeat_is_not_a_new_vintage():
    rows = CAL_2025 + [fact("2025-01-01", "2025-03-31", 10, "2026-04-29")]  # same value as comparative
    assert len(run(rows)) == 4


def test_june_fiscal_year_maps_to_calendar_quarters():
    rows = [fact("2025-07-01", "2025-09-30", 5, "2025-10-29"),
            fact("2025-07-01", "2025-12-31", 12, "2026-01-28"),
            fact("2025-07-01", "2026-03-31", 20, "2026-04-29"),
            fact("2025-07-01", "2026-06-30", 30, "2026-07-29", "10-K")]
    df = run(rows)
    assert latest(df) == {"2025Q3": 5, "2025Q4": 7, "2026Q1": 8, "2026Q2": 10}
    assert first_known(df)["2026Q2"] == "2026-07-29"


def test_52_week_year_ending_late_january_uses_midpoint_quarter():
    # Nvidia-style: quarters end late Apr/Jul/Oct/Jan; Aug-Oct is calendar Q3
    rows = [fact("2025-01-27", "2025-04-27", 1, "2025-05-28"),
            fact("2025-01-27", "2025-07-27", 3, "2025-08-27"),
            fact("2025-01-27", "2025-10-26", 6, "2025-11-19"),
            fact("2025-01-27", "2026-01-25", 10, "2026-02-25", "10-K")]
    df = run(rows)
    assert latest(df) == {"2025Q1": 1, "2025Q2": 2, "2025Q3": 3, "2025Q4": 4}
    assert sec.calendar_quarter(pd.Timestamp("2025-07-28"), pd.Timestamp("2025-10-26")) == pd.Period("2025Q3", "Q")
    assert (df["known_from"] >= pd.PeriodIndex(df["period"], freq="Q").end_time.normalize()).all()


def test_restatement_in_later_filings_is_a_second_vintage():
    rows = CAL_2025 + [
        fact("2025-01-01", "2025-03-31", 11, "2026-04-29"),  # Q1 2025 restated as comparative
        fact("2025-01-01", "2025-06-30", 27, "2026-07-29"),  # 6M restated: Q2 = 27 - 11 = 16
    ]
    df = run(rows)
    q1 = df[df["period"] == "2025Q1"].sort_values("known_from")
    assert list(q1["value"]) == [10, 11]
    assert [str(d.date()) for d in q1["known_from"]] == ["2025-04-30", "2026-04-29"]
    q2 = df[df["period"] == "2025Q2"].sort_values("known_from")
    assert list(q2["value"]) == [15, 16] and str(q2["known_from"].iloc[-1].date()) == "2026-07-29"


def test_amended_10q_is_a_later_vintage():
    rows = CAL_2025 + [fact("2025-01-01", "2025-03-31", 12, "2025-06-15", "10-Q/A")]
    q1 = run(rows).query("period == '2025Q1'").sort_values("known_from")
    assert list(q1["value"]) == [10, 12] and str(q1["known_from"].iloc[-1].date()) == "2025-06-15"


def test_full_year_restatement_without_quarterly_breakdown_is_not_dumped_in_q4():
    # Meta 2015: full year restated in a later 10-K, 9M never restated -> Q4 keeps its original value
    rows = CAL_2025 + [fact("2025-01-01", "2025-12-31", 90, "2027-02-01", "10-K")]
    assert latest(run(rows))["2025Q4"] == 25


def test_previous_ytd_restated_alone_does_not_change_the_quarter():
    # 3M restated in next year's Q1 10-Q, 6M not yet: Q2 stays until the 6M is filed again
    rows = CAL_2025 + [fact("2025-01-01", "2025-03-31", 11, "2026-04-29")]
    q2 = run(rows).query("period == '2025Q2'")
    assert list(q2["value"]) == [15]


def test_direct_quarter_beats_mixed_ytd_difference():
    # Amazon 2017-18: a 3-month fact exists; the YTD facts were later refiled under a new definition
    rows = [fact("2017-01-01", "2017-06-30", 50, "2017-07-28"),
            fact("2017-01-01", "2017-09-30", 70, "2017-10-27"),
            fact("2017-07-01", "2017-09-30", 20, "2017-10-27"),
            fact("2017-01-01", "2017-06-30", 60, "2018-07-27")]  # gross restatement of 6M only
    assert latest(run(rows))["2017Q3"] == 20


def test_10k_quarterly_note_facts_are_ignored():
    # Amazon FY2012 10-K tagged its quarterly table with the wrong year
    rows = [fact("2011-01-01", "2011-03-31", 9, "2011-04-27"),
            fact("2011-01-01", "2011-03-31", 13, "2013-01-30", "10-K")]
    df = run(rows)
    assert list(df["value"]) == [9]


def test_tags_spliced_per_quarter_then_per_fact():
    old, new = "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"
    cf = {"facts": {"us-gaap": {
        old: {"units": {"USD": [fact("2018-01-29", "2018-10-28", 9, "2018-11-15")]}},
        new: {"units": {"USD": [fact("2018-01-29", "2019-01-27", 12, "2019-02-21", "10-K")]}}}}}
    df = sec.vintages([sec.facts(cf, new), sec.facts(cf, old)])
    assert latest(df) == {"2018Q4": 3}  # Nvidia FY2019 Q4: new-tag full year minus old-tag 9M

    # Microsoft ASC 606: restated full year under the new tag is not differenced against old-basis 9M
    cf = {"facts": {"us-gaap": {
        old: {"units": {"USD": [fact("2015-07-01", "2016-03-31", 60, "2016-04-21"),
                                fact("2015-07-01", "2016-06-30", 80, "2016-07-28", "10-K")]}},
        new: {"units": {"USD": [fact("2015-07-01", "2016-06-30", 86, "2018-08-03", "10-K")]}}}}}
    df = sec.vintages([sec.facts(cf, new), sec.facts(cf, old)])
    assert latest(df)["2016Q2"] == 20


def test_contiguous_tail_drops_history_before_last_gap():
    df = pd.DataFrame({"period": ["2010Q1", "2010Q2", "2011Q1", "2011Q2"], "value": 1.0,
                       "known_from": pd.Timestamp("2012-01-01")})
    assert list(sec.contiguous_tail(df)["period"]) == ["2011Q1", "2011Q2"]


def frame(rows):
    return pd.DataFrame(rows, columns=["period", "value", "known_from"]).assign(
        known_from=lambda d: pd.to_datetime(d["known_from"]))


def test_aggregate_only_after_fourth_filing_and_revised_by_restatements():
    frames = {
        "a": frame([("2026Q3", 10, "2026-10-22")]),
        "b": frame([("2026Q3", 20, "2026-10-28"), ("2026Q3", 21, "2027-10-27")]),
        "c": frame([("2026Q3", 30, "2026-10-29")]),
        "d": frame([("2026Q3", 40, "2026-10-30"), ("2026Q2", 5, "2026-07-30")]),
    }
    agg = sec.aggregate(frames)
    assert list(agg["period"]) == ["2026Q3", "2026Q3"]  # 2026Q2 lacks three companies
    assert list(agg["value"]) == [100, 101]
    assert [str(d.date()) for d in agg["known_from"]] == ["2026-10-30", "2027-10-27"]


def test_as_of_before_and_after_filings():
    spec = catalog.Spec(key="capex_test", branch="G5", label="x", unit="MUSD", freq="Q", source="test",
                        fetch=lambda: None, lag_days=25, license="public", revised=True)
    rows = CAL_2025 + [fact("2025-01-01", "2025-03-31", 11, "2026-04-29")]
    table = observations.new_rows(spec, run(rows)[["period", "value", "known_from"]], observations._empty())
    assert set(table["source"]) == {"release"}
    assert observations.as_of("capex_test", "2025-04-29", table).empty
    assert observations.as_of("capex_test", "2025-10-30", table).to_dict() == {
        pd.Period("2025Q1", "Q"): 10, pd.Period("2025Q2", "Q"): 15, pd.Period("2025Q3", "Q"): 20}
    after = observations.as_of("capex_test", "2026-05-01", table)
    assert after[pd.Period("2025Q1", "Q")] == 11 and after[pd.Period("2025Q4", "Q")] == 25
    checks = warehouse.run_checks(warehouse.connect(table, [spec]))
    assert all(v.empty for v in checks.values()), {k: v for k, v in checks.items() if len(v)}


def test_catalog_entries():
    keys = {s.key for s in sec_series.SPECS}
    for c in ("msft", "googl", "amzn", "meta"):
        assert {f"capex_{c}", f"fin_lease_{c}", f"ocf_{c}", f"rev_{c}"} <= keys
    assert {"rev_nvda", "capex_hyp4", "ocf_hyp4", "fin_lease_hyp4"} <= keys
    assert catalog.validate(sec_series.SPECS) == []
    assert all(s.freq == "Q" and s.branch in ("G4", "G5") for s in sec_series.SPECS)


@pytest.mark.parametrize("measure", ["capex", "fin_lease", "ocf"])
def test_hyp4_uses_the_four_companies(measure):
    assert set(sec_series.TAGS[measure]) == set(sec_series.HYP4)
