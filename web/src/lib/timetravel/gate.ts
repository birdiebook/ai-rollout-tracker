// THE LEAKAGE BOUNDARY of time travel (W9). Every time-travel view gets its data only from the functions in this
// file, and these functions return new objects that contain nothing that was unknown on the chosen day D:
//
//   versions   rows with known_from <= D only (cutVersions; replay = observations.as_of in Python)
//   records    a month-end record (stripes, branch index history, the record's measures per series) only when the
//              record itself was known on D: its month end, or the live snapshot's date if later (monthKnown)
//   metadata   static catalogue fields only (label, unit, source, licence ...), by allow-list; today's measures,
//              levels, row counts, record lists and directions are never copied
//
// Every *On() result is checked by leaks() before it is returned, and a violation throws (LeakError) instead of
// rendering. The golden tests (timetravel.test.ts against web/fixtures/timetravel_golden.json) prove that the cut
// of today's bundle equals what Python would have built on D (vintages.encode(rows, D), site.data.Record(today=D)).
// Comparisons with today's version are never produced here: a view that shows "i dag" gets today's document
// separately and labels it (data-tt="today").
import type { Branch, Overview, RecordMeta, StateName, Stripes } from '$lib/data';
import type { Measure, MeasureHistory, SeriesDoc, Versions } from '$lib/series/types';
import { reconstructedOn, toDay } from '$lib/series/versions';

export class LeakError extends Error {
  constructor(public violations: string[]) {
    super(`time travel would show later knowledge: ${violations.slice(0, 5).join('; ')}`);
    this.name = 'LeakError';
  }
}

const MONTH = /^(\d{4})-(\d{2})$/;

/** "2026-02" -> "2026-02-28": the day a month-end record is computed for. */
export function monthEnd(month: string): string {
  const m = MONTH.exec(month);
  if (!m) throw new RangeError(`not a month: ${month}`);
  return new Date(Date.UTC(+m[1], +m[2], 0)).toISOString().slice(0, 10);
}

/** The month whose month end is the latest one on or before `day` ("2026-03-15" -> "2026-02", "2026-03-31" -> "2026-03"). */
export function lastMonthEnd(day: string): string {
  const d = toDay(day);
  const m = d.slice(0, 7);
  if (monthEnd(m) === d) return m;
  const [y, mo] = m.split('-').map(Number);
  return new Date(Date.UTC(y, mo - 2, 1)).toISOString().slice(0, 7);
}

/** The minimal record info the cut needs (overview.record / branch.record). */
export type RecordInfo = Pick<RecordMeta, 'month' | 'date' | 'status'>;

/** The day a month's record became known: its month end, or the live snapshot's date when that is later (never
 *  earlier: a record computed for a month end uses only data known by then, site.data.Record). */
export function monthKnown(month: string, rec?: RecordInfo | null): string {
  const end = monthEnd(month);
  return rec && rec.month === month && typeof rec.date === 'string' && rec.date > end ? rec.date : end;
}

/** Number of leading months (sorted) whose record was known on `day`. */
export function knownMonths(months: string[], day: string, rec?: RecordInfo | null): number {
  let n = 0;
  while (n < months.length && monthKnown(months[n], rec) <= day) n++;
  return n;
}

/** Versions known on `day`: the prefix of rows with known_from <= day, re-indexed so that the object holds no
 *  period or date that only later rows had. null when nothing was known (or before a collapse cutoff). Equal to
 *  vintages.encode(rows, day) for every series without a size-guard collapse (golden test). */
