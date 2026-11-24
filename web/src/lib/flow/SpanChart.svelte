<!-- Reconciliations between the leads as spans on the chain: nine fixed columns L1–L9, one bar per ratio from the
     first to the last lead it connects, the direction glyph and word on the bar. A withheld ratio is a dashed bar
     without name or direction. Track W6. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { DIRECTIONS } from '$lib/design';
  import type { Dir } from './types';

  type S = { key: string | null; short: string | null; span: number[]; lead: string | null; direction: Dir; linkable: boolean };
  let { spans, current }: { spans: S[]; current?: string } = $props();
  const cols = Array.from({ length: 9 }, (_, i) => `L${i + 1}`);
</script>

<div class="spans">
  <ol class="cols" aria-hidden="true">
    {#each cols as c (c)}<li class:cur={c === current}>{c}</li>{/each}
  </ol>
  <ul class="rows">
    {#each spans as s, i (s.key ?? `hidden-${i}`)}
      {@const d = s.direction === null ? null : DIRECTIONS[s.direction]}
      <li style:grid-column="{s.span[0]} / {s.span[1] + 1}">
        {#if s.key === null}
          <span class="bar held">inhållen avstämning ({s.lead})</span>
        {:else}
          <svelte:element
            this={s.linkable ? 'a' : 'span'}
            class="bar"
            href={s.linkable ? resolve('/serie/[key]', { key: s.key }) : undefined}
          >
            <span class="track" aria-hidden="true">
              {#each cols as c, j (c)}<span class:in={j + 1 >= s.span[0] && j + 1 <= s.span[1]}></span>{/each}
            </span>
            <span class="lbl">{s.short}</span>
            <span class="where">{s.lead}</span>
            {#if d}<span class="dir"><span class="g" style:color={d.color} aria-hidden="true">{d.glyph}</span> {d.word}</span>{/if}
          </svelte:element>
        {/if}
      </li>
    {/each}
  </ul>
</div>

<style>
  .spans {
    display: grid;
    gap: 6px;
  }
  .cols,
  .rows {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(9, minmax(0, 1fr));
    gap: 4px;
  }
  .cols li {
    text-align: center;
    font-size: 11px;
    color: var(--c-muted);
    border-bottom: 1px solid var(--c-grid);
    padding-bottom: 2px;
  }
  .cols li.cur {
    color: var(--c-ink);
    font-weight: 650;
    border-bottom: 2px solid var(--c-ink);
  }
  .rows {
    row-gap: 6px;
  }
  .rows li {
    min-width: 0;
  }
  .bar {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0 8px;
    padding: 5px 8px;
    border: 1px solid var(--c-axis);
    border-radius: var(--radius-md);
    background: var(--c-surface);
    font-size: 12px;
    text-decoration: none;
    min-height: var(--hit);
    color: var(--c-ink);
  }
  a.bar:hover {
    border-color: var(--c-ink);
  }
  .held {
    border-style: dashed;
    color: var(--c-ink-2);
  }
  .lbl {
    font-weight: 600;
  }
  .track {
    display: none;
  }
  @media (max-width: 639px) {
    .cols {
      display: none;
    }
    .rows li {
      grid-column: 1 / -1 !important;
    }
    .track {
      display: flex;
      gap: 2px;
      width: 100%;
      margin-bottom: 3px;
    }
    .track span {
      flex: 1;
      height: 5px;
      border-radius: 2px;
      background: var(--c-grid);
    }
    .track span.in {
      background: var(--c-ink-2);
    }
  }
  .where,
  .dir {
    color: var(--c-ink-2);
  }
</style>
