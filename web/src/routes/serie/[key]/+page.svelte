<!-- W7 Series instrument (docs/steg3/hemsida_vision.md 7, webb.md). W9 adds the global time travel on top of
     $lib/series/versions.ts (asOf) and the `as_of` hash parameter. -->
<script lang="ts">
  import { dataUrl, setChartData } from '$lib/design';
  import SeriesInstrument from '$lib/series/SeriesInstrument.svelte';

  let { data } = $props();
  setChartData(() => dataUrl(`series/${data.page.series.key}.json`));
  const status = $derived(data.site.record.status === 'live' ? 'live' : 'recon');
</script>

<svelte:head>
  <title>{data.page.series.label} – AI-utrullningen</title>
  <meta name="description" content="{data.page.series.label}: nivå, takt, förändring i takt och versioner. {data.page.series.license.attribution}" />
</svelte:head>

<SeriesInstrument data={data.page} recordStatus={status} />
