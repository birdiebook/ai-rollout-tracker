"""R11 review of F1, guidance revisions and surprise against guidance (docs/granskning/r11_revideringar.md).

The tests for the confirmed defects (R11-1 to R11-5) were strict xfails; the fix track X8 fixed them and they now
pass as ordinary tests (assertions unchanged).
Passing tests pin properties the review relies on: as_of truncation on the real table, guidance known before the
outcome, and a snapshot whose branch states do not depend on the expectations section. No network.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from ai_tracker import catalog, observations
from ai_tracker.series import guidance_revisions as GR
from ai_tracker.sources import guidance_capex
from ai_tracker.state import expectations as E
from ai_tracker.state import snapshot as S
from tests.conftest import real_table_exists

# microsoft.com, FY2026 Q4 call (2026-07-29), sentence #228 in guidance_capex.sentences: the CY2026 figure on the
# narrower basis after the useful-life update (the text stays out of the repo; SHA-256 as in the curated CSV)
MSFT_JULY_SHA = "d8cfaeea2501c1ee5624a917d9860500ddae5d4a279a838f647d23e5a9bb5a84"
CSV_BASED = ["f1_rev_index_4q", "f1_rev_index_q", "f1_rev_n_4q", "f1_rev_n_q", "f1_rev_median_4q", "f1_rev_median_q",
             "f1_surprise_meta_capex", "f1_surprise_googl_capex", "f1_surprise_index"]


def _csv() -> pd.DataFrame:
    return guidance_capex.load()


def _events(rows: list[tuple[str, int, float]]) -> pd.DataFrame:
    """Revision events (known_from, direction, size) of one synthetic chain."""
    out = []
    for i, (kf, direction, size) in enumerate(rows):
        out.append({c: None for c in GR.EVENT_COLUMNS} | {
            "company": "meta", "measure": "capex", "item": f"meta|capex|CY:2025|X{i}", "chain": "num",
            "period": "CY:2025", "definition": "X", "kind": "range", "known_from": pd.Timestamp(kf), "ref": f"r{i}",
            "size": size, "direction": direction})
    return pd.DataFrame(out, columns=GR.EVENT_COLUMNS)


def _csv_rows(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    """guidance_capex.load()-shaped Meta CY2025 rows (id, filed, midpoint)."""
    d = pd.DataFrame([{"id": i, "company": "meta", "horizon": "CY", "period": "2025", "kind": "approx",
                       "value_lo": v, "value_hi": v, "direction_code": np.nan, "direction_base": "",
                       "definition": "META_CAPEX_INCL_FL", "filed": f} for i, f, v in rows])
    d["known_from"] = pd.to_datetime(d["filed"])
    return d


# ------------------------------------------------------------------ confirmed defects (fixed in X8)


def test_csv_has_microsofts_cy2026_figure_from_the_july_2026_call():
    d = _csv()
    rows = d[(d["company"] == "msft") & (d["horizon"] == "CY") & (d["period"].astype(str) == "2026")
             & (d["known_from"] == pd.Timestamp("2026-07-29"))]
    assert len(rows) == 1
    assert float(rows["value_lo"].iloc[0]) == 175000.0 and rows["sentence_sha256"].iloc[0] == MSFT_JULY_SHA


def test_microsofts_2026_cut_is_a_downward_revision_on_the_same_basis():
    ev = GR.events(GR.statements(None, _csv()))
    m = ev[(ev["company"] == "msft") & (ev["period"] == "CY:2026") & (ev["known_from"] == pd.Timestamp("2026-10-28"))]
    assert len(m) == 1 and int(m["direction"].iloc[0]) == -1
    assert m["size"].iloc[0] == pytest.approx(100 * math.log(170 / 175), abs=0.01)


def test_closing_version_waits_until_the_quarters_last_day_has_passed():
    ev = _events([("2025-02-03", 1, 5.0), ("2025-02-20", 1, 2.0), ("2025-03-10", 0, 0.0)])
    start = pd.Period("2025Q1", "Q-DEC")
    after = GR.revision_index(ev, 4, "2025-07-01", start=start)
    assert (after.loc[after["period"] == "2025Q2", "known_from"] == pd.Timestamp("2025-06-30")).any()
    on_the_day = GR.revision_index(ev, 4, "2025-06-30", start=start)
    assert "2025Q2" not in set(on_the_day["period"])


def test_fetch_recomputes_when_the_curated_csv_changes(monkeypatch):
    table = pd.DataFrame({"series": ["capex_googl"], "freq": ["Q"], "period": ["2024Q4"], "value": [1.0],
                          "known_from": [pd.Timestamp("2025-02-05")], "source": ["release"],
                          "fetched_at": [pd.Timestamp("2026-11-24")]})
    up = _csv_rows([("a", "2025-01-29", 60000.0), ("b", "2025-04-30", 66000.0)])
    down = _csv_rows([("a", "2025-01-29", 60000.0), ("b", "2025-04-30", 54000.0)])
    fetch = GR._fetch("f1_rev_median_q")
    GR._CACHE.clear()
    try:
        monkeypatch.setattr(GR, "load_csv", lambda: up)
        first = fetch(table)
        monkeypatch.setattr(GR, "load_csv", lambda: down)
        second = fetch(table)
    finally:
        GR._CACHE.clear()
    assert len(first) and len(second)
    assert first["value"].iloc[-1] > 0 > second["value"].iloc[-1]


def test_series_from_the_curated_csv_respect_its_publish_gate():
    specs = catalog.by_key()
    gated = sorted(k for k, s in specs.items() if k.startswith("guid_capex_") and not s.publish)
    open_ = [k for k in CSV_BASED if specs[k].publish]
    assert not (gated and open_), f"publish=True {open_} while {len(gated)} guid_capex series are publish=False"


def test_csv_has_metas_2020_outlook_from_the_index_period():
    d = _csv()
    m = d[(d["company"] == "meta") & (d["horizon"] == "CY") & (d["period"].astype(str) == "2020")]
    assert set(m["filed"]) >= {"2020-07-30", "2020-10-29"}
    assert (m["value_lo"] == 16000.0).all()


# ------------------------------------------------------------------ properties that hold


def _real_inputs():
    if not real_table_exists():
        pytest.skip("no real observation table")
    t = observations.load()
    t = t[t["series"].isin(GR.COMPONENTS)].copy()
    need = {"tsmc_revenue_m", "tsmc_guid_rev_usd_lo", "nvda_guid_rev_mid", "rev_nvda", "capex_meta"}
    if not need <= set(t["series"]):
        pytest.skip("F1 components missing from the real table")
    t["known_from"] = pd.to_datetime(t["known_from"])
    return t, _csv()


def _asof(df: pd.DataFrame, when: pd.Timestamp) -> pd.Series:
    d = df[df["known_from"] <= when].sort_values("known_from", kind="stable")
    return d.groupby(d["period"].astype(str))["value"].last()


@pytest.mark.real_data
def test_real_table_as_of_truncation_gives_identical_series():
    """Every F1 series as_of(D) from today's table equals the series computed from what was known on D."""
    t, csv = _real_inputs()
    full = GR.compute(t, csv, "2026-11-24")
    for d in ("2021-06-30", "2023-09-30", "2025-03-31", "2026-07-30", "2026-10-31"):
        when = pd.Timestamp(d)
        # computed the day after `when` (X8): after the R11-2 fix a closing version dated `when` (a quarter's last
        # day) is emitted once the day has passed; everything used is still known on `when`
        cut = GR.compute(t[t["known_from"] <= when], csv[csv["known_from"] <= when], when + pd.Timedelta(days=1))
        for key in GR.KEYS:
            a, b = GR._series(key, full), GR._series(key, cut)
            assert (b["known_from"] <= when).all() if len(b) else True
            pd.testing.assert_series_equal(_asof(a, when), _asof(b, when), check_names=False)


