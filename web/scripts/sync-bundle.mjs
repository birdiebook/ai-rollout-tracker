// Copy the site_bundle the build should use into static/data/ (served as <base>/data/ and read by the prerender).
// Source, first match wins:
//   1. SITE_BUNDLE_DIR             the real bundle (CI: python -m ai_tracker.site_bundle build --out <dir>)
//   2. ../web-data-fixtures[/site_bundle]   W3's committed fixtures (contract tests)
//   3. fixtures/provisional        W4's provisional synthetic fixture (until W3's exist)
// REQUIRE_REAL_BUNDLE=1 refuses 2 and 3 (the deploy job: never publish fixtures as data).
import { cpSync, existsSync, rmSync, readFileSync } from 'node:fs';
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
cpSync(dir, out, { recursive: true, filter: (src) => !src.endsWith('.py') });
const m = JSON.parse(readFileSync(join(out, 'manifest.json'), 'utf-8'));
console.log(`sync-bundle: ${kind} from ${dir} (schema ${m.version ?? m.schema_version}${m.synthetic ? ', synthetic' : ''}${m.provisional ? ', provisional' : ''}) -> static/data/`);
