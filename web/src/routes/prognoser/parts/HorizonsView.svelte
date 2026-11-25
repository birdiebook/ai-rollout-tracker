<!-- W8: D2, forecasts 1–8 quarters ahead. A shadow throughout: it is evaluated, never a main model. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { DataTable, Term, dateLabel, fmt } from '$lib/design';
  import type { Horizons } from '$lib/data';
  import FanChart from './FanChart.svelte';
  import KindTag from './KindTag.svelte';
  import RoleTag from './RoleTag.svelte';
  import { daysUntil, periodShort, proofLinks } from './model';

  let { d2, site }: { d2: Horizons; site: { today: string; repo: string | null; sha: string | null } } = $props();

  const days = $derived(daysUntil(site.today, d2.next_origin));
  const live = $derived(d2.origin !== null && d2.origin >= d2.first_live);
  const proof = $derived(d2.file ? proofLinks(site.repo, site.sha, d2.file, d2.commit) : null);
  const sentence = $derived(
    `D2 ger banor 1–8 kvartal framåt för ${d2.targets.map((t) => t.label).join(' och ')}. ` +
      `Den är en skugga: den utvärderas men styr ingenting och ersätter inte nowcastens huvudmodell. ` +
      (d2.origin
        ? `Senaste bana från ${dateLabel(d2.origin)}${live ? '' : ', före den första skarpa prognosdagen'}.`
        : 'Ingen bana är lämnad ännu.') +
      ` Första skarpa prognosdag ${dateLabel(d2.first_live)}.`
  );
  const models = (t: Horizons['targets'][number]) => ['champion', ...t.models];
</script>

<svelte:head><title>D2 Prognoser 1–8 kvartal – Prognoser – AI-utrullningen</title></svelte:head>

<p class="kicker"><a href={resolve('/prognoser')}>Prognoser</a> / D2</p>
<h1>D2 Prognoser 1–8 kvartal</h1>
<p class="lede">{sentence}</p>
<p class="tags">
  <RoleTag role="shadow" id="D2" />
  <KindTag kind={live ? 'skarp' : 'skugga'} />
  {#if d2.next_origin}<span class="next">Nästa: <b>{dateLabel(d2.next_origin)}</b>{#if days !== null && days >= 0}&nbsp;(om {days} dagar){/if} → {periodShort(d2.next_period)}</span>{/if}
</p>
{#if d2.error}<p class="empty-line">Fel i underlaget: {d2.error}</p>{/if}

<section class="act" aria-labelledby="h-banor">
  <h2 id="h-banor">Banorna</h2>
  {#each d2.targets as t (t.id)}
    <div class="panel"><FanChart {t} origin={d2.origin} /></div>
  {/each}
  {#if d2.file}
    <p class="note">
      Fil: <code>{d2.file}</code>{#if d2.commit}, committad {dateLabel(d2.commit.date.slice(0, 10))}{#if proof?.commit} (<a href={proof.commit} rel="external"><code>{d2.commit.sha.slice(0, 7)}</code></a>){/if}{:else}, ingen commit i bygget{/if}{#if proof}: <a href={proof.history} rel="external">commit-historik</a>{/if}. Grupper: {Object.entries(d2.groups).map(([g, hs]) => `${g} = h ${hs.join(', ')}`).join('; ')}.
    </p>
  {/if}
</section>

<section class="act" aria-labelledby="h-facit">
  <h2 id="h-facit">Facit per horisont <KindTag kind="skugga" /></h2>
  {#each d2.targets as t (t.id)}
    <div class="panel">
      <h3>{t.label}</h3>
      {#if t.summary?.length}
        <DataTable
          table={{
            caption: `MAE per horisont och modell (100 × log), n i parentes`,
            columns: [{ key: 'h', label: 'Horisont', align: 'right' }, { key: 'g', label: 'Grupp', align: 'left' }, ...models(t).map((m) => ({ key: m, label: m === 'champion' ? 'vald modell' : m, align: 'right' as const }))],
            rows: t.summary.map((s) => ({
              h: s.h,
              g: s.group,
              ...Object.fromEntries(models(t).map((m) => [m, `${fmt(s[`mae_${m}`] as number | null, 1)} (${s[`n_${m}`] ?? 0})`]))
            }))
          }}
        />
        <p class="note">Få utfall per horisont: skillnaderna kan vara slump. Kalibrering (<Term id="crps">CRPS</Term>, täckning) visas när fördelningarna har utfall (n_dist).</p>
      {:else}
        <p class="empty-line">Inga utfall att jämföra med ännu.</p>
      {/if}
    </div>
  {/each}
</section>

<style>
  .tags {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 10px;
    margin: 10px 0 0;
  }
  .next {
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  .act {
    margin-top: 28px;
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 14px;
  }
  .act > h2 {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
  }
  .empty-line {
    color: var(--c-ink-2);
    font-size: var(--fs-small);
    margin: 4px 0 0;
  }
  .note {
    margin: 8px 0 0;
  }
</style>
