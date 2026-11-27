"""X26: correction of S1, QA1 and PV1 after review R29 (register 2026-11-27 "X26"). Synthetic data, except where marked.

- the register entry is in place and the module constants match it
- PV1: the geometric rows H-G, a-G and b-G beside the locked ones, exactly symmetric, the locked readings untouched,
  months and weeks <= 0 give no quarter, the backfill caveat and the antenna fact
- QA1: a label states only what was filed on its day, the same-day check, the two new considerations
- S1: the transition note no longer waits for the owner (closed by B18), EL1-S no longer says Quanta is unchecked
"""

from __future__ import annotations

import csv
import inspect
import math
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest

from ai_tracker import config
from ai_tracker.followed import common as C
from ai_tracker.followed import elflaskhalsen as E
from ai_tracker.followed import ledtid as L
from ai_tracker.followed import prisvolym as P
from ai_tracker.sources import acquisitions as ACQ

sys.path.insert(0, str(Path(__file__).parent))
import test_followed_prisvolym as TP  # the synthetic PV1 world

REGISTER = config.REPO / "docs" / "mattregister.md"
ENTRY = "### 2026-11-27 – X26: rättning av S1, QA1 och PV1 efter granskningen R29 (körning 17)"
DAY = "2026-11-27"


def test_register_entry_is_in_place_and_after_pv1():
    text = REGISTER.read_text(encoding="utf-8")
    assert ENTRY + "\n" in text
    assert text.index(ENTRY) > text.index("### 2026-11-27 – PV1:")
    entry = text.split(ENTRY + "\n", 1)[1].split("\n### ", 1)[0]
    for want in ("**H-G**, **a-G** och **b-G**", "exp(medlet av ln", "minst 1 förvärv", "väntar på ägarens bekräftelse"):
        assert want in entry, want
    assert P.X26_REGISTERED == "2026-11-27"
    assert P.READINGS_G == {"H-G": ("pv1_pris_gpqa_gq", "pv1_sdk_gq"), "a-G": ("pv1_pris_arena_gq", "pv1_sdk_gq"),
                            "b-G": ("pv1_pris_gpqa_gq", "pv1_sdk_rel_gq")}
    assert {k: v for k, v in P.DERIVED_G.items()} == {k.replace("_q", "_gq"): v for k, v in P.DERIVED.items()}
    assert P.MAIN_LOCKED == "H" and P.MAIN == "H-G"  # X26 put H-G beside H; the owner made it the main reading (B18)


# ------------------------------------------------------------------ PV1: geometric rows


def test_geometric_month_quarter_is_exp_of_the_mean_log():
    rows = TP.monthly(P.PRICE_GPQA, {"2026Q3": 1.0})
    t = pd.DataFrame(rows)
    t.loc[t["period"] == "2026-09", "value"] = 8.0
    q = P.monthly_quarters(t, (P.PRICE_GPQA,), geometric=True)
    assert q["2026Q3"][0] == pytest.approx(2.0)  # (1 * 1 * 8) ** (1/3)
    assert q["2026Q3"][1] == "2026-10-01"
    assert P.monthly_quarters(t, (P.PRICE_GPQA,))["2026Q3"][0] == pytest.approx(10.0 / 3.0)
    with pytest.raises(ValueError):
        P.monthly_quarters(t, (P.PRICE_GPQA, P.PRICE_ARENA), geometric=True)


def test_geometric_quarter_needs_positive_values():
    t = pd.DataFrame(TP.monthly(P.PRICE_GPQA, {"2026Q2": 1.0, "2026Q3": 1.0}))
    t.loc[t["period"] == "2026-08", "value"] = 0.0
    q = P.monthly_quarters(t, (P.PRICE_GPQA,), geometric=True)
    assert "2026Q3" not in q and "2026Q2" in q
    w = pd.DataFrame(TP.weekly(P.CONTROL[0], {"2026Q2": 5.0, "2026Q3": 5.0}))
    w.loc[w.index[-1], "value"] = 0.0
    g = P.weekly_quarters(w, (P.CONTROL[0],), geometric=True)
    assert "2026Q3" not in g and g["2026Q2"][0] == pytest.approx(5.0)
    assert P.weekly_quarters(w, (P.CONTROL[0],))["2026Q3"][0] == pytest.approx(5.0 * 12 / 13)


