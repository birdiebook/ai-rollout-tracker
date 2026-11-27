"""B18: the owner's three decisions after R29 (register 2026-11-27 "B18: ägarbeslut efter R29").

1. S1's count of tried origins is confirmed: the transition note no longer says it waits for the owner (R29-1 closed).
2. PV1's main reading is H-G (the geometric quarterly mean); a-G and b-G are the side readings, H, a and b stay beside
   them as locked rows. The antenna's outcome, facts and main_inputs follow H-G.
3. KL1 decides seen data per reading with X25's mechanism and KL1's register day 2026-11-25: the paragraph on seen
   data in section 4 follows the readings, not the reading day; everything else in sections 1-7 is unchanged.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from ai_tracker import catalog, config
from ai_tracker.followed import common as C
from ai_tracker.followed import kreditlagret as F
from ai_tracker.followed import prisvolym as P
from ai_tracker.series import kreditlagret as S

sys.path.insert(0, str(Path(__file__).parent))
import test_followed_prisvolym as TP  # the synthetic PV1 world
import test_x26_r29 as TX  # the step world (a price step inside a quarter)

REGISTER = config.REPO / "docs" / "mattregister.md"
ENTRY = "### 2026-11-27 – B18: ägarbeslut efter R29"
RESULTS = config.REPO / "docs" / "resultat"
DAY = "2026-11-27"
OLD_PARAGRAPH = "Alla kvartal i den här läsningen var kända före registerposten 2026-11-25"
NEW_PARAGRAPH = "Sedda data avgörs per läsning (registret 2026-11-27 B18, punkt 3)"


def _entry() -> str:
    text = REGISTER.read_text(encoding="utf-8")
    assert ENTRY + "\n" in text
    assert text.index(ENTRY) > text.index("### 2026-11-27 – X26:")
    return text.split(ENTRY + "\n", 1)[1].split("\n### ", 1)[0]


def test_register_entry_is_in_place_and_names_the_three_decisions():
    entry = _entry()
    for want in ("**1. F0:s räkning av prövade ursprung bekräftas (R29-1).**",
                 "**2. PV1:s huvudläsning blir H-G (R29-2).**",
                 "**3. KL1 avgör sedda data per läsning (R29-7).**",
                 "Läsdagar till och med 2026-11-25 är alltid sedda.", "`main_inputs` följer H-G"):
        assert want in entry, want
    assert P.MAIN == "H-G" and P.MAIN_LOCKED == "H" and P.SIDE == ("a-G", "b-G") and P.B18_REGISTERED == DAY
    assert P.LOCKED_OF == {"H-G": "H", "a-G": "a", "b-G": "b"}
    assert F.REGISTERED == "2026-11-25"


# ------------------------------------------------------------------ 1. F0's count confirmed (R29-1 closed)


def test_transition_note_keeps_both_counts_without_the_pending_owner_text():
    note = C.transition_note({"n_tested": 4, "n_x": 4, "n_tried": 3})
    assert "Med F0:s räkning före S1: 4 av 4; med den nya: 3 av 4." in note
    assert "väntar" not in note and "R29-1" not in note


@pytest.mark.parametrize("doc", ["kreditlagret", "ledtid", "betalningsgapet", "elflaskhalsen", "prisvolym"])
def test_generated_reports_no_longer_wait_for_the_owner(doc):
    text = (RESULTS / f"{doc}.md").read_text(encoding="utf-8")
    reports = text.split("\n## ", 1)[1]  # everything after the hand-written header line
    assert "Bytet väntar på ägarens bekräftelse" not in reports
    assert "Övergång (registret 2026-11-27 S1, punkt 3)" in reports


def test_r29_and_claude_md_say_r29_1_is_closed():
    r29 = (config.REPO / "docs" / "granskning" / "r29_korning17.md").read_text(encoding="utf-8")
    finding = r29.split("### R29-1 ", 1)[1].split("\n### ", 1)[0]
    assert "Stängt genom B18" in finding
    claude = (config.REPO / "CLAUDE.md").read_text(encoding="utf-8")
    row = next(x for x in claude.split("\n- **") if x.startswith("Körning 17"))
    assert "väntar på Johannes bekräftelse" not in row


# ------------------------------------------------------------------ 2. PV1: H-G is the main reading


def test_antenna_reports_h_g_and_its_facts():
    r = P.compute(DAY, table=TP.world(-60.0, 30.0))
    row = P.antenna(r)
    hg = r["readings_geo"]["H-G"]
    assert row["outcome"] == hg["outcome"] and row["reading"] == P.short(hg) and row["t"] == hg["t"]
    f = row["facts"]
    assert f["Bisak a-G (Arena-pris mot SDK, geometriskt medel)"] == P.short(r["readings_geo"]["a-G"])
    assert f["Bisak b-G (GPQA-pris mot SDK relativt kontroll, geometriskt medel)"] == P.short(r["readings_geo"]["b-G"])
    x = r["measures"]["pv1_pris_gpqa_gq"]
    assert f["GPQA-pris (geometriskt medel), förändring i takt"] == f"{C.fmt(x['change'], 1, True)} ({x['period']})"
    assert f["Låsta rader H / a / b (aritmetiskt medel)"] == " / ".join(P.short(r["readings"][n]) for n in "Hab")
    assert row["main_inputs"] == {"x": [P.PRICE_GPQA], "y": sorted(P.SDK), "x_stat": "förändring i takt", "sign": -1}
    assert r["params"]["main"] == "H-G" and r["main_seen"] is r["readings_geo"]["H-G"]["seen"]


def test_antenna_follows_h_g_where_h_differs():
    """A price step inside a quarter: the arithmetic mean gives H two impulses up, the geometric mean gives H-G one.
    The antenna counts H-G's."""
    r = P.compute(DAY, table=TX._step_world(3.0))
    h, hg = r["readings"]["H"]["history"], r["readings_geo"]["H-G"]["history"]
    assert (h["impulses_up"], hg["impulses_up"]) == (2, 1)
    assert P.antenna(r)["facts"]["Huvudläsningen, impulser upp/ned"] == f"1/0 av {hg['n_x']} ursprung"


