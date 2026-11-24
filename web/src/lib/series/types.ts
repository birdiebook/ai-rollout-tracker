// Types of one series document (series/<key>.json, docs/steg3/datakontrakt.md "series/<nyckel>.json", schema
// series.json in the bundle). Kept here (W7) and not in $lib/data/types.ts so that wave-1 tracks do not collide in
// the shared file; `SeriesDoc` is the loader's `Series` with every field the contract defines (cast from it).
export type Freq = 'D' | 'W' | '2W' | 'M' | 'Q' | 'A';
export type Direction = 1 | 0 | -1;
export type Method = 'log' | 'share' | 'logit' | 'doubling' | 'halving';

/** versions-v1 (datakontrakt section 5): one row per version, p/d/v sorted by (date, period). */
export interface Versions {
  encoding: 'versions-v1';
  freq: Exclude<Freq, 'D'>;
  native_freq: Freq;
  aggregation: 'mean' | 'sum' | null;
  periods: string[];
  /** distinct known_from days, ascending */
  dates: string[];
  p: number[];
  d: number[];
  v: number[];
  n_versions: number;
  n_revised_periods: number;
  first_known: string;
  last_known: string;
  collapsed_before: string | null;
}

/** common.json measure_fields (the state engine's numbers on the record date). */
export interface Measure {
  series?: string;
  entry?: string;
  method?: Method | null;
  freq?: Freq | null;
  measure_freq?: Freq | null;
  latest_period?: string | null;
  known_from?: string | null;
  sources?: string[] | null;
  level?: number | null;
  pace_unit?: string | null;
  pace?: number | null;
  change_in_pace?: number | null;
  pace_percentile?: number | null;
  change_percentile?: number | null;
  n_pace?: number | null;
  n_change?: number | null;
  surprise?: number | null;
  surprise_basis?: string | null;
  sd_change?: number | null;
  deadband?: number | null;
  direction?: Direction | null;
  valid?: boolean | null;
  reason?: string | null;
  flag?: string | null;
  resolved?: unknown;
  own_snapshot_months?: number | null;
}

export interface MeasurePath {
  periods: string[];
  pace: (number | null)[];
  change: (number | null)[];
}

/** The record's measure at every month end of the stripes (columnar). */
export interface MeasureHistory {
  months: string[];
  kind: ('skarp' | 'rekonstruerad' | string)[];
  counted: boolean[];
  latest_period?: (string | null)[];
  known_from?: (string | null)[];
  pace?: (number | null)[];
  change_in_pace?: (number | null)[];
  pace_percentile?: (number | null)[];
  change_percentile?: (number | null)[];
  direction?: (Direction | null)[];
  valid?: (boolean | null)[];
}

export interface Levels {
  as_of: string;
  periods: string[];
  values: (number | null)[];
}

/** Every field of a series document except `versions`. */
export interface SeriesFields {
  key: string;
  label: string;
  unit: string;
  freq: Freq;
  branch: string;
  branch_name?: string;
  question?: string;
  source: string;
  source_family?: string;
  license: { short: string; text: string; attribution: string };
  revised?: boolean;
  lag_days?: number | null;
  derived_from?: string[] | null;
  core?: boolean;
  reconciliation?: boolean;
  in_record?: boolean;
  counted?: boolean;
  record_branch?: string | null;
  method?: Method | null;
  aggregation?: 'mean' | 'sum' | null;
  measure_as_of: string;
  measure: Measure | null;
  measure_path: MeasurePath | null;
  measure_history: MeasureHistory | null;
  levels: Levels | null;
  rows?: { counts?: Record<string, number>; backfill_last_known?: string | null } | null;
}

export type SeriesDoc = SeriesFields & { versions: Versions | null };
