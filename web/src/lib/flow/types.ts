// Types for the lead and branch pages (track W6). They type the parts of flow.json and branch/<G>.json that these
// pages read (W3 schema: schema/flow.json, schema/branch.json, common.json#series_entry/withheld_entry/aggregate),
// plus the compact shapes the server loads hand to the pages. Candidates to lift into $lib/data/types.ts.
import type { Branch, RecordMeta, StateName } from '$lib/data';

export type Dir = 1 | 0 | -1 | null;

export interface MeasurePath {
  periods: string[];
  pace: (number | null)[];
  change: (number | null)[];
}

/** common.json#series_entry: measures + catalog metadata + the measure path (publishable series only). */
export interface SeriesEntry {
  key: string;
  label: string;
  unit?: string;
  question?: string;
  source?: string;
  license?: string;
  method?: 'log' | 'share' | 'logit' | 'doubling' | 'halving' | null;
  freq?: string | null;
  measure_freq?: string | null;
  latest_period?: string | null;
  known_from?: string | null;
  level?: number | null;
  pace_unit?: string | null;
  pace?: number | null;
  change_in_pace?: number | null;
  pace_percentile?: number | null;
  change_percentile?: number | null;
  deadband?: number | null;
  sd_change?: number | null;
  direction?: Dir;
  valid?: boolean;
  reason?: string;
  path?: MeasurePath | null;
  counted?: boolean;
  branch?: string | null;
  in_core?: boolean;
  short?: string;
  span?: number[] | null;
  lead?: string | null;
}

/** common.json#withheld_entry: names and reasons, never values or a per-series direction. */
export interface WithheldEntry {
  key: string;
  label: string;
  source?: string;
  license?: string;
  why: string;
  counted?: boolean;
  branch?: string;
}

/** common.json#aggregate: one month of a branch's index. */
export interface Aggregate {
  month: string;
  kind: string;
  index: number | null;
  state: StateName | null;
  n_series?: number | null;
  [k: string]: unknown;
}

export interface BranchDoc extends Branch {
  question: string;
  n_withheld?: number;
  n_withheld_counted?: number;
  has_core?: boolean;
  counted: SeriesEntry[];
  not_counted: SeriesEntry[];
  withheld: WithheldEntry[];
  history: Aggregate[];
}

export interface LeadBranch {
  code: string;
  name: string | null;
  state: StateName | null;
  index: number | null;
  n_series?: number | null;
  delta_index?: number | null;
  state_changed?: boolean | null;
}

export interface NowcastSummary {
  id: string;
  label: string;
  title: string;
  unit?: string | null;
  decimals?: number;
  champion: string;
  latest: { period?: string | null; origin?: string | null; value?: number | null; interval_80?: [number, number] | null } | null;
  next_origin?: string | null;
  next_period?: string | null;
}

export interface Lead {
  code: string;
  name: string;
  short: string[];
  content: string;
  branches: LeadBranch[];
  series: SeriesEntry[];
  n_withheld: number;
  nowcasts: NowcastSummary[];
}

export type Reconciliation = SeriesEntry | { hidden: true; span?: number[] | null; lead?: string | null };

export interface FlowDoc {
  record: RecordMeta;
  leads: Lead[];
  reconciliations: Reconciliation[];
  reconciliations_available: boolean;
  withheld: WithheldEntry[];
}

// ---- compact shapes handed to the pages (what is serialised into the HTML) ----

export interface XY {
  /** period labels as in the bundle ("2026-09", "2026Q3", "2026") */
  periods: string[];
  values: (number | null)[];
}

/** One small multiple: the latest measures, the pace path and (optionally) a thinned level path. */
export interface Multiple {
  key: string;
  label: string;
  branch: string | null;
  unit: string | null;
  source: string | null;
  license: string | null;
  method: SeriesEntry['method'];
  latest_period: string | null;
  known_from: string | null;
  pace: number | null;
  pace_unit: string | null;
  pace_percentile: number | null;
  change_in_pace: number | null;
  deadband: number | null;
  direction: Dir;
  counted: boolean;
  reason: string | null;
  pacePath: XY | null;
  levelPath: XY | null;
  /** /serie/<key> exists (the key is in series/index.json) */
  linkable: boolean;
}

/** The minimap: nine leads, each with its branches' index and state. */
export interface MiniLead {
  code: string;
  name: string;
  short: string[];
  branches: LeadBranch[];
}
