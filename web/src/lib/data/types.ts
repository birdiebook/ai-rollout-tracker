// Types of the site_bundle documents the pages read (built by Python, track W3: `python -m ai_tracker.site_bundle
// build`; JSON Schema in the bundle's schema/). Only the fields the skeleton relies on are typed strictly; every
// document keeps an index signature so wave-1 tracks can type more fields without breaking the others.
// Paths (relative to the bundle root): manifest.json, overview.json, flow.json, method.json, withheld.json,
// branch/<G>.json, series/index.json, series/<key>.json, nowcast/<id>.json, regime.json.

export type StateName = 'accelererar' | 'stabil' | 'bromsar in' | 'för få serier' | 'inga registrerade kärnserier';

/** The record a document was built from: live snapshot or reconstructed history (P9: always shown). */
export interface RecordMeta {
  status: 'live' | 'reconstructed';
  label: string;
  month: string;
  date: string;
  first_live_date?: string | null;
  live_months?: string[];
  [k: string]: unknown;
}

export interface Manifest {
  schema_version: string | number;
  /** true only for the provisional W4 fixture (synthetic values) */
  provisional?: boolean;
  note?: string;
  build?: { built_utc?: string; git_sha?: string; repo?: string; [k: string]: unknown };
  documents?: string[];
  [k: string]: unknown;
}

export interface BranchTile {
  code: string;
  name: string;
  question?: string;
  index: number | null;
  state: StateName | null;
  n_series?: number | null;
  previous?: { index: number | null; state: StateName | null; [k: string]: unknown } | null;
  delta_index?: number | null;
  state_changed?: boolean | null;
  [k: string]: unknown;
}

export interface Stripes {
  months: string[];
  /** record kind per month: 'skarp' | 'rekonstruerad' */
  kind: (string | null)[];
  rows: { code: string; name: string; index: (number | null)[]; state: (StateName | null)[]; n_series?: (number | null)[] }[];
  thresholds: { braking_at_most: number; accelerating_at_least: number };
}

export interface CalendarEntry {
  id: string;
  label: string;
  title: string;
  champion: string | null;
  next_origin: string | null;
  next_period: string | null;
  n_live: number;
}

export interface Overview {
  record: RecordMeta;
  headline: { month: string; sentence: string; change_sentence: string; counts: Record<string, number>; [k: string]: unknown };
  branches: BranchTile[];
  stripes: Stripes;
  calendar: CalendarEntry[];
  regime?: { available: boolean; blocks: unknown[] };
  facts?: Record<string, number | string | null>;
  [k: string]: unknown;
}

export interface Branch extends BranchTile {
  record: RecordMeta;
}

export interface SeriesIndexEntry {
  key: string;
  label: string;
  branch: string | null;
  freq: string | null;
  unit: string | null;
  license: string;
  core?: boolean;
  counted?: boolean;
  first_period?: string | null;
  latest_period?: string | null;
  direction?: 1 | 0 | -1 | null;
  [k: string]: unknown;
}

export interface SeriesIndex {
  as_of: string;
  n: number;
  series: SeriesIndexEntry[];
}

export interface Series {
  key: string;
  label: string;
  unit: string | null;
  freq: string | null;
  branch: string | null;
  source: string;
  license: { short: string; text: string; attribution: string };
  levels: { as_of: string; periods: string[]; values: (number | null)[] } | null;
  measure?: Record<string, unknown> | null;
  [k: string]: unknown;
}

export interface Nowcast {
  id: string;
  label: string;
  title: string;
  champion: string | null;
  next_origin: string | null;
  next_period: string | null;
  publishable?: boolean;
  [k: string]: unknown;
}

export interface Flow {
  record?: RecordMeta;
  [k: string]: unknown;
}

export interface Method {
  [k: string]: unknown;
}

export const BRANCH_CODES = ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9'] as const;
export type BranchCode = (typeof BRANCH_CODES)[number];
