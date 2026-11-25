<!-- W14: the quarterly report as a visual essay (docs/steg3/hemsida_vision.md 3.4). Six sections in the report's own
     order: the state at the quarter's end, the chain L1–L9 over the quarter, the flows and reconciliations, the live
     nowcasts against their outcomes, the regime, and data and method. Every section opens with a living figure from
     the existing components (lib/story, lib/flow, lib/regime, lib/series, routes/prognoser/parts), and every figure
     and sentence is as it was known on the report day (model.ts cuts them through $lib/timetravel/gate). The text
     comes from the bundle (site_bundle.report, generated from ai_tracker.quarterly's facts). Without JavaScript it is
     one long page; with JavaScript the section in view is marked in the rail and the links into the time-travel
     views open at the report day. prefers-reduced-motion: no smooth scrolling. -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { DIRECTIONS, DataTable, Glyph, StatusBadge, dateLabel, fmt, periodLabel, signed, stateStyle, type RecordStatus } from '$lib/design';
  import { IndexHistory, IndexSpark, Minimap, SpanChart, WithheldBoxes, withheldView } from '$lib/flow';
  import { RatioChart, RegimeMeter } from '$lib/regime';
  import LevelChart from '$lib/series/LevelChart.svelte';
  import StoryStripes from '$lib/story/StoryStripes.svelte';
  import ForecastDots from '../../routes/prognoser/parts/ForecastDots.svelte';
  import { at, branchHref, nowcastHref, quarterHref, seriesHref, startHref } from './links';
  import type { ReportNowcast } from '$lib/data';
  import { cap, type QuarterNav, type ReportPage } from './model';

  let { page, quarters = page.quarters }: { page: ReportPage; quarters?: QuarterNav[] } = $props();
  const r = $derived(page.report);
  const status = $derived<RecordStatus>(r.status === 'live' ? 'live' : 'recon');
  const i = $derived(quarters.findIndex((q) => q.quarter === r.quarter));
  const prev = $derived(i > 0 ? quarters[i - 1] : null);
  const next = $derived(i >= 0 && i < quarters.length - 1 ? quarters[i + 1] : null);
  const qMonths = $derived(r.months.map((m) => m.month_sv).join(', '));
  const sections = [
    { id: 'lage', n: 1, title: 'Läget vid kvartalets slut' },
    { id: 'kedjan', n: 2, title: 'Kedjan L1–L9' },
    { id: 'floden', n: 3, title: 'Flöden och avstämningar' },
    { id: 'prognoser', n: 4, title: 'Prognoser mot utfall' },
    { id: 'regim', n: 5, title: 'Regimen' },
    { id: 'data', n: 6, title: 'Data och metod' }
  ];
  const withNowcastFiles = $derived(page.nowcasts.filter((n) => n.n.n_files > 0).length);
  const fmtN = (dec: number) => (v: number | null | undefined) => fmt(v ?? null, dec);
  const stateWord = (s: string | null) => stateStyle(s).word;
  const cellTitle = (m: string, idx: number | null, st: string | null) => `${periodLabel(m)}: ${fmt(idx, 2)}, ${stateWord(st)}`;

  const branchTable = $derived({
    caption: `Diffusionsindex och tillstånd per gren${r.base ? `, ${r.base.month_sv} och` : ''} kvartalets tre månader`,
    columns: [
      { key: 'b', label: 'Gren', align: 'left' as const },
      ...(r.branches[0]?.path ?? []).map((c) => ({ key: c.month, label: periodLabel(c.month), align: 'left' as const })),
      { key: 'd', label: 'Över kvartalet', align: 'left' as const },
      { key: 'f', label: 'Serier som bytt riktning' }
    ],
    rows: r.branches.map((b) => ({
      b: `${b.code} ${b.name}`,
      ...Object.fromEntries(b.path.map((c) => [c.month, `${fmt(c.index, 2)} ${stateWord(c.state)}`])),
      d: `${signed(b.delta_index, 2)}${b.state_changed ? `; ${b.from} → ${b.to}` : ''}`,
      f: b.flips === null ? '–' : fmt(b.flips, 0)
    }))
  });
  const regimeTable = $derived({
    caption: 'P(inbromsning) och rapporterat tillstånd per månad, som de lagrades i ögonblicksbilderna',
    columns: [{ key: 'b', label: 'Block', align: 'left' as const }, ...r.regime.months.map((m) => ({ key: m, label: periodLabel(m), align: 'left' as const }))],
    rows: (r.regime.blocks ?? []).map((b) => ({
      b: b.label,
      ...Object.fromEntries(b.cells.map((c) => [c.month, c.present ? `${fmt(c.p_slow ?? null, 2)}; ${c.state ?? '–'}` : 'inget avsnitt']))
    }))
  });
  const metricsTable = (n: ReportNowcast) => ({
    caption: `Rullande utvärdering, ${n.n_scored} utfall (${n.error_unit})`,
    columns: [
      { key: 'v', label: 'Variant', align: 'left' as const },
      { key: 'n', label: 'n' },
      { key: 'mae', label: 'MAE' },
      { key: 'bias', label: 'Bias' },
      { key: 'd', label: 'MAE − baslinjen' },
      { key: 'c', label: 'Täckning 80 %' }
    ],
    rows: n.metrics.map((m) => ({
      v: (m.variant === 'champion' ? 'huvudmodell' : m.variant) + (m.role === 'baseline' ? ' (naiv baslinje)' : m.role === 'guidance' ? ' (bolagens guidance)' : ''),
      n: fmt(m.n, 0),
      mae: fmt(m.mae, 2),
      bias: signed(m.bias, 2),
      d: m.delta_mae === null ? '–' : signed(m.delta_mae, 2),
      c: m.coverage['80'] ? `${fmt(m.coverage['80'].rate, 2)} [${fmt(m.coverage['80'].lo, 2)}–${fmt(m.coverage['80'].hi, 2)}]` : '–'
    }))
  });

  let enhanced = $state(false);
  let active = $state('lage');
  let host: HTMLElement | undefined = $state();
  const day = $derived(enhanced ? page.day : null);

  onMount(() => {
    enhanced = true;
    if (typeof IntersectionObserver === 'undefined') return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) if (e.isIntersecting) active = (e.target as HTMLElement).dataset.sec ?? active;
      },
      { rootMargin: '-40% 0px -55% 0px' }
    );
    host?.querySelectorAll<HTMLElement>('[data-sec]').forEach((el) => io.observe(el));
    return () => io.disconnect();
  });
