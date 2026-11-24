// State vocabulary (docs/mattregister.md section 2): colour + glyph + word, always all three. Neutral words only.
import { cssVar } from './tokens';

export type StateName = 'accelererar' | 'stabil' | 'bromsar in' | 'för få serier';
export type Direction = 1 | 0 | -1;

export interface StateStyle {
  key: 'acc' | 'stb' | 'brk' | 'none';
  glyph: '▲' | '●' | '▼' | '○';
  word: string;
  color: string;
}

export const STATES: Record<StateName, StateStyle> = {
  accelererar: { key: 'acc', glyph: '▲', word: 'accelererar', color: cssVar('acc') },
  stabil: { key: 'stb', glyph: '●', word: 'stabil', color: cssVar('stb') },
  'bromsar in': { key: 'brk', glyph: '▼', word: 'bromsar in', color: cssVar('brk') },
  'för få serier': { key: 'none', glyph: '○', word: 'för få serier', color: cssVar('muted') }
};

export function stateStyle(s: string | null | undefined): StateStyle {
  return (s && STATES[s as StateName]) || STATES['för få serier'];
}

/** A series' direction (+1 more pace, 0 within the dead band, -1 less pace) in the same vocabulary. */
export const DIRECTIONS: Record<Direction, StateStyle> = {
  1: { key: 'acc', glyph: '▲', word: 'ökar takten', color: cssVar('acc') },
  0: { key: 'stb', glyph: '●', word: 'oförändrad takt', color: cssVar('stb') },
  [-1]: { key: 'brk', glyph: '▼', word: 'minskar takten', color: cssVar('brk') }
} as Record<Direction, StateStyle>;

/** Diverging fill for a diffusion index in [0, 1]: orange (0) – grey midpoint (0.5) – blue (1). Mixed by the
 *  browser in OKLab from the theme's tokens, so the same prerendered SVG is right in light and dark mode. */
export function divergingFill(x: number | null | undefined): string {
  if (x === null || x === undefined || Number.isNaN(x)) return 'transparent';
  const t = Math.max(-1, Math.min(1, (x - 0.5) * 2));
  const a = Math.round(Math.abs(t) ** 0.85 * 100);
  const pole = t >= 0 ? cssVar('acc') : cssVar('brk');
  return `color-mix(in oklab, ${cssVar('mid')}, ${pole} ${a}%)`;
}
