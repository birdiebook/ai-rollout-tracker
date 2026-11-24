// Share images (W12, P11): one 1200x630 picture per page, drawn from the page's own data at build time. This module
// turns a spec into a standalone SVG (no fonts or images from anywhere: system sans, flat colours from the light
// palette). The prerender writes it to og/<page>.svg (src/routes/og/[...path]), and scripts/og-png.mjs rasterises
// it to og/<page>.png, which og:image points to (the large platforms do not show SVG previews).
//
// Same grammar as the site: colour means direction only (blue more pace, orange less, grey balance), series are
// drawn in neutral ink, reconstructed history is dashed (P9), test data says so on the picture.
import { palettes } from '$lib/design/tokens';
import { oklab } from '$lib/design/color';

export const OG_W = 1200;
export const OG_H = 630;

export type OgStatus = 'live' | 'recon' | 'backtest' | null;

export interface OgStripeRow {
  code: string;
  index: (number | null)[];
}

export type OgGraphic =
  | { kind: 'stripes'; months: string[]; kinds: (string | null)[]; rows: OgStripeRow[]; highlight?: string | null }
  | { kind: 'chain'; leads: { code: string; index: number | null; glyphs: string[] }[]; current?: string | null }
  | { kind: 'index'; months: string[]; kinds: (string | null)[]; index: (number | null)[]; lo: number; hi: number }
  | {
      kind: 'line';
      values: (number | null)[];
      first: string;
      last: string;
      lastLabel: string;
      /** forecast point with its 80 % interval, drawn after the line in the model colour */
      forecast?: { value: number; lo: number | null; hi: number | null; label: string } | null;
    }
  | { kind: 'none' };

export interface OgSpec {
  kicker: string;
  title: string;
  subtitle: string;
  footer: string;
  /** small print under the picture (licence attribution for series) */
  credit?: string;
  status: OgStatus;
  testdata: boolean;
  graphic: OgGraphic;
}

const P = palettes.light;

const fmtN = (x: number) => x.toFixed(2).replace('.', ',');

export function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/** Rough advance width of a character in em for a system sans (good enough to wrap and truncate). */
function charEm(c: string, bold: boolean): number {
  let w: number;
  if (' .,:;!|il\'’ijtfr()[]'.includes(c)) w = 0.3;
  else if ('mwMW—'.includes(c)) w = 0.86;
  else if (/[A-ZÅÄÖ]/.test(c)) w = 0.68;
  else if (/[0-9]/.test(c)) w = 0.56;
  else w = 0.53;
  // calibrated against Chromium's system-ui (2026-11), plus slack for wider fallback fonts (DejaVu Sans)
  return (bold ? w * 1.1 : w * 1.07) * 1.05;
}

export const textWidth = (s: string, size: number, bold = false) => [...s].reduce((a, c) => a + charEm(c, bold), 0) * size;

/** Greedy word wrap to at most `lines` lines of `width` px; the last line ends with "…" when text is cut. */
export function wrap(text: string, size: number, width: number, lines: number, bold = false): string[] {
  const words = text.replace(/\s+/g, ' ').trim().split(' ').filter(Boolean);
  const out: string[] = [];
  let cur = '';
  let i = 0;
  for (; i < words.length; i++) {
    const next = cur ? `${cur} ${words[i]}` : words[i];
    if (textWidth(next, size, bold) <= width || !cur) {
      cur = next;
      continue;
    }
    out.push(cur);
    cur = words[i];
    if (out.length === lines) break;
  }
  if (out.length < lines && cur) {
    out.push(cur);
    cur = '';
    i = words.length;
  }
  const cut = i < words.length || cur !== '';
  if (out.length) {
    let last = out[out.length - 1];
    while (textWidth(last + (cut ? ' …' : ''), size, bold) > width && last.includes(' ')) last = last.slice(0, last.lastIndexOf(' '));
    while (textWidth(last + (cut ? '…' : ''), size, bold) > width && last.length > 1) last = last.slice(0, -1);
    out[out.length - 1] = cut ? `${last.replace(/[\s,.;:–-]+$/, '')} …` : last;
  }
  return out;
}

// --- colour: the site's divergingFill (OKLab mix of mid and pole), computed here because the SVG stands alone

