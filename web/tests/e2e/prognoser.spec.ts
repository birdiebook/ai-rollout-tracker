// W8: the forecast pages. Main model vs shadow and live vs backtest are always labelled, the small-n note is there,
// the charts are in the prerendered HTML, and every live forecast has its own page with a commit link.
import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';

type NC = { id: string; champion: string; forecasts?: { file: string; period: string | null }[]; backtest_calibration?: { available: boolean } | null };
const nc = (id: string) => JSON.parse(readFileSync(`static/data/nowcast/${id}.json`, 'utf-8')) as NC;
const ids = ['n1', 'n2', 'n3', 'n4', 'n5', 'n6'];
const card = (id: string) => `a.card:is([href$="/prognoser/${id}"], [href$="/prognoser/${id}/"])`;
const slug = (f: string) => (f.split('/').pop() ?? '').replace(/\.json$/, '').replace(/[^A-Za-z0-9_.-]/g, '_');

test('overview: calendar and one card per nowcast plus D2, linking to the detail pages', async ({ page }) => {
  await page.goto('prognoser/');
  await expect(page.locator('#kalender svg[role="img"]')).toBeVisible();
  for (const id of [...ids, 'd2']) await expect(page.locator(card(id))).toHaveCount(1);
  await expect(page.locator(card('d2'))).toContainText('Skugga');
  await page.locator(card('n2')).click();
  await expect(page.locator('h1')).toContainText('N2');
});

for (const id of ids) {
  test(`${id}: main model labelled, live calibration honest about n, backtest marked`, async ({ page }) => {
    const d = nc(id);
    await page.goto(`prognoser/${id}/`);
    await expect(page.locator('.tags [data-role="champion"]')).toContainText(d.champion);
    if (d.forecasts?.some((f) => /DF/.test(f.file))) await expect(page.locator('[data-role="shadow"]', { hasText: 'DF' })).toBeVisible();
    await expect(page.locator('.honest')).toContainText(/12/);
    if (d.backtest_calibration?.available) {
      await expect(page.locator('#bt-cov [data-status="backtest"]')).toBeVisible();
      await expect(page.locator('#bt-crps')).toContainText('n ');
    }
  });
}

test('N2 names B3 as main model, B1 as baseline and DF as shadow', async ({ page }) => {
  await page.goto('prognoser/n2/');
  await expect(page.locator('.tags [data-role="champion"]')).toContainText('B3');
  await expect(page.locator('.tags [data-role="baseline"]')).toContainText('B1');
  await expect(page.locator('.tags [data-role="shadow"]', { hasText: 'DF' })).toBeVisible();
});

test('D2 is a shadow', async ({ page }) => {
  await page.goto('prognoser/d2/');
  await expect(page.locator('.tags [data-role="shadow"]')).toContainText('D2');
});

const live = ids.flatMap((id) => (nc(id).forecasts ?? []).filter((f) => f.period).map((f) => ({ id, slug: slug(f.file), file: f.file })));
for (const f of live) {
  test(`live forecast page ${f.id}/${f.slug} has the commit link and the dots`, async ({ page }) => {
    await page.goto(`prognoser/${f.id}/${f.slug}/`);
    const link = page.getByRole('link', { name: /commit-historik/i });
    await expect(link).toHaveAttribute('href', new RegExp(`^https://github\\.com/.+/commits/main/${f.file.replace(/[.]/g, '\\.')}$`));
    await expect(page.locator('#dots circle.dot')).toHaveCount(20);
    await expect(page.locator('.tags [data-kind="skarp"]')).toBeVisible();
  });
}

test('forecast charts are in the prerendered HTML (no JS)', async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const page = await ctx.newPage();
  await page.goto('prognoser/n2/');
  await expect(page.locator('#over-time svg[role="img"]')).toBeAttached();
  await page.goto('prognoser/');
  await expect(page.locator('#kalender svg circle').first()).toBeAttached();
  await ctx.close();
});
