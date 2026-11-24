// Leakage proofs for time travel (W9). Three kinds:
//  1. golden: the cut of TODAY's bundle (gate.ts) equals Python's replay ON the day (web/fixtures/
//     timetravel_golden.json, made by gen_timetravel_golden.py from the source table: vintages.encode(rows, D),
//     observations.as_of(key, D), site.data.Record(today=D) with only the snapshots dated <= D);
//  2. invariants over every 9th day 2009–2027: nothing in any cut is dated after the day, the cut replays exactly
//     like the full versions on that day and never changes for later days, and it grows monotonically;
//  3. the guard itself: a doctored bundle with later knowledge throws instead of rendering.
// Real data: TT_BUNDLE=<site_bundle dir> TT_GOLDEN=<gen_timetravel_golden.py --real output> npx vitest run timetravel
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import type { Branch, Overview } from '$lib/data';
import type { SeriesDoc, Versions } from '$lib/series/types';
import { asOf } from '$lib/series/versions';
import {
  LeakError,
  branchOn,
  cutVersions,
  lastMonthEnd,
  leaks,
  monthEnd,
  monthKnown,
  overviewOn,
  seriesOn,
  STATIC_SERIES_FIELDS
} from './gate';
import { changeSentence, headlineSentence } from './sentence';
import { carryHref, readAsOf, stepMonth, withAsOf } from './url';

const BUNDLE = resolve(process.env.TT_BUNDLE ?? '../web-data-fixtures');
const GOLDEN = resolve(process.env.TT_GOLDEN ?? 'fixtures/timetravel_golden.json');
const json = <T>(p: string) => JSON.parse(readFileSync(resolve(BUNDLE, p), 'utf-8')) as T;

const overview = json<Overview>('overview.json');
const branches = Object.fromEntries(['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9'].map((c) => [c, json<Branch & { history: never[] }>(`branch/${c}.json`)]));
const series: Record<string, SeriesDoc> = Object.fromEntries(
  readdirSync(resolve(BUNDLE, 'series'))
    .filter((f) => f.endsWith('.json') && f !== 'index.json')
    .map((f) => [f.replace(/\.json$/, ''), json<SeriesDoc>(`series/${f}`)])
);

interface Golden {
  probes: {
    day: string;
    record: null | { month: string; kind: string; sentence: string; change_sentence: string; n_months: number; history: Record<string, number>; measure_history: Record<string, number> };
    series: Record<string, { versions: null | { n: number; n_periods: number; n_dates: number; n_revised_periods: number; first_known: string; last_known: string; sha: string }; as_of?: { n: number; sha: string } }>;
  }[];
}
const golden = JSON.parse(readFileSync(GOLDEN, 'utf-8')) as Golden;

// the same canonical text as gen_timetravel_golden.py (num: toExponential(5) with an integer exponent)
const num = (x: number) => {
  const [m, e] = x.toExponential(5).split('e');
  return `${m}e${Number(e)}`;
};
const sha = (lines: string[]) => createHash('sha256').update(lines.join('\n'), 'utf-8').digest('hex').slice(0, 20);
const versionsSha = (v: Versions) => sha(v.p.map((p, i) => `${v.periods[p]}|${v.dates[v.d[i]]}|${num(v.v[i])}`));

