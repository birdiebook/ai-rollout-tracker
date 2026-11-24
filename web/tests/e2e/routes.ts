import { readFileSync } from 'node:fs';

/** One URL per route (relative to the base), the dynamic ones with the first id in the bundle. */
export function routes(): { name: string; path: string }[] {
  const idx = JSON.parse(readFileSync('static/data/series/index.json', 'utf-8')) as { series: { key: string }[] };
  return [
    { name: 'hem', path: '' },
    { name: 'flode', path: 'flode/' },
    { name: 'gren', path: 'gren/G6/' },
    { name: 'serie', path: `serie/${idx.series[0].key}/` },
    { name: 'prognoser', path: 'prognoser/' },
    { name: 'metod', path: 'metod/' },
    { name: 'katalog', path: '_katalog/' }
  ];
}
