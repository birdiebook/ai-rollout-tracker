"""Correction track X16 after review R19 (docs/granskning/r19-order-orderstock.md). No network.

- F-1: GE Vernova's GW orders are split (register 2026-11-25): 'orders' in GW is 2025Q1 only, from 2025Q2 the orders
  among new contracts (orders_new_contracts) and the reservations converted to orders (orders_converted) are their
  own definitions. The conversions are checked against R19's own reading (tests/test_r19_order_orderstock.py,
  GW_FLOWS): same sentence hashes and numbers.
- F-2: a period with only a bound gets that reason, not 'not stated'.
- F-4 and N-5: the series notes on the Digital Realty share and Eaton's acquisitions.
- N-7: the Digital Realty 2023Q2 footnote in the CSV notes.
"""

from __future__ import annotations

import csv

import pandas as pd
import pytest

from ai_tracker import catalog
from ai_tracker.series import orders_backlog as series
from ai_tracker.sources import orders_backlog as ob

QUARTERS = [str(p) for p in pd.period_range("2025Q2", "2026Q3", freq="Q")]
OLD_KEY = "ob_gev_orders_gas_power_equipment_q_level_gw"
# Read by R19 (GW_FLOWS in tests/test_r19_order_orderstock.py): sha256 prefix of the backlog sentence, converted, shipped
R19_FLOWS = {
    "2025Q2": ("377331e22a2d6e00", 3, 5),
    "2025Q3": ("f139149a3153e7c5", 7, 4),
    "2025Q4": ("da1f37133e844f8d", 8, 3),
    "2026Q1": ("ec1a8d4f2913c00b", 6, 4),
    "2026Q2": ("10b622b9379ed96d", 10, 3),
    "2026Q3": ("13638dd10a42b1b8", 13, 5),
}
R19_INTAKE = {"2025Q2": 5, "2025Q3": 8, "2025Q4": 11, "2026Q1": 8, "2026Q2": 12, "2026Q3": 16}  # review, point 2


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return ob.load()


@pytest.fixture(scope="module")
def gw(df) -> pd.DataFrame:
    p = ob.points(df)
    return p[(p["company"] == "gev") & (p["unit"] == "GW")]


def _by_period(g: pd.DataFrame, measure: str) -> pd.Series:
    s = g[g["measure"] == measure].set_index("period")["value"]
    assert s.index.is_unique, measure
    return s


# ------------------------------------------------------------------ F-1

def test_conversions_are_coded_from_the_sentences_r19_read(df, gw):
    conv = gw[gw["measure"] == "orders_converted"].set_index("period")
    assert list(conv.index) == QUARTERS
    for per, (sha, converted, _) in R19_FLOWS.items():
        row = conv.loc[per]
        assert row["sentence_sha256"].startswith(sha) and row["value"] == converted, per
        backlog = df[(df["accession"] == row["accession"]) & (df["measure"] == "backlog") & (df["unit"] == "GW")
                     & (df["period_end"] == row["period_end"])]
        assert list(backlog["locator"]) == [row["locator"]], per  # same sentence as the backlog row


def test_gw_backlog_closes_with_new_orders_and_conversions(gw):
    """backlog(t) = backlog(t-1) + orders among new contracts + converted - shipped (R19's reading), within 1 GW."""
    backlog, new, conv = (_by_period(gw, m) for m in ("backlog", "orders_new_contracts", "orders_converted"))
    for per, (_, _, shipped) in R19_FLOWS.items():
        prev = str(pd.Period(per, "Q") - 1)
        assert abs(backlog[prev] + new[per] + conv[per] - shipped - backlog[per]) <= 1, per
        assert new[per] + conv[per] == R19_INTAKE[per], per


def test_gas_turbine_orders_of_2025q1_stay_alone_and_stop(df):
    rows = df[(df["company"] == "gev") & (df["unit"] == "GW") & (df["measure"] == "orders")]
    values = rows[rows["row_type"] == "value"]
    assert list(values["id"]) == ["gev-2025-04-23-15"] and list(values["value"]) == [7.0]
    stops = rows[rows["row_type"] == "stop"]
    assert list(stops["id"]) == ["gev-2025-07-23-s01"] and list(stops["fiscal_period"]) == ["2025Q2"]
    assert ob.stopped(df, OLD_KEY) is not None  # the definition is closed


def test_catalog_has_the_two_new_gw_series_and_not_the_spliced_one():
    specs = {s.key: s for s in catalog.ALL if s.key.startswith("ob_gev_") and s.key.endswith("_gw")}
    assert OLD_KEY not in specs
    for key in (series.GEV_NEW, series.GEV_CONVERTED):
        s = specs[key]
        assert list(s.fetch()["period"]) == QUARTERS and not s.publish and not s.closed
        assert series.GEV_NEW in s.note and series.GEV_CONVERTED in s.note and "summan" in s.note
    assert "utan konverterade reservationer" in specs[series.GEV_NEW].label


def _write(tmp_path, rows: list[dict]) -> pd.DataFrame:
    p = tmp_path / "orders_backlog.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ob.COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return ob.load(p)


def _committed(rid: str) -> dict:
    with open(ob.PATH, newline="", encoding="utf-8") as fh:
        return next(r for r in csv.DictReader(fh) if r["id"] == rid)