describe('golden: the cut of today’s bundle = Python’s replay on the day', () => {
  it('covers every series of the bundle and the record boundaries', () => {
    expect(golden.probes.length).toBeGreaterThanOrEqual(6);
    for (const p of golden.probes) expect(Object.keys(p.series).sort()).toEqual(Object.keys(series).sort());
    expect(golden.probes.some((p) => p.record === null)).toBe(true); // before the first month end: no record
  });

  for (const p of golden.probes) {
    it(`versions known on ${p.day} = vintages.encode(rows, ${p.day}), and asOf = observations.as_of`, () => {
      for (const [key, g] of Object.entries(p.series)) {
        const cut = cutVersions(series[key].versions, p.day);
        if (g.versions === null) {
          expect(cut, key).toBeNull();
        } else {
          expect(cut, key).not.toBeNull();
          const c = cut!;
          expect(
            { n: c.n_versions, n_periods: c.periods.length, n_dates: c.dates.length, n_revised_periods: c.n_revised_periods, first_known: c.first_known, last_known: c.last_known, sha: versionsSha(c) },
            key
          ).toEqual(g.versions);
        }
        if (g.as_of) {
          const rows = [...asOf(cut, p.day)].sort((a, b) => (a[0] < b[0] ? -1 : 1)).map(([per, v]) => `${per}|${num(v)}`);
          expect({ n: rows.length, sha: sha(rows) }, `${key} as_of`).toEqual(g.as_of);
        }
      }
    });

    it(`the record shown on ${p.day} = site.data.Record(today=${p.day})`, () => {
      const o = overviewOn(overview, p.day);
      if (p.record === null) {
        expect(o.month).toBeNull();
        expect(o.stripes.months).toEqual([]);
        return;
      }
      const r = p.record;
      expect([o.month, o.kind, o.stripes.months.length]).toEqual([r.month, r.kind, r.n_months]);
      expect(headlineSentence(o)).toBe(r.sentence);
      expect(changeSentence(o)).toBe(r.change_sentence);
      for (const [code, n] of Object.entries(r.history)) {
        const b = branchOn(branches[code], p.day);
        expect(b.history.length, code).toBe(n);
        if (n) expect(b.month, code).toBe(r.month);
      }
      for (const [key, n] of Object.entries(r.measure_history)) {
        const s = seriesOn(series[key], p.day, overview.record);
        expect(s.history?.months.length ?? 0, key).toBe(n);
      }
    });
  }
});

// every 9th day from 2009 to 2027 (crosses every month end, version day and the build day)
const DAYS: string[] = [];
const SLOW = { timeout: 180_000 }; // the real bundle has ~400 series
for (let t = Date.UTC(2009, 0, 1); t <= Date.UTC(2027, 0, 1); t += 9 * 86_400_000) DAYS.push(new Date(t).toISOString().slice(0, 10));

describe('invariants on every 9th day', () => {
  it('versions: nothing after the day, same replay as the full versions, frozen for later days, monotone', SLOW, () => {
    for (const doc of Object.values(series)) {
      const v = doc.versions;
      let prevN = 0;
      for (const day of DAYS) {
        const c = cutVersions(v, day);
        const n = c?.n_versions ?? 0;
        expect(n).toBeGreaterThanOrEqual(prevN);
        prevN = n;
        if (!c) {
          expect(asOf(v, day).size).toBe(0);
          continue;
        }
        expect(c.dates.every((d) => d <= day)).toBe(true);
        expect(c.last_known <= day).toBe(true);
        expect([...asOf(c, day)]).toEqual([...asOf(v, day)]);
        // the cut holds nothing that a later day could reveal
        expect([...asOf(c, '2099-12-31')]).toEqual([...asOf(v, day)]);
      }
    }
  });

  it('records: every month shown was known on the day; the latest one is the last month end before it', () => {
    for (const day of DAYS) {
      const o = overviewOn(overview, day);
      expect(o.stripes.known.every((k) => k <= day)).toBe(true);
      expect(leaks(o, day)).toEqual([]);
      if (o.month) {
        expect(monthKnown(o.month, overview.record) <= day).toBe(true);
        const next = overview.stripes.months[overview.stripes.months.indexOf(o.month) + 1];
        if (next) expect(monthKnown(next, overview.record) > day).toBe(true);
        const lme = lastMonthEnd(day);
        if (overview.stripes.months.includes(lme) && monthKnown(lme, overview.record) <= day) expect(o.month).toBe(lme);
      }
      for (const b of Object.values(branches)) {
        const x = branchOn(b, day);
        expect(x.history.every((h) => h.known <= day)).toBe(true);
        expect(x.month).toBe(o.month === null ? null : x.history.at(-1)?.month ?? null);
      }
    }
  });

  it('series: levels, measures and record months are all known on the day; no field of today is copied', SLOW, () => {
    for (const doc of Object.values(series)) {
      for (const day of DAYS.filter((_, i) => i % 4 === 0)) {
        const s = seriesOn(doc, day, overview.record);
        expect(leaks(s, day)).toEqual([]);
        expect(s.levels.every((l) => l.known <= day)).toBe(true);
        if (s.measure) {
          expect(s.measure.known <= day).toBe(true);
          if (s.measure.known_from) expect(s.measure.known_from <= day).toBe(true);
        }
        expect(Object.keys(s.meta).every((k) => (STATIC_SERIES_FIELDS as readonly string[]).includes(k))).toBe(true);
        for (const today of ['measure', 'measure_path', 'levels', 'rows', 'counted', 'in_record', 'record_branch', 'measure_as_of']) expect(s.meta).not.toHaveProperty(today);
      }
    }
  });
});

