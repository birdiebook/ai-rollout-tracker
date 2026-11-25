// The reconciliations between the leads (track W10): A5 ratios with their components. Measures from flow.json,
// component levels from series/<key>.json as known on the record date.
import { reconciliations } from '$lib/regime/load.server';
import { statusOf } from '$lib/flow/load.server';

export async function load() {
  const r = await reconciliations();
  return {
    status: statusOf(r.record),
    record: { label: r.record.label, month: r.record.month, date: r.record.date },
    available: r.available,
    views: r.views,
    hidden: r.hidden,
    spans: r.views.map((v) => ({ key: v.key, short: v.short, span: v.span, lead: v.lead, direction: v.direction, linkable: v.linkable }))
  };
}
