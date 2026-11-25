<!-- Branch page G1–G9 (owner: W6). Minimap, state now, index over time, the series as small multiples (pace or
     level, link to /serie/<key>), not counted series with reason, withheld series as named boxes without values. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { Glyph, StatusBadge, Term, dataUrl, fmt, periodLabel, setChartData, signed, stateStyle } from '$lib/design';
  import { IndexHistory, Minimap, Multiples, UnitBoxes, WithheldBoxes } from '$lib/flow';

  let { data } = $props();
  setChartData(() => dataUrl(`branch/${data.branch.code}.json`));
  const b = $derived(data.branch);
  const st = $derived(stateStyle(b.state));
  const heldCounted = $derived(data.withheld.filter((w) => w.counted));
  const nPub = $derived(data.counted.length);
</script>

<svelte:head><title>{b.code} {b.name} – AI-utrullningen</title></svelte:head>

<p class="kicker crumbs">
  <a href={resolve('/flode')}>Flödet</a>
  {#each data.leads as l (l.code)}
    <span aria-hidden="true">/</span> <a href={resolve('/flode/[led]', { led: l.code })}>{l.code} {l.name}</a>
  {/each}
  <span aria-hidden="true">/</span> <span>{b.code}</span>
</p>
<Minimap leads={data.minimap} current={data.leads.map((l) => l.code)} branch={b.code} />

<header class="hero">
  <h1>{b.code} {b.name}</h1>
  <p class="lede">{b.question}</p>
</header>

<section class="now panel" aria-labelledby="now-h">
  <div class="state">
    <h2 id="now-h" class="kicker">Läget {periodLabel(b.record.month, true)} <StatusBadge status={b.status} /></h2>
    <div class="big" data-state={st.key}><Glyph state={b.state} size="1.15em" /></div>
    <p class="idx">
      <span class="num">{fmt(b.index, 2)}</span>
      <span class="unit"><Term id="diffusionsindex">diffusionsindex</Term>: andel serier som ökar takten, 0–1</span>
    </p>
    {#if b.previous}
      <p class="note">
        Förra månaden ({periodLabel(b.previous.month)}): {fmt(b.previous.index, 2)}
        <Glyph state={b.previous.state} />{#if b.delta_index !== null}, förändring {signed(b.delta_index, 2)}{/if}.
      </p>
    {/if}
    {#if b.index === null}
      <p class="note">Inget index: ingen serie har ett giltigt mått på beräkningsdagen.</p>
    {:else if st.key === 'none'}
      <p class="note">Med färre än tre räknade serier visas indexet men inget tillstånd.</p>
    {/if}
  </div>
  <div class="units">
    <h3 class="kicker">{b.n_series} {b.n_series === 1 ? 'serie räknas' : 'serier räknas'}{#if heldCounted.length}, varav {heldCounted.length} inhållna{/if}</h3>
    {#if b.n_series > 0}
      <UnitBoxes
        label="Räknade serier och deras riktning"
        items={data.counted.map((m) => ({ key: m.key, label: m.label, direction: m.direction }))}
        withheld={heldCounted}
        withheldAnon={Math.max(0, b.n_withheld_counted - heldCounted.length)}
        href={(k) => `#s-${k}`}
      />
    {:else}
      <p class="note">Ingen serie räknas den här månaden.</p>
    {/if}
    <ul class="legend" aria-hidden="true">
      <li><span class="g acc">▲</span>ökar takten</li>
      <li><span class="g stb">●</span>oförändrad takt</li>
      <li><span class="g brk">▼</span>minskar takten</li>
      {#if heldCounted.length}<li><span class="sw held"></span>inhållen, ingen egen riktning</li>{/if}
    </ul>
    <p class="note">Index = (antal ▲ + ½ × antal ●) / antal räknade serier. Accelererar vid minst 0,67, bromsar in vid högst 0,33.</p>
  </div>
</section>

<section class="panel">
  <IndexHistory id="index" history={b.history} status={b.status} lo={data.thresholds.lo} hi={data.thresholds.hi} />
</section>

{#if nPub}
  <section aria-labelledby="counted-h">
    <h2 id="counted-h">Räknade serier</h2>
    <p class="note">
      Takt och riktning ur posten för {periodLabel(b.record.month, true)}, takten oftast i <Term id="log100">log ×100 per år</Term> (≈ procent per
      år för små tal). Punkten i slutet har riktningens färg; mätaren under visar förändringen i takt mot seriens
      <Term id="dodband">dödband</Term> (±0,25 standardavvikelser: inom bandet räknas takten som oförändrad).
    </p>
    <Multiples items={data.counted} label="Räknade serier" />
  </section>
{/if}

{#if data.notCounted.length}
  <section aria-labelledby="nc-h">
    <h2 id="nc-h">Registrerade men inte räknade</h2>
    <p class="note">Kärnserier som inte har ett giltigt mått den här månaden. Skälet står på varje kort.</p>
    <Multiples items={data.notCounted} label="Ej räknade serier" />
  </section>
{/if}

{#if data.withheld.length}
  <section id="inhallna" aria-labelledby="held-h">
    <h2 id="held-h">Inhållna serier ({data.withheld.length})</h2>
    <p class="note">
      Serier som inte får publiceras visas med namn och skäl, aldrig med värden eller egen riktning. De som räknas ingår bara i
      grenens index.
    </p>
    <WithheldBoxes items={data.withheld} />
  </section>
{/if}

<p class="note">Måtten, dödbandet och tillståndsreglerna: <a href={resolve('/metod')}>Metod</a>.</p>

<style>
  .crumbs {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 6px;
    margin: 18px 0 10px;
  }
  .hero {
    margin: 18px 0 8px;
  }
  .now {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 18px 28px;
    margin-top: 14px;
  }
  @media (min-width: 861px) {
    .now {
      grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
    }
  }
  .now h2.kicker,
  .now h3.kicker {
    font-size: var(--fs-small);
    font-weight: 400;
    margin: 0 0 6px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px 10px;
    align-items: center;
  }
  .big {
    font-size: 28px;
    font-weight: 680;
    letter-spacing: -0.01em;
    line-height: 1.2;
  }
  .idx {
    margin: 4px 0 6px;
    display: flex;
    align-items: baseline;
    gap: 10px;
    flex-wrap: wrap;
  }
  .idx .num {
    font-size: var(--fs-big);
    font-weight: 680;
    line-height: 1;
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.02em;
  }
  .idx .unit {
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  .note {
    margin: 4px 0;
  }
  .units .legend {
    margin: 10px 0 4px;
  }
  .g {
    margin-right: 4px;
  }
  .g.acc {
    color: var(--c-acc);
  }
  .g.stb {
    color: var(--c-stb);
  }
  .g.brk {
    color: var(--c-brk);
  }
  .sw.held {
    border: 1px dashed var(--c-ink-2);
    background: repeating-linear-gradient(135deg, var(--c-grid) 0 2px, transparent 2px 5px);
  }
</style>
