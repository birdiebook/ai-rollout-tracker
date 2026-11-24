// Types for the reconciliation and regime pages (track W10). The bundle documents are typed in $lib/data
// (Flow via $lib/flow's FlowDoc, Regime); these are the compact shapes the server loads hand to the pages.
import type { Dir } from '$lib/flow';

export interface Term {
  series: string;
  /** 1 = the quarter itself (a stock is its balance at the quarter end); 4 = sum over the quarter and the 3 before */
  window: number;
}

export interface ReconDef {
  key: string;
  num: Term[];
  den: Term[];
  scale: number;
}

/** One component series of a reconciliation as the page shows it. Withheld components keep only the name. */
export interface ComponentView {
  key: string;
  label: string;
  side: 'num' | 'den';
  window: number;
  /** series/<key> exists (published); false = withheld: name only, no values, no own direction */
  linkable: boolean;
  unit: string | null;
  latest_period: string | null;
  pace: number | null;
  pace_unit: string | null;
  pace_percentile: number | null;
  direction: Dir;
  /** levels as known on the record date, over the reconciliation's window (published components only) */
  levels: { periods: string[]; values: (number | null)[] } | null;
}

export interface ReconView {
  key: string;
  short: string;
  label: string;
  question: string;
  unit: string;
  lead: string | null;
  span: number[];
  linkable: boolean;
  source: string | null;
  license: string | null;
  method: string | null;
  latest_period: string | null;
  known_from: string | null;
  level: number | null;
  pace: number | null;
  pace_unit: string | null;
  pace_percentile: number | null;
  change_in_pace: number | null;
  change_percentile: number | null;
  deadband: number | null;
  direction: Dir;
  n_pace: number | null;
  valid: boolean;
  reason: string | null;
  /** "capex_hyp4 / (rev_aws + rev_google_cloud + rev_msft_cloud)" with the window spelled out */
  formula: string;
  /** quarters of the pipeline's pace path (as of the record date) */
  periods: string[];
  /** the ratio's level as known on the record date */
  ratio: (number | null)[];
  /** the pipeline's pace (log ×100 per year) */
  pace_path: (number | null)[];
  /** 100 × Δ4 log(numerator) and −100 × Δ4 log(denominator): the ratio's pace is their sum */
  num_c: (number | null)[];
  den_c: (number | null)[];
  /** pace − (num_c + den_c); about 0 when the components and the ratio come from the same versions */
  rest: (number | null)[];
  /** numerator and denominator indexed to 100 in the first period where both exist */
  num_idx: (number | null)[];
  den_idx: (number | null)[];
  max_rest: number | null;
  components: ComponentView[];
}

export interface RegimeLane {
  block: string;
  label: string;
  history: { month: string; p: number | null; state: string | null; shift: string | null; reason: string }[];
  latest: { month: string; p: number | null; state: string | null; shift: string | null; n_months: number | null; reason: string } | null;
}

export interface BreakView {
  month: string;
  series: string;
  label: string;
  branch: string | null;
  latest_period: string | null;
  p_recent: number | null;
  linkable: boolean;
}
