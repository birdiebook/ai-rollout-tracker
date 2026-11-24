// Full-page screenshots of every route, light and dark, for review (CI uploads them as an artifact).
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { test } from '@playwright/test';
import { routes } from './routes';

const dir = process.env.SHOTS_DIR ?? 'test-results/shots';
mkdirSync(dir, { recursive: true });

for (const scheme of ['light', 'dark'] as const) {
  for (const r of routes()) {
    test(`screenshot ${r.name} ${scheme}`, async ({ page }, info) => {
      await page.emulateMedia({ colorScheme: scheme, reducedMotion: 'reduce' });
      await page.goto(r.path);
      await page.waitForLoadState('networkidle');
      await page.screenshot({ path: join(dir, `${r.name}-${info.project.name}-${scheme}.png`), fullPage: true });
    });
  }
}
