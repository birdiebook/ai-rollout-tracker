// Deep links (W12): the section of a page lives in the URL hash next to the view state, as one more key:
//   /next/serie/us_ip_semis_m/#fonster=5&skala=log&avsnitt=rev-h
// Same convention as the series page's permalink.ts (W7): hash, not query (static pages), and every key this module
// does not own is kept as it was, in its order, so the series state, W9's as_of and later keys survive.
// A plain anchor ("#rev-h", what a browser or another site may link to) is read as the section too.

export const SECTION_KEY = 'avsnitt';

const isDay = (s: string) => /^\d{4}-\d{2}-\d{2}$/.test(s) && !Number.isNaN(Date.parse(s));

/** Parse a hash into ordered [key, value] pairs ("#a=1&b" -> [["a","1"],["b",""]]). */
export function hashPairs(hash: string): [string, string][] {
  return [...new URLSearchParams(hash.replace(/^#/, ''))];
}

/** The section a hash points to: `avsnitt=<id>`, or a plain anchor without "=" ("#rev-h"). */
export function sectionOf(hash: string): string | null {
  const h = hash.replace(/^#/, '');
  if (!h) return null;
  if (!h.includes('=') && !h.includes('&')) {
    try {
      return decodeURIComponent(h) || null;
    } catch {
      return h;
    }
  }
  const v = new URLSearchParams(h).get(SECTION_KEY);
  return v || null;
}

/** The hash with the section set (or removed with null); all other keys kept in place. */
export function withSection(hash: string, id: string | null): string {
  const h = hash.replace(/^#/, '');
  // a plain anchor is replaced, not kept as a key without value
  const pairs = h && !h.includes('=') && !h.includes('&') ? [] : hashPairs(h);
  const params = new URLSearchParams();
  let set = false;
  for (const [k, v] of pairs) {
    if (k === SECTION_KEY) {
      if (id && !set) params.append(k, id);
      set = true;
    } else params.append(k, v);
  }
  if (id && !set) params.append(SECTION_KEY, id);
  const s = params.toString();
  return s ? `#${s}` : '';
}

/** The time-travel date in the hash (`as_of=YYYY-MM-DD`, W7/W9), if valid. */
export function asOfOf(hash: string): string | null {
  const h = hash.replace(/^#/, '');
  if (!h.includes('=')) return null;
  const v = new URLSearchParams(h).get('as_of');
  return v && isDay(v) ? v : null;
}

/** A stable anchor id from a heading text, for headings the page left without one. Years, counts in parentheses
 *  and month names are dropped so that "Läget oktober 2026" stays "laget" next month; codes such as L1 stay. */
const MONTH_WORDS = /\b(januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december|jan|feb|mar|apr|jun|jul|aug|sep|okt|nov|dec|kv)\b/g;
export function slugify(text: string): string {
  return text
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .toLowerCase()
    .replace(/\([^)]*\)/g, ' ')
    .replace(/\bkv\.?\s*\d\b/g, ' ')
    .replace(/\b\d{4}(-\d{2})?\b/g, ' ')
    .replace(MONTH_WORDS, ' ')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48)
    .replace(/-+$/g, '');
}
