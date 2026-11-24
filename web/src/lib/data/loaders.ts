// Typed loaders for the site_bundle. One implementation for both sides: the server (prerender) reads files from
// disk (src/lib/server/bundle.ts), the browser fetches the same files from <base>/data/ (clientBundle below).
// Every document gets a structural check of the fields the pages rely on, and the manifest's schema major version
// must match: a contract break stops the build (handleHttpError: 'fail'), like the Python data tests do.

import type { Branch, Flow, Manifest, Method, Nowcast, Overview, Series, SeriesIndex } from './types';
import { BRANCH_CODES } from './types';

/** Supported major version of the bundle schema (W3: schema/v1). */
export const SCHEMA_MAJOR = 1;

export type Reader = (path: string) => Promise<unknown>;

export class BundleError extends Error {
  constructor(path: string, msg: string) {
    super(`site_bundle ${path}: ${msg}`);
    this.name = 'BundleError';
  }
}

type Check = (doc: Record<string, unknown>, path: string) => void;

const isObj = (x: unknown): x is Record<string, unknown> => typeof x === 'object' && x !== null && !Array.isArray(x);

function need(doc: Record<string, unknown>, path: string, fields: Record<string, 'string' | 'number' | 'array' | 'object' | 'boolean' | 'any'>) {
  for (const [f, t] of Object.entries(fields)) {
    if (!(f in doc)) throw new BundleError(path, `missing field "${f}"`);
    const v = doc[f];
    if (t === 'any' || v === null) continue;
    const ok = t === 'array' ? Array.isArray(v) : t === 'object' ? isObj(v) : typeof v === t;
    if (!ok) throw new BundleError(path, `field "${f}" is not ${t}`);
  }
}

const checks = {
  manifest: ((d, p) => {
    need(d, p, { schema_version: 'any' });
    const major = Number(String(d.schema_version).split('.')[0]);
    if (major !== SCHEMA_MAJOR) throw new BundleError(p, `schema_version ${d.schema_version}, the site supports ${SCHEMA_MAJOR}.x`);
  }) as Check,
  overview: ((d, p) => {
    need(d, p, { record: 'object', headline: 'object', branches: 'array', stripes: 'object', calendar: 'array' });
    need(d.stripes as Record<string, unknown>, p + '#stripes', { months: 'array', rows: 'array', thresholds: 'object' });
  }) as Check,
  branch: ((d, p) => need(d, p, { code: 'string', name: 'string', state: 'any', index: 'any' })) as Check,
  seriesIndex: ((d, p) => need(d, p, { series: 'array' })) as Check,
  series: ((d, p) => need(d, p, { key: 'string', label: 'string', license: 'object', levels: 'any' })) as Check,
  nowcast: ((d, p) => need(d, p, { id: 'string', title: 'string' })) as Check,
  any: (() => undefined) as Check
};

export function createBundle(read: Reader) {
  const cache = new Map<string, Promise<unknown>>();
  async function get<T>(path: string, check: Check): Promise<T> {
    let p = cache.get(path);
    if (!p) {
      p = read(path);
      cache.set(path, p);
    }
    const doc = await p;
    if (!isObj(doc)) throw new BundleError(path, 'not a JSON object');
    check(doc, path);
    return doc as T;
  }
  const safe = (id: string) => {
    if (!/^[A-Za-z0-9_][A-Za-z0-9_.-]*$/.test(id)) throw new BundleError(id, 'invalid id');
    return id;
  };

  return {
    manifest: () => get<Manifest>('manifest.json', checks.manifest),
    overview: () => get<Overview>('overview.json', checks.overview),
    flow: () => get<Flow>('flow.json', checks.any),
    method: () => get<Method>('method.json', checks.any),
    branch: async (code: string) => get<Branch>(`branch/${safe(code)}.json`, checks.branch),
    seriesIndex: () => get<SeriesIndex>('series/index.json', checks.seriesIndex),
    series: async (key: string) => get<Series>(`series/${safe(key)}.json`, checks.series),
    nowcast: async (id: string) => get<Nowcast>(`nowcast/${safe(id)}.json`, checks.nowcast),
    /** ids for prerendering the dynamic routes */
    async entries() {
      const [idx, ov] = await Promise.all([this.seriesIndex(), this.overview()]);
      return {
        branches: [...BRANCH_CODES] as string[],
        series: idx.series.map((s) => s.key),
        nowcasts: ov.calendar.map((c) => c.id)
      };
    }
  };
}

export type Bundle = ReturnType<typeof createBundle>;

/** Browser side: the bundle is published next to the pages under <base>/data/ (scripts/sync-bundle.mjs). */
export function clientBundle(fetcher: typeof fetch, base: string): Bundle {
  return createBundle(async (path) => {
    const r = await fetcher(`${base}/data/${path}`);
    if (!r.ok) throw new BundleError(path, `HTTP ${r.status}`);
    return r.json();
  });
}
