"""Fix track X9 for the R12 review of M1 (docs/granskning/r12_makro.md): guards next to the flipped R12 tests.

No network. The R12 tests (tests/test_r12_makro.py) pin the defects themselves; these pin the edges of the fixes.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from ai_tracker import catalog, http, observations, warehouse
from ai_tracker.sources import bea_nipa, bls

T = pd.Timestamp
P = pd.Period


def _q(*periods):
    return pd.PeriodIndex(periods, freq="Q-DEC")


# B852RX around the comprehensive update of 2023-09-28 (2012 $ -> 2017 $, start 2002Q1 -> 2007Q1)
REBASED = {
    T("2023-08-30"): {"B852RX": pd.Series([80963.0, 87694.0, 90000.0], _q("2006Q4", "2007Q1", "2023Q2"))},
    T("2023-09-28"): {"B852RX": pd.Series([82231.0, 99000.0], _q("2007Q1", "2023Q2"))},
}


def test_archive_rows_keep_only_newest_vintage_periods_with_all_their_vintages():
    rows = bea_nipa.archive_rows("B852RX", REBASED)
    assert [(str(p), v, k.date().isoformat()) for p, v, k in rows.itertuples(index=False)] == [
        ("2007Q1", 87694.0, "2023-08-30"), ("2023Q2", 90000.0, "2023-08-30"),
        ("2007Q1", 82231.0, "2023-09-28"), ("2023Q2", 99000.0, "2023-09-28")]
    assert rows.attrs[observations.COMPLETE] is True
    # every as_of view takes all periods from one vintage, so the base year never mixes
    spec = catalog.by_key()["us_imp_computers_real"]
    t = observations.new_rows(spec, rows, observations._empty(), date(2026, 11, 24))
    early = observations.as_of(spec.key, "2023-09-01", t)
    assert early.to_dict() == {P("2007Q1", "Q"): 87694.0, P("2023Q2", "Q"): 90000.0}


def test_a_complete_fetch_that_drops_a_stored_period_must_be_rebuilt():
    spec = catalog.by_key()["us_imp_computers_real"]
    before = bea_nipa.archive_rows("B852RX", {T("2023-08-30"): REBASED[T("2023-08-30")]})
    stored = observations.new_rows(spec, before, observations._empty(), date(2023, 9, 1))
    after = bea_nipa.archive_rows("B852RX", REBASED)
    with pytest.raises(ValueError, match=r"no longer has 1 stored periods \(2006Q4\.\.2006Q4\).*--rebuild"):
        observations.new_rows(spec, after, stored, date(2023, 10, 2))
    plain = after.copy()
    plain.attrs = {}  # a fetch that does not claim completeness keeps the old behaviour (nothing is deleted)
    assert len(observations.new_rows(spec, plain, stored, date(2023, 10, 2))) == 2


def test_first_published_floor_turns_a_release_date_into_backfill():
    cal = pd.Series({P("2001-04", "M"): T("2001-05-11"), P("2002-01", "M"): T("2002-02-15")})
    df = pd.DataFrame({"period": [P("2001-04", "M"), P("2002-01", "M")], "value": [1.0, 2.0], "footnotes": ["", ""]})
    out = bls.date_rows(df, "cpi_nsa", cal, T("2002-02-15"), first_published=T("2002-02-15"))
    assert list(zip(out["known_from"], out["source"])) == [(T("2002-02-15"), "backfill"), (T("2002-02-15"), "release")]
    assert bls.FIRST_PUBLISHED == {"PCU518210518210": T("2002-02-15")}


def test_vintage_date_uses_last_modified_and_the_fetch_only_for_unlisted_months():
    cal = pd.Series({P("2026-09", "M"): T("2026-10-14")})
    assert bls.vintage_date(cal, T("2026-10-15"), P("2026-10", "M"), T("2026-11-24")) == T("2026-10-15")
    assert bls.vintage_date(cal, None, P("2026-09", "M"), T("2026-11-24")) == T("2026-10-14")
    assert bls.vintage_date(cal, None, P("2026-10", "M"), T("2026-11-24")) == T("2026-11-24")


def test_six_digit_release_names_only_for_1994_to_1999():
    assert bls._release_name_date("051499") == T("1999-05-14")
    assert bls._release_name_date("021094") == T("1994-02-10")
    with pytest.raises(ValueError, match="outside 1994-1999"):
        bls._release_name_date("021003")


def test_known_gap_periods_accept_only_the_listed_month_and_whole_series_exemptions_still_work(monkeypatch):
    spec = catalog.by_key()["us_cpi_electricity_sa_m"]
    rows = pd.DataFrame({"period": ["2025-09", "2025-11"], "value": [1.0, 2.0],
                         "known_from": [T("2025-10-24"), T("2025-12-18")]})
    t = observations.new_rows(spec, rows, observations._empty(), date(2026, 11, 24))
    assert warehouse.run_checks(warehouse.connect(t, [spec]))["no_gaps"].empty
    monkeypatch.setitem(warehouse.KNOWN_GAP_PERIODS, spec.key, {"2025-12": "another month"})
    assert len(warehouse.run_checks(warehouse.connect(t, [spec]))["no_gaps"]) == 1
    monkeypatch.setitem(warehouse.KNOWN_GAPS, spec.key, "whole series")
    assert warehouse.run_checks(warehouse.connect(t, [spec]))["no_gaps"].empty


def test_contact_identity_for_sec_subdomains_and_a_port(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "ai-rollout-tracker contact@example.org")
    assert http.user_agent("data.sec.gov") == "ai-rollout-tracker contact@example.org"
    assert http.user_agent("WWW.SEC.GOV:443") == "ai-rollout-tracker contact@example.org"
    assert http.user_agent("evilsec.gov") == http.DEFAULT_UA
    assert http.user_agent("bls.gov.example.com") == http.DEFAULT_UA
