"""R19 review of the S3 orders and backlog extraction (docs/granskning/r19-order-orderstock.md). No network.

Evidence was read on 2026-11-25 in the 113 press release exhibits, re-fetched from www.sec.gov with the honest client
(source r19_review; every copy byte-identical to S3's), and dated with EDGAR's submissions API (filingDate,
acceptanceDateTime). Only ids, numbers, dates and SHA-256 prefixes are kept here, never source text.

- Pinned rows: the 65 rows of the stratified sample (58 drawn with seed 2026112519, 7 added for metric types the draw
  missed), as read by R19, plus a digest of the 610 reviewed rows outside the gas turbine GW flows (finding F-1).
- Properties: table sums, complete quarters, GW stocks, dating, closed Vertiv series, no core series, short wording.
- Findings F-1 to F-4 were strict xfail until corrected. Correction track X16 (register 2026-11-25) fixed them: the
  markers are removed and the assertions are unchanged. After F-1 the GW orders of 2025Q2- have the measure
  orders_new_contracts, so three references to that measure and the catalog count below follow the fix (marked X16).
"""

from __future__ import annotations

import hashlib
import re

import pandas as pd
import pytest

from ai_tracker import config
from ai_tracker.sources import orders_backlog as ob

SOURCE_DOC = config.REPO / "docs" / "kallor" / "order_orderstock.md"
REVIEW_DAY = "2026-11-25"


@pytest.fixture(scope="module")
def raw() -> pd.DataFrame:
    """The curated CSV as strings (exactly as committed)."""
    return pd.read_csv(ob.PATH, dtype=str).fillna("")


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return ob.load()


@pytest.fixture(scope="module")
def pts(df) -> pd.DataFrame:
    return ob.points(df)


# ------------------------------------------------------------------ pinned rows (read by R19 in the filings)

