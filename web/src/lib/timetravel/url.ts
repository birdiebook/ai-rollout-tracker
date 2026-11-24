// The global time-travel date in the URL: `as_of=YYYY-MM-DD` in the hash, next to the page's own keys (the series
// page's permalink.ts reads the same key and keeps unknown keys, so both live in one hash). Pure functions.
import { toDay } from '$lib/series/versions';

export const KEY = 'as_of';
const DAY = /^\d{4}-\d{2}-\d{2}$/;

export function isDay(s: string | null | undefined): s is string {
  return !!s && DAY.test(s) && !Number.isNaN(Date.parse(s + 'T00:00:00Z')) && new Date(s + 'T00:00:00Z').toISOString().slice(0, 10) === s;
}

/** The as_of day in a hash ("#a=1&as_of=2024-06-30"), or null (missing or not a real date). */
export function readAsOf(hash: string): string | null {
  const v = new URLSearchParams(hash.replace(/^#/, '')).get(KEY);
  return isDay(v) ? v : null;
}

/** The hash with as_of set to `day` (null removes it); every other key is kept in its place. "" when empty. */
export function withAsOf(hash: string, day: string | null): string {
  const params = new URLSearchParams(hash.replace(/^#/, ''));
  if (day) params.set(KEY, day);
  else params.delete(KEY);
  const s = params.toString();
  return s ? `#${s}` : '';
}

/** The month end `k` months from the month of `day` (k = -1 from 2024-06-15 or 2024-06-30 gives 2024-05-31). */
export function stepMonth(day: string, k: number): string {
  const [y, m] = toDay(day).split('-').map(Number);
  return new Date(Date.UTC(y, m - 1 + k + 1, 0)).toISOString().slice(0, 10);
}

export const clampDay = (day: string, min: string, max: string) => (day < min ? min : day > max ? max : day);

export const dayToMs = (day: string) => Date.parse(day + 'T00:00:00Z');
export const msToDay = (ms: number) => new Date(ms).toISOString().slice(0, 10);

/** An internal link with the time-travel date carried along (P11: the whole view is in the URL). Returns null for
 *  links that must not be touched: other origins, outside the site's base path, downloads, non-http schemes. */
export function carryHref(href: string, here: string, base: string, day: string | null): string | null {
  let u: URL;
  try {
    u = new URL(href, here);
  } catch {
    return null;
  }
  const h = new URL(here);
  if (u.origin !== h.origin || !/^https?:$/.test(u.protocol)) return null;
  const root = base.replace(/\/$/, '') + '/';
  if (!(u.pathname + '/').startsWith(root) && u.pathname !== base) return null;
  u.hash = withAsOf(u.hash, day);
  return u.href;
}
