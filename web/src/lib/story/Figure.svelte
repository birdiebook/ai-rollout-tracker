<!-- W13: the one figure of a story card, from existing components (lib/flow, lib/regime, routes/prognoser/parts) and
     the design system. Data: the card's figure, cut to the month's known day by the gate (model.ts). -->
<script lang="ts">
  import { fmt, type RecordStatus } from '$lib/design';
  import { IndexHistory } from '$lib/flow';
  import { RegimeMeter } from '$lib/regime';
  import ForecastDots from '../../routes/prognoser/parts/ForecastDots.svelte';
  import StoryStripes from './StoryStripes.svelte';
  import TrackChart from './TrackChart.svelte';
  import type { CardView } from './model';

  let { card }: { card: CardView } = $props();
  const status = $derived<RecordStatus>(card.status === 'live' ? 'live' : 'recon');
  const f = $derived(card.figure);
  const id = $derived(`fig-${card.id}`);
</script>

<div class="figure" data-figure={f.kind}>
  {#if f.kind === 'stripes'}
    <StoryStripes {id} stripes={f.stripes} highlight={f.highlight} {status} />
  {:else if f.kind === 'index'}
    <IndexHistory {id} title={`${f.code} ${f.name}: diffusionsindex`} history={f.history} {status} height={210} headingLevel={3} />
  {:else if f.kind === 'meter'}
    <div class="meter" role="group" aria-label={`P(inbromsning) för blocket ${f.lane.label}`}>
      <p class="kicker">P(inbromsning), blocket {f.lane.label}</p>
      <RegimeMeter lane={f.lane} />
    </div>
  {:else if f.kind === 'forecast'}
    <ForecastDots {id} row={f.row} unit={f.unit} format={(v) => fmt(v ?? null, f.decimals)} title="Prognosen som 20 lika sannolika utfall, och utfallet" />
  {:else if f.kind === 'track'}
    <TrackChart {id} track={f.track} month={f.month} direction={f.direction} unit={f.unit} {status} />
  {:else}
    <p class="note">{f.why}</p>
  {/if}
</div>

<style>
  .figure {
    background: var(--c-surface);
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-lg);
    padding: 14px;
  }
  .meter .kicker {
    margin: 0 0 8px;
  }
</style>
