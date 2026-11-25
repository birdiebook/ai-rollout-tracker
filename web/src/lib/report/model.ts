// Quarterly report (W14): the view model of the visual essay. The sections and their sentences come from
// report/<YYYYQn>.json, built in Python from ai_tracker.quarterly's facts (site_bundle.report). This file only
// attaches the living figures from today's bundle, each cut to the report day (the quarter's last month-end record)
// through the time-travel boundary ($lib/timetravel/gate): the stripes (cutStripes), the branch index histories
// (branchOn), and the levels of the ratios and the nowcast targets as they were known that day (seriesOn). The
// assembled page is checked with leaks() before it is returned: nothing known after the report day.
import type { Branch, Overview, Regime, Report, ReportIndex, ReportIndexEntry, ReportNowcast, ReportOutcome, ReportRatio } from '$lib/data';
import type { FlowDoc, MiniLead } from '$lib/flow/types';
import type { ReconView, RegimeLane } from '$lib/regime/types';
import type { SeriesDoc } from '$lib/series/types';
import { periodTime } from '$lib/series/period';
import type { TimePoint } from '$lib/series/chart';
import { LeakError, branchOn, cutStripes, leaks, seriesOn, type HistoryRow, type StripesOn } from '$lib/timetravel/gate';
import type { LiveRow } from '../../routes/prognoser/parts/model';

/** Months of history in the stripes and the index figures (as the monthly story). */
export const FIGURE_MONTHS = 24;
/** Periods of a level figure: five years of a monthly series, six of a quarterly one. */
const LEVEL_PERIODS: Record<string, number> = { M: 60, Q: 24, A: 10, W: 260, '2W': 130, D: 1830 };
/** Branches drawn as full index histories: the largest moves and the state changes (the report's own lists). */
export const MAX_MOVERS = 4;

const tail = <T>(xs: T[], n: number) => xs.slice(Math.max(0, xs.length - n));

export interface BranchView {
  code: string;
  name: string;
  state: string | null;
  index: number | null;
  delta: number | null;
  changed: boolean | null;
  /** index at the comparison month and the quarter's three month ends */
  spark: (number | null)[];
  months: string[];
}

export interface LeadView {
  lead: string;
  name: string;
  text: string;
  branches: BranchView[];
  ratios: string[];
  n_ratios_withheld: number;
}

export interface Mover {
  code: string;
  name: string;
  delta: number | null;
  from: string | null;
  to: string | null;
  history: (HistoryRow & { known: string })[];
}

export interface RatioView {
  ratio: ReportRatio;
  /** the ratio's levels known on the report day, in RatioChart's shape (null: no published series document) */
  recon: ReconView | null;
  short: string;
  span: number[];
}

export interface LevelFigure {
  key: string;
  label: string;
  unit: string;
  points: TimePoint[];
  total: number;
  source: string;
  license: string;
}

export interface NowcastView {
  n: ReportNowcast;
  level: LevelFigure | null;
  /** why there is no level figure: the target is withheld, has no series document (a sum, N4), or had no value yet */
  noLevel: 'withheld' | 'derived' | 'empty' | null;
  rows: LiveRow[];
}

export interface QuarterNav {
  quarter: string;
  quarter_sv: string;
  kind: string;
  known: string;
}

export interface ReportPage {
  day: string;
  report: Report;
  stripes: StripesOn;
  highlight: string;
  leads: LeadView[];
  mini: MiniLead[];
  movers: Mover[];
  ratios: RatioView[];
  spans: { key: string | null; short: string | null; span: number[]; lead: string | null; direction: -1 | 0 | 1 | null; linkable: boolean }[];
  nowcasts: NowcastView[];
  lanes: RegimeLane[];
  quarters: QuarterNav[];
  firstLive: string | null;
}

export interface Docs {
  report: Report;
  index: ReportIndex;
  overview: Overview;
  flow: FlowDoc;
  regime: Regime;
  branches: Record<string, Branch>;
  series: Record<string, SeriesDoc>;
}

