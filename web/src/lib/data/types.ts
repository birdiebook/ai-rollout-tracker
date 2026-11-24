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
  /** bundle schema version, semver (W3: "version"; "schema_version" accepted too) */
  version?: string;
  schema_version?: string;
  /** true for fixtures (synthetic values): the site then shows a "Testdata" note */
  synthetic?: boolean;
  /** true only for W4's provisional fixture */
  provisional?: boolean;
  note?: string;
  built_utc?: string;
  git_sha?: string;
  repo?: string;
  snapshot?: RecordMeta;
  files?: { path: string; schema?: string; bytes?: number; gzip_bytes?: number; sha256?: string }[];
  [k: string]: unknown;
}

export const schemaVersion = (m: Manifest): string => String(m.version ?? m.schema_version ?? '');

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

export type IntervalLevel = '50' | '80' | '95';
export type Pair = [number | null, number | null] | null;

/** A committed live forecast file (forecasts/<n>/*.json, W3 schema nowcast#/$defs/forecast). */
export interface LiveForecast {
  period: string | null;
  file: string;
  value: number | null;
  champion: string;
  origin?: string;
  registered_origin?: string;
  variants?: Record<string, number | null>;
  intervals?: Partial<Record<IntervalLevel, Pair>>;
  [k: string]: unknown;
}

/** One forecast file against the first vintage of its outcome. Model columns are err_<m>, crps_<m>, pit_<m>,
 *  hit_<level>_<m> (m includes "champion"), intervals interval_<level>. */
export interface ScoreRow {
  period: string;
  status: string;
  origin?: string | null;
  champion?: string | null;
  forecast?: number | null;
  outcome?: number | null;
  known_from?: string | null;
  [k: string]: unknown;
}

/** Coverage with a binomial band per level (live: `coverage[]`; backtest: `backtest_calibration.rows[]`). */
export interface CoverageRow {
  variant?: string;
  model?: string;
  n: number;
  crps?: number | null;
  [k: string]: unknown;
}

export interface BacktestCalibration {
  available: boolean;
  rows: (CoverageRow & { model: string; calibrated?: boolean | null; pit_mean?: number | null; pit_var?: number | null; first?: string; last?: string })[];
  n_periods?: number | null;
  first?: string | null;
  last?: string | null;
  best_baseline?: string | null;
  champion_mae?: { mae: number | null; n: number; first?: string; last?: string } | null;
  error?: string | null;
  [k: string]: unknown;
}

export interface SeriesValues {
  periods: string[];
  values: (number | null)[];
}

export interface Nowcast {
  id: string;
  label: string;
  title: string;
  champion: string | null;
  next_origin: string | null;
  next_period: string | null;
  publishable?: boolean;
  record?: RecordMeta;
  target?: string | null;
  target_label?: string | null;
  unit?: string | null;
  source?: string | null;
  license?: string | null;
  decimals?: number | null;
  error_unit?: string | null;
  frequency?: string | null;
  origin_rule?: string | null;
  results_doc?: string | null;
  shadows?: string[];
  variants?: { id: string; text: string }[];
  forecasts?: LiveForecast[];
  scorecard?: ScoreRow[];
  summary?: { variant: string; n: number; mae?: number | null; bias?: number | null }[];
  scorecard_error?: string | null;
  coverage?: CoverageRow[];
  interval_levels?: string[];
  history?: SeriesValues | null;
  backtest_calibration?: BacktestCalibration | null;
  [k: string]: unknown;
}

/** nowcast/d2.json (W3 schema `horizons`): D2, 1–8 quarters ahead, a shadow. */
export interface HorizonTarget {
  id: string;
  name: string;
  target: string;
  label: string;
  unit: string;
  publishable: boolean;
  models: string[];
  champion_by_group: Record<string, string>;
  base: string | null;
  fan: {
    periods: string[];
    champion: string[];
    values: (number | null)[];
    intervals: Partial<Record<IntervalLevel, { lo: (number | null)[]; hi: (number | null)[] }>>;
  } | null;
  paths: { h: number; quarter: string; champion: string; value: number | null; models: Record<string, number | null>; interval_80?: Pair }[] | null;
  history: SeriesValues | null;
  summary: ({ h: number; group: string; n: number; n_dist?: number; crps?: number | null } & Record<string, unknown>)[] | null;
  [k: string]: unknown;
}

export interface Horizons {
  record: RecordMeta;
  first_live: string;
  origin: string | null;
  file: string | null;
  next_origin: string | null;
  next_period: string | null;
  groups: Record<string, number[]>;
  interval_levels: string[];
  targets: HorizonTarget[];
  error: string | null;
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
