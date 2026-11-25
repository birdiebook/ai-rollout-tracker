// The chain L1–L9 (track W6): one row per lead with its branches (state, index, last 24 months), the key series as
// a unit chart, nowcasts, and the reconciliations between the leads as spans.
import { context, statusOf, thresholds } from '$lib/flow/load.server';

export async function load() {
  const { flow, overview, keys } = await context();
  const st = overview.stripes;
  const from = Math.max(0, st.months.length - 24);
  const spark = new Map(st.rows.map((r) => [r.code, r.index.slice(from)]));
  const counts: Record<string, number> = {};
  for (const b of overview.branches) {
    const s = b.state ?? 'för få källor';
    counts[s] = (counts[s] ?? 0) + 1;
  }
  return {
    status: statusOf(flow.record),
    record: { label: flow.record.label, month: flow.record.month },
    counts,
    sparkFrom: st.months[from] ?? null,
    leads: flow.leads.map((l) => ({
      code: l.code,
      name: l.name,
      content: l.content,
      n_withheld: l.n_withheld,
      branches: l.branches.map((b) => ({
        code: b.code,
        name: b.name ?? b.code,
        state: b.state,
        index: b.index,
        delta_index: b.delta_index ?? null,
        state_changed: b.state_changed ?? null,
        spark: spark.get(b.code) ?? []
      })),
      units: l.series.map((s) => ({ key: s.key, label: s.label, direction: s.direction ?? null, counted: s.counted !== false })),
      nowcasts: l.nowcasts.map((n) => ({ id: n.id, label: n.label, title: n.title }))
    })),
    spans: flow.reconciliations.map((r) => ({
      key: 'hidden' in r ? null : r.key,
      short: 'hidden' in r ? null : (r.short ?? r.label),
      span: (r.span ?? [1, 1]) as number[],
      lead: r.lead ?? null,
      direction: 'hidden' in r ? null : (r.direction ?? null),
      linkable: !('hidden' in r) && keys.has(r.key)
    })),
    thresholds: thresholds(overview)
  };
}
