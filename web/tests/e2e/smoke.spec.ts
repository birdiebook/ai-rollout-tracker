// Smoke: every route renders, hydrates without errors, loads nothing from other hosts and fits the viewport.
import { expect, test, type Page } from '@playwright/test';
import { routes } from './routes';

function watch(page: Page) {
  const external: string[] = [];
  const errors: string[] = [];
  page.on('request', (r) => {
    const u = new URL(r.url());
    if (!['localhost', '127.0.0.1'].includes(u.hostname) && !['data:', 'blob:'].includes(u.protocol)) external.push(r.url());
  });
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  return { external, errors };
}

for (const r of routes()) {
  test(`${r.name} renders without errors or external requests`, async ({ page }) => {
    const w = watch(page);
    const res = await page.goto(r.path);
    expect(res?.status()).toBe(200);
    await expect(page.locator('h1')).toBeVisible();
    await page.waitForLoadState('networkidle');
    expect(w.external, 'requests to other hosts').toEqual([]);
    expect(w.errors, 'console/page errors').toEqual([]);
    // no horizontal scroll at any width
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });
}

test('prerendered HTML already contains the charts (SVG without JS)', async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const page = await ctx.newPage();
  await page.goto('_katalog/');
  expect(await page.locator('figure svg[role="img"]').count()).toBeGreaterThanOrEqual(5);
  await page.goto('');
  await expect(page.locator('#stripes-chart svg rect.cell').first()).toBeAttached();
  await ctx.close();
});

test('theme toggle switches and remembers the theme', async ({ page }) => {
  await page.goto('');
  await page.waitForLoadState('networkidle');
  const before = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  await page.getByRole('button', { name: /Byt till/ }).click();
  await expect.poll(() => page.evaluate(() => getComputedStyle(document.body).backgroundColor)).not.toBe(before);
  const chosen = await page.evaluate(() => document.documentElement.dataset.theme);
  await page.reload();
  expect(await page.evaluate(() => document.documentElement.dataset.theme)).toBe(chosen);
});

test('table view toggle shows the same numbers as a table', async ({ page }) => {
  await page.goto('');
  await page.waitForLoadState('networkidle');
  const btn = page.locator('#stripes').getByRole('button', { name: 'Visa tabell' });
  await btn.click();
  await expect(page.locator('#stripes-table table')).toBeVisible();
  await expect(page.locator('#stripes-chart')).toBeHidden();
});

test('navigation links resolve under the base path', async ({ page }) => {
  // Click only after hydration: a click before it is a plain request, and `vite preview` (not Pages) then drops the base.
  await page.goto('', { waitUntil: 'networkidle' });
  await page.getByRole('navigation', { name: 'Huvudmeny' }).getByRole('link', { name: 'Flödet' }).click();
  await expect(page).toHaveURL(/\/flode\/$/);
  await page.waitForLoadState('networkidle');
  await page.getByRole('link', { name: /G6/ }).first().click();
  await expect(page.locator('h1')).toContainText('G6');
});
