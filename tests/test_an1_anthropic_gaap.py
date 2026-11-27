"""AN1: Anthropic's reported (GAAP) figures from the registration statement (register 2026-11-27 "AN1").

Synthetic lines for the parser (no network), the committed CSV for the catalog, versions and sums, and BG1's use of the
series (table rows and the quarter table, outside the rule).
"""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import catalog, licenses
from ai_tracker.followed import betalningsgapet as B
from ai_tracker.followed import common as C
from ai_tracker.series import anthropic_gaap as S
from ai_tracker.sources import anthropic_gaap as A
from ai_tracker.sources import credit_issuance_corpus as cc

QUARTERLY = [
    "Quarterly Results of Operations",
    "Quarterly Consolidated Statements of Operations",
    "Three Months Ended",
    "(in millions) | March 31, 2025 | June 30, 2025 | September 30, 2025 | December 31, 2025",
    "Revenue | $ 10 | $ 20 | $ 30 | $ 40",
    "Operating expenses:",
    "Compute and infrastructure | 5 | 6 | 7 | 8",
    "Personnel (1) | 1 | 1 | 1 | 1",
    "Operating income (loss) | (935) | — | 1,200 | (5)",
    "166",
]
STATEMENT = [
    "Consolidated Statements of Operations",
    "(In millions, except share amounts which are in thousands, and per share data)",
    "Year Ended December 31, | Nine Months Ended September 30,",
    "2023 | 2024 | 2025 | 2025 | 2026",
    "(unaudited)",
    "Revenue | $ 41 | $ 386 | $ 100 | $ 60 | $ 300",
    "Compute and infrastructure | 1 | 2 | 26 | 18 | 3",
    "Operating loss | (551) | (2,980) | (8,060) | (5,224) | (1,260)",
    "The accompanying notes are an integral part of these consolidated financial statements.",
    "F-8",
]
SUMMARY = [
    "Consolidated Statements of Operations Data",
    "Year Ended December 31, | Six Months Ended June 30,",
    "(in millions, except share and per share amounts) | 2023 | 2024 | 2025 | 2025 | 2026",
    "Revenue | $ 41 | $ 386 | $ 100 | $ 30 | $ 16,286",
    "12",
]


def test_cells_are_read_without_judgement():
    assert A.parse_cell("$ 1,382") == 1382 and A.parse_cell("(935)") == -935 and A.parse_cell("—") == 0
    assert A.parse_cell("$ (1,627)") == -1627 and A.parse_cell("974") == 974
    for bad in ("n/a", "(12", "12)", "", "1.2.3", "$"):
        with pytest.raises(A.ParseError):
            A.parse_cell(bad)


def test_the_quarter_table_maps_dates_to_calendar_quarters_and_locates_each_cell():
    rows = A.parse_table(QUARTERLY, "quarterly", ["revenue", "compute", "opinc"])
    by = {(r["item"], r["period"]): r for r in rows}
    assert [r["period"] for r in rows if r["item"] == "revenue"] == ["2025Q1", "2025Q2", "2025Q3", "2025Q4"]
    assert by[("opinc", "2025Q1")]["value"] == -935 and by[("opinc", "2025Q2")]["value"] == 0
    r = by[("revenue", "2025Q3")]
    assert r["kind"] == "q" and r["period_end"] == "2025-09-30" and r["page"] == "166"
    assert r["locator"] == "lines #3,#4 col #2"
    assert r["quote"] == QUARTERLY[3] + "\n" + QUARTERLY[4]
    assert r["quote_sha256"] == cc.block_hash([QUARTERLY[3], QUARTERLY[4]])
    assert A.cell_value(QUARTERLY, r["locator"]) == 30


def test_the_statement_splits_years_from_the_year_to_date_columns():
    rows = A.parse_table(STATEMENT, "operations", ["revenue", "opinc"])
    cols = [(r["kind"], r["period"], r["period_end"]) for r in rows if r["item"] == "revenue"]
    assert cols == [("a", "2023", "2023-12-31"), ("a", "2024", "2024-12-31"), ("a", "2025", "2025-12-31"),
                    ("ytd", "2025Q3", "2025-09-30"), ("ytd", "2026Q3", "2026-09-30")]
    assert next(r for r in rows if r["item"] == "opinc" and r["period"] == "2026Q3")["value"] == -1260
    assert rows[0]["page"] == "F-8" and rows[0]["locator"].startswith("lines #2,#3,#5 ")
    # the summary table has its years on the line with the units label
    s = A.parse_table(SUMMARY, "summary", ["revenue"])
    assert [(r["kind"], r["period"], r["value"]) for r in s][-2:] == [("ytd", "2025Q2", 30), ("ytd", "2026Q2", 16286)]


