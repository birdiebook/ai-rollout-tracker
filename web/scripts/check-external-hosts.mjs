// The built site loads nothing from other hosts (no CDN, fonts, analytics): the same rule as tests/test_site.py for
// the old site. Static half of the check; tests/e2e/smoke.spec.ts checks the requests a real browser makes.
//   node scripts/check-external-hosts.mjs [build-dir]
// Fails on: absolute/protocol-relative URLs in src=, srcset=, <link href>, <use href>, CSS url()/@import, and on
// http(s) URLs in JS/CSS whose host is not in ALLOWED (string constants that are never fetched).
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { rel, walk } from './lib.mjs';

/** Hosts that may appear as text: XML namespaces, and link targets/error docs that are never loaded. */
export const ALLOWED = new Set(['www.w3.org', 'github.com', 'svelte.dev']);

const build = resolve(process.argv[2] ?? 'build');
const problems = [];
const external = (u) => /^(https?:)?\/\//i.test(u.trim());

for (const file of walk(build)) {
  const name = rel(build, file);
  if (!/\.(html|js|css|svg|json)$/.test(file)) continue;
  const text = readFileSync(file, 'utf-8');
  if (/\.(html|svg)$/.test(file)) {
    for (const m of text.matchAll(/<(script|img|iframe|source|video|audio|embed|object|track|input)\b[^>]*\b(src|data|srcset|poster)="([^"]*)"/gi)) {
      if (m[3].split(',').some((p) => external(p))) problems.push(`${name}: <${m[1]} ${m[2]}="${m[3]}">`);
    }
    for (const m of text.matchAll(/<link\b[^>]*\bhref="([^"]*)"/gi)) if (external(m[1])) problems.push(`${name}: <link href="${m[1]}">`);
    for (const m of text.matchAll(/<(use|image)\b[^>]*\b(?:xlink:)?href="([^"]*)"/gi)) if (external(m[2])) problems.push(`${name}: <${m[1]} href="${m[2]}">`);
  }
  if (/\.(css|html)$/.test(file)) {
    for (const m of text.matchAll(/url\(\s*['"]?([^'")]+)/gi)) if (external(m[1])) problems.push(`${name}: url(${m[1]})`);
    for (const m of text.matchAll(/@import\s+(?:url\()?['"]?([^'");\s]+)/gi)) if (external(m[1])) problems.push(`${name}: @import ${m[1]}`);
  }
  // Code only: in HTML, source links (<a href>, attribution text, inlined data) are shown but never loaded; what HTML
  // loads is covered by the attribute checks above and by the browser test in tests/e2e/smoke.spec.ts.
  if (/\.(js|css)$/.test(file)) {
    for (const m of text.matchAll(/https?:\/\/([a-z0-9.-]+\.[a-z]{2,})/gi)) {
      if (!ALLOWED.has(m[1].toLowerCase())) problems.push(`${name}: host ${m[1]}`);
    }
  }
}

if (problems.length) {
  console.error(`external hosts: ${problems.length} problem(s)`);
  for (const p of [...new Set(problems)].slice(0, 50)) console.error('  ' + p);
  process.exit(1);
}
console.log(`external hosts: ok (allowed as text only: ${[...ALLOWED].join(', ')})`);
