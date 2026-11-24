// W7: one prerendered page per publishable series (ids from series/index.json). The page inlines the series
// without its versions (pageData); the versions are fetched at run time by the revision view (datakontrakt 8).
import { bundle } from '$lib/server/bundle';
import { pageData } from '$lib/series/page';
import type { SeriesDoc } from '$lib/series/types';
import type { EntryGenerator } from './$types';

export const entries: EntryGenerator = async () => (await bundle().seriesIndex()).series.map((s) => ({ key: s.key }));

export async function load({ params }) {
  const b = bundle();
  const [doc, idx] = await Promise.all([b.series(params.key), b.seriesIndex()]);
  return { page: pageData(doc as unknown as SeriesDoc, idx.series) };
}
