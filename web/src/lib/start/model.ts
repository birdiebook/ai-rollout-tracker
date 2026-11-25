// Start page (W5): the view model. Pure functions from the bundle documents (overview.json, flow.json, nowcast/*.json,
// series/index.json) to exactly what the page draws, so the page data stays small (it is inlined in the HTML) and
// every generated sentence can be tested without a DOM. Nothing here recomputes a pipeline measure: states, indices,
// percentiles, coverage and intervals come from the bundle; this file only selects, orders and words them.

import type { CalendarEntry, Flow, Manifest, Nowcast, Overview, RecordMeta, SeriesIndex } from '$lib/data';
import { fmt } from '$lib/design/format';

/** Months of index history in each lead's sparkline (vision 3.1: "diffusionsindex 24 månader bakåt"). */
export const SPARK_MONTHS = 24;

/** C4's registered threshold (docs/mattregister.md F-D2: a shift needs two consecutive months >= 0.8, back at <= 0.2).
 *  Not in the bundle yet (regime.json/overview.json carry no threshold); drawn as a reference line only. */
export const REGIME_HIGH = 0.8;
export const REGIME_LOW = 0.2;

// "för få källor": index v2's no-state (fewer than 3 counted source families, the official rule from the snapshot
// 2026-11-30); "för få serier": v1's, kept for records before v2 and for v1 beside v2.
export type State = 'accelererar' | 'stabil' | 'bromsar in' | 'för få källor' | 'för få serier' | 'inga registrerade kärnserier';
export const NO_STATE: State[] = ['för få källor', 'för få serier', 'inga registrerade kärnserier'];
const ALL_STATES: State[] = ['accelererar', 'stabil', 'bromsar in', 'för få källor', 'för få serier', 'inga registrerade kärnserier'];
export const WITH_STATE: State[] = ['accelererar', 'stabil', 'bromsar in'];

// ---------- shapes (what the page receives) ----------

export interface BranchView {
  code: string;
  name: string;
  question: string;
  state: State;
  index: number | null;
  n_series: number;
  n_up: number;
  n_neutral: number;
  n_down: number;
  n_withheld_counted: number;
  /** index v2 (bundle 1.4.0): rule, counted source families and v1 beside; v1 fields null on an older bundle */
  rule_version: 'v1' | 'v2';
  n_families: number | null;
  index_v1: number | null;
  state_v1: State | null;
  prev: { month: string | null; index: number | null; state: State | null } | null;
  state_changed: boolean;
}

export interface LeadBranch {
  code: string;
  /** the other lead that shows the same branch (L4 and L3 share G4, L7 and L5 share G5) */
  alsoIn: string[];
}

export interface LeadView {
  code: string;
  name: string;
  short: string[];
  content: string;
  branches: LeadBranch[];
  /** one state for the lead when all its branches agree, otherwise 'blandat' */
  state: State | 'blandat';
  nowcasts: { id: string; label: string; title: string }[];
}

export interface SparkView {
  months: string[];
  kind: ('skarp' | 'rekonstruerad' | null)[];
  index: (number | null)[];
  state: (State | null)[];
}

export interface ForecastView {
  id: string;
  label: string;
  title: string;
  unit: string;
  decimals: number;
  period: string;
  origin: string;
  value: number;
  champion: string;
  intervals: Record<'50' | '80' | '95', [number, number]>;
}

export interface CalibrationView {
  id: string;
  label: string;
  title: string;
  model: string;
  n: number;
  first: string | null;
  last: string | null;
  rows: { level: '50' | '80' | '95'; coverage: number | null; band: [number, number] | null }[];
}

export interface ReconView {
  key: string;
  short: string;
  label: string;
  lead: string;
  pace_percentile: number | null;
  direction: 1 | 0 | -1 | null;
  pace: number | null;
  pace_unit: string;
  latest_period: string | null;
  known_from: string | null;
  linkable: boolean;
}

