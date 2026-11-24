<!-- A series' levels exactly as known on the day (W9): the latest version of every period with known_from <= day,
     nothing else (today's version is in the revision view below, labelled). The axis runs to the day itself, so the
     publication lag shows as the gap after the last known period. Table: period, value and known_from. -->
<script lang="ts">
  import { Axis, ChartFrame, Line, dateLabel, type RecordStatus } from '$lib/design';
  import HoverLayer from '$lib/series/HoverLayer.svelte';
  import { logTicks, timeScale, timeTicks, valueScale } from '$lib/series/chart';
  import { periodText, periodTime } from '$lib/series/period';
  import { logTickNum, num, tickNum } from '$lib/series/text';
  import type { SeriesOn } from '../gate';
  import { dayToMs } from '../url';

  let { s, status, log = false }: { s: SeriesOn; status: RecordStatus; log?: boolean } = $props();

  const pts = $derived(s.levels.map((l) => ({ ...l, t: periodTime(l.period) })).filter((q) => Number.isFinite(q.t)));
  const vals = $derived(pts.map((q) => q.value));
  const scaleRef = $derived(Math.max(0, ...vals.map(Math.abs)));
  const lm = $derived(Math.min(72, 14 + 6.6 * Math.max(3, num(scaleRef, scaleRef).length)));
  const last = $derived(pts.at(-1) ?? null);
  const sentence = $derived(
    last
      ? `Den ${dateLabel(s.day)} var ${pts.length} perioder kända, den senaste ${periodText(last.period)} (${num(last.value, scaleRef)} ${s.meta.unit}, känd från ${dateLabel(last.known)}).`
      : `Inget värde var publicerat den ${dateLabel(s.day)}.`
  );
  const table = $derived({
    caption: `${s.meta.label}: värden kända den ${s.day}, nyast först`,
    columns: [
      { key: 'p', label: 'Period' },
      { key: 'v', label: 'Värde' },
      { key: 'k', label: 'Känd från', align: 'left' as const }
    ],
    rows: [...pts].reverse().map((q) => ({ p: periodText(q.period), v: num(q.value, scaleRef), k: q.known }))
  });
</script>

<ChartFrame id="tt-level" title="Nivå som den var känd" description={sentence} height={260} {status} margin={{ top: 16, right: 14, bottom: 26, left: lm }} source={s.meta.source} license={s.meta.license?.short} {table} headingLevel={2}>
  {#snippet children(d)}
    {#if pts.length}
      {@const x = timeScale(pts[0].t, Math.max(pts.at(-1)!.t, dayToMs(s.day)), d)}
      {@const ys = valueScale(vals, d, { log })}
      {@const y = ys.scale}
      {@const tt = timeTicks(x, d)}
      {@const xd = x(dayToMs(s.day))}
      <Axis
        scale={y}
        dims={d}
        orient="left"
        ticks={4}
        tickValues={ys.log ? logTicks(y.domain()[0], y.domain()[1]) : undefined}
        format={(v) => (ys.log ? logTickNum(v) : tickNum(v, scaleRef))}
        grid
        label={ys.log ? `${s.meta.unit} (logaritmisk skala)` : s.meta.unit}
      />
      <Axis scale={x} dims={d} tickValues={tt.values} format={tt.format} />
      <Line data={pts} x={(q) => x(q.t)} y={(q) => y(q.value)} width={2.5} />
      {#if pts.length === 1}<circle class="mark" cx={x(pts[0].t)} cy={y(pts[0].value)} r="4" fill="var(--c-ink)" />{/if}
      <line class="dayline" x1={xd} x2={xd} y1={d.top} y2={d.bottom} />
      <text class="ink2" x={Math.min(xd, d.right) - 4} y={d.bottom - 6} text-anchor="end">{dateLabel(s.day)}</text>
      <g data-known={s.versions?.last_known ?? ''}>
        <HoverLayer
          dims={d}
          points={pts.map((q) => ({ x: x(q.t), y: y(q.value), tip: { title: periodText(q.period, true), rows: [['Värde', num(q.value, scaleRef)], ['Känd från', dateLabel(q.known)]], note: s.meta.unit } }))}
        />
      </g>
    {/if}
  {/snippet}
</ChartFrame>

<style>
  .dayline {
    stroke: var(--c-ink);
    stroke-width: 1;
    stroke-dasharray: 2 3;
  }
</style>