# id: (sha256 prefix, measure/segment/component/window/form/organic/unit, qualifier+value, period_end, filed)
SAMPLE = {
    "vrt-2022-04-27-03": ("3ca33412cabdcdf4", "backlog/total/all/end/vs_ye_pct/unspecified/pct",
                          "29", "2022-03-31", "2022-04-27"),
    "vrt-2022-10-03-01": ("499333a3f317b69f", "orders/total/all/q/yoy_pct/cc/pct", "12", "2022-09-30", "2022-10-03"),
    "vrt-2022-10-26-03": ("dd6de677ddf3a539", "backlog/total/all/end/vs_ye_pct/unspecified/pct",
                          "46", "2022-09-30", "2022-10-26"),
    "vrt-2023-08-02-01": ("4541279adf59a2bd", "orders/total/all/q/yoy_pct/cc/pct", "-3", "2023-06-30", "2023-08-02"),
    "vrt-2024-04-24-03": ("a642406dffd641ae", "backlog/total/all/end/level/na/MUSD",
                          "6300", "2024-03-31", "2024-04-24"),
    "vrt-2024-07-24-03": ("02ab76e568087036", "orders/total/all/ttm/yoy_pct/organic/pct",
                          "37", "2024-06-30", "2024-07-24"),
    "vrt-2025-04-23-01": ("3a1ddb2a75ea2bd2", "orders/total/all/ttm/yoy_pct/organic/pct",
                          "approx20", "2025-03-31", "2025-04-23"),
    "vrt-2025-07-30-03": ("760f98fc9937db39", "orders/total/all/ttm/yoy_pct/organic/pct",
                          "approx11", "2025-06-30", "2025-07-30"),
    "vrt-2025-10-22-05": ("c5fc55c18f802c43", "backlog/total/all/end/level/na/MUSD",
                          "9500", "2025-09-30", "2025-10-22"),
    "vrt-2026-02-11-02": ("1b2d6072a38ff086", "orders/total/all/q/qoq_pct/organic/pct",
                          "117", "2025-12-31", "2026-02-11"),
    "gev-2024-04-25-02": ("a118f8d5c6ab239c", "orders/total/all/q/yoy_pct/organic/pct",
                          "-1", "2024-03-31", "2024-04-25"),
    "gev-2024-07-24-09": ("6d2d84f83aca8770", "orders/wind/all/q/yoy_pct/reported/pct",
                          "-44", "2024-06-30", "2024-07-24"),
    "gev-2024-07-24-12": ("0e469af1c9cc634c", "orders/electrification/all/q/level/na/MUSD",
                          "5011", "2023-06-30", "2024-07-24"),
    "gev-2024-07-24-14": ("0e469af1c9cc634c", "orders/electrification/all/q/yoy_pct/organic/pct",
                          "-5", "2024-06-30", "2024-07-24"),
    "gev-2025-01-22-03": ("8736f59e9e463a86", "orders/total/all/fy/level/na/MUSD",
                          "44100", "2024-12-31", "2025-01-22"),
    "gev-2025-07-23-01": ("6a4e1862cb6926d9", "orders/total/all/q/level/na/MUSD",
                          "12400", "2025-06-30", "2025-07-23"),
    "gev-2025-07-23-09": ("4c7ab2f57fecb981", "orders/wind/all/q/yoy_pct/reported/pct",
                          "-4", "2025-06-30", "2025-07-23"),
    "gev-2025-07-23-18": ("bc72e261d03ad7bb", "backlog_and_slot_reservations/gas_power/equipment/end/level/na/GW",
                          "55", "2025-06-30", "2025-07-23"),
    "gev-2025-10-22-03": ("5b997bbf5ffc7cda", "orders/power/all/q/level/na/MUSD", "7807", "2025-09-30", "2025-10-22"),
    "gev-2026-04-22-02": ("1524e05f89978cfd", "orders/total/all/q/yoy_pct/organic/pct",
                          "71", "2026-03-31", "2026-04-22"),
    "gev-2026-04-22-10": ("cdaab6dbf9ea8996", "orders/wind/all/q/yoy_pct/organic/pct",
                          "85", "2026-03-31", "2026-04-22"),
    "gev-2026-04-22-19": ("7993e862dafe7f24", "backlog/total/all/end/level/na/MUSD",
                          "163000", "2026-03-31", "2026-04-22"),
    "gev-2026-04-22-20": ("0f8c464f64142372", "backlog/electrification/equipment/end/level/na/MUSD",
                          "38600", "2026-03-31", "2026-04-22"),
    "gev-2026-10-28-02": ("55866decb9dfa209", "orders/total/all/q/yoy_pct/organic/pct",
                          "96", "2026-09-30", "2026-10-28"),
    "etn-2022-08-02-03": ("3b0ac9749644c7a8", "backlog/electrical_americas/all/end/yoy_pct/organic/pct",
                          "89", "2022-06-30", "2022-08-02"),
    "etn-2023-10-31-01": ("64d677b26672f9f2", "orders/electrical_americas/all/ttm/yoy_pct/organic/pct",
                          "-3", "2023-09-30", "2023-10-31"),
    "etn-2024-02-01-02": ("32ef267425f85c62", "backlog/electrical_americas/all/end/yoy_pct/organic/pct",
                          "18", "2023-12-31", "2024-02-01"),
    "etn-2025-01-31-02": ("60e529d0ff7c1600", "book_to_bill/electrical_americas/all/ttm/ratio/na/ratio",
                          "1.2", "2024-12-31", "2025-01-31"),
    "etn-2025-08-05-05": ("3352d9e1e2c06415", "backlog/electrical_global/all/end/yoy_pct/unspecified/pct",
                          "1", "2025-06-30", "2025-08-05"),
    "etn-2025-11-04-04": ("755475563edbf715", "orders/electrical_global/all/ttm/yoy_pct/organic/pct",
                          "2", "2025-09-30", "2025-11-04"),
    "etn-2026-02-03-01": ("f15ea18a794e5f73", "backlog/electrical/all/end/yoy_pct/unspecified/pct",
                          "29", "2025-12-31", "2026-02-03"),
    "etn-2026-02-03-02": ("697a501de128c610", "orders/electrical_americas/all/ttm/yoy_pct/organic/pct",
                          "16", "2025-12-31", "2026-02-03"),
    "etn-2026-05-05-02": ("290ce86cb91e9b7c", "orders/electrical_americas/all/ttm/yoy_pct/organic/pct",
                          "42", "2026-03-31", "2026-05-05"),
    "etn-2026-07-31-01": ("f04f8339d24aba76", "backlog/electrical/all/end/yoy_pct/unspecified/pct",
                          "43", "2026-06-30", "2026-07-31"),
    "etn-2026-07-31-02": ("5281598751aad5f2", "orders/electrical_americas/all/ttm/yoy_pct/organic/pct",
                          "41", "2026-06-30", "2026-07-31"),
    "etn-2026-11-03-03": ("6907a26dcb5a0f9c", "backlog/electrical_americas/all/end/yoy_pct/unspecified/pct",
                          "33", "2026-09-30", "2026-11-03"),
    "dell-2024-02-29-01": ("be37e06afce375b5", "orders/ai_servers/all/q/qoq_pct/unspecified/pct",
                           "lt40", "2024-02-02", "2024-02-29"),
    "dell-2024-02-29-02": ("be37e06afce375b5", "backlog/ai_servers/all/end/level/na/MUSD",
                           "2900", "2024-02-02", "2024-02-29"),
    "dell-2024-11-26-01": ("b1041f6a2d671a23", "orders/ai_servers/all/q/level/na/MUSD",
                           "3600", "2024-11-01", "2024-11-26"),
    "dell-2025-05-29-01": ("5d657cb1f260ae6d", "orders/ai_servers/all/q/level/na/MUSD",
                           "12100", "2025-05-02", "2025-05-29"),
    "dell-2025-05-29-02": ("5d657cb1f260ae6d", "backlog/ai_servers/all/end/level/na/MUSD",
                           "14400", "2025-05-02", "2025-05-29"),
    "dell-2025-11-25-01": ("e6062698134b9474", "orders/ai_servers/all/q/level/na/MUSD",
                           "12300", "2025-10-31", "2025-11-25"),
    "dell-2026-02-26-01": ("e6fbb8198d3366a0", "orders/ai_servers/all/fy/level/na/MUSD",
                           "gt64000", "2026-01-30", "2026-02-26"),
    "dell-2026-02-26-03": ("e6fbb8198d3366a0", "backlog/ai_servers/all/end/level/na/MUSD",
                           "43000", "2026-01-30", "2026-02-26"),
    "dlr-2022-02-17-01": ("1cd612e11d3e74ff", "leases_signed/0_1mw/dlr_share/q/level/na/MUSD",
                          "41.767", "2021-12-31", "2022-02-17"),
    "dlr-2022-02-17-02": ("1cd612e11d3e74ff", "leases_signed/0_1mw/dlr_share/q/level/na/MW",
                          "14.3", "2021-12-31", "2022-02-17"),
    "dlr-2022-02-17-03": ("1cd612e11d3e74ff", "leases_signed/gt_1mw/dlr_share/q/level/na/MUSD",
                          "96.676", "2021-12-31", "2022-02-17"),
    "dlr-2022-10-26-04": ("052fa020f87b562d", "leases_signed/gt_1mw/dlr_share/q/level/na/MW",
                          "90.7", "2022-09-30", "2022-10-26"),
    "dlr-2023-02-16-07": ("966fa766a45b32a0", "leases_signed/total/dlr_share/q/level/na/MUSD",
                          "117.198", "2022-12-31", "2023-02-16"),
    "dlr-2023-04-27-06": ("6d504ff353978aea", "leases_signed/interconnection/dlr_share/q/level/na/MUSD",
                          "14.063", "2023-03-31", "2023-04-27"),
    "dlr-2023-10-26-05": ("2cab426461009a3a", "leases_signed/other/dlr_share/q/level/na/MUSD",
                          "1.37", "2023-09-30", "2023-10-26"),
    "dlr-2024-02-15-05": ("5cc83f3e32b54124", "leases_signed/other/dlr_share/q/level/na/MUSD",
                          "0.477", "2023-12-31", "2024-02-15"),
    "dlr-2025-04-24-03": ("9e0efd6b76c77376", "leases_signed/gt_1mw/dlr_share/q/level/na/MUSD",
                          "172.129", "2025-03-31", "2025-04-24"),
    "dlr-2025-04-24-04": ("9e0efd6b76c77376", "leases_signed/gt_1mw/dlr_share/q/level/na/MW",
                          "61.8", "2025-03-31", "2025-04-24"),
    "dlr-2025-07-24-04": ("a5398f100e3474df", "leases_signed/gt_1mw/dlr_share/q/level/na/MW",
                          "23.3", "2025-06-30", "2025-07-24"),
    "dlr-2026-04-23-01": ("1049552940cd2d1f", "leases_signed/0_1mw/dlr_share/q/level/na/MUSD",
                          "78.954", "2026-03-31", "2026-04-23"),
    "dlr-2026-04-23-08": ("1049552940cd2d1f", "leases_signed/total/dlr_share/q/level/na/MW",
                          "176", "2026-03-31", "2026-04-23"),
    "dlr-2026-07-23-07": ("83d9d59e0cd0dc70", "leases_signed/total/dlr_share/q/level/na/MUSD",
                          "208.495", "2026-06-30", "2026-07-23"),
    "dlr-2025-07-24-09": ("3dbfbc72e9f9194a", "signed_not_commenced/total/dlr_share/end/level/na/MUSD",
                          "826", "2025-06-30", "2025-07-24"),
    "dlr-2026-10-29-11": ("21eb09eda522c8ed", "signed_not_commenced/total/all/end/level/na/MUSD",
                          "2500", "2026-09-30", "2026-10-29"),
    "vrt-2024-07-24-02": ("6ed2e94918263e7c", "book_to_bill/total/all/q/ratio/na/ratio",
                          "1.4", "2024-06-30", "2024-07-24"),
    "gev-2026-07-22-17": ("10b622b9379ed96d", "slot_reservations/gas_power/equipment/end/level/na/GW",
                          "63", "2026-06-30", "2026-07-22"),
    "gev-2026-07-22-15": ("ce0750a73da3f999", "orders_new_contracts/gas_power/equipment/q/level/na/GW",  # X16
                          "2", "2026-06-30", "2026-07-22"),
    "gev-2026-07-22-16": ("10b622b9379ed96d", "backlog/gas_power/equipment/end/level/na/GW",
                          "53", "2026-06-30", "2026-07-22"),
    "dell-2026-02-26-02": ("e6fbb8198d3366a0", "shipments/ai_servers/all/fy/level/na/MUSD",
                           "gt25000", "2026-01-30", "2026-02-26"),
}
REVIEWED_ROWS = 610
REVIEWED_DIGEST = "79b00ad0d08a5c0a222c90d2712c206a57f4752d63e4a4adc9da77af455a05f3"
GW_STOCKS = ("backlog", "slot_reservations", "backlog_and_slot_reservations")


