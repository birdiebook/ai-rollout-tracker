<!-- Expectations against outcomes (register F1; datakontrakt "Läsanvisningar för körning 13"): the revision index
     (share of raises of the companies' own guidance, unchanged counts half), the surprise of the outcome against the
     guidance per company and the surprise index. Level and percentile against the measure's own history, no pace,
     never in a branch index. A row whose numbers are withheld (publish=False) is a hatched, counted box with company,
     period and date only. -->
<script lang="ts">
  import { DIRECTIONS, StatusBadge, dateLabel, divergingFill, fmt, signed } from '$lib/design';
  // the surprise bars are neutral ink: above or below guidance is a sign, not a direction of pace
  import { expectationsSentence, type ExpectationsView, type IndexCard } from './expectations';

  let { v }: { v: ExpectationsView } = $props();
  const sentence = $derived(expectationsSentence(v));
  const maxAbs = $derived(Math.max(10, ...v.companies.map((c) => Math.abs(c.surprise ?? 0))));
  const pct = (x: number | null) => (x === null ? '–' : `${fmt(x, 0)}:e percentilen`);
  const qLabel = (p: string | null) => (p ? p.replace(/^(\d{4})Q(\d)$/, '$2:a kv. $1').replace(/^CY:(\d{4})$/, 'år $1') : '–');
</script>

{#snippet indexCard(title: string, c: IndexCard | null, what: string)}
  <div class="card" class:held={c?.withheld} data-testid="exp-card">
    <p class="ct">{title}</p>
    {#if !c}
      <p class="sub">Inga händelser i posten.</p>
    {:else if c.withheld}
      <p class="sub">Räknas, men värdet visas inte: det bygger på bolagsuppgifter som ännu inte får publiceras.</p>
      <p class="sub">{qLabel(c.period)}{c.known_from ? ` · känd ${dateLabel(c.known_from)}` : ''}</p>
    {:else}
      <p class="big num">{fmt(c.value, 2)}</p>
      {#if c.value !== null}
        <span class="bar" aria-hidden="true">
          <span class="fill" style:width="{Math.max(0, Math.min(1, c.value)) * 100}%" style:background={divergingFill(c.value)}></span>
          <span class="mid"></span>
        </span>
      {/if}
      <p class="sub">
        {what}{c.n !== null ? `, n = ${c.n}` : ''}{c.up !== null ? ` (▲ ${c.up} · ● ${c.unchanged ?? 0} · ▼ ${c.down ?? 0})` : ''}
      </p>
      <p class="sub">{qLabel(c.period)} · {pct(c.percentile)}{c.n_history ? ` av ${c.n_history}` : ''}{c.known_from ? ` · känd ${dateLabel(c.known_from)}` : ''}</p>
    {/if}
  </div>
{/snippet}

<section class="exp panel" id="forvantningar" aria-labelledby="exp-h">
  <header class="top">
    <p class="kick"><span class="tag">F1</span><span class="nc">räknas inte i grenarnas index</span> <StatusBadge status={v.status} /></p>
    <h2 id="exp-h">Förväntningar mot utfall</h2>
    <p class="lede">
      Hur bolagen ändrar sin egen guidance, och hur utfallet blev mot den. Revideringsindexet är andelen höjningar (oförändrad
      räknas som en halv) över fyra kvartal och med minst {v.minEvents ?? 3} revideringar: över 0,5 betyder fler höjningar än
      sänkningar. Överraskningen är utfallet mot bolagets guidance i log ×100, och överraskningsindexet är medel av
      standardiserade överraskningar över minst {v.minCompanies ?? 2} bolag. Ingen takt: nivå och percentil mot egen historik.
    </p>
    <p class="note caveat">
      Förbehåll: få händelser per kvartal (n står bredvid). {#if !v.csvPublic}Uppgifterna om Microsofts, Alphabets, Amazons och
        Metas capex-guidance kommer ur en kurerad fil som ännu inte får publiceras: de räknas, men visas här bara med bolag,
        period och datum.{/if}
      {#if v.status === 'recon'}Räknat i efterhand för {dateLabel(v.date)} på data som var kända då.{/if}
    </p>
    <p class="note" data-testid="exp-sentence">{sentence}</p>
  </header>

  {#if !v.available}
    <p class="note">Avsnittet kunde inte räknas för posten.</p>
  {:else}
    <div class="cards">
      {@render indexCard(`Revideringsindex, ${v.window ?? 4} kvartal`, v.revision4q, 'andel höjningar')}
      {@render indexCard('Revideringsindex, kvartalet', v.revisionQ, 'andel höjningar')}
      {@render indexCard('Överraskningsindex', v.surpriseIndex, 'medel av z')}
    </div>

    {#if v.companies.length}
      <h3 class="sub-h">Utfall mot egen guidance, senaste per bolag</h3>
      <ul class="sur" aria-label="Överraskning mot guidance per bolag">
        {#each v.companies as c (c.company + (c.measure ?? ''))}
          <li class="row" class:held={c.withheld}>
            <span class="who">{c.name}<span class="m">{c.measure ?? ''} · {qLabel(c.period)}</span></span>
            {#if c.withheld}
              <span class="box held-box" aria-hidden="true"></span>
              <span class="val sub">räknas, värdet visas inte{c.known_from ? ` · känd ${dateLabel(c.known_from)}` : ''}</span>
            {:else}
              <span class="axis" aria-hidden="true">
                <span class="zero"></span>
                {#if c.surprise !== null}
                  <span
                    class="seg"
                    style:left="{50 + Math.min(0, c.surprise / maxAbs) * 50}%"
                    style:width="{(Math.abs(c.surprise) / maxAbs) * 50}%"
                    style:background="var(--c-ink-2)"
                  ></span>
                {/if}
              </span>
              <span class="val">
                <strong class="num">{signed(c.surprise, 1)}</strong> log ×100{c.z !== null ? ` · z ${signed(c.z, 2)}` : ''} · {pct(c.percentile)}{c.n !== null ? ` · n = ${c.n}` : ''}
              </span>
            {/if}
          </li>
        {/each}
      </ul>
    {/if}

    {#if v.events.length}
      <h3 class="sub-h">Senaste revideringarna av guidance</h3>
      <ul class="events" aria-label="Senaste revideringarna av guidance">
        {#each v.events as e, i (i)}
          {@const st = e.direction === null ? null : DIRECTIONS[e.direction]}
          <li>
            <span
              class="unit"
              class:held={e.withheld}
              class:nodir={!e.withheld && !st}
              style:background={st ? st.color : undefined}
              title="{e.name} {e.known_from ?? ''}: {e.withheld ? 'räknas, riktningen visas inte' : st ? st.word : 'ingen riktning'}"
            >
              <span aria-hidden="true">{st ? st.glyph : ''}</span>
            </span>
            <span class="el">{e.name}<span class="m">{e.known_from ? dateLabel(e.known_from) : ''}</span></span>
            <span class="visually-hidden">{e.withheld ? 'räknas, riktningen visas inte' : st ? st.word : 'ingen riktning'}</span>
          </li>
        {/each}
      </ul>
    {/if}

    {#if v.breaks.length}
      <p class="note">
        Definitionsbrott hålls utanför jämförelsen: {v.breaks.map((b) => `${b.name} ${qLabel(b.period)} (${b.known_from ? dateLabel(b.known_from) : '–'})`).join(', ')}.
      </p>
    {/if}
  {/if}
</section>

<style>
  .exp {
    display: grid;
    gap: 14px;
    margin: 28px 0;
    scroll-margin-top: 16px;
  }
  .top {
    display: grid;
    gap: 6px;
  }
  .kick {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
    margin: 0;
  }
  .tag,
  .nc {
    font-size: 11px;
    padding: 1px 8px;
    border-radius: var(--radius-pill);
    border: 1px solid var(--c-axis);
    color: var(--c-ink-2);
  }
  .nc {
    border-style: dashed;
  }
  h2 {
    margin: 0;
    font-size: var(--fs-section);
  }
  .lede {
    margin: 0;
    max-width: 72ch;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  .caveat {
    max-width: 72ch;
  }
  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
    gap: 10px;
  }
  .card {
    display: grid;
    gap: 4px;
    align-content: start;
    padding: 12px 14px;
    border: 1px solid var(--c-grid);
    border-radius: var(--radius-md);
    background: var(--c-surface);
  }
  .held {
    border: 1px dashed var(--c-ink-2);
    background:
      repeating-linear-gradient(135deg, var(--c-grid) 0 1px, transparent 1px 9px),
      var(--c-surface);
  }
  .ct {
    margin: 0;
    font-size: var(--fs-small);
    font-weight: 600;
  }
  .big {
    margin: 0;
    font-size: var(--fs-big);
    font-weight: 680;
    line-height: 1.1;
  }
  .sub {
    margin: 0;
    font-size: 12px;
    color: var(--c-ink-2);
  }
  .bar {
    position: relative;
    display: block;
    height: 10px;
    border: 1px solid var(--c-axis);
    border-radius: 5px;
    overflow: hidden;
    background: var(--c-page);
  }
  .bar .fill {
    display: block;
    height: 100%;
  }
  .bar .mid {
    position: absolute;
    left: 50%;
    top: 0;
    bottom: 0;
    border-left: 1px solid var(--c-ink-2);
  }
  .sub-h {
    margin: 6px 0 0;
    font-size: var(--fs-body);
  }
  .sur,
  .events {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .sur {
    display: grid;
    gap: 6px;
  }
  .row {
    display: grid;
    grid-template-columns: minmax(110px, 1fr) minmax(120px, 2fr) minmax(0, 3fr);
    gap: 4px 12px;
    align-items: center;
    padding: 6px 10px;
    border: 1px solid var(--c-grid);
    border-radius: var(--radius-md);
  }
  @media (max-width: 600px) {
    .row {
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    }
    .row .val {
      grid-column: 1 / -1;
    }
  }
  .who {
    display: grid;
    font-weight: 600;
    font-size: var(--fs-small);
  }
  .m {
    font-weight: 400;
    font-size: 12px;
    color: var(--c-ink-2);
  }
  .axis {
    position: relative;
    display: block;
    height: 12px;
    background: var(--c-mid);
    border-radius: 3px;
  }
  .axis .zero {
    position: absolute;
    left: 50%;
    top: -2px;
    bottom: -2px;
    border-left: 1px solid var(--c-ink-2);
  }
  .axis .seg {
    position: absolute;
    top: 2px;
    bottom: 2px;
    border-radius: 2px;
  }
  .held-box {
    display: block;
    height: 12px;
    border: 1px dashed var(--c-ink-2);
    border-radius: 3px;
  }
  .val {
    font-size: var(--fs-small);
  }
  .events {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 12px;
  }
  .events li {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .unit {
    display: grid;
    place-items: center;
    width: 28px;
    height: 28px;
    border-radius: var(--radius-sm);
    color: var(--c-page);
    font-size: 16px;
    font-weight: 700;
  }
  .unit.nodir {
    border: 1px solid var(--c-axis);
  }
  .unit.held {
    border: 1px dashed var(--c-ink-2);
    background: repeating-linear-gradient(135deg, var(--c-grid) 0 3px, transparent 3px 7px);
  }
  .el {
    display: grid;
    font-size: 12px;
    line-height: 1.2;
  }
  @media (forced-colors: active) {
    .unit,
    .fill {
      forced-color-adjust: none;
    }
  }
</style>
