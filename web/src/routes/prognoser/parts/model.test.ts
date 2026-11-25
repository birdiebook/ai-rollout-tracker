import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { fsBundle } from '$lib/server/bundle';
import type { Nowcast } from '$lib/data';
import {
  MIN_LIVE_FOR_CALIBRATION,
  calibrationNote,
  committedBefore,
  daysUntil,
  dotDomain,
  hitCounts,
  inInterval,
  liveRows,
  overviewSentence,
  periodShort,
  pitBins,
  proofLinks,
  roleOf,
  roles,
  slugOf,
  storedQuantiles
} from './model';

const base: Nowcast = {
  id: 'n2',
  label: 'N2',
  title: 'TSMC',
  champion: 'B3',
  next_origin: '2026-12-05',
  next_period: '2026-11',
  shadows: ['B0', 'B1', 'V1', 'B2', 'DF'],
  variants: [
    { id: 'B0', text: 'slumpvandring' },
    { id: 'B1', text: 'säsongsnaiv tillväxt' },
    { id: 'B2', text: 'TSMC:s kvartalsguidance utslagen per månad' },
    { id: 'B3', text: 'B2 korrigerad för systematisk avvikelse mot guidance' },
    { id: 'DF', text: 'B2 + OLS på faktormodellens förändring (C3, skugga)' }
  ]
};

describe('roles', () => {
  it('N2: B3 is the main model, B1 the baseline, B2 (raw guidance) the guidance, DF a shadow', () => {
    const r = roles(base);
    expect(r).toMatchObject({ champion: 'B3', baseline: 'B1', guidance: 'B2' });
    expect(roleOf(r, 'DF')).toBe('shadow');
    expect(roleOf(r, 'B0')).toBe('shadow');
  });
  it('a B1 champion is compared with B0', () => {
    const r = roles({ ...base, champion: 'B1', variants: base.variants!.filter((v) => v.id !== 'B3') });
    expect(r.baseline).toBe('B0');
    expect(r.guidance).toBe('B2');
  });
  it('no guidance variant -> null', () => {
    expect(roles({ ...base, champion: 'B1', variants: [{ id: 'B0', text: 'x' }, { id: 'B1', text: 'y' }] }).guidance).toBeNull();
  });
});

describe('live rows', () => {
  const nc: Nowcast = {
    ...base,
    forecasts: [
      { period: '2026-10', file: 'forecasts/n2/2026-10.json', value: 100, champion: 'B3', origin: '2026-11-05', intervals: { '50': [95, 105], '80': [90, 110], '95': [85, 115] } },
      { period: '2026-09', file: 'forecasts/n2/2026-09.json', value: 100, champion: 'B3', origin: '2026-10-05', intervals: { '50': [95, 105], '80': [90, 110], '95': [85, 115] } }
    ],
    scorecard: [
      { period: '2026-09', status: 'utfall', outcome: 108, err_champion: -7.7, hit_50_champion: null, hit_80_champion: null, hit_95_champion: null, interval_50: [95, 105], interval_80: [90, 110], interval_95: [85, 115], pit_champion: 0.82 },
      { period: '2026-10', status: 'väntar', outcome: null }
    ]
  };
  const rows = liveRows(nc);
  it('are sorted oldest first and joined with the scorecard', () => {
    expect(rows.map((r) => r.period)).toEqual(['2026-09', '2026-10']);
    expect(rows[0]).toMatchObject({ scored: true, outcome: 108, err: -7.7, pit: 0.82, slug: '2026-09' });
    expect(rows[1]).toMatchObject({ scored: false, outcome: null, err: null });
  });
  it('derive hits from the stored interval when the scorecard has none', () => {
    expect(rows[0].inside).toEqual({ '50': false, '80': true, '95': true });
    expect(hitCounts(rows)['80']).toEqual({ k: 1, n: 1 });
    expect(hitCounts(rows)['50']).toEqual({ k: 0, n: 1 });
  });
  it('an outcome known at the origin is shown but not scored', () => {
    const r = liveRows({ ...nc, scorecard: [{ period: '2026-09', status: 'utfall känt vid origin, räknas inte', outcome: 108 }] });
    expect(r[0]).toMatchObject({ scored: false, outcome: 108 });
    expect(r[0].inside).toEqual({});
  });
  it('no forecasts -> no rows', () => {
    expect(liveRows(base)).toEqual([]);
  });
});