def test_sample_rows_match_r19_reading(raw):
    got = raw.set_index("id")
    assert len(SAMPLE) == 65
    for rid, (sha, definition, value, end, filed) in SAMPLE.items():
        r = got.loc[rid]
        assert r.sentence_sha256.startswith(sha), rid
        assert "/".join(r[c] for c in ("measure", "segment", "component", "window", "form", "organic", "unit")) \
            == definition, rid
        assert (r.qualifier + r.value, r.period_end, r.filed) == (value, end, filed), rid


def test_sample_covers_every_company_and_metric_type():
    companies = {rid.split("-")[0] for rid in SAMPLE}
    measures = {(rid.split("-")[0], d.split("/")[0], d.split("/")[-1]) for rid, (_, d, *_) in SAMPLE.items()}
    assert companies == {"vrt", "gev", "etn", "dell", "dlr"}
    for want in [("vrt", "book_to_bill", "ratio"), ("gev", "slot_reservations", "GW"),
                 ("gev", "orders_new_contracts", "GW"),  # X16: the measure after F-1
                 ("dell", "shipments", "MUSD"), ("dlr", "signed_not_commenced", "MUSD"), ("dlr", "leases_signed", "MW")]:
        assert want in measures


def test_reviewed_rows_are_unchanged(raw):
    """Every row filed by the review day was checked by R19, except the GW flows of F-1. A change needs a new review."""
    cols = [c for c in raw.columns if c != "note"]
    gw_flow = (raw["company"] == "gev") & (raw["unit"] == "GW") & ~raw["measure"].isin(GW_STOCKS)
    rows = raw[(raw["filed"] <= REVIEW_DAY) & ~gw_flow]
    lines = sorted("|".join(r[c] for c in cols) for _, r in rows.iterrows())
    assert len(lines) == REVIEWED_ROWS
    assert hashlib.sha256("\n".join(lines).encode()).hexdigest() == REVIEWED_DIGEST


