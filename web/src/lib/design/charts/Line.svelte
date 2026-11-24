<!-- A 2 px line (round join/cap) with an optional end dot and direct end label. Neutral ink by default: in small
     multiples the series identity is the heading, colour means direction only (lesson 8). -->
<script lang="ts" generics="T">
  import { line as d3line } from 'd3-shape';

  let {
    data,
    x,
    y,
    defined = () => true,
    color = 'var(--c-ink)',
    width = 2,
    dashed = false,
    opacity = 1,
    endDot = false,
    endLabel
  }: {
    data: T[];
    x: (d: T) => number;
    y: (d: T) => number;
    defined?: (d: T) => boolean;
    color?: string;
    width?: number;
    dashed?: boolean;
    opacity?: number;
    endDot?: boolean;
    endLabel?: string;
  } = $props();

  const path = $derived(d3line<T>().x(x).y(y).defined(defined)(data) ?? '');
  const last = $derived([...data].reverse().find(defined));
</script>

<path
  class="mark line"
  d={path}
  fill="none"
  stroke={color}
  stroke-width={width}
  stroke-linejoin="round"
  stroke-linecap="round"
  stroke-dasharray={dashed ? '4 4' : undefined}
  {opacity}
/>
{#if last && endDot}
  <circle class="mark" cx={x(last)} cy={y(last)} r="4" fill={color} stroke="var(--c-surface)" stroke-width="2" />
{/if}
{#if last && endLabel}
  <text class="ink2" x={x(last) + 8} y={y(last) + 4}>{endLabel}</text>
{/if}
