<!-- Change in pace against the series' dead band (register section 2): a grey band ±deadband around zero and a dot.
     Right = more pace for every method (doubling and halving times are flipped, shorter = faster). The dot is in
     the direction colour from the pipeline; the sentence next to it carries the numbers, so this is aria-hidden.
     Track W6. -->
<script lang="ts">
  import { DIRECTIONS } from '$lib/design';
  import type { Dir } from './types';

  let {
    change,
    deadband,
    direction,
    inverted = false
  }: { change: number | null; deadband: number | null; direction: Dir; inverted?: boolean } = $props();

  const v = $derived(change === null ? null : inverted ? -change : change);
  const range = $derived(deadband && deadband > 0 ? Math.max(deadband * 2.5, Math.abs(v ?? 0) * 1.15) : Math.max(1, Math.abs(v ?? 0) * 1.15));
  const pos = (x: number) => 50 + (Math.max(-range, Math.min(range, x)) / range) * 50;
  const color = $derived(direction === null ? 'var(--c-muted)' : DIRECTIONS[direction].color);
</script>

<div class="gauge" aria-hidden="true">
  <span class="end">mindre takt</span>
  <div class="track">
    {#if deadband}
      <span class="band" style:left="{pos(-deadband)}%" style:right="{100 - pos(deadband)}%"></span>
    {/if}
    <span class="zero"></span>
    {#if v !== null}
      <span class="dot" style:left="{pos(v)}%" style:background={color}></span>
    {/if}
  </div>
  <span class="end">mer takt</span>
</div>

<style>
  .gauge {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 6px;
    font-size: 11px;
    color: var(--c-muted);
  }
  .end {
    white-space: nowrap;
  }
  .track {
    position: relative;
    flex: 1;
    height: 14px;
    border-bottom: 1px solid var(--c-axis);
  }
  .band {
    position: absolute;
    top: 2px;
    bottom: 0;
    background: var(--c-mid);
    border: 1px dashed var(--c-axis);
    border-bottom: 0;
  }
  .zero {
    position: absolute;
    left: 50%;
    top: 0;
    bottom: 0;
    border-left: 1px solid var(--c-ink-2);
  }
  .dot {
    position: absolute;
    top: 50%;
    width: 10px;
    height: 10px;
    margin: -5px 0 0 -5px;
    border-radius: 50%;
    border: 2px solid var(--c-surface);
    box-sizing: content-box;
    margin-left: -7px;
    margin-top: -7px;
  }
  @media (forced-colors: active) {
    .dot {
      forced-color-adjust: none;
    }
  }
</style>
