"""PV1 "Pris mot volym" (register 2026-11-27 "PV1"). Synthetic data only, except the last tests (real table).

- the locked parameters equal the register entry, which is unchanged since it was committed
- the reading rule both ways: price falling faster then usage accelerating, falling slower then braking (talar för),
  and the opposite (talar emot); mirrored worlds are counted alike
- months and weeks to quarters: the mean of the three months, weeks by their Thursday, only whole quarters
- the as-of boundary: a row known after the day changes nothing
- missing data: a missing month or week gives no quarter, a missing package gives no sum, missing series are undecided
- seen data per reading (X25, point 1) with PV1's register day
- discovery, antenna (main_inputs, R28-4) and render
"""

from __future__ import annotations

import hashlib
import math

import pandas as pd
import pytest

from ai_tracker import config, followed
from ai_tracker.followed import antenner as AN
from ai_tracker.followed import common as C
from ai_tracker.followed import prisvolym as P

QS = [str(q) for q in pd.period_range("2023Q1", "2026Q3", freq="Q-DEC")]
DAY = "2026-11-27"
REGISTER = config.REPO / "docs" / "mattregister.md"
ENTRY = "### 2026-11-27 – PV1: följd fråga om pris mot volym (prisfall vid fast förmåga mot användningens takt)"


def _months(q: str) -> list[str]:
    p = pd.Period(q, freq="Q-DEC")
    return [str(m) for m in pd.period_range(p.asfreq("M", "start"), p.asfreq("M", "end"), freq="M")]


def _week_period(monday: pd.Timestamp) -> str:
    return f"{monday.date()}/{(monday + pd.Timedelta(days=6)).date()}"


def _m_kf(m: str) -> pd.Timestamp:
    return pd.Period(m, freq="M").end_time.normalize() + pd.Timedelta(days=1)


def _w_kf(period: str) -> pd.Timestamp:
    return pd.Timestamp(period.split("/")[1]) + pd.Timedelta(days=2)


def _row(series, freq, period, value, kf, source="release"):
    return {"series": series, "freq": freq, "period": period, "value": float(value), "known_from": kf,
            "source": source, "fetched_at": pd.Timestamp("2026-11-27")}


def _path(incs: dict[str, float], base: float, start: float) -> dict[str, float]:
    """Quarterly levels: log x100 increments `base` per quarter, plus incs[q] in quarter q."""
    y, out = 100.0 * math.log(start), {}
    for q in QS:
        y += base + incs.get(q, 0.0)
        out[q] = math.exp(y / 100.0)
    return out


def monthly(series: str, levels: dict[str, float]) -> list[dict]:
    """Every month of a quarter at the quarter's level, known the day after month end."""
    return [_row(series, "M", m, v, _m_kf(m)) for q, v in levels.items() for m in _months(q)]


def weekly(series: str, levels: dict[str, float]) -> list[dict]:
    """Every week of a quarter (by its Thursday) at the quarter's level, known Sunday + 2 days."""
    out = []
    for q, v in levels.items():
        for w in P.quarter_weeks(q):
            per = _week_period(w)
            out.append(_row(series, "W", per, v, _w_kf(per), "backfill"))
    return out


def world(x_jump: float = 0.0, y_inc: float = 0.0, arena_jump: float | None = None) -> pd.DataFrame:
    """A synthetic table. Prices fall 25 log points a quarter (pace -100, change 0), with an extra `x_jump` in 2026Q2
    (change in pace +x_jump at 2026Q2 and 2026Q3). SDK downloads grow 10 a quarter (pace 40, change 0), with an extra
    `y_inc` in 2026Q3 (change in pace y_inc at 2026Q3). The control packages are flat."""
    aj = x_jump if arena_jump is None else arena_jump
    rows = []
    rows += monthly(P.PRICE_GPQA, _path({"2026Q2": x_jump}, -25.0, 10.0))
    rows += monthly(P.PRICE_ARENA, _path({"2026Q2": aj}, -25.0, 20.0))
    sdk = _path({"2026Q3": y_inc}, 10.0, 1e6)
    rows += weekly(P.SDK[0], {q: 0.6 * v for q, v in sdk.items()})
    rows += weekly(P.SDK[1], {q: 0.4 * v for q, v in sdk.items()})
    for s in P.CONTROL:
        rows += weekly(s, {q: 5e7 for q in QS})
    return pd.DataFrame(rows)


def _main(r: dict) -> dict:
    return P.reading(r, P.MAIN)  # H-G since register B18, point 2


# ------------------------------------------------------------------ register


