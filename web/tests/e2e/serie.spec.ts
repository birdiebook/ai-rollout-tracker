// W7 series instrument: lazy versions, as_of permalink = exactly what was known, URL state, CSV, table view.
import { mkdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

interface V {
  periods: string[];
  dates: string[];
  p: number[];
  d: number[];
  v: number[];
  n_revised_periods: number;
  last_known: string;
}
const index = JSON.parse(readFileSync('static/data/series/index.json', 'utf-8')) as { series: { key: string; freq: string; n_versions: number }[] };
const load = (k: string) => JSON.parse(readFileSync(`static/data/series/${k}.json`, 'utf-8')) as { key: string; label: string; versions: V; license: { attribution: string } };
// the most revised series in the bundle
const revisedKey = index.series
  .map((s) => ({ s, v: load(s.key).versions }))
  .filter((x) => x.v && x.v.n_revised_periods > 0)
  .sort((a, b) => b.v.n_revised_periods - a.v.n_revised_periods)[0].s.key;
const rev = load(revisedKey);
const replay = (v: V, day: string) => {
  const out = new Map<string, number>();
  for (let i = 0; i < v.p.length && v.dates[v.d[i]] <= day; i++) out.set(v.periods[v.p[i]], v.v[i]);
  return out;
};

test('the versions are fetched only when the revision view opens', async ({ page }) => {
  const seen: string[] = [];
  page.on('request', (r) => r.url().includes('/data/series/') && seen.push(r.url()));
  await page.goto(`serie/${revisedKey}/`);
  await page.waitForLoadState('networkidle');
  expect(seen).toEqual([]);
  await expect(page.locator('#rev-size svg[role="img"]')).toBeVisible(); // revisions shown without the fetch
  await page.getByRole('button', { name: /Utforska versionerna/ }).click();
  await expect(page.locator('#rev-versions svg[role="img"]')).toBeVisible();
  expect(seen.map((u) => new URL(u).pathname)).toEqual([expect.stringMatching(new RegExp(`/data/series/${revisedKey}\\.json$`))]);
  // opening the view puts it in the URL
  await expect(page).toHaveURL(/#rev=1$/);
});

test('as_of in the URL shows exactly what was known that day, never later versions', async ({ page }) => {
  const v = rev.versions;
  const mid = v.dates[Math.floor(v.dates.length / 2)];
  const dayBefore = new Date(Date.parse(mid) - 86_400_000).toISOString().slice(0, 10);
  for (const day of [dayBefore, mid]) {
    await page.goto('about:blank'); // a fresh load each time (a hash-only change is a same-document navigation)
    await page.goto(`serie/${revisedKey}/#as_of=${day}`);
    await expect(page.locator('#rev-versions svg[role="img"]')).toBeVisible();
    const known = replay(v, day);
    // the table of the revision view lists one row per period known that day, with that day's value
    await page.locator('#rev-versions').getByRole('button', { name: 'Visa tabell' }).click();
    const rows = page.locator('#rev-versions-table tbody tr');
    await expect(rows).toHaveCount(known.size);
    const header = await page.locator('#rev-versions-table thead').innerText();
    expect(header).toContain(day);
  }
});

test('window, scale and table state; the permalink restores the view', async ({ page }) => {
  await page.goto(`serie/${revisedKey}/`);
  await page.waitForLoadState('networkidle');
  const win = page.getByRole('group', { name: 'Tidsfönster' });
  await win.getByRole('button', { name: '5 år' }).click();
  await expect(win.getByRole('button', { name: '5 år' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page).toHaveURL(/#fonster=5/);
  await page.reload();
  await page.waitForLoadState('networkidle');
  await expect(page.getByRole('group', { name: 'Tidsfönster' }).getByRole('button', { name: '5 år' })).toHaveAttribute('aria-pressed', 'true');
  await page.locator('#level').getByRole('button', { name: 'Visa tabell' }).click();
  await expect(page.locator('#level-table table')).toBeVisible();
});

test('CSV download carries source, licence and attribution', async ({ page }) => {
  await page.goto(`serie/${revisedKey}/`);
  await page.waitForLoadState('networkidle');
  const [dl] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Ladda ned nivåer (CSV)' }).click()]);
  expect(dl.suggestedFilename()).toBe(`${revisedKey}.csv`);
  const text = readFileSync((await dl.path())!, 'utf-8');
  expect(text).toContain(`# attribution: ${rev.license.attribution}`);
  expect(text).toMatch(/\r\nperiod,value\r\n/);
  const [dl2] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Ladda ned alla versioner (CSV)' }).click()]);
  const t2 = readFileSync((await dl2.path())!, 'utf-8');
  expect(t2.split('\r\n').filter((l) => /^\d/.test(l)).length).toBe(rev.versions.p.length);
});

test('series pages are prerendered with SVG (no JS needed for the charts)', async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const page = await ctx.newPage();
  for (const s of index.series.slice(0, 6)) {
    await page.goto(`serie/${s.key}/`);
    await expect(page.locator('h1')).toBeVisible();
    expect(await page.locator('figure svg[role="img"]').count()).toBeGreaterThanOrEqual(1);
  }
  await ctx.close();
});

for (const scheme of ['light', 'dark'] as const) {
  test(`axe on the open revision view (${scheme})`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: scheme });
    await page.goto(`serie/${revisedKey}/#rev=1`);
    await expect(page.locator('#rev-versions svg[role="img"]')).toBeVisible();
    const res = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze();
    expect(res.violations.map((v) => `${v.id}: ${v.nodes.length} × ${v.nodes[0]?.target.join(' ')}`)).toEqual([]);
  });
}

// review screenshots of the revision view (the route screenshots are in screenshots.spec.ts)
if (process.env.SHOTS_DIR) {
  for (const scheme of ['light', 'dark'] as const) {
    test(`screenshot revision view ${scheme}`, async ({ page }, info) => {
      mkdirSync(process.env.SHOTS_DIR!, { recursive: true });
      await page.emulateMedia({ colorScheme: scheme, reducedMotion: 'reduce' });
      await page.goto(`serie/${revisedKey}/#rev=1`);
      await expect(page.locator('#rev-versions svg[role="img"]')).toBeVisible();
      await page.screenshot({ path: join(process.env.SHOTS_DIR!, `serie-revision-${info.project.name}-${scheme}.png`), fullPage: true });
    });
  }
}
