// Pure helpers for the forecast pages (W8). Everything the pages say is derived here from the site_bundle
// documents (nowcast/n<k>.json, nowcast/d2.json), so the sentences, the charts and the tables agree and can be tested
// without a DOM. Nothing is computed that the pipeline already computes: errors, CRPS, PIT, hits and coverage are
// read from the scorecard; only counts and simple fallbacks (an outcome inside a stored interval) are derived.
import type { CalendarEntry, Commit, IntervalLevel, LiveForecast, Nowcast, Pair, ScoreRow } from '$lib/data';
import { dateLabel, fmt, periodLabel } from '$lib/design';

export const LEVELS: IntervalLevel[] = ['50', '80', '95'];
/** Below this many live outcomes the calibration is not meaningful (docs/steg3/hemsida_vision.md 4.2 and 7). */
export const MIN_LIVE_FOR_CALIBRATION = 12;
/** The registered main models (CLAUDE.md, Fas 4): N2 B3, the others B1. D2 and DF are shadows. */
export const SHADOW_IDS = ['DF'];

export interface Roles {
  champion: string;
  /** naive baseline the champion is compared with: B1 when the champion is something else, otherwise B0 */
  baseline: string | null;
  /** the raw guidance variant (not the bias-corrected one), when the nowcast has one */
  guidance: string | null;
  shadows: string[];
  text: Record<string, string>;
}

export function roles(nc: Nowcast): Roles {
  const variants = nc.variants ?? [];
  const ids = variants.map((v) => v.id);
  const champion = nc.champion ?? 'B1';
  const baseline = champion !== 'B1' && ids.includes('B1') ? 'B1' : champion !== 'B0' && ids.includes('B0') ? 'B0' : null;
  const guidance =
    variants.find((v) => v.id !== champion && v.id !== baseline && /guidance/i.test(v.text) && !/korrigerad/i.test(v.text))?.id ?? null;
  const shadows = nc.shadows ?? ids.filter((i) => i !== champion);
  return { champion, baseline, guidance, shadows, text: Object.fromEntries(variants.map((v) => [v.id, v.text])) };
}

/** What a variant is on this page: the main model, the comparison baseline, guidance, or a shadow. */
export function roleOf(r: Roles, id: string): 'champion' | 'baseline' | 'guidance' | 'shadow' {
  if (id === r.champion) return 'champion';
  if (id === r.baseline) return 'baseline';
  if (id === r.guidance) return 'guidance';
  return 'shadow';
}

/** The seven stored quantiles of a live forecast (central value as the median), for the quantile dot plot. */
export function storedQuantiles(value: number | null | undefined, iv: Partial<Record<IntervalLevel, Pair>> | undefined): [number, number][] {
  const out: [number, number][] = [];
  const add = (p: number, v: number | null | undefined) => {
    if (typeof v === 'number' && Number.isFinite(v)) out.push([p, v]);
  };
  add(0.025, iv?.['95']?.[0]);
  add(0.1, iv?.['80']?.[0]);
  add(0.25, iv?.['50']?.[0]);
  add(0.5, value);
  add(0.75, iv?.['50']?.[1]);
  add(0.9, iv?.['80']?.[1]);
  add(0.975, iv?.['95']?.[1]);
  return out;
}

const num = (x: unknown): number | null => (typeof x === 'number' && Number.isFinite(x) ? x : null);

/** Safe URL segment for one live forecast: the file's base name (forecasts/n2/2026-09.json -> 2026-09). */
export function slugOf(f: Pick<LiveForecast, 'file' | 'period'>): string {
  const base = ((f.file ? f.file.split('/').pop() : '') || String(f.period ?? '')).replace(/\.json$/, '');
  return base.replace(/[^A-Za-z0-9_.-]/g, '_') || 'prognos';
}

export interface LiveRow {
  slug: string;
  period: string;
  origin: string | null;
  file: string;
  value: number | null;
  intervals: Partial<Record<IntervalLevel, Pair>>;
  variants: Record<string, number | null>;
  champion: string;
  score: ScoreRow | null;
  /** the outcome counts in the facit (scorecard status "utfall"); an outcome known at the origin does not */
  scored: boolean;
  status: string;
  outcome: number | null;
  outcomeKnown: string | null;
  /** champion's error in the nowcast's error unit (from the scorecard) */
  err: number | null;
  /** inside the champion's interval per level (scorecard hit, else derived from the stored interval) */
  inside: Partial<Record<IntervalLevel, boolean>>;
  pit: number | null;
  crps: number | null;
  /** the commit that added the file (its timestamp); null: waiting for verification, never shown as live */
  commit: Commit | null;
  /** the file has its commit, dated before the outcome became known (when it is known) */
  verified: boolean;
}

/** The commit exists and its UTC day is before the day the outcome became known (no outcome yet: the commit exists). */
export function committedBefore(c: Commit | null, outcomeKnown: string | null): boolean {
  if (!c) return false;
  return !outcomeKnown || c.date.slice(0, 10) < outcomeKnown.slice(0, 10);
}

