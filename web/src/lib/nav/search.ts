// Search over the site (W12): series, branches, leads, forecasts and pages. The index is built at prerender time
// (src/routes/sok.json, searchindex.server.ts) and fetched only when the search opens. Matching runs in the
// browser on a few hundred entries, so a plain scan with a small scoring rule is enough and has no dependencies.
//
// Matching is accent- and case-insensitive ("elforbrukning" finds "elförbrukning"), every word of the query must
// match somewhere in the entry, and an exact code (G6, L3, N2, a series key) ranks first.

export type SearchKind = 'led' | 'gren' | 'prognos' | 'sida' | 'serie';

/** One entry, short field names: the index is shipped as JSON. */
export interface SearchItem {
  /** kind */
  t: SearchKind;
  /** code or key: L6, G6, n2, us_ip_semis_m, or a page id */
  id: string;
  /** label shown as the option's title */
  l: string;
  /** subline shown under the title (branch, frequency, source …) */
  s?: string;
  /** href, base path included */
  h: string;
  /** extra words that match but are not shown */
  k?: string;
}

export interface SearchIndex {
  v: 1;
  as_of: string;
  items: SearchItem[];
}

export const KIND_LABEL: Record<SearchKind, string> = {
  led: 'Led',
  gren: 'Gren',
  prognos: 'Prognos',
  sida: 'Sida',
  serie: 'Serie'
};

const KIND_ORDER: Record<SearchKind, number> = { led: 0, gren: 1, prognos: 2, sida: 3, serie: 4 };
const KIND_BOOST: Record<SearchKind, number> = { led: 3, gren: 3, prognos: 2, sida: 2, serie: 0 };

/** Fold one character: lower case without diacritics. Keeps the string length, so match positions map back. */
function foldChar(c: string): string {
  const f = c.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
  return f.length === 1 ? f : c.toLowerCase().slice(0, 1) || c;
}

/** Lower case, accents removed, one output character per input character (UTF-16 unit). */
export function fold(s: string): string {
  let out = '';
  for (const c of s.normalize('NFC')) {
    const f = foldChar(c);
    // a character outside the BMP is two units: keep the length equal to the input's
    out += c.length === 2 ? f.padEnd(2, ' ').slice(0, 2) : f;
  }
  return out;
}

export function tokens(q: string): string[] {
  return fold(q)
    .split(/[\s,;/·]+/)
    .map((t) => t.trim())
    .filter(Boolean)
    .slice(0, 8);
}

interface Prepared {
  item: SearchItem;
  id: string;
  label: string;
  words: string[];
  rest: string;
}

export function prepare(items: SearchItem[]): Prepared[] {
  return items.map((item) => {
    const label = fold(item.l);
    return {
      item,
      id: fold(item.id),
      label,
      words: label.split(/[^\p{L}\p{N}]+/u).filter(Boolean),
      rest: fold(`${item.s ?? ''} ${item.k ?? ''}`)
    };
  });
}

function wordStart(hay: string, tok: string): boolean {
  let i = hay.indexOf(tok);
  while (i >= 0) {
    if (i === 0 || !/[\p{L}\p{N}]/u.test(hay[i - 1])) return true;
    i = hay.indexOf(tok, i + 1);
  }
  return false;
}

/** Score of one entry for the query tokens, or null when a token matches nowhere. */
export function score(p: Prepared, toks: string[]): number | null {
  let total = 0;
  for (const tok of toks) {
    let best = 0;
    if (p.id === tok) best = 100;
    else if (p.id.startsWith(tok)) best = 55;
    if (p.label === tok) best = Math.max(best, 90);
    else if (p.label.startsWith(tok)) best = Math.max(best, 50);
    else if (p.words.some((w) => w.startsWith(tok))) best = Math.max(best, 40);
    else if (p.label.includes(tok)) best = Math.max(best, 20);
    if (!best) {
      if (wordStart(p.rest, tok)) best = 12;
      else if (p.rest.includes(tok) || p.id.includes(tok)) best = 6;
    }
    if (!best) return null;
    total += best;
  }
  return total + KIND_BOOST[p.item.t];
}

export interface Hit {
  item: SearchItem;
  score: number;
}

/** Ranked hits for a query (all of them; the caller shows the first few). Empty query: no hits. */
export function search(prepared: Prepared[], query: string): Hit[] {
  const toks = tokens(query);
  if (!toks.length) return [];
  const hits: Hit[] = [];
  for (const p of prepared) {
    const s = score(p, toks);
    if (s !== null) hits.push({ item: p.item, score: s });
  }
  return hits.sort(
    (a, b) => b.score - a.score || KIND_ORDER[a.item.t] - KIND_ORDER[b.item.t] || a.item.l.length - b.item.l.length || a.item.l.localeCompare(b.item.l, 'sv')
  );
}

/** What the search shows before anything is typed: the chain, the branches, the forecasts and the pages. */
export function suggestions(items: SearchItem[]): SearchItem[] {
  return items.filter((i) => i.t !== 'serie' && !(i.t === 'prognos' && i.id.includes('/')));
}

export interface Segment {
  text: string;
  hit: boolean;
}

/** The label split into matched and unmatched parts (for <mark>), using folded positions. */
export function highlight(label: string, query: string): Segment[] {
  const toks = tokens(query).sort((a, b) => b.length - a.length);
  const nfc = label.normalize('NFC');
  const hay = fold(nfc);
  const on = new Array<boolean>(nfc.length).fill(false);
  for (const tok of toks) {
    let i = hay.indexOf(tok);
    while (i >= 0) {
      for (let j = i; j < i + tok.length; j++) on[j] = true;
      i = hay.indexOf(tok, i + tok.length);
    }
  }
  const out: Segment[] = [];
  for (let i = 0; i < nfc.length; i++) {
    const last = out[out.length - 1];
    if (last && last.hit === on[i]) last.text += nfc[i];
    else out.push({ text: nfc[i], hit: on[i] });
  }
  return out;
}
