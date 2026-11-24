import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import RoleTag from './RoleTag.svelte';
import KindTag from './KindTag.svelte';
import LiveCalibration from './LiveCalibration.svelte';
import ForecastDots from './ForecastDots.svelte';
import { liveRows } from './model';
import type { Nowcast } from '$lib/data';

const nc: Nowcast = {
  id: 'n2', label: 'N2', title: 'TSMC', champion: 'B3', next_origin: null, next_period: null,
  variants: [{ id: 'B1', text: 'naiv' }, { id: 'B3', text: 'huvud' }],
  forecasts: [{ period: '2026-09', file: 'forecasts/n2/2026-09.json', value: 100, champion: 'B3', intervals: { '50': [95, 105], '80': [90, 110], '95': [85, 115] } }],
  scorecard: [{ period: '2026-09', status: 'utfall', outcome: 104, err_champion: -3.9, pit_champion: 0.7 }]
};

describe('RoleTag and KindTag', () => {
  it('names the main model with a solid ring and shadows dashed, always in words', () => {
    const c = render(RoleTag, { role: 'champion', id: 'B3' }).container;
    expect(c.textContent).toContain('Huvudmodell');
    expect(c.textContent).toContain('B3');
    expect(c.querySelector('[data-role="champion"]')).not.toBeNull();
    expect(render(RoleTag, { role: 'shadow', id: 'DF' }).container.textContent).toContain('Skugga');
  });
  it('tells live forecasts from backtests', () => {
    expect(render(KindTag, { kind: 'backtest' }).container.textContent).toContain('inte en skarp prognos');
    expect(render(KindTag, { kind: 'skarp' }).container.querySelector('[data-kind="skarp"]')).not.toBeNull();
  });
});

describe('LiveCalibration', () => {
  it('with no outcomes: the honest note and twelve waiting slots, no coverage chart', () => {
    const c = render(LiveCalibration, { id: 't', rows: [], coverage: [], champion: 'B1' }).container;
    expect(c.textContent).toContain('först efter cirka 12 skarpa utfall');
    expect(c.querySelectorAll('svg.slots circle')).toHaveLength(12);
    expect(c.querySelector('#t-cov')).toBeNull();
  });
  it('with one outcome: one filled slot (inside 80 %), the small-n warning and the coverage chart', () => {
    const c = render(LiveCalibration, { id: 't', rows: liveRows(nc), coverage: [], champion: 'B3' }).container;
    expect(c.textContent).toMatch(/1 av cirka 12.*slump/);
    expect(c.querySelectorAll('svg.slots circle[data-inside="true"]')).toHaveLength(1);
    expect(c.querySelector('#t-cov')).not.toBeNull();
    expect(c.querySelector('#t-pit svg[role="img"]')).not.toBeNull();
  });
});

describe('ForecastDots', () => {
  it('draws 20 dots and says where the outcome fell', () => {
    const row = liveRows(nc)[0];
    const c = render(ForecastDots, { id: 'fd', row, unit: 'mn TWD', format: (v: number | null | undefined) => String(v) }).container;
    expect(c.querySelectorAll('circle.dot')).toHaveLength(20);
    expect(c.querySelector('#fd-desc')?.textContent).toMatch(/Utfallet 104: \d+ av 20 prickar under/);
  });
});
