"""Provisional, SYNTHETIC site_bundle fixture for web/ until W3 puts its fixtures in web-data-fixtures/.

Usage: python web/fixtures/gen_provisional.py web/fixtures/provisional  (deterministic; no real values)
"""
import json, math, random, sys
from pathlib import Path

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
random.seed(7)
BR = {"G1": "Förmåga", "G2": "Kostnad", "G3": "Användning", "G4": "Intäkter", "G5": "Investeringar och finansiering",
      "G6": "Utbud och halvledare", "G7": "Fysiska flaskhalsar", "G8": "Arbete och produktivitet",
      "G9": "Forskning och öppet ekosystem"}
Q = {"G1": "Ökar förmågan i samma takt?", "G2": "Hur snabbt faller priset per förmåga?",
     "G3": "Hur brett och djupt används AI?", "G4": "Går det att tjäna pengar på det?",
     "G5": "Hur stor är capex, och hur finansieras den?", "G6": "Hur går leveranskedjan?",
     "G7": "Räcker kraft och nät?", "G8": "Syns effekter i ekonomin?", "G9": "Hur snabbt rör sig fältet?"}
LEADS = [("L1", "Förmåga och kostnad", ["G1", "G2"]), ("L2", "Användning", ["G3"]), ("L3", "Intäkter", ["G4"]),
         ("L4", "Kontrakterad efterfrågan", ["G4"]), ("L5", "Investeringar och finansiering", ["G5"]),
         ("L6", "Halvledare och minne", ["G6"]), ("L7", "El och byggen", ["G7", "G5"]), ("L8", "Effekter", ["G8"]),
         ("L9", "Forskning och förväntningar", ["G9"])]
months = [f"{y}-{m:02d}" for y in (2024, 2025, 2026) for m in range(1, 13)][10:34]  # 2024-11 .. 2026-10

def state(i):
    return None if i is None else ("accelererar" if i >= 0.67 else "bromsar in" if i <= 0.33 else "stabil")

record = {"status": "reconstructed", "kind": "rekonstruerad", "label": "rekonstruerad historik, inte ett skarpt underlag",
          "month": months[-1], "date": "2026-10-31", "file": None, "first_live_date": "2026-11-30", "live_months": [],
          "recon_label": "rekonstruerad historik, inte ett skarpt underlag"}
rows, tiles = [], []
for j, (code, name) in enumerate(BR.items()):
    if code == "G8":
        idx = [None] * 6 + [round(min(1, max(0, 0.3 + 0.03 * k + random.uniform(-0.1, 0.1))), 4) for k in range(18)]
    else:
        ph = j * 0.7
        idx = [round(min(1, max(0, 0.5 + 0.35 * math.sin(ph + k / 5) + random.uniform(-0.08, 0.08))), 4) for k in range(24)]
    n = [None if v is None else 3 + j % 4 for v in idx]
    rows.append({"code": code, "name": name, "index": idx, "state": [state(v) for v in idx], "n_series": n})
    cur, prev = idx[-1], idx[-2]
    tiles.append({"code": code, "name": name, "question": Q[code], "index": cur, "state": state(cur), "n_series": n[-1],
                  "previous": {"index": prev, "state": state(prev)}, "delta_index": round(cur - prev, 4),
                  "state_changed": state(cur) != state(prev)})
counts = {s: sum(t["state"] == s for t in tiles) for s in ("accelererar", "stabil", "bromsar in")}
headline = {"month": months[-1], "n_branches": 9, "n_with_state": sum(counts.values()), "counts": counts,
            "changes": [{"code": t["code"], "name": t["name"], "from": t["previous"]["state"], "to": t["state"]}
                        for t in tiles if t["state_changed"]],
            "sentence": f"Av {sum(counts.values())} grenar med tillstånd: {counts['accelererar']} accelererar, "
                        f"{counts['stabil']} är stabila och {counts['bromsar in']} bromsar in.",
            "change_sentence": "Testdata: meningen är syntetisk."}
calendar = [{"id": "n1", "label": "N1", "title": "Capex för de fyra största hyperscalers", "champion": "B1",
             "next_origin": "2027-01-20", "next_period": "2026Q4", "n_live": 0},
            {"id": "n2", "label": "N2", "title": "TSMC:s månadsintäkter", "champion": "B3",
             "next_origin": "2026-12-05", "next_period": "2026-11", "n_live": 0}]
overview = {"record": record, "headline": headline, "branches": tiles,
            "stripes": {"months": months, "kind": ["rekonstruerad"] * 24, "rows": rows,
                        "thresholds": {"braking_at_most": 0.33, "accelerating_at_least": 0.67}},
            "calendar": calendar, "regime": {"available": False, "blocks": []},
            "facts": {"n_series": 2, "n_published": 2, "n_withheld": 1, "n_nowcasts": 2, "table_max_fetched_at": "2026-11-24"}}

