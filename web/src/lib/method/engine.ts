// The method page's engine (track W11). Pure functions, no DOM. Each one is the TypeScript form of one Python
// function and is checked against it in engine.test.ts (golden file web/fixtures/method_golden.json, made by the
// Python engine itself, and every branch document of the bundle at the registered parameters):
//   directionAt / exploreBranch   ai_tracker.state.measures (direction) and state.branch.branch / diffusion / state_of
//   quantile6 / interval / pit    ai_tracker.nowcast.intervals.ErrorDistribution (empirical case, G-C)
//   binomialBand                  ai_tracker.nowcast.intervals.binomial_band
//   holm                          ai_tracker.evaluation.holm
// The page never replaces a registered number with one of these: the registered value is read from the bundle and
// drawn as "registrerat"; these give the reader's exploration ("utforskning") at other parameter values.

export type Dir = 1 | 0 | -1;
export type StateWord = 'accelererar' | 'stabil' | 'bromsar in' | 'för få serier' | 'inga registrerade kärnserier';

export interface Rules {
  deadband_sd: number;
  accelerating_at_least: number;
  braking_at_most: number;
  min_series: number;
}

/** The registered rules (docs/mattregister.md section 2), used when method.json lacks them. */
export const REGISTERED: Rules = { deadband_sd: 0.25, accelerating_at_least: 0.67, braking_at_most: 0.33, min_series: 3 };

/** What the engine needs of one counted series (branch/<G>.json `counted[]`). */
export interface ExploreSeries {
  key: string;
  label: string;
  method: string | null;
  change: number;
  sd: number;
  /** the pipeline's direction at the registered dead band */
  registered: Dir;
}

/** Doubling and halving times: a shorter time is acceleration, so the sign flips (register 2026-11-23, Fas 5 p. 2). */
export const signOf = (method: string | null | undefined): 1 | -1 => (method === 'doubling' || method === 'halving' ? -1 : 1);

/** Change in pace in units of the series' expanding SD, signed so that right = more pace. */
export const zOf = (s: Pick<ExploreSeries, 'method' | 'change' | 'sd'>): number => (signOf(s.method) * s.change) / s.sd;

/** Direction at dead band k (in SD): measures.py `1 if signed > band else -1 if signed < -band else 0`. */
export function directionAt(s: Pick<ExploreSeries, 'method' | 'change' | 'sd'>, k: number): Dir {
  const band = k * s.sd;
  const signed = signOf(s.method) * s.change;
  return signed > band ? 1 : signed < -band ? -1 : 0;
}

/** branch.diffusion: (n_up + 0.5 n_neutral) / n, the same float operations as Python. */
export function diffusion(dirs: Dir[]): number | null {
  if (dirs.length === 0) return null;
  let up = 0;
  let neutral = 0;
  for (const d of dirs) {
    if (d === 1) up++;
    else if (d === 0) neutral++;
  }
  return (up + 0.5 * neutral) / dirs.length;
}

/** branch.state_of: the index compared unrounded (2/3 = 0.667 is below 0.67: stable). */
export function stateOf(index: number | null, n: number, r: Rules = REGISTERED): StateWord {
  if (n < r.min_series || index === null) return 'för få serier';
  if (index >= r.accelerating_at_least) return 'accelererar';
  if (index <= r.braking_at_most) return 'bromsar in';
  return 'stabil';
}

export interface Explored {
  k: number;
  index: number | null;
  state: StateWord;
  n_series: number;
  n_up: number;
  n_neutral: number;
  n_down: number;
  directions: Record<string, Dir>;
}

export function exploreBranch(series: Pick<ExploreSeries, 'key' | 'method' | 'change' | 'sd'>[], k: number, r: Rules = REGISTERED): Explored {
  const directions: Record<string, Dir> = {};
  const dirs = series.map((s) => (directions[s.key] = directionAt(s, k)));
  const index = diffusion(dirs);
  return {
    k,
    index,
    state: stateOf(index, series.length, r),
    n_series: series.length,
    n_up: dirs.filter((d) => d === 1).length,
    n_neutral: dirs.filter((d) => d === 0).length,
    n_down: dirs.filter((d) => d === -1).length,
    directions
  };
}

/** The dead-band values where some series changes direction (|z|), ascending and distinct. Between two of them
 *  the branch's index is constant, so the index as a function of k is a step function with these steps. */
export function flipPoints(series: Pick<ExploreSeries, 'method' | 'change' | 'sd'>[]): number[] {
  return [...new Set(series.map((s) => Math.abs(zOf(s))))].sort((a, b) => a - b);
}

/** The index over k in [0, kMax] as steps [{from, to, index, state}]. A series exactly on the band edge is neutral
 *  (the rule is strict: signed > band), so the value at a flip point itself belongs to the step on its right. */
