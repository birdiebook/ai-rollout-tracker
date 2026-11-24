<!-- A branch's diffusion index as known on the day (W9): the month-end records known then, on a fixed calendar axis
     (P2: the same view every month), the months after the day left empty ("ännu inte känt"). Reconstructed months
     dashed, live snapshots solid (P9). Click a month to travel to its month end. -->
<script lang="ts">
  import { scalePoint, scaleLinear } from 'd3-scale';
  import { Axis, ChartFrame, Legend, Line, dateLabel, fmt, periodLabel, stateStyle, type RecordStatus } from '$lib/design';
  import HoverLayer from '$lib/series/HoverLayer.svelte';
  import type { HistoryRow } from '../gate';

  let {
    id,
    title = 'Diffusionsindex som det var känt',
    history,
    months,
    day,
    status,
    lo = 0.33,
    hi = 0.67,
    onpick
  }: {
    id: string;
    title?: string;
    history: (HistoryRow & { known: string })[];
    /** the calendar axis, first month of the history to the last month end before the bundle's day */
    months: string[];
    day: string;
    status: RecordStatus;
    lo?: number;
    hi?: number;
    onpick?: (month: string) => void;
  } = $props();

  const live = (h: { kind: string }) => h.kind === 'skarp' || h.kind === 'live';
  const firstLive = $derived(history.findIndex(live));
  const reconPart = $derived(firstLive < 0 ? history : history.slice(0, firstLive + 1));
  const livePart = $derived(firstLive < 0 ? [] : history.slice(Math.max(0, firstLive - 1)));
  const cur = $derived(history.at(-1) ?? null);
  const sentence = $derived(
    cur
      ? `Den ${dateLabel(day)} fanns ${history.length} månadsslut, det senaste ${periodLabel(cur.month, true)}: index ${fmt(cur.index, 2)}, ${stateStyle(cur.state).word}.`
      : `Den ${dateLabel(day)} fanns ännu inget månadsslut i grenens historik.`
  );
  function pick(e: MouseEvent, d: { left: number; right: number; width: number }, x: (m: string) => number | undefined) {
    if (!onpick) return;
    const svg = (e.currentTarget as SVGElement).ownerSVGElement ?? (e.currentTarget as SVGSVGElement);
    const box = svg.getBoundingClientRect();
    const px = ((e.clientX - box.left) / box.width) * d.width;
    let best = months[0];
    for (const m of months) if (Math.abs((x(m) ?? 0) - px) < Math.abs((x(best) ?? 0) - px)) best = m;
    if (best) onpick(best);
  }
</script>

<ChartFrame
  {id}
  {title}
  description={sentence}
  height={220}
  {status}
  headingLevel={2}
  margin={{ top: 14, right: 16, bottom: 24, left: 40 }}
  table={{
    caption: `${title}: månadsslut kända den ${day}`,
    columns: [
      { key: 'm', label: 'Månad' },
      { key: 'i', label: 'Index' },
      { key: 's', label: 'Tillstånd', align: 'left' },
      { key: 'k', label: 'Underlag', align: 'left' },
      { key: 'kf', label: 'Känd från', align: 'left' }
    ],
    rows: [...history].reverse().map((h) => ({ m: periodLabel(h.month), i: fmt(h.index, 2), s: `${stateStyle(h.state).glyph} ${stateStyle(h.state).word}`, k: h.kind, kf: h.known }))
  }}
>
  {#snippet children(d)}
    {@const x = scalePoint<string>().domain(months).range([d.left, d.right]).padding(0.5)}
    {@const y = scaleLinear().domain([0, 1]).range([d.bottom, d.top])}
    {@const xm = (m: string) => x(m) ?? 0}
    {@const step = months.length > 1 ? (d.right - d.left) / months.length : 20}
    {@const r = Math.max(2, Math.min(4, step * 0.38))}
    {@const edge = cur ? xm(cur.month) + step / 2 : d.left}
    {@const years = months.filter((m) => m.endsWith('-01'))}
    <rect x={d.left} y={y(hi)} width={d.right - d.left} height={y(lo) - y(hi)} fill="var(--c-mid)" />
    <Axis scale={y} dims={d} orient="left" tickValues={[0, 0.5, 1]} format={(v) => fmt(v, 1)} />
    <line class="thr" x1={d.left} x2={d.right} y1={y(hi)} y2={y(hi)} />
    <line class="thr" x1={d.left} x2={d.right} y1={y(lo)} y2={y(lo)} />
    <Axis scale={x} dims={d} tickValues={years.length ? years : months.slice(0, 1)} format={(v) => (String(v).endsWith('-01') ? String(v).slice(0, 4) : periodLabel(String(v)))} />
    {#if edge < d.right}
      <rect class="later" x={edge} y={d.top} width={d.right - edge} height={d.bottom - d.top} />
      {#if d.right - edge > 70}<text class="ink2" x={(edge + d.right) / 2} y={d.top + 14} text-anchor="middle">ännu inte känt</text>{/if}
    {/if}
    <Line data={reconPart} x={(h) => xm(h.month)} y={(h) => y(h.index ?? 0)} defined={(h) => h.index !== null} dashed width={1.5} color="var(--c-ink-2)" />
    {#if livePart.length > 1}<Line data={livePart} x={(h) => xm(h.month)} y={(h) => y(h.index ?? 0)} defined={(h) => h.index !== null} />{/if}
    {#each history as h (h.month)}
      {#if h.index !== null}
        {@const s = stateStyle(h.state)}
        <circle class="mark" cx={xm(h.month)} cy={y(h.index)} r={h === cur ? r + 3 : r} fill={s.key === 'none' ? 'var(--c-surface)' : s.color} stroke={live(h) || h === cur ? 'var(--c-ink)' : 'var(--c-surface)'} stroke-width={live(h) || h === cur ? 2 : 1} data-known={h.known} data-kind={h.kind} />
      {/if}
    {/each}
    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -- pointer shortcut; the slider and ±1 month are the keyboard path -->
    <g class="pick" onclick={(e) => pick(e, d, x)}>
      <HoverLayer
        dims={d}
        points={history
          .filter((h) => h.index !== null)
          .map((h) => ({
            x: xm(h.month),
            y: y(h.index!),
            tip: {
              title: periodLabel(h.month, true),
              rows: [
                ['Index', fmt(h.index, 2)],
                ['Tillstånd', `${stateStyle(h.state).glyph} ${stateStyle(h.state).word}`],
                ['Känd från', dateLabel(h.known)]
              ],
              note: `${live(h) ? 'skarp ögonblicksbild' : 'rekonstruerad historik'}${onpick ? ' · klicka för att resa dit' : ''}`
            }
          }))}
      />
    </g>
  {/snippet}
  {#snippet legend()}
    <Legend
      items={[
        { label: 'stabil zon', fill: 'var(--c-mid)', border: 'var(--c-axis)' },
        { label: 'streckad: rekonstruerad', line: true, fill: 'var(--c-ink-2)' },
        { label: 'tonat: efter dagen, ännu inte känt', fill: 'var(--c-grid)' }
      ]}
    />
  {/snippet}
</ChartFrame>

<style>
  .thr {
    stroke: var(--c-axis);
    stroke-width: 1;
    stroke-dasharray: 3 3;
  }
  .later {
    fill: var(--c-grid);
    opacity: 0.55;
  }
  .pick {
    cursor: pointer;
  }
</style>
