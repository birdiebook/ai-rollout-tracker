<!-- PLACEHOLDER (W4). Owner in wave 1: W7 (series instrument: level/pace/change, versions, table, source, licence,
     download, permalink); W9 adds time travel. -->
<script lang="ts">
  import { scaleLinear, scalePoint } from 'd3-scale';
  import { extent } from 'd3-array';
  import { Axis, ChartFrame, Line, fmt, periodLabel } from '$lib/design';

  let { data } = $props();
  const s = $derived(data.series);
  const pts = $derived(
    (s.levels?.periods ?? []).map((p, i) => ({ p, v: s.levels?.values[i] ?? null })).filter((d) => d.v !== null) as { p: string; v: number }[]
  );
</script>

<svelte:head><title>{s.label} – AI-utrullningen</title></svelte:head>

<p class="kicker">{s.branch} · {s.key}</p>
<h1>{s.label}</h1>
<p class="lede">Enhet: {s.unit ?? '–'}. {s.license.attribution}</p>

{#if pts.length > 1}
  <section class="panel">
    <ChartFrame
      id="level"
      title="Nivå"
      description="Senaste värde {fmt(pts.at(-1)?.v, 1)} ({periodLabel(pts.at(-1)?.p ?? '', true)})."
      height={220}
      margin={{ top: 10, right: 12, bottom: 24, left: 48 }}
      source={s.source}
      license={s.license.short}
      table={{ columns: [{ key: 'p', label: 'Period' }, { key: 'v', label: s.unit ?? 'Värde' }], rows: pts.map((d) => ({ p: d.p, v: fmt(d.v, 1) })) }}
    >
      {#snippet children(d)}
        {@const x = scalePoint<string>().domain(pts.map((q) => q.p)).range([d.left, d.right])}
        {@const y = scaleLinear().domain(extent(pts, (q) => q.v) as [number, number]).nice().range([d.bottom, d.top])}
        <Axis scale={y} dims={d} orient="left" ticks={4} format={(v) => fmt(v)} grid />
        <Axis scale={x} dims={d} tickValues={pts.filter((q) => q.p.endsWith('-01')).map((q) => q.p)} format={(v) => v.slice(0, 4)} />
        <Line data={pts} x={(q) => x(q.p) ?? 0} y={(q) => y(q.v)} endDot />
      {/snippet}
    </ChartFrame>
  </section>
{/if}
