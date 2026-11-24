// Server-side (prerender) loading for /avstamningar and /regim (track W10). Reads the bundle through the typed
// loaders and hands the pages only compact shapes. Withheld series never get values here: a component or a break
// that is not in series/index.json is passed on by name (withheld.json) or only counted.
import { bundle } from '$lib/server/bundle';
import type { Series } from '$lib/data';
import { asOf } from '$lib/series/versions';
import type { Versions } from '$lib/series/types';
import type { FlowDoc, SeriesEntry } from '$lib/flow';
import { contributions, formula, reconDef } from './recon';
import type { BreakView, ComponentView, ReconView, RegimeLane } from './types';

const num = (x: unknown): number | null => (typeof x === 'number' && Number.isFinite(x) ? x : null);

async function base() {
  const b = bundle();
  const [flow, idx, wd] = await Promise.all([b.flow() as unknown as Promise<FlowDoc>, b.seriesIndex(), b.withheld()]);
  return {
    b,
    flow,
    keys: new Set(idx.series.map((s) => s.key)),
    labels: new Map(idx.series.map((s) => [s.key, s.label])),
    withheld: wd.withheld
  };
}

export async function reconciliations() {
  const { b, flow, keys, withheld } = await base();
  const day = flow.record.date;
  const wLabel = new Map(withheld.map((w) => [w.key, w.label]));
  const docs = new Map<string, Series>();
  const doc = async (k: string) => {
    if (!keys.has(k)) return null;
    if (!docs.has(k)) docs.set(k, await b.series(k));
    return docs.get(k)!;
  };
  const views: ReconView[] = [];
  let hidden = 0;
  for (const r of flow.reconciliations) {
    if ('hidden' in r) {
      hidden++;
      continue;
    }
    const e = r as SeriesEntry;
    const def = reconDef(e.key);
    const periods = e.path?.periods ?? [];
    const pace = (e.path?.pace ?? []).map(num);
    const own = await doc(e.key);
    const ratioAsOf = asOf((own?.versions as Versions | undefined) ?? null, day);
    const levels = new Map<string, Map<string, number>>();
    const components: ComponentView[] = [];
    if (def) {
      for (const [sideName, terms] of [['num', def.num], ['den', def.den]] as const) {
        for (const t of terms) {
          const s = await doc(t.series);
          const lv = s ? asOf((s.versions as Versions | undefined) ?? null, day) : null;
          if (lv) levels.set(t.series, lv);
          const m = (s?.measure ?? null) as Record<string, unknown> | null;
          components.push({
            key: t.series,
            label: s?.label ?? wLabel.get(t.series) ?? t.series,
            side: sideName,
            window: t.window,
            linkable: !!s,
            unit: s?.unit ?? null,
            latest_period: s ? ((m?.latest_period as string) ?? null) : null,
            pace: s ? num(m?.pace) : null,
            pace_unit: s ? ((m?.pace_unit as string) ?? null) : null,
            pace_percentile: s ? num(m?.pace_percentile) : null,
            direction: s && m && m.direction !== undefined ? (m.direction as ComponentView['direction']) : null,
            levels: lv ? { periods, values: periods.map((p) => lv.get(p) ?? null) } : null
          });
        }
      }
    }
    const parts =
      def && components.every((c) => c.linkable)
        ? contributions(def, levels, periods, pace)
        : { num_c: [], den_c: [], rest: [], num_idx: [], den_idx: [], max_rest: null };
    views.push({
      key: e.key,
      short: e.short ?? e.label,
      label: e.label,
      question: e.question ?? '',
      unit: e.unit ?? '',
      lead: e.lead ?? null,
      span: e.span ?? [1, 1],
      linkable: keys.has(e.key),
      source: e.source ?? null,
      license: e.license ?? null,
      method: e.method ?? null,
      latest_period: e.latest_period ?? null,
      known_from: e.known_from ?? null,
      level: num(e.level),
      pace: num(e.pace),
      pace_unit: e.pace_unit ?? null,
      pace_percentile: num(e.pace_percentile),
      change_in_pace: num(e.change_in_pace),
      change_percentile: num(e.change_percentile),
      deadband: num(e.deadband),
      direction: e.direction ?? null,
      n_pace: num((e as unknown as Record<string, unknown>).n_pace),
      valid: e.valid !== false,
      reason: e.reason || null,
      formula: def ? formula(def) : '',
      periods,
      ratio: periods.map((p) => ratioAsOf.get(p) ?? null),
      pace_path: pace,
      ...parts,
      components
    });
  }
  return { record: flow.record, available: flow.reconciliations_available, views, hidden };
}

export async function regime() {
  const b = bundle();
  const [rg, idx] = await Promise.all([b.regime(), b.seriesIndex()]);
  const keys = new Map(idx.series.map((s) => [s.key, s.label]));
  const lanes: RegimeLane[] = rg.blocks.map((bl) => ({
    block: bl.block,
    label: bl.label,
    history: bl.history.map((h) => ({ month: h.month, p: num(h.p_slow), state: h.state, shift: h.shift, reason: h.reason ?? '' })),
    latest: bl.latest
      ? { month: bl.latest.month, p: num(bl.latest.p_slow), state: bl.latest.state, shift: bl.latest.shift, n_months: bl.latest.n_months, reason: bl.latest.reason ?? '' }
      : null
  }));
  // breaks are on publishable series only (site.probabilities.regime_view); link them only if the series page exists
  const breaks: BreakView[] = rg.breaks.map((x) => ({
    month: x.month,
    series: x.series,
    label: keys.get(x.series) ?? x.series,
    branch: x.branch,
    latest_period: x.latest_period,
    p_recent: num(x.p_recent),
    linkable: keys.has(x.series)
  }));
  return {
    record: rg.record,
    available: rg.available,
    months: rg.months,
    spec_version: rg.spec_version,
    lanes,
    block_labels: rg.block_labels,
    shifts: rg.shifts,
    breaks,
    n_breaks_withheld: rg.n_breaks_withheld,
    /** the holdout's two breaks link to their series when published */
    holdoutLinks: Object.fromEntries(['rpo_hyp4', 'rev_google_cloud'].map((k) => [k, keys.has(k)]))
  };
}
