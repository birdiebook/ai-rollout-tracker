"""Review R9 (docs/granskning/r9_index_v2.md): independent, adversarial tests of diffusion index v2 (track K1).

Passing tests pin edge cases that hold. A strict xfail marks every confirmed defect: it fails while the defect is
there and turns into a failure (XPASS) when it is fixed, so the fix track removes the marker.
"""

from __future__ import annotations

import io
import json
import re
from contextlib import redirect_stdout
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import test_letter as TL
import test_site as TS
from ai_tracker import catalog, config, letter as L, observations
from ai_tracker.site_bundle import export as E
from ai_tracker.site_bundle import gate as G
from ai_tracker.site_bundle import synthetic as SY
from ai_tracker.sources import census_btos
from ai_tracker.state import __main__ as CLI
from ai_tracker.state import branch as B
from ai_tracker.state import measures as M
from ai_tracker.state import register as R
from ai_tracker.state import snapshot as S

REAL = catalog.by_key()
WHEN = "2026-10-31"
FETCHED = pd.Timestamp("2026-11-20")


# ------------------------------------------------------------------ helpers


def real_rows(key: str, end: str, seed: int, start: str = "2010-01", accel: float = 0.0) -> pd.DataFrame:
    """Monthly rows for a real catalog key, known_from = period end + the catalog's lag_days."""
    spec = REAL[key]
    periods = pd.period_range(start, end, freq="M")
    rng = np.random.default_rng(seed)
    g = 0.01 + 0.004 * rng.standard_normal(len(periods))
    g[-6:] += accel
    known = pd.DatetimeIndex(periods.end_time.normalize()) + pd.Timedelta(days=max(spec.lag_days, 1))
    return pd.DataFrame({"series": key, "freq": "M", "period": [str(p) for p in periods],
                         "value": 100 * np.exp(np.cumsum(g)), "known_from": known, "source": "release",
                         "fetched_at": FETCHED})


def real_ctx(table: list[pd.DataFrame], core: dict, families: dict, selection=lambda when: []) -> M.Context:
    keys = {k for t in table for k in t["series"].unique()}
    return M.Context(pd.concat(table, ignore_index=True), specs={k: REAL[k] for k in keys if k in REAL},
                     core=core, families=families, derived={}, selection=selection,
                     forecasts=config.REPO / "no-forecasts-here")


def fixed(monkeypatch, directions: dict, stale: dict | None = None):
    """branch() with fixed directions per key (None = no valid measure); `stale` = key -> reason."""
    def fake(key, when, ctx):
        d = directions[key]
        return {"series": key, "valid": d is not None, "direction": d, "reason": "" if d is not None else "ingen takt"}

    monkeypatch.setattr(B, "measure", fake)
    monkeypatch.setattr(B, "stale_reason", lambda key, when, ctx: (stale or {}).get(key, ""))


def plain_ctx(keys, core, families, selection=lambda when: [], table=None) -> M.Context:
    specs = {k: catalog.Spec(key=k, branch="G6", label=k, unit="MUSD", freq="M", source="test",
                             fetch=lambda: pd.Series(dtype=float), lag_days=0, license="test") for k in keys}
    return M.Context(observations._empty() if table is None else table, specs=specs, core=core, families=families,
                     derived={}, selection=selection, forecasts=config.REPO / "no-forecasts-here")


def exact_index(family_directions: dict[str, list[int]]) -> Fraction | None:
    votes = [Fraction(sum(d + 1 for d in v), 2 * len(v)) for v in family_directions.values() if v]
    return sum(votes) / len(votes) if votes else None


def exact_state(x: Fraction | None, n_families: int) -> str:
    if x is None or n_families < R.MIN_FAMILIES:
        return R.STATE_FEW_FAMILIES
    return R.STATE_ACCEL if x >= Fraction(67, 100) else R.STATE_BRAKE if x <= Fraction(33, 100) else R.STATE_STABLE


def fam(up: int, neutral: int, down: int) -> list[int]:
    return [1] * up + [0] * neutral + [-1] * down


# ------------------------------------------------------------------ 1. register and family table


def test_rename_amendment_changes_only_the_name_of_the_g2_family(tmp_path):
    text = R.REGISTER_PATH.read_text(encoding="utf-8")
    head = "### 2026-11-24 – Diffusionsindex v2: familjenamnet i G2 byts"
    assert text.count(head) == 1 and text.index(head) > text.index("### 2026-11-24 – Diffusionsindex v2: en röst")
    before = tmp_path / "before.md"
    before.write_text(text.split(head, 1)[0], encoding="utf-8")
    old, new = R.parse_families(before), R.parse_families()
    assert old["G2"] == {"g2_price_at_capability": ["g2_price_at_capability_gpqa"]}
    assert new["G2"] == {"g2_price_at_capability_gpqa": ["g2_price_at_capability_gpqa"]}
    assert {k: v for k, v in old.items() if k != "G2"} == {k: v for k, v in new.items() if k != "G2"}
    assert new == R.FAMILIES and R.parse_register(before) == R.parse_register()  # core tables untouched


