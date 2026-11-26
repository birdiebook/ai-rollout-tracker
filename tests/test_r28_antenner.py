"""R28 adversarial review of run 16 "antenner" (F0, LT1, BG1, EL1): docs/granskning/r28_antenner.md. No network.

Evidence was read on 2026-11-26 in the code, the register, the observation table (854 series, fetched 2026-11-26) and
15 EDGAR 8-K exhibits fetched again from www.sec.gov (generic client identity, one request at a time). Only ids,
numbers and dates are kept here, never filing text.

- Pinned: the four register entries of 2026-11-26 as R28 read them, and the 15 ob_* rows R28 found correct in the
  source documents. A change to either must be reviewed again.
- Properties that hold: F0's rule is symmetric (mirrored X and Y give the mirrored outcome and counts; flipping the
  sign of Y and of s gives the same outcome).
- Findings R28-1, R28-2 and R28-3 were strict xfails; X25 fixed them and they are plain tests now.
"""

from __future__ import annotations

import hashlib
import random
import sys
from pathlib import Path

import pandas as pd
import pytest

from ai_tracker import config
from ai_tracker.followed import antenner as AN
from ai_tracker.followed import betalningsgapet as B
from ai_tracker.followed import common as C
from ai_tracker.followed import elflaskhalsen as E
from ai_tracker.followed import ledtid as L

sys.path.insert(0, str(Path(__file__).parent))
import test_followed_betalningsgapet as TB  # noqa: E402  (the questions' own synthetic worlds)
import test_followed_elflaskhalsen as TE  # noqa: E402
import test_followed_ledtid as TL  # noqa: E402

REGISTER = config.REPO / "docs" / "mattregister.md"
ORDERS = config.REPO / "curated" / "orders_backlog.csv"
SEEN_NOTE = "inget utfall på osedda data"

# ------------------------------------------------------------------ pinned: the register entries R28 read

ENTRIES = {  # heading -> sha256 of the entry's text after the heading line, up to the next "### "
    "### 2026-11-26 – F0: mall för symmetriska läsregler i följda frågor":
        "f9049cb9c3e7e108389c0bc85149d06ea5f91080928bf3165d2d88b19c81333d",
    "### 2026-11-26 – LT1: ledtid mellan leverantörernas orderstock och köparnas capex-takt (följd fråga)":
        "f5186914ca87ab4a320e41e2f71941e009628b711352465711d5a3ea8eeb361c",
    "### 2026-11-26 – BG1: följd fråga om betalningsgapet (intäktskrav mot intäkterna som ska bära det)":
        "fc816a4d3b0605cb824884e24bbe36cdf077be51761e5c52a5c888d33104f295",
    "### 2026-11-26 – EL1: följd fråga om elen som begränsning för utbyggnaden (förregistrering, före beräkning)":
        "bb4714762d672f768e766e8f681347eedc60c0ac564b941c2e6fd662312e26c2",
}


def test_register_entries_are_the_ones_r28_reviewed():
    text = REGISTER.read_text(encoding="utf-8")
    for head, digest in ENTRIES.items():
        assert head + "\n" in text, head
        entry = text.split(head + "\n", 1)[1].split("\n### ", 1)[0]
        assert hashlib.sha256(entry.encode("utf-8")).hexdigest() == digest, head


# ------------------------------------------------------------------ pinned: the 15 ob_* rows checked on sec.gov

SAMPLE = {  # id -> (value, filed): each value stands in the 8-K exhibit at source_url (R28, section 6)
    "etn-2025-05-02-02": (-4.0, "2025-05-02"), "etn-2025-08-05-02": (2.0, "2025-08-05"),
    "etn-2026-02-03-02": (16.0, "2026-02-03"), "etn-2026-05-05-02": (42.0, "2026-05-05"),
    "etn-2026-11-03-02": (39.0, "2026-11-03"),
    "dlr-2025-07-24-07": (135.320, "2025-07-24"), "dlr-2026-04-23-07": (422.774, "2026-04-23"),
    "dlr-2026-10-29-07": (626.604, "2026-10-29"),
    "dlr-2024-10-24-08": (188.8, "2024-10-24"), "dlr-2025-10-23-08": (49.8, "2025-10-23"),
    "dlr-2026-07-23-08": (79.0, "2026-07-23"),
    "gev-2025-07-23-19": (50.0, "2025-07-23"), "gev-2025-10-22-18": (62.0, "2025-10-22"),
    "gev-2026-04-22-18": (100.0, "2026-04-22"), "gev-2026-10-28-18": (122.0, "2026-10-28"),
}


def test_sampled_orders_rows_are_unchanged():
    d = pd.read_csv(ORDERS).set_index("id")
    for i, (value, filed) in SAMPLE.items():
        assert i in d.index, i
        assert float(d.loc[i, "value"]) == pytest.approx(value, abs=1e-9), i
        assert str(d.loc[i, "filed"]) == filed, i
        assert str(d.loc[i, "source_url"]).startswith("https://www.sec.gov/Archives/edgar/data/"), i


