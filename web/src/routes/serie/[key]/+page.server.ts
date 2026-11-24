import { bundle } from '$lib/server/bundle';
import type { EntryGenerator } from './$types';

export const entries: EntryGenerator = async () => (await bundle().seriesIndex()).series.map((s) => ({ key: s.key }));

export async function load({ params }) {
  return { series: await bundle().series(params.key) };
}
