"""W13: the monthly story (site_bundle.story), the rule pre-registered in docs/mattregister.md 2026-11-25."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from ai_tracker import catalog
from ai_tracker.site_bundle import schema as SC
from ai_tracker.site_bundle import story as ST

REPO = Path(__file__).resolve().parents[1]
COMMITTED = REPO / "web-data-fixtures"
REGISTER = REPO / "docs" / "mattregister.md"


def load(path: str) -> dict:
    return json.loads((COMMITTED / path).read_text(encoding="utf-8"))


def story_docs() -> dict[str, dict]:
    return {f"story/{p.name}": json.loads(p.read_text(encoding="utf-8")) for p in sorted((COMMITTED / "story").glob("*.json"))}


# ------------------------------------------------------------------ a small world for the pure rule


def measure(key, p_change=50.0, p_pace=50.0, direction=0, valid=True, method="log", kf="2026-10-14"):
    return {"series": key, "method": method, "freq": "M", "measure_freq": "M", "valid": valid, "latest_period": "2026-09",
            "known_from": kf, "pace": 10.0, "pace_unit": "log x100 per år", "change_in_pace": 1.0,
            "change_percentile": p_change, "pace_percentile": p_pace, "direction": direction, "direction_sign": 1}


def branch(state, index, series=()):
    return {"state": state, "index": index, "n_series": len(series), "n_up": 0, "n_neutral": len(series), "n_down": 0,
            "series_used": list(series), "series_not_counted": []}


def inp(**kw) -> dict:
    base = {"month": "2026-10", "kind": "rekonstruerad", "known": "2026-10-31",
            "branches": {"G1": branch("stabil", 0.5)}, "branch_names": dict(catalog.BRANCHES), "previous": "2026-09",
            "prev_branches": {"G1": branch("stabil", 0.5)}, "recon": [], "prev_recon": [], "outcomes": [],
            "regime": None, "history": {}, "recon_history": {}}
    base.update(kw)
    return base


def sel(i, withheld=()):
    return ST.select(i, lambda k: k not in withheld, lambda k: f"Etikett {k}")


def events(doc):
    return [c for c in doc["cards"] if c["type"] not in ("K0", "K9")]


def outcome(nowcast="n2", period="2026-09", outcome=100.0, kf="2026-10-14", origin="2026-10-05", err=1.0,
            intervals=None):
    return {"nowcast": nowcast, "label": nowcast.upper(), "title": "Mål", "publishable": True, "unit": "mn", "decimals": 0,
            "error_unit": "100 × log", "period": period, "origin": origin, "file": f"forecasts/{nowcast}/{period}.json",
            "slug": period, "champion": "B1", "status": "utfall", "known_from": kf, "forecast": 100.0,
            "outcome": outcome, "err_champion": err,
            "intervals": intervals or {"50": [95.0, 105.0], "80": [90.0, 110.0], "95": [80.0, 120.0]},
            "baseline": None, "guidance": None}


# ------------------------------------------------------------------ the rule


def test_the_rule_is_in_the_register_with_its_thresholds():
    text = REGISTER.read_text(encoding="utf-8")
    i = text.index("### " + ST.ENTRY)
    entry = text[i:]
    for needle in ("≥ 95", "≤ 5", "högst 8 kort", "K4 högst 3, K5 högst 3, K6 högst 2", "K9", "K0"):
        assert needle in entry, needle
    assert ST.CAP == 8 and ST.TYPE_CAPS == {"K4": 3, "K5": 3, "K6": 2} and (ST.LOW, ST.HIGH) == (5.0, 95.0)


def test_k0_first_and_k9_when_nothing_happened():
    doc = sel(inp())
    assert [c["type"] for c in doc["cards"]] == ["K0", "K9"] and doc["n_events"] == 0
    assert all(c["checked"] for c in doc["cards"][1]["facts"]["conditions"])
    first = sel(inp(previous=None, prev_branches=None, prev_recon=None))
    conds = {c["type"]: c["checked"] for c in first["cards"][1]["facts"]["conditions"]}
    assert conds == {"K1": False, "K2": True, "K3": True, "K4": True, "K5": False, "K6": False}
    assert first["previous"] is None


def test_state_changes_in_both_directions_ordered_by_absolute_change_then_code():
    cur = {"G1": branch("accelererar", 0.70), "G2": branch("bromsar in", 0.30), "G3": branch("stabil", 0.5),
           "G4": branch("accelererar", 0.80)}
    prev = {"G1": branch("stabil", 0.60), "G2": branch("stabil", 0.40), "G3": branch("stabil", 0.5),
            "G4": branch("bromsar in", 0.30)}
    doc = sel(inp(branches=cur, prev_branches=prev))
    ev = events(doc)
    assert [c["facts"]["branch"] for c in ev] == ["G4", "G1", "G2"]  # |0.5|, then |0.1| tie by code
    assert [c["direction"] for c in ev] == [1, 1, -1]


def test_the_rule_is_symmetric_under_mirroring():
    """Mirror every input around the neutral point (states, indices, percentiles, regime shift): the same series and
    branches are selected in the same order, only the direction flips."""
    mirror_state = {"accelererar": "bromsar in", "bromsar in": "accelererar", "stabil": "stabil"}
    s = [measure("a", 97.0, direction=1), measure("b", 2.0, direction=-1), measure("c", 60.0)]
    cur = {"G1": branch("accelererar", 0.75, s), "G2": branch("stabil", 0.5)}
    prev = {"G1": branch("stabil", 0.55, [measure("a", 50.0), measure("b", 50.0), measure("c", 50.0)]),
            "G2": branch("bromsar in", 0.2)}
    recon = [measure("x_r", p_pace=99.0)]
    regime = {"blocks": [{"block": "capex", "label": "capex", "shift": "expansion", "p_slow": 0.1}], "breaks": []}
    a = sel(inp(branches=cur, prev_branches=prev, recon=recon, prev_recon=[measure("x_r", p_pace=50.0)], regime=regime))

    def flip(bs):
        out = {}
        for code, b in bs.items():
            b = copy.deepcopy(b)
            b["state"], b["index"] = mirror_state[b["state"]], 1 - b["index"]
            for m in b["series_used"]:
                m["change_percentile"], m["direction"] = 100 - m["change_percentile"], -m["direction"]
            out[code] = b
        return out

    regime_m = {"blocks": [{"block": "capex", "label": "capex", "shift": "inbromsning", "p_slow": 0.9}], "breaks": []}
    b = sel(inp(branches=flip(cur), prev_branches=flip(prev), recon=[measure("x_r", p_pace=1.0)],
                prev_recon=[measure("x_r", p_pace=50.0)], regime=regime_m))
    ida, idb = [c["id"] for c in a["cards"]], [c["id"] for c in b["cards"]]
    assert ida == idb and len(events(a)) == 6
    flip_dir = lambda d: None if d is None else -d
    assert [c["direction"] for c in events(a)] == [flip_dir(c["direction"]) for c in events(b)]


def test_percentile_zone_entry():
    def run(p_now, p_prev, prev_counted=True):
        prev_s = [measure("a", p_prev)] if prev_counted else []
        return events(sel(inp(branches={"G1": branch("stabil", 0.5, [measure("a", p_now)])},
                              prev_branches={"G1": branch("stabil", 0.5, prev_s)})))

    assert len(run(96.0, 50.0)) == 1 and len(run(5.0, 50.0)) == 1 and len(run(95.0, 2.0)) == 1  # inclusive, opposite
    assert run(97.0, 96.0) == [] and run(1.0, 4.0) == []  # same zone last month
    assert run(94.9, 50.0) == [] and run(5.1, 50.0) == []
    assert len(run(99.0, 99.0, prev_counted=False)) == 1  # not counted last month
    assert run(99.0, None) and run(99.0, None)[0]["facts"]["prev_note"] == "saknade percentil förra månaden"
    invalid = events(sel(inp(branches={"G1": branch("stabil", 0.5, [measure("a", 99.0, valid=False)])},
                             prev_branches={"G1": branch("stabil", 0.5)})))
    assert invalid == []


def test_a_zone_card_names_only_its_own_bound():
    """R-W3: "i den nedre zonen (≥ 95 eller ≤ 5)" named the other zone's bound too. Each card names its own."""
    cur = {"G1": branch("stabil", 0.5, [measure("hi", 98.0, direction=1), measure("lo", 2.0, direction=-1)])}
    prev = {"G1": branch("stabil", 0.5, [measure("hi", 50.0), measure("lo", 50.0)])}
    recon = [measure("x_hi", p_pace=99.0), measure("x_lo", p_pace=1.0)]
    prev_recon = [measure("x_hi", p_pace=50.0), measure("x_lo", p_pace=50.0)]
    ev = {c["id"]: c["text"] for c in events(sel(inp(branches=cur, prev_branches=prev, recon=recon,
                                                       prev_recon=prev_recon)))}
    for k in ("k5-hi", "k6-x_hi"):
        assert "i den övre zonen (≥ 95)" in ev[k] and "≤ 5" not in ev[k], ev[k]
    for k in ("k5-lo", "k6-x_lo"):
        assert "i den nedre zonen (≤ 5)" in ev[k] and "≥ 95" not in ev[k], ev[k]