export interface StartData {
  record: Pick<RecordMeta, 'status' | 'label' | 'month' | 'date'> & { first_live_date: string | null };
  today: string;
  headline: {
    sentence: string;
    chainSentence: string;
    changeSentence: string;
    counts: Record<State, number>;
    nWithState: number;
    prevMonth: string | null;
    changes: { code: string; name: string; from: State; to: State }[];
    /** index v2 against v1 this month: the branches whose state differs, or '' (v1 bundle, or no difference) */
    v1Sentence: string;
  };
  facts: { n_series: number | null; n_published: number | null; n_withheld: number | null; fetched: string | null };
  branches: BranchView[];
  leads: LeadView[];
  sparks: Record<string, SparkView>;
  stripes: Overview['stripes'];
  thresholds: { low: number; high: number };
  calendar: Pick<CalendarEntry, 'id' | 'label' | 'title' | 'next_origin' | 'next_period' | 'n_live'>[];
  forecast: ForecastView | null;
  calibration: CalibrationView | null;
  regime: { available: boolean; blocks: { block: string; label: string; month: string | null; p_slow: number | null; state: string | null; shift: string | null }[] };
  reconciliations: ReconView[];
  nWithheldFlow: number;
}

// ---------- wording (Swedish, neutral, generated) ----------

/** "a", "a och b", "a, b och c" */
export function joinSv(items: string[]): string {
  if (items.length <= 1) return items.join('');
  return `${items.slice(0, -1).join(', ')} och ${items.at(-1)}`;
}

/** Consecutive lead codes as ranges: [L3, L4, L5, L6, L8] -> ["L3–L6", "L8"]. */
export function leadRanges(codes: string[]): string[] {
  const nums = codes.map((c) => Number(c.slice(1))).sort((a, b) => a - b);
  const out: string[] = [];
  let i = 0;
  while (i < nums.length) {
    let j = i;
    while (j + 1 < nums.length && nums[j + 1] === nums[j] + 1) j++;
    if (j - i >= 2) out.push(`L${nums[i]}–L${nums[j]}`);
    else for (let k = i; k <= j; k++) out.push(`L${nums[k]}`);
    i = j + 1;
  }
  return out;
}

const VERB: Record<State | 'blandat', [string, string]> = {
  accelererar: ['accelererar', 'accelererar'],
  stabil: ['är stabilt', 'är stabila'],
  'bromsar in': ['bromsar in', 'bromsar in'],
  'för få källor': ['har för få källor', 'har för få källor'],
  'för få serier': ['har för få serier', 'har för få serier'],
  'inga registrerade kärnserier': ['saknar registrerade kärnserier', 'saknar registrerade kärnserier'],
  blandat: ['har grenar i olika tillstånd', 'har grenar i olika tillstånd']
};
const CHAIN_ORDER: (State | 'blandat')[] = ['accelererar', 'stabil', 'bromsar in', 'blandat', 'för få källor', 'för få serier', 'inga registrerade kärnserier'];

/** The chain in one generated sentence, states in a fixed order (never ordered by "good" or "bad"):
 *  "I kedjan: L3–L6 och L8 accelererar, L2 och L9 är stabila, L7 har grenar i olika tillstånd och L1 har för få serier." */
export function chainSentence(leads: Pick<LeadView, 'code' | 'state'>[]): string {
  const parts: string[] = [];
  for (const s of CHAIN_ORDER) {
    const codes = leads.filter((l) => l.state === s).map((l) => l.code);
    if (codes.length) parts.push(`${joinSv(leadRanges(codes))} ${VERB[s][codes.length > 1 ? 1 : 0]}`);
  }
  return parts.length ? `I kedjan: ${joinSv(parts)}.` : '';
}

/** site_bundle.export._sv_number: 0 -> "ingen", 1 -> "en", otherwise the digits. */
export const svNumber = (n: number): string => (n === 0 ? 'ingen' : n === 1 ? 'en' : String(n));

/** Fallback for the headline when the bundle has none (the pipeline's own sentence is preferred, it is the record).
 *  The same words as site_bundle.export.headline, so the two cannot drift unnoticed (tested on every bundle). */
