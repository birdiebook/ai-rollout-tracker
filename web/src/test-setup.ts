// jsdom has no ResizeObserver (used by bind:clientWidth); a no-op is enough for component tests.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;

// R-W2 P1: components in tests are mounted, not hydrated: draw chart bodies directly (lazy.ts)
import { hydrationDone } from '$lib/design/charts/lazy';
hydrationDone();
