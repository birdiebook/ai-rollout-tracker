import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { render, within } from '@testing-library/svelte';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import { REST_TOLERANCE, RECON_DEFS, contributions, formula, overviewSentence, qShift, side } from './recon';
import { RULES, breaksSentence, headline, laneSentence, timelineMonths, zone } from './regime';
import { HOLDOUT, monthRange } from './holdout';
import RegimeMeter from './RegimeMeter.svelte';
import Components from './Components.svelte';
import type { ComponentView, RegimeLane } from './types';

describe('reconciliation arithmetic', () => {
  it('shifts quarters across years', () => {
    expect(qShift('2026Q1', -1)).toBe('2025Q4');
    expect(qShift('2026Q3', -4)).toBe('2025Q3');
    expect(qShift('2025Q4', 1)).toBe('2026Q1');
  });

  it('sums a 4-quarter window and refuses a missing quarter', () => {
    const lv = new Map([['a', new Map([['2025Q1', 1], ['2025Q2', 2], ['2025Q3', 3], ['2025Q4', 4]])]]);
    expect(side([{ series: 'a', window: 4 }], lv, '2025Q4')).toBe(10);
    expect(side([{ series: 'a', window: 4 }], lv, '2025Q3')).toBeNull();
    expect(side([{ series: 'a', window: 1 }, { series: 'b', window: 1 }], lv, '2025Q4')).toBeNull();
  });

  it('multiplies a term by its weight (P2b: r on net PP&E), 1 when absent', () => {
    const lv = new Map([
      ['dep', new Map([['2025Q1', 1], ['2025Q2', 2], ['2025Q3', 3], ['2025Q4', 4]])],
      ['ppe', new Map([['2025Q4', 200]])]
    ]);
    expect(side([{ series: 'dep', window: 4 }, { series: 'ppe', window: 1, weight: 0.08 }], lv, '2025Q4')).toBeCloseTo(10 + 16, 12);
    expect(side([{ series: 'ppe', window: 1 }], lv, '2025Q4')).toBe(200);
  });

  it('splits the pace exactly into numerator and denominator parts', () => {
    // N grows 10 %/quarter, D 5 %/quarter; ratio pace = 100 * 4 * (ln 1.1 - ln 1.05)
    const qs = monthQuarters('2020Q1', 12);
    const N = new Map(qs.map((q, i) => [q, 100 * 1.1 ** i]));
    const D = new Map(qs.map((q, i) => [q, 50 * 1.05 ** i]));
    const def = { key: 'x', num: [{ series: 'n', window: 1 }], den: [{ series: 'd', window: 1 }], scale: 100 };
    const periods = qs.slice(4);
    const pace = periods.map(() => 400 * (Math.log(1.1) - Math.log(1.05)));
    const c = contributions(def, new Map([['n', N], ['d', D]]), periods, pace);
    expect(c.num_c[0]).toBeCloseTo(400 * Math.log(1.1), 9);
    expect(c.den_c[0]).toBeCloseTo(-400 * Math.log(1.05), 9);
    expect(c.max_rest).toBeLessThan(1e-9);
    expect(c.num_idx[0]).toBe(100);
    expect(c.den_idx.at(-1)).toBeCloseTo(100 * 1.05 ** 7, 9);
  });

  it('shows what does not add up as a rest', () => {
    const qs = monthQuarters('2020Q1', 6);
    const N = new Map(qs.map((q) => [q, 1]));
    const def = { key: 'x', num: [{ series: 'n', window: 1 }], den: [{ series: 'n', window: 1 }], scale: 1 };
    const c = contributions(def, new Map([['n', N]]), qs.slice(4), [5, 5]);
    expect(c.rest).toEqual([5, 5]);
  });

  it('mirrors the registered definitions and writes them as formulas', () => {
    expect(RECON_DEFS.map((d) => d.key)).toEqual([
      'x_capex_cloud', 'x_rpo_cover', 'x_nvda_capex', 'x_debt_capex', 'x_capex_ocf',
      'x_dep_rev', 'x_capcost_rev_r08', 'x_capcost_rev_r12', 'x_dep_capex', 'x_dep_rev_aws'
    ]);
    const r08 = RECON_DEFS.find((d) => d.key === 'x_capcost_rev_r08')!;
    expect(r08.num.filter((t) => t.weight !== undefined)).toEqual([{ series: 'ppe_net_hyp4', window: 1, weight: 0.08 }]);
    expect(formula(r08)).toBe('(summa 4 kv. av dep_hyp4 + 0,08 × ppe_net_hyp4) / (summa 4 kv. av rev_msft + summa 4 kv. av rev_googl + summa 4 kv. av rev_amzn + summa 4 kv. av rev_meta) × 100');
    expect(formula(RECON_DEFS[0])).toBe('capex_hyp4 / (rev_aws + rev_google_cloud + rev_msft_cloud)');
    expect(formula(RECON_DEFS[1])).toBe('rpo_hyp4 / summa 4 kv. av capex_hyp4');
    expect(formula(RECON_DEFS[4])).toBe('capex_hyp4 / ocf_hyp4 × 100');
  });

  it('generates the overview sentence from the pipeline fields', () => {
    expect(
      overviewSentence([
        { pace_percentile: 98, direction: 1 },
        { pace_percentile: 40, direction: 0 },
        { pace_percentile: 60, direction: -1 }
      ])
    ).toBe('3 kvoter förbinder leden. För 2 av dem ligger takten över medianen i sin egen historik. 1 ökar takten, 1 har oförändrad takt och 1 minskar takten.');
    expect(overviewSentence([{ pace_percentile: 30, direction: null }])).toContain('En kvot förbinder leden. Dess takt ligger under medianen');
  });
});

