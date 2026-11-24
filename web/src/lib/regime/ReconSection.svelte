<!-- One reconciliation: name, definition and the pipeline's measures (level, pace with its percentile, change in
     pace against the dead band, direction), then the ratio over time, the pace split into its components, the
     numerator and denominator on one indexed axis, and the component series. Track W10. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { Glyph, dateLabel, fmt, periodLabel, signed } from '$lib/design';
  import { DeadbandGauge } from '$lib/flow';
  import Components from './Components.svelte';
  import ContributionChart from './ContributionChart.svelte';
  import RatioChart from './RatioChart.svelte';
  import { REST_TOLERANCE, levelText, ordinal } from './recon';
  import type { ReconView } from './types';

  let { r }: { r: ReconView } = $props();
  const inside = $derived(r.change_in_pace !== null && r.deadband !== null ? Math.abs(r.change_in_pace) <= r.deadband : null);
  const restNote = $derived(r.max_rest !== null && r.max_rest >= REST_TOLERANCE);
</script>

<section class="rc panel" id={r.key} aria-labelledby="{r.key}-h">
  <header class="top">
    <div class="name">
      <p class="kick"><span class="tag">{r.lead}</span><span class="nc">räknas inte i grenarnas index</span></p>
      <h2 id="{r.key}-h">{r.short}</h2>
      <p class="label">{r.label}</p>
      {#if r.question}<p class="q">{r.question}</p>{/if}
      {#if r.formula}<p class="formula"><span class="visually-hidden">Definition: </span>{r.formula}</p>{/if}
    </div>
    <dl class="facts">
      <div>
        <dt>Nivå {r.latest_period ? periodLabel(r.latest_period) : ''}</dt>
        <dd class="big num">{levelText(r.level, r.unit)}</dd>
        <dd class="sub">{r.unit}{r.known_from ? ` · känd ${dateLabel(r.known_from)}` : ''}</dd>
      </div>
      <div>
        <dt>Takt</dt>
        <dd class="mid num">{signed(r.pace, 1)}</dd>
        <dd class="sub">{ordinal(r.pace_percentile)}{r.n_pace ? ` av ${r.n_pace}` : ''}</dd>
        <dd class="pbar" aria-hidden="true"><span style:left="{r.pace_percentile ?? 0}%" class:none={r.pace_percentile === null}></span></dd>
      </div>
      <div>
        <dt>Riktning</dt>
        <dd class="mid">{#if r.direction !== null}<Glyph direction={r.direction} />{:else}<span class="sub">ingen riktning</span>{/if}</dd>
        <dd class="sub">
          förändring i takt {signed(r.change_in_pace, 1)}{r.deadband !== null ? `, dödband ±${fmt(r.deadband, 1)}` : ''}{inside === null ? '' : inside ? ' (inom)' : ' (utanför)'}
        </dd>
        <dd><DeadbandGauge change={r.change_in_pace} deadband={r.deadband} direction={r.direction} /></dd>
      </div>
    </dl>
  </header>

  {#if !r.valid && r.reason}<p class="note">Inget giltigt mått: {r.reason}.</p>{/if}

  <div class="charts">
    <RatioChart {r} mode="ratio" />
    <ContributionChart {r} />
    <RatioChart {r} mode="sides" />
  </div>
  {#if restNote}
    <p class="note warn">
      Komponenterna och kvoten går inte ihop helt (största rest {signed(r.max_rest, 1)}). Resten ritas för sig och döljs inte.
    </p>
  {/if}

  <Components items={r.components} />

  <p class="foot note">
    Mått och riktning ur posten ({r.method === 'log' ? 'årsförändring i log(kvot) ×100' : (r.method ?? '')}).
    Bidragen är den exakta uppdelningen av samma takt, ur komponenternas nivåer som de var kända på postens datum.
    {#if r.source}Källa: {r.source}.{/if}
    {#if r.license}Licens: {r.license}.{/if}
    {#if r.linkable}<a href={resolve('/serie/[key]', { key: r.key })}>Kvoten som serie →</a>{/if}
  </p>
</section>

<style>
  .rc {
    display: grid;
    gap: 16px;
    scroll-margin-top: 16px;
  }
  .top {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 14px 24px;
  }
  @media (min-width: 900px) {
    .top {
      grid-template-columns: minmax(0, 1fr) minmax(0, 1.25fr);
    }
  }
  .kick {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 0 0 4px;
  }
  .tag,
  .nc {
    font-size: 11px;
    border-radius: var(--radius-pill);
    padding: 1px 8px;
    border: 1px solid var(--c-axis);
    color: var(--c-ink-2);
  }
  .nc {
    border-style: dashed;
  }
  h2 {
    margin: 0;
    font-size: var(--fs-section);
  }
  .label,
  .q {
    margin: 2px 0 0;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  .q {
    font-style: italic;
  }
  .formula {
    margin: 6px 0 0;
    font-family: var(--mono);
    font-size: 12px;
    color: var(--c-ink-2);
    overflow-wrap: anywhere;
  }
  .facts {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin: 0;
  }
  @media (max-width: 560px) {
    .facts {
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    }
    .facts > div:last-child {
      grid-column: 1 / -1;
    }
  }
  dt {
    font-size: 12px;
    color: var(--c-muted);
  }
  dd {
    margin: 0;
  }
  .big {
    font-size: clamp(28px, 4vw, 40px);
    font-weight: 650;
    line-height: 1.15;
  }
  .mid {
    font-size: 20px;
    font-weight: 620;
    line-height: 1.4;
  }
  .sub {
    font-size: 12px;
    color: var(--c-ink-2);
  }
  .pbar {
    position: relative;
    height: 10px;
    margin-top: 6px;
    border-bottom: 1px solid var(--c-axis);
    background: linear-gradient(to right, transparent 25%, var(--c-mid) 25% 75%, transparent 75%);
  }
  .pbar span {
    position: absolute;
    top: 1px;
    width: 3px;
    height: 9px;
    margin-left: -1.5px;
    background: var(--c-ink);
  }
  .pbar span.none {
    display: none;
  }
  .charts {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 18px;
  }
  @media (min-width: 1000px) {
    .charts {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }
  .note {
    margin: 0;
  }
  .warn {
    border-left: 3px solid var(--c-axis);
    padding-left: 8px;
    color: var(--c-ink-2);
  }
</style>