def _mirror(t: pd.DataFrame) -> pd.DataFrame:
    m = t.copy()
    price = m["series"].isin((P.PRICE_GPQA, P.PRICE_ARENA))
    m.loc[price, "value"] = 1.0 / m.loc[price, "value"]
    return m


def _step_world(factor: float) -> pd.DataFrame:
    """The synthetic world with a price step by `factor` in the last month of 2026Q1 only (a step inside a quarter)."""
    t = TP.world()
    price = t["series"].isin((P.PRICE_GPQA, P.PRICE_ARENA))
    late = t["period"].isin([str(m) for m in pd.period_range("2026-03", "2026-12", freq="M")])
    t.loc[price & late, "value"] *= factor
    return t


@pytest.mark.parametrize("factor", [0.25, 4.0, 0.1])
def test_geometric_rows_give_the_mirrored_change_and_outcome(factor):
    t = _step_world(factor)
    r, m = P.compute(DAY, table=t), P.compute(DAY, table=_mirror(t))
    for key in ("pv1_pris_gpqa_gq", "pv1_pris_arena_gq"):
        a, b = C.series_of(r["measures"][key], "change"), C.series_of(m["measures"][key], "change")
        assert a and set(a) == set(b)
        for q in a:
            if a[q] is not None:
                assert a[q] == pytest.approx(-b[q], abs=1e-6), (key, q)
    for name in P.READINGS_G:
        x, y = r["readings_geo"][name], m["readings_geo"][name]
        ox = [(o["origin"], o["direction"], o["outcome"]) for o in x["origins"] if o["direction"]]
        oy = [(o["origin"], -o["direction"], o["outcome"]) for o in y["origins"] if o["direction"]]
        assert ox and ox == oy, name  # each impulse flips its direction; Y is the same, so talar för <-> talar emot flips
        assert x["history"]["impulses_up"] == y["history"]["impulses_down"]


def test_locked_readings_are_the_same_with_the_geometric_rows():
    """The locked rows read only the arithmetic quantities: computing the geometric rows changes nothing in them."""
    t = _step_world(0.25)
    r = P.compute(DAY, table=t)
    for name, (x, y) in P.READINGS.items():
        want = C.read_measures(r["measures"][x], r["measures"][y], x_stat=P.X_STAT, g=P.G, h=P.H, k=P.K, sign=P.SIGN)
        got = r["readings"][name]
        assert {k: got[k] for k in ("outcome", "origin", "t", "history")} == \
               {k: want[k] for k in ("outcome", "origin", "t", "history")}
    md = P.render(r)  # since B18, point 2: H-G, a-G and b-G in section 3, the locked rows in section 6
    head, tail = md.split("## 5. Förbehåll", 1)
    assert "(H-G, huvudläsning)" in head and "## 6. Aritmetiskt kvartalsmedel" in tail
    for name in P.READINGS:
        assert P.READING_NAME[name] in tail and P.READING_NAME[name] not in head


def test_geometric_rows_have_seen_flags_and_an_antenna_fact():
    r = P.compute("2026-12-31", table=TP.world(-60.0, 30.0))
    assert all("seen" in x for x in r["readings_geo"].values())
    row = P.antenna(r)
    fact = row["facts"]["Låsta rader H / a / b (aritmetiskt medel)"]  # since B18, point 2: the locked rows are the fact
    assert fact.count(" / ") == 2 and fact.split(" / ")[0] == P.short(r["readings"]["H"])
    assert row["outcome"] == r["readings_geo"]["H-G"]["outcome"]  # the row's outcome is H-G's (B18, point 2)


def test_classes_of_geometric_keys_follow_their_inputs():
    cl = P.classes(P.used_series())
    for k in P.DERIVED:
        assert cl[k.replace("_q", "_gq")] == cl[k]
    assert cl["pv1_sdk_rel_gq"] == cl["pv1_sdk_rel_q"]


def test_backfill_caveat_counts_rows_fetched_after_the_day():
    t = TP.world()
    r = P.compute("2025-11-27", table=t)
    assert r["fetch"]["after"] == r["fetch"]["n"] > 0  # the synthetic rows are all fetched 2026-11-27
    text = P.backfill_caveat(r)
    assert "backfill" in text and f"{r['fetch']['n']} av {r['fetch']['n']} rader" in text
    r2 = P.compute(DAY, table=t)
    assert r2["fetch"]["after"] == 0 and "i efterhand i en omgång" in P.backfill_caveat(r2)
    assert P.backfill_caveat(r2) in P.render(r2).split("## 5. Förbehåll", 1)[1]


