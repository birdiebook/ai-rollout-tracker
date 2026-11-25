import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import { fsBundle } from '$lib/server/bundle';
import type { Nowcast, Overview } from '$lib/data';
import UnitGlyphs from './UnitGlyphs.svelte';
import {
  calendarDescription,
  calibrationDescription,
  chainSentence,
  countsSentence,
  focusNowcast,
  forecastQuantiles,
  joinSv,
  latestForecast,
  leadRanges,
  moveCounts,
  nowDescription,
  reconDescription,
  sparkViews,
  startData,
  v1Sentence,
  type BranchView,
  type StartData
} from './model';

const fixtures = resolve('../web-data-fixtures');
// A real bundle can be checked too: START_BUNDLE_DIR=/tmp/bundle npm test
const dirs = [fixtures, process.env.START_BUNDLE_DIR].filter((d): d is string => !!d && existsSync(resolve(d, 'manifest.json')));

async function load(dir: string): Promise<StartData> {
  const b = fsBundle(dir);
  const [manifest, overview, flow, seriesIndex] = await Promise.all([b.manifest(), b.overview(), b.flow(), b.seriesIndex()]);
  const nowcasts = await Promise.all(overview.calendar.filter((c) => c.id !== 'd2').map((c) => b.nowcast(c.id)));
  return startData({ manifest, overview, flow, nowcasts, seriesIndex });
}

describe('wording', () => {
  it('joins Swedish lists', () => {
    expect(joinSv([])).toBe('');
    expect(joinSv(['a'])).toBe('a');
    expect(joinSv(['a', 'b'])).toBe('a och b');
    expect(joinSv(['a', 'b', 'c'])).toBe('a, b och c');
  });
  it('compresses runs of three or more leads', () => {
    expect(leadRanges(['L3', 'L4', 'L5', 'L6', 'L8'])).toEqual(['L3–L6', 'L8']);
    expect(leadRanges(['L2', 'L1'])).toEqual(['L1', 'L2']);
    expect(leadRanges(['L9'])).toEqual(['L9']);
  });
  it('writes the chain sentence in a fixed state order with neutral verbs', () => {
    const s = chainSentence([
      { code: 'L1', state: 'för få källor' },
      { code: 'L2', state: 'stabil' },
      { code: 'L3', state: 'accelererar' },
      { code: 'L4', state: 'accelererar' },
      { code: 'L5', state: 'accelererar' },
      { code: 'L6', state: 'bromsar in' },
      { code: 'L7', state: 'blandat' }
    ]);
    expect(s).toBe(
      'I kedjan: L3–L5 accelererar, L2 är stabilt, L6 bromsar in, L7 har grenar i olika tillstånd och L1 har för få källor.'
    );
    expect(s).not.toMatch(/oroande|bra|dålig|varning|risk/i);
  });
  it('falls back to a counts sentence that matches the pipeline wording', () => {
    expect(countsSentence({ accelererar: 4, stabil: 3, 'bromsar in': 0, 'för få källor': 2, 'för få serier': 0, 'inga registrerade kärnserier': 0 })).toBe(
      'Av 7 grenar med tillstånd: 4 accelererar, 3 är stabila och ingen bromsar in.'
    );
    // one is "en", as site_bundle.export._sv_number writes it
    expect(countsSentence({ accelererar: 0, stabil: 1, 'bromsar in': 1 })).toBe('Av 2 grenar med tillstånd: ingen accelererar, en är stabil och en bromsar in.');
  });
  it('names the branches whose state v1 would give differently', () => {
    const b = (code: string, state: BranchView['state'], state_v1: BranchView['state_v1']) => ({ code, state, state_v1, rule_version: 'v2' as const });
    expect(v1Sentence([b('G1', 'stabil', 'stabil'), b('G6', 'stabil', 'accelererar'), b('G8', 'för få källor', 'för få serier'), b('G9', 'för få källor', 'bromsar in')])).toBe(
      'Med regel v1, en röst per serie, hade G6 accelererat och G9 bromsat in.'
    );
    expect(v1Sentence([b('G8', 'för få källor', 'för få serier')])).toBe('Med regel v1, en röst per serie, hade alla grenar samma tillstånd.');
    expect(v1Sentence([b('G1', 'stabil', 'stabil')])).toBe('Med regel v1, en röst per serie, hade alla grenar samma tillstånd.');
    expect(v1Sentence([{ code: 'G1', state: 'stabil', state_v1: null, rule_version: 'v1' }])).toBe('');
  });
});