def test_register_entry_is_locked_and_matches_the_module():
    text = REGISTER.read_text(encoding="utf-8")
    assert ENTRY in text
    entry = text.split(ENTRY, 1)[1].split("\n### ", 1)[0]
    assert hashlib.sha256(entry.encode("utf-8")).hexdigest() == LOCKED_SHA256
    for want in ("| H, huvudläsning | `pv1_pris_gpqa_q` | `pv1_sdk_q` | 50 | 20 | 2 | −1 |",
                 "| a, bisak | `pv1_pris_arena_q` | `pv1_sdk_q` | 50 | 20 | 2 | −1 |",
                 "| b, bisak | `pv1_pris_gpqa_q` | `pv1_sdk_rel_q` | 50 | 20 | 2 | −1 |",
                 "X:s **förändring i takt** mot Y:s förändring i takt"):
        assert want in entry, want
    assert P.G == 50.0 and P.H == 20.0 and P.K == 2 and P.SIGN == -1 and P.X_STAT == "change"
    assert P.READINGS == {"H": ("pv1_pris_gpqa_q", "pv1_sdk_q"), "a": ("pv1_pris_arena_q", "pv1_sdk_q"),
                          "b": ("pv1_pris_gpqa_q", "pv1_sdk_rel_q")}
    assert P.MAIN_LOCKED == "H" and P.REGISTERED == "2026-11-27"  # the main reading is H-G since B18, point 2
    assert P.SDK == ("g3_npm_openai_w", "g3_npm_anthropic_sdk_w")
    assert P.CONTROL == ("g3_npm_react_w", "g3_npm_express_w")


LOCKED_SHA256 = "64a43d6ffb4f4482b49a5d00df164d2cd9ef79da6cda3fd2fbb0483aa1a495de"  # the entry as committed in 6ed50e2


# ------------------------------------------------------------------ the reading both ways


@pytest.mark.parametrize("x_jump,y_inc,want,direction", [
    (-60.0, 30.0, C.FOR, -1),      # price fell faster, then usage accelerated: talar för, nedåt
    (60.0, -30.0, C.FOR, 1),       # price fell slower, then usage braked: talar för, uppåt
    (-60.0, -30.0, C.AGAINST, -1),  # price fell faster, usage braked: talar emot, nedåt
    (60.0, 30.0, C.AGAINST, 1),    # price fell slower, usage accelerated: talar emot, uppåt
    (-30.0, 30.0, C.NEITHER, 0),   # |change| < g: no impulse
    (-60.0, 10.0, C.UNDECIDED, -1),  # Y within ±h at t, the window is open at q + 2
])
def test_main_reading_both_ways(x_jump, y_inc, want, direction):
    r = P.compute(DAY, table=world(x_jump, y_inc))
    m = _main(r)
    assert m["t"] == "2026Q3" and m["outcome"] == want, m
    o = next((x for x in m["origins"] if x["origin"] == m["origin"]), None)
    if direction:
        assert o["origin"] == "2026Q2" and o["direction"] == direction and o["expected"] == -direction
    if want == C.UNDECIDED:
        assert "fönstret öppet" in m["reason"]
    x = r["measures"]["pv1_pris_gpqa_q"]
    assert x["period"] == "2026Q3" and x["pace"] == pytest.approx(-100.0 + x_jump)
    assert x["path"]["2026Q2"]["change"] == pytest.approx(x_jump)
    y = r["measures"]["pv1_sdk_q"]
    assert y["change"] == pytest.approx(y_inc)
    # the control is flat: the ratio moves exactly as the SDK sum, so side reading b equals the main reading
    assert r["measures"]["pv1_sdk_rel_q"]["change"] == pytest.approx(y_inc)
    assert r["readings"]["b"]["outcome"] == want
    text = P.short(m)
    assert text.startswith(C.OUTCOME_TEXT[want])
    if want in (C.FOR, C.AGAINST):
        assert text.endswith("uppåt" if direction > 0 else "nedåt")


def test_mirrored_worlds_are_counted_alike():
    down = _main(P.compute(DAY, table=world(-60.0, 30.0)))
    up = _main(P.compute(DAY, table=world(60.0, -30.0)))
    assert (down["history"]["impulses_up"], down["history"]["impulses_down"]) == (0, 1)  # origin 2026Q2 before t
    assert (up["history"]["impulses_up"], up["history"]["impulses_down"]) == (1, 0)
    assert down["history"]["by_direction"]["down"][C.FOR] == up["history"]["by_direction"]["up"][C.FOR] == 1
    assert [d["outcome"] for d in down["decided"]] == [d["outcome"] for d in up["decided"]] == [C.FOR]


def test_side_reading_a_reads_the_arena_price_on_its_own():
    r = P.compute(DAY, table=world(-60.0, 30.0, arena_jump=60.0))
    assert _main(r)["outcome"] == C.FOR and r["readings"]["a"]["outcome"] == C.AGAINST


