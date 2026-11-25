<!-- W14: the quarterly report under global time travel (as_of = D). A quarter's report only uses what was known on
     its report day (the quarter's last month-end record), so it is shown when that day is on or before D. Otherwise
     the page says when it became known and points to the latest report known on D. The page data is checked again
     with the gate's leaks() against D before it is drawn; the quarter list is cut to the quarters known on D. -->
<script lang="ts">
  import { page as appPage } from '$app/state';
  import { dateLabel } from '$lib/design';
  import { LeakError, leaks } from '$lib/timetravel/gate';
  import ReportView from './ReportView.svelte';
  import { quarterHref } from './links';
  import { quartersKnownOn, type ReportPage } from './model';

  let { day }: { day: string; params: Record<string, string> } = $props();
  const p = $derived((appPage.data as { page?: ReportPage }).page ?? null);
  const shown = $derived(p !== null && p.day <= day);
  const quarters = $derived(p ? quartersKnownOn(p.quarters, day) : []);
  const latest = $derived(quarters.at(-1) ?? null);
  const view = $derived.by(() => {
    if (!p || !shown) return null;
    const bad = leaks({ ...p, quarters: [] }, day);
    if (bad.length) throw new LeakError(bad);
    return p;
  });
</script>

{#if view}
  <ReportView page={view} {quarters} />
{:else if p}
  <section class="tt-none" data-tt="report-unknown">
    <h1>Kvartalsrapporten för {p.report.quarter_sv} var inte känd {dateLabel(day)}</h1>
    <p class="lede">Den bygger på kvartalets sista månadsläge, som blev känt {dateLabel(p.day)}.</p>
    {#if latest}
      <p><a href={quarterHref(latest.quarter)}>Senaste kvartalsrapporten som var känd då: {latest.quarter_sv}</a></p>
    {:else}
      <p class="note">Ingen kvartalsrapport var känd ännu.</p>
    {/if}
  </section>
{/if}

<style>
  .tt-none {
    margin-top: 28px;
  }
</style>
