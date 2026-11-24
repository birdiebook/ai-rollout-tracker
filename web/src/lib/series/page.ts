// What the prerendered series page inlines (load() data), built at prerender time from series/<key>.json.
// The versions themselves are NOT inlined (datakontrakt section 8: series documents with versions are fetched at
// run time, only when the revision view or time travel is used). The page gets a summary instead: counts, and the
// first and latest version per period, so that it can show without any fetch that (and how much) values changed.
import type { SeriesIndexEntry } from '$lib/data';
import { revisions } from './versions';
import type { SeriesDoc, SeriesFields, Versions } from './types';

export interface VersionsSummary {
  freq: Versions['freq'];
  native_freq: Versions['native_freq'];
  aggregation: Versions['aggregation'];
  n_versions: number;
  n_periods: number;
  n_dates: number;
  n_revised_periods: number;
  first_known: string;
  last_known: string;
  collapsed_before: string | null;
}

/** First and latest version per period, columnar (only for series with at least one revised period). */
export interface RevisionColumns {
  periods: string[];
  first: number[];
  latest: number[];
  n: number[];
  first_known: string[];
}

export interface Sibling {
  key: string;
  label: string;
  freq: string | null;
  direction: 1 | 0 | -1 | null;
  core: boolean;
}

export interface SeriesPageData {
  series: SeriesFields & { versions: null };
  versions: VersionsSummary | null;
  revision: RevisionColumns | null;
  siblings: Sibling[];
  /** derived_from components with whether they have a page of their own */
  components: { key: string; label: string | null }[];
}

export function summarize(v: Versions | null): VersionsSummary | null {
  if (!v) return null;
  return {
    freq: v.freq,
    native_freq: v.native_freq,
    aggregation: v.aggregation,
    n_versions: v.n_versions,
    n_periods: v.periods.length,
    n_dates: v.dates.length,
    n_revised_periods: v.n_revised_periods,
    first_known: v.first_known,
    last_known: v.last_known,
    collapsed_before: v.collapsed_before
  };
}

export function revisionColumns(v: Versions | null): RevisionColumns | null {
  if (!v || v.n_revised_periods === 0) return null;
  const rs = revisions(v);
  return {
    periods: rs.map((r) => r.period),
    first: rs.map((r) => r.first),
    latest: rs.map((r) => r.latest),
    n: rs.map((r) => r.n),
    first_known: rs.map((r) => r.firstKnown)
  };
}

export function pageData(doc: SeriesDoc, index: SeriesIndexEntry[]): SeriesPageData {
  const { versions, ...rest } = doc;
  const byKey = new Map(index.map((e) => [e.key, e]));
  return {
    series: { ...rest, versions: null },
    versions: summarize(versions),
    revision: revisionColumns(versions),
    siblings: index
      .filter((e) => e.branch === doc.branch && e.key !== doc.key)
      .map((e) => ({ key: e.key, label: e.label, freq: e.freq, direction: e.direction ?? null, core: !!e.core }))
      .sort((a, b) => Number(b.core) - Number(a.core) || a.label.localeCompare(b.label, 'sv')),
    components: (doc.derived_from ?? []).map((k) => ({ key: k, label: byKey.get(k)?.label ?? null }))
  };
}
