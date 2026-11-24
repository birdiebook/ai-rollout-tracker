// Permalink state, CSV, periods, the inlined page data, and the instrument rendered for every fixture series.
import { readFileSync, readdirSync } from 'node:fs';
import { resolve as resolvePath } from 'node:path';
import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import SeriesInstrument from './SeriesInstrument.svelte';
import { csvCell, levelsCsv, versionsCsv } from './csv';
import { defaultLog, logTicks } from './chart';
import { pageData } from './page';
import { parseState, serializeState, DEFAULT_STATE } from './permalink';
import { periodSpan, periodText, periodTime, windowStart, windowsFor } from './period';
import { digitsFor, logTickNum, num, plural, snum } from './text';
import { asOf } from './versions';
import type { SeriesDoc } from './types';

const FIX = resolvePath('../web-data-fixtures/series');
const index = JSON.parse(readFileSync(resolvePath(FIX, 'index.json'), 'utf-8'));
const docs = readdirSync(FIX)
  .filter((f) => f.endsWith('.json') && f !== 'index.json')
  .map((f) => JSON.parse(readFileSync(resolvePath(FIX, f), 'utf-8')) as SeriesDoc);
const doc = (k: string) => docs.find((d) => d.key === k)!;

describe('permalink', () => {
  it('defaults give an empty hash and parse back', () => {
    expect(serializeState(DEFAULT_STATE)).toBe('');
    expect(parseState('')).toEqual(DEFAULT_STATE);
  });
  it('round-trips a view, in a fixed key order', () => {
    const st = { ...DEFAULT_STATE, fonster: '5' as const, skala: 'log' as const, rev: true, as_of: '2023-06-30' };
    const h = serializeState(st);
    expect(h).toBe('#fonster=5&skala=log&as_of=2023-06-30');
    expect(parseState(h)).toEqual(st);
  });
  it('as_of opens the revision view; rev=1 alone too', () => {
    expect(parseState('#as_of=2024-01-31').rev).toBe(true);
    expect(serializeState(parseState('#rev=1'))).toBe('#rev=1');
  });
  it('series-specific defaults are left out of the URL', () => {
    const d = { skala: 'log' as const };
    expect(serializeState({ ...DEFAULT_STATE, skala: 'log' }, d)).toBe('');
    expect(serializeState({ ...DEFAULT_STATE, skala: 'lin' }, d)).toBe('#skala=lin');
    expect(parseState('', d).skala).toBe('log');
  });
  it('invalid values fall back; unknown keys are kept for W9/W12', () => {
    const st = parseState('#fonster=7&skala=x&as_of=2023-02-31x&modell=b3');
    expect(st.fonster).toBe('alla');
    expect(st.skala).toBe('lin');
    expect(st.as_of).toBeNull();
    expect(serializeState(st)).toBe('#modell=b3');
  });
});

describe('periods of every frequency', () => {
  it('spans and midpoints', () => {
    expect(periodSpan('2026')).toEqual([Date.UTC(2026, 0, 1), Date.UTC(2026, 11, 31)]);
    expect(periodSpan('2026Q3')).toEqual([Date.UTC(2026, 6, 1), Date.UTC(2026, 8, 30)]);
    expect(periodSpan('2026-02')).toEqual([Date.UTC(2026, 1, 1), Date.UTC(2026, 1, 28)]);
    expect(periodSpan('2026-09-14')).toEqual([Date.UTC(2026, 8, 14), Date.UTC(2026, 8, 14)]);
    expect(periodTime('2026-09-08/2026-09-14')).toBe(Date.UTC(2026, 8, 11));
    expect(periodSpan('nonsense')).toBeNull();
  });
  it('periods sort as text and as time in the same order', () => {
    for (const d of docs) {
      const ps = d.levels?.periods ?? [];
      const ts = ps.map(periodTime);
      expect(ts.every((t, i) => i === 0 || t > ts[i - 1]), d.key).toBe(true);
    }
  });
  it('labels', () => {
    expect(periodText('2026-11-09/2026-11-15')).toBe('9–15 nov 2026');
    expect(periodText('2025-12-29/2026-01-04')).toBe('29 dec 2025–4 jan 2026');
    expect(periodText('2026-10-14')).toBe('14 okt 2026');
    expect(periodText('2026Q3')).toBe('kv. 3 2026');
    expect(periodText('2026')).toBe('2026');
    expect(periodText('2026-10', true)).toBe('oktober 2026');
  });
  it('windows', () => {
    expect(windowStart('alla', Date.UTC(2026, 0, 1))).toBe(-Infinity);
    expect(windowStart('5', Date.UTC(2026, 5, 15))).toBe(Date.UTC(2021, 5, 15));
    expect(windowsFor(3)).toEqual(['alla', '2']);
    expect(windowsFor(0)).toEqual(['alla']);
  });
});

describe('numbers', () => {
  it('precision follows the scale', () => {
    expect(digitsFor(30544)).toBe(0);
    expect(digitsFor(198.73)).toBe(1);
    expect(digitsFor(3.0789)).toBe(2);
    expect(digitsFor(0.057)).toBe(3);
    expect(num(30544).replace(/\s/g, ' ')).toBe('30 544');
    expect(snum(-0.55698)).toBe('−0,56');
  });
  it('large magnitudes are written short, log ticks without trailing decimals', () => {
    const n = (s: string) => s.replace(/\s/g, ' ');
    expect(n(num(206379000000))).toBe('206,4 md');
    expect(n(num(2_500_000))).toBe('2,50 mn');
    expect(n(logTickNum(1000))).toBe('1 000');
    expect(logTickNum(0.01)).toBe('0,01');
    expect(n(logTickNum(2e9))).toBe('2 md');
    expect(plural(1, 'rad', 'rader')).toBe('1 rad');
    expect(plural(3, 'rad', 'rader')).toBe('3 rader');
  });
  it('log ticks and the default scale', () => {
    expect(logTicks(30, 700)).toEqual([50, 100, 200, 500]);
    expect(logTicks(3, 700)).toEqual([10, 100]);
    expect(defaultLog([1, 10], 'log')).toBe(true);
    expect(defaultLog([1, 2], 'log')).toBe(false);
    expect(defaultLog([1, 10], 'share')).toBe(false);
    expect(defaultLog([1, 10], 'halving')).toBe(true);
    expect(defaultLog([-1, 10], 'log')).toBe(false);
  });
});

