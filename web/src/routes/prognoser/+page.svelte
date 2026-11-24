<!-- PLACEHOLDER (W4). Owner in wave 1: W8 (N1–N6: quantile dots, bands over time, calibration, PIT, CRPS, scorecard,
     one page per live forecast with commit link). -->
<script lang="ts">
  import { DataTable, dateLabel, periodLabel } from '$lib/design';

  let { data } = $props();
</script>

<svelte:head><title>Prognoser – AI-utrullningen</title></svelte:head>

<h1>Prognoser</h1>
<p class="lede">Kalendern för skarpa prognoser. Varje prognos har intervall, och facit visas öppet.</p>
<DataTable
  table={{
    caption: 'Nästa skarpa prognos per nowcast',
    columns: [
      { key: 'n', label: 'Nowcast' },
      { key: 'c', label: 'Huvudmodell', align: 'left' },
      { key: 'o', label: 'Prognosdag', align: 'left' },
      { key: 'p', label: 'Avser', align: 'left' },
      { key: 'k', label: 'Skarpa hittills' }
    ],
    rows: data.calendar.map((c) => ({
      n: `${c.label} ${c.title}`,
      c: c.champion ?? '–',
      o: c.next_origin ? dateLabel(c.next_origin) : '–',
      p: c.next_period ? periodLabel(c.next_period) : '–',
      k: c.n_live
    }))
  }}
/>
