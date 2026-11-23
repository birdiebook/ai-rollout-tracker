"""R2 independent review of the extracted company guidance (B2): pinned values read from the sources themselves.

Evidence was read on 2026-11-23 from the original documents on www.sec.gov (re-fetched, not the E1 cache) and from
EDGAR's submissions API (filingDate, acceptanceDateTime); see docs/granskning/r2_guidance.md. Only numbers and
references are kept here, never source text.

Tests marked xfail(strict=True) demonstrate a real error in the extraction; they turn into failures once the
error is fixed, so the fix must also remove the mark. No network.
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import observations

from conftest import real_table_exists
from ai_tracker.sources import guidance_capex as gc


def bug(reason: str):
    return pytest.mark.xfail(strict=True, reason=reason)


@pytest.fixture(scope="module")
def capex() -> pd.DataFrame:
    return gc.load()


# ------------------------------------------------------------------ 1. capex rows that B2 uses (all of them)

# (id, value_lo, value_hi, guided calendar year, EDGAR filingDate, EDGAR acceptanceDateTime, accession)
# Every Meta value is from the 8-K EX-99.1 "CFO outlook commentary" (meta-12: 8-K Item 7.01 of 2022-11-09); the
# Alphabet values from the 8-K EX-99.1 (googl-15: 8-K Item 7.01/8.01, equity offering). No earlier EDGAR document
# states any of these values (all Meta and Alphabet 8-Ks 2020-07..2026-11 were scanned).
B2_ROWS = [
    ("meta-01", 21000, 23000, 2021, "2020-10-29", "2020-10-29T20:07:58.000Z", "0001326801-20-000081"),
    ("meta-02", 21000, 23000, 2021, "2021-01-27", "2021-01-27T21:08:08.000Z", "0001326801-21-000011"),
    ("meta-03", 19000, 21000, 2021, "2021-04-28", "2021-04-28T20:09:19.000Z", "0001326801-21-000031"),
    ("meta-04", 19000, 21000, 2021, "2021-07-28", "2021-07-28T20:08:06.000Z", "0001326801-21-000047"),
    ("meta-05", 19000, 19000, 2021, "2021-10-25", "2021-10-25T20:08:12.000Z", "0001326801-21-000062"),
    ("meta-06", 29000, 34000, 2022, "2021-10-25", "2021-10-25T20:08:12.000Z", "0001326801-21-000062"),
    ("meta-07", 29000, 34000, 2022, "2022-02-02", "2022-02-02T21:08:34.000Z", "0001326801-22-000015"),
    ("meta-08", 29000, 34000, 2022, "2022-04-27", "2022-04-27T20:07:54.000Z", "0001326801-22-000054"),
    ("meta-09", 30000, 34000, 2022, "2022-07-27", "2022-07-27T20:07:22.000Z", "0001326801-22-000079"),
    ("meta-10", 32000, 33000, 2022, "2022-10-26", "2022-10-26T20:19:09.000Z", "0001326801-22-000105"),
    ("meta-11", 34000, 39000, 2023, "2022-10-26", "2022-10-26T20:19:09.000Z", "0001326801-22-000105"),
    ("meta-12", 34000, 37000, 2023, "2022-11-09", "2022-11-09T11:14:36.000Z", "0001326801-22-000116"),
    ("meta-13", 30000, 33000, 2023, "2023-02-01", "2023-02-01T21:22:15.000Z", "0001326801-23-000008"),
    ("meta-14", 30000, 33000, 2023, "2023-04-26", "2023-04-26T20:18:04.000Z", "0001326801-23-000063"),
    ("meta-15", 27000, 30000, 2023, "2023-07-26", "2023-07-26T20:06:51.000Z", "0001326801-23-000089"),
    ("meta-17", 27000, 29000, 2023, "2023-10-25", "2023-10-25T20:20:51.000Z", "0001326801-23-000100"),
    ("meta-18", 30000, 35000, 2024, "2023-10-25", "2023-10-25T20:20:51.000Z", "0001326801-23-000100"),
    ("meta-19", 30000, 37000, 2024, "2024-02-01", "2024-02-01T21:10:29.000Z", "0001326801-24-000010"),
    ("meta-20", 35000, 40000, 2024, "2024-04-24", "2024-04-24T20:07:26.000Z", "0001326801-24-000044"),
    ("meta-22", 37000, 40000, 2024, "2024-07-31", "2024-07-31T20:11:20.000Z", "0001326801-24-000065"),
    ("meta-24", 38000, 40000, 2024, "2024-10-30", "2024-10-30T20:08:12.000Z", "0001326801-24-000077"),
    ("meta-26", 60000, 65000, 2025, "2025-01-29", "2025-01-29T21:47:14.000Z", "0001326801-25-000014"),
    ("meta-27", 64000, 72000, 2025, "2025-04-30", "2025-04-30T20:16:00.000Z", "0001326801-25-000050"),
    ("meta-28", 66000, 72000, 2025, "2025-07-30", "2025-07-30T20:13:01.000Z", "0001628280-25-036719"),
    ("meta-30", 70000, 72000, 2025, "2025-10-29", "2025-10-29T20:08:34.000Z", "0001628280-25-047114"),
    ("meta-32", 115000, 135000, 2026, "2026-01-28", "2026-01-28T21:04:20.000Z", "0001628280-26-003832"),
    ("meta-33", 125000, 145000, 2026, "2026-04-29", "2026-04-29T20:05:41.000Z", "0001628280-26-028364"),
    ("meta-34", 130000, 145000, 2026, "2026-07-29", "2026-07-29T20:03:23.000Z", "0001628280-26-050596"),
    ("meta-35", 135000, 145000, 2026, "2026-10-21", "2026-10-21T20:03:35.000Z", "0001628280-26-066700"),
    ("googl-05", 75000, 75000, 2025, "2025-02-04", "2025-02-04T21:01:27.000Z", "0001652044-25-000010"),
    ("googl-09", 91000, 93000, 2025, "2025-10-29", "2025-10-29T20:01:48.000Z", "0001652044-25-000087"),
    ("googl-12", 175000, 185000, 2026, "2026-02-04", "2026-02-04T21:01:37.000Z", "0001652044-26-000012"),
    ("googl-15", 180000, 190000, 2026, "2026-06-04", "2026-06-04T21:07:39.000Z", "0001193125-26-257724"),
]
B2_DEFINITION = {"meta": "META_CAPEX_INCL_FL", "googl": "GOOGL_CAPEX"}


@pytest.mark.parametrize("rid,lo,hi,year,filed,accepted,accession", B2_ROWS)
def test_b2_capex_row_matches_source(capex, rid, lo, hi, year, filed, accepted, accession):
    r = capex.set_index("id").loc[rid]
    assert (r["value_lo"], r["value_hi"]) == (lo, hi)
    assert r["unit"] == "MUSD" and r["horizon"] == "CY" and r["period"] == str(year)
    assert (r["period_start"], r["period_end"]) == (f"{year}-01-01", f"{year}-12-31")
    assert r["definition"] == B2_DEFINITION[r["company"]]
    assert (r["filed"], r["accepted"], r["accession"]) == (filed, accepted, accession)
    assert r["known_from"] == pd.Timestamp(filed)


def test_b2_rows_are_all_quantitative_meta_and_alphabet_cy_rows(capex):
    sel = capex[capex["company"].isin(["meta", "googl"]) & (capex["horizon"] == "CY") & (capex["kind"] != "direction")]
    added_by_fix = sel[sel["accession"] == "0001652044-25-000056"]  # R2-F1, see below
    assert set(sel["id"]) - set(added_by_fix["id"]) == {r[0] for r in B2_ROWS}


# R2-F1. Alphabet's Q2 2025 earnings release (8-K EX-99.1, accession 0001652044-25-000056, googexhibit991q22025.htm,
# filed 2025-07-23, accepted 2025-07-23T20:01:33Z) states, in the CEO quote, that capital expenditures in 2025 are
# raised to approximately $85 billion. The CSV has no row for it and docs/kallor/guidance.md says the July 2025
# raise is not in EDGAR. B2 for Alphabet 2025Q3 (forecast date 2025-10-20) therefore uses the stale 75 bn.
def test_alphabet_2025_raise_to_85bn_is_in_the_csv(capex):
    r = capex[(capex["company"] == "googl") & (capex["horizon"] == "CY") & (capex["period"] == "2025")
              & (capex["kind"] == "approx") & (capex["value_lo"] == 85000)]
    assert len(r) == 1
    r = r.iloc[0]
    assert (r["filed"], r["accession"], r["definition"]) == ("2025-07-23", "0001652044-25-000056", "GOOGL_CAPEX")
    assert r["value_hi"] == 85000 and r["unit"] == "MUSD"


def test_alphabet_2025_guidance_known_at_2025q3_forecast_date(capex):
    for measure in ("lo", "hi"):
        s = gc.series_frame(capex, "googl", "CY", measure)
        known = s[(s["period"] == "2025") & (s["known_from"] <= pd.Timestamp("2025-10-20"))]
        assert known.sort_values("known_from").iloc[-1]["value"] == 85000


# ------------------------------------------------------------------ 2. sampled non-B2 rows (seed 20261124, 20 %)

SAMPLE = {  # id -> (kind, value_lo or direction_code, direction_base, period, filed); all confirmed in the source
    "amzn-05": ("direction", 2, "yoy", "2024", "2024-05-01"),
    "amzn-06": ("direction", 2, "yoy", "2024", "2024-08-02"),
    "amzn-10": ("direction", 1, "yoy", "2025", "2025-08-01"),
    "amzn-13": ("approx", 200000, "", "2026", "2026-02-05"),
    "amzn-15": ("approx", 200000, "", "2026", "2026-04-09"),
    "googl-07": ("direction", 1, "yoy", "2025", "2025-04-25"),
    "googl-08": ("direction", 1, "yoy", "2025", "2025-07-24"),
    "googl-16": ("direction", 2, "yoy", "2027", "2026-06-04"),
    "meta-25": ("direction", 2, "yoy", "2025", "2024-10-30"),
    "msft-04": ("direction", 1, "qoq", "2023Q1", "2023-01-24"),
    "msft-06": ("direction", 1, "qoq", "2023Q3", "2023-07-25"),
    "msft-08": ("direction", 2, "qoq", "2024Q1", "2024-01-30"),
    "msft-10": ("direction", 1, "prior_fy", "FY2025", "2024-04-25"),
    "msft-16": ("direction", -1, "growth_vs_prior", "FY2026", "2025-01-29"),
}


def test_sample_draw_is_reproducible(capex):
    b2 = capex["id"].isin([r[0] for r in B2_ROWS])
    drawn = capex[~b2].sample(frac=0.2, random_state=20261124)["id"]
    if len(capex) == 101:  # the CSV as reviewed; a fix adds rows and changes the draw
        assert set(drawn) == set(SAMPLE)


@pytest.mark.parametrize("rid", sorted(SAMPLE))
def test_sampled_row_matches_source(capex, rid):
    kind, v, base, period, filed = SAMPLE[rid]
    r = capex.set_index("id").loc[rid]
    assert (r["kind"], r["period"], r["filed"]) == (kind, period, filed)
    if kind == "direction":
        assert (int(r["direction_code"]), r["direction_base"]) == (v, base)
    else:
        assert r["value_lo"] == v == r["value_hi"]


def test_no_capex_row_dated_before_its_edgar_acceptance(capex):
    """known_from (= filed, the EDGAR filingDate) is never before the acceptance date in New York time.

    The accepted column was checked equal to EDGAR's acceptanceDateTime for all 72 rows with an accession
    (73 after the R2-F1 row was added).
    """
    d = capex[capex["accepted"] != ""]
    acc_ny = pd.to_datetime(d["accepted"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    assert (d["known_from"] >= acc_ny.dt.normalize()).all()
    assert len(d) == 73


# ------------------------------------------------------------------ 3. TSMC: sampled quarters, read by hand

# quarter -> [(first filing date, lo, hi)] revenue vintages in the stated currency (bn), and FX vintages
# [(date, fx)]. Read from the 6-K press release / presentation (EX-99.1/99.2 from 2019-10) on www.sec.gov.
TSMC = {
    "2006Q2": ("TWD", [("2006-04-28", 80, 82)], []),  # consolidated range; parent-only 79-81 also stated
    "2006Q4": ("TWD", [("2006-10-26", 74, 76)], []),
    "2008Q3": ("TWD", [("2008-07-31", 90, 92)], [("2008-08-01", 30.20)]),
    "2009Q1": ("TWD", [("2009-01-22", 32, 35), ("2009-03-10", 36, 38)], [("2009-01-23", 32.66)]),
    "2009Q2": ("TWD", [("2009-04-30", 71, 74)], [("2009-05-04", 33.62)]),
    "2010Q2": ("TWD", [("2010-04-27", 100, 102)], [("2010-04-28", 31.30)]),
    "2010Q3": ("TWD", [("2010-07-29", 109, 111)], [("2010-07-30", 31.87)]),
    "2012Q2": ("TWD", [("2012-04-26", 126, 128)], [("2012-04-26", 29.58)]),
    "2013Q3": ("TWD", [("2013-07-18", 161, 164)], [("2013-07-18", 29.83)]),
    "2013Q4": ("TWD", [("2013-10-17", 144, 147)], [("2013-10-17", 29.5)]),
    "2017Q2": ("TWD", [("2017-04-13", 213, 216)], [("2017-04-13", 30.5)]),
    "2017Q3": ("USD", [("2017-07-13", 8.12, 8.22)], [("2017-07-13", 30.3)]),
    "2017Q4": ("USD", [("2017-10-19", 9.10, 9.20)], [("2017-10-19", 30.3)]),
    "2018Q1": ("USD", [("2018-01-18", 8.40, 8.50)], [("2018-01-18", 29.6)]),
    "2018Q3": ("USD", [("2018-07-19", 8.45, 8.55)], [("2018-07-19", 30.5)]),
    "2019Q1": ("USD", [("2019-01-17", 7.3, 7.4), ("2019-02-15", 7.0, 7.1)],
               [("2019-01-17", 30.8), ("2019-01-18", 30.6)]),  # release 30.8, presentation 30.6 (source)
    "2020Q1": ("USD", [("2020-01-16", 10.2, 10.3)], [("2020-01-16", 29.9)]),
    "2021Q1": ("USD", [("2021-01-14", 12.7, 13.0)], [("2021-01-14", 27.95)]),
    "2022Q4": ("USD", [("2022-10-13", 19.9, 20.7)], [("2022-10-13", 31.5)]),
    "2023Q3": ("USD", [("2023-07-20", 16.7, 17.5)], [("2023-07-20", 30.8)]),
    "2024Q1": ("USD", [("2024-01-18", 18.0, 18.8)], [("2024-01-18", 31.1)]),
    "2024Q3": ("USD", [("2024-07-18", 22.4, 23.2)], [("2024-07-18", 32.5)]),
    "2025Q3": ("USD", [("2025-07-17", 31.8, 33.0)], [("2025-07-17", 29.0)]),
    "2026Q1": ("USD", [("2026-01-15", 34.6, 35.8)], [("2026-01-15", 31.6)]),
    "2026Q2": ("USD", [("2026-04-16", 39.0, 40.2)], [("2026-04-16", 31.7)]),
    "2026Q4": ("USD", [("2026-10-15", 52.3, 54.3)], [("2026-10-15", 31.8)]),
}

def needs_table(f):
    """Reads the real observation table (shared base + track view in a track worktree)."""
    return pytest.mark.real_data(pytest.mark.skipif(not real_table_exists(), reason="data/observations.parquet not built")(f))


@pytest.fixture(scope="module")
def stored() -> pd.DataFrame:
    o = observations.load()
    o = o[o["series"].str.startswith("tsmc_guid_")].copy()
    o["period"] = o["period"].astype(str)
    return o


def _vintages(stored, series, quarter):
    d = stored[(stored["series"] == series) & (stored["period"] == quarter)].sort_values("known_from")
    return [(pd.Timestamp(k).strftime("%Y-%m-%d"), round(v, 6)) for k, v in zip(d["known_from"], d["value"])]


@needs_table
@pytest.mark.parametrize("quarter", sorted(TSMC))
def test_tsmc_guidance_matches_hand_reading(stored, quarter):
    cur, revs, fxs = TSMC[quarter]
    c = cur.lower()
    assert _vintages(stored, f"tsmc_guid_rev_{c}_lo", quarter) == [(d, round(lo * 1000, 6)) for d, lo, _ in revs]
    assert _vintages(stored, f"tsmc_guid_rev_{c}_hi", quarter) == [(d, round(hi * 1000, 6)) for d, _, hi in revs]
    other = "usd" if c == "twd" else "twd"
    assert _vintages(stored, f"tsmc_guid_rev_{other}_lo", quarter) == []
    assert _vintages(stored, "tsmc_guid_fx", quarter) == [(d, fx) for d, fx in fxs]
