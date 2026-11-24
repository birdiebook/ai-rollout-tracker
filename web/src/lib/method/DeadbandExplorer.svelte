<!-- Diffusion index, explorable (track W11, vision 2.2 F): drag the dead band and see each series' direction and the
     branch's state change. The registered value (0,25 sd) and the pipeline's record are always drawn and labelled
     "registrerat"; the reader's value is labelled "utforskning". The explorer's numbers come from engine.ts, which is
     golden-tested against state.branch (Python) and reproduces the record exactly at the registered dead band. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { scaleLinear } from 'd3-scale';
  import { Axis, ChartFrame, DIRECTIONS, Legend, fmt, stateStyle, type RecordStatus } from '$lib/design';
  import { IndexHistory, UnitBoxes } from '$lib/flow';
  import { exploreBranch, indexSteps, zOf, type Rules } from './engine';
  import type { ExploreBranch } from './prepare';

  let {
    branches,
    initial,
    rules,
    status,
    linkable
  }: { branches: ExploreBranch[]; initial: string | null; rules: Rules; status: RecordStatus; linkable: string[] } = $props();

  const K_MAX = 1.5;
  const reg = $derived(rules.deadband_sd);
  // svelte-ignore state_referenced_locally
  let code = $state(initial);
  // svelte-ignore state_referenced_locally
  let k = $state(rules.deadband_sd);

  const eligible = $derived(branches.filter((b) => b.eligible));
  const other = $derived(branches.filter((b) => !b.eligible));
  const br = $derived(branches.find((b) => b.code === code) ?? null);
  const series = $derived(br?.series ?? []);
  const atReg = $derived(exploreBranch(series, reg, rules));
  const atK = $derived(exploreBranch(series, k, rules));
  const steps = $derived(indexSteps(series, K_MAX, rules));
  const isReg = $derived(Math.abs(k - reg) < 1e-9);
  const rows = $derived([...series].map((s) => ({ ...s, z: zOf(s) })).sort((a, b) => b.z - a.z));
  const zMax = $derived(Math.max(1.6, Math.min(4, Math.max(...rows.map((r) => Math.abs(r.z)), 0) * 1.08)));
  const links = $derived(new Set(linkable));
  const href = (key: string) => (links.has(key) ? resolve('/serie/[key]', { key }) : '#serier-' + key);

  const word = (d: number) => DIRECTIONS[d as 1 | 0 | -1].word;
  const st = (s: string) => stateStyle(s);
  const kTxt = (x: number) => fmt(x, 2);
  const changed = $derived(series.filter((s) => atK.directions[s.key] !== s.registered).length);

  const sentence = $derived(
    br
      ? `Med dödbandet ${kTxt(k)} standardavvikelser ${atK.n_up} av ${atK.n_series} serier ökar takten, ${atK.n_neutral} oförändrade och ${atK.n_down} minskar takten: index ${fmt(atK.index, 2)}, ${st(atK.state).word}. ` +
          (isReg
            ? 'Det är det registrerade dödbandet, och utfallet är exakt grenens registrerade tillstånd.'
            : `Registrerat (${kTxt(reg)}): index ${fmt(br.registered.index, 2)}, ${st(br.registered.state).word}. ${changed} ${changed === 1 ? 'serie byter' : 'serier byter'} riktning.`)
      : 'Ingen gren kan räknas om i webbläsaren.'
  );

  function setK(x: number) {
    k = Math.round(Math.max(0, Math.min(K_MAX, x)) * 100) / 100;
  }

  // Direct manipulation in the index chart: press or drag to set the dead band (the slider is the keyboard path).
  let dragging = false;
  function fromPointer(e: PointerEvent, left: number, right: number) {
    const svg = (e.currentTarget as SVGElement).closest('svg') as SVGSVGElement;
    const r = svg.getBoundingClientRect();
    const vb = svg.viewBox.baseVal;
    const x = ((e.clientX - r.left) / r.width) * vb.width;
    setK(((x - left) / (right - left)) * K_MAX);
  }