def test_a_steady_decline_is_no_impulse():
    """Prices that fall at a constant rate have change in pace 0: the rule reads a faster or slower fall, not a fall."""
    r = P.compute(DAY, table=world())
    assert all(rr["outcome"] == C.NEITHER for rr in r["readings"].values())
    assert r["measures"]["pv1_pris_gpqa_q"]["pace"] == pytest.approx(-100.0)


# ------------------------------------------------------------------ months and weeks to quarters


def test_weeks_belong_to_the_quarter_of_their_thursday():
    assert P.week_quarter("2026-12-28/2027-01-03") == "2026Q4"  # Thursday 2026-12-31
    assert P.week_quarter("2026-09-28/2026-10-04") == "2026Q4"  # Thursday 2026-10-01
    assert P.week_quarter("2026-09-21/2026-09-27") == "2026Q3"
    weeks = P.quarter_weeks("2026Q4")
    assert weeks[0] == pd.Timestamp("2026-09-28") and weeks[-1] == pd.Timestamp("2026-12-28") and len(weeks) == 14
    for q in QS:  # every week in exactly one quarter
        assert all(P.week_quarter(_week_period(w)) == q for w in P.quarter_weeks(q))
    assert len(P.quarter_weeks("2026Q3")) == 13


def test_quarter_means_are_dated_by_the_latest_month_and_week():
    t = world()
    t.loc[(t["series"] == P.PRICE_GPQA) & (t["period"] == "2026-08"), "value"] *= 4.0
    r = P.compute(DAY, table=t)
    x = r["measures"]["pv1_pris_gpqa_q"]
    lv = [t[(t["series"] == P.PRICE_GPQA) & (t["period"] == m)]["value"].iloc[0] for m in _months("2026Q3")]
    assert x["level"] == pytest.approx(sum(lv) / 3) and x["known_from"] == "2026-10-01"
    y = r["measures"]["pv1_sdk_q"]
    assert y["known_from"] == "2026-09-29"  # the week 2026-09-21–27, Sunday + 2


def test_a_missing_month_gives_no_quarter():
    t = world()
    t = t[~((t["series"] == P.PRICE_GPQA) & (t["period"] == "2026-08"))]
    m = P.compute(DAY, table=t)["measures"]["pv1_pris_gpqa_q"]
    assert m["period"] == "2026Q2" and "2026Q3" not in {q for q, v in m["path"].items() if v["level"] is not None}
    assert m["missing_next"] == {"period": "2026Q3", "months": {P.PRICE_GPQA: ["2026-08"]}}


def test_a_missing_week_or_package_gives_no_quarter():
    t = world()
    gone = _week_period(P.quarter_weeks("2026Q3")[5])
    t1 = t[~((t["series"] == P.SDK[1]) & (t["period"] == gone))]  # one package lacks one week
    r = P.compute(DAY, table=t1)
    y = r["measures"]["pv1_sdk_q"]
    assert y["period"] == "2026Q2" and y["missing_next"] == {"period": "2026Q3", "weeks": {P.SDK[1]: 1}}
    assert r["measures"][P.SDK[0]]["period"] == "2026Q3"  # openai alone is whole
    assert _main(r)["t"] == "2026Q2"


def test_missing_series_are_undecided_and_render():
    t = world()
    t = t[~t["series"].isin([P.PRICE_GPQA, *P.CONTROL])]
    r = P.compute(DAY, table=t)
    assert _main(r)["outcome"] == C.UNDECIDED and r["readings"]["b"]["t"] is None
    assert r["measures"]["pv1_sdk_rel_q"]["available"] is False
    text = P.render(r)
    assert "Regeln kunde inte prövas" in text and "kan inte avgöras" in text
    assert set(P.antenna(r)) == set(C.ANTENNA_KEYS)


def test_empty_table():
    r = P.compute(DAY, table=world().iloc[0:0])
    assert all(rr["outcome"] == C.UNDECIDED for rr in r["readings"].values())
    P.render(r)
    row = P.antenna(r)
    assert row["next_unseen_date"] == "2027-01-05" and row["t"] is None


# ------------------------------------------------------------------ the as-of boundary


def test_a_row_known_after_the_day_changes_nothing():
    base = world(-60.0, 30.0)
    day = pd.Timestamp(DAY)
    late = pd.DataFrame([
        _row(P.PRICE_GPQA, "M", "2026-09", 1e6, day + pd.Timedelta(days=1)),  # a later vintage
        *[_row(P.PRICE_GPQA, "M", m, 1e-6, day + pd.Timedelta(days=2)) for m in ("2026-10", "2026-11", "2026-12")],
        *[_row(s, "W", _week_period(w), 1e12, day + pd.Timedelta(days=3))
          for s in (*P.SDK, *P.CONTROL) for w in P.quarter_weeks("2026Q4")],  # a whole later quarter
    ])
    a = P.compute(DAY, table=base)
    b = P.compute(DAY, table=pd.concat([base, late], ignore_index=True))
    a.pop("generated"), b.pop("generated")
    assert a == b
    assert P.render(a) == P.render(b)
    assert _main(a)["outcome"] == C.FOR


