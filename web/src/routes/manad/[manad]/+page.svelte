<!-- /manad/[manad] (W13): the monthly story, cards chosen by the pre-registered rule (docs/mattregister.md
     2026-11-25). Components and the model live in $lib/story/. -->
<script lang="ts">
  import { dataUrl, setChartData } from '$lib/design';
  import StoryView from '$lib/story/StoryView.svelte';

  let { data } = $props();
  setChartData(() => dataUrl(`story/${data.page.story.month}.json`));
</script>

<svelte:head>
  <title>Månadens berättelse – {data.page.story.month_sv}</title>
  <meta name="description" content={data.page.story.headline} />
</svelte:head>

<StoryView page={data.page} />
