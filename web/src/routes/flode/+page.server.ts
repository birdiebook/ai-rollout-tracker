import { bundle } from '$lib/server/bundle';

export async function load() {
  const b = bundle();
  const [method, overview] = await Promise.all([b.method(), b.overview()]);
  const leads = (method.leads as { code: string; name: string; branches: string[] }[] | undefined) ?? [];
  return { leads, branches: overview.branches };
}
