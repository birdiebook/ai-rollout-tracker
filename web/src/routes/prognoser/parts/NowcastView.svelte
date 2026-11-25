<!-- W8: one nowcast (n1–n6) in three acts. See ../[id]/+page.svelte. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { DataTable, dateLabel, signed } from '$lib/design';
  import type { Commit, Nowcast } from '$lib/data';
  import BandsOverTime from './BandsOverTime.svelte';
  import BacktestCalibration from './BacktestCalibration.svelte';
  import Facit from './Facit.svelte';
  import GhostDots from './GhostDots.svelte';
  import ForecastDots from './ForecastDots.svelte';
  import KindTag from './KindTag.svelte';
  import LiveCalibration from './LiveCalibration.svelte';
  import RoleTag from './RoleTag.svelte';
  import { count, daysUntil, liveRows, periodShort, proofLinks, repoFile, roleOf, roles as mkRoles, valueFmt } from './model';

  let { nc, site }: { nc: Nowcast; site: { today: string; repo: string | null; sha: string | null } } = $props();

  const r = $derived(mkRoles(nc));
  const rows = $derived(liveRows(nc));
  const latest = $derived(rows.at(-1));
  const f = $derived(valueFmt(nc));
  const unit = $derived(nc.unit ?? '');
  const scored = $derived(rows.filter((x) => x.scored));
  const days = $derived(daysUntil(site.today, nc.next_origin));
  const srcLine = $derived(nc.source ?? undefined);
  const lic = $derived(nc.license ?? undefined);
  const sentence = $derived(
    [
      `Huvudmodellen ${r.champion} (${r.text[r.champion] ?? 'registrerad'}) lämnar en skarp prognos med intervall ${nc.origin_rule ? nc.origin_rule.split('.')[0] : 'enligt registret'}.`,
      rows.length === 0
        ? 'Ingen skarp prognos är lämnad ännu.'
        : `${rows.length === 1 ? 'En skarp prognos' : `${rows.length} skarpa prognoser`} hittills, ${count(scored.length, 'ett', 'inget')} med utfall.`,
      nc.next_origin ? `Nästa: ${dateLabel(nc.next_origin)} för ${periodShort(nc.next_period, true)}.` : ''
    ].join(' ')
  );
  const results = $derived(repoFile(site.repo, nc.results_doc));
  const proof = (file: string, commit?: Commit | null) => proofLinks(site.repo, site.sha, file, commit);
</script>

<svelte:head><title>{nc.label} {nc.title} – Prognoser – AI-utrullningen</title></svelte:head>

