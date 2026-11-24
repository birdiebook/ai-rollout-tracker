// Swedish number and date formatting (section 4.5): space as thousands separator, comma as decimal sign, a real
// minus sign (U+2212). Use these for every number on the site so that the tables and the charts agree.

export const MINUS = '−';
const nf = new Map<number, Intl.NumberFormat>();
function formatter(d: number) {
  let f = nf.get(d);
  if (!f) {
    f = new Intl.NumberFormat('sv-SE', { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: true });
    nf.set(d, f);
  }
  return f;
}

const missing = (x: number | null | undefined): x is null | undefined =>
  x === null || x === undefined || Number.isNaN(x);

/** 12345.6 -> "12 345,6" (no-break space). Negative numbers get a real minus. Missing -> "–". */
export function fmt(x: number | null | undefined, digits = 0): string {
  if (missing(x)) return '–';
  const s = formatter(digits).format(Math.abs(x));
  const zero = Number(Math.abs(x).toFixed(digits)) === 0;
  return x < 0 && !zero ? MINUS + s : s;
}

/** Always signed: +4,8 / −4,4 / ±0,0. */
export function signed(x: number | null | undefined, digits = 1): string {
  if (missing(x)) return '–';
  const zero = Number(Math.abs(x).toFixed(digits)) === 0;
  const sign = zero ? '±' : x > 0 ? '+' : MINUS;
  return sign + formatter(digits).format(Math.abs(x));
}

export function pct(x: number | null | undefined, digits = 0): string {
  return missing(x) ? '–' : `${fmt(x * 100, digits)} %`;
}

const MONTHS = ['jan', 'feb', 'mar', 'apr', 'maj', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec'];
const MONTHS_LONG = [
  'januari', 'februari', 'mars', 'april', 'maj', 'juni',
  'juli', 'augusti', 'september', 'oktober', 'november', 'december'
];

/** "2026-11" -> "nov 2026" (or "november 2026"). Quarters "2026Q3" -> "kv. 3 2026". */
export function periodLabel(period: string, long = false): string {
  const q = /^(\d{4})Q([1-4])$/.exec(period);
  if (q) return `kv. ${q[2]} ${q[1]}`;
  const m = /^(\d{4})-(\d{2})/.exec(period);
  if (!m) return period;
  return `${(long ? MONTHS_LONG : MONTHS)[Number(m[2]) - 1]} ${m[1]}`;
}

/** "2026-11-30" -> "30 nov 2026". */
export function dateLabel(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return iso;
  return `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]} ${m[1]}`;
}

/** Month ordinal helpers ("YYYY-MM" <-> integer), for monthly x scales. */
export const monthOrdinal = (ym: string) => {
  const [y, m] = ym.split('-').map(Number);
  return y * 12 + (m - 1);
};
export const ordinalMonth = (o: number) => `${Math.floor(o / 12)}-${String((o % 12) + 1).padStart(2, '0')}`;
