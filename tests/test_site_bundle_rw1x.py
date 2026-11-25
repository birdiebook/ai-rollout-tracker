"""RW1-X (fixes from review R-W1, docs/granskning/rw1_webb.md): the backfill boundary is the day the backfilled rows
were fetched (3a), every live forecast file carries the commit that added it and that commit precedes its outcome
(4a), and the built site is scanned for withheld keys, including constants written into web/src (1b)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from ai_tracker import observations
from ai_tracker.site_bundle import __main__ as CLI
from ai_tracker.site_bundle import build as B
from ai_tracker.site_bundle import export as E
from ai_tracker.site_bundle import gate as G
from ai_tracker.site_bundle import synthetic as SY
from ai_tracker.state import measures as M
from conftest import real_table_exists

REPO = Path(__file__).resolve().parents[1]
COMMITTED = REPO / "web-data-fixtures"


def _rows(known: list[str], fetched: list[str], source: str = "backfill") -> pd.DataFrame:
    return pd.DataFrame({"series": "x", "freq": "M", "period": [f"2010-{i + 1:02d}" for i in range(len(known))],
                         "value": 1.0, "known_from": pd.to_datetime(known), "source": source,
                         "fetched_at": pd.to_datetime(fetched)})


# ------------------------------------------------------------------ 3a: the backfill boundary


def test_backfill_fetched_is_the_fetch_day_not_the_rule_day():
    """us_elec_sales_com_*: rule days up to 2013-01-29, fetched 2026-11-23. The boundary is the fetch day."""
    r = _rows(["2010-03-01", "2013-01-29"], ["2026-11-23", "2026-11-23"])
    out = E._row_sources(r, "2026-11-25")
    assert out["backfill_last_known"] == "2013-01-29"
    assert out["backfill_fetched"] == "2026-11-23"


def test_backfill_fetched_rounds_a_time_of_day_up_and_ignores_rows_not_known_yet():
    r = _rows(["2010-03-01", "2013-01-29"], ["2026-11-23 10:15", "2026-11-23 00:00"])
    assert E._row_sources(r, "2026-11-25")["backfill_fetched"] == "2026-11-24"  # 10:15 is known from the next day
    late = pd.concat([_rows(["2013-01-29"], ["2026-11-23"]), _rows(["2027-01-01"], ["2027-01-01"])])
    assert E._row_sources(late, "2026-11-25")["backfill_fetched"] == "2026-11-23"  # a row after as_of is not known
    plain = _rows(["2010-03-01"], ["2026-11-23"], source="release")
    assert E._row_sources(plain, "2026-11-25") == {"counts": {"release": 1}, "backfill_last_known": None,
                                                    "backfill_fetched": None}


def test_fixture_backfilled_series_carries_the_fetch_day():
    d = json.loads((COMMITTED / "series" / "g9_epoch_notable_models.json").read_text(encoding="utf-8"))
    assert d["rows"]["backfill_last_known"] < "2020-01-01"  # the rule day
    assert d["rows"]["backfill_fetched"] == str(SY.FETCHED.date())  # the day the rows carry the vintage of


@pytest.mark.real_data
@pytest.mark.skipif(not real_table_exists(), reason="no real observation table")
def test_real_backfill_boundary_is_the_fetch_day_for_every_backfilled_series():
    """The 41 of 105 cases of R-W1 3a: every publishable series with backfill gets max(rule day, fetch day) as its
    boundary, computed here independently from the table; series fetched long after their rule day exist."""
    ctx = M.Context(observations.load())
    today = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
    keys = [k for k, s in ctx.specs.items() if s.publish and G.publishable(k, ctx)]
    late = 0
    n = 0
    for k in keys:
        rows = ctx.rows(k)
        b = rows[(rows["source"] == "backfill") & (rows["known_from"] <= today)]
        if b.empty:
            continue
        n += 1
        out = E._row_sources(rows, today)
        fetched = pd.to_datetime(b["fetched_at"]).max().ceil("D")
        assert out["backfill_fetched"] == str(fetched.date()), k
        if fetched - b["known_from"].max() > pd.Timedelta(days=7):
            late += 1
    assert n > 0 and late > 0, (n, late)


# ------------------------------------------------------------------ 4a: the commit of each live forecast file


def _git(cwd: Path, *args: str, date: str | None = None) -> str:
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.invalid", "HOME": str(cwd), "PATH": "/usr/bin:/bin:/usr/local/bin"}
    if date:
        env |= {"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout


def test_file_commit_is_the_commit_that_added_the_file(tmp_path):
    _git(tmp_path, "init", "-q")
    f = tmp_path / "forecasts" / "n2" / "2026-09.json"
    f.parent.mkdir(parents=True)
    f.write_text("{}", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "add", date="2026-10-05T08:41:12+02:00")
    sha = _git(tmp_path, "rev-parse", "HEAD").strip()
    f.write_text('{"x": 1}', encoding="utf-8")  # a later change is not the timestamp
    _git(tmp_path, "commit", "-qam", "change", date="2026-10-20T10:00:00+00:00")
    assert E.file_commit(f) == {"sha": sha, "date": "2026-10-05T06:41:12Z"}
    new = f.with_name("2026-10.json")
    new.write_text("{}", encoding="utf-8")
    assert E.file_commit(new) is None  # not committed
    outside = tmp_path.parent / f"{tmp_path.name}_nogit" / "f.json"
    outside.parent.mkdir()
    outside.write_text("{}", encoding="utf-8")
    assert E.file_commit(outside) is None  # not in git


def test_every_live_file_in_the_fixtures_has_its_commit_before_the_outcome():
    """Every scored live forecast: the commit that added the file is dated before the outcome's known_from."""
    checked = 0
    for p in sorted((COMMITTED / "nowcast").glob("n*.json")):
        n = json.loads(p.read_text(encoding="utf-8"))
        commits = {f["period"]: f.get("commit") for f in n.get("forecasts") or []}
        for f in n.get("forecasts") or []:
            assert f["commit"] is not None and len(f["commit"]["sha"]) == 40, (p.name, f["file"])
        for r in n.get("scorecard") or []:
            if r.get("status") == "utfall":
                c = commits[r["period"]]
                assert c["date"][:10] < r["known_from"][:10], (p.name, r["period"], c, r["known_from"])
                checked += 1
    assert checked >= 1
    d2 = json.loads((COMMITTED / "nowcast" / "d2.json").read_text(encoding="utf-8"))
    assert d2["commit"]["date"][:10] <= d2["origin"] < "2027"
    assert E.commit_violations([json.loads((COMMITTED / "nowcast" / "n2.json").read_text(encoding="utf-8"))]) == []


