<!-- Marks of the forecast calendar (Q2): a time axis from today to the last planned live forecast, one ring per
     origin date with the nowcasts stacked above it, the latest live forecast as a filled dot, and "i dag". -->
<script lang="ts">
  import { dateLabel, useTooltip, type ChartDims } from '$lib/design';
  import { upcoming, type ForecastView, type StartData } from './model';

  let { d, calendar, today, forecast }: { d: ChartDims; calendar: StartData['calendar']; today: string; forecast: ForecastView | null } = $props();
  const tip = useTooltip();
  const DAY = 864e5;
  const t = (s: string) => Date.parse(s + 'T00:00:00Z');
  const groups = $derived(upcoming(calendar));
  const t0 = $derived(Math.min(t(today), forecast ? t(forecast.origin) : Infinity) - 12 * DAY);
  const t1 = $derived(Math.max(t(today) + 60 * DAY, ...groups.map((g) => t(g.date))) + 18 * DAY);
  const x = (ms: number) => d.left + ((ms - t0) / (t1 - t0)) * d.innerWidth;
  const axisY = $derived(d.bottom - 20);
  const months = $derived.by(() => {
    const out: { ms: number; label: string }[] = [];
    const m = new Date(t0);
    m.setUTCDate(1);
    m.setUTCMonth(m.getUTCMonth() + 1);
    const names = ['jan', 'feb', 'mar', 'apr', 'maj', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec'];
    for (; m.getTime() < t1; m.setUTCMonth(m.getUTCMonth() + 1))
      out.push({ ms: m.getTime(), label: m.getUTCMonth() === 0 ? String(m.getUTCFullYear()) : names[m.getUTCMonth()] });
    return out;
  });
  const short = (s: string) => dateLabel(s).replace(/ \d{4}$/, '');
</script>

<line class="axisline" x1={d.left} x2={d.right} y1={axisY} y2={axisY} />
{#each months as m (m.ms)}
  <line class="axisline" x1={x(m.ms)} x2={x(m.ms)} y1={axisY - 3} y2={axisY + 3} />
{/each}

<line class="mark" x1={x(t(today))} x2={x(t(today))} y1={axisY - 16} y2={axisY + 8} stroke="var(--c-ink)" stroke-width="1.5" />
<text class="ink" x={x(t(today)) - 4} y={axisY + 15} text-anchor="end">i dag</text>

{#if forecast}
  {@const fx = x(t(forecast.origin))}
  <circle
    class="mark"
    cx={fx}
    cy={axisY}
    r="6"
    fill="var(--c-model)"
    stroke="var(--c-surface)"
    stroke-width="2"
    role="presentation"
    onpointerenter={(e) => tip?.show({ title: `${forecast.label} lämnad ${dateLabel(forecast.origin)}`, rows: [['Avser', forecast.period]], note: 'senaste skarpa prognos' }, e)}
    onpointerleave={() => tip?.hide()}
  />
  <text class="ink" x={fx} y={axisY - 12} text-anchor="middle">{forecast.label}</text>
{/if}

{#each groups as g (g.date)}
  {@const gx = x(t(g.date))}
  <circle
    class="mark"
    cx={gx}
    cy={axisY}
    r="6"
    fill="var(--c-surface)"
    stroke="var(--c-model)"
    stroke-width="2.5"
    role="presentation"
    onpointerenter={(e) =>
      tip?.show({ title: `Skarp prognos ${dateLabel(g.date)}`, rows: g.items.map((c) => [c.label, c.title] as [string, string]) }, e)}
    onpointerleave={() => tip?.hide()}
  />
  {#each g.items as c, j (c.id)}
    <text class="ink" x={gx} y={axisY - 12 - j * 13} text-anchor="middle">{c.label}</text>
  {/each}
  <text x={gx} y={axisY + 15} text-anchor="middle">{short(g.date)}</text>
{/each}
