"""R5 independent review of the agent-extracted values (B4, A3, D1, B6): pinned values read from the sources.

Evidence was read on 2026-11-23 from the original documents, re-fetched from www.sec.gov and www.microsoft.com
with the honest client (not the extracting tracks' caches), and dated with EDGAR's submissions API (filingDate,
acceptanceDateTime); see docs/granskning/r5_extraktion.md. B6's newsroom rows could not be re-fetched (the owner
paused automated fetching from anthropic.com on 2026-11-23) and are pinned from B6's stored sentences only. Only
numbers, ids and SHA-256 references are kept here, never source text.

Tests marked xfail(strict=True) demonstrate a real error or a missing row; they turn into failures once the CSV is
corrected, so the fix must also remove the mark. No network.
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import config, observations

from conftest import real_table_exists

CURATED = config.REPO / "curated"


def bug(reason: str):
    return pytest.mark.xfail(strict=True, reason=reason)


def _csv(name: str) -> pd.DataFrame:
    return pd.read_csv(CURATED / f"{name}.csv", dtype=str)


@pytest.fixture(scope="module")
def kpis() -> pd.DataFrame:
    return _csv("ai_kpis")


@pytest.fixture(scope="module")
def leases() -> pd.DataFrame:
    return _csv("lease_commitments")


@pytest.fixture(scope="module")
def plans() -> pd.DataFrame:
    return _csv("plans")


@pytest.fixture(scope="module")
def labrev() -> pd.DataFrame:
    return _csv("lab_revenue")


@pytest.fixture(scope="module")
def capex() -> pd.DataFrame:
    return _csv("guidance_capex")


def _row(df: pd.DataFrame, row_id: str) -> pd.Series:
    hit = df[df["id"] == row_id]
    assert len(hit) == 1, f"{row_id}: {len(hit)} rows"
    return hit.iloc[0]


# ------------------------------------------------------------------ pinned values (verified correct by R5)
# Capacity coding (B4): all 33 rows were re-read; these 30 match the locked rules and interpretations.
# (id, code, capacity_time, period, filed)
CAP = [
    ("amzn-cap-2025q3", 2, "current", "2025Q3", "2025-10-30"),
    ("amzn-cap-2025q4", 2, "current", "2025Q4", "2026-02-05"),
    ("amzn-cap-2026q2", 1, "current", "2026Q2", "2026-04-09"),
    ("amzn-capf-2026q2", 1, "forward", "2026Q2", "2026-02-05"),
    ("googl-cap-2026q2", 1, "current", "2026Q2", "2026-06-04"),
    ("msft-cap-2024q1", 1, "current", "2024Q1", "2024-04-25"),
    ("msft-cap-2024q2", 1, "current", "2024Q2", "2024-07-30"),
    ("msft-cap-2024q3", 1, "current", "2024Q3", "2024-10-30"),
    ("msft-cap-2024q4", 1, "current", "2024Q4", "2025-01-29"),
    ("msft-cap-2025q2", 1, "current", "2025Q2", "2025-07-30"),
    ("msft-cap-2025q3", 2, "current", "2025Q3", "2025-10-29"),
    ("msft-cap-2025q4", 1, "current", "2025Q4", "2026-01-28"),
    ("msft-cap-2026q1", 1, "current", "2026Q1", "2026-04-29"),
    ("msft-cap-2026q2", 2, "current", "2026Q2", "2026-07-29"),
    ("msft-cap-2026q3", 1, "current", "2026Q3", "2026-10-28"),
    ("msft-capf-2024q4", 1, "forward", "2024Q4", "2024-07-30"),
    ("msft-capf-2024q4b", 1, "forward", "2024Q4", "2024-10-30"),
    ("msft-capf-2025q1", 1, "forward", "2025Q1", "2025-01-29"),
    ("msft-capf-2025q2", 0, "forward", "2025Q2", "2025-01-29"),
    ("msft-capf-2025q3", 1, "forward", "2025Q3", "2025-04-30"),
    ("msft-capf-2025q4", 1, "forward", "2025Q4", "2025-07-30"),
    ("msft-capf-2026q2", 1, "forward", "2026Q2", "2025-10-29"),
    ("msft-capf-2026q4", 1, "forward", "2026Q4", "2026-04-29"),
    ("nvda-cap-2022q4", -2, "current", "2022Q4", "2023-02-22"),
    ("nvda-cap-2024q1", 1, "current", "2024Q1", "2024-05-29"),
    ("nvda-cap-2024q3", 1, "current", "2024Q3", "2024-11-20"),
    ("nvda-capf-2024q1", 1, "forward", "2024Q1", "2024-02-21"),
    ("nvda-capf-2024q4", 2, "forward", "2024Q4", "2024-05-29"),
    ("nvda-capf-2025q1", 1, "forward", "2025Q1", "2024-05-29"),
    ("nvda-capf-2025q2", 1, "forward", "2025Q2", "2024-11-20"),
]
# B4 KPIs, 20 % sample of the 136 non-capacity rows (seed 20261124): (id, definition, kind, value_lo, period, filed)
KPI_SAMPLE = [
    ("amzn-chip-02", "AMZN_CHIPS_RUNRATE", "min", 20000.0, "2026-04", "2026-04-29"),
    ("googl-aio-01", "GOOGL_AI_OVERVIEWS_MONTHLY_USERS", "point", 1500.0, "2025-04", "2025-04-24"),
    ("googl-tok-01", "GOOGL_API_TOKENS_PER_MIN", "point", 7.0, "2025-10", "2025-10-29"),
    ("msft-airr-00", "MSFT_AI_BUSINESS_RUNRATE_EXPECTED", "min", 10000.0, "2024-12", "2024-10-30"),
    ("msft-aimau-02", "MSFT_AI_FEATURES_MAU", "point", 900.0, "2025-10", "2025-10-29"),
    ("msft-aai-01", "MSFT_AZURE_AI_CUSTOMERS", "point", 53000.0, "2024-01", "2024-01-30"),
    ("msft-aai-02", "MSFT_AZURE_AI_CUSTOMERS", "min", 60000.0, "2024-07", "2024-07-30"),
    ("msft-aip-2023q4", "MSFT_AZURE_AI_PTS_V1", "approx", 1.0, "2023Q2", "2023-07-25"),
    ("msft-aip-2025q1", "MSFT_AZURE_AI_PTS_V2", "point", 12.0, "2024Q3", "2024-10-30"),
    ("msft-aip-2025q2", "MSFT_AZURE_AI_PTS_V2", "point", 13.0, "2024Q4", "2025-01-29"),
    ("msft-aip-2025q3", "MSFT_AZURE_AI_PTS_V2", "point", 16.0, "2025Q1", "2025-04-30"),
    ("msft-az-2023-07-25-cc", "MSFT_AZURE_GROWTH_CC_V1", "point", 27.0, "2023Q2", "2023-07-25"),
    ("msft-az-r24-q1c", "MSFT_AZURE_GROWTH_CC_V2", "point", 30.0, "2023Q3", "2024-08-21"),
    ("msft-az-2025-04-30-cc", "MSFT_AZURE_GROWTH_CC_V2", "point", 35.0, "2025Q1", "2025-04-30"),
    ("msft-az-2025-10-29-cc", "MSFT_AZURE_GROWTH_CC_V2", "point", 39.0, "2025Q3", "2025-10-29"),
    ("msft-az-2026-04-29-cc", "MSFT_AZURE_GROWTH_CC_V2", "point", 39.0, "2026Q1", "2026-04-29"),
    ("msft-az-2025-04-30-rep", "MSFT_AZURE_GROWTH_V2", "point", 33.0, "2025Q1", "2025-04-30"),
    ("msft-az-2025-07-30-rep", "MSFT_AZURE_GROWTH_V2", "point", 39.0, "2025Q2", "2025-07-30"),
    ("msft-aoai-03", "MSFT_AZURE_OPENAI_CUSTOMERS", "min", 18000.0, "2023-10", "2023-10-24"),
    ("msft-cps-01", "MSFT_COPILOT_STUDIO_ORGS", "point", 30000.0, "2024-04", "2024-04-25"),
    ("msft-ftok-01", "MSFT_FOUNDRY_TOKENS_FY", "min", 500.0, "2025", "2025-07-30"),
    ("msft-ghbo-02", "MSFT_GHCP_BUSINESS_ORGS", "min", 27000.0, "2023-07", "2023-07-25"),
    ("msft-lirr-01", "MSFT_LINKEDIN_AI_RUNRATE", "min", 450.0, "2026-04", "2026-04-29"),
    ("msft-m365s-01", "MSFT_M365_COPILOT_PAID_SEATS", "point", 15.0, "2026-01", "2026-01-28"),
    ("msft-m365s-03", "MSFT_M365_COPILOT_PAID_SEATS", "min", 30.0, "2026-07", "2026-07-29"),
    ("msft-ppai-05", "MSFT_POWER_PLATFORM_AI_ORGS", "min", 480000.0, "2024-07", "2024-07-30"),
    ("msft-ppcp-01", "MSFT_POWER_PLATFORM_COPILOT_ORGS", "min", 126000.0, "2023-10", "2023-10-24"),
]
# A3, 20 % sample (seed 20261124): (id, lease_type, MUSD, balance date, filed)
LEASE_SAMPLE = [
    ("amzn-2022-03-31-total", "total", 33770.0, "2022-03-31", "2022-04-29"),
    ("amzn-2023-06-30-total", "total", 23989.0, "2023-06-30", "2023-08-04"),
    ("amzn-2024-09-30-total", "total", 50335.0, "2024-09-30", "2024-11-01"),
    ("amzn-2025-12-31-total", "total", 96373.0, "2025-12-31", "2026-02-06"),
    ("crwv-2025-03-31-total", "total", 19900.0, "2025-03-31", "2025-05-15"),
    ("crwv-2026-06-30-total", "total", 35500.0, "2026-06-30", "2026-08-12"),
    ("crwv-2026-09-30-total", "total", 47400.0, "2026-09-30", "2026-11-12"),
    ("googl-2019-03-31-total", "total", 4400.0, "2019-03-31", "2019-04-30"),
    ("googl-2022-09-30-total", "total", 4100.0, "2022-09-30", "2022-10-26"),
    ("googl-2022-12-31-long_term", "long_term", 3100.0, "2022-12-31", "2023-02-03"),
    ("googl-2023-12-31-short_term", "short_term", 657.0, "2023-12-31", "2024-01-31"),
    ("googl-2024-03-31-total", "total", 3600.0, "2024-03-31", "2024-04-26"),
    ("googl-2024-12-31-long_term", "long_term", 6500.0, "2024-12-31", "2025-02-05"),
    ("googl-2026-09-30-total", "total", 130500.0, "2026-09-30", "2026-10-29"),
    ("meta-2019-06-30-finance", "finance", 471.0, "2019-06-30", "2019-07-25"),
    ("meta-2020-06-30-operating", "operating", 4910.0, "2020-06-30", "2020-07-31"),
    ("meta-2020-06-30-finance", "finance", 364.0, "2020-06-30", "2020-07-31"),
    ("meta-2020-12-31-finance", "finance", 443.0, "2020-12-31", "2021-01-28"),
    ("meta-2021-03-31-finance", "finance", 543.0, "2021-03-31", "2021-04-29"),
    ("meta-2021-06-30-operating", "operating", 5930.0, "2021-06-30", "2021-07-29"),
    ("meta-2021-06-30-finance", "finance", 887.0, "2021-06-30", "2021-07-29"),
    ("meta-2022-03-31-finance", "finance", 1630.0, "2022-03-31", "2022-04-28"),
    ("meta-2022-06-30-finance", "finance", 1630.0, "2022-06-30", "2022-07-28"),
    ("meta-2022-12-31-operating", "operating", 8360.0, "2022-12-31", "2023-02-02"),
    ("meta-2023-06-30-operating", "operating", 9620.0, "2023-06-30", "2023-07-27"),
    ("meta-2025-06-30-total", "total", 52560.0, "2025-06-30", "2025-07-31"),
    ("meta-2026-06-30-total", "total", 278990.0, "2026-06-30", "2026-07-30"),
    ("msft-2018-12-31-finance", "finance", 6400.0, "2018-12-31", "2019-01-30"),
    ("msft-2019-09-30-operating", "operating", 2300.0, "2019-09-30", "2019-10-23"),
    ("msft-2020-06-30-operating", "operating", 3400.0, "2020-06-30", "2020-07-30"),
    ("msft-2020-06-30-finance", "finance", 3500.0, "2020-06-30", "2020-07-30"),
    ("msft-2020-09-30-operating", "operating", 4300.0, "2020-09-30", "2020-10-27"),
    ("msft-2020-12-31-operating", "operating", 4000.0, "2020-12-31", "2021-01-26"),
    ("msft-2021-06-30-finance", "finance", 7300.0, "2021-06-30", "2021-07-29"),
    ("msft-2021-09-30-finance", "finance", 5900.0, "2021-09-30", "2021-10-26"),
    ("msft-2023-09-30-finance", "finance", 75100.0, "2023-09-30", "2023-10-24"),
    ("msft-2023-12-31-operating", "operating", 7500.0, "2023-12-31", "2024-01-30"),
    ("msft-2026-06-30-total", "total", 329100.0, "2026-06-30", "2026-07-29"),
]
# D1, 20 % sample (seed 20261124): (id, definition, kind, lo, hi, direction_code, period_end, filed)
PLANS_SAMPLE = [
    ("crwv-p001", "CRWV_ACTIVE_POWER", "min", 360.0, 360.0, None, "2024-12-31", "2025-03-03"),
    ("crwv-p007", "CRWV_CONTRACTED_POWER", "approx", 1600.0, 1600.0, None, "2025-03-31", "2025-05-14"),
    ("crwv-p016", "CRWV_ACTIVE_POWER", "min", 850.0, 850.0, None, "2025-12-31", "2026-02-26"),
    ("crwv-p018", "CRWV_LEASE_EQUIP_COMMIT", "range", 1100.0, 1700.0, None, "2025-12-31", "2026-03-02"),
    ("crwv-p021", "CRWV_ACTIVE_POWER", "min", 1000.0, 1000.0, None, "2026-03-31", "2026-05-07"),
    ("crwv-p032", "CRWV_ACTIVE_POWER", "min", 1700.0, 1700.0, None, "2026-09-30", "2026-11-10"),
    ("crwv-p033", "CRWV_CONTRACTED_POWER", "min", 4600.0, 4600.0, None, "2026-09-30", "2026-11-10"),
    ("crwv-p037", "CRWV_LEASE_EQUIP_COMMIT", "range", 188.0, 817.0, None, "2026-09-30", "2026-11-12"),
    ("googl-p003", "GOOGL_CLOUD_BACKLOG", "min", 460000.0, 460000.0, None, "2026-03-31", "2026-04-29"),
    ("meta-p004", "META_CAPEX_INCL_FL", "range", 34000.0, 39000.0, None, "2023-12-31", "2022-10-26"),
    ("meta-p010", "META_CAPEX_INCL_FL", "direction", None, None, 1, "2024-12-31", "2023-07-26"),
    ("meta-p018", "META_CAPEX_INCL_FL", "direction", None, None, 2, "2025-12-31", "2024-07-31"),
    ("meta-p019", "META_NONCANCEL_COMMIT", "reported", 19820.0, 19820.0, None, "2024-06-30", "2024-08-01"),
    ("meta-p020", "META_CAPEX_INCL_FL", "direction", None, None, 2, "2025-12-31", "2024-08-01"),
    ("meta-p028", "META_NONCANCEL_COMMIT", "reported", 27950.0, 27950.0, None, "2025-06-30", "2025-07-31"),
    ("meta-p035", "META_NONCANCEL_COMMIT", "reported", 454520.0, 454520.0, None, "2026-09-30", "2026-10-22"),
    ("msft-p007", "MSFT_COMMERCIAL_RPO", "reported", 212000.0, 212000.0, None, "2023-09-30", "2023-10-24"),
    ("msft-p009", "MSFT_COMMERCIAL_RPO", "reported", 235000.0, 235000.0, None, "2024-03-31", "2024-04-25"),
    ("msft-p010", "MSFT_CAPEX_INCL_FL", "direction", None, None, 1, "2025-06-30", "2024-04-25"),
    ("msft-p016", "MSFT_CAPEX_INCL_FL", "direction", None, None, -1, "2026-06-30", "2025-04-30"),
    ("msft-p021", "MSFT_COMMERCIAL_RPO", "reported", 625000.0, 625000.0, None, "2025-12-31", "2026-01-28"),
    ("msft-p023", "MSFT_POWER_ADDED_Q", "reported", 1000.0, 1000.0, None, "2026-03-31", "2026-04-29"),
    ("orcl-p001", "ORCL_DC_CAPACITY", "point", 2.0, 2.0, None, "2025-12-31", "2025-03-10"),
    ("orcl-p003", "ORCL_CAPEX", "point", 50000.0, 50000.0, None, "2026-05-31", "2026-03-10"),
    ("orcl-p008", "ORCL_UNCOND_OBLIG_1Y", "reported", 34150.0, 34150.0, None, "2026-08-31", "2026-09-11"),
]
# B6, all 14 rows: (id, scope, measure, qualifier, MUSD, period_end, known_from)
LAB_ROWS = [
    ("ant-01", "company", "RUN_RATE", "as_stated", 87.0, "2024-01-01", "2025-09-26"),
    ("ant-02", "company", "RUN_RATE", "approx", 1000.0, "2025-01-01", "2025-09-02"),
    ("ant-03", "company", "RUN_RATE", "over", 5000.0, "2025-08-31", "2025-09-02"),
    ("ant-04", "company", "RUN_RATE", "over", 5000.0, "2025-08-31", "2025-09-26"),
    ("ant-05", "company", "RUN_RATE", "as_stated", 7000.0, "2025-10-21", "2025-10-21"),
    ("ant-06", "company", "RUN_RATE", "approx", 9000.0, "2025-12-31", "2026-04-06"),
    ("ant-07", "company", "RUN_RATE", "as_stated", 14000.0, "2026-02-12", "2026-02-12"),
    ("ant-08", "company", "RUN_RATE", "over", 30000.0, "2026-04-06", "2026-04-06"),
    ("ant-09", "company", "RUN_RATE", "over", 30000.0, "2026-04-20", "2026-04-20"),
    ("ant-10", "company", "RUN_RATE", "over", 47000.0, "2026-05-28", "2026-05-28"),
    ("ant-11", "company", "RUN_RATE_S1", "approx", 81000.0, "2026-10-31", "2026-11-10"),
    ("ant-cc-01", "claude_code", "RUN_RATE", "over", 500.0, "2025-09-02", "2025-09-02"),
    ("ant-cc-02", "claude_code", "RUN_RATE", "as_stated", 1000.0, "2025-11-30", "2025-12-03"),
    ("ant-cc-03", "claude_code", "RUN_RATE", "over", 2500.0, "2026-02-12", "2026-02-12"),
]


@pytest.mark.parametrize("row_id,code,time,period,filed", CAP)
def test_capacity_row_matches_source(kpis, row_id, code, time, period, filed):
    r = _row(kpis, row_id)
    assert (int(r["code"]), r["capacity_time"], r["period"], r["filed"]) == (code, time, period, filed)


@pytest.mark.parametrize("row_id,definition,kind,value,period,filed", KPI_SAMPLE)
def test_kpi_sample_row_matches_source(kpis, row_id, definition, kind, value, period, filed):
    r = _row(kpis, row_id)
    assert (r["definition"], r["kind"], float(r["value_lo"]), r["period"], r["filed"]) == (
        definition, kind, value, period, filed)


@pytest.mark.parametrize("row_id,lease_type,value,period,filed", LEASE_SAMPLE)
def test_lease_sample_row_matches_source(leases, row_id, lease_type, value, period, filed):
    r = _row(leases, row_id)
    assert (r["lease_type"], float(r["value"]), r["period"], r["filed"]) == (lease_type, value, period, filed)


def _f(x):
    return None if pd.isna(x) else float(x)


@pytest.mark.parametrize("row_id,definition,kind,lo,hi,direction,period_end,filed", PLANS_SAMPLE)
def test_plans_sample_row_matches_source(plans, row_id, definition, kind, lo, hi, direction, period_end, filed):
    r = _row(plans, row_id)
    d = None if pd.isna(r["direction_code"]) else int(r["direction_code"])
    assert (r["definition"], r["kind"], _f(r["value_lo"]), _f(r["value_hi"]), d, r["period_end"], r["filed"]) == (
        definition, kind, lo, hi, direction, period_end, filed)


# B6: ant-11 (S-1/A) re-fetched from sec.gov; the 13 newsroom rows checked only against B6's stored sentences.
@pytest.mark.parametrize("row_id,scope,measure,qualifier,value,period_end,known_from", LAB_ROWS)
def test_lab_revenue_row_matches_stored_sentence(labrev, row_id, scope, measure, qualifier, value, period_end,
                                                 known_from):
    r = _row(labrev, row_id)
    assert (r["scope"], r["measure"], r["qualifier"], float(r["value"]), r["period_end"], r["known_from"]) == (
        scope, measure, qualifier, value, period_end, known_from)


# Nvidia revenue outlook used by N3 (B2): every quarter 2017Q2-2026Q4, hand-read from the re-fetched 8-K
# (EX-99.1 and EX-99.2). (period, midpoint MUSD, band %, first filing date). One vintage each: no 8-K (any item)
# in 2017-04..2026-11 restates a different revenue figure for a quarter in progress.
NVDA_N3 = [
    ("2017Q2", 1950.0, 2.0, "2017-05-09"),
    ("2017Q3", 2350.0, 2.0, "2017-08-10"),
    ("2017Q4", 2650.0, 2.0, "2017-11-09"),
    ("2018Q1", 2900.0, 2.0, "2018-02-08"),
    ("2018Q2", 3100.0, 2.0, "2018-05-10"),
    ("2018Q3", 3250.0, 2.0, "2018-08-16"),
    ("2018Q4", 2700.0, 2.0, "2018-11-15"),
    ("2019Q1", 2200.0, 2.0, "2019-02-14"),
    ("2019Q2", 2550.0, 2.0, "2019-05-16"),
    ("2019Q3", 2900.0, 2.0, "2019-08-15"),
    ("2019Q4", 2950.0, 2.0, "2019-11-14"),
    ("2020Q1", 3000.0, 2.0, "2020-02-13"),
    ("2020Q2", 3650.0, 2.0, "2020-05-21"),
    ("2020Q3", 4400.0, 2.0, "2020-08-19"),
    ("2020Q4", 4800.0, 2.0, "2020-11-18"),
    ("2021Q1", 5300.0, 2.0, "2021-02-24"),
    ("2021Q2", 6300.0, 2.0, "2021-05-26"),
    ("2021Q3", 6800.0, 2.0, "2021-08-18"),
    ("2021Q4", 7400.0, 2.0, "2021-11-17"),
    ("2022Q1", 8100.0, 2.0, "2022-02-16"),
    ("2022Q2", 8100.0, 2.0, "2022-05-25"),
    ("2022Q3", 5900.0, 2.0, "2022-08-24"),
    ("2022Q4", 6000.0, 2.0, "2022-11-16"),
    ("2023Q1", 6500.0, 2.0, "2023-02-22"),
    ("2023Q2", 11000.0, 2.0, "2023-05-24"),
    ("2023Q3", 16000.0, 2.0, "2023-08-23"),
    ("2023Q4", 20000.0, 2.0, "2023-11-21"),
    ("2024Q1", 24000.0, 2.0, "2024-02-21"),
    ("2024Q2", 28000.0, 2.0, "2024-05-22"),
    ("2024Q3", 32500.0, 2.0, "2024-08-28"),
    ("2024Q4", 37500.0, 2.0, "2024-11-20"),
    ("2025Q1", 43000.0, 2.0, "2025-02-26"),
    ("2025Q2", 45000.0, 2.0, "2025-05-28"),
    ("2025Q3", 54000.0, 2.0, "2025-08-27"),
    ("2025Q4", 65000.0, 2.0, "2025-11-19"),
    ("2026Q1", 78000.0, 2.0, "2026-02-25"),
    ("2026Q2", 91000.0, 2.0, "2026-05-20"),
    ("2026Q3", 108000.0, 2.0, "2026-08-26"),
    ("2026Q4", 130000.0, 3.0, "2026-11-17"),
]


def real_data(f):
    return pytest.mark.real_data(pytest.mark.skipif(not real_table_exists(), reason="observation table not built")(f))


@pytest.fixture(scope="module")
def nvda_obs() -> dict[str, pd.DataFrame]:
    o = observations.load()
    return {f: o[o["series"] == f"nvda_guid_rev_{f}"] for f in ("mid", "lo", "hi")}


@real_data
@pytest.mark.parametrize("period,mid,band,filed", NVDA_N3)
def test_nvda_outlook_matches_hand_reading(nvda_obs, period, mid, band, filed):
    m = nvda_obs["mid"][nvda_obs["mid"]["period"].astype(str) == period]
    assert len(m) == 1
    assert m["value"].iloc[0] == mid and str(pd.Timestamp(m["known_from"].iloc[0]).date()) == filed
    lo = nvda_obs["lo"][nvda_obs["lo"]["period"].astype(str) == period]["value"].iloc[0]
    hi = nvda_obs["hi"][nvda_obs["hi"]["period"].astype(str) == period]["value"].iloc[0]
    assert lo == pytest.approx(mid * (1 - band / 100)) and hi == pytest.approx(mid * (1 + band / 100))


# ------------------------------------------------------------------ errors found by R5 (xfail until fixed)

# R5-F1: Jensen Huang's "cloud GPUs are sold out" (8-K EX-99.1 2025-11-19, sentence #4) is about the clouds'
# rented GPU capacity, i.e. partners, which interpretation 7 excludes. No own-supply statement in that document.
@bug("R5-F1: nvda-cap-2025q3 codes partner (cloud) capacity, contrary to interpretation 7")
def test_nvda_partner_capacity_not_coded(kpis):
    assert "nvda-cap-2025q3" not in set(kpis["id"])


# R5-F2: interpretation 7 (excess supply of Data Center products = -2) is not applied consistently.
# H20: 8-K EX-99.1 0001045810-25-000115 (2025-05-28) q1fy26pr.htm sentence #2, $4.5 billion charge for H20 excess
# inventory as demand diminished, Q1 FY26 = 2025Q1.
H20_SHA = "0f78d53731f6076e1dd70be50e31ddcc58b83cecb65cfd98cf85a2a58a3781d0"


@bug("R5-F2a: H20 excess-inventory charge (2025Q1) not coded although interpretation 7 codes the FY23 Ampere case -2")
def test_nvda_h20_excess_supply_coded(kpis):
    hit = kpis[(kpis["definition"] == "NVDA_CAPACITY_CURRENT") & (kpis["period"] == "2025Q1")]
    assert len(hit) == 1 and int(hit["code"].iloc[0]) == -2 and hit["sentence_sha256"].iloc[0] == H20_SHA


# H200: 10-Q 0001045810-26-000075 (2026-08-26) sentence #323 (excess H200 inventory, demand diminished) is in the
# same document as the coded +1 (sentence #280): opposite signs give 0 under the locked rules.
@bug("R5-F2b: nvda-cap-2026q2 should be 0 (H200 excess supply and supply constraints in the same 10-Q)")
def test_nvda_2026q2_mixed_signs_give_zero(kpis):
    assert int(_row(kpis, "nvda-cap-2026q2")["code"]) == 0


# R5-F3: "secured inventory and capacity to meet demand beyond the next several quarters" (EX-99.2 2026-02-25,
# #30) states a horizon; interpretation 4 codes "several quarters" as at least two quarters: Q2-Q3 FY27 = 2026Q3.
@bug("R5-F3: nvda-capf-2026q1 has a stated horizon (next several quarters), period should be 2026Q3")
def test_nvda_forward_horizon(kpis):
    assert _row(kpis, "nvda-capf-2026q1")["period"] == "2026Q3"


# R5-F4: FY25 Q3 call (2025-04-30) #364: "matched supply and demand" for the reported quarter (2025Q1) = 0.
@bug("R5-F4: missing MSFT current capacity code for 2025Q1 (0, call 2025-04-30 sentence #364)")
def test_msft_2025q1_current_capacity_coded(kpis):
    hit = kpis[(kpis["definition"] == "MSFT_CAPACITY_CURRENT") & (kpis["period"] == "2025Q1")]
    assert len(hit) == 1 and int(hit["code"].iloc[0]) == 0 and hit["filed"].iloc[0] == "2025-04-30"


# R5-F5: FY24 Q3 call (2024-04-25) #221: Q4 FY24 Azure guidance includes "some impact from the AI capacity
# availability" = +1 forward for 2024Q2 (as msft-capf-2024q4b for the same kind of guidance statement).
@bug("R5-F5: missing MSFT forward capacity code for 2024Q2 (+1, call 2024-04-25 sentence #221)")
def test_msft_2024q2_forward_capacity_coded(kpis):
    hit = kpis[(kpis["definition"] == "MSFT_CAPACITY_FORWARD") & (kpis["period"] == "2024Q2")]
    assert len(hit) == 1 and int(hit["code"].iloc[0]) == 1 and hit["filed"].iloc[0] == "2024-04-25"


# R5-F6: Microsoft AI-product counts stated in the calls, neither coded nor listed under "Inte kodat".
MISSING_KPI_SENTENCES = [
    ("2023-10-24 #61 Sales Copilot >15,000 orgs", "15813fb49cec632a938f5e20f3b37ac680985d813d93081d33055bc39a5da679"),
    ("2024-01-30 #68 Sales Copilot >30,000 orgs", "461efc990bb568eaba3da84b01a1ef5be8a53c7f39d243d8d99357c13b60154c"),
    ("2024-07-30 #93 Copilot for Security >1,000 paid customers",
     "444faedaa88dc46cf41b3e95545fbae56fe25dfa9fbdaa1e1c55eaf9de4ddc7c"),
    ("2026-01-28 #51 Foundry, Anthropic+OpenAI >1,500",
     "f89269378cbacc55f2a46133d298dcf6a39d313eef233fa94f0d5d266858f92e"),
    ("2026-04-29 #46 Foundry, >1 model >10,000", "705ddfcc5fbfcdf7a968805b9f7a86b2e491386fc203688b507041a98260981c"),
    ("2026-04-29 #66 Foundry+Fabric >15,000", "a110a7194921205613333c8ede27a412c38e9ad6593ddb7cbf8890e92944a5d4"),
    ("2026-07-29 #68 Foundry+Fabric >17,000", "a39e851fc7a1f81f8ded7be0523bfb31dd22fadb925581d66238faf9b0c0bd89"),
    ("2026-10-28 #84 Foundry+Fabric >19,000", "33c534e530ee21098b9974b902ce94197620edeb1573db57674bd331aa76f345"),
]


@bug("R5-F6: Microsoft AI-product counts in the calls are missing from ai_kpis.csv")
@pytest.mark.parametrize("label,sha", MISSING_KPI_SENTENCES)
def test_missing_kpi_sentence_coded(kpis, label, sha):
    assert sha in set(kpis["sentence_sha256"]), label


# R5-F7: Oracle states "operating lease commitments" (not yet recorded, i.e. not commenced) in the MD&A of four
# 10-Qs that have no row; the same wording is coded for Nov 2022 and Feb 2023.
# (period, MUSD, accession, sentence # in lease_commitments.sentences, SHA-256)
ORCL_MISSING = [
    ("2023-11-30", 10600, "0000950170-23-069682", 877,
     "14f667171036dbe749d94bcd6dea666e83d09f730b697c43f55cc1967cfb920f"),
    ("2024-02-29", 18800, "0000950170-24-029904", 958,
     "617cd987a39295db6f82c7beb7687b6d8af86db9e38e168f1f35d252ca965855"),
    ("2024-08-31", 36200, "0000950170-24-104905", 857,
     "8d95a041cce05eaea8d3a562cd28056276326e65bbd353a863b1326363414100"),
    ("2024-11-30", 36700, "0000950170-24-134973", 909,
     "6da26ce736a6aca07e57f5c21a070ad1350ba41f92665cb11a930c6c733e851b"),
]


@bug("R5-F7: Oracle operating lease commitments in four 10-Q MD&As are missing")
@pytest.mark.parametrize("period,value,accession,k,sha", ORCL_MISSING)
def test_orcl_lease_rows_present(leases, period, value, accession, k, sha):
    hit = leases[(leases["company"] == "orcl") & (leases["period"] == period)]
    assert len(hit) == 1
    r = hit.iloc[0]
    assert (float(r["value"]), r["accession"], r["lease_type"], r["sentence_sha256"]) == (
        value, accession, "operating", sha)


# R5-F9: from 2026-06-30 Microsoft's amount includes "arrangements subject to certain contractual conditions";
# the definition widened and the row does not say so.
@bug("R5-F9: Microsoft's conditional lease arrangements (2026Q2-) are not flagged")
@pytest.mark.parametrize("row_id", ["msft-2026-06-30-total", "msft-2026-09-30-total"])
def test_msft_conditional_leases_flagged(leases, row_id):
    assert "condition" in str(_row(leases, row_id)["note"]).lower()


# R5-F10: FY25 Q2 call (2025-01-29) #240: FY26 capex growth "lower than FY25" (FY26 named in #239) is a plan for
# the next fiscal year (E1's msft-16) but has no row in plans.csv.
@bug("R5-F10: missing D1 row for Microsoft FY26 (growth_vs_prior -1, call 2025-01-29)")
def test_msft_fy26_first_statement_in_plans(plans):
    hit = plans[plans["sentence_sha256"] == "6d795323401c07a042aed4a8e50e85ca26d849fc74a3b0d2506b5059a8487242"]
    assert len(hit) == 1
    r = hit.iloc[0]
    assert (r["measure"], r["period_end"], int(r["direction_code"]), r["direction_base"]) == (
        "CAPEX", "2026-06-30", -1, "growth_vs_prior")


# R5-F11: Meta's commitments include third-party cloud capacity from 2025-09-30 (new wording, total x3 in one
# quarter); D1's own rule gives a new definition code for new wording.
@bug("R5-F11: META_NONCANCEL_COMMIT spans the change to third-party cloud capacity (2025Q3)")
def test_meta_commit_split_at_cloud_capacity(plans):
    late = plans[(plans["company"] == "meta") & (plans["measure"] == "COMMIT") & (plans["period_end"] >= "2025-09-30")]
    assert len(late) == 6 and not (late["definition"] == "META_NONCANCEL_COMMIT").any()


# R5-F12: msft-p022 says "double" without a qualifier (kind point), msft-p025 says "overall capacity" rather than
# "datacenter footprint" (new wording, new code under D1's rule).
@bug("R5-F12a: msft-p022 kind should be point (no qualifier in the sentence)")
def test_msft_p022_kind(plans):
    assert _row(plans, "msft-p022")["kind"] == "point"


@bug("R5-F12b: msft-p025 ('overall capacity') is coded as MSFT_DC_FOOTPRINT")
def test_msft_p025_definition(plans):
    assert _row(plans, "msft-p025")["definition"] != "MSFT_DC_FOOTPRINT"


# R5-F13: Oracle 10-Q for Feb 2024 (0000950170-24-029904): unconditional purchase obligations $4.4 billion,
# "primarily related to capital expenditures for our data centers" (sentences #429 and #431).
@bug("R5-F13: missing Oracle COMMIT row for 2024-02-29 (4,400 MUSD)")
def test_orcl_commit_feb_2024(plans):
    hit = plans[(plans["company"] == "orcl") & (plans["measure"] == "COMMIT") & (plans["period_end"] == "2024-02-29")]
    assert len(hit) == 1 and float(hit["value_lo"].iloc[0]) == 4400


# R5-F14 (E1, flagged by D1 and confirmed): FY27 Q1 call 2026-10-28 #226 lowers CY2026 capex to approximately
# $170 billion; guidance_capex.csv still has only msft-26 (approx 190,000).
@bug("R5-F14: guidance_capex.csv lacks Microsoft CY2026 approx 170,000 (call 2026-10-28)")
def test_msft_cy2026_cut_in_guidance(capex):
    hit = capex[capex["sentence_sha256"] == "c12864f550b4881de122eda842f6023fff77e59a899407c12fd939ffc7f79788"]
    assert len(hit) == 1
    r = hit.iloc[0]
    assert (r["horizon"], r["period"], float(r["value_lo"]), r["filed"]) == ("CY", "2026", 170000.0, "2026-10-28")
