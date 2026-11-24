<!-- Live calibration (W8). Frequencies first (section 4.2): one slot per live outcome up to about 12, filled inside
     the 80 % interval, a ring outside, dashed while waiting. Then the share inside each interval against the nominal
     level with the binomial band from the pipeline, and the PIT values (dots while n is small, a histogram later).
     Below MIN_LIVE_FOR_CALIBRATION outcomes the text says so plainly. -->
<script lang="ts">
  import { scaleLinear } from 'd3-scale';
  import { Axis, ChartFrame, fmt } from '$lib/design';
  import type { CoverageRow } from '$lib/data';
  import { LEVELS, MIN_LIVE_FOR_CALIBRATION, calibrationNote, hitCounts, pitBins, type LiveRow } from './model';
  import OutcomeMark from './OutcomeMark.svelte';

  let { id, rows, coverage, champion }: { id: string; rows: LiveRow[]; coverage: CoverageRow[]; champion: string } = $props();

  const scored = $derived(rows.filter((r) => r.scored));
  const n = $derived(scored.length);
  const hits = $derived(hitCounts(rows));
  const cov = $derived(coverage.find((c) => c.variant === 'champion') ?? coverage.find((c) => c.variant === champion));
  const slots = $derived(Math.max(MIN_LIVE_FOR_CALIBRATION, n));
  const pits = $derived(scored.map((r) => r.pit).filter((p): p is number => p !== null));
  const small = $derived(n < MIN_LIVE_FOR_CALIBRATION);
  const slotLabel = $derived(
    `${n} av cirka ${MIN_LIVE_FOR_CALIBRATION} skarpa utfall som behövs: ${hits['80'].k} inom 80 %-intervallet, ${hits['80'].n - hits['80'].k} utanför, ${Math.max(0, MIN_LIVE_FOR_CALIBRATION - n)} återstår.`
  );
</script>

