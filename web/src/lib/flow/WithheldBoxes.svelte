<!-- Withheld series (publish=False) as counted, named boxes (P9, section 4.1): name, source, licence, reason and
     whether it counts in the index. Never a value, never a per-series direction. Track W6. -->
<script lang="ts">
  import type { WithheldView } from './prepare';

  let { items, anon = 0 }: { items: WithheldView[]; anon?: number } = $props();
</script>

<ul class="held">
  {#each items as w (w.key)}
    <li class="box">
      <span class="name">{w.label}</span>
      {#if w.source}<span class="meta">Källa: {w.source}</span>{/if}
      <span class="meta">Skäl: {w.why}{w.license ? ` (licens: ${w.license})` : ''}</span>
      <span class="tag">{w.counted ? 'räknas i grenens index' : 'räknas inte'}</span>
    </li>
  {/each}
  {#each Array.from({ length: anon }, (_, i) => i) as i (i)}
    <li class="box">
      <span class="name">Inhållen serie</span>
      <span class="meta">Namn och skäl finns på grenens sida.</span>
    </li>
  {/each}
</ul>

<style>
  .held {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 250px), 1fr));
    gap: 10px;
  }
  .box {
    display: flex;
    flex-direction: column;
    gap: 3px;
    padding: 12px 14px;
    border: 1px dashed var(--c-ink-2);
    border-radius: var(--radius-md);
    background:
      repeating-linear-gradient(135deg, var(--c-grid) 0 1px, transparent 1px 9px),
      var(--c-surface);
    min-width: 0;
  }
  .name {
    font-weight: 600;
    font-size: 14px;
    line-height: 1.3;
  }
  .meta {
    font-size: 12px;
    color: var(--c-ink-2);
    overflow-wrap: anywhere;
  }
  .tag {
    margin-top: 4px;
    align-self: flex-start;
    font-size: 11px;
    border: 1px solid var(--c-axis);
    border-radius: var(--radius-pill);
    padding: 1px 8px;
    color: var(--c-ink-2);
    background: var(--c-surface);
  }
</style>