# ------------------------------------------------------------------ properties that hold

def test_dlr_table_categories_add_up_to_the_grand_total(pts):
    """0-1 MW + >1 MW + other + interconnection = grand total (rent), 0-1 MW + >1 MW = total (MW), 20 quarters."""
    d = pts[(pts["company"] == "dlr") & (pts["measure"] == "leases_signed") & (pts["component"] == "dlr_share")]
    for unit, parts, tol in (("MUSD", ["0_1mw", "gt_1mw", "other", "interconnection"], 0.0015),
                             ("MW", ["0_1mw", "gt_1mw"], 0.15)):
        t = d[d["unit"] == unit].pivot_table(index="period", columns="segment", values="value", aggfunc="first")
        assert len(t) == 20 and t.index.min() == "2021Q4" and t.index.max() == "2026Q3"
        assert ((t[parts].sum(axis=1) - t["total"]).abs() <= tol).all(), unit


def test_gev_segment_orders_are_complete_for_eleven_quarters(pts):
    g = pts[(pts["company"] == "gev") & (pts["measure"] == "orders") & (pts["window"] == "q")]
    quarters = [str(p) for p in pd.period_range("2024Q1", "2026Q3", freq="Q")]
    for seg in ("power", "wind", "electrification"):
        for form, org in (("level", "na"), ("yoy_pct", "reported"), ("yoy_pct", "organic")):
            got = set(g[(g["segment"] == seg) & (g["form"] == form) & (g["organic"] == org)]["period"])
            assert set(quarters) <= got, (seg, form, org)
    for form in ("level", "yoy_pct"):
        assert set(g[(g["segment"] == "total") & (g["form"] == form)]["period"]) == set(quarters)