def test_antenna_of_the_mirrored_world_is_the_mirror():
    t = TX._step_world(3.0)
    r, m = P.compute(DAY, table=t), P.compute(DAY, table=TX._mirror(t))
    a, b = r["readings_geo"]["H-G"]["history"], m["readings_geo"]["H-G"]["history"]
    assert (a["impulses_up"], a["impulses_down"]) == (b["impulses_down"], b["impulses_up"])
    assert P.antenna(m)["facts"]["Huvudläsningen, impulser upp/ned"] == f"0/1 av {b['n_x']} ursprung"


def test_report_reads_h_g_first_and_reports_the_locked_rows_beside():
    r = P.compute(DAY, table=TP.world(-60.0, 30.0))
    md = P.render(r)
    s3 = md.split("## 3. Läsregeln", 1)[1].split("\n## 4.", 1)[0]
    s6 = md.split("## 6. Aritmetiskt kvartalsmedel", 1)[1]
    for g, lk in P.LOCKED_OF.items():
        assert P.READING_NAME[g] in s3 and P.READING_NAME[g] not in s6
        assert P.READING_NAME[lk] in s6 and P.READING_NAME[lk] not in s3
    assert "(H-G, huvudläsning)" in s3 and "Samma utslag som H-G." in s6
    assert s3.count("inget utfall på osedda data") >= 1 and "2026-11-27 B18, punkt 2" in md


def test_h_g_reading_after_the_register_day_on_a_new_quarter_is_unseen():
    t = TP.world(-60.0, 30.0)
    late = pd.DataFrame([TP._row(s, "W", TP._week_period(w), v, TP._w_kf(TP._week_period(w)))
                         for s, v in ((P.SDK[0], 6e6), (P.SDK[1], 4e6), *((c, 5e7) for c in P.CONTROL))
                         for w in P.quarter_weeks("2026Q4")])
    after = P.compute("2027-01-10", table=pd.concat([t, late], ignore_index=True))
    assert after["readings_geo"]["H-G"]["t"] == "2026Q4" and after["main_seen"] is False
    assert P.antenna(after)["facts"]["Huvudläsningen på osedda data"] == "ja"


