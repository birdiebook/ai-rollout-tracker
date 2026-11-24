"""EIA-930: filtering the six-month CSVs, monthly aggregates, coverage and completeness rules (no network)."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from ai_tracker import catalog
from ai_tracker.series import eia930 as eia930_series
from ai_tracker.sources import eia930

BAL_COLS = ["Balancing Authority", "Data Date", "Hour Number", "Local Time at End of Hour", "Demand (MW)",
            "Demand (MW) (Adjusted)", "Region"]


def balance_csv(days=31, month=7, year=2026, skip_hours=0) -> bytes:
    lines = [",".join(f'"{c}"' for c in BAL_COLS)]
    n = 0
    for d in range(1, days + 1):
        for h in range(1, 25):
            n += 1
            for ba, base in (("PJM", 100000), ("ERCO", 60000), ("SOCO", 30000), ("AZPS", 5000), ("SRP", 4000),
                             ("MISO", 1)):
                adj = "" if (ba == "SRP" and n <= skip_hours) else str(base + h)
                lines.append(f'{ba},{month:02d}/{d:02d}/{year},{h},x,"1,234",{adj},R')
    return ("\n".join(lines) + "\n").encode()


def subregion_csv(days=31, month=7, year=2026) -> bytes:
    lines = ['"Balancing Authority","Data Date","Hour Number","Sub-Region","Demand (MW)","Local Time at End of Hour",'
             '"UTC Time at End of Hour"']
    for d in range(1, days + 1):
        for h in range(1, 25):
            lines.append(f"PJM,{month:02d}/{d:02d}/{year},{h},DOM,{18000 + h},x,y")
            lines.append(f"PJM,{month:02d}/{d:02d}/{year},{h},AEP,{1},x,y")
            lines.append(f"CISO,{month:02d}/{d:02d}/{year},{h},DOM,{9},x,y")
    return ("\n".join(lines) + "\n").encode()


def test_filter_and_monthly_aggregates():
    h = pd.concat([eia930.filter_hourly(balance_csv(), "BALANCE"),
                   eia930.filter_hourly(subregion_csv(), "SUBREGION")])
    assert set(h["area"]) == set(eia930.AREAS)
    m = eia930.monthly(h, date(2026, 8, 10)).set_index("area")
    assert m.loc["pjm", "peak_mw"] == 100024 and m.loc["pjm", "avg_mw"] == pytest.approx(100012.5)
    assert m.loc["pjm_dom", "peak_mw"] == 18024  # PJM sub-region DOM, not CISO's
    assert (m["period"].astype(str) == "2026-07").all()


def test_month_must_be_complete_and_covered():
    h = eia930.filter_hourly(balance_csv(skip_hours=40), "BALANCE")
    # 40 of 744 hours missing for SRP (94.6 % < 95 %): dropped; others kept
    m = eia930.monthly(h, date(2026, 8, 10))
    assert "srp" not in set(m["area"]) and "pjm" in set(m["area"])
    # a month is only used COMPLETE_DAYS after its end
    assert eia930.monthly(h, date(2026, 8, 1)).empty
    # a partial month (data so far) is never used
    part = eia930.filter_hourly(balance_csv(days=20, month=8), "BALANCE")
    assert eia930.monthly(part, date(2026, 9, 30)).empty


def test_filter_rejects_missing_columns():
    bad = b'"Balancing Authority","Data Date","Hour Number","Demand (MW)"\nPJM,07/01/2026,1,5\n'
    with pytest.raises(ValueError):
        eia930.filter_hourly(bad, "BALANCE")


def test_file_list():
    got = eia930.files("BALANCE", date(2016, 7, 1))
    assert got == [(2015, 2), (2016, 1), (2016, 2)]
    assert eia930.file_name("SUBREGION", 2018, 2) == "EIA930_SUBREGION_2018_Jul_Dec.csv"
    assert eia930.files("SUBREGION", date(2026, 11, 23))[0] == (2018, 2)


def test_fetch_keeps_contiguous_run(monkeypatch):
    periods = [pd.Period(p, "M") for p in ["2015-07", "2015-08", "2015-10", "2015-11", "2015-12"]]
    df = pd.DataFrame({"area": "srp", "period": periods, "avg_mw": [1.0, 2, 3, 4, 5], "peak_mw": 1.0})
    monkeypatch.setattr(eia930, "all_monthly", lambda: df)
    s = eia930.fetch("srp", "avg_mw")
    assert [str(p) for p in s.index] == ["2015-10", "2015-11", "2015-12"]


def test_catalog_entries():
    assert len(eia930_series.SPECS) == 12
    assert catalog.validate(eia930_series.SPECS) == []
    assert all(s.publish and s.freq == "M" for s in eia930_series.SPECS)


def test_glitches_are_removed_before_peak():
    h = eia930.filter_hourly(balance_csv(), "BALANCE")
    i = h.index[(h["area"] == "pjm")][100]
    h.loc[i, "mw"] = 224345.0  # single-hour spike
    j = h.index[(h["area"] == "soco")][50:52]
    h.loc[j, "mw"] = 0.0  # zeros
    m = eia930.monthly(h, date(2026, 8, 10)).set_index("area")
    assert m.loc["pjm", "peak_mw"] == 100024
    assert m.loc["soco", "avg_mw"] == pytest.approx(30012.5, abs=0.1)
