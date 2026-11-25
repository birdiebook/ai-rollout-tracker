<!-- A series page on a past day (W9): the levels exactly as known then (the latest version with known_from <= day),
     the record's measures at the month ends known then, and, clearly labelled, the revisions since: W7's revision
     view with the chosen version against today's (dashed). Its version buttons move the global day. -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { resolve } from '$app/paths';
  import { DIRECTIONS, Glyph, StatusBadge, dateLabel, fmt, periodLabel, signed } from '$lib/design';
  import type { Overview } from '$lib/data';
  import RevisionExplorer from '$lib/series/RevisionExplorer.svelte';
  import { defaultLog, logAllowed } from '$lib/series/chart';
  import { freqLabel, periodText } from '$lib/series/period';
  import { num } from '$lib/series/text';
  import type { SeriesDoc } from '$lib/series/types';
  import { lastMonthEnd, seriesOn } from '../gate';
  import { tt } from '../store.svelte';
  import Head from './Head.svelte';
  import LevelChart from './LevelChart.svelte';
  import PaceChart from './PaceChart.svelte';
  import { bundle } from './load';
  import { monthsBetween } from './months';

  let { day, params }: { day: string; params: { key: string } } = $props();
  let doc = $state<SeriesDoc | null>(null);
  let ov = $state<Overview | null>(null);
  let err = $state<string | null>(null);
  onMount(async () => {
    try {
      const b = bundle();
      const [d, o] = await Promise.all([b.series(params.key), b.overview()]);
      doc = d as unknown as SeriesDoc;
      ov = o;
    } catch (e) {
      err = String(e);
    }
  });
  const s = $derived(doc && ov ? seriesOn(doc, day, ov.record) : null);
  const status = $derived(s && (s.backfilled || !s.measure || s.measure.kind !== 'skarp') ? 'recon' : 'live');
  const vals = $derived(s ? s.levels.map((l) => l.value) : []);
  const log = $derived(!!s && logAllowed(vals) && defaultLog(vals, s.meta.method));
  const last = $derived(s?.levels.at(-1) ?? null);
  const scaleRef = $derived(Math.max(0, ...vals.map(Math.abs)));
  const months = $derived(doc?.measure_history?.months.length ? monthsBetween(doc.measure_history.months[0], lastMonthEnd(tt.max)) : []);
  const branchHref = $derived(s && /^G[1-9]$/.test(s.meta.branch) ? resolve('/gren/[id]', { id: s.meta.branch }) : null);
  const m = $derived(s?.measure ?? null);
</script>

<svelte:head><title>{s?.meta.label ?? params.key} som den var känd {day} – AI-utrullningen</title></svelte:head>

{#if err}
  <h1>{params.key}</h1>
  <p class="note" role="alert">Kunde inte hämta serien: {err}</p>
{:else if !s || !doc}
  <h1>{params.key}</h1>
  <p class="note" role="status">Hämtar seriens versioner …</p>
{:else}
  <Head title={s.meta.label} {day} month={m?.month ?? null} known={m?.known ?? null} status={status}>
    {#snippet kicker()}
      {#if branchHref}<a href={branchHref}>{s.meta.branch} {s.meta.branch_name ?? ''}</a>{:else}{s.meta.branch}{/if} · {freqLabel(s.meta.freq)} · <code>{s.meta.key}</code> · tidsresa till {dateLabel(day)}
    {/snippet}
    {#snippet extra()}
      {#if s.backfilled}<p class="note"><StatusBadge status="recon" /> Historiken fram till {dateLabel(doc!.rows?.backfill_last_known ?? '')} är bakåtfylld med dagens version: värdena före den dagen är rekonstruerade, inte de som publicerades då.</p>{/if}
    {/snippet}
  </Head>

  <section class="figs" aria-label="Nyckeltal den dagen" data-tt="asof" data-known={last?.known ?? ''}>
    <div class="panel fig">
      <p class="kicker">Senast kända värde</p>
      {#if last}
        <p class="big num">{num(last.value, scaleRef)} <span class="unit">{s.meta.unit}</span></p>
        <p class="note">{periodText(last.period, true)}, känt från {dateLabel(last.known)}</p>
      {:else}
        <p class="big">–</p>
        <!-- R-W1: the day of the first version is later knowledge and is not shown -->
        <p class="note">Inget var publicerat ännu.</p>
      {/if}
    </div>
    <div class="panel fig" data-known={m?.known ?? ''}>
      <p class="kicker">Postens riktning{m ? ` ${periodLabel(m.month)}` : ''}</p>
      {#if m && m.direction !== null && m.direction !== undefined}
        <p class="big"><Glyph direction={m.direction} /></p>
        <p class="note">Takt {signed(m.pace ?? null, 1)}, förändring i takt {signed(m.change_in_pace ?? null, 2)}{m.counted ? '' : ' · räknas inte'}</p>
      {:else if m}
        <p class="big">–</p>
        <p class="note">Mätt men utan riktning{m.counted ? '' : ', räknas inte'}.</p>
      {:else}
        <p class="big">–</p>
        <p class="note">Serien var inte i posten vid något känt månadsslut.</p>
      {/if}
    </div>
    <div class="panel fig">
      <p class="kicker">Versioner kända</p>
      <p class="big num">{fmt(s.versions?.n_versions ?? 0)}</p>
      <p class="note">{fmt(s.versions?.periods.length ?? 0)} perioder, {fmt(s.versions?.n_revised_periods ?? 0)} reviderade till dess</p>
    </div>
  </section>

  <section class="panel" data-tt="asof">
    <LevelChart {s} status={status} {log} />
    <p class="attrib">{s.meta.license?.attribution}</p>
  </section>

  {#if s.history && months.length}
    <section class="panel" data-tt="asof">
      <PaceChart {s} {months} status={status} />
      <p class="note">
        {#each [-1, 0, 1] as k (k)}<span class="lg"><span style:color={DIRECTIONS[k as -1 | 0 | 1].color} aria-hidden="true">{DIRECTIONS[k as -1 | 0 | 1].glyph}</span> {DIRECTIONS[k as -1 | 0 | 1].word}</span>{/each}
      </p>
    </section>
  {/if}

  {#if doc.versions}
    <section aria-labelledby="tt-rev-h" data-tt="compare">
      <h2 id="tt-rev-h">Revideringar sedan dess: då mot i dag</h2>
      <p class="note">Här, och bara här, visas också dagens version (streckad) för jämförelse. Versionsknapparna flyttar tidsresans datum.</p>
      <div class="panel">
        <RevisionExplorer versions={doc.versions} bind:day={() => day, (d) => tt.set(d)} unit={s.meta.unit} {log} backfillLastKnown={doc.rows?.backfill_last_known} source={s.meta.source} license={s.meta.license?.short} />
      </div>
    </section>
  {/if}
{/if}

<style>
  code {
    font-family: var(--mono);
    font-size: 0.92em;
    overflow-wrap: anywhere;
  }
  .figs {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
  }
  .fig p {
    margin: 0;
  }
  .big {
    font-size: 26px;
    font-weight: 680;
    line-height: 1.25;
  }
  .unit {
    font-size: var(--fs-small);
    font-weight: 400;
    color: var(--c-ink-2);
  }
  .attrib {
    font-size: 12px;
    color: var(--c-muted);
    margin: 10px 0 0;
  }
  .lg {
    margin-right: 14px;
  }
</style>
