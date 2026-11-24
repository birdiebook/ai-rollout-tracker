"""Tests for the flow page (E2) and the probabilities on the nowcast page (E4). Fixtures only, no network."""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import pytest

from ai_tracker import catalog
from ai_tracker.site import build as B
from ai_tracker.site import flow as F
from ai_tracker.site import probabilities as P
from ai_tracker.site import render as H
from ai_tracker.site import render_flow as RF
from ai_tracker.state import measures as M
from ai_tracker.state import snapshot as S

FETCHED = pd.Timestamp("2026-11-23")
TODAY = "2026-11-23"
SECRET_SERIES = "rpo_hyp4"  # withheld here (publish=False) although public in the real catalog
SECRET_RECON = "x_rpo_cover"
SECRET_BREAK = "zz_hidden_break"


def spec(key, branch, publish=True):
    return catalog.Spec(key=key, branch=branch, label=f"Etikett {key}", unit="MUSD", freq="M",
                        source=f"Testkälla {branch}", fetch=lambda: pd.Series(dtype=float), lag_days=10,
                        license="CC BY 4.0 (test)" if publish else "unverified: test", publish=publish,
                        question=f"Fråga {key}?")


def monthly(key, seed, start="2012-01", end="2026-09"):
    rng = np.random.default_rng(seed)
    periods = pd.period_range(start, end, freq="M")
    values = 100 * np.exp(np.cumsum(0.01 + 0.02 * rng.standard_normal(len(periods))))
    return pd.DataFrame({"series": key, "freq": "M", "period": [str(p) for p in periods], "value": values,
                         "known_from": pd.DatetimeIndex(periods.end_time.normalize()) + pd.Timedelta(days=10),
                         "source": "release", "fetched_at": FETCHED})


def make_ctx(tmp_path) -> M.Context:
    specs = [spec("rev_aws", "G4"), spec(SECRET_SERIES, "G4", publish=False), spec("capex_hyp4", "G5"),
             spec("debt_issued_hyp4", "G5"), spec("tsmc_revenue_m", "G6"),
             spec("x_capex_cloud", "G5"), spec(SECRET_RECON, "G5", publish=False), spec(SECRET_BREAK, "G6", publish=False)]
    table = pd.concat([monthly(s.key, i) for i, s in enumerate(specs)], ignore_index=True)
    return M.Context(table, specs={s.key: s for s in specs}, derived={},
                     core={"G4": ["rev_aws", SECRET_SERIES], "G5": ["capex_hyp4"], "G6": ["tsmc_revenue_m"]},
                     forecasts=tmp_path / "forecasts", selection=lambda when: [],
                     reconciliations=["x_capex_cloud", SECRET_RECON])


CAL = {"n1": {"available": True, "first": "2021Q3", "last": "2026Q3", "n_periods": 21, "best_baseline": "B1",
              "champion_mae": {"mae": 7.0, "n": 9, "first": "2024Q2", "last": "2026Q3"}, "error": None,
              "rows": [{"model": "B1", "n": 21, "coverage_50": 0.52, "band_50": [0.33, 0.67], "coverage_80": 0.81,
                        "band_80": [0.67, 0.95], "coverage_95": 0.95, "band_95": [0.86, 1.0], "crps": 4.93,
                        "calibrated": True},
                       {"model": "V1", "n": 1, "coverage_50": 1.0, "band_50": [0.0, 1.0], "coverage_80": 1.0,
                        "band_80": [0.0, 1.0], "coverage_95": 1.0, "band_95": [0.0, 1.0], "crps": 5.5,
                        "calibrated": True}]},
       "n2": {"available": False, "rows": [], "champion_mae": None, "error": "KeyError: x"}}

REGIME = {"spec_version": "c4-v1",
          "blocks": {"capex": {"p_slow": 0.91, "state": "inbromsning", "shift": "inbromsning", "n_months": 140},
                     "demand": {"p_slow": 0.04, "state": "expansion", "shift": None, "n_months": 70}},
          "breaks": [{"series": "tsmc_revenue_m", "branch": "G6", "latest_period": "2026-09", "p_recent": 0.86},
                     {"series": SECRET_BREAK, "branch": "G6", "latest_period": "2026-09", "p_recent": 0.9}]}


def build_site(tmp_path, live: bool = False, regime: bool = False):
    ctx = make_ctx(tmp_path)
    snaps = tmp_path / "snapshots"
    snaps.mkdir(exist_ok=True)
    if live:
        snap = S.build("2026-10-31", ctx=ctx)
        if regime:
            snap["regime"] = REGIME
        (snaps / "2026-10.json").write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    site = tmp_path / "site"
    B.build(site, ctx=ctx, snapshots_dir=snaps, forecasts_dir=tmp_path / "forecasts", today=TODAY,
            history_from="2026-08", checks=False, letters_dir=tmp_path / "letters", calibration=CAL)
    return site