export function inInterval(x: number | null, iv: Pair | undefined): boolean | null {
  if (x === null || !iv || iv[0] === null || iv[1] === null) return null;
  return x >= Math.min(iv[0], iv[1]) && x <= Math.max(iv[0], iv[1]);
}

/** Live forecasts joined with their scorecard row, oldest first. */
export function liveRows(nc: Nowcast): LiveRow[] {
  const score = new Map((nc.scorecard ?? []).map((s) => [s.period, s]));
  return (nc.forecasts ?? [])
    .filter((f) => f.period)
    .map((f) => {
      const period = String(f.period);
      const s = score.get(period) ?? null;
      const outcome = s && s.status !== 'väntar' ? num(s.outcome) : null;
      const scored = s?.status === 'utfall' && outcome !== null;
      const intervals = f.intervals ?? {};
      const inside: Partial<Record<IntervalLevel, boolean>> = {};
      for (const l of LEVELS) {
        if (!scored) break;
        const hit = s?.[`hit_${l}_champion`];
        const v = typeof hit === 'boolean' ? hit : typeof hit === 'number' ? hit > 0 : inInterval(outcome, (s?.[`interval_${l}`] as Pair) ?? intervals[l]);
        if (v !== null && v !== undefined) inside[l] = v;
      }
      return {
        slug: slugOf(f),
        period,
        origin: f.origin ?? (s?.origin as string | undefined) ?? null,
        file: f.file,
        value: num(f.value),
        intervals,
        variants: f.variants ?? {},
        champion: f.champion,
        score: s,
        scored,
        status: s?.status ?? 'väntar',
        outcome,
        outcomeKnown: (s?.known_from as string | null | undefined) ?? null,
        err: scored ? num(s?.err_champion) : null,
        inside,
        pit: num(s?.pit_champion),
        crps: num(s?.crps_champion),
        commit: validCommit(f.commit),
        verified: committedBefore(validCommit(f.commit), (s?.known_from as string | null | undefined) ?? null)
      };
    })
    .sort((a, b) => (a.period < b.period ? -1 : a.period > b.period ? 1 : 0));
}

/** "k av n inom" per level over the rows with an outcome. */
export function hitCounts(rows: LiveRow[]): Record<IntervalLevel, { k: number; n: number }> {
  const out = {} as Record<IntervalLevel, { k: number; n: number }>;
  for (const l of LEVELS) {
    const known = rows.filter((r) => r.inside[l] !== undefined);
    out[l] = { k: known.filter((r) => r.inside[l]).length, n: known.length };
  }
  return out;
}

/** Histogram of PIT values in `bins` equal bins on [0, 1]. */
export function pitBins(values: number[], bins = 10): number[] {
  const out = Array<number>(bins).fill(0);
  for (const v of values) if (Number.isFinite(v)) out[Math.min(bins - 1, Math.max(0, Math.floor(v * bins)))]++;
  return out;
}

/** Error of a model in a scorecard row (err_<model>), or null. */
export const errOf = (s: ScoreRow | null, model: string): number | null => num(s?.[`err_${model}`]);

/** A commit as the bundle gives it (sha of 40 hex characters, UTC date), or null when it is malformed or missing. */
export function validCommit(c: Commit | null | undefined): Commit | null {
  return c && /^[0-9a-f]{40}$/.test(c.sha) && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(c.date) ? c : null;
}

/** GitHub links that prove a forecast's timestamp: the commit that added the file (RW1-X 4a: its date is the
 *  timestamp), the file's commit history, and the file as it was at that commit (else at the build commit). Only for a
 *  github.com repository. */
export function proofLinks(repo: string | null | undefined, sha: string | null | undefined, file: string, commit?: Commit | null) {
  if (!repo || !/^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/?$/.test(repo)) return null;
  const r = repo.replace(/\/$/, '');
  const c = validCommit(commit);
  const ref = c ? c.sha : sha && /^[0-9a-f]{7,40}$/.test(sha) ? sha : 'main';
  return {
    history: `${r}/commits/main/${file}`,
    file: `${r}/blob/${ref}/${file}`,
    ref,
    commit: c ? `${r}/commit/${c.sha}` : null
  };
}

