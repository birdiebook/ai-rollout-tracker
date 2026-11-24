// Shapes the bundle documents into the compact inputs of the method page (track W11). Pure functions: the server
// load calls them at prerender time, and the tests call them on every bundle (fixtures and, with SITE_BUNDLE_DIR, a
// real one). Nothing is computed here that the pipeline computes; only selection, slicing and URL extraction.
import type { Versions, MeasureHistory, MeasurePath } from '$lib/series/types';
import { periodVersions } from '$lib/series/versions';
import { REGISTERED, type Dir, type ExploreSeries, type Rules } from './engine';

// ---------------------------------------------------------------- the dead band explorer

interface CountedEntry {
  key: string;
  label?: string;
  method?: string | null;
  change_in_pace?: number | null;
  sd_change?: number | null;
  direction?: Dir | null;
  valid?: boolean;
}

export interface BranchInput {
  code: string;
  name: string;
  index?: number | null;
  state?: string | null;
  n_series?: number;
  n_withheld_counted?: number;
  counted: CountedEntry[];
  history?: { month: string; kind: string; index: number | null; state: string | null; n_series?: number | null }[];
  record?: { status?: string; label?: string; date?: string; month?: string };
}

export interface ExploreBranch {
  code: string;
  name: string;
  /** the registered record (the pipeline's numbers) */
  registered: { index: number | null; state: string; n_series: number };
  /** can the browser recompute this branch? Only when every counted series is publishable and has its numbers */
  eligible: boolean;
  why: string | null;
  series: ExploreSeries[];
  history: { month: string; kind: string; index: number | null; state: string | null; n_series: number | null }[];
}

export function rulesOf(method: Record<string, unknown>): Rules {
  const r = (method.rules ?? {}) as Partial<Rules>;
  return {
    deadband_sd: r.deadband_sd ?? REGISTERED.deadband_sd,
    accelerating_at_least: r.accelerating_at_least ?? REGISTERED.accelerating_at_least,
    braking_at_most: r.braking_at_most ?? REGISTERED.braking_at_most,
    min_series: r.min_series ?? REGISTERED.min_series
  };
}

/** A branch for the explorer. Withheld series count in the index but their numbers are never in the bundle
 *  (licence gate), so a branch that counts one cannot be recomputed in the browser and is not offered. */
export function exploreBranchOf(b: BranchInput): ExploreBranch {
  const n = b.n_series ?? 0;
  const held = b.n_withheld_counted ?? 0;
  const usable = b.counted.filter(
    (s) => s.valid !== false && typeof s.change_in_pace === 'number' && typeof s.sd_change === 'number' && s.sd_change > 0 && s.direction !== null && s.direction !== undefined
  );
  let why: string | null = null;
  if (held > 0) why = `räknar ${held === 1 ? 'en inhållen serie' : `${held} inhållna serier`} vars tal inte publiceras`;
  else if (n === 0) why = 'inga räknade serier';
  else if (usable.length !== n) why = 'alla räknade serier har inte sina tal i paketet';
  return {
    code: b.code,
    name: b.name,
    registered: { index: b.index ?? null, state: b.state ?? 'för få serier', n_series: n },
    eligible: why === null,
    why,
    series:
      why === null
        ? usable.map((s) => ({
            key: s.key,
            label: s.label ?? s.key,
            method: s.method ?? null,
            change: s.change_in_pace as number,
            sd: s.sd_change as number,
            registered: s.direction as Dir
          }))
        : [],
    history: (b.history ?? []).map((h) => ({ month: h.month, kind: h.kind, index: h.index ?? null, state: h.state ?? null, n_series: h.n_series ?? null }))
  };
}

/** The default branch: the eligible one with the most counted series (ties: first in G1–G9). */
export function defaultBranch(bs: ExploreBranch[]): string | null {
  let best: ExploreBranch | null = null;
  for (const b of bs) if (b.eligible && (!best || b.series.length > best.series.length)) best = b;
  return best?.code ?? null;
}

// ---------------------------------------------------------------- as_of and known_from

export interface SeriesIndexRow {
  key: string;
  freq?: string | null;
  unit?: string | null;
  n_versions?: number;
}

/** Units whose level changes base between vintages (Fed G.17 "basår enligt vintage"): a rebase is not a revision of
 *  what was measured, so those series do not tell the as_of story on the level scale. */
const REBASED = /basår enligt vintage/i;

/** Candidates for the as_of figure: monthly series with versions and a stable base, most versions first. */
export function revisedCandidates(rows: SeriesIndexRow[], n = 8): string[] {
  return rows
    .filter((r) => r.freq === 'M' && (r.n_versions ?? 0) > 1 && !REBASED.test(r.unit ?? ''))
    .sort((a, b) => (b.n_versions ?? 0) - (a.n_versions ?? 0) || (a.key < b.key ? -1 : 1))
    .slice(0, n)
    .map((r) => r.key);
}

/** The series for the as_of figure among the candidates' documents: one the record measured (it has a measure history,
 *  so the leakage figure has pipeline numbers), then the most revised periods, then the most versions. */
export function pickRevised<T extends { key: string; measure_history?: unknown; versions?: { n_revised_periods: number; n_versions: number } | null }>(docs: T[]): T | null {
  const ok = docs.filter((d) => d.versions && d.versions.n_revised_periods > 0);
  ok.sort(
    (a, b) =>
      Number(!!b.measure_history) - Number(!!a.measure_history) ||
      (b.versions?.n_revised_periods ?? 0) - (a.versions?.n_revised_periods ?? 0) ||
      (b.versions?.n_versions ?? 0) - (a.versions?.n_versions ?? 0)
  );
  return ok[0] ?? null;
}

