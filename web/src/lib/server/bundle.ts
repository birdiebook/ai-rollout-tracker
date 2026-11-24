// Server side (prerender at build time): read the bundle from disk. scripts/sync-bundle.mjs copies the chosen
// bundle (SITE_BUNDLE_DIR, W3's web-data-fixtures/, or the provisional fixture) to static/data/, which is both
// what the prerender reads here and what the browser can fetch under <base>/data/.
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { BundleError, createBundle, type Bundle } from '$lib/data/loaders';

export function bundleDir(): string {
  return resolve(process.env.SITE_BUNDLE_READ_DIR ?? 'static/data');
}

export function fsBundle(dir = bundleDir()): Bundle {
  return createBundle(async (path) => {
    let text: string;
    try {
      text = await readFile(resolve(dir, path), 'utf-8');
    } catch {
      throw new BundleError(path, `not found in ${dir} (run npm run sync-bundle)`);
    }
    return JSON.parse(text);
  });
}

let shared: Bundle | undefined;
/** One cached bundle per build process. */
export const bundle = (): Bundle => (shared ??= fsBundle());
