"""Tests for the monthly letter (ai_tracker.letter): determinism, labels, refusal, licence rule, nowcasts, data news,
publishing with the snapshot, the workflow hook and the site page. Fixtures only, no network."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from ai_tracker import catalog, config, letter as L, observations, pipeline
from ai_tracker.site import build as B
from ai_tracker.site import markdown as MD
from ai_tracker.state import measures as M
from ai_tracker.state import snapshot as S

FETCHED = pd.Timestamp("2026-11-01")
TODAY = "2026-11-23"
MONTH = "2026-10"
SECRET = "zz_secret_series"  # publish=False, core series of G9
SECRET_LABEL = "Hemlig etikett zz"
PUBLIC = ["pub_a", "pub_b", "pub_c"]
SECRET_REVISED = 98765.4321


def spec(key, branch, publish=True, license="CC BY 4.0 (test)", label=None):
    return catalog.Spec(key=key, branch=branch, label=label or f"Etikett {key}", unit="MUSD", freq="M",
                        source=f"Testkälla {branch}", fetch=lambda: pd.Series(dtype=float), lag_days=10,
                        license=license, publish=publish, question=f"Fråga {key}?")


def monthly(key, seed, start="2012-01", end="2026-09", scale=100.0):
    rng = np.random.default_rng(seed)
    periods = pd.period_range(start, end, freq="M")
    values = scale * np.exp(np.cumsum(0.01 + 0.02 * rng.standard_normal(len(periods))))
    return pd.DataFrame({"series": key, "freq": "M", "period": [str(p) for p in periods], "value": values,
                         "known_from": pd.DatetimeIndex(periods.end_time.normalize()) + pd.Timedelta(days=10),
                         "source": "release", "fetched_at": FETCHED})


def revision(table, key, period, factor=None, value=None, known="2026-10-15"):
    old = table.loc[(table["series"] == key) & (table["period"] == period), "value"].iloc[-1]
    return pd.DataFrame({"series": [key], "freq": ["M"], "period": [period],
                         "value": [value if value is not None else old * factor], "known_from": [pd.Timestamp(known)],
                         "source": ["revision"], "fetched_at": [FETCHED]})


def make_ctx(tmp_path) -> M.Context:
    specs = [spec(k, "G6") for k in PUBLIC] + [
        spec(SECRET, "G9", publish=False, license="unverified: test", label=SECRET_LABEL),
        spec("pub_g9", "G9"), spec("pub_g9b", "G9"), spec("tsmc_revenue_m", "G6")]
    parts = [monthly(s.key, i, scale=1000.0 if s.key == SECRET else 100.0) for i, s in enumerate(specs)]
    table = pd.concat(parts, ignore_index=True)
    table = pd.concat([table, revision(table, "pub_a", "2026-06", 1.05), revision(table, "pub_b", "2026-06", 1.004),
                       revision(table, SECRET, "2026-06", value=SECRET_REVISED)], ignore_index=True)
    return M.Context(table, specs={s.key: s for s in specs}, derived={},
                     core={"G6": list(PUBLIC), "G9": [SECRET, "pub_g9", "pub_g9b"]},
                     forecasts=tmp_path / "forecasts", selection=lambda when: [])


def write_forecasts(root: Path):
    d = root / "n2"
    d.mkdir(parents=True, exist_ok=True)
    common = {"nowcast": "N2", "target": "tsmc_revenue_m", "unit": "mn TWD", "champion": "B2",
              "inputs": [{"series": SECRET, "period": "2026-08", "value": 1.0, "known_from": "2026-09-10"}]}
    (d / "2026-09.json").write_text(json.dumps({**common, "month": "2026-09", "origin": "2026-10-05", "value": 400.0,
                                                "variants": {"B0": 390.0, "B1": 395.0, "V1": 396.0, "B2": 400.0}}),
                                    encoding="utf-8")
    # origin after the month end: not part of the October letter
    (d / "2026-10.json").write_text(json.dumps({**common, "month": "2026-10", "origin": "2026-11-05", "value": 777.0,
                                                "variants": {"B0": 1.0, "B1": 1.0, "V1": 1.0, "B2": 777.0}}),
                                    encoding="utf-8")


def write_snapshot(ctx, snaps: Path, month: str) -> Path:
    snaps.mkdir(parents=True, exist_ok=True)
    path = snaps / f"{month}.json"
    path.write_text(json.dumps(S.build(S.month_end(month), ctx=ctx), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


@pytest.fixture
def env(tmp_path):
    ctx = make_ctx(tmp_path)
    write_forecasts(tmp_path / "forecasts")
    return ctx, tmp_path / "snapshots", tmp_path / "forecasts"


def live_letter(env, months=(MONTH,)) -> str:
    ctx, snaps, fc = env
    for m in months:
        write_snapshot(ctx, snaps, m)
    return L.letter(MONTH, ctx, snapshots_dir=snaps, forecasts_dir=fc)


def recon_letter(env) -> str:
    ctx, snaps, fc = env
    return L.letter(MONTH, ctx, snapshots_dir=snaps, forecasts_dir=fc, reconstructed=True, today=TODAY)


def outside_withheld(text: str) -> str:
    """The letter without the one section that may name withheld series."""
    return re.sub(r"^## Visas inte av licensskäl\n.*?(?=^## )", "", text, flags=re.S | re.M)


# ------------------------------------------------------------------ determinism, labels, refusal


def test_letter_is_deterministic(env, tmp_path):
    a = live_letter(env)
    ctx, snaps, fc = env
    again = M.Context(ctx.table.sample(frac=1.0, random_state=1), specs=ctx.specs, derived={}, core=ctx.core,
                      forecasts=ctx.forecasts, selection=ctx.selection)  # same data, other row order
    assert L.letter(MONTH, again, snapshots_dir=snaps, forecasts_dir=fc) == a
    p1 = L.write(MONTH, ctx, out_dir=tmp_path / "out", snapshots_dir=snaps, forecasts_dir=fc)
    first = p1.read_bytes()
    L.write(MONTH, ctx, out_dir=tmp_path / "out", snapshots_dir=snaps, forecasts_dir=fc)
    assert p1.read_bytes() == first and p1.name == f"{MONTH}.md"
    r = L.letter(MONTH, ctx, snapshots_dir=tmp_path / "none", forecasts_dir=fc, reconstructed=True, today=TODAY)
    assert r == L.letter(MONTH, ctx, snapshots_dir=tmp_path / "none", forecasts_dir=fc, reconstructed=True,
                         today=TODAY)


def test_live_letter_is_labelled_from_the_snapshot(env):
    text = live_letter(env)
    title = text.splitlines()[0]
    assert title == "# Månadsbrev: AI-utrullningen, oktober 2026"
    assert "`snapshots/2026-10.json`" in text and "Rekonstruerad, inte ett skarpt underlag" not in text
    assert L.parse(text) == {"title": title[2:], "kind": "skarp"}
    # no September snapshot: the comparison month is reconstructed and says so wherever it is used
    assert "sedan 2026-09 (rekonstruerad)" in text
    assert "## Så ska brevet läsas" in text and "inte investeringsrådgivning" in text


def test_live_letter_compares_with_the_previous_live_snapshot(env):
    text = live_letter(env, months=("2026-09", MONTH))
    assert "sedan 2026-09" in text and "2026-09 (rekonstruerad)" not in text


def test_reconstructed_letter_is_labelled_prominently(env):
    text = recon_letter(env)
    lines = text.splitlines()
    assert lines[0].endswith("(rekonstruerad)")
    assert lines[2].startswith("> **Rekonstruerad, inte ett skarpt underlag.**")
    assert L.parse(text)["kind"] == "rekonstruerad"
    assert "sedan 2026-09 (rekonstruerad)" in text


def test_refuses_without_snapshot_unless_reconstructed(env, tmp_path, capsys, monkeypatch):
    ctx, snaps, fc = env
    monkeypatch.setattr(observations, "PATH", observations.PATH)  # main(--table) sets it; restore after
    with pytest.raises(L.NoSnapshot, match="--reconstructed"):
        L.letter(MONTH, ctx, snapshots_dir=snaps, forecasts_dir=fc)
    out = tmp_path / "out"
    rc = L.main(["--month", MONTH, "--table", str(tmp_path / "missing.parquet"), "--snapshots-dir", str(snaps),
                 "--out-dir", str(out)])
    assert rc == 1 and not out.exists() and "refused" in capsys.readouterr().err
    # a reconstruction never replaces a live snapshot, and a month that has not ended cannot be reconstructed
    write_snapshot(ctx, snaps, MONTH)
    with pytest.raises(ValueError, match="exists"):
        L.letter(MONTH, ctx, snapshots_dir=snaps, forecasts_dir=fc, reconstructed=True, today=TODAY)
    with pytest.raises(ValueError, match="has not ended"):
        L.letter("2026-11", ctx, snapshots_dir=snaps, forecasts_dir=fc, reconstructed=True, today=TODAY)


def test_branch_content_comes_from_the_snapshot_file(env):
    ctx, snaps, fc = env
    path = write_snapshot(ctx, snaps, MONTH)
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["branches"]["G6"]["state"] = "bromsar in"  # an edited file shows that nothing is recomputed
    doc["branches"]["G6"]["index"] = 0.123
    path.write_text(json.dumps(doc), encoding="utf-8")
    text = L.letter(MONTH, ctx, snapshots_dir=snaps, forecasts_dir=fc)
    assert "### G6 Utbud och halvledare: bromsar in" in text and "Index 0,12 med" in text


# ------------------------------------------------------------------ licence rule


@pytest.mark.parametrize("kind", ["live", "recon"])
def test_withheld_series_only_in_the_withheld_list(env, kind):
    ctx = env[0]
    text = live_letter(env) if kind == "live" else recon_letter(env)
    rest = outside_withheld(text)
    assert SECRET not in rest and SECRET_LABEL not in rest
    section = text.split("## Visas inte av licensskäl", 1)[1].split("\n## ", 1)[0]
    assert SECRET in section and SECRET_LABEL in section and "licensen är inte kontrollerad" in section
    values = ctx.table.loc[ctx.table["series"] == SECRET, "value"]
    for v in [SECRET_REVISED, values.iloc[-2], *values.tail(24)]:
        assert L.value_text(float(v)) not in text, v
        assert f"{v:.1f}" not in text
    # the withheld series still counts in G9 and is counted, not named, in the data news
    assert "1 serie visas inte av licensskäl, den räknas i indexet" in rest
    note = next(x for x in rest.splitlines() if x.startswith("Serier som inte visas av licensskäl ingår i antalen"))
    assert "serier med revideringar 1" in note


def test_forecast_inputs_are_never_shown(env):
    text = live_letter(env)
    assert "inputs" not in text and "777" not in text  # the November-origin forecast is not in the October letter


# ------------------------------------------------------------------ content


def test_neutral_wording(env):
    for text in (recon_letter(env), live_letter(env)):
        assert not re.search(r"\b(bra|bättre|sämre|dålig\w*|stark\w*|svag\w*|oroande|tyvärr|glädjande|lyckad\w*)\b",
                             text, flags=re.I)
        assert re.search(r"\b(accelererar|stabil|bromsar in)\b", text)


def test_branch_paragraph_and_table(env):
    text = live_letter(env)
    g6 = text.split("### G6 Utbud och halvledare: ", 1)[1].split("\n### ", 1)[0]
    assert "Index " in g6 and "3 räknade serier" in g6
    assert "| Serie | Senaste period | Mått | Takt | Förändring i takt |" in g6
    for k in PUBLIC:
        assert f"(`{k}`)" in g6
    assert "log×100 per år" in g6 and "mot sex månader tidigare" in g6


def test_nowcasts_new_forecast_and_new_outcome(env):
    ctx = env[0]
    text = live_letter(env)
    nc = text.split("## Nowcasts", 1)[1].split("\n## ", 1)[0]
    assert "- 2026-09 (prognosdag 2026-10-05, `forecasts/n2/2026-09.json`): huvudmodell B2 400 mn TWD" in nc
    outcome = ctx.table.loc[(ctx.table["series"] == "tsmc_revenue_m") & (ctx.table["period"] == "2026-09"), "value"]
    err = 100 * np.log(400.0 / float(outcome.iloc[0]))
    assert f"fel huvudmodell (B2) {L.n(err, 2, signed=True)}" in nc
    # the current champion (B3 since step 2, C2); the file itself says B2
    assert "Huvudmodell: B3." in nc and "Utvärderade hittills: 1 av 1" in nc and "kan vara slump" in nc
    assert "Nowcasts: 1 ny skarp prognos och 1 nytt utfall i oktober 2026." in text


def test_revisions_listed_above_threshold_only(env):
    text = live_letter(env)
    data = text.split("## Data", 1)[1].split("\n## ", 1)[0]
    assert "(`pub_a`) | 1 (av 1) | 2026-06 |" in data and "(+5,0 %)" in data
    table = data.split("| Serie |", 1)[1].split("\n\n", 1)[0]
    assert "`pub_b`" not in table  # 0.4 % is below the threshold
    assert "varav 2 i 2 serier ändrades med minst 1 %" in data


def test_revision_detection():
    t = pd.DataFrame({"series": ["a"] * 4 + ["b"], "freq": "M", "period": ["2026-01", "2026-01", "2026-01", "2026-02",
                                                                         "2026-01"],
                      "value": [1.0, 1.0, 2.0, 5.0, 3.0],
                      "known_from": pd.to_datetime(["2026-02-10", "2026-03-10", "2026-03-20", "2026-03-05",
                                                    "2026-03-01"]),
                      "source": "release", "fetched_at": FETCHED})
    nv = L.new_versions(t, pd.Timestamp("2026-03-01"), pd.Timestamp("2026-03-31"))
    rev = nv[nv["old"].notna()]
    assert rev[["series", "period", "old", "new"]].values.tolist() == [["a", "2026-01", 1.0, 2.0]]
    assert sorted(nv.loc[nv["old"].isna(), "series"]) == ["a", "b"]  # new periods, not revisions


# ------------------------------------------------------------------ publish, workflow, site


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "README").write_text("x")
    _git(tmp_path, "add", "README")
    _git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "init")
    return tmp_path


def test_publish_commits_the_letter_with_the_snapshot(repo):
    snap, letter = repo / "snapshots" / "2026-11.json", repo / "docs" / "manadsbrev" / "2026-11.md"
    snap.parent.mkdir(parents=True)
    letter.parent.mkdir(parents=True)
    snap.write_text("{}\n")
    letter.write_text("# brev\n")
    paths = ["snapshots/2026-11.json", "docs/manadsbrev/2026-11.md"]
    assert pipeline.publish(paths, repo)
    assert set(_git(repo, "show", "--name-only", "--format=", "HEAD").split()) == set(paths)
    assert "Monthly letter 2026-11" in _git(repo, "log", "-1", "--format=%s")
    assert not pipeline.publish(paths, repo)  # both unchanged: no commit
    letter.write_text("# brev, omgenererat\n")  # the letter is not a record: a regenerated letter is committed
    assert pipeline.publish(["docs/manadsbrev/2026-11.md"], repo)
    assert _git(repo, "show", "--name-status", "--format=", "HEAD") == "M\tdocs/manadsbrev/2026-11.md"
    (repo / "README").write_text("changed")
    _git(repo, "add", "README")
    letter.write_text("# brev 3\n")
    with pytest.raises(SystemExit, match="unexpected staged"):
        pipeline.publish(["docs/manadsbrev/2026-11.md"], repo)
    with pytest.raises(SystemExit, match="only forecasts"):
        pipeline.publish(["docs/manadsbrev/notes.md"], repo)


def test_snapshot_workflow_writes_and_commits_the_letter():
    wf = yaml.safe_load((config.REPO / ".github" / "workflows" / "snapshot.yml").read_text(encoding="utf-8"))
    steps = wf["jobs"]["snapshot"]["steps"]
    names = [s.get("name", "") for s in steps]
    i_snap = names.index("Write the snapshot")
    i_letter = next(i for i, n in enumerate(names) if "letter" in n.lower() and "Write" in n)
    i_commit = next(i for i, n in enumerate(names) if n.startswith("Commit"))
    assert i_snap < i_letter < i_commit
    step = steps[i_letter]
    assert "python -m ai_tracker.letter --month" in step["run"] and step.get("continue-on-error") is True
    assert step["if"] == "steps.snap.outputs.written != ''"
    commit = steps[i_commit]
    assert commit["env"]["LETTER"] == "${{ steps.letter.outputs.letter }}"
    assert 'pipeline publish "${WRITTEN}" ${LETTER:+"$LETTER"}' in commit["run"]


def test_site_lists_and_renders_letters_withheld_only_in_its_section(env, tmp_path):
    ctx, snaps, fc = env
    letters = tmp_path / "letters"
    L.write(MONTH, ctx, out_dir=letters, snapshots_dir=snaps, forecasts_dir=fc, reconstructed=True, today=TODAY)
    site = tmp_path / "site"
    B.build(site, ctx=ctx, snapshots_dir=snaps, forecasts_dir=fc, today=TODAY, history_from="2026-08", checks=False,
            letters_dir=letters)
    index = (site / "manadsbrev.html").read_text(encoding="utf-8")
    assert 'href="manadsbrev-2026-10.html"' in index and "(rekonstruerad)" in index
    assert 'href="manadsbrev.html"' in (site / "index.html").read_text(encoding="utf-8")
    page = (site / "manadsbrev-2026-10.html").read_text(encoding="utf-8")
    assert "<h1>Månadsbrev: AI-utrullningen, oktober 2026 (rekonstruerad)</h1>" in page
    assert '<blockquote class="banner recon">' in page and "<table>" in page and "inte investeringsrådgivning" in page
    rest = re.sub(r'<section id="withheld".*?</section>', "", page, flags=re.S)
    assert SECRET not in rest and SECRET_LABEL not in rest and SECRET in page
    data = json.loads((site / "data" / "manadsbrev.json").read_text(encoding="utf-8"))
    assert [x["month"] for x in data["letters"]] == [MONTH] and "markdown" not in data["letters"][0]


def test_markdown_renderer_escapes_and_renders():
    md = ("# T <script>\n\n> **B** text\n\n## Avsnitt\n\nA *kursiv* `k<b>` [l](https://x.org) [j](javascript:alert(1))\n\n"
          "- ett\n\n  - under\n- två\n\n| a | b |\n|---|---|\n| 1 | <i>2</i> |\n")
    html = MD.render(md, {"Avsnitt": "withheld"})
    assert "<script>" not in html and "&lt;script&gt;" in html and "<i>" not in html
    assert '<blockquote class="banner recon"><p><strong>B</strong> text</p></blockquote>' in html
    assert '<section id="withheld">' in html and "<em>kursiv</em>" in html and "<code>k&lt;b&gt;</code>" in html
    assert '<a href="https://x.org">l</a>' in html and 'href="javascript' not in html
    assert "<li>ett<ul><li>under</li></ul></li><li>två</li>" in html
    assert "<thead><tr><th>a</th><th>b</th></tr></thead>" in html
