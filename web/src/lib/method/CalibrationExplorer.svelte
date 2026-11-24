<!-- Calibration, explorable (track W11, grind G-C): stretch or squeeze the forecast distribution and see coverage per
     level against the binomial 90 % band, and the PIT histogram against a uniform distribution. Illustration: 80 invented
     outcomes against the invented pool (illustration.json); width 1 is close to calibrated by construction. The
     coverage, PIT and band functions are engine.ts's, golden-tested against nowcast.intervals. -->
<script lang="ts">
  import { scaleBand, scaleLinear } from 'd3-scale';
  import { Axis, ChartFrame, Legend, fmt } from '$lib/design';
  import pool from './illustration.json';
  import { ascending, binomialBand, covers, pit, pitHistogram } from './engine';

  const LEVELS = [0.5, 0.8, 0.95];
  const n = pool.outcomes.length;
  let w = $state(1);
  const dist = $derived(ascending(pool.pool.map((x) => w * x)));
  const hits = $derived(LEVELS.map((L) => pool.outcomes.filter((e) => covers(dist, e, L)).length));
  const bands = LEVELS.map((L) => binomialBand(n, L));
  const pits = $derived(pool.outcomes.map((e) => pit(dist, e)));
  const hist = $derived(pitHistogram(pits));
  const expected = n / 10;
  const within = $derived(LEVELS.map((L, i) => hits[i] / n >= bands[i][0] && hits[i] / n <= bands[i][1]));
  const shape = $derived(
    within.every(Boolean)
      ? 'Alla tre nivåerna ligger inom slumpbandet.'
      : hits.every((h, i) => h / n <= bands[i][1]) && hits.some((h, i) => h / n < bands[i][0])
        ? 'För smala intervall: för få utfall inom, och PIT-histogrammet blir U-format (utfallen hamnar i svansarna).'
        : hits.every((h, i) => h / n >= bands[i][0]) && hits.some((h, i) => h / n > bands[i][1])
          ? 'För breda intervall: för många utfall inom, och PIT-histogrammet får en puckel i mitten.'
          : 'Blandad bild: en nivå utanför slumpbandet.'
  );
  const wTxt = $derived(fmt(w, 2));
</script>

<div class="controls">
  <label class="slider">
    <span>Intervallens bredd: <strong class="num">{wTxt} ×</strong> felpoolen</span>
    <input type="range" min="0.5" max="2" step="0.05" bind:value={w} aria-valuetext="{wTxt} gånger felpoolen" />
  </label>
  <button type="button" class="chip" onclick={() => (w = 1)} disabled={w === 1}>Bredd 1</button>
</div>
<p class="desc-line" aria-live="polite">
  {hits[1]} av {n} utfall inom 80 %-intervallet (slumpbandet {fmt(bands[1][0] * n)}–{fmt(bands[1][1] * n)}). {shape}
</p>

