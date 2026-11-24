// Playwright smoke, accessibility (axe) and screenshots against the built site (npm run build first).
// Desktop 1280 px and mobile 375 px. Screenshots go to SHOTS_DIR (default test-results/shots).
import { defineConfig, devices } from '@playwright/test';

const base = (process.env.BASE_PATH ?? '/next').replace(/\/+$/, '');

export default defineConfig({
  testDir: 'tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: `http://localhost:4173${base}/`,
    trace: 'retain-on-failure'
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 900 } } },
    { name: 'mobile', use: { ...devices['Desktop Chrome'], viewport: { width: 375, height: 812 }, deviceScaleFactor: 2, hasTouch: true } }
  ],
  webServer: {
    command: 'npm run preview',
    url: `http://localhost:4173${base}/`,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000
  }
});
