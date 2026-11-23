"""Tests for the public site (ai_tracker.site): pages, licence rule, record labelling, external hosts. No network."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import pytest

from ai_tracker import catalog, observations
from ai_tracker.site import build as B
from ai_tracker.site import data as D
from ai_tracker.state import measures as M
from ai_tracker.state import snapshot as S

FETCHED = pd.Timestamp("2026-11-23")
TODAY = "2026-11-23"
SECRET = "zz_secret_series"  # publish=False, a core series of G9: must never reach the output with data
PUBLIC = ["pub_a", "pub_b", "pub_c"]


def spec(key, branch, publish=True, license="CC BY 4.0 (test)"):
    return catalog.Spec(key=key, branch=branch, label=f"Etikett {key}", unit="MUSD", freq="M", source=f"Testkälla {branch}",
                        fetch=lambda: pd.Series(dtype=float), lag_days=10, license=license, publish=publish,
                        question=f"Fråga {key}?")


def monthly(key, seed, start="2012-01", end="2026-09"):
    rng = np.random.default_rng(seed)
    periods = pd.period_range(start, end, freq="M")
    values = 100 * np.exp(np.cumsum(0.01 + 0.02 * rng.standard_normal(len(periods))))
    return pd.DataFrame({"series": key, "freq": "M", "period": [str(p) for p in periods], "value": values,
                         "known_from": pd.DatetimeIndex(periods.end_time.normalize()) + pd.Timedelta(days=10),
                         "source": "release", "fetched_at": FETCHED})


def make_ctx(tmp_path) -> M.Context:
    specs = [spec(k, "G6") for k in PUBLIC] + [spec(SECRET, "G9", publish=False, license="unverified: test"),
                                               spec("pub_g9", "G9"), spec("pub_g9b", "G9"),
                                               spec("tsmc_revenue_m", "G6")]
    table = pd.concat([monthly(s.key, i) for i, s in enumerate(specs)], ignore_index=True)
    return M.Context(table, specs={s.key: s for s in specs}, derived={},
                     core={"G6": list(PUBLIC), "G9": [SECRET, "pub_g9", "pub_g9b"]},
                     forecasts=tmp_path / "forecasts", selection=lambda when: [])


def write_forecast(root: Path):
    d = root / "n2"
    d.mkdir(parents=True, exist_ok=True)
    (d / "2026-09.json").write_text(json.dumps({
        "nowcast": "N2", "target": "tsmc_revenue_m", "month": "2026-09", "origin": "2026-10-05", "champion": "B2",
        "value": 400.0, "variants": {"B0": 390.0, "B1": 395.0, "V1": 396.0, "B2": 400.0},
        "inputs": [{"series": SECRET, "period": "2026-08", "value": 1.0, "known_from": "2026-09-10"}],
    }), encoding="utf-8")


def build_site(tmp_path, live: bool = False) -> Path:
    ctx = make_ctx(tmp_path)
    snaps = tmp_path / "snapshots"
    snaps.mkdir(exist_ok=True)
    if live:  # a committed live snapshot, built by the real writer's build() on the same context
        snap = S.build("2026-10-31", ctx=ctx)
        (snaps / "2026-10.json").write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    write_forecast(tmp_path / "forecasts")
    site = tmp_path / "site"
    B.build(site, ctx=ctx, snapshots_dir=snaps, forecasts_dir=tmp_path / "forecasts", today=TODAY,
            history_from="2026-05", checks=False, letters_dir=tmp_path / "letters")
    return site


@pytest.fixture(scope="module")
def recon_site(tmp_path_factory):
    return build_site(tmp_path_factory.mktemp("recon"))


@pytest.fixture(scope="module")
def live_site(tmp_path_factory):
    return build_site(tmp_path_factory.mktemp("live"), live=True)


def load(site: Path, name: str) -> dict:
    return json.loads((site / "data" / f"{name}.json").read_text(encoding="utf-8"))


def all_json(site: Path) -> dict[str, object]:
    return {str(p.relative_to(site)): json.loads(p.read_text(encoding="utf-8")) for p in site.rglob("*.json")}


def strip_withheld(x):
    """Every JSON value except the `withheld` lists (the one place a withheld series may be named)."""
    if isinstance(x, dict):
        return {k: strip_withheld(v) for k, v in x.items() if k != "withheld"}
    if isinstance(x, list):
        return [strip_withheld(v) for v in x]
    return x


def withheld_lists(x):
    if isinstance(x, dict):
        for k, v in x.items():
            if k == "withheld":
                yield v
            else:
                yield from withheld_lists(v)
    elif isinstance(x, list):
        for v in x:
            yield from withheld_lists(v)


# ------------------------------------------------------------------ pages


def test_build_produces_every_page_and_data_file(recon_site):
    pages = ["index.html", "prognoser.html", "metod.html"] + [f"gren-{c.lower()}.html" for c in catalog.BRANCHES]
    for p in pages:
        html = (recon_site / p).read_text(encoding="utf-8")
        assert html.startswith("<!doctype html>") and '<html lang="sv">' in html and "<title>" in html, p
        assert "inte investeringsrådgivning" in html, p
    for name in ["oversikt", "prognoser", "metod", "build"] + [f"gren/{c}" for c in catalog.BRANCHES]:
        assert (recon_site / "data" / f"{name}.json").is_file(), name
    assert (recon_site / "assets" / "style.css").is_file() and (recon_site / "assets" / "app.js").is_file()
    assert (recon_site / ".nojekyll").is_file()
    # the start page has the nine tiles and links every branch page
    index = (recon_site / "index.html").read_text(encoding="utf-8")
    for c in catalog.BRANCHES:
        assert f'href="gren-{c.lower()}.html"' in index


def test_reconstructed_record_is_labelled_until_the_first_live_snapshot(recon_site):
    ov = load(recon_site, "oversikt")
    assert ov["record"]["kind"] == "rekonstruerad" and ov["record"]["label"] == D.RECON_LABEL
    assert ov["record"]["date"] == "2026-10-31" and ov["record"]["first_live_date"] == "2026-11-30"
    assert all(h["kind"] == "rekonstruerad" for t in ov["branches"] for h in t["history"])
    for p in ["index.html", "gren-g6.html"]:
        assert "Rekonstruerad historik, inte ett skarpt underlag" in (recon_site / p).read_text(encoding="utf-8")


def test_live_snapshot_is_the_record_and_earlier_months_stay_reconstructed(live_site):
    ov = load(live_site, "oversikt")
    assert ov["record"]["kind"] == "skarp" and ov["record"]["file"] == "snapshots/2026-10.json"
    g6 = next(t for t in ov["branches"] if t["code"] == "G6")
    kinds = {h["month"]: h["kind"] for h in g6["history"]}
    assert kinds["2026-10"] == "skarp" and kinds["2026-09"] == "rekonstruerad"
    assert g6["previous"]["month"] == "2026-09" and g6["previous"]["kind"] == "rekonstruerad"
    assert "Skarp ögonblicksbild" in (live_site / "index.html").read_text(encoding="utf-8")


def test_branch_page_has_series_measures_known_from_and_chart_data(recon_site):
    g6 = load(recon_site, "gren/G6")
    assert g6["n_series"] == 3 and len(g6["counted"]) == 3 and not g6["withheld"]
    s = g6["counted"][0]
    for k in ("latest_period", "known_from", "pace", "change_in_pace", "direction", "source", "license", "path"):
        assert k in s, k
    assert s["latest_period"] == "2026-09" and s["known_from"] == "2026-10-10"
    assert s["path"]["periods"][-1] == "2026-09" and s["path"]["pace"][-1] == pytest.approx(s["pace"], rel=1e-4)
    html = (recon_site / "gren-g6.html").read_text(encoding="utf-8")
    assert 'data-chart="pace" data-key="pub_a"' in html and 'data-chart="change" data-key="pub_a"' in html
    assert "Källa: Testkälla G6" in html  # every chart cites its source


def test_nowcast_page_shows_champion_shadows_and_scorecard_without_inputs(recon_site):
    doc = load(recon_site, "prognoser")
    n2 = next(n for n in doc["nowcasts"] if n["id"] == "n2")
    assert n2["champion"] == "B2" and set(n2["shadows"]) == {"B0", "B1", "V1", "B3"}  # B3: step-2 shadow (C2)
    assert n2["forecasts"][0]["value"] == 400.0 and "inputs" not in n2["forecasts"][0]
    assert n2["scorecard"][0]["status"] == "utfall" and n2["next_origin"] == "2026-12-05"
    n1 = next(n for n in doc["nowcasts"] if n["id"] == "n1")
    assert n1["forecasts"] == [] and n1["next_origin"] == "2027-01-20"
    assert "Inga skarpa prognoser än." in (recon_site / "prognoser.html").read_text(encoding="utf-8")


# ------------------------------------------------------------------ licences


@pytest.mark.parametrize("which", ["recon_site", "live_site"])
def test_withheld_series_never_appear_in_output_json(which, request):
    site = request.getfixturevalue(which)
    docs = all_json(site)
    assert SECRET not in json.dumps(strip_withheld(docs), ensure_ascii=False)
    lists = [w for d in docs.values() for lst in withheld_lists(d) for w in lst]
    assert lists, "the withheld series must be named"
    for w in lists:
        assert set(w) <= {"key", "label", "source", "license", "why", "counted", "branch"}
    # the branch counts it (aggregate only) and says so
    g9 = load(site, "gren/G9")
    assert g9["n_withheld_counted"] == 1 and [w["key"] for w in g9["withheld"]] == [SECRET]
    assert g9["n_series"] == 3 and len(g9["counted"]) == 2


@pytest.mark.parametrize("which", ["recon_site", "live_site"])
def test_withheld_series_only_named_in_the_withheld_section_of_the_html(which, request):
    site = request.getfixturevalue(which)
    for p in site.glob("*.html"):
        html = re.sub(r'<section id="withheld".*?</section>', "", p.read_text(encoding="utf-8"), flags=re.S)
        assert SECRET not in html, p.name


def test_publishable_and_licence_labels():
    ctx = M.Context(observations._empty())
    assert D.publishable("capex_ocf_hyp4", ctx)  # derived from two published SEC series
    assert not D.publishable("g9_arxiv_cs_ai", ctx) and not D.publishable(None, ctx)
    assert all(D.publishable(s.key, ctx) == s.publish for s in catalog.ALL)
    assert D.short_license("unverified: arXiv ...") == "inte kontrollerad"
    assert D.short_license("CC BY 4.0 (Epoch AI README ...)") == "CC BY 4.0"
    assert D.short_license("public: 'Information presented on sec.gov ...'") == "offentlig information (SEC)"
    assert D.short_license("US federal work, free under 17 U.S.C. § 105") == "public domain (amerikansk myndighet)"


# ------------------------------------------------------------------ external hosts and checks

URL = re.compile(r"""https?://[^\s"'<>)]+""")
LOADS = [re.compile(r"""<script[^>]*\bsrc=["']([^"']+)"""), re.compile(r"""<link[^>]*\bhref=["']([^"']+)"""),
         re.compile(r"""<(?:img|iframe|source|video|audio)[^>]*\bsrc=["']([^"']+)"""),
         re.compile(r"""url\(\s*["']?([^"')]+)"""), re.compile(r"""@import\s+["']([^"']+)"""),
         re.compile(r"""fetch\(\s*["']([^"']+)""")]


