import { base } from '$app/paths';
import { bundle } from '$lib/server/bundle';
import { schemaVersion } from '$lib/data';
import { describe, publicBase } from '$lib/nav/describe.server';

export async function load({ route, params, url }) {
  const b = bundle();
  const [m, ov] = await Promise.all([b.manifest(), b.overview()]);
  // W12: title, description, share image and citation for this page, from data (head tags and citation line)
  const { meta } = await describe(b, { routeId: route.id, params: params as Record<string, string> });
  const site = publicBase(m, base);
  const rel = url.pathname.startsWith(base) ? url.pathname.slice(base.length) : url.pathname;
  return {
    site: {
      testdata: m.synthetic === true || m.provisional === true,
      note: m.note ?? 'Syntetiska värden för tester av gränssnittet, inga riktiga värden.',
      schemaVersion: schemaVersion(m),
      build: { sha: m.git_sha ?? null, built: m.built_utc ?? null, repo: m.repo ?? null },
      record: ov.record
    },
    meta: { ...meta, url: site + rel, image: `${site}/og/${meta.og}.png` }
  };
}
