import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { fsBundle } from '$lib/server/bundle';
import { asOfOf, sectionOf, slugify, withSection } from './hash';
import { fold, highlight, prepare, search, suggestions, tokens, type SearchItem } from './search';
import { buildSearchIndex } from './searchindex.server';
import { describe as describePage, ogFor, ogRoutes, publicBase } from './describe.server';
import { esc, indexFill, ogSvg, textWidth, wrap, type OgSpec } from './og';
import { parseState, serializeState } from '$lib/series/permalink';

const FIX = resolve('../web-data-fixtures');
const b = fsBundle(FIX);

describe('search', () => {
  const items: SearchItem[] = [
    { t: 'gren', id: 'G6', l: 'G6 Utbud och halvledare', s: 'stabil · L6', h: '/next/gren/G6/' },
    { t: 'led', id: 'L6', l: 'L6 Halvledare och minne', s: 'G6 Utbud och halvledare', h: '/next/flode/L6/' },
    { t: 'serie', id: 'us_ip_semis_m', l: 'Industriproduktion, halvledare (USA)', s: 'G6 · månatlig · Federal Reserve G.17', h: '/next/serie/us_ip_semis_m/' },
    { t: 'serie', id: 'eia_elforbrukning', l: 'Elförbrukning i datacenter', s: 'G7 · årlig · EIA', h: '/next/serie/x/' },
    { t: 'prognos', id: 'n2', l: 'N2 TSMC:s månadsintäkt', s: 'huvudmodell B3', h: '/next/prognoser/n2/' },
    { t: 'prognos', id: 'n2/2026-09', l: 'N2 för september 2026', s: 'skarp', h: '/next/prognoser/n2/2026-09/' },
    { t: 'sida', id: 'metod', l: 'Metod', h: '/next/metod/' }
  ];
  const P = prepare(items);

  it('folds case and accents without changing the length', () => {
    expect(fold('Elförbrukning ÅÄÖ')).toBe('elforbrukning aao');
    expect(fold('Elförbrukning').length).toBe('Elförbrukning'.length);
    expect(tokens('  Halv·ledare,  USA ')).toEqual(['halv', 'ledare', 'usa']);
  });
  it('an exact code ranks first', () => {
    expect(search(P, 'g6')[0].item.id).toBe('G6');
    expect(search(P, 'L6')[0].item.id).toBe('L6');
    expect(search(P, 'n2')[0].item.id).toBe('n2');
    expect(search(P, 'us_ip_semis_m')[0].item.id).toBe('us_ip_semis_m');
  });
  it('matches without accents and requires every word', () => {
    expect(search(P, 'elforbrukning').map((h) => h.item.id)).toEqual(['eia_elforbrukning']);
    expect(search(P, 'halvledare usa').map((h) => h.item.id)).toEqual(['us_ip_semis_m']);
    expect(search(P, 'halvledare xyz')).toEqual([]);
    expect(search(P, '   ')).toEqual([]);
  });
  it('finds by source and subline, label matches first', () => {
    expect(search(P, 'federal').map((h) => h.item.id)).toEqual(['us_ip_semis_m']);
    const ids = search(P, 'halvledare').map((h) => h.item.id);
    expect(ids.slice(0, 2).sort()).toEqual(['G6', 'L6']);
    expect(ids).toContain('us_ip_semis_m');
  });
  it('suggestions leave out series and single forecast pages', () => {
    expect(suggestions(items).map((i) => i.id)).toEqual(['G6', 'L6', 'n2', 'metod']);
  });
  it('highlights matched parts using folded positions', () => {
    expect(highlight('Elförbrukning i datacenter', 'forb')).toEqual([
      { text: 'El', hit: false },
      { text: 'förb', hit: true },
      { text: 'rukning i datacenter', hit: false }
    ]);
  });
});

