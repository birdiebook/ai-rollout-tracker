// Performance budget (docs/steg3/hemsida_vision.md 6.3, P12): per prerendered page, the gzip size of the JS and CSS
// it loads (modulepreload/script/stylesheet links in its HTML) and of the data it inlines. Exit 1 over budget.
//   node scripts/budget.mjs [build-dir]      (default build/)
// Pages that intentionally load more (e.g. /data with DuckDB-WASM on demand) must load it lazily: lazy chunks are
// not in the HTML and do not count here, which is the point.
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { gzipSync } from 'node:zlib';
import { rel, walk } from './lib.mjs';

export const BUDGET = {
  jsKb: 150, // gzip, per page (start page target in the vision; applied to every page)
  cssKb: 30, // gzip, per page
  dataKb: 100 // gzip, data inlined in the page HTML (SvelteKit serialises load() data into it)
};

const build = resolve(process.argv[2] ?? 'build');
if (!existsSync(build)) {
  console.error(`budget: ${build} does not exist; run npm run build first`);
  process.exit(2);
}
const base = (process.env.BASE_PATH ?? '/next').replace(/\/+$/, '');
const gz = (buf) => gzipSync(buf, { level: 9 }).length;
const kb = (n) => n / 1024;
const sizeCache = new Map();
// R-W2: an asset the HTML names but the build lacks (usually BASE_PATH not set like the build's) used to count as
// 0 kB, so every page passed with JS 0 kB. It now fails the budget.
const missing = new Set();
function assetSize(url) {
  const path = url.startsWith(base + '/') ? url.slice(base.length + 1) : url.replace(/^\//, '');
  const file = join(build, path);
  if (!sizeCache.has(file)) {
    if (!existsSync(file)) missing.add(url);
    sizeCache.set(file, existsSync(file) ? gz(readFileSync(file)) : 0);
  }
  return sizeCache.get(file);
}

const rows = [];
let failed = false;
for (const file of walk(build).filter((f) => f.endsWith('.html'))) {
  const html = readFileSync(file, 'utf-8');
  const js = new Set();
  const css = new Set();
  for (const m of html.matchAll(/<link\b[^>]*>/g)) {
    const href = m[0].match(/\bhref="([^"]+)"/)?.[1];
    const relAttr = m[0].match(/\brel="([^"]+)"/)?.[1];
    if (!href) continue;
    if (relAttr === 'modulepreload') js.add(href);
    if (relAttr === 'stylesheet') css.add(href);
  }
  for (const m of html.matchAll(/<script[^>]+src="([^"]+)"/g)) js.add(m[1]);
  for (const m of html.matchAll(/import\("([^"]+\.js)"\)/g)) js.add(m[1]);
  const jsB = [...js].reduce((a, u) => a + assetSize(u), 0);
  const cssB = [...css].reduce((a, u) => a + assetSize(u), 0);
  // inlined data: the hydration script's data array
  const dataMatch = html.match(/data:\s*(\[[\s\S]*?\]),\s*form:/);
  const dataB = dataMatch ? gz(Buffer.from(dataMatch[1])) : 0;
  const over = [kb(jsB) > BUDGET.jsKb && 'js', kb(cssB) > BUDGET.cssKb && 'css', kb(dataB) > BUDGET.dataKb && 'data'].filter(Boolean);
  if (over.length) failed = true;
  rows.push({ page: rel(build, file), js_kb: +kb(jsB).toFixed(1), css_kb: +kb(cssB).toFixed(1), data_kb: +kb(dataB).toFixed(1), html_kb: +kb(gz(Buffer.from(html))).toFixed(1), over: over.join(',') });
}
rows.sort((a, b) => b.js_kb - a.js_kb);
console.table(rows);
console.log(`budget (gzip): JS <= ${BUDGET.jsKb} kB, CSS <= ${BUDGET.cssKb} kB, inlined data <= ${BUDGET.dataKb} kB per page`);
if (process.env.BUDGET_REPORT) writeFileSync(process.env.BUDGET_REPORT, JSON.stringify({ budget: BUDGET, pages: rows }, null, 2));
if (missing.size) {
  console.error(`budget: ${missing.size} referenced assets not found in the build (BASE_PATH=${base}; set it as for the build), e.g. ${[...missing][0]}`);
  failed = true;
}
if (failed) {
  console.error('budget: FAILED');
  process.exit(1);
}
console.log(`budget: ok (${rows.length} pages)`);