function linToHex(rgb: number[]): string {
  const enc = (c: number) => {
    const v = c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055;
    return Math.round(Math.max(0, Math.min(1, v)) * 255)
      .toString(16)
      .padStart(2, '0');
  };
  return '#' + rgb.map(enc).join('');
}

function oklabToHex([L, a, b]: number[]): string {
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  return linToHex([
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s
  ]);
}

/** Diffusion index in [0, 1] -> fill, like $lib/design divergingFill in the light palette. */
export function indexFill(x: number | null | undefined): string | null {
  if (x === null || x === undefined || Number.isNaN(x)) return null;
  const t = Math.max(-1, Math.min(1, (x - 0.5) * 2));
  const a = Math.abs(t) ** 0.85;
  const mid = oklab(P.mid);
  const pole = oklab(t >= 0 ? P.acc : P.brk);
  return oklabToHex(mid.map((c, i) => c + (pole[i] - c) * a));
}

const GLYPH_COLOR: Record<string, string> = { '▲': P.acc, '▼': P.brk, '●': P.stb, '○': P.muted };

// --- graphics, inside the box x0..x1, y0..y1

interface Box {
  x0: number;
  x1: number;
  y0: number;
  y1: number;
}

function stripes(g: Extract<OgGraphic, { kind: 'stripes' }>, b: Box): string {
  const n = g.months.length;
  if (!n || !g.rows.length) return '';
  const labelW = 46;
  const cw = (b.x1 - b.x0 - labelW) / n;
  const rh = Math.min(22, (b.y1 - b.y0 - 22) / g.rows.length);
  let s = '';
  g.rows.forEach((r, j) => {
    const y = b.y0 + j * rh;
    const hl = g.highlight && r.code === g.highlight;
    s += `<text x="${b.x0}" y="${(y + rh * 0.72).toFixed(1)}" font-size="15" font-weight="${hl ? 700 : 500}" fill="${hl ? P.ink : P.muted}">${esc(r.code)}</text>`;
    r.index.forEach((v, i) => {
      const f = indexFill(v);
      const x = b.x0 + labelW + i * cw;
      s += f
        ? `<rect x="${x.toFixed(1)}" y="${(y + 1).toFixed(1)}" width="${(cw + 0.4).toFixed(1)}" height="${(rh - 2).toFixed(1)}" fill="${f}"/>`
        : `<rect x="${(x + 0.5).toFixed(1)}" y="${(y + 1.5).toFixed(1)}" width="${(cw - 1).toFixed(1)}" height="${(rh - 3).toFixed(1)}" fill="none" stroke="${P.grid}"/>`;
    });
    if (hl) s += `<rect x="${b.x0 + labelW - 1}" y="${y}" width="${(cw * n + 2).toFixed(1)}" height="${rh}" fill="none" stroke="${P.ink}" stroke-width="2"/>`;
  });
  // the first live month: everything before it is reconstructed (P9)
  const firstLive = g.kinds.findIndex((k) => k === 'skarp');
  const yb = b.y0 + g.rows.length * rh;
  if (firstLive > 0) {
    const x = b.x0 + labelW + firstLive * cw;
    s += `<line x1="${x.toFixed(1)}" x2="${x.toFixed(1)}" y1="${b.y0 - 4}" y2="${yb + 4}" stroke="${P.ink}" stroke-width="2" stroke-dasharray="4 3"/>`;
    s += `<text x="${b.x0 + labelW}" y="${b.y0 - 12}" font-size="14" fill="${P.ink2}">Före den streckade linjen: rekonstruerad historik. Från ${esc(g.months[firstLive])}: skarpa ögonblicksbilder.</text>`;
  }
  s += `<text x="${b.x0 + labelW}" y="${yb + 20}" font-size="14" fill="${P.muted}">${esc(g.months[0])}</text>`;
  s += `<text x="${b.x1}" y="${yb + 20}" font-size="14" fill="${P.muted}" text-anchor="end">${esc(g.months[n - 1])}</text>`;
  return s;
}