describe('csv', () => {
  const s = doc('us_ip_semis_m');
  it('quotes only when needed', () => {
    expect(csvCell('a,b')).toBe('"a,b"');
    expect(csvCell('say "x"')).toBe('"say ""x"""');
    expect(csvCell(null)).toBe('');
    expect(csvCell(1.5)).toBe('1.5');
  });
  it('levels: attribution header, one row per level, machine-readable numbers', () => {
    const csv = levelsCsv(s, s.levels, 'https://example.invalid/serie/us_ip_semis_m/#fonster=5');
    const lines = csv.trimEnd().split('\r\n');
    expect(lines).toContain(`# attribution: ${s.license.attribution}`);
    expect(lines.some((l) => l.startsWith('# permalänk: https://example.invalid'))).toBe(true);
    const body = lines.filter((l) => !l.startsWith('#'));
    expect(body[0]).toBe('period,value');
    expect(body.length - 1).toBe(s.levels!.periods.length);
    expect(body[1]).toBe(`${s.levels!.periods[0]},${s.levels!.values[0]}`);
  });
  it('versions: every version in contract order; replaying the CSV gives asOf', () => {
    const v = s.versions!;
    const body = versionsCsv(s, v).trimEnd().split('\r\n').filter((l) => !l.startsWith('#'));
    expect(body[0]).toBe('period,known_from,value');
    expect(body.length - 1).toBe(v.n_versions);
    const day = v.dates[Math.floor(v.dates.length / 2)];
    const rep = new Map<string, number>();
    for (const l of body.slice(1)) {
      const [p, k, val] = l.split(',');
      if (k <= day) rep.set(p, Number(val));
    }
    expect([...rep].sort()).toEqual([...asOf(v, day)].sort());
  });
});

describe('page data (what the prerendered page inlines)', () => {
  for (const d of docs) {
    it(`${d.key}: no versions inlined, summary consistent`, () => {
      const pd = pageData(d, index.series);
      expect(pd.series.versions).toBeNull();
      expect(JSON.stringify(pd)).not.toContain('"versions-v1"');
      if (d.versions) {
        expect(pd.versions?.n_versions).toBe(d.versions.n_versions);
        expect(pd.versions?.n_revised_periods).toBe(d.versions.n_revised_periods);
        if (d.versions.n_revised_periods > 0) {
          const last = asOf(d.versions, d.versions.last_known);
          expect(pd.revision!.periods.map((p) => last.get(p))).toEqual(pd.revision!.latest);
        } else expect(pd.revision).toBeNull();
      }
      expect(pd.siblings.every((x) => x.key !== d.key)).toBe(true);
    });
  }
  it('stays small: inlined data well under the 100 kB gzip page budget even for daily series', () => {
    const pd = pageData(doc('ai_postings_share_us_d'), index.series);
    expect(JSON.stringify(pd).length).toBeLessThan(150_000);
  });
});

describe('SeriesInstrument renders every fixture series', () => {
  for (const d of docs) {
    it(`${d.key} (${d.freq})`, () => {
      const { container } = render(SeriesInstrument, { data: pageData(d, index.series), recordStatus: 'live' });
      expect(container.querySelector('h1')?.textContent).toBe(d.label);
      // attribution next to the charts and in the facts
      expect(container.textContent).toContain(d.license.attribution);
      if ((d.levels?.periods.length ?? 0) > 0) expect(container.querySelector('#level svg[role="img"]')).not.toBeNull();
      if (d.measure?.direction !== null && d.measure?.direction !== undefined && d.measure.change_in_pace !== null)
        expect(container.textContent).toMatch(/ökar takten|oförändrad takt|minskar takten/);
      // no alarm colours anywhere: colour is direction only
      expect(container.innerHTML).not.toMatch(/red|green|#f00|#0f0/i);
    });
  }
  it('a revised series shows how many periods changed without fetching', () => {
    const { container } = render(SeriesInstrument, { data: pageData(doc('us_ip_semis_m'), index.series) });
    expect(container.textContent).toMatch(/201 av 202 perioder har reviderats/);
    expect(container.querySelector('#rev-size svg')).not.toBeNull();
    expect(container.querySelector('#rev-explorer')?.hasAttribute('hidden')).toBe(true);
  });
  it('an unrevised series says so', () => {
    const { container } = render(SeriesInstrument, { data: pageData(doc('capex_hyp4'), index.series) });
    expect(container.textContent).toMatch(/Inga revideringar/);
    expect(container.querySelector('#rev-size')).toBeNull();
  });
  it('a series without levels, measure or versions still renders', () => {
    const bare = { ...doc('capex_hyp4'), levels: null, measure: null, measure_path: null, measure_history: null, versions: null } as SeriesDoc;
    const { container } = render(SeriesInstrument, { data: pageData(bare, index.series) });
    expect(container.textContent).toMatch(/inga publicerade värden/);
    expect(container.textContent).toMatch(/inga versioner/);
  });
});
