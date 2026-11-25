// The method page's engine against the Python engine (track W11).
// 1. Golden file (web/fixtures/method_golden.json, made by web/fixtures/gen_method_golden.py with state.branch,
//    nowcast.intervals and evaluation.holm): the same directions, index and state at every probed dead band, the same
//    quantiles, coverage, PIT, binomial bands and Holm values.
// 2. Every branch document of every bundle at the registered parameters: what the explorer computes at the
//    registered dead band is exactly the pipeline's record (index, state, counts, each series' direction).
//    Bundles: web-data-fixtures/ and, when set, SITE_BUNDLE_DIR (a real bundle).
// Index v2 (one vote per source family, register 2026-11-24) is the official rule; v1 is checked beside it.
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import pool from './illustration.json';
import {
  ascending,
  binomialBand,
  covers,
  directionAt,
  exploreBranch,
  holm,
  indexSteps,
  interval,
  pit,
  pitHistogram,
  quantile6,
  decimalRatio,
  diffusionV2Exact,
  ratioValue,
  stateOf,
  stateV2,
  voteExact,
  REGISTERED
} from './engine';
import { exploreBranchOf, rulesOf, type BranchInput } from './prepare';

const golden = JSON.parse(readFileSync(resolve('fixtures/method_golden.json'), 'utf-8'));
const fixtureSeries = (code: string) => {
  const doc = JSON.parse(readFileSync(resolve(`../web-data-fixtures/branch/${code}.json`), 'utf-8')) as BranchInput;
  const fam = new Map((doc.families ?? []).flatMap((f) => f.series.map((k) => [k, f.family] as const)));
  return doc.counted.map((s) => ({ key: s.key, method: s.method ?? null, change: s.change_in_pace as number, sd: s.sd_change as number, family: fam.get(s.key) }));
};

describe('dead band: golden values from state.branch with the dead band moved', () => {
  type Row = {
    k: number;
    index: number | null;
    state: string;
    n_up: number;
    n_neutral: number;
    n_down: number;
    n_families: number;
    index_v1: number | null;
    state_v1: string;
    votes: Record<string, number>;
    families: Record<string, string>;
    directions: Record<string, number>;
  };
  const branches = golden.deadband.branches as Record<string, Row[]>;
  for (const [code, rows] of Object.entries(branches)) {
    const doc = JSON.parse(readFileSync(resolve(`../web-data-fixtures/branch/${code}.json`), 'utf-8'));
    if ((doc.n_withheld_counted ?? 0) > 0) {
      it(`${code} counts withheld series and is not offered`, () => {
        expect(exploreBranchOf(doc).eligible).toBe(false);
      });
      continue;
    }
    it(`${code}: every probed dead band`, () => {
      const series = fixtureSeries(code);
      for (const r of rows) {
        const e = exploreBranch(series, r.k);
        expect(e.directions, `${code} k=${r.k}`).toEqual(r.directions);
        expect(e.index, `${code} k=${r.k}`).toBe(r.index);
        expect(e.state, `${code} k=${r.k}`).toBe(r.state);
        expect([e.n_up, e.n_neutral, e.n_down]).toEqual([r.n_up, r.n_neutral, r.n_down]);
        expect(e.n_families, `${code} k=${r.k}`).toBe(r.n_families);
        expect([e.index_v1, e.state_v1], `${code} k=${r.k} v1`).toEqual([r.index_v1, r.state_v1]);
        expect(Object.fromEntries(e.families.map((f) => [f.family, f.vote])), `${code} k=${r.k} votes`).toEqual(r.votes);
      }
    });
    it(`${code}: the fixture's families are the golden ones`, () => {
      const fam = Object.fromEntries(fixtureSeries(code).map((s) => [s.key, s.family]));
      expect(fam).toEqual(rows[0].families);
    });
    it(`${code}: the index steps agree with the probes`, () => {
      const series = fixtureSeries(code);
      const steps = indexSteps(series, 2.5);
      for (const r of rows.filter((x) => x.k > 0)) {
        const at = steps.filter((s) => s.from < r.k && r.k < s.to);
        // a probe exactly on a flip point lies between two steps; the others lie inside one
        if (at.length === 1) expect([at[0].index, at[0].state]).toEqual([r.index, r.state]);
      }
    });
  }
});

