<!-- Start page (W5): the chain L1→L9, the page's signature picture (P7). Each lead shows its branches' state
     (colour + glyph + word), one mark per counted series, the diffusion index over 24 months and its nowcasts.
     Desktop: nine nodes in a row (three rows of three on medium screens). Mobile (lesson 3): one row per lead
     (glyph, name, index dot) that opens into the full node. Same data, two layouts switched by CSS only, so the
     prerendered HTML is right at every width. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { Deferred, StatusBadge, Term, Tooltip, fmt, provideTooltip, stateStyle } from '$lib/design';
  import IndexSpark from './IndexSpark.svelte';
  import UnitGlyphs from './UnitGlyphs.svelte';
  import type { BranchView, LeadView, StartData } from './model';

  let { start }: { start: StartData } = $props();
  const byCode = $derived(new Map(start.branches.map((b) => [b.code, b])));
  const status = $derived(start.record.status === 'live' ? 'live' : 'recon');
  const tip = provideTooltip();
  let host: HTMLElement | undefined = $state();
  let hostWidth = $state(1000);
  $effect(() => {
    tip.host = host ?? null;
  });
  const br = (code: string) => byCode.get(code) as BranchView;
  const word = (s: string) => (s === 'inga registrerade kärnserier' ? s : stateStyle(s).word);
  const leadWord = (l: LeadView) => (l.state === 'blandat' ? 'olika tillstånd' : word(l.state));
</script>

