<!-- Pre-registration, holdout and the promotion rule (track W11; docs/mattregister.md G-E, G-B, F-E6). A timeline of
     what was locked when, and a Holm ladder the reader can move: invented p-values, marked "utforskning". The Holm
     adjustment is engine.ts's, golden-tested against evaluation.holm. -->
<script lang="ts">
  import { scaleLinear, scaleUtc } from 'd3-scale';
  import { Axis, ChartFrame, fmt } from '$lib/design';
  import { holm, promoted } from './engine';

  let { registerFile, registerSha, registerHref }: { registerFile: string; registerSha: string | null; registerHref: string | null } = $props();

  // Dates from docs/mattregister.md ("Steg 2: förregistrering", G-E Holdout).
  const T = (d: string) => Date.parse(d + 'T00:00:00Z');
  const PHASES = [
    { from: '2019-01-01', to: '2025-06-30', label: 'utveckling', cls: 'dev', text: 'Metoder utvecklas bara med prognosdagar t.o.m. 30 juni 2025' },
    { from: '2025-07-01', to: '2026-10-31', label: 'låst holdout', cls: 'hold', text: 'Holdout 1 juli 2025–31 oktober 2026, öppnas en gång per metodfamilj' },
    { from: '2026-12-01', to: '2027-12-31', label: 'skarpt register', cls: 'live', text: 'Skarpa, tidsstämplade prognoser från december 2026 är slutligt facit' }
  ];
  const MARKS = [{ date: '2026-11-23', label: 'registret låst' }];

  const ALPHA = 0.1;
  let p = $state({ B2: 0.03, B3: 0.045, DF: 0.2 } as Record<string, number>);
  let maeAll = $state({ B2: true, B3: true, DF: true } as Record<string, boolean>);
  let maeRecent = $state({ B2: true, B3: false, DF: true } as Record<string, boolean>);
  const adj = $derived(holm(p));
  const ladder = $derived(
    Object.entries(p)
      .sort((a, b) => a[1] - b[1] || (a[0] < b[0] ? -1 : 1))
      .map(([k, v], i, all) => ({ k, raw: v, mult: all.length - i, adj: adj[k] }))
  );
  const verdict = (k: string) => promoted(adj[k], maeAll[k], maeRecent[k], ALPHA);
  const why = (k: string) =>
    verdict(k)
      ? 'befordras'
      : `stannar som skugga (${[adj[k] >= ALPHA ? 'Holm-p för högt' : '', !maeAll[k] ? 'MAE inte lägre i hela perioden' : '', !maeRecent[k] ? 'MAE inte lägre från 2023' : ''].filter(Boolean).join(', ')})`;
  const xMax = $derived(Math.max(0.35, ...Object.values(adj)) * 1.08);
  const pTxt = (x: number) => fmt(x, 3);
</script>

<ChartFrame
  id="prereg-timeline"
  title="Vad som låstes när"
  description="Mått, tillståndsregler och intervallmetod låstes i måttregistret 23 november 2026, innan steg 2 kördes på verklig data. Komplexa metoder utvecklas på perioden till och med juni 2025, prövas en gång på den låsta holdouten och avgörs till slut i det skarpa registret."
  height={128}
  margin={{ top: 30, right: 14, bottom: 26, left: 14 }}
  table={{
    columns: [
      { key: 'f', label: 'Från', align: 'left' },
      { key: 't', label: 'Till', align: 'left' },
      { key: 'x', label: 'Vad', align: 'left' }
    ],
    rows: PHASES.map((ph) => ({ f: ph.from, t: ph.cls === 'live' ? 'pågår' : ph.to, x: ph.text }))
  }}