@pytest.fixture(scope="module")
def recon_site(tmp_path_factory):
    return build_site(tmp_path_factory.mktemp("flow_recon"))


@pytest.fixture(scope="module")
def regime_site(tmp_path_factory):
    return build_site(tmp_path_factory.mktemp("flow_regime"), live=True, regime=True)


def load(site, name):
    return json.loads((site / "data" / f"{name}.json").read_text(encoding="utf-8"))


def strip_withheld(x):
    if isinstance(x, dict):
        return {k: strip_withheld(v) for k, v in x.items() if k != "withheld"}
    if isinstance(x, list):
        return [strip_withheld(v) for v in x]
    return x


# ------------------------------------------------------------------ flow page


def test_flow_page_is_built_and_linked_from_every_page(recon_site):
    html = (recon_site / "flode.html").read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>") and "<h1>Flödet</h1>" in html and 'data-src="data/flode.json"' in html
    for p in recon_site.glob("*.html"):
        assert 'href="flode.html"' in p.read_text(encoding="utf-8"), p.name
    # both chain diagrams are inline SVG with one linked node per lead
    assert html.count('class="flowmap ') == 2
    for i in range(1, 10):
        assert html.count(f'href="#l{i}"') == 2 and f'id="l{i}"' in html


def test_flow_doc_has_nine_leads_states_series_and_nowcasts(recon_site):
    doc = load(recon_site, "flode")
    assert [lead["code"] for lead in doc["leads"]] == [f"L{i}" for i in range(1, 10)]
    l5 = next(x for x in doc["leads"] if x["code"] == "L5")
    assert [b["code"] for b in l5["branches"]] == ["G5"]
    keys = [s["key"] for s in l5["series"]]
    assert keys == ["capex_hyp4", "debt_issued_hyp4"]  # capex_ocf_hyp4 is not in the fixture catalog
    capex = l5["series"][0]
    for k in ("level", "pace", "change_in_pace", "direction", "latest_period", "known_from", "path", "source"):
        assert k in capex, k
    assert capex["counted"] and capex["in_core"] and capex["branch"] == "G5"
    debt = l5["series"][1]
    assert not debt["in_core"] and not debt["counted"]  # measured, but outside the core lists
    # the nowcast falls back on the backtest summary when there is no live forecast
    n1 = l5["nowcasts"][0]
    assert n1["id"] == "n1" and n1["latest"] is None and n1["backtest"]["coverage_80"] == 0.81
    html = (recon_site / "flode.html").read_text(encoding="utf-8")
    assert "Ingen skarp prognos än." in html and "täckning för 80 %-intervallet 0,81" in html


def test_reconciliations_sit_between_the_leads_of_their_span(recon_site):
    doc = load(recon_site, "flode")
    cc = next(r for r in doc["reconciliations"] if r.get("key") == "x_capex_cloud")
    assert cc["span"] == [3, 5] and cc["short"] == "Capex / moln"
    assert {"level", "pace", "change_in_pace", "direction"} <= set(cc)
    html = (recon_site / "flode.html").read_text(encoding="utf-8")
    l4, l5 = html.index('id="l4"'), html.index('id="l5"')
    assert l4 < html.index("<code>x_capex_cloud</code>") < l5


def test_flow_never_leaks_withheld_series(recon_site):
    doc = load(recon_site, "flode")
    text = json.dumps(strip_withheld(doc), ensure_ascii=False)
    for k in (SECRET_SERIES, SECRET_RECON):
        assert k not in text
    assert {w["key"] for w in doc["withheld"]} == {SECRET_SERIES, SECRET_RECON}
    for w in doc["withheld"]:
        assert set(w) <= {"key", "label", "source", "license", "why", "counted", "branch"}
    hidden = next(r for r in doc["reconciliations"] if r.get("hidden"))
    assert set(hidden) == {"hidden", "span", "lead"}
    html = (recon_site / "flode.html").read_text(encoding="utf-8")
    rest = re.sub(r'<section id="withheld".*?</section>', "", html, flags=re.S)
    assert SECRET_SERIES not in rest and SECRET_RECON not in rest
    assert SECRET_SERIES in html  # named once, in the withheld list
    l4 = next(x for x in doc["leads"] if x["code"] == "L4")
    assert l4["n_withheld"] == 1 and l4["series"] == []