function levelFigure(doc: SeriesDoc | undefined, day: string, rec: Overview['record']): LevelFigure | null {
  if (!doc) return null;
  const s = seriesOn(doc, day, rec);
  const pts = s.levels.map((l) => ({ p: l.period, t: periodTime(l.period), v: l.value })).filter((q) => Number.isFinite(q.t));
  const n = LEVEL_PERIODS[doc.freq ?? 'M'] ?? 60;
  return {
    key: doc.key,
    label: doc.label,
    unit: doc.unit ?? '',
    points: tail(pts, n),
    total: pts.length,
    source: doc.source ?? '',
    license: doc.license?.short ?? ''
  };
}

function reconView(r: ReportRatio, fig: LevelFigure | null, short: string, span: number[]): ReconView | null {
  if (!fig || !fig.points.length) return null;
  const periods = fig.points.map((p) => p.p);
  const nulls = periods.map(() => null);
  return {
    key: r.key,
    short,
    label: r.label,
    question: '',
    unit: fig.unit,
    lead: null,
    span,
    linkable: true,
    source: fig.source,
    license: fig.license,
    method: null,
    latest_period: r.latest_period,
    known_from: r.known_from,
    level: r.level,
    pace: r.pace,
    pace_unit: r.pace_unit,
    pace_percentile: r.pace_percentile,
    change_in_pace: r.change_in_pace,
    change_percentile: r.change_percentile,
    deadband: null,
    direction: r.direction,
    n_pace: r.n_pace,
    valid: r.valid ?? false,
    reason: null,
    formula: '',
    periods,
    ratio: fig.points.map((p) => p.v),
    pace_path: nulls,
    num_c: nulls,
    den_c: nulls,
    rest: nulls,
    num_idx: nulls,
    den_idx: nulls,
    max_rest: null,
    components: []
  };
}

/** An outcome of the quarter as ForecastDots' row (the champion's stored intervals, the first published outcome). */
export function outcomeRow(o: ReportOutcome): LiveRow {
  const iv = (o.intervals ?? {}) as LiveRow['intervals'];
  const inside: LiveRow['inside'] = {};
  for (const l of ['50', '80', '95'] as const) {
    const p = iv[l];
    if (p && p[0] !== null && p[1] !== null && o.outcome !== null) inside[l] = o.outcome >= Math.min(p[0], p[1]) && o.outcome <= Math.max(p[0], p[1]);
  }
  return {
    slug: o.slug ?? '',
    period: o.period,
    origin: o.origin,
    file: o.file ?? '',
    value: o.forecast,
    intervals: iv,
    variants: {},
    champion: o.champion ?? '',
    score: null,
    scored: true,
    status: 'utfall',
    outcome: o.outcome,
    outcomeKnown: o.known_from,
    err: o.err_champion,
    inside,
    pit: null,
    crps: null,
    // the forecast's own page shows its commit (RW1-X 4a); the report does not repeat it
    commit: null,
    verified: false
  };
}

function lanes(report: Report, regime: Regime): RegimeLane[] {
  const rg = report.regime;
  if (rg.blocks?.length) {
    return rg.blocks.map((b) => {
      const history = b.cells.filter((c) => c.present).map((c) => ({ month: c.month, p: c.p_slow ?? null, state: c.state ?? null, shift: c.shift ?? null, reason: c.reason ?? '' }));
      const last = history.at(-1) ?? null;
      return { block: b.block, label: b.label, history, latest: last ? { ...last, n_months: null } : null };
    });
  }
  // no regime section in the quarter: the registered blocks without a value (the meter says so)
  const labels = regime.block_labels ?? {};
  return Object.entries(labels).map(([block, label]) => ({ block, label, history: [], latest: null }));
}

/** The report page: the document's sections with their figures, cut to the report day by the gate. Throws LeakError
 *  when anything on the page was known later. */