@pytest.mark.parametrize("rid, change", [
    ("gev-2025-07-23-15", {"measure": "orders"}),  # 'orders' in GW from 2025Q2 is the spliced definition
    ("gev-2025-07-23-20", {"unit": "MUSD"}),  # the new measures are GW only
    ("gev-2025-07-23-20", {"segment": "power"}),
    ("gev-2025-07-23-20", {"window": "ytd"}),
])
def test_load_rejects_gw_orders_outside_the_amended_rule(tmp_path, rid, change):
    with pytest.raises(ob.CsvError):
        _write(tmp_path, [{**_committed(rid), **change}])


def test_load_accepts_the_committed_gw_rows(tmp_path):
    ids = ["gev-2025-04-23-15", "gev-2025-07-23-15", "gev-2025-07-23-20", "gev-2025-07-23-s01"]
    assert len(_write(tmp_path, [_committed(i) for i in ids])) == 4


# ------------------------------------------------------------------ F-2

def _row(**kw) -> dict:
    base = {c: "" for c in ob.COLUMNS}
    base.update(company="etn", row_type="value", measure="book_to_bill", segment="electrical", component="all",
                window="ttm", form="ratio", organic="na", unit="ratio", value="1.2", metric_as_stated="book-to-bill",
                form_type="8-K", exhibit="EX-99", locator="sentence #3", sentence_sha256="a" * 64)
    base.update(kw)
    if base["row_type"] == "stop":
        base.update(value="", qualifier="", locator="absent", sentence_sha256=ob.EMPTY_SHA256, metric_as_stated="")
    n = int(base["id"].split("-")[-1])
    acc = f"0001551182-25-{n:06d}"
    url = f"https://www.sec.gov/Archives/edgar/data/1551182/{acc.replace('-', '')}/ex99.htm"
    return {**base, "accession": acc, "source_url": url}


def _q(n: int, end: str, filed: str, fp: str) -> dict:
    return {"id": f"t-{n:02d}", "period_end": end, "filed": filed, "release_date": filed, "fiscal_period": fp}


Q1, Q2, Q3, Q4, Q5 = (_q(1, "2025-03-31", "2025-05-02", "2025Q1"), _q(2, "2025-06-30", "2025-08-05", "2025Q2"),
                      _q(3, "2025-09-30", "2025-11-04", "2025Q3"), _q(4, "2025-12-31", "2026-02-03", "2025Q4"),
                      _q(5, "2026-03-31", "2026-05-05", "2026Q1"))


def test_gap_reason_is_the_bound_when_only_a_bound_is_stated(tmp_path):
    df = _write(tmp_path, [_row(**Q1), _row(**Q2, qualifier="gt", value="1.0"), _row(**Q3)])
    key = ob.series_key(df.iloc[0])
    assert ob.gap_periods(df, key) == {"2025Q2": ob.GAP_BOUND}
    assert ob.expected_stops(df).empty  # a bound states the definition, so it is no stop


def test_gap_reason_after_a_stop_keeps_the_stop_and_names_the_bound(tmp_path):
    rows = [_row(**Q1), _row(**Q2, row_type="stop"), _row(**Q3, qualifier="gt", value="1.0"), _row(**Q4), _row(**Q5)]
    df = _write(tmp_path, rows)
    key = ob.series_key(df.iloc[0])
    gaps = ob.gap_periods(df, key)
    assert gaps.keys() == {"2025Q2", "2025Q3"}
    assert gaps["2025Q2"] == ob.GAP_STOP
    assert gaps["2025Q3"].startswith(ob.GAP_STOP) and "bound" in gaps["2025Q3"]


def test_committed_gap_reasons_say_not_stated_only_where_nothing_is_stated(df):
    vals = df[df["row_type"] == "value"]
    for key, gaps in series.KNOWN_GAP_PERIODS.items():
        rows = ob.definition_rows(vals, key)
        stated = {ob.period_of(e, w) for e, w in zip(rows["period_end"], rows["window"])}
        for per, why in gaps.items():
            assert why.startswith("stop") or (why == ob.GAP_BOUND) == (per in stated), (key, per)


# ------------------------------------------------------------------ F-4, N-5, N-7

def test_dlr_share_note_is_on_the_eight_lease_series_only():
    with_note = sorted(s.key for s in series.SPECS if series.DLR_SHARE_NOTE in s.note)
    want = sorted(s.key for s in series.SPECS if s.key.startswith("ob_dlr_leases_signed_") and "_dlr_share_" in s.key)
    assert len(want) == 8 and with_note == want
    assert all("2021Q4–2024Q1" in s.note and "kärnserie" in s.note for s in series.SPECS if s.key in want)


def test_eaton_backlog_without_basis_names_the_acquisitions():
    keys = sorted(s.key for s in series.SPECS if series.ETN_SCOPE_NOTE in s.note)
    assert keys == ["ob_etn_backlog_electrical_americas_end_yoy_pct_unspecified_pct",
                    "ob_etn_backlog_electrical_end_yoy_pct_unspecified_pct",
                    "ob_etn_backlog_electrical_global_end_yoy_pct_unspecified_pct"]


def test_csv_notes_for_the_acquisitions_and_the_lease_replacement(df):
    note = df.set_index("id")["note"]
    assert all("Boyd Thermal" in note[i] for i in ("etn-2026-05-05-05", "etn-2026-07-31-05", "etn-2026-11-03-05"))
    assert all("Fibrebond" in note[i] for i in ("etn-2025-08-05-03", "etn-2025-11-04-03", "etn-2026-02-03-03",
                                                  "etn-2026-05-05-03"))
    assert all("8 MW lease replacement" in note[i] for i in ("dlr-2023-07-27-03", "dlr-2023-07-27-04",
                                                             "dlr-2023-07-27-07", "dlr-2023-07-27-08"))
