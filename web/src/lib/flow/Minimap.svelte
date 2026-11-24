<!-- The chain L1–L9 as a minimap (P7, section 3.2): nine small boxes in a fixed order, one cell per branch in the
     diverging index colour, the current lead (or the leads a branch belongs to) marked. Every box links to its lead.
     Track W6; candidate for the design system. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { divergingFill, fmt, stateStyle } from '$lib/design';
  import type { MiniLead } from './types';

  let {
    leads,
    current = [],
    branch
  }: {
    leads: MiniLead[];
    /** the lead(s) to mark: one on a lead page, one or more on a branch page */
    current?: string[];
    /** on a branch page: the branch whose cell is outlined */
    branch?: string;
  } = $props();
  const on = $derived(new Set(current));
</script>

<nav class="minimap" aria-label="Kedjan L1–L9">
  <ol>
    {#each leads as l (l.code)}
      {@const isOn = on.has(l.code)}
      <li class:on={isOn}>
        <a
          href={resolve('/flode/[led]', { led: l.code })}
          aria-current={isOn ? (branch ? 'location' : 'page') : undefined}
          title="{l.code} {l.name}"
        >
          <span class="code">{l.code}</span>
          <span class="name" aria-hidden="true">{l.short.join(' ')}</span>
          <span class="visually-hidden">
            {l.name}: {l.branches.map((b) => `${b.code} ${stateStyle(b.state).word}`).join(', ')}
          </span>
          <span class="cells" aria-hidden="true">
            {#each l.branches as b (b.code)}
              <span
                class="cell"
                class:me={b.code === branch}
                class:empty={b.index === null}
                style:background={divergingFill(b.index)}
                title="{b.code} {b.name ?? ''}: {stateStyle(b.state).glyph} {stateStyle(b.state).word}, index {fmt(b.index, 2)}"
              ></span>
            {/each}
          </span>
        </a>
      </li>
    {/each}
  </ol>
</nav>

<style>
  .minimap ol {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(9, minmax(0, 1fr));
    gap: 4px;
  }
  .minimap li {
    position: relative;
    min-width: 0;
  }
  a {
    display: flex;
    flex-direction: column;
    gap: 3px;
    height: 100%;
    min-height: var(--hit);
    padding: 5px 6px 6px;
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-md);
    background: var(--c-surface);
    text-decoration: none;
    color: var(--c-ink-2);
  }
  a:hover {
    border-color: var(--c-axis);
    color: var(--c-ink);
  }
  .on a {
    border-color: var(--c-ink);
    box-shadow: 0 0 0 1px var(--c-ink);
    color: var(--c-ink);
  }
  .code {
    font-size: 12px;
    font-weight: 650;
    font-variant-numeric: tabular-nums;
  }
  .name {
    display: none;
    font-size: 11px;
    line-height: 1.25;
    min-height: 2.5em;
  }
  .cells {
    display: flex;
    gap: 2px;
    margin-top: auto;
  }
  .cell {
    flex: 1;
    height: 8px;
    border-radius: 2px;
    min-width: 0;
  }
  .cell.empty {
    border: 1px solid var(--c-grid);
  }
  .cell.me {
    outline: 2px solid var(--c-ink);
    outline-offset: 1px;
  }
  @media (min-width: 720px) {
    .name {
      display: block;
    }
    .minimap ol {
      gap: 6px;
    }
  }
  @media (forced-colors: active) {
    .cell {
      forced-color-adjust: none;
    }
  }
</style>