def test_a_forecast_committed_on_or_after_its_outcome_stops_the_build(tmp_path):
    ctx = SY.context(tmp_path)
    paths = SY.write_inputs(tmp_path, ctx)
    late = {"sha": "a" * 40, "date": "2026-10-14T05:00:00Z"}  # the N2 outcome is known from 2026-10-14

    with pytest.raises(E.CommitError, match="n2 2026-09"):
        E.assemble(ctx, today=SY.TODAY, history_from="2026-09", calibration={}, series=[],
                   commits=lambda p: dict(late), **paths)
    # without git history the build goes on; the file is shown as waiting for verification
    docs = E.assemble(ctx, today=SY.TODAY, history_from="2026-09", calibration={}, series=[],
                      commits=lambda p: None, **paths)
    assert docs["nowcast/n2.json"]["forecasts"][0]["commit"] is None
    assert docs["nowcast/d2.json"]["commit"] is None


def test_pages_workflows_check_out_the_full_history():
    import yaml

    for name in ("pages.yml", "pages-next.yml"):
        wf = yaml.safe_load((REPO / ".github" / "workflows" / name).read_text(encoding="utf-8"))
        cos = [s for j in wf["jobs"].values() for s in j.get("steps", [])
               if str(s.get("uses", "")).startswith("actions/checkout")]
        assert cos, name
        for s in cos:
            assert (s.get("with") or {}).get("fetch-depth") == 0, name


# ------------------------------------------------------------------ 1b: the scan covers the built site and web/src


def _fake_build(root: Path, html: str = "", data_js: str = "", node: list | None = None) -> Path:
    b = root / "build"
    (b / "data").mkdir(parents=True)
    (b / "data" / "manifest.json").write_text(json.dumps({"synthetic": True}), encoding="utf-8")
    (b / "_app" / "immutable" / "chunks").mkdir(parents=True)
    (b / "_app" / "immutable" / "chunks" / "holdout.js").write_text(data_js or 'const H=[{series:"rpo_hyp4"}];',
                                                                   encoding="utf-8")
    (b / "gren" / "G9").mkdir(parents=True)
    (b / "gren" / "G9" / "index.html").write_text(html or "<p>ok</p>", encoding="utf-8")
    flat = node or [{"withheld": 1, "counted": 4}, [2], {"key": 3}, SY.WITHHELD[0], []]
    (b / "gren" / "G9" / "__data.json").write_text(json.dumps({"type": "data", "nodes": [
        {"type": "skip"}, {"type": "data", "data": flat, "uses": {}}]}), encoding="utf-8")
    return b


