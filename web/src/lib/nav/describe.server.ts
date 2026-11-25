// Page descriptions from data (W12): title, description, share image and citation for every route, computed at
// prerender time from the same bundle the pages read. Used by the root layout (head tags and the citation line,
// src/routes/+layout.server.ts) and by the share-image endpoint (src/routes/og/[...path]/+server.ts), so the
// picture and the tags always describe the same thing.
//
// Routes this module does not know (a page added by another track) get a generic description and the generic
// picture, so a new route never breaks the build.
import type { Bundle, Manifest, Overview, RecordMeta } from '$lib/data';
import { dateLabel, fmt, periodLabel, stateStyle } from '$lib/design';
import { freqLabel } from '$lib/series/period';
import type { OgGraphic, OgSpec, OgStatus } from './og';
import type { PageMeta } from './meta';
export type { Citation, PageMeta } from './meta';
import { slugOf } from '../../routes/prognoser/parts/model';

export interface RouteRef {
  routeId: string | null;
  params: Record<string, string>;
}

const SITE = 'AI-utrullningen';
/** Routes whose page component already writes <meta name="description">. */
const OWN_DESCRIPTION = new Set(['/', '/serie/[key]']);

type Ctx = { b: Bundle; m: Manifest; ov: Overview };

interface Described {
  meta: PageMeta;
  og: OgSpec;
}

const statusOf = (r: RecordMeta | undefined | null): OgStatus => (r?.status === 'live' ? 'live' : 'recon');
const recordText = (r: RecordMeta) => `${periodLabel(r.month, true)}, ${r.status === 'live' ? 'skarp ögonblicksbild' : 'rekonstruerad historik'}`;
const stateWord = (s: string | null | undefined) => (s === 'inga registrerade kärnserier' ? s : stateStyle(s).word);
const glyph = (s: string | null | undefined) => (s === 'inga registrerade kärnserier' ? '○' : stateStyle(s).glyph);

function commitOf(m: Manifest): string | null {
  const sha = m.git_sha;
  return sha && /^[0-9a-f]{7,40}$/i.test(sha) ? sha.slice(0, 7) : null;
}

const today = (c: Ctx) => String(c.m.today ?? c.ov.record.date);

/** The overview's stripes, last `n` months, every branch. */
function overviewStripes(c: Ctx, highlight: string | null = null, n = 36): OgGraphic {
  const st = c.ov.stripes;
  const k = Math.max(0, st.months.length - n);
  return {
    kind: 'stripes',
    months: st.months.slice(k).map((x) => periodLabel(x)),
    kinds: st.kind.slice(k),
    rows: st.rows.map((r) => ({ code: r.code, index: r.index.slice(k) })),
    highlight
  };
}

interface FlowLead {
  code: string;
  name: string;
  content?: string;
  branches: { code: string; name: string; state: string | null; index: number | null }[];
  nowcasts: { id: string; label: string; title: string }[];
}

async function leads(c: Ctx): Promise<FlowLead[]> {
  return ((await c.b.flow()) as unknown as { leads: FlowLead[] }).leads;
}

function chainGraphic(ls: FlowLead[], current: string | null = null): OgGraphic {
  return {
    kind: 'chain',
    current,
    leads: ls.map((l) => {
      const ix = l.branches.map((x) => x.index).filter((v): v is number => v !== null);
      return { code: l.code, index: ix.length ? ix.reduce((a, v) => a + v, 0) / ix.length : null, glyphs: l.branches.map((x) => glyph(x.state)) };
    })
  };
}

function spec(c: Ctx, s: Omit<OgSpec, 'testdata' | 'footer'> & { footer?: string }): OgSpec {
  return { footer: `Version per ${dateLabel(today(c))} · ${SITE}`, testdata: c.m.synthetic === true || c.m.provisional === true, ...s };
}

/** `timeless`: the page's name for a citation under time travel, without today's month, state or value (defaults
 *  to the title, for routes whose title says nothing about today's record). */
