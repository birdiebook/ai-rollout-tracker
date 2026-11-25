// The search index is fetched once, the first time the search opens (W12; not part of any page's HTML).
import { resolve } from '$app/paths';
import type { SearchIndex } from './search';

let cached: Promise<SearchIndex> | null = null;

export function loadIndex(fetcher: typeof fetch = fetch): Promise<SearchIndex> {
  cached ??= fetcher(resolve('/sok.json'))
    .then((r) => {
      if (!r.ok) throw new Error(`sok.json: HTTP ${r.status}`);
      return r.json() as Promise<SearchIndex>;
    })
    .catch((e) => {
      cached = null; // a later open tries again
      throw e;
    });
  return cached;
}
