<!-- W8: one live forecast, permanently (/prognoser/<id>/<slug>/) (section 3.4): before (the forecast as 20 equally likely outcomes, every
     variant's value), the outcome and after (errors, CRPS and PIT per model from the scorecard). -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { DataTable, dateLabel, fmt, signed } from '$lib/design';
  import type { Nowcast } from '$lib/data';
  import ForecastDots from './ForecastDots.svelte';
  import KindTag from './KindTag.svelte';
  import RoleTag from './RoleTag.svelte';
  import { LEVELS, errOf, liveRows, periodShort, proofLinks, roleOf, roles as mkRoles, valueFmt } from './model';

  let { nc, slug, site }: { nc: Nowcast; slug: string; site: { today: string; repo: string | null; sha: string | null } } = $props();
  const r = $derived(mkRoles(nc));
  const row = $derived(liveRows(nc).find((x) => x.slug === slug)!);
  const f = $derived(valueFmt(nc));
  const unit = $derived(nc.unit ?? '');
  const proof = $derived(proofLinks(site.repo, site.sha, row.file));
  const ids = $derived((nc.variants ?? []).map((v) => v.id));
  const num = (x: unknown) => (typeof x === 'number' ? x : null);
</script>

<svelte:head><title>{nc.label} {periodShort(row.period, true)} – Prognoser – AI-utrullningen</title></svelte:head>

<p class="kicker">
  <a href={resolve('/prognoser')}>Prognoser</a> / <a href={resolve('/prognoser/[id]/[[slug]]', { id: nc.id })}>{nc.label}</a> / {periodShort(row.period)}
</p>
<h1>{nc.label} för {periodShort(row.period, true)}: {f(row.value)} {unit}</h1>
<p class="lede">
  {nc.title}. Lämnad {row.origin ? dateLabel(row.origin) : '–'} av huvudmodellen {row.champion}, med 80 %-intervallet
  {f(row.intervals['80']?.[0])}–{f(row.intervals['80']?.[1])}.
  {#if row.scored}Utfallet blev {f(row.outcome)}, {row.inside['80'] ? 'inom' : 'utanför'} 80 %-intervallet.{:else if row.outcome !== null}Utfallet {f(row.outcome)} var känt vid prognosdagen och räknas inte.{:else}Utfallet är inte publicerat ännu.{/if}
</p>
<p class="tags"><KindTag kind="skarp" /> <RoleTag role="champion" id={row.champion} /></p>

<section class="proof panel" aria-labelledby="h-proof">
  <h2 id="h-proof">Beviset: tidsstämpeln i git</h2>
  <p>
    Prognosen ligger i <code>{row.file}</code>. Den committades före utfallet och skrivs aldrig om; den första commiten i
    filens historik är tidsstämpeln.
  </p>
  {#if proof}
    <p class="links">
      <a href={proof.history} rel="external">Filens commit-historik på GitHub</a>
      <a href={proof.file} rel="external">Filen {proof.ref === 'main' ? 'på main' : `vid commit ${proof.ref.slice(0, 7)}`}</a>
    </p>
  {/if}
</section>

<section class="act" aria-labelledby="h-fore">
  <h2 id="h-fore"><span class="actno">1</span> Före</h2>
  <div class="panel">
    <ForecastDots id="dots" {row} {unit} format={f} title="Prognosen som 20 lika sannolika utfall" source={nc.source ?? undefined} license={nc.license ?? undefined} />
  </div>
  <div class="panel">
    <DataTable
      table={{
        caption: `Alla varianter i filen (${unit})`,
        columns: [{ key: 'm', label: 'Variant', align: 'left' }, { key: 'r', label: 'Roll', align: 'left' }, { key: 'v', label: 'Prognos', align: 'right' }],
        rows: ids
          .filter((id) => id in row.variants)
          .map((id) => ({
            m: id,
            r: { champion: 'huvudmodell', baseline: 'naiv baslinje', guidance: 'guidance', shadow: 'skugga' }[roleOf(r, id)],
            v: f(row.variants[id])
          }))
      }}
    />
  </div>
</section>

<section class="act" aria-labelledby="h-after">
  <h2 id="h-after"><span class="actno">2</span> Utfallet och efter</h2>
  <div class="panel">
    {#if row.scored}
      <p>
        Utfall <b>{f(row.outcome)}</b> {unit}{#if row.outcomeKnown}, första publicerade versionen {dateLabel(row.outcomeKnown)}{/if}.
        {LEVELS.map((l) => `${row.inside[l] ? 'Inom' : 'Utanför'} ${l} %`).join(' · ')}.
      </p>
      <DataTable
        table={{
          caption: `Fel per variant (${nc.error_unit}), CRPS och PIT där fördelningen finns`,
          columns: [
            { key: 'm', label: 'Variant', align: 'left' },
            { key: 'e', label: 'Fel', align: 'right' },
            { key: 'c', label: 'CRPS', align: 'right' },
            { key: 'p', label: 'PIT', align: 'right' }
          ],
          rows: ids.map((id) => ({
            m: id === r.champion ? `${id} (huvudmodell)` : id,
            e: signed(errOf(row.score, id), 1),
            c: fmt(num(row.score?.[`crps_${id}`]), 2),
            p: fmt(num(row.score?.[`pit_${id}`]), 2)
          }))
        }}
      />
      <p class="note">Ett enskilt utfall säger lite om en modell. Kalibreringen över alla skarpa prognoser finns på <a href={resolve('/prognoser/[id]/[[slug]]', { id: nc.id })}>{nc.label}-sidan</a>.</p>
    {:else}
      <p class="empty-line">Utfallet är inte publicerat ännu. När det kommer visas det här, i prickdiagrammet och i facit.</p>
    {/if}
  </div>
</section>

<style>
  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 10px 0 0;
  }
  .proof {
    margin-top: 18px;
    border: 1px solid var(--c-ink-2);
  }
  .proof p {
    margin: 4px 0 0;
    max-width: 75ch;
    overflow-wrap: anywhere;
  }
  .links {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 18px;
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
  .empty-line {
    color: var(--c-ink-2);
    font-size: var(--fs-small);
    margin: 0;
  }
</style>