function chain(g: Extract<OgGraphic, { kind: 'chain' }>, b: Box): string {
  const n = g.leads.length;
  if (!n) return '';
  const gap = 14;
  const w = (b.x1 - b.x0 - gap * (n - 1)) / n;
  const h = Math.min(130, b.y1 - b.y0);
  let s = '';
  g.leads.forEach((l, i) => {
    const x = b.x0 + i * (w + gap);
    const cur = g.current === l.code;
    const fill = indexFill(l.index) ?? P.surface;
    s += `<rect x="${x.toFixed(1)}" y="${b.y0}" width="${w.toFixed(1)}" height="${h}" rx="12" fill="${fill}" stroke="${cur ? P.ink : P.axis}" stroke-width="${cur ? 4 : 1.5}"/>`;
    s += `<text x="${(x + w / 2).toFixed(1)}" y="${b.y0 + 44}" font-size="26" font-weight="700" fill="${P.ink}" text-anchor="middle">${esc(l.code)}</text>`;
    const gl = l.glyphs.slice(0, 3);
    gl.forEach((c, k) => {
      const gx = x + w / 2 + (k - (gl.length - 1) / 2) * 30;
      // a surface disc behind the glyph keeps it legible on any fill
      s += `<circle cx="${gx.toFixed(1)}" cy="${b.y0 + 86}" r="14" fill="${P.surface}"/>`;
      s += `<text x="${gx.toFixed(1)}" y="${b.y0 + 94}" font-size="20" fill="${GLYPH_COLOR[c] ?? P.muted}" text-anchor="middle">${esc(c)}</text>`;
    });
    if (i < n - 1) s += `<path d="M${(x + w + 3).toFixed(1)} ${b.y0 + h / 2 - 6} l8 6 l-8 6 z" fill="${P.axis}"/>`;
  });
  return s;
}

function path(vals: (number | null)[], xOf: (i: number) => number, yOf: (v: number) => number): string {
  let d = '';
  let pen = false;
  vals.forEach((v, i) => {
    if (v === null || !Number.isFinite(v)) {
      pen = false;
      return;
    }
    d += `${pen ? 'L' : 'M'}${xOf(i).toFixed(1)} ${yOf(v).toFixed(1)}`;
    pen = true;
  });
  return d;
}

function indexChart(g: Extract<OgGraphic, { kind: 'index' }>, b: Box): string {
  const n = g.index.length;
  if (!n) return '';
  const top = b.y0;
  const h = b.y1 - b.y0 - 52;
  const xOf = (i: number) => b.x0 + (n === 1 ? 0.5 : i / (n - 1)) * (b.x1 - b.x0);
  const yOf = (v: number) => top + (1 - v) * h;
  let s = `<rect x="${b.x0}" y="${yOf(g.hi).toFixed(1)}" width="${b.x1 - b.x0}" height="${(yOf(g.lo) - yOf(g.hi)).toFixed(1)}" fill="${P.mid}"/>`;
  s += `<line x1="${b.x0}" x2="${b.x1}" y1="${yOf(0.5)}" y2="${yOf(0.5)}" stroke="${P.axis}"/>`;
  s += `<line x1="${b.x0}" x2="${b.x1}" y1="${top}" y2="${top}" stroke="${P.grid}"/><line x1="${b.x0}" x2="${b.x1}" y1="${top + h}" y2="${top + h}" stroke="${P.grid}"/>`;
  s += `<text x="${b.x0 + 6}" y="${top + 16}" font-size="14" fill="${P.muted}">1 alla serier ökar takten</text>`;
  s += `<text x="${b.x0 + 6}" y="${(yOf(g.lo) - 6).toFixed(1)}" font-size="14" fill="${P.muted}">stabilt läge ${fmtN(g.lo)}–${fmtN(g.hi)}</text>`;
  s += `<text x="${b.x0 + 6}" y="${top + h - 6}" font-size="14" fill="${P.muted}">0 alla minskar</text>`;
  const firstLive = g.kinds.findIndex((k) => k === 'skarp');
  const split = firstLive > 0 ? firstLive : n;
  const recon = g.index.map((v, i) => (i <= split ? v : null));
  const live = g.index.map((v, i) => (i >= split ? v : null));
  s += `<path d="${path(recon, xOf, yOf)}" fill="none" stroke="${P.ink}" stroke-width="3" stroke-dasharray="${split < n ? '7 5' : '0'}"/>`;
  if (split < n) s += `<path d="${path(live, xOf, yOf)}" fill="none" stroke="${P.ink}" stroke-width="3.5"/>`;
  const lastI = g.index.map((v, i) => (v === null ? -1 : i)).reduce((a, c) => Math.max(a, c), -1);
  if (lastI >= 0) {
    const v = g.index[lastI] as number;
    s += `<circle cx="${xOf(lastI).toFixed(1)}" cy="${yOf(v).toFixed(1)}" r="9" fill="${indexFill(v)}" stroke="${P.ink}" stroke-width="2.5"/>`;
  }
  // stripes under the line: the same months as colour
  const cw = (b.x1 - b.x0) / n;
  g.index.forEach((v, i) => {
    const f = indexFill(v);
    if (f) s += `<rect x="${(b.x0 + i * cw).toFixed(1)}" y="${top + h + 12}" width="${(cw + 0.4).toFixed(1)}" height="16" fill="${f}"/>`;
  });
  s += `<text x="${b.x0}" y="${b.y1}" font-size="14" fill="${P.muted}">${esc(g.months[0])}</text>`;
  s += `<text x="${b.x1}" y="${b.y1}" font-size="14" fill="${P.muted}" text-anchor="end">${esc(g.months[n - 1])}</text>`;
  return s;
}

