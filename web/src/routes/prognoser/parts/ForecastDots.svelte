<!-- One forecast as 20 equally likely outcomes (QuantileDots) with the 50/80/95 intervals as a ribbon under the dots
     and the outcome, when known, as a line. A far outcome is shown as an arrow at the edge, so that it does not squash
     the distribution (the distance is in the sentence and the table). -->
<script lang="ts">
  import { scaleLinear } from 'd3-scale';
  import { Axis, ChartFrame, QuantileDots, dotValues, fmt } from '$lib/design';
  import type { RecordStatus } from '$lib/design';
  import { LEVELS, dotDomain, storedQuantiles, type LiveRow } from './model';

  let {
    id,
    row,
    unit,
    format,
    title = 'Fördelningen som 20 lika sannolika utfall',
    status,
    source,
    license
  }: {
    id: string;
    row: LiveRow;
    unit: string;
    format: (v: number | null | undefined) => string;
    title?: string;
    /** record status badge; omitted for live forecasts (the page labels them with KindTag) */
    status?: RecordStatus;
    source?: string;
    license?: string;
  } = $props();

  const q = $derived(storedQuantiles(row.value, row.intervals));
  const values = $derived(dotValues(q, 20));
  const dom = $derived(dotDomain(q, row.outcome));
  const below = $derived(row.outcome === null ? null : values.filter((v) => v < (row.outcome as number)).length);
  const description = $derived(
    `Varje prick är 5 % sannolikhet. Medianen är ${format(row.value)} ${unit}, 80 %-intervallet ${format(row.intervals['80']?.[0])}–${format(row.intervals['80']?.[1])}.` +
      (row.outcome === null
        ? ' Utfallet är inte publicerat ännu.'
        : ` Utfallet ${format(row.outcome)}: ${below} av 20 prickar under${dom.offScale ? ', långt utanför skalan' : ''}.`)
  );
  const ribbon: Record<string, number> = { '95': 2, '80': 4, '50': 7 };
</script>

<ChartFrame
  {id}
  {title}
  {description}
  height={168}
  margin={{ top: 22, right: 14, bottom: 40, left: 14 }}
  {status}
  {source}
  {license}
  table={{
    caption: 'Lagrade kvantiler och utfall',
    columns: [{ key: 'p', label: 'Sannolikhet under', align: 'left' }, { key: 'v', label: `Värde (${unit})`, align: 'right' }],
    rows: [
      ...q.map(([p, v]) => ({ p: `${fmt(p * 100, p * 100 % 1 ? 1 : 0)} %`, v: format(v) })),
      ...(row.outcome === null ? [] : [{ p: 'Utfall', v: format(row.outcome) }])
    ]
  }}
>
  {#snippet children(d)}
    {@const x = scaleLinear().domain(dom.domain).range([d.left, d.right])}
    {@const dd = { ...d, bottom: d.bottom - 14 }}
    <Axis scale={x} dims={d} ticks={d.width < 420 ? 3 : 5} format={(v) => format(v)} />
    {#each [...LEVELS].reverse() as l (l)}
      {@const iv = row.intervals[l]}
      {#if iv && iv[0] !== null && iv[1] !== null}
        <line class="mark" x1={x(iv[0])} x2={x(iv[1])} y1={d.bottom - 6} y2={d.bottom - 6} stroke="var(--c-model)" stroke-width={ribbon[l]} stroke-linecap="butt" opacity={l === '50' ? 1 : l === '80' ? 0.6 : 0.35} />
      {/if}
    {/each}
    <QuantileDots
      {values}
      x={(v) => x(v)}
      dims={dd}
      outcome={row.outcome !== null && !dom.offScale ? row.outcome : undefined}
      {format}
    />
    {#if row.outcome !== null && dom.offScale}
      {@const right = dom.offScale > 0}
      <text class="ink" x={right ? d.right : d.left} y={d.top - 8} text-anchor={right ? 'end' : 'start'}>
        {right ? '' : '← '}utfall {format(row.outcome)} utanför skalan{right ? ' →' : ''}
      </text>
    {/if}
  {/snippet}
</ChartFrame>
