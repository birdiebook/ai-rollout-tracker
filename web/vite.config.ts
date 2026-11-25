import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig, type Plugin } from 'vitest/config';

// ChartFrame prerenders its SVG body with svelte/server's render() during SSR (R-W2 P1). The client never calls it
// (the branch is behind import.meta.env.SSR), so the client build gets a stub instead of the server renderer.
const serverRenderOnlyOnServer: Plugin = {
  name: 'svelte-server-stub-on-client',
  enforce: 'pre',
  resolveId(id, _importer, opts) {
    if (id === 'svelte/server' && !opts?.ssr) return '\0svelte-server-stub';
  },
  load(id) {
    if (id === '\0svelte-server-stub') return 'export function render() { throw new Error("svelte/server is server-only"); }';
  }
};

export default defineConfig({
  plugins: [serverRenderOnlyOnServer, sveltekit()],
  build: { target: 'es2022' },
  test: {
    include: ['src/**/*.test.ts'],
    environment: 'jsdom',
    setupFiles: ['src/test-setup.ts']
  },
  resolve: process.env.VITEST ? { conditions: ['browser'] } : undefined
});
