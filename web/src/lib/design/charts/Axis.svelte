<!-- A recessive axis (1 px, grid optional). Works with d3 continuous scales (ticks) and band scales (domain). -->
<script lang="ts">
  import type { AnyScale, ChartDims } from './types';

  let {
    scale,
    dims,
    orient = 'bottom',
    ticks = 5,
    tickValues,
    format = (v: unknown) => String(v),
    grid = false,
    baseline,
    label
  }: {
    scale: AnyScale;
    dims: ChartDims;
    orient?: 'bottom' | 'left';
    ticks?: number;
    tickValues?: unknown[];
    format?: (v: any) => string;
    grid?: boolean;
    /** value drawn as a stronger line, e.g. 0 for pace (section 4.1) */
    baseline?: number;
    label?: string;
  } = $props();

  const values = $derived(tickValues ?? (scale.ticks ? scale.ticks(ticks) : scale.domain()));
  const offset = $derived(scale.bandwidth ? scale.bandwidth() / 2 : 0);
  const pos = (v: unknown) => (scale(v) ?? 0) + offset;
</script>

<g class="axis axis-{orient}" aria-hidden="true">
  {#if orient === 'bottom'}
    <line class="axisline" x1={dims.left} x2={dims.right} y1={dims.bottom + 0.5} y2={dims.bottom + 0.5} />
    {#each values as v (String(v))}
      {#if grid}<line class="gridline" x1={pos(v)} x2={pos(v)} y1={dims.top} y2={dims.bottom} />{/if}
      <line class="axisline" x1={pos(v)} x2={pos(v)} y1={dims.bottom} y2={dims.bottom + 4} />
      <text x={pos(v)} y={dims.bottom + 16} text-anchor="middle">{format(v)}</text>
    {/each}
    {#if label}<text class="ink2" x={dims.right} y={dims.height - 2} text-anchor="end">{label}</text>{/if}
  {:else}
    {#each values as v (String(v))}
      {#if grid}<line class="gridline" x1={dims.left} x2={dims.right} y1={pos(v)} y2={pos(v)} />{/if}
      <text x={dims.left - 6} y={pos(v) + 4} text-anchor="end">{format(v)}</text>
    {/each}
    {#if label}<text class="ink2" x={dims.left} y={dims.top - 2}>{label}</text>{/if}
  {/if}
  {#if baseline !== undefined && orient === 'left'}
    <line class="axisline baseline" x1={dims.left} x2={dims.right} y1={pos(baseline)} y2={pos(baseline)} />
  {/if}
</g>

<style>
  .baseline {
    stroke: var(--c-ink-2);
  }
</style>