def test_gev_gas_turbine_backlog_plus_reservations_is_the_combined_figure(pts):
    g = pts[(pts["company"] == "gev") & (pts["unit"] == "GW") & pts["measure"].isin(GW_STOCKS)]
    t = g.pivot_table(index="period", columns="measure", values="value", aggfunc="first")
    assert list(t.index) == [str(p) for p in pd.period_range("2025Q1", "2026Q3", freq="Q")]
    diff = t["backlog"] + t["slot_reservations"] - t["backlog_and_slot_reservations"]
    assert (diff.abs() <= 1).all() and (diff != 0).sum() == 1  # 2025Q2: 29 + 25 vs "55 GW" (company rounding)


# Read by R19 in the sentence of each backlog GW row: GW converted from slot reservations to orders, and GW shipped.
GW_FLOWS = {  # period: (backlog row, sha256 prefix of its sentence, converted, shipped)
    "2025Q2": ("gev-2025-07-23-16", "377331e22a2d6e00", 3, 5),
    "2025Q3": ("gev-2025-10-22-16", "f139149a3153e7c5", 7, 4),
    "2025Q4": ("gev-2026-01-28-24", "da1f37133e844f8d", 8, 3),
    "2026Q1": ("gev-2026-04-22-16", "ec1a8d4f2913c00b", 6, 4),
    "2026Q2": ("gev-2026-07-22-16", "10b622b9379ed96d", 10, 3),
    "2026Q3": ("gev-2026-10-28-16", "13638dd10a42b1b8", 13, 5),
}


def test_coded_gw_orders_exclude_the_conversions_from_slot_reservations(raw, pts):
    """Evidence for F-1: backlog(t) = backlog(t-1) + coded orders + converted - shipped, within 1 GW (rounding)."""
    got = raw.set_index("id")
    g = pts[(pts["company"] == "gev") & (pts["unit"] == "GW")]
    backlog = g[g["measure"] == "backlog"].set_index("period")["value"]
    orders = g[g["measure"] == "orders_new_contracts"].set_index("period")["value"]  # X16: measure after F-1
    for per, (rid, sha, converted, shipped) in GW_FLOWS.items():
        assert got.loc[rid].sentence_sha256.startswith(sha)
        prev = str(pd.Period(per, "Q") - 1)
        assert abs(backlog[prev] + orders[per] + converted - shipped - backlog[per]) <= 1, per
        assert converted > orders[per], per  # most GW orders of the quarter are not in the coded series


