// jsdom has no ResizeObserver (used by bind:clientWidth); a no-op is enough for component tests.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;
