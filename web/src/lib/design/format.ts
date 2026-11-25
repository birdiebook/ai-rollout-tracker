// Swedish number and date formatting (section 4.5): space as thousands separator, comma as decimal sign, a real
// minus sign (U+2212). Use these for every number on the site so that the tables and the charts agree.

export const MINUS = '−';
const nf = new Map<number, Intl.NumberFormat>();
function intl(d: number) {
  let f = nf.get(d);
  if (!f) {
    f = new Intl.NumberFormat('sv-SE', { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: true });
    nf.set(d, f);
  }
  return f;
}
const NBSP = '\u00a0';
const group = (i: string) => {
  if (i.length <= 3) return i;
  let n = i.length % 3 || 3;
  let o = i.slice(0, n);
  for (; n < i.length; n += 3) o += NBSP + i.slice(n, n + 3);
  return o;
};
/** sv-SE formatting of a non-negative number with `d` decimals, without Intl (R-W2 P1: the first Intl.NumberFormat
 *  costs ~60 ms at 4x CPU during hydration). Same output as Intl.NumberFormat('sv-SE'): the shortest decimal form of
 *  the number rounded half away from zero (format.test.ts compares the two). Exponent forms fall back to Intl. */
function formatAbs(a: number, d: number): string {
  const s = String(a);
  if (s.includes('e')) return intl(d).format(a);
  const k = s.indexOf('.');
  let i = k < 0 ? s : s.slice(0, k);
  let f = k < 0 ? '' : s.slice(k + 1);
  if (f.length > d) {
    const up = f.charCodeAt(d) >= 53; // '5'
    f = f.slice(0, d);
    if (up) {
      const digits = (i + f).split('');
      let j = digits.length - 1;
      while (j >= 0 && digits[j] === '9') digits[j--] = '0';
      if (j < 0) digits.unshift('1');
      else digits[j] = String.fromCharCode(digits[j].charCodeAt(0) + 1);
      const all = digits.join('');
      i = all.slice(0, all.length - d) || '0';
      f = all.slice(all.length - d);
    }
  } else f = f.padEnd(d, '0');
  return d ? `${group(i)},${f}` : group(i);
}
const formatter = (d: number) => ({ format: (a: number) => formatAbs(a, d) });
/** Intl's own output, for the test that the fast path agrees with it. */
export const intlFormat = (a: number, d: number) => intl(d).format(a);

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
