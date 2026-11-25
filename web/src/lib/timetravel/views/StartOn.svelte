<!-- The start page on a past day (W9): the month-end record known then, its headline sentence (the same rule as
     Python's, golden-tested), every branch's state and change, and the stripes up to that month. -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { resolve } from '$app/paths';
  import { Glyph, dateLabel, fmt, periodLabel, signed } from '$lib/design';
  import type { Overview } from '$lib/data';
  import { lastMonthEnd, overviewOn } from '../gate';
  import { changeSentence, headlineSentence } from '../sentence';
  import { tt } from '../store.svelte';
  import Head from './Head.svelte';
  import StripesChart from './StripesChart.svelte';
  import { bundle } from './load';
  import { monthsBetween } from './months';

  let { day }: { day: string } = $props();
  let ov = $state<Overview | null>(null);
  let err = $state<string | null>(null);
  onMount(() => {
    bundle()
      .overview()
      .then((o) => (ov = o))
      .catch((e) => (err = String(e)));
  });
  const o = $derived(ov ? overviewOn(ov, day) : null);
  const months = $derived(ov && ov.stripes.months.length ? monthsBetween(ov.stripes.months[0], lastMonthEnd(tt.max)) : []);
</script>

<svelte:head><title>Läget som det var känt {day} – AI-utrullningen</title></svelte:head>

{#if err}
  <h1>Läget</h1>
  <p class="note" role="alert">Kunde inte hämta underlaget: {err}</p>
{:else if !o}
  <h1>Läget</h1>
  <p class="note" role="status">Hämtar underlaget …</p>
{:else}
  <Head title={o.month ? `Läget ${periodLabel(o.month, true)}` : 'Inget läge ännu'} {day} month={o.month} known={o.known} status={o.status}>
    {#snippet kicker()}Tidsresa · AI-flödet som det såg ut den {dateLabel(day)}{/snippet}
    {#snippet extra()}
      {#if o.month}
        <p class="lede" data-tt="asof">{headlineSentence(o)} {o.branches.some((b) => b.previous) ? changeSentence(o) : ''}</p>
      {:else}
        <p class="lede">
          Tillstånden finns per månadsslut från {o.first_month ? periodLabel(o.first_month, true) : '–'}. Den {dateLabel(day)} var inget av dem
          känt ännu. Serierna går längre tillbaka: öppna en seriesida.
        </p>
      {/if}
    {/snippet}
  </Head>

  {#if o.month}
    <section aria-labelledby="tt-br-h">
      <h2 id="tt-br-h">Grenarna {periodLabel(o.month, true)}</h2>
      <ul class="tiles" data-tt="asof">
        {#each o.branches as b (b.code)}
          <li class="panel tile" data-known={o.known} data-state={b.state ?? ''}>
            <a href={resolve('/gren/[id]', { id: b.code })}><span class="code">{b.code}</span> {b.name}</a>
            <span class="st"><Glyph state={b.state} /></span>
            <span class="idx">
              <span class="num">{fmt(b.index, 2)}</span>
              {#if b.delta_index !== null}<span class="note">{signed(b.delta_index, 2)} mot {periodLabel(b.previous?.month ?? '')}</span>{/if}
            </span>
          </li>
        {/each}
      </ul>
    </section>
  {/if}

  <section class="panel" data-tt="asof">
    <StripesChart stripes={o.stripes} {months} {day} status={o.status} onpick={(d) => tt.set(d)} />
    <p class="note">Klicka på en månad för att resa dit. Varje ruta är en gren ett månadsslut; färgen säger riktning, inte om det är bra eller dåligt.</p>
  </section>

  <p class="note">
    Prognoser, regimmodellen och avstämningarna har ingen tidsresa ännu och visas därför inte här. Tryck ”I dag” för dagens läge.
  </p>
{/if}

<style>
  .tiles {
    list-style: none;
    padding: 0;
    margin: 8px 0 0;
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr));
  }
  .tile {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: baseline;
    gap: 2px 12px;
    padding: 10px 14px;
  }
  .tile a {
    grid-column: 1 / -1;
  }
  .tile a {
    font-weight: 620;
    text-decoration: none;
    min-height: 24px;
  }
  .tile a:hover {
    text-decoration: underline;
  }
  .code {
    color: var(--c-ink-2);
  }
  .idx {
    display: flex;
    align-items: baseline;
    gap: 8px;
    flex-wrap: wrap;
  }
  .idx {
    justify-content: flex-end;
  }
  .idx .num {
    font-size: 22px;
    font-weight: 680;
  }
</style>
