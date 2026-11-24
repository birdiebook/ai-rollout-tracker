<!-- D2 fan (W8): the target's recent quarters (ink) and the 1–8 quarter path with 50/80/95 bands as a continuous
     area (Band, variant area). D2 is a shadow: the frame says so, and the model per horizon group is named. -->
<script lang="ts">
  import { scaleLinear, scalePoint } from 'd3-scale';
  import { Axis, Band, ChartFrame, Legend, Line, fmt } from '$lib/design';
  import type { HorizonTarget } from '$lib/data';
  import { extent, periodShort, periodTick } from './model';

  let { t, origin }: { t: HorizonTarget; origin: string | null } = $props();

  const fan = $derived(t.fan);
  const pts = $derived(
    fan
      ? fan.periods.map((p, i) => ({
          p,
          v: fan.values[i],
          lo: Object.fromEntries((['50', '80', '95'] as const).map((l) => [l, fan.intervals[l]?.lo[i] ?? fan.values[i]])),
          hi: Object.fromEntries((['50', '80', '95'] as const).map((l) => [l, fan.intervals[l]?.hi[i] ?? fan.values[i]]))
        }))
      : []
  );
  const hist = $derived(
    ((t.history?.periods ?? []).map((p, i) => ({ p, v: t.history?.values[i] ?? null })).filter((h) => h.v !== null) as { p: string; v: number }[])
  );
  const periods = $derived([...new Set([...hist.map((h) => h.p), ...pts.map((p) => p.p)])].sort());
  const yDom = $derived(extent([...hist.map((h) => h.v), ...pts.flatMap((p) => [p.lo['95'], p.hi['95']])]));
  const end = $derived(pts.at(-1));
  const f = (v: number | null | undefined) => fmt(v, 0);
  const description = $derived(
    end
      ? `Bana från ${periodShort(t.base)} till ${periodShort(end.p)}: ${f(end.v)} ${t.unit} om ${pts.length - 1} kvartal, 80 %-intervall ${f(end.lo['80'])}–${f(end.hi['80'])}. Modell per horisont: ${Object.entries(t.champion_by_group).map(([g, m]) => `${g} ${m}`).join(', ')}.`
      : 'Ingen bana i paketet ännu.'
  );
</script>

{#if pts.length}
  <ChartFrame
    id="fan-{t.name}"
    title={t.label}
    {description}
    height={240}
    margin={{ top: 12, right: 16, bottom: 26, left: 64 }}
    table={{
      caption: `Bana per horisont (${t.unit})${origin ? `, prognosdag ${origin}` : ''}`,
      columns: [
        { key: 'h', label: 'Horisont', align: 'right' },
        { key: 'q', label: 'Kvartal', align: 'left' },
        { key: 'm', label: 'Modell', align: 'left' },
        { key: 'v', label: 'Bana', align: 'right' },
        { key: 'i', label: '80 %-intervall', align: 'right' }
      ],
      rows: (t.paths ?? []).map((p) => ({
        h: p.h,
        q: periodShort(p.quarter),
        m: p.champion,
        v: f(p.value),
        i: p.interval_80 ? `${f(p.interval_80[0])}–${f(p.interval_80[1])}` : '–'
      }))
    }}
  >
    {#snippet children(d)}
      {@const x = scalePoint<string>().domain(periods).range([d.left, d.right]).padding(0.3)}
      {@const y = scaleLinear().domain(yDom).range([d.bottom, d.top]).nice()}
      <Axis scale={y} dims={d} orient="left" ticks={4} grid format={(v) => f(v)} />
      <Axis scale={x} dims={d} tickValues={periods.filter((p) => p.endsWith('Q1'))} format={(v) => periodTick(v)} />
      <Band
        data={pts}
        x={(p) => x(p.p) ?? 0}
        center={(p) => y(p.v ?? 0)}
        levels={(['95', '80', '50'] as const).map((l) => ({ level: l, lo: (p: (typeof pts)[number]) => y(p.lo[l] ?? 0), hi: (p: (typeof pts)[number]) => y(p.hi[l] ?? 0) }))}
      />
      <Line data={hist} x={(h) => x(h.p) ?? 0} y={(h) => y(h.v)} color="var(--c-ink-2)" width={1.5} />
    {/snippet}
    {#snippet legend()}
      <Legend items={[...(hist.length ? [{ label: 'utfall', fill: 'var(--c-ink-2)', line: true }] : []), { label: 'bana (skugga)', fill: 'var(--c-model)', line: true }, { label: '50 %', fill: 'var(--c-model-50)' }, { label: '80 %', fill: 'var(--c-model-80)' }, { label: '95 %', fill: 'var(--c-model-95)' }]} />
    {/snippet}
  </ChartFrame>
{:else}
  <div class="empty">
    <h3>{t.label}</h3>
    <p>Ingen bana i paketet ännu. Modeller: {t.models.join(', ')}. Modell per horisont: {Object.entries(t.champion_by_group).map(([g, m]) => `${g} ${m}`).join(', ')}.</p>
  </div>
{/if}

<style>
  .empty {
    border: 1px dashed var(--c-axis);
    border-radius: var(--radius-md);
    padding: 14px 16px;
  }
  .empty p {
    margin: 4px 0 0;
    color: var(--c-ink-2);
    font-size: var(--fs-small);
  }
</style>