# ------------------------------------------------------------------ property: F0's rule is symmetric


def test_rule_mirrors_exactly():
    qs = [str(q) for q in pd.period_range("2020Q1", "2026Q3", freq="Q-DEC")]
    rnd = random.Random(28)
    for _ in range(400):
        g, h, k, s = rnd.choice([2.0, 5.0, 10.0]), rnd.choice([0.0, 5.0, 10.0]), rnd.choice([1, 2, 4]), rnd.choice([1, -1])
        x = {q: rnd.choice([None, rnd.gauss(0, 12), g, -g]) for q in qs}
        y = {q: rnd.choice([None, rnd.gauss(0, 12), h, -h, 0.0]) for q in qs[1:]}
        t = qs[-1]
        neg = {q: None if v is None else -v for q, v in x.items()}
        negy = {q: None if v is None else -v for q, v in y.items()}
        a = C.read_rule(x, y, g=g, h=h, k=k, sign=s, t=t)
        b = C.read_rule(neg, negy, g=g, h=h, k=k, sign=s, t=t)
        c = C.read_rule(x, negy, g=g, h=h, k=k, sign=-s, t=t)
        assert a["outcome"] == b["outcome"] == c["outcome"] and a["origin"] == b["origin"] == c["origin"]
        ha, hb = a["history"], b["history"]
        assert (ha["impulses_up"], ha["impulses_down"]) == (hb["impulses_down"], hb["impulses_up"])
        assert ha["by_direction"]["up"] == hb["by_direction"]["down"] and ha["n_tested"] == hb["n_tested"]


# ------------------------------------------------------------------ R28-1: the seen-data caveat switches off too early


@pytest.fixture
def _no_f1(monkeypatch):
    from ai_tracker.series import guidance_revisions as F1

    monkeypatch.setattr(F1, "load_csv", lambda: None)


def test_r28_1_bg1_keeps_the_seen_note_when_no_new_quarter_has_come():
    w = TB.world()  # every row known by 2026-01-30, long before the register day 2026-11-26
    r = B.compute("2026-11-30", w)  # month end, no row known after the register day
    assert SEEN_NOTE in B.render(r)


def test_r28_1_el1_keeps_the_seen_note_when_no_new_quarter_has_come():
    w = TE.world()  # every row known by 2026-11-04
    r = E.compute("2026-11-30", w)
    assert SEEN_NOTE in E.render(r)


def test_r28_1_lt1_main_reading_keeps_the_seen_note_when_another_row_gets_a_new_quarter(_no_f1):
    w = TL._world(("2025Q1", 0.02, 0.06), ("2025Q3", 0.03, 0.08))  # L1 and the inner capex, known by 2026-11-04
    eq = TL._rows("rpo_eqix", {q: 100.0 for q in TL.QS})
    late = pd.DataFrame([{"series": "rpo_eqix", "freq": "Q", "period": "2026Q4", "value": 100.0,
                          "known_from": pd.Timestamp("2026-12-10"), "source": "release",
                          "fetched_at": pd.Timestamp("2026-12-10")}])
    r = L.compute("2026-12-15", pd.concat([w, eq, late], ignore_index=True))
    main = L.find(r, *r["main"])
    assert main["t"] == "2026Q3"  # the main reading has no quarter that came after the register day
    assert SEEN_NOTE in L.render(r)


# ------------------------------------------------------------------ R28-2: overlapping acquisitions in LT1


def test_r28_2_both_acquisitions_are_marked_at_2026q2():
    marks = L.acquisition_quarters("L1")
    assert "Fibrebond" in marks["2026Q2"] and "Boyd" in marks["2026Q2"]


# ------------------------------------------------------------------ R28-3: a change in BG1's antenna that is not one


def _bg1_report(main_t: str) -> dict:
    hist = {"impulses_up": 0, "impulses_down": 0, "n_x": 0}
    rd = [{"id": s["id"], "label": s["label"], "outcome": C.NEITHER,
           "t": "2026Q3" if s["who"] == "orcl" else main_t, "history": hist} for s in B.reading_specs()]
    q = {B._key("gap_moln", "moln4", B.R_MAIN): {"available": False}, B._key("capex4", "moln4"): {"available": False}}
    return {"readings": rd, "quantities": q, "next_filings": []}


def test_r28_3_unchanged_oracle_rows_are_not_listed_as_changed():
    # a month ago the main reading was at 2026Q2 and Oracle (who files first) at 2026Q3; now both are at 2026Q3.
    # Oracle's outcome and quarter are the same both months.
    ch = AN.changes(B.antenna(_bg1_report("2026Q2")), B.antenna(_bg1_report("2026Q3")))
    assert not [c for c in ch if c.startswith("Oracle")], ch
