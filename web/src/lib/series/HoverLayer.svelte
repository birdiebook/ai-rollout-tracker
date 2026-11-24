<!-- Nearest-point hover for a time chart (goes inside a ChartFrame): one transparent hit area over the plot, a rule
     and a ring at the nearest point, and the frame's tooltip. Pointer only; the same numbers are in the table view. -->
<script lang="ts">
  import { useTooltip, type ChartDims } from '$lib/design';
  import type { HoverPoint } from './chart';

  let { dims, points }: { dims: ChartDims; points: HoverPoint[] } = $props();
  const tip = useTooltip();
  let active = $state<HoverPoint | null>(null);

  function nearest(px: number): HoverPoint | null {
    if (points.length === 0) return null;
    let lo = 0;
    let hi = points.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >>> 1;
      if (points[mid].x < px) lo = mid + 1;
      else hi = mid;
    }
    const a = points[Math.max(0, lo - 1)];
    const b = points[lo];
    return Math.abs(a.x - px) <= Math.abs(b.x - px) ? a : b;
  }

  function move(e: PointerEvent) {
    const svg = (e.currentTarget as SVGElement).ownerSVGElement;
    const box = svg?.getBoundingClientRect();
    if (!box || box.width === 0) return;
    const px = ((e.clientX - box.left) / box.width) * dims.width;
    const p = nearest(px);
    active = p;
    if (p && tip) tip.show(p.tip, { clientX: box.left + (p.x / dims.width) * box.width, clientY: box.top + (p.y / dims.height) * box.height });
  }

  function leave() {
    active = null;
    tip?.hide();
  }
</script>

{#if active}
  <line class="rule" x1={active.x} x2={active.x} y1={dims.top} y2={dims.bottom} aria-hidden="true" />
  <circle class="mark" cx={active.x} cy={active.y} r="5" fill="var(--c-surface)" stroke="var(--c-ink)" stroke-width="2" aria-hidden="true" />
{/if}
<rect
  class="hit"
  x={dims.left}
  y={dims.top}
  width={dims.innerWidth}
  height={dims.innerHeight}
  fill="transparent"
  role="presentation"
  onpointermove={move}
  onpointerdown={move}
  onpointerleave={leave}
/>

<style>
  .rule {
    stroke: var(--c-axis);
    stroke-width: 1;
    pointer-events: none;
  }
  .hit {
    cursor: crosshair;
  }
</style>
