// W14 quarterly report end to end: the six sections with their figures (SVG without JavaScript), the reconstructed
// label, the chain L1–L9, links into the time-travel views at the report day, the entry from the start page, and the
// report under global time travel (shown only when it was known on the day).
import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';

interface Idx { latest: string; first_live: string; quarters: { quarter: string; quarter_sv: string; known: string; kind: string }[] }
const index = JSON.parse(readFileSync('static/data/report/index.json', 'utf-8')) as Idx;
const doc = JSON.parse(readFileSync(`static/data/report/${index.latest}.json`, 'utf-8')) as {
  quarter: string; quarter_sv: string; known: string; status: string; headline: string; ratios: { key: string }[]; nowcasts: { id: string }[];
};
const dayBefore = (d: string) => new Date(Date.parse(d) - 86400000).toISOString().slice(0, 10);

test('six sections, the headline from the data and the record status', async ({ page }) => {
  await page.goto(`kvartal/${doc.quarter}/`);
  const rp = page.locator('article.report');
  await expect(rp).toHaveAttribute('data-known', doc.known);
  await expect(page.locator('h1')).toContainText(doc.quarter_sv.replace(/^./, (c) => c.toUpperCase()));
  await expect(page.locator('.report .lede')).toHaveText(doc.headline);
  expect(await page.locator('section.sec').evaluateAll((els) => els.map((e) => e.id))).toEqual(['lage', 'kedjan', 'floden', 'prognoser', 'regim', 'data']);
  await expect(page.locator('[data-recon]')).toHaveCount(doc.status === 'reconstructed' ? 1 : 0);
  await expect(page.locator('li.lead')).toHaveCount(9);
  await expect(page.locator('[data-ratio]')).toHaveCount(doc.ratios.length);
  await expect(page.locator('[data-nowcast]')).toHaveCount(doc.nowcasts.length);
});

test('works without JavaScript: the figures are prerendered SVG', async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const page = await ctx.newPage();
  await page.goto(`kvartal/${doc.quarter}/`);
  await expect(page.locator('#lage svg').first()).toBeVisible();
  expect(await page.locator('#kedjan svg').count()).toBeGreaterThanOrEqual(9);
  if (doc.ratios.length) expect(await page.locator('#floden svg').count()).toBeGreaterThan(0);
  // without JS the links open today's views (time travel needs JS)
  for (const href of await page.locator('.report a.bname').evaluateAll((els) => els.map((e) => e.getAttribute('href') ?? ''))) expect(href).not.toContain('as_of');
  await ctx.close();
});

test('links into time-travel views carry the report day', async ({ page }) => {
  await page.goto(`kvartal/${doc.quarter}/`);
  await page.waitForFunction(() => document.querySelector('.essay.enhanced') !== null);
  const a = page.locator('#kedjan a.bname').first();
  await expect(a).toHaveAttribute('href', new RegExp(`#as_of=${doc.known}$`));
  await a.click();
  await expect(page).toHaveURL(new RegExp(`/gren/G\\d/#as_of=${doc.known}$`));
  await expect(page.locator('[data-tt="view"]')).toBeVisible();
});

test('the rail marks the section in view', async ({ page }, info) => {
  test.skip(info.project.name === 'mobile', 'the rail is shown on wide screens');
  await page.goto(`kvartal/${doc.quarter}/`);
  await page.waitForFunction(() => document.querySelector('.essay.enhanced') !== null);
  await page.locator('#regim').scrollIntoViewIfNeeded();
  await page.locator('#regim h2').evaluate((e) => e.scrollIntoView({ block: 'center' }));
  await expect(page.locator('nav.rail a[aria-current="step"]')).toHaveAttribute('href', '#regim');
});

test('the start page leads to the latest report', async ({ page }) => {
  await page.goto('');
  await page.locator('.report-entry a').click();
  await expect(page).toHaveURL(new RegExp(`/kvartal/${doc.quarter}/$`));
  await expect(page.locator('article.report')).toBeVisible();
});

test('time travel: the report only on or after its report day', async ({ page }) => {
  await page.goto(`kvartal/${doc.quarter}/#as_of=${dayBefore(doc.known)}`);
  await expect(page.locator('[data-tt="report-unknown"]')).toBeVisible();
  const prev = index.quarters.filter((q) => q.known <= dayBefore(doc.known)).at(-1);
  if (prev) await expect(page.locator('[data-tt="report-unknown"] a')).toHaveAttribute('href', new RegExp(`/kvartal/${prev.quarter}/?(#.*)?$`));
  await page.goto(`kvartal/${doc.quarter}/#as_of=${doc.known}`);
  const view = page.locator('[data-tt="view"] article.report');
  await expect(view).toBeVisible();
  await expect(view).toHaveAttribute('data-known', doc.known);
  // the quarter list under time travel names only the quarters known that day
  const listed = await page.locator('[data-tt="view"] .qlist a').evaluateAll((els) => els.map((e) => e.textContent?.trim()));
  expect(listed).toEqual([...index.quarters].filter((q) => q.known <= doc.known).reverse().map((q) => q.quarter_sv));
});
