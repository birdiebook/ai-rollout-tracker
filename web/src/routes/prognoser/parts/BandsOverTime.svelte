<!-- The target's recent levels (ink line) with every live forecast as a 50/80/95 bar (Band, variant bars) and its
     outcome as a dot: filled inside the 80 % interval, a ring outside (section 4.1). The next forecast period is
     marked on the axis. With no live forecasts it shows the target and where the first forecast will land. -->
<script lang="ts">
  import { scaleLinear, scalePoint } from 'd3-scale';
  import { Axis, Band, ChartFrame, Legend, Line } from '$lib/design';
  import { useTooltip } from '$lib/design';
  import { extent, periodShort, periodTick, yearTicks, type LiveRow } from './model';
  import Marks from './OutcomeMark.svelte';

  let {
    id,
    rows,
    history,
    nextPeriod,
    unit,
    format,
    source,
    license
  }: {
    id: string;
    rows: LiveRow[];
    history: { periods: string[]; values: (number | null)[] } | null | undefined;
    nextPeriod: string | null | undefined;
    unit: string;
    format: (v: number | null | undefined) => string;
    source?: string;
    license?: string;
  } = $props();

  const hist = $derived(
    (history?.periods ?? []).map((p, i) => ({ p, v: history?.values[i] ?? null })).filter((h) => h.v !== null) as { p: string; v: number }[]
  );
  const periods = $derived(
    [...new Set([...hist.map((h) => h.p), ...rows.map((r) => r.period), ...(nextPeriod ? [nextPeriod] : [])])].sort()
  );
  const yDom = $derived(
    extent([...hist.map((h) => h.v), ...rows.flatMap((r) => [r.intervals['95']?.[0], r.intervals['95']?.[1], r.value, r.outcome])])
  );
  const withOutcome = $derived(rows.filter((r) => r.scored));
  const inside80 = $derived(withOutcome.filter((r) => r.inside['80']).length);
  const last = $derived(hist.at(-1));
  const description = $derived(
    [
      last ? `Senaste utfallet ${format(last.v)} ${unit} (${periodShort(last.p)}).` : 'Målserien har inga publicerade nivåer i paketet.',
      rows.length === 0
        ? `Inga skarpa prognoser ännu${nextPeriod ? `; den första avser ${periodShort(nextPeriod, true)} (streckad markering)` : ''}.`
        : `${rows.length} skarp${rows.length === 1 ? '' : 'a'} prognos${rows.length === 1 ? '' : 'er'} med intervall, ${withOutcome.length} med utfall, ${inside80} av ${withOutcome.length} inom 80 %-intervallet.`
    ].join(' ')
  );
  const tip = useTooltip();
</script>

{#if periods.length}
  <ChartFrame
    {id}
    title="Prognoser och utfall över tid"
    {description}
    height={260}
    margin={{ top: 14, right: 16, bottom: 26, left: 64 }}
    {source}
    {license}
    table={{
      caption: `Nivåer och skarpa prognoser (${unit})`,
      columns: [
        { key: 'p', label: 'Period', align: 'left' },
        { key: 'y', label: 'Utfall', align: 'right' },
        { key: 'f', label: 'Prognos', align: 'right' },
        { key: 'i', label: '80 %-intervall', align: 'right' }
      ],
      rows: periods.map((p) => {
        const r = rows.find((x) => x.period === p);
        const h = hist.find((x) => x.p === p);
        return {
          p: periodShort(p) + (p === nextPeriod && !r ? ' (nästa)' : ''),
          y: format(r?.outcome ?? h?.v ?? null),
          f: r ? format(r.value) : '–',
          i: r ? `${format(r.intervals['80']?.[0])}–${format(r.intervals['80']?.[1])}` : '–'
        };
      })
    }}
  >
    {#snippet children(d)}
      {@const x = scalePoint<string>().domain(periods).range([d.left, d.right]).padding(0.5)}
      {@const y = scaleLinear().domain(yDom).range([d.bottom, d.top]).nice()}
      {@const bw = Math.max(4, Math.min(16, (x.step() || 10) * 0.6))}
      <Axis scale={y} dims={d} orient="left" ticks={4} grid format={(v) => format(v)} />
      <Axis scale={x} dims={d} tickValues={yearTicks(periods, d.width < 420 ? 4 : 8)} format={(v) => periodTick(v)} />
      {#if nextPeriod && !rows.some((r) => r.period === nextPeriod)}
        {@const nx = x(nextPeriod) ?? d.right}
        <line class="mark" x1={nx} x2={nx} y1={d.top} y2={d.bottom} stroke="var(--c-model)" stroke-width="1.5" stroke-dasharray="4 3" />
        <text class="ink2" x={nx - 6} y={d.top + 10} text-anchor="end">nästa: {periodShort(nextPeriod)}</text>
      {/if}
      <Line data={hist} x={(h) => x(h.p) ?? 0} y={(h) => y(h.v)} color="var(--c-ink-2)" width={1.5} />
      <Band
        variant="bars"
        barWidth={bw}
        data={rows.filter((r) => r.value !== null)}
        x={(r) => x(r.period) ?? 0}
        center={(r) => y(r.value ?? 0)}
        levels={(['95', '80', '50'] as const).map((l) => ({
          level: l,
          lo: (r: LiveRow) => y(r.intervals[l]?.[0] ?? r.value ?? 0),
          hi: (r: LiveRow) => y(r.intervals[l]?.[1] ?? r.value ?? 0)
        }))}
      />
      {#each rows as r (r.slug)}
        {#if r.outcome !== null}
          <Marks cx={x(r.period) ?? 0} cy={y(r.outcome)} inside={r.inside['80'] ?? false} />
        {/if}
        <rect
          role="presentation"
          x={(x(r.period) ?? 0) - (x.step() || 10) / 2}
          y={d.top}
          width={x.step() || 10}
          height={d.innerHeight}
          fill="transparent"
          onpointerenter={(e) =>
            tip?.show(
              {
                title: periodShort(r.period, true),
                rows: [
                  ['Prognos', format(r.value)],
                  ['80 %', `${format(r.intervals['80']?.[0])}–${format(r.intervals['80']?.[1])}`],
                  ['Utfall', r.outcome === null ? 'väntar' : format(r.outcome)]
                ],
                note: unit
              },
              e
            )}
          onpointerleave={() => tip?.hide()}
        />
      {/each}
    {/snippet}
    {#snippet legend()}
      <Legend
        items={[
          { label: 'utfall (målserien)', fill: 'var(--c-ink-2)', line: true },
          ...(rows.length
            ? [
                { label: '50 %', fill: 'var(--c-model-50)' },
                { label: '80 %', fill: 'var(--c-model-80)' },
                { label: '95 %', fill: 'var(--c-model-95)' },
                { label: 'prognos', fill: 'var(--c-model)', line: true },
                { label: 'utfall inom 80 %', fill: 'var(--c-ink)' },
                { label: 'utanför', border: 'var(--c-ink)' }
              ]
            : [{ label: 'nästa prognosperiod', border: 'var(--c-model)' }])
        ]}
      />
    {/snippet}
  </ChartFrame>
{:else}
  <p class="empty">Målserien har inga publicerade nivåer i paketet ännu, och ingen skarp prognos är lämnad.</p>
{/if}

<style>
  .empty {
    border: 1px dashed var(--c-axis);
    border-radius: var(--radius-md);
    padding: 14px 16px;
    color: var(--c-ink-2);
    font-size: var(--fs-small);
    margin: 0;
  }
</style>
