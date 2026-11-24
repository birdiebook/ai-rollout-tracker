<!-- Quantile dot plot: n equally likely outcomes as dots (frequency format, P4). Radius from the distribution's
     middle (lesson 5). Optional outcome as a vertical ink line with a direct label. -->
<script lang="ts">
  import { binDots, dotRadius } from './quantiles';
  import { useTooltip } from './tooltip.svelte';
  import type { ChartDims } from './types';

  let {
    values,
    x,
    dims,
    outcome,
    outcomeLabel = 'utfall',
    format = (v: number) => String(v)
  }: {
    values: number[];
    x: (v: number) => number;
    dims: ChartDims;
    outcome?: number;
    outcomeLabel?: string;
    format?: (v: number) => string;
  } = $props();

  const tip = useTooltip();
  const r = $derived(dotRadius(values.map(x)));
  const dots = $derived(binDots(values, x, dims.left, r));
  const share = $derived(Math.round(100 / values.length));
  const below = $derived(outcome === undefined ? 0 : values.filter((v) => v < outcome).length);
  const flip = $derived(outcome !== undefined && x(outcome) > dims.right - 110);
</script>

<g class="qdots">
  {#each dots as d, i (i)}
    <circle
      class="mark dot"
      cx={d.cx}
      cy={dims.bottom - r - d.k * r * 2.1}
      {r}
      fill="var(--c-model)"
      stroke="var(--c-surface)"
      stroke-width="1"
      role="presentation"
      onpointerenter={(e) =>
        tip?.show({ title: `Utfall ${i + 1} av ${values.length}`, rows: [['Värde', format(d.value)], ['Sannolikhet', `${share} %`]] }, e)}
      onpointerleave={() => tip?.hide()}
    />
  {/each}
  {#if outcome !== undefined}
    <line class="mark" x1={x(outcome)} x2={x(outcome)} y1={dims.top} y2={dims.bottom + 4} stroke="var(--c-ink)" stroke-width="2" />
    <text class="ink" x={x(outcome) + (flip ? -6 : 6)} y={dims.top + 10} text-anchor={flip ? 'end' : 'start'}>
      {outcomeLabel} {format(outcome)} · {below} av {values.length} under
    </text>
  {/if}
</g>
