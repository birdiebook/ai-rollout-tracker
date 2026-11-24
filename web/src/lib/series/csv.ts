// CSV downloads made from the series JSON (P6: every chart can be downloaded, with source and licence in the file).
// Plain RFC 4180 CSV with "#" comment lines on top (source, licence, attribution, as_of, permalink). Numbers are
// written with a decimal point and no rounding beyond the bundle's, so the file is machine-readable; the page
// shows the Swedish formatting.
import type { Levels, SeriesDoc, Versions } from './types';

export function csvCell(x: string | number | null | undefined): string {
  if (x === null || x === undefined || (typeof x === 'number' && !Number.isFinite(x))) return '';
  const s = String(x);
  return /[",\r\n#]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

const line = (cells: (string | number | null | undefined)[]) => cells.map(csvCell).join(',');

export function csvHeader(s: Pick<SeriesDoc, 'key' | 'label' | 'unit' | 'source' | 'license'>, extra: [string, string][] = []): string[] {
  const meta: [string, string][] = [
    ['serie', s.key],
    ['etikett', s.label],
    ['enhet', s.unit ?? ''],
    ['källa', s.source],
    ['licens', s.license.text || s.license.short],
    ['attribution', s.license.attribution],
    ...extra
  ];
  return meta.map(([k, v]) => `# ${k}: ${v.replace(/[\r\n]+/g, ' ')}`);
}

/** Levels as known on the bundle's build day: period,value. */
export function levelsCsv(s: Pick<SeriesDoc, 'key' | 'label' | 'unit' | 'source' | 'license'>, levels: Levels | null, permalink?: string): string {
  const head = csvHeader(s, [['as_of', levels?.as_of ?? ''], ...(permalink ? ([['permalänk', permalink]] as [string, string][]) : [])]);
  const rows = (levels?.periods ?? []).map((p, i) => line([p, levels?.values[i] ?? null]));
  return [...head, line(['period', 'value']), ...rows].join('\r\n') + '\r\n';
}

/** Every version (long form): period,known_from,value, in the contract's order (date, period). */
export function versionsCsv(s: Pick<SeriesDoc, 'key' | 'label' | 'unit' | 'source' | 'license'>, v: Versions | null, permalink?: string): string {
  const extra: [string, string][] = [
    ['kodning', 'versions-v1; known_from = första dag värdet var känt'],
    ['frekvens', v ? (v.native_freq !== v.freq ? `${v.freq} (${v.aggregation} av ${v.native_freq})` : v.freq) : '']
  ];
  if (v?.collapsed_before) extra.push(['hopslaget_före', v.collapsed_before]);
  if (permalink) extra.push(['permalänk', permalink]);
  const rows: string[] = [];
  if (v) for (let i = 0; i < v.p.length; i++) rows.push(line([v.periods[v.p[i]], v.dates[v.d[i]], v.v[i]]));
  return [...csvHeader(s, extra), line(['period', 'known_from', 'value']), ...rows].join('\r\n') + '\r\n';
}
