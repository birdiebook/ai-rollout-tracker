// Server-side (prerender) loading of the quarterly report (W14): the typed loaders only, then the pure model, which
// cuts every figure through the time-travel boundary.
import { bundle } from '$lib/server/bundle';
import type { Branch, Bundle } from '$lib/data';
import type { FlowDoc } from '$lib/flow/types';
import type { SeriesDoc } from '$lib/series/types';
import { reportPage, type Docs } from './model';

export async function reportQuarters(): Promise<string[]> {
  const idx = await bundle().reportIndex();
  return idx.quarters.map((q) => q.quarter);
}

export async function loadReport(quarter: string) {
  return reportPage(await reportDocs(bundle(), quarter));
}

/** The documents the report page draws from: the report, the index, and today's bundle documents its figures are
 *  cut from (overview stripes, branch histories of the movers, the series of the ratios and nowcast targets). */
export async function reportDocs(b: Bundle, quarter: string): Promise<Docs> {
  const [report, index, overview, flow, regime, seriesIndex] = await Promise.all([
    b.report(quarter),
    b.reportIndex(),
    b.overview(),
    b.flow(),
    b.regime(),
    b.seriesIndex()
  ]);
  const published = new Set(seriesIndex.series.map((s) => s.key));
  const branches: Record<string, Branch> = {};
  for (const m of [...report.summary.moved, ...report.summary.changed]) if (!branches[m.code]) branches[m.code] = await b.branch(m.code);
  const keys = [...report.ratios.map((r) => r.key), ...report.nowcasts.map((n) => n.target).filter((k): k is string => !!k)];
  const series: Record<string, SeriesDoc> = {};
  for (const k of keys) if (published.has(k) && !series[k]) series[k] = (await b.series(k)) as unknown as SeriesDoc;
  return { report, index, overview, flow: flow as unknown as FlowDoc, regime, branches, series };
}
