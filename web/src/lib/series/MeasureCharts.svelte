<!-- Pace and change in pace over time, as the state engine computed them on the record date (measure_path, the last
     ten years). Pace around a clear zero line; change in pace with the dead band drawn in, and the latest point in
     the direction's colour + glyph + word (section 4.1). Nothing is recomputed here. -->
<script lang="ts">
  import { Axis, ChartFrame, DIRECTIONS, Legend, Line, type RecordStatus } from '$lib/design';
  import HoverLayer from './HoverLayer.svelte';
  import { timeScale, timeTicks, valueScale } from './chart';
  import { periodText, periodTime } from './period';
  import { changeSentence, num, paceSentence, paceSign, snum, tickSigned } from './text';
  import type { Measure, MeasurePath } from './types';

  let {
    path,
    measure,
    from = -Infinity,
    status,
    source,
    license
  }: {
    path: MeasurePath;
    measure: Measure | null;
    /** window start (UTC ms) */
    from?: number;
    status?: RecordStatus;
    source?: string;
    license?: string;
  } = $props();

  type Pt = { p: string; t: number; pace: number | null; change: number | null };
  const pts = $derived(
    path.periods
      .map((p, i) => ({ p, t: periodTime(p), pace: path.pace[i] ?? null, change: path.change[i] ?? null }) as Pt)
      .filter((q) => q.t >= from)
  );
  const paceVals = $derived(pts.map((q) => q.pace).filter((v): v is number => v !== null));
  const changeVals = $derived(pts.map((q) => q.change).filter((v): v is number => v !== null));
  const unit = $derived(measure?.pace_unit ?? '');
  const db = $derived(measure?.deadband ?? null);
  const dir = $derived(measure?.direction ?? null);
  const sign = $derived(paceSign(measure?.method));
  const lastChange = $derived([...pts].reverse().find((q) => q.change !== null));
  const pScale = $derived(Math.max(...paceVals.map(Math.abs), 0));
  const cScale = $derived(Math.max(...changeVals.map(Math.abs), db ?? 0, 0));
  const margin = { top: 18, right: 14, bottom: 26, left: 52 };
  const tableOf = (k: 'pace' | 'change', label: string, ref: number) => ({
    caption: `${label} per period (${unit}), nyast först.`,
    columns: [
      { key: 'p', label: 'Period' },
      { key: 'x', label }
    ],
    rows: [...pts].reverse().map((q) => ({ p: periodText(q.p), x: snum(q[k], ref) }))
  });
</script>

<div class="pair">
  <ChartFrame id="pace" title="Takt" description={paceSentence(measure)} height={220} {margin} {status} {source} {license} table={tableOf('pace', 'Takt', pScale)}>
    {#snippet children(d)}
      {#if pts.length > 0}
        {@const x = timeScale(pts[0].t, pts.at(-1)!.t, d)}
        {@const y = valueScale(paceVals, d, { zero: true }).scale}
        {@const tt = timeTicks(x, d)}
        <Axis scale={y} dims={d} orient="left" ticks={4} format={(v) => tickSigned(v, pScale)} grid baseline={0} label={unit} />
        <Axis scale={x} dims={d} tickValues={tt.values} format={tt.format} />
        <Line data={pts} x={(q) => x(q.t)} y={(q) => y(q.pace ?? 0)} defined={(q) => q.pace !== null} endDot />
        <HoverLayer
          dims={d}
          points={pts.filter((q) => q.pace !== null).map((q) => ({ x: x(q.t), y: y(q.pace ?? 0), tip: { title: periodText(q.p, true), rows: [['Takt', snum(q.pace, pScale)]], note: unit } }))}
        />
      {/if}
    {/snippet}
  </ChartFrame>

  <ChartFrame id="change" title="Förändring i takt" description={changeSentence(measure)} height={220} {margin} {status} {source} {license} table={tableOf('change', 'Förändring i takt', cScale)}>
    {#snippet children(d)}
      {#if pts.length > 0}
        {@const x = timeScale(pts[0].t, pts.at(-1)!.t, d)}
        {@const y = valueScale(changeVals, d, { zero: true, pad: db !== null ? [-db * 1.6, db * 1.6] : [] }).scale}
        {@const tt = timeTicks(x, d)}
        {#if db !== null && db > 0}
          <rect class="deadband" x={d.left} width={d.innerWidth} y={y(db)} height={Math.max(1, y(-db) - y(db))} aria-hidden="true" />
        {/if}
        <Axis scale={y} dims={d} orient="left" ticks={4} format={(v) => tickSigned(v, cScale)} grid baseline={0} label={unit} />
        <Axis scale={x} dims={d} tickValues={tt.values} format={tt.format} />
        <Line data={pts} x={(q) => x(q.t)} y={(q) => y(q.change ?? 0)} defined={(q) => q.change !== null} />
        {#if lastChange && dir !== null}
          {@const cx = x(lastChange.t)}
          {@const cy = y(lastChange.change ?? 0)}
          <circle class="mark" {cx} {cy} r="5.5" fill={DIRECTIONS[dir].color} stroke="var(--c-surface)" stroke-width="2" />
          {#if d.innerWidth >= 420}
            <text class="ink" x={d.right} y={d.top - 6} text-anchor="end">senast: {DIRECTIONS[dir].glyph} {DIRECTIONS[dir].word}</text>
          {/if}
        {/if}
        <HoverLayer
          dims={d}
          points={pts
            .filter((q) => q.change !== null)
            .map((q) => ({
              x: x(q.t),
              y: y(q.change ?? 0),
              tip: {
                title: periodText(q.p, true),
                rows: [['Förändring i takt', snum(q.change, cScale)]],
                note: db !== null ? `dödband ±${num(db, db)} (vid postens datum)` : unit
              }
            }))}
        />
      {/if}
    {/snippet}
    {#snippet legend()}
      <Legend
        items={[
          ...(db !== null && db > 0 ? [{ label: `dödband ±${num(db, db)} (vid postens datum)`, fill: 'var(--c-grid)' }] : []),
          ...(dir !== null ? [{ label: `senaste: ${DIRECTIONS[dir].glyph} ${DIRECTIONS[dir].word}`, fill: DIRECTIONS[dir].color }] : [])
        ]}
      />
    {/snippet}
  </ChartFrame>
</div>
{#if sign < 0}
  <p class="note">Takten är en {measure?.method === 'doubling' ? 'fördubblingstid' : 'halveringstid'} i månader: en kortare tid betyder högre takt, så en negativ förändring räknas som att takten ökar.</p>
{/if}

<style>
  .pair {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 24px;
  }
  @media (min-width: 861px) {
    .pair {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
  .deadband {
    fill: var(--c-grid);
    opacity: 0.75;
  }
</style>