export function countsSentence(counts: Partial<Record<State, number>>): string {
  const n = WITH_STATE.reduce((a, s) => a + (counts[s] ?? 0), 0);
  if (n === 0) return 'Ingen gren har ännu tillräckligt många källor för ett tillstånd.';
  const a = counts.accelererar ?? 0;
  const s = counts.stabil ?? 0;
  const b = counts['bromsar in'] ?? 0;
  return `Av ${n} grenar med tillstånd: ${svNumber(a)} accelererar, ${svNumber(s)} ${s === 1 ? 'är stabil' : 'är stabila'} och ${svNumber(b)} bromsar in.`;
}

/** Index v2 against v1 in one neutral sentence: which branches v1 (one vote per series) would put in another state. */
export function v1Sentence(branches: Pick<BranchView, 'code' | 'state' | 'state_v1' | 'rule_version'>[]): string {
  // "för få källor" against "för få serier" is the same picture (no state), so only a real difference is named
  const none = (x: State | null) => x !== null && NO_STATE.includes(x);
  const diff = branches.filter((b) => b.rule_version === 'v2' && b.state_v1 !== null && b.state_v1 !== b.state && !(none(b.state) && none(b.state_v1)));
  if (!branches.some((b) => b.rule_version === 'v2')) return '';
  if (!diff.length) return 'Med regel v1, en röst per serie, hade alla grenar samma tillstånd.';
  return `Med regel v1, en röst per serie, hade ${joinSv(diff.map((b) => `${b.code} ${V1_SUPINE[b.state_v1 as State]}`))}.`;
}
const V1_SUPINE: Record<State, string> = {
  accelererar: 'accelererat',
  stabil: 'varit stabil',
  'bromsar in': 'bromsat in',
  'för få källor': 'haft för få källor',
  'för få serier': 'haft för få serier',
  'inga registrerade kärnserier': 'saknat registrerade kärnserier'
};

// ---------- selection ----------

const asState = (s: unknown): State => (typeof s === 'string' && s in VERB && s !== 'blandat' ? (s as State) : 'för få källor');
const num = (x: unknown): number | null => (typeof x === 'number' && Number.isFinite(x) ? x : null);
const int = (x: unknown): number => (typeof x === 'number' && Number.isFinite(x) ? x : 0);
const str = (x: unknown): string => (typeof x === 'string' ? x : '');

type Obj = Record<string, unknown>;
const arr = (x: unknown): Obj[] => (Array.isArray(x) ? (x as Obj[]) : []);

export function branchViews(ov: Overview): BranchView[] {
  return ov.branches.map((b) => {
    const p = (b.previous ?? null) as Obj | null;
    return {
      code: b.code,
      name: b.name,
      question: str(b.question),
      state: asState(b.state),
      index: num(b.index),
      n_series: int(b.n_series),
      n_up: int(b.n_up),
      n_neutral: int(b.n_neutral),
      n_down: int(b.n_down),
      n_withheld_counted: int(b.n_withheld_counted),
      rule_version: b.rule_version === 'v2' ? 'v2' : 'v1',
      n_families: num(b.n_families),
      index_v1: num(b.index_v1),
      state_v1: typeof b.state_v1 === 'string' ? asState(b.state_v1) : null,
      prev: p ? { month: str(p.month) || null, index: num(p.index), state: p.state ? asState(p.state) : null } : null,
      state_changed: b.state_changed === true
    };
  });
}

export function leadViews(flow: Flow, branches: BranchView[]): LeadView[] {
  const leads = arr(flow.leads);
  const where = new Map<string, string[]>();
  for (const l of leads) for (const b of arr(l.branches)) where.set(str(b.code), [...(where.get(str(b.code)) ?? []), str(l.code)]);
  const byCode = new Map(branches.map((b) => [b.code, b]));
  return leads.map((l) => {
    const codes = arr(l.branches).map((b) => str(b.code));
    const states = [...new Set(codes.map((c) => byCode.get(c)?.state ?? 'för få källor'))];
    return {
      code: str(l.code),
      name: str(l.name),
      short: Array.isArray(l.short) ? (l.short as string[]) : [str(l.name)],
      content: str(l.content),
      branches: codes.map((c) => ({ code: c, alsoIn: (where.get(c) ?? []).filter((x) => x !== l.code) })),
      state: states.length === 1 ? states[0] : 'blandat',
      nowcasts: arr(l.nowcasts).map((n) => ({ id: str(n.id), label: str(n.label), title: str(n.title) }))
    };
  });
}

