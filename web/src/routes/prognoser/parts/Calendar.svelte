<!-- The forecast calendar (W8): one row per nowcast on a shared time axis from today, the next registered forecast
     day as a dot. Main models and shadows are told apart by the dot (filled = main model, ring = shadow). -->
<script lang="ts">
  import { scaleTime } from 'd3-scale';
  import { Axis, ChartFrame, dateLabel } from '$lib/design';
  import type { CalendarEntry } from '$lib/data';
  import { daysUntil, periodShort } from './model';

  let { cal, today }: { cal: CalendarEntry[]; today: string } = $props();

  const dated = $derived(cal.filter((c) => c.next_origin));
  const t0 = $derived(new Date(today + 'T00:00:00Z'));
  const t1 = $derived(
    new Date(Math.max(t0.getTime() + 60 * 86_400_000, ...dated.map((c) => Date.parse(String(c.next_origin) + 'T00:00:00Z') + 12 * 86_400_000)))
  );
  const first = $derived([...dated].sort((a, b) => String(a.next_origin).localeCompare(String(b.next_origin)))[0]);
  const description = $derived(
    first
      ? `Nästa skarpa prognos är ${first.label} den ${dateLabel(String(first.next_origin))}, om ${daysUntil(today, first.next_origin)} dagar.` +
          (cal.length > dated.length ? ` ${cal.filter((c) => !c.next_origin).map((c) => c.label).join(', ')} har ingen planerad prognosdag.` : '')
      : 'Ingen planerad prognosdag.'
  );
  const shadow = (c: CalendarEntry) => c.id === 'd2' || !c.champion;
  const rowH = 32;
  const MONTHS = ['jan', 'feb', 'mar', 'apr', 'maj', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec'];
</script>

<ChartFrame
  id="kalender"
  title="Kalendern: nästa skarpa prognos"
  headingLevel={2}
  {description}
  height={cal.length * rowH + 30}
  margin={{ top: 4, right: 18, bottom: 24, left: 46 }}
  table={{
    columns: [
      { key: 'n', label: 'Prognos', align: 'left' },
      { key: 'c', label: 'Huvudmodell', align: 'left' },
      { key: 'o', label: 'Prognosdag', align: 'left' },
      { key: 'p', label: 'Avser', align: 'left' },
      { key: 'k', label: 'Skarpa hittills', align: 'right' }
    ],
    rows: cal.map((c) => ({
      n: `${c.label} ${c.title}`,
      c: c.champion ?? 'skugga',
      o: c.next_origin ? dateLabel(c.next_origin) : '–',
      p: periodShort(c.next_period),
      k: c.n_live
    }))
  }}
>
  {#snippet children(d)}
    {@const x = scaleTime().domain([t0, t1]).range([d.left, d.right])}
    <Axis scale={x} dims={d} ticks={d.width < 420 ? 3 : 6} format={(v: Date) => `${MONTHS[v.getUTCMonth()]}${v.getUTCMonth() === 0 ? ' ' + v.getUTCFullYear() : ''}`} />
    <line x1={d.left} x2={d.left} y1={d.top} y2={d.bottom} stroke="var(--c-ink-2)" stroke-width="1.5" />
    <text class="ink2" x={d.left + 4} y={d.bottom - 4}>i dag</text>
    {#each cal as c, i (c.id)}
      {@const cy = d.top + 14 + i * rowH}
      <text class="ink rowlab" x={d.left - 8} y={cy + 4} text-anchor="end">{c.label}</text>
      <line class="gridline" x1={d.left} x2={d.right} y1={cy} y2={cy} />
      {#if c.next_origin}
        {@const cx = x(new Date(c.next_origin + 'T00:00:00Z'))}
        {@const narrow = d.width < 520}
        {@const flip = cx > d.right - 150}
        <circle class="mark" {cx} {cy} r="6" fill={shadow(c) ? 'var(--c-surface)' : 'var(--c-model)'} stroke="var(--c-model)" stroke-width="2" />
        <text
          class="ink2"
          x={narrow ? Math.max(d.left + 4, Math.min(cx + (flip ? 6 : -6), d.right)) : cx + (flip ? -11 : 11)}
          y={narrow ? cy - 9 : cy + 4}
          text-anchor={flip ? 'end' : 'start'}
        >
          {dateLabel(c.next_origin)} → {periodShort(c.next_period)}
        </text>
      {:else}
        <text class="ink2" x={d.left + 8} y={cy + 4}>ingen planerad prognos</text>
      {/if}
    {/each}
  {/snippet}
</ChartFrame>

<style>
  .rowlab {
    font-weight: 620;
  }
</style>