function lineChart(g: Extract<OgGraphic, { kind: 'line' }>, b: Box): string {
  const vals = g.values;
  const fin = vals.filter((v): v is number => v !== null && Number.isFinite(v));
  if (fin.length < 2) return '';
  const f = g.forecast;
  const all = f ? [...fin, f.value, ...(f.lo !== null ? [f.lo] : []), ...(f.hi !== null ? [f.hi] : [])] : fin;
  let lo = Math.min(...all);
  let hi = Math.max(...all);
  if (hi === lo) {
    hi += 1;
    lo -= 1;
  }
  const pad = (hi - lo) * 0.08;
  lo -= pad;
  hi += pad;
  const labelW = 170;
  const x1 = b.x1 - labelW - (f ? 60 : 0);
  const n = vals.length;
  const h = b.y1 - b.y0 - 24;
  const xOf = (i: number) => b.x0 + (i / (n - 1)) * (x1 - b.x0);
  const yOf = (v: number) => b.y0 + (1 - (v - lo) / (hi - lo)) * h;
  let s = `<line x1="${b.x0}" x2="${x1}" y1="${b.y0 + h}" y2="${b.y0 + h}" stroke="${P.axis}"/>`;
  s += `<path d="${path(vals, xOf, yOf)}" fill="none" stroke="${P.ink}" stroke-width="3" stroke-linejoin="round"/>`;
  let li = n - 1;
  while (li > 0 && (vals[li] === null || !Number.isFinite(vals[li] as number))) li--;
  const lv = vals[li] as number;
  s += `<circle cx="${xOf(li).toFixed(1)}" cy="${yOf(lv).toFixed(1)}" r="7" fill="${P.ink}" stroke="${P.surface}" stroke-width="3"/>`;
  if (f) {
    const fx = x1 + 44;
    if (f.lo !== null && f.hi !== null)
      s += `<rect x="${fx - 9}" y="${yOf(f.hi).toFixed(1)}" width="18" height="${Math.max(2, yOf(f.lo) - yOf(f.hi)).toFixed(1)}" rx="4" fill="${P.model}" fill-opacity="0.3"/>`;
    s += `<line x1="${fx - 16}" x2="${fx + 16}" y1="${yOf(f.value).toFixed(1)}" y2="${yOf(f.value).toFixed(1)}" stroke="${P.model}" stroke-width="4"/>`;
    s += `<text x="${fx + 24}" y="${(yOf(f.value) + 8).toFixed(1)}" font-size="22" font-weight="650" fill="${P.ink}">${esc(f.label)}</text>`;
  } else {
    s += `<text x="${(xOf(li) + 16).toFixed(1)}" y="${(yOf(lv) + 8).toFixed(1)}" font-size="22" font-weight="650" fill="${P.ink}">${esc(g.lastLabel)}</text>`;
  }
  s += `<text x="${b.x0}" y="${b.y1}" font-size="14" fill="${P.muted}">${esc(g.first)}</text>`;
  s += `<text x="${x1}" y="${b.y1}" font-size="14" fill="${P.muted}" text-anchor="end">${esc(g.last)}</text>`;
  return s;
}

const STATUS_TEXT: Record<Exclude<OgStatus, null>, string> = {
  live: 'skarp ögonblicksbild',
  recon: 'rekonstruerad historik',
  backtest: 'backtest, inte skarp'
};

