<!-- W13: one series' record value per month end up to the story month: the percentile of the change in pace (K5),
     of the pace (K6) with the registered extreme zones (≤ 5, ≥ 95) shaded, or the pace itself (K4). The story month
     is the coloured dot (colour = direction only). Data: the card's track (Python, the record of each month). -->
<script lang="ts">
  import { scaleLinear, scalePoint } from 'd3-scale';
  import { Axis, ChartFrame, DIRECTIONS, Line, fmt, periodLabel, signed, type RecordStatus } from '$lib/design';
  import type { StoryTrack } from '$lib/data';

  let {
    id,
    track,
    month,
    direction,
    unit,
    status,
    low = 5,
    high = 95
  }: {
    id: string;
    track: StoryTrack;
    month: string;
    direction: -1 | 0 | 1 | null;
    unit: string | null;
    status: RecordStatus;
    low?: number;
    high?: number;
  } = $props();

  const pctMode = $derived(track.field !== 'pace');
  const pts = $derived(track.months.map((m, i) => ({ m, v: track.values[i] })));
  const vals = $derived(pts.map((p) => p.v).filter((v): v is number => v !== null));
  const yDomain = $derived.by((): [number, number] => {
    if (pctMode) return [0, 100];
    if (!vals.length) return [-1, 1];
    const lo = Math.min(0, ...vals);
    const hi = Math.max(0, ...vals);
    return lo === hi ? [lo - 1, hi + 1] : [lo, hi];
  });
  const last = $derived(pts.find((p) => p.m === month) ?? pts.at(-1));
  const color = $derived(direction === null ? 'var(--c-ink)' : DIRECTIONS[direction].color);
  const what = $derived(
    track.field === 'change_percentile' ? 'Percentil för förändring i takt' : track.field === 'pace_percentile' ? 'Percentil för takt' : 'Takt'
  );
  const valText = (v: number | null) => (v === null ? '–' : pctMode ? fmt(v, 1) : signed(v, 1));
  const description = $derived(
    `${what} enligt posten varje månadsslut, ${periodLabel(track.months[0], true)}–${periodLabel(month, true)}. ` +
      (last ? `I ${periodLabel(last.m, true)}: ${valText(last.v)}${pctMode ? ` av 100. Zonerna ≤ ${low} och ≥ ${high} är skuggade.` : ` ${unit ?? ''}.`}` : '')
  );
  const table = $derived({
    caption: `${what} per månadsslut`,
    columns: [
      { key: 'm', label: 'Månad', align: 'left' as const },
      { key: 'v', label: pctMode ? 'Percentil' : `Takt (${unit ?? ''})` }
    ],
    rows: [...pts].reverse().map((p) => ({ m: periodLabel(p.m, true), v: valText(p.v) }))
  });
</script>

<ChartFrame {id} title={what} {description} height={200} margin={{ top: 12, right: 16, bottom: 26, left: 40 }} {status} {table}>
  {#snippet children(d)}
    {@const x = scalePoint<string>().domain(track.months).range([d.left, d.right]).padding(0.3)}
    {@const y = scaleLinear().domain(yDomain).range([d.bottom, d.top]).nice()}
    {#if pctMode}
      <rect class="zone" x={d.left} width={d.innerWidth} y={y(100)} height={y(high) - y(100)} />
      <rect class="zone" x={d.left} width={d.innerWidth} y={y(low)} height={y(0) - y(low)} />
      <line class="edge" x1={d.left} x2={d.right} y1={y(high)} y2={y(high)} />
      <line class="edge" x1={d.left} x2={d.right} y1={y(low)} y2={y(low)} />
      <line class="mid" x1={d.left} x2={d.right} y1={y(50)} y2={y(50)} />
    {/if}
    <Axis scale={y} dims={d} orient="left" tickValues={pctMode ? [low, 50, high] : undefined} ticks={4} format={(v) => fmt(v, 0)} baseline={pctMode ? undefined : 0} />
    <Axis
      scale={x}
      dims={d}
      tickValues={track.months.filter((m, i) => m.endsWith('-01') || i === 0 || m === month)}
      format={(m) => (m === month ? periodLabel(m) : m.endsWith('-01') ? m.slice(0, 4) : periodLabel(m))}
    />
    <Line data={pts} x={(p) => x(p.m) ?? 0} y={(p) => y(p.v ?? 0)} defined={(p) => p.v !== null} color="var(--c-ink-2)" width={1.6} />
    {#if last && last.v !== null}
      <circle class="mark" cx={x(last.m) ?? 0} cy={y(last.v)} r="5.5" fill={color} stroke="var(--c-surface)" stroke-width="1.5" data-month={last.m} />
      <text class="lab" x={(x(last.m) ?? 0) - 8} y={y(last.v) + (last.v > 50 || !pctMode ? 16 : -10)} text-anchor="end">{valText(last.v)}</text>
    {/if}
  {/snippet}
</ChartFrame>

<style>
  .zone {
    fill: var(--c-mid);
  }
  .edge {
    stroke: var(--c-axis);
    stroke-dasharray: 3 3;
  }
  .mid {
    stroke: var(--c-grid);
  }
  .lab {
    font-size: var(--fs-chart, 12px);
    fill: var(--c-ink);
    font-variant-numeric: tabular-nums;
  }
</style>