@pytest.mark.real_data
def test_pv1_results_document_reports_h_g_as_the_main_reading():
    doc = (RESULTS / "prisvolym.md").read_text(encoding="utf-8")
    for day in ("2026-11-27", "2025-11-27"):
        part = doc.split(f"## Pris mot volym per {day}", 1)[1].split("\n## Rapporten per ", 1)[0]
        assert "(H-G, huvudläsning):**" in part and "### 6. Aritmetiskt kvartalsmedel" in part
    ant = (RESULTS / "antenner.md").read_text(encoding="utf-8")
    assert "Låsta rader H / a / b (aritmetiskt medel)" in ant


# ------------------------------------------------------------------ 3. KL1: seen data per reading


def _world_with(extra: pd.DataFrame | None = None) -> pd.DataFrame:
    """The synthetic KL1 world (tests.test_kreditlagret), with extra component rows and the kl_ series derived again."""
    from tests.test_kreditlagret import _report_world

    w = _report_world()
    comp = w[~w["series"].str.startswith("kl_")]
    if extra is not None:
        comp = pd.concat([comp, extra], ignore_index=True)
    derived = []
    for s in catalog.ALL:
        if s.key.startswith("kl_") and not s.key.startswith("kl_coupon"):
            d = S.derive(S.formula(*s.key.removeprefix("kl_").rsplit("_", 1)) if s.key != "kl_leases_msft_cond"
                         else S.formula("leases", "msft_cond"), comp)
            if not d.empty:
                derived.append(d.assign(series=s.key, freq="Q", fetched_at=pd.Timestamp("2026-12-12")))
    return pd.concat([comp, *derived], ignore_index=True)


@pytest.fixture(scope="module")
def kl_world():
    return _world_with()


@pytest.fixture(scope="module")
def kl_restated():
    """Oracle restates its 2025Q4 capex on 2026-12-11, after KL1's register day."""
    row = pd.DataFrame([{"series": "capex_orcl", "freq": "Q", "period": "2025Q4", "value": 9000.0,
                         "known_from": pd.Timestamp("2026-12-11"), "source": "release",
                         "fetched_at": pd.Timestamp("2026-12-12")}])
    return _world_with(row)


@pytest.fixture
def no_f1(monkeypatch):
    from ai_tracker.series import guidance_revisions as F1

    monkeypatch.setattr(F1, "load_csv", lambda: None)


def _kl(day, table):
    from tests.test_f0_engine import _csv

    return F.compute(day, table=table, csv=_csv())


def _paragraph(text: str) -> str:
    s4 = text.split("## 4. Läsregeln, mekaniskt", 1)[1].split("\n## 5.", 1)[0]
    lines = [x for x in s4.split("\n") if x.startswith((OLD_PARAGRAPH, NEW_PARAGRAPH))]
    assert len(lines) == 1
    return lines[0]


def test_kl1_up_to_the_register_day_the_paragraph_is_word_for_word_as_before(kl_world, no_f1):
    r = _kl("2026-11-25", kl_world)
    assert all(x["seen"] for x in r["readings"].values()) and r["main_seen"] is True
    assert _paragraph(F.render_locked(r)).startswith(OLD_PARAGRAPH)


def test_kl1_after_the_register_day_without_new_values_every_reading_is_seen(kl_world, no_f1):
    """The day is after the register day, but no value the readings rest on changed: the paragraph says so (before
    B18 it was left out because of the day)."""
    r = _kl("2026-12-20", kl_world)
    assert not r["seen_before_register"] and all(x["seen"] for x in r["readings"].values())
    p = _paragraph(F.render_locked(r))
    assert p.startswith(NEW_PARAGRAPH) and "Alla 5 läsningar nedan" in p and "Osedda" not in p
    assert F.antenna(r)["facts"]["Huvudläsningen på osedda data"] == "nej"


