<!-- W8: one nowcast as a story in three acts (section 3.4): before (the latest live forecast as 20 equally likely
     outcomes and the calendar), the outcome (forecasts and outcomes over time, facit against baseline and guidance)
     and after (calibration: live, honest about small n, and the backtest, always marked). D2 has its own view, and
     every live forecast its own permanent page. -->
<script lang="ts">
  import NowcastView from '../../parts/NowcastView.svelte';
  import HorizonsView from '../../parts/HorizonsView.svelte';
  import ForecastPage from '../../parts/ForecastPage.svelte';

  let { data } = $props();
</script>

{#if data.kind === 'd2'}
  <HorizonsView d2={data.d2} site={data.site} />
{:else if data.kind === 'forecast'}
  <ForecastPage nc={data.nc} slug={data.slug} site={data.site} />
{:else}
  <NowcastView nc={data.nc} site={data.site} />
{/if}
