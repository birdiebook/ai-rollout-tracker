// Typed loaders for the site_bundle. One implementation for both sides: the server (prerender) reads files from
// disk (src/lib/server/bundle.ts), the browser fetches the same files from <base>/data/ (clientBundle below).
// Every document gets a structural check of the fields the pages rely on, and the manifest's schema major version
// must match: a contract break stops the build (handleHttpError: 'fail'), like the Python data tests do.

import type { Branch, Flow, Horizons, Manifest, Method, Nowcast, Overview, Regime, Report, ReportIndex, Series, SeriesIndex, Story, StoryIndex, WithheldDoc } from './types';
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
    const v = d.version ?? d.schema_version;
    if (v === undefined || v === null) throw new BundleError(p, 'missing field "version"');
    const major = Number(String(v).split('.')[0]);
    if (major !== SCHEMA_MAJOR) throw new BundleError(p, `schema version ${v}, the site supports ${SCHEMA_MAJOR}.x`);
  }) as Check,
  overview: ((d, p) => {
    need(d, p, { record: 'object', headline: 'object', branches: 'array', stripes: 'object', calendar: 'array' });
    need(d.stripes as Record<string, unknown>, p + '#stripes', { months: 'array', rows: 'array', thresholds: 'object' });
  }) as Check,
  branch: ((d, p) => need(d, p, { code: 'string', name: 'string', state: 'any', index: 'any' })) as Check,
  seriesIndex: ((d, p) => need(d, p, { series: 'array' })) as Check,
  series: ((d, p) => need(d, p, { key: 'string', label: 'string', license: 'object', levels: 'any' })) as Check,
  nowcast: ((d, p) => need(d, p, { id: 'string', title: 'string' })) as Check,
  horizons: ((d, p) => need(d, p, { record: 'object', first_live: 'string', targets: 'array', groups: 'object' })) as Check,
  withheld: ((d, p) => need(d, p, { withheld: 'array' })) as Check,
  regime: ((d, p) =>
    need(d, p, { record: 'object', available: 'boolean', months: 'array', blocks: 'array', shifts: 'array', breaks: 'array', n_breaks_withheld: 'number' })) as Check,
  story: ((d, p) => need(d, p, { month: 'string', known: 'string', status: 'string', headline: 'string', cards: 'array' })) as Check,
  storyIndex: ((d, p) => need(d, p, { months: 'array', latest: 'any', rule: 'object' })) as Check,
  report: ((d, p) =>
    need(d, p, { quarter: 'string', known: 'string', status: 'string', headline: 'string', months: 'array', branches: 'array', chain: 'array', nowcasts: 'array', regime: 'object' })) as Check,
  reportIndex: ((d, p) => need(d, p, { quarters: 'array', latest: 'any', first_live: 'string' })) as Check,
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
    /** D2 (1–8 quarters, shadow) has its own schema (`horizons`), so it is not a `nowcast()` document */
    horizons: () => get<Horizons>('nowcast/d2.json', checks.horizons),
    /** C4 regime and structural breaks (W10) */
    regime: () => get<Regime>('regime.json', checks.regime),
    /** names and reasons of the series with publish=False (never values) */
    withheld: () => get<WithheldDoc>('withheld.json', checks.withheld),
    /** W13: the monthly story (cards selected by the pre-registered rule) and its index */
    story: async (month: string) => get<Story>(`story/${safe(month)}.json`, checks.story),
    storyIndex: () => get<StoryIndex>('story/index.json', checks.storyIndex),
    /** W14: the quarterly report as data (report/<YYYYQn>.json) and its index */
    report: async (quarter: string) => get<Report>(`report/${safe(quarter)}.json`, checks.report),
    reportIndex: () => get<ReportIndex>('report/index.json', checks.reportIndex),
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
