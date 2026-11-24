// The series page's view state in the URL hash (P11: every view can be shared and cited), e.g.
//   /next/serie/us_ip_semis_m/#fonster=5&skala=log&rev=1&as_of=2023-06-30
// Hash, not query: the pages are prerendered static files, and the hash never reaches the server. Defaults are left
// out so that the plain URL is the default view. `as_of` is the hook for W9 (time travel): it opens the revision
// view at that date. Unknown keys are kept, so that W9/W12 can add their own without this module dropping them.
import { WINDOWS, type Window } from './period';

export interface ViewState {
  fonster: Window;
  skala: 'lin' | 'log';
  /** revision view open (loads the series' versions at run time) */
  rev: boolean;
  /** time-travel date "YYYY-MM-DD" (revision view), null = today */
  as_of: string | null;
  /** other keys in the hash, kept as they were */
  extra: [string, string][];
}

export const DEFAULT_STATE: ViewState = { fonster: 'alla', skala: 'lin', rev: false, as_of: null, extra: [] };

const isDay = (s: string) => /^\d{4}-\d{2}-\d{2}$/.test(s) && !Number.isNaN(Date.parse(s));

/** Parse a hash ("#a=1&b=2" or "a=1&b=2"). Invalid values fall back to the default (a stale link still opens). */
export function parseState(hash: string, defaults: Partial<ViewState> = {}): ViewState {
  const st: ViewState = { ...DEFAULT_STATE, ...defaults, extra: [] };
  const params = new URLSearchParams(hash.replace(/^#/, ''));
  for (const [k, v] of params) {
    if (k === 'fonster') {
      if ((WINDOWS as readonly string[]).includes(v)) st.fonster = v as Window;
    } else if (k === 'skala') {
      if (v === 'lin' || v === 'log') st.skala = v;
    } else if (k === 'rev') st.rev = v === '1';
    else if (k === 'as_of') {
      if (isDay(v)) {
        st.as_of = v;
        st.rev = true;
      }
    } else st.extra.push([k, v]);
  }
  return st;
}

/** The hash for a state ("" for the defaults), keys in a fixed order so that equal views give equal URLs. */
export function serializeState(st: ViewState, defaults: Partial<ViewState> = {}): string {
  const d = { ...DEFAULT_STATE, ...defaults };
  const params = new URLSearchParams();
  if (st.fonster !== d.fonster) params.set('fonster', st.fonster);
  if (st.skala !== d.skala) params.set('skala', st.skala);
  if (st.as_of) params.set('as_of', st.as_of);
  else if (st.rev) params.set('rev', '1');
  for (const [k, v] of st.extra) params.append(k, v);
  const s = params.toString();
  return s ? `#${s}` : '';
}