function page(c: Ctx, og: string, title: string, description: string, o: OgSpec, own = false, timeless = title): Described {
  return {
    meta: { title, description, ownDescription: own, og, imageAlt: `${title}. ${description}`.slice(0, 420), cite: { what: title, timeless, date: today(c), commit: commitOf(c.m) } },
    og: o
  };
}

const lastLevels = (periods: string[], values: (number | null)[], years: number) => {
  // the last `years` years of a level series, thinned to at most 360 points (enough for 1080 px)
  const lastP = periods[periods.length - 1] ?? '';
  const y = Number(lastP.slice(0, 4));
  let i0 = 0;
  if (Number.isFinite(y)) {
    const cut = String(y - years);
    i0 = Math.max(0, periods.findIndex((p) => p.slice(0, 4) > cut));
  }
  const ps = periods.slice(i0);
  const vs = values.slice(i0);
  const step = Math.ceil(ps.length / 360);
  if (step <= 1) return { ps, vs };
  const keep = (i: number) => i % step === 0 || i === ps.length - 1;
  return { ps: ps.filter((_, i) => keep(i)), vs: vs.filter((_, i) => keep(i)) };
};

function numText(v: number): string {
  const a = Math.abs(v);
  const d = a >= 100 ? 0 : a >= 10 ? 1 : 2;
  return fmt(v, d);
}

async function describeSeries(c: Ctx, key: string): Promise<Described> {
  const s = await c.b.series(key);
  const label = s.label;
  const src = String(s.source_family ?? s.source ?? '');
  const branch = s.branch ? `${s.branch} ${String(s.branch_name ?? '')}`.trim() : '';
  const m = (s.measure ?? null) as { direction?: number | null; valid?: boolean; latest_period?: string | null; pace?: number | null; pace_unit?: string | null } | null;
  const lv = s.levels;
  const lastIdx = lv ? lv.values.map((v, i) => (v === null ? -1 : i)).reduce((a, v) => Math.max(a, v), -1) : -1;
  const lastP = lv && lastIdx >= 0 ? lv.periods[lastIdx] : null;
  const lastV = lv && lastIdx >= 0 ? (lv.values[lastIdx] as number) : null;
  const dir = m?.valid && m.direction !== null && m.direction !== undefined ? ({ 1: 'ökar takten', 0: 'oförändrad takt', [-1]: 'minskar takten' } as Record<number, string>)[m.direction] : null;
  const asOf = lv?.as_of ?? today(c);
  const bits = [
    lastP && lastV !== null ? `Senaste värde ${numText(lastV)}${s.unit ? ` ${s.unit}` : ''} (${periodLabel(lastP, true)})` : null,
    dir ? `riktning: ${dir}` : null
  ].filter(Boolean);
  const description = `${bits.length ? bits.join(', ') + '. ' : ''}${[branch, freqLabel(s.freq)].filter(Boolean).join(' · ')}. Källa: ${src}. Version per ${asOf}.`;
  let graphic: OgGraphic = { kind: 'none' };
  if (lv && lv.periods.length > 1) {
    const { ps, vs } = lastLevels(lv.periods, lv.values, 10);
    graphic = { kind: 'line', values: vs, first: periodLabel(ps[0] ?? ''), last: periodLabel(ps[ps.length - 1] ?? ''), lastLabel: lastV !== null ? numText(lastV) : '' };
  }
  const og = spec(c, {
    kicker: ['Serie', s.branch, freqLabel(s.freq)].filter(Boolean).join(' · '),
    title: label,
    subtitle: [s.unit, dir].filter(Boolean).join(' · '),
    footer: `Version per ${dateLabel(asOf)} · ${key}`,
    credit: s.license?.attribution ?? undefined,
    status: null,
    graphic
  });
  return {
    meta: {
      title: label,
      description,
      ownDescription: true,
      og: `serie/${key}`,
      imageAlt: `${label}: nivån de senaste tio åren. ${description}`.slice(0, 420),
      cite: { what: `serie ${label} (${key}; källa: ${src})`, timeless: `serie ${label} (${key}; källa: ${src})`, date: asOf, commit: commitOf(c.m) }
    },
    og
  };
}

