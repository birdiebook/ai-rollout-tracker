"""X27: corrections after the review R30 (docs/granskning/r30_korning18.md). No network.

- R30-1: the LT1 report says through which quarter each coded company's filings are read on the reading day, and an
  origin (före) or deciding quarter (efter) after that quarter says "förvärv inte kodade" instead of looking like a
  quarter coded without acquisitions. The text never changes an outcome.
- R30-2: Dell's quarter a follows the fiscal calendar (52/53 weeks to the Friday nearest January 31, quarters 1 to 3
  of 13 weeks): the period ends of all Dell documents behind the table are the computed quarter ends.
- R30-3: the description of Equinix 2025Q4 follows the goodwill table (the R30 test covers the note and the source
  document; here the decision log and the source document's table row).
"""

from __future__ import annotations

import re

import pandas as pd
import pytest

from ai_tracker import config
from ai_tracker.followed import ledtid as L
from ai_tracker.sources import acquisitions as A


@pytest.fixture(scope="module")
def df():
    return A.load()


# ------------------------------------------------------------------ R30-2: Dell's fiscal calendar


@pytest.mark.parametrize("year,end", [(2022, "2022-01-28"), (2023, "2023-02-03"), (2024, "2024-02-02"),
                                      (2025, "2025-01-31"), (2026, "2026-01-30"), (2027, "2027-01-29")])
def test_dell_fiscal_year_ends_on_the_friday_nearest_january_31(year, end):
    assert A.fiscal_year_end(year) == pd.Timestamp(end) and A.fiscal_year_end(year).weekday() == 4


def test_dell_quarter_ends_are_the_report_dates_of_its_filings(df):
    d = df[df["company"] == "dell"]
    assert len(set(d["source_url"])) == 14  # the documents behind Dell's rows (2023Q1 to 2026Q2)
    for url, q in zip(d["source_url"], d["quarter"]):
        day = pd.Timestamp(re.search(r"-(\d{8})\.htm$", url).group(1))
        fq = A.quarter_of(str(day.date()), "dell")
        assert A.fiscal_quarter_end(fq) == day  # the document's period ends on the computed quarter end
        assert A.quarter_of(str((day + pd.Timedelta(days=1)).date()), "dell") == str(pd.Period(fq, freq="Q") + 1)
        assert A.report_quarter(url, "dell") == fq
        if d.loc[d["source_url"] == url, "form"].iloc[0] == "10-Q":
            assert fq == q  # a 10-Q row is for the quarter the 10-Q reports on


def test_dell_quarter_of_is_unchanged_away_from_the_boundaries():
    # the one-month shift before X27 gave the same quarter for every day more than a week from a fiscal quarter end
    days = pd.date_range("2023-02-04", "2026-07-31", freq="D")
    old = {str(t.date()): str(pd.Period(t - pd.DateOffset(months=1), freq="Q")) for t in days}
    diff = [d for d in old if A.quarter_of(d, "dell") != old[d]]
    ends = [A.fiscal_quarter_end(str(q)) for q in pd.period_range("2022Q4", "2026Q3", freq="Q")]
    assert diff and all(min(abs((pd.Timestamp(d) - e).days) for e in ends) <= 7 for d in diff)
    assert all(A.quarter_of(d, c) == str(pd.Period(d, freq="Q")) for d in ("2023-11-01", "2024-02-01")
               for c in ("pwr", "smci", "eqix"))


def test_no_coded_mark_moves(df):
    # every row with a closing day lies in its quarter by the new quarter_of (load() checks it), and Dell has none
    closed = df[df["closed"] != ""]
    assert all(A.quarter_of(c, co) == q for c, co, q in zip(closed["closed"], closed["company"], closed["quarter"]))
    assert not (closed["company"] == "dell").any()


# ------------------------------------------------------------------ R30-1: coded through which quarter


def test_coded_through_is_the_last_period_read_per_day(df):
    assert {c: A.coded_through(c, "2026-11-27", df) for c in A.COMPANIES} == {
        "pwr": "2026Q3", "dell": "2026Q2", "smci": "2026Q3", "eqix": "2026Q3"}  # Quanta's 2026Q4 event is subsequent
    assert {c: A.coded_through(c, "2025-11-27", df) for c in A.COMPANIES} == {
        "pwr": "2025Q3", "dell": "2025Q2", "smci": "2025Q3", "eqix": "2025Q3"}
    assert A.coded_through("dell", "2022-12-31", df) is None


def test_every_quarter_up_to_coded_through_has_a_row(df):
    # coded_through means the coding is complete up to it: no gaps from 2023Q1
    for c in A.COMPANIES:
        last = A.coded_through(c, None, df)
        qs = {str(q) for q in pd.period_range(A.FIRST_QUARTER, last, freq="Q")}
        assert qs <= set(df.loc[df["company"] == c, "quarter"])