<div class="two">
  <ChartFrame
    id="cal-cov"
    title="Täckning per nivå"
    description={`Andel av ${n} påhittade utfall inom intervallet vid bredden ${wTxt}: ${LEVELS.map((L, i) => `${fmt((hits[i] / n) * 100)} % inom ${fmt(L * 100)} %`).join(', ')}. Strecket är nominell nivå, bandet vad slumpen ger (binomialt 90 %-band).`}
    height={170}
    margin={{ top: 8, right: 20, bottom: 26, left: 56 }}
    table={{
      columns: [
        { key: 'l', label: 'Nivå', align: 'left' },
        { key: 'k', label: 'Inom' },
        { key: 'p', label: 'Andel' },
        { key: 'b', label: 'Slumpband (90 %)' }
      ],
      rows: LEVELS.map((L, i) => ({
        l: `${fmt(L * 100)} %`,
        k: `${hits[i]} av ${n}`,
        p: `${fmt((hits[i] / n) * 100)} %`,
        b: `${fmt(bands[i][0] * 100)}–${fmt(bands[i][1] * 100)} %`
      }))
    }}
    legend={covLegend}
  >
    {#snippet children(d)}
      {@const x = scaleLinear().domain([0.2, 1]).range([d.left, d.right])}
      {@const y = scaleBand<number>().domain(LEVELS).range([d.top, d.bottom]).padding(0.25)}
      <Axis scale={x} dims={d} tickValues={[0.2, 0.4, 0.5, 0.6, 0.8, 0.95, 1]} format={(v) => `${fmt(v * 100)}`} />
      {#each LEVELS as L, i (L)}
        {@const yy = (y(L) ?? 0) + y.bandwidth() / 2}
        <text class="ink2" x={d.left - 8} y={yy + 4} text-anchor="end">{fmt(L * 100)} %</text>
        <rect class="cband" x={x(bands[i][0])} width={Math.max(2, x(bands[i][1]) - x(bands[i][0]))} y={yy - 9} height={18} />
        <line class="nominal" x1={x(L)} x2={x(L)} y1={yy - 12} y2={yy + 12} />
        <circle class="mark" class:inband={within[i]} class:outband={!within[i]} cx={x(hits[i] / n)} cy={yy} r="6" />
      {/each}
    {/snippet}
  </ChartFrame>

  <ChartFrame
    id="cal-pit"
    title="PIT-histogram"
    description={`PIT är var utfallet hamnar i den egna prognosfördelningen (0 = lägst, 1 = högst). Vid god kalibrering ligger lika många i varje tiondel, här ${fmt(expected)} av ${n}. Bredd ${wTxt}: ${hist.join(', ')}.`}
    height={170}
    margin={{ top: 10, right: 10, bottom: 26, left: 30 }}
    table={{
      columns: [
        { key: 'b', label: 'PIT', align: 'left' },
        { key: 'n', label: 'Utfall' },
        { key: 'e', label: 'Jämn fördelning' }
      ],
      rows: hist.map((c, i) => ({ b: `${fmt(i / 10, 1)}–${fmt((i + 1) / 10, 1)}`, n: c, e: fmt(expected) }))
    }}
  >
    {#snippet children(d)}
      {@const x = scaleLinear().domain([0, 1]).range([d.left, d.right])}
      {@const top = Math.max(expected * 2.5, ...hist) }
      {@const y = scaleLinear().domain([0, top]).range([d.bottom, d.top])}
      <Axis scale={y} dims={d} orient="left" ticks={3} format={(v) => fmt(v)} />
      <Axis scale={x} dims={d} tickValues={[0, 0.5, 1]} format={(v) => fmt(v, 1)} />
      {#each hist as c, i (i)}
        <rect class="mark bar" x={x(i / 10) + 1} width={x(0.1) - x(0) - 2} y={y(c)} height={d.bottom - y(c)} />
      {/each}
      <line class="nominal" x1={d.left} x2={d.right} y1={y(expected)} y2={y(expected)} />
      <text class="ink2" x={d.right - 2} y={y(expected) - 4} text-anchor="end">jämn</text>
    {/snippet}
  </ChartFrame>
</div>

{#snippet covLegend()}
  <Legend
    items={[
      { label: 'slumpband (binomialt 90 %)', fill: 'var(--c-mid)', border: 'var(--c-axis)' },
      { label: 'fylld: inom bandet', fill: 'var(--c-model)' },
      { label: 'ring: utanför', fill: 'var(--c-surface)', border: 'var(--c-model)' }
    ]}
  />
{/snippet}

<style>
  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: 10px 16px;
    align-items: end;
    margin: 12px 0 4px;
  }
  .slider {
    display: grid;
    gap: 2px;
    flex: 1 1 260px;
    font-size: var(--fs-small);
  }
  .slider input {
    width: 100%;
    min-height: var(--hit);
    accent-color: var(--c-ink);
  }
  .desc-line {
    font-size: var(--fs-small);
    color: var(--c-ink-2);
    max-width: 75ch;
    margin: 4px 0 12px;
  }
  .two {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 22px;
  }
  @media (min-width: 861px) {
    .two {
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    }
  }
  .cband {
    fill: var(--c-mid);
    stroke: var(--c-axis);
  }
  .nominal {
    stroke: var(--c-ink);
    stroke-width: 1.5;
    stroke-dasharray: 3 2;
  }
  .inband {
    fill: var(--c-model);
    stroke: var(--c-surface);
  }
  .outband {
    fill: var(--c-surface);
    stroke: var(--c-model);
    stroke-width: 2;
  }
  .bar {
    fill: var(--c-model-80);
    stroke: var(--c-model);
  }
</style>
