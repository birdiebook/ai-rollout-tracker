<!-- Heading of every time-travel view: what the page shows, the record's status (P9: dashed = reconstructed,
     solid = live snapshot, with its commit link), and the rule that nothing later than the day is shown. -->
<script lang="ts">
  import type { Snippet } from 'svelte';
  import { page } from '$app/state';
  import { StatusBadge, dateLabel, periodLabel, type RecordStatus } from '$lib/design';

  let {
    kicker,
    title,
    day,
    month,
    known,
    status,
    extra
  }: { kicker: Snippet; title: string; day: string; month: string | null; known: string | null; status: RecordStatus; extra?: Snippet } = $props();
  const repo = $derived((page.data as { site?: { build?: { repo?: string | null } } }).site?.build?.repo ?? null);
</script>

<header class="head" data-tt="asof" data-known={known ?? ''}>
  <p class="kicker">{@render kicker()}</p>
  <h1>{title}</h1>
  <p class="rec">
    <StatusBadge {status} />
    {#if month && known}
      <span class="note">
        Underlaget är posten för {periodLabel(month, true)}, känd från {dateLabel(known)}{#if status === 'live' && repo}
          (<a href="{repo}/blob/main/snapshots/{month}.json">ögonblicksbilden i git</a>){/if}. Visas som den var känd den {dateLabel(day)}.
      </span>
    {/if}
  </p>
  {#if extra}{@render extra()}{/if}
</header>

<style>
  .head {
    margin-top: 18px;
  }
  .rec {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 10px;
    margin: 4px 0 8px;
  }
  .rec a {
    color: var(--c-ink-2);
  }
</style>