</script>

<article class="report" data-quarter={r.quarter} data-status={r.status} data-known={r.known} bind:this={host}>
  <header class="head">
    <p class="kicker">Kvartalsrapporten <StatusBadge {status} /></p>
    <h1>{cap(r.quarter_sv)}</h1>
    <p class="lede">{r.headline}</p>
    {#if r.recon_note}
      <p class="recon" data-recon>
        <strong>Rekonstruerad.</strong>
        {r.recon_note.replace(/^Rekonstruerad, inte en skarp rapport\. /, '')}
        {#if page.firstLive}Den första skarpa kvartalsrapporten gäller {periodLabel(page.firstLive, true)}.{/if}
      </p>
    {/if}
    <p class="note">
      Kvartalet {dateLabel(r.start)}–{dateLabel(r.end)}: månadslägena för {qMonths}{r.base ? `, jämfört med ${r.base.month_sv}` : ''}.
      Allt på sidan är som det var känt {dateLabel(r.known)}. Texten är genererad ur datan och beskriver, den drar inga
      orsaksslutsatser.
    </p>
    <nav class="qnav" aria-label="Föregående och nästa kvartal">
      {#if prev}<a href={quarterHref(prev.quarter)} rel="prev"><span aria-hidden="true">←</span> {prev.quarter_sv}</a>{:else}<span></span>{/if}
      {#if next}<a href={quarterHref(next.quarter)} rel="next">{next.quarter_sv} <span aria-hidden="true">→</span></a>{/if}
    </nav>
  </header>

  <div class="essay" class:enhanced>
    <nav class="rail" aria-label="Rapportens avsnitt">
      <ol>
        {#each sections as s (s.id)}
          <li><a href={`#${s.id}`} aria-current={enhanced && active === s.id ? 'step' : undefined}><span class="no">{s.n}</span>{s.title}</a></li>
        {/each}
      </ol>
    </nav>

    <div class="body">
      <!-- 1. the state at the quarter's end -->
      <section class="sec" id="lage" data-sec="lage" aria-labelledby="h-lage">
        <p class="kicker secno">1 av 6</p>
        <h2 id="h-lage">Läget vid kvartalets slut</h2>
        <div class="split">
          <div class="txt">
            <ul class="facts">
              {#each r.summary.sentences as s, k (k)}<li>{s}</li>{/each}
              <li>{r.nowcast_news.text}</li>
            </ul>
            <ul class="counts" aria-label="Grenar per tillstånd vid kvartalets slut">
              {#each r.summary.groups as g (g.state)}
                <li><Glyph state={g.state} /> <span class="codes">{g.codes.join(', ')}</span></li>
              {/each}
            </ul>
            <p class="go"><a href={at(startHref(), day)} data-tt-own={day ? '' : undefined}>Öppna läget{day ? ` som det var känt ${dateLabel(day)}` : ''} <span aria-hidden="true">→</span></a></p>
          </div>
          <div class="fig">
            <div class="figure"><StoryStripes id="rp-stripes" stripes={page.stripes} highlight={page.highlight} {status} /></div>
          </div>
        </div>
      </section>

      <!-- 2. the chain over the quarter -->
      <section class="sec" id="kedjan" data-sec="kedjan" aria-labelledby="h-kedjan">
        <p class="kicker secno">2 av 6</p>
        <h2 id="h-kedjan">Kedjan L1–L9 över kvartalet</h2>
        <p class="intro">
          Flödet från förmåga och användning till el och forskning. Varje led visar sina grenars tillstånd vid kvartalets slut och
          diffusionsindex vid varje månadsslut{r.base ? `, från ${r.base.month_sv}` : ''} till {r.months[2].month_sv}.
        </p>
        <div class="figure mini"><Minimap leads={page.mini} /></div>
        <ol class="leads">
          {#each page.leads as l (l.lead)}
            <li class="lead" data-lead={l.lead}>
              <h3><span class="lcode">{l.lead}</span> {l.name}</h3>
              {#if l.branches.length}
                <ul class="brs">
                  {#each l.branches as b (b.code)}
                    <li>
                      <a class="bname" href={at(branchHref(b.code), day)} data-tt-own={day ? '' : undefined}>{b.code} {b.name}</a>
                      <span class="bst"><Glyph state={b.state} /></span>
                      <span class="bidx num" title={b.months.map((m, k) => cellTitle(m, b.spark[k], null)).join('; ')}>
                        {fmt(b.index, 2)}{#if b.delta !== null && Math.abs(b.delta) >= 0.005}<small>{signed(b.delta, 2)}</small>{/if}
                      </span>
                      <span class="bspark" aria-hidden="true"><IndexSpark values={b.spark} lo={page.stripes.thresholds.braking_at_most} hi={page.stripes.thresholds.accelerating_at_least} /></span>
                    </li>
                  {/each}
                </ul>
              {/if}
              <p class="ltxt">{l.text}</p>
            </li>
          {/each}
        </ol>
        {#if page.movers.length}
          <h3 class="sub">Grenarna som rörde sig mest</h3>
          <p class="note">Störst indexförändring över kvartalet och grenarna som bytte tillstånd, i rapportens ordning, med 24 månaders historik som den var känd.</p>
          <div class="movers">
            {#each page.movers as m (m.code)}
              <div class="figure" data-mover={m.code}>
                <IndexHistory id={`rp-idx-${m.code}`} title={`${m.code} ${m.name}: ${signed(m.delta, 2)} över kvartalet${m.from && m.to && m.from !== m.to ? `, ${m.from} → ${m.to}` : ''}`} history={m.history} {status} height={190} headingLevel={4} showLegend={false} />
              </div>
            {/each}
          </div>
        {/if}
        <details class="tbl">
          <summary>Tabell: index och tillstånd vid varje månadsslut</summary>
          <DataTable id="rp-branch-table" table={branchTable} />
        </details>
      </section>

      <!-- 3. flows and reconciliations -->
      <section class="sec" id="floden" data-sec="floden" aria-labelledby="h-floden">
        <p class="kicker secno">3 av 6</p>
        <h2 id="h-floden">Flöden och avstämningar</h2>
        <p class="intro">
          Kvoterna mellan leden (avstämningar, A5 i måttregistret), som posten hade dem vid kvartalets slut. Takten är årsförändringen i
          log(kvot) ×100 och räknas inte i något diffusionsindex. Riktningen är kvotens förändring i takt.
        </p>
        {#if page.ratios.length}
          <div class="figure"><SpanChart spans={page.spans} /></div>
          <div class="ratios">
            {#each page.ratios as x (x.ratio.key)}
              <div class="ratio" data-ratio={x.ratio.key}>
                <h3>
                  {#if x.ratio.direction !== null}<span class="g" aria-hidden="true" style:color={DIRECTIONS[x.ratio.direction].color}>{DIRECTIONS[x.ratio.direction].glyph}</span>{/if}
                  {x.short}
                </h3>
                <p class="rtxt">{x.ratio.text}</p>
                {#if x.recon}
                  <div class="figure"><RatioChart r={x.recon} mode="ratio" height={190} /></div>
                {:else}
                  <p class="note">Kvoten har inget publicerat seriedokument.</p>
                {/if}
                <p class="go"><a href={at(seriesHref(x.ratio.key), day)} data-tt-own={day ? '' : undefined}>Till kvoten <span aria-hidden="true">→</span></a></p>
              </div>
            {/each}
          </div>
        {:else}
          <p class="note">Inga avstämningar med data vid kvartalets slut.</p>
        {/if}
        {#if r.n_ratios_withheld}<p class="note">{r.n_ratios_withheld} {r.n_ratios_withheld === 1 ? 'avstämning visas' : 'avstämningar visas'} inte av licensskäl.</p>{/if}
      </section>

      <!-- 4. nowcasts against outcomes -->
      <section class="sec" id="prognoser" data-sec="prognoser" aria-labelledby="h-prognoser">
        <p class="kicker secno">4 av 6</p>
        <h2 id="h-prognoser">Prognoser mot utfall</h2>
        <p class="intro">
          Skarpa prognoser med prognosdag till och med {dateLabel(r.end)}, mot första publicerade utfall kända samma dag. {r.nowcast_news.text}
          {#if !withNowcastFiles}Inget av målen hade någon skarp prognos då, så figurerna visar målens nivåer som de var kända.{/if}
        </p>
        <div class="ncs">
          {#each page.nowcasts as x (x.n.id)}
            <div class="nc" data-nowcast={x.n.id}>
              <h3><span class="lcode">{x.n.label}</span> {x.n.title}</h3>
              <p class="rtxt">{x.n.text}</p>
              {#each x.rows as row (row.period)}
                <div class="figure">
                  <ForecastDots id={`rp-dots-${x.n.id}-${row.period}`} {row} unit={x.n.unit ?? ''} format={fmtN(x.n.decimals)} title={`${periodLabel(row.period, true)}: prognosen som 20 lika sannolika utfall, och utfallet`} />
                </div>
              {/each}
              {#if x.n.metrics.length}
                <div class="metrics"><DataTable id={`rp-metrics-${x.n.id}`} table={metricsTable(x.n)} /></div>
              {/if}
              {#if x.level && x.level.points.length}
                <p class="kicker flabel">Målet {x.level.label.replace(/^\[syntetisk\]\s*/, '')}, som det var känt</p>
                <div class="figure"><LevelChart id={`rp-lvl-${x.n.id}`} label={x.level.label} unit={x.level.unit} points={x.level.points} totalCount={x.level.total} {status} source={x.level.source} license={x.level.license} /></div>
              {:else if x.noLevel === 'withheld'}
                <p class="note">Målet visas inte av licensskäl.</p>
              {:else if x.noLevel === 'derived'}
                <p class="note">Målet har inget eget seriedokument (det är en summa av andra serier); nivån finns på prognossidan.</p>
              {:else}
                <p class="note">Målet hade inget publicerat värde {dateLabel(page.day)}.</p>
              {/if}
              <p class="go"><a href={nowcastHref(x.n.id)}>Till {x.n.label} <span aria-hidden="true">→</span></a></p>
            </div>
          {/each}
        </div>
      </section>

      <!-- 5. the regime -->
      <section class="sec" id="regim" data-sec="regim" aria-labelledby="h-regim">
        <p class="kicker secno">5 av 6</p>
        <h2 id="h-regim">Regimen</h2>
        <p class="intro">{r.regime.text}</p>
        <div class="lanes" role="group" aria-label="P(inbromsning) per block vid kvartalets slut">
          {#each page.lanes as lane (lane.block)}<div class="figure"><RegimeMeter {lane} /></div>{/each}
        </div>
        {#if r.regime.blocks}
          <DataTable id="rp-regime-table" table={regimeTable} />
        {/if}
        {#if r.regime.breaks?.length}
          <h3 class="sub">Strukturbrott i kvartalet</h3>
          <ul class="facts">
            {#each r.regime.breaks as b (b.month + b.series)}
              <li>{periodLabel(b.month, true)}: <a href={at(seriesHref(b.series), day)} data-tt-own={day ? '' : undefined}>{b.label}</a> ({b.branch ?? '–'}), senaste period {b.latest_period ?? '–'}, P(körlängd ≤ 2) {fmt(b.p_recent, 2)}.</li>
            {/each}
          </ul>
        {/if}
      </section>

      <!-- 6. data and method -->
      <section class="sec" id="data" data-sec="data" aria-labelledby="h-data">
        <p class="kicker secno">6 av 6</p>
        <h2 id="h-data">Data och metod</h2>
        <ul class="facts">
          {#each r.data.sentences as s, k (k)}<li>{s}</li>{/each}
        </ul>
        {#if r.data.revised.length}
          <p class="note">
            Flest reviderade värden:
            {#each r.data.revised as x, k (x.key)}<a href={seriesHref(x.key)}>{x.label}</a> ({x.n}){k < r.data.revised.length - 1 ? ', ' : '.'}{/each}
          </p>
        {/if}
        {#if r.data.reviews.length || r.data.register.length}
          <div class="two">
            {#if r.data.reviews.length}
              <div><h3 class="sub">Granskningar i kvartalet</h3><ul class="facts">{#each r.data.reviews as x (x.file)}<li>{dateLabel(x.date)}: {x.title}</li>{/each}</ul></div>
            {/if}
            {#if r.data.register.length}
              <div><h3 class="sub">Ändringar i måttregistret</h3><ul class="facts">{#each r.data.register as x (x.date + x.title)}<li>{dateLabel(x.date)}: {x.title}</li>{/each}</ul></div>
            {/if}
          </div>
        {/if}
        {#if r.withheld.length}
          <h3 class="sub">Visas inte av licensskäl</h3>
          <p class="note">Serierna räknas i sina grenars index men namnges bara här, utan värden.</p>
          <WithheldBoxes items={r.withheld.map((w) => withheldView({ ...w, branch: w.branch ?? undefined }))} />
        {/if}
      </section>
    </div>
  </div>

  <section class="about panel" id="om-rapporten" aria-labelledby="om-h">
    <h2 id="om-h">Om rapporten</h2>
    <p>
      Rapporten sammanfattar kvartalets tre månadslägen. Den räknar inte om något som månadslägena redan har lagrat och lägger inte till
      några mått. Tillstånd, index, kvoternas mått, prognosfel och regimvärden är posten och de skarpa filerna som de var kända
      {dateLabel(r.known)}. Grenar med tre till fem serier flyttas mycket av en enda serie, och med få utfall kan skillnader mellan
      prognosvarianter vara slump. Orden accelererar, stabil och bromsar in beskriver takten och är inga omdömen.
    </p>
    <details class="all">
      <summary>Alla kvartal ({quarters.length})</summary>
      <ol class="qlist">
        {#each [...quarters].reverse() as q (q.quarter)}
          <li>
            <a href={quarterHref(q.quarter)} aria-current={q.quarter === r.quarter ? 'page' : undefined}>{q.quarter_sv}</a>
            <span class="note">{q.kind === 'rekonstruerad' ? 'rekonstruerad' : 'skarp'}</span>
          </li>
        {/each}
      </ol>
    </details>
  </section>
</article>

<style>
  .head {
    margin: 20px 0 22px;
  }
  .head .kicker {
    display: flex;
    gap: 10px;
    align-items: center;
    margin: 0;
  }
  .head .note,
  .recon {
    max-width: 78ch;
    margin: 10px 0 0;
  }
  .recon {
    border: 1.5px dashed var(--c-axis);
    border-radius: var(--radius-lg);
    padding: 10px 14px;
    color: var(--c-ink-2);
  }
  .qnav {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    margin-top: 14px;
    font-size: var(--fs-small);
  }
  .qnav a,
  .rail a,
  .go a,
  .qlist a,
  .bname {
    display: inline-flex;
    align-items: center;
    min-height: var(--hit, 44px);
  }
  .rail {
    display: none;
  }
  .rail ol,
  .leads,
  .brs,
  .qlist,
  .counts {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .sec {
    border-top: 1px solid var(--c-grid);
    padding: 18px 0 26px;
    scroll-margin-top: 12px;
  }
  .sec h2 {
    margin: 4px 0 10px;
  }
  .secno {
    margin: 0;
  }
  .intro,
  .facts,
  .rtxt,
  .ltxt {
    max-width: 72ch;
  }
  .facts {
    padding-left: 18px;
    margin: 0 0 10px;
  }
  .facts li + li {
    margin-top: 4px;
  }
  .counts {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 16px;
    margin: 6px 0 4px;
    font-size: var(--fs-small);
  }
  .codes {
    color: var(--c-ink-2);
  }
  .split {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .split .fig {
    order: -1; /* mobile: the picture first (vision 3.4) */
    min-width: 0;
  }
  .figure {
    background: var(--c-surface);
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-lg);
    padding: 14px;
    min-width: 0;
  }
  .figure.mini {
    padding: 10px;
    margin: 6px 0 14px;
  }
  .leads {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 260px), 1fr));
    gap: 12px;
  }
  .lead {
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-lg);
    padding: 10px 12px;
    background: var(--c-surface);
    min-width: 0;
  }
  .lead h3 {
    margin: 0 0 4px;
    font-size: var(--fs-subsection);
  }
  .lcode {
    font-variant-numeric: tabular-nums;
    color: var(--c-ink-2);
    margin-right: 4px;
  }
  .brs li {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-areas: 'name idx' 'st spark';
    gap: 0 10px;
    align-items: center;
    padding: 2px 0;
    border-bottom: 1px dotted var(--c-grid);
  }
  .bname {
    grid-area: name;
    min-height: 32px;
  }
  .bst {
    grid-area: st;
    font-size: var(--fs-small);
  }
  .bidx {
    grid-area: idx;
    text-align: right;
  }
  .bidx small {
    margin-left: 6px;
    color: var(--c-ink-2);
  }
  .bspark {
    grid-area: spark;
    justify-self: end;
  }
  .ltxt {
    margin: 8px 0 0;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  .sub {
    margin: 22px 0 6px;
  }
  .movers,
  .ratios,
  .ncs,
  .lanes,
  .two {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 340px), 1fr));
    gap: 14px;
    margin-top: 10px;
  }
  .ratio h3,
  .nc h3 {
    margin: 0 0 6px;
    font-size: var(--fs-subsection);
  }
  .ratio,
  .nc {
    min-width: 0;
  }
  .ratio .g {
    margin-right: 4px;
  }
  .rtxt {
    margin: 0 0 10px;
  }
  .flabel {
    margin: 10px 0 6px;
  }
  .nc .figure + .figure {
    margin-top: 10px;
  }
  .go {
    margin: 6px 0 0;
  }
  .tbl {
    margin-top: 18px;
  }
  .metrics {
    margin: 4px 0 10px;
  }
  .about {
    margin: 30px 0 10px;
  }
  .about p {
    max-width: 78ch;
  }
  .qlist {
    columns: 2 220px;
    margin-top: 8px;
  }
  .qlist li {
    break-inside: avoid;
    display: flex;
    gap: 8px;
    align-items: center;
  }
  .qlist a[aria-current='page'] {
    font-weight: 650;
  }
  @media (min-width: 900px) {
    .essay {
      display: grid;
      grid-template-columns: 180px minmax(0, 1fr);
      gap: 24px;
      align-items: start;
    }
    .rail {
      display: block;
      position: sticky;
      top: 16px;
      font-size: var(--fs-small);
    }
    .rail a {
      gap: 8px;
      color: var(--c-ink-2);
      text-decoration: none;
      min-height: 32px;
      padding: 0 8px;
      border-left: 2px solid transparent;
    }
    .rail a:hover {
      color: var(--c-ink);
    }
    .rail a[aria-current='step'] {
      color: var(--c-ink);
      border-left-color: var(--c-ink);
      font-weight: 600;
    }
    .no {
      font-variant-numeric: tabular-nums;
      color: var(--c-muted);
    }
    .split {
      display: grid;
      grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
      gap: 24px;
      align-items: start;
    }
    .split .fig {
      order: 0;
      position: sticky;
      top: 16px;
    }
  }
  @media (prefers-reduced-motion: no-preference) {
    :global(html:has(.report)) {
      scroll-behavior: smooth;
    }
  }
</style>