# ------------------------------------------------------------------ QA1: labels per filing day


def _labels(day: str, q: str) -> list[str]:
    return [m[0] for m in ACQ.marks("pwr", day) if m[1] == q]


def test_labels_state_what_was_filed_on_the_day():
    assert _labels("2024-02-25", "2024Q1") == ["Quanta, 2 förvärv 2024Q1"]
    assert _labels("2024-05-02", "2024Q1")[0].startswith("Quanta, 3 förvärv 2024Q1")
    assert _labels("2024-05-02", "2024Q2") == ["Quanta, 1 förvärv 2024Q2 (cirka 72 MUSD)"]
    assert _labels("2024-08-01", "2024Q2")[0].startswith("Quanta, 2 förvärv 2024Q2")
    assert _labels("2026-07-30", "2026Q3") == ["Quanta, minst 1 förvärv 2026Q3"]
    assert _labels("2026-10-29", "2026Q3")[0].startswith("Quanta, 2 förvärv 2026Q3")
    assert _labels("2026-10-29", "2026Q4") == ["Quanta, minst 1 förvärv 2026Q4"]


def test_the_two_first_stated_considerations():
    dsi = [m[0] for m in ACQ.marks("pwr", "2025-07-31") if "Dynamic" in m[0]]
    assert dsi == ["Quanta–Dynamic Systems (cirka 1 350 MUSD)"]
    later = [m[0] for m in ACQ.marks("pwr", "2025-10-30") if "Dynamic" in m[0]]
    assert later == ["Quanta–Dynamic Systems (1 669 MUSD)"]  # a later filing replaces it (QA1, point 3)
    df = ACQ.load().set_index("id")
    for rid, musd, filed in (("pwr-2024Q3-cei-05", 1500.0, "2024-08-01"), ("pwr-2025Q3-dsi-05", 1350.0, "2025-07-31")):
        r = df.loc[rid]
        assert r["row_type"] == "consideration" and r["consideration_musd"] == musd and r["qualifier"] == "approx"
        assert r["filed"] == filed and r["consideration_scope"] == "deal"


def test_same_day_rows_of_an_event_must_share_the_label(tmp_path):
    p = tmp_path / "acq.csv"
    shutil.copy(ACQ.PATH, p)
    with open(p, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        if r["id"] == "pwr-2026Q2-02":
            r["label"] = "Quanta, 2 förvärv 2026Q2"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ACQ.COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    with pytest.raises(ACQ.CsvError, match="different labels"):
        ACQ.load(p)


def test_lt1_mark_per_2024_reading_days_has_no_hindsight():
    m = L.acquisition_quarters("L1", "2024-03-01")
    assert all("3 förvärv 2024Q1" not in v for v in m.values())
    assert any("2 förvärv 2024Q1" in v for v in m.values())


# ------------------------------------------------------------------ S1 texts


def test_transition_note_no_longer_waits_for_the_owner():
    """X26 made the note say the change waited for the owner; the owner confirmed it (register B18, point 1)."""
    h = {"n_tested": 4, "n_x": 4, "n_tried": 3}
    assert C.transition_note(h).endswith("med den nya: 3 av 4.")
    assert not hasattr(C, "PENDING_OWNER") and "PENDING_OWNER" not in inspect.getsource(L)


def test_el1s_text_points_to_qa1_and_lt1():
    src = inspect.getsource(E)
    assert "inte kontrollerade (R28-7)" not in src
    assert "registret 2026-11-27 QA1" in src and "X26, punkt 6" in src


@pytest.mark.real_data
def test_real_table_geometric_rows_give_r29s_numbers_and_the_same_outcomes():
    from ai_tracker import observations

    t = observations.load()
    r = P.compute(DAY, t)
    ch = {q: round(v, 1) for q, v in C.series_of(r["measures"]["pv1_pris_arena_gq"], "change").items()
          if v is not None}
    assert ch == {"2025Q3": 433.7, "2025Q4": 301.0, "2026Q1": 0.1, "2026Q2": -37.7, "2026Q3": 0.0}
    for g, lk in (("H-G", "H"), ("a-G", "a"), ("b-G", "b")):
        assert r["readings_geo"][g]["outcome"] == r["readings"][lk]["outcome"]
    assert math.isfinite(r["measures"]["pv1_sdk_gq"]["level"])
