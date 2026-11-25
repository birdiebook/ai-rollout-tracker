// W9 time travel end to end: as_of in the URL, carried between pages, playback, and the leakage rule in the real
// browser: every value shown under a past day was known that day (data-known <= day in the time-travel regions,
// table rows = the replay), Python's sentence for that day is the one on the page, and today's content never
// paints under a past date.
import { existsSync, readFileSync } from 'node:fs';
import { expect, test, type Page } from '@playwright/test';
import { TT_DAY } from './routes';

interface V {
  periods: string[];
  dates: string[];
  p: number[];
  d: number[];
  v: number[];
}
const manifest = JSON.parse(readFileSync('static/data/manifest.json', 'utf-8')) as { synthetic?: boolean };
const index = JSON.parse(readFileSync('static/data/series/index.json', 'utf-8')) as { series: { key: string; branch: string; n_versions?: number; freq?: string }[] };
const revised = [...index.series].sort((a, b) => (b.n_versions ?? 0) - (a.n_versions ?? 0))[0];
const doc = JSON.parse(readFileSync(`static/data/series/${revised.key}.json`, 'utf-8')) as { versions: V };
// Python's replay on each probe day (fixtures; or TT_GOLDEN for a real bundle)
const goldenPath = process.env.TT_GOLDEN ?? (manifest.synthetic ? 'fixtures/timetravel_golden.json' : '');
const golden = goldenPath && existsSync(goldenPath)
  ? (JSON.parse(readFileSync(goldenPath, 'utf-8')) as { probes: { day: string; record: { sentence: string; month: string } | null; series: Record<string, { as_of?: { n: number } }> }[] })
  : null;

/** Every known-day attribute inside the time-travel regions is <= the day; returns how many were checked. */
async function noLaterKnowledge(page: Page, day: string): Promise<number> {
  const known = await page.locator('[data-tt="asof"] [data-known], [data-tt="asof"][data-known]').evaluateAll((els) => els.map((e) => e.getAttribute('data-known') ?? ''));
  const dated = known.filter((k) => /^\d{4}-\d{2}-\d{2}$/.test(k));
  expect(dated.filter((k) => k > day), `known after ${day}`).toEqual([]);
  return dated.length;
}

const asOfInUrl = (page: Page) => new URL(page.url()).hash.match(/as_of=(\d{4}-\d{2}-\d{2})/)?.[1] ?? null;

test('start page on a past day: the record known then, Python’s sentence, nothing later', async ({ page }) => {
  await page.goto(`#as_of=${TT_DAY}`);
  await expect(page.locator('[data-tt="view"] h1')).toContainText('Läget');
  expect(await noLaterKnowledge(page, TT_DAY)).toBeGreaterThan(5);
  if (golden) {
    const g = golden.probes.find((p) => p.day === TT_DAY);
    if (g?.record) await expect(page.locator('[data-tt="view"] .lede').first()).toContainText(g.record.sentence);
  }
  // the stripes table lists only months whose month end is on or before the day
  await page.locator('#tt-stripes').getByRole('button', { name: 'Visa tabell' }).click();
  await expect(page.locator('#tt-stripes-table tbody tr').first()).toBeVisible();
});

test('every golden probe day: the start page shows the sentence Python’s Record(today=D) wrote', async ({ page }) => {
  test.skip(!golden, 'no golden for this bundle');
  for (const p of golden!.probes) {
    await page.goto('about:blank');
    await page.goto(`#as_of=${p.day}`);
    const h1 = page.locator('[data-tt="view"] h1');
    if (p.record) {
      await expect(page.locator('[data-tt="view"] .lede').first()).toContainText(p.record.sentence);
    } else {
      await expect(h1).toHaveText('Inget läge ännu');
    }
    await noLaterKnowledge(page, p.day);
  }
});

test('series on a past day: the level table is exactly the replay, every row known by then', async ({ page }) => {
  await page.goto(`serie/${revised.key}/#as_of=${TT_DAY}`);
  await expect(page.locator('#tt-level svg[role="img"]')).toBeVisible();
  const v = doc.versions;
  const known = new Map<string, string>();
  for (let i = 0; i < v.p.length && v.dates[v.d[i]] <= TT_DAY; i++) known.set(v.periods[v.p[i]], v.dates[v.d[i]]);
  await page.locator('#tt-level').getByRole('button', { name: 'Visa tabell' }).click();
  const rows = page.locator('#tt-level-table tbody tr');
  await expect(rows).toHaveCount(known.size);
  if (golden) {
    const g = golden.probes.find((p) => p.day === TT_DAY)?.series[revised.key]?.as_of;
    if (g) expect(known.size).toBe(g.n); // = observations.as_of(key, day) on the source table
  }
  const kf = await page.locator('#tt-level-table tbody tr td:last-child').allInnerTexts();
  expect(kf.every((d) => d <= TT_DAY)).toBe(true);
  expect(kf[0]).toBe([...known.values()].sort().at(-1));
  await noLaterKnowledge(page, TT_DAY);
  // W7's revision view (then against today, labelled) opens on the same day
  await expect(page.locator('[data-tt="compare"] #rev-versions')).toBeVisible();
});

