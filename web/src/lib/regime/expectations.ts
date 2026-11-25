// Expectations against outcomes (register F1, bundle 1.5.0 expectations.json): the view model of the section on
// /avstamningar. Pure: it only selects and words the pipeline's numbers. A row that carries ids only (the series that
// read curated/guidance_capex.csv are withheld, `csv_public` false) is shown as a counted box: company, period and
// date, never a value, size or direction.
import type { Expectations, ExpectationsIndexEntry, ExpectationsRow } from '$lib/data';
import { fmt } from '$lib/design/format';

type Dir = 1 | 0 | -1 | null;

export const COMPANY: Record<string, string> = {
  msft: 'Microsoft',
  googl: 'Alphabet',
  amzn: 'Amazon',
  meta: 'Meta',
  orcl: 'Oracle',
  tsmc: 'TSMC',
  nvda: 'Nvidia'
};
export const companyName = (c: unknown) => (typeof c === 'string' ? (COMPANY[c] ?? c.toUpperCase()) : '');

const num = (x: unknown): number | null => (typeof x === 'number' && Number.isFinite(x) ? x : null);
const str = (x: unknown): string | null => (typeof x === 'string' && x ? x : null);
const dir = (x: unknown): Dir => (x === 1 || x === 0 || x === -1 ? x : null);

export interface IndexCard {
  period: string | null;
  known_from: string | null;
  value: number | null;
  n: number | null;
  up: number | null;
  unchanged: number | null;
  down: number | null;
  percentile: number | null;
  n_history: number | null;
  /** counted but its numbers are not in the bundle (ids only) */
  withheld: boolean;
}

export interface CompanySurprise {
  company: string;
  name: string;
  measure: string | null;
  period: string | null;
  known_from: string | null;
  surprise: number | null;
  z: number | null;
  n: number | null;
  percentile: number | null;
  withheld: boolean;
}

export interface EventView {
  company: string;
  name: string;
  period: string | null;
  known_from: string | null;
  numeric: boolean;
  direction: Dir;
  withheld: boolean;
}

export interface ExpectationsView {
  status: 'live' | 'recon';
  date: string;
  available: boolean;
  error: string | null;
  csvPublic: boolean;
  minEvents: number | null;
  minCompanies: number | null;
  window: number | null;
  revision4q: IndexCard | null;
  revisionQ: IndexCard | null;
  surpriseIndex: IndexCard | null;
  companies: CompanySurprise[];
  events: EventView[];
  breaks: { company: string; name: string; period: string | null; known_from: string | null; withheld: boolean }[];
}

/** The entry's latest row with a value, else its latest row (which then has no value: too few events). */
function card(e: ExpectationsIndexEntry | undefined | null, value: string): IndexCard | null {
  if (!e) return null;
  const r: ExpectationsRow | null = e.latest_with_value ?? e.latest ?? null;
  if (!r) return null;
  const withheld = !(value in r) && !('n' in r);
  return {
    period: str(r.period),
    known_from: str(r.known_from),
    value: num(r[value]),
    n: num(r.n),
    up: num(r.n_up),
    unchanged: num(r.n_unchanged),
    down: num(r.n_down),
    percentile: num(r.percentile),
    n_history: num(r.n_history),
    withheld
  };
}

export function expectationsView(d: Expectations): ExpectationsView {
  const rules = (d.rules ?? {}) as Record<string, unknown>;
  const sur = d.surprise ?? {};
  return {
    status: d.kind === 'skarp' ? 'live' : 'recon',
    date: d.date,
    available: d.available,
    error: str(d.error),
    csvPublic: d.csv_public,
    minEvents: num(rules.min_events),
    minCompanies: num(rules.min_companies),
    window: num(rules.main_window_quarters),
    revision4q: card(d.revisions?.window_4q, 'index'),
    revisionQ: card(d.revisions?.window_1q, 'index'),
    surpriseIndex: card(sur.index, 'value'),
    companies: (sur.companies ?? []).map((c) => ({
      company: String(c.company ?? ''),
      name: companyName(c.company),
      measure: str(c.measure),
      period: str(c.period),
      known_from: str(c.known_from),
      surprise: num(c.surprise),
      z: num(c.z),
      n: num(c.n),
      percentile: num(c.surprise_percentile),
      withheld: !('surprise' in c)
    })),
    events: (d.events_recent ?? []).map((e) => ({
      company: String(e.company ?? ''),
      name: companyName(e.company),
      period: str(e.period),
      known_from: str(e.known_from),
      numeric: e.chain === 'num' || e.chain === 'min',
      direction: dir(e.direction),
      withheld: !('direction' in e)
    })),
    breaks: (d.break_statements ?? []).map((b) => ({
      company: String(b.company ?? ''),
      name: companyName(b.company),
      period: str(b.period),
      known_from: str(b.known_from),
      withheld: !('size' in b)
    }))
  };
}

/** The section's generated sentence (also the accessible summary): what is shown and what is withheld. */
export function expectationsSentence(v: ExpectationsView): string {
  if (!v.available) return 'Förväntningsavsnittet kunde inte räknas för posten.';
  const r = v.revision4q;
  const parts: string[] = [];
  if (r && !r.withheld && r.value !== null)
    parts.push(`Revideringsindexet över ${v.window ?? 4} kvartal är ${fmt(r.value, 2)} med ${r.n ?? '–'} revideringar (${r.up ?? 0} höjningar, ${r.unchanged ?? 0} oförändrade, ${r.down ?? 0} sänkningar).`);
  else if (r && r.withheld) parts.push('Revideringsindexet räknas, men dess värde visas inte än.');
  else parts.push('Revideringsindexet har för få revideringar för ett värde.');
  const s = v.surpriseIndex;
  if (s && !s.withheld && s.value !== null) parts.push(`Överraskningsindexet är ${fmt(s.value, 2)}.`);
  else if (s && s.withheld) parts.push('Överraskningsindexet räknas, men dess värde visas inte än.');
  const shown = v.companies.filter((c) => !c.withheld && c.surprise !== null);
  if (shown.length) parts.push(`Överraskning mot egen guidance visas för ${shown.map((c) => c.name).join(', ')}.`);
  return parts.join(' ');
}
