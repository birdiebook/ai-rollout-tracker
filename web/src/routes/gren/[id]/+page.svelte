<!-- PLACEHOLDER (W4). Owner in wave 1: W6 (branch page: index over time, core series as small multiples,
     uncounted and withheld series as counted boxes). -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { scaleLinear, scalePoint } from 'd3-scale';
  import { Axis, ChartFrame, Glyph, Line, StatusBadge, fmt, periodLabel } from '$lib/design';

  let { data } = $props();
  const b = $derived(data.branch);
  type H = { month: string; index: number | null; state: string | null };
  const history = $derived(((b.history as H[] | undefined) ?? []).filter((h) => h.index !== null));
  const counted = $derived((b.series_counted as { series: string; label: string }[] | undefined) ?? []);
  const status = $derived(b.record.status === 'live' ? 'live' : 'recon');
</script>

<svelte:head><title>{b.code} {b.name} – AI-utrullningen</title></svelte:head>

<p class="kicker"><a href={resolve('/flode')}>Flödet</a> / {b.code}</p>
<h1>{b.code} {b.name}</h1>
<p class="lede">{b.question} <Glyph state={b.state} /> <StatusBadge {status} /></p>

{#if history.length > 1}
  <section class="panel">
    <ChartFrame
      id="index"
      title="Diffusionsindex över tid"
      description="Index {fmt(history.at(-1)?.index, 2)} i {periodLabel(history.at(-1)?.month ?? '', true)}. Gränserna 0,33 och 0,67 skiljer tillstånden."
      height={200}
      table={{
        columns: [{ key: 'm', label: 'Månad' }, { key: 'i', label: 'Index' }, { key: 's', label: 'Tillstånd' }],
        rows: history.map((h) => ({ m: periodLabel(h.month), i: fmt(h.index, 2), s: h.state }))
      }}
      {status}
    >
      {#snippet children(d)}
        {@const x = scalePoint<string>().domain(history.map((h) => h.month)).range([d.left, d.right])}
        {@const y = scaleLinear().domain([0, 1]).range([d.bottom, d.top])}
        <Axis scale={y} dims={d} orient="left" tickValues={[0, 0.33, 0.67, 1]} format={(v) => fmt(v, 2)} grid />
        <Axis scale={x} dims={d} tickValues={history.filter((h) => h.month.endsWith('-01')).map((h) => h.month)} format={(v) => v.slice(0, 4)} />
        <Line data={history} x={(h) => x(h.month) ?? 0} y={(h) => y(h.index ?? 0)} endDot />
      {/snippet}
    </ChartFrame>
  </section>
{/if}

{#if counted.length}
  <section>
    <h2>Räknade serier</h2>
    <ul>
      {#each counted as s (s.series)}<li><a href={resolve('/serie/[key]', { key: s.series })}>{s.label}</a></li>{/each}
    </ul>
  </section>
{/if}