export function sparkViews(ov: Overview, months = SPARK_MONTHS): Record<string, SparkView> {
  const m = ov.stripes.months;
  const from = Math.max(0, m.length - months);
  const kind = (ov.stripes.kind ?? []).slice(from).map((k) => (k === 'skarp' || k === 'rekonstruerad' ? k : null));
  return Object.fromEntries(
    ov.stripes.rows.map((r) => [
      r.code,
      { months: m.slice(from), kind, index: r.index.slice(from).map(num), state: (r.state ?? []).slice(from).map((s) => (s ? asState(s) : null)) }
    ])
  );
}

/** The latest live forecast with intervals for its champion (null before the first one). */
export function latestForecast(nowcasts: Nowcast[]): ForecastView | null {
  let best: ForecastView | null = null;
  for (const n of nowcasts) {
    for (const f of arr(n.forecasts)) {
      const iv = f.intervals as Record<string, [number, number]> | undefined;
      const value = num(f.value);
      if (!iv || value === null || !iv['50'] || !iv['80'] || !iv['95']) continue;
      const v: ForecastView = {
        id: n.id,
        label: str(n.label) || n.id.toUpperCase(),
        title: n.title,
        unit: str(n.unit),
        decimals: int(n.decimals),
        period: str(f.period),
        origin: str(f.origin),
        value,
        champion: str(f.champion) || str(n.champion),
        intervals: { '50': iv['50'], '80': iv['80'], '95': iv['95'] }
      };
      if (!best || v.origin > best.origin) best = v;
    }
  }
  return best;
}

/** Stored quantiles of a forecast from its central value and its 50/80/95 intervals (for the 20 dots). */
export function forecastQuantiles(f: ForecastView): [number, number][] {
  const i = f.intervals;
  return [
    [0.025, i['95'][0]],
    [0.1, i['80'][0]],
    [0.25, i['50'][0]],
    [0.5, f.value],
    [0.75, i['50'][1]],
    [0.9, i['80'][1]],
    [0.975, i['95'][1]]
  ];
}

/** Which nowcast the "where are we heading" card follows: the one with the latest live forecast, otherwise the next
 *  live forecast in the calendar (ties: calendar order). D2 (horizons, a shadow) is never the focus. */
export function focusNowcast(calendar: CalendarEntry[], forecast: ForecastView | null): string | null {
  if (forecast) return forecast.id;
  const next = calendar
    .filter((c) => c.id !== 'd2' && c.next_origin)
    .sort((a, b) => String(a.next_origin).localeCompare(String(b.next_origin)))[0];
  return next?.id ?? null;
}

/** The champion's backtest coverage per level (always labelled backtest on the page). */
export function calibrationView(n: Nowcast | null | undefined): CalibrationView | null {
  if (!n) return null;
  const bc = (n.backtest_calibration ?? null) as Obj | null;
  if (!bc || bc.available === false) return null;
  const row = arr(bc.rows).find((r) => r.model === n.champion);
  if (!row) return null;
  const band = (x: unknown): [number, number] | null =>
    Array.isArray(x) && x.length === 2 && x.every((v) => typeof v === 'number') ? (x as [number, number]) : null;
  return {
    id: n.id,
    label: str(n.label) || n.id.toUpperCase(),
    title: n.title,
    model: String(n.champion),
    n: int(row.n),
    first: str(row.first) || null,
    last: str(row.last) || null,
    rows: (['50', '80', '95'] as const).map((level) => ({ level, coverage: num(row[`coverage_${level}`]), band: band(row[`band_${level}`]) }))
  };
}

export function reconViews(flow: Flow, linkable: Set<string>): ReconView[] {
  return arr(flow.reconciliations).map((r) => ({
    key: str(r.key),
    short: str(r.short) || str(r.label),
    label: str(r.label),
    lead: str(r.lead),
    pace_percentile: num(r.pace_percentile),
    direction: r.direction === 1 || r.direction === 0 || r.direction === -1 ? r.direction : null,
    pace: num(r.pace),
    pace_unit: str(r.pace_unit),
    latest_period: str(r.latest_period) || null,
    known_from: str(r.known_from) || null,
    linkable: linkable.has(str(r.key))
  }));
}

