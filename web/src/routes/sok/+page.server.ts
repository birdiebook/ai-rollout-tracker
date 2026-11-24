// W12: the search page and register of everything searchable. Works without JavaScript (the full list is in the
// HTML); with JavaScript the same combobox as the ⌘K dialog filters it.
import { bundle } from '$lib/server/bundle';
import { buildSearchIndex } from '$lib/nav/searchindex.server';

export async function load() {
  return { index: await buildSearchIndex(bundle()) };
}