def test_uncoded_marks_quarters_after_the_coding_only():
    assert L.uncoded("L2", "2026Q2", "2026-11-27") is None
    assert L.uncoded("L2", "2026Q3", "2026-12-10") == "Dell efter 2026Q2"
    assert L.uncoded("L2", "2026Q4", "2027-03-15") == "Dell efter 2026Q2; Super Micro efter 2026Q3"
    assert L.uncoded("L3", "2026Q4", "2027-02-15") == "Equinix efter 2026Q3"
    assert L.uncoded("L1", "2026Q4", "2027-02-15") == "Quanta efter 2026Q3"
    assert L.uncoded("O1", "2026Q4", "2027-02-15") is None  # no coded company
    assert L.uncoded("L2", "2022Q4", "2026-11-27") is None and L.uncoded("L2", None) is None


def _ms(row_key: str, xs: dict[str, float], ys: dict[str, float]) -> dict[str, dict]:
    def m(key, ch):
        return {"series": key, "available": True, "period": max(ch), "known_from": "2026-12-09",
                "path": {q: {"level": 1.0, "pace": 0.0, "change": v} for q, v in ch.items()}}
    return {row_key: m(row_key, xs), "kl_capex4_inner": m("kl_capex4_inner", ys)}


# Dell's 10-Q for 2026Q3 (about 2026-12-09) before it is coded: in "efter" 2026Q3 decides an origin (the first unseen
# reading of L2); in "före" it is an origin once the buyers have a later quarter
@pytest.mark.parametrize("direction,end", [("efter", "2026Q3"), ("fore", "2026Q4")])
def test_a_quarter_after_the_coding_is_marked_and_no_outcome_changes(monkeypatch, direction, end):
    qs = [str(q) for q in pd.period_range("2024Q1", end, freq="Q")]
    sup = {q: 0.0 for q in qs} | {"2026Q3": 30.0}
    buy = {q: 0.0 for q in qs} | {"2026Q2": 12.0}
    ms = _ms(L.SUPPLIERS["L2"][0], sup, buy)
    r = L.reading("L2", "inner", direction, 2, ms, "2026-12-10")
    key = "origin" if direction == "fore" else "decided_at"
    rows = r["history_rows"] + r["origins"]
    marked = {o[key] for o in rows if o.get("acquisition_uncoded")}
    assert marked and marked <= {"2026Q3"}
    assert all(o["acquisition_uncoded"] == "Dell efter 2026Q2" for o in rows if o.get("acquisition_uncoded"))
    keys = ("outcome", "origin", "t", "decided_at")
    monkeypatch.setattr(L, "ACQ_COMPANIES", {})
    without = L.reading("L2", "inner", direction, 2, ms, "2026-12-10")
    assert {k: r.get(k) for k in keys} == {k: without.get(k) for k in keys}
    assert [o["outcome"] for o in rows] == [o["outcome"] for o in without["history_rows"] + without["origins"]]


def test_cell_shows_the_uncoded_text():
    r = {"outcome": L.C.UNDECIDED, "origin": "2026Q3",
         "origins": [{"origin": "2026Q3", "x": 30.0, "decided_at": None, "acquisition": None,
                      "acquisition_uncoded": "Dell efter 2026Q2", "reason": None}]}
    assert "(förvärv inte kodade: Dell efter 2026Q2)" in L._cell(r)


def test_caveat_names_the_last_coded_quarter_per_company():
    t = L.coded_through_text({"pwr": "2026Q3", "dell": "2026Q2", "smci": "2026Q3", "eqix": "2026Q3"})
    assert ("Quanta till och med 2026Q3, Dell till och med 2026Q2, Super Micro till och med 2026Q3 och Equinix till och "
            "med 2026Q3") in t and "förvärv inte kodade" in t


# ------------------------------------------------------------------ R30-3: Equinix 2025Q4


def test_equinix_2025q4_follows_the_goodwill_table(df):
    note = df.set_index("id").loc["eqix-2025Q4-01", "note"]
    assert "#2682" in note and "EMEA" in note and "'" not in note.replace("TIM's", "")  # no quoted filing text
    doc = (config.REPO / "docs" / "kallor" / "ledtid.md").read_text(encoding="utf-8")
    assert "including the TIM Acquisition" not in doc
    assert "| Equinix | 2025Q4 | ej namngivet, i EMEA |" in doc and "goodwill 11" in doc
    # the label and the mark are unchanged (R30: the row and its mark are correct)
    assert df.set_index("id").loc["eqix-2025Q4-01", "label"] == "Equinix, ej namngivet förvärv 2025Q4"
