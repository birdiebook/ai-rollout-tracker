<!-- Marks of Q1 (inside NowDots' ChartFrame, which provides the tooltip). -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { fmt, stateStyle, useTooltip, type ChartDims } from '$lib/design';
  import type { StartData } from './model';

  let { d, start, rowH }: { d: ChartDims; start: StartData; rowH: number } = $props();
  const tip = useTooltip();
  const x = (v: number) => d.left + v * d.innerWidth;
  const H = $derived(start.branches.length * rowH);
</script>

<rect x={x(start.thresholds.low)} y={d.top} width={x(start.thresholds.high) - x(start.thresholds.low)} height={H} fill="var(--c-mid)" rx="3" />
{#each [0, start.thresholds.low, 0.5, start.thresholds.high, 1] as t (t)}
  <line class="gridline" x1={x(t)} x2={x(t)} y1={d.top} y2={d.top + H} />
  <text x={x(t)} y={d.top + H + 14} text-anchor="middle">{fmt(t, t === 0 || t === 1 ? 0 : t === 0.5 ? 1 : 2)}</text>
{/each}
<text class="ink2" x={x(start.thresholds.low / 2)} y={d.top + H + 28} text-anchor="middle">bromsar in</text>
<text class="ink2" x={x(0.5)} y={d.top + H + 28} text-anchor="middle">stabil</text>
<text class="ink2" x={x((1 + start.thresholds.high) / 2)} y={d.top + H + 28} text-anchor="middle">accelererar</text>
{#each start.branches as b, i (b.code)}
  {@const cy = d.top + i * rowH + rowH / 2}
  {@const st = stateStyle(b.state)}
  {@const pv = b.prev?.index ?? null}
  <text class="ink2" x="0" y={cy + 4}>{b.code}</text>
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <g
    class="row"
    role="presentation"
    data-branch={b.code}
    onclick={() => goto(resolve('/gren/[id]', { id: b.code }))}
    onpointerenter={(e) =>
      tip?.show(
        {
          title: `${b.code} ${b.name}`,
          rows: [
            ['Tillstånd', `${st.glyph} ${b.state}`],
            ['Index', b.index === null ? 'inget index' : fmt(b.index, 2)],
            ['Förra månaden', pv === null ? '–' : fmt(pv, 2)],
            ...(b.n_families !== null ? [['Källfamiljer', String(b.n_families)] as [string, string]] : []),
            ['Serier ▲ ● ▼', `${b.n_up} · ${b.n_neutral} · ${b.n_down}`],
            ...(b.rule_version === 'v2' && b.index_v1 !== null ? [['Regel v1', `${fmt(b.index_v1, 2)} ${b.state_v1 ?? ''}`.trim()] as [string, string]] : [])
          ],
          note: b.n_withheld_counted ? `varav ${b.n_withheld_counted} inhållna av licensskäl · klicka för grenen` : 'klicka för grenen'
        },
        e
      )}
    onpointerleave={() => tip?.hide()}
  >
    <rect x={d.left - 30} y={cy - rowH / 2} width={d.innerWidth + 30} height={rowH} fill="transparent" />
    {#if b.index === null}
      <text x={x(0.5)} y={cy + 4} text-anchor="middle">inget index</text>
    {:else}
      {#if pv !== null && Math.abs(pv - b.index) > 0.005}
        <line class="mark" x1={x(pv)} x2={x(b.index)} y1={cy} y2={cy} stroke="var(--c-ink-2)" stroke-width="1.5" />
        <circle class="mark" cx={x(pv)} {cy} r="3.5" fill="var(--c-surface)" stroke="var(--c-ink-2)" stroke-width="1.5" />
      {/if}
      {#if b.rule_version === 'v2' && b.index_v1 !== null && Math.abs(b.index_v1 - b.index) > 0.005}
        <line class="v1" x1={x(b.index_v1)} x2={x(b.index_v1)} y1={cy - 7} y2={cy + 7} stroke="var(--c-ink-2)" stroke-width="2" data-v1={b.index_v1} />
      {/if}
      <circle
        class="mark"
        cx={x(b.index)}
        {cy}
        r="6.5"
        fill={st.key === 'none' ? 'var(--c-surface)' : st.color}
        stroke={st.key === 'none' ? 'var(--c-muted)' : 'var(--c-surface)'}
        stroke-width="2"
        stroke-dasharray={st.key === 'none' ? '3 2' : undefined}
      />
    {/if}
  </g>
{/each}

<style>
  .row {
    cursor: pointer;
  }
  .row:hover rect {
    fill: var(--c-grid);
    fill-opacity: 0.35;
  }
</style>
