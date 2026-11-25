// State vocabulary (docs/mattregister.md section 2): colour + glyph + word, always all three. Neutral words only.
import { cssVar } from './tokens';

// "för få källor" is index v2's no-state (fewer than 3 counted source families, register 2026-11-24, the official rule
// from the snapshot 2026-11-30); "för få serier" is v1's (fewer than 3 counted series), kept for v1 and older records.
export type StateName = 'accelererar' | 'stabil' | 'bromsar in' | 'för få källor' | 'för få serier';
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
  'för få källor': { key: 'none', glyph: '○', word: 'för få källor', color: cssVar('muted') },
  'för få serier': { key: 'none', glyph: '○', word: 'för få serier', color: cssVar('muted') }
};

/** The fallback for a missing or unknown state: the official rule's no-state. */
export const NO_STATE: StateName = 'för få källor';

export function stateStyle(s: string | null | undefined): StateStyle {
  return (s && STATES[s as StateName]) || STATES[NO_STATE];
}

/** The words for "an index but no state": v2's "för få källor", v1's "för få serier" and a branch without core series. */
export const NO_STATE_WORDS: readonly string[] = ['för få källor', 'för få serier', 'inga registrerade kärnserier'];
export const isNoState = (s: string | null | undefined): boolean => !!s && NO_STATE_WORDS.includes(s);

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
