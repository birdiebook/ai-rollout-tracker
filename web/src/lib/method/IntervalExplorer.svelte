<!-- What an interval means (track W11, grind G-C): a forecast's interval is the point forecast plus the empirical
     quantiles of the model's own past errors. Drag the level and see which quantiles bound it and how many past errors
     fall inside. The pool is an illustration (invented errors, illustration.json); the quantiles are engine.ts's type 6,
     golden-tested against nowcast.intervals. -->
<script lang="ts">
  import { scaleLinear } from 'd3-scale';
  import { Axis, ChartFrame, Legend, fmt } from '$lib/design';
  import pool from './illustration.json';
  import { ascending, interval } from './engine';

  const sorted = ascending(pool.pool);
  const n = sorted.length;
  let pctLevel = $state(80);
  const L = $derived(pctLevel / 100);
  const iv = $derived(interval(sorted, L));
  const inside = $derived(sorted.filter((e) => iv[0] <= e && e <= iv[1]).length);
  const lowP = $derived((1 - L) / 2);
  const highP = $derived((1 + L) / 2);

  // dot plot: bins of 1 log point, dots stacked
  const BIN = 1;
  const dots = sorted.map((e, i) => ({ e, bin: Math.floor(e / BIN) })).map((o, i, all) => ({ ...o, stack: all.slice(0, i).filter((x) => x.bin === o.bin).length }));
  const maxStack = Math.max(...dots.map((d) => d.stack)) + 1;
  const ext = Math.ceil(Math.max(...sorted.map(Math.abs)) + 1);

  const pctTxt = (p: number) => `${fmt(p * 100, p * 100 < 10 || (p * 100) % 1 ? 1 : 0)} %`;
</script>

<div class="controls">
  <label class="slider">
    <span>Intervallnivå: <strong class="num">{pctLevel} %</strong>{#if [50, 80, 95].includes(pctLevel)} <span class="tag reg">registrerad nivå</span>{/if}</span>
    <input type="range" min="50" max="95" step="5" bind:value={pctLevel} aria-valuetext="{pctLevel} procent{[50, 80, 95].includes(pctLevel) ? ', registrerad nivå' : ''}" />
  </label>
  <div class="pick" role="group" aria-label="Registrerade nivåer">
    {#each [50, 80, 95] as l (l)}
      <button type="button" class="chip" aria-pressed={pctLevel === l} onclick={() => (pctLevel = l)}>{l} %</button>
    {/each}
  </div>
</div>

<ChartFrame
  id="iv-pool"
  title="{pctLevel} %-intervallet ur {n} tidigare fel"
  description={`Intervallet går från ${pctTxt(lowP)}- till ${pctTxt(highP)}-kvantilen av felen: ${fmt(iv[0], 1)} till ${fmt(iv[1], 1)} (log ×100). ${inside} av ${n} tidigare fel ligger inom. Felen är påhittade för illustrationen.`}
  height={Math.max(150, maxStack * 13 + 60)}
  margin={{ top: 22, right: 14, bottom: 30, left: 14 }}
  table={{
    caption: 'Påhittade tidigare fel (log ×100), sorterade, och om de ligger inom intervallet',
    columns: [
      { key: 'i', label: 'Rang' },
      { key: 'e', label: 'Fel' },
      { key: 'in', label: `Inom ${pctLevel} %`, align: 'left' }
    ],
    rows: sorted.map((e, i) => ({ i: i + 1, e: fmt(e, 2), in: iv[0] <= e && e <= iv[1] ? 'ja' : 'nej' }))
  }}
  legend={legend}
>
  {#snippet children(d)}
    {@const x = scaleLinear().domain([-ext, ext]).range([d.left, d.right])}
    {@const r = Math.min(5.5, (x(BIN) - x(0)) / 2 - 0.4)}
    {@const base = d.bottom - r - 2}
    <rect class="iv" x={x(iv[0])} y={d.top} width={x(iv[1]) - x(iv[0])} height={d.bottom - d.top} />
    <line class="edge" x1={x(iv[0])} x2={x(iv[0])} y1={d.top} y2={d.bottom} />
    <line class="edge" x1={x(iv[1])} x2={x(iv[1])} y1={d.top} y2={d.bottom} />
    <text class="ink" x={x(iv[0]) - 3} y={d.top - 8} text-anchor="end">{pctTxt(lowP)}: {fmt(iv[0], 1)}</text>
    <text class="ink" x={x(iv[1]) + 3} y={d.top - 8}>{pctTxt(highP)}: {fmt(iv[1], 1)}</text>
    <Axis scale={x} dims={d} ticks={8} format={(v) => fmt(v)} baseline={0} />
    {#each dots as o, i (i)}
      {@const inn = iv[0] <= o.e && o.e <= iv[1]}
      <circle class="mark" class:in={inn} class:out={!inn} cx={x(o.bin * BIN + BIN / 2)} cy={base - o.stack * (2 * r + 1)} {r} />
    {/each}
    <text x={(d.left + d.right) / 2} y={d.bottom + 27} text-anchor="middle">tidigare fel: prognos minus utfall (log ×100)</text>
  {/snippet}
</ChartFrame>

{#snippet legend()}
  <Legend
    items={[
      { label: 'fylld: felet ligger inom intervallet', fill: 'var(--c-model)' },
      { label: 'ring: utanför', fill: 'var(--c-surface)', border: 'var(--c-model)' },
      { label: 'Illustration: påhittade fel', fill: 'transparent', border: 'var(--c-axis)' }
    ]}
  />
{/snippet}

<style>
  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: 10px 16px;
    align-items: end;
    margin: 12px 0 10px;
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
  .pick {
    display: flex;
    gap: 6px;
  }
  .tag {
    font-size: 12px;
    border: 1px solid var(--c-ink-2);
    border-radius: 999px;
    padding: 1px 8px;
  }
  .iv {
    fill: var(--c-model-80);
    transition:
      x 250ms,
      width 250ms;
  }
  .edge {
    stroke: var(--c-model);
    stroke-width: 1.5;
  }
  circle.in {
    fill: var(--c-model);
    stroke: var(--c-surface);
    stroke-width: 1;
  }
  circle.out {
    fill: var(--c-surface);
    stroke: var(--c-model);
    stroke-width: 1.5;
  }
</style>