</script>

{#if br}
  <div class="controls">
    <div class="pick" role="group" aria-label="Välj gren att utforska">
      {#each eligible as b (b.code)}
        <button type="button" class="chip" aria-pressed={b.code === code} onclick={() => (code = b.code)}>{b.code} {b.name} <span class="n">({b.series.length})</span></button>
      {/each}
    </div>
    <label class="slider">
      <span class="lab">Dödband: <strong class="num">{kTxt(k)}</strong> standardavvikelser {#if isReg}<span class="tag reg">registrerat</span>{:else}<span class="tag exp">utforskning</span>{/if}</span>
      <input
        type="range"
        min="0"
        max={K_MAX}
        step="0.01"
        value={k}
        aria-valuetext="{kTxt(k)} standardavvikelser{isReg ? ', registrerat' : `, utforskning (registrerat ${kTxt(reg)})`}"
        oninput={(e) => setK(Number((e.currentTarget as HTMLInputElement).value))}
      />
    </label>
    <button type="button" class="chip" onclick={() => setK(reg)} disabled={isReg}>Tillbaka till registrerat ({kTxt(reg)})</button>
  </div>
  {#if other.length}
    <p class="note">
      Kan inte räknas om här: {other.map((b) => `${b.code} (${b.why})`).join(', ')}. Deras tillstånd finns på grensidorna.
    </p>
  {/if}

  <div class="verdicts" aria-live="polite">
    <div class="verdict reg-card">
      <span class="tag reg">registrerat</span>
      <span class="k">dödband {kTxt(reg)} sd, {br.registered.n_series} serier</span>
      <span class="state"><span class="sw" style:background={st(br.registered.state).color} aria-hidden="true"></span>{st(br.registered.state).glyph} {st(br.registered.state).word}</span>
      <span class="idx">index <strong class="num">{fmt(br.registered.index, 2)}</strong></span>
    </div>
    <div class="verdict exp-card" class:same={isReg}>
      <span class="tag exp">utforskning</span>
      <span class="k">dödband {kTxt(k)} sd</span>
      <span class="state"><span class="sw" style:background={st(atK.state).color} aria-hidden="true"></span>{st(atK.state).glyph} {st(atK.state).word}</span>
      <span class="idx">index <strong class="num">{fmt(atK.index, 2)}</strong></span>
    </div>
  </div>
  <p class="desc-line">{sentence}</p>

  <div class="two">
    <ChartFrame
      id="db-series"
      title="Seriernas förändring i takt mot dödbandet"
      description={`Förändring i takt för ${series.length} serier i ${br.code}, i seriens egna standardavvikelser (höger = mer takt). Inom bandet ±${kTxt(k)} är riktningen oförändrad.`}
      height={Math.max(160, rows.length * 32 + 56)}
      margin={{ top: 22, right: 16, bottom: 26, left: 16 }}
      {status}
      table={{
        caption: `${br.code}: förändring i takt i standardavvikelser och riktning vid registrerat och utforskat dödband`,
        columns: [
          { key: 's', label: 'Serie', align: 'left' },
          { key: 'z', label: 'Förändring (sd)' },
          { key: 'r', label: `Registrerat (${kTxt(reg)})`, align: 'left' },
          { key: 'e', label: `Utforskning (${kTxt(k)})`, align: 'left' }
        ],
        rows: rows.map((r) => ({
          s: r.label,
          z: fmt(r.z, 2),
          r: `${DIRECTIONS[r.registered as 1 | 0 | -1].glyph} ${word(r.registered as number)}`,
          e: `${DIRECTIONS[atK.directions[r.key]].glyph} ${word(atK.directions[r.key])}`
        }))
      }}
      legend={seriesLegend}
    >
      {#snippet children(d)}
        {@const x = scaleLinear().domain([-zMax, zMax]).range([d.left, d.right]).clamp(true)}
        {@const rowH = (d.bottom - d.top) / Math.max(1, rows.length)}
        <Axis scale={x} dims={d} ticks={6} format={(v) => fmt(v, 1)} />
        <rect class="band exp" x={x(-k)} y={d.top} width={Math.max(0, x(k) - x(-k))} height={d.bottom - d.top} />
        <line class="regline" x1={x(-reg)} x2={x(-reg)} y1={d.top} y2={d.bottom} />
        <line class="regline" x1={x(reg)} x2={x(reg)} y1={d.top} y2={d.bottom} />
        <line class="zero" x1={x(0)} x2={x(0)} y1={d.top} y2={d.bottom} />
        {#each rows as r, i (r.key)}
          {@const y = d.top + rowH * (i + 0.5)}
          {@const dir = atK.directions[r.key]}
          {@const off = Math.abs(r.z) > zMax}
          <text class="ink2 rowlab" x={d.left + 2} y={y - 6}>{r.label.length > 44 ? r.label.slice(0, 42) + '…' : r.label}</text>
          <line class="track" x1={d.left} x2={d.right} y1={y + 5} y2={y + 5} />
          <circle class="mark dot" cx={x(r.z)} cy={y + 5} r="6" style:fill={DIRECTIONS[dir].color} />
          {#if dir !== r.registered}<circle class="mark moved" cx={x(r.z)} cy={y + 5} r="9.5" />{/if}
          {#if off}<text class="ink2" x={r.z > 0 ? d.right - 10 : d.left + 10} y={y + 9} text-anchor={r.z > 0 ? 'end' : 'start'}>{fmt(r.z, 1)}</text>{/if}
        {/each}
        <text class="ink2" x={x(reg)} y={d.top - 6} text-anchor="middle">registrerat ±{kTxt(reg)}</text>
      {/snippet}
    </ChartFrame>

    <ChartFrame
      id="db-index"
      title="Grenens index när dödbandet ändras"
      description={`${br.code}: indexet är en trappa i dödbandet, eftersom en serie bara byter riktning när bandet passerar den. Tröskeln ${fmt(rules.accelerating_at_least, 2)} ger accelererar och ${fmt(rules.braking_at_most, 2)} bromsar in; med färre än ${rules.min_series} serier visas inget tillstånd.`}
      height={240}
      margin={{ top: 14, right: 18, bottom: 34, left: 40 }}
      {status}
      table={{
        caption: `${br.code}: index och tillstånd per intervall av dödbandet`,
        columns: [
          { key: 'f', label: 'Dödband från (sd)' },
          { key: 't', label: 'till' },
          { key: 'i', label: 'Index' },
          { key: 's', label: 'Tillstånd', align: 'left' }
        ],
        rows: steps.map((s) => ({ f: fmt(s.from, 2), t: fmt(s.to, 2), i: fmt(s.index, 2), s: `${st(s.state).glyph} ${st(s.state).word}` }))
      }}
      legend={indexLegend}
    >
      {#snippet children(d)}
        {@const x = scaleLinear().domain([0, K_MAX]).range([d.left, d.right])}
        {@const y = scaleLinear().domain([0, 1]).range([d.bottom, d.top])}
        <rect class="stable" x={d.left} width={d.right - d.left} y={y(rules.accelerating_at_least)} height={y(rules.braking_at_most) - y(rules.accelerating_at_least)} />
        <Axis scale={y} dims={d} orient="left" tickValues={[0, rules.braking_at_most, 0.5, rules.accelerating_at_least, 1]} format={(v) => fmt(v, 2)} />
        <Axis scale={x} dims={d} tickValues={[0, 0.25, 0.5, 0.75, 1, 1.25, 1.5]} format={(v) => fmt(v, 2)} />
        <text x={(d.left + d.right) / 2} y={d.bottom + 30} text-anchor="middle">dödband (standardavvikelser)</text>
        {#each steps as s, i (i)}
          {#if s.index !== null}
            <line class="mark step" x1={x(s.from)} x2={x(s.to)} y1={y(s.index)} y2={y(s.index)} style:stroke={st(s.state).color} />
            {#if i > 0 && steps[i - 1].index !== null}
              <line class="riser" x1={x(s.from)} x2={x(s.from)} y1={y(steps[i - 1].index as number)} y2={y(s.index)} />
            {/if}
          {/if}
        {/each}
        <line class="regline" x1={x(reg)} x2={x(reg)} y1={d.top} y2={d.bottom} />
        <text class="ink2" x={x(reg) + 4} y={d.top + 10}>registrerat</text>
        {#if !isReg}
          <line class="kline" x1={x(k)} x2={x(k)} y1={d.top} y2={d.bottom} />
          <text class="ink" x={Math.min(d.right - 4, x(k) + 4)} y={d.top + 24} text-anchor={x(k) > d.right - 70 ? 'end' : 'start'}>utforskning</text>
        {/if}
        {#if atReg.index !== null}<circle class="mark regdot" cx={x(reg)} cy={y(atReg.index)} r="5" />{/if}
        {#if atK.index !== null}<circle class="mark kdot" cx={x(k)} cy={y(atK.index)} r="6" style:fill={st(atK.state).color} />{/if}
        <!-- pointer surface: press or drag to move the dead band -->
        <rect
          class="hit"
          role="presentation"
          x={d.left}
          y={d.top}
          width={d.right - d.left}
          height={d.bottom - d.top}
          onpointerdown={(e) => {
            dragging = true;
            (e.currentTarget as Element).setPointerCapture?.(e.pointerId);
            fromPointer(e, d.left, d.right);
          }}
          onpointermove={(e) => dragging && fromPointer(e, d.left, d.right)}
          onpointerup={() => (dragging = false)}
          onpointercancel={() => (dragging = false)}
        />
      {/snippet}
    </ChartFrame>
  </div>

  <div class="units-pair">
    <div>
      <p class="unit-head"><span class="tag reg">registrerat</span> {kTxt(reg)} sd</p>
      <UnitBoxes label="Seriernas registrerade riktning i {br.code}" items={series.map((s) => ({ key: s.key, label: s.label, direction: s.registered }))} {href} />
    </div>
    <div>
      <p class="unit-head"><span class="tag exp">utforskning</span> {kTxt(k)} sd</p>
      <UnitBoxes label="Seriernas riktning i {br.code} vid dödbandet {kTxt(k)}" items={series.map((s) => ({ key: s.key, label: s.label, direction: atK.directions[s.key] }))} {href} />
    </div>
  </div>

  <details class="hist">
    <summary>{br.code}:s registrerade index över tid</summary>
    <IndexHistory id="db-history" title="{br.code} {br.name}: registrerat index" history={br.history} {status} lo={rules.braking_at_most} hi={rules.accelerating_at_least} height={200} headingLevel={4} />
  </details>
{:else}
  <p class="note">Ingen gren i paketet kan räknas om i webbläsaren (alla räknar inhållna serier eller saknar serier).</p>
{/if}

{#snippet seriesLegend()}
  <Legend
    items={[
      { label: 'utforskat dödband', fill: 'var(--c-mid)', border: 'var(--c-axis)' },
      { label: 'streckat: registrerat dödband', line: true, fill: 'var(--c-ink-2)' },
      { label: 'ring: annan riktning än registrerat', fill: 'var(--c-surface)', border: 'var(--c-ink)' }
    ]}
  />
{/snippet}

{#snippet indexLegend()}
  <Legend
    items={[
      { label: 'stabil zon mellan trösklarna', fill: 'var(--c-mid)', border: 'var(--c-axis)' },
      { label: 'ring: registrerat', fill: 'var(--c-surface)', border: 'var(--c-ink)' },
      { label: 'fylld: utforskning (klicka eller dra i diagrammet)', fill: 'var(--c-ink-2)' }
    ]}
  />
{/snippet}

<style>
  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: 10px 16px;
    align-items: center;
    margin: 12px 0 6px;
  }
  .pick {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    width: 100%;
  }
  .pick .n {
    opacity: 0.75;
  }
  .slider {
    display: grid;
    gap: 2px;
    flex: 1 1 280px;
    font-size: var(--fs-small);
  }
  .slider input {
    width: 100%;
    min-height: var(--hit);
    accent-color: var(--c-ink);
  }
  .tag {
    display: inline-block;
    font-size: 12px;
    border-radius: 999px;
    padding: 1px 8px;
    border: 1px solid var(--c-ink-2);
    color: var(--c-ink);
    white-space: nowrap;
    vertical-align: 1px;
  }
  .tag.exp {
    border-style: dashed;
  }
  .verdicts {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 10px;
    margin: 10px 0 4px;
  }
  .verdict {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 2px 10px;
    align-items: baseline;
    padding: 10px 14px;
    border-radius: var(--radius-md);
    background: var(--c-surface);
    border: 1px solid var(--c-ink-2);
  }
  .exp-card {
    border-style: dashed;
  }
  .verdict .k {
    font-size: var(--fs-small);
    color: var(--c-muted);
  }
  .verdict .state {
    font-size: 20px;
    font-weight: 650;
    grid-column: 1 / -1;
  }
  .verdict .sw {
    display: inline-block;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    margin-right: 8px;
    vertical-align: 1px;
    transition: background 250ms;
  }
  @media (forced-colors: active) {
    .verdict .sw {
      forced-color-adjust: none;
    }
  }
  .verdict .idx {
    grid-column: 1 / -1;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  .desc-line {
    font-size: var(--fs-small);
    color: var(--c-ink-2);
    max-width: 75ch;
    margin: 6px 0 14px;
  }
  .two {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 22px;
  }
  @media (min-width: 861px) {
    .two {
      grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
    }
  }
  .band.exp {
    fill: var(--c-mid);
    stroke: var(--c-axis);
    transition:
      x 250ms,
      width 250ms;
  }
  .stable {
    fill: var(--c-mid);
  }
  .regline {
    stroke: var(--c-ink-2);
    stroke-dasharray: 4 3;
    stroke-width: 1.2;
  }
  .zero {
    stroke: var(--c-axis);
  }
  .track {
    stroke: var(--c-grid);
  }
  .dot {
    stroke: var(--c-surface);
    stroke-width: 1.5;
    transition: fill 250ms;
  }
  .moved {
    fill: none;
    stroke: var(--c-ink);
    stroke-width: 1.5;
  }
  .rowlab {
    font-size: 11px;
    paint-order: stroke;
    stroke: var(--c-page);
    stroke-width: 3px;
    stroke-linejoin: round;
  }
  .step {
    stroke-width: 3;
  }
  .riser {
    stroke: var(--c-axis);
    stroke-dasharray: 2 2;
  }
  .kline {
    stroke: var(--c-ink);
    stroke-width: 1.5;
  }
  .regdot {
    fill: var(--c-surface);
    stroke: var(--c-ink);
    stroke-width: 2;
  }
  .kdot {
    stroke: var(--c-surface);
    stroke-width: 2;
  }
  .hit {
    fill: transparent;
    cursor: ew-resize;
    touch-action: none;
  }
  .units-pair {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 10px 24px;
    margin-top: 14px;
  }
  .unit-head {
    margin: 0 0 4px;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  .hist {
    margin-top: 16px;
  }
  .hist summary {
    cursor: pointer;
    font-size: var(--fs-small);
    min-height: var(--hit);
    padding-top: 4px;
  }
</style>
