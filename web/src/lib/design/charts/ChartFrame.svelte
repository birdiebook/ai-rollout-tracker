<!--
  The frame every chart sits in (OWID Grapher idea): title, generated sentence (also the accessible name of the
  SVG), status badge, the SVG itself, legend, table view toggle, source and licence. The SVG is prerendered at the
  default width and redrawn at the real width after hydration; the height is fixed in px, so nothing shifts (CLS).

  Accessibility: the SVG is role="img" named by the sentence. Hover tooltips are for pointer users; the same numbers
  are always one keypress away in the table view (TableToggle), which is the keyboard and screen-reader path.
-->
<script lang="ts">
  import type { Snippet } from 'svelte';
  import { dims as mkDims, type ChartDims, type Margin, type RecordStatus, type TableSpec } from './types';
  import { provideTooltip } from './tooltip.svelte';
  import Tooltip from './Tooltip.svelte';
  import TableToggle from './TableToggle.svelte';
  import DataTable from './DataTable.svelte';
  import StatusBadge from './StatusBadge.svelte';

  let {
    id,
    title,
    description,
    height = 240,
    width = 640,
    margin = { top: 10, right: 12, bottom: 24, left: 40 },
    table,
    status,
    source,
    license,
    headingLevel = 3,
    children,
    legend
  }: {
    id: string;
    title: string;
    /** one sentence generated from the data: what the chart shows (section 4.3) */
    description: string;
    height?: number;
    /** default (prerender) width; the real width is measured on the client */
    width?: number;
    margin?: Margin;
    table?: TableSpec;
    status?: RecordStatus;
    source?: string;
    license?: string;
    headingLevel?: 2 | 3 | 4;
    children: Snippet<[ChartDims]>;
    legend?: Snippet;
  } = $props();

  let measured = $state(0);
  let showTable = $state(false);
  const w = $derived(measured > 0 ? Math.round(measured) : width);
  const d = $derived(mkDims(w, height, margin));
  const tip = provideTooltip();
  let host: HTMLElement | undefined = $state();
  $effect(() => {
    tip.host = host ?? null;
  });
</script>

<figure class="chart" {id} aria-labelledby="{id}-title">
  <figcaption class="head">
    <svelte:element this={'h' + headingLevel} id="{id}-title" class="title">{title}</svelte:element>
    {#if status}<StatusBadge {status} />{/if}
  </figcaption>
  <p class="desc" id="{id}-desc">{description}</p>

  <div class="plot" bind:this={host} bind:clientWidth={measured} hidden={showTable} id="{id}-chart">
    <svg
      viewBox="0 0 {d.width} {d.height}"
      width="100%"
      height={d.height}
      preserveAspectRatio="xMinYMin meet"
      role="img"
      aria-labelledby="{id}-title {id}-desc"
      onpointerleave={() => tip.hide()}
    >
      {@render children(d)}
    </svg>
    <Tooltip state={tip} hostWidth={d.width} />
  </div>
  {#if table}
    <div hidden={!showTable} id="{id}-table"><DataTable {table} /></div>
  {/if}

  <div class="foot">
    {#if legend}<div class="legend-slot">{@render legend()}</div>{/if}
    <div class="meta">
      {#if source}<span>Källa: {source}</span>{/if}
      {#if license}<span>Licens: {license}</span>{/if}
      {#if table}<TableToggle bind:pressed={showTable} controls="{id}-chart {id}-table" />{/if}
    </div>
  </div>
</figure>

<style>
  .chart {
    margin: 0;
    min-width: 0;
  }
  .head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 10px;
  }
  .title {
    margin: 0;
    font-size: var(--fs-subsection);
    font-weight: 620;
  }
  .desc {
    margin: 2px 0 8px;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
    max-width: 70ch;
  }
  .plot {
    position: relative;
  }
  .plot[hidden] {
    display: none;
  }
  svg {
    display: block;
    overflow: visible;
  }
  .foot {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 8px 16px;
    margin-top: 8px;
  }
  .meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 14px;
    font-size: 12px;
    color: var(--c-muted);
    margin-left: auto;
  }
</style>