test('as_of follows the links between pages, and "I dag" returns to today', async ({ page }) => {
  await page.goto(`#as_of=${TT_DAY}`, { waitUntil: 'networkidle' });
  await page.locator('[data-tt="view"] .tiles a', { hasText: 'G6' }).click();
  await expect(page).toHaveURL(new RegExp(`/gren/G6/#as_of=${TT_DAY}$`));
  await expect(page.locator('[data-tt="view"] h1')).toContainText('G6');
  await page.waitForLoadState('networkidle');
  await noLaterKnowledge(page, TT_DAY);
  const card = page.locator('[data-tt="view"] .cards a').first();
  await card.click();
  await expect(page).toHaveURL(new RegExp(`/serie/[^/]+/#as_of=${TT_DAY}$`));
  await expect(page.locator('#tt-level')).toBeVisible();
  // the main menu carries it too
  await page.getByRole('navigation', { name: 'Huvudmeny' }).getByRole('link', { name: 'Läget' }).click();
  await expect(page).toHaveURL(new RegExp(`#as_of=${TT_DAY}$`));
  await page.getByRole('button', { name: 'I dag' }).first().click();
  expect(asOfInUrl(page)).toBeNull();
  await expect(page.locator('[data-tt="view"]')).toHaveCount(0);
  await expect(page.locator('#stripes-chart')).toBeVisible(); // W5's start page is back
  // and the links no longer carry the old day
  await page.getByRole('navigation', { name: 'Huvudmeny' }).getByRole('link', { name: 'Flödet' }).click();
  await expect(page).toHaveURL(/\/flode\/$/);
});

test('slider buttons step month ends; play advances and pauses; start from today with the button', async ({ page }) => {
  await page.goto('', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: /Tidsresa: vad visste vi den/ }).click();
  const first = asOfInUrl(page);
  expect(first).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  await page.getByRole('button', { name: '−1 månad' }).click();
  const back = asOfInUrl(page)!;
  expect(back < first!).toBe(true);
  expect(new Date(Date.parse(back) + 86_400_000).getUTCDate()).toBe(1); // a month end
  await page.getByRole('button', { name: '+1 månad' }).click();
  await page.getByRole('button', { name: 'Spela', exact: true }).click();
  await expect.poll(() => asOfInUrl(page), { timeout: 5000 }).not.toBe(first);
  await page.getByRole('button', { name: /Paus/ }).click();
  const paused = asOfInUrl(page)!;
  await page.waitForTimeout(900);
  expect(asOfInUrl(page)).toBe(paused);
  await noLaterKnowledge(page, paused);
});

test('clicking a month in the branch index travels to that month end', async ({ page }) => {
  await page.goto(`gren/G6/#as_of=${TT_DAY}`, { waitUntil: 'networkidle' });
  const svg = page.locator('#tt-index svg[role="img"]');
  await svg.scrollIntoViewIfNeeded();
  const box = (await svg.boundingBox())!;
  await page.mouse.click(box.x + box.width * 0.25, box.y + box.height * 0.5);
  const d = asOfInUrl(page)!;
  expect(d < TT_DAY).toBe(true);
  expect(new Date(Date.parse(d) + 86_400_000).getUTCDate()).toBe(1);
  await noLaterKnowledge(page, d);
});

test('a page without a time-travel view says so instead of showing today under a past day', async ({ page }) => {
  await page.goto(`prognoser/#as_of=${TT_DAY}`);
  await expect(page.locator('h1')).toHaveText('Den här sidan har ingen tidsresa ännu');
  await expect(page.locator('.tt-today')).toHaveCount(0);
  await page.getByRole('button', { name: 'Visa sidan som i dag' }).click();
  await expect(page.locator('.tt-today h1')).toBeVisible();
});

test('today’s content never paints under a past date (before hydration it is hidden)', async ({ page }) => {
  await page.route('**/_app/immutable/**/*.js', (r) => r.abort()); // no hydration at all: only the head script runs
  await page.goto(`#as_of=${TT_DAY}`);
  await expect(page.locator('.tt-today')).toBeAttached();
  expect(await page.locator('.tt-today h1').first().evaluate((e) => getComputedStyle(e).visibility)).toBe('hidden');
  await page.unroute('**/_app/immutable/**/*.js');
  await page.goto('about:blank');
  await page.goto('');
  await expect(page.locator('.tt-today h1').first()).toBeVisible(); // without as_of nothing is hidden
});
