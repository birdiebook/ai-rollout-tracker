import { bundle } from '$lib/server/bundle';

export async function load() {
  return { method: await bundle().method() };
}
