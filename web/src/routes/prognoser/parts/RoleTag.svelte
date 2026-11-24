<!-- Model role tag (W8): the registered main model has a solid ring and a filled model-coloured dot; a shadow,
     baseline or guidance variant has a dashed ring. The word is always written out (P9: honesty is visible). -->
<script lang="ts">
  let {
    role,
    id,
    title
  }: { role: 'champion' | 'shadow' | 'baseline' | 'guidance'; id?: string; title?: string } = $props();
  const WORD = { champion: 'Huvudmodell', shadow: 'Skugga', baseline: 'Naiv baslinje', guidance: 'Guidance' };
</script>

<span class="role" data-role={role} {title}>
  <span class="dot" aria-hidden="true"></span>{WORD[role]}{#if id}&nbsp;<b>{id}</b>{/if}
</span>

<style>
  .role {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    line-height: 1.4;
    color: var(--c-ink-2);
    border: 1px dashed var(--c-axis);
    border-radius: 999px;
    padding: 2px 9px;
    white-space: nowrap;
  }
  .role b {
    color: var(--c-ink);
    font-weight: 620;
  }
  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    border: 1.5px solid var(--c-base);
    background: transparent;
  }
  [data-role='champion'] {
    border-style: solid;
    border-color: var(--c-ink-2);
  }
  [data-role='champion'] .dot {
    background: var(--c-model);
    border-color: var(--c-model);
  }
  [data-role='guidance'] .dot {
    border-radius: 1px;
    transform: rotate(45deg);
    border-color: var(--c-ink-2);
  }
  @media (forced-colors: active) {
    .dot {
      border-color: CanvasText;
    }
  }
</style>
