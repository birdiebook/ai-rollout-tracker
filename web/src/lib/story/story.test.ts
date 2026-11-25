// W13: the story view model against the committed fixtures (and a real bundle with STORY_BUNDLE_DIR=/tmp/bundle).
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { render } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import { fsBundle } from '$lib/server/bundle';
import type { Branch, Story } from '$lib/data';
import type { SeriesDoc } from '$lib/series/types';
import { LeakError, monthKnown, seriesOn } from '$lib/timetravel/gate';
import { monthsKnownOn, storyPage, target, type Docs } from './model';
import StoryView from './StoryView.svelte';
import TrackChart from './TrackChart.svelte';

const dirs = [resolve('../web-data-fixtures'), process.env.STORY_BUNDLE_DIR].filter(
  (d): d is string => !!d && existsSync(resolve(d, 'story/index.json'))
);

async function docs(dir: string, month: string): Promise<Docs> {
  const b = fsBundle(dir);
  const [story, index, overview, regime] = await Promise.all([b.story(month), b.storyIndex(), b.overview(), b.regime()]);
  const branches: Record<string, Branch> = {};
  for (const c of story.cards) if (c.type === 'K1') branches[c.facts.branch] = await b.branch(c.facts.branch);
  return { story, index, overview, regime, branches };
}

for (const dir of dirs) {
  describe(`story model (${dir})`, async () => {
    const b = fsBundle(dir);
    const idx = await b.storyIndex();

    it('every month: one figure per card, everything cut to the month known day', async () => {
      for (const m of idx.months) {
        const d = await docs(dir, m.month);
        const p = storyPage(d);
        expect(p.day).toBe(monthKnown(m.month, d.overview.record));
        expect(p.cards.length).toBe(d.story.cards.length);
        expect(p.cards[0].type).toBe('K0');
        for (const c of p.cards) {
          expect(c.figure.kind).not.toBe('none');
          if (c.figure.kind === 'stripes') expect(c.figure.stripes.months.at(-1)).toBe(m.month);
          if (c.figure.kind === 'index') expect(c.figure.history.at(-1)!.month).toBe(m.month);
        }
      }
    });

    it('a story with later knowledge is refused (LeakError)', async () => {
      const d = await docs(dir, idx.latest!);
      const bad: Story = structuredClone(d.story);
      bad.cards[0].facts.known_from = '2999-01-01';
      expect(() => storyPage({ ...d, story: bad })).toThrow(LeakError);
      expect(() => storyPage({ ...d, story: { ...d.story, known: '2999-01-01' } })).toThrow(LeakError);
    });

    it("K5 tracks equal the gate's cut of the series' measure history", async () => {
      let n = 0;
      for (const m of idx.months) {
        const s = await b.story(m.month);
        for (const c of s.cards.filter((c) => c.type === 'K5')) {
          const on = seriesOn((await b.series(c.facts.series)) as unknown as SeriesDoc, s.known);
          const h = on.history!;
          expect(h.months).toEqual(c.track!.months);
          expect(h.change_percentile).toEqual(c.track!.values);
          n++;
        }
      }
      if (dir.endsWith('web-data-fixtures')) expect(n).toBeGreaterThan(0);
    });

    it('time travel lists only the months known on the day', () => {
      const months = idx.months.map((m) => ({ ...m }));
      const day = months[Math.floor(months.length / 2)].known;
      const on = monthsKnownOn(months, day);
      expect(on.every((m) => m.known <= day)).toBe(true);
      expect(on.at(-1)!.known).toBe(day);
    });
  });
}

describe('links', () => {
  it('time-travel views get the known day, the others open as today', () => {
    expect(target({ kind: 'branch', id: 'G6', slug: null, label: '' }, '2026-10-31')).toEqual({ route: '/gren/[id]', params: { id: 'G6' }, asOf: '2026-10-31' });
    expect(target({ kind: 'series', id: 'k', slug: null, label: '' }, '2026-10-31').asOf).toBe('2026-10-31');
    expect(target({ kind: 'nowcast', id: 'n2', slug: '2026-09', label: '' }, '2026-10-31')).toEqual({ route: '/prognoser/[id]/[[slug]]', params: { id: 'n2', slug: '2026-09' }, asOf: null });
    expect(target({ kind: 'regime', id: null, slug: null, label: '' }, '2026-10-31').asOf).toBeNull();
  });
});

describe('TrackChart', () => {
  it('draws the extreme zones and the month as the coloured dot, with a sentence from the data', () => {
    const { container } = render(TrackChart, {
      id: 't',
      track: { field: 'change_percentile', months: ['2026-08', '2026-09', '2026-10'], values: [40, 60, 97.5] },
      month: '2026-10',
      direction: 1,
      unit: null,
      status: 'recon'
    });
    expect(container.querySelectorAll('rect.zone').length).toBe(2);
    expect(container.querySelector('circle.mark')?.getAttribute('data-month')).toBe('2026-10');
    expect(container.textContent).toContain('97,5');
  });
});

describe('StoryView texts (R-W3)', () => {
  it('singular counts, a Swedish comparison month, and K1 directions as index (not pace)', async () => {
    const dir = resolve('../web-data-fixtures');
    const idx = await fsBundle(dir).storyIndex();
    const months = [];
    for (const m of idx.months) months.push(await docs(dir, m.month));
    const d = months.find((x) => x.story.previous && x.story.cards.some((c) => c.type === 'K1' && c.direction !== null));
    expect(d).toBeDefined();
    const story: Story = { ...structuredClone(d!.story), omitted: { K1: 0, K2: 0, K3: 0, K4: 0, K5: 1, K6: 2 } };
    // jsdom has neither: the view's onMount (scrollytelling) needs both
    vi.stubGlobal('matchMedia', () => ({ matches: true, addEventListener() {}, removeEventListener() {} }));
    vi.stubGlobal('IntersectionObserver', class { observe() {} disconnect() {} unobserve() {} });
    const { container } = render(StoryView, { page: storyPage({ ...d!, story }) });
    vi.unstubAllGlobals();
    const text = container.textContent ?? '';
    expect(text).toContain('1 kärnserie i extrem percentil, 2 avstämningar i extrem percentil');
    expect(text).not.toContain('1 kärnserier');
    const prevSv = idx.months.find((m) => m.month === story.previous)!.month_sv;
    expect(text).toContain(`Jämförelsemånad: ${prevSv}.`);
    expect(text).toMatch(/Tillståndsskifte, (högre|lägre) index/);
    expect(text).not.toMatch(/Tillståndsskifte, (mer|mindre) takt/);
  });
});
