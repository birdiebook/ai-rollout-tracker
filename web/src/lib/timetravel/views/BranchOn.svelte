<!-- A branch page on a past day (W9): the index history known then (click to travel), the state of the latest
     month end, and the series the record measured that month with the record's own direction and pace (each
     series' measure history cut at the day). Withheld series are counted in the index and never shown. -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { resolve } from '$app/paths';
  import { DIRECTIONS, Glyph, dateLabel, fmt, periodLabel, signed } from '$lib/design';
  import type { Branch, Overview, SeriesIndexEntry } from '$lib/data';
  import type { SeriesDoc } from '$lib/series/types';
  import { periodText } from '$lib/series/period';
  import { branchOn, lastMonthEnd, monthEnd, seriesOn, type HistoryRow } from '../gate';
  import { tt } from '../store.svelte';
  import Head from './Head.svelte';
  import IndexChart from './IndexChart.svelte';
  import { bundle } from './load';
  import { monthsBetween } from './months';

  let { day, params }: { day: string; params: { id: string } } = $props();
  let doc = $state<(Branch & { history?: HistoryRow[] }) | null>(null);
  let ov = $state<Overview | null>(null);
  let docs = $state<SeriesDoc[]>([]);
  let err = $state<string | null>(null);
  onMount(async () => {
    try {
      const b = bundle();
      const [d, o, idx] = await Promise.all([b.branch(params.id), b.overview(), b.seriesIndex()]);
      doc = d as Branch & { history?: HistoryRow[] };
      ov = o;
      // the series a record of this branch can have measured: its core series and the ones counted today (keys
      // only, to know which documents to fetch; what is drawn comes from each document's cut history)
      const keys = idx.series.filter((s: SeriesIndexEntry) => s.branch === params.id && (s.core || s.counted)).map((s) => s.key);
      docs = (await Promise.all(keys.map((k) => b.series(k)))) as unknown as SeriesDoc[];
    } catch (e) {
      err = String(e);
    }
  });
  const b = $derived(doc ? branchOn(doc, day) : null);
  const months = $derived(doc?.history?.length ? monthsBetween(doc.history[0].month, lastMonthEnd(tt.max)) : []);
  const series = $derived(
    b && ov
      ? docs
          .map((d) => seriesOn(d, day, ov!.record))
          .map((s) => ({ s, now: s.measure && s.measure.month === b.month ? s.measure : null }))
          .sort((x, y) => Number(!!y.now?.counted) - Number(!!x.now?.counted) || Number(!!y.now) - Number(!!x.now) || x.s.meta.label.localeCompare(y.s.meta.label, 'sv'))
      : []
  );
  const measured = $derived(series.filter((x) => x.now));
  const notMeasured = $derived(series.filter((x) => !x.now));
  const spark = (s: (typeof series)[number]['s']) => {
    const h = s.history;
    if (!h) return { d: '', dots: [] as { x: number; y: number; dir: number | null }[], zero: 0 };
    const pts = h.months.map((m, i) => ({ i: months.indexOf(m), v: h.pace?.[i] ?? null, dir: h.direction?.[i] ?? null })).filter((p) => p.i >= 0 && p.v !== null) as { i: number; v: number; dir: number | null }[];
    if (!pts.length) return { d: '', dots: [], zero: 0 };
    const lo = Math.min(0, ...pts.map((p) => p.v));
    const hi = Math.max(0, ...pts.map((p) => p.v));
    const X = (i: number) => 4 + (i / Math.max(1, months.length - 1)) * 232;
    const Y = (v: number) => 44 - ((v - lo) / (hi - lo || 1)) * 38;
    return { d: pts.map((p, k) => `${k ? 'L' : 'M'}${X(p.i).toFixed(1)},${Y(p.v).toFixed(1)}`).join(''), dots: [{ x: X(pts.at(-1)!.i), y: Y(pts.at(-1)!.v), dir: pts.at(-1)!.dir }], zero: Y(0) };
  };
</script>

<svelte:head><title>{params.id} som den var känd {day} – AI-utrullningen</title></svelte:head>