export function reportPage(d: Docs): ReportPage {
  const { report, index, overview, flow } = d;
  const day = report.known;
  const last = report.months[report.months.length - 1];
  if (!last || last.known > day || report.end > day) throw new LeakError([`report ${report.quarter}: known ${day} before its quarter end`]);
  const rec = overview.record;
  const st = cutStripes(overview.stripes, day, rec);
  const stripes: StripesOn = {
    ...st,
    months: tail(st.months, FIGURE_MONTHS),
    known: tail(st.known, FIGURE_MONTHS),
    kind: tail(st.kind, FIGURE_MONTHS),
    rows: st.rows.map((r) => ({ ...r, index: tail(r.index, FIGURE_MONTHS), state: tail(r.state, FIGURE_MONTHS), n_series: tail(r.n_series, FIGURE_MONTHS) }))
  };
  const byCode = new Map(report.branches.map((b) => [b.code, b]));
  const view = (code: string): BranchView => {
    const b = byCode.get(code);
    const end = b?.path.at(-1);
    return {
      code,
      name: b?.name ?? code,
      state: end?.state ?? null,
      index: end?.index ?? null,
      delta: b?.delta_index ?? null,
      changed: b?.state_changed ?? null,
      spark: b ? b.path.map((c) => c.index) : [],
      months: b ? b.path.map((c) => c.month) : []
    };
  };
  const leads: LeadView[] = report.chain.map((l) => ({
    lead: l.lead,
    name: l.name,
    text: l.text,
    branches: l.branches.map(view),
    ratios: l.ratios,
    n_ratios_withheld: l.n_ratios_withheld
  }));
  const shortOf = new Map(flow.leads.map((l) => [l.code, l.short]));
  const mini: MiniLead[] = leads.map((l) => ({
    code: l.lead,
    name: l.name,
    short: shortOf.get(l.lead) ?? [l.name],
    branches: l.branches.map((b) => ({ code: b.code, name: b.name, state: b.state as MiniLead['branches'][number]['state'], index: b.index }))
  }));
  // the movers: the report's largest index moves, then its state changes (registered order, no editorial choice)
  const codes: string[] = [];
  for (const c of [...report.summary.moved.map((m) => m.code), ...report.summary.changed.map((c) => c.code)]) if (!codes.includes(c)) codes.push(c);
  const movers: Mover[] = [];
  for (const code of codes.slice(0, MAX_MOVERS)) {
    const doc = d.branches[code];
    const b = byCode.get(code);
    if (!doc || !b) continue;
    const history = tail(branchOn(doc as Branch & { history?: HistoryRow[] }, day).history, FIGURE_MONTHS);
    if (history.length) movers.push({ code, name: b.name, delta: b.delta_index, from: b.from, to: b.to, history });
  }
  const recMeta = new Map(flow.reconciliations.filter((r): r is Exclude<typeof r, { hidden: true }> => !('hidden' in r)).map((r) => [r.key, r]));
  const ratios: RatioView[] = report.ratios.map((r) => {
    const m = recMeta.get(r.key);
    const short = m?.short ?? r.label;
    const span = (m?.span ?? [1, 1]) as number[];
    return { ratio: r, recon: reconView(r, levelFigure(d.series[r.key], day, rec), short, span), short, span };
  });
  const spans = ratios.map((r) => ({
    key: r.ratio.key,
    short: r.short,
    span: r.span,
    lead: r.ratio.leads.join('–') || null,
    direction: r.ratio.direction,
    linkable: !!d.series[r.ratio.key]
  }));
  const nowcasts: NowcastView[] = report.nowcasts.map((n) => {
    const fig = n.publishable && n.target ? levelFigure(d.series[n.target], day, rec) : null;
    const level = fig && fig.points.length ? fig : null;
    const noLevel = level ? null : !n.publishable || !n.target ? 'withheld' : !d.series[n.target] ? 'derived' : 'empty';
    return { n, level, noLevel, rows: n.outcomes.filter((o) => o.intervals && o.forecast !== null).map(outcomeRow) };
  });
  const quarters: QuarterNav[] = index.quarters.map((q: ReportIndexEntry) => ({ quarter: q.quarter, quarter_sv: q.quarter_sv, kind: q.kind, known: q.known }));
  const page: ReportPage = {
    day,
    report,
    stripes,
    highlight: last.month,
    leads,
    mini,
    movers,
    ratios,
    spans,
    nowcasts,
    lanes: lanes(report, d.regime),
    quarters,
    firstLive: index.first_live ?? null
  };
  // the quarter navigation may name later quarters (navigation, not knowledge); everything else must be known
  const bad = leaks({ ...page, quarters: [] }, day);
  if (bad.length) throw new LeakError(bad);
  return page;
}

/** Time travel on day D: the quarters whose report was known on D. */
export function quartersKnownOn(qs: QuarterNav[], day: string): QuarterNav[] {
  return qs.filter((q) => q.known <= day);
}

/** Quarter label for headings: "tredje kvartalet 2026" -> "Tredje kvartalet 2026". */
export const cap = (x: string) => x.charAt(0).toUpperCase() + x.slice(1);
