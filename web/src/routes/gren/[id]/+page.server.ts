// Branch page G1–G9 (track W6): index over time, the series as small multiples, withheld series as named boxes.
import { BRANCH_CODES } from '$lib/data';
import { branchDoc, compactHistory, context, multiples, statusOf, thresholds } from '$lib/flow/load.server';
import { leadsOfBranch, miniLeads, withheldView } from '$lib/flow/prepare';
import { error } from '@sveltejs/kit';
import type { EntryGenerator } from './$types';

export const entries: EntryGenerator = () => BRANCH_CODES.map((id) => ({ id }));

export async function load({ params }) {
  if (!(BRANCH_CODES as readonly string[]).includes(params.id)) error(404, `okänd gren ${params.id}`);
  const { b, flow, overview, keys } = await context();
  const doc = await branchDoc(b, params.id);
  const [counted, notCounted] = await Promise.all([multiples(b, doc.counted, keys, true), multiples(b, doc.not_counted, keys, false)]);
  const leads = leadsOfBranch(flow, doc.code);
  return {
    branch: {
      code: doc.code,
      name: doc.name,
      question: doc.question,
      index: doc.index,
      state: doc.state,
      n_series: doc.n_series ?? 0,
      n_withheld_counted: doc.n_withheld_counted ?? 0,
      // index v2 (bundle 1.4.0): one vote per source family; v1 beside it. A bundle before v2 has none of these.
      rule_version: doc.rule_version === 'v2' ? ('v2' as const) : ('v1' as const),
      n_families: doc.n_families ?? null,
      n_families_withheld: doc.n_families_withheld ?? 0,
      index_v1: doc.index_v1 ?? null,
      state_v1: doc.state_v1 ?? null,
      families: (doc.families ?? []).map((f) => ({ family: f.family, series: f.series, vote: f.vote ?? null })),
      previous: doc.previous ? { month: String(doc.previous.month ?? ''), index: doc.previous.index, state: doc.previous.state } : null,
      delta_index: doc.delta_index ?? null,
      state_changed: doc.state_changed ?? null,
      record: { label: doc.record.label, month: doc.record.month, date: doc.record.date },
      status: statusOf(doc.record),
      history: compactHistory(doc.history)
    },
    counted,
    notCounted,
    withheld: doc.withheld.map(withheldView),
    minimap: miniLeads(flow),
    leads: leads.map((c) => ({ code: c, name: flow.leads.find((l) => l.code === c)?.name ?? c })),
    thresholds: thresholds(overview)
  };
}
