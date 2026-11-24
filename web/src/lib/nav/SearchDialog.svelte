<!-- W12: the ⌘K / Ctrl+K search as a modal <dialog> (native: the page behind is inert, focus stays inside, Escape
     closes). Loaded lazily by SearchButton on first open, together with the index. Focus returns to the element
     that opened it. -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { onMount, tick } from 'svelte';
  import SearchBox from './SearchBox.svelte';
  import { loadIndex } from './loadIndex';
  import type { SearchItem } from './search';

  let { open = $bindable(false), returnFocus }: { open?: boolean; returnFocus?: () => void } = $props();

  let dlg: HTMLDialogElement | undefined = $state();
  let box: SearchBox | undefined = $state();
  let items: SearchItem[] | null = $state(null);
  let failed = $state(false);
  let query = $state('');

  function retry() {
    failed = false;
    loadIndex()
      .then((ix) => (items = ix.items))
      .catch(() => (failed = true));
  }
  onMount(retry);

  $effect(() => {
    if (!dlg) return;
    if (open && !dlg.open) {
      dlg.showModal();
      tick().then(() => box?.focus());
    } else if (!open && dlg.open) dlg.close();
  });

  function close() {
    open = false;
  }
  function onclose() {
    open = false;
    returnFocus?.();
  }
  async function pick(it: SearchItem) {
    open = false;
    query = '';
    await goto(it.h);
  }
</script>

<!-- a click on the backdrop (the dialog element itself, outside the panel) closes it -->
<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
<dialog bind:this={dlg} class="search-dlg" aria-labelledby="sokdlg-h" {onclose} onclick={(e) => e.target === dlg && close()}>
  <div class="panel-in">
    <div class="head">
      <h2 id="sokdlg-h">Sök</h2>
      <button type="button" class="close" onclick={close}>Stäng <kbd>Esc</kbd></button>
    </div>
    {#if failed}
      <p class="note" role="alert">
        Sökindexet gick inte att läsa. <button type="button" class="close" onclick={retry}>Försök igen</button> eller
        <a href={resolve('/sok')}>öppna registret</a>.
      </p>
    {/if}
    <SearchBox bind:this={box} {items} bind:query onpick={pick} onescape={close} idPrefix="sokdlg" limit={40} />
    <p class="keys note" aria-hidden="true"><kbd>↑</kbd> <kbd>↓</kbd> välj · <kbd>Enter</kbd> öppna · <kbd>Esc</kbd> rensa och stäng</p>
  </div>
</dialog>

<style>
  .search-dlg {
    width: min(680px, calc(100vw - 16px));
    max-width: none;
    max-height: calc(100dvh - 16px);
    margin: 8px auto auto;
    padding: 0;
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-lg);
    background: var(--c-surface);
    color: var(--c-ink);
    box-shadow: 0 18px 50px rgba(0, 0, 0, 0.28);
  }
  @media (min-width: 641px) {
    .search-dlg {
      margin-top: 10vh;
    }
  }
  .search-dlg::backdrop {
    background: rgba(11, 11, 11, 0.42);
  }
  .panel-in {
    padding: 12px 14px 10px;
  }
  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }
  h2 {
    font-size: var(--fs-subsection);
    margin: 0;
  }
  .close {
    font: inherit;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
    background: none;
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-md);
    min-height: var(--hit);
    padding: 2px 10px;
    cursor: pointer;
  }
  kbd {
    font-family: var(--mono);
    font-size: 11px;
    border: 1px solid var(--c-axis);
    border-bottom-width: 2px;
    border-radius: 4px;
    padding: 0 4px;
    color: var(--c-ink-2);
  }
  .keys {
    margin: 8px 2px 0;
    display: none;
  }
  @media (min-width: 641px) and (hover: hover) {
    .keys {
      display: block;
    }
  }
</style>
