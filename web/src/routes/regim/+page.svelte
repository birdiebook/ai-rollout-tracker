<!-- /regim (owner: W10). C4: the regime probability per factor block (MSIH(2)) against the registered thresholds,
     structural breaks (BOCPD) as markers on the same timeline, what the one-time holdout showed, and the method.
     Live months only: the regime is never reconstructed, and before the first live snapshot the page says so.
     Neutral: a regime shift is a description, not an alarm. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { StatusBadge, dateLabel, fmt, periodLabel } from '$lib/design';
  import { HOLDOUT, HoldoutStrip, RULES, RegimeMeter, RegimeTimeline, headline, timelineMonths, type RegimeLane } from '$lib/regime';

  let { data } = $props();
  const lanes = $derived<RegimeLane[]>(
    data.lanes.length
      ? data.lanes
      : Object.entries(data.block_labels).map(([block, label]) => ({ block, label, history: [], latest: null }))
  );
  const months = $derived(timelineMonths(data.months, data.firstLive));
  const pct = (x: number) => `${fmt(x * 100, 0)} %`;
  const inARow = ['noll', 'en', 'två', 'tre'][RULES.inARow] ?? String(RULES.inARow);
</script>

<svelte:head><title>Regim och strukturbrott – AI-utrullningen</title></svelte:head>

