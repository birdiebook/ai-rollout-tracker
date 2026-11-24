// W12: search (⌘K / Ctrl+K and the button, ARIA combobox), deep links to sections in the hash, share tags with a
// generated image per page, the citation line, the chain's links to the leads, and the header on mobile.
import { readFileSync } from 'node:fs';
import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { routes } from './routes';

const idx = JSON.parse(readFileSync('static/data/series/index.json', 'utf-8')) as { series: { key: string; label: string }[] };
const serie = idx.series.find((s) => s.key === 'us_ip_semis_m') ?? idx.series[0];

async function ready(page: Page, path: string) {
  // act only after hydration: the search button replaces its no-JS link then
  await page.goto(path, { waitUntil: 'networkidle' });
  await expect(page.locator('header button.sbtn')).toBeVisible();
}

async function openSearch(page: Page, how: 'key' | 'click') {
  if (how === 'click') await page.locator('header button.sbtn').click();
  else await page.keyboard.press('ControlOrMeta+k');
  const dlg = page.getByRole('dialog', { name: 'Sök' });
  await expect(dlg).toBeVisible();
  const box = dlg.getByRole('combobox');
  await expect(box).toBeFocused();
  // the index is loaded on open
  await expect(dlg.getByRole('status')).not.toHaveText(/Laddar/);
  return { dlg, box };
}

test('Ctrl/⌘+K opens the search, the index loads only then, keyboard picks a series', async ({ page }) => {
  const requested: string[] = [];
  page.on('request', (r) => requested.push(new URL(r.url()).pathname));
  await ready(page, '');
  expect(requested.some((p) => p.endsWith('/sok.json'))).toBe(false);
  const { dlg, box } = await openSearch(page, 'key');
  expect(requested.some((p) => p.endsWith('/sok.json'))).toBe(true);
  // suggestions before typing
  await expect(box).toHaveAttribute('aria-expanded', 'true');
  await expect(dlg.getByRole('option').first()).toBeVisible();
  await box.fill(serie.key);
  const first = dlg.getByRole('option').first();
  await expect(first).toHaveAttribute('aria-selected', 'true');
  await expect(box).toHaveAttribute('aria-activedescendant', (await first.getAttribute('id')) as string);
  await expect(first).toContainText('Serie');
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(new RegExp(`/serie/${serie.key}/$`));
  await expect(dlg).toBeHidden();
});

test('the button opens the search; arrows move, Escape clears then closes and focus returns', async ({ page }) => {
  await ready(page, 'flode/');
  const btn = page.locator('header button.sbtn');
  const { dlg, box } = await openSearch(page, 'click');
  await box.fill('G6');
  await expect(dlg.getByRole('option').first()).toContainText('G6');
  await page.keyboard.press('ArrowDown');
  await expect(box).toHaveAttribute('aria-activedescendant', /-opt-1$/);
  await page.keyboard.press('ArrowUp');
  await expect(box).toHaveAttribute('aria-activedescendant', /-opt-0$/);
  await page.keyboard.press('Escape');
  await expect(box).toHaveValue('');
  await expect(dlg).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(dlg).toBeHidden();
  await expect(btn).toBeFocused();
  // reopen and go to a branch by code
  await openSearch(page, 'key');
  await page.keyboard.type('g6');
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/gren\/G6\/$/);
  await expect(page.locator('h1')).toContainText('G6');
});

test('accents are optional and a query with no hits says so', async ({ page }) => {
  await ready(page, '');
  const { dlg, box } = await openSearch(page, 'key');
  await box.fill('flodet');
  await expect(dlg.getByRole('option').first()).toContainText('Flödet');
  await box.fill('qqqzzz');
  await expect(dlg.getByRole('option')).toHaveCount(0);
  await expect(box).toHaveAttribute('aria-expanded', 'false');
  await expect(dlg.getByRole('status')).toContainText('Inga träffar');
});

for (const scheme of ['light', 'dark'] as const) {
  test(`axe with the search dialog open (${scheme})`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: scheme });
    await ready(page, '');
    const { box } = await openSearch(page, 'key');
    await box.fill('halv');
    const res = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze();
    expect(res.violations.map((v) => `${v.id}: ${v.nodes[0]?.target.join(' ')}`)).toEqual([]);
  });
}

