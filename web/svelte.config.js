// SvelteKit config for the new site (docs/steg3/webb.md). Static: every page is prerendered, no server at runtime.
// BASE_PATH sets where the site lives on GitHub Pages: "/next" (default) while it runs beside the old site, "" at the
// root after the switch (W16). SvelteKit wants no trailing slash.
import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

const base = (process.env.BASE_PATH ?? '/next').replace(/\/+$/, '');

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({ pages: 'build', assets: 'build', fallback: undefined, strict: true }),
    paths: { base, relative: false },
    prerender: {
      entries: ['*'],
      handleHttpError: 'fail',
      handleMissingId: 'fail'
    },
    // Everything is self-hosted: no fonts, scripts or styles from other hosts (tests/e2e and scripts/check-external-hosts.mjs).
    inlineStyleThreshold: 0,
    version: { name: process.env.GITHUB_SHA ?? 'dev' }
  }
};

export default config;