def test_flow_and_nowcast_pages_load_nothing_external(recon_site):
    url = re.compile(r"""https?://[^\s"'<>)]+""")
    for name in ("flode.html", "prognoser.html", "assets/app.js", "assets/style.css"):
        text = (recon_site / name).read_text(encoding="utf-8")
        for u in url.findall(text):
            assert urlparse(u).netloc in {"github.com"} or u == "http://www.w3.org/2000/svg", (name, u)
        assert not re.search(r"""<(script|link|img|iframe)[^>]*(src|href)=["']https?:""", text), name


def test_lead_spans_come_from_the_registered_reconciliations():
    assert F.lead_span("x_capex_cloud") == (3, 5) and F.lead_span("x_debt_capex") == (5, 5)
    assert F.lead_span("x_nvda_capex") == (5, 6) and F.lead_span("nope") is None
    # every registered reconciliation has a short label and lies on the chain
    from ai_tracker.state import register as R

    for k in R.RECONCILIATIONS:
        a, b = F.lead_span(k)
        assert 1 <= a <= b <= 9 and k in F.RECON_SHORT


def test_number_format_for_levels():
    assert RF.num_auto(9.4e25) == "9,40 × 10²⁵"
    assert RF.num_auto(2492700.0) == "2\u202f492\u202f700" and RF.num_auto(1.4412) == "1,44" and RF.num_auto(None) == "–"


# ------------------------------------------------------------------ E4: calibration and regime


def test_nowcast_page_shows_backtest_calibration_with_band_and_crps(recon_site):
    doc = load(recon_site, "prognoser")
    n1 = next(n for n in doc["nowcasts"] if n["id"] == "n1")
    assert n1["backtest_calibration"]["rows"][0]["band_80"] == [0.67, 0.95]
    html = (recon_site / "prognoser.html").read_text(encoding="utf-8")
    sec = html[html.index('id="n1"'):html.index('id="n2"')]
    assert "Kalibrering i backtest" in sec and 'class="calib"' in sec
    assert "0,81<br>" in sec and "[0,67–0,95]" in sec and "4,93" in sec
    assert "för få" in sec  # V1 with n = 1 gets no verdict
    sec2 = html[html.index('id="n2"'):html.index('id="n3"')]
    assert "backtesten kunde inte beräknas vid bygget" in sec2


def test_regime_placeholder_until_a_snapshot_has_it(recon_site):
    doc = load(recon_site, "prognoser")
    assert doc["regime"]["available"] is False
    html = (recon_site / "prognoser.html").read_text(encoding="utf-8")
    assert 'id="regim"' in html and "Inget skarpt värde än." in html


def test_regime_renders_probabilities_shifts_and_only_public_breaks(regime_site):
    reg = load(regime_site, "prognoser")["regime"]
    assert reg["available"] and reg["months"] == ["2026-10"]
    capex = next(b for b in reg["blocks"] if b["block"] == "capex")
    assert capex["latest"]["p_slow"] == 0.91 and capex["label"] == "capex och leverantörsled"
    assert reg["shifts"] == [{"month": "2026-10", "block": "capex", "label": "capex och leverantörsled",
                              "state": "inbromsning"}]
    assert [b["series"] for b in reg["breaks"]] == ["tsmc_revenue_m"] and reg["n_breaks_withheld"] == 1
    html = (regime_site / "prognoser.html").read_text(encoding="utf-8")
    assert "P(inbromsning)" in html and "0,91" in html and "Inget skarpt värde än." not in html
    assert SECRET_BREAK not in html and SECRET_BREAK not in json.dumps(reg)
    assert "1 brott i serier som inte visas av licensskäl" in html


def test_regime_view_accepts_the_c4_record_shape():
    live = {"2026-11": {"regime": {"ms": {"capex": {"p_slow": 0.3}}, "bocpd": [
        {"series": "a", "p_recent": 0.9, "break": True}, {"series": "b", "p_recent": 0.1, "break": False}]}}}
    reg = P.regime_view(live, lambda k: True)
    assert reg["blocks"][0]["latest"]["p_slow"] == 0.3 and [b["series"] for b in reg["breaks"]] == ["a"]
    assert P.regime_view({"2026-11": {"branches": {}}}, lambda k: True)["available"] is False


def test_backtest_calibration_never_raises_on_a_thin_table(tmp_path):
    ctx = make_ctx(tmp_path)
    out = P.backtest_calibration(ctx.table, only={"n3", "n4"})
    assert set(out) == {"n3", "n4"}
    for v in out.values():
        assert set(v) >= {"available", "rows", "error"}


def test_calibration_svg_draws_band_and_dot():
    row = CAL["n1"]["rows"][0]
    svg = H.calibration_svg(row, ["50", "80", "95"])
    assert svg.count('class="cband"') == 3 and svg.count('class="cdot"') == 3 and "<svg" in svg