def test_multi_series_families_are_slices_of_one_catalog_source_and_unit():
    """The stated rule, checked against the catalog: a family with several series has one source (before the slice
    code in parentheses), one unit and one frequency."""
    checked = 0
    for code in catalog.BRANCHES:
        members: dict[str, list[str]] = {}
        for entry, f in R.entry_families(code).items():
            if "<" not in entry:
                members.setdefault(f, []).append(entry)
        for f, keys in members.items():
            if len(keys) < 2:
                continue
            specs = [REAL[k] for k in keys]
            assert len({s.source.split("(")[0].strip() for s in specs}) == 1, (code, f)
            assert len({s.unit for s in specs}) == 1 and len({s.freq for s in specs}) == 1, (code, f)
            assert {s.branch for s in specs} == {code}, (code, f)
            checked += 1
    assert checked == 11  # eu_ai_ent, npm, PyPI, Wikimedia, G.17, FT-900, EIA sales, EIA-930, PJM, Indeed, arXiv
    # the two ECI/Epoch-database borderline pairs are separate families by the registered rule (different concepts)
    assert R.entry_families("G9")["g9_epoch_open_weights_share"] != R.entry_families("G9")["g9_epoch_notable_models"]


def test_family_counts_match_the_register_text():
    n = {code: len(set(R.entry_families(code).values())) for code in catalog.BRANCHES}
    assert n == {"G1": 4, "G2": 1, "G3": 7, "G4": 6, "G5": 5, "G6": 7, "G7": 3, "G8": 1, "G9": 3}
    # G1: "3 plus antalet valda benchmarks" -> the placeholder family stands for each selected benchmark
    assert [f for f in R.FAMILIES["G1"] if R.SELECTED_PLACEHOLDER in f] == ["g1_epoch_bench_<valda>"]


def test_no_two_families_of_a_branch_share_a_series():
    for code in catalog.BRANCHES:
        seen: dict[str, str] = {}
        for entry, f in R.entry_families(code).items():
            assert entry not in seen, (code, entry)
            seen[entry] = f


# ------------------------------------------------------------------ 2. branch(): counting, votes, thresholds


def test_family_whose_only_series_are_stale_gets_no_vote_and_is_not_counted():
    """G6 with the real catalog specs: both Fed G.17 series end in 2024 (stale on the date), the other families are
    fresh. The G.17 family has no counted series, so v2 has 2 families ('för få källor') while v1 has 3 series."""
    core = {"G6": ["tsmc_revenue_m", "us_ip_semis_m", "us_ip_computers_m", "us_imports_tw_m"]}
    table = [real_rows("tsmc_revenue_m", "2026-09", 1), real_rows("us_ip_semis_m", "2024-06", 2),
             real_rows("us_ip_computers_m", "2024-06", 3), real_rows("us_imports_tw_m", "2026-08", 4)]
    out = B.branch("G6", WHEN, real_ctx(table, core, R.FAMILIES))
    stale = {m["series"]: m for m in out["series_not_counted"]}
    assert set(stale) == {"us_ip_semis_m", "us_ip_computers_m"}
    assert all(m["reason"].startswith("inaktuell") and m["family"] == "us_ip_g17" for m in stale.values())
    votes = {f["family"]: f for f in out["families"]}
    assert votes["us_ip_g17"]["vote"] is None and votes["us_ip_g17"]["series"] == []
    assert out["n_families"] == 2 and out["state"] == R.STATE_FEW_FAMILIES
    assert out["n_series"] == 2 and out["v1"]["state"] == R.STATE_FEW
    # with one more fresh series v1 has a state, v2 still too few sources
    table.append(real_rows("us_imports_kr_m", "2026-08", 5))
    core["G6"].append("us_imports_kr_m")
    out = B.branch("G6", WHEN, real_ctx(table, core, R.FAMILIES))
    assert out["n_series"] == 3 and out["n_families"] == 2 and out["state"] == R.STATE_FEW_FAMILIES
    assert out["v1"]["state"] in (R.STATE_ACCEL, R.STATE_STABLE, R.STATE_BRAKE)


