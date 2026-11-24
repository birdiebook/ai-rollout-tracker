"""E3: the quarterly report "Läget i AI-utrullningen" (kvartalsrapport), in Swedish, generated deterministically.

    python -m ai_tracker.quarterly --quarter YYYYQn [--reconstructed] [--out-dir D] [--stdout]
    python -m ai_tracker.quarterly --if-quarter-end YYYY-MM     (CI: writes the report only when the month ends a quarter)

Writes docs/kvartalsrapport/<YYYYQn>.md. No LLM and no clock: the same inputs give the same bytes.

Inputs (and nothing else):
- Branch states, indices, per-series measures and reconciliation ratios come from the quarter's three monthly
  snapshots (snapshots/<YYYY-MM>.json). Without all three the report is refused, unless `--reconstructed`: then each
  missing month is the as-of backcast at its month end (same code as the monthly letter, ai_tracker.letter), and the
  report says "rekonstruerad" in its title, in a banner and per month. The comparison point is the month before the
  quarter: its snapshot, or a reconstruction labelled "(rekonstruerad)".
- Nowcasts: the committed forecast files (forecasts/<nowcast>/) with origin on or before the quarter end, scored by
  `pipeline.score` against the observation table cut to the information set at the quarter end (first vintage).
- Regime (C4): the section "regime" in the live snapshots up to the quarter end, read as stored (F-D1: never
  recomputed). The reporting rules F-D2 (shift) and F-D4 (break) are applied to the stored sequence when a snapshot
  does not store the reported state itself. Absent section: the report says so and shows no probability.
- Data and method: the observation table cut to the quarter end; dated headings in docs/mattregister.md and
  docs/beslutslogg.md, review headers in docs/granskning/*.md, BLOCKED rows in docs/kallor/*.md, the lead table in
  docs/steg2/plan.md and the A5 table in the register.

Wording is neutral (the letter's rule and its banned-words test). Licences as in the letter: a series with
Spec.publish=False is never named and none of its values are shown, except in "Visas inte av licensskäl".
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ai_tracker import catalog, config, letter as L, observations, pipeline
from ai_tracker.nowcast import intervals
from ai_tracker.site import data as D
from ai_tracker.state import branch as BR
from ai_tracker.state import register as R
from ai_tracker.state import snapshot as S
from ai_tracker.state.measures import Context

REPORTS = config.REPO / "docs" / "kvartalsrapport"
DOCS = config.REPO / "docs"
RECON, LIVE = L.RECON, L.LIVE
QUARTER_SV = ["första", "andra", "tredje", "fjärde"]
BASELINE = "B0"  # the naive baseline of every target (random walk / latest value)
GUIDANCE = "B2"  # the companies' own guidance, where the target has it (N1, N2, N3)
BLOCK_LABEL = {"capex": "capex och leverantörsled", "demand": "efterfrågan"}
REVISION_ROWS = 12
HEADING = re.compile(r"^#{2,3} (\d{4}-\d{2}-\d{2}) [–-] (.+?)\s*$")
REVIEW_HEAD = re.compile(r"Granskningsspår (R\d+), (\d{4}-\d{2}-\d{2})")

# docs/steg2/plan.md, section 2 (used if the table cannot be parsed)
LEADS_FALLBACK = {
    "L1": ("Förmåga och kostnad", ["G1", "G2"]), "L2": ("Användning", ["G3"]), "L3": ("Intäkter", ["G4"]),
    "L4": ("Kontrakterad efterfrågan", []), "L5": ("Investeringar och finansiering", ["G5"]),
    "L6": ("Halvledare och minne", ["G6"]), "L7": ("El och byggen", ["G7", "G5"]), "L8": ("Effekter", ["G8"]),
    "L9": ("Forskning och förväntningar", ["G9"]),
}
# docs/mattregister.md, "2026-11-23 – A5" (used if the table cannot be parsed)
RATIO_LEADS_FALLBACK = {"x_capex_cloud": ["L3", "L5"], "x_rpo_cover": ["L4", "L5"], "x_nvda_capex": ["L5", "L6"],
                        "x_debt_capex": ["L5"], "x_capex_ocf": ["L5"]}


class NoSnapshot(L.NoSnapshot):
    pass


def quarter_sv(q) -> str:
    q = pd.Period(q, freq="Q")
    return f"{QUARTER_SV[q.quarter - 1]} kvartalet {q.year}"


def path_for(quarter, out_dir: Path | None = None) -> Path:
    return Path(out_dir or REPORTS) / f"{pd.Period(quarter, freq='Q')}.md"


def quarter_of_month_end(month) -> pd.Period | None:
    """The quarter that `month` (YYYY-MM) closes, or None when it is not the last month of a quarter."""
    m = pd.Period(month, freq="M")
    return m.asfreq("Q") if m.month % 3 == 0 else None


# ------------------------------------------------------------------ inputs


@dataclass
class Month:
    month: str
    date: pd.Timestamp
    kind: str  # LIVE | RECON
    doc: dict
    file: str | None


@dataclass
class Inputs:
    quarter: pd.Period
    start: pd.Timestamp
    end: pd.Timestamp
    kind: str  # LIVE when all three months are live snapshots, else RECON
    months: list[Month]  # the three months of the quarter
    base: Month | None  # the month before the quarter
    ctx: Context  # the table cut to the information set at the quarter end
    forecasts: Path
    docs: Path
    regime: list[tuple[str, dict]]  # (month, regime section) of the live snapshots up to the quarter end
    last: L.Inputs  # the quarter's last month as a letter input (for the letter's building blocks)


def _month(month: pd.Period, snaps: Path, ctx: Context, allow_recon: bool) -> Month | None:
    date = S.month_end(month)
    path = snaps / f"{month}.json"
    doc = L._read(path)
    if doc is not None:
        return Month(str(month), date, LIVE, doc, f"snapshots/{path.name}")
    if not allow_recon:
        return None
    return Month(str(month), date, RECON, L.reconstruct(date, L.cut_context(ctx, date, None)), None)


def gather(quarter, ctx: Context, snapshots_dir: Path | None = None, forecasts_dir: Path | None = None,
           docs_dir: Path | None = None, reconstructed: bool = False, today=None) -> Inputs:
    q = pd.Period(quarter, freq="Q")
    snaps = Path(snapshots_dir or S.SNAPSHOTS)
    start, end = q.start_time.normalize(), q.end_time.normalize()
    months = list(pd.period_range(q.asfreq("M", "s"), q.asfreq("M", "e"), freq="M"))
    live = [m for m in months if (snaps / f"{m}.json").is_file()]
    if reconstructed and len(live) == len(months):
        raise ValueError(f"all three snapshots of {q} exist: the report is written from them; a reconstructed "
                         "report would contradict the record")
    if not reconstructed and len(live) < len(months):
        missing = ", ".join(str(m) for m in months if m not in live)
        raise NoSnapshot(f"no snapshot for {missing} ({snaps}). The quarterly report is written from the quarter's "
                         "three monthly snapshots; use --reconstructed for a report from the as-of backcast "
                         "(labelled rekonstruerad)")
    today = pd.Timestamp(today).normalize() if today is not None else S.utc_today()
    if end > today:
        raise ValueError(f"{q} has not ended (quarter end {end.date()}, today {today.date()} UTC)")
    mm = [_month(m, snaps, ctx, True) for m in months]
    base = _month(months[0] - 1, snaps, ctx, len(ctx.table) > 0) if len(ctx.table) else None
    kind = LIVE if all(m.kind == LIVE for m in mm) else RECON
    last = mm[-1]
    cut = L.cut_context(ctx, end, last.doc.get("table_max_fetched_at") if last.kind == LIVE else None)
    regime = []
    for f in sorted(snaps.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].json")):
        if f.stem <= str(months[-1]):
            sec = (json.loads(f.read_text(encoding="utf-8")) or {}).get("regime")
            if sec:
                regime.append((f.stem, sec))
    prev = base.doc if base else None
    linp = L.Inputs(last.month, last.date, last.kind, last.doc, prev, base.kind if base else None, cut,
                    Path(forecasts_dir or config.REPO / "forecasts"), last.file)
    return Inputs(q, start, end, kind, mm, base, cut, Path(forecasts_dir or config.REPO / "forecasts"),
                  Path(docs_dir or DOCS), regime, linp)


# ------------------------------------------------------------------ helpers


n = L.n


def mlabel(m: Month | None) -> str:
    if m is None:
        return "–"
    return m.month + (" (rekonstruerad)" if m.kind == RECON else "")


def bstate(m: Month | None, code: str) -> dict:
    return ((m.doc.get("branches") or {}).get(code) or {}) if m else {}


def state_cell(b: dict) -> str:
    if not b:
        return "–"
    idx = b.get("index")
    return f"{n(idx, 2) if idx is not None else '–'} {b.get('state') or R.STATE_FEW}"


def publishable(key, inp: Inputs) -> bool:
    return D.publishable(key, inp.ctx)


def name(key, inp: Inputs) -> str:
    return L.series_name(key, inp.ctx)


def table(head: list[str], rows: list[list[str]]) -> list[str]:
    return ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|",
            *["| " + " | ".join(r) + " |" for r in rows], ""]


def sections(path: Path) -> list[tuple[pd.Timestamp, str, str]]:
    """Dated headings ("## YYYY-MM-DD – title" or "###") of a Markdown file: (date, title, body)."""
    if not path.is_file():
        return []
    out, cur = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = HEADING.match(line)
        if m:
            if cur:
                out.append(cur)
            cur = [pd.Timestamp(m.group(1)), m.group(2), []]
        elif line.startswith("## ") or line.startswith("# "):
            if cur:
                out.append(cur)
            cur = None
        elif cur is not None:
            cur[2].append(line)
    if cur:
        out.append(cur)
    return [(d, t, "\n".join(b)) for d, t, b in out]


def in_quarter(d: pd.Timestamp, inp: Inputs) -> bool:
    return inp.start <= d <= inp.end


def leads(inp: Inputs) -> dict[str, tuple[str, list[str]]]:
    path = inp.docs / "steg2" / "plan.md"
    out = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\| \*\*(L\d) ([^*]+)\*\* \|[^|]*\|([^|]*)\|", line)
            if m:
                out[m.group(1)] = (m.group(2).strip(), re.findall(r"G\d", m.group(3)))
    return out or dict(LEADS_FALLBACK)


def ratio_leads(inp: Inputs) -> dict[str, list[str]]:
    path = inp.docs / "mattregister.md"
    out = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\| `(x_\w+)` \|.*\| (L\d(?:\s*[–-]\s*L\d)?) \|\s*$", line)
            if m:
                out[m.group(1)] = re.findall(r"L\d", m.group(2))
    return out or dict(RATIO_LEADS_FALLBACK)


# ------------------------------------------------------------------ header


def header(inp: Inputs) -> list[str]:
    title = f"# Läget i AI-utrullningen, {quarter_sv(inp.quarter)}" + (" (rekonstruerad)" if inp.kind == RECON else "")
    cmd = f"`python -m ai_tracker.quarterly --quarter {inp.quarter}{' --reconstructed' if inp.kind == RECON else ''}`"
    lines = [title, ""]
    if inp.kind == RECON:
        recon = [m.month for m in inp.months if m.kind == RECON]
        lines += [f"> **Rekonstruerad, inte ett skarpt underlag.** Det finns ingen skarp ögonblicksbild för "
                  f"{', '.join(recon)}. De månaderna är beräknade i efterhand vid varje månadsslut med samma kod och "
                  f"bara data som var känd då, men med dagens versioner av serier som saknar sparade versioner. "
                  f"Revideringar kan därför läcka in. Det skarpa registret är ögonblicksbilderna i `snapshots/`.", ""]
    src = []
    for m in inp.months:
        if m.kind == LIVE:
            src.append(f"{m.month}: skarp `{m.file}` (skapad {m.doc.get('created_utc', '–')}, git "
                       f"{m.doc.get('git_sha', '–')}, data hämtad senast {m.doc.get('table_max_fetched_at') or '–'})")
        else:
            src.append(f"{m.month}: rekonstruerad vid {m.date.date()}")
    lines += [f"*Kvartalet {inp.start.date()}–{inp.end.date()}. Genererat av {cmd} från månadernas "
              f"ögonblicksbilder ({'; '.join(src)}), jämförelsemånaden {mlabel(inp.base)}, de committade "
              f"prognosfilerna, ögonblicksbildernas regimavsnitt och observationstabellen kapad vid "
              f"{inp.end.date()}. Ingen språkmodell. Beskrivande, inga orsaksslutsatser.*", ""]
    return lines


# ------------------------------------------------------------------ 1. summary


def _flips(code: str, a: Month | None, b: Month) -> int:
    pa, pb = L.by_key(bstate(a, code)), L.by_key(bstate(b, code))
    return sum(1 for k, m in pb.items() if k in pa and m["_counted"] and pa[k]["_counted"]
               and m.get("direction") != pa[k].get("direction"))


def summary(inp: Inputs, nowcast_news: str, regime_news: str) -> list[str]:
    path = [inp.base, *inp.months]
    last = inp.months[-1]
    lines = ["## Sammanfattning", ""]
    changed, moved, seqs = [], [], []
    for code, bname in catalog.BRANCHES.items():
        a, b = bstate(inp.base, code), bstate(last, code)
        if a and a.get("state") != b.get("state"):
            changed.append(f"{code} {bname} {a.get('state')} → {b.get('state')}")
        if a.get("index") is not None and b.get("index") is not None and round(b["index"] - a["index"], 2) != 0:
            moved.append((-abs(b["index"] - a["index"]), code, b["index"] - a["index"]))
        steps = [(m.month, bstate(m, code).get("state")) for m in path if m is not None]
        k = sum(1 for (_, s0), (_, s1) in zip(steps, steps[1:]) if s0 != s1)
        if k >= 2:
            seqs.append(f"{code} " + " → ".join(f"{s} ({mo})" for mo, s in steps))
    if inp.base is None:
        lines.append("- Ingen månad före kvartalet att jämföra med.")
    elif changed:
        lines.append(f"- Tillståndet vid kvartalets slut skilde sig från {mlabel(inp.base)} i {len(changed)} av "
                     f"{len(catalog.BRANCHES)} grenar: " + "; ".join(changed) + ".")
    else:
        lines.append(f"- Inget tillstånd vid kvartalets slut skilde sig från {mlabel(inp.base)}.")
    if seqs:
        lines.append("- Grenar som bytte tillstånd mer än en gång under kvartalet: " + "; ".join(seqs) + ".")
    moved.sort()
    if moved:
        lines.append("- Störst indexförändring över kvartalet: "
                     + ", ".join(f"{c} {n(d, 2, signed=True)}" for _, c, d in moved[:3]) + ".")
    elif inp.base is not None:
        lines.append("- Inget index ändrades över kvartalet (avrundat till två decimaler).")
    groups: dict[str, list[str]] = {}
    for code in catalog.BRANCHES:
        groups.setdefault(bstate(last, code).get("state") or R.STATE_FEW, []).append(code)
    order = [R.STATE_ACCEL, R.STATE_STABLE, R.STATE_BRAKE, R.STATE_FEW]
    parts = [f"{st} {', '.join(groups[st])}" for st in order if st in groups]
    parts += [f"{st} {', '.join(v)}" for st, v in groups.items() if st not in order]
    lines.append(f"- Läget vid kvartalets slut, {mlabel(last)}: " + "; ".join(parts) + ".")
    lines += [f"- {nowcast_news}", f"- {regime_news}", ""]
    head = ["Gren", *[mlabel(m) for m in path if m is not None], "Över kvartalet", "Serier som bytt riktning"]
    rows = []
    for code, bname in catalog.BRANCHES.items():
        a, b = bstate(inp.base, code), bstate(last, code)
        if a.get("index") is not None and b.get("index") is not None:
            over = n(b["index"] - a["index"], 2, signed=True)
        else:
            over = "–"
        if a and a.get("state") != b.get("state"):
            over += f"; {a.get('state')} → {b.get('state')}"
        elif a:
            over += "; samma tillstånd"
        rows.append([f"{code} {bname}", *[state_cell(bstate(m, code)) for m in path if m is not None], over,
                     n(_flips(code, inp.base, last), 0) if inp.base else "–"])
    lines += ["Diffusionsindex och tillstånd vid varje månadsslut (index; tillstånd). Sista kolumnen: räknade serier "
              "vars riktning skilde sig mellan jämförelsemånaden och kvartalets sista månad.", ""]
    return lines + table(head, rows)


# ------------------------------------------------------------------ 2. flow


def ratio_rows(keys: list[str], inp: Inputs, rl: dict[str, list[str]]) -> tuple[list[list[str]], int]:
    cur = {m["series"]: m for m in (inp.months[-1].doc.get("reconciliations") or {}).get("series", [])}
    old = {m["series"]: m for m in ((inp.base.doc if inp.base else {}).get("reconciliations") or {}).get("series", [])}
    rows, withheld = [], 0
    for key in keys:
        m = cur.get(key)
        if m is None:
            continue
        if not publishable(key, inp):
            withheld += 1
            continue
        o = old.get(key) or {}
        lvl0, lvl1 = o.get("level"), m.get("level")
        since = "–"
        if lvl0 is not None and lvl1 is not None:
            since = f"{L.value_text(lvl0)} ({o.get('latest_period') or '–'})"
        rows.append([f"{name(key, inp)} (`{key}`)", "–".join(rl.get(key, [])) or "–",
                     str(m.get("latest_period") or "–"), L.value_text(lvl1), L.pace_text(m), L.change_text(m), since])
    return rows, withheld


def flow(inp: Inputs) -> list[str]:
    ld, rl = leads(inp), ratio_leads(inp)
    lines = ["## Flödet", "",
             "Leden L1–L9 enligt planen (`docs/steg2/plan.md`, avsnitt 2): grenarnas tillstånd över kvartalet och de "
             "härledda kvoterna mellan leden (avstämningar, A5 i `docs/mattregister.md`). Kvoternas takt är "
             "årsförändringen i log(kvot) ×100. De räknas inte i något diffusionsindex.", ""]
    path = [m for m in [inp.base, *inp.months] if m is not None]
    for lead, (lname, branches) in ld.items():
        bl = ", ".join(branches) if branches else "ingen egen gren"
        lines += [f"### {lead} {lname} ({bl})", ""]
        for code in branches:
            states = [bstate(m, code) for m in path]
            idx = " → ".join(n(s.get("index"), 2) if s.get("index") is not None else "–" for s in states)
            sts = [s.get("state") or R.STATE_FEW for s in states]
            st = f"{sts[-1]} hela perioden" if len(set(sts)) == 1 else " → ".join(sts)
            lines.append(f"- {code} {catalog.BRANCHES.get(code, '')}: {st} (index {idx}).")
        keys = [k for k, ls in rl.items() if lead in ls]
        rows, withheld = ratio_rows(keys, inp, rl)
        if rows:
            lines += ["- Avstämningar vid kvartalets slut:", ""]
            lines += table(["Kvot", "Led", "Senaste period", "Nivå", "Takt (log×100 per år)", "Förändring i takt",
                            f"Nivå i {mlabel(inp.base)}"], rows)
        elif not keys:
            lines.append("- Inga registrerade avstämningar för ledet.")
        else:
            lines.append("- De registrerade avstämningarna för ledet har inga data som får visas vid kvartalets slut.")
        if withheld:
            lines.append(f"- {L._plural(withheld, 'avstämning', 'avstämningar')} visas inte av licensskäl.")
        lines.append("")
    return lines


# ------------------------------------------------------------------ 3. forecasts


def _err_unit(sub: str) -> str:
    return "procentenheter, prognos − utfall" if sub in pipeline.ADDITIVE else "100 × (log prognos − log utfall)"


def champion_decisions(label: str, inp: Inputs) -> list[str]:
    """Dated entries in the decision log and the register in the quarter whose heading names the target label and a
    champion ("huvudmodell"), with the reviews they cite."""
    out = []
    for rel in ("beslutslogg.md", "mattregister.md"):
        for d, title, body in sections(inp.docs / rel):
            if not in_quarter(d, inp) or "huvudmodell" not in title.lower() or not re.search(rf"\b{label}\b", title):
                continue
            refs = sorted(set(re.findall(r"docs/granskning/[\w.-]+\.md", body)))
            for r in sorted(set(re.findall(r"\b(R\d+)\b", title + " " + body))):
                refs += sorted(f"docs/granskning/{p.name}" for p in (inp.docs / "granskning").glob(f"{r.lower()}_*.md")
                               if f"docs/granskning/{p.name}" not in refs)
            cite = f" Granskning: {', '.join(f'`{r}`' for r in dict.fromkeys(refs))}." if refs else ""
            out.append(f"{d.date()} – {title} (`docs/{rel}`).{cite}")
    return out


def _metrics(scored: pd.DataFrame, variants, champion_col: bool = True) -> list[list[str]]:
    base = scored[f"err_{BASELINE}"].dropna() if f"err_{BASELINE}" in scored else pd.Series(dtype=float)
    base_mae = base.abs().mean() if len(base) else None
    keys = [intervals.level_key(x) for x in intervals.LEVELS]
    rows = []
    for v in (["champion"] if champion_col else []) + list(variants):
        e = scored[f"err_{v}"].dropna() if f"err_{v}" in scored else pd.Series(dtype=float)
        if not len(e):
            continue
        mae = e.abs().mean()
        delta = n(mae - base_mae, 2, signed=True) if base_mae is not None and v != BASELINE else "–"
        cov = []
        for k, lv in zip(keys, intervals.LEVELS):
            col = f"hit_{k}_{v}"
            hits = scored[col].dropna() if col in scored else pd.Series(dtype=float)
            if len(hits):
                lo, hi = intervals.binomial_band(len(hits), lv)
                cov.append(f"{n(hits.mean(), 2)} [{n(lo, 2)}–{n(hi, 2)}]")
            else:
                cov.append("–")
        tag = {BASELINE: " (naiv baslinje)", GUIDANCE: " (bolagens guidance)"}.get(v, "")
        rows.append([("huvudmodell" if v == "champion" else v) + tag, n(len(e), 0), n(mae, 2), n(e.mean(), 2, signed=True),
                     delta, *cov])
    return rows


def forecasts(inp: Inputs) -> tuple[list[str], str]:
    try:
        scores = pipeline.score(inp.forecasts, inp.ctx.table)
        error = None
    except Exception as e:  # noqa: BLE001 - the report still says that the scorecard failed
        scores, error = {}, f"{type(e).__name__}: {e}"
    lines = ["## Prognoser", "",
             f"Skarpa prognoser (`forecasts/<nowcast>/`) med prognosdag till och med {inp.end.date()}, mot första "
             f"publicerade utfall kända till och med samma dag. Baslinjer: {BASELINE} (naiv) för alla mål och {GUIDANCE} "
             f"(bolagens guidance) där målet har den. Täckning = andel utfall inom huvudmodellens lagrade intervall "
             f"[binomialt 90 %-band] ({intervals.REGISTER_REF}).", ""]
    n_new = n_out = 0
    for sub, (label, target, variants) in pipeline.NOWCASTS.items():
        info = D.NOWCAST_INFO.get(sub, {})
        show = publishable(target, inp)
        lines += [f"### {label} {info.get('title', '')} (`{target}`)" if show else f"### {label} {info.get('title', '')}",
                  ""]
        files = []
        for f in sorted((inp.forecasts / sub).glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            if pd.Timestamp(d["origin"]) <= inp.end:
                files.append((pd.Timestamp(d["origin"]), d, f"forecasts/{sub}/{f.name}"))
        code_champion = D.NOWCAST_MODULES[sub][2]
        if files:
            lines.append(f"Huvudmodell i den senaste skarpa prognosen till och med kvartalets slut: {files[-1][1]['champion']}. "
                         f"Prognosdag: {info.get('origin_rule', '–')}.")
        else:
            lines.append(f"Inga skarpa prognoser med prognosdag till och med {inp.end.date()}. Registrerad huvudmodell "
                         f"i koden: {code_champion}. Prognosdag: {info.get('origin_rule', '–')}.")
        lines.append("")
        new = [x for x in files if x[0] >= inp.start]
        n_new += len(new)
        if new:
            lines += [f"Nya skarpa prognoser i kvartalet ({len(new)}):", ""]
            for origin, d, p in new:
                period = d.get("quarter") or d.get("month") or d.get("period")
                if show:
                    vs = ", ".join(f"{v} {L.value_text((d.get('variants') or {}).get(v))}" for v in variants
                                   if v != d.get("champion"))
                    lines.append(f"- {period} (prognosdag {origin.date()}, `{p}`): huvudmodell {d.get('champion')} "
                                 f"{L.value_text(d.get('value'))} {d.get('unit', '')}; skuggor {vs}.")
                else:
                    lines.append(f"- {period} (prognosdag {origin.date()}, `{p}`): huvudmodell {d.get('champion')}; "
                                 "värdet visas inte av licensskäl.")
            lines.append("")
        elif files:
            lines += ["Ingen ny skarp prognos med prognosdag i kvartalet.", ""]
        df = scores.get(sub)
        if error:
            lines += [f"Scorecarden kunde inte beräknas: {error}.", ""]
        elif files and df is not None and len(df):
            df = df[df["origin"].isin({str(o.date()) for o, _d, _p in files})]
            scored = df[df["status"] == "utfall"]
            fresh = scored[pd.to_datetime(scored["known_from"]).between(inp.start, inp.end)] if len(scored) else scored
            n_out += len(fresh)
            if len(fresh):
                lines += [f"Utfall som blev kända i kvartalet (fel = {_err_unit(sub)}; positivt = prognosen låg över "
                          "utfallet):", ""]
                for r in fresh.to_dict("records"):
                    errs = ", ".join(f"{v} {n(r.get(f'err_{v}'), 2, signed=True)}" for v in variants
                                     if r.get("champion") != v)
                    vals = f"prognos {L.value_text(r['forecast'])}, utfall {L.value_text(r['outcome'])}, " if show else ""
                    lines.append(f"- {r['period']}: {vals}känt {r['known_from']}, fel huvudmodell ({r['champion']}) "
                                 f"{n(r['err_champion'], 2, signed=True)}; skuggor {errs}.")
                lines.append("")
            else:
                lines += ["Inga nya utfall i kvartalet.", ""]
            if len(scored):
                keys = [intervals.level_key(x) for x in intervals.LEVELS]
                lines += [f"Rullande utvärdering, alla {len(scored)} utfall av {len(df)} prognoser kända till och med "
                          f"{inp.end.date()} (fel = {_err_unit(sub)}):", ""]
                lines += table(["Variant", "n", "MAE", "Bias", f"MAE − MAE {BASELINE}",
                                *[f"Täckning {k} %" for k in keys]], _metrics(scored, variants))
                lines += [f"Med {L._plural(len(scored), 'utfall', 'utfall')} kan skillnaderna mellan varianterna och "
                          f"mot baslinjen vara slump. Täckningen blir meningsfull först efter många utfall.", ""]
            else:
                lines += [f"Utvärderade hittills: 0 av {len(df)}.", ""]
        changes = []
        prev = None
        for origin, d, p in files:
            if prev is not None and d.get("champion") != prev[1].get("champion") and origin >= inp.start:
                changes.append(f"från prognosdag {origin.date()} (`{p}`): {prev[1].get('champion')} → "
                               f"{d.get('champion')}")
            prev = (origin, d)
        docs = champion_decisions(label, inp)
        if changes or docs:
            lines.append("Byte av huvudmodell:")
            lines.append("")
            lines += [f"- I prognosfilerna {c}." for c in changes]
            lines += [f"- Beslut {x}" for x in docs]
            lines.append("")
        else:
            lines += ["Inget byte av huvudmodell i kvartalet (prognosfilerna, beslutsloggen och registret).", ""]
    d2 = sorted((inp.forecasts / "d2").glob("**/*.json")) if (inp.forecasts / "d2").is_dir() else []
    lines += ["### D2 Prognoser 1–8 kvartal", "",
              (f"{L._plural(len(d2), 'skarp prognosfil', 'skarpa prognosfiler')} i `forecasts/d2/`. " if d2 else
               "Inga skarpa prognosfiler för D2 (`forecasts/d2/`). ") +
              "Med 6 prognosdagar i holdouten görs inget test, och V_kedja går in som skugga (registret 2026-11-24). "
              "Utvecklingsresultat: `docs/resultat/d2_utveckling.md`.", ""]
    news = (f"Prognoser: {L._plural(n_new, 'ny skarp prognos', 'nya skarpa prognoser')} och "
            f"{L._plural(n_out, 'nytt utfall', 'nya utfall')} i kvartalet.")
    return lines, news


# ------------------------------------------------------------------ 4. regime


def _regime_frames(inp: Inputs) -> tuple[pd.DataFrame, pd.DataFrame]:
    ms_rows, b_rows = [], []
    for month, sec in inp.regime:
        date = S.month_end(month)
        for block, r in (sec.get("ms") or {}).items():
            ms_rows.append({"date": date, "month": month, "block": block, **r})
        for r in sec.get("bocpd") or []:
            b_rows.append({"date": date, "month": month, **r})
    return pd.DataFrame(ms_rows), pd.DataFrame(b_rows)


def _s(x) -> str | None:
    return x if isinstance(x, str) and x else None


def _p(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def regime(inp: Inputs) -> tuple[list[str], str]:
    from ai_tracker.regime import realtime as rt  # lazy: the factor model is only needed with a regime section

    lines = ["## Regim", ""]
    qmonths = [m.month for m in inp.months]
    in_q = [month for month, _ in inp.regime if month in qmonths]
    if not in_q:
        lines += ["Ögonblicksbilderna för kvartalet har inget regimavsnitt (C4). Regimmodellen ansluts till "
                  "ögonblicksbilden först när holdouten är öppnad (`docs/steg2/c4_spec.md`, avsnitt 1), och ett "
                  "rekonstruerat månadsläge har inget. Ingen sannolikhet för inbromsning och inget strukturbrott "
                  "redovisas för kvartalet, och inget räknas om här.", ""]
        return lines, "Regim: inget regimavsnitt i kvartalets ögonblicksbilder."
    ms_f, b_f = _regime_frames(inp)
    lines += ["Markov-switching per faktorblock (C3:s utjämnade faktorbana) och BOCPD per räknad kärnserie, lagrade i "
              "varje skarp ögonblicksbild och aldrig omräknade (F-D1). Rapporterat skifte (F-D2): två månader i följd "
              "med P(inbromsning) ≥ 0,8, tillbaka vid två i följd ≤ 0,2. Rapporterat brott (F-D4): P(körlängd ≤ 2) ≥ "
              "0,8, högst ett per serie inom tre perioder. Varken regim eller brott ändrar diffusionsindex eller "
              "tillstånd (F-D5, F-D8).", ""]
    news_parts = []
    if len(ms_f):
        ms_f = ms_f.assign(p_slow=[_p(x) for x in ms_f["p_slow"]])
        if "state" not in ms_f or ms_f["state"].isna().all():
            ms_f = rt.reported_states(ms_f.drop(columns=[c for c in ("state", "shift") if c in ms_f]))
        elif "shift" not in ms_f:
            ms_f = ms_f.sort_values(["block", "date"])
            ms_f["shift"] = [s if _s(p) and _s(s) and s != p else None
                             for s, p in zip(ms_f["state"], ms_f.groupby("block")["state"].shift(1))]
        rows, shifts = [], []
        for block in sorted(ms_f["block"].unique(), key=lambda b: (list(BLOCK_LABEL).index(b) if b in BLOCK_LABEL
                                                                     else 99, b)):
            g = ms_f[ms_f["block"] == block].set_index("month")
            cells = []
            for mo in qmonths:
                if mo not in g.index:
                    cells.append("– (inget avsnitt)")
                    continue
                r = g.loc[mo]
                p = r["p_slow"]
                cells.append(f"{n(p, 2) if math.isfinite(p) else '–'}; {_s(r.get('state')) or '–'}"
                             + ("" if math.isfinite(p) else f" ({_s(r.get('reason')) or 'ingen sannolikhet'})"))
                if _s(r.get("shift")):
                    shifts.append(f"{BLOCK_LABEL.get(block, block)}: {r['shift']} från {mo}")
            rows.append([BLOCK_LABEL.get(block, block), *cells])
        lines += table(["Block", *[f"{mo}: P(inbromsning); rapporterat tillstånd" for mo in qmonths]], rows)
        lines.append("- Rapporterade regimskiften i kvartalet: " + ("; ".join(shifts) if shifts else "inga") + ".")
        news_parts.append(f"{L._plural(len(shifts), 'rapporterat regimskifte', 'rapporterade regimskiften')}")
    else:
        lines.append("- Inga lagrade sannolikheter per block.")
    if len(b_f):
        b_f = b_f.assign(p_recent=[_p(x) for x in b_f["p_recent"]])
        if "break" not in b_f:
            b_f = rt.reported_breaks(b_f)
        q = b_f[b_f["month"].isin(qmonths) & b_f["break"].astype(bool)]
        shown = q[[publishable(k, inp) for k in q["series"]]] if len(q) else q
        hidden = len(q) - len(shown)
        lines.append(f"- Rapporterade strukturbrott i kvartalet: {n(len(q), 0)}" + (":" if len(shown) else "."))
        for r in shown.sort_values(["month", "branch", "series"]).to_dict("records"):
            lines.append(f"  - {r['month']}: {_s(r.get('branch')) or '–'} {name(r['series'], inp)} (`{r['series']}`), "
                         f"senaste period {_s(r.get('latest_period')) or '–'}, P(körlängd ≤ 2) {n(r['p_recent'], 2)}.")
        if hidden:
            lines.append(f"- Varav {n(hidden, 0)} i serier som inte visas av licensskäl.")
        news_parts.append(f"{L._plural(len(q), 'rapporterat brott', 'rapporterade brott')}")
    else:
        lines.append("- Inga lagrade BOCPD-värden.")
    missing = [mo for mo in qmonths if mo not in in_q]
    if missing:
        lines.append(f"- Utan regimavsnitt: {', '.join(missing)}.")
    lines.append("")
    return lines, "Regim: " + (", ".join(news_parts) if news_parts else "inga lagrade värden") + " i kvartalet."


# ------------------------------------------------------------------ 5. data and method


def reviews(inp: Inputs) -> list[str]:
    out = []
    for f in sorted((inp.docs / "granskning").glob("*.md")):
        text = f.read_text(encoding="utf-8")
        m = REVIEW_HEAD.search(text[:2000])
        if not m or not in_quarter(pd.Timestamp(m.group(2)), inp):
            continue
        title = next((x[2:].strip() for x in text.splitlines() if x.startswith("# ")), f.stem)
        out.append(f"{m.group(2)}: {title} (`docs/granskning/{f.name}`)")
    return sorted(out)


BLOCKED_HEADING = re.compile(r"^#{2,4} (?!\d|BLOCKED)(.+?)(?::\s*BLOCKED\b.*| \([^)]*\bBLOCKED\))\s*$")
BLOCKED_BOLD = re.compile(r"^\*\*(.+?) är BLOCKED:?\*\*")


def _clean_md(x: str) -> str:
    return re.sub(r"\*\*|`", "", x).strip()


def blocked(inp: Inputs) -> list[str]:
    """What the source docs mark BLOCKED: table rows with a status cell that starts with BLOCKED (named by the first
    cell), headings "<name>: BLOCKED ..." or "<name> (..., BLOCKED)", and paragraphs "**<name> är BLOCKED:**"."""
    out = []
    for f in sorted((inp.docs / "kallor").glob("*.md")):
        items = []
        for line in f.read_text(encoding="utf-8").splitlines():
            if "BLOCKED" not in line:
                continue
            item = None
            if line.startswith("|"):
                cells = [_clean_md(c) for c in line.strip().strip("|").split("|")]
                if any(c.startswith("BLOCKED") for c in cells[1:]):
                    item = cells[0]
            elif (m := BLOCKED_HEADING.match(line)) or (m := BLOCKED_BOLD.match(line)):
                item = re.sub(r" \(G\d\)$", "", _clean_md(m.group(1)))
            if item and item not in items:
                items.append(item)
        if items:
            out.append(f"`docs/kallor/{f.name}`: {'; '.join(items)}")
    return out


def data_method(inp: Inputs) -> list[str]:
    ctx, t = inp.ctx, inp.ctx.table
    lines = ["## Data och metod", ""]
    withheld = 0
    last = inp.months[-1]
    if inp.base is not None:
        keys = lambda m: {s["series"] for b in m.doc["branches"].values() for s in L.branch_series(b)  # noqa: E731
                          if s.get("series")}
        added, gone = sorted(keys(last) - keys(inp.base)), sorted(keys(inp.base) - keys(last))
        sa, sg = [k for k in added if publishable(k, inp)], [k for k in gone if publishable(k, inp)]
        withheld += len(added) + len(gone) - len(sa) - len(sg)
        lines.append(f"- Nya kärnserier i tillståndet sedan {mlabel(inp.base)}: "
                     + (", ".join(f"{name(k, inp)} (`{k}`)" for k in sa) if sa else "inga") + ".")
        if sg:
            lines.append(f"- Kärnserier som inte längre ingår sedan {mlabel(inp.base)}: "
                         + ", ".join(f"{name(k, inp)} (`{k}`)" for k in sg) + ".")
    if inp.kind == LIVE and len(t):
        first = t.groupby("series")["fetched_at"].min()
        new = sorted(k for k, f in first.items() if inp.start <= f <= inp.end + pd.Timedelta(days=1))
        shown = [k for k in new if publishable(k, inp)]
        withheld += len(new) - len(shown)
        lines.append("- Nya serier (källor) i observationstabellen, första hämtning i kvartalet: "
                     + (", ".join(f"{name(k, inp)} (`{k}`)" for k in shown) if shown else "inga") + ".")
    else:
        lines.append("- Nya serier i observationstabellen: redovisas inte i en rekonstruerad rapport, eftersom "
                     "hämtdatum i dagens tabell inte säger något om kvartalet.")
    nv = L.new_versions(t, inp.start, inp.end)
    is_guid = nv["series"].str.contains(L.GUIDANCE_MARK, regex=False)
    rev = nv[~is_guid & nv["old"].notna()]
    sizes = [L.revision_size(k, o, v, ctx) for k, o, v in zip(rev["series"], rev["old"], rev["new"])]
    rev = rev.assign(size=[x for x, _ in sizes], unit=[u for _, u in sizes])
    big = rev[np.array([L.notable(x, u) for x, u in zip(rev["size"], rev["unit"])], dtype=bool)]
    per = sorted(big.groupby("series").size().items(), key=lambda kv: (-kv[1], kv[0]))
    shown = [(k, c) for k, c in per if publishable(k, inp)]
    withheld += len(per) - len(shown)
    lines.append(f"- Revideringar som blev kända i kvartalet: "
                 f"{L._plural(len(rev), 'redan publicerat värde', 'redan publicerade värden')} fick en ny "
                 f"version med annat värde, varav {n(len(big), 0)} i {L._plural(len(per), 'serie', 'serier')} med "
                 f"minst {n(L.REVISION_MIN_PCT, 0)} % (andelar: {n(L.REVISION_MIN_PP, 1)} pe)"
                 + (": " + ", ".join(f"{name(k, inp)} (`{k}`) {n(c, 0)}" for k, c in shown[:REVISION_ROWS])
                    + (f" och {len(shown) - REVISION_ROWS} till" if len(shown) > REVISION_ROWS else "") + "."
                    if shown else "."))
    guid = nv[is_guid]
    lines.append(f"- Nya eller ändrade guidancevärden från bolagen, kända i kvartalet: {n(len(guid), 0)}.")
    stale, missing = [], []
    for s in sorted(ctx.specs.values(), key=lambda s: (s.branch, s.key)):
        if s.closed:
            continue
        why = BR.stale_reason(s.key, inp.end, ctx)
        if why:
            (missing if "inga data" in why else stale).append(s)
    ss = [s for s in stale if publishable(s.key, inp)]
    withheld += len(stale) - len(ss)
    lines.append(f"- Inaktuella serier per {inp.end.date()}: {n(len(stale), 0)}"
                 + (": " + ", ".join(f"{s.branch} {s.label} (`{s.key}`)" for s in ss) + "." if ss else "."))
    lines.append(f"- Serier i katalogen utan data kända per {inp.end.date()}: {n(len(missing), 0)}.")
    rv = reviews(inp)
    lines.append("- Granskningar daterade i kvartalet (`docs/granskning/`):" + ("" if rv else " inga."))
    lines += [f"  - {x}." for x in rv]
    reg = [f"{d.date()} – {title}" for d, title, _ in sections(inp.docs / "mattregister.md") if in_quarter(d, inp)]
    lines.append("- Ändringar i måttregistret daterade i kvartalet (`docs/mattregister.md`):" + ("" if reg else " inga."))
    lines += [f"  - {x}." for x in reg]
    bl = blocked(inp)
    lines.append("- Blockerade källor enligt källdokumentationen (`docs/kallor/`, rader märkta BLOCKED, läget när "
                 "rapporten genererades):" + ("" if bl else " inga."))
    lines += [f"  - {x}." for x in bl]
    lines.append("")
    if withheld:
        lines += [f"Serier som inte visas av licensskäl ingår i antalen ovan men namnges inte ({n(withheld, 0)}).", ""]
    return lines


# ------------------------------------------------------------------ 6. fixed text


def withheld(inp: Inputs) -> list[str]:
    return [x.replace("i brevet", "i rapporten") for x in L.withheld_section(inp.last)]


def footer(inp: Inputs) -> list[str]:
    rules = inp.months[-1].doc.get("rules") or {}
    dead = rules.get("deadband_sd", R.DEADBAND)
    acc, brk = rules.get("accelerating_at_least", R.ACCELERATING), rules.get("braking_at_most", R.BRAKING)
    mins = rules.get("min_series", R.MIN_SERIES)
    return [
        "## Så läses rapporten", "",
        "- Rapporten sammanfattar kvartalets tre månatliga ögonblicksbilder. Den räknar inte om något som "
        "ögonblicksbilderna redan har lagrat, och den lägger inte till några nya mått.",
        "- **Takt** är förändringen över ett år (log×100, procentenheter för andelar, fördubblings- eller "
        "halveringstid för G1 och G2). **Förändring i takt** är takten nu minus takten sex månader, två kvartal eller "
        "ett år tidigare.",
        f"- En serie **accelererar** när förändringen i takt är större än dödbandet, {n(dead, 2)} standardavvikelser "
        f"av seriens egen historik, **bromsar in** när den är mindre än minus dödbandet och är **stabil** däremellan. "
        f"**Diffusionsindex** = (antal som accelererar + 0,5 × antal stabila) / antal räknade serier. Grenen "
        f"accelererar vid index ≥ {n(acc, 2)}, bromsar in vid index ≤ {n(brk, 2)}, och med färre än {mins} räknade "
        f"serier anges inget tillstånd (`docs/mattregister.md`, avsnitt 2).",
        "- Grenar med tre till fem serier flyttas mycket av en enda serie, så ett tillstånd kan växla från månad till "
        "månad. Om tillståndsregeln har något prognosvärde är inte prövat.",
        "- Orden accelererar, stabil, bromsar in, expansion och inbromsning beskriver takten. De är inga omdömen, och en "
        "inbromsning redovisas på samma sätt som en acceleration.",
        "- **Prognoser:** fel mot första publicerade värde. Få utfall gör att skillnader mellan varianter och mot "
        "baslinjen kan vara slump. Huvudmodellen byts bara enligt registrets regel efter en oberoende granskning.",
        "- **Regim:** P(inbromsning) är en modellsannolikhet för faktorblocket, inte en prognos för någon enskild "
        "serie. Om regimmodellen har något prognosvärde prövas i holdouten och det skarpa registret.",
        "- Alla värden är de som var kända vid respektive månadsslut (`known_from`). Rekonstruerade månader kan "
        "innehålla senare revideringar. Rapporten kan genereras om från samma underlag och blir då identisk.",
        "- Serier vars licens inte tillåter vidarepublicering namnges bara i avsnittet Visas inte av licensskäl.",
        "",
        "## Inte investeringsrådgivning", "",
        f"{L.NOT_INVESTMENT_ADVICE} Projektet håller inga innehav och kopplar inte måtten till placeringar.",
        "",
    ]


# ------------------------------------------------------------------ assemble and write


def render(inp: Inputs) -> str:
    fc_lines, fc_news = forecasts(inp)
    rg_lines, rg_news = regime(inp)
    lines = header(inp) + summary(inp, fc_news, rg_news) + flow(inp) + fc_lines + rg_lines + data_method(inp)
    lines += withheld(inp) + footer(inp)
    text = "\n".join(lines)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.rstrip("\n") + "\n"


def report(quarter, ctx: Context | None = None, snapshots_dir: Path | None = None, forecasts_dir: Path | None = None,
           docs_dir: Path | None = None, reconstructed: bool = False, today=None) -> str:
    ctx = ctx or Context(observations.load())
    return render(gather(quarter, ctx, snapshots_dir, forecasts_dir, docs_dir, reconstructed, today))


def write(quarter, ctx: Context | None = None, out_dir: Path | None = None, **kw) -> Path:
    text = report(quarter, ctx, **kw)
    path = path_for(quarter, out_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def parse(text: str) -> dict:
    """Title and record kind of a report (for the site): {"title", "kind"}."""
    return L.parse(text)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ai_tracker.quarterly", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--quarter", help="YYYYQn")
    g.add_argument("--if-quarter-end", metavar="YYYY-MM",
                   help="the snapshot month: write the report of the quarter it closes, do nothing otherwise")
    ap.add_argument("--reconstructed", action="store_true",
                    help="months without a snapshot are reconstructed from the as-of backcast (labelled rekonstruerad)")
    ap.add_argument("--out-dir", default=None, help=f"default {REPORTS.relative_to(config.REPO)}")
    ap.add_argument("--stdout", action="store_true", help="print the report, write nothing")
    ap.add_argument("--table", default=None, help="observation table (default data/observations.parquet)")
    ap.add_argument("--snapshots-dir", default=None)
    ap.add_argument("--forecasts-dir", default=None)
    a = ap.parse_args(argv)
    if a.table:
        observations.PATH = Path(a.table)
    quarter = a.quarter
    if a.if_quarter_end:
        q = quarter_of_month_end(a.if_quarter_end)
        if q is None:
            print(f"{a.if_quarter_end} does not end a quarter: no report")
            return 0
        quarter = str(q)
    kw = dict(snapshots_dir=Path(a.snapshots_dir) if a.snapshots_dir else None,
              forecasts_dir=Path(a.forecasts_dir) if a.forecasts_dir else None, reconstructed=a.reconstructed)
    try:
        if a.stdout:
            sys.stdout.write(report(quarter, **kw))
            return 0
        path = write(quarter, out_dir=Path(a.out_dir) if a.out_dir else None, **kw)
    except (L.NoSnapshot, ValueError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1
    rel = path.resolve().relative_to(config.REPO) if path.resolve().is_relative_to(config.REPO) else path
    print(f"wrote {rel}")
    L._gh_output(report=str(rel))
    return 0


if __name__ == "__main__":
    sys.exit(main())