def test_no_external_host_other_than_the_allowed_one(recon_site):
    for p in [*recon_site.glob("*.html"), *(recon_site / "assets").iterdir()]:
        text = p.read_text(encoding="utf-8")
        for pat in LOADS:  # resources the browser loads: relative, or the one allowed CDN
            for ref in pat.findall(text):
                host = urlparse(ref).netloc
                assert not host or host in B.ALLOWED_EXTERNAL_HOSTS, (p.name, ref)
        for url in URL.findall(text):  # any other absolute URL may only be a link to the repository
            host = urlparse(url).netloc
            assert host in B.ALLOWED_EXTERNAL_HOSTS | {"github.com"} or url == "http://www.w3.org/2000/svg", (p.name, url)


def test_failed_warehouse_checks_stop_the_build(tmp_path):
    ctx = make_ctx(tmp_path)  # synthetic series are not in the catalog: series_in_catalog fails
    with pytest.raises(B.ChecksFailed):
        B.build(tmp_path / "site", ctx=ctx, snapshots_dir=tmp_path, forecasts_dir=tmp_path, today=TODAY)
    assert not (tmp_path / "site").exists()


def test_measure_path_ends_in_the_measure(tmp_path):
    ctx = make_ctx(tmp_path)
    m, path = M.measure_path("pub_a", "2026-10-31", ctx)
    assert m == M.measure("pub_a", "2026-10-31", ctx)
    assert path.index[-1] == m["latest_period"]
    assert path["pace"].iloc[-1] == pytest.approx(m["pace"]) and path["change"].iloc[-1] == pytest.approx(m["change_in_pace"])


def test_pages_workflow_follows_the_data_jobs_and_deploys_only_after_the_build():
    import yaml

    wf_dir = Path(__file__).resolve().parents[1] / ".github" / "workflows"
    names = {yaml.safe_load(p.read_text(encoding="utf-8"))["name"] for p in wf_dir.glob("*.yml")}
    wf = yaml.safe_load((wf_dir / "pages.yml").read_text(encoding="utf-8"))
    on = wf.get("on", wf.get(True))  # PyYAML reads the key `on` as True
    assert set(on["workflow_run"]["workflows"]) == {"Weekly data fetch", "Monthly snapshot", "Live nowcasts"}
    assert set(on["workflow_run"]["workflows"]) <= names and "workflow_dispatch" in on
    steps = wf["jobs"]["build"]["steps"]
    cache = next(s for s in steps if s.get("uses", "").startswith("actions/cache/restore"))
    assert cache["with"]["restore-keys"] == "ai-data-"
    assert any("ai_tracker.site build" in s.get("run", "") and "--skip-checks" not in s.get("run", "") for s in steps)
    assert wf["jobs"]["deploy"]["needs"] == "build"
    assert any(s.get("uses", "").startswith("actions/deploy-pages") for s in wf["jobs"]["deploy"]["steps"])