<p class="kicker"><a href={resolve('/prognoser')}>Prognoser</a> / {nc.label}</p>
<h1>{nc.label} {nc.title}</h1>
<p class="lede">{sentence}</p>
<p class="tags">
  <RoleTag role="champion" id={r.champion} title={r.text[r.champion]} />
  {#if r.baseline}<RoleTag role="baseline" id={r.baseline} title={r.text[r.baseline]} />{/if}
  {#if r.guidance}<RoleTag role="guidance" id={r.guidance} title={r.text[r.guidance]} />{/if}
  {#each r.shadows.filter((s) => s !== r.baseline && s !== r.guidance) as s (s)}<RoleTag role="shadow" id={s} title={r.text[s]} />{/each}
</p>

<section class="act" aria-labelledby="h-fore">
  <h2 id="h-fore"><span class="actno">1</span> Före: {latest ? 'den senaste skarpa prognosen' : 'nästa skarpa prognos'}</h2>
  <div class="hero">
    {#if latest}
      {@const pr = proof(latest.file, latest.commit)}
      <div class="panel">
        <p class="kicker">{periodShort(latest.period, true)} · <KindTag kind={latest.verified ? 'skarp' : 'overifierad'} /></p>
        <p class="big num">{f(latest.value)} <small>{unit}</small></p>
        <p class="range num">
          80 %: {f(latest.intervals['80']?.[0])}–{f(latest.intervals['80']?.[1])} · 50 %: {f(latest.intervals['50']?.[0])}–{f(latest.intervals['50']?.[1])}
        </p>
        <dl class="facts">
          <dt>Prognosdag</dt>
          <dd>{latest.origin ? dateLabel(latest.origin) : '–'}</dd>
          <dt>Utfall</dt>
          <dd>
            {#if latest.outcome !== null}<b>{f(latest.outcome)}</b> {unit}{#if latest.outcomeKnown}, publicerat {dateLabel(latest.outcomeKnown)}{/if}{:else}väntar{/if}
          </dd>
          {#if latest.err !== null}
            <dt>Fel</dt>
            <dd>{signed(latest.err, 1)} ({nc.error_unit}), {latest.inside['80'] ? 'inom' : 'utanför'} 80 %-intervallet</dd>
          {/if}
          <dt>Bevis</dt>
          <dd>
            <code>{latest.file}</code>{#if latest.commit}, committad {dateLabel(latest.commit.date.slice(0, 10))}
              ({#if pr?.commit}<a href={pr.commit} rel="external"><code>{latest.commit.sha.slice(0, 7)}</code></a>{:else}<code>{latest.commit.sha.slice(0, 7)}</code>{/if}){:else}, väntar på verifiering (ingen commit i bygget){/if}{#if pr}: <a href={pr.history} rel="external">commit-historik</a>{/if}
          </dd>
        </dl>
        <p><a href={resolve('/prognoser/[id]/[[slug]]', { id: nc.id, slug: latest.slug })}>Prognosens egen sida →</a></p>
      </div>
      <div class="panel">
        <ForecastDots id="dots" row={latest} {unit} format={f} source={srcLine} license={lic} />
      </div>
    {:else}
      <div class="panel">
        <p class="kicker">Nästa skarpa prognos · <KindTag kind="väntar" /></p>
        {#if nc.next_origin}
          <p class="big num">{dateLabel(nc.next_origin)}</p>
          <p class="range">{#if days !== null && days >= 0}om {days} dagar&nbsp;·&nbsp;{/if}avser {periodShort(nc.next_period, true)}</p>
        {:else}
          <p class="big">Ingen planerad</p>
        {/if}
        <p class="rule">{nc.origin_rule}</p>
      </div>
      <div class="panel empty">
        <GhostDots />
        <p>
          När prognosen är lämnad visas den här som <b>20 lika sannolika utfall</b> (en prick = 5 %), med 50-, 80- och
          95 %-intervallen under. Filen committas till <code>forecasts/</code>, och git-tidsstämpeln är beviset på att
          prognosen fanns före utfallet.
        </p>
      </div>
    {/if}
  </div>
</section>

<section class="act" aria-labelledby="h-utfall">
  <h2 id="h-utfall"><span class="actno">2</span> Utfallet: prognos mot utfall</h2>
  <div class="panel">
    {#if rows.length}<p class="kindline"><KindTag kind="skarp" /> bara skarpa, committade prognoser; inga backtestmånader</p>{/if}
    <BandsOverTime id="over-time" {rows} history={nc.history} nextPeriod={nc.next_period} {unit} format={f} source={srcLine} license={lic} />
  </div>
  <div class="panel">
    {#if scored.length}
      <p class="kindline"><KindTag kind="skarp" /> mot den första publicerade versionen av utfallet</p>
      <Facit id="facit" {rows} roles={r} errorUnit={nc.error_unit ?? ''} />
    {:else}
      <h3>Facit</h3>
      <p class="empty-line">
        Inget utfall att jämföra med ännu. När utfallet publiceras jämförs huvudmodellen {r.champion} med den naiva
        baslinjen{r.baseline ? ` ${r.baseline}` : ''}{r.guidance ? ` och med guidance (${r.guidance})` : ''}, mot den första publicerade versionen av utfallet.
      </p>
    {/if}
    {#if rows.length}
      <h3 class="sub">Skarpa prognoser</h3>
      <DataTable
        table={{
          caption: `Varje skarp prognos (${unit})`,
          columns: [
            { key: 'p', label: 'Avser', align: 'left' },
            { key: 'o', label: 'Lämnad', align: 'left' },
            { key: 'v', label: 'Prognos', align: 'right' },
            { key: 'y', label: 'Utfall', align: 'right' },
            { key: 'e', label: `Fel (${nc.error_unit})`, align: 'right' },
            { key: 'h', label: 'Inom 80 %', align: 'left' }
          ],
          rows: [...rows].reverse().map((x) => ({
            p: periodShort(x.period),
            o: x.origin ? dateLabel(x.origin) : '–',
            v: f(x.value),
            y: x.outcome === null ? 'väntar' : f(x.outcome),
            e: signed(x.err, 1),
            h: x.inside['80'] === undefined ? '–' : x.inside['80'] ? 'ja' : 'nej'
          }))
        }}
      />
      <ul class="pages">
        {#each [...rows].reverse() as x (x.slug)}
          <li><a href={resolve('/prognoser/[id]/[[slug]]', { id: nc.id, slug: x.slug })}>{nc.label} för {periodShort(x.period, true)}</a></li>
        {/each}
      </ul>
    {/if}
  </div>
</section>

<section class="act" aria-labelledby="h-efter">
  <h2 id="h-efter"><span class="actno">3</span> Efter: kalibrering</h2>
  <div class="panel">
    <h3>Skarpa utfall <KindTag kind={rows.length ? 'skarp' : 'väntar'} /></h3>
    <LiveCalibration id="live-cal" {rows} coverage={nc.coverage ?? []} champion={r.champion} />
  </div>
  <div class="panel">
    <h3>Backtest <KindTag kind="backtest" /></h3>
    {#if nc.backtest_calibration?.available && nc.backtest_calibration.rows.length}
      <BacktestCalibration id="bt" cal={nc.backtest_calibration} roles={r} />
    {:else}
      <p class="empty-line">Ingen backtestkalibrering i paketet för {nc.label}{nc.backtest_calibration?.error ? ` (${nc.backtest_calibration.error})` : ''}.</p>
    {/if}
  </div>
</section>

<section class="act" aria-labelledby="h-modeller">
  <h2 id="h-modeller">Modellerna</h2>
  <div class="panel">
    <ul class="variants">
      {#each nc.variants ?? [] as v (v.id)}
        <li><RoleTag role={roleOf(r, v.id)} id={v.id} /> <span>{v.text}</span></li>
      {/each}
    </ul>
    <p class="note">
      Mål: {nc.target_label ?? nc.target} ({unit}, {nc.frequency}). Källa: {nc.source}. Licens: {nc.license}.
      {#if results}Registrerad utvärdering: <a href={results} rel="external">{nc.results_doc}</a>.{/if}
    </p>
  </div>
</section>

<style>
  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 10px 0 0;
  }
  .act {
    margin-top: 28px;
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 14px;
  }
  .act > h2 {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .actno {
    display: inline-grid;
    place-items: center;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    border: 1.5px solid var(--c-ink-2);
    font-size: 13px;
    font-weight: 620;
  }
  .hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 14px;
  }
  @media (min-width: 861px) {
    .hero {
      grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
    }
  }
  .hero .kicker {
    margin: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
  }
  .big {
    font-size: var(--fs-big);
    font-weight: 700;
    letter-spacing: -0.03em;
    line-height: 1.05;
    margin: 8px 0 0;
  }
  .big small {
    font-size: 15px;
    font-weight: 500;
    color: var(--c-ink-2);
    letter-spacing: 0;
  }
  .range {
    color: var(--c-ink-2);
    margin: 6px 0 0;
  }
  .rule {
    margin: 14px 0 0;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  .facts {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 4px 14px;
    font-size: 14px;
    margin: 14px 0 10px;
  }
  .facts dt {
    color: var(--c-muted);
  }
  .facts dd {
    margin: 0;
    overflow-wrap: anywhere;
  }
  .empty {
    border-style: dashed;
    border-color: var(--c-axis);
    color: var(--c-ink-2);
    font-size: var(--fs-small);
  }
  .empty p {
    margin: 10px 0 0;
  }
  .empty-line {
    color: var(--c-ink-2);
    font-size: var(--fs-small);
    margin: 4px 0 0;
    max-width: 75ch;
  }
  .sub {
    margin-top: 18px;
  }
  .kindline {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin: 0 0 10px;
    font-size: 12px;
    color: var(--c-muted);
  }
  .pages {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 16px;
    padding: 0;
    list-style: none;
    font-size: var(--fs-small);
    margin: 8px 0 0;
  }
  .pages a {
    display: inline-block;
    min-height: 24px;
  }
  .panel h3 {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
  }
  .variants {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    gap: 8px;
    font-size: var(--fs-small);
  }
  .variants li {
    display: flex;
    gap: 10px;
    align-items: baseline;
  }
  .variants li span:last-child {
    color: var(--c-ink-2);
  }
</style>
