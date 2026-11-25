// WX2: the corrections after R-W2 (tables without JS, lazy tables, DOM budget, spark numbers, arrows, tooltip role)
// and R-W3 (reconstructed months marked at the heading, K6 without direction colour, stripes without a state,
// chance level and struck cards in "Om urvalet"). Data-driven, so it holds for fixtures and a real bundle.
import { readFileSync } from 'node:fs';
import { expect, test, type Page } from '@playwright/test';
import { TT_DAY } from './routes';

const index = JSON.parse(readFileSync('static/data/series/index.json', 'utf-8')) as { series: { key: string; freq?: string; n_versions?: number }[] };
const monthly = index.series.find((s) => s.freq === 'M') ?? index.series[0];
const overview = JSON.parse(readFileSync('static/data/overview.json', 'utf-8')) as {
  record: { status: string };
  stripes: { months: string[]; rows: { code: string; index: (number | null)[]; state?: (string | null)[] }[] };
};
const storyIndex = JSON.parse(readFileSync('static/data/story/index.json', 'utf-8')) as { months: { month: string; kind: string }[] };
type Story = { status: string; previous: string | null; cards: { id: string; type: string }[]; omitted_cards?: { id: string }[]; chance?: unknown };
const story = (m: string) => JSON.parse(readFileSync(`static/data/story/${m}.json`, 'utf-8')) as Story;
const reconMonth = storyIndex.months.find((m) => m.kind === 'rekonstruerad')?.month ?? null;
const liveMonth = storyIndex.months.find((m) => m.kind === 'skarp')?.month ?? null;
const k6Month = storyIndex.months.find((m) => story(m.month).cards.some((c) => c.type === 'K6'))?.month ?? null;

test.describe('without JavaScript', () => {
  test.use({ javaScriptEnabled: false });

  test('a small table opens natively and a large one links its data (R-W2 B1)', async ({ page, request }) => {
    await page.goto(`serie/${monthly.key}/`);
    const small = page.locator('details.tbl[data-pre]').first();
    if (await small.count()) {
      await small.locator('summary').click();
      await expect(small.locator('table')).toBeVisible();
    }
    const large = page.locator('details.tbl:not([data-pre])').first();
    await large.locator('summary').click();
    await expect(large.locator('.nojs')).toBeVisible();
    const href = await large.locator('a').getAttribute('href');
    expect(href).toMatch(/data\/series\/.+\.json$/);
    const url = new URL(href!, page.url());
    expect((await request.get(url.pathname)).status()).toBe(200);
  });

  for (const path of ['', 'gren/G6/', `serie/${monthly.key}/`, 'metod/', ...(liveMonth ? [`manad/${liveMonth}/`] : [])]) {
    test(`DOM budget and the charts are drawn: ${path || 'start'}`, async ({ page }) => {
      await page.goto(path);
      const n = await page.evaluate(() => document.getElementsByTagName('*').length);
      expect(n).toBeLessThanOrEqual(3000); // budget.mjs domElements
      // every chart is in the prerendered HTML, drawn (the deferred bodies are real markup)
      const empty = await page.locator('figure svg[role="img"]').evaluateAll((s) => s.filter((x) => x.children.length === 0).length);
      expect(empty).toBe(0);
    });
  }
});

test('a large table is drawn when it is opened (R-W2 P1)', async ({ page }) => {
  await page.goto(`serie/${monthly.key}/`, { waitUntil: 'networkidle' });
  await expect(page.locator('#level-table tbody tr')).toHaveCount(0);
  await page.locator('#level summary').click();
  expect(await page.locator('#level-table tbody tr').count()).toBeGreaterThan(0);
});

test('charts are drawn live after load, and the hover tip is not a live region (R-W2)', async ({ page }) => {
  await page.goto('', { waitUntil: 'networkidle' });
  await expect.poll(() => page.locator('figure.chart svg[role="img"]:not([data-live])').count()).toBe(0);
  const cell = page.locator('#stripes-chart rect.cell').first();
  await cell.hover();
  await expect(page.locator('#stripes .tip')).toBeVisible();
  expect(await page.locator('.tip[role]').count()).toBe(0);
});

async function linkNames(page: Page): Promise<string[]> {
  return page.locator('main a').evaluateAll((as) =>
    as.map((a) => {
      const c = a.cloneNode(true) as HTMLElement;
      c.querySelectorAll('[aria-hidden="true"]').forEach((x) => x.remove());
      return (a.getAttribute('aria-label') ?? c.textContent ?? '').trim();
    })
  );
}

