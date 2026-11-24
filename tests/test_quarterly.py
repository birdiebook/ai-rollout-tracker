"""Tests for the quarterly report (ai_tracker.quarterly): determinism, labels, refusal, content from the snapshots,
flow per lead, forecasts with baselines and champion changes, the regime section, data and method, licence rule,
neutral wording, publishing, the workflow hook and the site page. Fixtures only, no network."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from ai_tracker import catalog, config, letter as L, pipeline, quarterly as Q
from ai_tracker.site import build as B
from ai_tracker.state import measures as M
from ai_tracker.state import snapshot as S

FETCHED = pd.Timestamp("2026-10-20")
TODAY = "2026-11-23"
QUARTER = "2026Q3"
MONTHS = ["2026-07", "2026-08", "2026-09"]
SECRET = "zz_secret_series"  # publish=False, core series of G9
SECRET_LABEL = "Hemlig etikett zz"
PUBLIC = ["pub_a", "pub_b", "pub_c"]
RATIO = "x_rpo_cover"


def spec(key, branch, publish=True, freq="M", label=None, license="CC BY 4.0 (test)"):
    return catalog.Spec(key=key, branch=branch, label=label or f"Etikett {key}", unit="MUSD", freq=freq,
                        source=f"Testkälla {branch}", fetch=lambda: pd.Series(dtype=float), lag_days=10,
                        license=license, publish=publish, question=f"Fråga {key}?")


def monthly(key, seed, end="2026-09", scale=100.0):
    rng = np.random.default_rng(seed)
    periods = pd.period_range("2012-01", end, freq="M")
    values = scale * np.exp(np.cumsum(0.01 + 0.02 * rng.standard_normal(len(periods))))
    return pd.DataFrame({"series": key, "freq": "M", "period": [str(p) for p in periods], "value": values,
                         "known_from": pd.DatetimeIndex(periods.end_time.normalize()) + pd.Timedelta(days=10),
                         "source": "release", "fetched_at": FETCHED})


def quarterly_rows(key, seed, end="2026Q2"):
    rng = np.random.default_rng(seed)
    periods = pd.period_range("2012Q1", end, freq="Q")
    values = 3.0 * np.exp(np.cumsum(0.02 * rng.standard_normal(len(periods))))
    return pd.DataFrame({"series": key, "freq": "Q", "period": [str(p) for p in periods], "value": values,
                         "known_from": pd.DatetimeIndex(periods.end_time.normalize()) + pd.Timedelta(days=30),
                         "source": "release", "fetched_at": FETCHED})


def make_ctx(tmp_path) -> M.Context:
    specs = [spec(k, "G6") for k in PUBLIC] + [
        spec(SECRET, "G9", publish=False, label=SECRET_LABEL, license="unverified: test"),
        spec("pub_g9", "G9"), spec("pub_g9b", "G9"), spec("tsmc_revenue_m", "G6"),
        spec(RATIO, "G4", freq="Q", label="RPO-täckning (test)")]
    parts = [monthly(s.key, i, scale=1000.0 if s.key == SECRET else 100.0) for i, s in enumerate(specs[:-1])]
    parts.append(quarterly_rows(RATIO, 42))
    table = pd.concat(parts, ignore_index=True)
    rev = table[(table["series"] == "pub_a") & (table["period"] == "2026-03")].copy()
    rev["value"] *= 1.05
    rev["known_from"] = pd.Timestamp("2026-08-15")
    table = pd.concat([table, rev], ignore_index=True)
    return M.Context(table, specs={s.key: s for s in specs}, derived={},
                     core={"G6": list(PUBLIC), "G9": [SECRET, "pub_g9", "pub_g9b"]},
                     forecasts=tmp_path / "forecasts", selection=lambda when: [], reconciliations=[RATIO])


def write_forecasts(root: Path):
    d = root / "n2"
    d.mkdir(parents=True, exist_ok=True)
    common = {"nowcast": "N2", "target": "tsmc_revenue_m", "unit": "mn TWD"}
    files = {"2026-05": ("2026-06-05", "B2", 400.0), "2026-07": ("2026-08-05", "B2", 410.0),
             "2026-08": ("2026-09-05", "B3", 420.0), "2026-09": ("2026-10-05", "B3", 777.0)}
    for month, (origin, champ, value) in files.items():
        (d / f"{month}.json").write_text(json.dumps({
            **common, "month": month, "origin": origin, "champion": champ, "value": value,
            "variants": {"B0": value - 10, "B1": value - 5, "V1": value - 4, "B2": value - 1, "B3": value},
            "inputs": [{"series": SECRET, "period": "2026-05", "value": 1.0}]}), encoding="utf-8")


def write_docs(root: Path) -> Path:
    (root / "steg2").mkdir(parents=True)
    (root / "granskning").mkdir()
    (root / "kallor").mkdir()
    (root / "steg2" / "plan.md").write_text(
        "| Led | Fråga | Gren | Läge | Nytt |\n|---|---|---|---|---|\n"
        "| **L4 Kontrakterad efterfrågan** | x | ny | Saknas | RPO |\n"
        "| **L6 Halvledare och minne** | x | G6 | TSMC | Nvidia |\n"
        "| **L9 Forskning och förväntningar** | x | G9 | arXiv | x |\n", encoding="utf-8")
    (root / "mattregister.md").write_text(
        "# Måttregister\n\n## 1. Mått\n\ntext\n\n## Ändringar\n\n"
        "### 2026-05-01 – Före kvartalet\n\nx\n\n"
        "### 2026-08-01 – Testserie läggs till (före analys)\n\n| Nyckel | Definition | Led |\n|---|---|---|\n"
        f"| `{RATIO}` | rpo / capex | L4–L6 |\n\n"
        "### 2026-11-01 – Efter kvartalet\n\nx\n", encoding="utf-8")
    (root / "beslutslogg.md").write_text(
        "# Beslutslogg\n\n## 2026-09-02 – B3 blir huvudmodell för N2 (efter R7)\n\nEfter granskningen R7 "
        "(`docs/granskning/r7_test.md`) byts huvudmodell.\n\n## 2026-09-03 – N1: inget byte\n\nx\n\n"
        "## 2026-12-01 – B4 blir huvudmodell för N2\n\nefter kvartalet\n", encoding="utf-8")
    (root / "granskning" / "r7_test.md").write_text(
        "# R7: oberoende granskning av B3 (test)\n\nGranskningsspår R7, 2026-09-01, på en gren.\n", encoding="utf-8")
    (root / "granskning" / "r1_old.md").write_text(
        "# R1: gammal granskning\n\nGranskningsspår R1, 2026-01-05.\n", encoding="utf-8")
    (root / "kallor" / "test.md").write_text(
        "# Källa\n\n| Källa | Värd | Status |\n|---|---|---|\n| Exempelkälla | `x.example` | **BLOCKED** |\n"
        "| Öppen källa | `y.example` | ok |\n\n## Annan källa (G6): BLOCKED av villkoren\n\n"
        "| 2026-11-23 | körning | Del B förklaras BLOCKED |\n", encoding="utf-8")
    return root


def write_snapshot(ctx, snaps: Path, month: str, regime: dict | None = None) -> Path:
    snaps.mkdir(parents=True, exist_ok=True)
    doc = S.build(S.month_end(month), ctx=L.cut_context(ctx, S.month_end(month), None))
    if regime is not None:
        doc["regime"] = regime
    path = snaps / f"{month}.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


@pytest.fixture
def env(tmp_path):
    ctx = make_ctx(tmp_path)
    write_forecasts(tmp_path / "forecasts")
    return ctx, tmp_path / "snapshots", tmp_path / "forecasts", write_docs(tmp_path / "docs")


def live(env, regime: dict[str, dict] | None = None, months=MONTHS) -> str:
    ctx, snaps, fc, docs = env
    for m in months:
        if not (snaps / f"{m}.json").exists():
            write_snapshot(ctx, snaps, m, (regime or {}).get(m))
    return Q.report(QUARTER, ctx, snapshots_dir=snaps, forecasts_dir=fc, docs_dir=docs, today=TODAY)


def recon(env) -> str:
    ctx, snaps, fc, docs = env
    return Q.report(QUARTER, ctx, snapshots_dir=snaps, forecasts_dir=fc, docs_dir=docs, reconstructed=True,
                    today=TODAY)


def section(text: str, heading: str) -> str:
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def outside_withheld(text: str) -> str:
    return re.sub(r"^## Visas inte av licensskäl\n.*?(?=^## )", "", text, flags=re.S | re.M)


# ------------------------------------------------------------------ determinism, labels, refusal


def test_report_is_deterministic(env, tmp_path):
    ctx, snaps, fc, docs = env
    a = live(env)
    again = M.Context(ctx.table.sample(frac=1.0, random_state=3), specs=ctx.specs, derived={}, core=ctx.core,
                      forecasts=ctx.forecasts, selection=ctx.selection, reconciliations=ctx.reconciliations)
    assert Q.report(QUARTER, again, snapshots_dir=snaps, forecasts_dir=fc, docs_dir=docs, today=TODAY) == a
    p = Q.write(QUARTER, ctx, out_dir=tmp_path / "out", snapshots_dir=snaps, forecasts_dir=fc, docs_dir=docs,
                today=TODAY)
    first = p.read_bytes()
    Q.write(QUARTER, ctx, out_dir=tmp_path / "out", snapshots_dir=snaps, forecasts_dir=fc, docs_dir=docs, today=TODAY)
    assert p.read_bytes() == first and p.name == "2026Q3.md"


def test_live_report_is_labelled_from_the_snapshots(env):
    text = live(env)
    title = text.splitlines()[0]
    assert title == "# Läget i AI-utrullningen, tredje kvartalet 2026"
    assert Q.parse(text) == {"title": title[2:], "kind": "skarp"}
    for m in MONTHS:
        assert f"{m}: skarp `snapshots/{m}.json`" in text
    assert "Rekonstruerad, inte ett skarpt underlag" not in text
    assert "jämförelsemånaden 2026-06 (rekonstruerad)" in text  # no June snapshot: reconstructed and labelled
    assert "## Så läses rapporten" in text and "## Inte investeringsrådgivning" in text


def test_refuses_without_all_three_snapshots_unless_reconstructed(env, capsys, monkeypatch):
    ctx, snaps, fc, docs = env
    write_snapshot(ctx, snaps, "2026-07")
    with pytest.raises(Q.NoSnapshot, match="2026-08, 2026-09"):
        Q.report(QUARTER, ctx, snapshots_dir=snaps, forecasts_dir=fc, docs_dir=docs, today=TODAY)
    monkeypatch.setattr(Q.observations, "load", lambda: ctx.table)
    assert Q.main(["--quarter", QUARTER, "--snapshots-dir", str(snaps), "--forecasts-dir", str(fc), "--stdout"]) == 1
    assert "refused: no snapshot for 2026-08, 2026-09" in capsys.readouterr().err
    text = recon(env)  # mixed: July live, August and September reconstructed
    assert text.splitlines()[0].endswith("(rekonstruerad)")
    assert "Det finns ingen skarp ögonblicksbild för 2026-08, 2026-09." in text
    assert "2026-07: skarp `snapshots/2026-07.json`" in text and "2026-09: rekonstruerad vid 2026-09-30" in text
    assert "| 2026-06 (rekonstruerad) | 2026-07 | 2026-08 (rekonstruerad) | 2026-09 (rekonstruerad) |" in text
    for m in MONTHS[1:]:
        write_snapshot(ctx, snaps, m)
    with pytest.raises(ValueError, match="all three snapshots"):
        recon(env)
    with pytest.raises(ValueError, match="has not ended"):
        Q.report("2026Q4", ctx, snapshots_dir=snaps, forecasts_dir=fc, docs_dir=docs, reconstructed=True,
                 today=TODAY)


def test_states_come_from_the_snapshot_files(env):
    ctx, snaps, fc, docs = env
    p = write_snapshot(ctx, snaps, "2026-08")
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["branches"]["G6"]["state"], doc["branches"]["G6"]["index"] = "testtillstånd", 0.123
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    text = live(env)
    summ = section(text, "Sammanfattning")
    row = next(x for x in summ.splitlines() if x.startswith("| G6 "))
    assert "0,12 testtillstånd" in row
    assert "testtillstånd (2026-08)" in summ  # two state changes in the quarter are listed month by month
    assert re.search(r"- G6 Utbud och halvledare: .*testtillstånd.*\(index .*0,12", section(text, "Flödet"))


# ------------------------------------------------------------------ content


def test_summary_table_and_diffusion_path(env):
    text = live(env)
    summ = section(text, "Sammanfattning")
    assert "| Gren | 2026-06 (rekonstruerad) | 2026-07 | 2026-08 | 2026-09 | Över kvartalet |" in summ
    assert sum(1 for x in summ.splitlines() if re.match(r"\| G\d ", x)) == len(catalog.BRANCHES)
    assert "Läget vid kvartalets slut, 2026-09:" in summ
    assert "Prognoser: 2 nya skarpa prognoser och" in summ and "Regim: inget regimavsnitt" in summ


def test_flow_per_lead_with_reconciliation_ratio(env):
    flow = section(live(env), "Flödet")
    assert "### L4 Kontrakterad efterfrågan (ingen egen gren)" in flow
    assert "### L6 Halvledare och minne (G6)" in flow and "### L9 Forskning och förväntningar (G9)" in flow
    l4 = flow.split("### L4", 1)[1].split("### ", 1)[0]
    assert f"RPO-täckning (test) (`{RATIO}`) | L4–L6 | 2026Q2 |" in l4
    assert f"`{RATIO}`" in flow.split("### L6", 1)[1].split("### ", 1)[0]  # both ends of the ratio
    assert "Inga registrerade avstämningar för ledet." in flow.split("### L9", 1)[1]


def test_lead_and_ratio_tables_parse_from_the_real_docs():
    inp = type("I", (), {"docs": config.REPO / "docs"})()
    ld = Q.leads(inp)
    assert list(ld) == [f"L{i}" for i in range(1, 10)] and ld["L4"][1] == [] and ld["L7"][1] == ["G7", "G5"]
    assert ld == {k: (v[0], v[1]) for k, v in Q.LEADS_FALLBACK.items()}
    assert Q.ratio_leads(inp) == Q.RATIO_LEADS_FALLBACK


def test_forecasts_vs_outcomes_baselines_and_champion_change(env):
    ctx = env[0]
    fc = section(live(env), "Prognoser")
    n2 = fc.split("### N2", 1)[1].split("\n### ", 1)[0]
    assert "Nya skarpa prognoser i kvartalet (2):" in n2
    assert "- 2026-07 (prognosdag 2026-08-05, `forecasts/n2/2026-07.json`): huvudmodell B2 410 mn TWD" in n2
    assert "777" not in n2  # origin after the quarter
    out = ctx.table.loc[(ctx.table["series"] == "tsmc_revenue_m") & (ctx.table["period"] == "2026-07"), "value"]
    err = 100 * np.log(409.0 / float(out.iloc[0]))  # the champion's error: the file's B2 variant
    assert f"känt 2026-08-10, fel huvudmodell (B2) {L.n(err, 2, signed=True)}" in n2
    assert "Rullande utvärdering, alla 3 utfall av 3 prognoser kända till och med 2026-09-30" in n2
    assert "| B0 (naiv baslinje) | 3 |" in n2 and "| B2 (bolagens guidance) | 3 |" in n2
    assert "MAE − MAE B0" in n2 and "kan skillnaderna mellan varianterna och mot baslinjen vara slump" in n2
    assert "- I prognosfilerna från prognosdag 2026-09-05 (`forecasts/n2/2026-08.json`): B2 → B3." in n2
    assert ("- Beslut 2026-09-02 – B3 blir huvudmodell för N2 (efter R7) (`docs/beslutslogg.md`). Granskning: "
            "`docs/granskning/r7_test.md`.") in n2
    assert "B4" not in n2  # decision dated after the quarter
    n1 = fc.split("### N1", 1)[1].split("\n### ", 1)[0]
    assert "Inget byte av huvudmodell i kvartalet" in n1  # "N1: inget byte" names no champion
    assert "inputs" not in fc and SECRET not in fc


def test_regime_absent_renders_gracefully(env):
    rg = section(live(env), "Regim")
    assert "har inget regimavsnitt (C4)" in rg and "Ingen sannolikhet för inbromsning" in rg


def _regime(p_capex, p_demand, bocpd=()):
    return {"spec_version": "c4-v1",
            "ms": {"capex": {"p_slow": p_capex, "n_months": 80, "reason": ""},
                   "demand": {"p_slow": p_demand, "n_months": 40 if p_demand is None else 80,
                              "reason": "40 månader faktorhistorik < 60" if p_demand is None else ""}},
            "bocpd": list(bocpd)}


def _b(series, branch, p, period):
    return {"branch": branch, "series": series, "freq": "M", "latest_period": period, "hazard": 1 / 36,
            "p_recent": p, "n_periods": 100, "reason": ""}


def test_regime_probabilities_shifts_and_breaks_from_stored_values(env):
    regime = {
        "2026-07": _regime(0.85, None, [_b("pub_a", "G6", 0.1, "2026-06")]),
        "2026-08": _regime(0.9, None, [_b("pub_a", "G6", 0.92, "2026-07"), _b(SECRET, "G9", 0.95, "2026-07")]),
        "2026-09": _regime(0.5, None, [_b("pub_a", "G6", 0.9, "2026-08")]),  # within 3 periods: no new break
    }
    text = live(env, regime)
    rg = section(text, "Regim")
    capex = next(x for x in rg.splitlines() if x.startswith("| capex och leverantörsled"))
    assert capex == ("| capex och leverantörsled | 0,85; expansion | 0,90; inbromsning | 0,50; inbromsning |")
    demand = next(x for x in rg.splitlines() if x.startswith("| efterfrågan"))
    assert "–; – (40 månader faktorhistorik < 60)" in demand
    assert "Rapporterade regimskiften i kvartalet: capex och leverantörsled: inbromsning från 2026-08." in rg
    assert "Rapporterade strukturbrott i kvartalet: 2:" in rg
    assert "2026-08: G6 Etikett pub_a (`pub_a`), senaste period 2026-07, P(körlängd ≤ 2) 0,92." in rg
    assert "Varav 1 i serier som inte visas av licensskäl." in rg and SECRET not in rg
    assert "1 rapporterat regimskifte, 2 rapporterade brott i kvartalet" in section(text, "Sammanfattning")


def test_data_and_method(env):
    dm = section(live(env), "Data och metod")
    assert "Revideringar som blev kända i kvartalet:" in dm and "Etikett pub_a (`pub_a`) 1" in dm
    assert "2026-09-01: R7: oberoende granskning av B3 (test) (`docs/granskning/r7_test.md`)" in dm
    assert "r1_old" not in dm
    assert "2026-08-01 – Testserie läggs till (före analys)" in dm
    assert "Före kvartalet" not in dm and "Efter kvartalet" not in dm
    assert "`docs/kallor/test.md`: Exempelkälla; Annan källa." in dm
    assert "Öppen källa" not in dm and "2026-11-23" not in dm


@pytest.mark.parametrize("kind", ["live", "recon"])
def test_withheld_series_only_in_the_withheld_list(env, kind):
    text = live(env) if kind == "live" else recon(env)
    rest = outside_withheld(text)
    assert SECRET not in rest and SECRET_LABEL not in rest
    withheld = section(text, "Visas inte av licensskäl")
    assert f"`{SECRET}`" in withheld and "i rapporten" in withheld


def test_neutral_wording(env):
    for text in (recon(env), live(env)):
        assert not L.BANNED_WORDS.search(text)
        assert re.search(r"\b(accelererar|stabil|bromsar in)\b", text)


# ------------------------------------------------------------------ publish, workflow, CLI, site


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


def test_publish_commits_the_report_with_the_snapshot(tmp_path):
    repo = tmp_path
    _git(repo, "init", "-q")
    (repo / "README").write_text("x")
    _git(repo, "add", "README")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "init")
    files = {"snapshots/2026-12.json": "{}\n", "docs/manadsbrev/2026-12.md": "# brev\n",
             "docs/kvartalsrapport/2026Q4.md": "# rapport\n"}
    for p, body in files.items():
        (repo / p).parent.mkdir(parents=True, exist_ok=True)
        (repo / p).write_text(body)
    assert pipeline.publish(list(files), repo)
    assert set(_git(repo, "show", "--name-only", "--format=", "HEAD").split()) == set(files)
    assert "Quarterly report 2026Q4" in _git(repo, "log", "-1", "--format=%s")
    assert not pipeline.publish(["docs/kvartalsrapport/2026Q4.md"], repo)  # unchanged
    (repo / "docs/kvartalsrapport/2026Q4.md").write_text("# rapport, omgenererad\n")
    assert pipeline.publish(["docs/kvartalsrapport/2026Q4.md"], repo)
    with pytest.raises(SystemExit, match="only forecasts"):
        pipeline.publish(["docs/kvartalsrapport/2026Q5.md"], repo)


def test_snapshot_workflow_writes_and_commits_the_report():
    wf = yaml.safe_load((config.REPO / ".github" / "workflows" / "snapshot.yml").read_text(encoding="utf-8"))
    steps = wf["jobs"]["snapshot"]["steps"]
    names = [s.get("name", "") for s in steps]
    i_letter = next(i for i, n in enumerate(names) if "monthly letter" in n.lower())
    i_report = next(i for i, n in enumerate(names) if "quarterly report" in n.lower() and n.startswith("Write"))
    i_commit = next(i for i, n in enumerate(names) if n.startswith("Commit"))
    assert i_letter < i_report < i_commit
    step = steps[i_report]
    assert 'python -m ai_tracker.quarterly --if-quarter-end "${SNAPSHOT_DATE:0:7}"' in step["run"]
    assert step.get("continue-on-error") is True and step["if"] == "steps.snap.outputs.written != ''"
    assert "--reconstructed" not in step["run"]
    commit = steps[i_commit]
    assert commit["env"]["REPORT"] == "${{ steps.report.outputs.report }}"
    assert '${REPORT:+"$REPORT"}' in commit["run"]


def test_if_quarter_end(capsys):
    assert Q.quarter_of_month_end("2026-09") == pd.Period("2026Q3") and Q.quarter_of_month_end("2026-11") is None
    assert Q.main(["--if-quarter-end", "2026-11"]) == 0
    assert "does not end a quarter" in capsys.readouterr().out


def test_site_lists_and_renders_reports(env, tmp_path):
    ctx, snaps, fc, docs = env
    reports = tmp_path / "reports"
    Q.write(QUARTER, ctx, out_dir=reports, snapshots_dir=snaps, forecasts_dir=fc, docs_dir=docs, reconstructed=True,
            today=TODAY)
    site = tmp_path / "site"
    B.build(site, ctx=ctx, snapshots_dir=snaps, forecasts_dir=fc, today=TODAY, history_from="2026-08", checks=False,
            letters_dir=tmp_path / "letters", reports_dir=reports)
    index = (site / "kvartalsrapport.html").read_text(encoding="utf-8")
    assert 'href="kvartalsrapport-2026q3.html"' in index and "Tredje kvartalet 2026" in index
    assert "(rekonstruerad)" in index
    assert 'href="kvartalsrapport.html"' in (site / "index.html").read_text(encoding="utf-8")
    page = (site / "kvartalsrapport-2026q3.html").read_text(encoding="utf-8")
    assert "<h1>Läget i AI-utrullningen, tredje kvartalet 2026 (rekonstruerad)</h1>" in page
    assert '<blockquote class="banner recon">' in page and "<table>" in page and "inte investeringsrådgivning" in page
    rest = re.sub(r'<section id="withheld".*?</section>', "", page, flags=re.S)
    assert SECRET not in rest and SECRET_LABEL not in rest and SECRET in page
    data = json.loads((site / "data" / "kvartalsrapport.json").read_text(encoding="utf-8"))
    assert [x["quarter"] for x in data["reports"]] == [QUARTER] and "markdown" not in data["reports"][0]
