// Pure helpers for the lead and branch pages (track W6): compact the bundle documents into what the pages draw,
// and generate the sentences that name the charts. Nothing here recomputes a measure: pace, change in pace,
// direction and index come from the pipeline. Level paths are only thinned for drawing.
import { fmt, periodLabel, signed } from '$lib/design';
import type { Dir, FlowDoc, Lead, MiniLead, Multiple, SeriesEntry, WithheldEntry, XY } from './types';

/** A period as a fractional year, for a shared x axis across frequencies. Weeks "a/b" use their last day. */
export function periodTime(p: string): number {
  const s = p.includes('/') ? p.split('/')[1] : p;
  let m = /^(\d{4})Q([1-4])$/.exec(s);
  if (m) return Number(m[1]) + (Number(m[2]) - 0.5) / 4;
  m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (m) {
    const y = Number(m[1]);
    const t = Date.UTC(y, Number(m[2]) - 1, Number(m[3]));
    return y + (t - Date.UTC(y, 0, 1)) / (365.25 * 864e5);
  }
  m = /^(\d{4})-(\d{2})$/.exec(s);
  if (m) return Number(m[1]) + (Number(m[2]) - 0.5) / 12;
  m = /^(\d{4})$/.exec(s);
  if (m) return Number(m[1]) + 0.5;
  return NaN;
}

/** Keep at most `max` points: every k-th point, always the last one. For drawing only. */
export function thin(xy: XY, max = 160): XY {
  const n = xy.periods.length;
  if (n <= max) return xy;
  const k = Math.ceil(n / max);
  const keep: number[] = [];
  for (let i = (n - 1) % k; i < n; i += k) keep.push(i);
  return { periods: keep.map((i) => xy.periods[i]), values: keep.map((i) => xy.values[i]) };
}

/** Drop leading and trailing missing values. */
export function trim(xy: XY): XY | null {
  let a = 0;
  let b = xy.values.length - 1;
  while (a <= b && (xy.values[a] === null || xy.values[a] === undefined)) a++;
  while (b >= a && (xy.values[b] === null || xy.values[b] === undefined)) b--;
  if (a > b) return null;
  return { periods: xy.periods.slice(a, b + 1), values: xy.values.slice(a, b + 1) };
}

const num = (x: unknown): number | null => (typeof x === 'number' && Number.isFinite(x) ? x : null);

/** A series entry (branch or flow document) as one small multiple. `levels` from series/<key>.json, if any. */
export function toMultiple(
  e: SeriesEntry,
  opts: { levels?: { periods: string[]; values: (number | null)[] } | null; linkable: boolean; counted?: boolean }
): Multiple {
  const pacePath = e.path ? trim({ periods: e.path.periods, values: e.path.pace }) : null;
  let levelPath: XY | null = null;
  if (opts.levels && opts.levels.periods.length) {
    // the level over the same window as the pace path (plus the year the first pace needs), else the last 10 years
    const lastT = periodTime(opts.levels.periods.at(-1)!);
    const from = pacePath ? periodTime(pacePath.periods[0]) - 1 : lastT - 10;
    const idx = opts.levels.periods.map((p, i) => [p, i] as const).filter(([p]) => periodTime(p) >= from);
    levelPath = trim(thin({ periods: idx.map(([p]) => p), values: idx.map(([, i]) => opts.levels!.values[i]) }));
  }
  return {
    key: e.key,
    label: e.label,
    branch: e.branch ?? null,
    unit: e.unit ?? null,
    source: e.source ?? null,
    license: e.license ?? null,
    method: e.method ?? null,
    latest_period: e.latest_period ?? null,
    known_from: e.known_from ?? null,
    pace: num(e.pace),
    pace_unit: e.pace_unit ?? null,
    pace_percentile: num(e.pace_percentile),
    change_in_pace: num(e.change_in_pace),
    deadband: num(e.deadband),
    direction: (e.direction ?? null) as Dir,
    counted: opts.counted ?? e.counted ?? true,
    reason: e.reason ? e.reason : null,
    pacePath,
    levelPath,
    linkable: opts.linkable
  };
}

/** Shorter doubling or halving time counts as acceleration (register 2026-11-23, point 2): flip so up = more pace. */
export const invertedPace = (method: Multiple['method']) => method === 'doubling' || method === 'halving';

/** The x domain shared by a set of small multiples (so they line up in time). */
export function sharedDomain(ms: Multiple[], mode: 'pace' | 'level'): [number, number] | null {
  let lo = Infinity;
  let hi = -Infinity;
  for (const m of ms) {
    const xy = mode === 'pace' ? m.pacePath : (m.levelPath ?? m.pacePath);
    if (!xy) continue;
    lo = Math.min(lo, periodTime(xy.periods[0]));
    hi = Math.max(hi, periodTime(xy.periods.at(-1)!));
  }
  return Number.isFinite(lo) && hi > lo ? [lo, hi] : null;
}

