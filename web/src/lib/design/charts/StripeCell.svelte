<!-- One cell of the state stripes (branch x month, Hawkins): diverging fill from the diffusion index, no index =
     empty cell with a grid border. Reconstructed months are drawn at lower saturation, live ones solid (P9). -->
<script lang="ts">
  import { divergingFill } from '../state';
  import { useTooltip, type TooltipContent } from './tooltip.svelte';
  import type { RecordStatus } from './types';

  let {
    x,
    y,
    width,
    height,
    value,
    status = 'recon',
    tooltip
  }: {
    x: number;
    y: number;
    width: number;
    height: number;
    value: number | null;
    status?: RecordStatus;
    tooltip?: TooltipContent;
  } = $props();

  const tip = useTooltip();
</script>

<rect
  class="mark cell"
  class:live={status === 'live'}
  x={x + 0.5}
  y={y + 1}
  width={Math.max(1, width - 1)}
  height={Math.max(1, height - 2)}
  rx="2"
  style:fill={divergingFill(value)}
  stroke={value === null ? 'var(--c-grid)' : 'none'}
  opacity={status === 'live' || value === null ? 1 : 0.88}
  data-status={status}
  role="presentation"
  onpointerenter={(e) => tooltip && tip?.show(tooltip, e)}
  onpointerleave={() => tip?.hide()}
/>

<style>
  .cell:hover {
    stroke: var(--c-ink);
    stroke-width: 1.5;
  }
  .live {
    stroke: var(--c-ink);
    stroke-width: 1;
  }
</style>
