<!-- Interval bands 50/80/95: one colour (the model token) with falling opacity, widest first. As a continuous area
     (over time) or as one bar per period (the fan in prototype c). Optional central forecast line. -->
<script lang="ts" generics="T">
  import { area as d3area, line as d3line } from 'd3-shape';

  type Level = '50' | '80' | '95';
  let {
    data,
    x,
    levels,
    center,
    variant = 'area',
    barWidth = 10
  }: {
    data: T[];
    x: (d: T) => number;
    /** lower and upper pixel y per level */
    levels: { level: Level; lo: (d: T) => number; hi: (d: T) => number }[];
    center?: (d: T) => number;
    variant?: 'area' | 'bars';
    barWidth?: number;
  } = $props();

  const order: Level[] = ['95', '80', '50'];
  const sorted = $derived([...levels].sort((a, b) => order.indexOf(a.level) - order.indexOf(b.level)));
  const areaPath = (l: (typeof levels)[number]) => d3area<T>().x(x).y0(l.lo).y1(l.hi)(data) ?? '';
  const centerPath = $derived(center ? (d3line<T>().x(x).y(center)(data) ?? '') : '');
</script>

<g class="band" data-variant={variant}>
  {#if variant === 'area'}
    {#each sorted as l (l.level)}
      <path class="mark" d={areaPath(l)} fill="var(--c-model-{l.level})" data-level={l.level} />
    {/each}
    {#if center}<path class="mark" d={centerPath} fill="none" stroke="var(--c-model)" stroke-width="2" />{/if}
  {:else}
    {#each data as d, i (i)}
      {#each sorted as l (l.level)}
        {@const top = Math.min(l.hi(d), l.lo(d))}
        <rect
          class="mark"
          x={x(d) - barWidth / 2}
          y={top}
          width={barWidth}
          height={Math.max(1, Math.abs(l.lo(d) - l.hi(d)))}
          rx={Math.min(3, barWidth / 3)}
          fill="var(--c-model-{l.level})"
          data-level={l.level}
        />
      {/each}
      {#if center}
        <line class="mark" x1={x(d) - barWidth / 2 - 1} x2={x(d) + barWidth / 2 + 1} y1={center(d)} y2={center(d)} stroke="var(--c-model)" stroke-width="2" />
      {/if}
    {/each}
  {/if}
</g>