function monthQuarters(first: string, n: number) {
  return Array.from({ length: n }, (_, i) => qShift(first, i));
}

describe('regime helpers', () => {
  it('uses the registered thresholds', () => {
    expect([RULES.shiftAtLeast, RULES.backAtMost, RULES.inARow, RULES.breakAtLeast]).toEqual([0.8, 0.2, 2, 0.8]);
    expect(zone(0.8)).toBe('slow');
    expect(zone(0.2)).toBe('back');
    expect(zone(0.5)).toBe('between');
    expect(zone(null)).toBeNull();
  });

  it('runs the timeline at least twelve months from the first live month', () => {
    expect(timelineMonths([], '2026-11-30')).toEqual(monthRange('2026-11', '2027-10'));
    expect(timelineMonths(['2026-10'], '2026-10-31')[0]).toBe('2026-10');
    const long = monthRange('2026-11', '2028-02');
    expect(timelineMonths(long, '2026-11-30')).toEqual(long);
  });

  it('says plainly when there is no live month yet', () => {
    expect(headline(false, [], '2026-11-30')).toBe('Regimen följs skarpt från den första ögonblicksbilden 30 nov 2026. Ännu finns ingen skarp månad.');
    expect(breaksSentence(0, 0, 0)).toContain('Inga skarpa månader');
    expect(breaksSentence(1, 1, 1)).toBe('2 strukturbrott på 1 skarpa månad, varav 1 på en inhållen serie (räknas, visas utan namn och värde).');
  });

  it('describes a lane neutrally against the thresholds', () => {
    const lane: RegimeLane = {
      block: 'demand',
      label: 'efterfrågan',
      history: [],
      latest: { month: '2026-10', p: 0.83, state: 'inbromsning', shift: 'inbromsning', n_months: 96, reason: '' }
    };
    const s = laneSentence(lane);
    expect(s).toBe('Efterfrågan okt 2026: P(inbromsning) 0,83, på eller över 0,8. Rapporterat tillstånd: inbromsning. Tillståndet byttes till inbromsning denna månad.');
    expect(s).not.toMatch(/larm|varning|oroande|risk/i);
  });

  it('holdout constants agree with themselves', () => {
    const months = monthRange(HOLDOUT.first, HOLDOUT.last);
    expect(months).toHaveLength(HOLDOUT.n_days);
    for (const b of HOLDOUT.blocks) for (const m of b.slow_months) expect(months).toContain(m);
    expect(HOLDOUT.bocpd.breaks.every((x) => x.p_recent >= RULES.breakAtLeast)).toBe(true);
  });
});

describe('components', () => {
  it('RegimeMeter shows the probability, the state word and the thresholds', () => {
    const { container } = render(RegimeMeter, {
      lane: { block: 'capex', label: 'capex och leverantörsled', history: [], latest: { month: '2026-10', p: 0.12, state: 'expansion', shift: null, n_months: 140, reason: '' } }
    });
    const w = within(container);
    expect(w.getByRole('heading', { name: 'Capex och leverantörsled' })).toBeTruthy();
    expect(container.textContent).toContain('12 %');
    expect(container.textContent).toContain('expansion');
    expect(container.textContent).toContain('0,8');
    expect(container.textContent).toContain('0,2');
  });

  it('RegimeMeter without a live month shows no number', () => {
    const { container } = render(RegimeMeter, { lane: { block: 'capex', label: 'capex', history: [], latest: null } });
    expect(container.textContent).toContain('inget skarpt värde än');
    expect(container.querySelector('.mark')).toBeNull();
  });

  it('a withheld component has its name only: no link, no number, no direction', () => {
    const items: ComponentView[] = [
      { key: 'pub', label: 'Publicerad', side: 'num', window: 1, weight: 1, linkable: true, unit: 'USD', latest_period: '2026Q3', pace: 12.3, pace_unit: 'log', pace_percentile: 70, direction: 1, levels: { periods: ['2026Q2', '2026Q3'], values: [1, 2] } },
      { key: 'held', label: 'Inhållen serie', side: 'den', window: 4, weight: 1, linkable: false, unit: null, latest_period: null, pace: null, pace_unit: null, pace_percentile: null, direction: null, levels: null }
    ];
    const { container } = render(Components, { items });
    const held = container.querySelector('.held')!;
    expect(held.textContent).toContain('Inhållen serie');
    expect(held.querySelector('a')).toBeNull();
    expect(held.textContent).not.toMatch(/\d+,\d|ökar|minskar|oförändrad/);
    expect(within(container).getByRole('link', { name: 'Publicerad' }).getAttribute('href')).toContain('/serie/pub');
  });
});

