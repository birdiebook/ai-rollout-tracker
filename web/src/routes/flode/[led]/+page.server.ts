// One lead L1–L9 (track W6): its branches with index over time, key series as small multiples, nowcasts,
// reconciliations that touch the lead, withheld key series, and the way up- and downstream.
import { bundle } from '$lib/server/bundle';
import { branchDoc, compactHistory, context, multiples, statusOf, thresholds } from '$lib/flow/load.server';
import { leadNo, miniLeads, reconciliationsFor, withheldForLead, withheldView } from '$lib/flow/prepare';
import type { FlowDoc, SeriesEntry } from '$lib/flow/types';
import { error } from '@sveltejs/kit';
import type { EntryGenerator } from './$types';

export const entries: EntryGenerator = async () =>
  ((await bundle().flow()) as unknown as FlowDoc).leads.map((l) => ({ led: l.code }));

export async function load({ params }) {
  const { b, flow, overview, keys } = await context();
  const i = flow.leads.findIndex((l) => l.code === params.led);
  if (i < 0) error(404, `okänt led ${params.led}`);
  const lead = flow.leads[i];
  const docs = await Promise.all(lead.branches.map((x) => branchDoc(b, x.code)));
  // which branch each withheld key belongs to (from the branch documents), to name the lead's withheld series
  const all = await Promise.all(flow.leads.flatMap((l) => l.branches.map((x) => x.code)).filter((c, j, a) => a.indexOf(c) === j).map((c) => branchDoc(b, c)));
  const branchOf = new Map(all.flatMap((d) => d.withheld.map((w) => [w.key, d.code] as const)));
  const held = withheldForLead(lead, flow.withheld, branchOf);
  const recs = reconciliationsFor(flow, lead.code);
  const recSeries = recs.filter((r): r is SeriesEntry => !('hidden' in r));
  const nb = (j: number) => (flow.leads[j] ? { code: flow.leads[j].code, name: flow.leads[j].name } : null);
  return {
    lead: { code: lead.code, name: lead.name, content: lead.content, n_withheld: lead.n_withheld },
    status: statusOf(flow.record),
    record: { label: flow.record.label, month: flow.record.month },
    branches: docs.map((d) => ({
      code: d.code,
      name: d.name,
      question: d.question,
      state: d.state,
      index: d.index,
      n_series: d.n_series ?? 0,
      history: compactHistory(d.history)
    })),
    series: await multiples(b, lead.series, keys),
    nowcasts: lead.nowcasts.map((n) => ({
      id: n.id,
      label: n.label,
      title: n.title,
      unit: n.unit ?? null,
      decimals: n.decimals ?? 0,
      champion: n.champion,
      latest: n.latest
        ? { period: n.latest.period ?? null, value: n.latest.value ?? null, interval_80: n.latest.interval_80 ?? null }
        : null,
      next_origin: n.next_origin ?? null,
      next_period: n.next_period ?? null
    })),
    reconciliations: {
      series: await multiples(b, recSeries, keys),
      spans: recs.map((r) => ({
        key: 'hidden' in r ? null : r.key,
        short: 'hidden' in r ? null : (r.short ?? r.label),
        span: (r.span ?? [leadNo(lead.code), leadNo(lead.code)]) as number[],
        lead: r.lead ?? null,
        direction: 'hidden' in r ? null : (r.direction ?? null),
        linkable: !('hidden' in r) && keys.has(r.key)
      }))
    },
    withheld: held ? held.map(withheldView) : [],
    withheldAnon: held ? 0 : lead.n_withheld,
    prev: nb(i - 1),
    next: nb(i + 1),
    minimap: miniLeads(flow),
    thresholds: thresholds(overview)
  };
}
