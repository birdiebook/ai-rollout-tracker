"""Tests for the site bundle (ai_tracker.site_bundle): schemas, licence gate, versions (time travel), budgets, the
committed fixtures. No network; one test reads the real table when it is reachable (real_data)."""

from __future__ import annotations

import copy
import json
import math
import random
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ai_tracker import catalog, observations
from ai_tracker.site import data as D
from ai_tracker.site_bundle import VERSION
from ai_tracker.site_bundle import __main__ as CLI
from ai_tracker.site_bundle import build as B
from ai_tracker.site_bundle import export as E
from ai_tracker.site_bundle import gate as G
from ai_tracker.site_bundle import schema as SC
from ai_tracker.site_bundle import synthetic as SY
from ai_tracker.site_bundle import vintages as V
from ai_tracker.state import measures as M
from conftest import real_table_exists

REPO = Path(__file__).resolve().parents[1]
COMMITTED = REPO / "web-data-fixtures"


@pytest.fixture(scope="module")
def bundle(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("bundle") / "web-data"
    CLI.build_fixtures(out)
    return out


@pytest.fixture(scope="module")
def docs(bundle) -> dict:
    return B.read(bundle)


@pytest.fixture(scope="module")
def world():
    ctx = SY.context(Path("/nonexistent"))
    return ctx


def numbers(x):
    if isinstance(x, bool):
        return
    if isinstance(x, (int, float)):
        yield float(x)
    elif isinstance(x, dict):
        for v in x.values():
            yield from numbers(v)
    elif isinstance(x, list):
        for v in x:
            yield from numbers(v)


# ------------------------------------------------------------------ layout and schemas


def test_every_schema_is_valid_and_every_document_has_one(docs):
    for name in SC.names():
        SC.validator(name)  # check_schema inside
    paths = set(docs)
    for p in paths:
        SC.schema_for(p)
    expected = {"manifest.json", "overview.json", "flow.json", "regime.json", "method.json", "withheld.json",
                "letters.json", "series/index.json", "nowcast/d2.json", "letters/2026-10.json", "reports/2026Q3.json"}
    expected |= {f"branch/{c}.json" for c in catalog.BRANCHES} | {f"nowcast/n{k}.json" for k in range(1, 7)}
    assert expected <= paths
    published = [k for k, v in SY.SERIES.items() if v[5]]
    assert {f"series/{k}.json" for k in published} == {p for p in paths if p.startswith("series/")} - {"series/index.json"}


def test_every_document_validates_and_a_change_is_caught(docs):
    assert SC.validate(docs) == []
    bad = copy.deepcopy(docs["series/us_ip_semis_m.json"])
    bad["measure"]["new_field"] = 1
    assert SC.errors("series/us_ip_semis_m.json", bad)
    bad = copy.deepcopy(docs["overview.json"])
    bad["record"]["status"] = "maybe"
    assert SC.errors("overview.json", bad)
    with pytest.raises(B.BundleError, match="schema"):
        B.serialise({**{k: v for k, v in docs.items() if k != "manifest.json"}, "overview.json": bad},
                    E.build_info("x", SY.BUILT_UTC), SY.TODAY)


def test_manifest_lists_every_file_with_checksum_and_the_snapshot_status(bundle, docs):
    man = docs["manifest.json"]
    assert man["version"] == VERSION and man["synthetic"] is True and man["git_sha"] == SY.GIT_SHA
    assert man["snapshot"]["status"] == "live" and man["snapshot"]["file"] == "snapshots/2026-10.json"
    on_disk = {str(p.relative_to(bundle)) for p in bundle.rglob("*.json")} - {"manifest.json"}
    assert {f["path"] for f in man["files"]} == on_disk
    assert {f"schema/{n}.json" for n in SC.names()} <= on_disk
    assert CLI.validate_dir(bundle) == []
    (bundle / "overview.json").write_text("{}", encoding="utf-8")  # tampering is found (and restored below)
    try:
        assert any("sha256" in e for e in CLI.validate_dir(bundle))
    finally:
        (bundle / "overview.json").write_bytes(B.dumps(docs["overview.json"]))


def test_record_status_is_labelled_everywhere(docs):
    for p, d in docs.items():
        if isinstance(d, dict) and "record" in d:
            assert d["record"]["status"] == "live" and d["record"]["kind"] == "skarp", p
    st = docs["overview.json"]["stripes"]
    assert st["months"][-1] == "2026-10" and st["kind"][-1] == "skarp" and set(st["kind"][:-1]) == {"rekonstruerad"}
    assert all(len(r["index"]) == len(st["months"]) == len(r["state"]) for r in st["rows"])
    h = docs["overview.json"]["headline"]
    assert sum(h["counts"].values()) == 9 and h["sentence"].startswith(f"Av {h['n_with_state']} grenar")


# ------------------------------------------------------------------ licence gate


def test_the_gate_is_the_site_rule():
    ctx = M.Context(observations._empty())
    assert all(G.publishable(s.key, ctx) == D.publishable(s.key, ctx) == s.publish for s in catalog.ALL)
    assert G.publishable("capex_ocf_hyp4", ctx) and not G.publishable(None, ctx)
    assert {s.key for s in catalog.ALL if not s.publish} <= G.withheld_keys(ctx)


def test_no_withheld_key_or_value_anywhere_in_the_bundle(docs, world):
    assert G.scan(docs, world) == []
    text = json.dumps({k: v for k, v in docs.items()}, ensure_ascii=False)
    for key in SY.WITHHELD:  # named, but only in withheld lists (scan above) ...
        assert key in text
    named = [w["key"] for d in docs.values() for w in G.iter_withheld(d)]
    assert set(SY.WITHHELD) <= set(named)
    # ... and none of their values (drawn around 7e6 and 6e6) reaches any document, in any rounding
    t = SY.table()
    leaked = set()
    for v in t[t.series.isin(SY.WITHHELD)]["value"]:
        leaked |= {V._r(v), D._num(v), D._num(v, 4), round(float(v), 1), round(float(v))}
    assert not leaked & set(numbers(docs))
    assert "inputs" not in json.dumps(docs["nowcast/n2.json"])  # forecast inputs (name a withheld series) dropped
    g9 = docs["branch/G9.json"]
    assert g9["n_withheld_counted"] == 2 and {w["key"] for w in g9["withheld"]} == set(SY.WITHHELD)
    assert docs["regime.json"]["n_breaks_withheld"] == 1 and [b["series"] for b in docs["regime.json"]["breaks"]] == ["rev_google_cloud"]


def test_scan_finds_every_kind_of_leak(docs, world):
    key = SY.WITHHELD[0]
    planted = [
        ("overview.json", lambda d: d["headline"].__setitem__("sentence", f"se {key}.")),
        ("branch/G6.json", lambda d: d["counted"][0].__setitem__("label", key)),
        ("flow.json", lambda d: d.__setitem__(key, 1)),
        ("branch/G9.json", lambda d: d["withheld"][0].__setitem__("value", 7.7e6)),
        ("branch/G9.json", lambda d: d["withheld"][0].__setitem__("label", 3.0)),
    ]
    for path, plant in planted:
        d = copy.deepcopy(docs[path])
        plant(d)
        assert G.scan({path: d}, world), path
    assert G.scan({f"series/{key}.json": {}}, world)
    assert G.scan({"x.json": {"note": f"{key}_suffix and prefix_{key}"}}, world) == []  # word-bounded


def test_a_leak_stops_the_build(tmp_path, monkeypatch):
    ctx = SY.context(tmp_path)
    paths = SY.write_inputs(tmp_path, ctx)
    real = E.method_doc

    def leaky(ctx, rec):
        d = real(ctx, rec)
        d["labels"]["live"] = f"inkl. {SY.WITHHELD[0]}"
        return d

    monkeypatch.setattr(E, "method_doc", leaky)
    with pytest.raises(E.GateError):
        E.assemble(ctx, today=SY.TODAY, history_from="2026-09", calibration={}, series=[], **paths)


# ------------------------------------------------------------------ versions (time travel)


def _rows(ctx, key):
    r = ctx.rows(key).copy()
    r["kday"] = V.day_ceil(r["known_from"])
    return r


def test_versions_never_before_known_from_and_replay_equals_as_of(docs, world):
    today = pd.Timestamp(SY.TODAY)
    rnd = random.Random(7)
    for key, (*_, pub) in SY.SERIES.items():
        if not pub:
            continue
        enc = docs[f"series/{key}.json"]["versions"]
        rows = _rows(world, key)
        assert enc["dates"] == sorted(enc["dates"]) and max(enc["dates"]) <= SY.TODAY
        if enc["native_freq"] == "D":
            continue  # monthly versions: next test
        first_known = rows.groupby("period")["kday"].min()
        known = {(p, str(k.date())): V._r(v) for p, k, v in zip(rows["period"], rows["kday"], rows["value"])}
        for p, d, v in zip(enc["p"], enc["d"], enc["v"]):
            period, day = enc["periods"][p], enc["dates"][d]
            assert day >= str(first_known[period].date()), (key, period)  # never before the first known_from
            assert known[(period, day)] == v, (key, period, day)  # the exact table version on that day
        for day in rnd.sample(enc["dates"], min(15, len(enc["dates"]))) + [SY.TODAY]:
            want = {str(p): V._r(x) for p, x in observations.as_of(key, day, rows).items()}
            assert V.replay(enc, day) == want, (key, day)
        assert V.replay(enc, today) == dict(zip(docs[f"series/{key}.json"]["levels"]["periods"],
                                                docs[f"series/{key}.json"]["levels"]["values"]))


def test_daily_series_versions_are_the_registered_monthly_aggregate_as_of_each_day(docs, world):
    key = "ai_postings_share_us_d"
    enc = docs[f"series/{key}.json"]["versions"]
    assert enc["native_freq"] == "D" and enc["freq"] == "M" and enc["aggregation"] == M.rule_for(key, world).agg
    rows = _rows(world, key)
    days = sorted(rows["kday"].unique())
    for day in random.Random(3).sample(days, 30) + days[-2:]:
        s = observations.as_of(key, day, rows)
        want = {str(p): V._r(x) for p, x in M.to_monthly(s, enc["aggregation"]).items()}
        assert V.replay(enc, day) == want, day
    first_month = {}
    for p, kd in zip(rows["period"], rows["kday"]):  # a month version is never dated before all its days were known
        m = p[:7]
        first_month[m] = min(first_month.get(m, kd), kd)
    for p, d in zip(enc["p"], enc["d"]):
        assert enc["dates"][d] >= str(first_month[enc["periods"][p]].date())


def test_future_rows_time_of_day_and_collapse_never_date_a_value_earlier():
    rows = pd.DataFrame({"series": "s", "freq": "M", "period": ["2026-01", "2026-01", "2026-02", "2026-03"],
                         "value": [1.0, 1.5, 2.0, 3.0],
                         "known_from": pd.to_datetime(["2026-02-10", "2026-03-10 08:00", "2026-03-10", "2026-12-01"], format="ISO8601"),
                         "source": "release", "fetched_at": pd.Timestamp("2026-11-01")})
    enc = V.encode(rows, "2026-11-24")
    assert "2026-03" not in enc["periods"]  # not known yet on the build date
    assert V.replay(enc, "2026-03-10") == {"2026-01": 1.0, "2026-02": 2.0}  # 08:00 counts from the next day
    assert V.replay(enc, "2026-03-11") == {"2026-01": 1.5, "2026-02": 2.0}
    rng = np.random.default_rng(1)
    periods = [str(p) for p in pd.period_range("2010-01", "2026-09", freq="M")]
    big = pd.concat([pd.DataFrame({"series": "s", "freq": "M", "period": periods,
                                   "value": rng.standard_normal(len(periods)) + v,
                                   "known_from": pd.Timestamp("2015-01-01") + pd.Timedelta(days=200 * v),
                                   "source": "release", "fetched_at": pd.Timestamp("2026-11-01")}) for v in range(30)])
    enc = V.encode(big, "2026-11-24", max_rows=1000)
    cut = enc["collapsed_before"]
    assert cut and enc["n_versions"] <= 1000 and min(enc["dates"]) == cut
    big["kday"] = V.day_ceil(big["known_from"])
    mid = (pd.Timestamp(cut) + (pd.Timestamp("2026-11-24") - pd.Timestamp(cut)) / 2).date()
    for day in ["2026-11-24", mid, cut]:  # from the cutoff on, time travel is exact
        want = {str(p): V._r(x) for p, x in observations.as_of("s", day, big).items()}
        assert V.replay(enc, day) == want
    assert V.replay(enc, (pd.Timestamp(cut) - pd.Timedelta(days=1)).date()) == {}


def test_measure_history_is_the_record_of_each_month(docs):
    s = docs["series/tsmc_revenue_m.json"]
    h, months = s["measure_history"], docs["overview.json"]["stripes"]["months"]
    assert h["months"] == months and all(h["counted"]) and h["kind"][-1] == "skarp"
    g6 = docs["branch/G6.json"]
    m = next(x for x in g6["counted"] if x["key"] == "tsmc_revenue_m")
    assert h["pace"][-1] == m["pace"] and h["direction"][-1] == m["direction"]
    assert s["measure"]["pace"] == m["pace"] and s["in_record"] and s["counted"]
    assert all(k <= f"{mo}-31" for k, mo in zip(h["known_from"], h["months"]) if k)  # known by each month end


# ------------------------------------------------------------------ sizes and budgets


def test_budgets_are_enforced(docs):
    files = [{"path": "series/x.json", "bytes": 10, "gzip_bytes": 10}]
    assert B.budget_violations(files) == []
    raw, gz = B.budget_for("series/x.json")
    assert B.budget_violations([{"path": "series/x.json", "bytes": raw + 1, "gzip_bytes": 1}])
    assert B.budget_violations([{"path": "overview.json", "bytes": 1, "gzip_bytes": B.START_PAGE_GZIP_BUDGET + 1}])
    man = docs["manifest.json"]
    assert man["totals"]["files"] == len(man["files"]) and "start page data" in B.size_report(man)
    for f in man["files"]:
        B.budget_for(f["path"])  # every file has a budget


# ------------------------------------------------------------------ committed fixtures


def _close(a, b, path="") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return [f"{path}: keys {sorted(set(a) ^ set(b))[:5]}"]
        return [e for k in a for e in _close(a[k], b[k], f"{path}.{k}")]
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} != {len(b)}"]
        return [e for i, (x, y) in enumerate(zip(a, b)) for e in _close(x, y, f"{path}[{i}]")]
    if isinstance(a, float) and isinstance(b, (int, float)) and not isinstance(b, bool):
        return [] if math.isclose(a, b, rel_tol=1e-3, abs_tol=1e-6) else [f"{path}: {a} != {b}"]
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


