<!-- "One number" tiles (section 4.5): level, pace, change in pace and surprise, as the state engine computed them on
     the record date. Each tile has a small picture: the pace's percentile on 0–100, and the change in pace against
     the dead band, so the direction is seen, not only read (colour + glyph + word, P3). -->
<script lang="ts">
  import { DIRECTIONS, Glyph, dateLabel, fmt } from '$lib/design';
  import { periodText } from './period';
  import { num, ordinal, paceSign, snum } from './text';
  import type { Measure } from './types';

  let {
    measure,
    unit,
    last
  }: {
    measure: Measure | null;
    unit: string;
    /** latest level in the series' own frequency */
    last: { p: string; v: number } | null;
  } = $props();

  const m = $derived(measure);
  const hasPace = $derived(m?.pace !== null && m?.pace !== undefined);
  const hasChange = $derived(m?.change_in_pace !== null && m?.change_in_pace !== undefined);
  const dir = $derived(m?.direction ?? null);
  const sign = $derived(paceSign(m?.method));
  // dead-band picture: right = more pace for every method (doubling/halving times are read the other way)
  const span = $derived(Math.max(Math.abs(m?.change_in_pace ?? 0) * 1.25, (m?.deadband ?? 0) * 3, 1e-9));
  /** position in % of the meter for a value already oriented so that right = more pace */
  const pos = (v: number) => Math.max(0, Math.min(100, 50 + (v / span) * 46));
</script>

<div class="tiles">
  <div class="tile">
    <h2 class="t-title">Nivå</h2>
    {#if last}
      <p class="big num">{num(last.v)}</p>
      <p class="sub">{unit}</p>
      <p class="sub">{periodText(last.p, true)}</p>
    {:else}
      <p class="sub">Inga värden ännu.</p>
    {/if}
  </div>

  <div class="tile">
    <h2 class="t-title">Takt</h2>
    {#if hasPace}
      <p class="big num">{snum(m?.pace)}</p>
      <p class="sub">{m?.pace_unit} · {periodText(m?.latest_period ?? '')}</p>
      {#if m?.pace_percentile !== null && m?.pace_percentile !== undefined}
        {@const p = m.pace_percentile}
        <div class="meter" role="img" aria-label="Takten ligger på den {ordinal(p)} percentilen av seriens egen historik">
          <div class="rail"></div>
          {#each [0, 50, 100] as q (q)}<span class="tick" style:left="{q}%"></span><span class="tl" style:left="{q}%">{q}</span>{/each}
          <span class="dot" style:left="{Math.max(0, Math.min(100, p))}%" style:background="var(--c-ink)"></span>
        </div>
        <p class="sub">{ordinal(p)} percentilen av egen historik{m?.n_pace ? ` (${fmt(m.n_pace)} perioder)` : ''}</p>
      {:else}
        <p class="sub">För kort historik för percentil.</p>
      {/if}
    {:else}
      <p class="sub">{m?.reason || 'Ingen takt på senaste perioden.'}</p>
    {/if}
  </div>

  <div class="tile">
    <h2 class="t-title">Förändring i takt</h2>
    {#if hasChange}
      <p class="big num">{snum(m?.change_in_pace)}</p>
      <p class="sub">{#if dir !== null}<Glyph direction={dir} />{:else}ingen riktning{/if}</p>
      {#if m?.deadband !== null && m?.deadband !== undefined}
        {@const db = m.deadband}
        {@const c = m.change_in_pace ?? 0}
        <div class="meter" role="img" aria-label="Förändringen i takt {snum(c)} mot dödbandet ±{num(db, db)}">
          <div class="rail thin"></div>
          <span class="band" style:left="{pos(-db)}%" style:width="{Math.max(1, pos(db) - pos(-db))}%"></span>
          <span class="tick zero" style:left="50%"></span>
          <span class="tl start">mindre takt</span><span class="tl end">mer takt</span>
          <span class="dot" style:left="{pos(c * sign)}%" style:background={dir !== null ? DIRECTIONS[dir].color : 'var(--c-ink)'}></span>
        </div>
        <p class="sub">dödband ±{num(db, db)} (0,25 × standardavvikelsen {num(m.sd_change, m.sd_change ?? undefined)})</p>
      {/if}
    {:else}
      <p class="sub">{m?.reason || 'Ingen förändring i takt på senaste perioden.'}</p>
    {/if}
  </div>

  <div class="tile">
    <h2 class="t-title">Överraskning</h2>
    {#if m?.surprise !== null && m?.surprise !== undefined}
      <p class="big num">{snum(m.surprise)}</p>
      <p class="sub">utfall mot {m.surprise_basis ?? 'baslinje'}</p>
    {:else}
      <p class="sub">Ingen överraskning beräknad.</p>
    {/if}
    {#if m?.known_from}<p class="sub">Senaste period känd från {dateLabel(m.known_from)}</p>{/if}
  </div>
</div>

<style>
  .tiles {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }
  @media (min-width: 861px) {
    .tiles {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }
  }
  .tile {
    background: var(--c-surface);
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-lg);
    padding: 14px 16px;
    min-width: 0;
  }
  .t-title {
    font-size: var(--fs-small);
    font-weight: 600;
    color: var(--c-ink-2);
    margin: 0;
  }
  .big {
    font-size: clamp(26px, 4vw, 40px);
    font-weight: 650;
    letter-spacing: -0.02em;
    line-height: 1.15;
    margin: 4px 0 2px;
    font-variant-numeric: tabular-nums;
    overflow-wrap: anywhere;
  }
  .sub {
    margin: 2px 0 0;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  .meter {
    position: relative;
    height: 34px;
    margin: 10px 6px 0;
    max-width: 260px;
  }
  .rail {
    position: absolute;
    left: 0;
    right: 0;
    top: 9px;
    height: 6px;
    border-radius: 3px;
    background: var(--c-grid);
  }
  .rail.thin {
    top: 11px;
    height: 1px;
    background: var(--c-axis);
  }
  .band {
    position: absolute;
    top: 4px;
    height: 16px;
    border-radius: 3px;
    background: var(--c-grid);
    border: 1px solid var(--c-axis);
  }
  .tick {
    position: absolute;
    top: 6px;
    width: 1px;
    height: 12px;
    background: var(--c-axis);
  }
  .tick.zero {
    top: 2px;
    height: 20px;
    background: var(--c-ink-2);
  }
  .tl {
    position: absolute;
    top: 21px;
    font-size: 11px;
    line-height: 1;
    color: var(--c-muted);
    transform: translateX(-50%);
    white-space: nowrap;
  }
  .tl.start {
    left: 0;
    transform: none;
  }
  .tl.end {
    right: 0;
    transform: none;
  }
  .dot {
    position: absolute;
    top: 6px;
    width: 12px;
    height: 12px;
    margin-left: -6px;
    border-radius: 50%;
    box-shadow: 0 0 0 2px var(--c-surface);
  }
  @media (forced-colors: active) {
    .dot {
      forced-color-adjust: none;
    }
  }
</style>