describe('deep links in the hash', () => {
  it('reads the section from avsnitt= or a plain anchor', () => {
    expect(sectionOf('#fonster=5&avsnitt=rev-h')).toBe('rev-h');
    expect(sectionOf('#rev-h')).toBe('rev-h');
    expect(sectionOf('#fonster=5')).toBeNull();
    expect(sectionOf('')).toBeNull();
  });
  it('sets the section and keeps every other key in place', () => {
    expect(withSection('#fonster=5&skala=log&x=1', 'rev-h')).toBe('#fonster=5&skala=log&x=1&avsnitt=rev-h');
    expect(withSection('#avsnitt=a&fonster=5', 'b')).toBe('#avsnitt=b&fonster=5');
    expect(withSection('#rev-h', 'level-title')).toBe('#avsnitt=level-title');
    expect(withSection('#fonster=5&avsnitt=a', null)).toBe('#fonster=5');
    expect(withSection('', 'a')).toBe('#avsnitt=a');
  });
  it("survives W7's permalink parse/serialize (unknown keys kept)", () => {
    const h = withSection('#fonster=5&as_of=2023-06-30', 'rev-h');
    const st = parseState(h);
    expect(st.fonster).toBe('5');
    expect(sectionOf(serializeState(st))).toBe('rev-h');
    expect(asOfOf(serializeState(st))).toBe('2023-06-30');
  });
  it('reads a valid as_of only', () => {
    expect(asOfOf('#as_of=2023-06-30')).toBe('2023-06-30');
    expect(asOfOf('#as_of=2023-13-45x')).toBeNull();
    expect(asOfOf('#as_of')).toBeNull();
  });
  it('slugs drop dates so anchors stay stable month to month', () => {
    expect(slugify('Läget oktober 2026')).toBe('laget');
    expect(slugify('Läget november 2026')).toBe('laget');
    expect(slugify('Inhållna serier (12)')).toBe('inhallna-serier');
    expect(slugify('L1 Förmåga och kostnad')).toBe('l1-formaga-och-kostnad');
    expect(slugify('Facit per kv. 3 2026')).toBe('facit-per');
  });
});

