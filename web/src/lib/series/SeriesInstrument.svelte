<!-- The series instrument (W7): one component for every publishable series and every frequency (D/W/2W/M/Q/A).
     Picture first: the state engine's numbers as tiles, the level, pace and change in pace with the dead band, the
     record's direction month by month, and the revisions. Every chart has a table view, source and licence; the
     levels and versions can be downloaded as CSV; the view lives in the URL hash (permalink). The versions are
     fetched only when the revision view (or `as_of` in the URL, W9) is used. -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { resolve } from '$app/paths';
  import { replaceState } from '$app/navigation';
  import { Deferred, Glyph, StatusBadge, Term, dateLabel, fmt, type RecordStatus } from '$lib/design';
  import { clientBundle } from '$lib/data';
  import KeyFigures from './KeyFigures.svelte';
  import LevelChart from './LevelChart.svelte';
  import MeasureCharts from './MeasureCharts.svelte';
  import RecordStrip from './RecordStrip.svelte';
  import RevisionSummary from './RevisionSummary.svelte';
  import RevisionExplorer from './RevisionExplorer.svelte';
  import { defaultLog, logAllowed, type TimePoint } from './chart';
  import { levelsCsv, versionsCsv } from './csv';
  import { WINDOW_LABEL, YEAR_MS, freqLabel, periodText, periodTime, windowStart, windowsFor, type Window } from './period';
  import { parseState, serializeState, type ViewState } from './permalink';
  import { defaultAsOf } from './versions';
  import { plural } from './text';
  import type { SeriesPageData } from './page';
  import type { SeriesDoc, Versions } from './types';

  let { data, recordStatus = 'recon' }: { data: SeriesPageData; recordStatus?: RecordStatus } = $props();

  const s = $derived(data.series);
  const allPoints: TimePoint[] = $derived(
    (s.levels?.periods ?? [])
      .map((p, i) => ({ p, t: periodTime(p), v: s.levels?.values[i] ?? NaN }))
      .filter((q) => Number.isFinite(q.v) && Number.isFinite(q.t))
  );
  const vals = $derived(allPoints.map((q) => q.v));
  // log scale only for positive quantities measured in logs (not for shares, logit scores)
  const canLog = $derived(logAllowed(vals) && ['log', 'doubling', 'halving'].includes(s.method ?? ''));
  const defaults = $derived<Partial<ViewState>>({ skala: defaultLog(vals, s.method) ? 'log' : 'lin' });
  const years = $derived(allPoints.length > 1 ? (allPoints.at(-1)!.t - allPoints[0].t) / YEAR_MS : 0);
  const windows = $derived(windowsFor(years));
  // the prerendered page is the default view; the hash is applied after hydration
  let view = $state<ViewState>(parseState(''));
  let mounted = $state(false);
  const scale = $derived(mounted ? view.skala : (defaults.skala ?? 'lin'));
  const end = $derived(allPoints.at(-1)?.t ?? NaN);
  const from = $derived(windowStart(view.fonster, end));
  const points = $derived(allPoints.filter((q) => q.t >= from));
  const revisedMap = $derived(
    data.revision && (data.versions?.freq === s.freq)
      ? new Map(data.revision.periods.map((p, i) => [p, { first: data.revision!.first[i], n: data.revision!.n[i] }]).filter(([, r]) => (r as { n: number }).n > 1) as [string, { first: number; n: number }][])
      : undefined
  );
  const relative = $derived(s.method === 'log' && !!data.revision && data.revision.first.every((x) => x > 0) && data.revision.latest.every((x) => x > 0));
  const freqNote = $derived(
    data.versions && data.versions.native_freq !== data.versions.freq
      ? `${data.versions.aggregation === 'sum' ? 'månadssummor' : 'månadsmedel'} av dagliga värden, som i måtten`
      : undefined
  );
  const license = $derived(s.license.short);
  const branchHref = $derived(/^G[1-9]$/.test(s.branch) ? resolve('/gren/[id]', { id: s.branch }) : null);

  // --- run-time versions (revision view, time travel) ---
  let full = $state<Versions | null>(null);
  let loading = $state(false);
  let loadError = $state<string | null>(null);
  async function loadVersions(): Promise<Versions | null> {
    if (full) return full;
    if (loading) return null;
    loading = true;
    loadError = null;
    try {
      const doc = (await clientBundle(fetch, resolve('/').replace(/\/$/, '')).series(s.key)) as unknown as SeriesDoc;
      full = doc.versions;
      return full;
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
      return null;
    } finally {
      loading = false;
    }
  }
  $effect(() => {
    if (mounted && view.rev && !full && !loading && !loadError) loadVersions();
  });
  // without as_of in the URL the view opens on the version current a year before the latest (so that the chosen
  // version and today's differ); "I dag" is then an explicit as_of
  const defaultDay = $derived(full ? defaultAsOf(full) : '');
  const day = $derived(view.as_of ?? defaultDay);
  function setDay(d: string) {
    view = { ...view, rev: true, as_of: d === defaultDay ? null : d };
  }

  // --- URL state ---
  onMount(() => {
    const read = () => (view = parseState(location.hash, defaults));
    read();
    mounted = true;
    addEventListener('hashchange', read);
    return () => removeEventListener('hashchange', read);
  });
  $effect(() => {
    if (!mounted) return;
    const h = serializeState(view, defaults);
    if (h !== location.hash && !(h === '' && location.hash === '')) replaceState(location.pathname + location.search + h, {});
  });
  const setWindow = (w: Window) => (view = { ...view, fonster: w });
  const setScale = (k: 'lin' | 'log') => (view = { ...view, skala: k });

  // --- downloads and permalink ---
  let copied = $state('');
  function save(name: string, text: string) {
    const url = URL.createObjectURL(new Blob(['﻿' + text], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const downloadLevels = () => save(`${s.key}.csv`, levelsCsv(s, s.levels, location.href));
  async function downloadVersions() {
    const v = await loadVersions();
    if (v) save(`${s.key}_versioner.csv`, versionsCsv(s, v, location.href));
  }
  async function copyLink() {
    try {
      await navigator.clipboard.writeText(location.href);
      copied = 'Länken är kopierad.';
    } catch {
      copied = `Kopiera adressen: ${location.href}`;
    }
  }
  const counts = $derived(s.rows?.counts ?? {});
</script>

<header class="head">
  <p class="kicker">
    {#if branchHref}<a href={branchHref}>{s.branch} {s.branch_name ?? ''}</a>{:else}{s.branch}{/if}
    · {freqLabel(s.freq)} · <code>{s.key}</code>
  </p>
  <h1>{s.label}</h1>
  {#if s.question}<p class="lede">{s.question}</p>{/if}
  <ul class="tags" aria-label="Seriens roll">
    <li><StatusBadge status={recordStatus} /></li>
    {#if s.core}<li class="tag">kärnserie</li>{/if}
    {#if s.counted}<li class="tag">räknas i {s.record_branch ?? s.branch}</li>{:else if s.in_record}<li class="tag">mäts, räknas inte</li>{/if}
    {#if s.reconciliation}<li class="tag">avstämning</li>{/if}
    {#if s.revised}<li class="tag">källan reviderar</li>{/if}
  </ul>
</header>

<section aria-labelledby="kf-h">
  <h2 id="kf-h" class="visually-hidden">Läget enligt tillståndsmotorn</h2>
  <Deferred><KeyFigures measure={s.measure} unit={s.unit} last={allPoints.length ? { p: allPoints.at(-1)!.p, v: allPoints.at(-1)!.v } : null} /></Deferred>
  <p class="note">
    Tillståndsmotorns mått per {dateLabel(s.measure_as_of)}{s.measure?.known_from ? `, senaste period ${periodText(s.measure.latest_period ?? '')} känd från ${dateLabel(s.measure.known_from)}` : ''}.
    Riktningen räknas mot <Term id="dodband">dödbandet</Term> 0,25 × seriens egen standardavvikelse för förändring i takt (måttregistret avsnitt 2).
  </p>
</section>

<section class="panel" aria-labelledby="level-title">
  <div class="toolbar">
    {#if windows.length > 1}
      <div class="seg" role="group" aria-label="Tidsfönster">
        {#each windows as w (w)}
          <button type="button" class="chip" aria-pressed={view.fonster === w} onclick={() => setWindow(w)}>{WINDOW_LABEL[w]}</button>
        {/each}
      </div>
    {/if}
    {#if canLog}
      <div class="seg" role="group" aria-label="Skala">
        <button type="button" class="chip" aria-pressed={scale === 'lin'} onclick={() => setScale('lin')}>Linjär</button>
        <button type="button" class="chip" aria-pressed={scale === 'log'} onclick={() => setScale('log')}>Logaritmisk</button>
      </div>
    {/if}
  </div>
  {#if allPoints.length}
    <LevelChart
      label={s.label}
      unit={s.unit}
      {points}
      totalCount={allPoints.length}
      log={scale === 'log' && canLog}
      status={recordStatus}
      source={s.source}
      {license}
      revised={revisedMap}
    />
  {:else}
    <h2 id="level-title">Nivå</h2>
    <p class="note">Serien har inga publicerade värden ännu.</p>
  {/if}
  <p class="attrib">{s.license.attribution}</p>
  <div class="actions">
    <button type="button" class="chip" onclick={downloadLevels} disabled={!allPoints.length}>Ladda ned nivåer (CSV)</button>
    {#if data.versions}<button type="button" class="chip" onclick={downloadVersions}>Ladda ned alla versioner (CSV)</button>{/if}
    <button type="button" class="chip" onclick={copyLink}>Kopiera permalänk</button>
    <span class="note" role="status">{copied}</span>
  </div>
</section>

{#if s.measure_path && s.measure_path.periods.length}
  <section aria-labelledby="measures-h">
    <h2 id="measures-h">Takt och förändring i takt</h2>
    <p class="note">Som tillståndsmotorn räknade dem per {dateLabel(s.measure_as_of)}, de senaste tio åren{s.measure?.measure_freq && s.measure.measure_freq !== s.freq ? `, på ${freqLabel(s.measure.measure_freq)} nivå` : ''}.</p>
    <div class="panel">
      <MeasureCharts path={s.measure_path} measure={s.measure} {from} status={recordStatus} source={s.source} {license} />
    </div>
  </section>
{/if}

{#if s.measure_history && s.measure_history.months.length}
  <section class="panel">
    <RecordStrip history={s.measure_history} source={s.source} {license} />
  </section>
{/if}

<section aria-labelledby="rev-h">
  <h2 id="rev-h">Versioner och revideringar</h2>
  {#if data.versions}
    {@const vs = data.versions}
    <p class="lede rev-lede">
      {#if vs.n_revised_periods > 0}
        {fmt(vs.n_revised_periods)} av {fmt(vs.n_periods)} perioder har reviderats. {fmt(vs.n_versions)} versioner på {fmt(vs.n_dates)} dagar,
        från {dateLabel(vs.first_known)} till {dateLabel(vs.last_known)}.
      {:else}
        Inga revideringar: varje period har kvar värdet den först publicerades med ({plural(vs.n_periods, 'period', 'perioder')},
        {plural(vs.n_dates, 'publiceringsdag', 'publiceringsdagar')} från {dateLabel(vs.first_known)}).
      {/if}
      {#if s.rows?.backfill_last_known}Historiken fram till {dateLabel(s.rows.backfill_last_known)} är bakåtfylld med dagens version{#if s.rows.backfill_fetched && s.rows.backfill_fetched > s.rows.backfill_last_known}, hämtad {dateLabel(s.rows.backfill_fetched)}{/if}.{/if}
    </p>
    {#if data.revision}
      <div class="panel">
        <RevisionSummary rev={data.revision} unit={s.unit} {relative} {from} source={s.source} {license} {freqNote} />
      </div>
    {/if}
    <div class="explore">
      <button type="button" class="chip" aria-expanded={view.rev} aria-controls="rev-explorer" onclick={() => (view = { ...view, rev: !view.rev, as_of: view.rev ? null : view.as_of })}>
        {view.rev ? 'Stäng versionsvyn' : 'Utforska versionerna: vad visste vi när?'}
      </button>
      {#if !view.rev}<span class="note">Hämtar seriens versioner ({plural(vs.n_versions, 'rad', 'rader')}) först när vyn öppnas.</span>{/if}
    </div>
    <div id="rev-explorer" hidden={!view.rev}>
      {#if view.rev}
        {#if full}
          <div class="panel">
            <RevisionExplorer versions={full} bind:day={() => day, setDay} unit={s.unit} log={scale === 'log' && canLog} {from} backfill={s.rows} source={s.source} {license} />
          </div>
        {:else if loadError}
          <p class="note" role="alert">Kunde inte hämta versionerna: {loadError}</p>
        {:else}
          <p class="note" role="status">Hämtar versionerna …</p>
        {/if}
      {/if}
    </div>
  {:else}
    <p class="note">Serien har inga versioner ännu.</p>
  {/if}
</section>

<section aria-labelledby="about-h">
  <h2 id="about-h">Om serien</h2>
  <Deferred>
  <div class="panel about">
    <dl class="facts">
      <dt>Nyckel</dt><dd><code>{s.key}</code></dd>
      <dt>Enhet</dt><dd>{s.unit || '–'}</dd>
      <dt>Frekvens</dt><dd>{freqLabel(s.freq)}{s.aggregation ? ` (${s.aggregation === 'sum' ? 'summeras' : 'medel'} till månad i måtten)` : ''}</dd>
      <dt>Källa</dt><dd>{s.source}{s.source_family && s.source_family !== s.source ? ` (${s.source_family})` : ''}</dd>
      <dt>Licens</dt><dd>{s.license.text}</dd>
      <dt>Attribution</dt><dd>{s.license.attribution}</dd>
      <dt>Publiceringsfördröjning</dt><dd>{s.lag_days !== null && s.lag_days !== undefined ? `${fmt(s.lag_days)} dagar` : '–'}</dd>
      <dt>Måttmetod</dt><dd>{s.method ?? '–'}</dd>
      <dt>Rader i tabellen</dt><dd>{Object.entries(counts).map(([k, n]) => `${fmt(n)} ${k}`).join(', ') || '–'}</dd>
      <dt>Nivåer kända per</dt><dd>{s.levels ? dateLabel(s.levels.as_of) : '–'}</dd>
      {#if data.components.length}
        <dt>Härledd ur</dt>
        <dd>
          {#each data.components as c, i (c.key)}{i ? ', ' : ''}{#if c.label}<a href={resolve('/serie/[key]', { key: c.key })}>{c.label}</a>{:else}<code>{c.key}</code>{/if}{/each}
        </dd>
      {/if}
    </dl>
  </div>
  {#if data.siblings.length}
    <details class="siblings">
      <summary>Fler serier i {s.branch} {s.branch_name ?? ''} ({data.siblings.length})</summary>
      <ul>
        {#each data.siblings as o (o.key)}
          <li>
            {#if o.direction !== null}<Glyph direction={o.direction} word={false} />{:else}<span class="nodir" aria-hidden="true">–</span>{/if}
            <a href={resolve('/serie/[key]', { key: o.key })}>{o.label}</a>
            <span class="note">{freqLabel(o.freq)}{o.core ? ' · kärnserie' : ''}</span>
          </li>
        {/each}
      </ul>
    </details>
  {/if}
  </Deferred>
</section>

<style>
  .head {
    margin-top: 18px;
  }
  .kicker a {
    text-decoration: none;
  }
  .kicker a:hover {
    text-decoration: underline;
  }
  code {
    font-family: var(--mono);
    font-size: 0.92em;
    overflow-wrap: anywhere;
  }
  h1 {
    overflow-wrap: anywhere;
  }
  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    list-style: none;
    padding: 0;
    margin: 10px 0 0;
  }
  .tag {
    font-size: 12px;
    color: var(--c-ink-2);
    border: 1px solid var(--c-ring);
    border-radius: 999px;
    padding: 2px 9px;
  }
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    margin-bottom: 10px;
  }
  .seg {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .attrib {
    font-size: 12px;
    color: var(--c-muted);
    margin: 10px 0 0;
  }
  .actions,
  .explore {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 10px;
    margin-top: 10px;
  }
  .chip:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .rev-lede {
    margin-bottom: 12px;
  }
  #rev-explorer {
    margin-top: 12px;
  }
  .facts {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 2px 18px;
    margin: 0;
    font-size: var(--fs-small);
  }
  .facts dt {
    color: var(--c-ink-2);
    margin-top: 6px;
  }
  .facts dd {
    margin: 0;
    overflow-wrap: anywhere;
  }
  @media (min-width: 641px) {
    .facts {
      grid-template-columns: 200px minmax(0, 1fr);
    }
    .facts dt {
      margin-top: 0;
    }
  }
  .siblings {
    margin-top: 14px;
    font-size: var(--fs-small);
  }
  .siblings summary {
    cursor: pointer;
    min-height: var(--hit);
    display: flex;
    align-items: center;
  }
  .siblings ul {
    list-style: none;
    padding: 0;
    margin: 6px 0 0;
    columns: 2 320px;
    column-gap: 24px;
  }
  .siblings li {
    break-inside: avoid;
    padding: 3px 0;
  }
  .nodir {
    color: var(--c-muted);
    display: inline-block;
    width: 1em;
  }
</style>
