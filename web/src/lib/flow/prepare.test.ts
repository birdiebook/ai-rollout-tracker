import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import {
  deadbandSentence,
  indexSentence,
  invertedPace,
  leadsOfBranch,
  multipleSentence,
  periodTime,
  reconciliationsFor,
  sharedDomain,
  thin,
  toMultiple,
  trim,
  withheldForLead,
  withheldView
} from './prepare';
import type { BranchDoc, FlowDoc, SeriesEntry } from './types';

const fx = (p: string) => JSON.parse(readFileSync(resolve('../web-data-fixtures', p), 'utf-8'));
const flow = fx('flow.json') as FlowDoc;
const g9 = fx('branch/G9.json') as BranchDoc;
const g6 = fx('branch/G6.json') as BranchDoc;

describe('periodTime', () => {
  it('puts every frequency on one fractional-year axis, in order', () => {
    const ps = ['2025', '2025Q4', '2025-11', '2025-12-01', '2025-12-08/2025-12-14', '2026-01'];
    const ts = ps.map(periodTime);
    expect(ts.every(Number.isFinite)).toBe(true);
    expect([...ts].sort((a, b) => a - b)).toEqual(ts.slice(0, 1).concat(ts.slice(1)).sort((a, b) => a - b));
    expect(periodTime('2026-01')).toBeCloseTo(2026 + 0.5 / 12);
    expect(periodTime('2026Q3')).toBeCloseTo(2026.625);
    expect(periodTime('nonsense')).toBeNaN();
  });
});

describe('thin and trim', () => {
  it('keeps at most max points and always the last one', () => {
    const n = 1000;
    const xy = { periods: Array.from({ length: n }, (_, i) => `p${i}`), values: Array.from({ length: n }, (_, i) => i) };
    const t = thin(xy, 160);
    expect(t.periods.length).toBeLessThanOrEqual(160);
    expect(t.values.at(-1)).toBe(n - 1);
    expect(thin({ periods: ['a'], values: [1] })).toEqual({ periods: ['a'], values: [1] });
  });
  it('drops leading and trailing nulls, null when empty', () => {
    expect(trim({ periods: ['a', 'b', 'c', 'd'], values: [null, 1, 2, null] })).toEqual({ periods: ['b', 'c'], values: [1, 2] });
    expect(trim({ periods: ['a'], values: [null] })).toBeNull();
  });
});

describe('toMultiple', () => {
  const e = g6.counted[0];
  it('copies the pipeline measures, never recomputes them', () => {
    const m = toMultiple(e, { linkable: true });
    expect(m.pace).toBe(e.pace);
    expect(m.change_in_pace).toBe(e.change_in_pace);
    expect(m.direction).toBe(e.direction);
    expect(m.pacePath?.values.at(-1)).toBe(e.path?.pace.filter((v) => v !== null).at(-1));
    expect(m.levelPath).toBeNull();
  });
  it('thins and windows the level path to the pace window', () => {
    const periods = Array.from({ length: 400 }, (_, i) => `${1990 + Math.floor(i / 12)}-${String((i % 12) + 1).padStart(2, '0')}`);
    const m = toMultiple(e, { linkable: true, levels: { periods, values: periods.map((_, i) => i + 1) } });
    expect(m.levelPath!.periods.length).toBeLessThanOrEqual(160);
    expect(periodTime(m.levelPath!.periods[0])).toBeGreaterThanOrEqual(periodTime(m.pacePath!.periods[0]) - 1);
    expect(m.levelPath!.values.at(-1)).toBe(400);
  });
  it('marks uncounted series and says so in the sentence', () => {
    const m = toMultiple({ ...e, reason: 'för kort historik' } as SeriesEntry, { linkable: false, counted: false });
    expect(m.counted).toBe(false);
    expect(multipleSentence(m, 'pace')).toContain('Räknas inte');
  });
});

describe('sentences', () => {
  it('generates the multiple, dead band and index sentences from the data', () => {
    const m = toMultiple(g6.counted[0], { linkable: true });
    expect(multipleSentence(m, 'pace')).toMatch(/takten [+−±]\d/);
    expect(deadbandSentence(m)).toMatch(/dödband ±\d/);
    const s = indexSentence(g6.history);
    expect(s).toContain('Gränserna 0,33 och 0,67');
    expect(indexSentence([])).toBe('Inget index i historiken.');
  });
  it('flips doubling and halving times (shorter = more pace)', () => {
    expect(invertedPace('doubling')).toBe(true);
    expect(invertedPace('halving')).toBe(true);
    expect(invertedPace('log')).toBe(false);
  });
});

describe('chain helpers', () => {
  it('finds the leads of a branch and the reconciliations of a lead', () => {
    expect(leadsOfBranch(flow, 'G6')).toEqual(['L6']);
    expect(reconciliationsFor(flow, 'L4').length).toBeGreaterThan(0);
    expect(reconciliationsFor(flow, 'L9')).toEqual([]);
  });
  it('shares one x domain across a set of multiples', () => {
    const ms = g6.counted.map((e) => toMultiple(e, { linkable: true }));
    const d = sharedDomain(ms, 'pace')!;
    for (const m of ms) if (m.pacePath) expect(periodTime(m.pacePath.periods[0])).toBeGreaterThanOrEqual(d[0]);
  });
});

describe('withheld series (licence gate on the page)', () => {
  it('names a lead’s withheld key series only when they can be attributed exactly', () => {
    const l9 = flow.leads.find((l) => l.code === 'L9')!;
    const branchOf = new Map(g9.withheld.map((w) => [w.key, 'G9']));
    expect(withheldForLead(l9, flow.withheld, branchOf)?.map((w) => w.key)).toEqual(flow.withheld.map((w) => w.key));
    // unknown branch -> only the count, never a guess
    expect(withheldForLead(l9, flow.withheld, new Map())).toBeNull();
    expect(withheldForLead({ ...l9, n_withheld: 0 }, flow.withheld, branchOf)).toEqual([]);
  });
  it('the view keeps names and reasons only: no numbers, no direction', () => {
    for (const w of g9.withheld) {
      const v = withheldView({ ...w, direction: 1, value: 7e6 } as never);
      expect(Object.keys(v).sort()).toEqual(['counted', 'key', 'label', 'license', 'source', 'why']);
      expect(Object.values(v).some((x) => typeof x === 'number')).toBe(false);
    }
  });
});
