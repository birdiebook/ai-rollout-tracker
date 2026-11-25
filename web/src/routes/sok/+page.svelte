<!-- W12: search page and register. The full register (leads, branches, forecasts, pages, every published series by
     branch) is prerendered, so it works without JavaScript and is what the search button links to before
     hydration. With JavaScript the combobox on top searches the same index; the query lives in the hash (#q=…). -->
<script lang="ts">
  import { goto, replaceState } from '$app/navigation';
  import { onMount } from 'svelte';
  import { SearchBox, type SearchItem, type SearchKind } from '$lib/nav';
  import { hashPairs } from '$lib/nav/hash';

  let { data } = $props();
  const items = $derived(data.index.items);
  let query = $state('');
  let mounted = $state(false);

  const groups: { kind: SearchKind; title: string }[] = [
    { kind: 'led', title: 'Leden L1–L9' },
    { kind: 'gren', title: 'Grenarna G1–G9' },
    { kind: 'prognos', title: 'Prognoser' },
    { kind: 'sida', title: 'Sidor' }
  ];
  const series = $derived(items.filter((i) => i.t === 'serie'));
  const byBranch = $derived.by(() => {
    const m = new Map<string, SearchItem[]>();
    for (const s of series) {
      const code = (s.s ?? '').split(' · ')[0] || '–';
      if (!m.has(code)) m.set(code, []);
      m.get(code)?.push(s);
    }
    return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  });
  const branchName = $derived(new Map(items.filter((i) => i.t === 'gren').map((g) => [g.id, g.l])));

  onMount(() => {
    const q = new URLSearchParams(location.hash.replace(/^#/, '')).get('q');
    if (q) query = q;
    mounted = true;
  });
  // the query in the hash, other keys kept
  $effect(() => {
    if (!mounted) return;
    const params = new URLSearchParams();
    let set = false;
    for (const [k, v] of hashPairs(location.hash)) {
      if (k === 'q') {
        if (query.trim() && !set) params.set('q', query.trim());
        set = true;
      } else params.append(k, v);
    }
    if (!set && query.trim()) params.set('q', query.trim());
    const h = params.toString() ? `#${params}` : '';
    if (h !== location.hash) replaceState(location.pathname + location.search + h, {});
  });
</script>

<svelte:head><title>Sök och register – AI-utrullningen</title></svelte:head>

<p class="kicker">Sök · {items.length} poster</p>
<h1>Sök och register</h1>
<p class="lede">Alla publicerade serier, grenar, led och prognoser. Sök överallt på sidan med <kbd>⌘K</kbd> eller <kbd>Ctrl K</kbd>.</p>

<section class="panel search" aria-label="Sök">
  <SearchBox {items} bind:query onpick={(it) => goto(it.h)} idPrefix="sokpage" limit={60} suggest={false} maxHeight="50vh" />
</section>

<section aria-labelledby="reg-h" class="register">
  <h2 id="reg-h">Registret</h2>
  <div class="cols">
    {#each groups as g (g.kind)}
      <div class="grp">
        <h3>{g.title}</h3>
        <ul>
          {#each items.filter((i) => i.t === g.kind) as it (it.id)}
            <li><a href={it.h}>{it.l}</a>{#if it.s}<span class="s">{it.s}</span>{/if}</li>
          {/each}
        </ul>
      </div>
    {/each}
  </div>
</section>

<section aria-labelledby="serier-h" class="register">
  <h2 id="serier-h">Serierna per gren ({series.length})</h2>
  {#each byBranch as [code, list] (code)}
    <details class="br">
      <summary><b>{branchName.get(code) ?? code}</b> <span class="note">{list.length} serier</span></summary>
      <ul class="series">
        {#each list as it (it.id)}
          <li><a href={it.h}>{it.l}</a> <span class="s">{it.s?.split(' · ').slice(1).join(' · ')} · <code>{it.id}</code></span></li>
        {/each}
      </ul>
    </details>
  {/each}
  <p class="note">Serier som hålls inne av licensskäl finns inte här; de räknas och namnges på grensidorna och under Metod.</p>
</section>

<style>
  .search {
    margin-top: 18px;
  }
  kbd {
    font-family: var(--mono);
    font-size: 12px;
    border: 1px solid var(--c-axis);
    border-radius: 4px;
    padding: 0 4px;
  }
  .cols {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 12px 28px;
  }
  @media (min-width: 861px) {
    .cols {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
  h3 {
    margin: 8px 0 4px;
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  li {
    padding: 3px 0;
    line-height: 1.35;
  }
  li a {
    display: inline-block;
    min-height: 24px;
  }
  .s {
    display: block;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  .series .s {
    display: inline;
  }
  .series li {
    padding: 5px 0;
    border-top: 1px solid var(--c-grid);
  }
  details.br {
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-md);
    background: var(--c-surface);
    margin: 8px 0;
    padding: 0 12px;
  }
  summary {
    cursor: pointer;
    min-height: 44px;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  details[open] summary {
    border-bottom: 1px solid var(--c-grid);
  }
  .series {
    padding: 4px 0 8px;
  }
  code {
    font-size: 12px;
    overflow-wrap: anywhere;
  }
</style>