{#if err}
  <h1>{params.id}</h1>
  <p class="note" role="alert">Kunde inte hämta underlaget: {err}</p>
{:else if !b}
  <h1>{params.id}</h1>
  <p class="note" role="status">Hämtar underlaget …</p>
{:else}
  <Head title="{b.code} {b.name}" {day} month={b.month} known={b.known} status={b.status}>
    {#snippet kicker()}<a href={resolve('/flode')}>Flödet</a> / {b.code} · tidsresa till {dateLabel(day)}{/snippet}
    {#snippet extra()}{#if b.question}<p class="lede">{b.question}</p>{/if}{/snippet}
  </Head>

  <section class="now panel" aria-labelledby="tt-now-h" data-tt="asof" data-known={b.known ?? ''}>
    {#if b.month}
      <h2 id="tt-now-h" class="kicker">Läget {periodLabel(b.month, true)}</h2>
      <div class="big"><Glyph state={b.state} size="1.15em" /></div>
      <p class="idx"><span class="num">{fmt(b.index, 2)}</span> <span class="note">diffusionsindex, 0–1 · {b.n_up ?? 0} ▲ {b.n_neutral ?? 0} ● {b.n_down ?? 0} ▼ av {b.n_series ?? 0} räknade</span></p>
      {#if b.previous}
        <p class="note">Månaden före ({periodLabel(b.previous.month)}): {fmt(b.previous.index, 2)} <Glyph state={b.previous.state} />{#if b.delta_index !== null}, förändring {signed(b.delta_index, 2)}{/if}.</p>
      {/if}
    {:else}
      <h2 id="tt-now-h" class="kicker">Inget läge ännu</h2>
      <p class="note">Grenens historik börjar {b.first_month ? periodLabel(b.first_month, true) : '–'}. Den {dateLabel(day)} var inget månadsslut känt.</p>
    {/if}
  </section>

  <section class="panel" data-tt="asof">
    <IndexChart id="tt-index" history={b.history} {months} {day} status={b.status} lo={ov?.stripes.thresholds.braking_at_most} hi={ov?.stripes.thresholds.accelerating_at_least} onpick={(m) => tt.set(monthEnd(m))} />
  </section>

  {#if b.month}
    <section aria-labelledby="tt-ser-h" data-tt="asof">
      <h2 id="tt-ser-h">Serierna {periodLabel(b.month, true)}</h2>
      <p class="note">
        Postens riktning och takt vid månadsslutet, som de stod då (aldrig omräknade). Linjen är postens takt vid varje månadsslut fram till dagen.
        Inhållna serier räknas i indexet men visas inte.
      </p>
      {#if measured.length}
        <ul class="cards">
          {#each measured as { s, now } (s.meta.key)}
            {@const sp = spark(s)}
            <li class="panel card" data-known={now?.known ?? ''}>
              <h3><a href={resolve('/serie/[key]', { key: s.meta.key })}>{s.meta.label}</a></h3>
              <p class="dir">
                {#if now?.counted && now.direction !== null && now.direction !== undefined}<Glyph direction={now.direction} />{:else if now?.counted}<span class="note">räknas, ingen riktning</span>{:else}<span class="note">mäts, räknas inte</span>{/if}
              </p>
              <svg viewBox="0 0 240 48" width="100%" height="48" preserveAspectRatio="xMinYMid meet" role="img" aria-label="Postens takt för {s.meta.label} vid varje månadsslut fram till {periodLabel(b.month)}">
                {#if sp.d}
                  <line x1="4" x2="236" y1={sp.zero} y2={sp.zero} stroke="var(--c-axis)" stroke-width="1" />
                  <path d={sp.d} fill="none" stroke="var(--c-ink-2)" stroke-width="1.5" />
                  {#each sp.dots as p (p.x)}<circle cx={p.x} cy={p.y} r="4" fill={p.dir === null ? 'var(--c-surface)' : DIRECTIONS[p.dir as 1 | 0 | -1].color} stroke="var(--c-ink)" stroke-width="1" />{/each}
                {/if}
              </svg>
              <p class="note">
                Takt {signed(now?.pace ?? null, 1)}{#if now?.pace_percentile !== null && now?.pace_percentile !== undefined}, percentil {fmt(now.pace_percentile)}{/if}.
                {#if now?.latest_period}Senaste period {periodText(now.latest_period)}{#if now.known_from}, känd från {dateLabel(now.known_from)}{/if}.{/if}
              </p>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="note">Inga publicerbara serier mättes vid det här månadsslutet.</p>
      {/if}
      {#if notMeasured.length}
        <p class="note">
          Inte i posten {periodLabel(b.month)}: {#each notMeasured as { s }, i (s.meta.key)}{i ? ', ' : ''}<a href={resolve('/serie/[key]', { key: s.meta.key })}>{s.meta.label}</a>{/each}.
        </p>
      {/if}
    </section>
  {/if}
{/if}

<style>
  .now h2.kicker {
    font-size: var(--fs-small);
    font-weight: 400;
    margin: 0 0 6px;
  }
  .big {
    font-size: 28px;
    font-weight: 680;
  }
  .idx {
    margin: 4px 0;
    display: flex;
    gap: 10px;
    align-items: baseline;
    flex-wrap: wrap;
  }
  .idx .num {
    font-size: var(--fs-big);
    font-weight: 680;
    line-height: 1;
  }
  .cards {
    list-style: none;
    padding: 0;
    margin: 10px 0 0;
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 280px), 1fr));
  }
  .card {
    display: grid;
    gap: 4px;
    align-content: start;
  }
  .card h3 {
    font-size: 14px;
  }
  .card h3 a {
    text-decoration: none;
  }
  .card h3 a:hover {
    text-decoration: underline;
  }
  .dir,
  .card .note {
    margin: 0;
  }
</style>