export function cutVersions(v: Versions | null | undefined, date: string): Versions | null {
  if (!v) return null;
  const day = toDay(date);
  let n = 0;
  while (n < v.p.length && v.dates[v.d[n]] <= day) n++;
  if (n === 0) return null;
  const pUsed = [...new Set(v.p.slice(0, n))].sort((a, b) => a - b);
  const dUsed = [...new Set(v.d.slice(0, n))].sort((a, b) => a - b);
  const pMap = new Map(pUsed.map((p, i) => [p, i]));
  const dMap = new Map(dUsed.map((d, i) => [d, i]));
  const p = v.p.slice(0, n).map((x) => pMap.get(x)!);
  const per = new Map<number, number>();
  for (const x of p) per.set(x, (per.get(x) ?? 0) + 1);
  const dates = dUsed.map((d) => v.dates[d]);
  return {
    encoding: v.encoding,
    freq: v.freq,
    native_freq: v.native_freq,
    aggregation: v.aggregation,
    periods: pUsed.map((i) => v.periods[i]),
    dates,
    p,
    d: v.d.slice(0, n).map((x) => dMap.get(x)!),
    v: v.v.slice(0, n),
    n_versions: n,
    n_revised_periods: [...per.values()].filter((k) => k > 1).length,
    first_known: dates[0],
    last_known: dates[dates.length - 1],
    collapsed_before: v.collapsed_before && v.collapsed_before <= day ? v.collapsed_before : null
  };
}

export type HistoryRow = { month: string; kind: string; index: number | null; state: string | null; n_series?: number | null; n_up?: number | null; n_neutral?: number | null; n_down?: number | null };

/** A branch's index history as a site built on `day` had it: the month-end records known on that day. */
export function cutHistory<T extends { month: string }>(history: T[], day: string, rec?: RecordInfo | null): (T & { known: string })[] {
  const out: (T & { known: string })[] = [];
  for (const h of history) {
    const known = monthKnown(h.month, rec);
    if (known <= day) out.push({ ...h, known });
  }
  return out;
}

export interface StripesOn {
  months: string[];
  /** the day each month's record became known */
  known: string[];
  kind: (string | null)[];
  rows: { code: string; name: string; index: (number | null)[]; state: (StateName | null)[]; n_series: (number | null)[] }[];
  thresholds: Stripes['thresholds'];
}

export function cutStripes(s: Stripes, day: string, rec?: RecordInfo | null): StripesOn {
  const n = knownMonths(s.months, day, rec);
  const months = s.months.slice(0, n);
  return {
    months,
    known: months.map((m) => monthKnown(m, rec)),
    kind: s.kind.slice(0, n),
    rows: s.rows.map((r) => ({ code: r.code, name: r.name, index: r.index.slice(0, n), state: r.state.slice(0, n), n_series: (r.n_series ?? []).slice(0, n) })),
    thresholds: s.thresholds
  };
}

/** The record's measures of one series per month end, only for the months known on `day`. */
export function cutMeasureHistory(mh: MeasureHistory | null | undefined, day: string, rec?: RecordInfo | null): (MeasureHistory & { known: string[] }) | null {
  if (!mh || !mh.months.length) return null;
  const n = knownMonths(mh.months, day, rec);
  if (n === 0) return null;
  const out: Record<string, unknown> = { known: mh.months.slice(0, n).map((m) => monthKnown(m, rec)) };
  for (const [k, val] of Object.entries(mh)) out[k] = Array.isArray(val) ? val.slice(0, n) : val;
  return out as unknown as MeasureHistory & { known: string[] };
}

// ------------------------------------------------------------------ views

export type Status = 'live' | 'recon';
const statusOfKind = (kind: string | null | undefined): Status => (kind === 'skarp' || kind === 'live' ? 'live' : 'recon');

export interface BranchStateOn {
  code: string;
  name: string;
  index: number | null;
  state: StateName | null;
  n_series: number | null;
  previous: { month: string; index: number | null; state: StateName | null } | null;
  delta_index: number | null;
  state_changed: boolean | null;
}

export interface OverviewOn {
  day: string;
  /** the record shown on `day` (null: no month-end record of the bundle was known yet) */
  month: string | null;
  known: string | null;
  kind: string | null;
  status: Status;
  /** first month of the bundle's history (time travel before its month end shows no record) */
  first_month: string | null;
  branches: BranchStateOn[];
  counts: Record<string, number>;
  stripes: StripesOn;
  /** live months among the known ones (a committed snapshot exists in git) */
  live_months: string[];
}

const prevMonth = (m: string) => {
  const [y, mo] = m.split('-').map(Number);
  return new Date(Date.UTC(y, mo - 2, 1)).toISOString().slice(0, 7);
};

/** The start page on `day`: the latest month-end record known then, with every branch's state, the change against
 *  the month before (when that month is in the history) and the stripes up to that month. */