/** Everything the start page draws, from the bundle documents. */
export function startData(input: {
  manifest: Manifest;
  overview: Overview;
  flow: Flow;
  nowcasts: Nowcast[];
  seriesIndex: SeriesIndex;
}): StartData {
  const { manifest, overview: ov, flow, nowcasts, seriesIndex } = input;
  const branches = branchViews(ov);
  const leads = leadViews(flow, branches);
  const counts = Object.fromEntries(
    ALL_STATES.map((s) => [s, int(ov.headline.counts?.[s])])
  ) as Record<State, number>;
  const forecast = latestForecast(nowcasts);
  const focus = focusNowcast(ov.calendar, forecast);
  const facts = (ov.facts ?? {}) as Obj;
  const regime = (ov.regime ?? { available: false, blocks: [] }) as { available: boolean; blocks: Obj[] };
  const changes = arr(ov.headline.changes).map((c) => ({ code: str(c.code), name: str(c.name), from: asState(c.from), to: asState(c.to) }));
  return {
    record: {
      status: ov.record.status,
      label: ov.record.label,
      month: ov.record.month,
      date: ov.record.date,
      first_live_date: str(ov.record.first_live_date) || null
    },
    today: str(manifest.today) || str(manifest.built_utc).slice(0, 10) || ov.record.date,
    headline: {
      sentence: ov.headline.sentence || countsSentence(counts),
      chainSentence: chainSentence(leads),
      changeSentence: ov.headline.change_sentence ?? '',
      counts,
      nWithState: WITH_STATE.reduce((a, s) => a + counts[s], 0),
      prevMonth: branches.find((b) => b.prev?.month)?.prev?.month ?? null,
      changes,
      v1Sentence: v1Sentence(branches)
    },
    facts: {
      n_series: num(facts.n_series),
      n_published: num(facts.n_published),
      n_withheld: num(facts.n_withheld),
      fetched: str(facts.table_max_fetched_at) || null
    },
    branches,
    leads,
    sparks: sparkViews(ov),
    // only what the stripes draw: the page data is inlined in the HTML (the v2 arrays per month stay in the bundle)
    stripes: {
      months: ov.stripes.months,
      kind: ov.stripes.kind,
      rows: ov.stripes.rows.map((r) => ({ code: r.code, name: r.name, index: r.index, state: r.state })),
      thresholds: ov.stripes.thresholds
    },
    thresholds: { low: ov.stripes.thresholds.braking_at_most, high: ov.stripes.thresholds.accelerating_at_least },
    calendar: ov.calendar.map((c) => ({ id: c.id, label: c.label, title: c.title, next_origin: c.next_origin, next_period: c.next_period, n_live: c.n_live })),
    forecast,
    calibration: calibrationView(nowcasts.find((n) => n.id === focus)),
    regime: {
      available: regime.available === true,
      blocks: arr(regime.blocks).map((b) => ({
        block: str(b.block),
        label: str(b.label) || str(b.block),
        month: str(b.month) || null,
        p_slow: num(b.p_slow),
        state: str(b.state) || null,
        shift: str(b.shift) || null
      }))
    },
    reconciliations: reconViews(flow, new Set(seriesIndex.series.map((s) => s.key))),
    nWithheldFlow: arr(flow.withheld).length
  };
}

// ---------- generated sentences for the charts (also their accessible descriptions, vision 4.3) ----------

const f2 = (x: number | null) => fmt(x, 2); // fmt avoids Intl's start-up cost (R-W2 P1)

/** Q1: where the branches are now, and the largest move since last month. */
export function nowDescription(branches: BranchView[], monthLabel: string, prevLabel: string | null): string {
  const withIdx = branches.filter((b) => b.index !== null);
  const moves = withIdx
    .filter((b) => b.prev?.index !== null && b.prev?.index !== undefined)
    .map((b) => ({ b, d: (b.index as number) - (b.prev!.index as number) }))
    .filter((m) => Math.abs(m.d) >= 0.005)
    .sort((a, z) => Math.abs(z.d) - Math.abs(a.d) || a.b.code.localeCompare(z.b.code));
  const head = `Diffusionsindex för ${withIdx.length} av ${branches.length} grenar i ${monthLabel} (prick)${prevLabel ? ` och ${prevLabel} (ring)` : ''}.`;
  if (!prevLabel) return head;
  if (!moves.length) return `${head} Ingen gren har flyttat sig sedan förra månaden.`;
  const m = moves[0];
  return `${head} Störst förflyttning: ${m.b.code} från ${f2(m.b.prev!.index)} till ${f2(m.b.index)}.`;
}