def test_caps_per_type_and_total_and_omitted_counts():
    s = [measure(f"s{i}", 96.0 + i * 0.3 if i % 2 else 4.0 - i * 0.3) for i in range(6)]
    cur = {f"G{i}": branch("accelererar", 0.8, s if i == 1 else ()) for i in range(1, 10)}
    prev = {f"G{i}": branch("stabil", 0.5) for i in range(1, 10)}
    doc = sel(inp(branches=cur, prev_branches=prev))
    ev = events(doc)
    assert len(ev) == 8 and [c["type"] for c in ev] == ["K1"] * 8
    assert doc["qualified"]["K1"] == 9 and doc["omitted"]["K1"] == 1
    assert doc["qualified"]["K5"] == 6 and doc["omitted"]["K5"] == 6  # 3 by the type cap, 3 by the total cap
    few = sel(inp(branches={"G1": branch("stabil", 0.5, s)}, prev_branches={"G1": branch("stabil", 0.5)}))
    k5 = [c for c in events(few) if c["type"] == "K5"]
    assert len(k5) == 3 and few["omitted"]["K5"] == 3
    dist = [abs(c["facts"]["percentile"] - 50) for c in k5]
    assert dist == sorted(dist, reverse=True)


def test_outcomes_in_the_month_ordered_by_interval_then_error():
    rows = [outcome("n1", "2026Q3", 100.0, err=0.5), outcome("n2", "2026-09", 125.0, err=20.0),
            outcome("n3", "2026Q3", 85.0, err=-15.0), outcome("n4", "2026Q3", 85.0, err=-16.0),
            outcome("n5", "2026-08", 200.0, kf="2026-09-30"),  # known last month
            outcome("n6", "2026Q3", 200.0, origin="2026-11-02")]  # origin after the known day
    ev = events(sel(inp(outcomes=rows)))
    assert [c["facts"]["nowcast"] for c in ev] == ["n2", "n4", "n3", "n1"]
    assert [c["facts"]["interval_class"] for c in ev] == [3, 2, 2, 0]
    assert "utanför 95 %-intervallet" in ev[0]["title"] and "inom 50 %-intervallet" in ev[-1]["title"]


