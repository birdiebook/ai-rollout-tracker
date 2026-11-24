import { bundle } from '$lib/server/bundle';

export async function load() {
  return { overview: await bundle().overview() };
}