export function upcoming(calendar: StartData['calendar']) {
  const groups = new Map<string, StartData['calendar']>();
  for (const c of calendar.filter((c) => c.id !== 'd2' && c.next_origin).sort((a, b) => String(a.next_origin).localeCompare(String(b.next_origin)) || a.id.localeCompare(b.id)))
    groups.set(c.next_origin as string, [...(groups.get(c.next_origin as string) ?? []), c]);
  return [...groups.entries()].map(([date, items]) => ({ date, items }));
}

/** Q2: the calendar in words. `dl` formats a date ("5 dec 2026"), `pl` a period. */
export function calendarDescription(calendar: StartData['calendar'], dl: (d: string) => string, pl: (p: string) => string): string {
  const g = upcoming(calendar);
  if (!g.length) return 'Ingen skarp prognos är planerad.';
  const [first, ...rest] = g;
  const one = first.items.length === 1 ? first.items[0] : null;
  const head = one
    ? `Nästa skarpa prognos: ${one.label} (${one.title}${one.next_period ? `, ${pl(one.next_period)}` : ''}) lämnas ${dl(first.date)}.`
    : `Nästa skarpa prognoser: ${joinSv(first.items.map((c) => c.label))} lämnas ${dl(first.date)}.`;
  if (!rest.length) return head;
  return `${head} Därefter ${joinSv(rest.map((r) => `${joinSv(r.items.map((c) => c.label))} den ${dl(r.date)}`))}.`;
}

/** Q2: the champion's backtest coverage in frequency words, with the levels outside their binomial band named. */
export function calibrationDescription(c: CalibrationView): string {
  const pct = (x: number | null) => (x === null ? '–' : `${Math.round(x * 100)} %`);
  const span = c.first && c.last ? ` ${c.first.slice(0, 4)}–${c.last.slice(0, 4)}` : '';
  const lv = c.rows.map((r) => `${pct(r.coverage)} inom ${r.level} %-intervallet`);
  const outside = c.rows.filter((r) => r.coverage !== null && r.band && (r.coverage < r.band[0] || r.coverage > r.band[1]));
  const tail = outside.length
    ? ` ${joinSv(outside.map((r) => `${r.level} %`))}-nivån ligger utanför slumpbandet.`
    : ' Alla nivåer ligger inom slumpbandet.';
  return `Backtest av ${c.label}:s huvudmodell ${c.model}, ${c.n} prognoser${span}: ${joinSv(lv)}.${tail}`;
}

/** Q3: where each reconciliation's pace is in its own history. */
export function reconDescription(r: ReconView[]): string {
  const known = r.filter((x) => x.pace_percentile !== null);
  if (!known.length) return 'Inga avstämningar har mått ännu.';
  const s = [...known].sort((a, b) => (b.pace_percentile as number) - (a.pace_percentile as number));
  return `Takten i ${known.length} ${known.length === 1 ? 'avstämning' : 'avstämningar'} mellan leden, som percentil av sin egen historik: ${joinSv(s.map((x) => `${x.short} ${Math.round(x.pace_percentile as number)}`))}.`;
}

/** Q1's answer: how many branch indices moved up, down or not at all since last month. */
export function moveCounts(branches: BranchView[]): { up: number; down: number; same: number; n: number } {
  let up = 0, down = 0, same = 0;
  for (const b of branches) {
    if (b.index === null || b.prev?.index === null || b.prev?.index === undefined) continue;
    const dlt = b.index - b.prev.index;
    if (dlt > 0.005) up++;
    else if (dlt < -0.005) down++;
    else same++;
  }
  return { up, down, same, n: up + down + same };
}