/** Keep only the versions of periods >= `from` (and their dates). Rows keep their order, so asOf on the slice is
 *  exactly asOf on the full versions restricted to those periods (tested). */
export function slicePeriods(v: Versions, from: string): Versions {
  const keepP = v.periods.map((p) => p >= from);
  const rows = v.p.map((_, i) => i).filter((i) => keepP[v.p[i]]);
  const periods = v.periods.filter((_, i) => keepP[i]);
  const pIndex = new Map(periods.map((p, i) => [p, i]));
  const usedD = [...new Set(rows.map((i) => v.d[i]))].sort((a, b) => a - b);
  const dIndex = new Map(usedD.map((d, i) => [d, i]));
  const dates = usedD.map((d) => v.dates[d]);
  const revised = new Set<number>();
  const seen = new Set<number>();
  for (const i of rows) {
    if (seen.has(v.p[i])) revised.add(v.p[i]);
    seen.add(v.p[i]);
  }
  return {
    ...v,
    periods,
    dates,
    p: rows.map((i) => pIndex.get(v.periods[v.p[i]]) as number),
    d: rows.map((i) => dIndex.get(v.d[i]) as number),
    v: rows.map((i) => v.v[i]),
    n_versions: rows.length,
    n_revised_periods: revised.size,
    first_known: dates[0] ?? v.first_known,
    last_known: dates.at(-1) ?? v.last_known
  };
}

/** The period with the largest spread between its versions (relative to its last value), among periods with at least
 *  two versions. Ties: the later period. */
export function mostRevisedPeriod(v: Versions): string | null {
  let best: { p: string; s: number } | null = null;
  for (const p of v.periods) {
    const vs = periodVersions(v, p).map((x) => x.value);
    if (vs.length < 2) continue;
    const last = Math.abs(vs.at(-1) as number) || 1;
    const s = (Math.max(...vs) - Math.min(...vs)) / last;
    if (!best || s >= best.s) best = { p, s };
  }
  return best?.p ?? null;
}

/** The measure as the record said it then (measure_history, the pipeline's number per month end) next to the same
 *  period's measure in today's version (measure_path). Both are pipeline numbers; nothing is recomputed. */
export function leakageRows(h: MeasureHistory | null, path: MeasurePath | null) {
  if (!h || !h.latest_period || !h.pace || !path) return [];
  const today = new Map(path.periods.map((p, i) => [p, path.pace[i]]));
  const out: { month: string; kind: string; period: string; known_from: string | null; then: number; now: number | null }[] = [];
  h.months.forEach((m, i) => {
    const period = h.latest_period?.[i];
    const then = h.pace?.[i];
    if (!period || then === null || then === undefined) return;
    out.push({ month: m, kind: h.kind[i], period, known_from: h.known_from?.[i] ?? null, then, now: today.get(period) ?? null });
  });
  return out;
}

// ---------------------------------------------------------------- sources and licences

export type Segment = { text: string } | { text: string; href: string };

const URLISH =
  /\b((?:https?:\/\/)[^\s"'<>()[\]{}]+|(?:www\.)[a-z0-9.-]+\.[a-z]{2,}(?:\/[^\s"'<>()[\]{},;]*)?|(?:[a-z0-9-]+\.)+(?:org|com|gov|net|io|co|eu|se|markets|ai)\/[^\s"'<>()[\]{},;]*)/gi;

/** A safe absolute http(s) URL for a match, or null. Only http and https; no credentials. */
export function safeHref(raw: string): string | null {
  const t = raw.replace(/[.,;:!?'"`)\]]+$/, '');
  try {
    const u = new URL(/^https?:\/\//i.test(t) ? t : `https://${t}`);
    if (u.protocol !== 'https:' && u.protocol !== 'http:') return null;
    if (u.username || u.password) return null;
    if (!/\.[a-z]{2,}$/i.test(u.hostname)) return null;
    return u.href;
  } catch {
    return null;
  }
}

/** Split text into plain segments and link segments (URLs and bare host/path references in licence texts). The
 *  links are shown, never fetched: the page renders them as <a rel="noopener"> only. */
export function linkify(text: string): Segment[] {
  const out: Segment[] = [];
  let last = 0;
  for (const m of text.matchAll(URLISH)) {
    const raw = m[0];
    const trimmed = raw.replace(/[.,;:!?'"`)\]]+$/, '');
    const href = safeHref(trimmed);
    if (!href) continue;
    const at = m.index ?? 0;
    if (at > last) out.push({ text: text.slice(last, at) });
    out.push({ text: trimmed, href });
    last = at + trimmed.length;
  }
  if (last < text.length) out.push({ text: text.slice(last) });
  return out;
}

export interface SourceRow {
  source: string;
  license: string;
  license_text: string;
  branches: string[];
  n_series: number;
  n_published: number;
}

export interface SourceView {
  name: Segment[];
  license: string;
  text: Segment[];
  branches: string[];
  n_series: number;
  n_published: number;
  links: number;
}

export function sourceView(s: SourceRow): SourceView {
  const name = linkify(s.source ?? '');
  const text = linkify(s.license_text ?? '');
  return {
    name,
    license: s.license ?? '',
    text,
    branches: s.branches ?? [],
    n_series: s.n_series ?? 0,
    n_published: s.n_published ?? 0,
    links: [...name, ...text].filter((x) => 'href' in x).length
  };
}
