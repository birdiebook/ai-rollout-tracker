// Versions and time travel for one series (versions-v1, docs/steg3/datakontrakt.md section 5). Pure functions only:
// no fetching, no DOM. W9 (time travel) builds on this module.
//
// The one rule: what is shown for a date D is exactly what was known on D. `asOf(v, D)` is the contract's replay
// (= observations.as_of in Python: the latest version with known_from <= D, rows with known_from == D included).
// A version is never returned for a date before its known_from day; before the first known day the result is empty,
// and before `collapsed_before` (size guard) the series shows nothing, because every collapsed version is dated at
// the cutoff.
import type { Versions } from './types';

export type Snapshot = Map<string, number>;

const DAY = /^\d{4}-\d{2}-\d{2}$/;

/** "YYYY-MM-DD" from a Date or an ISO string (a time of day is dropped: the day itself counts, as in the contract). */
export function toDay(date: string | Date): string {
  if (date instanceof Date) {
    if (Number.isNaN(date.getTime())) throw new RangeError('asOf: invalid date');
    return date.toISOString().slice(0, 10);
  }
  const d = date.slice(0, 10);
  if (!DAY.test(d)) throw new RangeError(`asOf: not a date: ${date}`);
  return d;
}

/** Number of version rows known on `day` (rows are sorted by date, so this is a prefix). Binary search. */
export function knownRows(v: Versions, day: string): number {
  let lo = 0;
  let hi = v.p.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (v.dates[v.d[mid]] <= day) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

/** period -> value as known on `date`. Exactly the contract's replay (datakontrakt section 5). */
export function asOf(v: Versions | null | undefined, date: string | Date): Snapshot {
  const out: Snapshot = new Map();
  if (!v) return out;
  const day = toDay(date);
  const n = knownRows(v, day);
  for (let i = 0; i < n; i++) out.set(v.periods[v.p[i]], v.v[i]);
  return out;
}

/** The snapshot as rows sorted by period (every period format sorts correctly as text). */
export function asOfRows(v: Versions | null | undefined, date: string | Date): { period: string; value: number }[] {
  return [...asOf(v, date)].map(([period, value]) => ({ period, value })).sort((a, b) => (a.period < b.period ? -1 : a.period > b.period ? 1 : 0));
}

/** Snapshots for several dates in one pass (for the revision view's version lines). Same result as asOf per date. */
export function snapshots(v: Versions | null | undefined, dates: (string | Date)[]): Snapshot[] {
  const days = dates.map(toDay);
  const order = days.map((d, i) => [d, i] as const).sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
  const out: Snapshot[] = days.map(() => new Map());
  if (!v) return out;
  const cur: Snapshot = new Map();
  let i = 0;
  for (const [day, idx] of order) {
    while (i < v.p.length && v.dates[v.d[i]] <= day) {
      cur.set(v.periods[v.p[i]], v.v[i]);
      i++;
    }
    out[idx] = new Map(cur);
  }
  return out;
}

/** Distinct known_from days (ascending): the dates on which the series changed. */
export const versionDates = (v: Versions | null | undefined): string[] => (v ? [...v.dates] : []);

/** The latest version date on or before `date` (the version a reader saw that day), or null before the first. */
export function versionOn(v: Versions | null | undefined, date: string | Date): string | null {
  if (!v) return null;
  const n = knownRows(v, toDay(date));
  return n === 0 ? null : v.dates[v.d[n - 1]];
}

/** True when time travel to `date` shows nothing for the series (before its first version or the collapse cutoff). */
export function emptyOn(v: Versions | null | undefined, date: string | Date): boolean {
  return !v || knownRows(v, toDay(date)) === 0;
}

/** Every version of one period: [{date, value}] by date. */
export function periodVersions(v: Versions | null | undefined, period: string): { date: string; value: number }[] {
  if (!v) return [];
  const pi = v.periods.indexOf(period);
  if (pi < 0) return [];
  const out: { date: string; value: number }[] = [];
  for (let i = 0; i < v.p.length; i++) if (v.p[i] === pi) out.push({ date: v.dates[v.d[i]], value: v.v[i] });
  return out;
}

export interface PeriodRevision {
  period: string;
  /** first published value and its known_from day */
  first: number;
  firstKnown: string;
  /** latest value (as of the bundle's build day) and its known_from day */
  latest: number;
  latestKnown: string;
  /** number of versions of the period (1 = never revised) */
  n: number;
}

/** First and latest version per period, sorted by period. One pass. */
export function revisions(v: Versions | null | undefined): PeriodRevision[] {
  if (!v) return [];
  const acc = new Map<number, PeriodRevision>();
  for (let i = 0; i < v.p.length; i++) {
    const pi = v.p[i];
    const date = v.dates[v.d[i]];
    const r = acc.get(pi);
    if (!r) acc.set(pi, { period: v.periods[pi], first: v.v[i], firstKnown: date, latest: v.v[i], latestKnown: date, n: 1 });
    else {
      r.latest = v.v[i];
      r.latestKnown = date;
      r.n += 1;
    }
  }
  return [...acc.values()].sort((a, b) => (a.period < b.period ? -1 : a.period > b.period ? 1 : 0));
}

/** Revision of a period as a number on the series' own scale: % (log difference ×100) for positive levels under
 *  the log method, otherwise the difference in the unit. null when the log is undefined. */
export function revisionSize(r: Pick<PeriodRevision, 'first' | 'latest'>, relative: boolean): number | null {
  if (!relative) return r.latest - r.first;
  if (!(r.first > 0 && r.latest > 0)) return null;
  return Math.log(r.latest / r.first) * 100;
}

/** Up to `k` version dates spread evenly over the history (always the first and the last), for version lines. */
export function sampleDates(v: Versions | null | undefined, k = 24): string[] {
  if (!v || v.dates.length === 0) return [];
  const n = v.dates.length;
  if (n <= k) return [...v.dates];
  const out = new Set<string>();
  for (let j = 0; j < k; j++) out.add(v.dates[Math.round((j * (n - 1)) / (k - 1))]);
  return [...out];
}

/** The day before which time travel shows reconstructed history (datakontrakt 5.6): backfilled rows carry the
 *  vintage of the day they were fetched, so the boundary is the later of the last backfilled known_from (a rule day)
 *  and that fetch day (rows.backfill_fetched, from bundle 1.2.0). null: nothing is backfilled. */
export function backfillUntil(rows: { backfill_last_known?: string | null; backfill_fetched?: string | null } | null | undefined): string | null {
  const a = rows?.backfill_last_known ?? null;
  const b = rows?.backfill_fetched ?? null;
  return a && b ? (a > b ? a : b) : (a ?? b);
}

/** Time travel to a date before the backfill boundary (backfillUntil) shows reconstructed history. */
export function reconstructedOn(boundary: string | null | undefined, date: string | Date): boolean {
  return !!boundary && toDay(date) < boundary;
}

/** The day a revision view opens on when no date is given: the version current one year before the latest version
 *  (or the first version for a younger series). Always a real version day. */
export function defaultAsOf(v: Versions): string {
  const last = new Date(v.last_known + 'T00:00:00Z');
  const yearBack = new Date(Date.UTC(last.getUTCFullYear() - 1, last.getUTCMonth(), last.getUTCDate()));
  return versionOn(v, yearBack) ?? v.first_known;
}
