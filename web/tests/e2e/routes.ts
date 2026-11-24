import { readFileSync } from 'node:fs';

/** One URL per route (relative to the base), the dynamic ones with the first id in the bundle. */
export function routes(): { name: string; path: string }[] {
  const idx = JSON.parse(readFileSync('static/data/series/index.json', 'utf-8')) as { series: SeriesEntry[] };
  return [
    { name: 'hem', path: '' },
    { name: 'flode', path: 'flode/' },
    { name: 'gren', path: 'gren/G6/' },
    { name: 'gren-g9', path: 'gren/G9/' },
    { name: 'led', path: 'flode/L6/' },
    { name: 'led-l9', path: 'flode/L9/' },
    { name: 'serie', path: `serie/${idx.series[0].key}/` },
    ...seriesVariants(idx.series),
    { name: 'prognoser', path: 'prognoser/' },
    { name: 'metod', path: 'metod/' },
    { name: 'katalog', path: '_katalog/' }
  ];
}

interface SeriesEntry {
  key: string;
  freq?: string | null;
  n_versions?: number;
}

/** W7: one series page per frequency in the bundle (D/W/2W/M/Q/A), plus the most revised monthly series. */
export function seriesVariants(series: SeriesEntry[]): { name: string; path: string }[] {
  const out: { name: string; path: string }[] = [];
  for (const f of ['D', 'W', '2W', 'M', 'Q', 'A']) {
    const s = series.filter((x) => x.freq === f).sort((a, b) => (b.n_versions ?? 0) - (a.n_versions ?? 0))[0];
    if (s && s.key !== series[0].key) out.push({ name: `serie-${f.toLowerCase()}`, path: `serie/${s.key}/` });
  }
  return out;
}
