import { describe, expect, it } from 'vitest';
import { binDots, dotRadius, dotValues, quantileAt } from './quantiles';

const stored: [number, number][] = [[0.025, 228], [0.1, 236.5], [0.25, 243], [0.5, 249], [0.75, 255.5], [0.9, 262], [0.975, 271]];

describe('quantile dot plot', () => {
  it('interpolates linearly in probability and hits stored quantiles', () => {
    expect(quantileAt(stored, 0.5)).toBe(249);
    expect(quantileAt(stored, 0.375)).toBeCloseTo(246, 6);
    expect(quantileAt(stored, 0.01)).toBeLessThan(228);
  });
  it('gives n increasing, equally likely values', () => {
    const v = dotValues(stored, 20);
    expect(v).toHaveLength(20);
    for (let i = 1; i < v.length; i++) expect(v[i]).toBeGreaterThan(v[i - 1]);
    expect(v.filter((x) => x < 249).length).toBe(10);
  });
  it('sets the radius from the middle of the distribution, clamped to [4, 11]', () => {
    expect(dotRadius([0, 1, 2, 3, 4, 5, 6, 7])).toBe(4);
    expect(dotRadius(Array.from({ length: 20 }, (_, i) => i * 100))).toBe(11);
  });
  it('stacks dots in the same bin', () => {
    const d = binDots([1, 1.01, 1.02, 5], (v) => v * 10, 0, 4);
    expect(d.filter((x) => x.k > 0).length).toBe(2);
    expect(new Set(d.map((x) => x.cx)).size).toBe(2);
  });
});