def test_stale_series_in_a_mixed_family_drops_out_of_that_familys_vote():
    core = {"G6": ["tsmc_revenue_m", "us_ip_semis_m", "us_ip_computers_m", "us_imports_tw_m"]}
    table = [real_rows("tsmc_revenue_m", "2026-09", 1), real_rows("us_ip_semis_m", "2026-09", 2, accel=0.03),
             real_rows("us_ip_computers_m", "2024-06", 3), real_rows("us_imports_tw_m", "2026-08", 4)]
    out = B.branch("G6", WHEN, real_ctx(table, core, R.FAMILIES))
    used = {m["series"]: m for m in out["series_used"]}
    g17 = next(f for f in out["families"] if f["family"] == "us_ip_g17")
    assert g17["series"] == ["us_ip_semis_m"] and g17["vote"] == (used["us_ip_semis_m"]["direction"] + 1) / 2
    assert out["n_families"] == 3
    assert out["index"] == pytest.approx(float(exact_index(
        {f["family"]: [used[k]["direction"] for k in f["series"]] for f in out["families"]})))


def test_backfill_gated_family_is_excluded_before_voting():
    """G9: Epoch's notable-models series is gated (backfill, fewer than 24 months of own snapshots); arXiv counts."""
    core = {"G9": ["g9_arxiv_cs_ai", "g9_arxiv_cs_lg", "g9_epoch_notable_models"]}
    notable = real_rows("g9_epoch_notable_models", "2026-09", 9).assign(source="backfill")
    table = [real_rows("g9_arxiv_cs_ai", "2026-09", 7), real_rows("g9_arxiv_cs_lg", "2026-09", 8), notable]
    out = B.branch("G9", WHEN, real_ctx(table, core, R.FAMILIES))
    nc = {m["series"]: m for m in out["series_not_counted"]}
    assert "bakåtfylld" in nc["g9_epoch_notable_models"]["reason"]
    assert nc["g9_epoch_notable_models"]["family"] == "g9_epoch_notable_models"
    assert [f["family"] for f in out["families"] if f["vote"] is not None] == ["g9_arxiv"]
    assert out["n_families"] == 1 and out["n_series"] == 2 and out["state"] == R.STATE_FEW_FAMILIES


def test_benchmark_guard_removes_that_benchmarks_family(monkeypatch):
    """<valda>: one family per selected benchmark; a saturated benchmark (frontier > 0.90 known on the date) is not
    counted and its family gets no vote; a selected benchmark missing from the catalog is its own uncounted family."""
    sat, ok = "g1_epoch_bench_frontier_sat", "g1_epoch_bench_frontier_ok"
    fixed(monkeypatch, {sat: 1, ok: 1, "x1": -1, "x2": 0})
    months = pd.period_range("2025-01", "2026-09", freq="M")
    def rows(key, value):
        return pd.DataFrame({"series": key, "freq": "M", "period": [str(p) for p in months], "value": value,
                             "known_from": pd.DatetimeIndex(months.end_time.normalize()) + pd.Timedelta(days=1),
                             "source": "release", "fetched_at": FETCHED})
    table = pd.concat([rows(sat, 0.95), rows(ok, 0.4), rows("g1_epoch_bench_runs_ok", 3.0)], ignore_index=True)
    core = {"G1": ["g1_epoch_bench_frontier_<valda>", "x1", "x2"]}
    families = {"G1": {"g1_epoch_bench_<valda>": ["g1_epoch_bench_frontier_<valda>"], "x1": ["x1"], "x2": ["x2"]}}
    c = plain_ctx([sat, ok, "x1", "x2"], core, families, selection=lambda when: ["sat", "ok", "missing"], table=table)
    out = B.branch("G1", WHEN, c)
    fams = {f["family"]: f["vote"] for f in out["families"]}
    assert fams == {"g1_epoch_bench_sat": None, "g1_epoch_bench_ok": 1.0, "g1_epoch_bench_missing": None,
                    "x1": 0.0, "x2": 0.5}
    nc = {m["series"]: m for m in out["series_not_counted"]}
    assert nc[sat]["reason"].startswith("mättad") and nc[sat]["family"] == "g1_epoch_bench_sat"
    assert "saknas i katalogen" in nc["g1_epoch_bench_frontier_missing"]["reason"]
    assert out["n_families"] == 3 and out["index"] == pytest.approx(0.5) and out["state"] == R.STATE_STABLE


