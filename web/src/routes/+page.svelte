<!-- PLACEHOLDER (W4). Owner in wave 1: W5 (start page: chain L1→L9, three question cards, stripes, headline). -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { ChartFrame, Glyph, Legend, StatusBadge, Stripes, divergingFill, fmt, periodLabel } from '$lib/design';

  let { data } = $props();
  const ov = $derived(data.overview);
  const status = $derived(ov.record.status === 'live' ? 'live' : 'recon');
  const stripeTable = $derived({
    caption: 'Diffusionsindex per gren, senaste sex månaderna',
    columns: [{ key: 'b', label: 'Gren' }, ...ov.stripes.months.slice(-6).map((m) => ({ key: m, label: periodLabel(m) }))],
    rows: ov.stripes.rows.map((r) => ({
      b: `${r.code} ${r.name}`,
      ...Object.fromEntries(ov.stripes.months.slice(-6).map((m, i) => [m, fmt(r.index[r.index.length - 6 + i], 2)]))
    }))
  });
</script>

<svelte:head><title>AI-utrullningen – läget {periodLabel(ov.headline.month, true)}</title></svelte:head>

<p class="kicker">{periodLabel(ov.headline.month, true)} <StatusBadge {status} /></p>
<h1>{ov.headline.sentence}</h1>
<p class="lede">{ov.headline.change_sentence}</p>

<section aria-labelledby="branches-h">
  <h2 id="branches-h">Grenarna</h2>
  <ul class="tiles">
    {#each ov.branches as b (b.code)}
      <li class="panel">
        <a href={resolve('/gren/[id]', { id: b.code })}><b>{b.code}</b> {b.name}</a>
        <span class="row"><Glyph state={b.state} /> <span class="num note">index {fmt(b.index, 2)}</span></span>
      </li>
    {/each}
  </ul>
</section>

<section class="panel">
  <ChartFrame
    id="stripes"
    title="Hur tillstånden har skiftat"
    description="Diffusionsindex per gren och månad, {periodLabel(ov.stripes.months[0])}–{periodLabel(ov.stripes.months.at(-1) ?? '')}. Blått: fler serier ökar takten, orange: fler minskar den."
    height={ov.stripes.rows.length * 24 + 24}
    margin={{ top: 0, right: 0, bottom: 24, left: 0 }}
    table={stripeTable}
    {status}
  >
    {#snippet children(d)}
      <Stripes dims={d} months={ov.stripes.months} kind={ov.stripes.kind} rows={ov.stripes.rows} />
    {/snippet}
    {#snippet legend()}
      <Legend
        items={[
          { label: '0 · alla minskar takten', fill: divergingFill(0) },
          { label: '0,5 · balans', fill: divergingFill(0.5) },
          { label: '1 · alla ökar takten', fill: divergingFill(1) },
          { label: 'inget index', border: 'var(--c-grid)' }
        ]}
      />
    {/snippet}
  </ChartFrame>
</section>

<style>
  .tiles {
    list-style: none;
    padding: 0;
    margin: 8px 0 0;
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  }
  .tiles li {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 12px 14px;
  }
  .tiles a {
    text-decoration: none;
    font-size: 14px;
  }
  .row {
    display: flex;
    gap: 10px;
    align-items: baseline;
    font-size: 14px;
  }
</style>
