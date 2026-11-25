// R-W1 (independent review): try to break the time-travel boundary in the real browser. Every date written on the
// page under as_of=D (outside the labelled "then against today" comparison and the slider) must be on or before D,
// the footer must not name today's record, and a hash the store reads must hide today's content before paint.
import { readFileSync } from 'node:fs';
import { expect, test, type Page } from '@playwright/test';
import { TT_DAY } from './routes';

const index = JSON.parse(readFileSync('static/data/series/index.json', 'utf-8')) as { series: { key: string }[] };
type Rows = { backfill_last_known: string | null; backfill_fetched?: string | null } | null;
const docOf = (k: string) => JSON.parse(readFileSync(`static/data/series/${k}.json`, 'utf-8')) as { versions: { first_known: string } | null; rows: Rows };
const docs = index.series.map((s) => ({ key: s.key, d: docOf(s.key) }));
const DAYS = ['2019-06-30', TT_DAY];
// the backfill boundary (versions.ts backfillUntil): the later of the rule day and the fetch day (RW1-X 3a)
const until = (r: Rows) => [r?.backfill_last_known ?? '', r?.backfill_fetched ?? ''].sort().at(-1) ?? '';
// per day: a series published on the day whose backfilled rows were fetched later than their last rule day, with the
// day in between (the R-W1 3a case, us_elec_sales_com_* in the real bundle)
const gapFor = (day: string) => docs.find((x) => x.d.versions && x.d.versions.first_known <= day && (x.d.rows?.backfill_last_known ?? '9') <= day && until(x.d.rows) > day);
// per day: a series not published yet on the day, and one whose history is backfilled on the day
function seriesFor(day: string): string[] {
  const late = docs.find((x) => x.d.versions && x.d.versions.first_known > day);
  const back = docs.find((x) => x.d.versions && x.d.versions.first_known <= day && until(x.d.rows) > day);
  return [...new Set([late?.key, back?.key, gapFor(day)?.key, docs[0].key].filter((k): k is string => !!k))];
}

const MON = ['jan', 'feb', 'mar', 'apr', 'maj', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec'];
const LONG = ['januari', 'februari', 'mars', 'april', 'maj', 'juni', 'juli', 'augusti', 'september', 'oktober', 'november', 'december'];
const pad = (n: number) => String(n).padStart(2, '0');

/** Every day ("30 jun 2024", "2024-06-30") and month ("jun 2024", "juni 2024") written in the text. */
function datesIn(text: string): { days: string[]; months: string[] } {
  const days: string[] = [];
  const months: string[] = [];
  for (const m of text.matchAll(/\b(\d{4})-(\d{2})-(\d{2})\b/g)) days.push(`${m[1]}-${m[2]}-${m[3]}`);
  const names = [...LONG, ...MON].join('|');
  for (const m of text.matchAll(new RegExp(`(?:\\b(\\d{1,2}) )?\\b(${names})\\.? (\\d{4})\\b`, 'g'))) {
    const i = LONG.includes(m[2]) ? LONG.indexOf(m[2]) : MON.indexOf(m[2]);
    if (m[1]) days.push(`${m[3]}-${pad(i + 1)}-${pad(Number(m[1]))}`);
    else months.push(`${m[3]}-${pad(i + 1)}`);
  }
  return { days, months };
}

/** The visible text of the page except the slider, the labelled comparison with today and the backfill label. */
async function shownText(page: Page): Promise<string> {
  return page.evaluate(() => {
    const clone = document.body.cloneNode(true) as HTMLElement;
    for (const sel of ['section[aria-label="Tidsresa"]', '[data-tt="compare"]', '[data-rw1-exempt]', 'script', 'style', 'svg'])
      clone.querySelectorAll(sel).forEach((e) => e.remove());
    clone.querySelectorAll('.note').forEach((e) => {
      if (/bakåtfylld med dagens version/.test(e.textContent ?? '')) e.remove(); // the label of reconstructed history
    });
    // the first month of the state history is a build parameter (--history-from), not knowledge of the day
    return (clone.innerText || clone.textContent || '').replace(/(Tillstånden finns per månadsslut från|Grenens historik börjar) \p{L}+ \d{4}/gu, '');
  });
}

for (const day of DAYS) {
  for (const path of ['', 'gren/G9/', 'gren/G3/', ...seriesFor(day).map((k) => `serie/${k}/`)]) {
    test(`no date after ${day} is written on /${path} under as_of`, async ({ page }) => {
      await page.goto(`${path}#as_of=${day}`, { waitUntil: 'networkidle' });
      await expect(page.locator('[data-tt="view"] h1').first()).toBeVisible();
      await expect(page.locator('[data-tt="view"] [role="status"]')).toHaveCount(0); // loaded
      const { days, months } = datesIn(await shownText(page));
      expect(days.filter((d) => d > day), 'days after the as_of day').toEqual([]);
      expect(months.filter((m) => m > day.slice(0, 7)), 'months after the as_of month').toEqual([]);
      // the footer names the travel day, never today's record
      const foot = await page.locator('footer').innerText();
      expect(foot).toContain('tidsresa');
      expect(foot).not.toMatch(/rekonstruerad historik, inte ett skarpt underlag|skarp ögonblicksbild/);
    });
  }
}

for (const day of DAYS) {
  test(`RW1-X 3a: a series backfilled after its last rule day is labelled reconstructed on ${day}`, async ({ page }) => {
    const gap = gapFor(day);
    test.skip(!gap, 'no series with the rule day before and the fetch day after this day');
    await page.goto(`serie/${gap!.key}/#as_of=${day}`, { waitUntil: 'networkidle' });
    await expect(page.locator('[data-tt="view"] h1').first()).toBeVisible();
    const note = page.locator('[data-tt="view"] .note[data-backfill-until]');
    await expect(note).toBeVisible();
    await expect(note).toContainText('bakåtfylld med dagens version');
    expect(await note.getAttribute('data-backfill-until')).toBe(until(gap!.d.rows));
  });
}

test('an encoded as_of key (the store reads it) hides today before paint, like the plain key', async ({ page }) => {
  await page.route('**/_app/immutable/**/*.js', (r) => r.abort());
  for (const hash of [`#as%5Fof=${TT_DAY}`, `#x=1&as_of=${TT_DAY}`]) {
    await page.goto('about:blank');
    await page.goto(hash);
    expect(await page.locator('.tt-today h1').first().evaluate((e) => getComputedStyle(e).visibility), hash).toBe('hidden');
    expect(await page.locator('footer .tt-hide').evaluate((e) => getComputedStyle(e).visibility), hash).toBe('hidden');
  }
  // an invalid day does not travel, so nothing is hidden
  await page.goto('about:blank');
  await page.goto('#as_of=2024-02-30');
  await expect(page.locator('.tt-today h1').first()).toBeVisible();
});
