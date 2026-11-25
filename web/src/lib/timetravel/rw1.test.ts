// R-W1 (independent review): adversarial tests that try to break the time-travel leakage boundary (gate.ts) and
// the URL handling around it. Synthetic inputs only, so the edge cases are explicit. See docs/granskning/rw1_webb.md.
import { describe, expect, it } from 'vitest';
import type { Versions } from '$lib/series/types';
import { asOf, backfillUntil, toDay } from '$lib/series/versions';
import { branchOn, cutHistory, cutVersions, lastMonthEnd, leaks, monthEnd, monthKnown, overviewOn, seriesOn } from './gate';
import { carryHref, readAsOf } from './url';
import { hidesBeforePaint } from './prepaint';

/** versions-v1 from (period, known day, value) rows; sorted like vintages.encode (date, period). */
function enc(rows: [string, string, number][], collapsed: string | null = null): Versions {
  const sorted = [...rows].sort((a, b) => (a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
  const periods = [...new Set(sorted.map((r) => r[0]))].sort();
  const dates = [...new Set(sorted.map((r) => r[1]))].sort();
  const p = sorted.map((r) => periods.indexOf(r[0]));
  const per = new Map<number, number>();
  for (const x of p) per.set(x, (per.get(x) ?? 0) + 1);
  return {
    encoding: 'versions-v1',
    freq: 'M',
    native_freq: 'M',
    aggregation: null,
    periods,
    dates,
    p,
    d: sorted.map((r) => dates.indexOf(r[1])),
    v: sorted.map((r) => r[2]),
    n_versions: sorted.length,
    n_revised_periods: [...per.values()].filter((k) => k > 1).length,
    first_known: dates[0],
    last_known: dates[dates.length - 1],
    collapsed_before: collapsed
  };
}

// a monthly series revised on the month end, plus a later release
const V = enc([
  ['2024-04', '2024-05-15', 100],
  ['2024-05', '2024-06-14', 101],
  ['2024-05', '2024-06-30', 102], // revision published ON the month end
  ['2024-06', '2024-07-15', 103],
  ['2024-06', '2024-07-31', 104]
]);

describe('same day, month end, the day before', () => {
  it('a version dated D is known on D and not on D-1 (as observations.as_of: known_from <= D)', () => {
    expect(asOf(cutVersions(V, '2024-06-14'), '2024-06-14').get('2024-05')).toBe(101);
    expect(cutVersions(V, '2024-06-13')!.periods).toEqual(['2024-04']);
  });
  it('the month-end revision is in the cut on the month end, the release after it is not', () => {
    const c = cutVersions(V, '2024-06-30')!;
    expect(asOf(c, '2024-06-30').get('2024-05')).toBe(102);
    expect(c.periods).toEqual(['2024-04', '2024-05']);
    expect(c.last_known).toBe('2024-06-30');
    expect(leaks(c, '2024-06-30')).toEqual([]);
    expect(cutVersions(V, '2024-06-29')!.v).toEqual([100, 101]);
  });
  it('the cut never holds a period, date or value that only later rows had', () => {
    for (const day of ['2024-05-14', '2024-05-15', '2024-06-29', '2024-06-30', '2024-07-01', '2024-07-30', '2024-07-31']) {
      const c = cutVersions(V, day);
      if (!c) continue;
      expect(c.dates.every((d) => d <= day)).toBe(true);
      expect(c.n_versions).toBe(c.v.length);
      expect(leaks(c, day)).toEqual([]);
      // nothing in the cut changes when later rows are dropped from the source
      const prefix = enc(V.p.map((pi, i) => [V.periods[pi], V.dates[V.d[i]], V.v[i]] as [string, string, number]).filter((r) => r[1] <= day));
      expect(c).toEqual(prefix);
    }
  });
  it('a record for a month is known from its month end, never before', () => {
    expect(lastMonthEnd('2024-06-30')).toBe('2024-06');
    expect(lastMonthEnd('2024-06-29')).toBe('2024-05');
    expect(lastMonthEnd('2024-03-01')).toBe('2024-02');
    expect(monthEnd('2024-02')).toBe('2024-02-29');
    // a live snapshot dated after its month end moves the record later, never earlier
    expect(monthKnown('2024-06', { month: '2024-06', date: '2024-07-02', status: 'live' })).toBe('2024-07-02');
    expect(monthKnown('2024-06', { month: '2024-06', date: '2024-06-15', status: 'live' })).toBe('2024-06-30');
  });
});

describe('time zones: the day is the UTC day of known_from', () => {
  it('a Date is cut at its UTC day, a day string with a time or offset at its written day', () => {
    // 23:30 at UTC-2 on 30 June is 1 July in UTC: the UTC day, as every known_from in the table
    expect(toDay(new Date('2024-06-30T23:30:00-02:00'))).toBe('2024-07-01');
    // a string is cut at its written day (never later than the writer meant)
    expect(toDay('2024-06-30T23:30:00-02:00')).toBe('2024-06-30');
    expect(() => toDay('30/06/2024')).toThrow(RangeError);
  });
  it('the URL only takes real calendar days', () => {
    expect(readAsOf('#as_of=2024-02-30')).toBeNull();
    expect(readAsOf('#as_of=2024-02-29')).toBe('2024-02-29');
    expect(readAsOf('#as_of=2024-6-30')).toBeNull();
    expect(readAsOf('#as_of=2024-06-30T00:00')).toBeNull();
  });
});

describe('collapsed versions (size guard) and the backfill boundary', () => {
  // the size guard: everything known before the cutoff is dated AT the cutoff
  const C = enc(
    [
      ['2020-01', '2022-01-01', 1],
      ['2020-02', '2022-01-01', 2],
      ['2021-12', '2022-01-01', 3],
      ['2022-01', '2022-02-15', 4]
    ],
    '2022-01-01'
  );
  it('before the cutoff the series shows nothing, from the cutoff it shows the collapsed version', () => {
    expect(cutVersions(C, '2021-12-31')).toBeNull();
    const s = seriesOn({ key: 'x', label: 'x', versions: C } as never, '2021-06-30');
    expect(s.empty).toBe(true);
    expect(s.levels).toEqual([]);
    const at = cutVersions(C, '2022-01-01')!;
    expect(at.collapsed_before).toBe('2022-01-01');
    expect(at.periods).toEqual(['2020-01', '2020-02', '2021-12']);
  });
  it('a collapse cutoff after the day is never copied into the cut', () => {
    const late = { ...C, collapsed_before: '2022-02-15' };
    expect(cutVersions(late, '2022-01-31')!.collapsed_before).toBeNull();
  });
  it('the backfill flag is on strictly before the last backfilled day', () => {
    const doc = { key: 'x', label: 'x', versions: V, rows: { counts: {}, backfill_last_known: '2024-06-30' } } as never;
    expect(seriesOn(doc, '2024-06-29').backfilled).toBe(true);
    expect(seriesOn(doc, '2024-06-30').backfilled).toBe(false);
  });
  it('RW1-X 3a: the backfill flag holds until the fetch day, not only until the rule day (us_elec_sales_com_*)', () => {
    // rule days (period end + lag) up to 2013-01-29, but the rows were fetched 2026-11-23 with that day's vintage
    const doc = { key: 'x', label: 'x', versions: V, rows: { counts: {}, backfill_last_known: '2013-01-29', backfill_fetched: '2026-11-23' } } as never;
    for (const d of ['2013-01-28', '2013-01-29', '2020-06-30', '2026-11-22']) expect(seriesOn(doc, d).backfilled, d).toBe(true);
    expect(seriesOn(doc, '2026-11-23').backfilled).toBe(false);
    expect(backfillUntil({ backfill_last_known: '2013-01-29', backfill_fetched: '2026-11-23' })).toBe('2026-11-23');
    // the later of the two days, whichever it is; a bundle before 1.2.0 has only the rule day
    expect(backfillUntil({ backfill_last_known: '2026-12-31', backfill_fetched: '2026-11-23' })).toBe('2026-12-31');
    expect(backfillUntil({ backfill_last_known: '2013-01-29' })).toBe('2013-01-29');
    expect(backfillUntil({ backfill_last_known: null, backfill_fetched: null })).toBeNull();
    expect(backfillUntil(null)).toBeNull();
  });
});

describe('records: index history and stripes', () => {
  const history = [
    { month: '2024-05', kind: 'rekonstruerad', index: 0.5, state: 'stabil', n_series: 3, n_up: 1, n_neutral: 1, n_down: 1 },
    { month: '2024-06', kind: 'rekonstruerad', index: 0.8, state: 'accelererar', n_series: 3, n_up: 2, n_neutral: 1, n_down: 0 }
  ];
  it('a month-end record appears on its month end and not the day before', () => {
    expect(cutHistory(history, '2024-06-29').map((h) => h.month)).toEqual(['2024-05']);
    expect(cutHistory(history, '2024-06-30').map((h) => h.month)).toEqual(['2024-05', '2024-06']);
  });
  it('branchOn on the day before the month end shows the month before, with nothing from the later month', () => {
    const doc = { code: 'G1', name: 'G1', question: '', record: { month: '2024-06', date: '2024-06-30', status: 'reconstructed' }, history } as never;
    const b = branchOn(doc, '2024-06-29');
    expect(b.month).toBe('2024-05');
    expect(b.index).toBe(0.5);
    const txt = JSON.stringify(b);
    expect(txt).not.toContain('"2024-06"');
    expect(txt).not.toContain('2024-06-30');
    expect(txt).not.toContain('0.8');
  });
  it('overviewOn before the first month end of the history has no record and no stripes', () => {
    const ov = {
      record: { month: '2024-06', date: '2024-06-30', status: 'reconstructed' },
      stripes: { months: ['2024-05', '2024-06'], kind: ['rekonstruerad', 'rekonstruerad'], rows: [{ code: 'G1', name: 'G1', index: [0.5, 0.8], state: ['stabil', 'accelererar'], n_series: [3, 3] }], thresholds: { braking_at_most: 0.33, accelerating_at_least: 0.67 } }
    } as never;
    const o = overviewOn(ov, '2024-05-30');
    expect(o.month).toBeNull();
    expect(o.stripes.months).toEqual([]);
    expect(o.branches).toEqual([]);
  });
});

describe('the guard: any later day anywhere in a time-travel object', () => {
  it('catches a later day in a known-field (as before)', () => {
    expect(leaks({ versions: { dates: ['2030-01-01'] } }, '2024-01-01')).toHaveLength(1);
  });
  it('catches a later day in a field whose name is not on the known-field list (R-W1)', () => {
    expect(leaks({ rows: { backfill_last_known: '2030-01-01' } }, '2024-01-01')).toHaveLength(1);
    expect(leaks({ meta: { updated: '2030-01-01T10:00:00Z' } }, '2024-01-01')).toHaveLength(1);
    expect(leaks({ levels: [{ period: '2030-01-07/2030-01-13', value: 1, known: '2023-12-31' }] }, '2024-01-01')).toHaveLength(1);
  });
  it('lets static text with a date inside it through (licence texts quote the day they were read)', () => {
    expect(leaks({ license: { text: 'PJM, legal page redirects (2026-11-23)' } }, '2024-01-01')).toEqual([]);
  });
});

describe('links and the hash', () => {
  const here = 'https://x.github.io/repo/next/gren/G1/#as_of=2024-06-30';
  const base = '/repo/next';
  it('carries as_of to every page of the site, and only there', () => {
    expect(carryHref('/repo/next/serie/a/', here, base, '2024-06-30')).toBe('https://x.github.io/repo/next/serie/a/#as_of=2024-06-30');
    expect(carryHref('/repo/next', here, base, '2024-06-30')).toBe('https://x.github.io/repo/next#as_of=2024-06-30');
    expect(carryHref('/repo/next-old/', here, base, '2024-06-30')).toBeNull();
    expect(carryHref('/repo/', here, base, '2024-06-30')).toBeNull(); // the old site has no time travel
    expect(carryHref('https://github.com/x/repo', here, base, '2024-06-30')).toBeNull();
    // an as_of already in the target is replaced by the current day, never kept
    expect(carryHref('/repo/next/serie/a/#as_of=2030-01-01', here, base, '2024-06-30')).toBe('https://x.github.io/repo/next/serie/a/#as_of=2024-06-30');
  });
  it('the pre-paint check hides exactly when the time-travel store will travel (same parser)', () => {
    for (const h of ['#as_of=2024-06-30', '#a=1&as_of=2024-06-30', '#as%5Fof=2024-06-30', '#as_of=2024-06-30&as_of=2030-01-01', '#as_of=2024-02-30', '#xas_of=2024-06-30', '#as_of=2024-06-30x', '', '#']) {
      expect(hidesBeforePaint(h), h).toBe(readAsOf(h) !== null);
    }
  });
});