def test_committed_fixtures_are_the_current_synthetic_bundle(docs):
    """web-data-fixtures/ is what the front-end tracks develop against: regenerate it with
    `python -m ai_tracker.site_bundle fixtures` when the contract changes."""
    committed = B.read(COMMITTED)
    ignore = {"manifest.json"}
    diff = [e for p in sorted(set(docs) | set(committed)) if p not in ignore
            for e in (_close(docs.get(p), committed.get(p), p) if p in docs and p in committed else [f"{p}: missing"])]
    assert not diff, diff[:10]
    man = committed["manifest.json"]
    assert man["synthetic"] is True and man["version"] == VERSION
    assert {f["path"] for f in man["files"]} == {f["path"] for f in docs["manifest.json"]["files"]}
    for p in SC.SCHEMA_DIR.glob("*.json"):
        assert (COMMITTED / "schema" / p.name).read_bytes() == p.read_bytes(), p.name
    assert CLI.validate_dir(COMMITTED) == []


def test_fixture_labels_say_synthetic(docs):
    for p, d in docs.items():
        if p.startswith("series/") and p != "series/index.json":
            assert d["label"].startswith("[syntetisk]") and d["source"] == SY.SOURCE, p


# ------------------------------------------------------------------ real table


@pytest.mark.real_data
@pytest.mark.skipif(not real_table_exists(), reason="no real observation table")
def test_real_bundle_passes_the_gate_and_the_schemas():
    """A cut-down real build (few series, short history, no backtests): the catalog's real withheld keys never reach
    the documents, and every document validates."""
    ctx = M.Context(observations.load())
    keys = ["us_ip_semis_m", "tsmc_revenue_m", "ai_postings_share_us_d", "capex_ocf_hyp4", "x_capex_cloud",
            "g9_arxiv_cs_lg"]  # the last one is withheld: no document
    docs = E.assemble(ctx, today=D.utc_today(), history_from=str((D.utc_today() - pd.DateOffset(months=3)).to_period("M")),
                      calibration={}, series=keys)
    assert "series/g9_arxiv_cs_lg.json" not in docs and "series/us_ip_semis_m.json" in docs
    assert G.scan(docs, ctx) == []
    assert SC.validate(docs) == []
    files = B.serialise(docs, E.build_info("test"), str(D.utc_today().date()))
    man = json.loads(files["manifest.json"])
    assert man["synthetic"] is False and not B.budget_violations(man["files"])