{#snippet branchBlock(l: LeadView, code: string, alsoIn: string[], full: boolean)}
  {@const b = br(code)}
  {@const st = stateStyle(b.state)}
  <div class="br" data-branch={code}>
    <div class="br-head">
      <a href={resolve('/gren/[id]', { id: code })} aria-label="{code} {b.name}"><b>{code}</b>{#if full} {b.name}{/if}</a>
      <span class="st" data-state={st.key}><span aria-hidden="true" style:color={st.color}>{st.glyph}</span> {word(b.state)}</span>
    </div>
    <UnitGlyphs up={b.n_up} neutral={b.n_neutral} down={b.n_down} withheld={b.n_withheld_counted} />
    <IndexSpark spark={start.sparks[code]} {code} low={start.thresholds.low} high={start.thresholds.high} />
    {#if alsoIn.length}<span class="also">samma gren som i {alsoIn.join(', ')}</span>{/if}
  </div>
{/snippet}

{#snippet nowcastChips(l: LeadView)}
  {#if l.nowcasts.length}
    <span class="ncs">
      {#each l.nowcasts as n (n.id)}
        <a class="nc" href={resolve('/prognoser')} aria-label="{n.label} {n.title}, prognoser">{n.label}</a>
      {/each}
    </span>
  {/if}
{/snippet}

<section class="chain-sec" aria-labelledby="chain-h">
  <div class="sec-head">
    <h2 id="chain-h">Kedjan från förmåga till el</h2>
    <StatusBadge {status} />
  </div>
  <p class="note key">
    <span><span aria-hidden="true" style:color="var(--c-acc)">▲</span> ökar takten</span>
    <span><span aria-hidden="true" style:color="var(--c-stb)">●</span> oförändrad takt</span>
    <span><span aria-hidden="true" style:color="var(--c-brk)">▼</span> minskar takten</span>
    <span>en markering per räknad serie · linjen: {start.branches.some((b) => b.rule_version === 'v2') ? 'medel av källfamiljernas röster' : 'andel serier som ökar takten'} (<Term id="diffusionsindex">diffusionsindex</Term>), {start.sparks[start.branches[0]?.code]?.months.length ?? 24} månader, bandet är stabilt läge ({fmt(start.thresholds.low, 2)}–{fmt(start.thresholds.high, 2)})</span>
  </p>

  <div class="host" bind:this={host} bind:clientWidth={hostWidth}>
    <Deferred>
    <ol class="spine" aria-label="Leden L1 till L9">
      {#each start.leads as l (l.code)}
        <li class="node" data-lead={l.code}>
          <div class="top">
            <span class="code">{l.code}</span>
            {@render nowcastChips(l)}
          </div>
          <a class="name" href={resolve('/flode/[led]', { led: l.code })}>{l.name}</a>
          {#each l.branches as b (b.code)}
            {@render branchBlock(l, b.code, b.alsoIn, false)}
          {/each}
        </li>
      {/each}
    </ol>

    <ol class="list" aria-label="Leden L1 till L9">
      {#each start.leads as l (l.code)}
        <li data-lead={l.code}>
          <details>
            <summary>
              <span class="code">{l.code}</span>
              <span class="lname">{l.name}</span>
              <span class="glyphs">
                {#each l.branches as b (b.code)}
                  {@const st = stateStyle(br(b.code).state)}
                  <span aria-hidden="true" style:color={st.color}>{st.glyph}</span>
                {/each}
                <span class="visually-hidden">{leadWord(l)}</span>
              </span>
              <svg class="track" viewBox="0 0 64 14" width="64" height="14" aria-hidden="true">
                <rect x={4 + 56 * start.thresholds.low} y="3" width={56 * (start.thresholds.high - start.thresholds.low)} height="8" rx="2" fill="var(--c-mid)" />
                <line x1="4" x2="60" y1="7" y2="7" class="axisline" />
                {#each l.branches as b (b.code)}
                  {@const v = br(b.code).index}
                  {@const st = stateStyle(br(b.code).state)}
                  {#if v !== null}
                    <circle class="mark" cx={4 + 56 * v} cy="7" r="4" fill={st.key === 'none' ? 'var(--c-surface)' : st.color} stroke={st.key === 'none' ? 'var(--c-muted)' : 'var(--c-surface)'} stroke-width="1.5" />
                  {/if}
                {/each}
              </svg>
              <span class="chev" aria-hidden="true"></span>
            </summary>
            <div class="body">
              <p class="note content">{l.content}</p>
              <div class="bodies">
                {#each l.branches as b (b.code)}
                  {@render branchBlock(l, b.code, b.alsoIn, true)}
                {/each}
              </div>
              <p class="more">
                {@render nowcastChips(l)}
                <a href={resolve('/flode/[led]', { led: l.code })}>{l.code} i flödet <span aria-hidden="true">→</span></a>
              </p>
            </div>
          </details>
        </li>
      {/each}
    </ol>
    </Deferred>
    <Tooltip state={tip} {hostWidth} />
  </div>
</section>

<style>
  .sec-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 12px;
  }
  .key {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 14px;
    margin: 2px 0 14px;
  }
  .host {
    position: relative;
  }
  /* ---------- desktop / tablet: the spine ---------- */
  .spine {
    list-style: none;
    margin: 0;
    padding: 0;
    display: none;
    gap: 12px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .node {
    position: relative;
    background: var(--c-surface);
    border: 1px solid var(--c-ring);
    border-radius: 12px;
    padding: 10px 10px 10px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
  }
  .node::after {
    content: '';
    position: absolute;
    right: -11px;
    top: 21px;
    width: 10px;
    height: 10px;
    background: var(--c-axis);
    clip-path: polygon(0 0, 100% 50%, 0 100%);
    z-index: 1;
  }
  .node:hover {
    border-color: var(--c-axis);
  }
  .top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 4px;
    min-height: 20px;
  }
  .code {
    font-size: 12px;
    color: var(--c-muted);
    font-weight: 650;
    letter-spacing: 0.03em;
  }
  .name {
    font-size: 13px;
    font-weight: 620;
    line-height: 1.2;
    min-height: 2.4em;
    text-decoration: none;
  }
  .name:hover {
    text-decoration: underline;
  }
  .br {
    display: flex;
    flex-direction: column;
    gap: 5px;
    padding-top: 8px;
    border-top: 1px solid var(--c-grid);
    min-width: 0;
  }
  .br-head {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 2px 8px;
    font-size: 12px;
  }
  .br-head a {
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    min-height: 24px;
  }
  .br-head a:hover {
    text-decoration: underline;
  }
  .st {
    color: var(--c-ink);
    white-space: nowrap;
    font-weight: 560;
  }
  .st[data-state='none'] {
    color: var(--c-muted);
    font-weight: 400;
  }
  .also {
    font-size: 11px;
    color: var(--c-muted);
    line-height: 1.2;
  }
  .ncs {
    display: inline-flex;
    gap: 4px;
    flex-wrap: wrap;
  }
  .nc {
    font-size: 11px;
    line-height: 18px;
    padding: 0 7px;
    border: 1px solid var(--c-model);
    border-radius: var(--radius-pill);
    color: var(--c-ink-2);
    text-decoration: none;
    min-width: 24px;
    min-height: 24px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  .nc:hover {
    background: var(--c-model-80);
    color: var(--c-ink);
  }
  @media (min-width: 700px) {
    .spine {
      display: grid;
    }
    .list {
      display: none;
    }
    .node:nth-child(3n)::after {
      display: none;
    }
  }
  @media (min-width: 1100px) {
    .spine {
      grid-template-columns: repeat(9, minmax(0, 1fr));
      gap: 12px;
    }
    .node:nth-child(3n)::after {
      display: block;
    }
    .node:last-child::after {
      display: none;
    }
  }
  /* ---------- mobile: one row per lead, opens into the node ---------- */
  .list {
    list-style: none;
    margin: 0;
    padding: 0;
    border: 1px solid var(--c-ring);
    border-radius: 12px;
    background: var(--c-surface);
  }
  .list > li + li {
    border-top: 1px solid var(--c-grid);
  }
  summary {
    display: grid;
    grid-template-columns: 26px minmax(0, 1fr) auto 64px 10px;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    min-height: 44px;
    cursor: pointer;
    list-style: none;
  }
  summary::-webkit-details-marker {
    display: none;
  }
  .lname {
    font-size: 14px;
    font-weight: 560;
    line-height: 1.2;
  }
  .glyphs {
    display: inline-flex;
    gap: 3px;
    font-size: 14px;
  }
  .track {
    display: block;
  }
  .chev {
    width: 8px;
    height: 8px;
    border-right: 1.5px solid var(--c-muted);
    border-bottom: 1.5px solid var(--c-muted);
    transform: rotate(-45deg);
    transition: transform var(--motion-fast) var(--easing);
  }
  details[open] .chev {
    transform: rotate(45deg);
  }
  details[open] summary {
    background: var(--c-page);
  }
  .body {
    padding: 4px 12px 12px;
  }
  .content {
    margin: 4px 0 8px;
  }
  .bodies {
    display: grid;
    gap: 10px;
  }
  .more {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin: 10px 0 0;
    font-size: var(--fs-small);
  }
  .more > a {
    display: inline-flex;
    align-items: center;
    min-height: var(--hit);
  }
  @media (forced-colors: active) {
    .st span,
    .glyphs span,
    .key span span {
      color: CanvasText !important;
    }
  }
</style>
