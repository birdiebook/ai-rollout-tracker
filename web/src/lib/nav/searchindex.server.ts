// The search index (W12), built at prerender time from the bundle: series/index.json (publishable series only, the
// licence gate has already run in Python), the branches and leads, the forecasts and the main pages. Served as
// <base>/sok.json and fetched by the browser only when the search opens.
import { resolve } from '$app/paths';
import type { Bundle } from '$lib/data';
import { periodLabel, stateStyle } from '$lib/design';
import { freqLabel } from '$lib/series/period';
import { slugOf } from '../../routes/prognoser/parts/model';
import type { SearchIndex, SearchItem } from './search';

interface FlowLead {
  code: string;
  name: string;
  content?: string;
  branches: { code: string; name: string }[];
  nowcasts: { id: string; label: string }[];
}

const word = (s: string | null | undefined) => (s === 'inga registrerade kärnserier' ? s : stateStyle(s).word);

export async function buildSearchIndex(b: Bundle): Promise<SearchIndex> {
  const [ov, idx, flow] = await Promise.all([b.overview(), b.seriesIndex(), b.flow()]);
  const ls = (flow as unknown as { leads: FlowLead[] }).leads;
  const branchName = new Map(ov.branches.map((x) => [x.code, x.name]));
  const leadsOf = (code: string) => ls.filter((l) => l.branches.some((x) => x.code === code)).map((l) => l.code);
  const items: SearchItem[] = [];

  items.push(
    { t: 'sida', id: 'laget', l: 'Läget', s: 'Startsidan: kedjan, tre frågor och tillståndsränderna', h: resolve('/'), k: 'start hem översikt' },
    { t: 'sida', id: 'flode', l: 'Flödet L1–L9', s: 'Kedjan från förmåga till el', h: resolve('/flode'), k: 'kedjan led' },
    { t: 'sida', id: 'prognoser', l: 'Prognoser', s: 'N1–N6 och D2 med intervall och facit', h: resolve('/prognoser'), k: 'nowcast facit kalender' },
    { t: 'sida', id: 'avstamningar', l: 'Avstämningar', s: 'Går leden ihop? Kvoter mellan leden med komponenter', h: resolve('/avstamningar'), k: 'kvot avstämning A5 reconciliation glapp' },
    { t: 'sida', id: 'regim', l: 'Regim och strukturbrott', s: 'Har något fundamentalt ändrats? C4 per block', h: resolve('/regim'), k: 'regimskifte strukturbrott bocpd c4 inbromsning' },
    { t: 'sida', id: 'metod', l: 'Metod', s: 'Måttregistret, tillståndsregler, licenser', h: resolve('/metod'), k: 'register regler licens dödband' },
    { t: 'sida', id: 'sok', l: 'Alla serier', s: 'Registret över alla publicerade serier', h: resolve('/sok'), k: 'register katalog lista' }
  );

  for (const l of ls)
    items.push({
      t: 'led',
      id: l.code,
      l: `${l.code} ${l.name}`,
      s: l.branches.map((x) => `${x.code} ${x.name}`).join(' · '),
      h: resolve('/flode/[led]', { led: l.code }),
      k: [l.content, ...l.nowcasts.map((n) => n.label)].filter(Boolean).join(' ')
    });

  for (const x of ov.branches)
    items.push({
      t: 'gren',
      id: x.code,
      l: `${x.code} ${x.name}`,
      s: `${word(x.state)}${leadsOf(x.code).length ? ' · ' + leadsOf(x.code).join(', ') : ''}`,
      h: resolve('/gren/[id]', { id: x.code }),
      k: x.question ?? ''
    });

  for (const cal of ov.calendar) {
    const isD2 = cal.id === 'd2';
    items.push({
      t: 'prognos',
      id: cal.id,
      l: `${cal.label} ${cal.title}`,
      s: [isD2 ? 'skugga' : cal.champion ? `huvudmodell ${cal.champion}` : null, cal.next_origin ? `nästa ${cal.next_origin}` : null].filter(Boolean).join(' · '),
      h: resolve('/prognoser/[id]/[[slug]]', { id: cal.id }),
      k: 'prognos nowcast'
    });
    if (isD2) continue;
    const nc = await b.nowcast(cal.id);
    for (const f of nc.forecasts ?? []) {
      if (!f.period) continue;
      const slug = slugOf(f);
      items.push({
        t: 'prognos',
        id: `${cal.id}/${slug}`,
        l: `${cal.label} för ${periodLabel(f.period, true)}`,
        s: `skarp prognos${f.origin ? ` gjord ${f.origin}` : ''} · ${nc.title}`,
        h: resolve('/prognoser/[id]/[[slug]]', { id: cal.id, slug }),
        k: `skarp ${f.period}`
      });
    }
  }

  for (const s of idx.series) {
    const bn = s.branch ? branchName.get(s.branch) : null;
    items.push({
      t: 'serie',
      id: s.key,
      l: s.label,
      s: [s.branch, freqLabel(s.freq), String(s.source_family ?? '')].filter(Boolean).join(' · '),
      h: resolve('/serie/[key]', { key: s.key }),
      k: [bn, s.unit, s.core ? 'kärnserie' : null, s.reconciliation ? 'avstämning' : null].filter(Boolean).join(' ')
    });
  }
  return { v: 1, as_of: idx.as_of, items };
}
