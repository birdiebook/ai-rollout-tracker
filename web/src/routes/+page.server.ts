// Start page (W5). Reads the bundle at prerender time and hands the page only what it draws (lib/start/model.ts),
// so the data inlined in the HTML stays far below the 100 kB budget.
import { bundle } from '$lib/server/bundle';
import { startData } from '$lib/start/model';

export async function load() {
  const b = bundle();
  const [manifest, overview, flow, seriesIndex] = await Promise.all([b.manifest(), b.overview(), b.flow(), b.seriesIndex()]);
  const ids = overview.calendar.map((c) => c.id).filter((id) => id !== 'd2');
  const nowcasts = await Promise.all(ids.map((id) => b.nowcast(id)));
  return { start: startData({ manifest, overview, flow, nowcasts, seriesIndex }) };
}
