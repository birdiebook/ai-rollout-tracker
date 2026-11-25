<!-- One small multiple (section 4.1): a series' pace (pipeline measure path) or level, neutral ink, the latest point
     in the direction colour, the dead-band gauge for the change in pace, and a link to the series instrument.
     The x domain is shared by the whole set so the multiples line up in time. Track W6. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { scaleLinear, scaleLog } from 'd3-scale';
  import { Axis, ChartFrame, DIRECTIONS, Glyph, Line, dataUrl, fmt, periodLabel, signed } from '$lib/design';
  import DeadbandGauge from './DeadbandGauge.svelte';
  import { deadbandSentence, invertedPace, multipleSentence, periodTime } from './prepare';
  import type { Multiple } from './types';

  let {
    m,
    mode,
    domain,
    showBranch = false
  }: { m: Multiple; mode: 'pace' | 'level'; domain: [number, number] | null; showBranch?: boolean } = $props();

  const xy = $derived(mode === 'pace' ? m.pacePath : m.levelPath);
  const pts = $derived(
    xy ? xy.periods.map((p, i) => ({ t: periodTime(p), p, v: xy.values[i] })).filter((d) => Number.isFinite(d.t)) : []
  );
  const vals = $derived(pts.map((d) => d.v).filter((v): v is number => v !== null));
  const inverted = $derived(mode === 'pace' && invertedPace(m.method));
  const useLog = $derived(
    mode === 'level' && vals.length > 1 && Math.min(...vals) > 0 && ['log', 'doubling', 'halving'].includes(m.method ?? '') && Math.max(...vals) / Math.min(...vals) > 4
  );
  const yDomain = $derived.by((): [number, number] => {
    if (!vals.length) return [0, 1];
    let lo = Math.min(...vals);
    let hi = Math.max(...vals);
    if (mode === 'pace' && !inverted) {
      lo = Math.min(lo, 0);
      hi = Math.max(hi, 0);
    }
    if (lo === hi) {
      lo -= 1;
      hi += 1;
    }
    return [lo, hi];
  });

  const short = (v: number) => {
    const a = Math.abs(v);
    if (a >= 1e9) return fmt(v / 1e9, a >= 1e10 ? 0 : 1) + ' md';
    if (a >= 1e6) return fmt(v / 1e6, a >= 1e7 ? 0 : 1) + ' mn';
    if (a >= 1e4) return fmt(v / 1e3, 0) + ' tn';
    return fmt(v, a >= 100 ? 0 : a >= 10 ? 1 : 2);
  };
  const yearTicks = (lo: number, hi: number) => {
    const span = hi - lo;
    const step = span > 12 ? 4 : span > 6 ? 2 : 1;
    const out: number[] = [];
    for (let y = Math.ceil(lo); y <= hi; y++) if (y % step === 0) out.push(y);
    return out;
  };
  // a series that is not counted keeps its numbers but gets no direction colour (it does not count this month)
  const dirColor = $derived(m.direction === null || !m.counted ? 'var(--c-muted)' : DIRECTIONS[m.direction].color);
  const unitLine = $derived(
    mode === 'pace'
      ? inverted
        ? 'månader, kortare uppåt'
        : (m.pace_unit ?? 'takt')
      : `${m.unit ?? 'nivå'}${useLog ? ', logskala' : ''}`
  );
  const table = $derived({
    caption: `${m.label}: ${mode === 'pace' ? 'takt' : 'nivå'} per period`,
    columns: [
      { key: 'p', label: 'Period' },
      { key: 'v', label: mode === 'pace' ? `Takt (${m.pace_unit ?? ''})` : `Nivå (${m.unit ?? ''})` }
    ],
    rows: [...pts].reverse().map((d) => ({ p: periodLabel(d.p), v: d.v === null ? null : mode === 'pace' ? signed(d.v, 1) : short(d.v) }))
  });
</script>

