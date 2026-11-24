// Quantile dot plot helpers (Kay et al. 2016; docs/steg3/hemsida_vision.md 2.2 D, prototype c). Pure functions so
// they can be tested without a DOM.

/** Stored quantiles [[p, value], ...] sorted by p -> value at probability p, linear in probability, extrapolated
 *  linearly beyond the outermost stored quantiles. */
export function quantileAt(stored: [number, number][], p: number): number {
  const q = [...stored].sort((a, b) => a[0] - b[0]);
  if (q.length === 0) return NaN;
  if (q.length === 1) return q[0][1];
  const seg = (i: number) => {
    const [p0, v0] = q[i];
    const [p1, v1] = q[i + 1];
    return v0 + ((v1 - v0) * (p - p0)) / (p1 - p0);
  };
  if (p <= q[0][0]) return seg(0);
  for (let i = 1; i < q.length; i++) if (p <= q[i][0]) return seg(i - 1);
  return seg(q.length - 2);
}

/** n equally likely outcomes: the quantiles at (i + 0.5) / n. */
export function dotValues(stored: [number, number][], n = 20): number[] {
  return Array.from({ length: n }, (_, i) => quantileAt(stored, (i + 0.5) / n));
}

export interface Dot {
  value: number;
  cx: number;
  /** stack position from the baseline, 0 = lowest */
  k: number;
}

/** Dot radius from the middle of the distribution, not from the screen width (lesson 5): the middle half of the dots
 *  should form about 4.5 bins. Clamped to [4, 11] px. */
export function dotRadius(xs: number[]): number {
  const s = [...xs].sort((a, b) => a - b);
  const n = s.length;
  if (n < 4) return 6;
  const lo = s[Math.floor(n * 0.25)];
  const hi = s[Math.ceil(n * 0.75) - 1];
  return Math.max(4, Math.min(11, (hi - lo) / (2.1 * 4.5)));
}

/** Bin pixel positions into columns of width 2.1 r and stack them. */
export function binDots(values: number[], x: (v: number) => number, x0: number, r: number): Dot[] {
  const step = r * 2.1;
  const count = new Map<number, number>();
  return [...values]
    .sort((a, b) => a - b)
    .map((value) => {
      const b = Math.round((x(value) - x0) / step);
      const k = count.get(b) ?? 0;
      count.set(b, k + 1);
      return { value, cx: x0 + b * step + r, k };
    });
}
