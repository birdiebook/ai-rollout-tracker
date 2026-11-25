// Where a chart's numbers can be read without JavaScript (R-W2 B1). A page sets the published bundle document its
// charts are drawn from; ChartFrame links it under a table that is too large to prerender. A chart can pass its own
// `dataHref` instead (a branch page's small multiples link each series' document).
import { getContext, setContext } from 'svelte';
import { asset } from '$app/paths';

const KEY = Symbol('chart-data');

/** Tables up to this many cells (rows x columns) are prerendered inside the <details>; larger ones are drawn only
 *  when opened (R-W2 P1: hidden tables were 78 % of the DOM on a series page and drove the blocking time). */
export const PRERENDER_CELLS = 60;

/** URL of a published bundle document, e.g. dataUrl('series/us_ip_semis_m.json'). */
export const dataUrl = (path: string): string => asset(`/data/${path}` as Parameters<typeof asset>[0]);

/** Set in a page component: a getter, so a reused page component (another id of the same route) stays right. */
export function setChartData(get: () => string | null): void {
  setContext(KEY, get);
}

export function chartData(): () => string | null {
  return getContext<(() => string | null) | undefined>(KEY) ?? (() => null);
}
