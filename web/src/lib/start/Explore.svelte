<!-- Ways on from the start page (P6: every element links to the next layer). The branch chips repeat the state
     vocabulary (colour + glyph + word) so the next click is chosen from the picture. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { fmt, stateStyle } from '$lib/design';
  import type { StartData } from './model';

  let { start }: { start: StartData } = $props();
  const nNowcasts = $derived(start.calendar.filter((c) => c.id !== 'd2').length);
</script>

<section aria-labelledby="explore-h">
  <h2 id="explore-h">Gå vidare</h2>
  <ul class="branches" aria-label="Grenarna">
    {#each start.branches as b (b.code)}
      {@const st = stateStyle(b.state)}
      <li>
        <a href={resolve('/gren/[id]', { id: b.code })} data-state={st.key}>
          <span class="g" aria-hidden="true" style:color={st.color}>{st.glyph}</span>
          <span><b>{b.code}</b> {b.name}<span class="visually-hidden">, {b.state}</span></span>
          <span class="q">{b.question}</span>
        </a>
      </li>
    {/each}
  </ul>
  <ul class="ways">
    <li>
      <a href={resolve('/flode')}>
        <b>Flödet L1–L9 →</b>
        <span>Led för led: grenarnas tillstånd, nyckelserier och avstämningarna mellan leden.</span>
      </a>
    </li>
    <li>
      <a href={resolve('/prognoser')}>
        <b>Prognoserna →</b>
        <span>{nNowcasts} nowcasts med intervall, kalender och facit mot utfallen.</span>
      </a>
    </li>
    <li>
      <a href={resolve('/metod')}>
        <b>Metoden →</b>
        <span>
          Förregistrerade regler, källor och licenser{#if start.facts.n_withheld !== null}, och de {fmt(start.facts.n_withheld)} serier som räknas
            men hålls inne{/if}.
        </span>
      </a>
    </li>
  </ul>
</section>

<style>
  .branches,
  .ways {
    list-style: none;
    margin: 10px 0 0;
    padding: 0;
    display: grid;
    gap: 8px;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 240px), 1fr));
  }
  .ways {
    margin-top: 14px;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr));
  }
  a {
    display: grid;
    gap: 2px;
    height: 100%;
    text-decoration: none;
    background: var(--c-surface);
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-md);
    padding: 10px 12px;
    font-size: 14px;
  }
  .branches a {
    grid-template-columns: 18px minmax(0, 1fr);
    column-gap: 6px;
  }
  .branches .q {
    grid-column: 2;
    font-size: 12px;
    color: var(--c-muted);
  }
  .g {
    font-size: 14px;
  }
  @media (max-width: 560px) {
    .branches {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .branches .q {
      display: none;
    }
    .branches a {
      font-size: 13px;
      padding: 8px 10px;
    }
  }
  a:hover {
    border-color: var(--c-axis);
  }
  .ways span {
    color: var(--c-ink-2);
    font-size: var(--fs-small);
  }
  @media (forced-colors: active) {
    .g {
      color: CanvasText !important;
    }
  }
</style>