describe('the guard', () => {
  const someDoc = Object.values(series).find((d) => d.measure_history && d.measure_history.months.length > 2)!;
  it('a record measure known after its month end (a broken bundle) throws instead of rendering', () => {
    const mh = someDoc.measure_history!;
    const bad = { ...someDoc, measure_history: { ...mh, known_from: mh.known_from!.map((k, i) => (i === 0 ? '2099-01-01' : k)) } } as SeriesDoc;
    expect(() => seriesOn(bad, monthEnd(mh.months[1]), overview.record)).toThrow(LeakError);
  });
  it('leaks() finds a known day after the day at any depth, and ignores periods', () => {
    expect(leaks({ a: [{ known_from: '2024-02-01' }], periods: ['2030-01'] }, '2024-01-31')).toEqual(['$.a[0].known_from = 2024-02-01']);
    expect(leaks({ versions: { dates: ['2024-01-31'] } }, '2024-01-31')).toEqual([]);
  });
  it('a live snapshot dated after its month end is shown only from its date', () => {
    const rec = { month: '2026-10', date: '2026-11-02', status: 'live' as const };
    expect(monthKnown('2026-10', rec)).toBe('2026-11-02');
    expect(monthKnown('2026-09', rec)).toBe('2026-09-30');
  });
});

describe('URL state', () => {
  it('reads, writes and keeps the other keys', () => {
    expect(readAsOf('#fonster=5&as_of=2024-06-30')).toBe('2024-06-30');
    expect(readAsOf('#as_of=2024-02-30')).toBeNull();
    expect(withAsOf('#fonster=5&rev=1', '2024-06-30')).toBe('#fonster=5&rev=1&as_of=2024-06-30');
    expect(withAsOf('#as_of=2024-06-30', null)).toBe('');
    expect(withAsOf('#s-x&as_of=2024-06-30', '2023-01-31')).toBe('#s-x=&as_of=2023-01-31');
  });
  it('steps month ends', () => {
    expect(stepMonth('2024-06-15', -1)).toBe('2024-05-31');
    expect(stepMonth('2024-06-30', 1)).toBe('2024-07-31');
    expect(stepMonth('2024-01-31', 1)).toBe('2024-02-29');
    expect(lastMonthEnd('2024-03-15')).toBe('2024-02');
    expect(lastMonthEnd('2024-03-31')).toBe('2024-03');
  });
  it('carries as_of to internal links only', () => {
    const here = 'http://x.test/next/gren/G6/#as_of=2024-06-30';
    expect(carryHref('/next/serie/a/', here, '/next', '2024-06-30')).toBe('http://x.test/next/serie/a/#as_of=2024-06-30');
    expect(carryHref('/next/serie/a/#rev=1', here, '/next', '2024-06-30')).toBe('http://x.test/next/serie/a/#rev=1&as_of=2024-06-30');
    expect(carryHref('/next/serie/a/#as_of=2020-01-31', here, '/next', null)).toBe('http://x.test/next/serie/a/');
    expect(carryHref('https://github.com/x', here, '/next', '2024-06-30')).toBeNull();
    expect(carryHref('/old/', here, '/next', '2024-06-30')).toBeNull();
    expect(carryHref('mailto:a@b', here, '/next', '2024-06-30')).toBeNull();
  });
});
