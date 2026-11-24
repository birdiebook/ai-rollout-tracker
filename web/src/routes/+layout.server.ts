import { bundle } from '$lib/server/bundle';
import { schemaVersion } from '$lib/data';

export async function load() {
  const b = bundle();
  const [m, ov] = await Promise.all([b.manifest(), b.overview()]);
  return {
    site: {
      testdata: m.synthetic === true || m.provisional === true,
      note: m.note ?? 'Syntetiska värden för tester av gränssnittet, inga riktiga värden.',
      schemaVersion: schemaVersion(m),
      build: { sha: m.git_sha ?? null, built: m.built_utc ?? null, repo: m.repo ?? null },
      record: ov.record
    }
  };
}
