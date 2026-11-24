// W8: /prognoser/<id>/ is one nowcast (n1–n6) or D2; /prognoser/<id>/<slug>/ is one permanent page per live forecast
// file (forecasts/<n>/<slug>.json). One route with an optional slug, so that the build also works before the first
// live forecast exists (a separate [slug] route without entries would be an unseen prerender route).
import { error } from '@sveltejs/kit';
import { bundle } from '$lib/server/bundle';
import { slugOf } from '../../parts/model';
import type { EntryGenerator } from './$types';

export const entries: EntryGenerator = async () => {
  const b = bundle();
  const out: { id: string; slug?: string }[] = [];
  for (const c of (await b.overview()).calendar) {
    out.push({ id: c.id });
    if (c.id === 'd2') continue;
    for (const f of (await b.nowcast(c.id)).forecasts ?? []) if (f.period) out.push({ id: c.id, slug: slugOf(f) });
  }
  return out;
};

export async function load({ params }) {
  const b = bundle();
  const [m, ov] = await Promise.all([b.manifest(), b.overview()]);
  if (!ov.calendar.some((c) => c.id === params.id)) error(404, `okänd prognos ${params.id}`);
  const site = { today: String(m.today ?? ov.record.date), repo: m.repo ?? null, sha: m.git_sha ?? null };
  if (params.id === 'd2') {
    if (params.slug) error(404, 'D2 har inga sidor per prognos');
    return { kind: 'd2' as const, site, d2: await b.horizons() };
  }
  const nc = await b.nowcast(params.id);
  if (params.slug) {
    if (!(nc.forecasts ?? []).some((f) => f.period && slugOf(f) === params.slug)) error(404, `ingen skarp prognos ${params.slug}`);
    return { kind: 'forecast' as const, site, nc, slug: params.slug };
  }
  return { kind: 'n' as const, site, nc };
}
