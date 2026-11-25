// Pure helpers for the reconciliation page (track W10). The ratio's level, pace, change in pace, percentiles and
// direction come from the pipeline (flow.json). The only arithmetic here is the exact split of the pipeline's pace
// into its numerator and denominator parts, from the component levels as they were known on the record date:
//   pace = 100·Δ4 log(ratio) = 100·Δ4 log(N) − 100·Δ4 log(D)        (the scale cancels in the difference)
// Whatever does not add up (versions, rounding, synthetic fixtures) is shown as a rest, never hidden.
import { fmt, periodLabel, signed } from '$lib/design';
import type { ReconDef, ReconView, Term } from './types';
import defs from './reconciliations.json';

export const RECON_DEFS: ReconDef[] = defs.reconciliations;
export const reconDef = (key: string): ReconDef | undefined => RECON_DEFS.find((d) => d.key === key);

/** "2026Q3" shifted by k quarters (negative = earlier). */
export function qShift(p: string, k: number): string {
  const m = /^(\d{4})Q([1-4])$/.exec(p);
  if (!m) throw new RangeError(`not a quarter: ${p}`);
  const n = Number(m[1]) * 4 + Number(m[2]) - 1 + k;
  return `${Math.floor(n / 4)}Q${(n % 4) + 1}`;
}

/** Sum of the terms for quarter p (a 4-quarter term sums p-3..p); null when any input is missing. */
export function side(terms: Term[], levels: Map<string, Map<string, number>>, p: string): number | null {
  let s = 0;
  for (const t of terms) {
    const lv = levels.get(t.series);
    if (!lv) return null;
    for (let k = 0; k < t.window; k++) {
      const v = lv.get(qShift(p, -k));
      if (v === undefined || !Number.isFinite(v)) return null;
      s += v;
    }
  }
  return s;
}

const yoy = (a: number | null, b: number | null) => (a !== null && b !== null && a > 0 && b > 0 ? 100 * Math.log(a / b) : null);

/** Per quarter of the pace path: numerator part, denominator part (with its sign: −Δ4 log D) and the rest. */
export function contributions(def: ReconDef, levels: Map<string, Map<string, number>>, periods: string[], pace: (number | null)[]) {
  const num_c: (number | null)[] = [];
  const den_c: (number | null)[] = [];
  const rest: (number | null)[] = [];
  const nIdx: (number | null)[] = [];
  const dIdx: (number | null)[] = [];
  let base: [number, number] | null = null;
  periods.forEach((p, i) => {
    const n = side(def.num, levels, p);
    const d = side(def.den, levels, p);
    const nc = yoy(n, side(def.num, levels, qShift(p, -4)));
    const dc0 = yoy(d, side(def.den, levels, qShift(p, -4)));
    const dc = dc0 === null ? null : -dc0;
    num_c.push(nc);
    den_c.push(dc);
    rest.push(nc !== null && dc !== null && pace[i] !== null && pace[i] !== undefined ? (pace[i] as number) - nc - dc : null);
    if (!base && n !== null && d !== null && n > 0 && d > 0) base = [n, d];
    nIdx.push(base && n !== null ? (100 * n) / base[0] : null);
    dIdx.push(base && d !== null ? (100 * d) / base[1] : null);
  });
  const rs = rest.filter((r): r is number => r !== null).map(Math.abs);
  return { num_c, den_c, rest, num_idx: nIdx, den_idx: dIdx, max_rest: rs.length ? Math.max(...rs) : null };
}

/** Rests below this (log ×100) are rounding: the bundle rounds levels to 6 significant digits. */
export const REST_TOLERANCE = 0.05;

const termText = (t: Term, label: (k: string) => string) => (t.window === 4 ? `summa 4 kv. av ${label(t.series)}` : label(t.series));
export function formula(def: ReconDef, label: (k: string) => string = (k) => k): string {
  const part = (ts: Term[]) => (ts.length > 1 ? `(${ts.map((t) => termText(t, label)).join(' + ')})` : termText(ts[0], label));
  return `${part(def.num)} / ${part(def.den)}${def.scale !== 1 ? ` × ${fmt(def.scale)}` : ''}`;
}

