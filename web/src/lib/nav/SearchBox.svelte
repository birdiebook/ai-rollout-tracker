<!-- W12: the search combobox (WAI-ARIA APG "combobox with listbox popup", list autocomplete): an input with
     role=combobox that keeps focus, a listbox of options, aria-activedescendant for the active option.
     Keys: ↓/↑ move (wrapping), PageDown/PageUp move by 10, Enter opens the active option, Escape clears the text
     (in the dialog, Escape on an empty field closes it). Typing filters; with an empty field the list shows
     suggestions (leads, branches, forecasts, pages). Pointer: hover makes an option active, click opens it. -->
<script lang="ts">
  import { KIND_LABEL, highlight, prepare, search, suggestions, type SearchItem } from './search';

  let {
    items,
    query = $bindable(''),
    onpick,
    onescape,
    idPrefix = 'sok',
    limit = 40,
    suggest = true,
    maxHeight = 'min(60vh, calc(100dvh - 220px))',
    label = 'Sök serier, grenar, led och prognoser'
  }: {
    items: SearchItem[] | null;
    query?: string;
    onpick: (item: SearchItem) => void;
    onescape?: () => void;
    idPrefix?: string;
    limit?: number;
    /** show suggestions while the field is empty */
    suggest?: boolean;
    /** CSS max-height of the list (it scrolls) */
    maxHeight?: string;
    label?: string;
  } = $props();

  let input: HTMLInputElement | undefined = $state();
  let list: HTMLUListElement | undefined = $state();
  let active = $state(0);

  const prepared = $derived(items ? prepare(items) : []);
  const hits = $derived(query.trim() ? search(prepared, query) : []);
  const shown = $derived(query.trim() ? hits.slice(0, limit).map((h) => h.item) : items && suggest ? suggestions(items) : []);
  const total = $derived(query.trim() ? hits.length : shown.length);
  const expanded = $derived(shown.length > 0);
  const optId = (i: number) => `${idPrefix}-opt-${i}`;
  const status = $derived(
    !items
      ? 'Laddar sökindexet …'
      : !query.trim()
        ? suggest
          ? `Förslag: ${shown.length}. Skriv för att söka bland ${items.length} poster.`
          : `Skriv för att söka bland ${items.length} poster.`
        : total === 0
          ? `Inga träffar för ”${query.trim()}”.`
          : total > shown.length
            ? `${total} träffar, visar de ${shown.length} bästa.`
            : `${total} ${total === 1 ? 'träff' : 'träffar'}.`
  );

  // a new query starts at the top
  $effect(() => {
    void query;
    active = 0;
  });

  function move(to: number) {
    if (!shown.length) return;
    const n = shown.length;
    active = ((to % n) + n) % n;
    queueMicrotask(() => list?.querySelector(`#${optId(active)}`)?.scrollIntoView?.({ block: 'nearest' }));
  }

  function onkeydown(e: KeyboardEvent) {
    if (e.isComposing) return;
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        move(active + 1);
        break;
      case 'ArrowUp':
        e.preventDefault();
        move(active - 1);
        break;
      case 'PageDown':
        e.preventDefault();
        move(Math.min(active + 10, shown.length - 1));
        break;
      case 'PageUp':
        e.preventDefault();
        move(Math.max(active - 10, 0));
        break;
      case 'Enter':
        if (shown[active]) {
          e.preventDefault();
          onpick(shown[active]);
        }
        break;
      case 'Escape':
        if (query) {
          e.preventDefault();
          e.stopPropagation();
          query = '';
        } else if (onescape) {
          e.preventDefault();
          onescape();
        }
        break;
    }
  }

  export function focus() {
    input?.focus();
    input?.select();
  }
</script>

<div class="sb">
  <label class="visually-hidden" for="{idPrefix}-input">{label}</label>
  <div class="field">
    <svg class="icon" viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
      <circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" stroke-width="2" />
      <line x1="12.6" y1="12.6" x2="17" y2="17" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
    </svg>
    <input
      bind:this={input}
      bind:value={query}
      id="{idPrefix}-input"
      type="text"
      role="combobox"
      aria-autocomplete="list"
      aria-expanded={expanded}
      aria-controls="{idPrefix}-list"
      aria-activedescendant={expanded && shown[active] ? optId(active) : undefined}
      aria-describedby="{idPrefix}-status"
      autocomplete="off"
      autocapitalize="off"
      spellcheck="false"
      enterkeyhint="go"
      placeholder={label}
      {onkeydown}
    />
  </div>
  <p id="{idPrefix}-status" class="status note" role="status" aria-live="polite">{status}</p>
  <ul bind:this={list} id="{idPrefix}-list" role="listbox" aria-label="Träffar" class="list" style:max-height={maxHeight} hidden={!expanded}>
    {#each shown as it, i (it.t + ':' + it.id)}
      <!-- the input keeps focus and handles the keys (aria-activedescendant); the click is for pointers -->
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <li
        id={optId(i)}
        role="option"
        aria-selected={i === active}
        class="opt"
        data-kind={it.t}
        onpointermove={() => (active = i)}
        onmousedown={(e) => e.preventDefault()}
        onclick={() => onpick(it)}
      >
        <span class="kind">{KIND_LABEL[it.t]}</span>
        <span class="txt">
          <span class="l">{#each highlight(it.l, query) as seg, j (j)}{#if seg.hit}<mark>{seg.text}</mark>{:else}{seg.text}{/if}{/each}</span>
          {#if it.s}<span class="s">{it.s}</span>{/if}
        </span>
      </li>
    {/each}
  </ul>
</div>

<style>
  .field {
    position: relative;
    display: flex;
    align-items: center;
  }
  .icon {
    position: absolute;
    left: 12px;
    color: var(--c-muted);
    pointer-events: none;
  }
  input {
    width: 100%;
    font: inherit;
    font-size: 17px;
    color: var(--c-ink);
    background: var(--c-surface);
    border: 1px solid var(--c-axis);
    border-radius: var(--radius-md);
    padding: 10px 12px 10px 38px;
    min-height: 44px;
  }
  input::placeholder {
    color: var(--c-muted);
    opacity: 1;
  }
  input:focus-visible {
    outline: 2px solid var(--c-focus);
    outline-offset: 1px;
  }
  .status {
    margin: 6px 2px 6px;
  }
  .list {
    list-style: none;
    margin: 0;
    padding: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
  }
  .opt {
    display: grid;
    grid-template-columns: 64px minmax(0, 1fr);
    gap: 10px;
    align-items: baseline;
    padding: 8px 10px;
    border-radius: var(--radius-md);
    cursor: pointer;
    min-height: 44px;
  }
  .opt[aria-selected='true'] {
    background: var(--c-mid);
    outline: 2px solid var(--c-ink);
    outline-offset: -2px;
  }
  .kind {
    font-size: 11px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--c-ink-2);
    font-weight: 620;
  }
  .txt {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  .l {
    color: var(--c-ink);
    line-height: 1.3;
    overflow-wrap: anywhere;
  }
  .s {
    font-size: var(--fs-small);
    color: var(--c-ink-2);
    line-height: 1.3;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  mark {
    background: none;
    color: inherit;
    font-weight: 700;
    text-decoration: underline;
    text-decoration-thickness: 2px;
    text-underline-offset: 3px;
  }
  @media (forced-colors: active) {
    .opt[aria-selected='true'] {
      outline-color: Highlight;
    }
  }
</style>
