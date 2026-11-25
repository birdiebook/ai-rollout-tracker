<!-- W13: the monthly story under global time travel (as_of = D). A month's story only uses what was known on the
     month's known day (gate.monthKnown), so it is shown when that day is on or before D. Otherwise the page says
     when it became known and points to the latest story known on D. The page data is checked again with the gate's
     leaks() against D before it is drawn; the month list is cut to the months known on D. -->
<script lang="ts">
  import { page as appPage } from '$app/state';
  import { dateLabel } from '$lib/design';
  import { LeakError, leaks, monthKnown } from '$lib/timetravel/gate';
  import StoryView from './StoryView.svelte';
  import { monthHref } from './links';
  import { monthsKnownOn, type StoryPage } from './model';

  let { day }: { day: string; params: Record<string, string> } = $props();
  const p = $derived((appPage.data as { page?: StoryPage }).page ?? null);
  const known = $derived(p ? monthKnown(p.story.month, { month: p.story.month, date: p.story.known, status: p.story.status }) : null);
  const shown = $derived(p !== null && known !== null && known <= day);
  const months = $derived(p ? monthsKnownOn(p.months, day) : []);
  const latest = $derived(months.at(-1) ?? null);
  const view = $derived.by(() => {
    if (!p || !shown) return null;
    const bad = leaks({ ...p, months: [], next: null }, day);
    if (bad.length) throw new LeakError(bad);
    return p;
  });
</script>

{#if view}
  <StoryView page={view} {months} />
{:else if p}
  <section class="tt-none" data-tt="story-unknown">
    <h1>Berättelsen för {p.story.month_sv} var inte känd {dateLabel(day)}</h1>
    <p class="lede">Den bygger på månadens ögonblicksbild, som blev känd {dateLabel(known ?? p.story.known)}.</p>
    {#if latest}
      <p><a href={monthHref(latest.month)}>Senaste berättelsen som var känd då: {latest.month_sv}</a></p>
    {:else}
      <p class="note">Ingen månads berättelse var känd ännu.</p>
    {/if}
  </section>
{/if}

<style>
  .tt-none {
    margin-top: 28px;
  }
</style>
