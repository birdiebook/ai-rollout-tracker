<!-- /kvartal/[kvartal] (W14): the quarterly report as a visual essay (ai_tracker.quarterly via site_bundle.report).
     Components and the model live in $lib/report/. -->
<script lang="ts">
  import ReportView from '$lib/report/ReportView.svelte';

  let { data } = $props();
</script>

<svelte:head>
  <title>Kvartalsrapporten – {data.page.report.quarter_sv}</title>
  <meta name="description" content={data.page.report.headline} />
</svelte:head>

<ReportView page={data.page} />
