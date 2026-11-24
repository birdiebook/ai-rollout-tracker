<!-- Level over time (section 4.1: line, log scale for exponential quantities), any frequency. Neutral ink: colour
     means direction only. The tooltip tells when a period has been revised (versions summary, no fetch). -->
<script lang="ts">
  import { Axis, ChartFrame, Line, type RecordStatus } from '$lib/design';
  import HoverLayer from './HoverLayer.svelte';
  import { logTicks, timeScale, timeTicks, valueScale, type TimePoint } from './chart';
  import { periodText } from './period';
  import { logTickNum, num, levelSentence, tickNum } from './text';

  let {
    id = 'level',
    label,
    unit,
    points,
    totalCount,
    log = false,
    status,
    source,
    license,
    revised
  }: {
    id?: string;
    label: string;
    unit: string;
    points: TimePoint[];
    /** number of levels in the whole series (the table caption says when it shows fewer) */
    totalCount: number;
    log?: boolean;
    status?: RecordStatus;
    source?: string;
    license?: string;
    /** period -> { first published value, number of versions } for revised periods */
    revised?: Map<string, { first: number; n: number }>;
  } = $props();

  const TABLE_MAX = 600;
  const vals = $derived(points.map((q) => q.v));
  const scaleRef = $derived(Math.max(...vals.map(Math.abs), 0));
  const leftMargin = $derived(Math.min(72, 14 + 6.6 * Math.max(3, num(scaleRef, scaleRef).length)));
  const tableRows = $derived(points.slice(-TABLE_MAX).reverse());
  const showRev = $derived(!!revised && revised.size > 0);
</script>

<ChartFrame
  {id}
  title="Nivå"
  description={levelSentence(label, unit, points.at(-1) ? { p: points.at(-1)!.p, v: points.at(-1)!.v } : undefined, points[0]?.p)}
  height={260}
  margin={{ top: 18, right: 14, bottom: 26, left: leftMargin }}
  {status}
  {source}
  {license}
  table={{
    caption:
      tableRows.length < totalCount
        ? `De ${tableRows.length} senaste av ${totalCount} värden, nyast först. Alla finns i CSV-filen.`
        : `${totalCount} värden, nyast först. Enhet: ${unit}.`,
    columns: [
      { key: 'p', label: 'Period' },
      { key: 'v', label: unit || 'Värde', align: 'right' },
      ...(showRev ? [{ key: 'r', label: 'Versioner', align: 'right' as const }] : [])
    ],
    rows: tableRows.map((q) => ({ p: periodText(q.p), v: num(q.v, scaleRef), r: revised?.get(q.p)?.n ?? 1 }))
  }}
>
  {#snippet children(d)}
    {#if points.length > 0}
      {@const x = timeScale(points[0].t, points.at(-1)!.t, d)}
      {@const ys = valueScale(vals, d, { log })}
      {@const y = ys.scale}
      {@const tt = timeTicks(x, d)}
      {@const dom = y.domain()}
      <Axis
        scale={y}
        dims={d}
        orient="left"
        ticks={4}
        tickValues={ys.log ? logTicks(dom[0], dom[1]) : undefined}
        format={(v) => (ys.log ? logTickNum(v) : tickNum(v, scaleRef))}
        grid
        label={ys.log ? `${unit} (logaritmisk skala)` : unit}
      />
      <Axis scale={x} dims={d} tickValues={tt.values} format={tt.format} />
      <Line data={points} x={(q) => x(q.t)} y={(q) => y(q.v)} endDot={points.length > 0} width={points.length > 800 ? 1.5 : 2} />
      {#if points.length === 1}
        <circle class="mark" cx={x(points[0].t)} cy={y(points[0].v)} r="5" fill="var(--c-ink)" stroke="var(--c-surface)" stroke-width="2" />
      {/if}
      <HoverLayer
        dims={d}
        points={points.map((q) => {
          const r = revised?.get(q.p);
          return {
            x: x(q.t),
            y: y(q.v),
            tip: {
              title: periodText(q.p, true),
              rows: [
                ['Värde', `${num(q.v, scaleRef)}`],
                ...(r ? ([['Först publicerat', num(r.first, scaleRef)], ['Versioner', String(r.n)]] as [string, string][]) : [])
              ],
              note: unit
            }
          };
        })}
      />
    {/if}
  {/snippet}
</ChartFrame>