>
  {#snippet children(d)}
    {@const x = scaleUtc().domain([T('2019-01-01'), T('2027-12-31')]).range([d.left, d.right])}
    <Axis scale={x} dims={d} tickValues={[2019, 2021, 2023, 2025, 2027].map((y) => new Date(Date.UTC(y, 0, 1)))} format={(v) => String(v.getUTCFullYear())} />
    {#each PHASES as ph (ph.cls)}
      <rect class="ph {ph.cls}" x={x(T(ph.from))} width={Math.max(2, x(T(ph.to)) - x(T(ph.from)))} y={d.top + 10} height={d.bottom - d.top - 16} rx="3" />
      <text class="ink" x={x(T(ph.from)) + 5} y={d.top + 10 + (d.bottom - d.top - 16) / 2 + 4}>{d.innerWidth < 500 && ph.cls !== 'dev' ? '' : ph.label}</text>
    {/each}
    {#each MARKS as m (m.date)}
      <line class="lock" x1={x(T(m.date))} x2={x(T(m.date))} y1={d.top - 4} y2={d.bottom} />
      <text class="ink" x={x(T(m.date)) - 4} y={d.top - 10} text-anchor="end">{m.label} 23 nov 2026</text>
    {/each}
  {/snippet}
</ChartFrame>
<p class="note phases">
  {#each PHASES as ph (ph.cls)}<span class="ph-key {ph.cls}" aria-hidden="true"></span> {ph.text}. {/each}
</p>

<div class="gates" aria-label="Befordringsregeln">
  <div class="gate"><span class="n">1</span><span>Holm-justerat p &lt; 0,10 inom målets familj av varianter</span></div>
  <span class="and" aria-hidden="true">och</span>
  <div class="gate"><span class="n">2</span><span>Lägre MAE än jämförelsemodellen i hela perioden</span></div>
  <span class="and" aria-hidden="true">och</span>
  <div class="gate"><span class="n">3</span><span>Lägre MAE från 2023 (komplexa familjer: på holdouten och i utvecklingsperioden)</span></div>
  <span class="and" aria-hidden="true">→</span>
  <div class="gate out"><span>Ny huvudmodell. Annars skugga i det skarpa registret.</span></div>
</div>

<h3 class="sub">Holm-trappan <span class="tag exp">utforskning med påhittade p-värden</span></h3>
<p class="note">
  Med tre varianter testas den med lägst p mot 0,10/3, nästa mot 0,10/2 och den sista mot 0,10. Justerat p = p × antal kvar, och
  aldrig lägre än föregående steg. Dra i p-värdena och kryssa i MAE-villkoren.
</p>
<div class="holm">
  {#each Object.keys(p) as k (k)}
    <div class="row">
      <label class="pv">
        <span>{k}: p = <strong class="num">{pTxt(p[k])}</strong></span>
        <input type="range" min="0.001" max="0.3" step="0.001" bind:value={p[k]} aria-valuetext="{k}: p {pTxt(p[k])}, Holm-justerat {pTxt(adj[k])}" />
      </label>
      <label class="cb"><input type="checkbox" bind:checked={maeAll[k]} /> lägre MAE, hela perioden</label>
      <label class="cb"><input type="checkbox" bind:checked={maeRecent[k]} /> lägre MAE, från 2023</label>
    </div>
  {/each}
</div>

<ChartFrame
  id="prereg-holm"
  title="Justerade p-värden mot gränsen 0,10"
  description={ladder.map((r) => `${r.k}: p ${pTxt(r.raw)} × ${r.mult} → ${pTxt(r.adj)}, ${why(r.k)}`).join('. ') + '.'}
  height={150}
  margin={{ top: 10, right: 120, bottom: 26, left: 44 }}
  table={{
    columns: [
      { key: 'k', label: 'Variant', align: 'left' },
      { key: 'p', label: 'p' },
      { key: 'm', label: '× kvar' },
      { key: 'a', label: 'Holm-p' },
      { key: 'v', label: 'Utfall', align: 'left' }
    ],
    rows: ladder.map((r) => ({ k: r.k, p: pTxt(r.raw), m: r.mult, a: pTxt(r.adj), v: why(r.k) }))
  }}
>
  {#snippet children(d)}
    {@const x = scaleLinear().domain([0, xMax]).range([d.left, d.right]).clamp(true)}
    {@const rowH = (d.bottom - d.top) / ladder.length}
    <Axis scale={x} dims={d} tickValues={[0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1].filter((t) => t <= xMax)} format={(v) => fmt(v, 1)} />
    <line class="alpha" x1={x(ALPHA)} x2={x(ALPHA)} y1={d.top} y2={d.bottom} />
    {#each ladder as r, i (r.k)}
      {@const y = d.top + rowH * (i + 0.5)}
      <text class="ink" x={d.left - 8} y={y + 4} text-anchor="end">{r.k}</text>
      <line class="arrow" x1={x(r.raw)} x2={x(r.adj)} y1={y} y2={y} />
      <circle class="mark raw" cx={x(r.raw)} cy={y} r="4" />
      <circle class="mark adjd" class:pass={r.adj < ALPHA} cx={x(r.adj)} cy={y} r="6" />
      <text class="ink2" x={d.right + 8} y={y + 4}>{verdict(r.k) ? '▲ befordras' : '● skugga'}</text>
    {/each}
  {/snippet}
</ChartFrame>

<p class="note">
  Registret: <code>{registerFile}</code>{#if registerSha}, SHA-256 <code class="sha">{registerSha.slice(0, 12)}…</code>{/if}.
  {#if registerHref}<a href={registerHref} rel="noopener" referrerpolicy="no-referrer">Läs registret</a>.{/if}
  Ändringar läggs till längst ned med datum och motivering, och inget skrivs om.
</p>

<style>
  .ph.dev {
    fill: var(--c-mid);
    stroke: var(--c-axis);
  }
  .ph.hold {
    fill: var(--c-model-50);
    stroke: var(--c-model);
    stroke-dasharray: 4 3;
  }
  .ph.live {
    fill: var(--c-surface);
    stroke: var(--c-ink);
    stroke-width: 1.5;
  }
  .lock {
    stroke: var(--c-ink);
    stroke-width: 2;
  }
  .phases {
    margin-top: 2px;
  }
  .ph-key {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 3px;
    vertical-align: -1px;
    margin-left: 4px;
  }
  .ph-key.dev {
    background: var(--c-mid);
    border: 1px solid var(--c-axis);
  }
  .ph-key.hold {
    background: var(--c-model-50);
    border: 1px dashed var(--c-model);
  }
  .ph-key.live {
    background: var(--c-surface);
    border: 1.5px solid var(--c-ink);
  }
  .gates {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin: 16px 0;
  }
  .gate {
    display: flex;
    gap: 8px;
    align-items: center;
    background: var(--c-surface);
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-md);
    padding: 8px 12px;
    font-size: var(--fs-small);
    max-width: 260px;
  }
  .gate.out {
    border-color: var(--c-ink);
  }
  .gate .n {
    font-weight: 700;
    border: 1.5px solid var(--c-ink);
    border-radius: 50%;
    width: 22px;
    height: 22px;
    display: inline-grid;
    place-items: center;
    flex: none;
  }
  .and {
    font-size: var(--fs-small);
    color: var(--c-muted);
  }
  .sub {
    margin-top: 18px;
  }
  .tag {
    font-size: 12px;
    border: 1px dashed var(--c-ink-2);
    border-radius: 999px;
    padding: 1px 8px;
    font-weight: 400;
    vertical-align: 2px;
  }
  .holm {
    display: grid;
    gap: 6px;
    margin: 8px 0 10px;
  }
  .row {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 16px;
    align-items: center;
    font-size: var(--fs-small);
  }
  .pv {
    display: grid;
    flex: 1 1 240px;
  }
  .pv input {
    width: 100%;
    min-height: var(--hit);
    accent-color: var(--c-ink);
  }
  .cb {
    display: inline-flex;
    gap: 6px;
    align-items: center;
    min-height: var(--hit);
  }
  .cb input {
    width: 18px;
    height: 18px;
    accent-color: var(--c-ink);
  }
  .alpha {
    stroke: var(--c-ink);
    stroke-dasharray: 4 3;
  }
  .arrow {
    stroke: var(--c-axis);
    stroke-width: 2;
  }
  .raw {
    fill: var(--c-surface);
    stroke: var(--c-ink-2);
    stroke-width: 1.5;
  }
  .adjd {
    fill: var(--c-surface);
    stroke: var(--c-ink);
    stroke-width: 2;
  }
  .adjd.pass {
    fill: var(--c-ink);
  }
  .sha {
    font-size: 12px;
  }
</style>