for (const path of ['', ...(liveMonth ? [`manad/${liveMonth}/`] : []), 'gren/G6/']) {
  test(`no arrow is read in a link name: ${path || 'start'}`, async ({ page }) => {
    await page.goto(path, { waitUntil: 'networkidle' });
    const bad = (await linkNames(page)).filter((t) => /[→←↑↓]/.test(t));
    expect(bad).toEqual([]);
  });
}

test('start page: a reconstructed record is marked at the heading, a live one is not (R-W3)', async ({ page }) => {
  await page.goto('', { waitUntil: 'networkidle' });
  if (overview.record.status === 'live') {
    await expect(page.locator('[data-testid="recon-note"]')).toHaveCount(0);
    await expect(page.locator('.hero .badge')).toHaveAttribute('data-status', 'live');
  } else {
    await expect(page.locator('.hero .badge.prominent[data-status="recon"]')).toContainText('Rekonstruerat läge');
    await expect(page.locator('[data-testid="recon-note"]')).toBeVisible();
  }
});

test('month page: the status is in the heading of a reconstructed month (R-W3)', async ({ page }) => {
  test.skip(!reconMonth, 'no reconstructed month');
  await page.goto(`manad/${reconMonth}/`, { waitUntil: 'networkidle' });
  await expect(page.locator('h1 .h1-status')).toHaveText('rekonstruerad');
  await expect(page.locator('[data-testid="recon-note"]')).toBeVisible();
  if (liveMonth) {
    await page.goto(`manad/${liveMonth}/`, { waitUntil: 'networkidle' });
    await expect(page.locator('h1 .h1-status')).toHaveCount(0);
  }
});

test('month page: a reconciliation card has no direction colour (R-W3, A5)', async ({ page }) => {
  test.skip(!k6Month, 'no K6 card');
  await page.goto(`manad/${k6Month}/`, { waitUntil: 'networkidle' });
  const tag = page.locator('.step[data-type="K6"] .tag').first();
  const style = (await tag.getAttribute('style')) ?? '';
  expect(style).toContain('var(--c-ink)');
  expect(style).not.toMatch(/--c-acc|--c-brk/);
  await expect(tag).toContainText(/kvotens takt (högt|lågt) i egen historik/);
});

test('month page: "Om urvalet" lists the struck cards and the chance level (R-W3b, c)', async ({ page }) => {
  const m = storyIndex.months.at(-1)!.month;
  const s = story(m);
  await page.goto(`manad/${m}/`, { waitUntil: 'networkidle' });
  await expect(page.locator('.struck li')).toHaveCount(s.omitted_cards?.length ?? 0);
  await expect(page.locator('[data-testid="chance"]')).toHaveCount(s.previous && s.chance ? 1 : 0);
  if (s.previous && s.chance) await expect(page.locator('[data-testid="chance"]')).toContainText('av en slump');
});

test('stripes: a month without a state gets no direction colour (R-W3)', async ({ page }) => {
  await page.goto('', { waitUntil: 'networkidle' });
  const few = overview.stripes.rows.flatMap((r) => r.index.map((v, i) => (v !== null && ['för få serier', 'inga registrerade kärnserier'].includes(r.state?.[i] ?? '') ? 1 : 0))).reduce<number>((a, b) => a + b, 0);
  await expect(page.locator('#stripes-chart rect.cell[data-few]')).toHaveCount(few);
  const fills = await page.locator('#stripes-chart rect.cell[data-few]').evaluateAll((rs) => rs.map((r) => (r as SVGElement).style.fill));
  expect(fills.every((f) => f === 'transparent')).toBe(true);
});

test('time travel, branch page: every spark has numbers in its name and a shared table (R-W2 B2)', async ({ page }) => {
  await page.goto(`gren/G6/#as_of=${TT_DAY}`, { waitUntil: 'networkidle' });
  const sparks = page.locator('[data-tt="asof"] .card svg[role="img"]');
  const n = await sparks.count();
  test.skip(n === 0, 'no measured series that day');
  const names = await sparks.evaluateAll((s) => s.map((x) => x.getAttribute('aria-label') ?? ''));
  expect(names.every((t) => /lägst .+, högst .+, senast /.test(t) && /Riktningen bytte \d+/.test(t)) || names.every((t) => /inga mått/.test(t))).toBe(true);
  await page.locator('[data-tt="spark-table"] summary').click();
  await expect(page.locator('[data-tt="spark-table"] table thead th')).toHaveCount(n + 1);
});
