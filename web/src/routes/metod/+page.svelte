<!-- PLACEHOLDER (W4). Owner in wave 1: W11 (explorable method: drag the dead band, interval level, as_of). -->
<script lang="ts">
  import { fmt } from '$lib/design';

  let { data } = $props();
  const rules = $derived((data.method.rules as Record<string, number> | undefined) ?? {});
</script>

<svelte:head><title>Metod – AI-utrullningen</title></svelte:head>

<h1>Metod</h1>
<p class="lede">Mått, tillståndsregler och intervall är låsta i måttregistret innan data analyseras.</p>
<dl class="panel rules">
  <dt>Dödband</dt><dd class="num">{fmt(rules.deadband_sd, 2)} sd</dd>
  <dt>Accelererar vid index ≥</dt><dd class="num">{fmt(rules.accelerating_at_least, 2)}</dd>
  <dt>Bromsar in vid index ≤</dt><dd class="num">{fmt(rules.braking_at_most, 2)}</dd>
</dl>

<style>
  .rules {
    display: grid;
    grid-template-columns: auto auto;
    justify-content: start;
    gap: 4px 24px;
    margin-top: 16px;
  }
  dd {
    margin: 0;
  }
</style>