const bundles = [resolve('../web-data-fixtures'), process.env.SITE_BUNDLE_DIR ? resolve(process.env.SITE_BUNDLE_DIR) : null].filter(
  (d): d is string => !!d && existsSync(resolve(d, 'manifest.json'))
);

describe.each(bundles)('registered parameters reproduce the record in %s', (dir) => {
  const method = JSON.parse(readFileSync(resolve(dir, 'method.json'), 'utf-8'));
  const rules = rulesOf(method);
  it('the rules are the registered ones', () => {
    expect(rules).toEqual({ deadband_sd: 0.25, accelerating_at_least: 0.67, braking_at_most: 0.33, min_series: 3, min_families: 3, index_rule: 'v2' });
    expect(rules).toEqual(REGISTERED);
  });
  for (const code of ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9']) {
    it(`${code}`, () => {
      const doc = JSON.parse(readFileSync(resolve(dir, `branch/${code}.json`), 'utf-8'));
      const b = exploreBranchOf(doc);
      if (!b.eligible) {
        expect((doc.n_withheld_counted ?? 0) > 0 || (doc.n_series ?? 0) === 0 || b.series.length !== doc.n_series).toBe(true);
        return;
      }
      const e = exploreBranch(b.series, rules.deadband_sd, rules);
      expect(e.index).toBe(doc.index);
      expect(e.state).toBe(doc.state);
      expect([e.n_up, e.n_neutral, e.n_down]).toEqual([doc.n_up, doc.n_neutral, doc.n_down]);
      expect(e.n_families).toBe(doc.n_families);
      expect([e.index_v1, e.state_v1]).toEqual([doc.index_v1, doc.state_v1]);
      // the bundle rounds a family's vote to 4 decimals (the index itself is exact)
      const votes = new Map(e.families.map((f) => [f.family, f.vote as number]));
      expect([...votes.keys()]).toEqual((doc.families ?? []).map((f: { family: string }) => f.family));
      for (const f of doc.families ?? []) expect(votes.get(f.family), f.family).toBeCloseTo(f.vote, 4);
      for (const s of b.series) expect(directionAt(s, rules.deadband_sd), s.key).toBe(s.registered);
    });
  }
  it('at least one branch can be explored', () => {
    const n = ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9'].filter(
      (c) => exploreBranchOf(JSON.parse(readFileSync(resolve(dir, `branch/${c}.json`), 'utf-8'))).eligible
    ).length;
    expect(n).toBeGreaterThan(0);
  });
});