<header class="hero">
  <p class="kicker">
    Regim och strukturbrott (C4)
    {#if data.isLive}<StatusBadge status="live" />{:else}<span class="pending">skarpt från {dateLabel(data.firstLive)}</span>{/if}
  </p>
  <h1>Har något fundamentalt ändrats?</h1>
  <p class="lede">{headline(data.available, data.lanes, data.firstLive)}</p>
  <p class="callout">
    Ett regimskifte beskriver att takten i ett block har bytt nivå. Det är ingen varning och ingen värdering.
    <em>Inbromsning</em> är regimen med lägre takt, och den kan fortfarande vara positiv. Regimen ingår inte i grenarnas
    tillstånd och ändrar inget index.
  </p>
</header>

<section aria-labelledby="now-h" class="panel">
  <h2 id="now-h">Läget per block</h2>
  <p class="note">
    P(inbromsning) ur en Markov-switching-modell med två tillstånd (MSIH(2)) på faktorn för varje block. Skifte rapporteras
    till inbromsning när sannolikheten är minst {fmt(RULES.shiftAtLeast, 1)} {inARow} månader i rad, och till expansion när den är högst
    {fmt(RULES.backAtMost, 1)} {inARow} månader i rad. Däremellan behålls tillståndet.
  </p>
  <div class="meters">
    {#each lanes as l (l.block)}<RegimeMeter lane={l} />{/each}
  </div>
  {#if !data.available}
    <p class="empty">
      Ingen skarp månad än. Regimen följs live från den första ögonblicksbilden efter holdouten,
      {dateLabel(data.firstLive)}, och rekonstrueras aldrig bakåt. Fram till dess finns bara holdoutens resultat nedan.
    </p>
  {/if}
</section>

<section class="panel" aria-label="Tidslinje">
  <RegimeTimeline
    {months}
    liveMonths={data.months}
    {lanes}
    breaks={data.breaks}
    nWithheld={data.n_breaks_withheld}
    firstLive={data.firstLive}
    status={data.isLive ? 'live' : undefined}
  />
  {#if data.breaks.length}
    <p class="links">
      Brott i:
      {#each data.breaks as b, i (b.month + b.series)}{#if i}{', '}{/if}{#if b.linkable}<a href={resolve('/serie/[key]', { key: b.series })}>{b.label}</a>{:else}{b.label}{/if}
        ({b.branch ?? ''}, {b.latest_period ?? ''}, P {fmt(b.p_recent, 2)}){/each}.
    </p>
  {/if}
</section>

<section aria-labelledby="ho-h">
  <h2 id="ho-h">Vad holdouten visade</h2>
  <p class="kicker"><span class="pending">holdout, beskrivande, inte skarp</span> öppnad en gång {dateLabel(HOLDOUT.opened)} · specifikation {HOLDOUT.spec} ({HOLDOUT.spec_commit})</p>
  <p class="lede">
    C4 prövades en gång på {HOLDOUT.n_days} månadsslut, {periodLabel(HOLDOUT.first)}–{periodLabel(HOLDOUT.last)}, beräknade i
    realtid med samma kod som nu körs skarpt. C4 är beskrivande: den befordras inte och styr ingen prognos.
  </p>
  <div class="panel">
    <HoldoutStrip links={data.holdoutLinks} />
  </div>

  <div class="facts">
    <div class="panel">
      <h3>Skiften och omklassning</h3>
      <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
      <div class="tw" tabindex="0" role="region" aria-label="Holdouten per block, tabell">
      <table class="nums">
        <caption class="visually-hidden">Holdouten per block</caption>
        <thead>
          <tr><th scope="col">Block</th><th scope="col">Skiften till inbromsning</th><th scope="col">Skiften till expansion</th><th scope="col">Månader i inbromsning</th><th scope="col">Omklassat i efterhand</th></tr>
        </thead>
        <tbody>
          {#each HOLDOUT.blocks as b (b.block)}
            <tr>
              <th scope="row">{b.label}</th>
              <td>{b.shifts_to_slow}</td>
              <td>{b.shifts_back}</td>
              <td>{b.slow_months.length} av {HOLDOUT.n_days}</td>
              <td>{pct(b.reclassified)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
      </div>
      {#each HOLDOUT.blocks as b (b.block)}<p class="note"><strong>{b.label}:</strong> {b.note}</p>{/each}
    </div>
    <div class="panel">
      <h3>Strukturbrott</h3>
      <p class="stat"><span class="num">{HOLDOUT.bocpd.breaks.length}</span> brott på {fmt(HOLDOUT.bocpd.series_days)} serie-dagar ({HOLDOUT.bocpd.n_series} serier)</p>
      <p class="note">
        {fmt(HOLDOUT.bocpd.per_100, 2)} per 100 serie-dagar, mot {fmt(HOLDOUT.bocpd.per_100_dev, 2)} i utvecklingsperioden. Takten är
        autokorrelerad, så metoden ger fler brott än nominellt. Det är en känd svaghet som redovisas, inte rättas.
      </p>
      <h3>Samband med prognosfel</h3>
      <table>
        <caption class="visually-hidden">Spearmans rho mellan P(inbromsning) och huvudmodellernas absoluta fel</caption>
        <thead><tr><th scope="col">Mål</th><th scope="col">Block</th><th scope="col">n</th><th scope="col">ρ</th></tr></thead>
        <tbody>
          {#each HOLDOUT.rho as x (x.target + x.block)}
            <tr><td>{x.target}</td><td>{x.block}</td><td>{x.n}</td><td>{fmt(x.rho, 2)}</td></tr>
          {/each}
        </tbody>
      </table>
      <p class="note">Bara information, inget test. Inget samband syns: med n = 6 ligger ±0,9 inom slumpens ram.</p>
    </div>
  </div>
  <ul class="caveats note">
    <li><strong>Delvis känd holdout.</strong> Baslinjefelen för perioden var publicerade före öppningen, och bakåtfyllda serier har dagens version. Testet är inte helt blint.</li>
    <li><strong>Omskattade banor.</strong> Faktorn och modellen skattas om varje månad. Det förklarar efterfrågeblockets språng mellan oktober och november 2025, och att fyra månader klassas om i efterhand.</li>
    <li><strong>Få regimer att lära av.</strong> Med 10–13 års månadsdata och persistenta regimer blir skiftena få.</li>
  </ul>
  <p class="note">Underlag: <code>{HOLDOUT.doc}</code>, körlogg <code>{HOLDOUT.run_log}</code>.</p>
</section>

<section aria-labelledby="m-h" class="panel">
  <h2 id="m-h">Metoden i korthet</h2>
  <dl class="method">
    <div><dt>Regim</dt><dd>MSIH(2): två tillstånd med eget medel och egen varians på den månatliga faktorn för "capex och leverantörsled" och för "efterfrågan" (faktormodellen C3). Skattas om varje månad med expanderande fönster. Tillståndet med lägre medel kallas inbromsning.</dd></div>
    <div><dt>Skifte</dt><dd>P(inbromsning) ≥ {fmt(RULES.shiftAtLeast, 1)} {inARow} månader i rad ger inbromsning, ≤ {fmt(RULES.backAtMost, 1)} {inARow} månader i rad ger expansion. En månad utan värde bryter följden.</dd></div>
    <div><dt>Strukturbrott</dt><dd>Bayesiansk online-changepoint (BOCPD) per räknad kärnserie på takten, hazard {RULES.hazard.M} per månad ({RULES.hazard.Q} per kvartal, {RULES.hazard.A} per år). Brott när P(körlängd ≤ {RULES.runLength}) ≥ {fmt(RULES.breakAtLeast, 1)}. Brott i inhållna serier räknas men visas utan namn.</dd></div>
    <div><dt>Registrerat</dt><dd>Måttregistret, G-D (trösklarna kommer därifrån; regime.json bär dem inte). Specifikation {data.spec_version ?? HOLDOUT.spec}. Skarpt från {dateLabel(data.firstLive)}.</dd></div>
  </dl>
  <p class="note">Mer om registret och tillstånden på <a href={resolve('/metod')}>metodsidan</a>. Avstämningarna mellan leden ingår inte i regimmodellen: <a href={resolve('/avstamningar')}>avstämningar</a>.</p>
</section>

<style>
  .hero {
    margin: 22px 0 18px;
    display: grid;
    gap: 8px;
  }
  .kicker {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 10px;
    align-items: center;
    margin: 0;
  }
  h1 {
    margin: 0;
  }
  .pending {
    font-size: 12px;
    color: var(--c-ink-2);
    border: 1px dashed var(--c-axis);
    border-radius: 999px;
    padding: 2px 9px;
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
  h2 {
    margin: 0 0 6px;
  }
  .meters {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 22px 32px;
    margin-top: 14px;
  }
  @media (min-width: 760px) {
    .meters {
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    }
  }
  .empty {
    margin: 16px 0 0;
    padding: 10px 12px;
    border: 1px dashed var(--c-axis);
    border-radius: var(--radius-md);
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  .links {
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  #ho-h + .kicker {
    margin-bottom: 8px;
  }
  .facts {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 14px;
    margin-top: 14px;
  }
  @media (min-width: 900px) {
    .facts {
      grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
    }
  }
  .facts h3 {
    margin: 0 0 8px;
  }
  .facts h3 + table,
  .facts .stat + .note {
    margin-bottom: 14px;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    font-size: 13px;
  }
  th,
  td {
    text-align: right;
    padding: 4px 6px;
    border-bottom: 1px solid var(--c-grid);
  }
  th:first-child,
  td:first-child,
  table:not(.nums) td:nth-child(2),
  table:not(.nums) th:nth-child(2) {
    text-align: left;
  }
  .tw {
    overflow-x: auto;
    max-width: 100%;
  }
  code {
    overflow-wrap: anywhere;
  }
  thead th {
    font-weight: 600;
    color: var(--c-ink-2);
    font-size: 12px;
  }
  .stat {
    margin: 0;
    font-size: var(--fs-small);
  }
  .stat .num {
    font-size: 28px;
    font-weight: 650;
    margin-right: 6px;
  }
  .caveats {
    margin: 14px 0 6px;
    padding-left: 18px;
    display: grid;
    gap: 4px;
    max-width: 80ch;
  }
  .method {
    display: grid;
    gap: 10px;
    margin: 8px 0;
  }
  .method div {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 2px 16px;
  }
  @media (min-width: 760px) {
    .method div {
      grid-template-columns: 140px minmax(0, 1fr);
    }
  }
  .method dt {
    font-weight: 620;
  }
  .method dd {
    margin: 0;
    color: var(--c-ink-2);
    max-width: 75ch;
  }
</style>