def test_withheld_series_are_counted_never_named():
    s = [measure("hidden_key", 99.0), measure("shown", 1.0)]
    regime = {"blocks": [], "breaks": [{"series": "hidden_key", "branch": "G9", "latest_period": "2026-09",
                                        "p_recent": 0.9}]}
    doc = sel(inp(branches={"G1": branch("stabil", 0.5, s)}, prev_branches={"G1": branch("stabil", 0.5)},
                  regime=regime), withheld={"hidden_key"})
    # amendment 2026-11-25 (L3-1): K5 and K6 test only publishable series; K4 still counts a withheld break
    assert doc["withheld"]["K5"] == 0 and doc["withheld"]["K4"] == 1
    assert "hidden_key" not in json.dumps(doc)
    assert [c["facts"]["series"] for c in events(doc)] == ["shown"]


def test_deterministic():
    i = inp(branches={"G1": branch("accelererar", 0.8, [measure("a", 99.0)])},
            prev_branches={"G1": branch("stabil", 0.5)}, outcomes=[outcome()])
    assert json.dumps(sel(i), ensure_ascii=False) == json.dumps(sel(copy.deepcopy(i)), ensure_ascii=False)


# ------------------------------------------------------------------ the committed fixtures


def test_one_story_per_record_month_and_the_index():
    ov = load("overview.json")
    docs = story_docs()
    idx = docs.pop("story/index.json")
    assert [m["month"] for m in idx["months"]] == ov["stripes"]["months"] == [d["month"] for d in docs.values()]
    assert idx["latest"] == ov["record"]["month"]
    for path, d in docs.items():
        assert SC.errors(path, d) == []
        kinds = dict(zip(ov["stripes"]["months"], ov["stripes"]["kind"]))
        assert d["kind"] == kinds[d["month"]]
        assert d["cards"][0]["type"] == "K0" and 1 <= len(d["cards"]) - 1 <= ST.CAP
        assert (d["cards"][1]["type"] == "K9") == (d["n_events"] == 0)
    assert SC.errors("story/index.json", idx) == []


