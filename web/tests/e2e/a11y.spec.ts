// WCAG 2.2 AA with axe on every route, in light and dark mode.
import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { routes } from './routes';

for (const scheme of ['light', 'dark'] as const) {
  for (const r of routes()) {
    test(`axe ${r.name} (${scheme})`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: scheme });
      await page.goto(r.path);
      await page.waitForLoadState('networkidle');
      const res = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze();
      const summary = res.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.length} × ${v.nodes[0]?.target.join(' ')}`);
      expect(summary).toEqual([]);
    });
  }
}
