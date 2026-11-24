// W10: /avstamningar and /regim. Smoke, axe and screenshots cover them through routes.ts; this checks the content.
import { expect, test } from '@playwright/test';

test('reconciliations: not counted in the branch index, every ratio with its components', async ({ page }) => {
  await page.goto('avstamningar/');
  await expect(page.getByText('Räknas inte i grenarnas index.')).toBeVisible();
  const sections = page.locator('section.rc');
  const n = await sections.count();
  expect(n).toBeGreaterThan(0);
  for (let i = 0; i < n; i++) {
    const s = sections.nth(i);
    await expect(s.getByText('räknas inte i grenarnas index')).toBeVisible();
    await expect(s.getByRole('heading', { name: 'Takten och vad komponenterna bidrog med' })).toBeVisible();
    expect(await s.locator('.comps li').count()).toBeGreaterThan(1);
  }
  // the overview picture is in the prerendered HTML and every ratio has an anchor
  await expect(page.locator('#rc-overview svg')).toBeVisible();
  const first = await page.locator('.toc a').first().getAttribute('href');
  await expect(page.locator(first!)).toBeVisible();
});

test('regime: registered thresholds, live from the first snapshot, holdout told honestly', async ({ page }) => {
  await page.goto('regim/');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Har något fundamentalt ändrats?');
  await expect(page.locator('#regime-timeline svg')).toBeVisible();
  await expect(page.getByText(/≥ 0,8: skifte till inbromsning/).first()).toBeVisible();
  await expect(page.getByText(/≤ 0,2: tillbaka till expansion/).first()).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Vad holdouten visade' })).toBeVisible();
  await expect(page.getByText('Delvis känd holdout.')).toBeVisible();
  const text = (await page.locator('main').textContent()) ?? '';
  expect(text).not.toMatch(/larm|varning!|oroande|kris/i);
});
