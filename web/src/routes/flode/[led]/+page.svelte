<!-- One lead L1–L9 (owner: W6): minimap, the lead's branches with index over time, key series as small multiples,
     nowcasts, reconciliations touching the lead, withheld key series, up- and downstream. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { Glyph, StatusBadge, dataUrl, fmt, periodLabel, dateLabel, setChartData } from '$lib/design';
  import { IndexHistory, Minimap, Multiples, SpanChart, UnitBoxes, WithheldBoxes } from '$lib/flow';

  let { data } = $props();
  setChartData(() => dataUrl('flow.json'));
  const l = $derived(data.lead);
</script>

<svelte:head><title>{l.code} {l.name} – AI-utrullningen</title></svelte:head>

<p class="kicker crumbs"><a href={resolve('/flode')}>Flödet</a> <span aria-hidden="true">/</span> <span>{l.code}</span></p>
<Minimap leads={data.minimap} current={[l.code]} />

<header class="hero">
  <h1>{l.code} {l.name}</h1>
  <p class="lede">{l.content}. <StatusBadge status={data.status} /></p>
</header>

<nav class="updown" aria-label="Uppströms och nedströms">
  {#if data.prev}
    <a class="chip" href={resolve('/flode/[led]', { led: data.prev.code })}><span aria-hidden="true">←</span> {data.prev.code} {data.prev.name}</a>
  {/if}
  {#if data.next}
    <a class="chip next" href={resolve('/flode/[led]', { led: data.next.code })}>{data.next.code} {data.next.name} <span aria-hidden="true">→</span></a>
  {/if}
</nav>

<section aria-labelledby="br-h">
  <h2 id="br-h">{data.branches.length === 1 ? 'Grenen' : 'Grenarna'} i ledet</h2>
  <div class="branches" class:two={data.branches.length > 1}>
    {#each data.branches as b (b.code)}
      <article class="panel br">
        <div class="br-head">
          <h3><a href={resolve('/gren/[id]', { id: b.code })}>{b.code} {b.name}</a></h3>
          <span class="state"><Glyph state={b.state} /></span>
          <span class="num">{fmt(b.index, 2)}</span>
        </div>
        <p class="note q">{b.question} {b.n_series} {b.n_series === 1 ? 'serie räknas' : 'serier räknas'}.</p>
        <IndexHistory
          id="index-{b.code}"
          title="{b.code}: index över tid"
          history={b.history}
          status={data.status}
          lo={data.thresholds.lo}
          hi={data.thresholds.hi}
          height={170}
          headingLevel={4}
          showLegend={false}
        />
      </article>
    {/each}
  </div>
</section>

<section aria-labelledby="ks-h">
  <h2 id="ks-h">Nyckelserier</h2>
  {#if data.series.length || l.n_withheld}
    <div class="units-row">
      <UnitBoxes
        label="Nyckelseriernas riktning"
        items={data.series.map((m) => ({ key: m.key, label: m.label, direction: m.direction, counted: m.counted }))}
        withheld={data.withheld}
        withheldAnon={data.withheldAnon}
        href={(k) => `#s-${k}`}
      />
      <p class="note">
        {data.series.length} publicerade{#if l.n_withheld}, {l.n_withheld} inhållna{/if}. Takt och riktning ur posten för
        {periodLabel(data.record.month, true)}.
      </p>
    </div>
    <Multiples items={data.series} label="Nyckelserier" showBranch />
  {:else}
    <p class="note">Ledet har inga nyckelserier i posten.</p>
  {/if}
</section>

{#if data.nowcasts.length}
  <section aria-labelledby="nc-h">
    <h2 id="nc-h">Prognoser i ledet</h2>
    <ul class="nowcasts">
      {#each data.nowcasts as n (n.id)}
        <li class="panel">
          <span class="nc-id">{n.label}</span>
          <span class="nc-title">{n.title}</span>
          {#if n.latest && n.latest.value !== null}
            <span class="nc-val">
              <span class="num">{fmt(n.latest.value, n.decimals)}</span>
              {n.unit ?? ''} för {periodLabel(n.latest.period ?? '')}{#if n.latest.interval_80}, 80 %: {fmt(n.latest.interval_80[0], n.decimals)}–{fmt(
                  n.latest.interval_80[1],
                  n.decimals
                )}{/if}
            </span>
          {:else}
            <span class="note">Ingen skarp prognos än.</span>
          {/if}
          <span class="note">
            Huvudmodell {n.champion}.{#if n.next_origin}{' '}Nästa prognos {dateLabel(n.next_origin)}{n.next_period ? ` för ${periodLabel(n.next_period)}` : ''}.{/if}
          </span>
        </li>
      {/each}
    </ul>
    <p class="note"><a href={resolve('/prognoser')}>Alla prognoser med intervall och facit</a></p>
  </section>
{/if}

{#if data.reconciliations.spans.length}
  <section aria-labelledby="rc-h">
    <h2 id="rc-h">Avstämningar som rör {l.code}</h2>
    <p class="note">Kvoter mellan leden. Stapeln visar vilka led kvoten förbinder.</p>
    <SpanChart spans={data.reconciliations.spans} current={l.code} />
    {#if data.reconciliations.series.length}
      <div class="rec-multiples">
        <Multiples items={data.reconciliations.series} label="Avstämningar" />
      </div>
    {/if}
  </section>
{/if}

{#if data.withheld.length || data.withheldAnon}
  <section id="inhallna" aria-labelledby="held-h">
    <h2 id="held-h">Inhållna nyckelserier ({l.n_withheld})</h2>
    <p class="note">Visas med namn och skäl, aldrig med värden eller egen riktning.</p>
    <WithheldBoxes items={data.withheld} anon={data.withheldAnon} />
  </section>
{/if}

<style>
  .crumbs {
    display: flex;
    gap: 6px;
    margin: 18px 0 10px;
  }
  .hero {
    margin: 18px 0 8px;
  }
  .updown {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 10px 0 0;
  }
  .updown a {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    text-decoration: none;
  }
  .updown .next {
    margin-left: auto;
  }
  .branches {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 12px;
  }
  @media (min-width: 861px) {
    .branches.two {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
  .br-head {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 4px 12px;
  }
  .br-head h3 {
    font-size: 17px;
  }
  .br-head .num {
    margin-left: auto;
    font-size: 26px;
    font-weight: 680;
    font-variant-numeric: tabular-nums;
  }
  .q {
    margin: 2px 0 10px;
  }
  .units-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 16px;
    margin: 8px 0 4px;
  }
  .units-row .note {
    margin: 0;
  }
  .nowcasts {
    list-style: none;
    margin: 8px 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr));
    gap: 10px;
  }
  .nowcasts li {
    display: flex;
    flex-direction: column;
    gap: 3px;
    padding: 14px;
  }
  .nc-id {
    font-size: 12px;
    font-weight: 650;
    color: var(--c-ink-2);
  }
  .nc-title {
    font-weight: 600;
  }
  .nc-val .num {
    font-size: 22px;
    font-weight: 680;
    font-variant-numeric: tabular-nums;
  }
  .rec-multiples {
    margin-top: 14px;
  }
</style>