def series(key, label, unit, base, growth):
    periods = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13)][:58]
    vals = [round(base * math.exp(growth * k / 12 + 0.05 * math.sin(k / 3)) * (1 + random.uniform(-0.02, 0.02)), 3) for k in range(len(periods))]
    return {"key": key, "label": label, "unit": unit, "freq": "M", "branch": "G6", "branch_name": BR["G6"],
            "question": Q["G6"], "source": "Syntetisk testdata", "source_family": "test",
            "license": {"short": "testdata", "text": "Syntetiska värden för gränssnittstester, inte data.",
                        "attribution": "Syntetisk testdata."},
            "revised": True, "core": True, "counted": True,
            "measure": {"pace": 12.3, "change_in_pace": 2.1, "pace_percentile": 0.81, "direction": 1, "valid": True},
            "levels": {"as_of": "2026-11-24", "periods": periods, "values": vals}, "versions": None}

S = [series("test_semis_m", "Testserie: halvledarproduktion (syntetisk)", "index", 100, 0.08),
     series("test_revenue_m", "Testserie: månadsintäkt (syntetisk)", "mdr", 200, 0.25)]
index = {"as_of": "2026-11-24", "n": len(S), "series": [
    {"key": s["key"], "label": s["label"], "branch": s["branch"], "freq": s["freq"], "unit": s["unit"],
     "source_family": "test", "license": "testdata", "core": True, "counted": True, "reconciliation": False,
     "first_period": s["levels"]["periods"][0], "latest_period": s["levels"]["periods"][-1], "n_versions": 1,
     "direction": 1, "valid": True} for s in S]}

def branch(code):
    t = next(t for t in tiles if t["code"] == code)
    r = next(r for r in rows if r["code"] == code)
    return {"record": record, **t, "history": [{"month": m, "index": i, "state": s} for m, i, s in zip(months, r["index"], r["state"])],
            "series_counted": [{"series": s["key"], "label": s["label"], "direction": 1} for s in S] if code == "G6" else [],
            "series_withheld": [{"key": "test_withheld_m", "label": "Testserie som hålls inne", "why": "licens ej kontrollerad"}] if code == "G6" else []}

qs = [[0.025, 228.0], [0.10, 236.5], [0.25, 243.0], [0.5, 249.0], [0.75, 255.5], [0.90, 262.0], [0.975, 271.0]]
nowcast = {"record": record, "publishable": True, "id": "n2", "label": "N2", "title": "TSMC:s månadsintäkter (testdata)",
           "frequency": "månad", "champion": "B3", "next_origin": "2026-12-05", "next_period": "2026-11",
           "unit": "mdr TWD", "forecasts": [],
           "example": {"status": "backtest", "period": "2026-10", "origin": "2026-11-05", "quantiles": qs, "outcome": 252.4},
           "history": [{"period": p, "f": 200 + 2 * k, "lo95": 185 + 2 * k, "lo80": 190 + 2 * k, "lo50": 195 + 2 * k,
                        "hi50": 205 + 2 * k, "hi80": 210 + 2 * k, "hi95": 216 + 2 * k,
                        "y": round(200 + 2 * k + random.uniform(-9, 9), 1)} for k, p in enumerate(months[-18:])]}
n1 = {"record": record, "publishable": True, "id": "n1", "label": "N1", "title": "Capex för de fyra största hyperscalers (testdata)",
      "frequency": "kvartal", "champion": "B1", "next_origin": "2027-01-20", "next_period": "2026Q4", "forecasts": []}
method = {"record": record, "rules": {"deadband_sd": 0.25, "accelerating_at_least": 0.67, "braking_at_most": 0.33},
          "leads": [{"code": c, "name": n, "branches": b} for c, n, b in LEADS],
          "branches": [{"code": c, "name": n, "question": Q[c]} for c, n in BR.items()]}
flow = {"record": record, "leads": [{"code": c, "name": n, "branches": b} for c, n, b in LEADS]}
manifest = {"bundle": "ai-rollout-tracker/site-bundle", "version": "1.0.0", "synthetic": True, "provisional": True,
            "note": "Provisorisk, syntetisk fixture från spår W4. Ersätts av W3:s web-data-fixtures/. Inga riktiga värden.",
            "built_utc": "2026-11-24T00:00:00Z", "git_sha": "0000000",
            "repo": "https://github.com/birdiebook/ai-rollout-tracker", "snapshot": record, "files": []}
docs = {"overview.json": overview, "flow.json": flow, "method.json": method, "series/index.json": index,
        "nowcast/n2.json": nowcast, "nowcast/n1.json": n1,
        "withheld.json": {"withheld": [{"key": "test_withheld_m", "label": "Testserie som hålls inne", "why": "licens ej kontrollerad"}], "n": 1}}
for code in BR: docs[f"branch/{code}.json"] = branch(code)
for s in S: docs[f"series/{s['key']}.json"] = {"record": record, **s}
manifest["files"] = [{"path": p} for p in sorted(docs)]
docs["manifest.json"] = manifest
for p, d in docs.items():
    f = out / p; f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
print(len(docs), "documents")
