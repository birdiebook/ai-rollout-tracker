// W12: the search index as one static file, <base>/sok.json (fetched only when the search opens).
import { json } from '@sveltejs/kit';
import { bundle } from '$lib/server/bundle';
import { buildSearchIndex } from '$lib/nav/searchindex.server';

export const prerender = true;

export async function GET() {
  return json(await buildSearchIndex(bundle()));
}