export function overviewOn(ov: Overview, date: string): OverviewOn {
  const day = toDay(date);
  const rec = ov.record;
  const stripes = cutStripes(ov.stripes, day, rec);
  const i = stripes.months.length - 1;
  const month = i >= 0 ? stripes.months[i] : null;
  const prevI = month ? stripes.months.indexOf(prevMonth(month)) : -1;
  const branches: BranchStateOn[] = i < 0 ? [] : stripes.rows.map((r) => {
    const prev = prevI >= 0 ? { month: stripes.months[prevI], index: r.index[prevI], state: r.state[prevI] } : null;
    return {
      code: r.code,
      name: r.name,
      index: r.index[i],
      state: r.state[i],
      n_series: r.n_series[i] ?? null,
      previous: prev,
      delta_index: prev && prev.index !== null && r.index[i] !== null ? round4(r.index[i]! - prev.index) : null,
      state_changed: prev ? prev.state !== r.state[i] : null
    };
  });
  const counts: Record<string, number> = { accelererar: 0, stabil: 0, 'bromsar in': 0, 'för få serier': 0, 'inga registrerade kärnserier': 0 };
  for (const b of branches) if (b.state) counts[b.state] = (counts[b.state] ?? 0) + 1;
  const out: OverviewOn = {
    day,
    month,
    known: month ? stripes.known[i] : null,
    kind: i >= 0 ? stripes.kind[i] : null,
    status: statusOfKind(i >= 0 ? stripes.kind[i] : null),
    first_month: ov.stripes.months[0] ?? null,
    branches,
    counts,
    stripes,
    live_months: stripes.months.filter((_, j) => statusOfKind(stripes.kind[j]) === 'live')
  };
  return checked(out, day);
}

const round4 = (x: number) => Math.round(x * 1e4) / 1e4;

export interface SeriesRef {
  key: string;
  label: string;
}

export interface BranchOn {
  day: string;
  code: string;
  name: string;
  question: string;
  month: string | null;
  known: string | null;
  kind: string | null;
  status: Status;
  first_month: string | null;
  index: number | null;
  state: StateName | null;
  n_series: number | null;
  n_up: number | null;
  n_neutral: number | null;
  n_down: number | null;
  previous: { month: string; index: number | null; state: StateName | null } | null;
  delta_index: number | null;
  history: (HistoryRow & { known: string })[];
}

/** A branch page on `day`: the index history known then and the state of its latest month. Which series it counted
 *  that month comes from each series' own cut measure history (seriesOn), not from today's lists. */
export function branchOn(doc: Branch & { history?: HistoryRow[] }, date: string): BranchOn {
  const day = toDay(date);
  const history = cutHistory((doc.history ?? []) as HistoryRow[], day, doc.record);
  const cur = history.at(-1) ?? null;
  const prev = cur ? history.find((h) => h.month === prevMonth(cur.month)) ?? null : null;
  const out: BranchOn = {
    day,
    code: doc.code,
    name: doc.name,
    question: typeof doc.question === 'string' ? doc.question : '',
    month: cur?.month ?? null,
    known: cur?.known ?? null,
    kind: cur?.kind ?? null,
    status: statusOfKind(cur?.kind),
    first_month: doc.history?.[0]?.month ?? null,
    index: cur?.index ?? null,
    state: (cur?.state as StateName | null) ?? null,
    n_series: cur?.n_series ?? null,
    n_up: cur?.n_up ?? null,
    n_neutral: cur?.n_neutral ?? null,
    n_down: cur?.n_down ?? null,
    previous: prev ? { month: prev.month, index: prev.index, state: prev.state as StateName | null } : null,
    delta_index: prev && prev.index !== null && cur && cur.index !== null ? round4(cur.index - prev.index) : null,
    history
  };
  return checked(out, day);
}

/** Static catalogue fields of a series that time travel may show (allow-list: nothing that changes with the data). */
export const STATIC_SERIES_FIELDS = [
  'key', 'label', 'unit', 'freq', 'branch', 'branch_name', 'question', 'source', 'source_family', 'license', 'revised',
  'lag_days', 'derived_from', 'core', 'reconciliation', 'method', 'aggregation'
] as const;
type StaticKey = (typeof STATIC_SERIES_FIELDS)[number];
export type SeriesStatic = Pick<SeriesDoc, StaticKey>;

