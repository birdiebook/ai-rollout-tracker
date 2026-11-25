<!-- The chain L1–L9 (owner: W6). One row per lead in fixed order (P2): branches with state, index and the last 24
     months, the key series as a unit chart, nowcasts; reconciliations between the leads as spans. Each lead links to
     /flode/<L>, each branch to /gren/<G>. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { Glyph, StatusBadge, dataUrl, fmt, periodLabel, setChartData, signed, stateStyle } from '$lib/design';
  import { IndexSpark, SpanChart, UnitBoxes } from '$lib/flow';

  let { data } = $props();
  setChartData(() => dataUrl('flow.json'));
  const c = $derived(data.counts);
  const n = (k: string) => c[k] ?? 0;
  const sentence = $derived(
    `${n('accelererar')} accelererar, ${n('stabil')} ${n('stabil') === 1 ? 'är stabil' : 'är stabila'}, ` +
      `${n('bromsar in') || 'ingen'} bromsar in` +
      // v2's no-state ("för få källor"), v1's in a record before v2, and a branch without core series
      (n('för få källor') ? ` och ${n('för få källor')} har för få källor` : '') +
      (n('för få serier') + n('inga registrerade kärnserier') ? ` och ${n('för få serier') + n('inga registrerade kärnserier')} har för få serier` : '') +
      '.'
  );
</script>

<svelte:head><title>Flödet L1–L9 – AI-utrullningen</title></svelte:head>

<header class="hero">
  <p class="kicker">Kedjan L1→L9 · {periodLabel(data.record.month, true)} <StatusBadge status={data.status} /></p>
  <h1>Flödet från förmåga till forskning</h1>
  <p class="lede">Nio led i fast ordning. Av nio grenar: {sentence}</p>
</header>