def test_btos_regimes_are_one_family_and_an_unknown_regime_is_no_family(monkeypatch):
    fixed(monkeypatch, {"btos_x_v1": 1, "btos_x_v2": -1, "p": 1, "q": 1})
    def rows(key, start, end):
        w = pd.period_range(start, end, freq="W-SUN")
        return pd.DataFrame({"series": key, "freq": "W", "period": [str(p) for p in w], "value": 5.0,
                             "known_from": pd.DatetimeIndex(w.end_time.normalize()) + pd.Timedelta(days=4),
                             "source": "release", "fetched_at": FETCHED})
    table = pd.concat([rows("btos_x_v1", "2024-01-01", "2025-06-01"), rows("btos_x_v2", "2025-06-15", "2026-10-18")],
                      ignore_index=True)
    core = {"G3": ["btos_x_<aktiv regim>", "p", "q"]}
    families = {"G3": {"btos_x": ["btos_x_<aktiv regim>"], "p": ["p"], "q": ["q"]}}
    out = B.branch("G3", WHEN, plain_ctx(["btos_x_v1", "btos_x_v2", "p", "q"], core, families, table=table))
    assert [m["series"] for m in out["series_used"] if m["family"] == "btos_x"] == ["btos_x_v2"]  # active regime only
    assert {f["family"]: f["vote"] for f in out["families"]} == {"btos_x": 0.0, "p": 1.0, "q": 1.0}
    assert out["n_families"] == 3 and out["index"] == pytest.approx(2 / 3) and out["state"] == R.STATE_STABLE
    early = B.branch("G3", "2023-06-30", plain_ctx(["btos_x_v1", "btos_x_v2", "p", "q"], core, families, table=table))
    assert early["series_not_counted"][0] == {"entry": "btos_x_<aktiv regim>", "series": None, "family": "btos_x",
                                               "reason": "btos_x_<aktiv regim>: ingen regim känd på beräkningsdagen"}
    assert early["n_families"] == 2 and early["state"] == R.STATE_FEW_FAMILIES


def test_empty_branch_and_branch_without_counted_series(monkeypatch):
    fixed(monkeypatch, {"a": None, "b": None, "c": None})
    c = plain_ctx(["a", "b", "c"], {"G5": [], "G6": ["a", "b", "c"]}, {"G6": {"f": ["a", "b"], "c": ["c"]}})
    empty = B.branch("G5", WHEN, c)
    assert (empty["state"], empty["v1"]["state"]) == ("inga registrerade kärnserier",) * 2
    assert empty["index"] is None and empty["n_families"] == 0 and empty["families"] == []
    none = B.branch("G6", WHEN, c)
    assert none["index"] is None and none["v1"]["index"] is None and none["n_families"] == 0
    assert none["state"] == R.STATE_FEW_FAMILIES and none["v1"]["state"] == R.STATE_FEW
    assert [f["vote"] for f in none["families"]] == [None, None]


@pytest.mark.parametrize("seed", range(20))
def test_v2_is_exactly_v1_when_every_family_is_one_series(monkeypatch, seed):
    rng = np.random.default_rng(100 + seed)
    dirs = {f"s{i}": int(rng.integers(-1, 2)) for i in range(int(rng.integers(1, 40)))}
    fixed(monkeypatch, dirs)
    out = B.branch("G4", WHEN, plain_ctx(dirs, {"G4": list(dirs)}, {"G4": {k: [k] for k in dirs}}))
    assert out["index"] == out["v1"]["index"]  # exact, not approx
    assert out["n_families"] == out["n_series"]
    assert out["state"] == out["v1"]["state"] or (out["state"], out["v1"]["state"]) == (R.STATE_FEW_FAMILIES,
                                                                                        R.STATE_FEW)


EXACT_OK = {
    "0,67 tre singletons + en 10-familj + en ned": ({"A": [1], "B": [1], "C": [1], "D": fam(3, 1, 6), "E": [-1]},
                                                    R.STATE_ACCEL),
    "0,67 med 25-familj": ({"A": [1], "B": [1], "C": [0], "D": fam(4, 1, 20)}, R.STATE_ACCEL),
    "0,33 med 10-familj": ({"A": [1], "B": [0], "C": fam(1, 1, 8), "D": [-1], "E": [-1]}, R.STATE_BRAKE),
    "2/3 är stabil": ({"A": [1], "B": [0], "C": [0, -1, 1, 0]}, R.STATE_STABLE),
    "1/3 är stabil": ({"A": [0], "B": [-1], "C": [1, -1, 0, 0]}, R.STATE_STABLE),
}


@pytest.mark.parametrize("case", list(EXACT_OK))
def test_mixed_families_at_the_thresholds(monkeypatch, case):
    family_dirs, expected = EXACT_OK[case]
    dirs = {f"{f}{i}": d for f, ds in family_dirs.items() for i, d in enumerate(ds)}
    fixed(monkeypatch, dirs)
    families = {"G6": {f: [f"{f}{i}" for i in range(len(ds))] for f, ds in family_dirs.items()}}
    out = B.branch("G6", WHEN, plain_ctx(dirs, {"G6": list(dirs)}, families))
    x = exact_index(family_dirs)
    assert exact_state(x, len(family_dirs)) == expected and out["state"] == expected
    assert out["index"] == pytest.approx(float(x), abs=1e-12) and out["n_families"] == len(family_dirs)