async function describeNowcast(c: Ctx, id: string, slug: string | undefined): Promise<Described> {
  if (id === 'd2') {
    const d2 = await c.b.horizons();
    const t = d2.targets.find((x) => x.fan) ?? d2.targets[0];
    const title = 'D2 Prognoser 1–8 kvartal';
    const description = `Skuggprognoser för ${d2.targets.length} mål, 1–8 kvartal framåt.${d2.next_origin ? ` Nästa prognosdag ${dateLabel(d2.next_origin)}.` : ''}`;
    const h = t?.history;
    const graphic: OgGraphic =
      h && h.periods.length > 1 ? { kind: 'line', values: lastLevels(h.periods, h.values, 10).vs, first: periodLabel(lastLevels(h.periods, h.values, 10).ps[0]), last: periodLabel(h.periods[h.periods.length - 1]), lastLabel: '' } : { kind: 'none' };
    return page(c, 'prognoser/d2', title, description, spec(c, { kicker: 'Prognos · skugga', title, subtitle: t ? `${t.label}${t.unit ? `, ${t.unit}` : ''}` : '', status: statusOf(d2.record), graphic }));
  }
  const nc = await c.b.nowcast(id);
  const live = (nc.forecasts ?? []).filter((f) => f.period);
  const unit = nc.unit ?? '';
  const dec = nc.decimals ?? 0;
  const hist = nc.history;
  const row = slug ? live.find((f) => slugOf(f) === slug) : live[live.length - 1];
  const histG = (): OgGraphic => {
    if (!hist || hist.periods.length < 2) return { kind: 'none' };
    const { ps, vs } = lastLevels(hist.periods, hist.values, 6);
    const i80 = row?.intervals?.['80'] ?? null;
    return {
      kind: 'line',
      values: vs,
      first: periodLabel(ps[0]),
      last: periodLabel(ps[ps.length - 1]),
      lastLabel: (() => {
        const v = [...vs].reverse().find((x) => x !== null);
        return v === undefined || v === null ? '' : `${fmt(v, dec)} ${unit}`.trim();
      })(),
      forecast: row && row.value !== null ? { value: row.value, lo: i80?.[0] ?? null, hi: i80?.[1] ?? null, label: `${fmt(row.value, dec)} ${unit}`.trim() } : null
    };
  };
  if (slug && row) {
    const i80 = row.intervals?.['80'];
    const title = `${nc.label} för ${periodLabel(String(row.period), true)}: ${fmt(row.value, dec)} ${unit}`.trim();
    const description = `Skarp prognos${row.origin ? ` gjord ${dateLabel(String(row.origin))}` : ''} med huvudmodellen ${row.champion}${i80 && i80[0] !== null && i80[1] !== null ? `, 80 %-intervall ${fmt(i80[0], dec)}–${fmt(i80[1], dec)} ${unit}` : ''}. ${nc.title}.`;
    return page(c, `prognoser/${id}/${slug}`, title, description, spec(c, { kicker: `Prognos · ${nc.label} · skarp`, title, subtitle: nc.title, status: 'live', graphic: histG() }), false, `${nc.label} ${nc.title}, en skarp prognos`);
  }
  const title = `${nc.label} ${nc.title}`;
  const next = nc.next_origin ? `Nästa skarpa prognos ${dateLabel(nc.next_origin)}${nc.next_period ? ` för ${periodLabel(nc.next_period, true)}` : ''}.` : '';
  const description = `Huvudmodell ${nc.champion ?? '–'}. ${live.length ? `${live.length} skarp${live.length === 1 ? '' : 'a'} prognos${live.length === 1 ? '' : 'er'} med öppet facit.` : 'Ännu ingen skarp prognos.'} ${next}`.trim();
  return page(c, `prognoser/${id}`, title, description, spec(c, { kicker: `Prognos · ${nc.label}`, title: nc.title, subtitle: next || `Huvudmodell ${nc.champion ?? '–'}`, status: live.length ? 'live' : null, graphic: histG() }));
}

