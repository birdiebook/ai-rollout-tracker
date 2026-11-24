<!-- Tooltip for one chart. Positioned inside the ChartFrame; flips left/up near the edges. Text only. -->
<script lang="ts">
  import type { TooltipState } from './tooltip.svelte';

  let { state, hostWidth = 640 }: { state: TooltipState; hostWidth?: number } = $props();
  const flipX = $derived(state.x > hostWidth - 200);
</script>

{#if state.visible && state.content}
  <div
    class="tip"
    role="status"
    style:left="{state.x}px"
    style:top="{state.y}px"
    style:transform="translate({flipX ? 'calc(-100% - 12px)' : '12px'}, calc(-100% - 8px))"
  >
    <b>{state.content.title}</b>
    {#if state.content.rows}
      <dl>
        {#each state.content.rows as [k, v] (k)}
          <dt>{k}</dt>
          <dd>{v}</dd>
        {/each}
      </dl>
    {/if}
    {#if state.content.note}<span class="t-muted">{state.content.note}</span>{/if}
  </div>
{/if}

<style>
  .tip {
    position: absolute;
    pointer-events: none;
    z-index: 20;
    background: var(--c-surface);
    color: var(--c-ink);
    border: 1px solid var(--c-ring);
    border-radius: 10px;
    padding: 8px 10px;
    font-size: var(--fs-small);
    line-height: 1.35;
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.14);
    max-width: 280px;
    width: max-content;
    font-variant-numeric: tabular-nums;
  }
  b {
    font-weight: 620;
    display: block;
  }
  dl {
    display: grid;
    grid-template-columns: auto auto;
    gap: 0 10px;
    margin: 2px 0 0;
  }
  dt {
    color: var(--c-ink-2);
  }
  dd {
    margin: 0;
    text-align: right;
  }
  .t-muted {
    color: var(--c-muted);
    font-size: 12px;
    display: block;
    margin-top: 2px;
  }
</style>
