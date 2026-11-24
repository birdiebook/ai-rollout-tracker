// Shared helpers for the build checks (budget, external hosts).
import { readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

export function walk(dir) {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });
}

export const rel = (root, p) => relative(root, p).split('\\').join('/');
