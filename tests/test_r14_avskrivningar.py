"""R14 review of P1, depreciation and PP&E from SEC XBRL (docs/granskning/r14_avskrivningar.md). Fixtures only.

The Microsoft fixture is the line "Depreciation, amortization, and other" (msft:DepreciationAmortizationAndOther) as
filed, read off the rendered cash-flow statements (R pages) of the 10-Q/10-K filings 2024-04-25 to 2026-10-28 on
www.sec.gov. It pins the values that hold (every single quarter is on one basis) and marks the confirmed defect as a
strict xfail: the first quarter of FY2025 (2024Q3) was restated through the six- and nine-month figures in the
10-Q 2026-01-28 and later, but the series keeps the old three-month value, so the fiscal year 2025 window mixes bases.
Both strict xfails (R-1, R-2) were fixed in track X11 (auto14/x11-avskrivningar) and are ordinary tests now.
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker.series import sec_avskrivningar as m
from ai_tracker.series.sec_segments import DefinitionBreakError
from ai_tracker.sources import sec, sec_custom

M = 1e6


def F(start, end, val, filed, form="10-Q"):
    return sec.Fact(pd.Timestamp(start), pd.Timestamp(end), val * M, pd.Timestamp(filed), form, f"acc-{filed}")


# Microsoft, USD millions, as filed (accessions in the review doc). FY = July-June.
MSFT_ROWS = [
    F("2023-07-01", "2024-03-31", 15907, "2024-04-25"), F("2024-01-01", "2024-03-31", 6027, "2024-04-25"),
    F("2023-07-01", "2024-06-30", 22287, "2024-07-30", "10-K"),
    F("2024-07-01", "2024-09-30", 7383, "2024-10-30"),
    F("2024-10-01", "2024-12-31", 6827, "2025-01-29"), F("2024-07-01", "2024-12-31", 14210, "2025-01-29"),
    F("2025-01-01", "2025-03-31", 8740, "2025-04-30"), F("2024-07-01", "2025-03-31", 22950, "2025-04-30"),
    F("2024-01-01", "2024-03-31", 6027, "2025-04-30"), F("2023-07-01", "2024-03-31", 15907, "2025-04-30"),
    F("2024-07-01", "2025-06-30", 34153, "2025-07-30", "10-K"), F("2023-07-01", "2024-06-30", 22287, "2025-07-30", "10-K"),
    F("2025-07-01", "2025-09-30", 13061, "2025-10-29"), F("2024-07-01", "2024-09-30", 7383, "2025-10-29"),
    # 10-Q 2026-01-28: amounts moved out of 'other'; the six-month comparative is restated, the Q1 column is not shown
    F("2025-10-01", "2025-12-31", 9198, "2026-01-28"), F("2024-10-01", "2024-12-31", 5667, "2026-01-28"),
    F("2025-07-01", "2025-12-31", 17345, "2026-01-28"), F("2024-07-01", "2024-12-31", 12383, "2026-01-28"),
    F("2026-01-01", "2026-03-31", 10167, "2026-04-29"), F("2025-01-01", "2025-03-31", 7734, "2026-04-29"),
    F("2025-07-01", "2026-03-31", 27512, "2026-04-29"), F("2024-07-01", "2025-03-31", 20116, "2026-04-29"),
    F("2025-07-01", "2026-06-30", 38534, "2026-07-29", "10-K"), F("2024-07-01", "2025-06-30", 29433, "2026-07-29", "10-K"),
    F("2023-07-01", "2024-06-30", 20958, "2026-07-29", "10-K"),
    F("2026-07-01", "2026-09-30", 11744, "2026-10-28"), F("2025-07-01", "2025-09-30", 8147, "2026-10-28"),
]


@pytest.fixture(autouse=True)
def clear_caches():
    for f in (m.flow_series, m.balance_series, m.fiscal_quarters, m.hyp4_series, m.aws_series):
        f.cache_clear()
    yield
    for f in (m.flow_series, m.balance_series, m.fiscal_quarters, m.hyp4_series, m.aws_series):
        f.cache_clear()


@pytest.fixture
def msft(monkeypatch):
    monkeypatch.setattr(sec_custom, "duration_facts", lambda cik, concepts, since, until: tuple(MSFT_ROWS))
    return m.flow_series("dep", "msft")


def versions(df, period):
    d = df[df.period == period].sort_values("known_from")
    return [(round(v, 3), str(k.date())) for v, k in zip(d.value, d.known_from)]


def latest(df):
    return df.sort_values("known_from").groupby("period")["value"].last().round(3).to_dict()


# ------------------------------------------------------------------ properties that hold


def test_msft_declared_break_is_the_only_one_found():
    """The fixture (real figures) triggers exactly the declared break; the stop rule passes."""
    m.checked("dep_msft", MSFT_ROWS, ("2026-01-28",))
    with pytest.raises(DefinitionBreakError):
        m.checked("dep_msft", MSFT_ROWS, ())


def test_declared_break_that_does_not_occur_also_stops_the_fetch():
    rows = [r for r in MSFT_ROWS if r.filed < pd.Timestamp("2026-01-01")]
    with pytest.raises(DefinitionBreakError, match="declared"):
        m.checked("dep_msft", rows, ("2026-01-28",))


def test_msft_single_quarters_never_mix_bases(msft):
    """Q4 = FY - 9M takes both from one basis in every vintage; the hand-checked values of the review."""
    # Q4 FY2025: old FY - old 9M, then the 10-K FY2026 (new FY) with the 10-Q 2026-04-29 (new 9M)
    assert versions(msft, "2025Q2") == [(11203, "2025-07-30"), (9317, "2026-07-29")]
    # Q4 FY2024: only the full year was restated (22,287 -> 20,958); it is not dumped into Q4
    assert versions(msft, "2024Q2") == [(6380, "2024-07-30")]
    assert versions(msft, "2024Q4") == [(6827, "2025-01-29"), (5667, "2026-01-28")]
    assert versions(msft, "2026Q2") == [(11022, "2026-07-29")]  # 38,534 - 27,512
    got = latest(msft)
    assert sum(got[p] for p in ("2025Q3", "2025Q4", "2026Q1", "2026Q2")) == 38534  # FY2026 window on one basis


def test_msft_known_from_is_the_filing_date_and_never_before_quarter_end(msft):
    filed = {r.filed for r in MSFT_ROWS}
    assert set(msft.known_from) <= filed
    assert all(k > pd.Period(p, "Q").end_time for p, k in zip(msft.period, msft.known_from))


def test_coreweave_rounding_filter_drops_a_difference_of_rounded_comparatives(monkeypatch):
    """The P1 test passes without the filter. Here the filter is needed: the six-month comparative moves by less than
    sec.TOL, so the difference is taken against the rounded Q1 comparative (560 instead of 559.4, as 2025Q2 in the
    real data)."""
    rows = [{"start": s, "end": e, "val": int(v * M), "filed": d, "form": "10-Q", "accn": f"a-{d}", "fy": 0, "fp": "x"}
            for s, e, v, d in [("2025-01-01", "2025-03-31", 300.2, "2025-05-15"),
                               ("2025-01-01", "2025-06-30", 859.6, "2025-08-13"),
                               ("2025-01-01", "2025-03-31", 300, "2026-05-08"),
                               ("2025-01-01", "2025-06-30", 860, "2026-08-12")]]
    cf = {"facts": {"us-gaap": {"DepreciationDepletionAndAmortization": {"units": {"USD": rows}}}}}
    monkeypatch.setattr(m, "_cf", lambda cik: cf)
    assert versions(m.flow_series("dep", "crwv"), "2025Q2") == [(559.4, "2025-08-13")]
    m.flow_series.cache_clear()
    monkeypatch.setattr(m, "rounding_revisions_dropped", lambda df: df)
    assert versions(m.flow_series("dep", "crwv"), "2025Q2") == [(559.4, "2025-08-13"), (560, "2026-08-12")]


def test_gross_is_not_formed_from_net_and_accumulated_of_different_filings(monkeypatch):
    """Net from the 10-K and accumulated depreciation only from a later 10-Q for the same date: no gross."""
    ocf = [{"start": s, "end": e, "val": 1, "filed": d, "form": "10-Q", "accn": f"a-{d}", "fy": 0, "fp": "x"}
           for s, e, d in [("2025-07-01", "2025-09-30", "2025-10-30"), ("2025-10-01", "2025-12-31", "2026-04-30")]]
    tags = {"NetCashProvidedByUsedInOperatingActivities": ocf,
            m.NET_B: [{"end": "2025-12-31", "val": int(300 * M), "filed": "2026-02-01", "form": "10-K", "accn": "k"},
                      {"end": "2025-09-30", "val": int(280 * M), "filed": "2025-10-30", "form": "10-Q", "accn": "q3"}],
            m.ACC_B: [{"end": "2025-12-31", "val": int(100 * M), "filed": "2026-04-30", "form": "10-Q", "accn": "q1"},
                      {"end": "2025-09-30", "val": int(90 * M), "filed": "2025-10-30", "form": "10-Q", "accn": "q3"}]}
    monkeypatch.setattr(m, "_cf", lambda cik: {"facts": {"us-gaap": {t: {"units": {"USD": r}} for t, r in tags.items()}}})
    assert latest(m.balance_series("gross", "meta")) == {"2025Q3": 370}


def test_oracle_calendar_lag_and_freshness_as_documented():
    specs = {s.key: s for s in m.SPECS}
    for key in ("dep_orcl", "dep_ppe_orcl", "ppe_net_orcl"):
        assert (specs[key].lag_days, specs[key].max_age_days) == (-31, 119)
    # Sep-Nov maps to Q4 (midpoint rule), filed about 10 December, before the calendar quarter ends
    assert sec.calendar_quarter(pd.Timestamp("2025-09-01"), pd.Timestamp("2025-11-30")) == pd.Period("2025Q4", "Q")


# ------------------------------------------------------------------ confirmed defects (fixed in X11)


def test_msft_first_quarter_restated_through_ytd_is_a_new_vintage(msft):
    """R14 R-1: Microsoft restated Q1 FY2025 through the six-month comparative in the 10-Q 2026-01-28 (12,383 - 5,667
    = 6,716; also 20,116 - 5,667 - 7,734 and 29,433 - 22,718), so 2024Q3 gets a version on the new basis and the
    FY2025 window equals the restated full year."""
    assert versions(msft, "2024Q3")[-1] == (6716, "2026-01-28")
    got = latest(msft)
    assert abs(sum(got[p] for p in ("2024Q3", "2024Q4", "2025Q1", "2025Q2")) - 29433) <= 1


def test_msft_q1_fy2026_on_the_new_basis_is_dated_to_the_six_month_filing(msft):
    """X11: 2025Q3 on the new basis (17,345 - 9,198 = 8,147) is known from the 10-Q 2026-01-28, not 2026-10-28, so
    no vintage from 2026-01-28 has 2025Q3 on the old basis next to 2025Q4 on the new one."""
    assert versions(msft, "2025Q3") == [(13061, "2025-10-29"), (8147, "2026-01-28")]
    assert versions(msft, "2024Q3") == [(7383, "2024-10-30"), (6716, "2026-01-28")]


def test_dep_hyp4_note_names_the_definitions_it_sums():
    """R14 R-2: the published note of dep_hyp4 names the definitions it sums (MSFT 'other' with quarters on the old
    basis, AMZN content and operating leases, META intangibles, GOOGL depreciation only)."""
    note = {s.key: s for s in m.SPECS}["dep_hyp4"].note
    for word in ("other", "operationell", "immateriell", "gamla basen"):
        assert word in note, word