def test_exact_threshold_is_compared_exactly_with_a_large_family(monkeypatch):
    family_dirs = {"A": [1], "B": [1], "C": fam(0, 1, 49)}  # votes 1, 1, 1/100 -> index exactly 67/100
    dirs = {f"{f}{i}": d for f, ds in family_dirs.items() for i, d in enumerate(ds)}
    fixed(monkeypatch, dirs)
    families = {"G6": {f: [f"{f}{i}" for i in range(len(ds))] for f, ds in family_dirs.items()}}
    out = B.branch("G6", WHEN, plain_ctx(dirs, {"G6": list(dirs)}, families))
    assert exact_index(family_dirs) == Fraction(67, 100)
    assert out["state"] == R.STATE_ACCEL  # float gives 0.6699999999999999 -> "stabil"


def test_registered_family_tables_cannot_hit_a_threshold_exactly():
    """Why R9-N1 is latent: with the registered family sizes (G1 with up to 3 selected benchmarks) no combination of
    counted series and directions gives an index of exactly 0.67 or 0.33, so float rounding cannot flip a state."""
    def options(size):
        return {Fraction(k, 2 * n) for n in range(1, size + 1) for k in range(2 * n + 1)}

    for code in catalog.BRANCHES:
        sizes: dict[str, int] = {}
        for entry, f in R.entry_families(code).items():
            sizes[f] = sizes.get(f, 0) + 1
        if "g1_epoch_bench_<valda>" in sizes:
            del sizes["g1_epoch_bench_<valda>"]
            sizes.update({f"bench{i}": 1 for i in range(3)})
        sums = {(0, Fraction(0))}  # (counted families, sum of votes)
        for size in sizes.values():
            sums |= {(k + 1, s + v) for k, s in sums for v in options(size)}
        hits = [(k, s / k) for k, s in sums if k >= R.MIN_FAMILIES and s / k in (Fraction(67, 100), Fraction(33, 100))]
        assert not hits, code


def test_n_families_counts_a_family_whose_series_are_withheld(monkeypatch):
    fixed(monkeypatch, {"pub1": 1, "pub2": -1, "zz_w1": 1, "zz_w2": 1})
    c = plain_ctx(["pub1", "pub2", "zz_w1", "zz_w2"], {"G9": ["pub1", "pub2", "zz_w1", "zz_w2"]},
                  {"G9": {"pub1": ["pub1"], "pub2": ["pub2"], "w": ["zz_w1", "zz_w2"]}})
    for k in ("zz_w1", "zz_w2"):
        c.specs[k] = catalog.Spec(key=k, branch="G9", label=k, unit="MUSD", freq="M", source="test",
                                  fetch=lambda: pd.Series(dtype=float), lag_days=0, license="unverified", publish=False)
    out = B.branch("G9", WHEN, c)
    assert out["n_families"] == 3 and out["index"] == pytest.approx((1 + 0 + 1) / 3) and out["state"] == R.STATE_STABLE


# ------------------------------------------------------------------ 3. licence gate through every consumer

SINGLETON_WITHHELD = {"G6": {"pub_pair": ["pub_a", "pub_b"], "pub_c": ["pub_c"]},
                      "G9": {TL.SECRET: [TL.SECRET], "pub_g9_pair": ["pub_g9", "pub_g9b"]}}


def test_letter_counts_a_withheld_singleton_family_without_naming_or_voting_it(tmp_path):
    """The family id of a singleton family is its series key (as in the register): it must be hidden like the series."""
    ctx = TL.make_ctx(tmp_path)
    ctx.families = SINGLETON_WITHHELD
    TL.write_forecasts(tmp_path / "forecasts")
    snaps = tmp_path / "snapshots"
    doc = json.loads(TL.write_snapshot(ctx, snaps, TL.MONTH).read_text(encoding="utf-8"))
    g9 = doc["branches"]["G9"]
    assert g9["n_families"] == 2 and g9["n_series"] == 3 and {f["family"] for f in g9["families"]} == {
        TL.SECRET, "pub_g9_pair"}
    text = L.letter(TL.MONTH, ctx, snapshots_dir=snaps, forecasts_dir=tmp_path / "forecasts")
    sec = text.split("### G9 ", 1)[1].split("\n### ", 1)[0]
    assert "2 källor (3 serier: " in sec and "`pub_g9_pair` " in sec
    assert "1 källa med serier som inte visas av licensskäl räknas utan att namnges" in sec
    outside = TL.outside_withheld(text)
    assert TL.SECRET not in outside and TL.SECRET_LABEL not in outside
    assert TL.SECRET in text  # named only in the withheld section