export function repoFile(repo: string | null | undefined, path: string | null | undefined): string | null {
  if (!path || !repo || !/^https:\/\/github\.com\//.test(repo)) return null;
  return `${repo.replace(/\/$/, '')}/blob/main/${path}`;
}

/** Period labels: months and quarters via format.ts; biweekly "a/b" periods by their last day. */
export function periodShort(p: string | null | undefined, long = false): string {
  if (!p) return '–';
  const w = /^(\d{4}-\d{2}-\d{2})\/(\d{4}-\d{2}-\d{2})$/.exec(p);
  if (w) return `v. t.o.m. ${dateLabel(w[2])}`;
  if (/^\d{4}-\d{2}-\d{2}$/.test(p)) return dateLabel(p);
  return periodLabel(p, long);
}

/** Axis label for a period on a time axis (year for January/Q1, otherwise short). */
export function periodTick(p: string): string {
  const q = /^(\d{4})Q([1-4])$/.exec(p);
  if (q) return q[2] === '1' ? q[1] : `kv${q[2]}`;
  const m = /^(\d{4})-(\d{2})$/.exec(p);
  if (m) return m[2] === '01' ? m[1] : periodLabel(p).split(' ')[0];
  const w = /\/(\d{4})-(\d{2})-\d{2}$/.exec(p);
  if (w) return periodLabel(`${w[1]}-${w[2]}`);
  return p;
}

/** Tick periods for a categorical time axis: every year start, thinned to at most `max` ticks. */
export function yearTicks(periods: string[], max = 8): string[] {
  const starts = periods.filter((p, i) => i === 0 || p.slice(0, 4) !== periods[i - 1].slice(0, 4));
  const ticks = starts.length >= 2 ? starts.slice(1) : periods.filter((_, i) => i % Math.ceil(periods.length / 4) === 0);
  const step = Math.ceil(ticks.length / max);
  return ticks.filter((_, i) => i % step === 0);
}

/** Whole days from `today` to `date` (both YYYY-MM-DD), or null. */
export function daysUntil(today: string | null | undefined, date: string | null | undefined): number | null {
  if (!today || !date) return null;
  const t = Date.parse(today + 'T00:00:00Z');
  const d = Date.parse(date + 'T00:00:00Z');
  if (Number.isNaN(t) || Number.isNaN(d)) return null;
  return Math.round((d - t) / 86_400_000);
}

export const valueFmt = (nc: Pick<Nowcast, 'decimals'>) => (v: number | null | undefined) => fmt(v, nc.decimals ?? 0);

/** A plain-Swedish count: 0 -> "inga", 1 -> "en", else the number. */
export function count(n: number, one = 'en', none = 'inga'): string {
  return n === 0 ? none : n === 1 ? one : String(n);
}

/** The overview's generated sentence (P1): how many forecasts are followed, how many live, the next one. */
export function overviewSentence(cal: CalendarEntry[], liveCount: number, outcomeCount: number, today?: string | null): string {
  const next = cal
    .filter((c) => c.next_origin && (!today || c.next_origin >= today))
    .sort((a, b) => String(a.next_origin).localeCompare(String(b.next_origin)))[0];
  const parts = [
    `${cal.length} prognoser följs.`,
    liveCount === 0
      ? 'Ingen skarp prognos är lämnad ännu.'
      : `${liveCount === 1 ? 'En skarp prognos' : `${liveCount} skarpa prognoser`} är lämnad${liveCount === 1 ? '' : 'e'}, ${count(outcomeCount, 'en', 'ingen')} med utfall.`
  ];
  if (next) parts.push(`Nästa: ${next.label} den ${dateLabel(String(next.next_origin))} för ${periodShort(next.next_period, true)}.`);
  return parts.join(' ');
}

/** The calibration honesty note: below MIN_LIVE_FOR_CALIBRATION live outcomes the coverage is not meaningful. */
export function calibrationNote(nOutcomes: number): string {
  if (nOutcomes === 0) return `Inga skarpa utfall ännu. Kalibreringen blir meningsfull först efter cirka ${MIN_LIVE_FOR_CALIBRATION} skarpa utfall.`;
  if (nOutcomes < MIN_LIVE_FOR_CALIBRATION)
    return `${nOutcomes} av cirka ${MIN_LIVE_FOR_CALIBRATION} skarpa utfall. För få för att bedöma kalibreringen: andelarna nedan kan vara slump.`;
  return `${nOutcomes} skarpa utfall. Det grå bandet visar vad slumpen ger runt den nominella nivån.`;
}

/** y-domain covering all finite values, padded. */
export function extent(values: (number | null | undefined)[], pad = 0.06): [number, number] {
  const v = values.filter((x): x is number => typeof x === 'number' && Number.isFinite(x));
  if (!v.length) return [0, 1];
  let lo = Math.min(...v);
  let hi = Math.max(...v);
  if (lo === hi) {
    const d = Math.abs(lo) * 0.1 || 1;
    lo -= d;
    hi += d;
  }
  const p = (hi - lo) * pad;
  return [lo - p, hi + p];
}

/** Domain for the quantile dot plot: the 95 % interval, padded; the outcome is included when it is near, otherwise
 *  it is shown as off the scale (an arrow), so that a far outcome does not squash the distribution. */
export function dotDomain(q: [number, number][], outcome: number | null): { domain: [number, number]; offScale: -1 | 0 | 1 } {
  const vals = q.map((x) => x[1]);
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const w = hi - lo || Math.abs(hi) * 0.1 || 1;
  let a = lo - w * 0.12;
  let b = hi + w * 0.12;
  let off: -1 | 0 | 1 = 0;
  if (outcome !== null) {
    if (outcome < a) {
      if (outcome >= lo - w) a = outcome - w * 0.08;
      else off = -1;
    } else if (outcome > b) {
      if (outcome <= hi + w) b = outcome + w * 0.08;
      else off = 1;
    }
  }
  return { domain: [a, b], offScale: off };
}
