<!-- All reconciliations in one picture: where each ratio's pace sits in its own history (pipeline percentile, 0–100),
     the dot in the direction colour with glyph and word. Rows in the registered order. Track W10. -->
<script lang="ts">
  import { scaleLinear } from 'd3-scale';
  import { Axis, ChartFrame, DIRECTIONS, fmt, signed, type RecordStatus } from '$lib/design';
  import { levelText, overviewSentence } from './recon';
  import type { ReconView } from './types';

  let { views, status }: { views: ReconView[]; status: RecordStatus } = $props();
  const ROW = 40;
  const height = $derived(views.length * ROW + 40);
  const dirOf = (d: ReconView['direction']) => (d === null || d === undefined ? null : DIRECTIONS[d]);
</script>

<ChartFrame
  id="rc-overview"
  title="Var ligger takten i sin egen historik?"
  description={overviewSentence(views)}
  {height}
  {status}
  headingLevel={2}
  margin={{ top: 22, right: 22, bottom: 24, left: 118 }}
  table={{
    caption: 'Avstämningarna: nivå, takt, percentil och riktning',
    columns: [
      { key: 'n', label: 'Kvot', align: 'left' },
      { key: 'l', label: 'Led', align: 'left' },
      { key: 'p', label: 'Period', align: 'left' },
      { key: 'v', label: 'Nivå' },
      { key: 't', label: 'Takt (log ×100/år)' },
      { key: 'tp', label: 'Percentil takt' },
      { key: 'c', label: 'Förändring i takt' },
      { key: 'cp', label: 'Percentil förändring' },
      { key: 'd', label: 'Riktning', align: 'left' }
    ],
    rows: views.map((r) => ({
      n: r.short,
      l: r.lead ?? '',
      p: r.latest_period ?? '',
      v: levelText(r.level, r.unit),
      t: signed(r.pace, 1),
      tp: fmt(r.pace_percentile, 0),
      c: signed(r.change_in_pace, 1),
      cp: fmt(r.change_percentile, 0),
      d: dirOf(r.direction)?.word ?? 'ingen riktning'
    }))
  }}
>
  {#snippet children(d)}
    {@const x = scaleLinear().domain([0, 100]).range([d.left, d.right])}
    <text class="ink2" x={d.left} y={d.top - 10}>percentil av takten i egen historik</text>
    <rect x={x(25)} y={d.top} width={x(75) - x(25)} height={d.innerHeight} fill="var(--c-mid)" />
    <Axis scale={x} dims={d} tickValues={[0, 25, 50, 75, 100]} format={(v) => fmt(v)} />
    <line x1={x(50)} x2={x(50)} y1={d.top} y2={d.bottom} stroke="var(--c-axis)" stroke-dasharray="3 3" />
    {#each views as r, i (r.key)}
      {@const cy = d.top + ROW * i + ROW / 2}
      {@const dir = dirOf(r.direction)}
      <line x1={d.left} x2={d.right} y1={cy} y2={cy} stroke="var(--c-grid)" />
      <text x={d.left - 10} y={cy - 2} text-anchor="end" class="lbl">{r.short}</text>
      <text x={d.left - 10} y={cy + 11} text-anchor="end" class="ink2 sub">{r.lead}</text>
      {#if r.pace_percentile !== null}
        {@const cx = x(r.pace_percentile)}
        <circle class="mark" {cx} {cy} r="6" fill={dir?.color ?? 'var(--c-muted)'} stroke="var(--c-surface)" stroke-width="2" />
        <text
          x={cx > d.right - 60 ? cx - 11 : cx + 11}
          y={cy + 4}
          text-anchor={cx > d.right - 60 ? 'end' : 'start'}
          class="val">{fmt(r.pace_percentile, 0)}{#if dir}<tspan dx="4" fill={dir.color}>{dir.glyph}</tspan>{/if}</text
        >
      {:else}
        <text x={d.left + 4} y={cy + 4} class="ink2">ingen percentil</text>
      {/if}
    {/each}
  {/snippet}
  {#snippet legend()}
    <ul class="keys" aria-label="Teckenförklaring">
      <li><span class="g" style:color="var(--c-acc)" aria-hidden="true">▲</span>ökar takten</li>
      <li><span class="g" style:color="var(--c-stb)" aria-hidden="true">●</span>oförändrad takt</li>
      <li><span class="g" style:color="var(--c-brk)" aria-hidden="true">▼</span>minskar takten</li>
      <li><span class="sw" aria-hidden="true"></span>mittersta hälften av historiken</li>
    </ul>
  {/snippet}
</ChartFrame>

<style>
  .lbl {
    font-size: 12px;
    font-weight: 600;
    fill: var(--c-ink);
  }
  .sub {
    font-size: 11px;
  }
  .val {
    font-size: 12px;
    font-weight: 600;
    fill: var(--c-ink);
    font-variant-numeric: tabular-nums;
  }
  .keys {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 4px 14px;
    font-size: 12px;
    color: var(--c-ink-2);
  }
  .g {
    margin-right: 4px;
  }
  .sw {
    display: inline-block;
    width: 14px;
    height: 10px;
    margin-right: 5px;
    background: var(--c-mid);
    border: 1px solid var(--c-axis);
    vertical-align: -1px;
  }
</style>