test('the search page works without JavaScript and filters with it', async ({ browser, page }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const nojs = await ctx.newPage();
  await nojs.goto('');
  // before hydration the header search is a link to the search page
  await expect(nojs.locator('header a.sbtn')).toHaveAttribute('href', /\/sok\/?$/);
  await nojs.goto('sok/');
  await expect(nojs.locator(`.register a[href$="/serie/${serie.key}"]`)).toHaveCount(1);
  await ctx.close();

  await ready(page, `sok/#q=${encodeURIComponent('G6')}`);
  const box = page.getByRole('combobox');
  await expect(box).toHaveValue('G6');
  await expect(page.getByRole('option').first()).toContainText('G6');
  await box.fill('flode');
  await expect(page).toHaveURL(/#q=flode$/);
});

test('every page has its share tags, a generated PNG and one description', async ({ page, request }) => {
  for (const r of routes()) {
    await page.goto(r.path);
    const meta = (sel: string) => page.locator(sel).getAttribute('content');
    expect(await page.locator('meta[name="description"]').count(), r.name).toBe(1);
    expect(await page.locator('title').count(), r.name).toBe(1);
    expect(await meta('meta[name="twitter:card"]')).toBe('summary_large_image');
    const title = await meta('meta[property="og:title"]');
    expect(title?.length, r.name).toBeGreaterThan(3);
    const img = (await meta('meta[property="og:image"]')) as string;
    const url = (await meta('meta[property="og:url"]')) as string;
    expect(img).toMatch(/^https:\/\/.+\/og\/.+\.png$/);
    expect(url.endsWith('/' + r.path)).toBe(true);
    // the image exists in this build: same path below the base
    const local = new URL(img).pathname.replace(/^.*?\/og\//, 'og/');
    const res = await request.get(local);
    expect(res.status(), local).toBe(200);
    const body = await res.body();
    expect(body.subarray(1, 4).toString()).toBe('PNG');
    expect(body.readUInt32BE(16)).toBe(1200);
    expect(body.readUInt32BE(20)).toBe(630);
    expect(body.length).toBeLessThan(120 * 1024);
  }
});

test('the citation names the series, the version date and the permalink, and copies', async ({ page, context, baseURL }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await ready(page, `serie/${serie.key}/`);
  const cite = page.locator('#cite-text');
  await expect(cite).toContainText(`AI-utrullningen, serie ${serie.label} (${serie.key}; källa: `);
  await expect(cite).toContainText(/version per \d{4}-\d{2}-\d{2}/);
  await expect(cite).toContainText(`${baseURL}serie/${serie.key}/`);
  // the view state in the hash is part of the permalink, and as_of becomes the version date
  await page.evaluate(() => (location.hash = '#as_of=2024-06-30'));
  await expect(cite).toContainText('version per 2024-06-30');
  await expect(cite).toContainText('#as_of=2024-06-30');
  await page.getByRole('button', { name: 'Kopiera citeringen' }).click();
  await expect(page.locator('.share [role="status"]')).toContainText(/kopierad|Kopiera för hand/);
  const clip = await page.evaluate(() => navigator.clipboard.readText().catch(() => ''));
  if (clip) expect(clip).toContain(`(${serie.key}; källa:`);
});

test('sections are deep-linkable in the hash next to the view state', async ({ page }) => {
  await ready(page, `serie/${serie.key}/#fonster=5&avsnitt=rev-h`);
  await expect(page.locator('#rev-h')).toBeInViewport();
  await expect(page.locator('#rev-h')).toBeFocused();
  // the series page kept its own state and our key
  await expect(page).toHaveURL(/#fonster=5&avsnitt=rev-h$/);
  // the section list links keep the state too
  const link = page.locator('.share nav').getByRole('link', { name: 'Om serien' });
  await expect(link).toHaveAttribute('href', '#fonster=5&avsnitt=about-h');
  await link.click();
  await expect(page.locator('#about-h')).toBeInViewport();
  await expect(page).toHaveURL(/#fonster=5&avsnitt=about-h$/);
  // the page's headings are left as they are
  await expect(page.locator('#rev-h a')).toHaveCount(0);
});

test('a plain anchor and a section on a branch page scroll there', async ({ page }) => {
  await ready(page, 'gren/G6/#avsnitt=counted-h');
  await expect(page.locator('#counted-h')).toBeInViewport();
  await ready(page, 'flode/L6/#ks-h');
  await expect(page.locator('#ks-h')).toBeInViewport();
});

test('the chain on the start page links each lead to its own page', async ({ page }, info) => {
  await page.goto('');
  if (info.project.name === 'mobile') {
    const row = page.locator('ol.list li[data-lead="L3"]');
    await row.locator('summary').click();
    await expect(row.getByRole('link', { name: /L3 i flödet/ })).toHaveAttribute('href', /\/flode\/L3\/?$/);
  } else {
    const hrefs = await page.locator('ol.spine a.name').evaluateAll((as) => as.map((a) => a.getAttribute('href')));
    expect(hrefs.map((h) => h?.replace(/^.*\/flode\//, '').replace(/\/$/, ''))).toEqual(['L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8', 'L9']);
  }
});

test('the header fits: brand, menu, search and theme reachable without overflow', async ({ page }, info) => {
  await ready(page, `serie/${serie.key}/`);
  const header = page.locator('header.top');
  const box = await header.boundingBox();
  const vw = page.viewportSize()?.width ?? 0;
  for (const el of [header.locator('.brand'), header.getByRole('navigation', { name: 'Huvudmeny' }), header.locator('button.sbtn'), header.getByRole('button', { name: /Byt till/ })]) {
    const b = await el.boundingBox();
    expect(b).not.toBeNull();
    expect((b?.x ?? 0) + (b?.width ?? 0)).toBeLessThanOrEqual(vw);
  }
  // targets at least 24 px (WCAG 2.2 target size), current page marked
  for (const a of await header.locator('nav a').all()) expect((await a.boundingBox())?.height ?? 0).toBeGreaterThanOrEqual(24);
  await expect(header.locator('nav a[aria-current="page"]')).toHaveText('Flödet');
  if (info.project.name === 'mobile') expect(box?.height ?? 0).toBeLessThan(140);
  else expect(box?.height ?? 0).toBeLessThan(80);
});