// The page loads, against the bundle the build uses (static/data, synced by npm run sync-bundle) or W3's fixtures.
const dir = [resolve('static/data'), resolve('../web-data-fixtures')].find((d) => existsSync(resolve(d, 'manifest.json')));
describe.runIf(!!dir)('page loads against the bundle', () => {
  let mod: typeof import('./load.server');
  let synthetic = true;
  beforeAll(async () => {
    vi.stubEnv('SITE_BUNDLE_READ_DIR', dir!);
    mod = await import('./load.server');
    synthetic = !!JSON.parse(readFileSync(resolve(dir!, 'manifest.json'), 'utf-8')).synthetic;
  });

  it('every visible reconciliation has its components; withheld ones carry no values', async () => {
    const r = await mod.reconciliations();
    expect(r.views.length).toBeGreaterThan(0);
    for (const v of r.views) {
      expect(v.components.length).toBeGreaterThan(1);
      for (const c of v.components) if (!c.linkable) expect([c.pace, c.levels, c.direction, c.pace_percentile]).toEqual([null, null, null, null]);
      expect(v.periods.length).toBe(v.pace_path.length);
    }
  });

  it('on real data the components add up to the pipeline pace (rest is rounding only)', async () => {
    if (synthetic) return; // the synthetic fixture draws ratio and components independently
    const r = await mod.reconciliations();
    for (const v of r.views) expect(v.max_rest ?? 0).toBeLessThan(REST_TOLERANCE);
  });

  it('regime loads; breaks name only publishable series', async () => {
    const g = await mod.regime();
    expect(typeof g.available).toBe('boolean');
    if (!g.available) expect(g.lanes).toEqual([]);
    for (const b of g.breaks) expect(b.linkable).toBe(true);
  });
});

// F1 expectations (bundle 1.5.0): rows whose numbers are withheld are counted boxes with ids only.
describe('expectations against outcomes', () => {
  const doc = JSON.parse(readFileSync(resolve('../web-data-fixtures/expectations.json'), 'utf-8'));
  it('reads the fixture: the curated companies are withheld, never in a branch index', async () => {
    const { expectationsView } = await import('./expectations');
    const v = expectationsView(doc);
    expect(doc.in_diffusion).toBe(false);
    expect(v.csvPublic).toBe(false);
    expect(v.revision4q?.withheld).toBe(true);
    expect(v.revision4q?.value).toBeNull();
    expect(v.events.length).toBeGreaterThan(0);
    for (const e of v.events) if (e.withheld) expect(e.direction).toBeNull();
  });
  it('shows a withheld card and event without any number or direction', async () => {
    const { expectationsView } = await import('./expectations');
    const { default: ExpectationsSection } = await import('./ExpectationsSection.svelte');
    const { container } = render(ExpectationsSection, { v: expectationsView(doc) });
    const held = [...container.querySelectorAll('.card.held')];
    expect(held.length).toBeGreaterThan(0);
    for (const c of held) expect(c.textContent).not.toMatch(/\d,\d|n = /);
    for (const u of container.querySelectorAll('.events .unit.held')) expect(u.textContent?.trim()).toBe('');
  });
  it('shows the numbers of a published row', async () => {
    const { expectationsSentence, expectationsView } = await import('./expectations');
    const pub = {
      ...doc,
      csv_public: true,
      revisions: { window_4q: { latest: null, latest_with_value: { period: '2026Q4', known_from: '2026-10-29', n: 13, n_up: 4, n_unchanged: 8, n_down: 1, index: 0.6154, percentile: 58.7, n_history: 23 } } },
      surprise: { companies: [{ company: 'tsmc', measure: 'revenue', period: '2026Q3', known_from: '2026-10-16', surprise: 3.2, z: 0.8, n: 20, surprise_percentile: 70 }], index: { latest: null, latest_with_value: null } }
    };
    const v = expectationsView(pub);
    expect(v.revision4q).toMatchObject({ value: 0.6154, n: 13, up: 4, withheld: false });
    expect(v.companies[0]).toMatchObject({ name: 'TSMC', surprise: 3.2, withheld: false });
    expect(expectationsSentence(v)).toContain('Revideringsindexet över 4 kvartal är 0,62 med 13 revideringar');
  });
});
