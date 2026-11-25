// W13 monthly story end to end: the cards of story/<month>.json in their registered order, one figure per card that
// is there without JavaScript, keyboard steps (rail links, j/k) and reduced motion, links into the time-travel views
// at the month's known day, the entry from the start page, and the story under global time travel (only months
// known on the day).
import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';
import { TT_DAY } from './routes';

interface Card { id: string; type: string; title: string; link: { kind: string } }
interface StoryDoc { month: string; month_sv: string; known: string; cards: Card[] }
const index = JSON.parse(readFileSync('static/data/story/index.json', 'utf-8')) as { latest: string; months: { month: string; known: string; n_events: number }[] };
const story = (m: string) => JSON.parse(readFileSync(`static/data/story/${m}.json`, 'utf-8')) as StoryDoc;
const latest = story(index.latest);

test('the cards in the registered order, each with its figure and a link on', async ({ page }) => {
  await page.goto(`manad/${latest.month}/`);
  const steps = page.locator('article.step');
  await expect(steps).toHaveCount(latest.cards.length);
  expect(await steps.evaluateAll((els) => els.map((e) => e.getAttribute('data-card')))).toEqual(latest.cards.map((c) => c.id));
  for (let i = 0; i < latest.cards.length; i++) {
    const s = steps.nth(i);
    await expect(s.locator('h2').first()).toHaveText(latest.cards[i].title);
    expect(await s.locator('.fig svg, .fig [role="group"]').count(), latest.cards[i].id).toBeGreaterThan(0);
    await expect(s.locator('a[data-link]')).toHaveCount(1);
  }
  await expect(page.locator('article.story')).toHaveAttribute('data-known', latest.known);
});

test('works without JavaScript: every figure is prerendered SVG and the rail links are anchors', async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const page = await ctx.newPage();
  await page.goto(`manad/${latest.month}/`);
  const n = latest.cards.filter((c) => c.type !== 'K2').length;
  expect(await page.locator('article.step .fig svg').count()).toBeGreaterThanOrEqual(n);
  const rail = await page.locator('nav.rail a').evaluateAll((els) => els.map((e) => e.getAttribute('href')));
  if (rail.length) expect(rail).toEqual(latest.cards.map((c) => `#kort-${c.id}`));
  // without JS the links open today's views (time travel needs JS)
  for (const href of await page.locator('a[data-link]').evaluateAll((els) => els.map((e) => e.getAttribute('href') ?? ''))) expect(href).not.toContain('as_of');
  await ctx.close();
});

test('keyboard: j and k step through the cards, focus follows, reduced motion is respected', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(`manad/${latest.month}/`);
  await page.locator('article.step').first().waitFor();
  await page.waitForFunction(() => document.querySelector('.scrolly.enhanced') !== null);
  const transition = await page.locator('article.step').first().evaluate((e) => getComputedStyle(e).transitionDuration);
  expect(transition).toBe('0s');
  await page.keyboard.press('j');
  await expect(page.locator(`#kort-${latest.cards[1].id}`)).toBeFocused();
  await page.keyboard.press('j');
  await page.keyboard.press('k');
  await expect(page.locator(`#kort-${latest.cards[1].id}`)).toBeFocused();
});

test('links into time-travel views carry the month known day', async ({ page }) => {
  await page.goto(`manad/${latest.month}/`);
  await page.waitForFunction(() => document.querySelector('.scrolly.enhanced') !== null);
  for (const c of latest.cards.filter((c) => ['branch', 'series', 'start'].includes(c.link.kind))) {
    await expect(page.locator(`#kort-${c.id} a[data-link]`)).toHaveAttribute('href', new RegExp(`#as_of=${latest.known}$`));
  }
  const branch = latest.cards.find((c) => c.link.kind === 'branch');
  if (branch) {
    await page.locator(`#kort-${branch.id} a[data-link]`).click();
    await expect(page).toHaveURL(new RegExp(`/gren/G\\d/#as_of=${latest.known}$`));
    await expect(page.locator('[data-tt="view"]')).toBeVisible();
  }
});

test('the start page leads to the latest story', async ({ page }) => {
  await page.goto('');
  await page.locator('.story-entry a').click();
  await expect(page).toHaveURL(new RegExp(`/manad/${latest.month}/$`));
  await expect(page.locator('h1')).toContainText(latest.month_sv.split(' ')[0].replace(/^./, (c) => c.toUpperCase()));
});

test('a month without any selected event says so (K9)', async ({ page }) => {
  const quiet = [...index.months].reverse().find((m) => m.n_events === 0 && m.month !== index.months[0].month);
  test.skip(!quiet, 'no quiet month in this bundle');
  await page.goto(`manad/${quiet!.month}/`);
  await expect(page.locator('article.step')).toHaveCount(2);
  await expect(page.locator('article.step[data-type="K9"]')).toBeVisible();
});

test('time travel: a story is shown only from its known day, and the month list is cut', async ({ page }) => {
  await page.goto(`manad/${latest.month}/#as_of=${TT_DAY}`);
  if (latest.known > TT_DAY) {
    await expect(page.locator('[data-tt="story-unknown"]')).toBeVisible();
    const known = index.months.filter((m) => m.known <= TT_DAY).at(-1);
    if (known) {
      await page.locator('[data-tt="story-unknown"] a').click();
      await expect(page).toHaveURL(new RegExp(`/manad/${known.month}/#as_of=${TT_DAY}$`));
      await expect(page.locator('[data-tt="view"] article.story')).toHaveAttribute('data-month', known.month);
      const listed = await page.locator('[data-tt="view"] .mlist a').evaluateAll((els) => els.map((e) => e.textContent ?? ''));
      expect(listed.length).toBe(index.months.filter((m) => m.known <= TT_DAY).length);
    }
  }
  const after = index.months.at(-1)!.known;
  await page.goto(`manad/${latest.month}/#as_of=${after}`);
  await expect(page.locator('[data-tt="view"] article.story')).toHaveAttribute('data-known', latest.known);
});