/** Title, description, share image and citation for one route. */
export async function describe(b: Bundle, ref: RouteRef): Promise<Described> {
  const [m, ov] = await Promise.all([b.manifest(), b.overview()]);
  const c: Ctx = { b, m, ov };
  const r = ov.record;
  const p = ref.params;
  switch (ref.routeId) {
    case '/': {
      const title = `Läget ${periodLabel(r.month, true)}`;
      const description = [ov.headline.sentence, ov.headline.change_sentence].filter(Boolean).join(' ');
      return page(c, 'start', `${SITE}: ${title.toLowerCase()}`, description, spec(c, { kicker: recordText(r), title: ov.headline.sentence, subtitle: ov.headline.change_sentence ?? '', status: statusOf(r), graphic: overviewStripes(c) }), true, 'startsidan, läget');
    }
    case '/flode': {
      const ls = await leads(c);
      const title = 'Flödet L1–L9';
      const description = `Nio led från förmåga till el, ${periodLabel(r.month, true)}. ${ov.headline.sentence}`;
      return page(c, 'flode', title, description, spec(c, { kicker: recordText(r), title: 'Flödet från förmåga till forskning', subtitle: ov.headline.sentence, status: statusOf(r), graphic: chainGraphic(ls) }));
    }
    case '/flode/[led]': {
      const ls = await leads(c);
      const l = ls.find((x) => x.code === p.led);
      if (l) {
        const states = l.branches.map((x) => `${x.code} ${x.name}: ${stateWord(x.state)}${x.index !== null ? ` (index ${fmt(x.index, 2)})` : ''}`).join('; ');
        const title = `${l.code} ${l.name}`;
        const description = `${l.content ? l.content + '. ' : ''}${states}, ${periodLabel(r.month, true)}.${l.nowcasts.length ? ` Prognoser: ${l.nowcasts.map((n) => n.label).join(', ')}.` : ''}`;
        return page(c, `flode/${l.code}`, title, description, spec(c, { kicker: `Led ${l.code} · ${recordText(r)}`, title, subtitle: l.branches.map((x) => `${x.code} ${stateWord(x.state)}`).join(' · '), status: statusOf(r), graphic: chainGraphic(ls, l.code) }), false, `led ${l.code} ${l.name}`);
      }
      break;
    }
    case '/gren/[id]': {
      const br = ov.branches.find((x) => x.code === p.id);
      if (br) {
        const doc = (await b.branch(br.code)) as unknown as { history: { month: string; kind: string | null; index: number | null }[]; question?: string; record: RecordMeta };
        const counts = [br.n_up, br.n_neutral, br.n_down].every((x) => typeof x === 'number') ? ` Av ${br.n_series ?? 0} räknade serier: ${br.n_up} ökar, ${br.n_neutral} oförändrade och ${br.n_down} minskar takten.` : '';
        const title = `${br.code} ${br.name}: ${stateWord(br.state)}`;
        const description = `${br.question ? br.question + ' ' : ''}Diffusionsindex ${fmt(br.index, 2)} i ${periodLabel(doc.record.month, true)} (${doc.record.status === 'live' ? 'skarp' : 'rekonstruerad'}).${counts}`;
        const hist = doc.history.slice(-48);
        const th = ov.stripes.thresholds;
        const graphic: OgGraphic = hist.length > 1
          ? { kind: 'index', months: hist.map((h) => periodLabel(h.month)), kinds: hist.map((h) => h.kind), index: hist.map((h) => h.index), lo: th.braking_at_most, hi: th.accelerating_at_least }
          : overviewStripes(c, br.code);
        return page(c, `gren/${br.code}`, title, description, spec(c, { kicker: `Gren ${br.code} · ${recordText(doc.record)}`, title, subtitle: br.question ?? '', status: statusOf(doc.record), graphic }), false, `gren ${br.code} ${br.name}`);
      }
      break;
    }
    case '/serie/[key]':
      return describeSeries(c, p.key);
    case '/prognoser': {
      const next = [...ov.calendar].filter((x) => x.next_origin).sort((a, x) => String(a.next_origin).localeCompare(String(x.next_origin)))[0];
      const title = 'Prognoser med öppet facit';
      const description = `N1–N6 och D2 med intervall, kalibrering och facit.${next ? ` Nästa skarpa prognos: ${next.label} ${dateLabel(String(next.next_origin))}${next.next_period ? ` för ${periodLabel(next.next_period, true)}` : ''}.` : ''}`;
      return page(c, 'prognoser', title, description, spec(c, { kicker: 'Prognoser · N1–N6 och D2', title, subtitle: description, status: null, graphic: { kind: 'none' } }));
    }
    case '/prognoser/[id]/[[slug]]':
      return describeNowcast(c, p.id, p.slug);
    case '/avstamningar': {
      const fl = (await b.flow()) as unknown as { reconciliations: ({ hidden?: boolean; key?: string; short?: string; label?: string; direction?: number | null } | Record<string, unknown>)[]; reconciliations_available?: boolean };
      const recs = fl.reconciliations ?? [];
      const shown = recs.filter((x) => !('hidden' in x));
      const title = 'Avstämningar: går leden ihop?';
      const description = `${shown.length} kvoter mellan leden med sina komponenter${recs.length > shown.length ? ` (${recs.length - shown.length} till hålls inne av licensskäl)` : ''}, ${periodLabel(r.month, true)}. När en kvot rör sig växer det ena ledet snabbare än det andra.`;
      return page(c, 'avstamningar', title, description, spec(c, { kicker: `Avstämningar · ${recordText(r)}`, title, subtitle: description, status: statusOf(r), graphic: chainGraphic(await leads(c)) }));
    }
    case '/regim': {
      const rg = await b.regime();
      const title = 'Regim och strukturbrott';
      const latest = rg.blocks.map((x) => x.latest).filter((x): x is NonNullable<typeof x> => !!x);
      const description = rg.available
        ? `Sannolikheten för inbromsning per block (C4) ur de skarpa ögonblicksbilderna, ${latest.length} block, ${rg.shifts.length} skiften och ${rg.breaks.length + rg.n_breaks_withheld} strukturbrott.`
        : 'Regimmodellen (C4) visas först från den första skarpa ögonblicksbilden; den rekonstrueras aldrig bakåt.';
      return page(c, 'regim', title, description, spec(c, { kicker: 'Regim · C4', title: 'Har något fundamentalt ändrats?', subtitle: description, status: rg.available ? statusOf(rg.record) : null, graphic: overviewStripes(c) }));
    }
    case '/metod': {
      const meth = (await b.method()) as { n_series?: number; n_published?: number; n_withheld?: number };
      const title = 'Metod: förregistrerade mått och tillstånd';
      const description = `Mått, tillståndsregler och intervall är låsta i måttregistret innan data analyseras.${meth.n_series ? ` ${fmt(meth.n_series)} serier i katalogen, ${fmt(meth.n_published ?? 0)} publicerade och ${fmt(meth.n_withheld ?? 0)} inhållna av licensskäl.` : ''}`;
      return page(c, 'metod', title, description, spec(c, { kicker: 'Metod', title, subtitle: description, status: null, graphic: { kind: 'none' } }));
    }
    case '/manad/[manad]': {
      // W13's page writes its own <title> and description; the share image names the month and its headline only
      // (no figure: today's stripes would show later knowledge than the month's story)
      const st = (await b.story(p.manad)) as unknown as { month_sv?: string; month: string; headline: string; status: string };
      const title = `Månadens berättelse – ${st.month_sv ?? st.month}`;
      return page(c, `manad/${st.month}`, title, st.headline, spec(c, { kicker: 'Månadens berättelse', title: st.headline, subtitle: st.month_sv ?? st.month, status: st.status === 'live' ? 'live' : null, graphic: { kind: 'none' } }), true, 'Månadens berättelse');
    }
    case '/sok': {
      const idx = await b.seriesIndex();
      const title = 'Sök och register';
      const description = `Alla ${fmt(idx.series.length)} publicerade serier, nio grenar, nio led och prognoserna, sökbart.`;
      return page(c, 'sok', title, description, spec(c, { kicker: 'Sök', title, subtitle: description, status: statusOf(r), graphic: overviewStripes(c) }));
    }
    case '/_katalog': {
      const title = 'Komponentkatalog';
      return page(c, 'katalog', title, 'Designsystemets färger, typografi och diagramprimitiver med exempelvärden.', spec(c, { kicker: 'Designsystemet', title, subtitle: 'Exempelvärden, inte data.', status: null, graphic: { kind: 'none' } }));
    }
  }
  return generic(c);
}

