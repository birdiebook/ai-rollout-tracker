// asOf must give exactly what the contract's replay gives (datakontrakt section 5), and never a version before its
// known_from. Three independent checks:
//  1. golden: Python's reference replay (site_bundle.vintages.replay) at probe days around version days, for every
//     versioned fixture series (web/fixtures/series_asof_golden.json, kept current by pytest);
//  2. table semantics: an independent re-implementation of observations.as_of over the versions as rows
//     (filter known_from <= D, latest known_from per period), on every version day and the days around it;
//  3. invariants: empty before the first version, every value comes from a version known that day.
import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  asOf,
  asOfRows,
  defaultAsOf,
  emptyOn,
  knownRows,
  periodVersions,
  reconstructedOn,
  revisionSize,
  revisions,
  sampleDates,
  snapshots,
  toDay,
  versionOn
} from './versions';
import type { Versions } from './types';

const FIX = resolve('../web-data-fixtures/series');
const docs = readdirSync(FIX)
  .filter((f) => f.endsWith('.json') && f !== 'index.json')
  .map((f) => JSON.parse(readFileSync(resolve(FIX, f), 'utf-8')) as { key: string; versions: Versions | null });
const versioned = docs.filter((d) => d.versions) as { key: string; versions: Versions }[];

const golden = JSON.parse(readFileSync(resolve('fixtures/series_asof_golden.json'), 'utf-8')) as {
  series: Record<string, { day: string; n: number; changed: [number, number][] }[]>;
};

const shift = (day: string, n: number) => new Date(Date.parse(day) + n * 86_400_000).toISOString().slice(0, 10);

/** observations.as_of over rows (period, known_from, value): independent of the prefix walk in asOf. */
function tableAsOf(v: Versions, day: string): Map<string, number> {
  const rows = v.p.map((p, i) => ({ period: v.periods[p], known: v.dates[v.d[i]], value: v.v[i], i }));
  const known = rows.filter((r) => r.known <= day).sort((a, b) => (a.known < b.known ? -1 : a.known > b.known ? 1 : a.i - b.i));
  const out = new Map<string, number>();
  for (const r of known) out.set(r.period, r.value);
  return out;
}

const sameMap = (a: Map<string, number>, b: Map<string, number>) => {
  expect([...a.entries()].sort()).toEqual([...b.entries()].sort());
};

describe('asOf against Python replay (golden)', () => {
  it('covers every versioned fixture series', () => {
    expect(Object.keys(golden.series).sort()).toEqual(versioned.map((d) => d.key).sort());
  });
  for (const { key, versions: v } of versioned) {
    it(`${key}: exactly the reference replay on every probe day`, () => {
      const ref = new Map<string, number>();
      for (const probe of golden.series[key]) {
        for (const [i, val] of probe.changed) ref.set(v.periods[i], val);
        const got = asOf(v, probe.day);
        expect(got.size, `${key} ${probe.day}`).toBe(probe.n);
        sameMap(got, ref);
      }
    });
  }
});

describe('asOf against table semantics (observations.as_of)', () => {
  for (const { key, versions: v } of versioned) {
    it(`${key}: on every version day and the days around it`, () => {
      const days = new Set<string>();
      for (const d of v.dates) for (const k of [-1, 0, 1]) days.add(shift(d, k));
      for (const day of days) sameMap(asOf(v, day), tableAsOf(v, day));
    });
  }
});

describe('never a version before known_from', () => {
  for (const { key, versions: v } of versioned) {
    it(`${key}: empty before the first version, every value known that day`, () => {
      expect(asOf(v, shift(v.first_known, -1)).size).toBe(0);
      expect(emptyOn(v, shift(v.first_known, -1))).toBe(true);
      expect(asOf(v, v.first_known).size).toBeGreaterThan(0); // known_from == D counts
      for (const day of sampleDates(v, 12)) {
        const before = shift(day, -1);
        const snap = asOf(v, before);
        for (const [p, val] of snap) {
          const ok = periodVersions(v, p).some((x) => x.date <= before && x.value === val);
          expect(ok, `${key} ${p} on ${before}`).toBe(true);
        }
        // the versions that appear on `day` are not visible the day before
        const n = knownRows(v, day);
        const m = knownRows(v, before);
        for (let i = m; i < n; i++) expect(v.dates[v.d[i]]).toBe(day);
      }
    });
  }
});