def test_scan_build_passes_withheld_lists_and_catches_a_planted_constant(tmp_path):
    from ai_tracker.site_bundle import scan_build as SB

    key, label = SY.WITHHELD[0], SY.specs()[SY.WITHHELD[0]].label
    inline = ('<script>data:{branch:{withheld:[{key:"%s",label:"a ] in [a string",why:"x"}],counted:[]}}</script>'
              '<li><span class="name">%s</span></li>' % (key, label))
    assert SB.scan_build(_fake_build(tmp_path / "ok", html=inline)) == []
    # a constant written into web/src ends up in a compiled chunk
    bad = SB.scan_build(_fake_build(tmp_path / "js", data_js=f'const HOLDOUT=[{{series:"{key}",v:1.2}}];'))
    assert len(bad) == 1 and "holdout.js" in bad[0] and key in bad[0]
    bad = SB.scan_build(_fake_build(tmp_path / "lab", data_js=f'const T="{label}";'))
    assert len(bad) == 1 and "withheld label" in bad[0]
    # inline page data outside a withheld list, and load data (devalue) outside a withheld list
    bad = SB.scan_build(_fake_build(tmp_path / "html", html=inline.replace("counted:[]", f'counted:["{key}"]')))
    assert len(bad) == 1 and "index.html" in bad[0]
    bad = SB.scan_build(_fake_build(tmp_path / "node", node=[{"withheld": 1, "counted": 3}, [], key, [2]]))
    assert len(bad) == 1 and "__data.json" in bad[0]
    assert SB.scan_build(tmp_path / "empty") != []  # nothing built is not clean


def test_scan_src_catches_a_key_in_a_hand_written_constant(tmp_path):
    from ai_tracker.site_bundle import scan_build as SB

    src = tmp_path / "src" / "lib" / "regime"
    src.mkdir(parents=True)
    (src / "holdout.ts").write_text("export const HOLDOUT = [{ series: 'rpo_hyp4' }];\n", encoding="utf-8")
    (src / "reconciliations.json").write_text('[{"a": "rev_aws"}]', encoding="utf-8")
    assert SB.scan_src(tmp_path / "src") == []
    (src / "reconciliations.json").write_text('[{"a": "g9_arxiv_cs_lg"}]', encoding="utf-8")
    bad = SB.scan_src(tmp_path / "src")
    assert len(bad) == 1 and "reconciliations.json" in bad[0]


def test_the_web_sources_hold_no_withheld_key_or_label():
    from ai_tracker.site_bundle import scan_build as SB

    assert SB.scan_src(REPO / "web" / "src") == []


def test_strip_withheld_lists_respects_strings_and_nesting():
    from ai_tracker.site_bundle import scan_build as SB

    t = 'a,withheld:[{k:"x]",l:[1,[2]],s:\'y\\\'[\'}],b:"after"'
    assert SB.strip_withheld_lists(t) == 'a,,b:"after"'
    assert SB.strip_withheld_lists('"withheld": [{"key": "x"}], "z": 1') == ', "z": 1'


def test_pages_next_scans_the_build_after_building():
    import yaml

    steps = yaml.safe_load((REPO / ".github" / "workflows" / "pages-next.yml").read_text(encoding="utf-8"))["jobs"]["web"]["steps"]
    runs = [s.get("run", "") for s in steps]
    i_build = next(i for i, r in enumerate(runs) if r.strip() == "npm run build")
    i_scan = next(i for i, r in enumerate(runs) if "ai_tracker.site_bundle scan-build" in r)
    i_up = next(i for i, s in enumerate(steps) if (s.get("with") or {}).get("name") == "web-next")
    assert i_build < i_scan < i_up
    assert "--src" in runs[i_scan] and not steps[i_scan].get("if") and not steps[i_scan].get("continue-on-error")
    py = [s for s in steps if str(s.get("uses", "")).startswith("actions/setup-python")]
    assert py and not py[0].get("if"), "Python is set up for the fixtures run too"