/** The minimap's view of the chain. */
export function miniLeads(flow: FlowDoc): MiniLead[] {
  return flow.leads.map((l) => ({
    code: l.code,
    name: l.name,
    short: l.short,
    branches: l.branches.map((b) => ({ code: b.code, name: b.name, state: b.state, index: b.index }))
  }));
}

/** The leads a branch belongs to (G4 is in L3 and L4, G5 in L5 and L7). */
export const leadsOfBranch = (flow: FlowDoc, code: string): string[] =>
  flow.leads.filter((l) => l.branches.some((b) => b.code === code)).map((l) => l.code);

/** Lead number ("L6" -> 6). */
export const leadNo = (code: string) => Number(code.replace(/^L/, ''));

/** Reconciliations whose lead span touches the lead. */
export function reconciliationsFor(flow: FlowDoc, code: string) {
  const n = leadNo(code);
  return flow.reconciliations.filter((r) => {
    const s = r.span;
    return Array.isArray(s) && s.length === 2 && s[0] <= n && n <= s[1];
  });
}

/**
 * The withheld key series of a lead, by name, when they can be attributed: candidates are flow.withheld entries
 * whose branch (looked up in the branch documents) is one of the lead's branches. If the candidates do not match
 * the lead's count exactly, only the count is shown (never a guess).
 */
export function withheldForLead(lead: Lead, flowWithheld: WithheldEntry[], branchOf: Map<string, string>): WithheldEntry[] | null {
  if (!lead.n_withheld) return [];
  const codes = new Set(lead.branches.map((b) => b.code));
  const c = flowWithheld.filter((w) => codes.has(w.branch ?? branchOf.get(w.key) ?? ''));
  return c.length === lead.n_withheld ? c : null;
}

/** Reduce a withheld entry to what the page may show: name, source, licence, reason, counted. Never values. */
export const withheldView = (w: WithheldEntry) => ({
  key: w.key,
  label: w.label,
  source: w.source ?? null,
  license: w.license ?? null,
  why: w.why,
  counted: w.counted === true
});
export type WithheldView = ReturnType<typeof withheldView>;

// ---- sentences (section 4.3: every chart has a generated sentence, also its accessible description) ----

const DIR_WORD: Record<string, string> = { '1': 'ökar takten', '0': 'oförändrad takt', '-1': 'minskar takten' };

export function multipleSentence(m: Multiple, mode: 'pace' | 'level'): string {
  const when = m.latest_period ? periodLabel(m.latest_period) : 'senaste perioden';
  if (mode === 'level') {
    const v = m.levelPath?.values.at(-1);
    const p = m.levelPath?.periods.at(-1);
    return v === undefined || v === null
      ? `${m.label}: ingen nivå i paketet.`
      : `${m.label}: nivån ${fmt(v, Math.abs(v) < 10 ? 2 : 0)}${m.unit ? ' ' + m.unit : ''} (${periodLabel(p ?? '')}).`;
  }
  if (m.pace === null) return `${m.label}: ingen takt ${m.reason ? '(' + m.reason + ')' : 'på senaste perioden'}.`;
  const pct = m.pace_percentile !== null ? `, ${fmt(m.pace_percentile, 0)}:e percentilen av egen historik` : '';
  const dir = !m.counted ? ' Räknas inte i grenens index.' : m.direction === null ? '' : ` Riktning: ${DIR_WORD[String(m.direction)]}.`;
  return `${m.label}: takten ${signed(m.pace, 1)} ${m.pace_unit ?? ''} i ${when}${pct}.${dir}`.replace(/\s+\./g, '.');
}

export function deadbandSentence(m: Multiple): string {
  if (m.change_in_pace === null || m.deadband === null) return 'Förändring i takt saknas.';
  const inside = Math.abs(m.change_in_pace) <= m.deadband;
  return `Förändring i takt ${signed(m.change_in_pace, 1)}, dödband ±${fmt(m.deadband, 1)}: ${inside ? 'inom' : 'utanför'} bandet.`;
}

export function indexSentence(hist: { month: string; index: number | null; state: string | null }[]): string {
  const h = hist.filter((x) => x.index !== null);
  if (!h.length) return 'Inget index i historiken.';
  const last = h.at(-1)!;
  const changes = h.slice(1).filter((x, i) => x.state !== h[i].state).length;
  return (
    `Index ${fmt(last.index, 2)} (${last.state ?? 'inget tillstånd'}) i ${periodLabel(last.month, true)}, ` +
    `${h.length} månader sedan ${periodLabel(h[0].month)}, ${changes} tillståndsbyten. Gränserna 0,33 och 0,67 skiljer tillstånden.`
  );
}
