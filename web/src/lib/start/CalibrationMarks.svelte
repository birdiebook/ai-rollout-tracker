<!-- Marks of the calibration row (Q2): per level the coverage (dot) against the nominal level (tick) and the
     binomial band (grey), on 0–100 %. -->
<script lang="ts">
  import { fmt, useTooltip, type ChartDims } from '$lib/design';
  import type { CalibrationView } from './model';

  let { d, c, rowH }: { d: ChartDims; c: CalibrationView; rowH: number } = $props();
  const tip = useTooltip();
  const x = (v: number) => d.left + v * d.innerWidth;
  const p = (v: number | null) => (v === null ? '–' : `${fmt(v * 100, 0)} %`);
</script>

{#each c.rows as r, i (r.level)}
  {@const cy = d.top + i * rowH + rowH / 2}
  <text class="ink2" x="0" y={cy + 4}>{r.level} %</text>
  <line class="gridline" x1={x(0)} x2={x(1)} y1={cy} y2={cy} />
  {#if r.band}<rect x={x(r.band[0])} y={cy - 5} width={Math.max(2, x(r.band[1]) - x(r.band[0]))} height="10" rx="3" fill="var(--c-mid)" stroke="var(--c-axis)" stroke-width="0.5" />{/if}
  <line x1={x(Number(r.level) / 100)} x2={x(Number(r.level) / 100)} y1={cy - 7} y2={cy + 7} stroke="var(--c-ink-2)" stroke-width="1.5" />
  {#if r.coverage !== null}
    <circle
      class="mark"
      cx={x(r.coverage)}
      {cy}
      r="5"
      fill="var(--c-model)"
      stroke="var(--c-surface)"
      stroke-width="2"
      role="presentation"
      onpointerenter={(e) =>
        tip?.show(
          {
            title: `${r.level} %-intervallet`,
            rows: [
              ['Täckning', p(r.coverage)],
              ['Slumpband', r.band ? `${p(r.band[0])}–${p(r.band[1])}` : '–'],
              ['Prognoser', String(c.n)]
            ],
            note: 'backtest, inte skarpa prognoser'
          },
          e
        )}
      onpointerleave={() => tip?.hide()}
    />
  {/if}
  <text class="ink" x={d.right + 6} y={cy + 4}>{p(r.coverage)}</text>
{/each}
<text x={x(0)} y={d.bottom + 14} text-anchor="middle">0</text>
<text x={x(0.5)} y={d.bottom + 14} text-anchor="middle">50</text>
<text x={x(1)} y={d.bottom + 14} text-anchor="middle">100 %</text>