def test_old_site_counts_a_withheld_singleton_family_without_naming_or_voting_it(tmp_path):
    site = TS.build_site(tmp_path, live=True, families=SINGLETON_WITHHELD)
    g9 = TS.load(site, "gren/G9")
    assert g9["n_families"] == 2 and g9["n_families_withheld"] == 1
    assert [f["family"] for f in g9["families"]] == ["pub_g9_pair"]
    assert TS.SECRET not in json.dumps(TS.strip_withheld(TS.all_json(site)), ensure_ascii=False)
    method = TS.load(site, "metod")["index_families"]
    assert ("G9", TS.SECRET) not in {(r["branch"], r["family"]) for r in method}
    assert {"branch": "G9", "family": "pub_g9_pair", "entries": ["pub_g9", "pub_g9b"], "n_withheld": 0} in method
    for p in site.glob("*.html"):
        html = re.sub(r'<section id="withheld".*?</section>', "", p.read_text(encoding="utf-8"), flags=re.S)
        assert TS.SECRET not in html, p.name
    html = (site / "gren-g9.html").read_text(encoding="utf-8")
    assert "1 källa med serier som inte visas av licensskäl räknas i indexet utan att namnges här" in html


@pytest.fixture(scope="module")
def singleton_bundle(tmp_path_factory):
    """The synthetic world with both withheld arXiv series as singleton families named after their keys."""
    root = tmp_path_factory.mktemp("r9_bundle")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(census_btos, "SCHEDULE_LOG", root / "no_schedule.parquet")
        ctx = SY.context(root)
        ctx.families = {**ctx.families, "G9": {k: [k] for k in SY.CORE["G9"]}}
        paths = SY.write_inputs(root, ctx)
        docs = E.assemble(ctx, today=SY.TODAY, history_from=SY.HISTORY_FROM, calibration=SY.calibration(), **paths)
    return ctx, docs


def test_bundle_with_withheld_singleton_families_passes_the_gate(singleton_bundle):
    ctx, docs = singleton_bundle
    assert G.scan(docs, ctx) == []
    g9 = docs["branch/G9.json"]
    assert g9["n_families_withheld"] == 2 and [f["family"] for f in g9["families"]] == ["g9_epoch_notable_models"]
    assert g9["n_families"] == 3
    fams = next(b for b in docs["method.json"]["branches"] if b["code"] == "G9")["families"]
    assert {f["family"] for f in fams} == {"g9_epoch_notable_models"}
    for key in SY.WITHHELD:
        assert key not in json.dumps(TS.strip_withheld(docs), ensure_ascii=False)


def test_gate_catches_a_withheld_family_id_if_a_consumer_ever_exposes_it(singleton_bundle):
    ctx, docs = singleton_bundle
    planted = json.loads(json.dumps(docs["branch/G9.json"]))
    planted["families"].append({"family": SY.WITHHELD[0], "series": [], "n_series": 1, "vote": 1.0})
    assert G.scan({"branch/G9.json": planted}, ctx)


def test_quarterly_report_with_v2_snapshots(tmp_path):
    """K1 changed the quarterly summary order and footer without a test: v2 states and wording, withheld unnamed."""
    import test_quarterly as TQ

    ctx = TQ.make_ctx(tmp_path)
    ctx.families = {"G6": {"pub_all": list(TQ.PUBLIC)}, "G9": {TQ.SECRET: [TQ.SECRET], "pub_g9": ["pub_g9"],
                                                              "pub_g9b": ["pub_g9b"]}}
    env = (ctx, tmp_path / "snapshots", tmp_path / "forecasts", TQ.write_docs(tmp_path / "docs"))
    TQ.write_forecasts(tmp_path / "forecasts")
    text = TQ.live(env)
    snap = json.loads((tmp_path / "snapshots" / "2026-09.json").read_text(encoding="utf-8"))
    assert snap["branches"]["G6"]["state"] == R.STATE_FEW_FAMILIES and snap["branches"]["G9"]["n_families"] == 3
    summary = [line for line in text.splitlines() if line.startswith("- Läget vid kvartalets slut")][0]
    assert "för få källor" in summary and "G6" in summary.split("för få källor", 1)[1].split(";", 1)[0]
    assert "(regel v2)" in text and "räknade källor anges inget tillstånd" in text
    assert TQ.SECRET not in TQ.outside_withheld(text) and TQ.SECRET_LABEL not in TQ.outside_withheld(text)


