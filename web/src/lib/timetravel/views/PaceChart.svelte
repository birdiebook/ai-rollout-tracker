<!-- The record's pace for a series at every month end known on the day (measure_history, the pipeline's numbers,
     never recomputed): one dot per month in its direction's colour, reconstructed months dashed. -->
<script lang="ts">
  import { scalePoint } from 'd3-scale';
  import { Axis, ChartFrame, DIRECTIONS, Line, dateLabel, fmt, periodLabel, signed, type RecordStatus } from '$lib/design';
  import HoverLayer from '$lib/series/HoverLayer.svelte';
  import { valueScale } from '$lib/series/chart';
  import type { SeriesOn } from '../gate';

  let { s, months, status, id = 'tt-pace', compact = false }: { s: SeriesOn; months: string[]; status: RecordStatus; id?: string; compact?: boolean } = $props();

  const h = $derived(s.history);
  const rows = $derived(
    h ? h.months.map((m, i) => ({ m, kind: h.kind[i], pace: h.pace?.[i] ?? null, dir: h.direction?.[i] ?? null, counted: h.counted[i], known: h.known[i] })) : []
  );
  const shown = $derived(rows.filter((r) => r.pace !== null));
  const unit = 'takt';
  const sentence = $derived(
    shown.length
      ? `Postens takt vid ${shown.length} månadsslut fram till ${periodLabel(shown.at(-1)!.m, true)}: ${signed(shown.at(-1)!.pace, 1)}.`
      : `Serien mättes inte i posten vid något månadsslut fram till ${dateLabel(s.day)}.`
  );
</script>

<ChartFrame
  {id}
  title="Takt enligt posten vid varje månadsslut"
  description={sentence}
  height={compact ? 120 : 200}
  {status}
  headingLevel={compact ? 4 : 2}
  margin={{ top: 10, right: 10, bottom: 22, left: 40 }}
  table={{
    caption: `Postens mått per månadsslut, kända den ${s.day}`,
    columns: [
      { key: 'm', label: 'Månad' },
      { key: 'p', label: 'Takt' },
      { key: 'd', label: 'Riktning', align: 'left' },
      { key: 'c', label: 'Räknad', align: 'left' },
      { key: 'k', label: 'Underlag', align: 'left' }
    ],
    rows: [...rows].reverse().map((r) => ({ m: periodLabel(r.m), p: signed(r.pace, 1), d: r.dir === null ? '–' : `${DIRECTIONS[r.dir].glyph} ${DIRECTIONS[r.dir].word}`, c: r.counted ? 'ja' : 'nej', k: r.kind }))
  }}
>
  {#snippet children(d)}
    {@const x = scalePoint<string>().domain(months).range([d.left, d.right]).padding(0.5)}
    {@const ys = valueScale(shown.map((r) => r.pace!), d, { zero: true })}
    {@const y = ys.scale}
    {@const xm = (m: string) => x(m) ?? 0}
    {@const years = months.filter((m) => m.endsWith('-01'))}
    {@const step = months.length ? (d.right - d.left) / months.length : 0}
    {@const edge = shown.length ? xm(rows.at(-1)!.m) + step / 2 : d.left}
    {#if edge < d.right}<rect class="later" x={edge} y={d.top} width={d.right - edge} height={d.bottom - d.top} />{/if}
    <Axis scale={y} dims={d} orient="left" ticks={compact ? 2 : 4} format={(v) => fmt(v, 0)} grid baseline={0} label={compact ? undefined : unit} />
    <Axis scale={x} dims={d} tickValues={years.length ? years : months.slice(0, 1)} format={(v) => (String(v).endsWith('-01') ? String(v).slice(0, 4) : periodLabel(String(v)))} />
    {#if shown.length}
      <Line data={shown} x={(r) => xm(r.m)} y={(r) => y(r.pace!)} dashed={shown.every((r) => r.kind !== 'skarp')} width={1.5} color="var(--c-ink-2)" />
      {#each shown as r (r.m)}
        <circle class="mark" cx={xm(r.m)} cy={y(r.pace!)} r={r === shown.at(-1) ? 5 : 3} fill={r.dir === null ? 'var(--c-surface)' : DIRECTIONS[r.dir].color} stroke={r === shown.at(-1) ? 'var(--c-ink)' : 'var(--c-surface)'} stroke-width="1.5" data-known={r.known} />
      {/each}
      <HoverLayer
        dims={d}
        points={shown.map((r) => ({
          x: xm(r.m),
          y: y(r.pace!),
          tip: {
            title: periodLabel(r.m, true),
            rows: [
              ['Takt', signed(r.pace, 1)],
              ['Riktning', r.dir === null ? '–' : `${DIRECTIONS[r.dir].glyph} ${DIRECTIONS[r.dir].word}`],
              ['Räknad', r.counted ? 'ja' : 'nej']
            ],
            note: r.kind === 'skarp' ? 'skarp ögonblicksbild' : 'rekonstruerad historik'
          }
        }))}
      />
    {/if}
  {/snippet}
</ChartFrame>

<style>
  .later {
    fill: var(--c-grid);
    opacity: 0.55;
  }
</style>
