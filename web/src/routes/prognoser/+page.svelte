<!-- PLACEHOLDER (W4). Owner in wave 1: W8 (N1–N6: quantile dots, bands over time, calibration, PIT, CRPS, scorecard,
     one page per live forecast with commit link). -->
<script lang="ts">
  import { dateLabel, periodLabel } from '$lib/design';

  let { data } = $props();
</script>

<svelte:head><title>Prognoser – AI-utrullningen</title></svelte:head>

<h1>Prognoser</h1>
<p class="lede">Kalendern för skarpa prognoser. Varje prognos har intervall, och facit visas öppet.</p>
<table class="data">
  <caption>Nästa skarpa prognos per nowcast</caption>
  <thead><tr><th scope="col">Nowcast</th><th scope="col">Huvudmodell</th><th scope="col">Prognosdag</th><th scope="col">Avser</th><th scope="col">Skarpa hittills</th></tr></thead>
  <tbody>
    {#each data.calendar as c (c.id)}
      <tr>
        <th scope="row" style="font-weight:400">{c.label} {c.title}</th>
        <td>{c.champion ?? '–'}</td>
        <td>{c.next_origin ? dateLabel(c.next_origin) : '–'}</td>
        <td>{c.next_period ? periodLabel(c.next_period) : '–'}</td>
        <td>{c.n_live}</td>
      </tr>
    {/each}
  </tbody>
</table>