@pytest.mark.real_data
def test_real_table_guidance_is_known_before_the_outcome():
    t, csv = _real_inputs()
    s = GR.surprises(t, csv)
    assert len(s) and (s["guidance_known_from"] < s["outcome_known_from"]).all()
    ok = s[np.isfinite(s["z"].astype(float))]
    assert (ok["n_past"] >= GR.MIN_PAST).all()


def test_snapshot_branch_states_do_not_depend_on_the_expectations_section(tmp_path, monkeypatch):
    """write() = build() plus the separate section: same branches, input table untouched."""
    monkeypatch.setattr(S, "compute", lambda when, ctx: {"G5": {"index": float(len(ctx.table)), "state": "x"}})
    csv = _csv_rows([("a", "2025-01-29", 60000.0), ("b", "2025-04-30", 66000.0), ("c", "2025-07-30", 70000.0)])
    monkeypatch.setattr(GR, "load_csv", lambda: csv)
    table = pd.DataFrame({"series": ["capex_meta"] * 4, "freq": "Q", "period": [f"2025Q{k}" for k in (1, 2, 3, 4)],
                          "value": [1.0, 2.0, 3.0, 4.0],
                          "known_from": pd.to_datetime(["2025-05-01", "2025-07-31", "2025-10-30", "2026-01-29"]),
                          "source": "release", "fetched_at": pd.Timestamp("2026-11-24")})
    before = table.copy()
    p = S.write("2025-12-31", table, tmp_path, today="2026-11-24", regime=False)
    pd.testing.assert_frame_equal(table, before)
    written = json.loads(p.read_text(encoding="utf-8"))
    built = S.build("2025-12-31", table)
    assert written["branches"] == built["branches"]
    assert set(written) - set(built) == {E.SECTION}
    assert written[E.SECTION]["in_diffusion"] is False and "error" not in written[E.SECTION]