/** A level in a ratio's own unit: 1,44 (kvot) or 115 % (procent av OCF). */
export function levelText(v: number | null, unit: string): string {
  if (v === null) return '–';
  if (unit.startsWith('procent')) return `${fmt(v, 0)} %`;
  return fmt(v, Math.abs(v) >= 10 ? 1 : 2);
}

export const ordinal = (p: number | null) => (p === null ? '–' : `${fmt(p, 0)}:e percentilen`);

/** The page's headline sentence: how many ratios, where their pace sits in its own history, and directions. */
export function overviewSentence(rs: Pick<ReconView, 'pace_percentile' | 'direction'>[]): string {
  const n = rs.length;
  if (!n) return 'Inga avstämningar i paketet.';
  const high = rs.filter((r) => r.pace_percentile !== null && r.pace_percentile >= 50).length;
  const c = (d: number) => rs.filter((r) => r.direction === d).length;
  const word = (k: number) => (k === 0 ? 'ingen' : String(k));
  const cap = (x: string) => x.charAt(0).toUpperCase() + x.slice(1);
  const lead = n === 1 ? 'En kvot förbinder leden. Dess takt ligger ' + (high ? 'över' : 'under') + ' medianen i sin egen historik.'
    : `${n} kvoter förbinder leden. För ${word(high)} av dem ligger takten över medianen i sin egen historik.`;
  return `${lead} ${cap(word(c(1)))} ökar takten, ${word(c(0))} har oförändrad takt och ${word(c(-1))} minskar takten.`;
}

/** The generated sentence of the contribution chart (also its accessible name). */
export function contributionSentence(r: ReconView): string {
  const i = r.periods.length - 1;
  if (i < 0 || r.pace_path[i] === null) return `${r.short}: ingen takt i posten.`;
  const p = periodLabel(r.periods[i]);
  const base = `Takten ${p} var ${signed(r.pace_path[i], 1)} (log ×100 per år).`;
  if (r.num_c[i] === null || r.den_c[i] === null) return `${base} Komponenterna saknas för kvartalet.`;
  const rest = r.rest[i] !== null && Math.abs(r.rest[i] as number) >= REST_TOLERANCE ? ` Resten ${signed(r.rest[i], 1)} förklaras inte av komponenterna.` : '';
  return `${base} Täljaren bidrog med ${signed(r.num_c[i], 1)} och nämnaren med ${signed(r.den_c[i], 1)}.${rest}`;
}

export function ratioSentence(r: ReconView): string {
  return (
    `${r.short} ${r.latest_period ? periodLabel(r.latest_period) : ''}: ${levelText(r.level, r.unit)}` +
    `${r.unit.startsWith('procent') ? '' : ` (${r.unit})`}. Takten ligger på ${ordinal(r.pace_percentile)} av ${r.n_pace ?? '–'} kvartal.`
  );
}

export function sidesSentence(r: ReconView): string {
  const i = r.periods.length - 1;
  const first = r.num_idx.findIndex((v) => v !== null);
  if (i < 0 || first < 0) return `${r.short}: täljare och nämnare saknas.`;
  return (
    `Indexerat till 100 ${periodLabel(r.periods[first])}: täljaren ${fmt(r.num_idx[i], 0)} och nämnaren ${fmt(r.den_idx[i], 0)} ` +
    `${periodLabel(r.periods[i])}.`
  );
}

/** Year ticks for a fractional-year axis: every year, or every 2nd/4th on long spans. */
export function yearTicks(lo: number, hi: number): number[] {
  const span = hi - lo;
  const step = span > 12 ? 4 : span > 6 ? 2 : 1;
  const out: number[] = [];
  for (let y = Math.ceil(lo); y <= hi; y++) if (y % step === 0) out.push(y);
  return out;
}
