<!-- A set of small multiples with one switch for the whole set: pace (the pipeline's measure, default and what the
     prerendered HTML shows) or level. The x domain is shared within the set. Track W6. -->
<script lang="ts">
  import SeriesMultiple from './SeriesMultiple.svelte';
  import { sharedDomain } from './prepare';
  import type { Multiple } from './types';

  let {
    items,
    label,
    showBranch = false,
    toggle = true
  }: { items: Multiple[]; label: string; showBranch?: boolean; toggle?: boolean } = $props();

  let mode = $state<'pace' | 'level'>('pace');
  const hasLevels = $derived(items.some((m) => m.levelPath));
  const domain = $derived(sharedDomain(items, mode));
</script>

{#if toggle && hasLevels}
  <div class="switch" role="group" aria-label="{label}: visa takt eller nivå">
    <button type="button" class="chip" aria-pressed={mode === 'pace'} onclick={() => (mode = 'pace')}>Takt</button>
    <button type="button" class="chip" aria-pressed={mode === 'level'} onclick={() => (mode = 'level')}>Nivå</button>
  </div>
{/if}
<div class="multiples" data-mode={mode}>
  {#each items as m (m.key)}
    <SeriesMultiple {m} {mode} {domain} {showBranch} />
  {/each}
</div>

<style>
  .switch {
    display: flex;
    gap: 6px;
    margin: 6px 0 12px;
  }
  .multiples {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 12px;
  }
  @media (min-width: 640px) {
    .multiples {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
  @media (min-width: 980px) {
    .multiples {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }
</style>
