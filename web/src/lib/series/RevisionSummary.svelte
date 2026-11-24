<!-- Revisions without any fetch (prerendered from the page's versions summary): the size of each period's revision
     (today's value against the first published), with both values in the tooltip and the table. Neutral ink and grey: a revision up or down is not a
     direction of pace. -->
<script lang="ts">
  import { Axis, ChartFrame, fmt } from '$lib/design';
  import HoverLayer from './HoverLayer.svelte';
  import { timeScale, timeTicks, valueScale } from './chart';
  import { periodText, periodTime } from './period';
  import { num, snum, tickSigned } from './text';
  import { revisionSize } from './versions';
  import type { RevisionColumns } from './page';

  let {
    rev,
    unit,
    relative,
    from = -Infinity,
    source,
    license,
    freqNote
  }: {
    rev: RevisionColumns;
    unit: string;
    /** revisions in % (log difference ×100) instead of the unit */
    relative: boolean;
    from?: number;
    source?: string;
    license?: string;
    /** e.g. "månadsmedel av dagliga värden" when versions are stored at a coarser frequency */
    freqNote?: string;
  } = $props();

  const TABLE_MAX = 240;
  const rows = $derived(
    rev.periods
      .map((p, i) => ({ p, t: periodTime(p), first: rev.first[i], latest: rev.latest[i], n: rev.n[i], known: rev.first_known[i] }))
      .filter((q) => q.t >= from)
      .map((q) => ({ ...q, size: revisionSize(q, relative) }))
  );
  const vals = $derived(rows.flatMap((q) => [q.first, q.latest]));
  const scaleRef = $derived(Math.max(...vals.map(Math.abs), 0));
  const sizes = $derived(rows.map((q) => q.size).filter((v): v is number => v !== null));
  const sScale = $derived(Math.max(...sizes.map(Math.abs), 0));
  const sizeUnit = $derived(relative ? '%' : unit);
  const nRev = $derived(rows.filter((q) => q.n > 1).length);
  const biggest = $derived([...rows].filter((q) => q.size !== null).sort((a, b) => Math.abs(b.size ?? 0) - Math.abs(a.size ?? 0))[0]);
  const table = $derived({
    caption: `Första publicerade och dagens värde per period${freqNote ? ` (${freqNote})` : ''}, nyast först${rows.length > TABLE_MAX ? `; de ${TABLE_MAX} senaste av ${rows.length}, alla versioner finns i CSV-filen` : ''}.`,
    columns: [
      { key: 'p', label: 'Period' },
      { key: 'first', label: 'Först publicerat' },
      { key: 'known', label: 'Känt från', align: 'left' as const },
      { key: 'latest', label: 'I dag' },
      { key: 'size', label: `Revidering (${sizeUnit})` },
      { key: 'n', label: 'Versioner' }
    ],
    rows: [...rows].reverse().slice(0, TABLE_MAX).map((q) => ({ p: periodText(q.p), first: num(q.first, scaleRef), known: q.known, latest: num(q.latest, scaleRef), size: snum(q.size, sScale), n: fmt(q.n) }))
  });
</script>

<ChartFrame
  id="rev-size"
  title="Revidering per period"
  description={`${nRev} av ${rows.length} perioder har ändrats sedan de först publicerades${freqNote ? ` (${freqNote})` : ''}. Staplarna visar dagens värde mot det först publicerade, i ${relative ? 'procent' : unit}${
    biggest && biggest.size !== null ? `; störst ${periodText(biggest.p)}, ${snum(biggest.size, sScale)} ${sizeUnit}` : ''
  }.`}
  height={200}
  margin={{ top: 18, right: 14, bottom: 26, left: 56 }}
  {source}
  {license}
  {table}
>
  {#snippet children(d)}
    {#if rows.length > 0}
      {@const x = timeScale(rows[0].t, rows.at(-1)!.t, d)}
      {@const y = valueScale(sizes, d, { zero: true }).scale}
      {@const tt = timeTicks(x, d)}
      {@const bw = Math.max(1, Math.min(10, (d.innerWidth / Math.max(1, rows.length)) * 0.7))}
      <Axis scale={y} dims={d} orient="left" ticks={4} format={(v) => tickSigned(v, sScale)} grid baseline={0} label={sizeUnit} />
      <Axis scale={x} dims={d} tickValues={tt.values} format={tt.format} />
      {#each rows as q (q.p)}
        {#if q.size !== null && q.size !== 0}
          <rect class="mark bar" x={x(q.t) - bw / 2} width={bw} y={Math.min(y(0), y(q.size))} height={Math.max(1, Math.abs(y(q.size) - y(0)))} />
        {/if}
      {/each}
      <HoverLayer
        dims={d}
        points={rows.map((q) => ({
          x: x(q.t),
          y: y(q.size ?? 0),
          tip: {
            title: periodText(q.p, true),
            rows: [
              ['Först publicerat', num(q.first, scaleRef)],
              ['I dag', num(q.latest, scaleRef)],
              ['Revidering', `${snum(q.size, sScale)} ${sizeUnit}`],
              ['Versioner', fmt(q.n)]
            ],
            note: `först känt ${q.known}`
          }
        }))}
      />
    {/if}
  {/snippet}
</ChartFrame>

<style>
  .bar {
    fill: var(--c-ink-2);
  }
</style>
