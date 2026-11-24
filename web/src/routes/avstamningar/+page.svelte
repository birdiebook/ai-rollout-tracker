<!-- /avstamningar (owner: W10). The A5 reconciliations between the leads: one picture of where every ratio's pace
     sits in its own history, the ratios on the chain, then one section per ratio with its components. The ratios
     are not counted in any branch index (register A5); the page says so at the top and on every ratio. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { StatusBadge, periodLabel } from '$lib/design';
  import { SpanChart } from '$lib/flow';
  import { ReconOverview, ReconSection } from '$lib/regime';

  let { data } = $props();
</script>

<svelte:head><title>Avstämningar – AI-utrullningen</title></svelte:head>

<header class="hero">
  <p class="kicker">Avstämningar mellan leden · {periodLabel(data.record.month, true)} <StatusBadge status={data.status} /></p>
  <h1>Går leden ihop?</h1>
  <p class="lede">
    Kvoter mellan leden, till exempel investeringar mot molnintäkter. När en kvot rör sig växer det ena ledet snabbare än
    det andra. Varje kvot visas med nivå, takt, var takten ligger i sin egen historik, riktning och hur täljaren och nämnaren
    bidrar.
  </p>
  <p class="callout">
    <strong>Räknas inte i grenarnas index.</strong> Avstämningarna (<code>x_*</code>) är förregistrerade som en egen
    redovisning (måttregistret, A5). De påverkar inget diffusionsindex och inget tillstånd, och regimmodellen använder dem inte.
  </p>
</header>

{#if !data.views.length}
  <p class="panel note">Inga publicerbara avstämningar i paketet{data.hidden ? ` (${data.hidden} inhållna)` : ''}.</p>
{:else}
  <section class="panel" aria-label="Översikt">
    <ReconOverview views={data.views} status={data.status} />
    <nav class="toc" aria-label="Avstämningarna">
      {#each data.views as v (v.key)}<a href="#{v.key}">{v.short} <span>{v.lead}</span></a>{/each}
    </nav>
  </section>

  <section aria-labelledby="chain-h">
    <h2 id="chain-h">Var i kedjan</h2>
    <p class="note">Varje kvot förbinder de led den spänner över. Riktningen är kvotens förändring i takt.</p>
    <SpanChart spans={data.spans} />
    {#if data.hidden}<p class="note">{data.hidden} avstämningar hålls inne av licensskäl och visas inte.</p>{/if}
  </section>

  {#each data.views as v (v.key)}
    <ReconSection r={v} />
  {/each}
{/if}

<p class="note end">
  Läs om måtten på <a href={resolve('/metod')}>metodsidan</a>. Takt = årsförändring i log(kvot) ×100, förändring i takt
  och percentiler som för alla serier. En kvot kan röra sig för att täljaren växer, för att nämnaren krymper, eller båda.
  Riktningen säger inget om vilket som är bra.
</p>

<style>
  .hero {
    margin: 22px 0 18px;
    display: grid;
    gap: 8px;
  }
  .hero .kicker {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 10px;
    align-items: center;
    margin: 0;
  }
  h1 {
    margin: 0;
  }
  .callout {
    margin: 4px 0 0;
    max-width: 72ch;
    padding: 8px 12px;
    border: 1px dashed var(--c-axis);
    border-radius: var(--radius-md);
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  .toc {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 12px;
  }
  .toc a {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-height: var(--hit);
    padding: 2px 10px;
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-pill);
    font-size: 13px;
    text-decoration: none;
    color: var(--c-ink);
    background: var(--c-page);
  }
  .toc a span {
    color: var(--c-muted);
    font-size: 11px;
  }
  .toc a:hover {
    border-color: var(--c-ink);
  }
  .end {
    margin-top: 28px;
    max-width: 72ch;
  }
  :global(.rc) {
    margin: 22px 0;
  }
</style>
