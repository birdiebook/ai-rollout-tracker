<!-- W12: the search button in the header and the shortcuts ⌘K / Ctrl+K. The dialog
     and the index load on first use only (dynamic import + fetch), so no page pays for them up front. Before
     hydration (or without JavaScript) the button is a link to the search page /sok/, which works without scripts. -->
<script lang="ts">
  import { onMount, type Component } from 'svelte';
  import { resolve } from '$app/paths';

  let mounted = $state(false);
  let open = $state(false);
  let mac = $state(false);
  let Dialog: Component<{ open?: boolean; returnFocus?: () => void }> | null = $state(null);
  let btn: HTMLButtonElement | undefined = $state();
  let opener: HTMLElement | null = null;

  async function show() {
    opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    if (!Dialog) Dialog = (await import('./SearchDialog.svelte')).default as unknown as typeof Dialog;
    open = true;
  }
  const back = () => (opener && opener.isConnected ? opener : btn)?.focus();

  onMount(() => {
    mounted = true;
    mac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
    const onkey = (e: KeyboardEvent) => {
      if (e.defaultPrevented || e.isComposing) return;
      const k = e.key.toLowerCase();
      if (k === 'k' && (e.metaKey || e.ctrlKey) && !e.altKey && !e.shiftKey) {
        e.preventDefault();
        if (!open) show();
      }
      // R-W2 (WCAG 2.1.4): no single-character shortcut ("/" was one): it fires for speech input and stray keys and
      // could not be turned off. ⌘K / Ctrl+K and the button remain.
    };
    addEventListener('keydown', onkey);
    return () => removeEventListener('keydown', onkey);
  });
</script>

{#if mounted}
  <button bind:this={btn} type="button" class="sbtn" aria-haspopup="dialog" aria-keyshortcuts="Meta+K Control+K" onclick={show}>
    {@render inner()}
  </button>
{:else}
  <a class="sbtn" href={resolve('/sok')}>{@render inner()}</a>
{/if}
{#if Dialog}<Dialog bind:open returnFocus={back} />{/if}

{#snippet inner()}
  <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true">
    <circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" stroke-width="2" />
    <line x1="12.6" y1="12.6" x2="17" y2="17" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
  </svg>
  <span>Sök</span>
  <kbd aria-hidden="true">{mac ? '⌘K' : 'Ctrl K'}</kbd>
{/snippet}

<style>
  .sbtn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border: 1px solid var(--c-ring);
    background: var(--c-surface);
    color: var(--c-ink-2);
    border-radius: var(--radius-md);
    font: inherit;
    font-size: var(--fs-small);
    padding: 4px 10px;
    min-height: var(--hit);
    cursor: pointer;
    text-decoration: none;
  }
  .sbtn:hover {
    color: var(--c-ink);
    border-color: var(--c-axis);
  }
  kbd {
    display: none;
    font-family: var(--mono);
    font-size: 11px;
    border: 1px solid var(--c-axis);
    border-radius: 4px;
    padding: 0 4px;
    min-width: 42px;
    text-align: center;
    color: var(--c-muted);
  }
  @media (min-width: 900px) and (hover: hover) {
    kbd {
      display: inline-block;
    }
  }
</style>
