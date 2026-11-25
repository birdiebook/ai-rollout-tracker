// Share images, step 2 (W12): rasterise every build/og/**/*.svg (written by the prerender, src/routes/og) to a PNG
// beside it, 1200x630. og:image points to the PNG because the large platforms do not show SVG previews.
// Chromium from Playwright (already a dev dependency for the e2e tests; CI installs it before the build), no
// other tool and no network. A content-hash cache (node_modules/.cache/og-png) skips unchanged pictures.
//   node scripts/og-png.mjs [build-dir]
// Fails when an SVG cannot be rasterised or a PNG is over the budget (OG_BUDGET in budget.mjs's terms).
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync, copyFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { chromium } from '@playwright/test';
import { walk } from './lib.mjs';

export const OG_BUDGET = { pngKb: 120, svgKb: 40 };

const build = resolve(process.argv[2] ?? 'build');
const dir = join(build, 'og');
if (!existsSync(dir)) {
  console.error(`og-png: ${dir} does not exist (the prerender writes it); run vite build first`);
  process.exit(2);
}
// `vite preview` (and so the e2e tests) serves the prerendered files from SvelteKit's output, not from build/: the
// PNGs go there too when it is the build being post-processed
const mirror = resolve('.svelte-kit/output/prerendered/pages/og');
const mirrorOf = (out) => (build === resolve('build') && existsSync(mirror) ? join(mirror, out.slice(dir.length + 1)) : null);
const cache = resolve('node_modules/.cache/og-png');
mkdirSync(cache, { recursive: true });

const svgs = walk(dir).filter((f) => f.endsWith('.svg'));
const todo = [];
let hits = 0;
for (const f of svgs) {
  const svg = readFileSync(f);
  const key = createHash('sha256').update('v1').update(svg).digest('hex').slice(0, 32);
  const cached = join(cache, `${key}.png`);
  const out = f.replace(/\.svg$/, '.png');
  if (existsSync(cached)) {
    copyFileSync(cached, out);
    const mo = mirrorOf(out);
    if (mo) copyFileSync(cached, mo);
    hits++;
  } else todo.push({ svg: svg.toString('utf-8'), out, cached });
}

if (todo.length) {
  let browser;
  try {
    browser = await chromium.launch();
  } catch (e) {
    console.error('og-png: could not start Chromium. Install it with `npx playwright install chromium` (CI does this before the build).');
    console.error(String(e).split('\n')[0]);
    process.exit(1);
  }
  const ctx = await browser.newContext({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
  const work = [...todo];
  async function worker() {
    const page = await ctx.newPage();
    for (let t = work.shift(); t; t = work.shift()) {
      await page.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;padding:0;background:#fff}svg{display:block}</style></head><body>${t.svg}</body></html>`, { waitUntil: 'load' });
      const png = await page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: 1200, height: 630 } });
      writeFileSync(t.out, png);
      writeFileSync(t.cached, png);
      const mo = mirrorOf(t.out);
      if (mo) writeFileSync(mo, png);
    }
    await page.close();
  }
  await Promise.all(Array.from({ length: 4 }, worker));
  await browser.close();
}

let over = 0;
let total = 0;
for (const f of svgs) {
  const png = readFileSync(f.replace(/\.svg$/, '.png'));
  const svgKb = readFileSync(f).length / 1024;
  total += png.length;
  if (png.length / 1024 > OG_BUDGET.pngKb || svgKb > OG_BUDGET.svgKb) {
    over++;
    console.error(`og-png: over budget ${f}: png ${(png.length / 1024).toFixed(1)} kB, svg ${svgKb.toFixed(1)} kB`);
  }
}
console.log(`og-png: ${svgs.length} share images (${todo.length} drawn, ${hits} from cache), ${(total / 1024 / 1024).toFixed(2)} MB PNG; budget ${OG_BUDGET.pngKb} kB PNG / ${OG_BUDGET.svgKb} kB SVG each`);
if (over) process.exit(1);