# ------------------------------------------------------------------ 4. snapshot writer and CLI on a tmp table


def cli_table(path: Path) -> Path:
    parts = [real_rows("tsmc_revenue_m", "2026-09", 11), real_rows("us_ip_semis_m", "2026-09", 12),
             real_rows("us_ip_computers_m", "2026-09", 13), real_rows("us_imports_tw_m", "2026-08", 14),
             real_rows("us_imports_kr_m", "2026-08", 15), real_rows("g9_arxiv_cs_ai", "2026-09", 16),
             real_rows("g9_arxiv_cs_lg", "2026-09", 17)]
    days = pd.period_range("2020-01-01", "2026-10-20", freq="D")
    for i, c in enumerate(("us", "gb")):
        rng = np.random.default_rng(20 + i)
        parts.append(pd.DataFrame({
            "series": f"ai_postings_share_{c}_d", "freq": "D", "period": [str(p) for p in days],
            "value": 1.0 + np.abs(np.cumsum(0.001 * rng.standard_normal(len(days)))),
            "known_from": pd.DatetimeIndex(days.end_time.normalize()) + pd.Timedelta(days=17),
            "source": "release", "fetched_at": FETCHED}))
    quarters = pd.period_range("2012Q1", "2026Q2", freq="Q")
    for i, k in enumerate(("rev_aws", "rev_google_cloud", "rev_msft_cloud", "rev_nvda_datacenter")):
        rng = np.random.default_rng(30 + i)
        parts.append(pd.DataFrame({
            "series": k, "freq": "Q", "period": [str(q) for q in quarters],
            "value": 1000 * np.exp(np.cumsum(0.04 + 0.02 * rng.standard_normal(len(quarters)))),
            "known_from": pd.DatetimeIndex(quarters.end_time.normalize()) + pd.Timedelta(days=30),
            "source": "release", "fetched_at": FETCHED}))
    t = pd.concat(parts, ignore_index=True)
    observations.write_parquet(t, path)
    return path


def run_cli(argv) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert CLI.main(argv) == 0
    return buf.getvalue()


@pytest.fixture
def tmp_table(tmp_path, monkeypatch):
    monkeypatch.setattr(observations, "PATH", observations.PATH)  # main() sets it; restored afterwards
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    return cli_table(tmp_path / "obs.parquet")


def test_cli_snapshot_records_the_rule_and_families(tmp_path, tmp_table):
    out = tmp_path / "snaps"
    printed = run_cli(["--table", str(tmp_table), "snapshot", "--date", WHEN, "--out-dir", str(out)])
    assert "wrote" in printed
    d = json.loads((out / "2026-10.json").read_text(encoding="utf-8"))
    r = d["rules"]
    assert (r["index_rule"], r["min_families"], r["min_series"]) == ("v2", 3, 3)
    assert r["families"] == {code: R.FAMILIES[code] for code in catalog.BRANCHES} and "v2" in r["index_rule_note"]
    assert d["register_sha256"] == S.register_sha256() and d["record"] == "skarp ögonblicksbild"
    assert "regime" not in d and d["reconciliations"]["in_diffusion"] is False  # C4 from 2026-11-30 only
    g6, g4, g8, g9 = (d["branches"][c] for c in ("G6", "G4", "G8", "G9"))
    assert all(b["rule_version"] == "v2" and set(b["v1"]) == {"index", "state", "n_series", "n_up", "n_neutral",
                                                              "n_down"} for b in d["branches"].values())
    assert g6["n_series"] == 5 and g6["n_families"] == 3
    assert [f["family"] for f in g6["families"] if f["vote"] is not None] == ["tsmc_revenue_m", "us_ip_g17",
                                                                             "us_imports_ft900"]
    dirs = {m["series"]: m["direction"] for m in g6["series_used"]}
    assert g6["index"] == pytest.approx(float(exact_index(
        {f["family"]: [dirs[k] for k in f["series"]] for f in g6["families"]})))
    assert g4["n_families"] == g4["n_series"] == 4 and g4["index"] == g4["v1"]["index"]
    assert (g8["n_series"], g8["n_families"], g8["state"]) == (2, 1, R.STATE_FEW_FAMILIES)
    assert (g9["n_families"], g9["state"]) == (1, R.STATE_FEW_FAMILIES)
    with pytest.raises(FileExistsError):  # never rewritten
        S.write(WHEN, observations.load(tmp_table), out_dir=out)