def test_kl1_a_restatement_after_the_register_day_makes_only_the_readings_resting_on_it_unseen(kl_restated, no_f1):
    r = _kl("2026-12-20", kl_restated)
    seen = {e: x["seen"] for e, x in r["readings"].items()}
    assert seen == {"outer": False, "orcl": False, "crwv": True, "nbis": True, "iren": True}
    p = _paragraph(F.render_locked(r))
    assert "Osedda, alltså utfall på osedda data (2 av 5): yttre lagret (huvudläsning), Oracle mot inre lagret." in p
    assert "Sedda, inget utfall på osedda data: CoreWeave mot inre lagret, Nebius mot inre lagret, IREN mot inre " \
           "lagret." in p
    assert F.antenna(r)["facts"]["Huvudläsningen på osedda data"] == "ja"
    # before the restatement is known, the same data are seen
    before = _kl("2026-12-10", kl_restated)
    assert all(x["seen"] for x in before["readings"].values())


def test_kl1_rests_on_everything_rule_c_reads(kl_world, no_f1):
    r = _kl("2026-12-20", kl_world)
    x = r["readings"]["orcl"]
    rests = F.locked_resting_on(x)
    assert ("kl_capex4_orcl", "change", x["t"]) in rests and ("kl_capex4_inner", "change", x["inner_period"]) in rests
    assert {k for k, stat, q in rests if stat == "pace" and q == x["t_minus_2"]} == \
           {f"kl_{m}_orcl" for m in F.measures_of("orcl")}


def test_kl1_only_the_paragraph_differs_from_the_day_based_rule(kl_world, monkeypatch, no_f1):
    """Sections 1-7 apart from the paragraph and every outcome are the same as with the rule before B18 (on a day
    after the register day the paragraph was left out)."""
    r = _kl("2026-12-20", kl_world)
    new = F.render_locked(r).split("\n")
    p = _paragraph("\n".join(new))
    i = new.index(p)
    assert new[i + 1] == ""
    old = new[:i] + new[i + 2:]
    monkeypatch.setattr(F, "seen_paragraph", lambda _r: [])
    assert F.render_locked(r).split("\n") == old


# ------------------------------------------------------------------ KL1 on the real table, against 3edc854


@pytest.fixture(scope="module")
def real():
    from ai_tracker import observations

    t = observations.load()
    if t.empty or "kl_capex4_outer" not in set(t["series"]):
        pytest.skip("no real observation table with the KL1 series")
    return t


def _base_locked(day: str) -> str:
    """The locked part (sections 1-7) of KL1's report per `day` in docs/resultat/kreditlagret.md at 3edc854 (the
    commit before B18), with the headings promoted back."""
    try:
        doc = subprocess.run(["git", "-C", str(config.REPO), "show", "3edc854:docs/resultat/kreditlagret.md"],
                             capture_output=True, text=True, check=True, encoding="utf-8").stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("commit 3edc854 is not available")
    part = doc.split(f"## Kreditlagret per {day}", 1)[1].split("\n### 8. ", 1)[0]
    text = f"## Kreditlagret per {day}" + part
    return "\n".join(x[1:] if x.startswith("##") else x for x in text.split("\n")).strip("\n")


@pytest.mark.real_data
def test_kl1_real_report_2025_11_27_is_byte_identical_to_3edc854(real):
    r = F.compute("2025-11-27", real)
    assert F.render_locked(r).strip("\n") == _base_locked("2025-11-27")


@pytest.mark.real_data
def test_kl1_real_report_2026_11_27_differs_from_3edc854_only_by_the_paragraph(real):
    r = F.compute("2026-11-27", real)
    assert all(x["seen"] for x in r["readings"].values())
    new = F.render_locked(r).strip("\n").split("\n")
    p = _paragraph("\n".join(new))
    assert p.startswith(NEW_PARAGRAPH) and "Alla 5 läsningar nedan" in p
    i = new.index(p)
    assert new[:i] + new[i + 2:] == _base_locked("2026-11-27").split("\n")
