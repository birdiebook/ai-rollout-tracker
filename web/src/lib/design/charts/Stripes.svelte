<!-- State stripes, branch x month: the whole history in one picture (lesson 1). Labels shorten to the code on narrow
     screens. Goes inside a ChartFrame. The cells are drawn inline (same marks as StripeCell) with one delegated
     tooltip handler, since a page can have hundreds of them (R-W2 P1). A month where the branch has too few series
     for a state is drawn without the diverging colour (R-W3: an index without a state is no direction). -->
<script lang="ts">
  import { fmt, periodLabel } from '../format';
  import { divergingFill, stateStyle } from '../state';
  import { useTooltip } from './tooltip.svelte';
  import type { ChartDims, RecordStatus } from './types';

  let {
    dims,
    months,
    kind = [],
    rows,
    rowHeight = 24
  }: {
    dims: ChartDims;
    months: string[];
    /** record kind per month ('skarp' = live) */
    kind?: (string | null)[];
    rows: { code: string; name: string; index: (number | null)[]; state?: (string | null)[] }[];
    rowHeight?: number;
  } = $props();

  const labelW = $derived(dims.width < 500 ? 34 : 200);
  const cw = $derived((dims.width - labelW) / Math.max(1, months.length));
  const status = (i: number): RecordStatus => (kind[i] === 'skarp' || kind[i] === 'live' ? 'live' : 'recon');
  /** no state for that month: too few series (or none registered) */
  const few = (s: string | null | undefined) => s === 'för få serier' || s === 'inga registrerade kärnserier';
  const tip = useTooltip();

  function over(e: PointerEvent) {
    const t = e.target as SVGElement | null;
    const i = Number(t?.dataset?.i);
    const j = Number(t?.dataset?.j);
    const r = rows[j];
    if (!tip || !r || !Number.isFinite(i)) return;
    const st = r.state?.[i];
    tip.show(
      {
        title: `${r.code} ${r.name}`,
        rows: [
          ['Månad', periodLabel(months[i], true)],
          ['Index', r.index[i] === null ? 'inget index' : fmt(r.index[i], 2)],
          ['Tillstånd', `${stateStyle(st).glyph} ${stateStyle(st).word}`]
        ],
        note: (status(i) === 'live' ? 'skarp ögonblicksbild' : 'rekonstruerad historik') + (few(st) ? '; utan tillstånd, därför ingen färg' : '')
      },
      e
    );
  }
</script>

<g class="cells" onpointerover={over} onpointerleave={() => tip?.hide()} role="presentation">
  {#each rows as r, j (r.code)}
    <text class="ink2" x="0" y={j * rowHeight + rowHeight / 2 + 4}>{dims.width < 500 ? r.code : `${r.code} ${r.name}`}</text>
    {#each months as m, i (m)}
      {@const v = r.index[i]}
      {@const s = status(i)}
      {@const nostate = v !== null && few(r.state?.[i])}
      <rect
        class="mark cell"
        class:live={s === 'live'}
        class:few={nostate}
        x={labelW + i * cw + 0.5}
        y={j * rowHeight + 1}
        width={Math.max(1, cw - 1)}
        height={Math.max(1, rowHeight - 2)}
        rx="2"
        style:fill={nostate ? 'transparent' : divergingFill(v)}
        stroke={v === null ? 'var(--c-grid)' : nostate ? 'var(--c-axis)' : 'none'}
        opacity={s === 'live' || v === null ? 1 : 0.88}
        data-status={s}
        data-few={nostate ? '' : undefined}
        data-i={i}
        data-j={j}
      />
    {/each}
  {/each}
</g>
{#each months as m, i (m)}
  {#if m.endsWith('-01')}
    <line class="axisline" x1={labelW + i * cw} x2={labelW + i * cw} y1={rows.length * rowHeight} y2={rows.length * rowHeight + 6} />
    <text x={labelW + i * cw} y={rows.length * rowHeight + 18}>{m.slice(0, 4)}</text>
  {/if}
{/each}

<style>
  .cell:hover {
    stroke: var(--c-ink);
    stroke-width: 1.5;
  }
  .live {
    stroke: var(--c-ink);
    stroke-width: 1;
  }
  .few {
    stroke-dasharray: 2 2;
  }
</style>