describe('helpers', () => {
  const v = versioned.find((d) => d.key === 'us_ip_semis_m')!.versions;
  it('snapshots in one pass equal asOf per date, in the order asked', () => {
    const ds = [v.last_known, v.first_known, sampleDates(v, 5)[2], '2000-01-01'];
    const snaps = snapshots(v, ds);
    ds.forEach((d, i) => sameMap(snaps[i], asOf(v, d)));
  });
  it('toDay accepts dates and timestamps, rejects junk', () => {
    expect(toDay('2024-05-06T13:00:00Z')).toBe('2024-05-06');
    expect(toDay(new Date(Date.UTC(2024, 4, 6)))).toBe('2024-05-06');
    expect(() => toDay('maj 2024')).toThrow(RangeError);
  });
  it('asOf of null versions is empty; rows are sorted by period', () => {
    expect(asOf(null, '2026-01-01').size).toBe(0);
    const rows = asOfRows(v, v.last_known);
    expect(rows.map((r) => r.period)).toEqual([...rows.map((r) => r.period)].sort());
  });
  it('versionOn gives the version a reader saw that day', () => {
    expect(versionOn(v, shift(v.first_known, -1))).toBeNull();
    expect(versionOn(v, v.dates[3])).toBe(v.dates[3]);
    expect(versionOn(v, shift(v.dates[4], -1))).toBe(v.dates[3]);
  });
  it('revisions: first and latest per period agree with asOf on the first and last day', () => {
    const rs = revisions(v);
    const last = asOf(v, v.last_known);
    expect(rs.length).toBe(v.periods.length);
    for (const r of rs) {
      expect(r.latest).toBe(last.get(r.period));
      expect(asOf(v, r.firstKnown).get(r.period)).toBe(r.first);
      expect(asOf(v, shift(r.firstKnown, -1)).has(r.period)).toBe(false);
    }
    expect(rs.filter((r) => r.n > 1).length).toBe(v.n_revised_periods);
  });
  it('revisionSize is % in logs or the unit difference', () => {
    expect(revisionSize({ first: 100, latest: 110 }, true)).toBeCloseTo(9.531, 3);
    expect(revisionSize({ first: 100, latest: 110 }, false)).toBe(10);
    expect(revisionSize({ first: -1, latest: 2 }, true)).toBeNull();
  });
  it('sampleDates keeps the first and last day', () => {
    const s = sampleDates(v, 10);
    expect(s.length).toBeLessThanOrEqual(10);
    expect(s[0]).toBe(v.first_known);
    expect(s.at(-1)).toBe(v.last_known);
  });
  it('defaultAsOf is a version day about a year before the latest', () => {
    const d = defaultAsOf(v);
    expect(v.dates).toContain(d);
    expect(Date.parse(v.last_known) - Date.parse(d)).toBeGreaterThan(300 * 86_400_000);
  });
  it('collapsed versions show nothing before the cutoff (size guard)', () => {
    const c: Versions = { ...v, dates: ['2020-01-01', '2020-02-01'], p: [0, 1], d: [0, 1], v: [1, 2], periods: ['2019-11', '2019-12'], collapsed_before: '2020-01-01' };
    expect(asOf(c, '2019-12-31').size).toBe(0);
    expect(asOf(c, '2020-01-01').get('2019-11')).toBe(1);
  });
  it('reconstructedOn marks days before the last backfilled row', () => {
    expect(reconstructedOn('2025-03-01', '2025-02-28')).toBe(true);
    expect(reconstructedOn('2025-03-01', '2025-03-01')).toBe(false);
    expect(reconstructedOn(null, '2000-01-01')).toBe(false);
  });
});
