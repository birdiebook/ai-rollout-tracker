// Periods of every frequency on one continuous time axis (D/W/2W/M/Q/A), and their Swedish labels.
// Period formats (datakontrakt "Gemensamma format"): 2026, 2026Q3, 2026-09, 2026-09-14, week 2026-09-08/2026-09-14.
import { dateLabel, periodLabel } from '$lib/design';
import type { Freq } from './types';

const DAY_MS = 86_400_000;
const utc = (y: number, m: number, d: number) => Date.UTC(y, m, d);

/** [start, end] of a period in UTC ms (end = the last day's start). null for an unknown format. */
export function periodSpan(p: string): [number, number] | null {
  let m: RegExpExecArray | null;
  if ((m = /^(\d{4}-\d{2}-\d{2})\/(\d{4}-\d{2}-\d{2})$/.exec(p))) return [Date.parse(m[1]), Date.parse(m[2])];
  if ((m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(p))) {
    const t = utc(+m[1], +m[2] - 1, +m[3]);
    return [t, t];
  }
  if ((m = /^(\d{4})-(\d{2})$/.exec(p))) return [utc(+m[1], +m[2] - 1, 1), utc(+m[1], +m[2], 1) - DAY_MS];
  if ((m = /^(\d{4})Q([1-4])$/.exec(p))) return [utc(+m[1], (+m[2] - 1) * 3, 1), utc(+m[1], +m[2] * 3, 1) - DAY_MS];
  if ((m = /^(\d{4})$/.exec(p))) return [utc(+m[1], 0, 1), utc(+m[1] + 1, 0, 1) - DAY_MS];
  return null;
}

/** The period's midpoint in UTC ms: where it sits on the time axis (so months, weeks and days line up). */
export function periodTime(p: string): number {
  const s = periodSpan(p);
  return s ? (s[0] + s[1]) / 2 : NaN;
}

const MONTHS = ['jan', 'feb', 'mar', 'apr', 'maj', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec'];

/** Human label of a period of any frequency: "14 okt 2026", "9–15 nov 2026", "okt 2026", "kv. 3 2026", "2026". */
export function periodText(p: string, long = false): string {
  const w = /^(\d{4})-(\d{2})-(\d{2})\/(\d{4})-(\d{2})-(\d{2})$/.exec(p);
  if (w) {
    const [, y1, m1, d1, y2, m2, d2] = w;
    if (y1 === y2 && m1 === m2) return `${Number(d1)}–${Number(d2)} ${MONTHS[+m2 - 1]} ${y2}`;
    if (y1 === y2) return `${Number(d1)} ${MONTHS[+m1 - 1]}–${Number(d2)} ${MONTHS[+m2 - 1]} ${y2}`;
    return `${dateLabel(`${y1}-${m1}-${d1}`)}–${dateLabel(`${y2}-${m2}-${d2}`)}`;
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(p)) return dateLabel(p);
  if (/^\d{4}$/.test(p)) return p;
  return periodLabel(p, long);
}

export const FREQ_LABEL: Record<Freq, string> = {
  D: 'daglig',
  W: 'veckovis',
  '2W': 'varannan vecka',
  M: 'månatlig',
  Q: 'kvartalsvis',
  A: 'årlig'
};

export const freqLabel = (f: string | null | undefined) => (f && FREQ_LABEL[f as Freq]) || (f ?? '–');

/** Time windows offered on the charts. 'alla' = the whole history. */
export const WINDOWS = ['alla', '10', '5', '2'] as const;
export type Window = (typeof WINDOWS)[number];
export const WINDOW_LABEL: Record<Window, string> = { alla: 'Allt', '10': '10 år', '5': '5 år', '2': '2 år' };

/** Start of a window (UTC ms) ending at `end`, or -Infinity for the whole history. */
export function windowStart(w: Window, end: number): number {
  if (w === 'alla' || !Number.isFinite(end)) return -Infinity;
  const d = new Date(end);
  return Date.UTC(d.getUTCFullYear() - Number(w), d.getUTCMonth(), d.getUTCDate());
}

/** The windows that make sense for a history of `years` (a window as long as the history is left out). */
export function windowsFor(years: number): Window[] {
  return WINDOWS.filter((w) => w === 'alla' || Number(w) < years - 0.25);
}

/** Tick label for a time axis: years for long spans, "okt 2026" for short ones. */
export function timeTick(t: number, spanYears: number): string {
  const d = new Date(t);
  if (spanYears > 3) return String(d.getUTCFullYear());
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

export const YEAR_MS = 365.25 * DAY_MS;