<div class="live-cal">
  <p class="honest" data-small={small}>{calibrationNote(n)}</p>
  <svg class="slots" viewBox="0 0 {slots * 22} 26" width={Math.min(slots * 22, 560)} height="26" role="img" aria-label={slotLabel}>
    {#each Array.from({ length: slots }, (_, i) => i) as i (i)}
      {@const r = scored[i]}
      {#if r}
        <OutcomeMark cx={11 + i * 22} cy={13} r={8} inside={r.inside['80'] ?? false} />
      {:else}
        <circle cx={11 + i * 22} cy={13} r="8" fill="none" stroke="var(--c-axis)" stroke-width="1.5" stroke-dasharray="3 3" />
      {/if}
    {/each}
  </svg>
  <p class="note">● inom 80 %-intervallet · ○ utanför · streckad = väntar på utfall</p>

  {#if n > 0}
    <div class="two">
      <ChartFrame
        id="{id}-cov"
        title="Andel utfall inom intervallen"
        description={LEVELS.map((l) => `${hits[l].k} av ${hits[l].n} inom ${l} %`).join(', ') + '. Strecket är den nominella nivån, det grå bandet vad slumpen ger.'}
        height={3 * 30 + 30}
        margin={{ top: 8, right: 44, bottom: 24, left: 44 }}
        table={{
          columns: [{ key: 'l', label: 'Nivå', align: 'left' }, { key: 'k', label: 'Inom', align: 'right' }, { key: 's', label: 'Andel', align: 'right' }, { key: 'b', label: 'Slumpband', align: 'right' }],
          rows: LEVELS.map((l) => {
            const b = cov?.[`band_${l}`] as [number, number] | null | undefined;
            return { l: `${l} %`, k: `${hits[l].k} av ${hits[l].n}`, s: hits[l].n ? `${fmt((100 * hits[l].k) / hits[l].n)} %` : '–', b: b ? `${fmt(b[0] * 100)}–${fmt(b[1] * 100)} %` : '–' };
          })
        }}
      >
        {#snippet children(d)}
          {@const x = scaleLinear().domain([0, 1]).range([d.left, d.right])}
          <Axis scale={x} dims={d} tickValues={[0, 0.5, 1]} format={(v) => `${fmt(v * 100)} %`} />
          {#each LEVELS as l, i (l)}
            {@const cy = d.top + 14 + i * 30}
            {@const b = cov?.[`band_${l}`] as [number, number] | null | undefined}
            <text class="ink" x={d.left - 8} y={cy + 4} text-anchor="end">{l} %</text>
            {#if b && b[0] !== null && b[1] !== null}
              <rect x={x(b[0])} y={cy - 6} width={Math.max(1, x(b[1]) - x(b[0]))} height="12" rx="3" fill="var(--c-grid)" />
            {/if}
            <line x1={x(+l / 100)} x2={x(+l / 100)} y1={cy - 9} y2={cy + 9} stroke="var(--c-ink-2)" stroke-width="1.5" />
            {#if hits[l].n}
              <circle class="mark" cx={x(hits[l].k / hits[l].n)} {cy} r="5" fill="var(--c-model)" stroke="var(--c-surface)" stroke-width="2" />
              <text class="ink2" x={d.right + 6} y={cy + 4}>{hits[l].k}/{hits[l].n}</text>
            {/if}
          {/each}
        {/snippet}
      </ChartFrame>

      {#if pits.length === 0}
        <div class="nopit">
          <h3>Var utfallen hamnade i fördelningen (PIT)</h3>
          <p>Inga PIT-värden ännu. PIT räknas när utfallet kan ställas mot den lagrade fördelningen.</p>
        </div>
      {:else}
      <ChartFrame
        id="{id}-pit"
        title="Var utfallen hamnade i fördelningen (PIT)"
        description={pits.length === 0
          ? 'Inga PIT-värden ännu.'
          : `${pits.length} utfall. Jämnt fördelat över 0–1 betyder kalibrerat; samlat i mitten betyder för breda intervall, i kanterna för smala.${small ? ' Med så få utfall säger formen ingenting än.' : ''}`}
        height={120}
        margin={{ top: 10, right: 12, bottom: 24, left: 12 }}
        table={{ columns: [{ key: 'p', label: 'Period', align: 'left' }, { key: 'v', label: 'PIT', align: 'right' }], rows: scored.map((r) => ({ p: r.period, v: fmt(r.pit, 2) })) }}
      >
        {#snippet children(d)}
          {@const x = scaleLinear().domain([0, 1]).range([d.left, d.right])}
          <Axis scale={x} dims={d} tickValues={[0, 0.25, 0.5, 0.75, 1]} format={(v) => fmt(v, 2)} />
          {#if small}
            {#each pits as p, i (i)}
              <circle class="mark" cx={x(p)} cy={d.bottom - 10 - (i % 4) * 12} r="5" fill="var(--c-model)" stroke="var(--c-surface)" stroke-width="1.5" />
            {/each}
          {:else}
            {@const bins = pitBins(pits)}
            {@const y = scaleLinear().domain([0, Math.max(...bins, pits.length / 10) * 1.2]).range([d.bottom, d.top])}
            {#each bins as c, i (i)}
              <rect class="mark" x={x(i / 10) + 1} y={y(c)} width={x(0.1) - x(0) - 2} height={y(0) - y(c)} rx="2" fill="var(--c-model)" />
            {/each}
            <line x1={d.left} x2={d.right} y1={y(pits.length / 10)} y2={y(pits.length / 10)} stroke="var(--c-ink)" stroke-dasharray="4 3" />
          {/if}
        {/snippet}
      </ChartFrame>
      {/if}
    </div>
  {/if}
</div>

<style>
  .honest {
    margin: 0 0 8px;
    font-size: var(--fs-body);
    max-width: 62ch;
  }
  .honest[data-small='true'] {
    border-left: 3px solid var(--c-axis);
    padding-left: 10px;
  }
  .slots {
    display: block;
    max-width: 100%;
    height: auto;
  }
  .note {
    margin: 4px 0 14px;
  }
  .nopit h3 {
    font-size: var(--fs-subsection);
  }
  .nopit p {
    margin: 4px 0 0;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  .two {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 18px;
  }
  @media (min-width: 861px) {
    .two {
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    }
  }
</style>
