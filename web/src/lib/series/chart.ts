// Scale helpers shared by the series charts (any frequency on one UTC time axis; linear or log values).
import { extent } from 'd3-array';
import { scaleLinear, scaleLog, scaleUtc } from 'd3-scale';
import type { ChartDims, TooltipContent } from '$lib/design';
import { YEAR_MS, timeTick } from './period';

export interface HoverPoint {
  x: number;
  y: number;
  tip: TooltipContent;
}

export interface TimePoint {
  /** period */
  p: string;
  /** UTC ms (period midpoint) */
  t: number;
  v: number;
}

/** UTC time scale over [t0, t1]; a single instant is padded by half a year on each side. */
export function timeScale(t0: number, t1: number, d: ChartDims) {
  const pad = t1 > t0 ? 0 : YEAR_MS / 2;
  return scaleUtc().domain([t0 - pad, t1 + pad]).range([d.left, d.right]);
}

export function timeTicks(x: ReturnType<typeof scaleUtc>, d: ChartDims): { values: Date[]; format: (v: Date) => string } {
  const [a, b] = x.domain();
  const span = (b.getTime() - a.getTime()) / YEAR_MS;
  const n = Math.max(2, Math.floor(d.innerWidth / 80));
  let values = x.ticks(n);
  // year labels for long spans: keep only Jan 1 ticks so a label never repeats
  if (span > 3) values = values.filter((v) => v.getUTCMonth() === 0 && v.getUTCDate() === 1);
  return { values, format: (v: Date) => timeTick(v.getTime(), span) };
}

/** True when a log scale can show the values (all positive, and they span enough to need it). */
export const logAllowed = (vals: number[]) => vals.length > 1 && vals.every((v) => v > 0);

/** Default scale: log for positive quantities measured in logs (log, doubling, halving) that change at least
 *  threefold (section 4.1: log scale for exponential quantities). */
export function defaultLog(vals: number[], method: string | null | undefined): boolean {
  if (!['log', 'doubling', 'halving'].includes(method ?? '') || !logAllowed(vals)) return false;
  const [lo, hi] = extent(vals) as [number, number];
  return hi / lo >= 3;
}

/** 1-2-5 ticks inside a positive domain, at most `max`. */
export function logTicks(lo: number, hi: number, max = 6): number[] {
  const out: number[] = [];
  for (let e = Math.floor(Math.log10(lo)); e <= Math.ceil(Math.log10(hi)); e++)
    for (const m of [1, 2, 5]) {
      const v = m * 10 ** e;
      if (v >= lo && v <= hi) out.push(v);
    }
  if (out.length <= max) return out.length ? out : [lo, hi];
  const pow = out.filter((v) => Math.log10(v) % 1 === 0);
  return pow.length >= 2 ? pow : out.filter((_, i) => i % Math.ceil(out.length / max) === 0);
}

export function valueScale(vals: number[], d: ChartDims, opts: { log?: boolean; zero?: boolean; pad?: number[] } = {}) {
  const all = [...vals, ...(opts.pad ?? [])].filter((v) => Number.isFinite(v));
  let [lo, hi] = (all.length ? extent(all) : [0, 1]) as [number, number];
  if (opts.log && logAllowed(all)) {
    // no nice(): on a log axis it can add a whole decade of empty space; a 5 % margin instead
    if (lo === hi) [lo, hi] = [lo / 1.5, hi * 1.5];
    return { scale: scaleLog().domain([lo / 1.05, hi * 1.05]).range([d.bottom, d.top]), log: true as const };
  }
  if (opts.zero) [lo, hi] = [Math.min(0, lo), Math.max(0, hi)];
  if (lo === hi) [lo, hi] = lo === 0 ? [-1, 1] : [lo - Math.abs(lo) * 0.1, hi + Math.abs(hi) * 0.1];
  return { scale: scaleLinear().domain([lo, hi]).nice(4).range([d.bottom, d.top]), log: false as const };
}
