"""E1: the monthly letter (månadsbrev) for a monthly snapshot, in Swedish, generated deterministically from data.

    python -m ai_tracker.letter --month YYYY-MM [--reconstructed] [--out-dir D] [--stdout]

Writes docs/manadsbrev/<YYYY-MM>.md. No LLM and no clock: the same inputs give the same bytes.

Inputs (and nothing else):
- Branch states, indices and per-series measures come from the month's snapshot (snapshots/<YYYY-MM>.json) only;
  nothing about the current month is recomputed. Without that file the letter is refused, unless `--reconstructed`:
  then the state is the as-of backcast at the month end (same code, today's table) and the letter says
  "rekonstruerad" in its title and in a banner at the top.
- The comparison month is the previous month's snapshot. When none exists (before the first live snapshot, or a gap)
  the previous month is reconstructed from the same information set and labelled "(rekonstruerad)" wherever it is used.
- Nowcasts: the committed forecast files (forecasts/n1, forecasts/n2) with origin on or before the snapshot date, and
  outcomes from the observation table cut to the snapshot's information set.
- Data news (new series, revisions, stale or missing series): the observation table cut to the snapshot's information
  set: rows with known_from <= the snapshot date and, for a live snapshot, fetched_at <= its table_max_fetched_at.

Wording is neutral: states and directions are "accelererar", "stabil" or "bromsar in" with numbers, never a judgement.
Licences: a series with Spec.publish=False (a derived series: any component) is never named and none of its values
are shown, except in the section "Visas inte av licensskäl", which lists name, source and reason. Branch-level
aggregates (index, state, counts) include such series, as registered. Forecast inputs are never shown.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ai_tracker import catalog, config, observations, pipeline
from ai_tracker.site import data as D
from ai_tracker.site.render import NOT_INVESTMENT_ADVICE, num
from ai_tracker.state import branch as BR
from ai_tracker.state import register as R
from ai_tracker.state import snapshot as S
from ai_tracker.state.measures import Context, rule_for

LETTERS = config.REPO / "docs" / "manadsbrev"
RECON = "rekonstruerad"
LIVE = "skarp"
WITHHELD_HEADING = "## Visas inte av licensskäl"
REVISION_MIN_PCT = 1.0  # a revision is notable when the value moved at least this many percent from the previous vintage
REVISION_MIN_PP = 0.1  # ... or, for shares (register method "share"), at least this many percentage points
REVISION_ROWS = 12  # at most this many series in the revision table (most notable revisions first)
GUIDANCE_MARK = "guid_"  # company guidance series: a new value is guidance news, not a data revision
TOP_SERIES = 3  # series named per direction in a branch paragraph (the table lists all)

MONTHS_SV = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober",
             "november", "december"]
DIRECTION_WORD = {1: "accelererar", 0: "stabil", -1: "bromsar in"}
DIRECTION_ICON = {1: "↑", 0: "→", -1: "↓"}
PACE_UNIT = {"log": "log×100 per år", "share": "pe per år", "logit": "logit per år",
             "doubling": "fördubblingstid, mån", "halving": "halveringstid, mån"}
CHANGE_LAG_TEXT = {"M": "sex månader tidigare", "Q": "två kvartal tidigare", "A": "ett år tidigare"}


class NoSnapshot(RuntimeError):
    pass


def month_sv(month) -> str:
    p = pd.Period(month, freq="M")
    return f"{MONTHS_SV[p.month - 1]} {p.year}"


def path_for(month, out_dir: Path | None = None) -> Path:
    return Path(out_dir or LETTERS) / f"{pd.Period(month, freq='M')}.md"


# ------------------------------------------------------------------ inputs


@dataclass
class Inputs:
    month: str
    date: pd.Timestamp
    kind: str  # LIVE | RECON
    current: dict  # snapshot document (live: the file as committed)
    previous: dict | None  # previous month's branches document, or None
    previous_kind: str | None  # LIVE | RECON | None
    ctx: Context  # the observation table cut to the information set of the snapshot
    forecasts: Path
    snapshot_file: str | None


def cut_context(ctx: Context, date: pd.Timestamp, max_fetched: str | None) -> Context:
    """`ctx` restricted to rows known on `date` (and, for a live snapshot, fetched by its table_max_fetched_at)."""
    t = ctx.table
    keep = t["known_from"] <= date
    if max_fetched:
        keep &= t["fetched_at"] <= pd.Timestamp(max_fetched) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    return Context(t[keep].reset_index(drop=True), specs=ctx.specs, forecasts=ctx.forecasts, core=ctx.core,
                   derived=ctx.derived, selection=ctx.selection,
                   reconciliations=ctx.reconciliations)


def reconstruct(when: pd.Timestamp, ctx: Context) -> dict:
    """The snapshot document `state.snapshot.build` would write, without the clock and git fields."""
    doc = S.build(when, ctx=ctx)
    doc["record"] = S.BACKCAST_LABEL
    for k in ("created_utc", "git_sha"):
        doc.pop(k, None)
    return doc


def _read(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def gather(month, ctx: Context, snapshots_dir: Path | None = None, forecasts_dir: Path | None = None,
           reconstructed: bool = False, today=None) -> Inputs:
    month = pd.Period(month, freq="M")
    date = S.month_end(month)
    snaps = Path(snapshots_dir or S.SNAPSHOTS)
    snap_path = snaps / f"{month}.json"
    current = _read(snap_path)
    if current is not None and reconstructed:
        raise ValueError(f"{snap_path} exists: the letter for {month} is written from the live snapshot; "
                         "a reconstructed letter would contradict the record")
    if current is None:
        if not reconstructed:
            raise NoSnapshot(f"no snapshot for {month} ({snap_path}). The letter is written from the month's snapshot; "
                             "use --reconstructed for a letter from the as-of backcast (labelled rekonstruerad)")
        today = pd.Timestamp(today).normalize() if today is not None else S.utc_today()
        if date > today:
            raise ValueError(f"{month} has not ended (month end {date.date()}, today {today.date()} UTC)")
        cut = cut_context(ctx, date, None)
        current, kind, file = reconstruct(date, cut), RECON, None
    else:
        cut = cut_context(ctx, date, current.get("table_max_fetched_at"))
        kind, file = LIVE, f"snapshots/{snap_path.name}"
    prev_month = month - 1
    prev = _read(snaps / f"{prev_month}.json")
    prev_kind = LIVE if prev is not None else None
    if prev is None and len(cut.table):
        prev, prev_kind = {"snapshot": str(prev_month), "date": str(S.month_end(prev_month).date()),
                           "branches": S._clean(S.compute(S.month_end(prev_month), cut))}, RECON
    return Inputs(str(month), date, kind, current, prev, prev_kind, cut,
                  Path(forecasts_dir or config.REPO / "forecasts"), file)


# ------------------------------------------------------------------ formatting


def n(x, nd: int = 1, signed: bool = False) -> str:
    return num(x, nd, signed)


def value_text(x) -> str:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "–"
    a = abs(x)
    return n(x, 0 if a >= 100 else 2 if a >= 1 else 3)


def prev_label(inp: Inputs) -> str:
    if inp.previous is None:
        return ""
    return str(inp.previous["snapshot"]) + (" (rekonstruerad)" if inp.previous_kind == RECON else "")


def series_name(key: str, ctx: Context) -> str:
    return D.series_meta(key, ctx)["label"]


def pace_text(m: dict, with_unit: bool = False) -> str:
    """The pace; with_unit: as a phrase ("+43,6 log×100 per år (≈ +55 %)", "fördubblingstid 7,5 mån")."""
    p, method = m.get("pace"), m.get("method")
    if p is None:
        return "–"
    if method in ("doubling", "halving"):
        word = "fördubblingstid" if method == "doubling" else "halveringstid"
        return f"{word} {n(p, 1)} mån" if with_unit else n(p, 1)
    s = n(p, 1, signed=True)
    if with_unit:
        s += " " + PACE_UNIT.get(method, "")
    if method == "log":
        pct = 100 * math.expm1(p / 100)
        s += f" (≈ {n(pct, 1 if abs(pct) < 10 else 0, signed=True)} %)"
    return s


def change_text(m: dict) -> str:
    c = m.get("change_in_pace")
    if c is None:
        return "–"
    if m.get("method") in ("doubling", "halving"):
        return f"{n(c, 1, signed=True)} mån mot 12 månader tidigare (kortare tid = snabbare)"
    return f"{n(c, 1, signed=True)} mot {CHANGE_LAG_TEXT.get(m.get('measure_freq') or m.get('freq'), '')}"


def counts_text(b: dict) -> str:
    up, neu, down = b.get("n_up", 0), b.get("n_neutral", 0), b.get("n_down", 0)
    return f"{up} accelererar, {neu} {'stabil' if neu == 1 else 'stabila'}, {down} bromsar in"


def z_of(m: dict) -> float | None:
    """Signed change in pace in SDs of its own history (positive = faster), for ranking only."""
    c, sd = m.get("change_in_pace"), m.get("sd_change")
    if c is None or not sd:
        return None
    return (m.get("direction_sign") or 1) * c / sd


def publishable(key, inp: Inputs) -> bool:
    return D.publishable(key, inp.ctx)


def branch_series(b: dict) -> list[dict]:
    return [*b.get("series_used", []), *b.get("series_not_counted", [])]


def by_key(b: dict | None) -> dict[str, dict]:
    if not b:
        return {}
    out = {}
    for m in b.get("series_used", []):
        out[m["series"]] = {**m, "_counted": True}
    for m in b.get("series_not_counted", []):
        if m.get("series"):
            out[m["series"]] = {**m, "_counted": False}
    return out


# ------------------------------------------------------------------ sections


def header(inp: Inputs) -> list[str]:
    cur = inp.current
    title = f"# Månadsbrev: AI-utrullningen, {month_sv(inp.month)}" + (" (rekonstruerad)" if inp.kind == RECON else "")
    cmd = f"`python -m ai_tracker.letter --month {inp.month}{' --reconstructed' if inp.kind == RECON else ''}`"
    lines = [title, ""]
    if inp.kind == RECON:
        lines += [f"> **Rekonstruerad, inte ett skarpt underlag.** Det finns ingen skarp ögonblicksbild för "
                  f"{inp.month}. Tillståndet är beräknat i efterhand vid månadsslutet {inp.date.date()} med samma kod "
                  f"och bara data som var känd då, men med dagens versioner av serier som saknar sparade versioner "
                  f"(tabellen hämtad senast {cur.get('table_max_fetched_at') or '–'}). Revideringar kan därför läcka in. "
                  f"Det skarpa registret är ögonblicksbilderna i `snapshots/`.", ""]
        lines += [f"*Genererat av {cmd} från as-of-backcasten (inte ett skarpt register), de committade prognosfilerna "
                  f"och observationstabellen kapad vid {inp.date.date()}. Beskrivande, inga orsaksslutsatser.*", ""]
    else:
        lines += [f"*Skarp ögonblicksbild `{inp.snapshot_file}`, beräknad per {cur.get('date')} "
                  f"(skapad {cur.get('created_utc', '–')}, git {cur.get('git_sha', '–')}, data hämtad senast "
                  f"{cur.get('table_max_fetched_at') or '–'}). Genererat av {cmd} från ögonblicksbilden, de committade "
                  f"prognosfilerna och observationstabellen så som den var känd då. Beskrivande, inga "
                  f"orsaksslutsatser.*", ""]
    return lines


def branch_delta(code: str, inp: Inputs) -> tuple[dict, dict | None, float | None]:
    cur = inp.current["branches"].get(code, {})
    prev = (inp.previous or {}).get("branches", {}).get(code) if inp.previous else None
    d = None
    if prev and cur.get("index") is not None and prev.get("index") is not None:
        d = cur["index"] - prev["index"]
    return cur, prev, d


def headline(inp: Inputs, nowcast_news: list[str], data_news: list[str]) -> list[str]:
    lines = ["## Huvudbudskap", ""]
    pl = prev_label(inp)
    if inp.previous is None:
        lines.append("- Ingen föregående månad att jämföra med.")
    else:
        changed, moved = [], []
        for code, name in catalog.BRANCHES.items():
            cur, prev, d = branch_delta(code, inp)
            if prev and cur.get("state") != prev.get("state"):
                changed.append(f"{code} {name} {prev.get('state')} → {cur.get('state')} "
                               f"(index {n(prev.get('index'), 2)} → {n(cur.get('index'), 2)})")
            if d is not None and round(d, 2) != 0:
                moved.append((abs(d), code, d))
        if changed:
            lines.append(f"- Tillståndet ändrades i {len(changed)} av {len(catalog.BRANCHES)} grenar sedan {pl}: "
                         + "; ".join(changed) + ".")
        else:
            lines.append(f"- Inget tillstånd ändrades sedan {pl}.")
        moved.sort(key=lambda t: (-t[0], t[1]))
        if moved:
            lines.append("- Störst indexförändring: " + ", ".join(f"{c} {n(d, 2, signed=True)}" for _, c, d in moved[:3])
                         + ".")
        else:
            lines.append("- Inget index ändrades (avrundat till två decimaler).")
    groups: dict[str, list[str]] = {}
    for code in catalog.BRANCHES:
        st = inp.current["branches"].get(code, {}).get("state") or R.STATE_FEW
        groups.setdefault(st, []).append(code)
    order = [R.STATE_ACCEL, R.STATE_STABLE, R.STATE_BRAKE, R.STATE_FEW]
    parts = [f"{st} {', '.join(groups[st])}" for st in order if st in groups]
    parts += [f"{st} {', '.join(v)}" for st, v in groups.items() if st not in order]
    lines.append("- Läget: " + "; ".join(parts) + ".")
    movers = []
    for code in catalog.BRANCHES:
        for m in inp.current["branches"].get(code, {}).get("series_used", []):
            z = z_of(m)
            if z is not None and m.get("direction") and publishable(m["series"], inp):
                movers.append((-abs(z), m["series"], code, z))
    movers.sort()
    if movers:
        lines.append("- Störst förändring i takt bland räknade serier som visas, i standardavvikelser av seriens egen "
                     "historik: " + ", ".join(f"{series_name(k, inp.ctx)} ({c}) {n(z, 1, signed=True)} SD"
                                                for _, k, c, z in movers[:TOP_SERIES]) + ".")
    lines += [f"- {x}" for x in nowcast_news + data_news]
    return lines + [""]


def series_table(code: str, inp: Inputs) -> list[str]:
    cur = inp.current["branches"].get(code, {})
    prev = by_key((inp.previous or {}).get("branches", {}).get(code)) if inp.previous else {}
    rows = []
    for m in cur.get("series_used", []):
        key = m["series"]
        if not publishable(key, inp):
            continue
        p = prev.get(key)
        since = "–"
        if p and m.get("pace") is not None and p.get("pace") is not None:
            since = n(m["pace"] - p["pace"], 1, signed=True)
            same = p.get("latest_period") == m.get("latest_period")
            since += " (samma period)" if same else f" (ny period, förra {p.get('latest_period')})"
        d = m.get("direction")
        rows.append([f"{series_name(key, inp.ctx)} (`{key}`)", str(m.get("latest_period") or "–"),
                     PACE_UNIT.get(m.get("method"), ""), pace_text(m), change_text(m),
                     f"{DIRECTION_ICON.get(d, '')} {DIRECTION_WORD.get(d, '–')} (±{n(m.get('deadband'), 1)})", since])
    if not rows:
        return []
    head = ["Serie", "Senaste period", "Mått", "Takt", "Förändring i takt", "Riktning (dödband)",
            f"Ändring i takt sedan {prev_label(inp) or 'förra månaden'}"]
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    return out + ["| " + " | ".join(r) + " |" for r in rows] + [""]


def _int(k: int) -> str:
    return n(k, 0)


def _plural(k: int, one: str, many: str) -> str:
    return f"{_int(k)} {one if k == 1 else many}"


def branch_section(code: str, inp: Inputs) -> list[str]:
    name = catalog.BRANCHES[code]
    cur, prev, d = branch_delta(code, inp)
    entries = cur.get("registered_entries", R.core_entries(code, inp.ctx.core))
    state = cur.get("state") or R.STATE_FEW
    lines = [f"### {code} {name}: {state}", ""]
    if not entries:
        return lines + ["Grenen har inga registrerade kärnserier.", ""]
    k = cur.get("n_series") or 0
    para = []
    if k:
        para.append(f"Index {n(cur.get('index'), 2)} med {_plural(k, 'räknad serie', 'räknade serier')} "
                    f"({counts_text(cur)}).")
    else:
        para.append("Inga räknade serier, så inget index.")
    if k and k < R.MIN_SERIES:
        para.append(f"Med färre än {R.MIN_SERIES} räknade serier anges inget tillstånd.")
    if prev is not None:
        pl = prev_label(inp)
        if d is not None:
            idx = (f"index oförändrat ({n(cur.get('index'), 2)})" if round(d, 2) == 0 else
                   f"index {n(prev.get('index'), 2)} → {n(cur.get('index'), 2)} ({n(d, 2, signed=True)})")
            para.append(f"Sedan {pl}: {idx}, " +
                        (f"tillståndet {prev.get('state')} → {state}." if prev.get("state") != state
                         else "tillståndet oförändrat."))
        elif prev.get("state") != state:
            para.append(f"Sedan {pl}: tillståndet {prev.get('state')} → {state}.")
        else:
            para.append(f"Sedan {pl}: oförändrat.")
    shown = [m for m in cur.get("series_used", []) if publishable(m["series"], inp)]
    for dval in (1, -1, 0):
        group = [m for m in shown if m.get("direction") == dval]
        if not group:
            continue
        group.sort(key=lambda m: (-abs(z_of(m) or 0.0), m["series"]))
        named = [f"{series_name(m['series'], inp.ctx)} (förändring i takt {n(m.get('change_in_pace'), 1, signed=True)}, "
                 f"dödband ±{n(m.get('deadband'), 1)})" for m in group[:TOP_SERIES]]
        more = f" och {len(group) - TOP_SERIES} till" if len(group) > TOP_SERIES else ""
        word = {1: "Accelererar", -1: "Bromsar in",
                0: "Stabil, inom dödbandet" if len(group) == 1 else "Stabila, inom dödbandet"}[dval]
        para.append(f"{word}: {', '.join(named)}{more}.")
    prev_map = by_key(prev)
    flips = []
    for key, m in by_key(cur).items():
        p = prev_map.get(key)
        if p is None or not publishable(key, inp):
            continue
        if m["_counted"] and p["_counted"] and m.get("direction") != p.get("direction"):
            flips.append(f"{series_name(key, inp.ctx)} {DIRECTION_WORD.get(p.get('direction'), '–')} → "
                         f"{DIRECTION_WORD.get(m.get('direction'), '–')}")
        elif m["_counted"] != p["_counted"]:
            flips.append(f"{series_name(key, inp.ctx)} " + ("räknas nu" if m["_counted"] else "räknas inte längre"))
    if flips:
        para.append(f"Ändrat sedan {prev_label(inp)}: {'; '.join(sorted(flips))}.")
    withheld = [m for m in branch_series(cur) if m.get("series") and not publishable(m["series"], inp)]
    if withheld:
        w_c = sum(1 for m in cur.get("series_used", []) if not publishable(m["series"], inp))
        counted = ("den räknas" if len(withheld) == 1 else "alla räknas") if w_c == len(withheld) else \
            f"varav {w_c} räknas"
        para.append(f"{_plural(len(withheld), 'serie', 'serier')} visas inte av licensskäl, {counted} i indexet "
                    f"(se avsnittet Visas inte av licensskäl).")
    lines += [" ".join(para), ""]
    lines += series_table(code, inp)
    nc = []
    for m in cur.get("series_not_counted", []):
        key = m.get("series")
        if key is None:
            nc.append(f"- `{m.get('entry')}`: {m.get('reason')}.")
        elif publishable(key, inp):
            extra = ""
            if m.get("pace") is not None:
                extra = f" Beskrivande: takt {pace_text(m, with_unit=True)}, förändring i takt {change_text(m)}."
            nc.append(f"- {series_name(key, inp.ctx)} (`{key}`): {m.get('reason')}.{extra}")
    if nc:
        lines += ["Räknas inte (beskriver men påverkar inte indexet):", "", *nc, ""]
    flags = [f"- {series_name(m['series'], inp.ctx)}: {m['flag']}." for m in cur.get("series_used", [])
             if m.get("flag") and publishable(m["series"], inp)]
    if flags:
        lines += ["Flaggor:", "", *flags, ""]
    if code == "G1":
        sel = (inp.current.get("rules") or {}).get("g1_selected_benchmarks")
        if sel is not None:
            lines += [f"Valda benchmarks på beräkningsdagen (registrerad urvalsregel): "
                      f"{', '.join(f'`{s}`' for s in sel) or 'inga'}.", ""]
    return lines


# ------------------------------------------------------------------ nowcasts


def _next_origin(sub: str, after: pd.Timestamp, horizon: int = 200) -> tuple[str, str] | None:
    for i in range(1, horizon):
        dd = pipeline.due_for(sub, after + pd.Timedelta(days=i))
        if dd is not None:
            return str(dd.origin.date()), dd.period
    return None


def nowcasts(inp: Inputs) -> tuple[list[str], list[str]]:
    start, end = inp.date.to_period("M").start_time, inp.date
    try:
        scores = pipeline.score(inp.forecasts, inp.ctx.table)
        error = None
    except Exception as e:  # noqa: BLE001 - the letter still says that the scorecard failed
        scores, error = {}, f"{type(e).__name__}: {e}"
    lines, news = ["## Nowcasts", ""], []
    n_new, n_out = 0, 0
    for sub, (label, target, variants, champion) in {
            k: (v[0], v[1], v[2], D.NOWCAST_MODULES[k][2]) for k, v in pipeline.NOWCASTS.items()}.items():
        info = D.NOWCAST_INFO[sub]
        show = publishable(target, inp)
        lines += [f"### {label} {info['title']} (`{target}`)" if show else f"### {label} {info['title']}", ""]
        lines.append(f"Huvudmodell: {champion}. Skuggor: {', '.join(v for v in variants if v != champion)}. "
                     f"Prognosdag: {info['origin_rule']}.")
        files = []
        for f in sorted((inp.forecasts / sub).glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            origin = pd.Timestamp(d["origin"])
            if origin <= end:
                files.append((origin, d, f"forecasts/{sub}/{f.name}"))
        new = [x for x in files if x[0] >= start]
        n_new += len(new)
        lines.append("")
        nxt = _next_origin(sub, end)
        nxt_text = f" Nästa skarpa prognos: {nxt[1]}, prognosdag {nxt[0]}." if nxt else ""
        if not files:
            lines += [f"Inga skarpa prognoser med prognosdag till och med {end.date()}.{nxt_text}", ""]
            continue
        if new:
            lines += [f"Nya skarpa prognoser med prognosdag i {month_sv(inp.month)}:", ""]
            for origin, d, path in new:
                period = d.get("quarter") or d.get("month") or d.get("period")
                if show:
                    vs = ", ".join(f"{v} {value_text((d.get('variants') or {}).get(v))}" for v in variants
                                   if v != d.get("champion"))
                    lines.append(f"- {period} (prognosdag {origin.date()}, `{path}`): huvudmodell {d.get('champion')} "
                                 f"{value_text(d.get('value'))} {d.get('unit', '')}; skuggor {vs}.")
                else:
                    lines.append(f"- {period} (prognosdag {origin.date()}, `{path}`): huvudmodell {d.get('champion')}; "
                                 f"värdet visas inte av licensskäl.")
        else:
            lines.append(f"Ingen ny skarp prognos med prognosdag i {month_sv(inp.month)}.")
        lines.append("")
        df = scores.get(sub)
        origins = {str(o.date()) for o, _d, _p in files}
        if error:
            lines.append(f"Scorecarden kunde inte beräknas: {error}.")
        elif df is not None and len(df):
            df = df[df["origin"].isin(origins)]
            scored = df[df["status"] == "utfall"]
            fresh = scored[pd.to_datetime(scored["known_from"]) >= start]
            n_out += len(fresh)
            if len(fresh):
                lines += [f"Nya utfall i {month_sv(inp.month)} (första publicerade värdet; fel = 100 × (log prognos "
                          f"− log utfall), positivt = prognosen låg över utfallet):", ""]
                for r in fresh.to_dict("records"):
                    errs = ", ".join(f"{v} {n(r.get(f'err_{v}'), 2, signed=True)}" for v in variants
                                     if r.get("champion") != v)
                    vals = (f"prognos {value_text(r['forecast'])}, utfall {value_text(r['outcome'])}, "
                            if show else "")
                    lines.append(f"- {r['period']}: {vals}känt {r['known_from']}, fel huvudmodell ({r['champion']}) "
                                 f"{n(r['err_champion'], 2, signed=True)}; skuggor {errs}.")
                lines.append("")
            else:
                lines.append(f"Inga nya utfall i {month_sv(inp.month)}.")
            if len(scored):
                e = scored["err_champion"].dropna()
                lines.append(f"Utvärderade hittills: {len(scored)} av {len(df)}. Huvudmodellens MAE "
                             f"{n(e.abs().mean(), 2)}, bias {n(e.mean(), 2, signed=True)}. Få utfall: skillnader "
                             f"mellan varianter kan vara slump.{nxt_text}")
            else:
                lines.append(f"Utvärderade hittills: 0 av {len(df)}.{nxt_text}")
        lines.append("")
    news.append(f"Nowcasts: {_plural(n_new, 'ny skarp prognos', 'nya skarpa prognoser')} och "
                f"{_plural(n_out, 'nytt utfall', 'nya utfall')} i {month_sv(inp.month)}.")
    return lines, news


# ------------------------------------------------------------------ data news


def new_versions(table: pd.DataFrame, start, end) -> pd.DataFrame:
    """Rows that became known in [start, end]: series, period, old (previous vintage or NaN for a new period),
    new, known_from. Rows whose value equals the previous vintage are dropped (a re-reported number is no news)."""
    cols = ["series", "period", "old", "new", "known_from"]
    if table.empty:
        return pd.DataFrame(columns=cols)
    t = table.sort_values(["series", "period", "known_from"], kind="mergesort")
    prev = t.groupby(["series", "period"], sort=False)["value"].shift(1)
    sel = (t["known_from"] >= start) & (t["known_from"] <= end) & ~(t["value"] == prev)
    r = t[sel]
    return pd.DataFrame({"series": r["series"].to_numpy(), "period": r["period"].astype(str).to_numpy(),
                         "old": prev[sel].to_numpy(), "new": r["value"].to_numpy(),
                         "known_from": r["known_from"].to_numpy()}, columns=cols)


def revision_size(key: str, old: float, new: float, ctx: Context) -> tuple[float, str]:
    """(size, unit): percentage points for shares (register method "share"), otherwise percent of the old value."""
    try:
        method = rule_for(key, ctx).method
    except KeyError:
        method = "log"
    if method == "share":
        spec = ctx.specs.get(key)
        scale = 100.0 if spec is not None and re.search(r"0\s*[-–]\s*1\b", spec.unit) else 1.0
        return scale * (new - old), "pe"
    return (100.0 * (new / old - 1.0) if old else math.inf), "%"


def notable(size: float, unit: str) -> bool:
    return abs(size) >= (REVISION_MIN_PP if unit == "pe" else REVISION_MIN_PCT)


def data_news(inp: Inputs) -> tuple[list[str], list[str]]:
    ctx, t = inp.ctx, inp.ctx.table
    start, end = inp.date.to_period("M").start_time, inp.date
    lines, news = ["## Data", ""], []
    withheld_counts: dict[str, int] = {}

    # new core series in the state (snapshot vs previous)
    if inp.previous is not None:
        cur_keys = {m["series"] for b in inp.current["branches"].values() for m in branch_series(b) if m.get("series")}
        prev_keys = {m["series"] for b in inp.previous["branches"].values() for m in branch_series(b) if m.get("series")}
        added = sorted(cur_keys - prev_keys)
        gone = sorted(prev_keys - cur_keys)
        shown_added = [k for k in added if publishable(k, inp)]
        shown_gone = [k for k in gone if publishable(k, inp)]
        withheld_counts["nya eller borttagna kärnserier"] = len(added) + len(gone) - len(shown_added) - len(shown_gone)
        if shown_added or shown_gone:
            if shown_added:
                lines.append("- Nya kärnserier i tillståndet sedan " + prev_label(inp) + ": "
                             + ", ".join(f"{series_name(k, ctx)} (`{k}`)" for k in shown_added) + ".")
            if shown_gone:
                lines.append("- Kärnserier som inte längre ingår sedan " + prev_label(inp) + ": "
                             + ", ".join(f"{series_name(k, ctx)} (`{k}`)" for k in shown_gone) + ".")
        else:
            lines.append(f"- Inga nya kärnserier i tillståndet sedan {prev_label(inp)}.")

    # new series in the observation table (live only: in a reconstruction fetched_at says nothing about the month)
    if inp.kind == LIVE and len(t):
        first = t.groupby("series")["fetched_at"].min()
        new = sorted(k for k, f in first.items() if start <= f <= end)
        shown = [k for k in new if publishable(k, inp)]
        withheld_counts["nya serier i tabellen"] = len(new) - len(shown)
        lines.append(f"- Nya serier i observationstabellen (första hämtning i {month_sv(inp.month)}): "
                     + (", ".join(f"{series_name(k, ctx)} (`{k}`)" for k in shown) if shown else "inga") + ".")
        news_new = len(new)
    else:
        lines.append("- Nya serier i observationstabellen: redovisas inte i ett rekonstruerat brev, eftersom "
                     "hämtdatum i dagens tabell inte säger något om månaden.")
        news_new = None

    # revisions and guidance (new versions that became known in the month)
    nv = new_versions(t, start, end)
    is_guid = nv["series"].str.contains(GUIDANCE_MARK, regex=False)
    rev = nv[~is_guid & nv["old"].notna()]
    sizes = [revision_size(k, o, v, ctx) for k, o, v in zip(rev["series"], rev["old"], rev["new"])]
    rev = rev.assign(size=[x for x, _ in sizes], unit=[u for _, u in sizes])
    rev = rev.assign(notable=[notable(x, u) for x, u in zip(rev["size"], rev["unit"])])
    big = rev[rev["notable"].astype(bool)]  # astype: an empty object column would select columns, not rows
    per = []
    for key, g in big.groupby("series", sort=True):
        top = g.loc[g["size"].abs().idxmax()]
        per.append({"series": key, "n_all": int((rev["series"] == key).sum()), "n_big": len(g),
                    "top": top, "first": str(g["period"].min()), "last": str(g["period"].max())})
    shown = [x for x in per if publishable(x["series"], inp)]
    withheld_counts["serier med revideringar"] = len(per) - len(shown)
    lines.append(f"- Revideringar som blev kända i {month_sv(inp.month)}: {_int(len(rev))} redan publicerade värden "
                 f"fick en ny version med annat värde, varav {_int(len(big))} i {_plural(len(per), 'serie', 'serier')} "
                 f"ändrades med minst {n(REVISION_MIN_PCT, 0)} % (andelar: minst {n(REVISION_MIN_PP, 1)} pe)"
                 + (":" if shown else "."))
    lines.append("")
    if shown:
        shown.sort(key=lambda x: (-x["n_big"], -abs(x["top"]["size"]), x["series"]))
        head = ["Serie", "Reviderade perioder över tröskeln (av alla reviderade)", "Perioder", "Största ändring", "Känd från"]
        lines += ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
        for x in shown[:REVISION_ROWS]:
            top = x["top"]
            span = x["first"] if x["first"] == x["last"] else f"{x['first']} – {x['last']}"
            lines.append(f"| {series_name(x['series'], ctx)} (`{x['series']}`) | {x['n_big']} (av {x['n_all']}) | "
                         f"{span} | {top['period']}: {value_text(top['old'])} → {value_text(top['new'])} "
                         f"({n(top['size'], 1, signed=True)} {top['unit']}) | {pd.Timestamp(top['known_from']).date()} |")
        if len(shown) > REVISION_ROWS:
            lines += ["", f"Ytterligare {len(shown) - REVISION_ROWS} serier med revideringar listas inte."]
        lines.append("")
    guid = nv[is_guid]
    guid_shown = guid[[publishable(k, inp) for k in guid["series"]]] if len(guid) else guid
    withheld_counts["nya guidancevärden"] = len(guid) - len(guid_shown)
    lines.append(f"- Ny eller ändrad guidance från bolagen, känd i {month_sv(inp.month)}: {_int(len(guid))} värden"
                 + (":" if len(guid_shown) else "."))
    if len(guid_shown):
        lines.append("")
        for r in guid_shown.sort_values(["series", "period", "known_from"]).to_dict("records"):
            spec = ctx.specs.get(r["series"])
            unit = spec.unit if spec else ""
            was = "" if pd.isna(r["old"]) else f" (tidigare {value_text(r['old'])})"
            lines.append(f"  - {series_name(r['series'], ctx)} (`{r['series']}`), {r['period']}: "
                         f"{value_text(r['new'])} {unit}{was}, känd {pd.Timestamp(r['known_from']).date()}.")
    lines.append("")

    # stale or without data (register rule, same bound as the weekly check)
    stale, missing = [], []
    for s in sorted(ctx.specs.values(), key=lambda s: (s.branch, s.key)):
        if s.closed:
            continue
        why = BR.stale_reason(s.key, end, ctx)
        if not why:
            continue
        (missing if "inga data" in why else stale).append((s, why))
    shown_stale = [(s, w) for s, w in stale if publishable(s.key, inp)]
    shown_missing = [(s, w) for s, w in missing if publishable(s.key, inp)]
    withheld_counts["inaktuella serier"] = len(stale) - len(shown_stale)
    withheld_counts["serier utan data"] = len(missing) - len(shown_missing)
    lines.append(f"- Inaktuella serier per {end.date()} (senaste period äldre än aktualitetsgränsen): {len(stale)}"
                 + (":" if shown_stale else "."))
    if shown_stale:
        lines.append("")
        lines += [f"  - {s.branch} {s.label} (`{s.key}`): {w.removeprefix('inaktuell: ')}." for s, w in shown_stale]
        lines.append("")
    lines.append(f"- Serier i katalogen utan data kända per {end.date()} (inte hämtade, blockerade eller ännu inte "
                 f"publicerade): {len(missing)}" + (":" if shown_missing else "."))
    if shown_missing:
        lines.append("")
        lines += [f"  - {s.branch} {s.label} (`{s.key}`)." for s, _ in shown_missing]
    lines.append("")
    w = {k: v for k, v in withheld_counts.items() if v}
    if w:
        lines += ["Serier som inte visas av licensskäl ingår i antalen ovan men namnges inte: "
                  + ", ".join(f"{k} {v}" for k, v in w.items()) + ".", ""]
    news.append(f"Data: {_plural(len(per), 'serie', 'serier')} med revideringar över tröskeln, "
                f"{_plural(len(stale), 'inaktuell serie', 'inaktuella serier')}"
                + (f", {_plural(news_new, 'ny serie', 'nya serier')} i tabellen" if news_new is not None else "") + ".")
    return lines, news


# ------------------------------------------------------------------ reconciliations (A5)


RECONCILIATION_HEADING = "## Avstämningar"


def reconciliation_section(inp: Inputs) -> list[str]:
    """Level, pace and change in pace per A5 reconciliation series, from the snapshot (a group outside the branches).
    Omitted when the snapshot has no such section (written before A5)."""
    rec = inp.current.get("reconciliations")
    if not rec:
        return []
    lines = [RECONCILIATION_HEADING, "",
             "Härledda kvoter mellan leden (registrerade 2026-11-23, A5). Takt = årsförändring i log(kvot) ×100. "
             "De räknas inte i grenarnas diffusionsindex.", ""]
    rows = []
    for m in rec.get("series", []):
        key = m["series"]
        if not publishable(key, inp):
            continue
        rows.append([f"{series_name(key, inp.ctx)} (`{key}`)", str(m.get("latest_period") or "–"),
                     value_text(m.get("level")), pace_text(m), change_text(m), m.get("reason") or "–"])
    if not rows:
        return lines + ["Inga avstämningar som får visas har data på beräkningsdagen.", ""]
    head = ["Avstämning", "Senaste period", "Nivå", "Takt (log×100 per år)", "Förändring i takt", "Anmärkning"]
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    return lines + out + ["| " + " | ".join(r) + " |" for r in rows] + [""]


# ------------------------------------------------------------------ withheld and footer


def withheld_section(inp: Inputs) -> list[str]:
    seen, items = set(), []
    for code in catalog.BRANCHES:
        b = inp.current["branches"].get(code, {})
        counted = {m["series"] for m in b.get("series_used", [])}
        for m in branch_series(b):
            key = m.get("series")
            if not key or key in seen or publishable(key, inp):
                continue
            seen.add(key)
            w = D.withheld_entry(key, inp.ctx, counted=key in counted)
            items.append(f"- {code}: {w['label']} (`{key}`). Källa: {w['source'] or '–'}. Skäl: {w['why']}. "
                         + ("Räknas i grenens index." if w["counted"] else "Räknas inte i grenens index."))
    for m in (inp.current.get("reconciliations") or {}).get("series", []):
        key = m.get("series")
        if not key or key in seen or publishable(key, inp):
            continue
        seen.add(key)
        w = D.withheld_entry(key, inp.ctx, counted=False)
        items.append(f"- {R.RECONCILIATION_GROUP}: {w['label']} (`{key}`). Källa: {w['source'] or '–'}. "
                     f"Skäl: {w['why']}. Räknas inte i något grenindex.")
    lines = [WITHHELD_HEADING, ""]
    if not items:
        return lines + ["Alla kärnserier i ögonblicksbilden får visas.", ""]
    return lines + ["Kärnserier som ingår i grenarnas index och antal enligt registret, men vars värden, takter och "
                    "riktningar inte visas här. Inga andra uppgifter om dem finns i brevet.", "", *items, ""]


def footer(inp: Inputs) -> list[str]:
    rules = inp.current.get("rules") or {}
    dead = rules.get("deadband_sd", R.DEADBAND)
    acc, brk = rules.get("accelerating_at_least", R.ACCELERATING), rules.get("braking_at_most", R.BRAKING)
    mins = rules.get("min_series", R.MIN_SERIES)
    return [
        "## Så ska brevet läsas", "",
        f"- **Takt** är förändringen över ett år: log×100 för positiva storheter (≈ procent för små tal, omräknat inom "
        f"parentes), procentenheter (pe) för andelar, logit för begränsade poäng, och fördubblings- eller "
        f"halveringstid i månader för förmåga och pris (G1, G2).",
        "- **Förändring i takt** är takten nu minus takten sex månader, två kvartal eller ett år tidigare "
        "(12 månader för fördubblingstid, där kortare tid räknas som snabbare).",
        f"- En serie **accelererar** när förändringen i takt är större än dödbandet, {n(dead, 2)} standardavvikelser "
        f"av seriens egen historik, **bromsar in** när den är mindre än minus dödbandet och är **stabil** däremellan.",
        f"- **Diffusionsindex** = (antal som accelererar + 0,5 × antal stabila) / antal räknade serier. Grenen "
        f"accelererar vid index ≥ {n(acc, 2)}, bromsar in vid index ≤ {n(brk, 2)} och är stabil däremellan. Med färre "
        f"än {mins} räknade serier anges inget tillstånd. Reglerna är förregistrerade i `docs/mattregister.md`.",
        "- Orden accelererar, stabil och bromsar in beskriver takten. De är inga omdömen, och en inbromsning redovisas "
        "på samma sätt som en acceleration.",
        "- Grenar med tre till fem serier flyttas mycket av en enda serie. Om tillståndsregeln har något prognosvärde "
        "är inte prövat. Kvartalsserier är korta och har regimbrott efter 2023.",
        "- Alla värden är de som var kända på beräkningsdagen (`known_from`). Serier utan sparade versioner dateras "
        "med publiceringsfördröjning (backfill). Ögonblicksbilden skrivs en gång och skrivs aldrig om. Brevet kan "
        "genereras om från samma underlag och blir då identiskt.",
        "- Serier vars licens inte tillåter vidarepublicering namnges bara i avsnittet Visas inte av licensskäl.",
        "",
        "## Inte investeringsrådgivning", "",
        f"{NOT_INVESTMENT_ADVICE} Projektet håller inga innehav och kopplar inte måtten till placeringar.",
        "",
    ]


# ------------------------------------------------------------------ assemble and write


def render(inp: Inputs) -> str:
    nc_lines, nc_news = nowcasts(inp)
    dn_lines, dn_news = data_news(inp)
    lines = header(inp) + headline(inp, nc_news, dn_news)
    lines += ["## Grenarna", ""]
    for code in catalog.BRANCHES:
        lines += branch_section(code, inp)
    lines += reconciliation_section(inp)
    lines += nc_lines + dn_lines + withheld_section(inp) + footer(inp)
    text = "\n".join(lines)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.rstrip("\n") + "\n"


def letter(month, ctx: Context | None = None, snapshots_dir: Path | None = None, forecasts_dir: Path | None = None,
           reconstructed: bool = False, today=None) -> str:
    ctx = ctx or Context(observations.load())
    return render(gather(month, ctx, snapshots_dir, forecasts_dir, reconstructed, today))


def write(month, ctx: Context | None = None, out_dir: Path | None = None, **kw) -> Path:
    text = letter(month, ctx, **kw)
    path = path_for(month, out_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def parse(text: str) -> dict:
    """Title and record kind of a letter (for the site): {"title", "kind"}."""
    title = next((line[2:].strip() for line in text.splitlines() if line.startswith("# ")), "")
    return {"title": title, "kind": RECON if title.endswith(f"({RECON})") else LIVE}


def _gh_output(**kv: str) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            for k, v in kv.items():
                f.write(f"{k}={v}\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ai_tracker.letter", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--month", required=True, help="YYYY-MM (the snapshot month)")
    ap.add_argument("--reconstructed", action="store_true",
                    help="no snapshot yet: write the letter from the as-of backcast, labelled rekonstruerad")
    ap.add_argument("--out-dir", default=None, help=f"default {LETTERS.relative_to(config.REPO)}")
    ap.add_argument("--stdout", action="store_true", help="print the letter, write nothing")
    ap.add_argument("--table", default=None, help="observation table (default data/observations.parquet)")
    ap.add_argument("--snapshots-dir", default=None)
    ap.add_argument("--forecasts-dir", default=None)
    a = ap.parse_args(argv)
    if a.table:
        observations.PATH = Path(a.table)
    kw = dict(snapshots_dir=Path(a.snapshots_dir) if a.snapshots_dir else None,
              forecasts_dir=Path(a.forecasts_dir) if a.forecasts_dir else None, reconstructed=a.reconstructed)
    try:
        if a.stdout:
            sys.stdout.write(letter(a.month, **kw))
            return 0
        path = write(a.month, out_dir=Path(a.out_dir) if a.out_dir else None, **kw)
    except (NoSnapshot, ValueError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1
    rel = path.resolve().relative_to(config.REPO) if path.resolve().is_relative_to(config.REPO) else path
    print(f"wrote {rel}")
    _gh_output(letter=str(rel))
    return 0


if __name__ == "__main__":
    sys.exit(main())