def test_signs_are_registered_per_item():
    lines = ["Consolidated Statements of Cash Flows", "(In millions)",
             "Year Ended December 31, | Six Months Ended June 30,", "2024 | 2025 | 2025 | 2026",
             "Net cash provided by (used in) operating activities | (5,692) | (2,637) | (1,513) | 3,929",
             "Purchases of property and equipment | (15) | (131) | (18) | (482)",
             "Prepayments for leased assets and equipment | — | (54) | — | (1,955)"]
    rows = {(r["item"], r["period"]): r["value"] for r in A.parse_table(lines, "cashflows", ["cfo", "capex",
                                                                                             "prepay_leased"])}
    assert rows[("cfo", "2024")] == -5692 and rows[("cfo", "2026Q2")] == 3929  # signed as stated
    assert rows[("capex", "2026Q2")] == 482 and rows[("prepay_leased", "2025")] == 54  # outflows as positive


def test_nothing_is_guessed():
    with pytest.raises(A.ParseError, match="title"):
        A.parse_table(QUARTERLY[2:], "quarterly", ["revenue"])
    with pytest.raises(A.ParseError, match="not found"):
        A.parse_table(QUARTERLY, "quarterly", ["cfo"])
    short = QUARTERLY[:4] + ["Revenue | $ 10 | $ 20 | $ 30"] + QUARTERLY[5:]
    with pytest.raises(A.ParseError, match="cells"):
        A.parse_table(short, "quarterly", ["revenue"])
    twice = QUARTERLY + QUARTERLY[1:]
    with pytest.raises(A.ParseError, match="exactly 1"):
        A.parse_table(twice, "quarterly", ["revenue"])
    # a row listed as absent gives no values, and its presence is an error
    lines = ["Consolidated Statements of Cash Flows", "(In millions)", "Year Ended December 31, | Six Months Ended "
             "June 30,", "2025 | 2025 | 2026", "Purchases of property and equipment | (131) | (18) | (482)"]
    assert A.parse_table(lines, "cashflows", ["prepay_leased"], absent=("prepay_leased",)) == []
    with pytest.raises(A.ParseError, match="absent"):
        A.parse_table(lines, "cashflows", ["capex"], absent=("capex",))


def _csv_rows(values: dict[tuple[str, str], list[tuple[str, float]]]) -> pd.DataFrame:
    """{(series, period): [(filed, value), ...]} -> CSV-shaped rows, one per document."""
    rows = []
    for (key, period), docs in values.items():
        for filed, v in docs:
            acc = f"acc-{filed}"
            item, kind = key.removeprefix("lab_gaap_anthropic_").rsplit("_", 1)
            rows.append({"id": f"{acc}-{key}-{period}", "series": key, "item": item, "kind": kind, "period": period,
                         "value": v, "filed": filed, "accepted": filed + "T12:00:00.000Z", "accession": acc})
    return pd.DataFrame(rows)


def test_versions_take_the_first_document_and_every_change():
    key = "lab_gaap_anthropic_revenue_q"
    df = _csv_rows({(key, "2026Q2"): [("2026-10-26", 100.0), ("2026-11-02", 100.0), ("2026-11-10", 101.0)],
                    (key, "2026Q3"): [("2026-11-02", 200.0), ("2026-11-17", 200.0)]})
    v = A.versions(df, key)
    assert list(zip(v["period"], v["value"], v["known_from"].dt.strftime("%Y-%m-%d"))) == [
        ("2026Q2", 100.0, "2026-10-26"), ("2026Q2", 101.0, "2026-11-10"), ("2026Q3", 200.0, "2026-11-02")]


def test_gross_profit_is_derived_within_one_document():
    rev, cor = "lab_gaap_anthropic_revenue_a", "lab_gaap_anthropic_cost_of_revenue_a"
    df = _csv_rows({(rev, "2025"): [("2026-10-26", 100.0), ("2026-11-02", 100.0)],
                    (cor, "2025"): [("2026-11-02", 30.0)]})  # cost of revenue first in the second document
    v = A.versions(df, "lab_gaap_anthropic_gross_profit_a")
    assert list(zip(v["period"], v["value"], v["known_from"].dt.strftime("%Y-%m-%d"))) == [("2025", 70.0, "2026-11-02")]


def test_sum_checks_compare_quarters_with_the_year_and_the_year_to_date():
    rows = [dict(r, accession="a1", form="S-1", filed="2026-10-26") for r in
            A.parse_table(QUARTERLY, "quarterly", ["revenue"]) + A.parse_table(STATEMENT, "operations", ["revenue"])]
    checks = A.sum_checks(pd.DataFrame(rows))
    year = next(c for c in checks if c["check"].endswith("a 2025"))
    assert year["sum"] == 100 and year["stated"] == 100 and year["ok"]
    nine = next(c for c in checks if c["check"].endswith("ytd 2025Q3"))
    assert nine["sum"] == 60 and nine["ok"]


# ------------------------------------------------------------------ the committed extraction and the catalog