def test_snapshot_writer_still_adds_the_regime_section(tmp_path, tmp_table, monkeypatch):
    from ai_tracker.regime import live as regime_live

    monkeypatch.setattr(S, "regime_section", lambda when, table, out_dir=None: {"model": "C4", "ms": {"x": 1}})
    p = S.write(WHEN, observations.load(tmp_table), out_dir=tmp_path / "s", regime=True)
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d[regime_live.SECTION] == {"model": "C4", "ms": {"x": 1}} and d["rules"]["index_rule"] == "v2"


def test_cli_show_due_and_backcast_compare(tmp_path, tmp_table):
    show = run_cli(["--table", str(tmp_table), "show", "--date", WHEN])
    g6 = next(line for line in show.splitlines() if line.startswith("G6 "))
    assert "källor=3" in g6 and "n=5" in g6 and " v1 " in g6
    g8 = next(line for line in show.splitlines() if line.startswith("G8 "))
    assert "för få källor" in g8 and "källor=1" in g8 and "v1 " in g8
    assert "Avstämningar (inte i något grenindex)" in show
    assert "no snapshot due" in run_cli(["due", "--today", "2026-11-24"])
    assert S.due("2026-11-30", tmp_path / "none") and not S.due("2026-11-29", tmp_path / "none")
    csv = tmp_path / "bc.csv"
    printed = run_cli(["--table", str(tmp_table), "backcast", "--start", "2026-08", "--end", "2026-10",
                       "--out", str(csv), "--compare", "2"])
    df = pd.read_csv(csv)
    assert len(df) == 3 * len(catalog.BRANCHES) and set(df["label"]) == {S.BACKCAST_LABEL}
    lines = [x for x in printed.splitlines() if x.startswith("|")]
    assert lines[0] == "| Gren | Månad | Index v1 | Tillstånd v1 | Serier | Index v2 | Tillstånd v2 | Källor |"
    assert len(lines) == 2 + 2 * len(catalog.BRANCHES)
    assert any(x.startswith("| G1 | 2026-10 | – |") for x in lines)  # no counted series: dash, no crash
    assert any(x.startswith("| G8 | 2026-10 |") and "| för få källor | 1 |" in x for x in lines)


# ------------------------------------------------------------------ 5. bundle 1.4.0 and the web


def test_state_enum_has_both_few_states_and_the_bundle_is_1_4():
    from ai_tracker import site_bundle

    common = json.loads((Path(SY.__file__).parent / "schema" / "common.json").read_text(encoding="utf-8"))
    states = common["$defs"]["state"]["enum"]
    assert R.STATE_FEW_FAMILIES in states and R.STATE_FEW in states and states == E.STATES
    # index v2 came with 1.4.0 after main's 1.3.0 (W14), a minor: additive; 1.5.0 (WV2) adds expectations.json
    major, minor, _ = (int(x) for x in site_bundle.VERSION.split("."))
    assert (major, minor) >= (1, 4) and major == 1
    man = json.loads((config.REPO / "web-data-fixtures" / "manifest.json").read_text(encoding="utf-8"))
    assert man["version"] == site_bundle.VERSION


def _schedule(path: Path) -> Path:
    pd.DataFrame({"smpdt": [202624], "col_end": [pd.Timestamp("2026-11-29")],
                  "published": [pd.Timestamp("2026-12-03")], "fetched_at": [pd.Timestamp("2026-11-20")]}
                 ).to_parquet(path, index=False)
    return path


def test_synthetic_bundle_does_not_read_the_environments_btos_schedule(tmp_path, monkeypatch):
    monkeypatch.setattr(census_btos, "SCHEDULE_LOG", _schedule(tmp_path / "schedule_log.parquet"))
    ctx = SY.context(tmp_path)
    paths = SY.write_inputs(tmp_path, ctx)
    docs = E.assemble(ctx, today=SY.TODAY, history_from=SY.HISTORY_FROM, calibration=SY.calibration(), **paths)
    n5 = next(c for c in docs["overview.json"]["calendar"] if c["id"] == "n5")
    assert n5["next_origin"] is None  # as in the committed fixtures, built without a schedule


def test_web_state_vocabulary_has_the_v2_state():
    """R9-S1, fixed by WV2: the web's state vocabulary has the v2 no-state and falls back to it."""
    text = (config.REPO / "web" / "src" / "lib" / "design" / "state.ts").read_text(encoding="utf-8")
    assert "'för få källor'" in text and "'för få källor'" in (
        config.REPO / "web" / "src" / "lib" / "data" / "types.ts").read_text(encoding="utf-8")
    assert "NO_STATE: StateName = 'för få källor'" in text


def test_asml_licence_text_names_asml_not_tsmc():
    assert "TSMC" not in REAL["asml_net_sales"].license
