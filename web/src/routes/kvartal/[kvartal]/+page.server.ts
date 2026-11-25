// /kvartal/[kvartal] (W14): the quarterly report as a visual essay. One page per quarter of report/index.json,
// prerendered from report/<YYYYQn>.json; every figure is cut to the report day by the time-travel boundary
// ($lib/report/model.ts).
import { error } from '@sveltejs/kit';
import { loadReport, reportQuarters } from '$lib/report/load.server';

export async function entries() {
  return (await reportQuarters()).map((kvartal) => ({ kvartal }));
}

export async function load({ params }) {
  if (!(await reportQuarters()).includes(params.kvartal)) error(404, `Ingen kvartalsrapport för ${params.kvartal}`);
  return { page: await loadReport(params.kvartal) };
}
