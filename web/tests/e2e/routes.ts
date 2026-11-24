import { readFileSync } from 'node:fs';

/** W8: the first live forecast page, when the bundle has one (forecasts/<n>/<slug>.json -> prognoser/<n>/<slug>/). */
function liveForecastPages(): { name: string; path: string }[] {
  const out: { name: string; path: string }[] = [];
  for (const id of ['n1', 'n2', 'n3', 'n4', 'n5', 'n6']) {
    const nc = JSON.parse(readFileSync(`static/data/nowcast/${id}.json`, 'utf-8')) as { forecasts?: { file: string; period: string | null }[] };
    for (const f of nc.forecasts ?? []) {
      const slug = (f.file.split('/').pop() ?? '').replace(/\.json$/, '').replace(/[^A-Za-z0-9_.-]/g, '_');
      if (f.period && slug) out.push({ name: `prognos-${id}-skarp`, path: `prognoser/${id}/${slug}/` });
    }
  }
  return out;
}

/** One URL per route (relative to the base), the dynamic ones with the first id in the bundle. */
export function routes(): { name: string; path: string }[] {
  const idx = JSON.parse(readFileSync('static/data/series/index.json', 'utf-8')) as { series: { key: string }[] };
  return [
    { name: 'hem', path: '' },
    { name: 'flode', path: 'flode/' },
    { name: 'gren', path: 'gren/G6/' },
    { name: 'serie', path: `serie/${idx.series[0].key}/` },
    { name: 'prognoser', path: 'prognoser/' },
    { name: 'prognos-n2', path: 'prognoser/n2/' },
    { name: 'prognos-n1', path: 'prognoser/n1/' },
    { name: 'prognos-n5', path: 'prognoser/n5/' },
    { name: 'prognos-d2', path: 'prognoser/d2/' },
    ...liveForecastPages().slice(0, 1),
    { name: 'metod', path: 'metod/' },
    { name: 'katalog', path: '_katalog/' }
  ];
}
