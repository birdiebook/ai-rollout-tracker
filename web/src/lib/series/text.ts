// Number precision and the generated sentences (section 4.3: every chart has a sentence from the data, which is
// also its accessible description). Neutral words only: "ökar takten", never "oroande".
import { DIRECTIONS, fmt, signed, dateLabel } from '$lib/design';
import { periodText } from './period';
import type { Measure, Method } from './types';

/** Decimals that show a number at a sensible precision on its own scale. */
export function digitsFor(x: number | null | undefined, scale?: number): number {
  const a = Math.abs(scale ?? x ?? 0);
  if (!Number.isFinite(a) || a === 0) return 1;
  if (a >= 1000) return 0;
  if (a >= 10) return 1;
  if (a >= 1) return 2;
  return Math.min(4, 1 - Math.floor(Math.log10(a)));
}

const BIG: [number, string][] = [
  [1e12, 'bn'],
  [1e9, 'md'],
  [1e6, 'mn']
];

/** Large magnitudes in Swedish short form (mn = miljoner, md = miljarder, bn = biljoner), 4 significant digits. */
export function compact(x: number, scale: number): string | null {
  const a = Math.abs(scale);
  for (const [k, w] of BIG) if (a >= k) return `${fmt(x / k, digitsFor(x / k, scale / k))} ${w}`;
  return null;
}

export const num = (x: number | null | undefined, scale?: number) =>
  x === null || x === undefined || Number.isNaN(x) ? fmt(x) : (compact(x, scale ?? x) ?? fmt(x, digitsFor(x, scale)));
export const snum = (x: number | null | undefined, scale?: number) => signed(x, digitsFor(x, scale));
/** Axis ticks: one decimal less than the values (ticks are round numbers). */
export const tickNum = (x: number, scale: number) =>
  Math.abs(scale) >= 1e6 ? (compact(x, scale) ?? fmt(x)) : fmt(x, Math.max(0, digitsFor(scale) - 1));
/** Log-axis ticks (1-2-5 × 10^k): no trailing decimals, compact for large magnitudes. */
export function logTickNum(x: number): string {
  for (const [k, w] of BIG) if (Math.abs(x) >= k) return `${fmt(x / k, 0)} ${w}`;
  return fmt(x, x >= 1 ? 0 : Math.ceil(-Math.log10(x) - 1e-9));
}
/** "1 period" / "2 perioder" */
export const plural = (n: number, one: string, many: string) => `${fmt(n)} ${n === 1 ? one : many}`;
export const tickSigned = (x: number, scale: number) => signed(x, Math.max(0, digitsFor(scale) - 1));

/** Doubling/halving times: a shorter time is more pace, so the change axis is read the other way (measures.py). */
export const paceSign = (m: Method | null | undefined) => (m === 'doubling' || m === 'halving' ? -1 : 1);

export function ordinal(p: number): string {
  return `${fmt(Math.round(p))}:e`;
}

export function levelSentence(label: string, unit: string, last: { p: string; v: number } | undefined, first: string | undefined): string {
  if (!last) return `${label}: inga värden ännu.`;
  return `Senaste värde ${num(last.v)} ${unit} (${periodText(last.p)})${first ? `, serien börjar ${periodText(first)}` : ''}.`;
}

export function paceSentence(m: Measure | null): string {
  if (!m || m.pace === null || m.pace === undefined) return 'Ingen takt på senaste perioden.';
  const pct = m.pace_percentile !== null && m.pace_percentile !== undefined ? `, den ${ordinal(m.pace_percentile)} percentilen av seriens egen historik` : '';
  return `Takten var ${snum(m.pace)} ${m.pace_unit ?? ''} för ${periodText(m.latest_period ?? '')}${pct}.`;
}

export function changeSentence(m: Measure | null): string {
  if (!m || m.change_in_pace === null || m.change_in_pace === undefined) return 'Ingen förändring i takt på senaste perioden.';
  const dir = m.direction !== null && m.direction !== undefined ? DIRECTIONS[m.direction].word : null;
  const band = m.deadband !== null && m.deadband !== undefined ? `, dödbandet är ±${num(m.deadband, m.deadband)}` : '';
  return `Förändringen i takt är ${snum(m.change_in_pace)}${band}${dir ? `: ${dir}` : ''}.`;
}

export function knownSentence(m: Measure | null): string {
  if (!m?.known_from) return '';
  return `Senaste period ${periodText(m.latest_period ?? '')}, känd från ${dateLabel(m.known_from)}.`;
}