<article class="sm panel" id="s-{m.key}" class:uncounted={!m.counted}>
  <div class="top">
    {#if !m.counted}
      <span class="nodir">räknas inte</span>
    {:else if m.direction !== null}
      <Glyph direction={m.direction} />
    {:else}
      <span class="nodir">ingen riktning</span>
    {/if}
    {#if mode === 'pace' && m.pace !== null}
      <span class="val num">takt {signed(m.pace, 1)}{#if m.pace_percentile !== null}<span class="pct">{` · ${fmt(m.pace_percentile, 0)}:e percentilen`}<span class="visually-hidden"> av seriens egen historik</span></span>{/if}</span>
    {/if}
    {#if showBranch && m.branch}<span class="tag">{m.branch}</span>{/if}
    {#if m.linkable}
      <a class="open" href={resolve('/serie/[key]', { key: m.key })}>Serien<span class="visually-hidden">: {m.label}</span> <span aria-hidden="true">→</span></a>
    {/if}
  </div>
  <ChartFrame
    id="c-{m.key}"
    title={m.label}
    description={multipleSentence(m, mode)}
    height={118}
    width={340}
    headingLevel={3}
    margin={{ top: 16, right: 12, bottom: 20, left: 44 }}
    {table}
    dataHref={m.linkable ? dataUrl(`series/${m.key}.json`) : undefined}
    source={m.source ?? undefined}
    license={m.license ?? undefined}
    legend={m.counted || m.change_in_pace !== null ? gauge : undefined}
  >
    {#snippet children(d)}
      {#if pts.length && domain}
        {@const x = scaleLinear().domain(domain).range([d.left, d.right])}
        {@const y = useLog
          ? scaleLog().domain(yDomain).range([d.bottom, d.top]).nice()
          : scaleLinear().domain(yDomain).range(inverted ? [d.top, d.bottom] : [d.bottom, d.top]).nice()}
        {@const ticks = useLog ? y.ticks(3).filter((_, i, a) => a.length <= 4 || i % Math.ceil(a.length / 3) === 0) : y.ticks(3)}
        <text class="ink2 unit" x={d.left} y={d.top - 6}>{unitLine}</text>
        <Axis scale={y} dims={d} orient="left" tickValues={ticks} format={short} grid baseline={mode === 'pace' && !inverted ? 0 : undefined} />
        <Axis scale={x} dims={d} tickValues={yearTicks(domain[0], domain[1])} format={(v) => String(v)} />
        <Line data={pts} x={(p) => x(p.t)} y={(p) => y(p.v ?? 1)} defined={(p) => p.v !== null} />
        {@const last = [...pts].reverse().find((p) => p.v !== null)}
        {#if last}
          <circle
            class="mark"
            cx={x(last.t)}
            cy={y(last.v ?? 1)}
            r="4"
            fill={mode === 'pace' ? dirColor : 'var(--c-ink)'}
            stroke="var(--c-surface)"
            stroke-width="2"
          />
        {/if}
      {:else}
        <text class="ink2" x={d.left} y={d.top + d.innerHeight / 2}>{mode === 'pace' ? 'Ingen takt i posten' : 'Ingen nivå i paketet'}</text>
      {/if}
    {/snippet}
  </ChartFrame>
  {#if !m.counted && m.reason}<p class="reason">Räknas inte: {m.reason}.</p>{/if}
</article>

{#snippet gauge()}
  <div class="gauge-wrap">
    <DeadbandGauge change={m.change_in_pace} deadband={m.deadband} direction={m.counted ? m.direction : null} inverted={invertedPace(m.method)} />
    <p class="gauge-note">{deadbandSentence(m)}</p>
  </div>
{/snippet}

<style>
  .sm {
    padding: 12px 14px 12px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }
  .sm :global(.title) {
    font-size: 14px;
    line-height: 1.3;
  }
  /* the generated sentence stays the chart's accessible description; visually the numbers are in the top row */
  .sm :global(.desc) {
    position: absolute;
    width: 1px;
    height: 1px;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
  }
  .sm :global(.foot) {
    margin-top: 2px;
  }
  .sm :global(.legend-slot) {
    flex: 1 1 100%;
  }
  .sm :global(.meta) {
    font-size: 11px;
    gap: 2px 10px;
  }
  .val {
    font-weight: 650;
    font-variant-numeric: tabular-nums;
  }
  .pct {
    font-weight: 400;
    color: var(--c-ink-2);
  }
  .uncounted {
    border-style: dashed;
  }
  .top {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: var(--fs-small);
    min-height: 22px;
  }
  .nodir {
    color: var(--c-muted);
  }
  .tag {
    font-size: 11px;
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-pill);
    padding: 0 7px;
    color: var(--c-ink-2);
  }
  .open {
    margin-left: auto;
    font-size: var(--fs-small);
    padding: 4px 0;
  }
  .unit {
    font-size: 11px;
  }
  .gauge-note,
  .reason {
    margin: 0;
    font-size: 12px;
    color: var(--c-ink-2);
  }
  .reason {
    color: var(--c-muted);
  }
</style>
