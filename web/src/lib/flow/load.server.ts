// Server-side (prerender) loading for the lead and branch pages (track W6): read the bundle through the typed
// loaders and hand the pages only the compact shapes they draw (P12: inlined data stays small).
import { bundle } from '$lib/server/bundle';
import type { Bundle, Overview, RecordMeta } from '$lib/data';
import type { RecordStatus } from '$lib/design';
import { toMultiple } from './prepare';
import type { Aggregate, BranchDoc, FlowDoc, Multiple, SeriesEntry } from './types';

export async function context() {
  const b = bundle();
  const [flow, overview, idx] = await Promise.all([b.flow(), b.overview(), b.seriesIndex()]);
  return { b, flow: flow as unknown as FlowDoc, overview, keys: new Set(idx.series.map((s) => s.key)) };
}

export const thresholds = (ov: Overview) => ({
  lo: ov.stripes.thresholds.braking_at_most,
  hi: ov.stripes.thresholds.accelerating_at_least
});

export const statusOf = (r: RecordMeta | undefined): RecordStatus => (r?.status === 'live' ? 'live' : 'recon');

/** Small multiples for a list of series entries; levels from series/<key>.json where the series is published. */
export async function multiples(b: Bundle, entries: SeriesEntry[], keys: Set<string>, counted?: boolean): Promise<Multiple[]> {
  return Promise.all(
    entries
      .filter((e) => e.key)
      .map(async (e) => {
        const linkable = keys.has(e.key);
        const levels = linkable ? (await b.series(e.key)).levels : null;
        return toMultiple(e, { levels, linkable, counted });
      })
  );
}

export const compactHistory = (h: Aggregate[]) =>
  h.map((a) => ({ month: a.month, kind: a.kind, index: a.index ?? null, state: a.state ?? null, n_series: a.n_series ?? null }));

export async function branchDoc(b: Bundle, code: string): Promise<BranchDoc> {
  return (await b.branch(code)) as unknown as BranchDoc;
}
