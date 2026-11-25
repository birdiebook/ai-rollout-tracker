"""Golden replay for time travel (W9): what a site built on day D would have shown, made by Python from the source
table, for the front end's cut of TODAY's bundle (web/src/lib/timetravel/gate.ts) to match.

For every probe day D this replays the pipeline on D itself, not the bundle:

- record:   site.data.Record(ctx, <only the live snapshots dated <= D>, today=D) - the record a site built on D
            would show, its month and kind, the headline sentence (site_bundle.export.headline), and for every
            branch the length of its index history. The script asserts that the history, the stripes and every
            series' measure history of the replay are exactly a PREFIX of today's bundle (same months, same
            values), so the front end only has to cut at the right length; vitest checks that it does.
- versions: site_bundle.vintages.encode(rows, D) per series - the versions a bundle built on D would hold, as a
            SHA-256 over the rows (period|day|value). vitest checks that cutVersions(today's versions, D) gives the
            same digest. For monthly and coarser series also observations.as_of(key, D) on the raw rows (the
            replay of the table itself), as a digest over (period|value).
- backfilled: whether D is before the backfill boundary, from the raw rows: max(latest known_from, latest
            fetched_at day rounded up) of the rows with source "backfill" known on the build day (datakontrakt 5.6,
            RW1-X 3a: backfilled rows carry the vintage of their fetch day). vitest checks seriesOn(doc, D).backfilled.

Usage:
    PYTHONPATH=src python web/fixtures/gen_timetravel_golden.py                 # fixtures -> timetravel_golden.json
    PYTHONPATH=src python web/fixtures/gen_timetravel_golden.py --real BUNDLE OUT   # the real table and bundle
Deterministic. pytest (tests/test_web_timetravel.py) checks that the committed fixture golden is current.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

from ai_tracker import catalog, observations
from ai_tracker.site import data as D
from ai_tracker.site_bundle import export as E
from ai_tracker.site_bundle import vintages as V
from ai_tracker.state import snapshot as S
from ai_tracker.state.measures import rule_for

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "web-data-fixtures"
OUT = Path(__file__).resolve().parent / "timetravel_golden.json"

FIXTURE_PROBES = ["2025-06-29", "2025-06-30", "2025-07-01", "2025-12-31", "2026-02-14", "2026-03-15", "2026-09-30",
                  "2026-10-30", "2026-10-31", "2026-11-13", "2026-11-14", "2026-11-24"]
REAL_PROBES = ["2022-12-30", "2023-01-31", "2023-06-15", "2024-03-31", "2025-07-01", "2026-09-30", "2026-10-31",
               "2026-11-24"]


def num(x: float) -> str:
    """A stored (6 significant digits) value in a form JS writes identically: toExponential(5), exponent as int."""
    m, e = f"{float(x):.5e}".split("e")
    return f"{m}e{int(e)}"


def digest(lines: list[str]) -> str:
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:20]


def versions_digest(enc: dict | None) -> dict | None:
    if not enc:
        return None
    lines = [f"{enc['periods'][p]}|{enc['dates'][d]}|{num(v)}" for p, d, v in zip(enc["p"], enc["d"], enc["v"])]
    return {"n": enc["n_versions"], "n_periods": len(enc["periods"]), "n_dates": len(enc["dates"]),
            "n_revised_periods": enc["n_revised_periods"], "first_known": enc["first_known"],
            "last_known": enc["last_known"], "sha": digest(lines)}


def backfilled_on(rows: pd.DataFrame, day: str, today: pd.Timestamp) -> bool:
    """D before the day the backfilled rows' vintage became known: their latest known_from, or their fetch day."""
    b = rows[(rows["source"] == "backfill") & (rows["known_from"] <= today)]
    if b.empty:
        return False
    until = max(pd.Timestamp(b["known_from"].max()).normalize(), pd.to_datetime(b["fetched_at"]).max().ceil("D"))
    return pd.Timestamp(day) < until


def asof_digest(key: str, day: str, rows: pd.DataFrame) -> dict:
    s = observations.as_of(key, pd.Timestamp(day), rows).dropna()
    lines = [f"{p}|{num(V._r(v))}" for p, v in sorted((str(p), v) for p, v in s.items())]
    return {"n": len(lines), "sha": digest(lines)}


class _Record(D.Record):
    """Record with month-end computations shared between replays (compute(month) depends only on ctx)."""

    shared: dict[str, dict] = {}

    def compute(self, month: str) -> dict:
        if month not in self.shared:
            self.shared[month] = S._clean(S.compute(S.month_end(month), self.ctx))
        self._computed[month] = self.shared[month]  # export.month_branches reads _computed
        return self.shared[month]


