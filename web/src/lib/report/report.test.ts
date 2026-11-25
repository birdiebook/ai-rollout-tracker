// W14: the quarterly report's view model against the committed fixtures (and a real bundle with
// REPORT_BUNDLE_DIR=/tmp/bundle): every figure cut to the report day, the movers in the report's order, a document
// with later knowledge refused, time travel only showing reports known on the day, and the essay rendered.
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import { fsBundle } from '$lib/server/bundle';
import type { Report } from '$lib/data';
import { LeakError, leaks } from '$lib/timetravel/gate';
import { reportDocs } from './load.server';
import { MAX_MOVERS, outcomeRow, quartersKnownOn, reportPage } from './model';
import ReportView from './ReportView.svelte';

const dirs = [resolve('../web-data-fixtures'), process.env.REPORT_BUNDLE_DIR].filter(
  (d): d is string => !!d && existsSync(resolve(d, 'report/index.json'))
);

for (const dir of dirs) {
  describe(`report model (${dir})`, async () => {
    const b = fsBundle(dir);
    const idx = await b.reportIndex();

    it('every quarter: figures cut to the report day, nothing known later', async () => {
      expect(idx.quarters.length).toBeGreaterThan(0);
      for (const q of idx.quarters) {
        const d = await reportDocs(b, q.quarter);
        const p = reportPage(d);
        expect(p.day).toBe(q.known);
        expect(p.day >= d.report.end).toBe(true);
        expect(p.stripes.months.at(-1)).toBe(d.report.months[2].month);
        expect(p.stripes.known.every((k) => k <= p.day)).toBe(true);
        expect(p.highlight).toBe(d.report.months[2].month);
        for (const m of p.movers) expect(m.history.at(-1)!.month <= d.report.months[2].month).toBe(true);
        for (const r of p.ratios) if (r.recon) expect(r.recon.periods.length).toBeGreaterThan(0);
        for (const n of p.nowcasts) if (n.level) expect(n.level.points.length).toBeGreaterThan(0);
        expect(leaks({ ...p, quarters: [] }, p.day)).toEqual([]);
        expect(p.leads.map((l) => l.lead)).toEqual(['L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8', 'L9']);
        expect(p.mini.length).toBe(9);
      }
    });

    it('the movers follow the report: largest moves first, then state changes, at most four', async () => {
      const d = await reportDocs(b, idx.latest!);
      const p = reportPage(d);
      const want = [...new Set([...d.report.summary.moved.map((m) => m.code), ...d.report.summary.changed.map((c) => c.code)])].slice(0, MAX_MOVERS);
      expect(p.movers.map((m) => m.code)).toEqual(want);
    });

    it('a report with later knowledge is refused (LeakError)', async () => {
      const d = await reportDocs(b, idx.latest!);
      const bad: Report = structuredClone(d.report);
      bad.ratios = [{ ...(bad.ratios[0] ?? ({} as Report['ratios'][number])), key: 'x', known_from: '2999-01-01' } as Report['ratios'][number]];
      expect(() => reportPage({ ...d, report: bad })).toThrow(LeakError);
      const early: Report = { ...structuredClone(d.report), known: '2000-01-01' };
      expect(() => reportPage({ ...d, report: early })).toThrow(LeakError);
    });

    it('time travel: only the quarters known on the day', async () => {
      const p = reportPage(await reportDocs(b, idx.latest!));
      const first = p.quarters[0];
      expect(quartersKnownOn(p.quarters, first.known).map((q) => q.quarter)).toEqual([first.quarter]);
      const before = new Date(Date.parse(first.known) - 86400000).toISOString().slice(0, 10);
      expect(quartersKnownOn(p.quarters, before)).toEqual([]);
    });

    it('renders the six sections, the reconstructed label and the generated text', async () => {
      const p = reportPage(await reportDocs(b, idx.latest!));
      const { container } = render(ReportView, { props: { page: p } });
      expect([...container.querySelectorAll('section.sec')].map((s) => s.id)).toEqual(['lage', 'kedjan', 'floden', 'prognoser', 'regim', 'data']);
      expect(container.querySelector('h1')!.textContent).toMatch(/kvartalet \d{4}/);
      expect(container.querySelector('.lede')!.textContent).toBe(p.report.headline);
      expect(!!container.querySelector('[data-recon]')).toBe(p.report.status === 'reconstructed');
      expect(container.querySelectorAll('li.lead').length).toBe(9);
      expect(container.querySelectorAll('[data-nowcast]').length).toBe(p.report.nowcasts.length);
      expect(container.querySelector('article.report')!.getAttribute('data-known')).toBe(p.day);
    });
  });
}

describe('outcome rows for the quantile dots', () => {
  it('inside per level from the stored intervals', () => {
    const r = outcomeRow({ period: '2026-07', origin: '2026-08-05', file: 'forecasts/n2/2026-07.json', slug: '2026-07', champion: 'B2', forecast: 100, outcome: 104, known_from: '2026-08-10', err_champion: -3.9, errors: {}, intervals: { '50': [98, 102], '80': [95, 105], '95': [90, 110] } });
    expect(r.inside).toEqual({ '50': false, '80': true, '95': true });
    expect(r.value).toBe(100);
    expect(r.outcomeKnown).toBe('2026-08-10');
  });
});
