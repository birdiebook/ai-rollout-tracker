<!-- Start page (W5): the headline. The sentence is the pipeline's (overview.headline.sentence), the chain sentence is
     generated from flow.json (model.ts); nothing is written by hand. Tally and changes are pictures of the same counts. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { Deferred, StatusBadge, Term, dateLabel, fmt, periodLabel, stateStyle } from '$lib/design';
  import type { StartData } from './model';

  let { start }: { start: StartData } = $props();
  const h = $derived(start.headline);
  const status = $derived(start.record.status === 'live' ? 'live' : 'recon');
  const tally = $derived([
    { s: 'accelererar', n: h.counts.accelererar, word: 'accelererar' },
    { s: 'stabil', n: h.counts.stabil, word: h.counts.stabil === 1 ? 'stabil' : 'stabila' },
    { s: 'bromsar in', n: h.counts['bromsar in'], word: 'bromsar in' },
    { s: 'för få serier', n: h.counts['för få serier'] + h.counts['inga registrerade kärnserier'], word: 'utan tillstånd' }
  ] as const);
</script>

<header class="hero">
  <p class="kicker">
    {#if status === 'recon'}
      <!-- R-W3: a reconstructed month must not read as a live one; the status is the kicker itself, not a grey tag -->
      <StatusBadge {status} prominent label="Rekonstruerat läge {periodLabel(start.record.month, true)}" />
      {#if start.record.first_live_date}<span class="first">skarpt från {dateLabel(start.record.first_live_date)}</span>{/if}
    {:else}
      <span>Läget {periodLabel(start.record.month, true)}</span>
      <StatusBadge {status} />
    {/if}
  </p>
  <h1 data-testid="headline">{h.sentence}</h1>
  {#if status === 'recon'}
    <p class="recon" data-testid="recon-note">
      Räknat i efterhand med dagens kod på data som var kända vid månadsslutet, inte sparat då. En rekonstruktion kan se
      säkrare ut än det som gick att se i realtid. <Term id="rekonstruerad">Mer om rekonstruerade månader</Term>
    </p>
  {/if}

  <Deferred>
  <ul class="tally" aria-label="Grenar per tillstånd">
    {#each tally as t (t.s)}
      {@const st = stateStyle(t.s)}
      <li data-state={st.key}>
        <span class="g" aria-hidden="true" style:color={st.color}>{st.glyph}</span>
        <span class="n num">{t.n}</span>
        <span class="w">{t.word}</span>
      </li>
    {/each}
  </ul>

  <p class="lede" data-testid="chain-sentence">{h.chainSentence}</p>

  {#if h.changes.length}
    <div class="changes">
      <span class="note">Sedan {h.prevMonth ? periodLabel(h.prevMonth, true) : 'förra månaden'}:</span>
      <ul aria-label="Grenar som bytt tillstånd">
        {#each h.changes as c (c.code)}
          {@const a = stateStyle(c.from)}
          {@const b = stateStyle(c.to)}
          <li>
            <a href={resolve('/gren/[id]', { id: c.code })}>
              <b>{c.code}</b> {c.name}
              <span class="move">
                <span aria-hidden="true" style:color={a.color}>{a.glyph}</span>
                {a.word} <span aria-hidden="true">→</span><span class="visually-hidden">till</span> <span aria-hidden="true" style:color={b.color}>{b.glyph}</span>
                {b.word}
              </span>
            </a>
          </li>
        {/each}
      </ul>
    </div>
  {:else}
    <p class="note changes">Ingen gren bytte tillstånd sedan {h.prevMonth ? periodLabel(h.prevMonth, true) : 'förra månaden'}.</p>
  {/if}

  {#if start.facts.n_series !== null}
    <p class="note facts">
      {fmt(start.facts.n_series)} serier i katalogen, {fmt(start.facts.n_published)} publicerade med värden och
      {fmt(start.facts.n_withheld)} som räknas men hålls inne av licensskäl{#if start.facts.fetched}. Data hämtad till och med {dateLabel(start.facts.fetched)}{/if}.
    </p>
  {/if}
  </Deferred>
</header>

<style>
  .hero {
    padding: 22px 0 4px;
  }
  .kicker {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 10px;
    align-items: center;
    margin: 0;
  }
  h1 {
    max-width: 28ch;
    margin: 10px 0 14px;
  }
  .first {
    color: var(--c-ink-2);
  }
  .recon {
    margin: -6px 0 14px;
    max-width: 70ch;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
    border-left: 2px dashed var(--c-ink-2);
    padding-left: 10px;
  }
  .tally {
    list-style: none;
    margin: 0 0 14px;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .tally li {
    display: inline-flex;
    align-items: baseline;
    gap: 6px;
    padding: 6px 12px 6px 10px;
    border: 1px solid var(--c-ring);
    background: var(--c-surface);
    border-radius: var(--radius-pill);
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  .tally .g {
    font-size: 15px;
    line-height: 1;
  }
  .tally .n {
    font-size: 20px;
    font-weight: 680;
    color: var(--c-ink);
    line-height: 1;
  }
  .lede {
    font-size: 17px;
    max-width: 70ch;
  }
  .changes {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 10px;
    margin: 12px 0 0;
  }
  .changes ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .changes a {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 2px 6px;
    font-size: var(--fs-small);
    text-decoration: none;
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-md);
    padding: 5px 10px;
    background: var(--c-surface);
    min-height: var(--hit);
  }
  .changes a:hover {
    border-color: var(--c-axis);
  }
  .move {
    color: var(--c-ink-2);
    white-space: nowrap;
  }
  .facts {
    margin: 12px 0 0;
    max-width: 80ch;
  }
  @media (forced-colors: active) {
    .tally .g,
    .move span {
      color: CanvasText !important;
    }
  }
</style>
