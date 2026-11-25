// Copy the site_bundle the build should use into static/data/ (served as <base>/data/ and read by the prerender).
// Source, first match wins:
//   1. SITE_BUNDLE_DIR             the real bundle (CI: python -m ai_tracker.site_bundle build --out <dir>)
//   2. ../web-data-fixtures[/site_bundle]   W3's committed fixtures (contract tests)
//   3. fixtures/provisional        W4's provisional synthetic fixture (until W3's exist)
// REQUIRE_REAL_BUNDLE=1 refuses 2 and 3 (the deploy job: never publish fixtures as data).
import { createHash } from 'node:crypto';
import { copyFileSync, cpSync, existsSync, mkdirSync, rmSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const web = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const hasManifest = (d) => existsSync(join(d, 'manifest.json'));

function pick() {
  const env = process.env.SITE_BUNDLE_DIR;
  if (env) {
    const d = resolve(env);
    if (!hasManifest(d)) throw new Error(`SITE_BUNDLE_DIR=${d} has no manifest.json`);
    return { dir: d, kind: 'bundle' };
  }
  if (process.env.REQUIRE_REAL_BUNDLE === '1') throw new Error('REQUIRE_REAL_BUNDLE=1 but SITE_BUNDLE_DIR is not set');
  for (const d of [join(web, '..', 'web-data-fixtures'), join(web, '..', 'web-data-fixtures', 'site_bundle')]) {
    if (hasManifest(d)) return { dir: d, kind: 'w3-fixtures' };
  }
  return { dir: join(web, 'fixtures', 'provisional'), kind: 'provisional-fixture' };
}

const { dir, kind } = pick();
const out = join(web, 'static', 'data');
rmSync(out, { recursive: true, force: true });
const src = JSON.parse(readFileSync(join(dir, 'manifest.json'), 'utf-8'));
if (Array.isArray(src.files)) {
  // R-W1: publish exactly the files the licence-scanned bundle lists, checksum-verified; a stray file in the bundle
  // directory (a debug dump, a file left by another tool) is never copied to the public site
  for (const f of src.files) {
    if (typeof f.path !== 'string' || f.path.startsWith('/') || f.path.split('/').includes('..')) throw new Error(`sync-bundle: bad path in manifest: ${f.path}`);
    const from = join(dir, f.path);
    const buf = readFileSync(from);
    if (f.sha256 && createHash('sha256').update(buf).digest('hex') !== f.sha256) throw new Error(`sync-bundle: ${f.path} differs from the manifest's sha256`);
    mkdirSync(dirname(join(out, f.path)), { recursive: true });
    copyFileSync(from, join(out, f.path));
  }
  copyFileSync(join(dir, 'manifest.json'), join(out, 'manifest.json'));
} else {
  if (kind === 'bundle') throw new Error('sync-bundle: the bundle manifest lists no files');
  cpSync(dir, out, { recursive: true, filter: (p) => !p.endsWith('.py') }); // the provisional fixture (no file list)
}
const m = JSON.parse(readFileSync(join(out, 'manifest.json'), 'utf-8'));
console.log(`sync-bundle: ${kind} from ${dir} (schema ${m.version ?? m.schema_version}${m.synthetic ? ', synthetic' : ''}${m.provisional ? ', provisional' : ''}) -> static/data/`);
