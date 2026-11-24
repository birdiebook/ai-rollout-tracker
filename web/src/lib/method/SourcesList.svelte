<!-- Sources and licences (track W11): every source family in method.json with its licence, branches and how many of
     its series are published. URLs in the source names and licence texts are shown as links (rel="noopener", no
     referrer) and are never fetched by the page. -->
<script lang="ts">
  import type { SourceView } from './prepare';

  let { sources, counts }: { sources: SourceView[]; counts: { n_series: number; n_published: number; n_withheld: number } } = $props();

  let filter = $state<'all' | 'pub' | 'held'>('all');
  const shown = $derived(sources.filter((s) => (filter === 'all' ? true : filter === 'pub' ? s.n_published > 0 : s.n_published < s.n_series)));
  const pubShare = $derived(counts.n_series ? counts.n_published / counts.n_series : 0);
</script>

<div class="summary">
  <div class="bar" role="img" aria-label="{counts.n_published} av {counts.n_series} serier publiceras, {counts.n_withheld} hålls inne av licensskäl">
    <span class="pub" style:width="{pubShare * 100}%"></span>
    <span class="held" style:width="{(1 - pubShare) * 100}%"></span>
  </div>
  <p class="note">
    <strong class="num">{counts.n_published}</strong> av {counts.n_series} serier publiceras. <strong class="num">{counts.n_withheld}</strong>
    hålls inne: de räknas i grenarnas index men visas bara med namn och skäl, aldrig med tal. Publicering kräver en kontrollerad licens.
  </p>
</div>

<div class="pick" role="group" aria-label="Filtrera källor">
  <button type="button" class="chip" aria-pressed={filter === 'all'} onclick={() => (filter = 'all')}>Alla ({sources.length})</button>
  <button type="button" class="chip" aria-pressed={filter === 'pub'} onclick={() => (filter = 'pub')}>Publiceras</button>
  <button type="button" class="chip" aria-pressed={filter === 'held'} onclick={() => (filter = 'held')}>Hålls inne helt eller delvis</button>
</div>

<ul class="sources">
  {#each shown as s, i (i)}
    <li>
      <div class="head">
        <span class="name">{#each s.name as seg, j (j)}{#if 'href' in seg}<a href={seg.href} rel="noopener" referrerpolicy="no-referrer">{seg.text}</a>{:else}{seg.text}{/if}{/each}</span>
        <span class="count num" title="publicerade av serier">{s.n_published}/{s.n_series}</span>
      </div>
      <div class="meta">
        <span class="lic" class:open={s.n_published > 0}>{s.license}</span>
        <span>{s.branches.join(', ')}</span>
      </div>
      <details>
        <summary>Licensvillkor{s.links ? ` och ${s.links} ${s.links === 1 ? 'länk' : 'länkar'}` : ''}</summary>
        <p class="text">{#each s.text as seg, j (j)}{#if 'href' in seg}<a href={seg.href} rel="noopener" referrerpolicy="no-referrer">{seg.text}</a>{:else}{seg.text}{/if}{/each}</p>
      </details>
    </li>
  {/each}
</ul>

<style>
  .summary {
    margin: 8px 0 12px;
  }
  .bar {
    display: flex;
    height: 14px;
    border-radius: 4px;
    overflow: hidden;
    border: 1px solid var(--c-ring);
    max-width: 560px;
  }
  .pub {
    background: var(--c-ink-2);
  }
  .held {
    background: repeating-linear-gradient(45deg, var(--c-surface) 0 3px, var(--c-axis) 3px 5px);
  }
  .pick {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 10px;
  }
  .sources {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr));
    gap: 8px;
  }
  li {
    background: var(--c-surface);
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-md);
    padding: 8px 12px;
    min-width: 0;
    overflow-wrap: anywhere;
  }
  .head {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    font-size: var(--fs-small);
    font-weight: 600;
  }
  .count {
    color: var(--c-ink-2);
    font-weight: 400;
    white-space: nowrap;
  }
  .meta {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 12px;
    font-size: 12px;
    color: var(--c-muted);
    margin-top: 2px;
  }
  .lic {
    border: 1px dashed var(--c-axis);
    border-radius: 999px;
    padding: 0 6px;
  }
  .lic.open {
    border-style: solid;
  }
  details summary {
    cursor: pointer;
    font-size: 12px;
    color: var(--c-ink-2);
    min-height: 24px;
    padding-top: 4px;
  }
  .text {
    font-size: 12px;
    color: var(--c-ink-2);
    margin: 4px 0 2px;
  }
</style>
