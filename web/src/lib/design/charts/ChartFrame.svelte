<!--
  The frame every chart sits in (OWID Grapher idea): title, generated sentence (also the accessible name of the
  SVG), status badge, the SVG itself, legend, table view, source and licence. The SVG is prerendered at the default
  width and redrawn at the real width after hydration; the height is fixed in px, so nothing shifts (CLS).

  Accessibility: the SVG is role="img" named by the sentence. Hover tooltips are for pointer users; the same numbers
  are in the table view, which is the keyboard and screen-reader path. The table view is a native <details>, so it
  opens without JavaScript (R-W2 B1). A small table (<= PRERENDER_CELLS cells) is prerendered inside it; a larger one
  is drawn only when the <details> is first opened (R-W2 P1), and without JavaScript the <details> holds a link to
  the published data the chart is drawn from (`dataHref`, or the page's setChartData).
-->
<script lang="ts">
  import { getAllContexts, onMount, type Snippet } from 'svelte';
  import { render } from 'svelte/server';
  import { dims as mkDims, type ChartDims, type Margin, type RecordStatus, type TableSpec } from './types';
  import { provideTooltip } from './tooltip.svelte';
  import Tooltip from './Tooltip.svelte';
  import DataTable from './DataTable.svelte';
  import StatusBadge from './StatusBadge.svelte';
  import { PRERENDER_CELLS, chartData } from './chartData';
  import { claimingServerMarkup, enqueue, staticMarkup } from './lazy';
  import SnippetHost from './SnippetHost.svelte';

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
    dataHref,
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
    /** the published data behind the chart, linked in the table view (default: the page's setChartData) */
    dataHref?: string | null;
    children: Snippet<[ChartDims]>;
    legend?: Snippet;
  } = $props();

  let measured = $state(0);
  // R-W2 P1: the SVG body is server markup until the chart is drawn live (lazy.ts)
  let live = $state(!import.meta.env.SSR && !claimingServerMarkup());
  let open = $state(false);
  let opened = $state(false);
  $effect(() => {
    if (open) opened = true; // drawn once, kept when closed again
  });
  const pageData = chartData();
  const href = $derived(dataHref === undefined ? pageData() : dataHref);
  const tbl = $derived(table);
  const nRows = $derived(tbl?.rows.length ?? 0);
  const prerendered = $derived(!!tbl && nRows * tbl.columns.length <= PRERENDER_CELLS);
  const w = $derived(measured > 0 ? Math.round(measured) : width);
  const d = $derived(mkDims(w, height, margin));
  const d0 = $derived(mkDims(width, height, margin)); // the prerendered body's dimensions
  const vb = $derived(live ? d : d0);
  const tip = provideTooltip();
  const ctx = import.meta.env.SSR ? getAllContexts() : null; // after provideTooltip: the body's marks read it
  let host: HTMLElement | undefined = $state();
  $effect(() => {
    tip.host = host ?? null;
  });
  // server: the body as a string; client during the first hydration: any non-empty value claims that markup
  const body = $derived(
    import.meta.env.SSR
      ? staticMarkup(render(SnippetHost, { props: { snippet: children as never, args: d0 as never }, context: ctx ?? undefined }).body)
      : ' '
  );
  let job: ReturnType<typeof enqueue> | null = null;
  let seen = false;
  $effect(() => {
    // the inputs the generated sentence and table depend on changed (a view in the URL, a slider): draw live now
    void description;
    void tbl;
    if (seen && !live) {
      job?.cancel();
      live = true;
    }
    seen = true;
  });
  onMount(() => {
    if (!live && host) job = enqueue(host, () => (live = true));
  });
</script>

<figure class="chart" {id} aria-labelledby="{id}-title">
  <figcaption class="head">
    <svelte:element this={'h' + headingLevel} id="{id}-title" class="title">{title}</svelte:element>
    {#if status}<StatusBadge {status} />{/if}
  </figcaption>
  <p class="desc" id="{id}-desc">{description}</p>

  <div class="plot" bind:this={host} bind:clientWidth={measured} id="{id}-chart">
    <svg
      viewBox="0 0 {vb.width} {vb.height}"
      width="100%"
      height={vb.height}
      preserveAspectRatio="xMinYMin meet"
      role="img"
      aria-labelledby="{id}-title {id}-desc"
      onpointerleave={() => tip.hide()}
      onpointerenter={() => job?.now()}
      data-live={live ? '' : undefined}
    >
      {#if live}{@render children(d)}{:else}{@html body}{/if}
    </svg>
    <Tooltip state={tip} hostWidth={d.width} />
  </div>

  <div class="foot">
    {#if legend}<div class="legend-slot">{@render legend()}</div>{/if}
    <div class="meta">
      {#if source}<span>Källa: {source}</span>{/if}
      {#if license}<span>Licens: {license}</span>{/if}
    </div>
    {#if table}
      <details class="tbl" bind:open data-rows={nRows} data-pre={prerendered ? '' : undefined}>
        <summary class="chip">Tabell <span class="n">({nRows} {nRows === 1 ? 'rad' : 'rader'})</span></summary>
        <div id="{id}-table">
          {#if prerendered || opened}
            <DataTable {table} />
          {:else}
            <p class="note nojs">Tabellen har {nRows} rader och ritas när sidan har JavaScript.{#if href} Talen finns i den publicerade datan nedan.{/if}</p>
          {/if}
          {#if href}<p class="note data"><a href={href}>Datan bakom diagrammet (JSON)</a></p>{/if}
        </div>
      </details>
    {/if}
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
  .tbl > summary {
    list-style: none;
    font-size: 12px;
  }
  .tbl > summary::-webkit-details-marker {
    display: none;
  }
  .tbl > summary::before {
    content: '▸';
    margin-right: 5px;
  }
  .tbl[open] > summary::before {
    content: '▾';
  }
  .tbl .n {
    color: var(--c-muted);
  }
  .tbl[open] {
    flex-basis: 100%;
  }
  .tbl[open] > div {
    margin-top: 8px;
  }
  .tbl .note {
    margin: 6px 0 0;
    font-size: 12px;
  }
</style>
