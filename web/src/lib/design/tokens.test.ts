// The colour system is computable, so it is computed (docs/steg3/hemsida_vision.md 4.4, dataviz validator checks).
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { contrast, deltaE } from './color';
import { palettes, tokensCss, type Theme } from './tokens';

const themes: Theme[] = ['light', 'dark'];

describe.each(themes)('palette %s', (t) => {
  const p = palettes[t];
  it('text tokens pass WCAG AA (4.5:1) on page and surface', () => {
    for (const k of ['ink', 'ink2', 'muted'] as const) {
      for (const bg of [p.page, p.surface]) expect(contrast(p[k], bg), `${k} on ${bg}`).toBeGreaterThanOrEqual(4.5);
    }
  });
  it('direction, model and baseline marks pass 3:1 against the surface (WCAG 1.4.11)', () => {
    for (const k of ['acc', 'brk', 'stb', 'model', 'base'] as const) {
      expect(contrast(p[k], p.surface), k).toBeGreaterThanOrEqual(3);
      expect(contrast(p[k], p.page), k).toBeGreaterThanOrEqual(3);
    }
  });
  it('blue/orange stay apart for colour-blind readers (OKLab dE x100 >= 8) and normal vision (>= 15)', () => {
    for (const v of ['protan', 'deutan', 'tritan'] as const) expect(deltaE(p.acc, p.brk, v), v).toBeGreaterThanOrEqual(8);
    expect(deltaE(p.acc, p.brk)).toBeGreaterThanOrEqual(15);
  });
  it('the balance grey is distinguishable from both poles', () => {
    expect(deltaE(p.stb, p.acc)).toBeGreaterThanOrEqual(15);
    expect(deltaE(p.stb, p.brk)).toBeGreaterThanOrEqual(15);
  });
  it('never uses green or red hues for direction', () => {
    // OKLab hue angle: red ~ 20-40 deg, green ~ 130-150 deg. Orange sits at ~55-60, blue at ~255.
    for (const k of ['acc', 'brk'] as const) {
      const [r, g, b] = [1, 3, 5].map((i) => parseInt(p[k].slice(i, i + 2), 16));
      expect(g > r && g > b, `${k} is not green`).toBe(false);
    }
  });
});

it('matches the validated values quoted in the vision (CVD protan 26.1 light, 26.8 dark)', () => {
  expect(deltaE(palettes.light.acc, palettes.light.brk, 'protan')).toBeCloseTo(26.1, 1);
  expect(deltaE(palettes.dark.acc, palettes.dark.brk, 'protan')).toBeCloseTo(26.8, 1);
});

it('dark mode is its own palette, not an inversion of light', () => {
  expect(palettes.dark.acc).not.toBe(palettes.light.acc);
  expect(Object.keys(palettes.dark).sort()).toEqual(Object.keys(palettes.light).sort());
});

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? files(p) : [p];
  });
}

it('every var(--c-*) used in components and pages is defined by tokensCss', () => {
  const css = tokensCss();
  const defined = new Set([...css.matchAll(/(--[a-z0-9-]+):/g)].map((m) => m[1]));
  const used = new Set<string>();
  for (const f of files('src').filter((f) => /\.(svelte|ts|css)$/.test(f) && !f.endsWith('.test.ts'))) {
    for (const m of readFileSync(f, 'utf-8').matchAll(/var\((--[a-z0-9-]+)/g)) used.add(m[1]);
  }
  // --c-model-{level} is built from a template literal in Band.svelte
  used.delete('--c-model-');
  const missing = [...used].filter((v) => !defined.has(v));
  expect(missing).toEqual([]);
});
