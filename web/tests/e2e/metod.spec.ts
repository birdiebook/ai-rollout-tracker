// W11 explorable method page: the registered value is the pipeline's record, the sliders work by keyboard, and
// source links are shown (rel="noopener") but never fetched.
import { mkdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test } from '@playwright/test';

const shots = process.env.SHOTS_DIR;
if (shots) mkdirSync(shots, { recursive: true });

/** The explorer's default branch: the eligible branch (no counted withheld series) with the most counted series. */
function defaultBranch() {
  let best: { code: string; n: number; state: string; index: number } | null = null;
  for (const code of ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9']) {
    const d = JSON.parse(readFileSync(`static/data/branch/${code}.json`, 'utf-8'));
    if ((d.n_withheld_counted ?? 0) > 0 || !d.n_series || d.counted.length !== d.n_series) continue;
    if (!best || d.n_series > best.n) best = { code, n: d.n_series, state: d.state, index: d.index };
  }
  return best;
}

test('registered card shows the pipeline record; the slider is keyboard operable and labelled exploration', async ({ page }, info) => {
  const b = defaultBranch();
  test.skip(!b, 'no explorable branch in this bundle');
  await page.goto('metod/');
  await page.waitForLoadState('networkidle');
  const reg = page.locator('.reg-card');
  await expect(reg).toContainText(b!.state);
  await expect(reg).toContainText(b!.index.toFixed(2).replace('.', ','));
  const exp = page.locator('.exp-card');
  await expect(exp).toContainText(b!.state); // at the registered value the exploration equals the record

  const slider = page.getByRole('slider', { name: /Dödband/ });
  await slider.focus();
  await expect(slider).toBeFocused();
  for (let i = 0; i < 25; i++) await page.keyboard.press('ArrowRight');
  await expect(slider).toHaveValue('0.5');
  await expect(page.locator('.controls .tag.exp').first()).toHaveText('utforskning');
  await expect(exp).toContainText('0,50');
  await expect(reg).toContainText(b!.state); // the registered card never changes
  if (shots) await page.locator('#diffusion').screenshot({ path: join(shots, `metod-diffusion-k050-${info.project.name}.png`) });

  await page.keyboard.press('Home');
  await expect(slider).toHaveValue('0');
  await page.getByRole('button', { name: /Tillbaka till registrerat/ }).click();
  await expect(slider).toHaveValue('0.25');
  await expect(page.locator('.controls .tag.reg').first()).toHaveText('registrerat');
});

test('interval level and width sliders by keyboard', async ({ page }, info) => {
  await page.goto('metod/');
  await page.waitForLoadState('networkidle');
  const level = page.getByRole('slider', { name: /Intervallnivå/ });
  await level.focus();
  await page.keyboard.press('ArrowRight');
  await expect(level).toHaveValue('85');
  await expect(page.locator('#iv-pool-title')).toContainText('85 %');
  const width = page.getByRole('slider', { name: /Intervallens bredd/ });
  await width.focus();
  for (let i = 0; i < 8; i++) await page.keyboard.press('ArrowLeft');
  await expect(width).toHaveValue('0.6');
  await expect(page.locator('#intervall')).toContainText('För smala intervall');
  if (shots) await page.locator('#intervall').screenshot({ path: join(shots, `metod-intervall-w060-${info.project.name}.png`) });
});

test('source links are rel="noopener", absolute http(s), and hovering them loads nothing', async ({ page }) => {
  const external: string[] = [];
  page.on('request', (r) => {
    const u = new URL(r.url());
    if (!['localhost', '127.0.0.1'].includes(u.hostname)) external.push(r.url());
  });
  await page.goto('metod/');
  await page.waitForLoadState('networkidle');
  const links = page.locator('#kallor a[href^="http"], #forregistrering a[href^="http"]');
  const n = await links.count();
  for (let i = 0; i < n; i++) {
    const a = links.nth(i);
    expect(await a.getAttribute('rel')).toBe('noopener');
    expect(await a.getAttribute('href')).toMatch(/^https?:\/\//);
  }
  if (n) {
    await page.locator('#kallor details').first().evaluate((d) => ((d as HTMLDetailsElement).open = true));
    await links.first().hover();
    await page.waitForTimeout(300);
  }
  expect(external).toEqual([]);
});

test('the method figures are in the prerendered HTML (SVG without JS)', async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const page = await ctx.newPage();
  await page.goto('metod/');
  for (const id of ['iv-pool', 'cal-cov', 'cal-pit', 'prereg-timeline', 'prereg-holm']) await expect(page.locator(`#${id} svg[role="img"]`)).toBeAttached();
  await ctx.close();
});
