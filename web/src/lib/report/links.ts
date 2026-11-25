// W14: hrefs of the quarterly report. Time-travel-capable views (start, branch, series) can open at the report day
// (as_of in the hash, the global key of $lib/timetravel); the page adds as_of only after mount (time travel needs JS).
import { resolve } from '$app/paths';

export const quarterHref = (q: string) => resolve('/kvartal/[kvartal]', { kvartal: q });
export const at = (path: string, day: string | null) => (day ? `${path}#as_of=${day}` : path);
export const branchHref = (code: string) => resolve('/gren/[id]', { id: code });
export const seriesHref = (key: string) => resolve('/serie/[key]', { key });
export const startHref = () => resolve('/');
export const nowcastHref = (id: string, slug?: string | null) =>
  slug ? resolve('/prognoser/[id]/[[slug]]', { id, slug }) : resolve('/prognoser/[id]/[[slug]]', { id });
