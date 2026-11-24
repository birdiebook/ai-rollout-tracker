// Start page (W5): headline from the data, the chain L1→L9 in both layouts, three question cards, stripes with the
// record status, and the ways on. Runs against whatever bundle the build used (fixtures or a real one).
import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';

const ov = JSON.parse(readFileSync('static/data/overview.json', 'utf-8')) as {
  headline: { sentence: string };
  record: { status: string };
  stripes: { months: string[]; kind: string[] };
  branches: { code: string }[];
};

test('the headline is the sentence generated from the data', async ({ page }) => {
  await page.goto('');
  await expect(page.locator('h1')).toHaveText(ov.headline.sentence);
  await expect(page.getByTestId('chain-sentence')).toHaveText(/^I kedjan: .+\.$/);
  // the record status sits next to the headline
  await expect(page.locator('.hero .badge')).toHaveAttribute('data-status', ov.record.status === 'live' ? 'live' : 'recon');
});

test('the chain shows L1–L9 in the layout that fits the viewport', async ({ page }, info) => {
  await page.goto('');
  const spine = page.locator('ol.spine');
  const list = page.locator('ol.list');
  if (info.project.name === 'mobile') {
    await expect(spine).toBeHidden();
    await expect(list.locator('> li')).toHaveCount(9);
    // a row opens into the full node with units, sparkline and links
    const row = list.locator('li[data-lead="L6"]');
    await row.locator('summary').click();
    await expect(row.locator('.br svg[role="img"]').first()).toBeVisible();
    await expect(row.getByRole('link', { name: /L6 i flödet/ })).toBeVisible();
  } else {
    await expect(list).toBeHidden();
    await expect(spine.locator('> li')).toHaveCount(9);
    const codes = await spine.locator('> li').evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.lead));
    expect(codes).toEqual(['L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8', 'L9']);
    // one row of nine at desktop width
    const tops = await spine.locator('> li').evaluateAll((els) => new Set(els.map((e) => Math.round(e.getBoundingClientRect().top))).size);
    expect(tops).toBe(1);
  }
});

test('a branch in the chain leads to its page', async ({ page }, info) => {
  await page.goto('');
  await page.waitForLoadState('networkidle');
  const scope = info.project.name === 'mobile' ? page.locator('ol.list li[data-lead="L6"]') : page.locator('ol.spine');
  if (info.project.name === 'mobile') await scope.locator('summary').click();
  await scope.getByRole('link', { name: /^G6 / }).first().click();
  await expect(page).toHaveURL(/\/gren\/G6\/$/);
});

test('three question cards, each with pictures and generated answers', async ({ page }) => {
  await page.goto('');
  const cards = page.locator('article[data-question]');
  await expect(cards).toHaveCount(3);
  await expect(cards.nth(0).getByRole('heading', { level: 2 })).toHaveText('Var står vi nu?');
  await expect(cards.nth(1).getByRole('heading', { level: 2 })).toHaveText('Vart är vi på väg?');
  await expect(cards.nth(2).getByRole('heading', { level: 2 })).toHaveText('Har något fundamentalt ändrats?');
  // Q1: one row per branch with a dot
  await expect(page.locator('#now svg g.row')).toHaveCount(ov.branches.length);
  // Q2: the calendar is a timeline, the backtest is always labelled as such
  await expect(page.locator('#calendar svg[role="img"]')).toBeVisible();
  const cal = page.locator('#calibration');
  if (await cal.count()) await expect(cal.locator('.badge')).toHaveAttribute('data-status', 'backtest');
  // Q3: reconciliations as percentile rows
  expect(await page.locator('[data-recon]').count()).toBeGreaterThan(0);
});

test('the stripes mark reconstructed and live months', async ({ page }) => {
  await page.goto('');
  const live = ov.stripes.kind.filter((k) => k === 'skarp').length;
  const cells = page.locator('#stripes-chart rect.cell');
  await expect(cells).toHaveCount(ov.stripes.months.length * ov.branches.length);
  await expect(page.locator('#stripes-chart rect.cell[data-status="live"]')).toHaveCount(live * ov.branches.length);
  await expect(page.locator('#stripes-chart line[data-status="recon"]')).toHaveCount(live === ov.stripes.months.length ? 0 : 1);
  if (live) await expect(page.locator('#stripes-chart line[data-status="live"]')).not.toHaveCount(0);
});

test('the pictures are in the prerendered HTML (no JS needed)', async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const page = await ctx.newPage();
  await page.goto('');
  expect(await page.locator('ol.spine .br svg[role="img"]').count()).toBeGreaterThanOrEqual(9);
  await expect(page.locator('#now svg circle').first()).toBeAttached();
  await expect(page.locator('#calendar svg circle').first()).toBeAttached();
  await ctx.close();
});

test('neutral wording: no alarm words on the page', async ({ page }) => {
  await page.goto('');
  const text = (await page.locator('main').innerText()).toLowerCase();
  for (const w of ['oroande', 'larm', 'varning', 'alarm', 'kris', 'bra nyhet', 'dåliga nyheter']) expect(text).not.toContain(w);
});
