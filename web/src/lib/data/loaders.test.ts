import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { fsBundle } from '$lib/server/bundle';
import { BundleError, createBundle, SCHEMA_MAJOR } from './loaders';
import { BRANCH_CODES } from './types';

// The loaders run against every fixture set that exists: W4's provisional one and, once committed, W3's.
const dirs = [resolve('fixtures/provisional'), resolve('../web-data-fixtures'), resolve('../web-data-fixtures/site_bundle')]
  .filter((d) => existsSync(resolve(d, 'manifest.json')));

describe.each(dirs)('bundle fixtures in %s', (dir) => {
  const b = fsBundle(dir);
  it('manifest has the supported schema major version', async () => {
    expect(Number(String((await b.manifest()).schema_version).split('.')[0])).toBe(SCHEMA_MAJOR);
  });
  it('overview has headline, nine branches and stripes', async () => {
    const ov = await b.overview();
    expect(ov.headline.sentence.length).toBeGreaterThan(0);
    expect(ov.branches.map((x) => x.code)).toEqual([...BRANCH_CODES]);
    expect(ov.stripes.rows.every((r) => r.index.length === ov.stripes.months.length)).toBe(true);
    expect(['live', 'reconstructed']).toContain(ov.record.status);
  });
  it('every branch, listed series and nowcast loads', async () => {
    const e = await b.entries();
    for (const c of e.branches) expect((await b.branch(c)).code).toBe(c);
    for (const k of e.series) expect((await b.series(k)).key).toBe(k);
    for (const id of e.nowcasts.filter((i) => i !== 'd2')) expect((await b.nowcast(id)).id).toBe(id);
  });
});

describe('contract checks', () => {
  const mem = (docs: Record<string, unknown>) => createBundle(async (p) => {
    if (!(p in docs)) throw new BundleError(p, 'missing');
    return docs[p];
  });
  it('refuses another schema major version', async () => {
    await expect(mem({ 'manifest.json': { schema_version: '2.0.0' } }).manifest()).rejects.toThrow(/schema_version/);
  });
  it('refuses a document without a required field', async () => {
    await expect(mem({ 'overview.json': { record: {}, headline: {}, branches: [], calendar: [] } }).overview()).rejects.toThrow(/stripes/);
  });
  it('refuses path traversal in ids', async () => {
    await expect(mem({}).series('../manifest')).rejects.toThrow(/invalid id/);
  });
  it('refuses non-objects', async () => {
    await expect(mem({ 'flow.json': [1, 2] }).flow()).rejects.toThrow(/not a JSON object/);
  });
});