describe('selection', () => {
  const nc = (id: string, forecasts: unknown[]): Nowcast =>
    ({ id, label: id.toUpperCase(), title: id, champion: 'B1', next_origin: null, next_period: null, unit: 'u', decimals: 0, forecasts }) as Nowcast;
  const f = (origin: string, value: number) => ({ period: '2026-09', origin, value, champion: 'B1', intervals: { '50': [value - 1, value + 1], '80': [value - 2, value + 2], '95': [value - 3, value + 3] } });

  it('picks the latest live forecast across nowcasts and ignores files without intervals', () => {
    const got = latestForecast([nc('n1', [f('2026-10-05', 10)]), nc('n2', [f('2026-11-05', 20), { origin: '2026-12-01', value: 1 }])]);
    expect(got?.id).toBe('n2');
    expect(got?.value).toBe(20);
    expect(latestForecast([nc('n1', [])])).toBeNull();
  });
  it('turns the intervals into monotone stored quantiles', () => {
    const q = forecastQuantiles(latestForecast([nc('n1', [f('2026-10-05', 10)])])!);
    expect(q.map((x) => x[0])).toEqual([0.025, 0.1, 0.25, 0.5, 0.75, 0.9, 0.975]);
    expect(q.map((x) => x[1])).toEqual([7, 8, 9, 10, 11, 12, 13]);
  });
  it('focuses the next live forecast when none has been made, never D2', () => {
    const cal = [
      { id: 'd2', label: 'D2', title: '', champion: null, next_origin: '2026-12-01', next_period: null, n_live: 0 },
      { id: 'n4', label: 'N4', title: '', champion: 'B1', next_origin: '2027-01-20', next_period: null, n_live: 0 },
      { id: 'n2', label: 'N2', title: '', champion: 'B3', next_origin: '2026-12-05', next_period: null, n_live: 0 }
    ];
    expect(focusNowcast(cal, null)).toBe('n2');
  });
  it('counts index moves since last month', () => {
    const b = (index: number | null, prev: number | null) => ({ index, prev: { month: '2026-09', index: prev, state: null } }) as BranchView;
    expect(moveCounts([b(0.5, 0.4), b(0.2, 0.4), b(0.5, 0.5), b(null, 0.5), b(0.5, null)])).toEqual({ up: 1, down: 1, same: 1, n: 3 });
  });
  it('slices the last 24 months for the sparklines', () => {
    const months = Array.from({ length: 30 }, (_, i) => `20${24 + Math.floor(i / 12)}-${String((i % 12) + 1).padStart(2, '0')}`);
    const ov = {
      stripes: { months, kind: months.map(() => 'rekonstruerad'), rows: [{ code: 'G1', name: 'x', index: months.map((_, i) => i / 30), state: months.map(() => 'stabil'), n_series: [] }], thresholds: {} }
    } as unknown as Overview;
    const s = sparkViews(ov).G1;
    expect(s.months).toHaveLength(24);
    expect(s.months[0]).toBe(months[6]);
    expect(s.index[23]).toBeCloseTo(29 / 30);
  });
});

