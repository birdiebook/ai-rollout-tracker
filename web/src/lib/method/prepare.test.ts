import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { asOf, periodVersions } from '$lib/series/versions';
import type { Versions } from '$lib/series/types';
import { linkify, mostRevisedPeriod, pickRevised, revisedCandidates, safeHref, slicePeriods, sourceView } from './prepare';

const bundles = [resolve('../web-data-fixtures'), process.env.SITE_BUNDLE_DIR ? resolve(process.env.SITE_BUNDLE_DIR) : null].filter(
  (d): d is string => !!d && existsSync(resolve(d, 'manifest.json'))
);

describe.each(bundles)('as_of inputs in %s', (dir) => {
  const idx = JSON.parse(readFileSync(resolve(dir, 'series/index.json'), 'utf-8'));
  const docs = revisedCandidates(idx.series).map((k) => JSON.parse(readFileSync(resolve(dir, `series/${k}.json`), 'utf-8')));
  const key = pickRevised(docs)?.key;
  it('finds a revised monthly series with a stable base', () => {
    expect(key).toBeTruthy();
    expect(docs.every((d) => !/basår enligt vintage/.test(d.unit))).toBe(true);
  });
  it('a period slice replays exactly like the full versions on every version day', () => {
    const v = JSON.parse(readFileSync(resolve(dir, `series/${key}.json`), 'utf-8')).versions as Versions;
    const from = v.periods[Math.floor(v.periods.length * 0.6)];
    const s = slicePeriods(v, from);
    expect(s.n_versions).toBeLessThan(v.n_versions);
    for (const day of [...v.dates.filter((_, i) => i % 7 === 0), v.last_known]) {
      const full = [...asOf(v, day)].filter(([p]) => p >= from);
      expect([...asOf(s, day)].sort()).toEqual(full.sort());
    }
    const p = mostRevisedPeriod(s);
    expect(p).not.toBeNull();
    expect(periodVersions(s, p as string).length).toBeGreaterThanOrEqual(2);
  });
});

describe.each(bundles)('sources in %s', (dir) => {
  const method = JSON.parse(readFileSync(resolve(dir, 'method.json'), 'utf-8'));
  it('every link is absolute http(s) and the text survives unchanged', () => {
    for (const s of method.sources) {
      const v = sourceView(s);
      expect(v.name.map((x) => x.text).join('')).toBe(s.source);
      expect(v.text.map((x) => x.text).join('')).toBe(s.license_text);
      for (const seg of [...v.name, ...v.text]) if ('href' in seg) expect(seg.href).toMatch(/^https?:\/\/[^/]+\.[a-z]{2,}/i);
    }
  });
});

describe('linkify', () => {
  it('finds full URLs, www hosts and host/path references, trims trailing punctuation', () => {
    const segs = linkify('CC BY 4.0 (metr.org/time-horizons: "x"), see www.eia.gov/about/copyrights_reuse.php). And http://aws.amazon.com.\'');
    expect(segs.filter((s) => 'href' in s).map((s) => (s as { href: string }).href)).toEqual([
      'https://metr.org/time-horizons',
      'https://www.eia.gov/about/copyrights_reuse.php',
      'http://aws.amazon.com/'
    ]);
  });
  it('leaves file names, statute numbers and plain words alone', () => {
    expect(linkify('README in benchmark_data.zip; 17 U.S.C. § 105; model_prices.json').every((s) => !('href' in s))).toBe(true);
  });
  it('refuses other schemes and credentials', () => {
    expect(safeHref('javascript:alert(1)')).toBeNull();
    expect(safeHref('https://user:pw@example.com/x')).toBeNull();
  });
});
