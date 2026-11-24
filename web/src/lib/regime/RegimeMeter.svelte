<!-- P(inbromsning) for one block as a straight 0–100 % scale (not a speedometer) with the registered thresholds
     0,2 and 0,8 marked. The zones are neutral grey: a regime shift is a description, not an alarm. The reported
     state (two months in a row, register G-D) is a word next to the number. The track is aria-hidden; the
     sentence carries the numbers. Track W10. -->
<script lang="ts">
  import { fmt, periodLabel } from '$lib/design';
  import { RULES, cap, laneSentence, pctText } from './regime';
  import type { RegimeLane } from './types';

  let { lane }: { lane: RegimeLane } = $props();
  const p = $derived(lane.latest?.p ?? null);
  const lo = RULES.backAtMost * 100;
  const hi = RULES.shiftAtLeast * 100;
</script>

<article class="meter" class:empty={p === null}>
  <h3>{cap(lane.label)}</h3>
  <p class="now">
    {#if p === null}
      <span class="wait">–</span><span class="what">P(inbromsning) · inget skarpt värde än</span>
    {:else}
      <span class="big num">{pctText(p)}</span>
      <span class="what">P(inbromsning){lane.latest ? ` · ${periodLabel(lane.latest.month)}` : ''}</span>
    {/if}
  </p>
  <p class="state">
    Rapporterat tillstånd: <strong>{lane.latest?.state ?? 'inget än'}</strong>{#if lane.latest?.shift}<span class="shift">skifte denna månad</span>{/if}
  </p>
  <div class="track" aria-hidden="true">
    <span class="zone low" style:width="{lo}%"></span>
    <span class="zone high" style:left="{hi}%"></span>
    {#if p !== null}<span class="mark" style:left="{p * 100}%"></span>{/if}
  </div>
  <div class="scale" aria-hidden="true">
    <span style:left="0%">0</span>
    <span style:left="{lo}%">{fmt(RULES.backAtMost, 1)}</span>
    <span style:left="{hi}%">{fmt(RULES.shiftAtLeast, 1)}</span>
    <span style:left="100%">1</span>
  </div>
  <p class="zones" aria-hidden="true"><span>≤ {fmt(RULES.backAtMost, 1)}: tillbaka till expansion</span><span>≥ {fmt(RULES.shiftAtLeast, 1)}: skifte till inbromsning</span></p>
  {#if p !== null}<p class="sentence">{laneSentence(lane)}</p>{/if}
</article>

<style>
  .meter {
    display: grid;
    gap: 4px;
    min-width: 0;
  }
  h3 {
    margin: 0;
    font-size: var(--fs-subsection);
  }
  .now {
    margin: 0;
    display: flex;
    align-items: baseline;
    gap: 8px;
    flex-wrap: wrap;
  }
  .big {
    font-size: clamp(30px, 4.4vw, 44px);
    font-weight: 650;
    line-height: 1.1;
  }
  .wait {
    font-size: 22px;
    color: var(--c-muted);
  }
  .what,
  .state {
    font-size: var(--fs-small);
    color: var(--c-ink-2);
    margin: 0;
  }
  .shift {
    display: inline-block;
    white-space: nowrap;
    margin-left: 8px;
    font-size: 11px;
    border: 1px solid var(--c-axis);
    border-radius: var(--radius-pill);
    padding: 0 7px;
  }
  .track {
    position: relative;
    height: 18px;
    margin-top: 8px;
    border: 1px solid var(--c-axis);
    border-radius: 3px;
    background: var(--c-surface);
  }
  .empty .track {
    border-style: dashed;
  }
  .zone {
    position: absolute;
    top: 0;
    bottom: 0;
    background: var(--c-mid);
  }
  .zone.low {
    left: 0;
    border-right: 1.5px dashed var(--c-ink-2);
  }
  .zone.high {
    right: 0;
    border-left: 1.5px dashed var(--c-ink-2);
  }
  .mark {
    position: absolute;
    top: -5px;
    bottom: -5px;
    width: 4px;
    margin-left: -2px;
    background: var(--c-ink);
    border-radius: 2px;
    box-shadow: 0 0 0 2px var(--c-surface);
  }
  .scale {
    position: relative;
    height: 16px;
    font-size: 11px;
    color: var(--c-muted);
    font-variant-numeric: tabular-nums;
  }
  .scale span {
    position: absolute;
    transform: translateX(-50%);
  }
  .scale span:first-child {
    transform: none;
  }
  .scale span:last-child {
    transform: translateX(-100%);
  }
  .zones {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    margin: 0;
    font-size: 11px;
    color: var(--c-muted);
  }
  .zones span:last-child {
    text-align: right;
  }
  .sentence {
    margin: 4px 0 0;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  @media (forced-colors: active) {
    .mark {
      background: CanvasText;
    }
  }
</style>
