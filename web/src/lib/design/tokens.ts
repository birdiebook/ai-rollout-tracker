// Design tokens (W2), from docs/steg3/hemsida_vision.md section 4.4–4.6 and the prototypes in prototypes/hemsida/.
// One source of truth: the CSS custom properties are generated from these objects (tokensCss) and inlined in the
// page head by the root layout, so the tests that validate contrast read the same values the browser paints.
//
// Colour means direction only: blue = more pace, orange = less pace, grey = balance. Never green/red. Every
// direction colour has a glyph and a word next to it (state.ts). Dark mode is its own selected palette.

export type Theme = 'light' | 'dark';

export interface Palette {
  /** page background */
  page: string;
  /** cards, panels and chart surface */
  surface: string;
  /** primary text */
  ink: string;
  /** secondary text */
  ink2: string;
  /** muted text: axis labels, notes */
  muted: string;
  /** gridlines (recessive) */
  grid: string;
  /** axis lines, dashed status borders */
  axis: string;
  /** hairline borders on panels */
  ring: string;
  /** more pace (accelererar), index towards 1 */
  acc: string;
  /** less pace (bromsar in), index towards 0 */
  brk: string;
  /** balance (stabil) */
  stb: string;
  /** diverging midpoint, index 0.5 */
  mid: string;
  /** a model's forecast and its intervals */
  model: string;
  /** naive baseline B0/B1 */
  base: string;
  /** focus ring */
  focus: string;
}

export const palettes: Record<Theme, Palette> = {
  light: {
    page: '#f9f9f7',
    surface: '#fcfcfb',
    ink: '#0b0b0b',
    ink2: '#52514e',
    muted: '#6a6862',
    grid: '#e1e0d9',
    axis: '#c3c2b7',
    ring: 'rgba(11, 11, 11, 0.10)',
    acc: '#2a78d6',
    brk: '#c25a00', // R-W3: balanced against blue (distance to the mid grey 39.6 vs 41.2), was #d9661f
    stb: '#8a8880',
    mid: '#f0efec',
    model: '#6250d6',
    base: '#5e5d58', // R-W3: not the stable grey (was #898781, dE 0.4 to stb)
    focus: '#0b0b0b'
  },
  dark: {
    page: '#0d0d0d',
    surface: '#1a1a19',
    ink: '#f0efec',
    ink2: '#c3c2b7',
    muted: '#9a988f',
    grid: '#2c2c2a',
    axis: '#4a4a46',
    ring: 'rgba(255, 255, 255, 0.10)',
    acc: '#3987e5',
    brk: '#d46600', // R-W3: hue 51 deg instead of 40 deg (read as red), was #d95926
    stb: '#8f8d85',
    mid: '#383835',
    model: '#9085e9',
    base: '#bdbbb2', // R-W3: not the stable grey (was #898781)
    focus: '#f0efec'
  }
};

/** Interval bands 50/80/95: one colour (model) with falling opacity, never three colours (section 4.2). */
export const bandOpacity: Record<'50' | '80' | '95', Record<Theme, number>> = {
  '50': { light: 0.42, dark: 0.45 },
  '80': { light: 0.22, dark: 0.24 },
  '95': { light: 0.1, dark: 0.11 }
};

/** Typography (section 4.5): system stack only, nothing from other hosts. Sizes in px. */
export const typography = {
  font: 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  mono: 'ui-monospace, "SF Mono", Menlo, Consolas, monospace',
  /** headline sentence: fluid 26–40 px */
  headline: 'clamp(26px, 4.2vw, 40px)',
  section: 20,
  subsection: 15,
  body: 16,
  small: 13,
  chart: 12,
  chartSmall: 11,
  /** "one number" tile: fluid 34–52 px */
  bigNumber: 'clamp(34px, 5vw, 52px)',
  lineHeight: 1.5,
  weights: { regular: 400, medium: 560, semibold: 620, bold: 680 }
} as const;

/** Spacing scale (4 px base). */
export const space = { 0: 0, 1: 4, 2: 8, 3: 12, 4: 16, 5: 24, 6: 32, 7: 48, 8: 64 } as const;
export const radius = { sm: 3, md: 8, lg: 14, pill: 999 } as const;
/** Motion (section 4.6): transitions explain change only, 200–400 ms; prefers-reduced-motion makes them instant. */
export const motion = { fast: 200, base: 300, slow: 400, easing: 'cubic-bezier(0.2, 0, 0, 1)' } as const;
/** Layout */
export const layout = { maxWidth: 1160, gutter: 16, minHitTarget: 32 } as const;

/** Chart mark specs (dataviz skill): 2 px lines, r >= 4 markers, 2 px surface ring, 1 px recessive grid. */
export const marks = { line: 2, dot: 4, ring: 2, grid: 1, barMax: 24 } as const;

const cssName = (k: string) => '--c-' + k.replace(/([a-z])([A-Z0-9])/g, (_, a: string, b: string) => `${a}-${b.toLowerCase()}`);

function hexToRgb(hex: string): [number, number, number] {
  const v = hex.replace('#', '');
  return [0, 2, 4].map((i) => parseInt(v.slice(i, i + 2), 16)) as [number, number, number];
}

function paletteVars(t: Theme): string {
  const p = palettes[t];
  const lines = Object.entries(p).map(([k, v]) => `${cssName(k)}:${v}`);
  const [r, g, b] = hexToRgb(p.model);
  for (const lvl of ['50', '80', '95'] as const) lines.push(`--c-model-${lvl}:rgba(${r}, ${g}, ${b}, ${bandOpacity[lvl][t]})`);
  lines.push(`color-scheme:${t}`);
  return lines.join(';');
}

/** The CSS custom properties for both themes. Light by default; dark from the OS unless the user chose light;
 *  data-theme on <html> overrides (set by the theme toggle before paint, see app.html). */
export function tokensCss(): string {
  const shared = [
    `--font:${typography.font}`,
    `--mono:${typography.mono}`,
    `--fs-headline:${typography.headline}`,
    `--fs-section:${typography.section}px`,
    `--fs-subsection:${typography.subsection}px`,
    `--fs-body:${typography.body}px`,
    `--fs-small:${typography.small}px`,
    `--fs-chart:${typography.chart}px`,
    `--fs-chart-small:${typography.chartSmall}px`,
    `--fs-big:${typography.bigNumber}`,
    ...Object.entries(space).map(([k, v]) => `--space-${k}:${v}px`),
    ...Object.entries(radius).map(([k, v]) => `--radius-${k}:${v}px`),
    `--motion-fast:${motion.fast}ms`,
    `--motion-base:${motion.base}ms`,
    `--motion-slow:${motion.slow}ms`,
    `--easing:${motion.easing}`,
    `--max-width:${layout.maxWidth}px`,
    `--gutter:${layout.gutter}px`,
    `--hit:${layout.minHitTarget}px`
  ].join(';');
  return [
    `:root{${shared};${paletteVars('light')}}`,
    `@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){${paletteVars('dark')}}}`,
    // any element can force a theme for its subtree (the catalogue shows both side by side)
    `:root[data-theme="dark"],[data-theme="dark"]{${paletteVars('dark')}}`,
    `[data-theme="light"]:not(:root){${paletteVars('light')}}`
  ].join('\n');
}

/** CSS variable reference for a palette role, e.g. cssVar('acc') -> 'var(--c-acc)'. */
export const cssVar = (k: keyof Palette | 'model-50' | 'model-80' | 'model-95') => `var(${cssName(k)})`;
