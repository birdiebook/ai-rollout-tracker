<!-- State stripes, branch x month (composed from StripeCell): the whole history in one picture (lesson 1). Labels
     shorten to the code on narrow screens. Goes inside a ChartFrame. -->
<script lang="ts">
  import { fmt, periodLabel } from '../format';
  import { stateStyle } from '../state';
  import StripeCell from './StripeCell.svelte';
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
</script>

{#each rows as r, j (r.code)}
  <text class="ink2" x="0" y={j * rowHeight + rowHeight / 2 + 4}>{dims.width < 500 ? r.code : `${r.code} ${r.name}`}</text>
  {#each months as m, i (m)}
    <StripeCell
      x={labelW + i * cw}
      y={j * rowHeight}
      width={cw}
      height={rowHeight}
      value={r.index[i]}
      status={status(i)}
      tooltip={{
        title: `${r.code} ${r.name}`,
        rows: [
          ['Månad', periodLabel(m, true)],
          ['Index', r.index[i] === null ? 'inget index' : fmt(r.index[i], 2)],
          ['Tillstånd', `${stateStyle(r.state?.[i]).glyph} ${stateStyle(r.state?.[i]).word}`]
        ],
        note: status(i) === 'live' ? 'skarp ögonblicksbild' : 'rekonstruerad historik'
      }}
    />
  {/each}
{/each}
{#each months as m, i (m)}
  {#if m.endsWith('-01')}
    <line class="axisline" x1={labelW + i * cw} x2={labelW + i * cw} y1={rows.length * rowHeight} y2={rows.length * rowHeight + 6} />
    <text x={labelW + i * cw} y={rows.length * rowHeight + 18}>{m.slice(0, 4)}</text>
  {/if}
{/each}
