<!-- W8 Prognossidor: overview of N1–N6 and D2. Calendar first (when is the next forecast), then one card per nowcast
     with the target's recent levels and its live forecasts as interval bars, then how to read the markings. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import type { Nowcast } from '$lib/data';
  import Calendar from './parts/Calendar.svelte';
  import NowcastCard from './parts/NowcastCard.svelte';
  import RoleTag from './parts/RoleTag.svelte';
  import KindTag from './parts/KindTag.svelte';
  import { liveRows, overviewSentence } from './parts/model';

  let { data } = $props();
  const cards = $derived(data.nowcasts.map((n) => ({ n, rows: liveRows(n as unknown as Nowcast) })));
  const nLive = $derived(cards.reduce((a, c) => a + c.rows.length, 0));
  const nOut = $derived(cards.reduce((a, c) => a + c.rows.filter((r) => r.scored).length, 0));
  const sentence = $derived(overviewSentence(data.calendar, nLive, nOut, data.today));
</script>

<svelte:head><title>Prognoser – AI-utrullningen</title></svelte:head>

<p class="kicker">Prognoser · N1–N6 och D2</p>
<h1>Prognoser med öppet facit</h1>
<p class="lede">{sentence}</p>

<section class="panel cal">
  <Calendar cal={data.calendar} today={data.today} />
</section>

<section aria-labelledby="h-cards">
  <h2 id="h-cards">Varje prognos</h2>
  <div class="cards">
    {#each cards as c (c.n.id)}
      <NowcastCard
        href={resolve('/prognoser/[id]/[[slug]]', { id: c.n.id })}
        label={c.n.label}
        title={c.n.title}
        champion={c.n.champion}
        history={c.n.history}
        rows={c.rows}
        nextOrigin={c.n.next_origin}
        nextPeriod={c.n.next_period}
        today={data.today}
        unit={c.n.unit}
        note={c.n.next_origin ? undefined : 'Ingen skarp prognos i den aktiva regimen.'}
      />
    {/each}
    <NowcastCard
      href={resolve('/prognoser/[id]/[[slug]]', { id: 'd2' })}
      label="D2"
      title="Prognoser 1–8 kvartal ({data.d2.n_targets} mål)"
      champion={null}
      shadow
      history={data.d2.history}
      rows={[]}
      nextOrigin={data.d2.next_origin}
      nextPeriod={data.d2.next_period}
      today={data.today}
      unit={data.d2.unit}
      note="Ingen bana i paketet ännu."
    />
  </div>
</section>

<section class="howto panel" aria-labelledby="h-read">
  <h2 id="h-read">Så läser du märkningen</h2>
  <ul>
    <li><RoleTag role="champion" id="B3" /> den registrerade huvudmodellen: B3 för N2, B1 för övriga. Bara den ger de skarpa intervallen.</li>
    <li><RoleTag role="shadow" /> räknas och utvärderas men styr ingenting: DF (faktormodellen) och hela D2.</li>
    <li><RoleTag role="baseline" id="B0/B1" /> den naiva jämförelsen. <RoleTag role="guidance" /> bolagets egen prognos där den finns.</li>
    <li><KindTag kind="skarp" /> lämnad före utfallet och committad; git-tidsstämpeln är beviset. <KindTag kind="backtest" /> räknad i efterhand med bara data som var kända då.</li>
  </ul>
</section>

<style>
  .cal {
    margin: 18px 0 22px;
  }
  .cards {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 14px;
    margin-top: 8px;
  }
  @media (min-width: 640px) {
    .cards {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
  @media (min-width: 981px) {
    .cards {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }
  .howto {
    margin: 22px 0 8px;
  }
  .howto ul {
    margin: 8px 0 0;
    padding: 0;
    list-style: none;
    display: grid;
    gap: 8px;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
</style>