/** The share image as a standalone SVG document. */
export function ogSvg(spec: OgSpec): string {
  const M = 60;
  const hasG = spec.graphic.kind !== 'none';
  const titleSize = hasG ? 50 : 60;
  const title = wrap(spec.title, titleSize, OG_W - 2 * M, 2, true);
  const subSize = 26;
  const ty0 = 150;
  const titleBottom = ty0 + (title.length - 1) * titleSize * 1.12;
  const sub = wrap(spec.subtitle, subSize, OG_W - 2 * M, hasG ? (title.length > 1 ? 1 : 2) : 4);
  const gr0 = spec.graphic;
  const subTop = titleBottom + 48;
  const subBottom = subTop + (sub.length - 1) * subSize * 1.3;
  const box: Box = { x0: M, x1: OG_W - M, y0: Math.max(subBottom + (gr0.kind === 'stripes' ? 60 : 50), gr0.kind === 'stripes' ? 340 : gr0.kind === 'chain' ? 330 : 280), y1: spec.credit ? 532 : 548 };

  let g = '';
  const gr = spec.graphic;
  if (gr.kind === 'stripes') g = stripes(gr, box);
  else if (gr.kind === 'chain') g = chain(gr, { ...box, y0: box.y0 + Math.max(0, (box.y1 - box.y0 - 130) / 2) });
  else if (gr.kind === 'index') g = indexChart(gr, box);
  else if (gr.kind === 'line') g = lineChart(gr, box);

  const kicker = wrap(spec.kicker, 22, spec.testdata ? 520 : 640, 1)[0] ?? '';
  const status = spec.status ? STATUS_TEXT[spec.status] : '';
  const statusW = status ? textWidth(status, 18) + 28 : 0;
  const footer = wrap(spec.footer, 18, OG_W - 2 * M - statusW - 24, 1)[0] ?? '';
  const credit = spec.credit ? (wrap(spec.credit, 15, OG_W - 2 * M, 1)[0] ?? '') : '';

  const parts = [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${OG_W}" height="${OG_H}" viewBox="0 0 ${OG_W} ${OG_H}" font-family="system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif">`,
    `<rect width="${OG_W}" height="${OG_H}" fill="${P.page}"/>`,
    `<rect x="0" y="0" width="${OG_W}" height="8" fill="${P.ink}"/>`,
    `<text x="${M}" y="70" font-size="26" font-weight="700" fill="${P.ink}" letter-spacing="-0.3">AI-utrullningen</text>`,
    `<text x="${OG_W - M}" y="70" font-size="22" fill="${P.ink2}" text-anchor="end">${esc(kicker)}</text>`,
    ...title.map((t, i) => `<text x="${M}" y="${(ty0 + i * titleSize * 1.12).toFixed(0)}" font-size="${titleSize}" font-weight="700" fill="${P.ink}" letter-spacing="-1">${esc(t)}</text>`),
    ...sub.map((t, i) => `<text x="${M}" y="${(subTop + i * subSize * 1.3).toFixed(0)}" font-size="${subSize}" fill="${P.ink2}">${esc(t)}</text>`),
    g,
    `<line x1="${M}" x2="${OG_W - M}" y1="574" y2="574" stroke="${P.grid}" stroke-width="2"/>`,
    `<text x="${M}" y="607" font-size="18" fill="${P.ink2}">${esc(footer)}</text>`
  ];
  if (status) {
    const x = OG_W - M - statusW;
    parts.push(
      `<rect x="${x.toFixed(1)}" y="586" width="${statusW.toFixed(1)}" height="30" rx="15" fill="none" stroke="${P.ink2}" stroke-width="1.5"${spec.status === 'live' ? '' : ' stroke-dasharray="5 4"'}/>`,
      `<text x="${(x + statusW / 2).toFixed(1)}" y="607" font-size="18" fill="${P.ink2}" text-anchor="middle">${esc(status)}</text>`
    );
  }
  if (credit) parts.push(`<text x="${M}" y="560" font-size="15" fill="${P.muted}">${esc(credit)}</text>`);
  if (spec.testdata) {
    parts.push(
      `<g transform="translate(${M + 232} 44)"><rect width="118" height="34" rx="8" fill="${P.surface}" stroke="${P.ink}" stroke-width="2" stroke-dasharray="6 4"/>`,
      `<text x="59" y="24" font-size="19" font-weight="700" fill="${P.ink}" text-anchor="middle">Testdata</text></g>`
    );
  }
  parts.push('</svg>');
  return parts.join('');
}
