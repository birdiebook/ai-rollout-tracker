"""Neoclouds and Oracle (L5): Nebius 6-K parsing and vintages, rounding revisions, Oracle's offset quarters, catalog.

Synthetic fixtures, no network. Values in USD millions (x 1e6 in sec.Facts).
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import catalog, observations, warehouse
from ai_tracker.series import neoclouds as nc
from ai_tracker.sources import nebius_sec as nb
from ai_tracker.sources import sec

M = 1e6
T = pd.Timestamp


def latest(df):
    return df.sort_values("known_from").groupby("period")["value"].last().to_dict()


def first_known(df):
    return {p: str(d.date()) for p, d in df.groupby("period")["known_from"].min().items()}


HEAD = ("EX-99.1 2 x_ex99-1.htm EXHIBIT 99.1 Exhibit 99.1 Nebius reports {q} quarter 2026 financial results "
        "Amsterdam – Nebius Group N.V. (NASDAQ: NBIS), the AI cloud company, today announced its unaudited results. ")

# Layouts as in the real releases (plain text after tsmc_sec.to_text): Q1 (3M only, units first),
# H1 (units after the period labels), FY (Twelve months, older capex label without intangibles).
REL_Q1 = HEAD.format(q="first") + (
    "Q1 2026 Financial Highlights Consolidated results (1), (2) In USD $ millions Three months ended March 31 2025 2026 "
    "Change Revenues 50.9 399.0 684 % Adjusted EBITDA / (loss) (53.7 ) 129.5 n/m Operating expenses ... "
    "Selected consolidated cash flow data In USD $ millions Three months ended March 31 2025 2026 Change "
    "Cash provided by / (used in) operating activities – continuing operations (184.1 ) 2,258.0 n/m "
    "Purchases of property and equipment and intangible assets (543.9 ) (2,472.9 ) 355 % Outstanding Shares")
REL_H1 = HEAD.format(q="second") + (
    "Q2 2026 Financial Highlights Consolidated results (1), (2) Three months ended June 30 Six months ended June 30 "
    "In USD $ millions 2025 2026 Change 2025 2026 Change Revenues 105.1 582.3 454 % 156.0 981.3 529 % Adjusted "
    "EBITDA ... Selected consolidated cash flow data Three months ended June 30 Six months ended June 30 In USD $ "
    "millions 2025 2026 Change 2025 2026 Change Net cash provided by / (used in) operating activities – continuing "
    "operations (167.7 ) 2,246.1 n/m (352.0 ) 4,504.1 n/m Purchases of property and equipment and intangible assets "
    "(510.6 ) (5,657.4 ) 1008 % (1,054.5 ) (8,130.3 ) 671 % Outstanding Shares")
REL_FY = HEAD.format(q="fourth").replace("2026", "2025") + (
    "Q4 2025 Financial Highlights Consolidated results (1), (2) In USD $ millions Three months ended December 31 "
    "Twelve months ended December 31 2024 2025 Change 2024 2025 Change Revenues 35.2 227.7 547 % 91.5 529.8 479 % "
    "... Selected consolidated cash flow data In USD $ millions Three months ended December 31 Twelve months ended "
    "December 31 2024 2025 Change 2024 2025 Change Cash provided by / (used in) operating activities – continuing "
    "operations (73.1 ) 834.3 n/m (269.9 ) 401.9 n/m Purchases of property and equipment (417.5 ) (2,056.0 ) 392 % "
    "(807.5 ) (4,066.0 ) 404 % Outstanding Shares")


def cols(rel, measure):
    return [(str(s.date()), str(e.date()), v) for s, e, v in rel[measure]]


def test_parse_release_layouts():
    q1 = nb.parse_release(REL_Q1)
    assert cols(q1, "rev") == [("2025-01-01", "2025-03-31", 50.9), ("2026-01-01", "2026-03-31", 399.0)]
    assert cols(q1, "capex") == [("2025-01-01", "2025-03-31", 543.9), ("2026-01-01", "2026-03-31", 2472.9)]  # sign flipped
    assert cols(q1, "ocf") == [("2025-01-01", "2025-03-31", -184.1), ("2026-01-01", "2026-03-31", 2258.0)]
    h1 = nb.parse_release(REL_H1)
    assert cols(h1, "rev") == [("2025-04-01", "2025-06-30", 105.1), ("2026-04-01", "2026-06-30", 582.3),
                               ("2025-01-01", "2025-06-30", 156.0), ("2026-01-01", "2026-06-30", 981.3)]
    assert cols(h1, "capex")[3] == ("2026-01-01", "2026-06-30", 8130.3)
    fy = nb.parse_release(REL_FY)
    assert cols(fy, "rev")[1] == ("2025-10-01", "2025-12-31", 227.7)
    assert cols(fy, "capex")[3] == ("2025-01-01", "2025-12-31", 4066.0)
    assert cols(fy, "ocf")[0] == ("2024-10-01", "2024-12-31", -73.1)


def test_non_release_and_miscounted_rows_are_rejected():
    assert nb.parse_release("FORM 6-K Report of Foreign Private Issuer ... Nebius Group N.V. annual general meeting") is None
    broken = REL_H1.replace("(510.6 ) (5,657.4 ) 1008 %", "(510.6 ) 1008 %")  # a value missing: the row is not used
    rel = nb.parse_release(broken)
    assert "capex" not in rel and len(rel["rev"]) == 4
    assert nb.parse_release(REL_Q1.replace("Revenues 50.9", "Sales 50.9")) is None  # no revenue row, no release


def items(*rels):
    return [(nb.Filing(f"acc-{d}", d, "6-K", "cover.htm"), nb.parse_release(t)) for d, t in rels]


def test_vintages_derive_q1_and_q4_and_date_by_filing():
    its = items(("2026-02-12", REL_FY), ("2026-05-13", REL_Q1), ("2026-08-12", REL_H1))
    rev = nb.vintages(its, "rev")
    assert latest(rev) == {"2024Q4": 35.2, "2025Q4": 227.7, "2025Q1": 50.9, "2026Q1": 399.0,
                           "2025Q2": 105.1, "2026Q2": 582.3}
    assert first_known(rev)["2025Q4"] == "2026-02-12"
    capex = nb.vintages(items(("2025-08-07", REL_H1.replace("2026", "2027").replace("2025", "2026"))), "capex")
    # Q1 of both years = 6M - Q2 from the same release, dated by it
    assert latest(capex) == pytest.approx({"2026Q2": 510.6, "2027Q2": 5657.4, "2026Q1": 543.9, "2027Q1": 2472.9})
    assert set(first_known(capex).values()) == {"2025-08-07"}


def test_restatement_beyond_two_percent_is_a_definition_break():
    restated = REL_H1.replace("105.1 582.3", "95.0 582.3").replace("156.0 981.3", "146.0 981.3")
    its = items(("2026-05-13", REL_Q1), ("2026-08-12", REL_H1), ("2026-11-12", restated))
    with pytest.raises(nb.DefinitionBreakError):
        nb.vintages(its, "rev")
    assert latest(nb.vintages(its, "rev", declared_breaks=("2026-11-12",)))["2025Q2"] == 95.0
    small = REL_H1.replace("105.1 582.3", "105.0 582.3")  # rounding-sized change: an ordinary vintage, no break
    nb.vintages(items(("2026-08-12", REL_H1), ("2026-11-12", small)), "rev")


def test_release_of_skips_non_results_months_and_the_cover(monkeypatch):
    f = nb.Filing("0001-26-1", "2026-08-12", "6-K", "cover.htm")
    monkeypatch.setattr(nb, "candidate_docs", lambda f: ["letter.htm", "press.htm"])
    monkeypatch.setattr(nb.sec_segment, "_cached_get",
                        lambda url: (REL_H1 if url.endswith("press.htm") else "Dear shareholders").encode())
    assert cols(nb.release_of(f), "rev")[1][2] == 582.3
    assert nb.release_of(nb.Filing("0001-26-2", "2026-10-01", "6-K", "x.htm")) is None


def test_rounding_to_millions_is_not_a_revision():
    df = pd.DataFrame({"period": ["2025Q2", "2025Q3", "2025Q2", "2025Q3", "2025Q2"],
                       "value": [1212.788, 1364.676, 1212.0, 1365.0, 1250.0],
                       "known_from": [T("2025-08-13"), T("2025-11-13"), T("2026-08-12"), T("2026-11-12"), T("2027-01-01")]})
    out = nc.rounding_revisions_dropped(df)
    assert out[["period", "value"]].values.tolist() == [["2025Q2", 1212.788], ["2025Q3", 1364.676], ["2025Q2", 1250.0]]


def test_oracle_offset_quarter_passes_leakage_check():
    # Oracle Q2 FY (Sep-Nov) = calendar Q4 by midpoint, filed ~10 December: allowed by lag_days = -31
    df = sec.vintages([[sec.Fact(T("2025-09-01"), T("2025-11-30"), 16_058 * M, T("2025-12-11"), "10-Q", "a")]])
    assert latest(df) == {"2025Q4": 16_058}
    spec = catalog.Spec(**{**catalog.by_key(nc.SPECS)["rev_orcl"].__dict__, "fetch": lambda: None})
    table = observations.new_rows(spec, df[["period", "value", "known_from"]], observations._empty())
    checks = warehouse.run_checks(warehouse.connect(table, [spec]))
    assert all(v.empty for v in checks.values()), {k: v for k, v in checks.items() if len(v)}


def test_catalog_entries():
    keys = {s.key for s in nc.SPECS}
    assert keys == {f"{m}_{c}" for m in ("rev", "capex", "ocf") for c in ("orcl", "crwv", "nbis")} | {"capex_iren", "ocf_iren"}
    assert catalog.validate(nc.SPECS) == []
    assert catalog.validate() == []  # no key clashes with the rest of the catalog
    for s in nc.SPECS:
        assert s.freq == "Q" and s.publish and s.revised and s.max_age_days and not s.closed
        assert s.branch == ("G4" if s.key.startswith("rev_") else "G5")
    assert catalog.by_key(nc.SPECS)["rev_orcl"].lag_days == -31