def test_the_committed_csv_is_valid_and_has_every_registered_series():
    df = A.load()
    assert A.validate(df) == []
    assert set(df["form"]) == {"S-1", "S-1/A", "424B4"} and df["accession"].nunique() == 5
    keys = {A.series_key(i, k) for i, k in S.keys()}
    stated = keys - {"lab_gaap_anthropic_gross_profit_a", "lab_gaap_anthropic_gross_profit_ytd"}
    assert stated == set(df.loc[df["series"] != "", "series"])
    first = df.sort_values("filed").groupby(["series", "period"]).first()
    assert first["filed"].min() == "2026-10-26"  # never dated before the public S-1


def test_the_catalog_series_are_withheld_and_commercially_usable():
    specs = [s for s in catalog.ALL if s.key.startswith("lab_gaap_anthropic_")]
    assert len(specs) == 19
    assert not [e for e in catalog.validate() if "lab_gaap" in e]
    for s in specs:
        assert s.publish is False and s.branch == "G4" and s.unit == "MUSD"
        assert licenses.verdict(s).klass == licenses.JA
        v = s.fetch()
        assert not v.empty and (v["known_from"] >= pd.Timestamp("2026-10-26")).all()


def test_the_run_rate_and_gaap_series_stay_apart():
    gaap = {s.key for s in catalog.ALL if s.key.startswith("lab_gaap_")}
    assert not gaap & set(B.LABS) and set(B.LABS_GAAP) <= gaap
    assert not any("GAAP" in b for b in B.BLOCKED)


# ------------------------------------------------------------------ BG1 (register AN1, (f))


def _obs(key: str, freq: str, rows: list[tuple[str, float, str]]) -> list[dict]:
    return [{"series": key, "freq": freq, "period": p, "value": v, "known_from": pd.Timestamp(kf), "source": "release",
             "fetched_at": pd.Timestamp("2026-11-27")} for p, v, kf in rows]


def _table() -> pd.DataFrame:
    rows = _obs("lab_gaap_anthropic_revenue_q", "Q", [("2026Q2", 11555.0, "2026-10-26"),
                                                       ("2026Q3", 16956.0, "2026-11-02")])
    rows += _obs("lab_gaap_anthropic_compute_q", "Q", [("2026Q2", 5558.0, "2026-10-26"),
                                                       ("2026Q3", 9863.0, "2026-11-02")])
    rows += _obs("lab_gaap_anthropic_opinc_q", "Q", [("2026Q2", 974.0, "2026-10-26")])
    rows += _obs("lab_rev_anthropic_company_run_rate", "D", [("2026-05-28", 47000.0, "2026-05-28"),
                                                             ("2026-09-15", 60000.0, "2026-10-05")])
    rows += _obs("lab_rev_anthropic_company_run_rate_s1", "D", [("2026-10-31", 81000.0, "2026-11-10")])
    return pd.DataFrame(rows)


def test_the_quarter_table_shows_the_run_rate_known_at_the_quarter_end_beside_the_gaap_revenue():
    t = _table()
    qs = B.lab_quarters(t, pd.Timestamp("2026-11-26"))
    assert [q["period"] for q in qs] == ["2026Q2", "2026Q3"]
    q2, q3 = qs
    assert q2["x4"] == 4 * 11555 and q2["compute_pct"] == pytest.approx(100 * 5558 / 11555) and q2["opinc"] == 974
    assert q3["opinc"] is None
    # 2026-09-15 refers to the quarter but became known only on 2026-10-05: not known at the quarter's end
    assert q3["run_rate"]["date"] == "2026-05-28" and q3["run_rate"]["value"] == 47000
    # the as-of boundary: the S-1/A quarter is not there before 2026-11-02
    assert [q["period"] for q in B.lab_quarters(t, pd.Timestamp("2026-11-01"))] == ["2026Q2"]
    assert B.lab_quarters(t, pd.Timestamp("2026-10-25")) == []


def test_bg1_renders_the_gaap_rows_outside_the_rule_and_keeps_every_reading():
    t = _table()
    r = B.compute("2026-11-26", table=t)
    text = B.render(r)
    assert "Anthropics redovisade tal (GAAP" in text and "Skillnaden mot run-rate" in text
    assert "| 2026Q3 | 17,0 mdr | 67,8 mdr |" in text
    assert "BLOCKED:** OpenAI" in text and "BLOCKED:** Anthropic" not in text
    base = B.compute("2026-11-26", table=t[~t["series"].str.startswith("lab_gaap_")])
    assert [x["outcome"] for x in r["readings"]] == [x["outcome"] for x in base["readings"]]
    assert B.antenna(r) == B.antenna(base)  # the antenna does not read the GAAP rows
    empty = B.render(B.compute("2025-11-26", table=t))
    assert "Inga redovisade kvartal kända på dagen." in empty
    assert C.fmt_bn(16956) == "17,0 mdr"