function generic(c: Ctx): Described {
  const r = c.ov.record;
  return page(c, 'sida', SITE, `AI-utrullningen i världen, kvantitativt och neutralt. ${c.ov.headline.sentence}`, spec(c, { kicker: recordText(r), title: c.ov.headline.sentence, subtitle: c.ov.headline.change_sentence ?? '', status: statusOf(r), graphic: overviewStripes(c) }));
}

/** Every share image the build writes (path below og/, without extension), with its route. */
export async function ogRoutes(b: Bundle): Promise<{ og: string; ref: RouteRef | null }[]> {
  const [ov, idx] = await Promise.all([b.overview(), b.seriesIndex()]);
  const ls = ((await b.flow()) as unknown as { leads: { code: string }[] }).leads;
  const out: { og: string; ref: RouteRef | null }[] = [
    { og: 'start', ref: { routeId: '/', params: {} } },
    { og: 'flode', ref: { routeId: '/flode', params: {} } },
    ...ls.map((l) => ({ og: `flode/${l.code}`, ref: { routeId: '/flode/[led]', params: { led: l.code } } })),
    ...ov.branches.map((x) => ({ og: `gren/${x.code}`, ref: { routeId: '/gren/[id]', params: { id: x.code } } })),
    ...idx.series.map((s) => ({ og: `serie/${s.key}`, ref: { routeId: '/serie/[key]', params: { key: s.key } } })),
    { og: 'prognoser', ref: { routeId: '/prognoser', params: {} } },
    { og: 'avstamningar', ref: { routeId: '/avstamningar', params: {} } },
    { og: 'regim', ref: { routeId: '/regim', params: {} } },
    { og: 'metod', ref: { routeId: '/metod', params: {} } },
    { og: 'sok', ref: { routeId: '/sok', params: {} } },
    { og: 'katalog', ref: { routeId: '/_katalog', params: {} } },
    { og: 'sida', ref: null }
  ];
  for (const mo of ((await b.storyIndex()) as unknown as { months: { month: string }[] }).months)
    out.push({ og: `manad/${mo.month}`, ref: { routeId: '/manad/[manad]', params: { manad: mo.month } } });
  for (const cal of ov.calendar) {
    out.push({ og: `prognoser/${cal.id}`, ref: { routeId: '/prognoser/[id]/[[slug]]', params: { id: cal.id } } });
    if (cal.id === 'd2') continue;
    for (const f of (await b.nowcast(cal.id)).forecasts ?? [])
      if (f.period) out.push({ og: `prognoser/${cal.id}/${slugOf(f)}`, ref: { routeId: '/prognoser/[id]/[[slug]]', params: { id: cal.id, slug: slugOf(f) } } });
  }
  return out;
}

/** The share image spec for an og path (null = unknown path). */
export async function ogFor(b: Bundle, og: string): Promise<OgSpec | null> {
  const hit = (await ogRoutes(b)).find((x) => x.og === og);
  if (!hit) return null;
  if (!hit.ref) {
    const [m, ov] = await Promise.all([b.manifest(), b.overview()]);
    return generic({ b, m, ov }).og;
  }
  return (await describe(b, hit.ref)).og;
}

/** The site's public address (og:url, og:image and the citation need absolute URLs). SITE_URL wins; otherwise
 *  GitHub Pages for the manifest's repo: https://<owner>.github.io/<repo> plus the base path. */
export function publicBase(m: Manifest, base: string): string {
  const env = process.env.SITE_URL?.replace(/\/+$/, '');
  if (env) return env;
  const gh = /github\.com\/([^/]+)\/([^/#?]+?)(?:\.git)?\/?$/.exec(String(m.repo ?? ''));
  if (!gh) return `https://example.invalid${base}`;
  const repo = `/${gh[2]}`;
  return `https://${gh[1].toLowerCase()}.github.io${base.startsWith(repo) ? base : repo + base}`;
}