def test_the_day_before_the_last_week_is_known_reads_the_quarter_before():
    t = world(-60.0, 30.0)
    r = P.compute("2026-09-28", table=t)  # the week 2026-09-21–27 is known 2026-09-29
    assert r["measures"]["pv1_sdk_q"]["period"] == "2026Q2" and _main(r)["t"] == "2026Q2"


# ------------------------------------------------------------------ seen data per reading (X25, point 1)


def test_readings_after_the_register_day_on_new_quarters_are_unseen():
    t = world(-60.0, 30.0)
    late = pd.DataFrame([_row(s, "W", _week_period(w), v, _w_kf(_week_period(w)))
                         for s, v in ((P.SDK[0], 6e6), (P.SDK[1], 4e6), *((c, 5e7) for c in P.CONTROL))
                         for w in P.quarter_weeks("2026Q4")])
    t2 = pd.concat([t, late], ignore_index=True)
    on = P.compute(DAY, table=t2)
    assert on["seen_before_register"] and on["main_seen"]
    after = P.compute("2027-01-10", table=t2)
    assert _main(after)["t"] == "2026Q4" and after["main_seen"] is False
    assert P.antenna(after)["facts"]["Huvudläsningen på osedda data"] == "ja"
    assert "osedda data" in P.render(after)


# ------------------------------------------------------------------ discovery, antenna, render


def test_found_as_a_question_and_in_antenner():
    assert followed.questions()["prisvolym"] is P
    a = AN.compute(DAY, table=world(-60.0, 30.0), modules={"prisvolym": P})
    row = a["rows"][0]
    assert not row.get("error") and row["outcome"] == C.FOR and row["t"] == "2026Q3"


def test_antenna_declares_the_main_inputs():
    r = P.compute(DAY, table=world(-60.0, 30.0))
    row = P.antenna(r)
    assert row["main_inputs"] == {"x": [P.PRICE_GPQA], "y": sorted(P.SDK), "x_stat": "förändring i takt",
                                  "sign": -1}
    assert row["reading"] == "talar för mekanismen, nedåt" and len(row["facts"]) == 7  # + the locked rows (B18)
    assert row["next_unseen_date"] == "2027-01-05" and row["next_unseen"].startswith("npm-kvartalet 2026Q4")


def test_render_has_every_reading_and_no_alarm_words():
    r = P.compute(DAY, table=world(-60.0, 30.0))
    text = P.render(r)
    assert text.startswith("# Pris mot volym per 2026-11-27")
    for name in (*P.READINGS_G, *P.READINGS):
        assert P.READING_NAME[name] in text
    assert "(H-G, huvudläsning):** talar för mekanismen, nedåt" in text
    assert "inget utfall på osedda data" in text and "Ändras sambandet?" in text
    low = text.lower()
    for word in ("larm", "varning", "bubbla", "kris"):
        assert word not in low


def test_licence_classes_take_the_most_restrictive_input():
    cl = P.classes(P.used_series())
    assert cl["pv1_pris_gpqa_q"] == "ja" and cl["pv1_pris_arena_q"] == "okänd"
    assert cl["pv1_sdk_q"] == "okänd" and cl["pv1_sdk_rel_q"] == "okänd"
    assert not any(k.startswith("g3_cf_") for k in P.used_series())  # Cloudflare (class nej) is not read


# ------------------------------------------------------------------ the real table (shared base + track view)

RESULTS = config.REPO / "docs" / "resultat" / "prisvolym.md"


def _demote(text: str) -> str:
    return "\n".join(("#" + x) if x.startswith("#") else x for x in text.split("\n"))


@pytest.fixture(scope="module")
def real():
    from ai_tracker import observations

    t = observations.load()
    if t.empty or P.PRICE_GPQA not in set(t["series"]) or P.SDK[0] not in set(t["series"]):
        pytest.skip("no real observation table with the PV1 series")
    return t


@pytest.mark.real_data
@pytest.mark.parametrize("day,main,side_a", [("2026-11-27", C.UNDECIDED, C.NEITHER),
                                             ("2025-11-27", C.UNDECIDED, C.UNDECIDED)])
def test_results_document_is_the_command_output(real, day, main, side_a):
    r = P.compute(day, table=real)
    assert _main(r)["outcome"] == main and r["readings"]["a"]["outcome"] == side_a
    assert _demote(P.render(r)).strip("\n") in RESULTS.read_text(encoding="utf-8")


def test_results_say_the_readings_are_on_seen_data():
    res = RESULTS.read_text(encoding="utf-8")
    assert "Läsningarna är gjorda på sedda data" in res and "Vad som skiljer de två dagarna" in res
