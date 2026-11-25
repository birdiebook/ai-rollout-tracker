<!-- The inside of a chart's table view (ChartFrame's <details>): the summary and either the prerendered table (small),
     the table drawn on opening (large, with JS) or a note and the link to the published data (large, without JS).
     ChartFrame keeps this as server markup until the chart is live or the <details> is opened, so the hydration does
     not build any table (R-W2 P1). -->
<script lang="ts">
  import DataTable from './DataTable.svelte';
  import { PRERENDER_CELLS } from './chartData';
  import type { TableSpec } from './types';

  let { id, table, href, drawn = false }: { id: string; table: TableSpec; href: string | null; drawn?: boolean } = $props();
  const nRows = $derived(table.rows.length);
  const pre = $derived(nRows * table.columns.length <= PRERENDER_CELLS);
</script>

<summary class="chip">Tabell <span class="n">({nRows} {nRows === 1 ? 'rad' : 'rader'})</span></summary>
<div id="{id}-table" class="tv" data-rows={nRows} data-pre={pre ? '' : undefined}>
  {#if pre || drawn}
    <DataTable {table} />
  {:else}
    <p class="note nojs">Tabellen har {nRows} rader och ritas när sidan har JavaScript.{#if href} Talen finns i den publicerade datan nedan.{/if}</p>
  {/if}
  {#if href}<p class="note data"><a {href}>Datan bakom diagrammet (JSON)</a></p>{/if}
</div>

<style>
  summary {
    list-style: none;
    font-size: 12px;
  }
  summary::-webkit-details-marker {
    display: none;
  }
  summary::before {
    content: '▸';
    margin-right: 5px;
  }
  :global(details[open]) > summary::before {
    content: '▾';
  }
  .n {
    color: var(--c-muted);
  }
  .tv {
    margin-top: 8px;
  }
  .note {
    margin: 6px 0 0;
    font-size: 12px;
  }
</style>
