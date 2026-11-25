"""W14: the quarterly report as bundle documents (site_bundle.report on ai_tracker.quarterly): built from the same
facts as the Markdown report, labelled live or reconstructed, nothing known after the report day, withheld series only
named in the withheld list, neutral wording, schema-valid, and present in the committed fixtures."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

from ai_tracker import quarterly as Q
from ai_tracker.site import data as D
from ai_tracker.site_bundle import gate as G
from ai_tracker.site_bundle import report as RP
from ai_tracker.site_bundle import schema as SC

sys.path.insert(0, str(Path(__file__).parent))
import test_quarterly as T

REPO = Path(__file__).resolve().parents[1]
COMMITTED = REPO / "web-data-fixtures"
DAY_VALUE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:T[\d:.]+(?:Z|[+-]\d{2}:?\d{2})?|/\d{4}-\d{2}-\d{2})?$")


def later_days(x, day: str, path: str = "$") -> list[str]:
    """Every day value in the document later than `day` (the web gate's leaks() rule)."""
    out = []
    if isinstance(x, str):
        m = DAY_VALUE.match(x)
        if m and m.group(1) > day:
            out.append(f"{path} = {x}")
    elif isinstance(x, dict):
        for k, v in x.items():
            out += later_days(v, day, f"{path}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            out += later_days(v, day, f"{path}[{i}]")
    return out


@pytest.fixture
def world(tmp_path):
    ctx, snaps, fc, docs = T.make_ctx(tmp_path), tmp_path / "snapshots", tmp_path / "forecasts", T.write_docs(tmp_path / "docs")
    T.write_forecasts(fc)
    regime = {
        "2026-07": T._regime(0.85, None, [T._b("pub_a", "G6", 0.1, "2026-06")]),
        "2026-08": T._regime(0.9, None, [T._b("pub_a", "G6", 0.92, "2026-07"), T._b(T.SECRET, "G9", 0.95, "2026-07")]),
        "2026-09": T._regime(0.5, None, [T._b("pub_a", "G6", 0.9, "2026-08")]),
    }
    for m in T.MONTHS:
        T.write_snapshot(ctx, snaps, m, regime[m])
    rec = D.Record(ctx, snaps, T.TODAY, "2026-03")
    out = RP.docs(rec, fc, docs)
    return {"ctx": ctx, "snaps": snaps, "fc": fc, "docs": docs, "rec": rec, "out": out}


def test_quarters_live_and_reconstructed(world):
    out = world["out"]
    idx = out["report/index.json"]
    assert [q["quarter"] for q in idx["quarters"]] == ["2026Q2", "2026Q3"] and idx["latest"] == "2026Q3"
    live, recon = out["report/2026Q3.json"], out["report/2026Q2.json"]
    assert live["kind"] == "skarp" and live["status"] == "live" and live["recon_note"] is None
    assert [m["file"] for m in live["months"]] == [f"snapshots/{m}.json" for m in T.MONTHS]
    assert recon["kind"] == "rekonstruerad" and "(rekonstruerad)" in recon["title"]
    assert recon["recon_note"].startswith("Rekonstruerad, inte en skarp rapport")
    assert all(m["kind"] == "rekonstruerad" and m["file"] is None for m in recon["months"])
    assert live["base"]["month"] == "2026-06" and live["base"]["kind"] == "rekonstruerad"
    assert idx["first_live"] == "2026Q3"  # the first live snapshot (2026-07) opens its quarter


def test_first_live_quarter_without_snapshots():
    class Rec:
        first_live, first_live_date = None, "2026-11-30"
    assert RP.first_live_quarter(Rec()) == "2027Q1"
    Rec.first_live = "2027-01"
    assert RP.first_live_quarter(Rec()) == "2027Q1"


def test_nothing_known_after_the_report_day(world):
    for path, doc in world["out"].items():
        if path == "report/index.json":
            continue
        assert doc["known"] >= doc["end"]
        assert all(m["known"] <= doc["known"] for m in doc["months"])
        assert later_days(doc, doc["known"]) == [], path


def test_facts_are_the_markdown_reports_facts(world):
    """The live quarter's document and quarterly.report (Markdown) come from the same inputs and say the same."""
    w = world
    doc = w["out"]["report/2026Q3.json"]
    md = Q.report("2026Q3", w["ctx"], snapshots_dir=w["snaps"], forecasts_dir=w["fc"], docs_dir=w["docs"], today=T.TODAY)
    summary = T.section(md, "Sammanfattning")
    for b in doc["branches"]:
        cells = " | ".join(f"{Q.n(c['index'], 2) if c['index'] is not None else '–'} {c['state']}" for c in b["path"])
        assert f"| {b['code']} {b['name']} | {cells} |" in summary
    snap = json.loads((w["snaps"] / "2026-09.json").read_text(encoding="utf-8"))
    g6 = next(b for b in doc["branches"] if b["code"] == "G6")
    assert g6["path"][-1]["index"] == pytest.approx(snap["branches"]["G6"]["index"], abs=1e-4)
    n2 = next(x for x in doc["nowcasts"] if x["id"] == "n2")
    assert n2["n_files"] == 3 and [x["period"] for x in n2["new"]] == ["2026-07", "2026-08"]
    assert all(x["value"] != 777.0 for x in n2["new"])  # origin after the quarter
    out = w["ctx"].table.loc[(w["ctx"].table["series"] == "tsmc_revenue_m") & (w["ctx"].table["period"] == "2026-07"), "value"]
    o = next(x for x in n2["outcomes"] if x["period"] == "2026-07")
    assert o["err_champion"] == pytest.approx(100 * np.log(409.0 / float(out.iloc[0])), rel=1e-4)
    assert o["known_from"] == "2026-08-10" and o["champion"] == "B2"
    assert n2["changes"] == [{"origin": "2026-09-05", "file": "forecasts/n2/2026-08.json", "from": "B2", "to": "B3"}]
    assert any(d.startswith("2026-09-02 – B3 blir huvudmodell för N2") for d in n2["decisions"])
    assert not any("B4" in d for d in n2["decisions"])
    roles = {m["variant"]: m["role"] for m in n2["metrics"]}
    assert roles["B0"] == "baseline" and roles["B2"] == "guidance" and roles["champion"] == "champion"
    assert f"alla {n2['n_scored']} utfall av {n2['n_files_scored']} prognoser" in md
    news = doc["nowcast_news"]
    assert news["n_new"] == 2 and news["n_outcomes"] == sum(x["n_outcomes"] for x in doc["nowcasts"])
    assert f"- Prognoser: {news['text'][0].lower()}{news['text'][1:]}" in summary


def test_regime_from_stored_values(world):
    rg = world["out"]["report/2026Q3.json"]["regime"]
    assert rg["available"] is True
    capex = next(b for b in rg["blocks"] if b["block"] == "capex")
    assert [c["p_slow"] for c in capex["cells"]] == [0.85, 0.9, 0.5]
    assert [c["state"] for c in capex["cells"]] == ["expansion", "inbromsning", "inbromsning"]
    assert rg["shifts"] == [{"block": "capex", "label": "capex och leverantörsled", "shift": "inbromsning", "month": "2026-08"}]
    assert rg["n_breaks"] == 2 and rg["n_breaks_withheld"] == 1
    assert [b["series"] for b in rg["breaks"]] == ["pub_a"]
    recon = world["out"]["report/2026Q2.json"]["regime"]
    assert recon["available"] is False and recon["blocks"] is None


def test_withheld_only_in_the_withheld_list(world):
    for path, doc in world["out"].items():
        assert G.scan({path: doc}, world["ctx"]) == [], path
        rest = {k: v for k, v in doc.items() if k != "withheld"}
        text = json.dumps(rest, ensure_ascii=False)
        assert T.SECRET not in text and T.SECRET_LABEL not in text
    w = world["out"]["report/2026Q3.json"]["withheld"]
    assert [x["key"] for x in w] == [T.SECRET] and w[0]["counted"] is True and w[0]["branch"] == "G9"


def test_schema_and_neutral_wording(world):
    assert SC.validate(world["out"]) == []
    for doc in world["out"].values():
        for t in RP.texts(doc):
            assert RP.neutral(t), t
            assert "`" not in t


def test_committed_fixtures_have_the_reports():
    idx = json.loads((COMMITTED / "report" / "index.json").read_text(encoding="utf-8"))
    assert idx["quarters"] and idx["first_live"] == "2026Q4"
    docs = {"report/index.json": idx}
    for q in idx["quarters"]:
        assert q["kind"] == "rekonstruerad"  # the synthetic record has one live month (2026-10), no complete live quarter
        doc = json.loads((COMMITTED / "report" / f"{q['quarter']}.json").read_text(encoding="utf-8"))
        assert doc["known"] == q["known"] and later_days(doc, doc["known"]) == []
        docs[f"report/{q['quarter']}.json"] = doc
    assert SC.validate(docs) == []
    man = json.loads((COMMITTED / "manifest.json").read_text(encoding="utf-8"))
    assert any(f["path"].startswith("report/") for f in man["files"])
