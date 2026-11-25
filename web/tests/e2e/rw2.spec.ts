// R-W2 (accessibility and performance review, docs/granskning/rw2_tillganglighet.md): the fixes made in the review.
import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

const idx = JSON.parse(readFileSync('static/data/series/index.json', 'utf-8')) as { series: { key: string; freq?: string | null; n_versions?: number }[] };
const monthly = [...idx.series].filter((s) => s.freq === 'M').sort((a, b) => (b.n_versions ?? 0) - (a.n_versions ?? 0))[0] ?? idx.series[0];
const TT = '2026-03-15';

test('skip link moves focus to main and keeps the view state in the hash', async ({ page }) => {
  await page.goto(`serie/${monthly.key}/#fonster=5`, { waitUntil: 'networkidle' });
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Hoppa till innehållet' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('main#main')).toBeFocused();
  expect(new URL(page.url()).hash).toBe('#fonster=5');
  await page.keyboard.press('Tab');
  expect(await page.evaluate(() => !!document.activeElement?.closest('main'))).toBe(true);
});

test('time travel keeps keyboard focus when it starts and ends', async ({ page }) => {
  await page.goto('gren/G6/', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: /Tidsresa: vad visste vi den/ }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('slider', { name: 'Datum för tidsresan' })).toBeFocused();
  await page.getByRole('button', { name: 'I dag' }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('button', { name: /Tidsresa: vad visste vi den/ })).toBeFocused();
  // the play button: no aria-pressed (its name says what it does), the glyph is not part of the name
  await page.goto(`gren/G6/#as_of=${TT}`, { waitUntil: 'networkidle' });
  const play = page.getByRole('button', { name: 'Spela', exact: true });
  await expect(play).toBeVisible();
  expect(await play.getAttribute('aria-pressed')).toBeNull();
});

test('the sticky time bar never covers the focused element (WCAG 2.4.11)', async ({ page }, info) => {
  test.skip(info.project.name !== 'desktop', 'the bar is sticky from 861 px');
  await page.goto(`gren/G6/#as_of=${TT}`, { waitUntil: 'networkidle' });
  await page.locator('[data-tt="view"]').waitFor();
  for (let i = 0; i < 50; i++) await page.keyboard.press('Tab');
  let covered = 0;
  for (let i = 0; i < 35; i++) {
    await page.keyboard.press('Shift+Tab');
    covered += await page.evaluate(() => {
      const a = document.activeElement as HTMLElement | null;
      const bar = document.querySelector('.bar.on');
      if (!a || a === document.body || !bar || bar.contains(a) || a.closest('header.top')) return 0;
      const r = a.getBoundingClientRect();
      const b = bar.getBoundingClientRect();
      return r.top < b.bottom - 1 && r.bottom > b.top ? 1 : 0;
    });
  }
  expect(covered).toBe(0);
});

test('no single-character shortcut opens the search (WCAG 2.1.4); Ctrl+K does', async ({ page }) => {
  await page.goto('', { waitUntil: 'networkidle' });
  await page.keyboard.press('/');
  await page.waitForTimeout(300);
  await expect(page.locator('dialog[open]')).toHaveCount(0);
  await page.keyboard.press('ControlOrMeta+k');
  await expect(page.locator('dialog[open] input')).toBeFocused();
});

test('the table view is a native disclosure that keeps its name (WX2: <details>, no aria-pressed)', async ({ page }) => {
  await page.goto(`serie/${monthly.key}/`, { waitUntil: 'networkidle' });
  const d = page.locator('#level details.tbl');
  const s = d.locator('summary');
  const name = await s.innerText();
  expect(await s.getAttribute('aria-pressed')).toBeNull();
  await s.click();
  await expect(d).toHaveAttribute('open', '');
  await expect(page.locator('#level-table table')).toBeVisible();
  expect(await s.innerText()).toBe(name);
});

test('heading levels do not skip on the forecast overview', async ({ page }) => {
  await page.goto('prognoser/', { waitUntil: 'networkidle' });
  const levels = await page.locator('h1, h2, h3, h4').evaluateAll((hs) => hs.filter((h) => (h as HTMLElement).offsetParent !== null).map((h) => Number(h.tagName[1])));
  for (let i = 1; i < levels.length; i++) expect(levels[i]).toBeLessThanOrEqual(levels[i - 1] + 1);
});

test('CSS is inline: no render-blocking stylesheet', async ({ request }) => {
  for (const path of ['', `serie/${monthly.key}/`, 'metod/']) {
    const html = await (await request.get(path)).text();
    const blocking = [...html.matchAll(/<link[^>]*rel="stylesheet"[^>]*>/g)].map((m) => m[0]).filter((l) => !/\sdisabled/.test(l));
    expect(blocking).toEqual([]);
    expect(html).toMatch(/<style>/);
  }
});

test('forced colours: a pressed chip is marked by the system highlight, legend swatches keep their colour', async ({ page }) => {
  await page.emulateMedia({ forcedColors: 'active' });
  await page.goto(`serie/${monthly.key}/`, { waitUntil: 'networkidle' });
  const pressed = page.locator('.chip[aria-pressed="true"]').first();
  await expect(pressed).toBeVisible();
  const bg = await pressed.evaluate((e) => getComputedStyle(e).backgroundColor);
  const highlight = await page.evaluate(() => {
    const d = document.createElement('div');
    d.style.backgroundColor = 'Highlight';
    document.body.append(d);
    const c = getComputedStyle(d).backgroundColor;
    d.remove();
    return c;
  });
  expect(bg).toBe(highlight);
  const sw = page.locator('.legend .sw').first();
  if (await sw.count()) expect(await sw.evaluate((e) => getComputedStyle(e).forcedColorAdjust)).toBe('none');
});
