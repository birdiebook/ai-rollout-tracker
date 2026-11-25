// Colour checks used by the token tests (and available to chart code): WCAG 2 contrast, OKLab distance (x100) and
// colour-vision-deficiency simulation (Machado et al. 2009, severity 1). The numbers match the dataviz skill's
// validator that docs/steg3/hemsida_vision.md section 4.4 quotes (CVD dE 26.7 light / 27.5 dark for blue/orange, R-W3 colours).

type RGB = [number, number, number];

export function hexToSrgb(hex: string): RGB {
  const v = hex.trim().replace('#', '');
  if (!/^[0-9a-fA-F]{6}$/.test(v)) throw new Error(`not a #rrggbb colour: ${hex}`);
  return [0, 2, 4].map((i) => parseInt(v.slice(i, i + 2), 16) / 255) as RGB;
}

const s2lin = (c: number) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const lin = (hex: string): RGB => hexToSrgb(hex).map(s2lin) as RGB;

export function relativeLuminance(hex: string): number {
  const [r, g, b] = lin(hex);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** WCAG 2.x contrast ratio, 1..21. */
export function contrast(a: string, b: string): number {
  const [hi, lo] = [relativeLuminance(a), relativeLuminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

function oklabFromLin([r, g, b]: RGB): RGB {
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [
    0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s
  ];
}

export type Vision = 'normal' | 'protan' | 'deutan' | 'tritan';

const MACHADO: Record<Exclude<Vision, 'normal'>, [RGB, RGB, RGB]> = {
  protan: [
    [0.152286, 1.052583, -0.204868],
    [0.114503, 0.786281, 0.099216],
    [-0.003882, -0.048116, 1.051998]
  ],
  deutan: [
    [0.367322, 0.860646, -0.227968],
    [0.280085, 0.672501, 0.047413],
    [-0.01182, 0.04294, 0.968881]
  ],
  tritan: [
    [1.255528, -0.076749, -0.178779],
    [-0.078411, 0.930809, 0.147602],
    [0.004733, 0.691367, 0.3039]
  ]
};

function simulate(hex: string, v: Vision): RGB {
  const c = lin(hex);
  if (v === 'normal') return c;
  const M = MACHADO[v];
  const clamp = (x: number) => Math.max(0, Math.min(1, x));
  return M.map((row) => clamp(row[0] * c[0] + row[1] * c[1] + row[2] * c[2])) as RGB;
}

export function oklab(hex: string): RGB {
  return oklabFromLin(lin(hex));
}

/** Euclidean distance in OKLab x100 under the given vision. */
export function deltaE(a: string, b: string, v: Vision = 'normal'): number {
  const p = oklabFromLin(simulate(a, v));
  const q = oklabFromLin(simulate(b, v));
  return 100 * Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]);
}