describe.each(dirs)('start data from %s', (dir) => {
  it('uses the pipeline headline and generates the chain sentence from flow.json', async () => {
    const s = await load(dir);
    const ov = await fsBundle(dir).overview();
    expect(s.headline.sentence).toBe(ov.headline.sentence);
    // the frontend fallback says the same as the pipeline, so neither drifts unnoticed
    expect(countsSentence(s.headline.counts)).toBe(ov.headline.sentence);
    expect(s.headline.chainSentence).toMatch(/^I kedjan: .+\.$/);
    for (const l of s.leads) expect(s.headline.chainSentence).toMatch(new RegExp(`${l.code}\\b|L\\d–L\\d`));
  });
  it('has nine leads in chain order whose branches all exist, and a sparkline per branch', async () => {
    const s = await load(dir);
    expect(s.leads.map((l) => l.code)).toEqual(['L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8', 'L9']);
    const codes = new Set(s.branches.map((b) => b.code));
    for (const l of s.leads) for (const b of l.branches) expect(codes.has(b.code)).toBe(true);
    for (const b of s.branches) {
      expect(s.sparks[b.code].index.length).toBeLessThanOrEqual(24);
      expect(b.n_up + b.n_neutral + b.n_down).toBe(b.n_series);
    }
  });
  it('labels every stripe month as live or reconstructed', async () => {
    const s = await load(dir);
    expect(s.stripes.kind).toHaveLength(s.stripes.months.length);
    for (const k of s.stripes.kind) expect(['skarp', 'rekonstruerad']).toContain(k);
  });
  it('keeps the page data small (it is inlined in the HTML)', async () => {
    const s = await load(dir);
    expect(JSON.stringify(s).length).toBeLessThan(40_000);
  });
  it('generates the chart sentences', async () => {
    const s = await load(dir);
    expect(nowDescription(s.branches, 'oktober 2026', 'september 2026')).toMatch(/^Diffusionsindex för \d av 9 grenar/);
    expect(calendarDescription(s.calendar, (d) => d, (p) => p)).toMatch(/^Nästa skarpa prognos/);
    if (s.calibration) expect(calibrationDescription(s.calibration)).toMatch(/^Backtest av N\d:s huvudmodell/);
    expect(reconDescription(s.reconciliations)).toMatch(/^Takten i \d+ avstämning/);
  });
});

describe('fixture specifics', () => {
  it('shows the live N2 forecast and its champion backtest', async () => {
    const s = await load(fixtures);
    expect(s.forecast?.id).toBe('n2');
    expect(s.forecast?.intervals['80']).toEqual([38100, 44100]);
    expect(s.calibration?.id).toBe('n2');
    expect(s.calibration?.model).toBe('B3');
    expect(s.regime.available).toBe(true);
    expect(s.headline.changes.map((c) => c.code)).toEqual(['G6']);
    // index v2 in the fixtures: G6 has three families (two series in us_ip_g17) and is stable; v1 says accelerating
    const g6 = s.branches.find((b) => b.code === 'G6')!;
    expect([g6.rule_version, g6.n_families, g6.state, g6.state_v1]).toEqual(['v2', 3, 'stabil', 'accelererar']);
    expect(s.headline.counts['för få källor']).toBe(6);
    expect(s.headline.v1Sentence).toBe('Med regel v1, en röst per serie, hade G6 accelererat och G9 bromsat in.');
  });
  it('names a level outside its binomial band', () => {
    const c = { id: 'n2', label: 'N2', title: '', model: 'B3', n: 226, first: '2008-01', last: '2026-09', rows: [
      { level: '50' as const, coverage: 0.4, band: [0.42, 0.58] as [number, number] },
      { level: '80' as const, coverage: 0.8, band: [0.74, 0.86] as [number, number] },
      { level: '95' as const, coverage: 0.95, band: [0.91, 0.98] as [number, number] }
    ] };
    expect(calibrationDescription(c)).toBe(
      'Backtest av N2:s huvudmodell B3, 226 prognoser 2008–2026: 40 % inom 50 %-intervallet, 80 % inom 80 %-intervallet och 95 % inom 95 %-intervallet. 50 %-nivån ligger utanför slumpbandet.'
    );
  });
});

describe('UnitGlyphs', () => {
  it('draws one mark per counted series, grouped ▲ ● ▼, and names withheld ones only as a count', () => {
    const { container } = render(UnitGlyphs, { up: 2, neutral: 1, down: 3, withheld: 1 });
    expect(container.querySelectorAll('svg .mark')).toHaveLength(6);
    expect(container.querySelectorAll('svg circle')).toHaveLength(1);
    expect(container.querySelector('svg')?.getAttribute('aria-label')).toBe(
      '6 räknade serier: 2 ökar takten, 1 oförändrad takt, 3 minskar takten, varav 1 inhållna av licensskäl'
    );
    expect(container.textContent).toContain('varav 1 inhållna');
  });
  it('says so when a branch has no counted series', () => {
    const { container } = render(UnitGlyphs, { up: 0, neutral: 0, down: 0 });
    expect(container.querySelector('svg')).toBeNull();
    expect(container.textContent).toContain('inga räknade serier');
  });
});
