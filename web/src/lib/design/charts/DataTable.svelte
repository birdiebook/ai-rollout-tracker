<!-- The table view of a chart: same numbers as the chart, already formatted (format.ts). -->
<script lang="ts">
  import type { TableSpec } from './types';

  let { table, id }: { table: TableSpec; id?: string } = $props();
  const align = (v: unknown, a?: 'left' | 'right') => a ?? (typeof v === 'number' || /^[−+±\d]/.test(String(v ?? '')) ? 'right' : 'left');
</script>

<!-- focusable so keyboard users can scroll a wide table (axe scrollable-region-focusable) -->
<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
<div class="scroll-x" {id} tabindex="0" role="region" aria-label={table.caption ?? 'Tabell'}>
  <table class="data">
    {#if table.caption}<caption>{table.caption}</caption>{/if}
    <thead>
      <tr>
        {#each table.columns as c (c.key)}<th scope="col" style:text-align={c.align}>{c.label}</th>{/each}
      </tr>
    </thead>
    <tbody>
      {#each table.rows as r, i (i)}
        <tr>
          {#each table.columns as c, j (c.key)}
            {#if j === 0}
              <th scope="row" style:text-align={c.align ?? 'left'} style:font-weight="400">{r[c.key] ?? '–'}</th>
            {:else}
              <td style:text-align={align(r[c.key], c.align)}>{r[c.key] ?? '–'}</td>
            {/if}
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>