export function indexSteps(series: Pick<ExploreSeries, 'key' | 'method' | 'change' | 'sd'>[], kMax: number, r: Rules = REGISTERED) {
  const cuts = [0, ...flipPoints(series).filter((x) => x > 0 && x < kMax), kMax];
  const out: { from: number; to: number; index: number | null; state: StateWord }[] = [];
  for (let i = 0; i < cuts.length - 1; i++) {
    const mid = (cuts[i] + cuts[i + 1]) / 2;
    const e = exploreBranch(series, mid, r);
    const last = out.at(-1);
    if (last && last.index === e.index && last.state === e.state) last.to = cuts[i + 1];
    else out.push({ from: cuts[i], to: cuts[i + 1], index: e.index, state: e.state });
  }
  return out;
}

// ---------------------------------------------------------------- intervals (G-C, empirical case)

/** numpy.quantile(x, p, method="weibull") (Hyndman-Fan type 6) on an ascending sample, with numpy's lerp. */
export function quantile6(sorted: number[], p: number): number {
  const n = sorted.length;
  if (n === 0) return NaN;
  const virt = n * p + p - 1;
  if (virt < 0) return sorted[0];
  if (virt >= n - 1) return sorted[n - 1];
  const lo = Math.floor(virt);
  const g = virt - lo;
  const a = sorted[lo];
  const b = sorted[lo + 1];
  const diff = b - a;
  return g >= 0.5 ? b - diff * (1 - g) : a + diff * g;
}

export const ascending = (x: number[]) => [...x].sort((a, b) => a - b);

/** Central `level` interval of the error: [Q((1-L)/2), Q((1+L)/2)]. */
export function interval(sorted: number[], level: number): [number, number] {
  return [quantile6(sorted, (1 - level) / 2), quantile6(sorted, (1 + level) / 2)];
}

export function covers(sorted: number[], e: number, level: number): boolean {
  const [lo, hi] = interval(sorted, level);
  return lo <= e && e <= hi;
}

/** PIT of the outcome, mid-rank: (#{x > e} + 0.5 #{x = e} + 0.5) / (n + 1). */
export function pit(sorted: number[], e: number): number {
  let above = 0;
  let ties = 0;
  for (const x of sorted) {
    if (x > e) above++;
    else if (x === e) ties++;
  }
  return (above + 0.5 * ties + 0.5) / (sorted.length + 1);
}

/** intervals.pit_histogram: ten equal bins on [0, 1], 1 in the last bin (numpy.histogram). */
export function pitHistogram(values: number[], bins = 10): number[] {
  const out = new Array(bins).fill(0);
  for (const v of values) {
    if (!Number.isFinite(v)) continue;
    const x = Math.min(1, Math.max(0, v));
    out[Math.min(bins - 1, Math.floor(x * bins))]++;
  }
  return out;
}

/** 5th and 95th percentile of Bin(n, level) / n: the smallest k with P(K <= k) >= prob (intervals.binomial_band). */
export function binomialBand(n: number, level: number, probs: [number, number] = [0.05, 0.95]): [number, number] {
  if (n <= 0) return [NaN, NaN];
  const logC: number[] = [0];
  for (let k = 1; k <= n; k++) logC.push(logC[k - 1] + Math.log((n - k + 1) / k));
  const cdf: number[] = [];
  let acc = 0;
  for (let k = 0; k <= n; k++) {
    const lp = logC[k] + (k ? k * Math.log(level) : 0) + (n - k ? (n - k) * Math.log1p(-level) : 0);
    acc += Math.exp(lp);
    cdf.push(acc);
  }
  const search = (p: number) => {
    const t = p - 1e-12;
    let i = 0;
    while (i < cdf.length && cdf[i] < t) i++;
    return i / n;
  };
  return [search(probs[0]), search(probs[1])];
}

// ---------------------------------------------------------------- Holm

/** evaluation.holm: step-down, monotone, capped at 1. */
export function holm(p: Record<string, number>): Record<string, number> {
  const valid = Object.entries(p)
    .filter(([, v]) => !Number.isNaN(v))
    .sort((a, b) => a[1] - b[1] || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
  const m = valid.length;
  const out: Record<string, number> = Object.fromEntries(Object.keys(p).map((k) => [k, NaN]));
  let running = 0;
  valid.forEach(([k, v], i) => {
    running = Math.max(running, Math.min(1, (m - i) * v));
    out[k] = running;
  });
  return out;
}

/** The promotion rule (G-B, F-E6): Holm-p < 0.10 and a lower MAE than the comparison model in both periods. */
export function promoted(holmP: number, maeBetterAll: boolean, maeBetterRecent: boolean, alpha = 0.1): boolean {
  return holmP < alpha && maeBetterAll && maeBetterRecent;
}
