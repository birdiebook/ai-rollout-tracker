import { bundle } from '$lib/server/bundle';

export async function load() {
  const b = bundle();
  const [m, ov] = await Promise.all([b.manifest(), b.overview()]);
  return {
    site: {
      provisional: m.provisional === true,
      note: m.note ?? null,
      schemaVersion: String(m.schema_version),
      build: { sha: m.build?.git_sha ?? null, built: m.build?.built_utc ?? null, repo: m.build?.repo ?? null },
      record: ov.record
    }
  };
}
