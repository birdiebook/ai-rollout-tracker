<!-- R-W2 P1: a block of a page that is prerendered and then left as server markup on the first hydration instead of
     being walked node by node (see lazy.ts). mode "static": the markup stays until a mouse pointer enters (hover
     tips); for content that never changes after load and has nothing but links and native <details>. mode "idle":
     drawn live in the background queue, for content that changes after mount. On the swap the open <details> and
     the focused element are carried over. Not for blocks with form controls. The wrapper is display: contents, so
     the page's layout and CSS are untouched. -->
<script lang="ts">
  import { getAllContexts, onMount, type Snippet } from 'svelte';
  import { render } from 'svelte/server';
  import { claimingServerMarkup, drawOnce, enqueue, staticMarkup } from './lazy';
  import SnippetHost from './SnippetHost.svelte';

  let { children, mode = 'static' }: { children: Snippet; mode?: 'static' | 'idle' } = $props();
  let live = $state(!import.meta.env.SSR && !claimingServerMarkup());
  const ctx = import.meta.env.SSR ? getAllContexts() : null;
  const body = $derived(
    import.meta.env.SSR
      ? staticMarkup(render(SnippetHost, { props: { snippet: children as never, args: undefined as never }, context: ctx ?? undefined }).body)
      : ' '
  );
  let host: HTMLElement | undefined = $state();
  const FOCUSABLE = 'a[href], button, summary, input, select, textarea, [tabindex]';
  let carry: { open: boolean[]; focus: number } | null = null;
  function before() {
    if (!host) return;
    const f = [...host.querySelectorAll(FOCUSABLE)];
    carry = { open: [...host.querySelectorAll('details')].map((d) => d.open), focus: f.indexOf(document.activeElement as Element) };
  }
  function after() {
    if (!host || !carry) return;
    host.querySelectorAll('details').forEach((d, i) => (d.open = carry!.open[i] ?? d.open));
    if (carry.focus >= 0) (host.querySelectorAll(FOCUSABLE)[carry.focus] as HTMLElement | undefined)?.focus({ preventScroll: true });
    carry = null;
  }
  const draw = () => {
    before();
    live = true;
  };
  let job: ReturnType<typeof enqueue> | null = null;
  onMount(() => {
    if (live || !host) return;
    if (mode === 'idle') job = enqueue(host, draw, after);
  });
  function enter(e: PointerEvent) {
    if (live || e.pointerType !== 'mouse') return; // a touch swap would lose the tap's target
    if (job) job.now();
    else drawOnce(draw, after);
  }
</script>

<div class="deferred" bind:this={host} onpointerenter={enter} role="presentation" data-live={live ? '' : undefined}>
  {#if live}{@render children()}{:else}{@html body}{/if}
</div>

<style>
  .deferred {
    display: contents;
  }
</style>