describe('helpers', () => {
  it('stored quantiles are the seven interval ends around the median', () => {
    expect(storedQuantiles(100, { '50': [95, 105], '80': [90, 110], '95': [85, 115] })).toEqual([
      [0.025, 85], [0.1, 90], [0.25, 95], [0.5, 100], [0.75, 105], [0.9, 110], [0.975, 115]
    ]);
    expect(storedQuantiles(100, { '80': [null, 110] })).toEqual([[0.5, 100], [0.9, 110]]);
  });
  it('a far outcome is off scale, a near one widens the domain', () => {
    const q = storedQuantiles(100, { '95': [85, 115] });
    expect(dotDomain(q, 300).offScale).toBe(1);
    expect(dotDomain(q, 10).offScale).toBe(-1);
    const near = dotDomain(q, 125);
    expect(near.offScale).toBe(0);
    expect(near.domain[1]).toBeGreaterThan(125);
  });
  it('slugs are safe URL segments', () => {
    expect(slugOf({ file: 'forecasts/n5/2026-09-28/2026-10-04.json', period: 'x' })).toBe('2026-10-04');
    expect(slugOf({ file: 'forecasts/n1/2026Q4.json', period: '2026Q4' })).toBe('2026Q4');
    expect(slugOf({ file: '', period: '2026-09-28/2026-10-04' })).toBe('2026-09-28_2026-10-04');
  });
  it('proof links only for github.com, pinned to a real sha', () => {
    const p = proofLinks('https://github.com/o/r', 'a233b1f', 'forecasts/n2/2026-11.json');
    expect(p).toEqual({ history: 'https://github.com/o/r/commits/main/forecasts/n2/2026-11.json', file: 'https://github.com/o/r/blob/a233b1f/forecasts/n2/2026-11.json', ref: 'a233b1f', commit: null });
    expect(proofLinks('https://github.com/o/r', 'a233b1f+dirty', 'f.json')?.ref).toBe('main');
    expect(proofLinks('https://example.com/o/r', 'abc1234', 'f.json')).toBeNull();
  });
  it('RW1-X 4a: the proof links the exact commit that added the file, and only a well-formed one', () => {
    const c = { sha: 'a'.repeat(40), date: '2026-10-05T06:41:12Z' };
    const p = proofLinks('https://github.com/o/r', 'b233b1f', 'forecasts/n2/2026-09.json', c)!;
    expect(p.commit).toBe(`https://github.com/o/r/commit/${'a'.repeat(40)}`);
    expect(p.file).toBe(`https://github.com/o/r/blob/${'a'.repeat(40)}/forecasts/n2/2026-09.json`);
    expect(proofLinks('https://github.com/o/r', 'b233b1f', 'f.json', { sha: 'abc', date: '2026-10-05' })?.commit).toBeNull();
    expect(committedBefore(c, '2026-10-14')).toBe(true);
    expect(committedBefore(c, '2026-10-05')).toBe(false); // the same day as the outcome is not before it
    expect(committedBefore(c, null)).toBe(true);
    expect(committedBefore(null, null)).toBe(false);
  });
  it('the calibration note is honest about small n', () => {
    expect(calibrationNote(0)).toMatch(/först efter cirka 12/);
    expect(calibrationNote(3)).toMatch(/3 av cirka 12.*slump/);
    expect(calibrationNote(MIN_LIVE_FOR_CALIBRATION)).not.toMatch(/för få/i);
  });
  it('PIT bins, intervals, days and period labels', () => {
    expect(pitBins([0, 0.05, 0.5, 0.999, 1])).toEqual([2, 0, 0, 0, 0, 1, 0, 0, 0, 2]);
    expect(inInterval(5, [1, 4])).toBe(false);
    expect(inInterval(null, [1, 4])).toBeNull();
    expect(daysUntil('2026-11-24', '2026-12-05')).toBe(11);
    expect(periodShort('2026Q4')).toBe('kv. 4 2026');
    expect(periodShort('2026-10-26/2026-11-01')).toBe('v. t.o.m. 1 nov 2026');
  });
  it('the overview sentence counts and names the next forecast', () => {
    const cal = [
      { id: 'n1', label: 'N1', title: '', champion: 'B1', next_origin: '2027-01-20', next_period: '2026Q4', n_live: 0 },
      { id: 'n2', label: 'N2', title: '', champion: 'B3', next_origin: '2026-12-05', next_period: '2026-11', n_live: 0 }
    ];
    expect(overviewSentence(cal, 0, 0, '2026-11-24')).toBe('2 prognoser följs. Ingen skarp prognos är lämnad ännu. Nästa: N2 den 5 dec 2026 för november 2026.');
    expect(overviewSentence(cal, 3, 1, '2026-11-24')).toContain('3 skarpa prognoser är lämnade, en med utfall.');
  });
});

// Every fixture set: the pages' derivations hold for each nowcast and for D2 (the horizons loader).
const dirs = [resolve('../web-data-fixtures'), resolve('fixtures/provisional')].filter((d) => existsSync(resolve(d, 'nowcast/n1.json')));
describe.each(dirs)('nowcast fixtures in %s', (dir) => {
  const b = fsBundle(dir);
  it('every nowcast yields roles and live rows with slugs that match the forecast files', async () => {
    for (const c of (await b.overview()).calendar.filter((x) => x.id !== 'd2')) {
      const nc = await b.nowcast(c.id);
      const r = roles(nc);
      expect(r.champion).toBe(nc.champion);
      for (const row of liveRows(nc)) expect(row.file.endsWith(`${row.slug}.json`) || row.slug.includes('_')).toBe(true);
    }
  });
  it('RW1-X 4a: every live file with a commit was committed before its outcome became known', async () => {
    let scored = 0;
    for (const c of (await b.overview()).calendar.filter((x) => x.id !== 'd2')) {
      const nc = await b.nowcast(c.id);
      for (const row of liveRows(nc)) {
        if (!row.commit) {
          expect(row.verified, row.file).toBe(false); // never shown as live without its commit
          continue;
        }
        if (row.outcomeKnown) {
          expect(row.commit.date.slice(0, 10) < row.outcomeKnown.slice(0, 10), `${row.file}: ${row.commit.date} vs ${row.outcomeKnown}`).toBe(true);
          if (row.scored) scored++;
        }
        expect(row.verified, row.file).toBe(true);
      }
    }
    if (dir.endsWith('web-data-fixtures')) expect(scored).toBeGreaterThan(0);
  });
  it('D2 loads through horizons() and is not a nowcast() document', async () => {
    if (!existsSync(resolve(dir, 'nowcast/d2.json'))) return;
    const d2 = await b.horizons();
    expect(Array.isArray(d2.targets)).toBe(true);
    expect(d2.first_live).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});
