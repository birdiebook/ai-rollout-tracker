// W12: one share image per page as a standalone SVG, <base>/og/<page>.svg, drawn from the page's data
// ($lib/nav/describe.server). scripts/og-png.mjs rasterises each to .png after the build; og:image points there.
import { error } from '@sveltejs/kit';
import { bundle } from '$lib/server/bundle';
import { ogFor, ogRoutes } from '$lib/nav/describe.server';
import { ogSvg } from '$lib/nav/og';
import type { EntryGenerator } from './$types';

export const prerender = true;

export const entries: EntryGenerator = async () => (await ogRoutes(bundle())).map((r) => ({ path: `${r.og}.svg` }));

export async function GET({ params }) {
  const m = /^(.+)\.svg$/.exec(params.path);
  const spec = m ? await ogFor(bundle(), m[1]) : null;
  if (!spec) error(404, `ingen delningsbild ${params.path}`);
  return new Response(ogSvg(spec), { headers: { 'content-type': 'image/svg+xml; charset=utf-8' } });
}