<ol class="chain">
  {#each data.leads as l, i (l.code)}
    <li class="lead" id={l.code}>
      <div class="node" aria-hidden="true"><span>{l.code}</span></div>
      <div class="about">
        <h2><a href={resolve('/flode/[led]', { led: l.code })}>{l.code} {l.name}</a></h2>
        <p class="note">{l.content}</p>
        {#if l.nowcasts.length}
          <p class="ncs">
            {#each l.nowcasts as nc (nc.id)}<span class="tag" title={nc.title}>{nc.label}</span>{/each}
            <span class="visually-hidden">prognoser i ledet</span>
          </p>
        {/if}
      </div>
      <ul class="branches" aria-label="Grenar i {l.code}">
        {#each l.branches as b (b.code)}
          {@const s = stateStyle(b.state)}
          <li>
            <a class="bname" href={resolve('/gren/[id]', { id: b.code })}>{b.code} {b.name}</a>
            <span class="bstate"><Glyph state={b.state} /></span>
            <span class="bidx num">{fmt(b.index, 2)}{#if b.delta_index}<small>{signed(b.delta_index, 2)}</small>{/if}</span>
            <span class="bspark"><IndexSpark values={b.spark} lo={data.thresholds.lo} hi={data.thresholds.hi} color={s.key === 'none' ? 'var(--c-muted)' : 'var(--c-ink)'} /></span>
          </li>
        {/each}
      </ul>
      <div class="units">
        <span class="ukick" aria-hidden="true">Nyckelserier</span>
        <UnitBoxes
          label="Nyckelserier i {l.code}"
          items={l.units}
          withheldAnon={l.n_withheld}
          href={(k) => `${resolve('/flode/[led]', { led: l.code })}#s-${k}`}
          withheldHref="{resolve('/flode/[led]', { led: l.code })}#inhallna"
        />
      </div>
      {#if i < data.leads.length - 1}<span class="link" aria-hidden="true"></span>{/if}
    </li>
  {/each}
</ol>

<ul class="legend keys" aria-label="Teckenförklaring">
  <li><span class="g acc" aria-hidden="true">▲</span>serie ökar takten</li>
  <li><span class="g stb" aria-hidden="true">●</span>oförändrad takt</li>
  <li><span class="g brk" aria-hidden="true">▼</span>minskar takten</li>
  <li><span class="sw none" aria-hidden="true"></span>räknas inte denna månad</li>
  <li><span class="sw held" aria-hidden="true"></span>inhållen serie (räknas, ingen egen riktning)</li>
  <li><span class="sw mid" aria-hidden="true"></span>linjen: grenens index {data.sparkFrom ? `sedan ${periodLabel(data.sparkFrom)}` : ''}, grått = stabil zon</li>
</ul>

{#if data.spans.length}
  <section aria-labelledby="rc-h">
    <h2 id="rc-h">Avstämningar mellan leden</h2>
    <p class="note">Kvoter som förbinder led, till exempel investeringar mot intäkter. Riktningen är kvotens förändring i takt.</p>
    <SpanChart spans={data.spans} />
  </section>
{/if}

<style>
  .hero {
    margin: 22px 0 18px;
  }
  .hero .kicker {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 10px;
    align-items: center;
    margin: 0;
  }
  .chain {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 10px;
  }
  .lead {
    position: relative;
    display: grid;
    grid-template-columns: 40px minmax(0, 1fr);
    gap: 8px 14px;
    padding: 14px 16px 14px 12px;
    background: var(--c-surface);
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-lg);
  }
  .node {
    grid-row: span 3;
  }
  .node span {
    display: grid;
    place-items: center;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    border: 1.5px solid var(--c-ink);
    font-size: 13px;
    font-weight: 680;
    background: var(--c-surface);
  }
  .link {
    position: absolute;
    left: 29px;
    bottom: -12px;
    height: 14px;
    border-left: 1.5px solid var(--c-axis);
  }
  .about h2 {
    font-size: 17px;
    margin: 6px 0 0;
  }
  .about .note {
    margin: 0;
  }
  .ncs {
    margin: 6px 0 0;
    display: flex;
    gap: 4px;
  }
  .tag {
    font-size: 11px;
    border: 1px solid var(--c-model);
    color: var(--c-ink);
    border-radius: var(--radius-pill);
    padding: 0 7px;
  }
  .branches {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 6px;
  }
  .branches li {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-areas: 'name idx' 'state spark';
    gap: 2px 10px;
    align-items: center;
    font-size: 14px;
  }
  .bname {
    grid-area: name;
    font-weight: 560;
  }
  .bstate {
    grid-area: state;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  .bidx {
    grid-area: idx;
    text-align: right;
    font-weight: 650;
    font-variant-numeric: tabular-nums;
  }
  .bidx small {
    margin-left: 4px;
    font-weight: 400;
    color: var(--c-ink-2);
  }
  .bspark {
    grid-area: spark;
    width: 96px;
  }
  .units {
    align-self: center;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .ukick {
    font-size: 11px;
    color: var(--c-muted);
  }
  @media (min-width: 900px) {
    .lead {
      grid-template-columns: 40px minmax(0, 1.05fr) minmax(0, 1.5fr) minmax(0, 1fr);
      align-items: center;
    }
    .node {
      grid-row: auto;
    }
    .branches li {
      grid-template-columns: minmax(0, 1fr) 118px 64px 96px;
      grid-template-areas: 'name state idx spark';
    }
    .units {
      justify-self: end;
      align-items: flex-end;
    }
  }
  .keys {
    margin: 14px 0 0;
  }
  /* mobile: one compact block per lead (lesson 3), the description lives on the lead page */
  @media (max-width: 599px) {
    .lead {
      padding: 12px 12px 12px 10px;
      gap: 6px 10px;
    }
    .about .note {
      display: none;
    }
    .units {
      flex-direction: row;
      align-items: center;
      gap: 8px;
    }
    .units :global(.unit) {
      width: 28px;
      height: 28px;
    }
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
  .sw.none {
    border: 1px solid var(--c-axis);
  }
  .sw.mid {
    background: var(--c-mid);
    border: 1px solid var(--c-axis);
  }
</style>