describe('state rule edges (register section 2)', () => {
  it('2/3 is below 0.67 and therefore stable; 0.33 itself is braking; fewer than 3 series gives no state', () => {
    expect(stateOf(2 / 3, 3)).toBe('stabil');
    expect(stateOf(0.67, 3)).toBe('accelererar');
    expect(stateOf(0.33, 3)).toBe('bromsar in');
    expect(stateOf(1, 2)).toBe('för få serier');
  });
  it('v2: one vote per family, compared exactly; fewer than 3 families gives "för få källor"', () => {
    expect(voteExact([1])).toEqual({ num: 1, den: 1 });
    expect(voteExact([1, 0])).toEqual({ num: 3, den: 4 });
    expect(voteExact([])).toBeNull();
    expect(decimalRatio(0.67)).toEqual({ num: 67, den: 100 });
    // G6 in the fixtures: votes 1/2, 1 (two series up), 1/2 -> 2/3, below 0.67: stable (v1 would say 3/4: accelerating)
    const g6 = diffusionV2Exact([[0], [1, 1], [0]]);
    expect(g6).toEqual({ num: 2, den: 3 });
    expect(ratioValue(g6)).toBe(2 / 3);
    expect(stateV2(g6, 3)).toBe('stabil');
    expect(stateV2({ num: 67, den: 100 }, 3)).toBe('accelererar');
    expect(stateV2({ num: 33, den: 100 }, 3)).toBe('bromsar in');
    expect(stateV2({ num: 1, den: 1 }, 2)).toBe('för få källor');
    expect(stateV2(null, 5)).toBe('för få källor');
  });
  it('v2 equals v1 when every family has one series', () => {
    const series = [
      { key: 'a', method: 'log', change: 3, sd: 1 },
      { key: 'b', method: 'log', change: 0, sd: 1 },
      { key: 'c', method: 'log', change: -3, sd: 1 },
      { key: 'd', method: 'log', change: 3, sd: 1 }
    ];
    const e = exploreBranch(series, 0.25);
    expect(e.index).toBe(e.index_v1);
    expect(e.n_families).toBe(4);
    const grouped = exploreBranch(series.map((s) => ({ ...s, family: s.key === 'd' ? 'a' : s.key })), 0.25);
    expect(grouped.n_families).toBe(3);
    expect(grouped.index).toBe((1 + 0.5 + 0) / 3);
    expect(grouped.index_v1).toBe(e.index_v1);
  });
  it('doubling and halving times are flipped: a shorter time is more pace', () => {
    expect(directionAt({ method: 'doubling', change: -2, sd: 1 }, 0.25)).toBe(1);
    expect(directionAt({ method: 'log', change: -2, sd: 1 }, 0.25)).toBe(-1);
    expect(directionAt({ method: 'log', change: 0.25, sd: 1 }, 0.25)).toBe(0);
  });
});

describe('intervals: golden values from nowcast.intervals', () => {
  const g = golden.intervals;
  const sorted = ascending(pool.pool);
  it('the pool is the one the golden file was made from', () => {
    expect([g.n_pool, g.n_outcomes]).toEqual([pool.pool.length, pool.outcomes.length]);
  });
  it('empirical (type 6) intervals and in-sample counts per level', () => {
    for (const r of g.by_level) {
      const [lo, hi] = interval(sorted, r.level);
      expect(lo).toBeCloseTo(r.lo, 10);
      expect(hi).toBeCloseTo(r.hi, 10);
      expect(pool.pool.filter((e) => covers(sorted, e, r.level)).length).toBe(r.inside);
    }
  });
  it('coverage, PIT and PIT histogram for every width factor', () => {
    for (const r of g.by_width) {
      const s = ascending(pool.pool.map((x) => r.w * x));
      for (const L of ['50', '80', '95']) expect(pool.outcomes.filter((e) => covers(s, e, Number(L) / 100)).length, `w=${r.w} L=${L}`).toBe(r.hits[L]);
      const p = pool.outcomes.map((e) => pit(s, e));
      p.forEach((x, i) => expect(x).toBeCloseTo(r.pit[i], 12));
      expect(pitHistogram(p)).toEqual(r.pit_histogram);
    }
  });
  it('binomial 90 % bands', () => {
    for (const [lv, bands] of Object.entries(g.binomial as Record<string, [number, number][]>)) {
      g.binomial_n.forEach((n: number, i: number) => {
        const [lo, hi] = binomialBand(n, Number(lv) / 100);
        expect(lo, `n=${n} L=${lv}`).toBeCloseTo(bands[i][0], 12);
        expect(hi, `n=${n} L=${lv}`).toBeCloseTo(bands[i][1], 12);
      });
    }
  });
  it('quantile6 clamps outside the reachable range (numpy weibull)', () => {
    expect(quantile6([1, 2, 3], 0.01)).toBe(1);
    expect(quantile6([1, 2, 3], 0.99)).toBe(3);
    expect(quantile6([1, 2, 3], 0.5)).toBe(2);
  });
});

describe('Holm: golden values from evaluation.holm', () => {
  for (const r of golden.holm) {
    it(JSON.stringify(r.p), () => {
      const got = holm(r.p);
      for (const k of Object.keys(r.p)) expect(got[k]).toBeCloseTo(r.adjusted[k], 14);
    });
  }
});
