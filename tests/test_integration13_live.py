"""Fixes after the run 13 review of the live routines (L3) and of the merge (L1): the public snapshot carries no values
of a withheld series (L3-1), the bundle's letters and reports pass the licence gate (L3-3), the snapshot workflow
writes the snapshot when only freshness fails (L3-4), the public texts date the reconciliations from the register
(L3-5), and the story's K0 counts the index v2 state on its own."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from ai_tracker import catalog, config, observations
from ai_tracker import letter as L
from ai_tracker import quarterly as Q
from ai_tracker.site import data as D
from ai_tracker.site import render as RN
from ai_tracker.site_bundle import export as E
from ai_tracker.site_bundle import gate as G
from ai_tracker.site_bundle import story as ST
from ai_tracker.site_bundle import synthetic as SY
from ai_tracker.state import expectations as EX
from ai_tracker.state import register as R
from ai_tracker.state import snapshot as S
from ai_tracker.state.measures import Context
from conftest import real_table_exists

REGISTER = config.REPO / "docs" / "mattregister.md"


def _series_entries(doc: dict):
    for code, b in doc["branches"].items():
        for lst in ("series_used", "series_not_counted"):
            for m in b.get(lst) or []:
                if m.get("series"):
                    yield code, lst, m
    for m in (doc.get("reconciliations") or {}).get("series") or []:
        yield "A5", "reconciliations", m


# ------------------------------------------------------------------ L3-1: no values of a withheld series


def test_synthetic_snapshot_has_no_values_for_withheld_series_and_keeps_their_direction():
    ctx = SY.context(Path("/nonexistent"))
    doc = S.build("2026-10-31", ctx=ctx)
    withheld = [m for _, _, m in _series_entries(doc) if not D.publishable(m["series"], ctx)]
    shown = [m for _, lst, m in _series_entries(doc) if lst == "series_used" and D.publishable(m["series"], ctx)]
    assert withheld and shown  # the synthetic world has both (arXiv is withheld there)
    for m in withheld:
        assert not set(S.VALUE_FIELDS) & set(m), m["series"]
        assert "direction" in m or not m.get("valid"), m["series"]
    assert any(m.get("level") is not None and m.get("pace") is not None for m in shown)
    assert doc["rules"]["withheld_values"] == S.WITHHELD_NOTE
    # the in-memory reconstruction keeps everything (only the public record is stripped)
    full = S._clean(S.compute("2026-10-31", ctx))
    assert any("level" in m for b in full.values() for m in b["series_used"] if not D.publishable(m["series"], ctx))


@pytest.mark.skipif(not real_table_exists(), reason="needs the real observation table")
def test_real_snapshot_carries_no_withheld_value(tmp_path):
    table = observations.load()
    p = S.write("2026-10-31", table, tmp_path, today="2026-11-25", regime=False)
    doc = json.loads(p.read_text(encoding="utf-8"))
    ctx = Context(table)
    keys = []
    for _, _, m in _series_entries(doc):
        if not D.publishable(m["series"], ctx):
            keys.append(m["series"])
            assert not set(S.VALUE_FIELDS) & set(m), m["series"]
    assert {"pjm_lf_peak_dom_h5", "pjm_lf_peak_rto_h5"} <= set(keys)  # PJM is class "nej" (licensniva.md)
    ex = doc[EX.SECTION]
    if "error" not in ex and not EX.csv_public(lambda k: D.publishable(k, ctx)):
        for b in ex["break_statements"]:
            if EX.from_csv(b["company"]):
                assert not {"value", "prev_value", "size", "reason"} & set(b)
        for c in ex["surprise"]["companies"]:
            if EX.from_csv(c["company"]):
                assert set(c) <= {"company", "measure", "period", "known_from", "guidance_known_from"}


def _section() -> dict:
    idx = {"period": "2026Q4", "known_from": "2026-10-29", "n": 3, "index": 0.5, "median_size": -0.5,
           "percentile": 5.5, "companies": "googl,msft"}
    return {"group": "g", "in_diffusion": False,
            "revisions": {"window_4q": {"latest": dict(idx), "latest_with_value": dict(idx)}},
            "revisions_numeric_only": {"window_4q": {"latest": dict(idx), "latest_with_value": None}},
            "composition_main_window": {"period": "2026Q4", "numbers": {"n": 2}, "directions": {"n": 1}},
            "break_statements": [{"ref": "msft-r11f1", "company": "msft", "value": 175000.0, "prev_value": 190000.0,
                                  "size": -8.2, "reason": "r"},
                                 {"ref": "tsmc_guid_capex", "company": "tsmc", "value": 40000.0, "size": 1.0}],
            "events_recent": [{"company": "meta", "direction": 1, "size": 7.7, "known_from": "2026-04-29"},
                              {"company": "nvda", "direction": 0, "size": 0.0, "known_from": "2026-05-20"}],
            "events_per_company_year": {"meta": {"2026": {"n": 2}}, "tsmc": {"2026": {"n": 4}}},
            "surprise": {"companies": [{"company": "googl", "measure": "capex", "period": "2025", "outcome": 91.0,
                                        "guidance": 92000.0, "surprise": 1.0, "z": 0.3, "known_from": "2026-02-05"},
                                       {"company": "tsmc", "measure": "revenue", "guidance": 1.0, "surprise": 2.0}],
                         "index": {"latest": {"period": "2026Q3", "known_from": "2026-10-16", "value": 0.4},
                                   "latest_with_value": None},
                         "tsmc_usd_sensitivity": {"latest": {"surprise_usd": 1.0}}}}


def test_expectations_keep_no_curated_value_while_its_series_are_withheld():
    s = EX.withhold(_section(), lambda k: False)
    text = json.dumps(s)
    for v in ("175000", "190000", "92000", "-8.2", "7.7", "-0.5", "0.4"):
        assert v not in text, v
    assert s["break_statements"][0] == {"ref": "msft-r11f1", "company": "msft"}  # the reason quotes the figure
    assert s["break_statements"][1]["value"] == 40000.0  # TSMC's capex guidance is an SEC series
    assert s["events_recent"][0] == {"company": "meta", "known_from": "2026-04-29"}
    assert s["events_recent"][1]["size"] == 0.0 and s["events_per_company_year"] == {"tsmc": {"2026": {"n": 4}}}
    assert s["revisions"]["window_4q"]["latest"] == {"period": "2026Q4", "known_from": "2026-10-29",
                                                     "companies": "googl,msft"}
    assert s["composition_main_window"] == {"period": "2026Q4"}
    assert s["surprise"]["companies"][1]["surprise"] == 2.0 and "guidance" not in s["surprise"]["companies"][0]
    assert s["surprise"]["tsmc_usd_sensitivity"] == {"latest": {"surprise_usd": 1.0}}
    assert s["values_withheld"] == EX.WITHHELD_NOTE
    # the owner's decision (R11-4) makes them publishable: the section is unchanged
    assert EX.withhold(_section(), lambda k: True) == _section()
    err = {"group": "g", "in_diffusion": False, "error": "x"}
    assert EX.withhold(err, lambda k: False) == err


def test_from_csv_matches_the_statement_sources():
    import inspect

    from ai_tracker.series import guidance_revisions as GR

    # the companies GR builds from SEC series in the table (statements and surprises) are exactly TABLE_COMPANIES
    src = inspect.getsource(GR.table_statements) + inspect.getsource(GR)
    literal = set(re.findall(r'out\.append\(\("(\w+)", "(?:revenue|capex)"', src))
    assert literal == set(EX.TABLE_COMPANIES) == {"tsmc", "nvda"}
    assert not any(EX.from_csv(c) for c in EX.TABLE_COMPANIES)
    assert all(EX.from_csv(c) for c in GR.CAPEX_SURPRISE)  # Meta and Alphabet capex: from the CSV


def test_regime_rows_of_withheld_series_keep_the_break_flag_only():
    sec = {"ms": {"capex": {"p_slow": 0.1}},
           "bocpd": [{"series": "hidden", "branch": "G7", "p_recent": 0.9, "break": True, "n_periods": 20},
                     {"series": "shown", "branch": "G6", "p_recent": 0.7, "break": True}]}
    out = S.withhold_regime(sec, lambda k: k != "hidden")
    assert out["bocpd"][0] == {"series": "hidden", "branch": "G7", "break": True, "n_periods": 20}
    assert out["bocpd"][1]["p_recent"] == 0.7 and out["ms"] == sec["ms"]
    assert sec["bocpd"][0]["p_recent"] == 0.9  # the input is not changed


# ------------------------------------------------------------------ L3-3: letters and reports pass the gate


def test_without_withheld_names_replaces_only_the_section_body():
    md = ("# Brev\n\nText om `shown_key`.\n\n## Visas inte av licensskäl\n\n- G9: arXiv (`hidden_key`). Skäl: x.\n\n"
          "### Under\n\n`hidden_key` igen\n\n## Så läses brevet\n\n- slut\n")
    out = E.without_withheld_names(md, "docs/manadsbrev/2026-11.md")
    assert "hidden_key" not in out and "`shown_key`" in out
    assert "## Visas inte av licensskäl" in out and "## Så läses brevet\n\n- slut" in out
    assert "`withheld.json`" in out and "`docs/manadsbrev/2026-11.md`" in out
    assert E.without_withheld_names("# Brev\n\nInget avsnitt.\n", "f") == "# Brev\n\nInget avsnitt.\n"


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    """The synthetic world with a letter and a quarterly report generated by the real modules (not stubs)."""
    root = tmp_path_factory.mktemp("synthetic")
    ctx = SY.context(root)
    paths = SY.write_inputs(root, ctx)
    letters, reports = root / "letters_gen", root / "reports_gen"
    L.write("2026-10", ctx, out_dir=letters, snapshots_dir=paths["snapshots_dir"], forecasts_dir=paths["forecasts_dir"])
    Q.write("2026Q3", ctx, out_dir=reports, snapshots_dir=paths["snapshots_dir"], forecasts_dir=paths["forecasts_dir"],
            docs_dir=paths["docs_dir"], reconstructed=True, today=SY.TODAY)
    return ctx, dict(paths, letters_dir=letters, reports_dir=reports)


def test_generated_letter_and_report_pass_the_bundle_gate(generated):
    ctx, paths = generated
    withheld = set(SY.WITHHELD)
    raw_letter = (paths["letters_dir"] / "2026-10.md").read_text(encoding="utf-8")
    raw_report = (paths["reports_dir"] / "2026Q3.md").read_text(encoding="utf-8")
    # the files in the repo name the withheld series on purpose, in their own section
    assert L.WITHHELD_HEADING in raw_letter and any(k in raw_letter for k in withheld)
    assert any(k in raw_report for k in withheld)
    docs = E.assemble(ctx, today=SY.TODAY, history_from=SY.HISTORY_FROM, calibration=SY.calibration(),
                      commits=SY.commits, **paths)  # raises GateError on a violation
    assert G.scan(docs, ctx) == []
    for path in ("letters/2026-10.json", "reports/2026Q3.json"):
        md = docs[path]["markdown"]
        assert not any(re.search(rf"(?<![A-Za-z0-9_]){k}(?![A-Za-z0-9_])", md) for k in withheld), path
        assert "`withheld.json`" in md, path


# ------------------------------------------------------------------ L3-4: stale series alone do not stop the snapshot


def _step(steps, name):
    return next(s for s in steps if s.get("name") == name)


def test_snapshot_workflow_handles_exit_2_like_the_weekly_fetch(tmp_path):
    wf = yaml.safe_load((config.REPO / ".github" / "workflows" / "snapshot.yml").read_text(encoding="utf-8"))
    steps = wf["jobs"]["snapshot"]["steps"]
    names = [s.get("name", "") for s in steps]
    refresh = _step(steps, "Refresh all series and run the warehouse checks")
    assert refresh["id"] == "refresh" and "python -m ai_tracker.pipeline weekly" in refresh["run"]
    i_refresh, i_snap = names.index(refresh["name"]), names.index("Write the snapshot")
    i_commit = next(i for i, n in enumerate(names) if n.startswith("Commit"))
    fail = _step(steps, "Fail on stale series")
    assert i_refresh < i_snap < i_commit < names.index("Fail on stale series") == len(steps) - 1
    assert fail["if"] == "always() && steps.refresh.outputs.rc == '2'"
    assert _step(steps, "Write the snapshot")["if"] == "steps.due.outputs.due == 'true'"
    # run the step's script with the pipeline replaced by a fixed exit code (GitHub runs it with bash -e)
    for rc, want in ((0, 0), (2, 0), (1, 1)):
        out = tmp_path / f"out{rc}"
        script = refresh["run"].replace("python -m ai_tracker.pipeline weekly", f"(exit {rc})")
        res = subprocess.run(["bash", "-e", "-c", script], env={"GITHUB_OUTPUT": str(out), "PATH": "/usr/bin:/bin"},
                             capture_output=True, text=True)
        assert res.returncode == want, (rc, res.stdout, res.stderr)
        assert out.read_text().strip() == f"rc={rc}"
        assert ("::warning::" in res.stdout) == (rc == 2)


# ------------------------------------------------------------------ L3-5: register dates of the reconciliations


def test_reconciliation_dates_match_the_register_tables():
    assert set(R.RECONCILIATION_REGISTERED) == set(R.RECONCILIATIONS)
    text = REGISTER.read_text(encoding="utf-8")
    heads = [(m.start(), m.group(1)) for m in re.finditer(r"^### (\d{4}-\d{2}-\d{2}) – A5", text, re.M)]
    for key, day in R.RECONCILIATION_REGISTERED.items():
        first = min(i for i, _ in heads if f"| `{key}` |" in text[i:text.find("\n### ", i + 4)])
        assert dict(heads)[first] == day, key
    assert R.reconciliation_dates(["x_capex_cloud"]) == "2026-11-23"
    assert R.reconciliation_dates(["x_dep_rev", "x_capex_cloud"]) == "2026-11-23 och 2026-11-24"
    assert R.reconciliation_dates([]) == "2026-11-23 och 2026-11-24"


def test_letter_and_old_site_date_the_reconciliations_they_show(monkeypatch):
    monkeypatch.setattr(L, "publishable", lambda key, inp: key != "x_dep_rev_aws")
    monkeypatch.setattr(L, "series_name", lambda key, ctx: key)

    def text(keys):
        inp = SimpleNamespace(current={"reconciliations": {"series": [{"series": k} for k in keys]}}, ctx=None)
        return "\n".join(L.reconciliation_section(inp))

    assert "registrerade 2026-11-23 och 2026-11-24, A5" in text(["x_capex_cloud", "x_dep_rev"])
    assert "registrerade 2026-11-23, A5" in text(["x_capex_cloud", "x_dep_rev_aws"])  # the withheld one is not shown
    assert "2026-11-24" not in text(["x_capex_cloud"])
    html = RN.reconciliation_section({"available": True, "date": "2026-11-30", "kind": "skarp",
                                      "series": [{"key": "x_capcost_rev_r08", "label": "Kapitalkostnad"}]})
    assert "registrerade i måttregistret 2026-11-24, A5" in html


# ------------------------------------------------------------------ story after the merge (K0, amendment L3-1)


def test_story_k0_counts_the_few_sources_state_on_its_own():
    def br(state):
        return {"state": state, "index": 0.5, "n_series": 0, "n_up": 0, "n_neutral": 0, "n_down": 0,
                "series_used": [], "series_not_counted": []}

    inp = {"month": "2026-10", "kind": "rekonstruerad", "known": "2026-10-31",
           "branches": {"G1": br(R.STATE_STABLE), "G8": br(R.STATE_FEW_FAMILIES), "G2": br(R.STATE_FEW)},
           "branch_names": dict(catalog.BRANCHES), "previous": None, "prev_branches": None, "recon": [],
           "prev_recon": None, "outcomes": [], "regime": None, "history": {}, "recon_history": {}}
    k0 = ST.select(inp, lambda k: True, lambda k: k)["cards"][0]
    assert k0["facts"]["counts"][R.STATE_FEW_FAMILIES] == 1 and k0["facts"]["counts"][R.STATE_FEW] == 1
    assert "1 gren har för få källor." in k0["text"] and "1 gren har för få serier." in k0["text"]
    inp["branches"] = {"G1": br(R.STATE_STABLE)}
    assert R.STATE_FEW_FAMILIES not in ST.select(inp, lambda k: True, lambda k: k)["cards"][0]["facts"]["counts"]


def test_the_l3_amendment_is_in_the_register_after_the_w13_rule():
    text = REGISTER.read_text(encoding="utf-8")
    i, j = text.index("### " + ST.ENTRY), text.index("Ändring av W13 (L3-1)")
    k = text.index("Ändring av W13 (R-W3a–c)")
    assert i < k < j
    amend = text[j:]
    for needle in ("K5 och K6", "publicerbara", "för få källor", "2026-11-30"):
        assert needle in amend, needle
