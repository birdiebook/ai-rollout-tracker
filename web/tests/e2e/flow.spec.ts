// W6: the chain, lead pages and branch pages (works against fixtures and a real bundle).
import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';

const doc = (p: string) => JSON.parse(readFileSync(`static/data/${p}`, 'utf-8'));

test('chain: nine leads in order, each linking to its lead page', async ({ page }) => {
  await page.goto('flode/');
  const rows = page.locator('ol.chain > li.lead');
  await expect(rows).toHaveCount(9);
  for (let i = 1; i <= 9; i++) await expect(rows.nth(i - 1).locator('h2 a')).toHaveAttribute('href', new RegExp(`/flode/L${i}/?$`));
  await rows.nth(5).locator('h2 a').click();
  await expect(page.locator('h1')).toContainText('L6');
  await expect(page.getByRole('navigation', { name: 'Kedjan L1–L9' }).locator('[aria-current="page"]')).toHaveCount(1);
});

test('lead page: minimap marks the lead, up- and downstream links', async ({ page }) => {
  await page.goto('flode/L6/');
  const map = page.getByRole('navigation', { name: 'Kedjan L1–L9' });
  await expect(map.getByRole('link')).toHaveCount(9);
  await expect(map.locator('a[aria-current="page"]')).toHaveAttribute('href', /\/flode\/L6\/?$/);
  const updown = page.getByRole('navigation', { name: 'Uppströms och nedströms' });
  await expect(updown.getByRole('link', { name: /L5/ })).toBeVisible();
  await expect(updown.getByRole('link', { name: /L7/ })).toBeVisible();
});

test('branch page: minimap, index chart, unit boxes point at the cards, cards link to the series', async ({ page }) => {
  await page.goto('gren/G6/');
  await expect(page.getByRole('navigation', { name: 'Kedjan L1–L9' }).locator('a[aria-current="location"]')).toHaveCount(1);
  await expect(page.locator('#index svg[role="img"] circle.dot').first()).toBeAttached();
  const g6 = doc('branch/G6.json');
  await expect(page.locator('article.sm')).toHaveCount(g6.counted.length + g6.not_counted.length);
  for (const a of await page.locator('ul.units a.unit:not(.held)').all()) {
    const href = (await a.getAttribute('href'))!;
    await expect(page.locator(href)).toHaveCount(1);
  }
  await expect(page.locator('article.sm a.open').first()).toHaveAttribute('href', /\/serie\/[^/]+\/?$/);
});

test('branch page: the pace/level switch redraws all multiples', async ({ page }) => {
  await page.goto('gren/G6/');
  await page.waitForLoadState('networkidle');
  const group = page.getByRole('group', { name: /Räknade serier/ });
  const before = await page.locator('article.sm svg').first().innerHTML();
  await group.getByRole('button', { name: 'Nivå' }).click();
  await expect(group.getByRole('button', { name: 'Nivå' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('.multiples').first()).toHaveAttribute('data-mode', 'level');
  expect(await page.locator('article.sm svg').first().innerHTML()).not.toBe(before);
});

test('withheld series are named boxes without values or direction', async ({ page }) => {
  const g9 = doc('branch/G9.json');
  test.skip(!g9.withheld.length, 'no withheld series in this bundle');
  await page.goto('gren/G9/');
  const boxes = page.locator('#inhallna li.box');
  await expect(boxes).toHaveCount(g9.withheld.length);
  for (const w of g9.withheld) await expect(page.locator('#inhallna')).toContainText(w.label);
  const held = page.locator('ul.units a.unit.held');
  await expect(held).toHaveCount(g9.n_withheld_counted);
  for (const h of await held.all()) {
    expect((await h.textContent())?.trim()).toBe('');
    expect(await h.getAttribute('aria-label')).not.toMatch(/ökar|minskar|oförändrad/);
  }
});

test('lead and branch pages are prerendered (SVG without JS)', async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const page = await ctx.newPage();
  await page.goto('gren/G6/');
  expect(await page.locator('figure svg[role="img"]').count()).toBeGreaterThanOrEqual(2);
  await page.goto('flode/L6/');
  expect(await page.locator('figure svg[role="img"]').count()).toBeGreaterThanOrEqual(2);
  await ctx.close();
});
