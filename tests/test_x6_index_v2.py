"""Fix track X6 after review R9 (docs/granskning/r9_index_v2.md): the fixes beyond R9's own strict xfail tests."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from ai_tracker import http, letter as L, pipeline, quarterly as Q
from ai_tracker.site import data as D
from ai_tracker.site import render as RE
from ai_tracker.sources import census_btos
from ai_tracker.state import branch as B
from ai_tracker.state import register as R
from ai_tracker.state.measures import Context
from ai_tracker import observations


# ------------------------------------------------------------------ R9-N1: v2 is decided exactly


def test_exact_index_is_compared_with_the_registered_decimal_thresholds():
    assert B.state_v2(Fraction(67, 100), 3) == R.STATE_ACCEL
    assert B.state_v2(Fraction(33, 100), 3) == R.STATE_BRAKE
    assert B.state_v2(Fraction(2, 3), 3) == R.STATE_STABLE and B.state_v2(Fraction(1, 3), 3) == R.STATE_STABLE
    assert B.state_v2(Fraction(67, 100) - Fraction(1, 10**9), 3) == R.STATE_STABLE
    assert B.state_v2(Fraction(1), 2) == R.STATE_FEW_FAMILIES
    # a float index keeps the float comparison (v1, and callers that pass floats): 0.67 and 0.33 are at the limits
    assert B.state_of(0.67, 3) == R.STATE_ACCEL and B.state_of(0.33, 3) == R.STATE_BRAKE


def test_exact_index_and_votes_at_the_braking_threshold():
    fams = {"A": [-1], "B": [-1], "C": [1] * 49 + [0]}  # votes 0, 0, 99/100 -> index exactly 33/100
    x = B.diffusion_v2_exact(fams)
    assert x == Fraction(33, 100) and B.state_v2(x, 3) == R.STATE_BRAKE
    assert B.diffusion_v2(fams) == float(x) == 0.33
    assert B.vote([1, 0, -1]) == 0.5 and B.vote_exact([1, 1, 0]) == Fraction(5, 6) and B.vote([]) is None
    assert B.diffusion_v2_exact({"A": []}) is None and B.diffusion_v2({}) is None


# ------------------------------------------------------------------ R9-S2: the BTOS schedule is part of the context


def _schedule(path: Path) -> Path:
    pd.DataFrame({"smpdt": [202621], "col_end": [pd.Timestamp("2026-10-18")], "published": [pd.Timestamp("2026-10-22")],
                  "fetched_at": [pd.Timestamp("2026-10-01")]}).to_parquet(path, index=False)
    return path


def test_unit_tests_do_not_see_the_raw_cache_schedule():
    assert Context(observations._empty()).btos_schedule is None  # default: the schedule the fetch logged
    assert http.RAW_DIR not in census_btos.SCHEDULE_LOG.parents and not census_btos.SCHEDULE_LOG.exists()


def test_due_for_and_next_origin_follow_the_given_schedule(tmp_path):
    log = _schedule(tmp_path / "schedule_log.parquet")
    assert pipeline.due_for("n5", "2026-10-21", log) == pipeline.Due("n5", pd.Timestamp("2026-10-21"), "2026-10-18")
    assert pipeline.due_for("n5", "2026-10-21") is None  # the (isolated, absent) default log
    assert pipeline.due_for("n5", "2026-10-21", tmp_path / "absent.parquet") is None
    assert D.next_origin("n5", "2026-10-15", tmp_path / "fc", schedule_file=log) == ("2026-10-21", "2026-10-18")
    assert D.next_origin("n5", "2026-10-15", tmp_path / "fc") is None
    assert L._next_origin("n5", pd.Timestamp("2026-10-15"), schedule_file=log) == ("2026-10-21", "2026-10-18")


def test_the_letters_cut_context_keeps_the_schedule(tmp_path):
    ctx = Context(observations._empty(), btos_schedule=tmp_path / "s.parquet")
    assert L.cut_context(ctx, pd.Timestamp("2026-10-31"), None).btos_schedule == tmp_path / "s.parquet"


# ------------------------------------------------------------------ R9-N5: no v1 line between two "för få"


def test_no_v1_line_when_neither_rule_gives_a_state():
    few = {"rule_version": "v2", "state": R.STATE_FEW_FAMILIES, "v1": {"state": R.STATE_FEW, "index": 1.0}}
    assert L.v1_note(few) == ""
    assert RE.v1_text({"rule_version": "v2", "state": R.STATE_FEW_FAMILIES, "state_v1": R.STATE_FEW,
                       "index_v1": 1.0}) == ""
    other = {"rule_version": "v2", "state": R.STATE_FEW_FAMILIES, "v1": {"state": R.STATE_STABLE, "index": 0.5}}
    assert L.v1_note(other).startswith("Med regel v1, en röst per serie, är tillståndet stabil")
    assert "Med regel v1" in RE.v1_text({"rule_version": "v2", "state": R.STATE_STABLE, "state_v1": R.STATE_FEW,
                                         "index_v1": None})


def test_family_votes_when_every_voting_family_is_hidden(monkeypatch):
    monkeypatch.setattr(L, "publishable", lambda key, inp: not key.startswith("w_"))
    b = {"families": [{"family": "w", "series": ["w_a", "w_b"], "vote": 0.75},
                      {"family": "w_c", "series": ["w_c"], "vote": 1.0}]}
    text = L.family_votes_text(b, None)
    assert text == "2 källor med serier som inte visas av licensskäl räknas utan att namnges."
    b["families"].append({"family": "pub", "series": ["p"], "vote": 0.5})
    text = L.family_votes_text(b, None)
    assert text.startswith("Röst per källa, medel av (riktning + 1)/2: `pub` 0,50 (1 serie); 2 källor med serier")
    assert "–" not in text


# ------------------------------------------------------------------ R9-N6 and N7: footers


V2_RULES = {"index_rule": "v2", "min_families": 3, "accelerating_at_least": 0.67, "braking_at_most": 0.33}


def test_quarterly_footer_uses_sources_under_v2_and_says_unrounded():
    v2 = "\n".join(Q.footer(SimpleNamespace(months=[SimpleNamespace(doc={"rules": V2_RULES})])))
    assert "Grenar med tre till fem källor flyttas mycket av en enda källa" in v2
    assert "Indexet jämförs oavrundat, så ett index som visas som 0,67 kan vara 2/3 och då stabilt." in v2
    v1 = "\n".join(Q.footer(SimpleNamespace(months=[SimpleNamespace(doc={"rules": {}})])))
    assert "Grenar med tre till fem serier flyttas mycket av en enda serie" in v1 and "oavrundat" not in v1


def test_letter_footer_says_the_index_is_compared_unrounded():
    text = "\n".join(L.footer(SimpleNamespace(current={"rules": V2_RULES})))
    assert "Indexet jämförs oavrundat, så ett index som visas som 0,67 kan vara 2/3 och då stabilt." in text


@pytest.mark.parametrize("key", ["asml_net_sales", "asml_net_bookings"])
def test_asml_licence_names_asml_and_tsmc_keeps_its_text(key):
    from ai_tracker import catalog

    specs = catalog.by_key()
    assert "Statutory filing by ASML;" in specs[key].license and "TSMC" not in specs[key].license
    assert specs["tsmc_revenue_m"].license.endswith("Statutory filing by TSMC; only extracted figures with source "
                                                    "citation are published. TSMC IR terms not readable (403)")