export interface SeriesOn {
  day: string;
  meta: SeriesStatic;
  /** versions known on `day` (null: nothing known yet) */
  versions: Versions | null;
  /** latest version per period known on `day`: [{period, value, known}] by period */
  levels: { period: string; value: number; known: string }[];
  /** the record's measures per month end known on `day` */
  history: (MeasureHistory & { known: string[] }) | null;
  /** the record's measure of the latest month known on `day` (when the series was measured that month) */
  measure: (Partial<Measure> & { month: string; kind: string; counted: boolean; known: string }) | null;
  /** the history before rows.backfill_last_known is backfilled with today's version (datakontrakt 5.6) */
  backfilled: boolean;
  /** the series had no version yet on `day` (or it is before a collapse cutoff) */
  empty: boolean;
}

/** One series on `day`. `rec` is the bundle's record (overview.record), for the live snapshot's date. */
export function seriesOn(doc: SeriesDoc, date: string, rec?: RecordInfo | null): SeriesOn {
  const day = toDay(date);
  const meta = {} as Record<string, unknown>;
  for (const k of STATIC_SERIES_FIELDS) if (k in doc) meta[k] = (doc as unknown as Record<string, unknown>)[k];
  const versions = cutVersions(doc.versions, day);
  const levels: SeriesOn['levels'] = [];
  if (versions) {
    const last = new Map<number, number>();
    for (let i = 0; i < versions.p.length; i++) last.set(versions.p[i], i);
    for (const [pi, i] of [...last].sort((a, b) => a[0] - b[0])) levels.push({ period: versions.periods[pi], value: versions.v[i], known: versions.dates[versions.d[i]] });
  }
  const history = cutMeasureHistory(doc.measure_history, day, rec);
  let measure: SeriesOn['measure'] = null;
  if (history) {
    const j = history.months.length - 1;
    measure = {
      month: history.months[j],
      kind: history.kind[j],
      counted: history.counted[j],
      known: history.known[j],
      latest_period: history.latest_period?.[j] ?? null,
      known_from: history.known_from?.[j] ?? null,
      pace: history.pace?.[j] ?? null,
      change_in_pace: history.change_in_pace?.[j] ?? null,
      pace_percentile: history.pace_percentile?.[j] ?? null,
      change_percentile: history.change_percentile?.[j] ?? null,
      direction: history.direction?.[j] ?? null,
      valid: history.valid?.[j] ?? null
    };
  }
  const out: SeriesOn = {
    day,
    meta: meta as SeriesStatic,
    versions,
    levels,
    history,
    measure,
    backfilled: reconstructedOn(doc.rows?.backfill_last_known ?? null, day),
    empty: versions === null
  };
  return checked(out, day);
}

// ------------------------------------------------------------------ the invariant

/** Fields that carry a day something became known. Every one of them in a time-travel object must be <= the day. */
const KNOWN_KEYS = new Set(['dates', 'known_from', 'first_known', 'last_known', 'known', 'collapsed_before']);
const DAY_RE = /^\d{4}-\d{2}-\d{2}/;

/** Every known-day field (any depth) that is later than `day`. Empty = no later knowledge in the object. */
export function leaks(obj: unknown, day: string, path = '$'): string[] {
  const out: string[] = [];
  const visit = (x: unknown, p: string, knownField: boolean) => {
    if (typeof x === 'string') {
      if (knownField && DAY_RE.test(x) && x.slice(0, 10) > day) out.push(`${p} = ${x}`);
    } else if (Array.isArray(x)) x.forEach((y, i) => visit(y, `${p}[${i}]`, knownField));
    else if (x && typeof x === 'object') for (const [k, y] of Object.entries(x)) visit(y, `${p}.${k}`, knownField || KNOWN_KEYS.has(k));
  };
  visit(obj, path, false);
  return out;
}

function checked<T>(obj: T, day: string): T {
  const bad = leaks(obj, day);
  if (bad.length) throw new LeakError(bad);
  return obj;
}