def _snapshots_until(src: Path, day: str, dst: Path) -> Path:
    """A snapshots directory with only the live snapshots that existed on `day` (their date <= day)."""
    dst.mkdir(parents=True, exist_ok=True)
    for f in sorted(Path(src).glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if str(d.get("date", "9999"))[:10] <= day:
            shutil.copy(f, dst / f.name)
    return dst


def _prefix(replayed: list, today: list, what: str) -> int:
    assert replayed == today[: len(replayed)], f"{what}: the replay on D is not a prefix of today's bundle"
    return len(replayed)


def _columns_prefix(replayed: dict, today: dict, what: str) -> int:
    n = len(replayed["months"])
    for k, col in replayed.items():
        if isinstance(col, list):
            assert col == today[k][:n], f"{what}.{k}: the replay on D is not a prefix of today's bundle"
    return n


def _json_roundtrip(x):
    return json.loads(json.dumps(x, ensure_ascii=False))


def golden(ctx, snapshots_dir: Path, bundle: Path, probes: list[str], history_from: str) -> dict:
    overview = json.loads((bundle / "overview.json").read_text(encoding="utf-8"))
    branch_docs = {c: json.loads((bundle / "branch" / f"{c}.json").read_text(encoding="utf-8")) for c in catalog.BRANCHES}
    series_docs = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in sorted((bundle / "series").glob("*.json"))
                   if f.name != "index.json"}
    first_month = overview["stripes"]["months"][0]
    today = pd.Timestamp(json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))["today"])
    out_probes = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, day in enumerate(probes):
            snaps = _snapshots_until(snapshots_dir, day, Path(tmp) / f"s{i}")
            rec = _Record(ctx, snaps, pd.Timestamp(day), history_from)
            probe: dict = {"day": day}
            if rec.month < first_month:
                # the bundle's history starts later: time travel shows no record (and the replay's month must be
                # before the first month of the bundle, never inside it)
                probe["record"] = None
            else:
                branches = {}
                for code in catalog.BRANCHES:
                    cur = D.aggregate(rec.branches.get(code, {}))
                    branches[code] = {"name": catalog.BRANCHES[code], **cur, **D.change_vs_previous(cur, rec.previous(code))}
                head = E.headline(rec, branches)
                stripes = _json_roundtrip(E.stripes(rec))
                n_months = _prefix(stripes["months"], overview["stripes"]["months"], "stripes.months")
                assert stripes["kind"] == overview["stripes"]["kind"][:n_months], "stripes.kind"
                for r, t in zip(stripes["rows"], overview["stripes"]["rows"]):
                    for k in ("index", "state", "n_series"):
                        assert r[k] == t[k][:n_months], f"stripes {r['code']}.{k}"
                hist = {}
                for code in catalog.BRANCHES:
                    hist[code] = _prefix(_json_roundtrip(rec.history[code]), branch_docs[code]["history"], f"{code}.history")
                mh = _json_roundtrip(E.measure_history(rec))
                mh_n = {}
                for key, doc in series_docs.items():
                    today_mh = doc.get("measure_history")
                    if key in mh:
                        mh_n[key] = _columns_prefix(mh[key], today_mh, f"{key}.measure_history")
                    else:
                        mh_n[key] = 0
                probe["record"] = {"month": rec.month, "kind": rec.kind, "sentence": head["sentence"],
                                   "change_sentence": head["change_sentence"], "n_months": n_months,
                                   "history": hist, "measure_history": mh_n}
            vs = {}
            for key, doc in series_docs.items():
                rows = ctx.rows(key)
                freq = doc.get("freq")
                try:
                    agg = rule_for(key, ctx).agg
                except KeyError:
                    agg = None
                entry = {"versions": versions_digest(V.encode(rows, pd.Timestamp(day), agg=agg if freq == "D" else None))}
                if freq != "D":
                    entry["as_of"] = asof_digest(key, day, rows)
                entry["backfilled"] = backfilled_on(rows, day, today)
                vs[key] = entry
            probe["series"] = vs
            out_probes.append(probe)
    return {"about": "W9 time-travel replay on each probe day; see web/fixtures/gen_timetravel_golden.py",
            "probes": out_probes}


def fixture_golden() -> dict:
    from ai_tracker.site_bundle import synthetic as SY

    _Record.shared = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ctx = SY.context(root)
        paths = SY.write_inputs(root, ctx)
        return golden(ctx, paths["snapshots_dir"], FIXTURES, FIXTURE_PROBES, SY.HISTORY_FROM)


def render(g: dict | None = None) -> str:
    return json.dumps(g if g is not None else fixture_golden(), ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"


def main(argv: list[str]) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", nargs=2, metavar=("BUNDLE", "OUT"), help="replay the real table against a real bundle")
    a = ap.parse_args(argv)
    if a.real:
        from ai_tracker.state.measures import Context

        _Record.shared = {}
        ctx = Context(observations.load())
        g = golden(ctx, S.SNAPSHOTS, Path(a.real[0]), REAL_PROBES, D.HISTORY_FROM)
        out = Path(a.real[1])
        out.write_text(render(g), encoding="utf-8")
    else:
        out = OUT
        out.write_text(render(), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1024:.1f} kB)")


if __name__ == "__main__":
    main(sys.argv[1:])
