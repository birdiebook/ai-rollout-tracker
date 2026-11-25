<!-- Start page /next/ (W5): "AI-flödet denna månad" (docs/steg3/hemsida_vision.md 3.1). Headline sentence from the
     data, the chain L1→L9 as the spine, three question cards, the state stripes and the ways on. Components and the
     view model live in $lib/start/; data comes only through the typed loaders (+page.server.ts). -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { dataUrl, dateLabel, fmt, periodLabel, setChartData } from '$lib/design';
  import Calibration from '$lib/start/Calibration.svelte';
  import CalendarChart from '$lib/start/CalendarChart.svelte';
  import Chain from '$lib/start/Chain.svelte';
  import Changed from '$lib/start/Changed.svelte';
  import Explore from '$lib/start/Explore.svelte';
  import ForecastDots from '$lib/start/ForecastDots.svelte';
  import Hero from '$lib/start/Hero.svelte';
  import NowDots from '$lib/start/NowDots.svelte';
  import QuestionCard from '$lib/start/QuestionCard.svelte';
  import StateStripes from '$lib/start/StateStripes.svelte';
  import { moveCounts, upcoming } from '$lib/start/model';

  let { data } = $props();
  setChartData(() => dataUrl('overview.json'));
  const s = $derived(data.start);
  const moves = $derived(moveCounts(s.branches));
  const next = $derived(upcoming(s.calendar)[0] ?? null);
  const shifts = $derived(s.regime.blocks.filter((b) => b.shift));
</script>

<svelte:head>
  <title>AI-utrullningen – läget {periodLabel(s.record.month, true)}</title>
  <meta name="description" content={s.headline.sentence} />
</svelte:head>

<Hero start={s} />

<p class="story-entry">
  <a href={resolve('/manad/[manad]', { manad: s.record.month })}>Månadens berättelse, {periodLabel(s.record.month, true)} <span aria-hidden="true">→</span></a>
  <span class="note">det som hände enligt den förregistrerade urvalsregeln, kort för kort</span>
</p>
{#if data.report}
  <p class="report-entry">
    <a href={resolve('/kvartal/[kvartal]', { kvartal: data.report.quarter })}>Kvartalsrapporten, {data.report.quarter_sv}{data.report.kind === 'rekonstruerad' ? ' (rekonstruerad)' : ''} <span aria-hidden="true">→</span></a>
    <span class="note">kedjan, flödena, prognoserna och regimen över kvartalet</span>
  </p>
{/if}

<Chain start={s} />

<section class="grid3 questions" aria-label="Tre frågor">
  <QuestionCard n={1} id="q-now" question="Var står vi nu?">
    {#snippet answer()}
      {#if moves.n && s.headline.prevMonth}
        Sedan {periodLabel(s.headline.prevMonth, true)} har {moves.up} {moves.up === 1 ? 'gren' : 'grenar'} fått högre index,
        {moves.down} lägre och {moves.same} samma.
      {:else}
        Grenarnas läge mellan alla serier som minskar takten (0) och alla som ökar den (1).
      {/if}
    {/snippet}
    <NowDots start={s} />
  </QuestionCard>

  <QuestionCard n={2} id="q-ahead" question="Vart är vi på väg?">
    {#snippet answer()}
      {#if s.forecast}
        Senaste skarpa prognos: {s.forecast.label} {fmt(s.forecast.value, s.forecast.decimals)} {s.forecast.unit} för
        {periodLabel(s.forecast.period)}{#if next}. Nästa lämnas {dateLabel(next.date)}{/if}.
      {:else if next}
        Ingen skarp prognos är lämnad ännu. Den första, {next.items.map((c) => c.label).join(' och ')}, lämnas
        {dateLabel(next.date)}, före utfallet.
      {:else}
        Ingen skarp prognos är planerad.
      {/if}
    {/snippet}
    <CalendarChart start={s} />
    {#if s.forecast}<ForecastDots forecast={s.forecast} />{/if}
    {#if s.calibration}<Calibration c={s.calibration} />{/if}
  </QuestionCard>

  <QuestionCard n={3} id="q-changed" question="Har något fundamentalt ändrats?">
    {#snippet answer()}
      {#if s.regime.available}
        {shifts.length === 0
          ? `Inget av ${s.regime.blocks.length} block har ett registrerat regimskifte.`
          : `${shifts.length} av ${s.regime.blocks.length} block har ett registrerat regimskifte: ${shifts.map((b) => `${b.label} (${b.shift})`).join(', ')}.`}
      {:else}
        Regimmodellen väntar på den första skarpa ögonblicksbilden. Avstämningarna visar redan var takten ligger.
      {/if}
    {/snippet}
    <Changed start={s} />
  </QuestionCard>
</section>

<section aria-labelledby="stripes-h">
  <h2 id="stripes-h">Hur tillstånden har skiftat</h2>
  <p class="note intro">Varje ruta är en gren en månad. Färgen säger riktning, inte om det är bra eller dåligt.</p>
  <div class="panel"><StateStripes start={s} /></div>
</section>

<Explore start={s} />

<style>
  .questions {
    align-items: start;
  }
  .intro {
    margin: 0 0 10px;
  }
  .story-entry {
    margin: 6px 0 18px;
    display: flex;
    flex-wrap: wrap;
    gap: 4px 12px;
    align-items: baseline;
  }
  .story-entry a {
    font-weight: 600;
  }
  /* W14: the quarterly report's entry, right under the monthly story's and in the same form */
  .story-entry:has(+ .report-entry) {
    margin-bottom: 4px;
  }
  .report-entry {
    margin: 0 0 18px;
    display: flex;
    flex-wrap: wrap;
    gap: 4px 12px;
    align-items: baseline;
  }
  .report-entry a {
    font-weight: 600;
  }
</style>