describe('share image SVG', () => {
  const spec: OgSpec = {
    kicker: 'Serie · G6',
    title: 'A & B <test> "quoted"',
    subtitle: 'x',
    footer: 'Version per 24 nov 2026',
    credit: 'Källa: X',
    status: 'recon',
    testdata: true,
    graphic: { kind: 'line', values: [1, 2, null, 3], first: 'jan 2020', last: 'okt 2026', lastLabel: '3' }
  };
  it('escapes text and is a standalone 1200x630 SVG without external references', () => {
    const svg = ogSvg(spec);
    expect(svg.startsWith('<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630"')).toBe(true);
    expect(svg).toContain('A &amp; B &lt;test&gt; &quot;quoted&quot;');
    expect(svg).not.toMatch(/<image|href=|url\(|@import/);
    expect(svg).toContain('Testdata');
    expect(svg).toContain('rekonstruerad historik');
    expect(esc('<&>')).toBe('&lt;&amp;&gt;');
  });
  it('wraps and truncates long titles inside the width', () => {
    const lines = wrap('ett två tre fyra fem sex sju åtta nio tio elva tolv tretton fjorton femton sexton', 50, 400, 2, true);
    expect(lines).toHaveLength(2);
    expect(lines[1].endsWith('…')).toBe(true);
    for (const l of lines) expect(textWidth(l, 50, true)).toBeLessThanOrEqual(400);
    expect(wrap('kort', 50, 400, 2)).toEqual(['kort']);
  });
  it('index colours follow the diverging scale (orange low, blue high, null none)', () => {
    expect(indexFill(null)).toBeNull();
    const [lo, mid, hi] = [indexFill(0), indexFill(0.5), indexFill(1)] as string[];
    expect(mid).toBe('#f0efec');
    expect(hi).toBe('#2a78d6');
    expect(lo).toBe('#d9661f');
  });
});

describe('page descriptions from the fixtures', () => {
  it('every route has a share image that renders', async () => {
    const routes = await ogRoutes(b);
    expect(new Set(routes.map((r) => r.og)).size).toBe(routes.length);
    const idx = await b.seriesIndex();
    expect(routes.filter((r) => r.og.startsWith('serie/'))).toHaveLength(idx.series.length);
    for (const r of routes) {
      const s = await ogFor(b, r.og);
      expect(s, r.og).not.toBeNull();
      const svg = ogSvg(s as OgSpec);
      expect(svg.length).toBeLessThan(40 * 1024);
      expect(svg).not.toContain('NaN');
      expect(svg).not.toContain('undefined');
    }
    expect(await ogFor(b, 'nope')).toBeNull();
  });
  it('titles and descriptions come from data', async () => {
    const ov = await b.overview();
    const start = (await describePage(b, { routeId: '/', params: {} })).meta;
    expect(start.description).toContain(ov.headline.sentence);
    expect(start.ownDescription).toBe(true);
    const g6 = (await describePage(b, { routeId: '/gren/[id]', params: { id: 'G6' } })).meta;
    expect(g6.title).toMatch(/^G6 .+: (accelererar|stabil|bromsar in|för få serier)/);
    expect(g6.og).toBe('gren/G6');
    expect(g6.ownDescription).toBe(false);
    const s = (await describePage(b, { routeId: '/serie/[key]', params: { key: 'us_ip_semis_m' } })).meta;
    expect(s.cite.what).toMatch(/^serie .+ \(us_ip_semis_m; källa: .+\)$/);
    expect(s.cite.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(s.cite.commit).toBeNull(); // fixtures: git_sha "fixture"
    const unknown = (await describePage(b, { routeId: '/nagot-nytt', params: {} })).meta;
    expect(unknown.og).toBe('sida');
  });
  it('RW1-X: every route has a timeless citation name, without the month, state or value of today', async () => {
    const months = /\b(januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december) \d{4}\b/;
    const states = /accelererar|stabil|bromsar in|för få serier/;
    for (const r of await ogRoutes(b)) {
      const ref = r.ref ?? { routeId: '/nagot-nytt', params: {} };
      const { cite } = (await describePage(b, ref)).meta;
      expect(cite.timeless, r.og).toBeTruthy();
      expect(cite.timeless, r.og).not.toMatch(months);
      expect(cite.timeless, r.og).not.toMatch(states);
      if (!r.og.startsWith('serie/')) expect(cite.timeless, r.og).not.toMatch(/\d{4}-\d{2}-\d{2}/); // a series label is the catalog's name
    }
    const start = (await describePage(b, { routeId: '/', params: {} })).meta.cite;
    expect(start.what).toMatch(months); // today's title names the record; the timeless name does not
    expect(start.timeless).toBe('startsidan, läget');
    expect((await describePage(b, { routeId: '/gren/[id]', params: { id: 'G6' } })).meta.cite.timeless).toMatch(/^gren G6 \S/);
  });
  it('the public base follows GitHub Pages for the repo, SITE_URL wins', () => {
    const m = { repo: 'https://github.com/Owner/ai-rollout-tracker' };
    expect(publicBase(m, '/next')).toBe('https://owner.github.io/ai-rollout-tracker/next');
    expect(publicBase(m, '/ai-rollout-tracker/next')).toBe('https://owner.github.io/ai-rollout-tracker/next');
    process.env.SITE_URL = 'https://example.org/x/';
    expect(publicBase(m, '/next')).toBe('https://example.org/x');
    delete process.env.SITE_URL;
  });
});

describe('search index from the fixtures', () => {
  it('has every published series, nine branches, nine leads and the forecasts, and no withheld key', async () => {
    const ix = await buildSearchIndex(b);
    const idx = await b.seriesIndex();
    const by = (t: string) => ix.items.filter((i) => i.t === t);
    expect(by('serie').map((i) => i.id).sort()).toEqual(idx.series.map((s) => s.key).sort());
    expect(by('gren')).toHaveLength(9);
    expect(by('led')).toHaveLength(9);
    expect(by('prognos').length).toBeGreaterThanOrEqual(7);
    expect(by('sida').map((i) => i.id)).toEqual(expect.arrayContaining(['flode', 'prognoser', 'avstamningar', 'regim', 'metod']));
    const withheld = JSON.parse(readFileSync(resolve(FIX, 'withheld.json'), 'utf-8')) as { withheld: { key: string }[] };
    const text = JSON.stringify(ix);
    for (const w of withheld.withheld) expect(text).not.toContain(w.key);
    for (const i of ix.items) expect(i.h.startsWith('/')).toBe(true);
  });
});