def test_fixture_live_month_has_every_live_card_type():
    d = load("story/2026-10.json")
    # index v2 (K1, merged 2026-11-25): the synthetic G9 has two source families, so it is "för få källor" in both
    # 2026-09 and 2026-10 and has no state change; G6's change (accelererar -> stabil) is the one K1 card
    assert [c["type"] for c in d["cards"]] == ["K0", "K1", "K2", "K3", "K4"]
    assert d["cards"][1]["facts"]["branch"] == "G6"
    assert d["status"] == "live" and d["withheld"]["K4"] == 1  # the withheld break is counted, not named
    k3 = next(c for c in d["cards"] if c["type"] == "K3")
    assert k3["facts"]["baseline"]["variant"] == "B1" and k3["facts"]["guidance"]["variant"] == "B2"
    assert k3["link"] == {"kind": "nowcast", "id": "n2", "slug": "2026-09", "label": k3["link"]["label"]}


def test_nothing_known_after_the_months_known_day():
    known_keys = {"known_from", "known", "origin"}

    def visit(x, day, path):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in known_keys and isinstance(v, str) and re.match(r"\d{4}-\d{2}-\d{2}", v):
                    assert v <= day, f"{path}.{k} = {v} > {day}"
                visit(v, day, f"{path}.{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                visit(v, day, f"{path}[{i}]")

    for path, d in story_docs().items():
        if path.endswith("index.json"):
            continue
        visit(d, d["known"], path)
        for c in d["cards"]:
            if c["track"]:
                assert max(c["track"]["months"]) <= d["month"]


def test_generated_texts_are_neutral():
    assert not ST.neutral("Ett rekord och en kris") and ST.neutral("Takten är högre, G6 accelererar")
    n = 0
    for d in story_docs().values():
        for t in ST.texts(d) if "cards" in d else [m["headline"] for m in d["months"]]:
            assert ST.neutral(t), t
            n += 1
    assert n > 50


def test_no_withheld_key_in_any_story(tmp_path):
    from ai_tracker.site_bundle import synthetic as SY

    text = json.dumps(story_docs(), ensure_ascii=False)
    for k in SY.WITHHELD:
        assert k not in text


@pytest.mark.parametrize("month", ["2026-03"])
def test_a_quiet_fixture_month_exists(month):
    d = load(f"story/{month}.json")
    assert [c["type"] for c in d["cards"]] == ["K0", "K9"]


# ------------------------------------------------------------------ R-W3a-c (register: "Ändring av W13 (R-W3a–c)")


def test_the_amendment_is_in_the_register_after_the_rule():
    text = REGISTER.read_text(encoding="utf-8")
    i = text.index("### " + ST.ENTRY)
    j = text.index("Ändring av W13 (R-W3a–c)")
    assert j > i
    amend = text[j:]
    for needle in ("R-W3a", "R-W3b", "R-W3c", "N/10", "dubblett"):
        assert needle in amend, needle


def test_same_quantity_matches_the_a5_table():
    """SAME_QUANTITY is exactly the A5 rows defined as an existing core series ("befintlig `<key>`")."""
    text = REGISTER.read_text(encoding="utf-8")
    a5 = text[text.index("A5: avstämningar mellan leden"):]
    a5 = a5[:a5.index("\n### ")]
    rows = dict(re.findall(r"^\| `(x_\w+)` \| befintlig `(\w+)` \|", a5, flags=re.M))
    assert rows == ST.SAME_QUANTITY


def dup_world(p_core=98.0, p_recon=99.0, core_shown=True, others=0):
    core = [measure("capex_ocf_hyp4", p_core, direction=1)]
    core += [measure(f"s{i}", 99.5 - i * 0.1, direction=1) for i in range(others)]
    cur = {"G1": branch("stabil", 0.5, core)}
    prev = {"G1": branch("stabil", 0.5, [measure(m["series"], 50.0) for m in core])}
    recon = [measure("x_capex_ocf", p_pace=p_recon), measure("x_other", p_pace=1.0)]
    prev_recon = [measure("x_capex_ocf", p_pace=50.0), measure("x_other", p_pace=50.0)]
    return inp(branches=cur, prev_branches=prev, recon=recon, prev_recon=prev_recon)


def test_r_w3a_a_reconciliation_that_is_a_shown_k5_series_gets_no_card():
    doc = sel(dup_world())
    ids = [c["id"] for c in events(doc)]
    assert "k5-capex_ocf_hyp4" in ids and "k6-x_capex_ocf" not in ids and "k6-x_other" in ids
    assert doc["duplicates"]["K6"] == 1 and doc["omitted"]["K6"] == 0 and doc["qualified"]["K6"] == 2
    k5 = next(c for c in events(doc) if c["id"] == "k5-capex_ocf_hyp4")
    assert "Samma storhet är avstämningen Etikett x_capex_ocf" in k5["text"]
    assert k5["facts"]["same_quantity"] == {"series": "x_capex_ocf", "label": "Etikett x_capex_ocf",
                                            "percentile": 99.0, "zone": "övre"}
    # no direction is read: the mirrored world drops the same card
    mirrored = sel(dup_world(p_core=2.0, p_recon=1.0))
    assert [c["id"] for c in events(mirrored)] == ids and mirrored["duplicates"]["K6"] == 1


def test_r_w3a_the_reconciliation_stays_when_the_core_card_is_not_shown():
    # the core series is struck by K5's cap (three series further from 50 come first)
    doc = sel(dup_world(p_core=96.0, others=3))
    ids = [c["id"] for c in events(doc)]
    assert "k5-capex_ocf_hyp4" not in ids and "k6-x_capex_ocf" in ids and doc["duplicates"]["K6"] == 0
    # the core series is not in a zone: no K5 card, the K6 card stays
    doc = sel(dup_world(p_core=60.0))
    assert "k6-x_capex_ocf" in [c["id"] for c in events(doc)] and doc["duplicates"]["K6"] == 0


def test_r_w3b_chance_level():
    doc = sel(dup_world(others=3))
    assert doc["chance"]["K5"] == {"n": 4, "expected": 0.4, "met": 4}
    assert doc["chance"]["K6"] == {"n": 2, "expected": 0.2, "met": 2}
    withheld = sel(dup_world(others=3), withheld=("s0",))
    # amendment 2026-11-25 (L3-1): a withheld series is not tested, so it is in neither n nor met
    assert withheld["chance"]["K5"] == {"n": 3, "expected": 0.3, "met": 3}
    assert sel(inp(previous=None, prev_branches=None, prev_recon=None))["chance"] is None


def test_r_w3c_struck_cards_are_listed_with_name_and_direction_in_the_rules_order():
    s = [measure(f"s{i}", 96.0 + i * 0.5 if i % 2 else 4.0 - i * 0.5, direction=1 if i % 2 else -1) for i in range(6)]
    doc = sel(inp(branches={"G1": branch("stabil", 0.5, s)}, prev_branches={"G1": branch("stabil", 0.5)}))
    shown = [c["id"] for c in events(doc)]
    struck = doc["omitted_cards"]
    assert len(struck) == doc["omitted"]["K5"] == 3
    assert {c["id"] for c in struck}.isdisjoint(shown)
    assert all(c["type"] == "K5" and c["label"].endswith("(G1)") and c["direction"] in (1, -1) for c in struck)
    dist = {c["facts"]["series"]: abs(c["facts"]["percentile"] - 50) for c in events(doc)}
    assert min(dist.values()) >= max(abs((96.0 + i * 0.5 if i % 2 else 4.0 - i * 0.5) - 50)
                                     for i in range(6) if f"k5-s{i}" in {c["id"] for c in struck})
    # the total cap: K5 cards struck after K1 filled the cap are listed too, after the struck K1 card
    cur = {f"G{i}": branch("accelererar", 0.8, s if i == 1 else ()) for i in range(1, 10)}
    prev = {f"G{i}": branch("stabil", 0.5) for i in range(1, 10)}
    doc = sel(inp(branches=cur, prev_branches=prev))
    types = [c["type"] for c in doc["omitted_cards"]]
    assert types == ["K1"] + ["K5"] * 6 and sum(doc["omitted"].values()) == len(types)
    assert doc["omitted_cards"][0]["label"] == f"G9 {catalog.BRANCHES['G9']}"


def test_no_internal_codes_in_reader_texts():
    regime = {"blocks": [{"block": "capex", "label": "capex", "shift": "expansion", "p_slow": 0.1}],
              "breaks": [{"series": "s", "branch": "G1", "latest_period": "2026-09", "p_recent": 0.9}]}
    doc = sel(dup_world(p_core=60.0) | {"regime": regime})
    for t in ST.texts(doc):
        assert not re.search(r"\((A5|G-D, C4|BOCPD, G-D)\)|\bC4\b|\bG-D\b", t), t
    k5 = sel(dup_world())
    first = next(c for c in events(k5) if c["type"] == "K5")["text"]
    assert first.startswith("Förändringen i takt är högre än i 98 % av seriens egen historik.")
    low = next(c for c in events(sel(dup_world(p_core=1.6))) if c["type"] == "K5")["text"]
    assert low.startswith("Förändringen i takt är lägre än i 98 % av seriens egen historik.")