def test_eaton_rolling_orders_are_complete(pts):
    e = pts[(pts["company"] == "etn") & (pts["measure"] == "orders") & (pts["organic"] == "organic")]
    ea = set(e[e["segment"] == "electrical_americas"]["period"])
    eg = set(e[e["segment"] == "electrical_global"]["period"])
    assert ea == {str(p) for p in pd.period_range("2021Q4", "2026Q3", freq="Q")}
    assert eg == {str(p) for p in pd.period_range("2022Q1", "2026Q3", freq="Q")} - {"2025Q1"}  # 2025Q1 "flat"


def test_dates_are_filing_dates_and_datelines(df):
    """known_from = filed; the dateline equals the filing day except Eaton's typo (left empty, interpretation 10)."""
    assert (df["known_from"] == pd.to_datetime(df["filed"])).all()
    typo = df["accession"] == "0001551182-26-000002"
    assert (df.loc[typo, "release_date"] == "").all()
    assert (df.loc[~typo, "release_date"] == df.loc[~typo, "filed"]).all()
    assert (pd.to_datetime(df["period_end"]) < df["known_from"]).all()


def test_vertiv_series_are_closed_after_2025q4():
    from ai_tracker.series import orders_backlog as series

    vrt = [s for s in series.SPECS if s.key.startswith("ob_vrt_")]
    assert len(vrt) == 10 and all(s.closed and s.max_age_days is None for s in vrt)


def test_no_ob_series_is_a_core_series():
    from ai_tracker.state import register

    for branch in register.CORE_SERIES:
        assert not [k for k in register.core_entries(branch) if k.startswith("ob_")]


def test_csv_wording_is_short(raw):
    assert raw["metric_as_stated"].str.split().str.len().max() <= 10
    quoted = [q for n in raw["note"] for q in re.findall(r"'([^']+)'", n)]
    assert quoted and max(len(q.split()) for q in quoted) <= 8


def test_catalog_series_stay_unpublished_until_the_corrections():
    from ai_tracker import catalog

    specs = [s for s in catalog.ALL if s.key.startswith("ob_")]
    assert len(specs) == 62 and not any(s.publish for s in specs)  # X16: F-1 drops one key and adds two


# ------------------------------------------------------------------ findings (strict xfail until corrected by X16)

def test_gas_turbine_orders_wording_change_is_split(df):
    rows = df.set_index("id")
    assert ob.series_key(rows.loc["gev-2025-04-23-15"]) != ob.series_key(rows.loc["gev-2025-07-23-15"])


def test_gap_reason_names_the_bound():
    from ai_tracker.series import orders_backlog as series

    gaps = series.KNOWN_GAP_PERIODS["ob_etn_book_to_bill_electrical_ttm_ratio_ratio"]
    assert {"2023Q3", "2023Q4", "2025Q1", "2025Q2"} <= set(gaps)
    assert not any(gaps[p].startswith("not stated") for p in ("2023Q3", "2023Q4", "2025Q1", "2025Q2"))


def test_source_doc_has_no_long_quotes():
    text = re.sub(r"\n\s*", " ", SOURCE_DOC.read_text(encoding="utf-8"))
    quotes = [q for q in re.findall(r'"([^"]{3,300}?)"', text) if not re.search(r"[åäöÅÄÖ]", q)]
    assert max(len(q.split()) for q in quotes) < 11


def test_dlr_share_note_says_the_share_is_not_stated_before_2025():
    from ai_tracker.series import orders_backlog as series

    note = next(s.note for s in series.SPECS if s.key == "ob_dlr_leases_signed_total_dlr_share_q_level_mw")
    assert re.search(r"andel.{0,120}(anges inte|inte angiven|ej angiven|obelagd)", note)
